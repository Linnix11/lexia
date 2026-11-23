"""Images des reseaux sociaux et image Open Graph, rendues depuis des gabarits HTML.

Textes : uniquement des phrases autorisees de docs/marketing/contenus-mois-1.md et le titre du site.
Exemple juridique : Code civil, article 1137 (dol), relu dans le corpus de Lexia pour le plan marketing
(https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000036829827).

Usage, depuis la racine du depot : python3 -I brand/outils/images.py
"""
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))

import marque as m  # noqa: E402
from rendu import page, rendre  # noqa: E402

KIT = ICI.parent
RESEAUX = KIT / "reseaux"
OG = KIT / "open-graph"

SIGNATURE = "Le droit, sources à\u00a0l’appui."
INSEC = "\u202f"  # espace fine insecable avant ? ; : !
ADRESSE = "lexia-axionstudio.cloud"

STYLE = f"""
* {{ box-sizing: border-box; }}
body {{ font-family: Inter, sans-serif; color: {m.ENCRE}; -webkit-font-smoothing: antialiased; }}
.serif {{ font-family: "Source Serif 4", Georgia, serif; font-weight: 400; font-variation-settings: "opsz" 60; }}
.surtitre {{ font-weight: 700; text-transform: uppercase; letter-spacing: .14em; color: {m.FORET}; }}
.carte {{ background: {m.SURFACE}; border: 2px solid #e4e4dc; border-radius: 24px; }}
.cite {{ color: {m.FORET}; font-weight: 600; border-bottom: 2px solid #b2c2b7; white-space: nowrap; }}
.source {{ display: flex; gap: .7em; align-items: center; }}
.signe {{ display: grid; place-items: center; flex-shrink: 0; width: 1.9em; height: 1.9em; border-radius: .4em;
          background: #eef1eb; color: {m.FORET}; font-family: "Source Serif 4", serif; font-weight: 600; }}
.entete {{ font-weight: 600; display: block; }}
sup {{ font-size: .7em; line-height: 0; }}
.version {{ color: #666e69; display: block; font-size: .85em; margin-top: .15em; }}
"""


def logo(forme, variante, hauteur, aligne="flex-start"):
    texte = {"horizontal": m.logo_horizontal, "principal": m.logo_principal, "symbole": m.logo_symbole}[forme](variante)
    style = f"height:{hauteur}px;width:auto;flex-shrink:0;align-self:{aligne}"
    return texte.replace("<svg ", f'<svg style="{style}" height="{hauteur}" ', 1)


def carte_reponse(taille):
    """Carte « une question, une reponse sourcee », a l'image du site. taille : corps du texte en px."""
    return f"""
<div class="carte" style="padding:{taille * 1.6}px;font-size:{taille}px;line-height:1.5">
  <div class="surtitre" style="font-size:{taille * .62}px">Question</div>
  <div class="serif" style="font-size:{taille * 1.45}px;line-height:1.2;margin:.3em 0 .7em">Qu’est-ce que le dol{INSEC}?</div>
  <div>Le dol est le fait pour un contractant d’obtenir le consentement de l’autre par des manœuvres ou
  des mensonges <span class="cite">[1]</span>.</div>
  <div style="border-top:2px solid #eeede7;margin-top:1em;padding-top:1em" class="source">
    <span class="signe">§</span>
    <span><span class="entete">Code civil, article 1137</span>
    <span class="version">Version depuis le 1<sup>er</sup> octobre 2018</span></span>
  </div>
</div>"""


def og():
    corps = f"""
<div style="width:1200px;height:630px;background:{m.PAPIER};display:flex;align-items:center;gap:56px;padding:0 72px;position:relative">
  <div style="flex:1;display:flex;flex-direction:column;gap:28px">
    {logo("horizontal", "couleur", 60)}
    <div class="serif" style="font-size:60px;line-height:1.08;letter-spacing:-.01em">Le droit,<br>sources à\u00a0l’appui.</div>
    <div style="font-size:25px;line-height:1.4;color:#4a524d">Réviser le droit avec les textes officiels{INSEC}:
    chaque réponse cite ses sources.</div>
    <div style="font-size:22px;font-weight:600;color:{m.FORET}">{ADRESSE}</div>
  </div>
  <div style="width:470px">{carte_reponse(20)}</div>
  <div style="position:absolute;left:0;right:0;bottom:0;height:10px;background:{m.FORET}"></div>
</div>"""
    return [(page(corps, 1200, 630, STYLE), 1200, 630, OG / "og-image-1200x630.png", 2000)]


def profils():
    taches = []
    icone = m.icone_app(taille_signet=0.6)
    for nom, t in [("profil-1080", 1080), ("tiktok-profil-200", 200), ("instagram-profil-320", 320),
                   ("youtube-profil-800", 800), ("linkedin-logo-400", 400)]:
        corps = icone.replace("<svg ", f'<svg width="{t}" height="{t}" ', 1)
        taches.append((page(corps, t, t), t, t, RESEAUX / "profils" / f"{nom}.png"))
    return taches


def youtube():
    # Zone visible partout (televiseur, ordinateur, telephone) : 1235 x 338 au centre ; le reste est du fond.
    corps = f"""
<div style="width:2560px;height:1440px;background:{m.PAPIER};position:relative;display:grid;place-items:center">
  <div style="position:absolute;left:0;right:0;top:0;height:400px;background:{m.FORET}"></div>
  <div style="position:absolute;left:0;right:0;bottom:0;height:400px;background:{m.FORET}"></div>
  <div style="display:flex;align-items:center;gap:72px">
    {logo("horizontal", "couleur", 150, "center")}
    <div style="width:3px;height:170px;background:{m.OR}"></div>
    <div style="display:flex;flex-direction:column;gap:18px">
      <div class="serif" style="font-size:66px;line-height:1.05">{SIGNATURE}</div>
      <div style="font-size:34px;color:#4a524d">Réviser le droit avec les textes officiels.</div>
    </div>
  </div>
</div>"""
    return [(page(corps, 2560, 1440, STYLE), 2560, 1440, RESEAUX / "couvertures" / "youtube-banniere-2560x1440.png", 2000)]


def linkedin():
    entreprise = f"""
<div style="width:1128px;height:191px;background:{m.FORET};display:flex;align-items:center;justify-content:flex-end;padding:0 64px;gap:28px;color:{m.SURFACE}">
  <div style="text-align:right">
    <div class="serif" style="font-size:40px;line-height:1.1">{SIGNATURE}</div>
    <div style="font-size:18px;margin-top:10px;opacity:.92">Réviser le droit avec les textes officiels · {ADRESSE}</div>
  </div>
  <div style="width:3px;height:96px;background:{m.OR}"></div>
  {logo("symbole", "inverse", 104, "center")}
</div>"""
    profil = f"""
<div style="width:1584px;height:396px;background:{m.PAPIER};display:flex;align-items:center;justify-content:flex-end;padding:0 110px;gap:48px;border-bottom:12px solid {m.FORET}">
  <div style="text-align:right">
    <div class="serif" style="font-size:58px;line-height:1.1">{SIGNATURE}</div>
    <div style="font-size:24px;margin-top:14px;color:#4a524d">Réviser le droit avec les textes officiels · <b style="color:{m.FORET}">{ADRESSE}</b></div>
  </div>
  {logo("symbole", "couleur", 170, "center")}
</div>"""
    return [
        (page(entreprise, 1128, 191, STYLE), 1128, 191, RESEAUX / "couvertures" / "linkedin-entreprise-1128x191.png", 2000),
        (page(profil, 1584, 396, STYLE), 1584, 396, RESEAUX / "couvertures" / "linkedin-profil-1584x396.png", 2000),
    ]


def instagram():
    publication = f"""
<div style="width:1080px;height:1350px;background:{m.PAPIER};padding:96px 84px;display:flex;flex-direction:column;gap:48px">
  {logo("horizontal", "couleur", 64)}
  <div class="serif" style="font-size:76px;line-height:1.08">Une question,<br>une réponse sourcée.</div>
  {carte_reponse(32)}
  <div style="margin-top:auto;display:flex;justify-content:space-between;align-items:center;font-size:28px">
    <span style="color:#4a524d">Chaque réponse cite ses sources.</span>
    <b style="color:{m.FORET}">{ADRESSE}</b>
  </div>
</div>"""
    story = f"""
<div style="width:1080px;height:1920px;background:{m.FORET};color:{m.SURFACE};display:flex;flex-direction:column;align-items:center;justify-content:center;gap:56px;padding:0 96px;text-align:center">
  {logo("principal", "inverse", 420, "center")}
  <div class="serif" style="font-size:74px;line-height:1.1">{SIGNATURE}</div>
  <div style="font-size:36px;line-height:1.4;opacity:.95">Réviser le droit avec les textes officiels.</div>
  <div style="margin-top:80px;font-size:34px;font-weight:600;border:3px solid {m.OR};border-radius:999px;padding:22px 44px">{ADRESSE}</div>
</div>"""
    taches = [
        (page(publication, 1080, 1350, STYLE), 1080, 1350, RESEAUX / "modeles" / "instagram-publication-1080x1350.png", 2000),
        (page(story, 1080, 1920, STYLE), 1080, 1920, RESEAUX / "modeles" / "instagram-story-1080x1920.png", 2000),
    ]
    # Couvertures des « stories a la une » : seul le disque central est visible.
    for nom, contenu in [
        ("signet", logo("symbole", "inverse", 460, "center")),
        ("articles", f'<span class="serif" style="font-size:420px;line-height:1;font-weight:500">§</span>'),
        ("questions", f'<span class="serif" style="font-size:420px;line-height:1;font-weight:500">?</span>'),
    ]:
        corps = f"""
<div style="width:1080px;height:1920px;background:{m.FORET};color:{m.SURFACE};display:grid;place-items:center">
  <div style="width:720px;height:720px;border-radius:50%;border:6px solid {m.OR};display:grid;place-items:center">{contenu}</div>
</div>"""
        taches.append((page(corps, 1080, 1920, STYLE), 1080, 1920, RESEAUX / "modeles" / f"instagram-a-la-une-{nom}.png", 2000))
    return taches


if __name__ == "__main__":
    taches = og() + profils() + youtube() + linkedin() + instagram()
    rendre(taches)
    print(f"{len(taches)} images")
