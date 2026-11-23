#!/usr/bin/env python3
"""Visuels des publications du mois 1 (docs/marketing/contenus-mois-1.md), en HTML puis PNG.

Rendu par Chrome sans interface (installe sur le Mac de l'editeur), aucune dependance Python.
Polices libres (SIL OFL 1.1) dans source/polices : Gelasio (metriques de Georgia) pour les titres,
Inter pour le texte, comme l'identite « Identite visuelle Lexia » (Georgia et Inter).

Usage :
    python3 visuels.py            # HTML, PNG et PDF des carrousels LinkedIn
    python3 visuels.py P4 V       # seulement les visuels dont l'identifiant commence par P4 ou V
    python3 visuels.py --html     # HTML seulement (relecture des textes sans Chrome)

Pour changer de logo : remplacer les fonctions signet() et logotype() ci-dessous (ou lire brand/ quand
les logos definitifs seront dans main), puis relancer. Pour changer un texte : modifier POSTS, relancer.
"""
from __future__ import annotations

import html
import json
import re
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ICI = Path(__file__).resolve().parent            # production/source
PROD = ICI.parent                                 # production
SORTIE = PROD / "visuels"
PAGES = ICI / "html"
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
SITE = "lexia-axionstudio.cloud"

# Couleurs de l'identite (tokens.json de l'artefact « Identite visuelle Lexia », 13 novembre 2026)
C = {
    "paper": "#f5f4ef", "surface": "#fffefa", "line": "#e4e4dc", "ink": "#202724", "muted": "#707873",
    "forest": "#315e4b", "forest_dark": "#244735", "mint": "#e7efe9", "gold": "#bd8951",
    "brick": "#8c4a36", "brick_tint": "#f6e9e4", "cream": "#fbf7ef", "ochre": "#746347",
}

FORMATS = {"carre45": (1080, 1350), "story": (1080, 1920), "linkedin": (1200, 627)}


# --------------------------------------------------------------------------- typographie

def typo(s: str) -> str:
    """Espaces insecables francaises ; le texte peut contenir des balises (<b>, <br>, <s>) : il n'est pas echappe."""
    for a, b in ((" ?", " ?"), (" ;", " ;"), (" :", " :"), ("« ", "« "),
                 (" »", " »"), (" €", " €"), (" %", " %"), ("1er ", "1<sup>er</sup> ")):
        s = s.replace(a, b)
    return re.sub(r"(\d) (\d{3})\b", "\\1\u202f\\2", s)  # 900 000 jamais coupe en fin de ligne


def signet(h: int, sombre: bool = False) -> str:
    """Le signet de l'identite (marque-page forest, lisere gold, « L » blanc)."""
    fond, lettre = (C["surface"], C["forest"]) if sombre else (C["forest"], "#ffffff")
    w = h * 32 / 60
    return (f'<svg class="signet" width="{w:.0f}" height="{h}" viewBox="16 2 32 60" aria-hidden="true">'
            f'<path d="M16 2 H48 V62 L32 49 L16 62 Z" fill="{fond}"/>'
            f'<rect x="16" y="2" width="32" height="5" fill="{C["gold"]}"/>'
            f'<text x="32" y="38" text-anchor="middle" font-family="Gelasio, Georgia, serif" font-size="26" '
            f'fill="{lettre}">L</text></svg>')


def fleche(taille: int = 40) -> str:
    """Fleche dessinee : le glyphe U+2192 n'est pas dans le sous-ensemble latin des polices."""
    return (f'<svg width="{taille}" height="{taille}" viewBox="0 0 24 24" aria-hidden="true" style="vertical-align:middle">'
            f'<path d="M4 12h15M13 6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="2.2" '
            f'stroke-linecap="round" stroke-linejoin="round"/></svg>')


def logotype(h: int, sombre: bool = False) -> str:
    coul = C["surface"] if sombre else C["ink"]
    return (f'<span class="logotype" style="color:{coul};font-size:{h * 0.82:.0f}px">'
            f'{signet(h, sombre)}<span>lexia</span></span>')


# --------------------------------------------------------------------------- feuille de style

def css(w: int, h: int) -> str:
    return f"""
@font-face {{ font-family: Gelasio; src: url(../polices/gelasio-latin-400-normal.woff2); font-weight: 400; }}
@font-face {{ font-family: Gelasio; src: url(../polices/gelasio-latin-400-italic.woff2); font-style: italic; }}
@font-face {{ font-family: Inter; src: url(../polices/inter-latin-400-normal.woff2); font-weight: 400; }}
@font-face {{ font-family: Inter; src: url(../polices/inter-latin-600-normal.woff2); font-weight: 600; }}
@font-face {{ font-family: Inter; src: url(../polices/inter-latin-700-normal.woff2); font-weight: 700; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ width: {w}px; height: {h}px; overflow: hidden; }}
body {{ background: {C['paper']}; color: {C['ink']}; font-family: Inter, sans-serif;
       -webkit-font-smoothing: antialiased; font-feature-settings: "kern"; }}
.page {{ position: relative; width: {w}px; height: {h}px; display: flex; flex-direction: column; }}
.sombre {{ background: {C['forest']}; color: {C['surface']}; }}
.serif {{ font-family: Gelasio, Georgia, serif; font-weight: 400; }}
.logotype {{ display: inline-flex; align-items: center; gap: .32em; font-family: Gelasio, Georgia, serif;
            line-height: 1; }}
.surtitre {{ font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: {C['forest']}; }}
.sombre .surtitre {{ color: #cfe0d6; }}
.puce {{ display: inline-flex; align-items: center; gap: .45em; background: {C['mint']}; color: {C['forest']};
        font-weight: 600; border-radius: 999px; padding: .38em .9em; }}
.sombre .puce {{ background: rgba(255,254,250,.12); color: {C['surface']}; }}
.carte {{ background: {C['surface']}; border: 2px solid {C['line']}; border-radius: 28px; }}
.filet {{ width: 96px; height: 8px; background: {C['gold']}; }}
sup {{ font-size: .6em; line-height: 0; }}
s {{ text-decoration-thickness: .08em; }}
"""


def document(w: int, h: int, corps: str, extra_css: str = "", fond: str | None = None) -> str:
    style = f"body{{background:{fond}}}" if fond else ""
    return (f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Visuel Lexia</title>'
            f'<style>{css(w, h)}{extra_css}{style}</style></head><body>{corps}</body></html>')


# --------------------------------------------------------------------------- gabarits 1080 x 1350

CSS_DIAPO = f"""
.page {{ padding: 84px 88px 76px; }}
.tete {{ display: flex; justify-content: space-between; align-items: center; height: 60px; }}
.compteur {{ font-size: 26px; font-weight: 600; color: {C['muted']}; letter-spacing: .04em; }}
.sombre .compteur {{ color: #cfe0d6; }}
.milieu {{ flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 40px; }}
.pied {{ display: flex; justify-content: space-between; align-items: flex-end; font-size: 26px; color: {C['muted']};
        gap: 40px; }}
.sombre .pied {{ color: #cfe0d6; }}
.pied .suite {{ font-weight: 600; color: {C['forest']}; white-space: nowrap; }}
.sombre .pied .suite {{ color: {C['surface']}; }}
h1 {{ font-family: Gelasio, Georgia, serif; font-weight: 400; font-size: 84px; line-height: 1.1; letter-spacing: -.01em; }}
h1.geant {{ font-size: 100px; }}
h2 {{ font-family: Gelasio, Georgia, serif; font-weight: 400; font-size: 70px; line-height: 1.14; }}
.surtitre {{ font-size: 26px; }}
.corps {{ font-size: 40px; line-height: 1.45; }}
.corps + .corps {{ margin-top: -12px; }}
.sous {{ font-size: 40px; line-height: 1.4; color: #e8efe9; }}
.sources {{ display: flex; flex-wrap: wrap; gap: 16px; }}
.sources .puce {{ font-size: 28px; }}
.num, .ligne .ancien, .ligne .actuel, .chiffres b {{ font-variant-numeric: lining-nums; }}
.num {{ font-family: Gelasio, Georgia, serif; font-size: 150px; line-height: .9; color: {C['forest']}; }}
.exemple {{ background: {C['cream']}; border-left: 6px solid {C['gold']}; padding: 28px 34px; font-size: 34px;
           line-height: 1.45; color: {C['ochre']}; border-radius: 0 18px 18px 0; }}
.corresp {{ display: flex; flex-direction: column; gap: 30px; }}
.ligne {{ display: grid; grid-template-columns: 1fr 70px 1.25fr; align-items: center; padding: 34px 40px; }}
.ligne .ancien {{ font-family: Gelasio, Georgia, serif; font-size: 96px; color: {C['brick']}; }}
.ligne .ancien s {{ text-decoration-color: {C['brick']}; }}
.ligne .fleche {{ font-size: 56px; color: {C['muted']}; text-align: center; }}
.ligne .actuel {{ font-family: Gelasio, Georgia, serif; font-size: 112px; color: {C['forest']}; }}
.ligne .lib {{ grid-column: 1 / -1; font-size: 32px; font-weight: 600; margin-top: 10px; }}
.etiq {{ font-size: 24px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: {C['muted']}; }}
.verdict {{ display: inline-block; font-size: 64px; font-weight: 700; letter-spacing: .08em; padding: 14px 40px;
           border-radius: 999px; align-self: flex-start; }}
.verdict.vrai {{ background: {C['forest']}; color: {C['surface']}; }}
.verdict.faux {{ background: {C['brick']}; color: {C['surface']}; }}
.affirmation {{ font-family: Gelasio, Georgia, serif; font-size: 72px; line-height: 1.15; }}
.affirmation::before {{ content: "« "; }} .affirmation::after {{ content: " »"; }}
.liste {{ list-style: none; display: flex; flex-direction: column; gap: 22px; }}
.liste li {{ font-size: 44px; line-height: 1.25; padding: 22px 32px; }}
.cta {{ display: inline-flex; align-self: flex-start; align-items: center; gap: 18px; background: {C['forest']};
       color: {C['surface']}; font-size: 38px; font-weight: 600; padding: 26px 44px; border-radius: 18px; }}
.sombre .cta {{ background: {C['surface']}; color: {C['forest']}; }}
.url {{ font-size: 34px; font-weight: 600; color: {C['forest']}; }}
.sombre .url {{ color: {C['surface']}; }}
.reponse {{ padding: 40px 44px; display: flex; flex-direction: column; gap: 20px; }}
.reponse .q {{ align-self: flex-end; background: {C['mint']}; border-radius: 22px; padding: 20px 28px; font-size: 30px;
              max-width: 82%; line-height: 1.4; }}
.reponse .t {{ font-family: Gelasio, Georgia, serif; font-size: 44px; }}
.reponse .r {{ font-size: 31px; line-height: 1.5; }}
.reponse .r b {{ color: {C['forest']}; }}
.reponse .src {{ border-top: 2px solid {C['line']}; padding-top: 18px; font-size: 25px; color: {C['muted']}; line-height: 1.6; }}
.reponse .src b {{ color: {C['forest']}; }}
.reponse .leg {{ font-size: 22px; color: {C['muted']}; }}
"""


def diapo(contenu: str, i: int, n: int, sombre: bool = False, suite: str | None = None) -> str:
    pied_g = SITE
    fl = f" {fleche(30)}" if suite == "Fais défiler" else ""
    pied_d = f'<span class="suite">{typo(suite)}{fl}</span>' if suite else ""
    return (f'<div class="page{" sombre" if sombre else ""}">'
            f'<div class="tete">{logotype(56, sombre)}<span class="compteur">{f"{i} / {n}" if n > 1 else ""}</span></div>'
            f'<div class="milieu">{contenu}</div>'
            f'<div class="pied"><span>{pied_g}</span>{pied_d}</div></div>')


def sources(*refs: str) -> str:
    return '<div class="sources">' + "".join(f'<span class="puce">§ {typo(r)}</span>' for r in refs) + "</div>"


def k_couv(surtitre: str, titre: str, sous: str | None = None, geant: bool = False) -> dict:
    c = f'<div class="filet"></div><p class="surtitre">{typo(surtitre)}</p>'
    c += f'<h1 class="{"geant" if geant else ""}">{typo(titre)}</h1>'
    if sous:
        c += f'<p class="sous">{typo(sous)}</p>'
    return {"html": c, "sombre": True, "suite": "Fais défiler"}


def k_texte(surtitre: str | None, titre: str, *corps: str, refs: tuple = (), extra: str = "") -> dict:
    c = f'<p class="surtitre">{typo(surtitre)}</p>' if surtitre else ""
    c += f"<h2>{typo(titre)}</h2>"
    c += "".join(f'<p class="corps">{typo(p)}</p>' for p in corps)
    c += extra
    if refs:
        c += sources(*refs)
    return {"html": c}


def k_etape(num: int, titre: str, corps: str, exemple: str | None = None) -> dict:
    c = f'<div class="num">{num}</div><h2>{typo(titre)}</h2><p class="corps">{typo(corps)}</p>'
    if exemple:
        c += f'<div class="exemple">{typo(exemple)}</div>'
    return {"html": c}


def k_corresp(lignes: list[tuple[str, str, str]], note: str | None = None) -> dict:
    c = '<div class="corresp">'
    for ancien, actuel, lib in lignes:
        c += (f'<div class="ligne carte"><div><div class="etiq">Avant 2016</div><div class="ancien"><s>{ancien}</s></div></div>'
              f'<div class="fleche">{fleche(64)}</div><div><div class="etiq">Aujourd’hui</div><div class="actuel">{actuel}</div></div>'
              f'<div class="lib">{typo(lib)}</div></div>')
    c += "</div>"
    if note:
        c += f'<p class="corps">{typo(note)}</p>'
    return {"html": c}


def k_vf(affirmation: str, vrai: bool, explication: str, ref: str) -> dict:
    v = "vrai" if vrai else "faux"
    c = (f'<p class="etiq">Vrai ou faux</p><p class="affirmation">{typo(affirmation)}</p>'
         f'<span class="verdict {v}">{v.upper()}</span><p class="corps">{typo(explication)}</p>{sources(ref)}')
    return {"html": c}


def k_liste(surtitre: str, titre: str, items: list[str]) -> dict:
    c = f'<p class="surtitre">{typo(surtitre)}</p><h2>{typo(titre)}</h2><ul class="liste">'
    c += "".join(f'<li class="carte">{typo(x)}</li>' for x in items) + "</ul>"
    return {"html": c}


def k_fin(titre: str, corps: str | None, cta: str) -> dict:
    c = f'{signet(120, True)}<h2>{typo(titre)}</h2>'
    if corps:
        c += f'<p class="sous">{typo(corps)}</p>'
    c += f'<span class="cta">{typo(cta)}</span><p class="url">{SITE}</p>'
    return {"html": c, "sombre": True}


REPONSE_1240 = f"""<div class="reponse carte">
<div class="q">{typo("Quelles sont les conditions de la responsabilité pour faute ?")}</div>
<div class="t">La responsabilité pour faute</div>
<div class="r">{typo("Celui qui cause un dommage à autrui par sa faute doit le réparer : il faut une faute, un dommage et un lien de causalité.")} <b>[1]</b></div>
<div class="src"><b>[1]</b> Code civil, article 1240 · en vigueur depuis le 1<sup>er</sup> octobre 2016<br>
<b>[2]</b> Code civil, article 1241 · en vigueur depuis le 1<sup>er</sup> octobre 2016</div>
<div class="leg">{typo("Exemple de présentation d’une réponse.")}</div></div>"""


# --------------------------------------------------------------------------- gabarits 1080 x 1920

CSS_STORY = f"""
.page {{ padding: 250px 96px 400px; justify-content: center; gap: 44px; }}
.haut {{ position: absolute; top: 120px; left: 96px; }}
.surtitre {{ font-size: 30px; }}
h1 {{ font-family: Gelasio, Georgia, serif; font-weight: 400; font-size: 104px; line-height: 1.08; }}
.corps {{ font-size: 46px; line-height: 1.42; }}
.zone {{ border-radius: 28px; }}
.bas {{ font-size: 36px; font-weight: 600; color: {C['forest']}; }}
.sombre .bas {{ color: {C['surface']}; }}
.sources {{ display: flex; flex-wrap: wrap; gap: 16px; }} .sources .puce {{ font-size: 32px; }}
.etiquette {{ align-self: flex-start; font-size: 32px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase;
              border: 3px solid currentColor; border-radius: 999px; padding: 12px 30px; }}
.couv h1 {{ font-size: 118px; }}
.couv .sous {{ font-size: 46px; line-height: 1.4; color: #e8efe9; }}
.couv .pied {{ position: absolute; bottom: 150px; left: 96px; right: 96px; display: flex; justify-content: space-between;
              align-items: center; font-size: 32px; color: #cfe0d6; }}
"""


def story(contenu: str, sombre: bool = False) -> str:
    return (f'<div class="page{" sombre" if sombre else ""}"><div class="haut">{logotype(64, sombre)}</div>'
            f'{contenu}</div>')


def s_texte(surtitre: str | None, titre: str, corps: str | None = None, zone: int = 0, bas: str | None = None,
            refs: tuple = (), sombre: bool = False) -> dict:
    c = f'<p class="surtitre">{typo(surtitre)}</p>' if surtitre else ""
    c += f"<h1>{typo(titre)}</h1>"
    if corps:
        c += f'<p class="corps">{typo(corps)}</p>'
    if refs:
        c += sources(*refs)
    if zone:  # place laissee libre pour l'autocollant Instagram (sondage, quiz, questions, lien)
        c += f'<div class="zone" style="height:{zone}px"></div>'
    if bas:
        c += f'<p class="bas">{typo(bas)}</p>'
    return {"html": story(c, sombre)}


def s_couv(etiquette: str, titre: str, sous: str | None = None) -> dict:
    c = (f'<div class="couv" style="display:contents"><span class="etiquette">{typo(etiquette)}</span>'
         f'<h1>{typo(titre)}</h1>' + (f'<p class="sous">{typo(sous)}</p>' if sous else "") +
         f'<div class="pied"><span>{SITE}</span><span>Vidéo</span></div></div>')
    return {"html": f'<div class="page sombre couv">{c}<div class="haut">{logotype(64, True)}</div></div>'}


# --------------------------------------------------------------------------- gabarits 1200 x 627

CSS_LI = f"""
.page {{ flex-direction: row; padding: 56px 64px; gap: 56px; align-items: stretch; }}
.g {{ flex: 1.05; display: flex; flex-direction: column; justify-content: space-between; }}
.d {{ flex: 1; display: flex; flex-direction: column; justify-content: center; }}
.surtitre {{ font-size: 17px; }}
h1 {{ font-family: Gelasio, Georgia, serif; font-weight: 400; font-size: 50px; line-height: 1.12; margin: 14px 0 18px; }}
.corps {{ font-size: 22px; line-height: 1.5; color: {C['ink']}; }}
.url {{ font-size: 19px; font-weight: 600; color: {C['forest']}; }}
.reponse {{ padding: 26px 28px; display: flex; flex-direction: column; gap: 12px; }}
.reponse .q {{ align-self: flex-end; background: {C['mint']}; border-radius: 14px; padding: 12px 16px; font-size: 17px; max-width: 85%; line-height: 1.4; }}
.reponse .t {{ font-family: Gelasio, Georgia, serif; font-size: 26px; }}
.reponse .r {{ font-size: 17px; line-height: 1.5; }} .reponse .r b {{ color: {C['forest']}; }}
.reponse .src {{ border-top: 1px solid {C['line']}; padding-top: 10px; font-size: 14px; color: {C['muted']}; line-height: 1.6; }}
.reponse .src b {{ color: {C['forest']}; }} .reponse .leg {{ font-size: 13px; color: {C['muted']}; }}
.carte {{ border-radius: 18px; border-width: 1.5px; }}
.flux {{ display: flex; flex-direction: column; gap: 10px; }}
.etape {{ display: flex; align-items: center; gap: 14px; padding: 12px 16px; font-size: 21px; line-height: 1.3; }}
.etape .n {{ flex: none; width: 34px; height: 34px; border-radius: 50%; background: {C['mint']}; color: {C['forest']};
             font-weight: 700; display: grid; place-items: center; font-size: 16px; }}
.etape.cle {{ border-color: {C['forest']}; }}
.fin {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
.fin .etape {{ font-size: 19px; }}
.chiffres {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
.chiffres .carte {{ padding: 18px 20px; }}
.chiffres b {{ display: block; font-family: Gelasio, Georgia, serif; font-weight: 400; font-size: 36px; color: {C['forest']}; }}
.chiffres span {{ font-size: 18px; line-height: 1.4; }}
"""


def li(surtitre: str, titre: str, corps: str, droite: str) -> dict:
    g = (f'<div class="g"><div>{logotype(40)}</div><div><p class="surtitre">{typo(surtitre)}</p>'
         f'<h1>{typo(titre)}</h1><p class="corps">{typo(corps)}</p></div><p class="url">{SITE}</p></div>')
    return {"html": f'<div class="page">{g}<div class="d">{droite}</div></div>'}


REPONSE_LI = REPONSE_1240.replace('class="reponse carte"', 'class="reponse carte" style="font-size:1px"')

SCHEMA_CONTROLE = f"""<div class="flux">
<div class="etape carte"><span class="n">1</span>{typo("La question de l’étudiant")}</div>
<div class="etape carte"><span class="n">2</span>{typo("Recherche dans les textes officiels")}</div>
<div class="etape carte"><span class="n">3</span>{typo("Réponse rédigée à partir de ces extraits")}</div>
<div class="etape carte cle"><span class="n">4</span>{typo("Contrôle : numéro inventé ou affirmation sans source retirés")}</div>
<div class="fin"><div class="etape carte"><span class="n">5</span>{typo("Réponse sourcée")}</div>
<div class="etape carte"><span class="n">5</span>{typo("ou abstention")}</div></div></div>"""

CHIFFRES_LI = f"""<div class="chiffres">
<div class="carte"><b>900 000+</b><span>{typo("passages officiels : codes, lois, Constitution, jurisprudence, traités de l’Union")}</span></div>
<div class="carte"><b>20</b><span>{typo("matières, de la L1 à la L3")}</span></div>
<div class="carte"><b>3</b><span>{typo("méthodes : cas pratique, commentaire d’arrêt, dissertation")}</span></div>
<div class="carte"><b>0 €</b><span>{typo("avec un compte : 10 questions et 2 questionnaires par jour")}</span></div></div>"""


# --------------------------------------------------------------------------- ambassadeurs

CSS_AMB = f"""
.bandeau {{ position: absolute; left: 0; right: 0; top: 0; background: {C['surface']}; color: {C['ink']};
           border-bottom: 6px solid {C['gold']}; padding: 150px 72px 34px; font-size: 44px; font-weight: 700; line-height: 1.25; }}
.bandeau span {{ display: block; font-size: 30px; font-weight: 400; margin-top: 8px; color: {C['ink']}; }}
"""


def amb_bandeau() -> dict:
    c = (f'<div class="bandeau">{typo("Publicité · Collaboration commerciale avec Lexia")}'
         f'<span>{typo("Formule Intensif offerte par Lexia")}</span></div>')
    return {"html": f'<div class="page" style="background:transparent">{c}</div>', "transparent": True}


# --------------------------------------------------------------------------- les publications

def carrousel(*diapos: dict) -> list[dict]:
    n = len(diapos)
    out = []
    for i, d in enumerate(diapos, 1):
        out.append({"html": diapo(d["html"], i, n, d.get("sombre", False), d.get("suite")), "css": CSS_DIAPO,
                    "format": "carre45"})
    return out


def un(fmt: str, d: dict) -> list[dict]:
    feuille = {"story": CSS_STORY, "linkedin": CSS_LI, "carre45": CSS_DIAPO}[fmt]
    if d.get("transparent"):
        feuille += CSS_AMB
    return [{"html": d["html"], "css": feuille, "format": fmt, "transparent": d.get("transparent", False)}]


POSTS: list[dict] = [
    {"id": "P1", "date": "2026-11-30", "reseaux": "Instagram + LinkedIn (document PDF)", "type": "Carrousel",
     "titre": "Présentation de Lexia", "pdf": True, "visuels": carrousel(
        k_couv("Droit français · Licence", "Réviser le droit avec les textes officiels.",
               "Lexia, l’espace d’étude des étudiants en licence de droit.", geant=True),
        k_texte("Les sources", "Plus de 900 000 passages officiels.",
                "Codes, lois, Constitution, Cour de cassation, Conseil d’État, Conseil constitutionnel, traités de l’Union.",
                "Codes et lois mis à jour chaque nuit depuis les données ouvertes de la DILA. La date de chaque source est affichée."),
        k_texte("Les citations", "Chaque réponse cite ses sources.",
                "Un clic ouvre le texte officiel. Une affirmation sans source est retirée.", extra=REPONSE_1240),
        k_texte("La méthode", "Les méthodes de la licence.",
                "Cas pratique, commentaire d’arrêt, dissertation : la réponse suit les rubriques attendues.",
                "Et pour réviser : questionnaires corrigés, cartes à retourner, résumés à écouter."),
        k_texte("Les matières", "20 matières, de la L1 à la L3.",
                "Le niveau d’explication suit ton semestre. Tu peux aussi déposer tes cours, même scannés, et les confronter au droit en vigueur."),
        k_fin("Gratuit avec un compte.", "10 questions et 2 questionnaires par jour. Conditions d’inscription dans les CGU.", "Lien en bio"),
    )},
    {"id": "P2", "date": "2026-11-30", "reseaux": "LinkedIn (profil de l’éditeur)", "type": "Image",
     "titre": "Lancement (post du fondateur)", "visuels": un("linkedin", li(
        "Lancement", "Le droit en vigueur, cité et vérifiable.",
        "Lexia est un espace d’étude du droit français pour les étudiants de licence : chaque réponse s’appuie sur des textes officiels, avec la source à un clic.",
        REPONSE_LI))},
    {"id": "P3", "date": "2026-12-01", "reseaux": "TikTok, Reels, Shorts", "type": "Vidéo courte (V1)",
     "titre": "Cas pratique en 30 s : la piscine", "visuels": un("story", s_couv(
        "Cas pratique · 30 s", "Il le pousse dans la piscine pour rire. Doit-il réparer ?",
        "Faute, dommage, lien de causalité : article 1240 du Code civil."))},
    {"id": "P4", "date": "2026-12-02", "reseaux": "Instagram", "type": "Carrousel",
     "titre": "Les anciens numéros du Code civil", "visuels": carrousel(
        k_couv("Droit des obligations", "1382, 1134, 1147 : les anciens numéros qui coûtent des points en L1"),
        k_texte("Depuis le 1er octobre 2016", "Le droit des contrats et des obligations a été renuméroté.",
                "Beaucoup de manuels et de polycopiés anciens citent encore les anciens articles."),
        k_corresp([("1382", "1240", "Responsabilité pour faute"), ("1383", "1241", "Négligence ou imprudence")]),
        k_corresp([("1134", "1103", "Force obligatoire du contrat")],
                  "Et l’article 1104 pour la bonne foi, l’article 1193 pour la révocation."),
        k_corresp([("1147", "1231-1", "Inexécution et dommages et intérêts"), ("1165", "1199", "Effet relatif du contrat")]),
        k_texte("Attention", "1382 existe toujours. Il parle d’autre chose.",
                "L’article 1382 actuel porte sur les présomptions laissées à l’appréciation du juge. L’article 1134 actuel, sur l’erreur sur les qualités essentielles du cocontractant.",
                "Citer le mauvais numéro, c’est citer une autre règle.", refs=("Code civil, art. 1382 et 1134 en vigueur",)),
        k_fin("Dans Lexia, un ancien numéro est relié à l’article actuel.",
              "Même dans un cours que tu déposes. Enregistre ce carrousel pour tes révisions.", "Lien en bio"),
    )},
    {"id": "P5", "date": "2026-12-03", "reseaux": "TikTok, Reels, Shorts", "type": "Vidéo courte (V3)",
     "titre": "Le piège du 1382", "visuels": un("story", s_couv(
        "Démonstration · 30 s", "Tu cites encore 1382 ?", "Regarde ce que dit vraiment l’article 1382 aujourd’hui."))},
    {"id": "P6", "date": "2026-12-04", "reseaux": "Instagram", "type": "3 stories",
     "titre": "Sondage, quiz, réponse", "visuels":
        un("story", s_texte("Sondage", "Tes partiels commencent…", zone=380, bas="Réponds, on adapte les contenus.")) +
        un("story", s_texte("Quiz", "La responsabilité pour faute, c’est l’article…", zone=520)) +
        un("story", s_texte("Réponse", "1240.", "Depuis le 1er octobre 2016. L’article 1382 actuel parle des présomptions laissées au juge.",
                            refs=("Code civil, article 1240",), bas="Le reste dans notre carrousel d’hier.", sombre=False))},
    {"id": "P7", "date": "2026-12-05", "reseaux": "TikTok, Reels, Shorts", "type": "Vidéo courte (V4)",
     "titre": "Fiche d’arrêt Blanco en 45 s", "visuels": un("story", s_couv(
        "Fiche d’arrêt · 45 s", "Blanco, 1873 : le premier grand arrêt du droit administratif",
        "Tribunal des conflits, 8 février 1873."))},
    {"id": "P8", "date": "2026-12-07", "reseaux": "Instagram + LinkedIn (document PDF)", "type": "Carrousel",
     "titre": "Le cas pratique en 5 rubriques", "pdf": True, "visuels": carrousel(
        k_couv("Méthode", "Le cas pratique en 5 rubriques", geant=True),
        k_etape(1, "Faits et qualification", "Quels faits comptent, et que deviennent-ils en droit ?",
                "Une blague devient un « fait », une blessure devient un « dommage »."),
        k_etape(2, "Problème de droit", "Une question juridique générale, pas l’histoire des personnes.",
                "Pas : « Sami peut-il être indemnisé ? ». Plutôt : « La personne qui cause un dommage par sa faute doit-elle le réparer ? »"),
        k_etape(3, "Majeure", "La règle, avec son article. Pas de règle sans source.", "Code civil, article 1240."),
        k_etape(4, "Mineure", "On applique la règle aux faits, condition par condition.",
                "Une faute ? Un dommage ? Un lien de causalité ?"),
        k_etape(5, "Conclusion", "On répond à la question posée, clairement."),
        k_fin("Ton chargé de TD a sa propre présentation ? Suis-la.",
              "Lexia en mode Cas pratique répond avec ces rubriques.", "Essaie le mode Cas pratique"),
    )},
    {"id": "P9", "date": "2026-12-08", "reseaux": "TikTok, Reels, Shorts", "type": "Vidéo courte (V2)",
     "titre": "3 erreurs en L1", "visuels": un("story", s_couv(
        "Méthode · 45 s", "3 erreurs qui coûtent des points en L1", "Tu en fais combien ?"))},
    {"id": "P10", "date": "2026-12-09", "reseaux": "LinkedIn", "type": "Image",
     "titre": "Le contrôle des citations", "visuels": un("linkedin", li(
        "Garde-fous", "Une référence inventée est retirée quand le contrôle la détecte.",
        "Le contrôle se fait après le modèle, sur le serveur. Il ne rend pas les réponses infaillibles : le choix des sources et l’explication peuvent rester imparfaits.",
        SCHEMA_CONTROLE))},
    {"id": "P11", "date": "2026-12-10", "reseaux": "TikTok, Reels, Shorts", "type": "Vidéo courte",
     "titre": "Cas pratique n° 2 : le dol", "visuels": un("story", s_couv(
        "Cas pratique · 30 s", "Il n’a rien dit sur l’accident. Est-ce un dol ?", "Article 1137 du Code civil, alinéa 2."))},
    {"id": "P12", "date": "2026-12-11", "reseaux": "Instagram", "type": "Carrousel",
     "titre": "La fiche d’arrêt en 5 cases", "visuels": carrousel(
        k_couv("Méthode", "La fiche d’arrêt en 5 cases", geant=True),
        k_etape(1, "Les faits", "Qui, quoi, sans détails inutiles."),
        k_etape(2, "La procédure", "Qui a saisi qui, et ce qu’ont décidé les juges avant."),
        k_etape(3, "Les prétentions", "Ce que soutient chaque partie, souvent le moyen du pourvoi."),
        k_etape(4, "Le problème de droit", "La question juridique que tranche la juridiction."),
        k_etape(5, "La solution", "Ce que décide la juridiction, et sur quel fondement."),
        k_fin("La fiche d’arrêt ouvre le commentaire.",
              "Lexia en mode Commentaire d’arrêt t’aide à la faire, avec les textes cités.", "Enregistre pour ton prochain commentaire"),
    )},
    {"id": "P13", "date": "2026-12-12", "reseaux": "Instagram", "type": "Stories questions",
     "titre": "Boîte à questions et réponses", "visuels":
        un("story", s_texte("Tes questions", "Ta question de cours pour les partiels ?",
                            "On répond avec l’article.", zone=420)) +
        un("story", s_texte("Ta question", "Nullité relative ou absolue : quelle différence ?",
                            "Absolue quand la règle violée protège l’intérêt général ; relative quand elle protège seulement un intérêt privé.",
                            refs=("Code civil, article 1179",), bas="Exemple de réponse : une story par question.")) +
        un("story", s_texte("À savoir", "Une question sur ta situation personnelle ?",
                            "On ne donne pas de conseil sur une situation personnelle : adresse-toi à un professionnel du droit ou à un point-justice (point d’accès au droit).",
                            sombre=True))},
    {"id": "P14", "date": "2026-12-13", "reseaux": "TikTok, Reels, Shorts", "type": "Vidéo courte",
     "titre": "Démonstration : dépose ton cours", "visuels": un("story", s_couv(
        "Démonstration · 40 s", "Ton poly cite encore 1382 ? Dépose-le.",
        "PDF, Word, PowerPoint, OpenDocument, et même un scan ou une photo de ton cours."))},
    {"id": "P15", "date": "2026-12-14", "reseaux": "TikTok, Reels, Shorts", "type": "Vidéo courte (V5)",
     "titre": "Un quiz en 2 minutes", "visuels": un("story", s_couv(
        "Révision · 55 s", "5 questions, 2 minutes, corrigé avec les articles", "La révision de la pause café."))},
    {"id": "P16", "date": "2026-12-15", "reseaux": "Instagram + LinkedIn (document PDF)", "type": "Carrousel",
     "titre": "Dissertation : le plan en deux parties", "pdf": True, "visuels": carrousel(
        k_couv("Méthode", "Dissertation : construire un plan en deux parties"),
        k_etape(1, "Définir les termes", "Chaque mot du sujet compte."),
        k_etape(2, "Trouver la problématique", "La tension que le sujet fait apparaître."),
        k_etape(3, "Deux parties, deux sous-parties",
                "C’est l’usage dans beaucoup de facultés de droit. Les titres répondent à la problématique."),
        k_etape(4, "Des textes et des décisions", "Chaque sous-partie s’appuie sur des sources."),
        k_fin("Lexia en mode Dissertation propose un plan et cite les sources.",
              "Il ne remplace pas ta réflexion : sers-t’en pour vérifier et compléter.", "Partage à ton groupe de TD"),
    )},
    {"id": "P17", "date": "2026-12-16", "reseaux": "Instagram", "type": "Carrousel",
     "titre": "Vrai ou faux : droit des contrats", "visuels": carrousel(
        k_couv("Vrai ou faux", "Droit des contrats : 5 affirmations avant les partiels", geant=False),
        k_vf("Le silence vaut acceptation.", False,
             "En principe non, sauf si la loi, les usages, les relations d’affaires ou des circonstances particulières en décident autrement.",
             "Code civil, article 1120"),
        k_vf("Les contrats doivent être exécutés de bonne foi.", True,
             "Ils doivent aussi être négociés et formés de bonne foi. Cette disposition est d’ordre public.", "Code civil, article 1104"),
        k_vf("Un contrat peut obliger un tiers à l’exécuter.", False,
             "Le contrat ne crée d’obligations qu’entre les parties, sous réserve des exceptions prévues.", "Code civil, article 1199"),
        k_vf("Un mineur ne peut jamais contracter seul.", False,
             "Il peut accomplir seul les actes courants autorisés par la loi ou l’usage, conclus à des conditions normales.",
             "Code civil, article 1148"),
        k_vf("Se taire peut être un dol.", True,
             "La dissimulation intentionnelle d’une information dont on sait le caractère déterminant pour l’autre est un dol.",
             "Code civil, article 1137, al. 2"),
        k_fin("Combien de bonnes réponses ?", "Dis-le en commentaire.", "Lien en bio"),
    )},
    {"id": "P18", "date": "2026-12-17", "reseaux": "TikTok, Reels, Shorts", "type": "Vidéo courte",
     "titre": "Vrai ou faux en 20 secondes", "visuels": un("story", s_couv(
        "Vrai ou faux · 20 s", "3 questions de droit des contrats avant les partiels", "Ton score en commentaire."))},
    {"id": "P19", "date": "2026-12-18", "reseaux": "LinkedIn", "type": "Image",
     "titre": "Appel aux relecteurs", "visuels": un("linkedin", li(
        "Appel à relecteurs", "Enseignants, chargés de TD, doctorants : notez nos réponses.",
        "Aucune notation par un enseignant n’a encore été faite, et nous ne voulons pas parler de fiabilité avant. Grille simple, conditions envoyées sur demande.",
        CHIFFRES_LI))},
    {"id": "P20", "date": "2026-12-19", "reseaux": "Instagram", "type": "Story",
     "titre": "Dernière ligne droite", "visuels": un("story", s_texte(
        "Partiels", "Dernière ligne droite.",
        "Bon courage pour les partiels. Une question de dernière minute ? 10 questions par jour avec le compte gratuit.",
        zone=200, sombre=True))},
    {"id": "P21", "date": "2026-12-21", "reseaux": "TikTok, Reels, Shorts", "type": "Vidéo courte",
     "titre": "Vérifier qu’un article est en vigueur", "visuels": un("story", s_couv(
        "Réflexe · 15 s", "Avant de citer un article, vérifie qu’il est en vigueur.", "Un clic."))},
    {"id": "P22", "date": "2026-12-22", "reseaux": "Instagram", "type": "Carrousel",
     "titre": "Les 20 matières", "visuels": carrousel(
        k_couv("De la L1 à la L3", "Les 20 matières de Lexia", geant=True),
        k_liste("L1", "Première année", ["Introduction au droit", "Droit constitutionnel", "Droit civil",
                                         "Droit de la famille", "Droit des biens"]),
        k_liste("L2", "Deuxième année", ["Droit des contrats", "Droit administratif", "Droit européen", "Droit pénal",
                                         "Droit des affaires", "Finances publiques"]),
        {"html": k_liste("L3", "Troisième année", [
            "Procédure civile · Procédure pénale", "Droit social · Droit des sociétés",
            "Contentieux administratif · Droit administratif des biens", "Droit international · Libertés fondamentales",
            "Droit fiscal"])["html"], "suite": "Il manque ta matière ? Dis-le en commentaire."},
    )},
    {"id": "P23", "date": "2026-12-23", "reseaux": "TikTok, Reels, Shorts", "type": "Vidéo courte",
     "titre": "Fiche d’arrêt : Nicolo en 45 s", "visuels": un("story", s_couv(
        "Fiche d’arrêt · 45 s", "Nicolo, 1989 : le revirement que tout L2 doit connaître",
        "Conseil d’État, assemblée, 20 octobre 1989."))},
    {"id": "P24", "date": "2026-12-24", "reseaux": "Instagram", "type": "Story",
     "titre": "Bonnes fêtes", "visuels": un("story", s_texte(
        None, "Bonnes fêtes.", "Le site reste ouvert pendant les vacances.", sombre=True))},
    {"id": "P25", "date": "2026-12-26", "reseaux": "Instagram + LinkedIn (document PDF)", "type": "Carrousel",
     "titre": "Ce que Lexia ne fait pas (encore)", "pdf": True, "visuels": carrousel(
        k_couv("Transparence", "Ce que Lexia ne fait pas (encore)", geant=True),
        k_texte("Jurisprudence", "Un retard, affiché.",
                "Cour de cassation : décisions jusqu’à mi-septembre 2026. Conseil constitutionnel : jusqu’au 16 octobre 2026.",
                "Les codes et les lois sont mis à jour chaque nuit. La date de chaque source est affichée."),
        k_texte("Europe", "Pas encore de jurisprudence européenne.",
                "Ni la Cour de justice de l’Union européenne ni la Cour européenne des droits de l’homme. Les traités de l’Union, eux, sont dans le corpus."),
        k_texte("Mobile", "Pas d’application mobile.", "Le site s’installe sur l’écran d’accueil du téléphone."),
        k_texte("Révision", "Tes fiches et tes cartes restent dans ton navigateur.",
                "Elles ne passent pas encore d’un appareil à l’autre."),
        k_texte("Qualité", "Les réponses n’ont pas encore été notées par un enseignant.",
                "Nous cherchons des relecteurs. Et toi : dis-nous ce qui doit passer en premier."),
    )},
    {"id": "P26", "date": "2026-12-27", "reseaux": "Instagram + LinkedIn", "type": "Image",
     "titre": "Bilan du mois", "visuels":
        un("carre45", {"html": diapo(k_fin("Un mois de Lexia. Merci.",
                                           "En janvier : appel à ambassadeurs dans les facultés de droit (étudiants majeurs, conditions écrites et transparentes) et de nouveaux cas pratiques.",
                                           "Lien en bio")["html"], 1, 1, True)}) +
        un("linkedin", li("Bilan", "Un mois de Lexia. Merci pour vos retours.",
                          "En janvier : appel à ambassadeurs dans les facultés de droit (étudiants majeurs, conditions écrites et transparentes), relecture par des enseignants et nouveaux cas pratiques.",
                          CHIFFRES_LI))},
    {"id": "AMB", "date": "", "reseaux": "Comptes des ambassadeurs", "type": "Modèle à superposer",
     "titre": "Bandeau « Publicité » des ambassadeurs (fond transparent)", "visuels": un("story", amb_bandeau())},
]


# --------------------------------------------------------------------------- rendu

def chrome(*args: str) -> None:
    with tempfile.TemporaryDirectory(prefix="lexia-chrome-") as profil:
        subprocess.run([CHROME, "--headless=new", f"--user-data-dir={profil}", "--disable-gpu", "--hide-scrollbars",
                        "--no-first-run", "--allow-file-access-from-files", "--virtual-time-budget=4000", *args],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)


def rendre_png(page: Path, png: Path, w: int, h: int, transparent: bool) -> None:
    extra = ["--default-background-color=00000000"] if transparent else []
    chrome(f"--window-size={w},{h}", "--force-device-scale-factor=1", *extra, f"--screenshot={png}", page.as_uri())


def rendre_pdf(pngs: list[Path], pdf: Path, w: int, h: int) -> None:
    corps = "".join(f'<img src="{p.as_uri()}">' for p in pngs)
    source = PAGES / f"{pdf.stem}.pdf.html"
    source.write_text(f'<!doctype html><html><head><meta charset="utf-8"><style>@page{{size:{w}px {h}px;margin:0}}'
                      f'body{{margin:0}}img{{display:block;width:{w}px;height:{h}px;page-break-after:always}}</style>'
                      f'</head><body>{corps}</body></html>', encoding="utf-8")
    chrome("--no-pdf-header-footer", "--print-to-pdf-no-header", f"--print-to-pdf={pdf}", source.as_uri())
    source.unlink()


def main(argv: list[str]) -> None:
    html_seul = "--html" in argv
    filtres = [a for a in argv if not a.startswith("--")]
    PAGES.mkdir(exist_ok=True)
    SORTIE.mkdir(exist_ok=True)
    manifeste = []
    for post in POSTS:
        fichiers = []
        retenu = not filtres or any(post["id"].startswith(f) for f in filtres)
        for i, v in enumerate(post["visuels"], 1):
            w, h = FORMATS[v["format"]]
            nom = f'{post["id"]}-{i:02d}-{w}x{h}'
            fichiers.append({"png": f"visuels/{post['id']}/{nom}.png", "format": f"{w}x{h}"})
            if not retenu:
                continue
            page = PAGES / f"{nom}.html"
            page.write_text(document(w, h, v["html"], v["css"], "transparent" if v.get("transparent") else None),
                            encoding="utf-8")
            if not html_seul:
                dossier = SORTIE / post["id"]
                dossier.mkdir(exist_ok=True)
                rendre_png(page, dossier / f"{nom}.png", w, h, v.get("transparent", False))
                print("png", nom, flush=True)
        pdf = None
        if post.get("pdf"):
            pdf = f"visuels/{post['id']}/{post['id']}-linkedin-document.pdf"
            if retenu and not html_seul:
                rendre_pdf([PROD / f["png"] for f in fichiers], PROD / pdf, 1080, 1350)
                print("pdf", pdf, flush=True)
        manifeste.append({k: post[k] for k in ("id", "date", "reseaux", "type", "titre")} |
                         {"fichiers": fichiers, "pdf": pdf})
    (SORTIE / "manifeste.json").write_text(json.dumps(manifeste, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(manifeste), "publications,", sum(len(m["fichiers"]) for m in manifeste), "visuels")


if __name__ == "__main__":
    if not Path(CHROME).exists() and "--html" not in sys.argv:
        sys.exit(f"Chrome introuvable : {CHROME} (variable CHROME, ou --html)")
    main(sys.argv[1:])
