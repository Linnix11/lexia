"""Trois videos verticales (9:16, 1080 x 1920) sous forme de pages HTML animees, et leurs couvertures.

  01-intro-logo.html             6 s   le signet se deroule, « lexia », la signature
  02-demo-question-reponse.html  14 s  « une question, une reponse sourcee » (reconstitution de l'interface)
  03-carte-de-fin.html           7 s   logo, signature, adresse du site

Le texte juridique de la demo (Code civil, articles 1137 et 1131) est celui releve pour le plan marketing
(docs/marketing/contenus-mois-1.md, P11), avec ses liens Legifrance.

Usage, depuis la racine du depot : python3 -I brand/outils/videos.py
Les couvertures (PNG) sont capturees a un instant donne grace au parametre ?t= de commun.js.
Pour l'export MP4, voir brand/videos/enregistrer.md.
"""
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))

import marque as m  # noqa: E402
from rendu import rendre_url  # noqa: E402

VIDEOS = ICI.parent / "videos"
INSEC = " "


def signet(hauteur, t0, variante="couleur"):
    """Signet anime (grille 64) : corps a t0, liseré a t0 + 0,4 s, signe a t0 + 0,8 s."""
    corps, lisere, signe = (m.FORET, m.OR, m.SURFACE) if variante == "couleur" else (m.SURFACE, m.OR, m.FORET)
    largeur = hauteur * (m.D - m.G) / (m.BAS - m.HAUT)
    return (
        f'<svg class="signet" viewBox="{m.G} {m.HAUT} {m.D - m.G} {m.BAS - m.HAUT}" width="{largeur:.0f}" height="{hauteur}" aria-hidden="true">'
        f'<path class="corps" style="animation-delay:{t0:.2f}s" d="{m.CORPS_CHEMIN}" fill="{corps}"/>'
        f'<path class="lisere" style="animation-delay:{t0 + 0.4:.2f}s" d="{m.LISERE_CHEMIN}" fill="{lisere}"/>'
        f'<path class="signe" style="animation-delay:{t0 + 0.8:.2f}s" d="{m.signe_chemin()}" fill="{signe}"/></svg>'
    )


def mot(hauteur_l, t0, teinte):
    """« lexia » anime lettre par lettre ; hauteur_l : hauteur du « l » en px."""
    lettres, largeur = m.mot_chemins(0, m.MOT_HAUTEUR_L)
    k = hauteur_l / m.MOT_HAUTEUR_L
    chemins = "".join(f'<path style="animation-delay:{t0 + i * 0.09:.2f}s" d="{d}"/>' for i, d in enumerate(lettres))
    return (
        f'<svg class="mot" viewBox="0 0 {largeur:.2f} {m.MOT_HAUTEUR_L + 0.7}" width="{largeur * k:.0f}" '
        f'height="{(m.MOT_HAUTEUR_L + 0.7) * k:.0f}" role="img" aria-label="{m.MOT}"><g fill="{teinte}">{chemins}</g></svg>'
    )


def apparait(t, duree=0.6):
    return f"animation:apparait {duree}s var(--doux) {t:.2f}s both"


def fond(t, duree=0.5):
    return f"animation:fond {duree}s ease-out {t:.2f}s both"


def page(titre, duree, scene, style_scene="", style=""):
    return f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titre}</title>
<link rel="stylesheet" href="commun.css">
<style>{style}</style>
</head>
<body>
<div class="cadre"><div class="scene" data-duree="{duree}" style="{style_scene}">
{scene}
</div></div>
<div class="commandes">
  <button type="button" data-rejouer>Rejouer</button>
  <span data-horloge></span>
  <a href="?enregistrer">Mode enregistrement</a>
  <a href="enregistrer.md">Procédure</a>
</div>
<p class="avis-mouvement" hidden>Votre système demande moins de mouvement : la vidéo est affichée à sa dernière
image. Ajoutez <code>?mouvement</code> à l’adresse pour la lire quand même.</p>
<script src="commun.js"></script>
</body>
</html>
"""


def intro():
    scene = f"""
<div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:56px;padding:0 96px;text-align:center">
  {signet(440, 0.2)}
  <div style="margin-top:-8px">{mot(150, 1.4, m.ENCRE)}</div>
  <div class="serif" style="font-size:72px;line-height:1.1;{apparait(2.7)}">Le droit, sources à l’appui.</div>
  <div style="font-size:38px;line-height:1.4;color:#4a524d;{apparait(3.4)}">Réviser le droit avec les textes officiels.</div>
</div>"""
    return page("Lexia, vidéo 1 : intro du logo", 6, scene)


def demo():
    reponse_1 = "Le dol est le fait pour un contractant d’obtenir le consentement de l’autre par des manœuvres ou des mensonges"
    reponse_2 = "Comme les autres vices du consentement, il est une cause de nullité relative du contrat"
    style = f"""
.carte {{ position:absolute; left:84px; right:84px; background:var(--surface); border:2px solid var(--ligne); border-radius:28px; }}
.cite {{ display:inline-block; color:var(--foret); font-weight:600; border-bottom:3px solid #b2c2b7; border-radius:6px; padding:0 4px; }}
.cite.active {{ animation: active 1.6s ease-in-out 7.0s both; }}
@keyframes active {{ 0% {{ background:transparent; }} 20%,100% {{ background:var(--menthe); }} }}
.envoyer {{ animation: presse .4s ease-in-out 2.9s both; }}
@keyframes presse {{ 50% {{ transform: scale(.88); }} }}
.signe-source {{ display:grid; place-items:center; width:72px; height:72px; border-radius:14px; background:#eef1eb; color:var(--foret);
  font:600 40px/1 "Source Serif 4", serif; flex-shrink:0; }}
"""
    scene = f"""
<div style="position:absolute;left:84px;top:190px;{fond(0)}">{m.logo_horizontal("couleur").replace("<svg ", '<svg height="64" style="height:64px;width:auto;display:block" ', 1)}</div>
<div class="serif" style="position:absolute;left:84px;right:84px;top:300px;font-size:76px;line-height:1.08;animation:apparait .6s var(--doux) .2s both, disparait .4s ease-in 10.6s forwards">Une question,<br>une réponse sourcée.</div>
<div class="serif" style="position:absolute;left:84px;right:84px;top:300px;font-size:64px;line-height:1.12;{apparait(11.0)}">Chaque réponse cite ses sources. Un clic ouvre le texte officiel.</div>

<div class="carte" style="top:540px;height:150px;display:flex;align-items:center;gap:24px;padding:0 24px 0 40px;{apparait(0.7)}">
  <div style="flex:1;font-size:42px"><span data-taper="1.2,0.065">Qu’est-ce que le dol{INSEC}?</span></div>
  <div class="envoyer" style="width:96px;height:96px;border-radius:20px;background:var(--foret);display:grid;place-items:center">
    <svg width="44" height="44" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h13M12 5l7 7-7 7" fill="none" stroke="#fffefa" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
  </div>
</div>

<div class="carte" style="top:730px;padding:44px 44px 48px;font-size:38px;line-height:1.48;{apparait(3.4)}">
  <div class="surtitre" style="font-size:24px;margin-bottom:18px">Réponse</div>
  <span style="{fond(3.9, 0.7)}">{reponse_1}</span> <span class="cite active" style="{fond(4.6, 0.3)}">[1]</span><span style="{fond(4.6, 0.3)}">.</span>
  <span style="{fond(5.3, 0.7)}">{reponse_2}</span> <span class="cite" style="{fond(6.0, 0.3)}">[2]</span><span style="{fond(6.0, 0.3)}">.</span>
</div>

<div class="carte" style="top:1250px;padding:40px 44px;font-size:32px;line-height:1.45;border-color:var(--foret);{apparait(7.6, 0.7)}">
  <div style="display:flex;gap:24px;align-items:center">
    <span class="signe-source">§</span>
    <div><div style="font-weight:600;font-size:36px">Code civil, article 1137</div>
    <div style="color:var(--gris);font-size:28px;margin-top:4px">Version depuis le 1<sup>er</sup> octobre 2018</div></div>
  </div>
  <p class="serif" style="font-size:36px;line-height:1.4;margin:28px 0 22px;font-variation-settings:'opsz' 20">« Le dol est le fait pour un contractant d’obtenir le consentement de l’autre par des manœuvres ou des mensonges. »</p>
  <div style="color:var(--foret);font-weight:600">Ouvrir sur Légifrance ↗</div>
</div>

<div style="position:absolute;right:84px;top:206px;font-size:26px;color:#4a524d;{fond(0)}">Reconstitution de l’interface</div>
<div style="position:absolute;left:84px;right:84px;top:1560px;font-size:34px;font-weight:600;color:var(--foret);{fond(12.0)}">lexia-axionstudio.cloud</div>"""
    return page("Lexia, vidéo 2 : une question, une réponse sourcée", 14, scene, style=style)


def fin():
    scene = f"""
<div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:52px;padding:0 96px;text-align:center;color:var(--surface)">
  {signet(400, 0.1, "inverse")}
  <div style="margin-top:-6px">{mot(140, 1.1, m.SURFACE)}</div>
  <div class="serif" style="font-size:70px;line-height:1.1;{apparait(2.0)}">Le droit, sources à l’appui.</div>
  <div style="margin-top:40px;font-size:46px;font-weight:600;border:4px solid var(--or);border-radius:999px;padding:26px 54px;{apparait(2.7)}">lexia-axionstudio.cloud</div>
  <div style="font-size:34px;line-height:1.45;{apparait(3.4)}">Gratuit avec un compte{INSEC}: 10 questions<br>et 2 questionnaires par jour.<br>Conditions d’inscription dans les CGU.</div>
</div>"""
    return page("Lexia, vidéo 3 : carte de fin", 7, scene, style_scene=f"background:{m.FORET}")


PAGES = {
    "01-intro-logo.html": (intro, 5.6),
    "02-demo-question-reponse.html": (demo, 9.5),
    "03-carte-de-fin.html": (fin, 6.5),
}


if __name__ == "__main__":
    VIDEOS.mkdir(parents=True, exist_ok=True)
    for nom, (fabrique, instant) in PAGES.items():
        (VIDEOS / nom).write_text(fabrique(), encoding="utf-8")
        couverture = VIDEOS / "couvertures" / nom.replace(".html", ".png")
        rendre_url(f"{(VIDEOS / nom).as_uri()}?capture&t={instant}", 1080, 1920, couverture, attente=2500)
        print(nom, "et", couverture.name)
