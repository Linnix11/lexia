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
            r"|\bray(?:e|er|ant)\b|\bfractur|\bheurt|\bmord|\bgriff|\bpietin)")
_REPARER = r"(?:repar|indemni|dedommag|dommages|\bpayer\b|rembours|responsable|poursuivre|se retourner)"
_SUSPENDRE = (r"(?:refuser?|cesser?|suspendre|arreter|retenir) (?:de )?(?:payer|livrer|fournir|travailler|executer"
              r"|la fourniture|le paiement|sa prestation)")
_MANQUE = (r"(?:ne (?:livre|paie|paye|fournit|execute)\w* (?:pas|plus)|pas (?:livre|paye)|impaye"
           r"|cesse de (?:payer|livrer|fournir))")
_AGE = (r"(?:\benfants?\b|\bfils\b|\bfille\b|\bmineure?s?\b|adolescent|\b(?:[2-9]|1[0-7]) ans\b"
        r"|\b(?:deux|trois|quatre|cinq|six|sept|huit|neuf|dix|onze|douze|treize|quatorze|quinze|seize|dix-sept) ans\b)")

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
    (r"legalite des delits|legalite criminelle|legalite penale|nullum crimen", ((CP, "111-3"), (CP, "111-4"), (DDHC, "8"))),
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
    (r"\bfiliation", ((CC, "310-1"),)),
    (r"obligation alimentaire|\baliments\b", ((CC, "205"),)),
    (r"pension alimentaire|contribution a l.entretien", ((CC, "371-2"), (CC, "373-2-2"))),
    (r"aide sociale a l.enfance|\base\b", ((CASF, "L221-1"),)),
    (r"protection de l.enfance", ((CASF, "L112-3"),)),
    # --- droit des biens (Code civil, expropriation) --------------------------------------------
    (r"\busufruit", ((CC, "578"),)),
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
    (_AGE + r".{0,80}" + _DOMMAGE, ((CC, "1242"), (CC, "1240"))),
    (r"(?:salarie|employe|prepose|livreur|chauffeur|ouvrier|apprenti)\w*.{0,120}" + _DOMMAGE
     + r"|" + _DOMMAGE + r".{0,120}(?:son employeur|l.entreprise|la (?:societe|compagnie))", ((CC, "1242"),)),
    (r"(?:glisse|trebuch)\w* (?:sur|dans)\b.{0,80}(?:magasin|supermarche|escalier|flaque|chantier|piscine|sol)"
     r"|\b(?:pots?|objets?|panneaux?|echelles?|branches?)\b.{0,60}tomb", ((CC, "1242"),)),
    (r"\b(?:chiens?|chats?|chevaux|cheval|vaches?|taureaux?|moutons?|chevres?)\b.{0,80}"
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
    (r"ne (?:livre|vient|fait|execute|termine|rembourse|honore)\w* (?:pas|jamais|plus|rien)"
     r"|n.(?:a|ont) (?:jamais|pas) (?:livre|fait|execute|termine|effectue|realise)|abandonn\w* (?:le )?chantier"
     r"|jamais (?:livre|venu|fait|realise)", ((CC, "1217"), (CC, "1231-1"), (CC, "1224"), (CC, "1221"))),
    (_AGE + r".{0,100}(?:achet|achat|signe|souscri|contrat|abonnement|emprunt)", ((CC, "1146"), (CC, "1148"))),
    (r"(?:par erreur|deux fois|en trop|a tort|par meprise).{0,100}(?:pay|vers|vire|virement|credit|rembours|somme)"
     r"|(?:pay|vers|vire|virement|credit)\w*.{0,100}(?:par erreur|deux fois|en trop|a tort)", ((CC, "1302"), (CC, "1302-1"))),
    # Famille et biens
    (r"(?:ne (?:verse|paie|paye)|refuse de (?:payer|verser)|plus rien).{0,100}(?:enfants?|pension|entretien)",
     ((CC, "371-2"), (CC, "373-2-2"))),
    (r"(?:depuis|pendant|plus de) (?:\d+|dix|vingt|trente|quarante|cinquante) ans.{0,120}(?:terrain|maison|parcelle|champ|occup|cultiv)"
     r"|(?:terrain|parcelle|champ|maison).{0,120}(?:depuis|pendant) (?:\d+|dix|vingt|trente|quarante|cinquante) ans"
     r"|devenir proprietaire", ((CC, "2272"), (CC, "2261"))),
    (r"enclav|(?:aucun|pas d.|sans) acces.{0,40}(?:route|voie publique|chemin)", ((CC, "682"),)),
    (r"(?:branches?|racines?|arbres?|haie)\b.{0,80}(?:depass|avanc|empiet|deborde)", ((CC, "673"), (CC, "671"))),
    (r"(?:construi|bati|install|pose|empiet|depass)\w*.{0,100}sur (?:mon|son|le|leur|notre) (?:terrain|jardin|propriete|parcelle)"
     r"|(?:dans|sur) (?:mon|son|notre) (?:jardin|terrain).{0,80}sans (?:mon|son|leur|notre) (?:avis|accord|autorisation)",
     ((CC, "544"), (CC, "545"))),
    # Penal
    (r"(?:frapp|repouss|riposte|se defend|coups?|neutralis)\w*.{0,120}(?:agress|attaqu|cambriol|voleur|arracher)"
     r"|(?:agress|attaqu|cambriol|voleur)\w*.{0,120}(?:frapp|repouss|riposte|se defend|coups? de poing|neutralis)",
     ((CP, "122-5"), (CP, "122-6"))),
    (r"(?:prend|pris|vole|derob|subtilis|empoch|glisse|emporte|s.empare)\w*.{0,80}"
     r"(?:portefeuille|sac|telephone|bijou|parfum|argent|objet|velo|marchandise)|sans payer|a l.etalage", ((CP, "311-1"),)),
    (r"se (?:fait|faisant|faisait) passer pour|faux (?:site|plombier|policier|agent|conseiller|profil|annonce|billets?)"
     r"|fausse (?:qualite|identite|annonce|facture)|arnaqu|manoeuvres? frauduleuses?", ((CP, "313-1"),)),
    (r"(?:utilise|detourn|depens|vire|empoch|puise)\w*.{0,100}(?:argent|fonds|caisse|sommes?).{0,100}"
     r"(?:confie|association|employeur|clients?)", ((CP, "314-1"),)),
    (r"(?:prete|fourni|donne|aide|procure|conduit|guette|fait le guet)\w*.{0,120}(?:sachant|savait|connaissant).{0,120}"
     r"(?:cambriol|vol|crime|delit|infraction|agression|meurtre|braquage)", ((CP, "121-7"), (CP, "121-6"))),
    # Travail
    (r"renvoy|mis\w* a la porte|congedi|licencie\w*.{0,80}(?:sans|parce|pour avoir|au motif|car\b|du jour au lendemain)",
     ((CT, "L1232-1"), (CT, "L1235-3"))),
    (r"(?:humili|brimad|denigr|insult|rabaiss|reproches? (?:injustifi|incessant|permanent))\w*.{0,120}"
     r"(?:chef|manager|employeur|superieur|collegue|travail|salari)"
     r"|(?:chef|manager|employeur|superieur|collegue)\w*.{0,120}(?:humili|brimad|denigr|insult|rabaiss)", ((CT, "L1152-1"),)),
    (r"\bavances\b|propositions? (?:sexuelles?|deplacees?)|gestes? deplaces?|remarques? (?:sexistes|sexuelles)", ((CT, "L1153-1"),)),
    # Administratif : une decision publique et une demande d'urgence
    (r"^(?=.*(?:mairie|\bmaire\b|prefe|administrati|ministre|arrete|commune|recteur|universite))"
     r".*(?:en urgence|d.urgence|rapidement|au plus vite|suspension)", ((CJA, "L521-2"), (CJA, "L521-1"))),
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
