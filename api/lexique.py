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
CPC = "code_procedure_civile"
DDHC, P46, CSI = "ddhc_1789", "preambule_1946", "code_securite_interieure"
CGI, LPF, CJF = "code_general_impots", "livre_procedures_fiscales", "code_juridictions_financieres"
CASF, CPEN, CEXP = "code_action_sociale_familles", "code_penitentiaire", "code_expropriation"
CJPM, CGCT, CCONSO = "code_justice_penale_mineurs", "code_collectivites_territoriales", "code_consommation"
CCOM, CSS, CGPPP = "code_commerce", "code_securite_sociale", "code_propriete_personnes_publiques"
TUE, TFUE, CDF = "tue", "tfue", "charte_droits_fondamentaux_ue"
MAX_LEXIQUE = 4
_SILENCE = (r"(?:\bcach(?:ant|ait|aient|er)\b|\b(?:a|avait|ont|avaient|lui|leur|il|elle) cache\b|dissimul"
            r"|(?<!vice )(?<!defaut )\bcache (?:que|qu|l.|le|la|les|une?|des|son|sa|ses|a|aux?)\b"
            r"|\bmensong|\bmenti\b|\bmentant\b|\bment\b"
            r"|sans (?:le |l.)?(?:lui |leur )?(?:dire|signaler|preciser|indiquer|reveler|mentionner|avertir|informer)"
            r"|sans qu.on (?:le |l.)?(?:lui |leur )?(?:dise|signale|precise|indique|revele|mentionne|avertisse|informe)"
            r"|ne (?:l.)?(?:lui |leur )?(?:a|avait) (?:pas|jamais|rien) (?:dit|signale|precise|indique|revele|mentionne)"
            r"|sous silence)")
_CONTRAT = r"(?:\bvend|\bvente|\bachet|\bachat|\bacquere|contrat|\bsign|\bcede|\bcession|\bbail\b|\blou)"
_DOMMAGE = (r"(?:\bbless|renvers|percut|\bcass(?:e|ant)\b|\bbris(?:e|ant)\b|\babim|endommag|\bdegats?\b|degrad"
            r"|\bray(?:e|er|ant)\b|\bfractur|\bheurt|\bmord|\bgriff|\bpietin"
            # tag, graffiti : exemple meme de la consigne (api/prompts.py, regle 8), qui ramenait 682 et 1253
            # (audit du 2026-11-19, SRC-1)
            r"|\btagu|\btags?\b|graffit|vandalis)")
_REPARER = r"(?:repar|indemni|dedommag|dommages|\bpayer\b|rembours|responsable|poursuivre|se retourner)"
_SUSPENDRE = (r"(?:refuser?|cesser?|suspendre|arreter|retenir) (?:de )?(?:payer|livrer|fournir|travailler|executer"
              r"|la fourniture|le paiement|sa prestation)")
_MANQUE = (r"(?:ne (?:livre|paie|paye|fournit|execute)\w* (?:pas|plus)|pas (?:livre|paye)|impaye"
           r"|cesse de (?:payer|livrer|fournir))")
_AGE = (r"(?:\benfants?\b|\bfils\b|\bfille\b|\bmineure?s?\b|adolescent|\b(?:[2-9]|1[0-7]) ans\b"
        r"|\b(?:deux|trois|quatre|cinq|six|sept|huit|neuf|dix|onze|douze|treize|quatorze|quinze|seize|dix-sept) ans\b)")

# Choses (sans moteur) qui peuvent causer un dommage dans un cas pratique : la garde de la chose (art. 1242 al. 1)
# n'etait jamais developpee, 0 cas sur 6 (D115). Vehicule a moteur exclu : loi du 5 juillet 1985, pas 1242 al. 1.
_CHOSE = (r"\b(?:ballons?|balles?|skate(?:board)?s?|planches? a roulettes|trottinettes?|velos?|bicyclettes?"
    r"|rollers?|patins?|pierres?|cailloux|caillou|lance-pierres?|petards?|fusees?|boules?|raquettes?|batte"
    r"|frisbees?|drones?|cerfs?-volants?|pots? de fleurs?|echelles?|branches?)\b")
_CHOSES = re.compile(_CHOSE.replace("(?:", "(?P<chose>", 1))

# Accident de la circulation : un vehicule terrestre a moteur cause le dommage. La loi n° 85-677 du 5 juillet 1985
# s'applique seule et ecarte les articles 1240 a 1242 ; Lexia repondait sur 1240 a 1242 (recette du 23/11, R-1).
# Le vehicule doit etre l'auteur du heurt, pas la chose abimee : « des tuiles abiment une voiture garee » (cp-06) et
# « heurte une voiture et raye la carrosserie » (cp-34) restent au Code civil. Sans moteur (velo, cp-04) : non plus.
# Articles de loi par identifiant : des milliers de lois ont un « article 1 » (api/retrieval/local.py).
LOIS = "lois"
_VTM = (r"\b(?P<vehicule>voitures?|automobiles?|autos|motos?|motocyclettes?|scooters?|camions?|camionnettes?"
        r"|poids lourds?|vehicules?|autocars?|autobus|bus|tracteurs?|quads?|cyclomoteurs?|mobylettes?"
        r"|voiturettes?|automobilistes?|motards?)\b")
# Heurt cause par le vehicule ; ni « raye » ni « abime », qui disent le dommage subi par une chose
_HEURT = (r"(?:\brenvers|\bpercut|\bfauch|\bheurt|\bbless|\becras|\baccroch|\bdeval|\btamponn|\bpercussion"
          r"|\btuee?s?\b|\broule sur|\brecule sur)")
# Question de droit penal (« quelle est sa responsabilite penale ? », ctl4-11) : l'indemnisation n'est pas posee
_PENAL = r"(?:penal|infraction|\bdelits?\b|homicide|\bpeines?\b|contravention)"
_ACCIDENT = re.compile(
    r"^(?![\s\S]*" + _PENAL + r")[\s\S]*?(?:"
    + _VTM + r"[^?]{0,150}?" + _HEURT
    + r"|" + _HEURT + r"\w* (?:par|contre) (?:une?|la|le|sa|son|leur) " + _VTM.replace("?P<vehicule>", "?P<vehicule2>")
    + r"|(?P<accident>accidents? de (?:la )?(?:circulation|route)|accidents? (?:de|en) (?:voiture|moto|scooter|camion)"
    r"|loi badinter|vehicules? terrestres? a moteur))")
# Article 1 (champ : accident de la circulation, vehicule terrestre a moteur implique), 3 (victime non conductrice,
# seule sa faute inexcusable cause exclusive lui est opposable), 2 (ni force majeure ni fait d'un tiers opposables)
LOI_1985 = ((LOIS, "LEGIARTI000006839396"), (LOIS, "LEGIARTI000006839422"), (LOIS, "LEGIARTI000006839413"))


NOTIONS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    # --- introduction au droit -------------------------------------------------
    (r"entree en vigueur d.{0,6}loi|publication des lois|lois? .{0,40}opposable", ((CC, "1"),)),
    (r"retroactiv", ((CC, "2"),)),
    (r"deni de justice|loi (?:est )?obscure|silence de la loi|insuffisance de la loi", ((CC, "4"),)),
    # article 4 (deni de justice) : le juge doit juger, fondement du pouvoir createur de la jurisprudence (question 25
    # du dossier enseignant, D122)
    (r"arrets? de reglement|lie par ses (?:propres )?decisions|precedents? judiciaires?|jurisprudence.{0,20}source",
     ((CC, "5"), (CC, "1355"), (CC, "4"))),
    (r"autorite de (?:la )?chose jugee", ((CC, "1355"),)),
    (r"ordre public|bonnes moeurs", ((CC, "6"), (CC, "1102"), (CC, "1162"))),
    (r"vie privee", ((CC, "9"),)),
    (r"droit des personnes|droits? de la personnalite", ((CC, "16"), (CC, "9"), (CC, "16-1"))),
    (r"presomption d.innocence", ((CC, "9-1"), (DDHC, "9"))),
    (r"corps humain", ((CC, "16"), (CC, "16-1"))),
    (r"\bmajeurs?\b|\bmajorite\b", ((CC, "414"),)),
    (r"droit de propriete|\bla propriete\b", ((CC, "544"), (DDHC, "17"))),
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
    (r"contreseing", ((CONST, "19"),)),
    (r"incompatib\w*.{0,40}(?:ministre|gouvernement|parlement)|(?:ministre|membres? du gouvernement).{0,40}(?:depute|senateur|parlementaire)",
     ((CONST, "23"),)),
    (r"composition du parlement|parlement (?:comprend|se compose)", ((CONST, "24"),)),
    (r"lois? organiques?", ((CONST, "46"),)),
    (r"(?:composition|membres) du conseil constitutionnel", ((CONST, "56"),)),
    (r"hierarchie des normes|autorite des traites|traites? (?:internationaux|et (?:les )?lois)", ((CONST, "55"),)),
    # --- droit des contrats ------------------------------------------------------
    (r"force obligatoire", ((CC, "1103"), (CC, "1193"))),
    (r"liberte contractuelle", ((CC, "1102"),)),
    (r"bonne foi.{0,40}contrat|contrat.{0,40}bonne foi", ((CC, "1104"),)),
    (r"pourparlers|negociations? precontractuel", ((CC, "1112"),)),
    (r"devoir (?:precontractuel )?d.information|obligation (?:precontractuelle )?d.information", ((CC, "1112-1"),)),
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
    # Reticence ou mensonge racontes sans le mot « dol » (cas pratique) : « en lui cachant que la voiture
    # avait ete accidentee », « le vendeur a menti », « sans lui dire »... pres d'une vente ou d'un contrat.
    # « vice cache » n'est pas vise : seules les formes verbales de « cacher » le sont.
    (_SILENCE + r".{0,80}" + _CONTRAT + "|" + _CONTRAT + r".{0,80}" + _SILENCE, ((CC, "1137"), (CC, "1112-1"))),
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
    (r"capacite (?:de|a) contracter|incapacite.{0,30}(?:mineur|contracter)|mineurs? non emancipes?", ((CC, "1145"), (CC, "1146"), (CC, "1148"))),
    (r"obligations? du (?:preneur|locataire)", ((CC, "1728"),)),
    (r"obligations? du bailleur|obligations? du loueur", ((CC, "1719"), (CC, "1720"))),
    # --- responsabilite et quasi-contrats ---------------------------------------
    (r"responsabilite (?:civile )?(?:pour faute|du fait personnel|delictuelle)|faute.{0,40}(?:dommage|responsab)", ((CC, "1240"), (CC, "1241"))),
    # fait des choses : la fiche ne disait pas que les accidents de la circulation en sont exclus (loi du 5 juillet
    # 1985, article 1er ; question 22 du dossier enseignant, D122)
    (r"fait des choses|gard(?:e|ien) de la chose", ((CC, "1242"), LOI_1985[0])),
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
    (r"legalite des delits|legalite criminelle|legalite penale|nullum crimen", ((CP, "111-3"), (CP, "111-4"), (DDHC, "8"))),
    (r"interpretation stricte", ((CP, "111-4"),)),
    (r"in mitius|loi penale (?:plus douce|dans le temps)|application de la loi penale dans le temps", ((CP, "112-1"),)),
    (r"\btentative\b", ((CP, "121-5"),)),
    (r"\bcomplic", ((CP, "121-7"), (CP, "121-6"))),
    (r"responsabilite penale des personnes morales|personnes? morales?.{0,30}penalement", ((CP, "121-2"),)),
    (r"homicide involontaire", ((CP, "221-6"), (CP, "121-3"))),
    (r"blessures? involontaires?", ((CP, "222-19"), (CP, "121-3"))),
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
    (r"heures? supplementaires?", ((CT, "L3121-28"), (CT, "L3121-36"))),
    (r"\bsmic\b|salaire minimum", ((CT, "L3231-2"),)),
    (r"comite social et economique|\bcse\b", ((CT, "L2311-2"),)),
    (r"\bgrev(?:e|iste)", ((CT, "L2511-1"),)),
    (r"preavis.{0,30}licenciement|licenciement.{0,30}preavis|indemnite de licenciement", ((CT, "L1234-1"),)),
    (r"rupture du contrat de travail", ((CT, "L1231-1"),)),
    # --- droit administratif (Code de justice administrative, CRPA) ---------------------------
    (r"exces de pouvoir|\brep\b|recours (?:en|pour) annulation|delai.{0,30}recours.{0,40}(?:decision|administrati)",
     ((CJA, "R421-1"),)),
    (r"refere.suspension", ((CJA, "L521-1"),)),
    (r"refere.liberte|liberte fondamentale.{0,40}refere|refere.{0,40}liberte fondamentale", ((CJA, "L521-2"),)),
    (r"refere.mesures? utiles|refere conservatoire", ((CJA, "L521-3"),)),
    (r"pouvoir d.injonction|injonction.{0,40}(?:administration|juge administratif)", ((CJA, "L911-1"),)),
    (r"silence (?:garde par |de )l.administration|silence vaut (?:acceptation|accord|rejet)|administration.{0,20}garde le silence",
     ((CRPA, "L231-1"),)),
    (r"motivation des (?:actes|decisions) administrati", ((CRPA, "L211-2"),)),
    (r"(?:retrait|abrogation).{0,40}(?:acte|decision)s? administrati|decisions? creatrices? de droits", ((CRPA, "L242-1"), (CRPA, "L243-1"))),
    (r"(?:acces|communication).{0,30}documents? administratifs?", ((CRPA, "L311-1"),)),
    # --- procedure civile (Code de procedure civile) --------------------------------------------
    (r"interet a agir", ((CPC, "31"),)),
    (r"action en justice|droit d.agir en justice", ((CPC, "30"), (CPC, "31"))),
    (r"\bassignation", ((CPC, "56"),)),
    (r"principe (?:du )?contradictoire|principe de la contradiction", ((CPC, "16"),)),
    (r"fins? de non.recevoir", ((CPC, "122"),)),
    # --- libertes fondamentales (DDHC 1789, Preambule de 1946, Code de la securite interieure) ---
    (r"egalite devant la loi|principe d.egalite", ((DDHC, "6"), (DDHC, "1"), (CONST, "1"))),
    (r"liberte d.expression|libre communication des pensees|liberte d.opinion", ((DDHC, "11"),)),
    (r"separation des pouvoirs|garantie des droits", ((DDHC, "16"),)),
    (r"necessite des peines|proportionnalite des peines", ((DDHC, "8"),)),
    (r"definition de la liberte|liberte consiste", ((DDHC, "4"),)),
    (r"consentement (?:a|de) l.impot", ((DDHC, "14"),)),
    (r"egalite devant (?:l.impot|les charges publiques)|contribution commune", ((DDHC, "13"),)),
    (r"preambule de (?:la constitution de )?1946|droits? (?:economiques et )?sociaux.{0,30}constitution|liberte syndicale|(?:droit de greve|greve).{0,40}(?:constitution|preambule)",
     ((P46, "PREAMBULE"),)),
    (r"(?:manifestations?|cortege|rassemblement).{0,40}(?:declaration|interdi)|declaration prealable", ((CSI, "L211-1"),)),
    (r"dissolution.{0,30}(?:association|groupement)", ((CSI, "L212-1"),)),
    (r"\bmicas\b|mesures? individuelles? de controle", ((CSI, "L228-1"),)),
    # --- droit fiscal (CGI, LPF) ---------------------------------------------------------------
    (r"droit de reprise|prescription.{0,20}fiscale|rectifier l.impot|(?:delai|combien de temps).{0,60}(?:administration fiscale|\bfisc\b)",
     ((LPF, "L169"),)),
    (r"impot sur le revenu", ((CGI, "1 A"), (CGI, "4 A"))),
    (r"quotient familial|parts? fiscales?", ((CGI, "194"), (CGI, "193"))),
    (r"impot sur les societes", ((CGI, "205"), (CGI, "206"))),
    (r"\btva\b|taxe sur la valeur ajoutee", ((CGI, "256"), (CGI, "256 A"), (CGI, "278"))),
    (r"verification de comptabilite|controle fiscal", ((LPF, "L13"), (LPF, "L10"))),
    (r"examen contradictoire de (?:la )?situation fiscale|\besfp\b", ((LPF, "L47"),)),
    (r"(?:procedure|proposition) de rectification|rectification contradictoire", ((LPF, "L55"), (LPF, "L57"))),
    (r"reclamation.{0,30}(?:impot|fiscal)|contentieux fiscal", ((LPF, "L190"),)),
    # --- finances publiques (Constitution, CJF) -------------------------------------------------
    (r"lois? de finances", ((CONST, "47"),)),
    (r"cour des comptes", ((CONST, "47-2"), (CJF, "L111-2"), (CJF, "L111-3"))),
    (r"chambres? regionales? des comptes", ((CJF, "L211-1"),)),
    # --- droit de la famille (Code civil, CASF) -------------------------------------------------
    (r"autorite parentale", ((CC, "371-1"),)),
    (r"\bdivorce", ((CC, "229"),)),
    # Divorce pour alteration definitive du lien conjugal : un an de separation (art. 238 depuis le 1er janvier 2021).
    # Dossier enseignant, question 15 (25/11) : sans 237 et 238 parmi les extraits, la reponse disait 14 mois
    # insuffisants d'apres une decision de l'epoque des deux ans (D133).
    (r"alteration definitive du lien conjugal|cessation de la communaute de vie"
     r"|divorc.{0,160}\b(?:vivent|vivant|vit|vivaient)\b.{0,20}separ|\b(?:vivent|vivant|vit|vivaient)\b.{0,20}separ.{0,160}divorc",
     ((CC, "238"), (CC, "237"))),
    (r"\bfiliation", ((CC, "310-1"),)),
    (r"obligation alimentaire|\baliments\b", ((CC, "205"),)),
    (r"pension alimentaire|contribution a l.entretien", ((CC, "371-2"), (CC, "373-2-2"))),
    (r"grands?.parents?|grand.(?:mere|pere)s?\b.{0,100}(?:petits?.enfants?|voir|visite|contact)"
     r"|(?:voir|visite|contact)\w*.{0,60}grand.(?:mere|pere)", ((CC, "371-4"),)),
    (r"aide sociale a l.enfance|\base\b", ((CASF, "L221-1"),)),
    (r"protection de l.enfance", ((CASF, "L112-3"),)),
    # --- droit des biens (Code civil, expropriation) --------------------------------------------
    # droits (fruits, 582), obligations (entretien, 605) et extinction (617) : la question 6 du dossier enseignant
    # n'avait que la definition et l'inventaire (D122)
    (r"\busufruit", ((CC, "578"), (CC, "582"), (CC, "605"), (CC, "617"))),
    (r"\bservitude", ((CC, "637"),)),
    (r"prescription acquisitive|usucapion", ((CC, "2258"), (CC, "2272"), (CC, "2261"))),
    (r"\bpossession", ((CC, "2255"), (CC, "2261"))),
    (r"\baccession", ((CC, "546"),)),
    (r"\bindivision", ((CC, "815"),)),
    (r"indemni\w*.{0,40}expropri|expropri\w*.{0,40}indemni", ((CEXP, "L321-1"), (CEXP, "L1"))),
    (r"\bexpropri|utilite publique", ((CEXP, "L1"), (CEXP, "L121-1"), (CEXP, "L321-1"))),
    # --- execution des peines (Code penitentiaire) ----------------------------------------------
    (r"service public penitentiaire|\bprisons?\b|\bdetenus?\b", ((CPEN, "L1"), (CPEN, "L2"))),
    # --- situations racontees (cas pratiques, D75) ------------------------------------------------
    # Faits decrits sans le nom de la notion. Apres les notions de cours, qui restent prioritaires ; une
    # suggestion hors des sources de la matiere choisie est ignoree par la recherche.
    # Responsabilite civile
    # Accident de la circulation d'abord : la loi de 1985 ecarte 1240 a 1242 (R-1). Trois articles, une place
    # reste pour le Code civil (le modele dit pourquoi il ne s'applique pas).
    (_ACCIDENT.pattern, LOI_1985),
    (_AGE + r".{0,80}" + _DOMMAGE, ((CC, "1242"), (CC, "1240"))),
    # Chose (sans moteur) et dommage sans age dit : « Leo brise la vitrine en jouant au ballon » ne recevait pas
    # l'article 1242, ni donc la garde de la chose (D119).
    (_CHOSE + r".{0,80}" + _DOMMAGE + r"|" + _DOMMAGE + r".{0,80}" + _CHOSE, ((CC, "1242"), (CC, "1240"))),
    (r"(?:salarie|employe|prepose|livreur|chauffeur|ouvrier|apprenti)\w*.{0,120}" + _DOMMAGE
     + r"|" + _DOMMAGE + r".{0,120}(?:son employeur|l.entreprise|la (?:societe|compagnie))", ((CC, "1242"),)),
    (r"(?:glisse|trebuch)\w* (?:sur|dans)\b.{0,80}(?:magasin|supermarche|escalier|flaque|chantier|piscine|sol)"
     r"|\b(?:pots?|objets?|panneaux?|echelles?|branches?)\b.{0,60}tomb|(?:fait|laisse|faisant|laissant) tomber",
     ((CC, "1242"), (CC, "1240"))),
    # « en voulant eviter un chien, un conducteur blesse un pieton » : l'animal n'est pas la cause du dommage
    (r"(?<!eviter un )(?<!eviter une )(?<!eviter le )(?<!eviter la )(?<!esquiver un )(?<!esquiver une )"
     r"\b(?:chiens?|chats?|chevaux|cheval|vaches?|taureaux?|moutons?|chevres?)\b.{0,80}"
     r"(?:mord|griff|bless|attaqu|pietin|renvers|echapp|devor)|\bmordu\b|\bmorsures?\b", ((CC, "1243"),)),
    (r"\b(?:tuiles?|toit|toiture|murs?|balcon|facade|cheminee|batiment|immeuble|gouttiere)\b.{0,80}"
     r"(?:tomb|effondr|ecroul|s.est detache)", ((CC, "1244"),)),
    (_DOMMAGE + r".{0,120}" + _REPARER + r"|" + _REPARER + r".{0,60}(?:degats|blessures?|prejudice)",
     ((CC, "1240"), (CC, "1241"))),
    # Contrats
    (r"menac\w*.{0,120}" + _CONTRAT + r"|" + _CONTRAT + r"\w*.{0,120}menac", ((CC, "1140"),)),
    (r"(?:croyant|pensant|croyait|pensait|persuade|presente\w* comme)\b.{0,120}" + _CONTRAT
     + r"|" + _CONTRAT + r"\w*.{0,120}(?:croyant|pensant|croyait|pensait|presente\w* comme)\b", ((CC, "1132"), (CC, "1133"))),
    (r"loyers?.{0,60}(?:impaye|ne (?:paie|paye|verse)|plus|retard)|(?:ne (?:paie|paye|verse) plus|impayes?).{0,60}loyer",
     ((CC, "1728"), (CC, "1224"), (CC, "1741"))),
    # exception d'inexecution : suspendre sa prestation parce que l'autre partie n'execute pas la sienne
    (_SUSPENDRE + r".{0,40}(?:en attendant|tant que|jusqu.a ce)|" + _MANQUE + r".{0,150}" + _SUSPENDRE
     + r"|" + _SUSPENDRE + r".{0,150}" + _MANQUE, ((CC, "1219"), (CC, "1220"))),
    # avant les travaux jamais faits : « la proprietaire ne fait rien malgre une fuite » releve du bailleur
    (r"(?:proprietaire|bailleur|bailleresse|loueur)\w*.{0,120}(?:repar|travaux|fuite|chauffage|insalubr|humid|ne fait rien)"
     r"|(?:locataire|\bloue|location|logement loue).{0,120}(?:ne (?:repare|fait)|refuse de repar|en panne|fuite|insalubr|humid)",
     ((CC, "1719"), (CC, "1720"))),
    (r"ne (?:livre|vient|fait|execute|termine|rembourse|honore)\w* (?:pas|jamais|plus|rien)"
     r"|n.(?:a|ont) (?:jamais|pas) (?:livre|fait|execute|termine|effectue|realise)|abandonn\w* (?:le )?chantier"
     r"|jamais (?:livre|venu|fait|realise)", ((CC, "1217"), (CC, "1231-1"), (CC, "1224"), (CC, "1221"))),
    (r"(?:acompte|avance|paye|payee|regle|verse|encaiss|commande)\w*.{0,120}(?:n.(?:a|ont|avait) (?:jamais|pas) \w+|annul\w*|abandonn)"
     r"|n.(?:a|ont|avait) jamais \w+.{0,120}(?:acompte|avance|paye|commande)", ((CC, "1217"), (CC, "1229"), (CC, "1231-1"))),
    # garantie des vices caches : un bien achete qui casse ou tombe en panne a cause d'un defaut anterieur
    (r"(?:achet|achat|vend|vendu|vente|livr|neuf|d.occasion)\w*.{0,150}(?:tombe\w* en panne|ne (?:fonctionne|marche|demarre|s.allume)\w* plus"
     r"|\bcass|\bcede|\bdefaut|fissure|\bvices?\b(?! du consentement)|termites?|merule|amiante|infiltr|moisi|rouill|\brong)"
     r"|defaut de fabrication|existait (?:deja|avant)|avant la vente",
     ((CC, "1641"), (CC, "1644"))),
    (_AGE + r".{0,100}(?:achet|achat|signe|souscri|contrat|abonnement|emprunt)", ((CC, "1146"), (CC, "1148"))),
    (r"(?:par erreur|deux fois|en trop|a tort|par meprise).{0,100}(?:pay|vers|vire|virement|credit|rembours|somme)"
     r"|(?:pay|vers|vire|virement|credit)\w*.{0,100}(?:par erreur|deux fois|en trop|a tort)", ((CC, "1302"), (CC, "1302-1"))),
    # Famille et biens
    (r"(?:ne (?:verse|paie|paye)|refuse de (?:payer|verser)|plus rien).{0,100}(?:enfants?|pension|entretien)",
     ((CC, "371-2"), (CC, "373-2-2"))),
    (r"(?:demenag|partir vivre|s.installer|changer de ville|residence|vivre (?:chez|avec)|vivra)\w*.{0,100}(?:\benfants?\b|\bfils\b|\bfille\b)"
     r"|(?:\benfants?\b|\bfils\b|\bfille\b).{0,100}(?:demenag|residence|vivra|vivre chez)", ((CC, "373-2"), (CC, "371-1"), (CC, "373-2-6"))),
    (r"(?:depuis|pendant|plus de) (?:\d+|dix|vingt|trente|quarante|cinquante) ans.{0,120}(?:terrain|maison|parcelle|champ|occup|cultiv)"
     r"|(?:terrain|parcelle|champ|maison).{0,120}(?:depuis|pendant) (?:\d+|dix|vingt|trente|quarante|cinquante) ans"
     r"|devenir proprietaire", ((CC, "2272"), (CC, "2261"))),
    (r"enclav|(?:aucun|pas d.|sans) acces.{0,40}(?:route|voie publique|chemin)", ((CC, "682"),)),
    (r"(?:branches?|racines?|arbres?|haie)\b.{0,80}(?:depass|avanc|empiet|deborde)", ((CC, "673"), (CC, "671"))),
    (r"(?:construi|bati|install|pose|empiet|depass|stock|depos|occup)\w*.{0,100}(?:sur|dans) (?:mon|son|le|leur|notre|un|une) "
     r"(?:terrain|jardin|propriete|parcelle|champ)"
     r"|(?:jardin|terrain|propriete|parcelle).{0,80}sans (?:\w+ ){0,3}(?:avis|accord|autorisation|permission)",
     ((CC, "544"), (CC, "545"))),
    # Penal
    (r"(?:frapp|repouss|riposte|se defend|coups?|neutralis)\w*.{0,120}(?:agress|attaqu|cambriol|voleur|arracher)"
     r"|(?:agress|attaqu|cambriol|voleur)\w*.{0,120}(?:frapp|repouss|riposte|se defend|coups? de poing|neutralis)",
     ((CP, "122-5"), (CP, "122-6"))),
    (r"(?:prend|pris|vole|derob|subtilis|empoch|glisse|emporte|s.empare)\w*.{0,80}"
     r"(?:portefeuille|sac|telephone|bijou|parfum|argent|objet|velo|marchandise)|sans payer|a l.etalage", ((CP, "311-1"),)),
    # bien de l'entreprise ou d'autrui emporte : vol, ou abus de confiance s'il avait ete remis
    (r"(?:emport|prend|pris|subtilis|derob|vole|empoch|repart\w*.{0,20}\bavec|\bpart\w*.{0,20}\bavec|emmen)\w*.{0,80}(?:de l.entreprise|de son employeur|du magasin|de la boutique"
     r"|qui ne lui appart|d.autrui)", ((CP, "311-1"), (CP, "314-1"))),
    (r"se (?:fait|faisant|faisait) passer pour|se present\w* comme|pretend\w* etre|en se disant|usurp\w*|faux (?:site|plombier|policier|agent|conseiller|profil|annonce|billets?)"
     r"|fausse (?:qualite|identite|annonce|facture)|arnaqu|manoeuvres? frauduleuses?", ((CP, "313-1"),)),
    (r"(?:utilise|detourn|depens|vire|empoch|puise)\w*.{0,100}(?:argent|fonds|caisse|sommes?).{0,100}"
     r"(?:confie|association|employeur|clients?)"
     r"|(?:garde\w* pour (?:lui|elle|soi|eux)|conserv\w*|devait (?:reverser|rendre|restituer|remettre)|ne (?:reverse|rend|restitue)\w* pas)"
     r".{0,100}(?:argent|fonds|sommes?|ventes|recettes|caisse|loyers|cotisations)"
     r"|(?:argent|fonds|sommes?|recettes).{0,100}(?:devait (?:reverser|rendre|restituer|remettre))", ((CP, "314-1"),)),
    (r"(?:prete|fourni|donne|aide|procure|conduit|guette|fait le guet)\w*.{0,120}(?:sachant|savait|connaissant).{0,120}"
     r"(?:cambriol|vol|crime|delit|infraction|agression|meurtre|braquage)", ((CP, "121-7"), (CP, "121-6"))),
    (r"(?:imprudence|inattention|maladresse|distrait|negligen|embardee|par accident|sans le vouloir|involontairement)\w*.{0,120}"
     r"(?:bless|\btue\b|mort|deced)|(?:bless|renvers|percut)\w*.{0,120}(?:penalement|pour imprudence)",
     ((CP, "222-19"), (CP, "121-3"))),
    # Travail
    (r"renvoy|mis\w* a la porte|congedi|licencie\w*.{0,80}(?:sans|parce|pour avoir|au motif|car\b|du jour au lendemain)",
     ((CT, "L1232-1"), (CT, "L1235-3"))),
    (r"(?:humili|brimad|denigr|insult|rabaiss|reproches? (?:injustifi|incessant|permanent))\w*.{0,120}"
     r"(?:chef|manager|employeur|superieur|collegue|travail|salari)"
     r"|(?:chef|manager|employeur|superieur|collegue)\w*.{0,120}(?:humili|brimad|denigr|insult|rabaiss)", ((CT, "L1152-1"),)),
    (r"heures? (?:de travail )?en plus|(?:travail|temps) en plus|au.dela de (?:35|trente-cinq) heures"
     r"|\b(?:3[6-9]|[4-6]\d) heures (?:par|chaque|toutes les) semaine", ((CT, "L3121-28"), (CT, "L3121-36"))),
    (r"(?:refus\w* d.(?:embaucher|recruter|engager)|licenci\w*|sanction\w*|ecart\w*|renvoy\w*).{0,80}"
     r"(?:parce qu|a cause d|en raison d|au motif)\w*.{0,60}(?:voile|religio|origine|couleur|\bsexe\b|enceinte|grossesse"
     r"|handicap|\bage\b|accent|syndica|orientation sexuelle|apparence|tatou|barbe|cheveux|nationalite)", ((CT, "L1132-1"),)),
    (r"\bavances\b|propositions? (?:sexuelles?|deplacees?)|gestes? deplaces?|remarques? (?:sexistes|sexuelles)", ((CT, "L1153-1"),)),
    (r"^(?=.*(?:mairie|\bmaire\b|prefe|administrati|ministre|arrete|commune|recteur|rectorat|universite))"
     r".*(?:sans (?:\w+ ){0,4}(?:explication|raison|motif|justification)|non motive|pas motive)",
     (("code_relations_public_administration", "L211-2"), (CJA, "R421-1"))),
    # Administratif : une decision publique et une demande d'urgence
    (r"^(?=.*(?:mairie|\bmaire\b|prefe|administrati|ministre|arrete|commune|recteur|universite))"
     r".*(?:en urgence|d.urgence|rapidement|\bvite\b|sans attendre|suspension)", ((CJA, "L521-2"), (CJA, "L521-1"))),
    # --- notions des maquettes de licence (D97, docs/plaquettes-licence.md) -----------------------------
    # Apres les situations racontees : un cas pratique garde ses articles de principe en premier.
    # Consommation, regimes matrimoniaux, successions et securite sociale servent les matieres existantes
    # (contrats et affaires, famille, droit social) : rares en licence, elles n'ont pas de matiere propre.
    # Procedure penale (Code de procedure penale, Code de la justice penale des mineurs)
    (r"article preliminaire|principes? directeurs? (?:de la |du )?(?:procedure|proces) penal|proces penal equitable",
     ((CPP, "préliminaire"),)),
    (r"mise en mouvement de l.action publique|mettre en mouvement l.action publique|exercice de l.action publique",
     ((CPP, "1"),)),
    (r"extinction de l.action publique|action publique s.eteint", ((CPP, "6"),)),
    (r"\baction civile\b|constitu\w* partie civile|\bpartie civile\b", ((CPP, "2"), (CPP, "85"))),
    (r"opportunite des poursuites|classement sans suite|classe\w* sans suite", ((CPP, "40-1"), (CPP, "40"))),
    (r"alternatives? aux poursuites|rappel a la loi|avertissement penal probatoire|mediation penale", ((CPP, "41-1"),)),
    (r"composition penale", ((CPP, "41-2"),)),
    (r"(?:role|pouvoirs?|missions?) du procureur de la republique", ((CPP, "41"), (CPP, "40"))),
    (r"police judiciaire|\bopj\b", ((CPP, "14"), (CPP, "16"))),
    (r"enquete de flagrance|enquete flagrante|(?:crimes?|delits?) flagrants?|flagrant delit", ((CPP, "53"),)),
    (r"enquete preliminaire", ((CPP, "75"),)),
    (r"perquisitions?|visites? domiciliaires?", ((CPP, "56"), (CPP, "76"))),
    (r"controles? d.identite", ((CPP, "78-2"),)),
    (r"droit (?:de se taire|au silence|de garder le silence)|avocat.{0,40}garde a vue|garde a vue.{0,40}avocat"
     r"|droits? (?:de la personne )?(?:gardee|placee) a vue|droits? en garde a vue", ((CPP, "63-1"), (CPP, "63-3-1"))),
    (r"juge d.instruction|instruction preparatoire|information judiciaire", ((CPP, "79"), (CPP, "81"))),
    (r"mise en examen|mis en examen", ((CPP, "80-1"),)),
    (r"temoin assiste", ((CPP, "113-1"),)),
    (r"\bmandats? (?:d.arret|d.amener|de comparution|de recherche|de depot)", ((CPP, "122"),)),
    (r"detention provisoire", ((CPP, "144"), (CPP, "137"), (CPP, "137-1"))),
    (r"juge des libertes et de la detention|\bjld\b", ((CPP, "137-1"),)),
    (r"controle judiciaire", ((CPP, "138"),)),
    (r"ecoutes? telephoniques?|interceptions? (?:de )?(?:correspondances|communications)", ((CPP, "100"),)),
    (r"geolocalisation", ((CPP, "230-32"),)),
    (r"chambre de l.instruction", ((CPP, "191"),)),
    (r"nullites?.{0,40}(?:penal|garde a vue|perquisition|instruction|enquete)"
     r"|(?:garde a vue|perquisition|enquete).{0,40}nullites?", ((CPP, "171"), (CPP, "802"))),
    (r"cour d.assises", ((CPP, "231"), (CPP, "380-1"))),
    (r"cour criminelle", ((CPP, "380-16"),)),
    (r"tribunal correctionnel", ((CPP, "381"),)),
    (r"tribunal de police", ((CPP, "521"),)),
    (r"comparution immediate", ((CPP, "395"),)),
    (r"comparution sur reconnaissance prealable|\bcrpc\b|plaider.coupable", ((CPP, "495-7"),)),
    (r"preuve.{0,30}(?:penal|infraction)|(?:penal|infraction).{0,30}preuve|intime conviction|loyaute de la preuve",
     ((CPP, "427"),)),
    (r"(?:non|ne) bis in idem|deux fois pour les memes faits|personne acquittee", ((CPP, "368"), (CPP, "6"))),
    (r"pourvoi.{0,30}(?:penal|chambre criminelle)|cassation en matiere penale", ((CPP, "567"),)),
    (r"application des peines|amenagements? de (?:la |sa )?peine|\bjap\b", ((CPP, "712-1"),)),
    (r"liberation conditionnelle", ((CPP, "729"),)),
    (r"casier judiciaire", ((CPP, "768"),)),
    (r"criminalite organisee|criminalite et (?:la )?delinquance organisees", ((CPP, "706-73"),)),
    (r"droits? des victimes?.{0,40}(?:penal|enquete|infraction|plainte)|victimes? d.infractions?", ((CPP, "10-2"),)),
    (r"justice penale des mineurs|responsabilite penale des mineurs|mineurs?.{0,40}(?:discernement|mesures? educatives?)",
     ((CJPM, "L11-1"), (CJPM, "Préliminaire"), (CJPM, "L11-3"))),
    # Droit administratif des biens (Code general de la propriete des personnes publiques)
    (r"domaine public (?:maritime|naturel)", ((CGPPP, "L2111-4"),)),
    (r"(?:definition|criteres?|composition|consistance|appartenance au|delimitation) du domaine public"
     r"|qu.est.ce que le domaine public|domanialite publique|accessoires? du domaine public", ((CGPPP, "L2111-1"), (CGPPP, "L2111-2"))),
    (r"domaine prive (?:des personnes publiques|de l.etat|de la commune|d.une personne publique)", ((CGPPP, "L2211-1"),)),
    (r"inalienab|imprescriptib", ((CGPPP, "L3111-1"),)),
    (r"declassement|desaffectation|sortie du domaine public", ((CGPPP, "L2141-1"),)),
    (r"redevances? (?:d.occupation|domaniale)|occupation.{0,40}gratuit", ((CGPPP, "L2125-1"),)),
    (r"occup\w* (?:privative )?(?:du |le )?domaine public|autorisations? d.occupation|titre d.occupation",
     ((CGPPP, "L2122-1"), (CGPPP, "L2122-2"), (CGPPP, "L2122-3"))),
    (r"biens des personnes publiques|propriete des personnes publiques|proprietes publiques", ((CGPPP, "L1"), (CGPPP, "L2111-1"))),
    # Contentieux administratif (Code de justice administrative, CRPA, CGCT)
    (r"decision implicite|silence.{0,40}(?:vaut|valant) (?:decision de )?rejet", ((CJA, "R421-2"),)),
    (r"recours (?:administratif )?(?:gracieux|hierarchique)", ((CRPA, "L411-2"),)),
    (r"astreinte.{0,40}(?:administration|personne publique|juge administratif)"
     r"|(?:administration|juge administratif).{0,40}astreinte", ((CJA, "L911-3"),)),
    (r"execution des (?:decisions|jugements).{0,30}administrati|inexecution d.un jugement.{0,40}administrati", ((CJA, "L911-4"),)),
    (r"competence.{0,40}tribunal administratif|tribunal administratif.{0,40}competen|role du tribunal administratif"
     r"|juge de droit commun du contentieux administratif", ((CJA, "L211-1"), (CJA, "R312-1"))),
    (r"cours? administratives? d.appel|appel.{0,40}(?:jugement|tribunal) administratif", ((CJA, "L211-2"), (CJA, "R811-1"))),
    (r"conseil d.etat.{0,40}(?:cassation|juge supreme|juridiction (?:administrative )?supreme)"
     r"|cassation.{0,40}(?:administrati|conseil d.etat)|admission des pourvois", ((CJA, "L111-1"), (CJA, "L821-1"), (CJA, "L822-1"))),
    (r"rapporteur public|commissaire du gouvernement", ((CJA, "L7"),)),
    (r"contradictoire.{0,40}(?:juge|juridiction|instruction|proces) administrati", ((CJA, "L5"),)),
    (r"refere.provision", ((CJA, "R541-1"),)),
    (r"refere.(?:expertise|instruction)", ((CJA, "R532-1"),)),
    (r"refere.constat", ((CJA, "R531-1"),)),
    (r"refere precontractuel", ((CJA, "L551-1"),)),
    (r"refere contractuel", ((CJA, "L551-13"),)),
    (r"(?:pouvoirs?|role|office) du juge des referes|procedures? d.urgence.{0,30}administrati", ((CJA, "L511-1"),)),
    (r"moyens? (?:souleves?|releves?) d.office|moyens? d.ordre public", ((CJA, "R611-7"),)),
    (r"tierce opposition.{0,60}administrati|administrati.{0,60}tierce opposition", ((CJA, "R832-1"),)),
    (r"(?:ministere|representation) (?:obligatoire )?(?:d.|par un )avocat.{0,40}administrati|dispense d.avocat", ((CJA, "R431-2"),)),
    (r"defere\w*.{0,30}prefet|prefet.{0,30}defere|controle de legalite.{0,40}(?:collectivites?|communes?|prefet)",
     ((CGCT, "L2131-6"),)),
    (r"(?:abroger|abrogation).{0,40}(?:reglement|acte reglementaire) illegal", ((CRPA, "L243-2"),)),
    # Droit de la consommation (Code de la consommation)
    (r"(?:definition|notion) (?:du |de )?(?:consommateur|non.professionnel)|qu.est.ce qu.un (?:consommateur|non.professionnel)"
     r"|qualite de consommateur", ((CCONSO, "liminaire"),)),
    (r"clauses? abusives?.{0,60}(?:consommat|professionnel)|(?:consommat|professionnel)\w*.{0,60}clauses? abusives?",
     ((CCONSO, "L212-1"),)),
    (r"(?:droit|delai) de retractation", ((CCONSO, "L221-18"),)),
    (r"contrats? (?:conclus? )?a distance|hors etablissement|demarchage a domicile", ((CCONSO, "L221-1"), (CCONSO, "L221-18"))),
    (r"demarchage telephonique|demarch\w* par telephone", ((CCONSO, "L223-1"),)),
    (r"pratiques? commerciales? trompeuses?|publicite (?:mensongere|trompeuse)", ((CCONSO, "L121-2"),)),
    (r"pratiques? commerciales? deloyales?", ((CCONSO, "L121-1"),)),
    (r"pratiques? commerciales? agressives?", ((CCONSO, "L121-6"),)),
    (r"abus de (?:la )?faiblesse", ((CCONSO, "L121-8"),)),
    (r"obligation (?:generale )?(?:precontractuelle )?d.information.{0,40}(?:consommateur|professionnel)"
     r"|(?:professionnel|consommateur).{0,40}obligation (?:generale )?(?:precontractuelle )?d.information", ((CCONSO, "L111-1"),)),
    (r"garantie (?:legale )?de conformite|defauts? de conformite", ((CCONSO, "L217-3"), (CCONSO, "L217-5"))),
    (r"garantie commerciale", ((CCONSO, "L217-21"),)),
    (r"refus de vente|ventes? (?:liees|subordonnees)", ((CCONSO, "L121-11"),)),
    (r"credit (?:a la consommation|renouvelable)|pret a la consommation", ((CCONSO, "L312-1"),)),
    (r"credit immobilier|pret immobilier", ((CCONSO, "L313-1"),)),
    (r"surendettement", ((CCONSO, "L711-1"),)),
    (r"obsolescence programmee", ((CCONSO, "L441-2"),)),
    # Droit des societes (Code civil, Code de commerce)
    (r"contrat de societe|definition de (?:la )?societe|defini\w*(?:-\w+)? (?:la |une )?societe|qu.est.ce qu.une societe|constitution d.une societe|affectio societatis",
     ((CC, "1832"), (CC, "1833"))),
    (r"interet social|objet social", ((CC, "1833"),)),
    (r"personnalite (?:morale|juridique).{0,40}societe|societes?.{0,40}personnalite (?:morale|juridique)"
     r"|immatriculation.{0,40}societe", ((CC, "1842"), (CCOM, "L210-6"))),
    (r"\bapports?\b.{0,30}(?:en nature|en numeraire|en industrie|associe)|apport en societe", ((CC, "1843-3"),)),
    (r"commissaires? aux apports", ((CCOM, "L225-8"), (CCOM, "L223-9"))),
    (r"societe a responsabilite limitee|\bsarl\b|\beurl\b", ((CCOM, "L223-1"),)),
    (r"societe anonyme", ((CCOM, "L225-1"),)),
    (r"societe par actions simplifiee|\bsasu?\b", ((CCOM, "L227-1"),)),
    (r"societe en nom collectif|\bsnc\b", ((CCOM, "L221-1"),)),
    (r"societes? civiles?", ((CC, "1845"), (CC, "1857"))),
    (r"societe en participation", ((CC, "1871"),)),
    (r"societe creee de fait|societe de fait", ((CC, "1873"),)),
    (r"abus de biens sociaux", ((CCOM, "L241-3"), (CCOM, "L242-6"))),
    (r"responsabilite (?:civile )?des (?:dirigeants|gerants|administrateurs)", ((CCOM, "L223-22"), (CCOM, "L225-251"))),
    (r"revo\w*.{0,30}(?:gerant|dirigeant|administrateur|directeur general)", ((CCOM, "L223-25"), (CC, "1851"))),
    (r"conventions? reglementees?", ((CCOM, "L225-38"), (CCOM, "L223-19"))),
    (r"cessions? de parts sociales|agrement.{0,30}(?:cession|associe)", ((CCOM, "L223-14"),)),
    (r"nullite (?:de la |d.une )?societe", ((CC, "1844-10"),)),
    (r"dissolution (?:de la |d.une )?societe|fin de la societe", ((CC, "1844-7"),)),
    (r"\bfiliales?\b|groupes? de societes", ((CCOM, "L233-1"),)),
    (r"droits? des associes|participer aux decisions collectives", ((CC, "1844"),)),
    # Regimes matrimoniaux (Code civil)
    (r"regime (?:matrimonial )?primaire|devoirs? (?:et droits )?(?:respectifs )?des epoux", ((CC, "212"), (CC, "214"), (CC, "215"), (CC, "220"))),
    (r"contribution aux charges du mariage", ((CC, "214"),)),
    (r"logement (?:de la )?famill|residence de la famille", ((CC, "215"),)),
    (r"dettes? menageres?|solidarite (?:des epoux|menagere)|entretien du menage", ((CC, "220"),)),
    (r"participation aux acquets", ((CC, "1569"),)),
    (r"communaute (?:reduite aux acquets|legale)|regime (?:matrimonial )?legal|regime de (?:la )?communaute", ((CC, "1400"), (CC, "1401"))),
    (r"communaute universelle", ((CC, "1526"),)),
    (r"biens propres", ((CC, "1405"), (CC, "1404"))),
    (r"biens communs|presomption de communaute", ((CC, "1401"), (CC, "1402"))),
    (r"gestion (?:concurrente|des biens communs)|pouvoirs? des epoux", ((CC, "1421"), (CC, "1424"))),
    (r"cogestion", ((CC, "1424"),)),
    (r"\brecompenses?\b", ((CC, "1433"), (CC, "1437"))),
    (r"separation de biens", ((CC, "1536"),)),
    (r"(?:changement|changer|modifier|modification) (?:de |du |leur |le )?regime matrimonial", ((CC, "1397"),)),
    (r"contrat de mariage|conventions? matrimoniales?", ((CC, "1387"), (CC, "1394"))),
    # Successions et liberalites (Code civil)
    (r"ouverture de (?:la )?succession|successions? s.ouvr", ((CC, "720"),)),
    (r"indign\w* (?:de |a )?succeder|indignite successorale", ((CC, "726"), (CC, "727"))),
    (r"(?:conditions?|capacite|aptitude) (?:pour |a )succeder|pour succeder", ((CC, "725"),)),
    (r"saisine (?:des )?heritiers|heritiers? (?:sont )?saisis", ((CC, "724"),)),
    (r"pactes? sur (?:une )?succession future|succession non (?:encore )?ouverte", ((CC, "722"),)),
    (r"ordres? (?:des )?heritiers|qui herite|devolution (?:legale|de la succession)|heritiers? (?:legaux|ab intestat)",
     ((CC, "734"), (CC, "721"))),
    (r"representation successorale|par representation", ((CC, "751"),)),
    (r"conjoint survivant|droits? (?:successoraux )?du conjoint", ((CC, "756"), (CC, "757"))),
    (r"accept\w* (?:une |la )?succession|renon\w* a (?:une |la )?succession|a concurrence de l.actif net", ((CC, "768"),)),
    (r"reserve hereditaire|heritiers? reservataires?|quotite disponible", ((CC, "912"), (CC, "913"))),
    (r"reduction des liberalites|action en reduction|liberalites? (?:excessives?|reductibles?)", ((CC, "920"),)),
    (r"rapport (?:des donations|des liberalites|successoral|a (?:la )?succession)", ((CC, "843"),)),
    (r"partage (?:de la |d.une )?succession|partage successoral", ((CC, "816"), (CC, "815"))),
    (r"donation.partage", ((CC, "1075"),)),
    (r"\bliberalites?\b", ((CC, "893"),)),
    (r"donations? entre vifs|\bdonations?\b.{0,30}(?:forme|notaire|irrevocab)", ((CC, "894"), (CC, "931"))),
    (r"testament olographe", ((CC, "970"),)),
    (r"testament (?:authentique|par acte public)", ((CC, "971"),)),
    (r"legs universel", ((CC, "1003"),)),
    (r"legs a titre universel", ((CC, "1010"),)),
    (r"legs (?:a titre )?particulier", ((CC, "1014"),)),
    (r"\btestaments?\b", ((CC, "969"), (CC, "967"))),
    # Droit de la securite sociale (Code de la securite sociale)
    (r"principes? de la securite sociale|securite sociale.{0,40}(?:solidarite|fondee|objet|organisation)", ((CSS, "L111-1"),)),
    (r"protection universelle maladie|\bpuma\b|prise en charge des frais de sante", ((CSS, "L160-1"), (CSS, "L111-2-1"))),
    (r"affili\w*.{0,30}regime general|regime general.{0,30}(?:securite sociale|affili)", ((CSS, "L311-2"),)),
    (r"cotisations? (?:de securite )?socia|assiette des cotisations", ((CSS, "L242-1"),)),
    (r"\burssaf\b|recouvrement des cotisations", ((CSS, "L213-1"),)),
    (r"indemnites? journalieres?", ((CSS, "L321-1"), (CSS, "L323-1"))),
    (r"pension d.invalidite|assurance invalidite", ((CSS, "L341-1"),)),
    (r"assurance vieillesse|pension de retraite", ((CSS, "L351-1"),)),
    (r"accidents? de trajet", ((CSS, "L411-2"),)),
    (r"accidents? du travail", ((CSS, "L411-1"), (CSS, "L451-1"))),
    (r"maladies? professionnelles?", ((CSS, "L461-1"),)),
    (r"faute inexcusable", ((CSS, "L452-1"),)),
    (r"rente.{0,40}(?:accident|incapacite)|incapacite permanente", ((CSS, "L434-2"),)),
    (r"prestations? familiales?|allocations? familiales?", ((CSS, "L511-1"),)),
    (r"contentieux de la securite sociale|pole social", ((CSS, "L142-1"),)),
    # --- droit de l'Union europeenne (TUE, TFUE, Charte des droits fondamentaux ; D72, D98) -------------
    (r"renvoi prejudiciel|question prejudicielle.{0,40}(?:cour de justice|cjue|union)", ((TFUE, "267"),)),
    (r"abus de position dominante", ((TFUE, "102"),)),
    (r"\bententes?\b.{0,60}(?:concurrence|entreprises)|pratiques? concertees?", ((TFUE, "101"),)),
    (r"aides? d.etat", ((TFUE, "107"), (TFUE, "108"))),
    (r"libre circulation des marchandises|restrictions? quantitatives?|mesures? d.effet equivalent",
     ((TFUE, "34"), (TFUE, "36"))),
    (r"libre circulation des travailleurs|(?:ressortissants?|citoyens?) (?:d.un (?:autre )?etat membre|europeens?|de l.union)"
     r".{0,80}(?:travaill|emploi|embauch)|\b(?:portugais|espagnols?|italiens?|allemands?|belges?|polonais|roumains?)\b"
     r".{0,60}(?:travailler|emploi|embauch).{0,60}(?:en france|meme(?:s)? conditions)", ((TFUE, "45"),)),
    (r"liberte d.etablissement", ((TFUE, "49"),)),
    (r"libre prestation (?:de|des) services", ((TFUE, "56"),)),
    (r"libre circulation des capitaux", ((TFUE, "63"),)),
    (r"recours en manquement|manquement d.un etat membre", ((TFUE, "258"), (TFUE, "260"))),
    (r"annul\w* (?:d.)?(?:un |les? |des )?actes? de l.union|recours en annulation.{0,60}(?:union|europe|cour de justice|tribunal de l.union)"
     r"|(?:union|europe|cour de justice).{0,60}recours en annulation", ((TFUE, "263"),)),
    (r"recours en carence", ((TFUE, "265"),)),
    (r"citoyennete (?:europeenne|de l.union)", ((TFUE, "20"), (TUE, "9"))),
    (r"principe de subsidiarite|principe d.attribution", ((TUE, "5"),)),
    (r"valeurs de l.union", ((TUE, "2"),)),
    (r"retrait de l.union|\bbrexit\b|quitter l.union", ((TUE, "50"),)),
    (r"charte des droits fondamentaux", ((TUE, "6"),)),
    (r"actes? (?:juridiques )?de l.union|\breglements?\b.{0,30}\bdirectives?\b|effet des (?:reglements|directives)",
     ((TFUE, "288"),)),
    (r"procedure legislative (?:ordinaire|de l.union)", ((TFUE, "294"),)),
    (r"competences? (?:exclusives?|partagees?) de l.union|competences de l.union", ((TFUE, "3"), (TFUE, "4"))),
    (r"commission europeenne", ((TUE, "17"),)),
    (r"parlement europeen", ((TUE, "14"),)),
    (r"conseil europeen", ((TUE, "15"),)),
    (r"conseil de l.union", ((TUE, "16"),)),
    (r"cour de justice de l.union|\bcjue\b", ((TUE, "19"),)),
    (r"discrimination.{0,30}nationalite|nationalite.{0,30}discrimination", ((TFUE, "18"),)),
    (r"responsabilite (?:extracontractuelle )?de l.union", ((TFUE, "340"),)),
    (r"primaute du droit (?:de l.union|europeen|communautaire)|participation de la france a l.union", ((CONST, "88-1"),)),
    (r"vie privee.{0,60}(?:charte|union europeenne)", ((CDF, "7"),)),
    # --- droit international (sources francaises : Constitution, Code civil ; D98) ---------------------
    (r"ratifi\w* (?:des |un |les )?traites?|negocia\w* (?:des |les )?traites?|traites? (?:ratifies?|negocies?)",
     ((CONST, "52"), (CONST, "53"))),
    (r"traites?.{0,40}contraires? a la constitution|controle de constitutionnalite des (?:traites|engagements internationaux)",
     ((CONST, "54"),)),
    (r"conflits? de lois|lois? de police|statut personnel|loi applicable.{0,40}(?:etrang|international)", ((CC, "3"),)),
    (r"competence (?:internationale|des (?:juridictions|tribunaux) francais)|privilege de juridiction|articles? 14 et 15",
     ((CC, "14"), (CC, "15"))),
    (r"loi applicable au divorce|divorce.{0,40}(?:etranger|international)", ((CC, "309"),)),
    (r"loi applicable a la filiation|filiation.{0,40}(?:etranger|international)", ((CC, "311-14"),)),
    (r"loi applicable au mariage|mariage.{0,40}(?:etranger|international)|epoux de nationalites? differentes?",
     ((CC, "202-1"),)),
    (r"adoption internationale|adoption.{0,40}(?:etranger|loi applicable)", ((CC, "370-3"),)),
    # Conditions de fond du mariage, hors questions internationales (ti-06 garde 202-1 seul). Sans l'article 143, la
    # reponse donnait la difference de sexe pour condition, abandonnee par la loi du 17 mai 2013 (dossier enseignant,
    # question 5 ; D122).
    (r"^(?![\s\S]*(?:loi applicable|nationalit|etranger|international))[\s\S]*?(?:"
     r"conditions? (?:de fond |de validite |requises? )?(?:du|au|pour (?:le|se)|d.un) mari|empechements? (?:a|au) mari"
     r"|qualites? et conditions.{0,30}mari|mariage pour tous|(?:meme sexe|homosexu|deux (?:hommes|femmes))\w*.{0,60}mari"
     r"|mari\w*.{0,60}(?:meme sexe|homosexu)|(?:conditions?|faut-il).{0,40}se marier)",
     ((CC, "143"), (CC, "146"), (CC, "144"), (CC, "147"))),
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
# Articles 1100 a 1100-2 (sources des obligations) : remontes par le mot « source » pour un sujet sur les sources du
# droit, ils ont ete pris pour une liste des sources du droit (question 25 du dossier enseignant, D122). Ecartes quand
# la question ne parle ni d'obligation ni d'acte ou de fait juridique. Le titre « Des sources d'obligations » couvre
# tout le droit des contrats et de la responsabilite : le filtre vise ces trois numeros seulement.
SOURCES_DES_OBLIGATIONS = ("1100", "1100-1", "1100-2")
_OBLIGATIONS = re.compile(r"obligation|actes? juridiques?|faits? juridiques?|contrat|engagement|quasi|responsabilit")


def chose_en_cause(question: str) -> str | None:
    """Chose nommee dans des faits ou un dommage est cause (« casse la vitre avec son ballon »), ou None."""
    q = normaliser(question)
    m = _CHOSES.search(q)
    return m.group("chose") if m and re.search(_DOMMAGE, q) else None


def vehicule_en_cause(question: str) -> str | None:
    """Vehicule terrestre a moteur auteur du dommage (« la voiture devale la pente et renverse une pietonne »),
    ou accident de la circulation nomme ; None sinon (R-1)."""
    m = _ACCIDENT.search(normaliser(question))
    if m is None:
        return None
    return m.group("vehicule") or m.group("vehicule2") or "accident de la circulation"


def hors_matiere(passage: dict, question: str) -> bool:
    """Article du Code civil d'une matiere speciale dont la question ne parle pas."""
    if passage.get("source_id") != CC:
        return False
    plan = " ".join((passage.get("meta") or {}).get("plan") or [])
    q = normaliser(question)
    if passage.get("numero") in SOURCES_DES_OBLIGATIONS and not _OBLIGATIONS.search(q):
        return True
    return any(titre in plan and not mots.search(q) for titre, mots in MATIERES_SPECIALES)


def normaliser(question: str) -> str:
    return sans_accents(question.lower().replace("’", "'"))


def suggestions(question: str, maximum: int = MAX_LEXIQUE,
                sources: tuple[str, ...] | None = None) -> list[tuple[str, str]]:
    """Articles de principe des notions reconnues dans la question, dans l'ordre du lexique.
    `sources` : celles de la matiere choisie ; un article d'une autre source ne prend pas de place (D97)."""
    q = normaliser(question)
    out: list[tuple[str, str]] = []
    for motif, arts in _COMPILES:
        if motif.search(q):
            for a in arts:
                if a not in out and (sources is None or a[0] in sources):
                    out.append(a)
        if len(out) >= maximum:
            break
    return out[:maximum]
