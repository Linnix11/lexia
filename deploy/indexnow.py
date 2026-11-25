#!/usr/bin/env python3
"""IndexNow (D134) : signale aux moteurs qui suivent ce protocole gratuit (Bing, Yandex, Seznam, Naver...) les
adresses du sitemap apres une publication. Prepare, PAS ACTIVE : rien ne part sans --envoyer, et deploy/publier.sh
ne l'appelle qu'avec LEXIA_INDEXNOW=1.

    python3 deploy/indexnow.py             # essai a blanc : affiche ce qui serait envoye, aucune connexion
    python3 deploy/indexnow.py --envoyer   # verifie que le fichier de cle est en ligne, puis envoie

La cle n'est pas un secret : elle est publiee a https://<site>/<cle>.txt (web/public/<cle>.txt, copie par Vite a la
racine du front) pour prouver que le site autorise l'envoi. Changer de cle : nouvelle valeur ici et fichier renomme
(tests/test_indexnow.py verifie l'accord). Bibliotheque standard seulement : lance depuis le Mac par python3.
Mode d'emploi pour l'editeur : docs/seo-geo.md, partie 7.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit

CLE = "f7cd81d8dd2ed8dd0079972257ad7049"
ORIGINE = "https://lexia-axionstudio.cloud"
POINT_D_ENTREE = "https://api.indexnow.org/indexnow"   # point commun, partage avec les moteurs participants
SITEMAP = Path(__file__).resolve().parents[1] / "web" / "dist" / "sitemap.xml"
MAX_ADRESSES = 10_000   # plafond d'un envoi selon le protocole
_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"

REPONSES = {
    200: "recu",
    202: "recu, cle en cours de verification par le moteur",
    400: "requete mal formee",
    403: "cle refusee : fichier de cle absent ou different en ligne",
    422: "adresses hors du site, ou cle differente du fichier",
    429: "trop d'envois, reessayer plus tard",
}


def adresses(xml: str) -> list[str]:
    """Adresses <loc> du sitemap compile (web/dist/sitemap.xml), toutes sur le site."""
    locs = [e.text.strip() for e in ET.fromstring(xml).iter(f"{_NS}loc") if e.text and e.text.strip()]
    if not locs:
        raise ValueError("sitemap vide : lancer npm run build dans web/")
    hors = [u for u in locs if not u.startswith(ORIGINE + "/")]
    if hors:
        raise ValueError(f"adresses hors du site {ORIGINE} : {', '.join(hors[:3])}")
    if len(locs) > MAX_ADRESSES:
        raise ValueError(f"{len(locs)} adresses : plus de {MAX_ADRESSES}, a envoyer en plusieurs fois")
    return locs


def charge(urls: list[str]) -> dict:
    return {"host": urlsplit(ORIGINE).hostname, "key": CLE, "keyLocation": f"{ORIGINE}/{CLE}.txt", "urlList": urls}


def cle_en_ligne(ouvrir=urllib.request.urlopen) -> bool:
    """Le moteur lit ce fichier pour valider l'envoi : sans lui, chaque envoi serait refuse (403)."""
    requete = urllib.request.Request(f"{ORIGINE}/{CLE}.txt", headers={"User-Agent": "Lexia-publication"})
    try:
        with ouvrir(requete, timeout=10) as r:
            return r.read().decode("utf-8").strip() == CLE
    except (urllib.error.URLError, OSError, UnicodeDecodeError):
        return False


def envoyer(donnees: dict, ouvrir=urllib.request.urlopen) -> int:
    requete = urllib.request.Request(
        POINT_D_ENTREE, data=json.dumps(donnees).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "Lexia-publication"})
    try:
        with ouvrir(requete, timeout=30) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def main(argv: list[str] | None = None, ouvrir=urllib.request.urlopen) -> int:
    p = argparse.ArgumentParser(description="Signale les adresses du sitemap a IndexNow (a blanc par defaut).")
    p.add_argument("--envoyer", action="store_true", help="envoi reel ; sans cette option, rien ne part")
    p.add_argument("--sitemap", default=str(SITEMAP), help="sitemap compile (defaut : web/dist/sitemap.xml)")
    args = p.parse_args(argv)

    donnees = charge(adresses(Path(args.sitemap).read_text(encoding="utf-8")))
    n = len(donnees["urlList"])
    if not args.envoyer:
        print(f"IndexNow, essai a blanc : {n} adresses seraient envoyees a {POINT_D_ENTREE}. Rien n'est parti.")
        print(json.dumps(donnees, indent=2, ensure_ascii=False))
        return 0
    if not cle_en_ligne(ouvrir):
        print(f"Refus : fichier de cle {donnees['keyLocation']} absent ou different en ligne. Publier d'abord le "
              "front (web/public/<cle>.txt), puis relancer.", file=sys.stderr)
        return 1
    code = envoyer(donnees, ouvrir)
    message = f"IndexNow : {n} adresses, reponse {code} ({REPONSES.get(code, 'inattendue')})"
    print(message, file=sys.stdout if code in (200, 202) else sys.stderr)
    return 0 if code in (200, 202) else 1


if __name__ == "__main__":
    sys.exit(main())
