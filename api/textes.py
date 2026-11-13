"""Textes officiels du corpus : identifiants de source, noms et facons de les citer.

Sert a reconnaitre « article 121-3 du code penal » dans une question, a separer textes et
jurisprudence dans la recherche, et a nommer les sources dans l'interface.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Texte:
    source_id: str
    nom: str
    motifs: tuple[str, ...]  # expressions reconnues, sans accents, en minuscules


TEXTES: tuple[Texte, ...] = (
    Texte("constitution_1958", "Constitution de 1958", (r"constitution",)),
    Texte("code_civil", "Code civil", (r"code civil", r"c\.? ?civ\.?")),
    Texte("code_penal", "Code pénal", (r"code penal", r"c\.? ?pen\.?")),
    Texte("code_procedure_penale", "Code de procédure pénale", (r"code de procedure penale", r"c\.? ?pr\.? ?pen\.?", r"cpp")),
    Texte("code_justice_penale_mineurs", "Code de la justice pénale des mineurs",
          (r"code de la justice penale des mineurs", r"cjpm")),
    Texte("code_procedure_civile", "Code de procédure civile", (r"code de procedure civile", r"c\.? ?pr\.? ?civ\.?", r"cpc")),
    Texte("code_organisation_judiciaire", "Code de l'organisation judiciaire", (r"code de l'organisation judiciaire", r"coj")),
    Texte("code_procedures_civiles_execution", "Code des procédures civiles d'exécution",
          (r"code des procedures civiles d'execution", r"cpce")),
    Texte("code_commerce", "Code de commerce", (r"code de commerce", r"c\.? ?com\.?")),
    Texte("code_monetaire_financier", "Code monétaire et financier", (r"code monetaire et financier", r"cmf")),
    Texte("code_consommation", "Code de la consommation", (r"code de la consommation", r"c\.? ?consom?\.?")),
    Texte("code_propriete_intellectuelle", "Code de la propriété intellectuelle",
          (r"code de la propriete intellectuelle", r"cpi")),
    Texte("code_assurances", "Code des assurances", (r"code des assurances",)),
    Texte("code_travail", "Code du travail", (r"code du travail", r"c\.? ?trav\.?")),
    Texte("code_securite_sociale", "Code de la sécurité sociale", (r"code de la securite sociale", r"css")),
    Texte("code_justice_administrative", "Code de justice administrative", (r"code de justice administrative", r"cja")),
    Texte("code_relations_public_administration", "Code des relations entre le public et l'administration",
          (r"code des relations entre le public et l'administration", r"crpa")),
    Texte("code_collectivites_territoriales", "Code général des collectivités territoriales",
          (r"code general des collectivites territoriales", r"cgct")),
    Texte("code_propriete_personnes_publiques", "Code général de la propriété des personnes publiques",
          (r"code general de la propriete des personnes publiques", r"cg3p")),
    Texte("code_commande_publique", "Code de la commande publique", (r"code de la commande publique", r"ccp")),
    Texte("code_fonction_publique", "Code général de la fonction publique", (r"code general de la fonction publique", r"cgfp")),
    Texte("code_urbanisme", "Code de l'urbanisme", (r"code de l'urbanisme", r"c\.? ?urb\.?")),
    Texte("code_environnement", "Code de l'environnement", (r"code de l'environnement", r"c\.? ?env\.?")),
    Texte("code_construction_habitation", "Code de la construction et de l'habitation",
          (r"code de la construction et de l'habitation", r"cch")),
    Texte("code_entree_sejour_etrangers", "Code de l'entrée et du séjour des étrangers et du droit d'asile",
          (r"code de l'entree et du sejour des etrangers", r"ceseda")),
    Texte("code_electoral", "Code électoral", (r"code electoral",)),
    Texte("ddhc_1789", "Déclaration des droits de l'homme et du citoyen de 1789", ("declaration des droits de l'homme(?: et du citoyen)?", 'ddhc',)),
    Texte("preambule_1946", "Préambule de la Constitution du 27 octobre 1946", ('preambule de (?:la constitution de )?1946',)),
    Texte("code_general_impots", "Code général des impôts", ('code general des impots', 'cgi',)),
    Texte("livre_procedures_fiscales", "Livre des procédures fiscales", ('livre des procedures fiscales', 'lpf',)),
    Texte("code_juridictions_financieres", "Code des juridictions financières", ('code des juridictions financieres', 'cjf',)),
    Texte("code_securite_interieure", "Code de la sécurité intérieure", ('code de la securite interieure', 'csi',)),
    Texte("code_action_sociale_familles", "Code de l'action sociale et des familles", ("code de l'action sociale et des familles", 'casf',)),
    Texte("code_penitentiaire", "Code pénitentiaire", ('code penitentiaire',)),
    Texte("code_expropriation", "Code de l'expropriation pour cause d'utilité publique", ("code de l'expropriation",)),
    Texte("lois", "Lois et ordonnances en vigueur", ()),
)

SOURCES_TEXTES: frozenset[str] = frozenset(t.source_id for t in TEXTES)
NOMS: dict[str, str] = {t.source_id: t.nom for t in TEXTES} | {
    "decisions_conseil_constitutionnel": "Décisions du Conseil constitutionnel",
    "judilibre": "Cour de cassation : chambres civiles, Assemblée plénière, chambre mixte",
    "cass_criminelle": "Cour de cassation : chambre criminelle",
    "cass_sociale": "Cour de cassation : chambre sociale",
    "cass_commerciale": "Cour de cassation : chambre commerciale",
    "conseil_etat": "Conseil d'État et Tribunal des conflits",
}
# Ordre d'essai d'un numero d'article sans code precise (sans prefixe L., R., D.).
ORDRE_PAR_DEFAUT = ("code_civil", "constitution_1958", "code_penal", "code_procedure_civile", "code_procedure_penale")
SOURCES_CASSATION = ("judilibre", "cass_criminelle", "cass_sociale", "cass_commerciale")

_MOTIFS = [(re.compile(rf"(?<![\w]){m}(?![\w])"), t.source_id) for t in TEXTES for m in t.motifs]
# « constitution » seul ne doit pas masquer un code cite dans la meme question : traite a part.
_MOTIFS_CODES = [(r, s) for r, s in _MOTIFS if s != "constitution_1958"]


def sans_accents(texte: str) -> str:
    return unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode().lower().replace("’", "'")


def codes_cites(texte: str) -> tuple[str, ...]:
    """Codes nommes dans le texte, dans l'ordre d'apparition."""
    t = sans_accents(texte)
    trouves = sorted((m.start(), s) for r, s in _MOTIFS_CODES for m in r.finditer(t))
    out: list[str] = []
    for _, s in trouves:
        if s not in out:
            out.append(s)
    return tuple(out)


def cibles_article(numero: str, codes: tuple[str, ...], constitution: bool) -> tuple[str, ...]:
    """Sources ou chercher un numero d'article, par ordre de priorite."""
    if codes:
        return codes + (("constitution_1958",) if constitution else ())
    if constitution:
        return ("constitution_1958",)
    if re.match(r"^[LRDA]", numero):
        # Article a prefixe sans code nomme : tous les codes, la matiere choisie filtre ensuite.
        return tuple(t.source_id for t in TEXTES if t.source_id.startswith("code_") and t.source_id != "code_civil")
    return ORDRE_PAR_DEFAUT


# --- lois et ordonnances : reconnaitre un texte cite ------------------------------------

_MOIS = {"janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7, "aout": 8,
         "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12}
# « n° » perd son « ° » une fois les accents retires : « n 90-14 », « no 92-254 », « n°90-14 ».
_NUM_LOI = r"\bno?\.?\s*(\d{2,4}-\d{1,5})"
_DATE_LOI = rf"(\d{{1,2}})(?:er)?\s+({'|'.join(_MOIS)})\s+(\d{{4}})"
_LOI_CITEE_RE = re.compile(
    rf"\b(?:loi|ordonnance)s?(?:\s+organique)?(?:\s+{_NUM_LOI})?(?:\s*,?\s*du\s+{_DATE_LOI})?")
_NUM_SEUL_RE = re.compile(rf"(?:{_NUM_LOI}|\b(?:loi|ordonnance)\s+(\d{{4}}-\d{{1,5}})\b)")
_DATE_RE = re.compile(rf"\bdu\s+{_DATE_LOI}")


def _cle_date(j: str, mois: str, an: str) -> str:
    return f"date:{an}-{_MOIS[mois]:02d}-{int(j):02d}"


def cles_texte_loi(nom: str) -> frozenset[str]:
    """Cles d'un nom de texte (« Loi n°90-14 du 2 janvier 1990 » -> numero et date)."""
    t = sans_accents(nom)
    cles = set()
    m = _NUM_SEUL_RE.search(t)
    if m:
        cles.add("num:" + (m.group(1) or m.group(2)))
    d = _DATE_RE.search(t)
    if d:
        cles.add(_cle_date(*d.groups()))
    return frozenset(cles)


def lois_citees(texte: str) -> tuple[frozenset[str], ...]:
    """Lois ou ordonnances citees dans une question, chacune sous forme de cles (numero, date)."""
    out: list[frozenset[str]] = []
    for m in _LOI_CITEE_RE.finditer(sans_accents(texte)):
        num, j, mois, an = m.groups()
        cles = set()
        if num:
            cles.add("num:" + num)
        if an:
            cles.add(_cle_date(j, mois, an))
        if cles and frozenset(cles) not in out:
            out.append(frozenset(cles))
    return tuple(out)


def meme_loi(citee: frozenset[str], nom_texte: str) -> bool:
    """Le texte nomme correspond-il a la loi citee ? Le numero prime sur la date quand les deux sont connus."""
    cles = cles_texte_loi(nom_texte)
    num_c = {c for c in citee if c.startswith("num:")}
    num_t = {c for c in cles if c.startswith("num:")}
    if num_c and num_t:
        return bool(num_c & num_t)
    return bool(citee & cles)
