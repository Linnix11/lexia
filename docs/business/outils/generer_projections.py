"""Genere docs/business/projections.xlsx (modele financier de Lexia sur 36 mois, trois scenarios).

Toutes les sorties sont des formules ; les seules valeurs saisies sont dans la feuille Hypotheses
(texte bleu). Lancer : python3 docs/business/outils/generer_projections.py, puis
docs/business/outils/enregistrer_excel.sh pour ecrire les valeurs en cache (audit du 23/11/2026, F8).
"""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName

SORTIE = Path(__file__).resolve().parent.parent / "projections.xlsx"
LU = "lu le 23/11/2026"

# Styles -------------------------------------------------------------------------------------
POLICE = "Arial"
F_NORMAL = Font(name=POLICE, size=10)
F_GRAS = Font(name=POLICE, size=10, bold=True)
F_TITRE = Font(name=POLICE, size=14, bold=True)
F_SOUS = Font(name=POLICE, size=11, bold=True, color="FFFFFF")
F_SAISIE = Font(name=POLICE, size=10, color="0000FF")
F_LIEN = Font(name=POLICE, size=10, color="008000")
F_NOTE = Font(name=POLICE, size=9, italic=True, color="555555")
FOND_TETE = PatternFill("solid", fgColor="2F5D4A")
FOND_SECTION = PatternFill("solid", fgColor="E3EDE7")
FOND_CLE = PatternFill("solid", fgColor="FFFF00")
FOND_NONSOURCE = PatternFill("solid", fgColor="FCE4D6")
BORD = Border(bottom=Side(style="thin", color="BBBBBB"))

EUR = '#,##0" €";(#,##0" €");"-"'
EUR2 = '#,##0.00" €";(#,##0.00" €");"-"'
EUR4 = '0.0000" €";(0.0000" €");"-"'
USD = '#,##0.00" $";(#,##0.00" $");"-"'
NB = '#,##0;(#,##0);"-"'
NB1 = '#,##0.0;(#,##0.0);"-"'
PCT = '0.0%;(0.0%);"-"'
DATE = 'mmm yyyy'

SCENARIOS = [("Prudent", "C"), ("Central", "D"), ("Ambitieux", "E")]
NB_MOIS = 36

# Hypotheses globales (meme valeur pour les trois scenarios) ----------------------------------
# (cle, libelle, unite, valeur, format, source, sourcee)
GLOBALES = [
    ("__", "Calendrier", None, None, None, None, None),
    ("annee_debut", "Annee du premier mois du modele", "annee", 2027, "0", "Choix de planification : premier mois = janvier 2027 (prerequis leves en decembre 2026)", False),
    ("mois_debut", "Mois du premier mois du modele", "1 a 12", 1, "0", "Choix de planification", False),
    ("__", "Prix des formules (api/plans.py, en ligne sur /api/formules le 23/11/2026)", None, None, None, None, None),
    ("prix_etudiant", "Prix Etudiant, toutes taxes comprises", "€ / mois", 4.99, EUR2, "api/plans.py ; site en ligne, page Tarifs, lu le 23/11/2026", True),
    ("prix_intensif", "Prix Intensif, toutes taxes comprises", "€ / mois", 9.99, EUR2, "api/plans.py ; site en ligne, page Tarifs, lu le 23/11/2026", True),
    ("__", "Cout du modele par question", None, None, None, None, None),
    ("usd_par_eur", "Taux de change : dollars pour 1 euro", "$ / €", 1.0968, "0.0000", "Banque de France, parites quotidiennes du 18/11/2026 (https://www.banque-france.fr/fr/statistiques/taux-et-cours/taux-de-change-parites-quotidiennes-2026-11-18), via recherche, " + LU, True),
    ("gem_in", "Gemini 3.5 Flash-Lite, jetons d'entree", "$ / million", 0.30, USD, "https://aistudio.google.com/docs/pricing (niveau payant), " + LU, True),
    ("gem_out", "Gemini 3.5 Flash-Lite, jetons de sortie (reflexion comprise)", "$ / million", 2.50, USD, "https://aistudio.google.com/docs/pricing, " + LU, True),
    ("sec_in", "Gemini 3.8 Flash (secours), entree, a partir du 01/01/2027", "$ / million", 1.50, USD, "https://aistudio.google.com/docs/pricing : 0,75 $ jusqu'au 31/12/2026 puis 1,50 $, " + LU, True),
    ("sec_out", "Gemini 3.8 Flash (secours), sortie, a partir du 01/01/2027", "$ / million", 7.50, USD, "https://aistudio.google.com/docs/pricing : 3,75 $ jusqu'au 31/12/2026 puis 7,50 $, " + LU, True),
    ("groq_in", "Groq qwen/qwen3.8-27b (secours), entree", "$ / million", 0.80, USD, "https://console.groq.com/docs/models, " + LU, True),
    ("groq_out", "Groq qwen/qwen3.8-27b (secours), sortie", "$ / million", 4.00, USD, "https://console.groq.com/docs/models, " + LU, True),
    ("tok_gen_in", "Jetons d'entree par reponse (moyenne)", "jetons", 2036, NB, "logs/modele.jsonl du Mac, 12 appels du 13 au 17/11/2026 : essais, pas de trafic reel", True),
    ("tok_gen_out", "Jetons de sortie par reponse (moyenne)", "jetons", 538, NB, "logs/modele.jsonl, memes 12 appels (reflexion : 0)", True),
    ("tok_ref_in", "Jetons d'entree par reformulation", "jetons", 136, NB, "logs/modele.jsonl, 8 appels", True),
    ("tok_ref_out", "Jetons de sortie par reformulation", "jetons", 60, NB, "logs/modele.jsonl, 8 appels", True),
    ("taux_reform", "Reformulations par question", "ratio", 0.74, "0.00", "D88 : 82 questions sur 111 reformulees en ligne", True),
    ("part_secours", "Part des questions servies par Gemini 3.8 Flash", "%", 0.05, PCT, "Hypothese non sourcee : aucune mesure au niveau payant", False),
    ("part_groq", "Part des questions servies par Groq (payant)", "%", 0.05, PCT, "Hypothese non sourcee : D88 mesure 15 sur 111 au niveau gratuit de Gemini (saturation), a remesurer au niveau payant", False),
    ("annexes", "Appels annexes (questionnaires, resumes vocaux, cartes mentales), en equivalent questions", "ratio", 0.25, "0.00", "Hypothese non sourcee", False),
    ("cout_q_usd", "Cout moyen d'une question (calcule)", "$", None, '0.00000" $"', "Formule : voir la cellule", True),
    ("cout_q_eur", "Cout moyen d'une question (calcule)", "€", None, '0.00000" €"', "Formule : cout en dollars / taux de change", True),
    ("__", "Paiement (Stripe Checkout, paiement unique de 1 a 12 mois, D86)", None, None, None, None, None),
    ("stripe_pct", "Stripe, cartes standard de l'EEE, part variable", "%", 0.015, PCT, "https://stripe.com/fr/pricing, " + LU, True),
    ("stripe_fixe", "Stripe, part fixe par paiement", "€", 0.25, EUR2, "https://stripe.com/fr/pricing, " + LU, True),
    ("duree_achat", "Duree moyenne achetee par paiement", "mois", 2, "0.0", "Hypothese non sourcee : achats de 1 a 12 mois possibles, aucune vente a ce jour", False),
    ("__", "Charges fixes et ponctuelles (prix publics ; sous franchise de TVA, la TVA sur achats n'est pas recuperable)", None, None, None, None, None),
    ("vps", "Serveur VPS Hostinger KVM 2 (2 processeurs, 8 Go), prix de renouvellement", "€ / mois", 14.99, EUR2, "https://www.hostinger.com/fr/vps-hosting : promotion 7,79 €/mois sur 24 mois, renouvellement 14,99 €/mois, " + LU + " ; contrat actuel de l'editeur non lu : on retient le renouvellement", True),
    ("domaine", "Nom de domaine .cloud chez Hostinger, renouvellement", "€ / an", 24.99, EUR2, "https://www.hostinger.com/fr/domaines, " + LU, True),
    ("cloudflare", "Cloudflare, plan Free", "€ / mois", 0, EUR2, "https://www.cloudflare.com/plans/network-cdn.md (Free : 0 $), " + LU, True),
    ("resend_seuil", "Resend gratuit : e-mails par mois", "e-mails", 3000, NB, "https://resend.com/pricing (100 par jour, 3 000 par mois), " + LU, True),
    ("resend_jour", "Resend gratuit : e-mails par jour", "e-mails", 100, NB, "https://resend.com/pricing : « The Free plan is limited to 100 emails per day » ; Pro : pas de limite quotidienne, " + LU, True),
    ("pic_jour", "Jour le plus charge du mois, en multiple de la moyenne quotidienne", "ratio", 3, "0.0", "Hypothese non sourcee : jour de rentree ou veille de partiels (audit du 23/11/2026, F10)", False),
    ("resend_pro", "Resend Pro (50 000 e-mails par mois, sans limite quotidienne)", "$ / mois", 20, USD, "https://resend.com/pricing, " + LU, True),
    ("mails_insc", "E-mails envoyes par inscription", "e-mails", 1.5, "0.0", "Hypothese non sourcee : lien de verification (D69), renvois et mot de passe oublie", False),
    ("mails_paiement", "E-mails envoyes par paiement", "e-mails", 1, "0.0", "Confirmation du contrat (D91) ; les recus sont envoyes par Stripe", True),
    ("apple", "Apple Developer Program", "$ / an", 99, USD, "https://developer.apple.com/programs/, " + LU + " (montant en euros affiche seulement a l'inscription)", True),
    ("assurance", "Assurance responsabilite civile professionnelle", "€ / mois", 25, EUR2, "Hypothese non sourcee : demander des devis", False),
    ("banque", "Compte bancaire dedie", "€ / mois", 5, EUR2, "Hypothese non sourcee", False),
    ("mediateur", "Mediateur de la consommation (SMP), adhesion 3 ans", "€ HT", 25, EUR2, "MEDIATEUR_SOURCE", True),
    ("mois_mediateur", "Mois de l'adhesion au mediateur", "n° de mois", 1, "0", "Planification", False),
    ("inpi", "Depot de marque INPI en ligne, 3 classes (9, 41, 42)", "€", None, EUR2, "INPI_SOURCE", True),
    ("inpi_1", "INPI : premiere classe", "€", 190, EUR2, "INPI_SOURCE", True),
    ("inpi_sup", "INPI : classe supplementaire", "€", 40, EUR2, "INPI_SOURCE", True),
    ("mois_inpi", "Mois du depot de marque (apres avis du conseil)", "n° de mois", 3, "0", "Planification", False),
    ("conseil_pi", "Conseil en propriete industrielle (recherche d'anteriorites, avis)", "€ HT", 800, EUR2, "Hypothese non sourcee : demander un devis", False),
    ("mois_conseil_pi", "Mois de la consultation du conseil", "n° de mois", 1, "0", "Planification", False),
    ("avocat", "Avocat : relecture des CGU et avis sur D77 (faits personnels)", "€ HT", 1500, EUR2, "Hypothese non sourcee : demander un devis", False),
    ("mois_avocat", "Mois de la consultation de l'avocat", "n° de mois", 2, "0", "Planification", False),
    ("tva_achats", "TVA sur les achats en euros (non recuperable en franchise)", "%", 0.20, PCT, "Taux normal, CGI art. 278 ; non recuperable sous l'art. 293 B", True),
    ("__", "Statut : micro-entreprise (entrepreneur individuel, statut affiche sur /api/config)", None, None, None, None, None),
    ("taux_cotis", "Cotisations sociales micro-entreprise", "% du CA", "TAUX_COTIS", PCT, "COTIS_SOURCE", True),
    ("taux_cfp", "Contribution a la formation professionnelle", "% du CA", "TAUX_CFP", "0.00%", "CFP_SOURCE", True),
    ("option_vl", "Option pour le versement liberatoire (1 = oui, 0 = non)", "0 ou 1", 0, "0", "Choix de l'editeur ; conditions de revenu du foyer", False),
    ("taux_vl", "Versement liberatoire de l'impot sur le revenu", "% du CA", "TAUX_VL", "0.00%", "VL_SOURCE", True),
    ("tva", "TVA si la franchise est perdue", "%", 0.20, PCT, "CGI art. 278", True),
    ("seuil_base", "Franchise en base de TVA, seuil de base (services)", "€ / an", "SEUIL_BASE", EUR, "TVA_SOURCE", True),
    ("seuil_majore", "Franchise en base de TVA, seuil majore (services)", "€ / an", "SEUIL_MAJORE", EUR, "TVA_SOURCE", True),
    ("plafond_micro", "Plafond de chiffre d'affaires micro (services)", "€ / an", "PLAFOND_MICRO", EUR, "PLAFOND_SOURCE", True),
    ("tresorerie_depart", "Tresorerie au depart", "€", 0, EUR, "Hypothese non sourcee : apport de l'editeur a saisir", False),
    ("__", "Saisonnalite des inscriptions (moyenne 1 sur l'annee ; calendrier de docs/marketing/plan.md, partie 6)", None, None, None, None, None),
]
SAISON = [("Janvier", 1.2), ("Fevrier", 0.8), ("Mars", 0.7), ("Avril", 1.0), ("Mai", 1.1), ("Juin", 0.6),
          ("Juillet", 0.3), ("Aout", 0.5), ("Septembre", 2.0), ("Octobre", 1.6), ("Novembre", 1.0), ("Decembre", 1.2)]

# Hypotheses par scenario ----------------------------------------------------------------------
# (cle, libelle, unite, (prudent, central, ambitieux), format, source)
PAR_SCENARIO = [
    ("__", "Lancement", None, None, None, None),
    ("mois_paiement", "Mois d'activation du paiement en ligne (1 = premier mois)", "n° de mois", (4, 2, 1), "0", "Depend du SIRET, du mediateur et de Stripe (docs/avant-la-vente.md)"),
    ("mois_ios", "Mois de publication de l'app iOS (0 = jamais)", "n° de mois", (0, 9, 7), "0", "Hypothese ; D101 : voie App Store des formules payantes non tranchee"),
    ("__", "Acquisition", None, None, None, None),
    ("insc_base", "Inscriptions organiques par mois, annee 1, avant saisonnalite", "comptes", (150, 400, 1000), NB, "Hypothese non sourcee : aucune mesure (lancement public non fait)"),
    ("croissance", "Croissance annuelle des inscriptions organiques (annees 2 et 3)", "%", (0.20, 0.50, 0.80), PCT, "Hypothese non sourcee"),
    ("cpa", "Cout d'une inscription obtenue par la publicite", "€ / compte", (6.0, 4.0, 2.5), EUR2, "Hypothese non sourcee : CPM de 12 a 20 € sur Meta (source tierce, plan marketing partie 8) ; taux de clic et d'inscription inconnus"),
    ("mkt_a2", "Budget publicitaire, annee 2", "€ / an", (3000, 6000, 15000), EUR, "Hypothese ; paliers du plan marketing, partie 8"),
    ("mkt_a3", "Budget publicitaire, annee 3", "€ / an", (5000, 12000, 30000), EUR, "Hypothese"),
    ("__", "Comptes gratuits", None, None, None, None),
    ("abandon_gratuit", "Comptes gratuits actifs perdus chaque mois", "% / mois", (0.35, 0.25, 0.20), PCT, "Hypothese non sourcee : fidelite a 7 et 30 jours mesurable dans l'administration (D111), pas encore de donnees"),
    ("q_gratuit", "Questions par compte gratuit actif", "questions / mois", (60, 45, 40), NB, "Hypothese non sourcee ; plafond 10 par jour"),
    ("__", "Passage au payant", None, None, None, None),
    ("conversion", "Conversion mensuelle des gratuits actifs vers le payant", "% / mois", (0.006, 0.012, 0.020), "0.00%", "Hypothese non sourcee : aucune vente a ce jour"),
    ("part_intensif", "Part de l'Intensif parmi les nouveaux payants", "%", (0.15, 0.20, 0.25), PCT, "Hypothese non sourcee"),
    ("churn", "Abonnes payants perdus chaque mois (non-renouvellement)", "% / mois", (0.15, 0.10, 0.07), PCT, "Hypothese non sourcee : paiement sans reconduction (D86), le rachat n'est pas automatique"),
    ("churn_ete", "Perte supplementaire en juillet et en aout", "points / mois", (0.25, 0.20, 0.15), PCT, "Hypothese non sourcee : fin des cours"),
    ("q_etudiant", "Questions par abonne Etudiant", "questions / mois", (300, 220, 180), NB, "Hypothese non sourcee ; plafond 100 par jour"),
    ("q_intensif", "Questions par abonne Intensif", "questions / mois", (800, 600, 500), NB, "Hypothese non sourcee ; plafond 300 par jour"),
    ("__", "Publicite de l'annee 1, mois par mois (plan marketing, partie 8 : organique jusqu'en avril, palier 1 en mai, palier 2 a la rentree)", None, None, None, None),
]
MKT_A1 = [  # prudent, central, ambitieux
    ("Janvier", (0, 0, 0)), ("Fevrier", (0, 0, 0)), ("Mars", (0, 0, 0)), ("Avril", (0, 0, 0)),
    ("Mai", (150, 300, 300)), ("Juin", (0, 0, 150)), ("Juillet", (0, 0, 0)), ("Aout", (0, 0, 0)),
    ("Septembre", (500, 750, 1000)), ("Octobre", (500, 750, 1000)), ("Novembre", (0, 300, 500)), ("Decembre", (0, 300, 500)),
]


def construire(fiscal: dict) -> Workbook:
    wb = Workbook()
    lisez = wb.active
    lisez.title = "Lisez-moi"
    hyp = wb.create_sheet("Hypotheses")
    ref: dict[str, int] = {}

    # --- Hypotheses ---------------------------------------------------------------------------
    hyp.column_dimensions["A"].width = 62
    hyp.column_dimensions["B"].width = 16
    for c in "CDE":
        hyp.column_dimensions[c].width = 13
    hyp.column_dimensions["F"].width = 110
    hyp["A1"] = "Hypotheses du modele (texte bleu = valeur saisie, modifiable ; fond orange = hypothese non sourcee ; noir = formule)"
    hyp["A1"].font = F_TITRE
    hyp["A2"] = "Outil de planification, pas un conseil financier. Les sources ont ete lues le 23 novembre 2026."
    hyp["A2"].font = F_NOTE
    ligne = 4
    for cle, lib, unite, val, fmt, src, sourcee in GLOBALES:
        if cle == "__":
            hyp.cell(ligne, 1, lib).font = F_SOUS
            for c in range(1, 7):
                hyp.cell(ligne, c).fill = FOND_TETE
            if lib.startswith("Calendrier"):
                hyp.cell(ligne, 3, "Valeur").font = F_SOUS
                hyp.cell(ligne, 6, "Source ou statut").font = F_SOUS
            ligne += 1
            continue
        if isinstance(val, str):
            val = fiscal[val]
        if isinstance(src, str) and src in fiscal:
            src = fiscal[src]
        ref[cle] = ligne
        hyp.cell(ligne, 1, lib).font = F_NORMAL
        hyp.cell(ligne, 2, unite).font = F_NORMAL
        c = hyp.cell(ligne, 3, val)
        c.number_format = fmt
        c.font = F_SAISIE
        hyp.cell(ligne, 6, src).font = F_NOTE
        if not sourcee:
            for col in (1, 3):
                hyp.cell(ligne, col).fill = FOND_NONSOURCE
        ligne += 1
    # formules de calcul dans les hypotheses
    R = lambda k: f"$C${ref[k]}"  # noqa: E731
    hyp[f"C{ref['cout_q_usd']}"] = (
        f"=((1-{R('part_secours')}-{R('part_groq')})*({R('tok_gen_in')}*{R('gem_in')}+{R('tok_gen_out')}*{R('gem_out')})"
        f"+{R('part_secours')}*({R('tok_gen_in')}*{R('sec_in')}+{R('tok_gen_out')}*{R('sec_out')})"
        f"+{R('part_groq')}*({R('tok_gen_in')}*{R('groq_in')}+{R('tok_gen_out')}*{R('groq_out')})"
        f"+{R('taux_reform')}*({R('tok_ref_in')}*{R('gem_in')}+{R('tok_ref_out')}*{R('gem_out')}))"
        f"*(1+{R('annexes')})/1000000"
    )
    hyp[f"C{ref['cout_q_eur']}"] = f"={R('cout_q_usd')}/{R('usd_par_eur')}"
    hyp[f"C{ref['inpi']}"] = f"={R('inpi_1')}+2*{R('inpi_sup')}"
    for k in ("cout_q_usd", "cout_q_eur", "inpi"):
        hyp[f"C{ref[k]}"].font = F_NORMAL
    hyp[f"C{ref['cout_q_eur']}"].fill = FOND_CLE

    # saisonnalite
    ref["saison_debut"] = ligne
    for nom, v in SAISON:
        hyp.cell(ligne, 1, nom).font = F_NORMAL
        hyp.cell(ligne, 2, "indice").font = F_NORMAL
        c = hyp.cell(ligne, 3, v)
        c.font = F_SAISIE
        c.number_format = "0.00"
        c.fill = FOND_NONSOURCE
        hyp.cell(ligne, 6, "Hypothese non sourcee : pics a la rentree et aux partiels, creux l'ete").font = F_NOTE
        ligne += 1
    ref["saison_fin"] = ligne - 1
    hyp.cell(ligne, 1, "Moyenne (doit valoir 1)").font = F_GRAS
    hyp.cell(ligne, 3, f"=AVERAGE(C{ref['saison_debut']}:C{ref['saison_fin']})").number_format = "0.00"
    ligne += 2

    # hypotheses par scenario
    ligne_tete = ligne
    for cle, lib, unite, vals, fmt, src in PAR_SCENARIO:
        if cle == "__":
            hyp.cell(ligne, 1, lib).font = F_SOUS
            for c in range(1, 7):
                hyp.cell(ligne, c).fill = FOND_TETE
            if ligne == ligne_tete:
                for (nom, col) in SCENARIOS:
                    hyp[f"{col}{ligne}"] = nom
                    hyp[f"{col}{ligne}"].font = F_SOUS
                hyp.cell(ligne, 6, "Source ou statut").font = F_SOUS
            ligne += 1
            continue
        ref[cle] = ligne
        hyp.cell(ligne, 1, lib).font = F_NORMAL
        hyp.cell(ligne, 2, unite).font = F_NORMAL
        for (nom, col), v in zip(SCENARIOS, vals):
            c = hyp[f"{col}{ligne}"]
            c.value = v
            c.number_format = fmt
            c.font = F_SAISIE
            c.fill = FOND_CLE
        hyp.cell(ligne, 6, src).font = F_NOTE
        if "non sourcee" in src or src.startswith("Hypothese"):
            hyp.cell(ligne, 1).fill = FOND_NONSOURCE
        ligne += 1
    ref["mkt_debut"] = ligne
    for nom, vals in MKT_A1:
        hyp.cell(ligne, 1, f"Publicite, {nom} de l'annee 1").font = F_NORMAL
        hyp.cell(ligne, 2, "€").font = F_NORMAL
        for (_, col), v in zip(SCENARIOS, vals):
            c = hyp[f"{col}{ligne}"]
            c.value = v
            c.number_format = EUR
            c.font = F_SAISIE
        hyp.cell(ligne, 6, "Plan marketing, partie 8 ; montants de l'editeur a confirmer").font = F_NOTE
        ligne += 1
    ref["mkt_fin"] = ligne - 1
    hyp.freeze_panes = "C4"

    # --- Feuilles de scenario ----------------------------------------------------------------
    lignes = {}
    for nom, col in SCENARIOS:
        ws = wb.create_sheet(nom)
        lignes = remplir_scenario(ws, col, ref)

    synthese(wb, ref, lignes)
    graphiques(wb, lignes)
    lisez_moi(lisez, fiscal)
    wb.move_sheet("Synthese", offset=-(len(wb.sheetnames) - 2))
    wb.move_sheet("Graphiques", offset=-(len(wb.sheetnames) - 3))
    wb.calculation.fullCalcOnLoad = True
    return wb


def remplir_scenario(ws, col: str, ref: dict) -> dict:
    H = lambda k: f"Hypotheses!${col}${ref[k]}"  # noqa: E731  (hypothese du scenario)
    G = lambda k: f"Hypotheses!$C${ref[k]}"  # noqa: E731  (hypothese globale)
    saison = f"Hypotheses!$C${ref['saison_debut']}:$C${ref['saison_fin']}"
    mkt = f"Hypotheses!${col}${ref['mkt_debut']}:${col}${ref['mkt_fin']}"

    ws.column_dimensions["A"].width = 52
    ws.column_dimensions["B"].width = 12
    der = get_column_letter(2 + NB_MOIS)
    ws["A1"] = f"Scenario {ws.title} : calcul mois par mois (36 mois). Ne rien saisir ici : tout vient de la feuille Hypotheses."
    ws["A1"].font = F_TITRE

    L = {}
    plan = [
        ("mois", "Mois n°", "", None, "0"),
        ("date", "Mois", "", None, DATE),
        ("annee", "Annee du modele", "", None, "0"),
        ("mois_civil", "Mois civil", "", None, "0"),
        ("saison", "Indice de saisonnalite", "", None, "0.00"),
        ("actif", "Paiement en ligne actif (1 = oui)", "", None, "0"),
        ("_", "Acquisition", None, None, None),
        ("insc_org", "Inscriptions organiques", "comptes", None, NB),
        ("mkt", "Budget publicitaire", "€", None, EUR),
        ("insc_pub", "Inscriptions obtenues par la publicite", "comptes", None, NB),
        ("insc", "Inscriptions totales", "comptes", None, NB),
        ("_", "Comptes", None, None, None),
        ("grat_debut", "Comptes gratuits actifs en debut de mois", "comptes", None, NB),
        ("nv_payants", "Nouveaux abonnes payants", "abonnes", None, NB1),
        ("nv_etud", "  dont Etudiant", "abonnes", None, NB1),
        ("nv_int", "  dont Intensif", "abonnes", None, NB1),
        ("grat_fin", "Comptes gratuits actifs en fin de mois", "comptes", None, NB),
        ("taux_perte", "Taux de perte des payants ce mois", "%", None, PCT),
        ("ab_etud", "Abonnes Etudiant en fin de mois", "abonnes", None, NB1),
        ("ab_int", "Abonnes Intensif en fin de mois", "abonnes", None, NB1),
        ("ab_total", "Abonnes payants en fin de mois", "abonnes", None, NB1),
        ("pertes", "Abonnes perdus ce mois", "abonnes", None, NB1),
        ("_", "Chiffre d'affaires", None, None, None),
        ("ca_ttc", "Encaissements des abonnes (prix affiches)", "€", None, EUR),
        ("tva_due", "TVA applicable (1 = franchise perdue)", "", None, "0"),
        ("ca", "Chiffre d'affaires hors TVA", "€", None, EUR),
        ("tva_col", "TVA collectee a reverser", "€", None, EUR),
        ("_", "Couts variables", None, None, None),
        ("questions", "Questions posees", "questions", None, NB),
        ("cout_modele", "Cout du modele (Gemini, secours)", "€", None, EUR),
        ("stripe", "Frais Stripe", "€", None, EUR),
        ("mails", "E-mails envoyes", "e-mails", None, NB),
        ("resend", "Resend (au-dela de l'offre gratuite)", "€", None, EUR),
        ("cv", "Total des couts variables", "€", None, EUR),
        ("marge", "Marge brute", "€", None, EUR),
        ("marge_pct", "Taux de marge brute", "%", None, PCT),
        ("_", "Charges fixes et ponctuelles", None, None, None),
        ("f_vps", "Serveur VPS", "€", None, EUR),
        ("f_dom", "Nom de domaine", "€", None, EUR),
        ("f_cf", "Cloudflare", "€", None, EUR),
        ("f_apple", "Apple Developer Program", "€", None, EUR),
        ("f_ass", "Assurance et banque", "€", None, EUR),
        ("f_ponct", "Frais ponctuels (mediateur, conseil, marque, avocat)", "€", None, EUR),
        ("fixes", "Total des charges fixes et ponctuelles", "€", None, EUR),
        ("_", "Resultat et tresorerie", None, None, None),
        ("pub", "Publicite", "€", None, EUR),
        ("rex", "Resultat avant cotisations", "€", None, EUR),
        ("cotis", "Cotisations sociales et formation professionnelle", "€", None, EUR),
        ("vl", "Versement liberatoire de l'impot sur le revenu", "€", None, EUR),
        ("net", "Resultat net pour l'editeur (avant sa remuneration)", "€", None, EUR),
        ("treso", "Tresorerie en fin de mois", "€", None, EUR),
        ("_", "Indicateurs", None, None, None),
        ("pm", "Mois a resultat net positif (999 = non)", "", None, "0"),
        ("arpu", "Recette moyenne par abonne payant, hors TVA", "€ / mois", None, EUR2),
        ("mails_pic", "E-mails du jour le plus charge (estimation)", "e-mails", None, NB),
        ("_", "Part apportee par la publicite (meme calcul, inscriptions publicitaires seules)", None, None, None),
        ("grat_pub", "Comptes gratuits actifs venus de la publicite, fin de mois", "comptes", None, NB),
        ("nv_pub", "Nouveaux abonnes payants venus de la publicite", "abonnes", None, NB1),
        ("ab_pub", "Abonnes payants venus de la publicite, fin de mois", "abonnes", None, NB1),
    ]
    r = 3
    for cle, lib, unite, _, fmt in plan:
        if cle == "_":
            ws.cell(r, 1, lib).font = F_SOUS
            for c in range(1, 3 + NB_MOIS):
                ws.cell(r, c).fill = FOND_TETE
            r += 1
            continue
        L[cle] = (r, fmt)
        ws.cell(r, 1, lib).font = F_GRAS if cle in ("insc", "ab_total", "ca", "marge", "net", "treso") else F_NORMAL
        ws.cell(r, 2, unite).font = F_NORMAL
        r += 1

    def f(cle, j):
        """Formule de la ligne `cle` pour la colonne de mois j (1..36)."""
        c = get_column_letter(2 + j)
        p = get_column_letter(1 + j)  # colonne precedente (B au premier mois : texte, N() donne 0)
        x = lambda k: f"{c}{L[k][0]}"  # noqa: E731
        prev = lambda k: f"N({p}{L[k][0]})"  # noqa: E731
        lr = lambda k: f"${'C'}${L[k][0]}:${der}${L[k][0]}"  # noqa: E731
        return {
            "mois": f"=N({p}{L['mois'][0]})+1",
            "date": f"=DATE({G('annee_debut')},{G('mois_debut')}+{x('mois')}-1,1)",
            "annee": f"=INT(({x('mois')}-1)/12)+1",
            "mois_civil": f"=MONTH({x('date')})",
            "saison": f"=INDEX({saison},{x('mois_civil')})",
            "actif": f"=IF({x('mois')}>={H('mois_paiement')},1,0)",
            "insc_org": f"={H('insc_base')}*{x('saison')}*(1+{H('croissance')})^({x('annee')}-1)",
            "mkt": f"=IF({x('annee')}=1,INDEX({mkt},{x('mois_civil')}),IF({x('annee')}=2,{H('mkt_a2')},{H('mkt_a3')})*{x('saison')}/12)",
            "insc_pub": f"=IF({H('cpa')}>0,{x('mkt')}/{H('cpa')},0)",
            "insc": f"={x('insc_org')}+{x('insc_pub')}",
            "grat_debut": f"={prev('grat_fin')}",
            "nv_payants": f"={x('grat_debut')}*{H('conversion')}*{x('actif')}",
            "nv_etud": f"={x('nv_payants')}*(1-{H('part_intensif')})",
            "nv_int": f"={x('nv_payants')}*{H('part_intensif')}",
            "grat_fin": f"={x('grat_debut')}*(1-{H('abandon_gratuit')})+{x('insc')}-{x('nv_payants')}",
            "taux_perte": f"=MIN(1,{H('churn')}+IF(OR({x('mois_civil')}=7,{x('mois_civil')}=8),{H('churn_ete')},0))",
            "ab_etud": f"={prev('ab_etud')}*(1-{x('taux_perte')})+{x('nv_etud')}",
            "ab_int": f"={prev('ab_int')}*(1-{x('taux_perte')})+{x('nv_int')}",
            "ab_total": f"={x('ab_etud')}+{x('ab_int')}",
            "pertes": f"=({prev('ab_etud')}+{prev('ab_int')})*{x('taux_perte')}",
            "ca_ttc": f"={x('ab_etud')}*{G('prix_etudiant')}+{x('ab_int')}*{G('prix_intensif')}",
            # Franchise perdue : CA de l'annee precedente au-dessus du seuil de base, ou cumul de l'annee
            # (mois en cours compris : la TVA est due des le depassement, audit du 23/11/2026, F9) au-dessus
            # du seuil majore ; tout le mois du depassement est soumis a la TVA (prudent). Test sur les encaissements TTC pour eviter une
            # reference circulaire (legerement prudent).
            "tva_due": (f"=IF(OR(SUMIFS({lr('ca_ttc')},{lr('annee')},{x('annee')}-1)>{G('seuil_base')},"
                        f"SUMIFS({lr('ca_ttc')},{lr('annee')},{x('annee')},{lr('mois')},\"<=\"&{x('mois')})>{G('seuil_majore')}),1,0)"),
            "ca": f"={x('ca_ttc')}/(1+{G('tva')}*{x('tva_due')})",
            "tva_col": f"={x('ca_ttc')}-{x('ca')}",
            "questions": f"={x('grat_fin')}*{H('q_gratuit')}+{x('ab_etud')}*{H('q_etudiant')}+{x('ab_int')}*{H('q_intensif')}",
            "cout_modele": f"={x('questions')}*{G('cout_q_eur')}",
            "stripe": f"={x('ca_ttc')}*{G('stripe_pct')}+{x('ab_total')}/{G('duree_achat')}*{G('stripe_fixe')}",
            "mails": f"={x('insc')}*{G('mails_insc')}+{x('ab_total')}/{G('duree_achat')}*{G('mails_paiement')}",
            "resend": f"=IF(OR({x('mails')}>{G('resend_seuil')},{x('mails_pic')}>{G('resend_jour')}),{G('resend_pro')}/{G('usd_par_eur')},0)",
            "cv": f"={x('cout_modele')}+{x('stripe')}+{x('resend')}",
            "marge": f"={x('ca')}-{x('cv')}",
            "marge_pct": f"=IF({x('ca')}>0,{x('marge')}/{x('ca')},0)",
            "f_vps": f"={G('vps')}",
            "f_dom": f"={G('domaine')}/12",
            "f_cf": f"={G('cloudflare')}",
            "f_apple": f"=IF(AND({H('mois_ios')}>0,{x('mois')}>={H('mois_ios')}),{G('apple')}/{G('usd_par_eur')}/12,0)",
            "f_ass": f"={G('assurance')}+{G('banque')}",
            "f_ponct": (f"=(IF({x('mois')}={G('mois_mediateur')},{G('mediateur')},0)"
                        f"+IF({x('mois')}={G('mois_conseil_pi')},{G('conseil_pi')},0)"
                        f"+IF({x('mois')}={G('mois_avocat')},{G('avocat')},0))*(1+{G('tva_achats')})"
                        f"+IF({x('mois')}={G('mois_inpi')},{G('inpi')},0)"),
            "fixes": f"=SUM({c}{L['f_vps'][0]}:{c}{L['f_ponct'][0]})",
            "pub": f"={x('mkt')}",
            "rex": f"={x('marge')}-{x('fixes')}-{x('pub')}",
            "cotis": f"={x('ca')}*({G('taux_cotis')}+{G('taux_cfp')})",
            "vl": f"={x('ca')}*{G('taux_vl')}*{G('option_vl')}",
            "net": f"={x('rex')}-{x('cotis')}-{x('vl')}",
            "treso": f"={prev('treso')}+{x('net')}+IF({x('mois')}=1,{G('tresorerie_depart')},0)",
            "pm": f"=IF(AND({x('actif')}=1,{x('net')}>=0),{x('mois')},999)",
            "arpu": f"=IF({x('ab_total')}>0,{x('ca')}/{x('ab_total')},0)",
            "mails_pic": f"={x('mails')}/30.4*{G('pic_jour')}",
            # Le calcul des comptes et des abonnes est lineaire en inscriptions : la meme chaine appliquee aux
            # seules inscriptions publicitaires donne exactement les abonnes en plus dus a la publicite.
            "nv_pub": f"={prev('grat_pub')}*{H('conversion')}*{x('actif')}",
            "grat_pub": f"={prev('grat_pub')}*(1-{H('abandon_gratuit')})+{x('insc_pub')}-{x('nv_pub')}",
            "ab_pub": f"={prev('ab_pub')}*(1-{x('taux_perte')})+{x('nv_pub')}",
        }[cle]

    for j in range(1, NB_MOIS + 1):
        ws.column_dimensions[get_column_letter(2 + j)].width = 11
        for cle, (rr, fmt) in L.items():
            cell = ws.cell(rr, 2 + j, f(cle, j))
            cell.number_format = fmt
            cell.font = F_NORMAL
            if cle in ("mois", "date"):
                cell.font = F_GRAS
            if cle in ("ca", "net", "treso"):
                cell.fill = FOND_SECTION
    ws.freeze_panes = "C3"
    return {k: v[0] for k, v in L.items()}


def synthese(wb, ref, L):
    ws = wb.create_sheet("Synthese")
    ws.column_dimensions["A"].width = 58
    ws["A1"] = "Synthese par annee et par scenario (formules liees aux feuilles Prudent, Central, Ambitieux)"
    ws["A1"].font = F_TITRE
    ws["A2"] = "Annee 1 = 2027 si la feuille Hypotheses n'est pas modifiee. Resultats avant remuneration de l'editeur. Outil de planification, pas un conseil financier."
    ws["A2"].font = F_NOTE
    col = 2
    entetes = []
    for nom, hcol in SCENARIOS:
        for a in (1, 2, 3):
            entetes.append((nom, hcol, a, get_column_letter(col)))
            ws.column_dimensions[get_column_letter(col)].width = 13
            col += 1
    for nom, hcol, a, c in entetes:
        ws[f"{c}4"] = nom
        ws[f"{c}5"] = f"Annee {a}"
        for rr in (4, 5):
            ws[f"{c}{rr}"].font = F_SOUS
            ws[f"{c}{rr}"].fill = FOND_TETE
            ws[f"{c}{rr}"].alignment = Alignment(horizontal="center")
    ws["A4"].fill = FOND_TETE
    ws["A5"].fill = FOND_TETE
    ws["A5"] = "Indicateur"
    ws["A5"].font = F_SOUS

    der = get_column_letter(2 + NB_MOIS)

    def plage(nom, cle):
        return f"'{nom}'!$C${L[cle]}:${der}${L[cle]}"

    def somme(nom, cle, a):
        return f"=SUMIFS({plage(nom, cle)},{plage(nom, 'annee')},{a})"

    def fin(nom, cle, a):
        return f"=INDEX({plage(nom, cle)},{12 * a})"

    lignes = [
        ("Inscriptions", lambda n, h, a: somme(n, "insc", a), NB),
        ("Comptes gratuits actifs en fin d'annee", lambda n, h, a: fin(n, "grat_fin", a), NB),
        ("Nouveaux abonnes payants", lambda n, h, a: somme(n, "nv_payants", a), NB),
        ("Abonnes payants en fin d'annee", lambda n, h, a: fin(n, "ab_total", a), NB),
        ("Chiffre d'affaires hors TVA", lambda n, h, a: somme(n, "ca", a), EUR),
        ("Couts variables", lambda n, h, a: somme(n, "cv", a), EUR),
        ("  dont cout du modele", lambda n, h, a: somme(n, "cout_modele", a), EUR),
        ("  dont frais Stripe", lambda n, h, a: somme(n, "stripe", a), EUR),
        ("Marge brute", lambda n, h, a: somme(n, "marge", a), EUR),
        ("Taux de marge brute", None, PCT),
        ("Charges fixes et ponctuelles", lambda n, h, a: somme(n, "fixes", a), EUR),
        ("Publicite", lambda n, h, a: somme(n, "pub", a), EUR),
        ("Cotisations, formation professionnelle, impot liberatoire", None, EUR),
        ("Resultat net pour l'editeur", lambda n, h, a: somme(n, "net", a), EUR),
        ("Tresorerie en fin d'annee", lambda n, h, a: fin(n, "treso", a), EUR),
        ("Recette moyenne par abonne et par mois, hors TVA", None, EUR2),
        ("Perte mensuelle moyenne des payants (hypothese, ete compris)", None, PCT),
        ("Duree de vie moyenne d'un abonne (mois)", None, NB1),
        ("LTV nette du cout des gratuits : marge brute sur la duree de vie d'un abonne", None, EUR2),
        ("CAC moyen : publicite / tous les nouveaux abonnes (organiques compris)", None, EUR2),
        ("Rapport LTV / CAC moyen", None, "0.0"),
        ("Nouveaux abonnes payants apportes par la publicite", lambda n, h, a: somme(n, "nv_pub", a), NB1),
        ("CAC marginal : publicite / abonnes apportes par la publicite", None, EUR2),
        ("Rapport LTV / CAC marginal", None, "0.0"),
        ("Cout par question (€)", None, '0.00000" €"'),
        ("Franchise de TVA perdue dans l'annee (1 = oui)", None, "0"),
        ("Plafond du regime micro depasse (1 = oui)", None, "0"),
    ]
    rr = 6
    pos = {}
    for lib, fn, fmt in lignes:
        pos[lib] = rr
        ws.cell(rr, 1, lib).font = F_GRAS if lib in ("Chiffre d'affaires hors TVA", "Marge brute", "Resultat net pour l'editeur", "Tresorerie en fin d'annee") else F_NORMAL
        ws.cell(rr, 1).border = BORD
        rr += 1
    for nom, hcol, a, c in entetes:
        HS = lambda k: f"Hypotheses!${hcol}${ref[k]}"  # noqa: E731
        for lib, fn, fmt in lignes:
            r0 = pos[lib]
            if fn is not None:
                v = fn(nom, hcol, a)
            elif lib == "Taux de marge brute":
                v = f"=IF({c}{pos['Chiffre d' + chr(39) + 'affaires hors TVA']}>0,{c}{pos['Marge brute']}/{c}{pos['Chiffre d' + chr(39) + 'affaires hors TVA']},0)"
            elif lib.startswith("Cotisations"):
                v = f"=SUMIFS({plage(nom, 'cotis')},{plage(nom, 'annee')},{a})+SUMIFS({plage(nom, 'vl')},{plage(nom, 'annee')},{a})"
            elif lib.startswith("Recette moyenne"):
                v = (f"=IF(SUMIFS({plage(nom, 'ab_total')},{plage(nom, 'annee')},{a})>0,"
                     f"{c}{pos['Chiffre d' + chr(39) + 'affaires hors TVA']}/SUMIFS({plage(nom, 'ab_total')},{plage(nom, 'annee')},{a}),0)")
            elif lib.startswith("Perte mensuelle"):
                v = f"={HS('churn')}+2*{HS('churn_ete')}/12"
            elif lib.startswith("Duree de vie"):
                v = f"=IF({c}{pos[lib] - 1}>0,1/{c}{pos[lib] - 1},0)"
            elif lib.startswith("LTV nette"):
                v = f"={c}{pos['Recette moyenne par abonne et par mois, hors TVA']}*{c}{pos['Taux de marge brute']}*{c}{pos['Duree de vie moyenne d' + chr(39) + 'un abonne (mois)']}"
            elif lib.startswith("CAC moyen"):
                v = f"=IF({c}{pos['Nouveaux abonnes payants']}>0,{c}{pos['Publicite']}/{c}{pos['Nouveaux abonnes payants']},0)"
            elif lib.startswith("CAC marginal"):
                v = f"=IF({c}{pos[lib] - 1}>0,{c}{pos['Publicite']}/{c}{pos[lib] - 1},0)"
            elif lib.startswith("Rapport"):
                ltv = f"{c}{pos['LTV nette du cout des gratuits : marge brute sur la duree de vie d' + chr(39) + 'un abonne']}"
                v = f"=IF({c}{pos[lib] - 1}>0,{ltv}/{c}{pos[lib] - 1},0)"
            elif lib.startswith("Cout par question"):
                v = f"=Hypotheses!$C${ref['cout_q_eur']}"
            elif lib.startswith("Franchise"):
                v = f"=IF(SUMIFS({plage(nom, 'tva_due')},{plage(nom, 'annee')},{a})>0,1,0)"
            elif lib.startswith("Plafond"):
                v = f"=IF({c}{pos['Chiffre d' + chr(39) + 'affaires hors TVA']}>Hypotheses!$C${ref['plafond_micro']},1,0)"
            cell = ws[f"{c}{r0}"]
            cell.value = v
            cell.number_format = fmt
            cell.font = F_LIEN if (fn is not None or lib.startswith("Perte") or lib.startswith("Cout par")) else F_NORMAL
            cell.border = BORD

    # Indicateurs sur 36 mois
    rr += 1
    ws.cell(rr, 1, "Sur les 36 mois").font = F_SOUS
    for c in range(1, 11):
        ws.cell(rr, c).fill = FOND_TETE
    for i, (nom, _h) in enumerate(SCENARIOS):
        c = get_column_letter(2 + 3 * i)
        ws[f"{c}{rr}"] = nom
        ws[f"{c}{rr}"].font = F_SOUS
    rr += 1
    pm_ligne = rr
    ws.cell(rr, 1, "Point mort : premier mois a resultat net positif (n° de mois)").font = F_GRAS
    ws.cell(rr + 1, 1, "Point mort : date").font = F_NORMAL
    ws.cell(rr + 2, 1, "Besoin de financement : tresorerie la plus basse (si negative)").font = F_GRAS
    ws.cell(rr + 3, 1, "Mois de la tresorerie la plus basse").font = F_NORMAL
    ws.cell(rr + 4, 1, "Resultat net cumule sur 36 mois").font = F_NORMAL
    for i, (nom, _h) in enumerate(SCENARIOS):
        c = get_column_letter(2 + 3 * i)
        pm = f"MIN({plage(nom, 'pm')})"
        ws[f"{c}{rr}"] = f'=IF({pm}=999,"non atteint",{pm})'
        ws[f"{c}{rr + 1}"] = f'=IF({pm}=999,"non atteint",INDEX({plage(nom, "date")},{pm}))'
        ws[f"{c}{rr + 1}"].number_format = DATE
        ws[f"{c}{rr + 2}"] = f"=-MIN(0,MIN({plage(nom, 'treso')}))"
        ws[f"{c}{rr + 2}"].number_format = EUR
        ws[f"{c}{rr + 3}"] = f"=MATCH(MIN({plage(nom, 'treso')}),{plage(nom, 'treso')},0)"
        ws[f"{c}{rr + 4}"] = f"=SUM({plage(nom, 'net')})"
        ws[f"{c}{rr + 4}"].number_format = EUR
        for k in range(5):
            ws[f"{c}{rr + k}"].font = F_LIEN
    ws.cell(rr + 6, 1, "Lecture : point mort = premier mois ou le resultat net est positif apres l'activation du paiement ; il peut redevenir negatif ensuite (ete, campagnes). Le besoin de financement est l'apport qu'il faudrait pour que la tresorerie ne soit jamais negative.").font = F_NOTE
    ws.cell(rr + 7, 1, "LTV : recette moyenne x taux de marge brute de l'annee / perte mensuelle moyenne ; le taux de marge comprend le cout des comptes gratuits (LTV nette du cout des gratuits). CAC moyen : publicite de l'annee / tous les nouveaux abonnes de l'annee, organiques compris. CAC marginal : publicite / abonnes en plus dus a la publicite (lignes « venus de la publicite » des feuilles de scenario) ; c'est lui qui dit si la publicite rapporte plus qu'elle ne coute.").font = F_NOTE
    ws.freeze_panes = "B6"
    return pm_ligne


def graphiques(wb, L):
    ws = wb.create_sheet("Graphiques")
    ws["A1"] = "Graphiques de synthese (donnees liees aux feuilles de scenario)"
    ws["A1"].font = F_TITRE
    entetes = ["Mois"] + [f"CA {n}" for n, _ in SCENARIOS] + [f"Tresorerie {n}" for n, _ in SCENARIOS] + [f"Abonnes {n}" for n, _ in SCENARIOS]
    for j, e in enumerate(entetes, start=1):
        c = ws.cell(3, j, e)
        c.font = F_SOUS
        c.fill = FOND_TETE
        ws.column_dimensions[get_column_letter(j)].width = 14
    for i in range(1, NB_MOIS + 1):
        r = 3 + i
        mc = get_column_letter(2 + i)
        ws.cell(r, 1, f"='Central'!{mc}{L['date']}").number_format = DATE
        for k, (nom, _) in enumerate(SCENARIOS):
            ws.cell(r, 2 + k, f"='{nom}'!{mc}{L['ca']}").number_format = EUR
            ws.cell(r, 5 + k, f"='{nom}'!{mc}{L['treso']}").number_format = EUR
            ws.cell(r, 8 + k, f"='{nom}'!{mc}{L['ab_total']}").number_format = NB
        for j in range(1, 11):
            ws.cell(r, j).font = F_LIEN
    der = 3 + NB_MOIS
    couleurs = ["B85042", "2F5D4A", "D4A017"]

    def courbe(titre, col0, ytitre, ancre):
        ch = LineChart()
        ch.title = titre
        ch.y_axis.title = ytitre
        ch.x_axis.title = "Mois"
        ch.height, ch.width = 9, 22
        data = Reference(ws, min_col=col0, max_col=col0 + 2, min_row=3, max_row=der)
        ch.add_data(data, titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=1, min_row=4, max_row=der))
        ch.x_axis.number_format = "mmm yy"
        for s, coul in zip(ch.series, couleurs):
            s.graphicalProperties.line.solidFill = coul
            s.graphicalProperties.line.width = 22000
            s.smooth = False
        ch.roundedCorners = False
        ch.legend.position = "b"
        ch.legend.overlay = False
        ch.title.overlay = False
        ch.x_axis.title.overlay = False
        ch.y_axis.title.overlay = False
        ch.x_axis.delete = False
        ch.y_axis.delete = False
        ws.add_chart(ch, ancre)

    courbe("Chiffre d'affaires mensuel hors TVA (€)", 2, "€", "L3")
    courbe("Trésorerie en fin de mois (€)", 5, "€", "L22")
    courbe("Abonnés payants en fin de mois", 8, "abonnés", "L41")
    ws.freeze_panes = "B4"


def lisez_moi(ws, fiscal):
    ws.column_dimensions["A"].width = 130
    lignes = [
        ("Lexia : projections financieres sur 3 ans (36 mois), trois scenarios", F_TITRE),
        ("Prepare le 23 novembre 2026 par Axion Studio. Outil de planification : ni prevision certaine, ni conseil financier ou d'investissement.", F_NOTE),
        ("", None),
        ("Feuilles", F_GRAS),
        ("Hypotheses : toutes les valeurs saisies (prix, couts, taux, acquisition, conversion, perte des abonnes, publicite). C'est la seule feuille a modifier.", F_NORMAL),
        ("Synthese : resultats par annee et par scenario, point mort, besoin de financement, CAC et LTV.", F_NORMAL),
        ("Graphiques : chiffre d'affaires, tresorerie et abonnes payants des trois scenarios sur 36 mois.", F_NORMAL),
        ("Prudent, Central, Ambitieux : calcul mois par mois ; l'annee 1 se lit dans les colonnes C a N. Aucune valeur saisie, seulement des formules.", F_NORMAL),
        ("", None),
        ("Code des couleurs", F_GRAS),
        ("Texte bleu : valeur saisie, modifiable. Texte noir : formule. Texte vert : lien vers une autre feuille.", F_NORMAL),
        ("Fond jaune : hypothese cle de scenario. Fond orange : hypothese non sourcee (aucune mesure ni page officielle derriere).", F_NORMAL),
        ("", None),
        ("Mecanique du modele", F_GRAS),
        ("1. Inscriptions = organiques (base x saisonnalite x croissance annuelle) + publicite / cout d'une inscription.", F_NORMAL),
        ("2. Comptes gratuits actifs : stock du mois precedent, moins les abandons, plus les inscriptions, moins les passages au payant.", F_NORMAL),
        ("3. Nouveaux payants = gratuits actifs en debut de mois x conversion mensuelle, a partir du mois d'activation du paiement ; repartis entre Etudiant et Intensif.", F_NORMAL),
        ("4. Abonnes : stock precedent x (1 - perte du mois) + nouveaux. Le paiement est unique pour 1 a 12 mois, sans reconduction (D86) : la perte represente le non-rachat.", F_NORMAL),
        ("5. Encaissements = abonnes x prix mensuel affiche (simplification : un achat de plusieurs mois est etale). Sous franchise de TVA, le prix affiche est le chiffre d'affaires ; si la franchise est perdue, la TVA est retiree du prix.", F_NORMAL),
        ("6. Couts variables : questions x cout par question (jetons mesures x grille Gemini, part de secours, appels annexes), frais Stripe, Resend Pro dès que le mois dépasse 3 000 e-mails ou que le jour le plus chargé dépasse 100 e-mails.", F_NORMAL),
        ("7. Micro-entreprise : cotisations et formation professionnelle en pourcentage du chiffre d'affaires, versement liberatoire en option. Pas d'impot sur les societes.", F_NORMAL),
        ("8. Tresorerie = apport de depart + resultats nets cumules (les cotisations sont supposees payees le mois meme).", F_NORMAL),
        ("", None),
        ("Limites", F_GRAS),
        ("Aucune donnee de vente ni de fidelite reelle : Lexia est en phase de developpement. Les hypotheses d'acquisition, de conversion et de perte sont des ordres de grandeur a remplacer par les mesures de l'administration (D111) des qu'elles existent.", F_NORMAL),
        ("Le cout par question vient de 20 appels d'essai (logs/modele.jsonl, 13 au 17 novembre 2026), pas de trafic reel ; a remesurer avec eval/cout.py apres le passage de Gemini au niveau payant.", F_NORMAL),
        ("Le seuil de TVA est teste sur les encaissements toutes taxes comprises (evite une reference circulaire, legerement prudent).", F_NORMAL),
        ("Le temps de l'editeur n'est pas valorise ; le resultat net est avant sa remuneration.", F_NORMAL),
        ("Les valeurs en cache sont ecrites par un enregistrement dans Excel apres la generation (outils/enregistrer_excel.sh) : l'apercu du Mac, GitHub ou une messagerie affichent donc les resultats ; Excel, Numbers ou LibreOffice recalculent a l'ouverture.", F_NORMAL),
        ("", None),
        ("Sources fiscales et sociales (lues le 23/11/2026)", F_GRAS),
    ] + [(s, F_NORMAL) for s in fiscal["SOURCES_LISTE"]]
    for i, (t, fnt) in enumerate(lignes, start=1):
        c = ws.cell(i, 1, t)
        if fnt:
            c.font = fnt
        c.alignment = Alignment(wrap_text=True, vertical="top")


MOTS = {
    "Hypotheses": "Hypothèses", "Hypothese": "Hypothèse", "hypothese": "hypothèse", "hypotheses": "hypothèses",
    "sourcee": "sourcée", "Resultat": "Résultat", "resultat": "résultat", "resultats": "résultats",
    "Tresorerie": "Trésorerie", "tresorerie": "trésorerie", "Annee": "Année", "annee": "année", "annees": "années",
    "Etudiant": "Étudiant", "Synthese": "Synthèse", "Mecanique": "Mécanique", "Modele": "Modèle",
    "premiere": "première", "reponse": "réponse", "entree": "entrée", "reflexion": "réflexion", "calcule": "calculé",
    "Cout": "Coût", "cout": "coût", "couts": "coûts", "Couts": "Coûts", "depart": "départ", "Duree": "Durée",
    "duree": "durée", "achetee": "achetée", "recuperable": "récupérable", "mediateur": "médiateur",
    "Mediateur": "Médiateur", "adhesion": "adhésion", "depot": "dépôt", "Depot": "Dépôt", "propriete": "propriété",
    "anteriorites": "antériorités", "responsabilite": "responsabilité", "dedie": "dédié", "liberatoire": "libératoire",
    "impot": "impôt", "regime": "régime", "Saisonnalite": "Saisonnalité", "saisonnalite": "saisonnalité",
    "Fevrier": "Février", "Aout": "Août", "Decembre": "Décembre", "ete": "été", "supplementaire": "supplémentaire",
    "publicite": "publicité", "Publicite": "Publicité", "Abonnes": "Abonnés", "abonnes": "abonnés", "abonne": "abonné",
    "Abonne": "Abonné", "affiches": "affichés", "collectee": "collectée", "posees": "posées", "envoyes": "envoyés",
    "editeur": "éditeur", "remuneration": "rémunération", "debut": "début", "Depend": "Dépend", "deja": "déjà",
    "donnees": "données", "donnee": "donnée", "reelle": "réelle", "reel": "réel", "Prepare": "Préparé",
    "prevision": "prévision", "negative": "négative", "negatif": "négatif", "apres": "après", "precedent": "précédent",
    "precedente": "précédente", "precedents": "précédents", "verification": "vérification", "oublie": "oublié",
    "recus": "reçus", "parites": "parités", "decembre": "décembre", "leves": "levés", "equivalent": "équivalent",
    "reference": "référence", "legerement": "légèrement", "represente": "représente", "etale": "étalé",
    "retiree": "retirée", "affiche": "affiché", "supposees": "supposées", "payees": "payées", "meme": "même",
    "valorise": "valorisé", "cle": "clé", "fidelite": "fidélité", "developpement": "développement", "teste": "testé",
    "evite": "évite", "verifiee": "vérifiée", "activite": "activité", "classee": "classée", "refusee": "refusée",
    "Activite": "Activité", "liberale": "libérale", "ajoutee": "ajoutée", "liberal": "libéral",
    "reglementees": "réglementées", "liberales": "libérales", "majore": "majoré", "reforme": "réforme",
    "abandonnee": "abandonnée", "mediation": "médiation", "facturee": "facturée", "Recette": "Recette",
    "mesuree": "mesurée", "mesures": "mesures", "reformulees": "reformulées", "reformulation": "reformulation",
    "Groq": "Groq", "servies": "servies", "aupres": "auprès", "etudiants": "étudiants", "Prix": "Prix",
    "Charges": "Charges", "ponctuels": "ponctuels", "detail": "détail", "reconduction": "reconduction",
    "Lu": "Lu", "lu": "lu", "lues": "lues", "a jour": "à jour", "telephone": "téléphone", "periode": "période",
    "Inscriptions": "Inscriptions", "inscriptions": "inscriptions", "Perte": "Perte", "renvois": "renvois",
    "jusqu'a": "jusqu'à", "systeme": "système", "deux": "deux", "precise": "précise", "economie": "économie",
    "Marche": "Marché", "marche": "marché", "regles": "règles", "cree": "créé", "termine": "terminé",
    "theorique": "théorique", "lie": "lié", "liees": "liées", "colonne": "colonne", "Indicateur": "Indicateur",
    "Ne": "Ne", "ou": "ou", "Etalement": "Étalement", "categorie": "catégorie", "Categorie": "Catégorie",
    "differe": "diffère", "citee": "citée", "cumule": "cumulé", "depasse": "dépassé", "Resultats": "Résultats",
    "modifiee": "modifiée", "aout": "août", "tranchee": "tranchée", "synthese": "synthèse", "modele": "modèle", "financieres": "financières", "scenario": "scénario",
    "scenarios": "scénarios", "Scenario": "Scénario", "derriere": "derrière", "repartis": "répartis", "dela": "delà",
    "societes": "sociétés", "cumules": "cumulés", "memes": "mêmes", "prerequis": "prérequis", "resumes": "résumés",
    "Recette": "Recette", "frequence": "fréquence", "Duree": "Durée", "credit": "crédit", "Equivalent": "Équivalent",
    "reglementee": "réglementée", "apportes": "apportés", "apportee": "apportée", "charge": "chargé", "coute": "coûte", "ecrites": "écrites", "apercu": "aperçu", "generation": "génération", "lineaire": "linéaire", "categories": "catégories", "electroniques": "électroniques", "visee": "visée", "Recapitulatif": "Récapitulatif", "selectionne": "sélectionné",
}
PHRASES = [(" a partir", " à partir"), (" a saisir", " à saisir"), (" a confirmer", " à confirmer"),
           (" a remesurer", " à remesurer"), (" a ce jour", " à ce jour"), (" a l'ouverture", " à l'ouverture"),
           (" a modifier", " à modifier"), (" a remplacer", " à remplacer"), ("des qu'elles", "dès qu'elles"),
           (" a faire", " à faire"), ("Classement a faire", "Classement à faire"), (" a resultat", " à résultat"),
           (" a la rentree", " à la rentrée"), ("rentree", "rentrée"), (" a 12", " à 12"), (" a 20", " à 20"),
           ("de 1 a 12", "de 1 à 12"), (" a l'annee", " à l'année"), (" a chiffrer", " à chiffrer"),
           ("Choix de l'editeur", "Choix de l'éditeur"), (" a verifier", " à vérifier"), ("A verifier", "À vérifier"),
           (" a l'inscription", " à l'inscription"), ("1 a 12", "1 à 12"), (" a C", " à C"), ("C a N", "C à N"),
           ("est a ", "est à "), (" des que ", " dès que "), (" a demander", " à demander"), (" a la ", " à la "), (" a 7 ", " à 7 ")]


def accentuer(t: str) -> str:
    import re
    for a, b in PHRASES:
        t = t.replace(a, b)
    def rempl(m):
        return MOTS.get(m.group(0), m.group(0))
    # pas de remplacement dans les noms de fichiers ou les adresses (logs/modele.jsonl, api/plans.py)
    return re.sub(r"(?<![/\w.])[A-Za-z']+(?![\w/]|\.\w)", lambda m: rempl(m) if "'" not in m.group(0) else
                  "'".join(MOTS.get(p, p) for p in m.group(0).split("'")), t)


def franciser(wb):
    wb["Hypotheses"].title = "Hypothèses"
    wb["Synthese"].title = "Synthèse"
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                v = c.value
                if not isinstance(v, str):
                    continue
                if v.startswith("="):
                    c.value = v.replace("Hypotheses!", "'Hypothèses'!")
                elif " " in v or not v.startswith("http"):
                    c.value = accentuer(v)


if __name__ == "__main__":
    import json
    import sys

    fiscal = json.loads(Path(sys.argv[1]).read_text()) if len(sys.argv) > 1 else json.loads(
        (Path(__file__).with_name("fiscal.json")).read_text())
    wb = construire(fiscal)
    franciser(wb)
    wb.save(SORTIE)
    print(SORTIE)
