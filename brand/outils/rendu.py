"""Rendu d'une page HTML en PNG avec Google Chrome sans interface (aucune dependance a installer).

Chrome est lance en mode --headless=new, une instance par image, chacune avec son propre profil temporaire,
plusieurs en parallele. Le fond est transparent sauf si la page en peint un.
"""
import os
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
# Sous cette taille de fenetre, Chrome sans interface se bloque : on capture plus grand puis on recadre.
MINI = 200
TYPOS = Path(__file__).resolve().parent.parent / "typographies"

POLICES_CSS = f"""
@font-face {{ font-family: "Source Serif 4"; src: url("file://{TYPOS}/SourceSerif4-Variable.ttf"); font-weight: 200 900; }}
@font-face {{ font-family: "Inter"; src: url("file://{TYPOS}/Inter-Variable.ttf"); font-weight: 100 900; }}
"""


def page(corps, largeur, hauteur, style=""):
    return (
        "<!doctype html><html lang=\"fr\"><head><meta charset=\"utf-8\"><style>"
        + POLICES_CSS
        + f"html,body{{margin:0;padding:0;width:{largeur}px;height:{hauteur}px;overflow:hidden;background:transparent}}"
        + "svg{display:block}"
        + style
        + "</style></head><body>"
        + corps
        + "</body></html>"
    )


def _un(tache):
    html, largeur, hauteur, sortie, attente = tache
    sortie = Path(sortie)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        fichier = Path(tmp) / "page.html"
        fichier.write_text(html, encoding="utf-8")
        cmd = [
            CHROME,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--allow-file-access-from-files",
            "--force-device-scale-factor=1",
            "--default-background-color=00000000",
            f"--user-data-dir={tmp}/profil",
            f"--window-size={max(largeur, MINI)},{max(hauteur, MINI)}",
            f"--screenshot={sortie}",
            fichier.as_uri(),
        ]
        if attente:
            cmd.insert(-2, f"--virtual-time-budget={attente}")
        _lancer(cmd)
        if largeur < MINI or hauteur < MINI:
            with Image.open(sortie) as im:
                im.crop((0, 0, largeur, hauteur)).save(sortie)
    return sortie


def _lancer(cmd, essais=3):
    """Chrome sans interface se bloque parfois au demarrage : on relance (40 s maximum par essai)."""
    for essai in range(essais):
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=40)
            return
        except subprocess.TimeoutExpired:
            if essai == essais - 1:
                raise


def rendre(taches, paralleles=4):
    """taches : liste de (html, largeur, hauteur, chemin_png[, attente_ms]). attente 0 : capture immediate."""
    norm = [(t + (0,))[:5] if len(t) == 4 else t for t in taches]
    with ThreadPoolExecutor(paralleles) as pool:
        return list(pool.map(_un, norm))


def rendre_url(url, largeur, hauteur, sortie, attente=1500):
    """Capture d'une page existante (videos figees a un instant donne avec ?t=)."""
    sortie = Path(sortie)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [
            CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
            "--force-device-scale-factor=1", f"--user-data-dir={tmp}/profil", f"--window-size={largeur},{hauteur}",
            f"--virtual-time-budget={attente}", f"--screenshot={sortie}", url,
        ]
        _lancer(cmd)
    return sortie
