"""Lexique local : notions du programme de licence -> articles de principe.

Complete la reformulation par Gemini (api/expansion.py) sans en dependre : quand le modele est
indisponible ou lent, la recherche retrouvait 3 questions de cours sur 8 seulement (D47). Comme pour la
reformulation, ces articles ne sont jamais montres tels quels : seul leur texte officiel du corpus est
ajoute aux candidats, et le controle des citations reste inchange.

Chaque entree : motif (expression reguliere sur la question en minuscules et sans accents) -> articles.
Numerotation actuelle uniquement. Chaque article est verifie par tests/test_lexique.py sur l'index
reel quand il est present. N'ajouter que des correspondances de cours certaines.
"""

from __future__ import annotations

import re

from api.textes import sans_accents

CC, CONST = "code_civil", "constitution_1958"
MAX_LEXIQUE = 4

NOTIONS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    # --- introduction au droit -------------------------------------------------
    (r"entree en vigueur d.{0,6}loi|publication des lois|lois? .{0,40}opposable", ((CC, "1"),)),
    (r"retroactiv", ((CC, "2"),)),
    (r"deni de justice|loi (?:est )?obscure|silence de la loi|insuffisance de la loi", ((CC, "4"),)),
    (r"arrets? de reglement|lie par ses (?:propres )?decisions|precedents? judiciaires?|jurisprudence.{0,20}source",
     ((CC, "5"), (CC, "1355"))),
    (r"autorite de (?:la )?chose jugee", ((CC, "1355"),)),
    (r"ordre public|bonnes moeurs", ((CC, "6"), (CC, "1102"), (CC, "1162"))),
    (r"vie privee", ((CC, "9"),)),
    (r"presomption d.innocence", ((CC, "9-1"),)),
    (r"corps humain", ((CC, "16"), (CC, "16-1"))),
    (r"\bmajeurs?\b|\bmajorite\b", ((CC, "414"),)),
    (r"droit de propriete|\bla propriete\b", ((CC, "544"),)),
    (r"meubles?.{0,12}immeubles?|immeubles?.{0,12}meubles?", ((CC, "516"),)),
    (r"charge de la preuve", ((CC, "1353"),)),
    (r"prescription extinctive|delai de prescription", ((CC, "2219"), (CC, "2224"))),
    (r"pacte civil de solidarite|\bpacs\b", ((CC, "515-1"),)),
    # --- droit constitutionnel ---------------------------------------------------
    (r"revision (?:de la )?constitution|revision constitutionnelle|reviser la constitution|forme republicaine",
     ((CONST, "89"),)),
    (r"souverainete", ((CONST, "3"),)),
    (r"question prioritaire de constitutionnalite|\bqpc\b", ((CONST, "61-1"),)),
    (r"saisi\w* (?:du |le )?conseil constitutionnel|controle de constitutionnalite", ((CONST, "61"),)),
    (r"motion de censure|responsabilite du gouvernement|49.{0,4}alinea 3|49-3", ((CONST, "49"),)),
    (r"(?:dissolution|dissoudre) (?:de )?l.assemblee", ((CONST, "12"),)),
    (r"domaine de la loi", ((CONST, "34"), (CONST, "37"))),
    (r"destitu", ((CONST, "68"),)),
    (r"libre administration", ((CONST, "72"),)),
    (r"hierarchie des normes|autorite des traites|traites? (?:internationaux|et (?:les )?lois)", ((CONST, "55"),)),
    # --- droit des contrats ------------------------------------------------------
    (r"droit des contrats|theorie generale du contrat", ((CC, "1101"), (CC, "1103"), (CC, "1104"), (CC, "1128"))),
    (r"force obligatoire", ((CC, "1103"), (CC, "1193"))),
    (r"liberte contractuelle", ((CC, "1102"),)),
    (r"bonne foi.{0,40}contrat|contrat.{0,40}bonne foi", ((CC, "1104"),)),
    (r"pourparlers|negociations? precontractuel", ((CC, "1112"),)),
    (r"devoir d.information", ((CC, "1112-1"),)),
    (r"formation du contrat|comment se forme", ((CC, "1113"),)),
    (r"\boffre de contracter|\bl.offre\b", ((CC, "1114"), (CC, "1115"), (CC, "1116"))),
    (r"\bacceptation", ((CC, "1118"),)),
    (r"pacte de preference", ((CC, "1123"),)),
    (r"promesse unilaterale", ((CC, "1124"),)),
    (r"conditions de validite", ((CC, "1128"),)),
    (r"vices? du consentement", ((CC, "1130"),)),
    (r"violence economique|etat de dependance", ((CC, "1143"),)),
    (r"\bviolence", ((CC, "1140"),)),
    (r"\bdol\b", ((CC, "1137"),)),
    (r"\berreur.{0,30}(?:nullite|contrat)", ((CC, "1132"),)),
    (r"\blesion", ((CC, "1168"),)),
    (r"obligation essentielle|prive de (?:sa )?substance", ((CC, "1170"),)),
    (r"clauses? abusives?|contrat d.adhesion", ((CC, "1171"),)),
    (r"nullite (?:absolue|relative)", ((CC, "1179"),)),
    (r"caducite", ((CC, "1186"),)),
    (r"interpret\w* (?:un |le )?contrat", ((CC, "1188"),)),
    (r"imprevision", ((CC, "1195"),)),
    (r"effet relatif", ((CC, "1199"),)),
    (r"inexecution", ((CC, "1217"),)),
    (r"force majeure", ((CC, "1218"),)),
    (r"exception d.inexecution", ((CC, "1219"),)),
    (r"execution forcee", ((CC, "1221"),)),
    (r"resolution du contrat|contrat .{0,20}resolu", ((CC, "1224"),)),
    (r"dommages(?: |-)et(?: |-)interets", ((CC, "1231-1"),)),
    # --- responsabilite et quasi-contrats ---------------------------------------
    (r"responsabilite (?:civile )?(?:pour faute|du fait personnel|delictuelle)|faute.{0,40}(?:dommage|responsab)", ((CC, "1240"), (CC, "1241"))),
    (r"fait des choses|fait d.autrui|\bparents\b.{0,40}(?:responsab|enfants?)", ((CC, "1242"),)),
    (r"\banimal|\banimaux", ((CC, "1243"),)),
    (r"produits? defectueux", ((CC, "1245"),)),
    (r"gestion d.affaires", ((CC, "1301"),)),
    (r"paiement de l.indu|\bl.indu\b", ((CC, "1302"), (CC, "1302-1"))),
    (r"enrichissement injustifie|enrichissement sans cause", ((CC, "1303"),)),
)

_COMPILES = tuple((re.compile(motif), arts) for motif, arts in NOTIONS)


def normaliser(question: str) -> str:
    return sans_accents(question.lower().replace("’", "'"))


def suggestions(question: str, maximum: int = MAX_LEXIQUE) -> list[tuple[str, str]]:
    """Articles de principe des notions reconnues dans la question, dans l'ordre du lexique."""
    q = normaliser(question)
    out: list[tuple[str, str]] = []
    for motif, arts in _COMPILES:
        if motif.search(q):
            for a in arts:
                if a not in out:
                    out.append(a)
        if len(out) >= maximum:
            break
    return out[:maximum]
