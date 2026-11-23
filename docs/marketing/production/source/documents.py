#!/usr/bin/env python3
"""Documents imprimables du mois 1 : storyboards des 5 videos, kit ambassadeur, flyer, dossier de presse.

HTML puis PDF par Chrome sans interface. Memes polices et memes couleurs que visuels.py.

Usage :
    python3 documents.py            # tout
    python3 documents.py flyer      # un seul document (storyboards, kit, flyer, presse)
    python3 documents.py --html     # HTML seulement
"""
from __future__ import annotations

import sys
from pathlib import Path

from visuels import C, CHROME, SITE, chrome, fleche, logotype, signet, typo

ICI = Path(__file__).resolve().parent
PROD = ICI.parent
PAGES = ICI / "html"
DATE = "23 novembre 2026"
CONTACT = "arthur.champagne@icloud.com"   # adresse des mentions legales (/api/config, lue le 23 novembre 2026)

# Phrases autorisees et interdites, relues le 23 novembre 2026 sur le site en ligne et dans le depot
# (detail et preuves : production/README.md, partie « Ce qui a ete verifie »).
AUTORISEES = [
    "Plus de 900 000 passages officiels : codes, lois, Constitution, Cour de cassation, Conseil d’État, Conseil constitutionnel et traités de l’Union.",
    "Codes et lois mis à jour chaque nuit depuis les données ouvertes de la DILA ; la date de chaque source est affichée.",
    "Chaque réponse cite ses sources, avec le texte officiel à un clic. Une affirmation sans source est retirée.",
    "Vérifiez en un clic qu’un article est en vigueur. Les anciens numéros du Code civil sont reliés aux nouveaux.",
    "Les méthodes de la licence : cas pratique, commentaire d’arrêt, dissertation.",
    "20 matières, de la L1 à la L3, et un niveau d’explication adapté à votre semestre.",
    "Déposez vos cours (PDF, Word, PowerPoint, OpenDocument, RTF, texte, et même un scan ou une photo) et confrontez-les au droit en vigueur.",
    "Questionnaires corrigés avec les sources, et cartes à retourner avec répétition espacée.",
    "Résumés à écouter : une réponse, une fiche ou un cours résumé en 2 à 5 minutes, lu par la voix de votre appareil.",
    "Gratuit avec un compte : 10 questions et 2 questionnaires par jour.",
    "Ouvert dès 15 ans.",
]
INTERDITES = [
    "« Jurisprudence à jour chaque nuit » (vrai pour les codes et lois, pas pour la Cour de cassation ni le Conseil constitutionnel).",
    "« Vos données ne servent jamais à entraîner une IA », « plus respectueux de vos données ».",
    "« Hébergé en France » (non vérifié).",
    "« Sans erreur », « fiable à 100 % », « validé par des enseignants » (aucune notation par un enseignant n’est faite).",
    "« Cartes mentales », « application mobile », « paiement par carte » ou « paiement en ligne » (pas en ligne aujourd’hui).",
    "« Le meilleur », « le seul », « n° 1 », et toute comparaison qui nomme un autre outil.",
    "« Remplace ton manuel », « plus besoin de cours », « avocat dans ta poche », « conseil juridique ».",
    "« Offre limitée » sans limite réelle ; un autre chiffre de passages que « plus de 900 000 ».",
]


# --------------------------------------------------------------------------- styles communs

def base_css(page: str) -> str:
    return f"""
@font-face {{ font-family: Gelasio; src: url(../polices/gelasio-latin-400-normal.woff2); }}
@font-face {{ font-family: Inter; src: url(../polices/inter-latin-400-normal.woff2); font-weight: 400; }}
@font-face {{ font-family: Inter; src: url(../polices/inter-latin-600-normal.woff2); font-weight: 600; }}
@font-face {{ font-family: Inter; src: url(../polices/inter-latin-700-normal.woff2); font-weight: 700; }}
@page {{ size: {page}; margin: 0; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: Inter, sans-serif; color: {C['ink']}; font-size: 10.5pt; line-height: 1.5;
       -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
.feuille {{ position: relative; overflow: hidden; page-break-after: always; background: {C['paper']}; }}
.feuille:last-child {{ page-break-after: auto; }}
h1, h2, h3 {{ font-family: Gelasio, Georgia, serif; font-weight: 400; line-height: 1.15; }}
.surtitre {{ font-size: 8pt; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: {C['forest']}; }}
.carte {{ background: {C['surface']}; border: 1px solid {C['line']}; border-radius: 10px; }}
.encadre {{ background: {C['cream']}; border-left: 3px solid {C['gold']}; padding: 10px 14px; color: {C['ochre']};
           border-radius: 0 8px 8px 0; }}
.puce {{ display: inline-block; background: {C['mint']}; color: {C['forest']}; font-weight: 600; border-radius: 999px;
        padding: 1px 9px; font-size: 8.5pt; }}
.logotype {{ display: inline-flex; align-items: center; gap: .32em; font-family: Gelasio, Georgia, serif; line-height: 1; }}
ul.ok, ul.non {{ list-style: none; display: flex; flex-direction: column; gap: 5px; }}
ul.ok li, ul.non li {{ padding-left: 20px; position: relative; }}
ul.ok li::before {{ content: ""; position: absolute; left: 2px; top: .45em; width: 9px; height: 9px; border-radius: 50%;
                   background: {C['forest']}; }}
ul.non li::before {{ content: ""; position: absolute; left: 2px; top: .62em; width: 10px; height: 2.5px; background: {C['brick']}; }}
table {{ border-collapse: collapse; width: 100%; }}
td, th {{ text-align: left; vertical-align: top; padding: 6px 8px; border-bottom: 1px solid {C['line']}; }}
th {{ font-size: 8pt; text-transform: uppercase; letter-spacing: .08em; color: {C['forest']}; }}
a {{ color: {C['forest']}; }}
sup {{ font-size: .65em; line-height: 0; }}
"""


def ecrire(nom: str, titre: str, page: str, corps: str, css: str = "") -> Path:
    PAGES.mkdir(exist_ok=True)
    chemin = PAGES / f"{nom}.html"
    chemin.write_text(f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>{titre}</title>'
                      f'<style>{base_css(page)}{css}</style></head><body>{corps}</body></html>', encoding="utf-8")
    return chemin


def pdf(source: Path, cible: Path) -> None:
    cible.parent.mkdir(parents=True, exist_ok=True)
    chrome("--no-pdf-header-footer", "--print-to-pdf-no-header", f"--print-to-pdf={cible}", source.as_uri())
    print("pdf", cible.relative_to(PROD), flush=True)


def check(t: int = 12) -> str:
    return (f'<svg width="{t}" height="{t}" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12.5l5 5L20 6.5" '
            f'fill="none" stroke="{C["forest"]}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>')


# --------------------------------------------------------------------------- storyboards

CSS_SB = f"""
.feuille {{ width: 297mm; height: 210mm; padding: 11mm 13mm 9mm; display: flex; flex-direction: column; gap: 4mm; }}
.entete {{ display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 1px solid {C['line']};
          padding-bottom: 3mm; }}
.entete h1 {{ font-size: 20pt; }} .entete .meta {{ font-size: 8.5pt; color: {C['muted']}; text-align: right; line-height: 1.45; }}
.plans {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 4mm; flex: 1; align-content: start; }}
.plan {{ display: grid; grid-template-columns: 30mm 1fr; gap: 3.2mm; padding: 3mm; }}
.cadre {{ width: 30mm; height: 53.3mm; border-radius: 3mm; overflow: hidden; position: relative; background: {C['paper']};
         border: 1px solid {C['line']}; display: flex; flex-direction: column; justify-content: center; padding: 2.2mm;
         gap: 1.5mm; font-size: 6pt; line-height: 1.3; }}
.cadre.sombre {{ background: {C['forest']}; color: {C['surface']}; border-color: {C['forest']}; }}
.cadre .gros {{ font-family: Gelasio, Georgia, serif; font-size: 10.5pt; line-height: 1.12; }}
.cadre .moyen {{ font-family: Gelasio, Georgia, serif; font-size: 8pt; line-height: 1.15; }}
.cadre svg.illu {{ width: 100%; height: auto; }}
.cadre .sous {{ position: absolute; left: 2mm; right: 2mm; bottom: 4mm; background: rgba(32,39,36,.78); color: #fff;
               font-size: 4.8pt; padding: .8mm 1.2mm; border-radius: 1mm; text-align: center; }}
.cadre .tel {{ background: {C['surface']}; border: 1px solid {C['line']}; border-radius: 1.6mm; padding: 1.4mm; display: flex;
              flex-direction: column; gap: 1mm; font-size: 4.8pt; }}
.cadre .bulle {{ align-self: flex-end; background: {C['mint']}; border-radius: 1.2mm; padding: .8mm 1.2mm; max-width: 85%; }}
.cadre .src {{ color: {C['forest']}; font-weight: 600; }}
.cadre .l {{ height: 1.1mm; background: {C['line']}; border-radius: 1mm; }}
.info {{ display: flex; flex-direction: column; gap: 1.3mm; font-size: 8pt; line-height: 1.38; }}
.info .t {{ font-weight: 700; color: {C['forest']}; font-size: 8.5pt; }}
.info .e {{ font-weight: 600; }}
.info .lab {{ font-size: 6.5pt; text-transform: uppercase; letter-spacing: .08em; color: {C['muted']}; font-weight: 700; }}
.info .n {{ color: {C['ochre']}; }}
.bas {{ display: grid; grid-template-columns: 1.1fr 1fr; gap: 6mm; font-size: 8.5pt; }}
.bas h3 {{ font-size: 11pt; margin-bottom: 1.5mm; }}
.annexe {{ display: grid; grid-template-columns: .82fr 1.18fr; gap: 6mm; font-size: 8.6pt; flex: 1; }}
.annexe h2 {{ font-size: 14pt; margin-bottom: 2mm; }}
.annexe table {{ table-layout: fixed; }}
.annexe td, .annexe th {{ padding: 2.5px 4px; font-size: 7pt; line-height: 1.32; overflow-wrap: anywhere; }}
.annexe .annexe-droite {{ display: flex; flex-direction: column; }}
"""


def cadre(contenu: str, sombre: bool = False, sous: str | None = None) -> str:
    s = f'<div class="sous">{typo(sous)}</div>' if sous else ""
    return f'<div class="cadre{" sombre" if sombre else ""}">{contenu}{s}</div>'


def c_titre(t: str, sombre: bool = True, petit: str | None = None) -> str:
    return cadre(f'<div class="gros">{typo(t)}</div>' + (f'<div>{typo(petit)}</div>' if petit else ""), sombre)


def c_article(ref: str, texte: str) -> str:
    return cadre(f'<div class="surtitre" style="font-size:5pt">Majeure</div><div class="tel"><span class="src">§ {typo(ref)}</span>'
                 f'<span>« {typo(texte)} »</span></div>', sous="Il faut une faute, un dommage, un lien de causalité.")


def c_coches(lignes: list[str]) -> str:
    return cadre('<div class="moyen">Mineure</div>' + "".join(
        f'<div style="display:flex;gap:1.2mm;align-items:center">{check(9)}<span>{typo(x)}</span></div>' for x in lignes))


def c_ecran(question: str, lignes: int = 3, source: str | None = None, note: str | None = None) -> str:
    corps = (f'<div class="tel">{logotype(7)}<div class="bulle">{typo(question)}</div>' +
             '<div class="l"></div>' * lignes + (f'<span class="src">[1] {typo(source)}</span>' if source else "") + "</div>")
    return cadre(corps + (f'<div style="font-size:5pt;color:{C["muted"]}">{typo(note)}</div>' if note else ""))


def c_panneau(ref: str) -> str:
    return cadre(f'<div class="tel"><span class="src">§ {typo(ref)}</span><div class="l"></div><div class="l"></div>'
                 f'<div class="l" style="width:70%"></div><span>En vigueur depuis le 1<sup>er</sup> octobre 2016</span>'
                 f'<span class="puce" style="font-size:4.6pt;align-self:flex-start">Vérifier la version en vigueur</span></div>')


def c_barre() -> str:
    return cadre(f'<div class="moyen">Erreur 1</div><div style="display:flex;align-items:center;gap:1.5mm;'
                 f'font-family:Gelasio,serif;font-size:13pt"><s style="color:{C["brick"]}">1382</s>'
                 f'<span style="color:{C["forest"]};border:1.2px solid {C["forest"]};border-radius:50%;padding:0 1.2mm">1240</span></div>')


def c_colonnes() -> str:
    return cadre('<div class="moyen">Erreur 3</div><div style="display:grid;grid-template-columns:1fr 1fr;gap:1mm">'
                 f'<div class="tel"><b style="color:{C["brick"]}">Raconter</b><div class="l"></div><div class="l"></div></div>'
                 f'<div class="tel"><b style="color:{C["forest"]}">Analyser</b><span>sens</span><span>valeur</span><span>portée</span></div></div>')


def c_majeure() -> str:
    return cadre('<div class="moyen">Erreur 2</div>'
                 f'<div class="tel"><s style="color:{C["brick"]}">La faute oblige à réparer.</s></div>'
                 f'<div class="tel">La faute oblige à réparer <span class="src">(C. civ., art. 1240)</span>.</div>')


def c_fin(texte: str) -> str:
    return cadre(f'{signet(34, True)}<div class="moyen">{typo(texte)}</div><div style="font-weight:600">{SITE}</div>',
                 sombre=True)


def c_quiz(etat: str) -> str:
    opts = ["Dol", "Erreur", "Violence"]
    lignes = "".join(f'<div class="tel" style="padding:.9mm 1.2mm;flex-direction:row;justify-content:space-between">{o}'
                     f'{check(7) if (etat == "corr" and o == "Dol") else ""}</div>' for o in opts)
    extra = (f'<div class="tel"><span class="src">§ Code civil, art. 1137</span><span>Correction avec la source</span></div>'
             if etat == "corr" else "")
    return cadre(f'<div style="font-size:5pt;color:{C["muted"]}">Droit des contrats · QCM · 2 / 5</div>'
                 f'<div class="moyen">Manœuvres pour obtenir le consentement ?</div>{lignes}{extra}')


def c_reglages() -> str:
    return cadre('<div class="tel">' + logotype(7) + '<b>Nouveau questionnaire</b>'
                 '<span>Matière : Droit des contrats</span><span>Thème : vices du consentement</span>'
                 '<span>Format : QCM · 5 questions</span>'
                 f'<span class="puce" style="font-size:4.6pt;align-self:flex-start">Générer le questionnaire</span></div>')


ILLU_PISCINE = f"""<svg class="illu" viewBox="0 0 100 120" aria-hidden="true">
<rect x="0" y="70" width="100" height="50" fill="{C['mint']}"/>
<path d="M6 84 q8 -4 16 0 t16 0 t16 0 t16 0 t16 0 t16 0" fill="none" stroke="{C['hover_line'] if 'hover_line' in C else '#9eafa3'}" stroke-width="1.4"/>
<path d="M6 98 q8 -4 16 0 t16 0 t16 0 t16 0 t16 0 t16 0" fill="none" stroke="#9eafa3" stroke-width="1.4"/>
<rect x="0" y="64" width="100" height="6" fill="{C['line']}"/>
<circle cx="30" cy="24" r="7" fill="{C['forest']}"/><rect x="23" y="33" width="14" height="31" rx="6" fill="{C['forest']}"/>
<g transform="rotate(28 62 50)"><circle cx="62" cy="26" r="7" fill="{C['gold']}"/><rect x="55" y="35" width="14" height="31" rx="6" fill="{C['gold']}"/></g>
<path d="M39 42 L52 44" stroke="{C['forest']}" stroke-width="3" stroke-linecap="round"/></svg>"""

ILLU_WAGONNET = f"""<svg class="illu" viewBox="0 0 100 80" aria-hidden="true">
<line x1="0" y1="66" x2="100" y2="66" stroke="{C['ink']}" stroke-width="2"/>
<line x1="0" y1="72" x2="100" y2="72" stroke="{C['ink']}" stroke-width="1" stroke-dasharray="3 4"/>
<path d="M22 34 H78 L72 56 H28 Z" fill="{C['ochre']}"/><circle cx="36" cy="60" r="6" fill="{C['ink']}"/>
<circle cx="64" cy="60" r="6" fill="{C['ink']}"/><rect x="20" y="30" width="60" height="5" fill="{C['gold']}"/></svg>"""


def c_illu(svg: str, texte: str, sous: str | None = None) -> str:
    return cadre(f'{svg}<div class="moyen">{typo(texte)}</div>', sous=sous)


MUSIQUE = [
    # (bibliotheque, morceau, licence, attribution, reserve)
    ("TikTok : bibliothèque musicale commerciale (CML)", "Au choix dans l’application, compte professionnel",
     "Usage commercial et publicitaire permis sur TikTok seulement", "Non demandée",
     "Pas de reprise de la vidéo avec ce son sur Instagram ou YouTube."),
    ("Instagram : Meta Sound Collection", "Au choix dans l’application",
     "Usage commercial permis sur les produits Meta seulement", "Non demandée",
     "Conditions acceptées avec le compte ; pas d’usage hors Meta."),
    ("YouTube : bibliothèque audio de YouTube Studio", "Au choix, filtre « Attribution non requise »",
     "Licence YouTube standard : à réserver à YouTube", "Selon le titre (CC BY : nom dans la description)",
     "Titres non réclamés par Content ID."),
    ("Incompetech (Kevin MacLeod)", "« Light Thought var 1 » (2:42) ou « Water Droplets on the River » (1:45)",
     "CC BY 4.0, usage commercial avec crédit", "\"Titre\" Kevin MacLeod (incompetech.com) / Licensed under Creative Commons: By Attribution 4.0 License / http://creativecommons.org/licenses/by/4.0/",
     "Crédit obligatoire dans la légende sur chaque réseau."),
    ("Free Music Archive", "« Portage », 1000 Handz (0:45) ; « Revolving Evolving », Ketsa (2:52)",
     "CC BY 4.0 (vérifier sur la page du morceau au téléchargement)", "« 1000Handz.com » ; « Ketsa.uk », et la licence",
     "Écarter tout morceau NC ou ND : la synchronisation sur une vidéo est une œuvre dérivée."),
    ("Pixabay Music", "« Calm Piano », AtlasAudio (1:22) ; « Soft Piano », MondaMusic (1:59)",
     "Pixabay Content License, usage commercial permis", "Facultative",
     "Morceaux enregistrés à Content ID : garder le certificat de téléchargement pour contester une réclamation."),
]

VIDEOS = [
    {"id": "V1", "post": "P3 (1er décembre)", "titre": "Cas pratique résolu en 30 secondes : la piscine", "duree": "30 s",
     "objectif": "Montrer la méthode du cas pratique sur un cas simple et l’article qui fonde la règle.",
     "musique": "Incompetech « Water Droplets on the River » (CC BY 4.0, crédit en légende), ou un son de la bibliothèque de chaque réseau.",
     "sources": "Code civil, article 1240 (LEGIARTI000032041571), en vigueur depuis le 1er octobre 2016.",
     "plans": [
         ("0-3 s", c_titre("Cas pratique en 30 secondes.", petit="Prêt ?"), "Cas pratique en 30 secondes. Prêt ?",
          "Cas pratique en 30 secondes. Prêt ?", "Texte plein écran, apparition en fondu court."),
         ("3-8 s", c_illu(ILLU_PISCINE, "Hugo pousse Sami pour rire."), "Hugo doit-il réparer ?",
          "Pour rire, Hugo pousse Sami dans la piscine. Sami se casse le poignet. Hugo doit-il réparer ?",
          "Illustration sans visage (personnages stylisés). Pas de personne réelle filmée."),
         ("8-12 s", c_titre("Problème de droit", petit="La personne qui cause un dommage par sa faute doit-elle le réparer ?"),
          "Problème de droit", "La personne qui cause un dommage par sa faute doit-elle le réparer ?", ""),
         ("12-18 s", c_article("Code civil, article 1240", "Tout fait quelconque de l’homme, qui cause à autrui un dommage, oblige celui par la faute duquel il est arrivé à le réparer."),
          "Majeure : article 1240 du Code civil", "Majeure : article 1240 du Code civil. Tout fait de l’homme qui cause à autrui un dommage oblige celui par la faute duquel il est arrivé à le réparer. Il faut une faute, un dommage, un lien de causalité.",
          "Citer le texte exact à l’écran ; la voix peut l’abréger."),
         ("18-26 s", c_coches(["Pousser, même pour rire : faute", "Poignet cassé : dommage", "Sans la poussée, pas de chute : lien de causalité"]),
          "Faute · dommage · lien de causalité", "Mineure : pousser quelqu’un, même pour rire, est une faute. Le poignet cassé est un dommage. Sans la poussée, pas de chute : lien de causalité.",
          "Les trois coches apparaissent une à une, sur le rythme de la voix."),
         ("26-30 s", c_fin("Hugo doit réparer."), "Conclusion : Hugo doit réparer. Lien en bio",
          "Hugo doit réparer le dommage de Sami. Fais le tien avec Lexia : lien en bio.",
          "Ne pas ajouter d’autre fondement en 30 s ; répondre en commentaire (faute de la victime, par exemple)."),
     ]},
    {"id": "V2", "post": "P9 (8 décembre)", "titre": "3 erreurs qui coûtent des points en L1", "duree": "45 s",
     "objectif": "Conseils de méthode courants, présentés comme tels, et rappel des anciens numéros.",
     "musique": "Free Music Archive « Portage », 1000 Handz (0:45, CC BY 4.0, crédit « 1000Handz.com »), ou un son de la bibliothèque de chaque réseau.",
     "sources": "Code civil, articles 1240 et 1382 en vigueur. Les erreurs 2 et 3 sont des conseils de méthode, pas des règles de droit.",
     "plans": [
         ("0-3 s", c_titre("3 erreurs qui coûtent des points en L1"), "3 erreurs qui coûtent des points en L1",
          "3 erreurs qui coûtent des points en L1.", "Accroche lue en moins de 2 s."),
         ("3-15 s", c_barre(), "Erreur 1 : citer un ancien numéro",
          "Citer un ancien numéro. Depuis 2016, la responsabilité pour faute, c’est l’article 1240, plus 1382. L’article 1382 actuel parle d’autre chose : des présomptions.",
          "1382 barré en brique, 1240 entouré en vert."),
         ("15-27 s", c_majeure(), "Erreur 2 : une majeure sans source",
          "Une majeure sans source. Dans un cas pratique, la règle s’énonce avec son article. Sans texte, ce n’est qu’une opinion.",
          "Même phrase, d’abord sans article (barrée), puis avec."),
         ("27-40 s", c_colonnes(), "Erreur 3 : raconter l’arrêt au lieu de l’analyser",
          "Raconter l’arrêt au lieu de l’analyser. Dans un commentaire, on explique le sens, la valeur et la portée de la solution, pas seulement ce qui s’est passé.",
          ""),
         ("40-45 s", c_fin("Suis toujours la méthode de ton chargé de TD."), "Lien en bio",
          "Lexia cite l’article en vigueur à chaque réponse. Lien en bio. Et suis toujours la méthode de ton chargé de TD.", ""),
     ]},
    {"id": "V3", "post": "P5 (3 décembre)", "titre": "Le piège du 1382 (démonstration)", "duree": "30 s",
     "objectif": "Démontrer la correspondance des anciens numéros, à l’écran, sans montage trompeur.",
     "musique": "Incompetech « Light Thought var 1 » (CC BY 4.0, crédit en légende), très bas sous la voix.",
     "sources": "Code civil, article 1382 en vigueur (LEGIARTI000032042379) et article 1240 ; correspondance D53 (api/concordance.py).",
     "plans": [
         ("0-3 s", c_titre("Tu cites encore 1382 ?"), "Tu cites encore 1382 ?", "Tu cites encore 1382 ?", ""),
         ("3-10 s", c_panneau("Code civil, article 1382"), "L’article 1382 aujourd’hui : les présomptions",
          "Voici l’article 1382 aujourd’hui : il parle des présomptions laissées à l’appréciation du juge. Rien à voir avec la responsabilité.",
          "Capture de la page Légifrance de l’article 1382 en vigueur, avec son adresse visible."),
         ("10-22 s", c_ecran("Article 1382 : faute et dommage", 4, "Code civil, article 1240", "Compte de test"),
          "Lexia reconnaît l’ancien numéro", "Dans Lexia, l’ancien numéro est reconnu : la réponse t’indique que la règle est aujourd’hui à l’article 1240.",
          "Enregistrement d’écran réel, compte de test. Poser la question avant de filmer ; ne filmer que si la correspondance s’affiche."),
         ("22-28 s", c_panneau("Code civil, article 1240"), "Un clic : le texte officiel daté",
          "Un clic : le texte officiel, et sa date de vigueur.", "Clic sur la citation [1], panneau de la source."),
         ("28-30 s", c_fin("Gratuit avec un compte."), "Gratuit avec un compte · lien en bio",
          "Gratuit avec un compte. Lien en bio.", ""),
     ]},
    {"id": "V4", "post": "P7 (5 décembre)", "titre": "Fiche d’arrêt en 45 secondes : Blanco", "duree": "45 s",
     "objectif": "Fiche d’arrêt d’un grand arrêt de L2, reconnu par son nom dans Lexia.",
     "musique": "Pixabay « Calm Piano », AtlasAudio (Pixabay Content License, Content ID : garder le certificat), ou un son de la bibliothèque de chaque réseau.",
     "sources": "Tribunal des conflits, 8 février 1873, Blanco (CETATEXT000007605886, api/grands_arrets.py). Relire les faits sur la décision et une source académique ; supprimer tout détail non confirmé.",
     "plans": [
         ("0-3 s", c_titre("Le premier grand arrêt du droit administratif"), "Le premier grand arrêt du droit administratif",
          "Le premier grand arrêt du droit administratif.", ""),
         ("3-12 s", c_illu(ILLU_WAGONNET, "Bordeaux, 1871"), "Faits",
          "Bordeaux, 1871. La jeune Agnès Blanco est renversée et blessée par un wagonnet d’une manufacture de tabacs, gérée par l’État. Son père demande réparation.",
          "Illustration d’un wagonnet, aucune personne représentée. Faits à confirmer avant tournage."),
         ("12-20 s", c_titre("Problème", sombre=False, petit="Quel juge, et quelles règles, quand un service public cause un dommage ?"),
          "Problème", "Quel juge est compétent, et quelles règles s’appliquent, quand un service public cause un dommage ?", ""),
         ("20-35 s", c_titre("Solution", petit="Tribunal des conflits, 8 février 1873"), "Solution : des règles spéciales, le juge administratif",
          "Tribunal des conflits, 8 février 1873. La responsabilité de l’État pour les dommages causés par ses services publics ne relève pas des règles du Code civil : elle a des règles spéciales. C’est le juge administratif qui est compétent.", ""),
         ("35-42 s", c_titre("Portée", sombre=False, petit="Compétence administrative et droit propre de la responsabilité administrative."),
          "Portée", "L’arrêt lie la compétence administrative et l’existence d’un droit propre de la responsabilité administrative.", ""),
         ("42-45 s", c_fin("Demande « arrêt Blanco » à Lexia."), "Demande « arrêt Blanco »",
          "Demande « arrêt Blanco » à Lexia : la décision est reconnue par son nom.",
          "Vérifier avant de filmer que la question « arrêt Blanco » cite bien la décision."),
     ]},
    {"id": "V5", "post": "P15 (14 décembre)", "titre": "Un quiz en 2 minutes (démonstration)", "duree": "55 s",
     "objectif": "Montrer un questionnaire réel, du réglage à la correction sourcée.",
     "musique": "Free Music Archive « Revolving Evolving », Ketsa (CC BY 4.0, crédit « Ketsa.uk »), ou un son de la bibliothèque de chaque réseau.",
     "sources": "Questionnaire généré en vrai sur le compte de test (api/quiz.py) ; relire chaque question et chaque correction.",
     "plans": [
         ("0-3 s", c_titre("Réviser en 2 minutes ?"), "Réviser en 2 minutes ?", "Réviser en 2 minutes ?", ""),
         ("3-12 s", c_reglages(), "Matière · thème · format",
          "Tu choisis la matière, le thème, le format : QCM, vrai ou faux ou questions ouvertes.",
          "Enregistrement d’écran réel, compte de test."),
         ("12-35 s", c_quiz("rep"), "Tu réponds.", "Tu réponds.",
          "Réponses en accéléré (x2), sans couper une question."),
         ("35-50 s", c_quiz("corr"), "La correction cite les sources",
          "La correction cite les sources : tu sais pourquoi tu t’es trompé. Et tu peux ajouter les questions à tes cartes à réviser.",
          "Montrer le bouton « Ajouter aux cartes à réviser » (en ligne, D104)."),
         ("50-55 s", c_fin("2 questionnaires par jour avec le compte gratuit."), "2 questionnaires par jour · lien en bio",
          "2 questionnaires par jour avec le compte gratuit. Lien en bio.",
          "Si une erreur apparaît dans le questionnaire : refaire, ne pas couper au montage. Garder l’enregistrement brut."),
     ]},
]


def storyboard(v: dict) -> str:
    entete = (f'<div class="entete"><div><p class="surtitre">Storyboard {v["id"]} · {typo(v["post"])}</p>'
              f'<h1>{typo(v["titre"])}</h1></div><div class="meta">Durée : {v["duree"]} · vertical 9:16, 1080 × 1920<br>'
              f'TikTok, Instagram Reels, YouTube Shorts<br>Version du {DATE}</div></div>')
    plans = ""
    for t, cad, ecran, voix, note in v["plans"]:
        plans += (f'<div class="plan carte">{cad}<div class="info"><span class="t">{t}</span>'
                  f'<span class="lab">À l’écran</span><span class="e">{typo(ecran)}</span>'
                  f'<span class="lab">Voix off</span><span>{typo(voix)}</span>'
                  + (f'<span class="lab">Note</span><span class="n">{typo(note)}</span>' if note else "") + "</div></div>")
    bas = (f'<div class="bas"><div><h3>Objectif et sources</h3><p>{typo(v["objectif"])}</p><p>{typo(v["sources"])}</p></div>'
           f'<div><h3>Musique proposée</h3><p>{typo(v["musique"])}</p><p>Licences et crédits : dernière page.</p></div></div>')
    return f'<section class="feuille">{entete}<div class="plans">{plans}</div>{bas}</section>'


def annexe_tournage() -> str:
    lignes = "".join(f"<tr><td><b>{typo(a)}</b></td><td>{typo(b)}</td><td>{typo(c)}</td><td>{typo(d)}</td><td>{typo(e)}</td></tr>"
                     for a, b, c, d, e in MUSIQUE)
    return f"""<section class="feuille"><div class="entete"><div><p class="surtitre">Storyboards · annexe</p>
<h1>Tournage, sous-titres et musique</h1></div><div class="meta">Licences lues sur les pages officielles le {DATE}<br>À revérifier au téléchargement de chaque morceau</div></div>
<div class="annexe"><div><h2>Avant de tourner</h2><ul class="ok">
<li>{typo("Compte de test uniquement, sans données réelles d’étudiant ; écran montré tel qu’il est, sans retouche qui ferait croire à une fonction absente.")}</li>
<li>{typo("Poser chaque question de démonstration dans Lexia le jour même ; ne filmer que si la réponse montre bien ce que dit la voix.")}</li>
<li>{typo("Aucun mineur à l’image, aucun visage ni voix générés par IA ; la voix dit « la réponse de Lexia ».")}</li>
<li>{typo("Voix de l’éditeur. Si un ambassadeur filme : mention « Publicité » dès la première seconde, dans la légende, et l’option « partenariat rémunéré » de la plateforme.")}</li>
<li>{typo("Sous-titres incrustés (beaucoup regardent sans le son) ; première phrase à l’écran dans les deux premières secondes.")}</li>
<li>{typo("Zones sûres : rien d’important à moins de 250 px du haut ni 400 px du bas, ni dans les 120 px de droite (boutons des applications).")}</li>
<li>{typo("Export : 1080 × 1920, 30 images par seconde, H.264, son AAC. Couvertures prêtes dans visuels/ (P3, P5, P7, P9, P15).")}</li>
<li>{typo("Tourner par lots de 4 à 6 vidéos ; garder les enregistrements bruts.")}</li></ul>
<h2 style="margin-top:4mm">Conseil pour la musique</h2>
<p>{typo("Le plus sûr : exporter chaque vidéo sans musique, puis ajouter un son de la bibliothèque de chaque réseau au moment de publier (TikTok, Instagram, YouTube). Ces bibliothèques ne valent que sur leur propre plateforme. Pour une seule version avec musique intégrée, publiée partout, prendre un morceau sous CC BY 4.0 (Incompetech ou Free Music Archive) et mettre le crédit dans chaque légende.")}</p></div>
<div><h2>Bibliothèques gratuites et licences</h2><table><colgroup><col style="width:17%"><col style="width:22%"><col style="width:19%"><col style="width:23%"><col style="width:19%"></colgroup><tr><th>Bibliothèque</th><th>Morceaux</th><th>Licence</th><th>Crédit</th><th>Réserve</th></tr>{lignes}</table></div></div>
<p style="font-size:7.2pt;color:{C['muted']}">{typo("Pages lues : ads.tiktok.com/help/article?aid=10005905 et conditions CML ; facebook.com/sound/collection/terms ; support.google.com/youtube/answer/3376882 ; pixabay.com/service/license-summary ; incompetech.com/music/royalty-free/licenses ; freemusicarchive.org/License_Guide. Relevé factuel, pas un avis juridique.")}</p></section>"""


# --------------------------------------------------------------------------- kit ambassadeur (A4 portrait)

CSS_A4 = f"""
.feuille {{ width: 210mm; height: 297mm; padding: 18mm 18mm 14mm; display: flex; flex-direction: column; gap: 5mm; }}
.feuille.sombre {{ background: {C['forest']}; color: {C['surface']}; justify-content: space-between; }}
.feuille.sombre .surtitre {{ color: #cfe0d6; }}
.tete {{ display: flex; justify-content: space-between; align-items: center; font-size: 8pt; color: {C['muted']};
        border-bottom: 1px solid {C['line']}; padding-bottom: 3mm; }}
h1 {{ font-size: 34pt; }} h2 {{ font-size: 20pt; }} h3 {{ font-size: 13pt; margin-bottom: 1.5mm; }}
.deux {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6mm; }}
.bloc {{ padding: 5mm 6mm; }}
.pied {{ margin-top: auto; font-size: 7.5pt; color: {C['muted']}; display: flex; justify-content: space-between; gap: 6mm; }}
.pied span:last-child {{ white-space: nowrap; }}
.deux .bloc {{ font-size: 9pt; line-height: 1.42; }}
.deux ul.ok, .deux ul.non {{ gap: 3.5px; }}
.sombre .pied {{ color: #cfe0d6; }}
.mention {{ background: {C['surface']}; border: 2px solid {C['ink']}; padding: 4mm 5mm; font-weight: 700; font-size: 12pt; }}
ol.regles {{ padding-left: 6mm; display: flex; flex-direction: column; gap: 2.5mm; }}
ol.regles li b {{ color: {C['forest']}; }}
.captures {{ display: grid; grid-template-columns: 1fr 1fr; gap: 4mm; }}
.captures img {{ width: 100%; border: 1px solid {C['line']}; border-radius: 6px; display: block; }}
.legende {{ font-size: 7.5pt; color: {C['muted']}; margin-top: 1mm; }}
"""


def tete(titre: str, n: int, total: int) -> str:
    return f'<div class="tete">{logotype(14)}<span>{typo(titre)} · {n} / {total}</span></div>'


def pied(texte: str) -> str:
    return f'<div class="pied"><span>{typo(texte)}</span><span>{SITE}</span></div>'


def kit() -> str:
    T = "Kit ambassadeur"
    p1 = f"""<section class="feuille sombre"><div>{logotype(28, True)}</div>
<div><p class="surtitre">Ambassadeurs · facultés de droit</p><h1 style="margin:4mm 0 6mm">Kit ambassadeur Lexia</h1>
<p style="font-size:14pt;line-height:1.45;max-width:150mm">{typo("Pour les étudiantes et étudiants majeurs en licence ou en master de droit qui présentent Lexia à leur promotion, dans la transparence.")}</p></div>
<div style="font-size:9pt;line-height:1.6">{typo(f"Version de travail du {DATE}. À remettre seulement avec le contrat d’ambassadeur signé (loi n° 2023-451 du 9 juin 2023, article 8).")}<br>
{typo(f"Contact : {CONTACT}")}</div></section>"""

    autor = "".join(f"<li>{typo(x)}</li>" for x in AUTORISEES)
    inter = "".join(f"<li>{typo(x)}</li>" for x in INTERDITES)
    p2 = f"""<section class="feuille">{tete(T, 2, 5)}<p class="surtitre">Lexia en bref</p>
<h2>{typo("L’espace d’étude du droit qui cite ses sources.")}</h2>
<p>{typo("Lexia répond aux questions de cours des étudiants de licence à partir des textes officiels, applique les méthodes de la licence et montre d’où vient chaque phrase. C’est un outil d’étude, pas un avis juridique.")}</p>
<div class="deux"><div class="carte bloc"><h3>{typo("Ce que tu peux dire")}</h3><ul class="ok">{autor}</ul></div>
<div class="carte bloc"><h3>{typo("Ce que tu ne dis jamais")}</h3><ul class="non">{inter}</ul>
<p class="encadre" style="margin-top:4mm">{typo("Dans le doute, ne le dis pas et pose la question avant de publier. Une phrase fausse sur le service est une pratique commerciale trompeuse (Code de la consommation, article L. 121-2).")}</p></div></div>
{pied("Phrases vérifiées sur le site et le dépôt le " + DATE + " ; la liste à jour fait foi.")}</section>"""

    p3 = f"""<section class="feuille">{tete(T, 3, 5)}<p class="surtitre">Le rôle</p><h2>{typo("Ce qu’on te propose, ce qu’on te demande")}</h2>
<div class="deux"><div class="carte bloc"><h3>Ce qu’on te propose</h3><ul class="ok">
<li>{typo("La formule Intensif offerte tant que tu es ambassadeur (valeur affichée : 9,99 € par mois). C’est un avantage en nature : il fait de toi une personne qui promeut Lexia « à titre onéreux » (loi n° 2023-451, article 1er), d’où les règles de la page suivante.")}</li>
<li>{typo("Un accès anticipé aux nouveautés et un lien direct avec l’éditeur pour remonter les problèmes.")}</li>
<li>{typo("Plus tard, si l’éditeur le décide : une rémunération fixe par mois ou par atelier, écrite dans un avenant. Pas de commission par inscription.")}</li></ul></div>
<div class="carte bloc"><h3>Ce qu’on te demande</h3><ul class="ok">
<li>{typo("Deux publications ou stories par mois au plus, sur tes propres comptes.")}</li>
<li>{typo("Une présentation de Lexia par semestre à ton association ou à ton groupe de TD, avec leur accord.")}</li>
<li>{typo("Des retours honnêtes, y compris négatifs, par message à l’éditeur.")}</li>
<li>{typo("Envoyer tes premiers contenus avant publication : l’annonceur est solidairement responsable des dommages causés aux tiers (loi n° 2023-451, article 8, III).")}</li></ul></div></div>
<div class="carte bloc"><h3>{typo("Qui peut être ambassadeur")}</h3><p>{typo("Étudiantes et étudiants en licence ou en master de droit, majeurs. Un ou deux par faculté au départ, actifs dans une association, un groupe de TD ou un serveur de promo. Pas de nombre d’abonnés minimal : on cherche des personnes crédibles auprès de leur promotion.")}</p>
<p class="legende">{typo("Pourquoi majeurs : un mineur ne conclut seul que des actes courants (Code civil, articles 1146 et 1148).")}</p></div>
<div class="carte bloc"><h3>{typo("Trois idées de vidéos, à refaire avec ta voix")}</h3><ul class="ok">
<li><b>{typo("Cas pratique en 30 s")}</b> {typo("(storyboard V1) : un cas simple, la règle avec son article, les conditions une à une.")}</li>
<li><b>{typo("3 erreurs en L1")}</b> {typo("(storyboard V2) : ancien numéro, majeure sans source, raconter au lieu d’analyser.")}</li>
<li><b>{typo("Un quiz en 2 minutes")}</b> {typo("(storyboard V5) : un questionnaire réel, corrigé avec les sources.")}</li></ul>
<p class="legende">{typo("Toujours : mention « Publicité » dès la première seconde. Démonstrations filmées sur ton propre compte, sans données d’autres étudiants.")}</p></div>
{pied("Les storyboards complets sont remis avec ce kit.")}</section>"""

    p4 = f"""<section class="feuille">{tete(T, 4, 5)}<p class="surtitre">Obligatoire</p><h2>{typo("Les sept règles, reprises dans ton contrat")}</h2>
<ol class="regles">
<li><b>{typo("Mention « Publicité » ou « Collaboration commerciale »")}</b> {typo("sur chaque contenu qui parle de Lexia : claire, lisible, sur tout support. Au début de la vidéo, dans la légende, et avec l’option de la plateforme qui signale un partenariat rémunéré. Base : loi n° 2023-451, article 5-2 ; sans mention, c’est une pratique commerciale trompeuse (Code de la consommation, article L. 121-3).")}</li>
<li><b>{typo("Jamais te présenter comme un simple utilisateur")}</b> {typo("ni publier d’avis « spontané » : c’est une pratique réputée trompeuse (Code de la consommation, article L. 121-4, 21° et 28°).")}</li>
<li><b>{typo("Uniquement les phrases autorisées")}</b> {typo("(page 2). Rien sur les données, l’hébergement, une validation par des enseignants, des fonctions non publiées, ni comparaison avec un autre outil.")}</li>
<li><b>{typo("Pas d’image retouchée ni générée par IA")}</b> {typo("d’un visage ou d’une silhouette ; sinon « Images retouchées » ou « Images virtuelles » (loi n° 2023-451, article 5).")}</li>
<li><b>{typo("Pas de conseil juridique personnel")}</b> {typo("en commentaire ou en message : renvoyer vers un professionnel du droit ou un point-justice.")}</li>
<li><b>{typo("Pas de démarchage")}</b> {typo(": pas de messages privés en masse, pas de listes d’adresses de la promotion sans l’accord des personnes.")}</li>
<li><b>{typo("Respect de la faculté et de l’association")}</b> {typo(": pas de distribution dans les locaux ni d’envoi sur une liste de diffusion universitaire sans autorisation.")}</li></ol>
<h3 style="margin-top:3mm">{typo("Les mentions à copier")}</h3>
<div class="mention">{typo("Publicité : collaboration commerciale avec Lexia (formule offerte).")}</div>
<p>{typo("Dans la vidéo, au début, en grand : utilise le bandeau prêt à superposer (visuels/AMB, fond transparent, 1080 × 1920). Sur Instagram, active « Partenariat rémunéré » ; sur TikTok, le réglage de divulgation du contenu commercial ; sur YouTube, « Inclut une promotion rémunérée » (intitulés à vérifier dans l’application, ils changent).")}</p>
<p class="encadre">{typo("Le contrat est écrit et signé avant toute publication : identité et résidence fiscale des parties, missions, contrepartie et valeur de l’avantage, propriété des contenus, droit français. Il prend fin à tout moment avec un préavis court ; la formule offerte s’arrête avec lui.")}</p>
{pied("Règles fondées sur la loi n° 2023-451 du 9 juin 2023 et le Code de la consommation, lus le 19 et le 20 novembre 2026.")}</section>"""

    caps = PROD / "presse" / "captures"
    p5 = f"""<section class="feuille">{tete(T, 5, 5)}<p class="surtitre">Candidater, poser une question</p><h2>{typo("Candidature et contact")}</h2>
<div class="captures"><div><img src="{(caps / 'accueil.png').as_uri()}"><p class="legende">{typo("Page d’accueil, " + DATE)}</p></div>
<div><img src="{(caps / 'tarifs.png').as_uri()}"><p class="legende">{typo("Formules affichées, " + DATE)}</p></div></div>
<div class="carte bloc"><h3>Candidater</h3><p>{typo(f"Écris à {CONTACT} avec : prénom, nom, faculté et année, date de naissance (pour vérifier la majorité), comptes de réseaux sociaux (facultatif) et ta motivation en cinq lignes.")}</p>
<p class="legende" style="margin-top:2mm">{typo("Données utilisées par l’éditeur seul, pour choisir les ambassadeurs (mesures précontractuelles). Conservation : 12 mois après la sélection si la candidature n’est pas retenue ; durée du contrat et délais de prescription si elle l’est. Tu peux demander l’accès, la rectification ou l’effacement, t’opposer, et saisir la CNIL. Éditeur : Arthur Champagne-Forterre, entrepreneur individuel, nom commercial Axion Studio, 5 allée des Pommiers, 95680 Montlignon.")}</p></div>
<div class="carte bloc"><h3>{typo("Une question avant de publier ?")}</h3><p>{typo(f"Écris à {CONTACT}. Réponse avant publication : si tu n’as pas de réponse, ne publie pas le contenu concerné.")}</p></div>
{pied("Captures du site en ligne, pages publiques.")}</section>"""
    return p1 + p2 + p3 + p4 + p5


# --------------------------------------------------------------------------- flyer (A5 portrait)

CSS_FLYER = f"""
.feuille {{ width: 148mm; height: 210mm; padding: 10mm 12mm 7mm; display: flex; flex-direction: column; gap: 3.6mm; }}
.haut {{ background: {C['forest']}; color: {C['surface']}; margin: -12mm -12mm 0; padding: 10mm 12mm 7mm; }}
.haut .surtitre {{ color: #cfe0d6; }}
.haut h1 {{ font-size: 22pt; margin: 2mm 0 2.5mm; }}
.haut p {{ font-size: 9.5pt; line-height: 1.42; color: #e8efe9; }}
.points {{ display: grid; grid-template-columns: 1fr 1fr; gap: 3mm; }}
.points .carte {{ padding: 2.6mm 3.4mm; font-size: 8.2pt; line-height: 1.36; }}
.points b {{ display: block; font-family: Gelasio, Georgia, serif; font-weight: 400; font-size: 11.5pt; color: {C['forest']};
            margin-bottom: 1mm; }}
.offre {{ display: flex; gap: 5mm; align-items: center; }}
.offre .qr {{ width: 27mm; height: 27mm; background: {C['surface']}; padding: 2mm; border: 1px solid {C['line']}; border-radius: 3mm; flex: none; }}
.offre .qr svg {{ width: 100%; height: 100%; display: block; }}
.offre h2 {{ font-size: 15pt; }} .offre p {{ font-size: 9pt; }}
.offre .url {{ font-weight: 700; color: {C['forest']}; font-size: 10.5pt; margin-top: 1.5mm; }}
.mentions {{ margin-top: auto; font-size: 6.2pt; line-height: 1.45; color: {C['muted']}; border-top: 1px solid {C['line']}; padding-top: 2mm; }}
"""


def flyer() -> str:
    qr = (ICI / "qr-site.svg").read_text(encoding="utf-8")
    points = [
        ("Les textes officiels", "Plus de 900 000 passages : codes, lois, Constitution, Cour de cassation, Conseil d’État, Conseil constitutionnel, traités de l’Union."),
        ("Chaque réponse sourcée", "Le texte officiel à un clic. Une affirmation sans source est retirée."),
        ("La bonne version", "Vérifie en un clic qu’un article est en vigueur. 1382 est relié à 1240."),
        ("Les méthodes de la licence", "Cas pratique, commentaire d’arrêt, dissertation. 20 matières, de la L1 à la L3."),
        ("Tes cours", "Dépose-les (PDF, Word, scan, photo) et confronte-les au droit en vigueur."),
        ("Pour réviser", "Questionnaires corrigés, cartes à retourner, résumés à écouter."),
    ]
    cartes = "".join(f'<div class="carte"><b>{typo(t)}</b>{typo(d)}</div>' for t, d in points)
    return f"""<section class="feuille"><div class="haut">{logotype(22, True)}
<p class="surtitre" style="margin-top:4.5mm">Droit français · Licence</p><h1>{typo("Réviser le droit avec les textes officiels.")}</h1>
<p>{typo("Lexia, l’espace d’étude des étudiants en licence de droit : des explications, des fiches et des questionnaires appuyés sur des sources que tu peux ouvrir et vérifier.")}</p></div>
<div class="points">{cartes}</div>
<div class="offre"><div class="qr">{qr}</div><div><h2>{typo("Gratuit avec un compte.")}</h2>
<p>{typo("10 questions et 2 questionnaires par jour, sans carte bancaire. Dès 15 ans.")}</p><p class="url">{SITE}</p></div></div>
<div class="mentions">{typo("Lexia, outil d’étude du droit français, pas un avis juridique. Éditeur : Arthur Champagne-Forterre, entrepreneur individuel, nom commercial Axion Studio, 5 allée des Pommiers, 95680 Montlignon. Imprimé par [nom et adresse de l’imprimeur]. Ne pas jeter sur la voie publique.")}</div></section>"""


# --------------------------------------------------------------------------- dossier de presse (A4 portrait)

def presse() -> str:
    T = "Dossier de presse"
    caps = PROD / "presse" / "captures"
    chiffres = [
        ("Plus de 900 000", "passages officiels dans le corpus : Constitution et textes constitutionnels, 36 codes, lois et ordonnances en vigueur, Cour de cassation, Conseil d’État et Tribunal des conflits, Conseil constitutionnel, traités de l’Union", "Index reconstruit le 19 novembre 2026 : environ 916 000 passages officiels, hors fiches pratiques (docs/cours-libres.md)"),
        ("Chaque nuit", "mise à jour des codes et des lois depuis les archives quotidiennes de la DILA", "Textes au 22 novembre 2026, Conseil d’État au 19 novembre 2026 (/api/fraicheur, lu le 23 novembre 2026)"),
        ("20", "matières, de la L1 à la L3", "/api/matieres, lu le 23 novembre 2026"),
        ("64", "grands arrêts reconnus par leur nom (20 judiciaires, 44 administratifs)", "api/grands_arrets.py, main au 23 novembre 2026"),
        ("26", "anciens numéros du Code civil reliés aux articles actuels (1382 vers 1240, 1134 vers 1103...)", "api/concordance.py"),
        ("1 149", "fiches pratiques de l’administration (service-public.gouv.fr, Licence Ouverte), à part des réponses", "Page « Cours récupérés », décision D103"),
        ("0 €, 4,99 €, 9,99 €", "par mois : formules Gratuit, Étudiant et Intensif ; paiement en ligne pas encore actif", "/api/formules et /api/config, lus le 23 novembre 2026"),
        ("15 ans", "âge minimum d’inscription", "CGU, article 3"),
    ]
    lignes = "".join(f"<tr><td style='width:34mm'><b style='font-family:Gelasio,serif;font-weight:400;font-size:13pt;color:{C['forest']}'>{typo(a)}</b></td>"
                     f"<td>{typo(b)}</td><td style='width:52mm;font-size:7.5pt;color:{C['muted']}'>{typo(c)}</td></tr>"
                     for a, b, c in chiffres)
    p1 = f"""<section class="feuille sombre"><div>{logotype(28, True)}</div>
<div><p class="surtitre">Dossier de presse</p><h1 style="margin:4mm 0 6mm">{typo("Lexia, le droit en vigueur, cité et vérifiable, pour les étudiants de licence")}</h1>
<p style="font-size:13pt;line-height:1.5;max-width:160mm">{typo("Un espace d’étude du droit français qui répond à partir des textes officiels, applique les méthodes de la licence et cite chaque source. Édité par Axion Studio, en développement ouvert au public.")}</p></div>
<div style="font-size:9pt;line-height:1.6">{typo(f"Version du {DATE}. Chiffres datés et sources en page 2.")}<br>{typo(f"Contact presse : {CONTACT} · {SITE}")}</div></section>"""
    p2 = f"""<section class="feuille">{tete(T, 2, 4)}<p class="surtitre">Présentation</p>
<h2>{typo("Ce que fait Lexia")}</h2>
<p>{typo("En droit, une réponse sans article ne vaut rien. Lexia part de là : l’étudiant pose une question de cours, Lexia cherche dans les textes officiels, rédige une réponse avec un modèle de langage, puis un contrôle sur le serveur retire toute source qui ne vient pas des extraits retrouvés, tout numéro d’article ou de décision inventé et toute affirmation de droit sans source. S’il ne reste rien de sourcé, Lexia s’abstient.")}</p>
<p>{typo("Les réponses suivent les méthodes de la licence (cas pratique, commentaire d’arrêt, dissertation, fiche) et le niveau du semestre choisi. L’étudiant peut déposer ses cours, même scannés, et les confronter au droit en vigueur ; un ancien numéro du Code civil y est signalé. Pour réviser : questionnaires corrigés avec les sources, cartes à retourner avec répétition espacée, résumés à écouter.")}</p>
<h3 style="margin-top:2mm">{typo("Chiffres clés, datés")}</h3><table><tr><th>Chiffre</th><th>Ce que c’est</th><th>Source et date</th></tr>{lignes}</table>
{pied("Lexia est un outil d’étude, pas un avis juridique.")}</section>"""
    p3 = f"""<section class="feuille">{tete(T, 3, 4)}<p class="surtitre">Transparence</p><h2>{typo("Ce que Lexia ne fait pas encore")}</h2>
<ul class="non"><li>{typo("La jurisprudence de la Cour de cassation va jusqu’à mi-septembre 2026, celle du Conseil constitutionnel jusqu’au 16 octobre 2026 : la DILA ne publie plus d’archive régulière pour ces juridictions. La date est affichée sous chaque source.")}</li>
<li>{typo("Pas de jurisprudence de la Cour de justice de l’Union européenne ni de la Cour européenne des droits de l’homme.")}</li>
<li>{typo("Les réponses n’ont pas encore été notées par un enseignant ; un appel à relecteurs est prévu.")}</li>
<li>{typo("Pas d’application mobile publiée : le site s’installe sur l’écran d’accueil du téléphone.")}</li>
<li>{typo("Paiement en ligne pas encore actif : les formules payantes se demandent par e-mail.")}</li>
<li>{typo("Les réponses sont rédigées par un modèle de langage (Gemini de Google, Groq en secours), aujourd’hui au niveau gratuit de l’API de Google : la politique de confidentialité le dit.")}</li></ul>
<h3 style="margin-top:3mm">Le site</h3><div class="captures"><div><img src="{(caps / 'accueil.png').as_uri()}"><p class="legende">{typo("Accueil, " + DATE)}</p></div>
<div><img src="{(caps / 'tarifs.png').as_uri()}"><p class="legende">{typo("Tarifs, " + DATE)}</p></div>
<div><img src="{(caps / 'inscription.png').as_uri()}"><p class="legende">{typo("Inscription, " + DATE)}</p></div>
<div style="display:flex;gap:3mm"><img src="{(caps / 'accueil-mobile.png').as_uri()}" style="width:45%"><p class="legende">{typo("Accueil sur téléphone (390 px), " + DATE + ". Captures de l’espace étudiant : à ajouter depuis un compte de test.")}</p></div></div>
{pied("Captures en haute définition : presse/captures/.")}</section>"""
    p4 = f"""<section class="feuille">{tete(T, 4, 4)}<p class="surtitre">{typo("L’éditeur")}</p><h2>{typo("Le fondateur")}</h2>
<div class="carte bloc"><p><b>Arthur Champagne-Forterre</b>{typo(", fondateur d’Axion Studio et éditeur de Lexia.")}</p>
<p style="margin-top:2mm;color:{C['ochre']}">{typo("[Biographie à compléter par le fondateur, 60 à 100 mots : parcours, pourquoi Lexia, ce qui vient ensuite. Ne rien écrire qui ne soit vérifiable.]")}</p>
<p style="margin-top:2mm;color:{C['ochre']}">{typo("[Citation du fondateur, une ou deux phrases.]")}</p>
<p style="margin-top:2mm;color:{C['ochre']}">{typo("[Photo du fondateur : fichier à fournir, droits d’usage accordés pour la presse.]")}</p></div>
<h3>{typo("L’entreprise")}</h3><p>{typo("Arthur Champagne-Forterre, entrepreneur individuel (micro-entreprise), nom commercial Axion Studio, 5 allée des Pommiers, 95680 Montlignon. SIRET en cours d’attribution (mentions légales du site, 23 novembre 2026).")}</p>
<h3>Contact</h3><p>{typo(f"Presse et partenariats : {CONTACT}")}<br>{typo(f"Site : {SITE}")}</p>
<h3>{typo("Logos et visuels")}</h3><p>{typo("Signet et logotype : identité visuelle du 13 novembre 2026, logos définitifs en préparation. Visuels des publications : dossier visuels/.")}</p>
<p class="encadre" style="margin-top:3mm">{typo("Le nom « Lexia » fait l’objet d’une vérification de marque en cours : à confirmer avant toute diffusion large de ce dossier.")}</p>
{pied("Dossier de presse · " + DATE)}</section>"""
    return p1 + p2 + p3 + p4


# --------------------------------------------------------------------------- main

def main(argv: list[str]) -> None:
    html_seul = "--html" in argv
    voulus = [a for a in argv if not a.startswith("--")] or ["storyboards", "kit", "flyer", "presse"]
    taches = []
    if "storyboards" in voulus:
        for v in VIDEOS:
            corps = storyboard(v) + annexe_tournage()
            taches.append((ecrire(f"storyboard-{v['id']}", f"Storyboard {v['id']}", "297mm 210mm", corps, CSS_SB),
                           PROD / "videos" / f"storyboard-{v['id']}.pdf"))
    if "kit" in voulus:
        taches.append((ecrire("kit-ambassadeur", "Kit ambassadeur Lexia", "210mm 297mm", kit(), CSS_A4),
                       PROD / "ambassadeurs" / "kit-ambassadeur.pdf"))
    if "flyer" in voulus:
        taches.append((ecrire("flyer", "Flyer Lexia", "148mm 210mm", flyer(), CSS_FLYER),
                       PROD / "impression" / "flyer-a5.pdf"))
    if "presse" in voulus:
        taches.append((ecrire("dossier-de-presse", "Dossier de presse Lexia", "210mm 297mm", presse(), CSS_A4),
                       PROD / "presse" / "dossier-de-presse.pdf"))
    if not html_seul:
        for source, cible in taches:
            pdf(source, cible)


if __name__ == "__main__":
    if not Path(CHROME).exists() and "--html" not in sys.argv:
        sys.exit(f"Chrome introuvable : {CHROME}")
    main(sys.argv[1:])
