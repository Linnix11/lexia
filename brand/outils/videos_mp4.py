"""Export MP4 image par image des videos verticales (1080 x 1920, 30 images par seconde, H.264).

Chaque image est capturee par Chrome sans interface a l'instant exact (parametre ?capture&t=), puis ffmpeg
assemble la suite d'images. Le resultat ne depend ni de la vitesse de la machine ni d'un enregistrement d'ecran.

Necessite ffmpeg (logiciel libre, LGPL/GPL), absent de ce Mac au 23 novembre 2026. Installation :
    brew install ffmpeg
Usage, depuis la racine du depot :
    python3 -I brand/outils/videos_mp4.py              # les trois videos
    python3 -I brand/outils/videos_mp4.py 01-intro-logo
Duree : environ 2 a 4 minutes par video (une capture Chrome par image, 4 en parallele).
"""
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))

from rendu import rendre_url  # noqa: E402

VIDEOS = ICI.parent / "videos"
IPS = 30
DUREES = {"01-intro-logo": 6, "02-demo-question-reponse": 14, "03-carte-de-fin": 7}


def exporter(nom, ffmpeg):
    duree = DUREES[nom]
    page = (VIDEOS / f"{nom}.html").as_uri()
    with tempfile.TemporaryDirectory() as tmp:
        def image(i):
            rendre_url(f"{page}?capture&t={i / IPS:.4f}", 1080, 1920, Path(tmp) / f"{i:05d}.png", attente=1500)

        with ThreadPoolExecutor(4) as pool:
            list(pool.map(image, range(duree * IPS)))
        sortie = VIDEOS / "mp4" / f"{nom}.mp4"
        sortie.parent.mkdir(exist_ok=True)
        subprocess.run(
            [ffmpeg, "-y", "-loglevel", "error", "-framerate", str(IPS), "-i", f"{tmp}/%05d.png",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart", str(sortie)],
            check=True,
        )
    return sortie


if __name__ == "__main__":
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        sys.exit("ffmpeg introuvable. Installez-le (brew install ffmpeg) ou suivez brand/videos/enregistrer.md, "
                 "partie « Sans ffmpeg ».")
    noms = sys.argv[1:] or list(DUREES)
    for nom in noms:
        print("ecrit :", exporter(nom, ffmpeg))
