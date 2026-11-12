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
CP, CPP, CT = "code_penal", "code_procedure_penale", "code_travail"
CJA, CRPA = "code_justice_administrative", "code_relations_public_administration"
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
    (r"prescription extinctive|delai de prescription(?!.{0,30}(?:delit|crime|contravention|penal|action publique))",
     ((CC, "2219"), (CC, "2224"))),
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
    # Vice du consentement dans une succession : regle propre (art. 777), avant celles des contrats.
    (r"option successorale|(?:heriti|success)\w*.{0,60}(?:\bdol\b|erreur|violence)|(?:\bdol\b|erreur|violence).{0,60}(?:heriti|success)",
     ((CC, "777"),)),
    # Dol : definition, sanction (nullite relative), dol d'un tiers, erreur provoquee par dol.
    (r"reticence dolosive", ((CC, "1137"), (CC, "1112-1"))),
    (r"\bdol\b|\bdolosi", ((CC, "1137"), (CC, "1131"), (CC, "1138"), (CC, "1139"))),
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
    # --- droit penal (Code penal, Code de procedure penale) -------------------------------
    (r"legitime defense", ((CP, "122-5"), (CP, "122-6"))),
    (r"etat de necessite", ((CP, "122-7"),)),
    (r"contrainte (?:morale|physique)|force majeure.{0,40}penal|penal.{0,40}force majeure", ((CP, "122-2"),)),
    (r"erreur (?:sur le|de) droit", ((CP, "122-3"),)),
    (r"ordre de la loi|commandement de l.autorite legitime", ((CP, "122-4"),)),
    (r"trouble psychique|abolition du discernement|alteration du discernement", ((CP, "122-1"),)),
    (r"(?:mineurs?|minorite).{0,40}penal", ((CP, "122-8"),)),
    (r"legalite des delits|legalite criminelle|legalite penale|nullum crimen", ((CP, "111-3"), (CP, "111-4"))),
    (r"interpretation stricte", ((CP, "111-4"),)),
    (r"in mitius|loi penale (?:plus douce|dans le temps)|application de la loi penale dans le temps", ((CP, "112-1"),)),
    (r"\btentative\b", ((CP, "121-5"),)),
    (r"\bcomplic", ((CP, "121-7"), (CP, "121-6"))),
    (r"responsabilite penale des personnes morales|personnes? morales?.{0,30}penalement", ((CP, "121-2"),)),
    (r"homicide involontaire", ((CP, "221-6"), (CP, "121-3"))),
    (r"element (?:moral|intentionnel)|faute d.imprudence|delits? non intentionnels?|intention (?:coupable|de commettre)", ((CP, "121-3"),)),
    (r"\bmeurtre", ((CP, "221-1"),)),
    (r"\bassassinat", ((CP, "221-3"),)),
    (r"\bvol\b", ((CP, "311-1"),)),
    (r"escroquerie", ((CP, "313-1"),)),
    (r"abus de confiance", ((CP, "314-1"),)),
    (r"prescription de l.action publique|prescription.{0,30}(?:crimes?|delits?)\b", ((CPP, "7"), (CPP, "8"))),
    (r"garde a vue", ((CPP, "62-2"),)),
    # --- droit social (Code du travail) -----------------------------------------------------
    (r"licenciement (?:pour motif |)economique|motif economique", ((CT, "L1233-3"),)),
    (r"cause reelle et serieuse|licenciement pour motif personnel", ((CT, "L1232-1"),)),
    (r"entretien prealable", ((CT, "L1232-2"),)),
    (r"rupture conventionnelle", ((CT, "L1237-11"),)),
    (r"(?:contrat (?:de travail )?a )?duree indeterminee|\bcdi\b", ((CT, "L1221-2"),)),
    (r"(?:contrat (?:de travail )?a )?duree determinee|\bcdd\b", ((CT, "L1242-1"), (CT, "L1242-2"))),
    (r"periode d.essai", ((CT, "L1221-19"),)),
    (r"harcelement moral", ((CT, "L1152-1"),)),
    (r"harcelement sexuel", ((CT, "L1153-1"),)),
    (r"discrimination.{0,40}(?:travail|salari|embauche|emploi|recrutement)|(?:travail|salari|embauche|emploi|recrutement).{0,40}discrimination",
     ((CT, "L1132-1"),)),
    (r"duree legale du travail|35 heures|trente-cinq heures", ((CT, "L3121-27"),)),
    (r"\bsmic\b|salaire minimum", ((CT, "L3231-2"),)),
    (r"comite social et economique|\bcse\b", ((CT, "L2311-2"),)),
    (r"\bgreve", ((CT, "L2511-1"),)),
    (r"preavis.{0,30}licenciement|licenciement.{0,30}preavis|indemnite de licenciement", ((CT, "L1234-1"),)),
    (r"rupture du contrat de travail", ((CT, "L1231-1"),)),
    # --- droit administratif (Code de justice administrative, CRPA) ---------------------------
    (r"exces de pouvoir|\brep\b|recours (?:en|pour) annulation", ((CJA, "R421-1"),)),
    (r"refere.suspension", ((CJA, "L521-1"),)),
    (r"refere.liberte|liberte fondamentale.{0,40}refere|refere.{0,40}liberte fondamentale", ((CJA, "L521-2"),)),
    (r"refere.mesures? utiles|refere conservatoire", ((CJA, "L521-3"),)),
    (r"pouvoir d.injonction|injonction.{0,40}(?:administration|juge administratif)", ((CJA, "L911-1"),)),
    (r"silence (?:garde par |de )l.administration|silence vaut (?:acceptation|accord|rejet)|administration.{0,20}garde le silence",
     ((CRPA, "L231-1"),)),
    (r"motivation des (?:actes|decisions) administrati", ((CRPA, "L211-2"),)),
    (r"(?:retrait|abrogation).{0,40}(?:acte|decision)s? administrati|decisions? creatrices? de droits", ((CRPA, "L242-1"), (CRPA, "L243-1"))),
    (r"(?:acces|communication).{0,30}documents? administratifs?", ((CRPA, "L311-1"),)),
    # --- notions generales : en dernier, pour laisser la place aux notions precises de la question ---
    (r"droit des contrats|theorie generale du contrat", ((CC, "1101"), (CC, "1103"), (CC, "1104"), (CC, "1128"))),
)

_COMPILES = tuple((re.compile(motif), arts) for motif, arts in NOTIONS)


# Parties du Code civil propres a une matiere : un article qui en vient (ex. art. 777, nullite de l'option
# successorale pour dol) n'est garde que si la question parle de cette matiere. Sans ce filtre, toute question
# sur le dol, l'erreur ou la violence ramenait l'article 777, et le modele en tirait une regle des contrats.
MATIERES_SPECIALES: tuple[tuple[str, re.Pattern], ...] = (
    ("Des successions", re.compile(r"success|heriti|herit|\blegs\b|legataire|testament|defunt|indivision|option successorale")),
    ("Des libéralités", re.compile(r"liberalit|donation|testament|\blegs\b|legataire|reserve hereditaire|quotite disponible")),
    ("régimes matrimoniaux", re.compile(r"regimes? matrimoni|contrat de mariage|epoux|conjoint|communaute")),
)


def hors_matiere(passage: dict, question: str) -> bool:
    """Article du Code civil d'une matiere speciale dont la question ne parle pas."""
    if passage.get("source_id") != CC:
        return False
    plan = " ".join((passage.get("meta") or {}).get("plan") or [])
    q = normaliser(question)
    return any(titre in plan and not mots.search(q) for titre, mots in MATIERES_SPECIALES)


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
