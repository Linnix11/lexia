"""Genere les logos (SVG et PNG) et les icones (favicon, ICO, PNG 16 a 512, Apple, maskable) du kit.

Usage, depuis la racine du depot :
    python3 -I brand/outils/glyphes.py      # une fois, ou apres un changement de police
    python3 -I brand/outils/generer.py      # logos et icones
    python3 -I brand/outils/images.py       # images des reseaux et Open Graph

Besoins : Python 3 avec fontTools et Pillow, Google Chrome (rendu des PNG).
"""
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))

from PIL import Image  # noqa: E402

import marque as m  # noqa: E402
from rendu import page, rendre  # noqa: E402

KIT = ICI.parent
LOGOS = KIT / "logos"
ICONES = KIT / "icones"

VARIANTES = ["couleur", "inverse", "mono-clair", "mono-fonce"]
FORMES = {
    "symbole": m.logo_symbole,
    "horizontal": m.logo_horizontal,
    "principal": m.logo_principal,
}
# Tailles d'export : cote pour le symbole, largeur pour les deux autres.
TAILLES = {"symbole": [64, 128, 256, 512, 1024], "horizontal": [320, 640, 1280, 2560], "principal": [256, 512, 1024]}


def proportions(svg_texte):
    vb = svg_texte.split('viewBox="')[1].split('"')[0].split()
    return float(vb[2]), float(vb[3])


def image(svg_texte, largeur, hauteur, fond=None):
    style = f"body{{background:{fond}}}" if fond else ""
    corps = svg_texte.replace("<svg ", f'<svg width="{largeur}" height="{hauteur}" ', 1)
    return page(corps, largeur, hauteur, style)


def logos():
    taches = []
    for forme, fabrique in FORMES.items():
        for variante in VARIANTES:
            texte = fabrique(variante)
            nom = f"lexia-{forme}-{variante}"
            (LOGOS / "svg").mkdir(parents=True, exist_ok=True)
            (LOGOS / "svg" / f"{nom}.svg").write_text(texte, encoding="utf-8")
            w, h = proportions(texte)
            for taille in TAILLES[forme]:
                largeur = taille
                hauteur = round(taille * h / w)
                taches.append((image(texte, largeur, hauteur), largeur, hauteur, LOGOS / "png" / f"{nom}-{largeur}.png"))
    rendre(taches)
    return len(taches)


def icones():
    ICONES.mkdir(parents=True, exist_ok=True)
    favicon = m.favicon()
    favicon_petit = m.favicon(petit=True)
    (ICONES / "favicon.svg").write_text(favicon, encoding="utf-8")
    app = m.icone_app()
    (ICONES / "icone-app.svg").write_text(app, encoding="utf-8")
    maskable = m.icone_app(taille_signet=0.56)
    (ICONES / "icone-maskable.svg").write_text(maskable, encoding="utf-8")

    taches = [
        (image(favicon_petit, 16, 16), 16, 16, ICONES / "favicon-16.png"),
        (image(favicon, 32, 32), 32, 32, ICONES / "favicon-32.png"),
        (image(favicon, 48, 48), 48, 48, ICONES / "favicon-48.png"),
        (image(app, 180, 180), 180, 180, ICONES / "apple-touch-icon.png"),
    ]
    for t in (64, 96, 128, 192, 256, 384, 512, 1024):
        taches.append((image(app, t, t), t, t, ICONES / f"icone-{t}.png"))
    for t in (192, 512):
        taches.append((image(maskable, t, t), t, t, ICONES / f"icone-maskable-{t}.png"))
    rendre(taches)

    # ICO a trois tailles, chacune dessinee pour sa taille (16 px sans le signe §).
    images = [Image.open(ICONES / f"favicon-{t}.png").convert("RGBA") for t in (16, 32, 48)]
    images[2].save(ICONES / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48)], append_images=images[:2])

    manifeste = {
        "name": "Lexia, l'espace d'étude juridique",
        "short_name": "Lexia",
        "lang": "fr",
        "start_url": "/app",
        "scope": "/",
        "display": "standalone",
        "background_color": m.PAPIER,
        "theme_color": m.PAPIER,
        "icons": [
            {"src": "/icone-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "/icone-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": "/icone-maskable-192.png", "sizes": "192x192", "type": "image/png", "purpose": "maskable"},
            {"src": "/icone-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }
    (ICONES / "manifest-exemple.json").write_text(json.dumps(manifeste, ensure_ascii=False, indent=2) + "\n")
    return len(taches)


if __name__ == "__main__":
    if "--icones" not in sys.argv:
        n = logos()
        print(f"logos : {n} PNG")
    n = icones()
    print(f"icones : {n} PNG, favicon.ico, favicon.svg, manifest-exemple.json")
