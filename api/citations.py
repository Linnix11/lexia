"""Validation des citations produites par le modele.

Principes :
  - une source citee doit etre un des extraits fournis (S1..Sn) ; sinon elle est retiree ;
  - un element de droit positif sans source valide est retire ;
  - un element qui mentionne un numero d'article / de decision / de pourvoi absent de tous
    les extraits fournis est retire (le modele ne doit rien inventer) ;
  - s'il ne reste aucune affirmation sourcee, la reponse devient une abstention.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from api.references import references_non_couvertes

_LABEL_RE = re.compile(r"S\d+")
# « [S1] », « (S2) », « [S1, S5] » ecrits dans le texte : la source s'affichait deux fois sur la meme
# ligne (dans le texte et en pastille). Retires du texte et rattaches aux sources de l'element.
_LABELS_DANS_TEXTE = re.compile(r"\s*[\[(]\s*S\d+(?:\s*(?:,|;|/|et)\s*S\d+)*\s*[\])]", re.IGNORECASE)


@dataclass
class Controle:
    citations_retirees: int = 0
    elements_retires: int = 0
    references_non_verifiees: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "citations_retirees": self.citations_retirees,
            "elements_retires": self.elements_retires,
            "references_non_verifiees": self.references_non_verifiees,
        }


def labels_valides(brutes, table: dict[str, dict], controle: Controle) -> list[str]:
    """Normalise ['[S1]', 's2', 'S9'] -> ids de passages connus, sans doublon."""
    ids: list[str] = []
    for b in brutes or []:
        m = _LABEL_RE.search(str(b).upper())
        if m and m.group(0) in table:
            pid = table[m.group(0)]["id"]
            if pid not in ids:
                ids.append(pid)
        else:
            controle.citations_retirees += 1
    return ids


def verifier_texte(texte: str, passages: list[dict], controle: Controle) -> bool:
    manquantes = references_non_couvertes(texte, passages)
    if manquantes:
        controle.references_non_verifiees.extend(m for m in manquantes if m not in controle.references_non_verifiees)
        return False
    return True


def nettoyer_elements(items, table: dict[str, dict], controle: Controle, *, exiger_source: bool,
                      rubriques: tuple[str, ...] = ()) -> list[dict]:
    """rubriques : rubriques admises pour ces elements (le champ est garde s'il en fait partie)."""
    passages = list(table.values())
    out: list[dict] = []
    for it in items or []:
        texte = str((it or {}).get("texte", "")).strip()
        dans_texte = [lab for m in _LABELS_DANS_TEXTE.finditer(texte) for lab in _LABEL_RE.findall(m.group(0).upper())]
        texte = _LABELS_DANS_TEXTE.sub("", texte).strip()
        if not texte:
            continue
        sources = labels_valides(list((it or {}).get("sources") or []) + dans_texte, table, controle)
        if (exiger_source and not sources) or not verifier_texte(texte, passages, controle):
            controle.elements_retires += 1
            continue
        element = {"texte": texte, "sources": sources}
        rubrique = str((it or {}).get("rubrique") or "").strip()
        if rubrique in rubriques:
            element["rubrique"] = rubrique
        out.append(element)
    return out


def valider_reponse(brut: dict, table: dict[str, dict], mode: str = "expliquer") -> tuple[dict, Controle]:
    """mode : dans les modes methode, une explication de methode sans source est acceptee
    (la methode n'est pas une regle de droit) ; le droit positif exige toujours une source."""
    controle = Controle()
    statut = brut.get("statut") if brut.get("statut") in ("reponse", "abstention", "hors_champ") else "abstention"
    message = str(brut.get("message") or "").strip()
    titre = str(brut.get("titre") or "").strip()
    passages = list(table.values())
    # Le titre est affiche en gros au-dessus de la reponse : un numero d'article invente y restait,
    # alors qu'il etait retire partout ailleurs.
    if not verifier_texte(titre, passages, controle):
        titre = ""

    if statut != "reponse":
        if not verifier_texte(message, passages, controle):
            message = ""
        return {"statut": statut, "titre": titre, "droit_positif": [], "explication": [],
                "points_incertains": [], "reponse_directe": [], "message": message or _message_defaut(statut)}, controle

    droit = nettoyer_elements(brut.get("droit_positif"), table, controle, exiger_source=True)
    from api.prompts import MAX_REPONSE_DIRECTE, MODES_METHODE, RUBRIQUES  # import local : prompts importe deja ce module indirectement
    expl = nettoyer_elements(brut.get("explication"), table, controle, exiger_source=False,
                             rubriques=RUBRIQUES.get(mode, RUBRIQUES["expliquer"]))
    incert = nettoyer_elements(brut.get("points_incertains"), table, controle, exiger_source=False)
    # Lue en premier : meme exigence que le droit positif (source valide, aucune reference inventee). Elle ne
    # compte pas pour eviter l'abstention : la reponse doit tenir par ses developpements sources.
    directe = nettoyer_elements(brut.get("reponse_directe"), table, controle,
                                exiger_source=True)[:MAX_REPONSE_DIRECTE]

    methode_seule = mode in MODES_METHODE and bool(expl)
    if not droit and not any(e["sources"] for e in expl) and not methode_seule:
        return {"statut": "abstention", "titre": titre, "droit_positif": [], "explication": [],
                "points_incertains": [], "reponse_directe": [], "message": _message_defaut("abstention")}, controle
    return {"statut": "reponse", "titre": titre, "droit_positif": droit, "explication": expl,
            "points_incertains": incert, "reponse_directe": directe, "message": ""}, controle


def _message_defaut(statut: str) -> str:
    if statut == "hors_champ":
        return ("Lexia est un outil d'étude : il ne donne pas de conseil sur une situation personnelle. "
                "Pour un litige réel, adressez-vous à un professionnel du droit (avocat, point d'accès au droit).")
    return ("Les sources disponibles ne permettent pas de répondre de façon vérifiable. "
            "Reformulez la question ou précisez la matière, l'article ou la décision visés.")
