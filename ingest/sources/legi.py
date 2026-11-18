"""Code civil depuis l'archive DILA LEGI (toutes les versions d'articles, datees).

1 passage = 1 version d'article (identifiant LEGIARTI). Les versions anciennes sont
conservees avec en_vigueur = false pour pouvoir repondre "dans sa redaction applicable
au litige" ; la recherche filtre par defaut sur les versions en vigueur.

Les fichiers du Code civil sont extraits avec ceux des autres codes (ingest.sources.codes.extraire),
puis relus depuis le disque.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from datetime import date
from pathlib import Path

from ingest import dila
from ingest.jurisprudence import date_fr
from ingest.models import Passage

SOURCE_ID = "code_civil"
FONDS = "legi"
CODE_ID = "LEGITEXT000006070721"  # Code civil (verifie : TITREFULL = "Code civil")
CODE_NOM = "Code civil"
DATE_INFINIE = "2999-01-01"
DATE_NON_FIXEE = "2222-02-22"  # date de fin DILA d'une abrogation programmee mais pas encore datee (CGI 302 J)

ETATS = {
    "VIGUEUR": "en vigueur",
    "MODIFIE": "modifié",
    "ABROGE": "abrogé",
    "TRANSFERE": "transféré",
    "MODIFIE_MORT_NE": "jamais entré en vigueur",
    "VIGUEUR_DIFF": "entrée en vigueur différée",
    "ABROGE_DIFF": "en vigueur, abrogation différée",
}

# Lien Legifrance vers une version d'article. Verifie dans un navigateur le 2026-11-18 (audit B11) : les codes
# sont sous /codes/, les textes non codifies (lois, ordonnances, DDHC, Preambule de 1946) sous /loda/ ; /codes/
# ouvrait aussi ces derniers, mais avec l'interface d'un code (« Rechercher dans tout le code »).
URL_ARTICLE = "https://www.legifrance.gouv.fr/codes/article_lc/{id}"
URL_ARTICLE_TEXTE = "https://www.legifrance.gouv.fr/loda/article_lc/{id}"


# Ligne sans contenu : « I. Paragraphe modificateur », « II. - (Abrogé). », « (texte non reproduit). »
_LIGNE_VIDE = re.compile(
    r"^(?:(?:[IVX]+|\d+°?|[a-z])\s*[.)°]?\s*[-–:]?\s*)?\(?\s*(?:(?:alin[ée]as?|paragraphes?|dispositions?|articles?)\s+)?"
    r"(?:modificat(?:eur|eurs|rice|rices)|abrog[ée]e?s?|non reproduite?s?|texte non reproduit|périmée?s?)\s*\)?\s*\.?$",
    re.IGNORECASE)


def sans_contenu(alineas: list[str]) -> bool:
    """Article dont chaque alinea n'est qu'une mention (modificateur, abroge, non reproduit) : 22 passages de lois
    « en vigueur » sans rien a citer (audit du 2026-11-18, B10)."""
    lignes = [l.strip() for a in alineas for l in a.split("\n") if l.strip()]
    return bool(lignes) and all(_LIGNE_VIDE.match(l) for l in lignes)


def _couvre(el: ET.Element, date: str) -> bool:
    return el.get("debut", "") <= date < el.get("fin", DATE_INFINIE)


def etat_reel(etat: str, debut: str, fin: str, aujourdhui: str) -> tuple[bool, str]:
    """(en vigueur aujourd'hui, libelle), d'apres l'etat DILA corrige par les dates quand elles le contredisent.

    ABROGE_DIFF : version applicable dont l'abrogation est programmee (ex. refonte du Code de procedure penale au
    1er janvier 2029) ; la compter hors vigueur retirait 3 718 articles actuels de la recherche (D61).
    ABROGE ou MODIFIE avec une date de fin a venir : la DILA marque parfois ainsi la version applicable dont la fin
    est programmee (LPF L24 a L40 « abroges » du 18 aout 1993 au 1er mai 2027, C. trav. R4451-39) : 19 articles
    applicables etaient affiches abroges (audit du 2026-11-18, B1).
    VIGUEUR dont l'entree en vigueur est a venir, ou fixee au 1er janvier 2999 (date DILA non fixee,
    ordonnance 2025-229 art. 68) : pas encore en vigueur.
    """
    commence = bool(debut) and debut <= aujourdhui
    fin_a_venir = bool(fin) and fin != DATE_INFINIE and fin > aujourdhui
    if etat in ("VIGUEUR", "VIGUEUR_DIFF") and not commence:
        return False, "pas encore en vigueur"
    if etat == "VIGUEUR":
        return True, ETATS[etat]
    if etat in ("ABROGE_DIFF", "ABROGE") and commence and fin_a_venir:
        return True, ETATS["ABROGE_DIFF"]
    if etat == "MODIFIE" and commence and fin_a_venir:
        return True, "en vigueur, modification différée"
    return False, ETATS.get(etat, etat.lower())


def _periode(debut: str, fin: str, aujourdhui: str) -> str:
    if debut == DATE_INFINIE:
        return "date d'entrée en vigueur non fixée"
    if debut > aujourdhui:
        return f"à compter du {date_fr(debut)}"
    # DATE_FIN absente : traitee comme « sans date de fin » (sinon l'entete affichait « du ... au »).
    if not fin or fin in (DATE_INFINIE, DATE_NON_FIXEE):
        return f"depuis le {date_fr(debut)}"
    return f"du {date_fr(debut)} au {date_fr(fin)}"


def plan(root: ET.Element, date: str) -> list[str]:
    """Chemin Livre > Titre > Chapitre... applicable a la date de debut de la version."""
    chemin: list[str] = []
    noeud = root.find("CONTEXTE/TEXTE")
    while noeud is not None:
        tm = noeud.find("TM")
        if tm is None:
            break
        titres = tm.findall("TITRE_TM")
        choisi = next((t for t in titres if _couvre(t, date)), titres[-1] if titres else None)
        if choisi is not None:
            chemin.append(dila.clean("".join(choisi.itertext())))
        noeud = tm
    return chemin


def parse_article(raw: bytes, *, date_recuperation: str, version_archive: str,
                  source_id: str = SOURCE_ID, nom: str | None = CODE_NOM) -> Passage | None:
    """nom=None : nom du texte lu dans l'article (lois et ordonnances)."""
    root = ET.fromstring(raw)
    if root.tag != "ARTICLE":
        return None
    art_id = dila.text_of(root, "META/META_COMMUN/ID")
    num = dila.text_of(root, "META/META_SPEC/META_ARTICLE/NUM")
    etat = dila.text_of(root, "META/META_SPEC/META_ARTICLE/ETAT")
    debut = dila.text_of(root, "META/META_SPEC/META_ARTICLE/DATE_DEBUT")
    fin = dila.text_of(root, "META/META_SPEC/META_ARTICLE/DATE_FIN")
    # le fichier contient aussi un CONTENU de NOTA : on cible BLOC_TEXTUEL
    bloc = root.find("BLOC_TEXTUEL/CONTENU")
    alineas = dila.contenu_lines(ET.tostring(bloc, encoding="unicode")) if bloc is not None else []
    if not num or not alineas or sans_contenu(alineas):
        return None
    # Version de duree nulle ou negative (C. civ. 214 « du 1er juillet 1976 au 1er juillet 1976 ») : jamais
    # applicable, elle s'affichait dans l'historique des versions (B10). Les versions mort-nees restent.
    if fin and fin != DATE_INFINIE and fin <= debut and etat != "MODIFIE_MORT_NE":
        return None
    nota_el = root.find("NOTA/CONTENU")
    nota = " ".join(dila.contenu_lines(ET.tostring(nota_el, encoding="unicode"))) if nota_el is not None else ""

    aujourdhui = date.today().isoformat()
    en_vigueur, statut = etat_reel(etat, debut, fin, aujourdhui)
    chemin = plan(root, debut)
    if nom is None:
        titre_txt = root.find("CONTEXTE/TEXTE/TITRE_TXT")
        nom = (titre_txt.get("c_titre_court") or dila.clean("".join(titre_txt.itertext()))) if titre_txt is not None else "Texte"
        texte_id = titre_txt.get("id_txt") if titre_txt is not None else None
    else:
        texte_id = None
    periode = _periode(debut, fin, aujourdhui)
    meta = {
        "code": nom,
        "id_legi": art_id,
        "etat": etat,
        "en_vigueur": en_vigueur,
        "date_debut": debut,
        "date_fin": None if not fin or fin == DATE_INFINIE else fin,
        "plan": chemin,
    }
    # Entree en vigueur datee apres l'import : recalculee a la requete (api.textes.en_vigueur_aujourdhui).
    if etat in ("VIGUEUR", "VIGUEUR_DIFF") and debut != DATE_INFINIE and debut > aujourdhui:
        meta["en_vigueur_le"] = debut
    if nota:
        meta["nota"] = nota
    if texte_id:
        meta["id_texte"] = texte_id
    return Passage(
        id=f"{source_id}:{art_id}",
        source_id=source_id,
        type="article",
        numero=num,
        titre=" > ".join(chemin) or None,
        alineas=alineas,
        url=(URL_ARTICLE if source_id.startswith("code_") or source_id == "livre_procedures_fiscales"
             else URL_ARTICLE_TEXTE).format(id=art_id),
        version=f"Version {periode}, article {statut} ({version_archive})",
        date_recuperation=date_recuperation,
        meta=meta,
        entete=f"{nom}, article {num} ({statut}, {periode})" + (f" - {chemin[-1]}" if chemin else ""),
    )


def _cle_num(p: Passage):
    parts = re.split(r"(\d+)", p.numero or "")
    return ([int(x) if x.isdigit() else x for x in parts], p.meta["date_debut"])


def collect(raw_dir: Path, *, date_recuperation: str) -> Iterator[Passage]:
    from ingest.sources import codes  # import local : codes importe ce module

    dossier = codes.extraire(raw_dir) / CODE_ID
    version_archive = f"archive DILA LEGI du {dila.date_corpus(raw_dir, FONDS)}"

    passages: dict[str, Passage] = {}
    for f in dossier.rglob("LEGIARTI*.xml"):
        p = parse_article(f.read_bytes(), date_recuperation=date_recuperation, version_archive=version_archive)
        if p is not None:
            passages.setdefault(p.id, p)
    if sum(1 for p in passages.values() if p.meta["en_vigueur"]) < 2000:
        raise RuntimeError("Moins de 2000 articles en vigueur : extraction incomplete ?")
    yield from sorted(passages.values(), key=_cle_num)
