"""Application de production : l'API sous /api et le panel etudiant (web/dist) sur /.

Un seul processus, un seul domaine : pas de CORS a configurer.

    cd web && npm ci && npm run build && cd ..
    uvicorn api.serveur:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips 127.0.0.1

(--proxy-headers : derriere nginx, l'adresse IP reelle de l'etudiant sert a la limite de requetes.)
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.config import ROOT
from api.main import create_app

DIST = ROOT / "web" / "dist"


def creer_serveur(dist: Path = DIST, api: FastAPI | None = None) -> FastAPI:
    racine = FastAPI(title="Lexia", docs_url=None, redoc_url=None, openapi_url=None)
    racine.mount("/api", api or create_app())

    # introuvable.html et chemins-application.json sont ecrits par le prerendu (web/scripts/prerendu.mjs, D134)
    for requis in ("index.html", "introuvable.html", "chemins-application.json"):
        if not (dist / requis).exists():
            raise RuntimeError(f"Front non compile : {dist / requis} absent. Lancer `npm run build` dans web/.")
    # Ecrans du routeur du front (espace, connexion, invitation...) : seules adresses servies par la coquille
    ecrans = frozenset(json.loads((dist / "chemins-application.json").read_text(encoding="utf-8")))
    # Coquille vide et page introuvable : pas d'index (audit SEO du 24/11, D134). En-tete plutot que balise seule :
    # il vaut aussi pour un robot qui ne lit pas le HTML.
    sans_index = {"Cache-Control": "no-cache", "X-Robots-Tag": "noindex"}

    racine.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    pages = (dist / "pages").resolve()

    # HEAD aussi : des robots et des verificateurs de liens testent une adresse par HEAD (405 avant D116).
    @racine.api_route("/{chemin:path}", methods=["GET", "HEAD"], include_in_schema=False)
    async def front(chemin: str):  # async : ne prend pas de thread, le site reste servi si Gemini est lent
        if "\x00" in chemin:  # Path.resolve leve ValueError : 500 au lieu d'un refus (audit du 23/11, B10)
            raise HTTPException(400, "Adresse invalide.")
        # fichiers publics (favicon, sitemap.xml, llms.txt...) ; dist/pages/ n'est servi que par son adresse publique
        # .html de la racine (coquille, page introuvable) : jamais a leur propre adresse (/index.html en double, D134)
        fichier = (dist / chemin).resolve()
        if (chemin and fichier.is_file() and dist.resolve() in fichier.parents and pages not in fichier.parents
                and fichier.suffix != ".html"):
            # robots.txt, sitemap.xml, llms.txt : relus a chaque publication, pas gardes 4 h par Cloudflare (D11)
            return FileResponse(fichier, headers={"Cache-Control": "no-cache"} if fichier.suffix in (".txt", ".xml") else None)
        if chemin.startswith("api/"):
            raise HTTPException(404)
        # Ecrans du routeur du front, meme regle de barre finale que web/src/Site.tsx. Comparaison exacte : sur un
        # disque insensible a la casse (Mac), /Tarifs trouverait sinon pages/tarifs (D134).
        route = "/" + chemin.strip("/")
        if route in ecrans or route == "/":
            # Page publique prerendue a la compilation (D116) : /tarifs -> dist/pages/tarifs/index.html
            prerendue = (pages / chemin.strip("/") / "index.html").resolve()
            if prerendue.is_file() and (prerendue.parent == pages or pages in prerendue.parents):
                return FileResponse(prerendue, headers={"Cache-Control": "no-cache"})
            # Autre ecran : index.html, l'application le dessine
            return FileResponse(dist / "index.html", headers=sans_index)
        # Toute autre adresse : vraie 404, avec la page introuvable prerendue (liens vers l'accueil, matieres, guides)
        return FileResponse(dist / "introuvable.html", status_code=404, headers=sans_index)

    return racine


def demarrer_amorce(api: FastAPI) -> threading.Thread | None:
    """Premier parcours des vecteurs et premier reclassement dans un fil a part, des le demarrage (recette du 23/11,
    R-2) : la premiere question apres une publication ne paie plus ~17 s. Le service repond pendant l'amorce ; une
    question posee pendant ce temps fait le meme parcours qu'avant, sans attendre l'amorce."""
    lexia = getattr(api.state, "lexia", None)
    if lexia is None:
        return None
    fil = threading.Thread(target=lexia.amorcer, name="amorce", daemon=True)
    fil.start()
    return fil


def __getattr__(name: str):
    if name == "app":
        logging.basicConfig(level=logging.INFO)
        global app
        api = create_app()
        app = creer_serveur(api=api)
        demarrer_amorce(api)
        return app
    raise AttributeError(name)
