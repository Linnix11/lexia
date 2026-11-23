"""Application de production : l'API sous /api et le panel etudiant (web/dist) sur /.

Un seul processus, un seul domaine : pas de CORS a configurer.

    cd web && npm ci && npm run build && cd ..
    uvicorn api.serveur:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips 127.0.0.1

(--proxy-headers : derriere nginx, l'adresse IP reelle de l'etudiant sert a la limite de requetes.)
"""

from __future__ import annotations

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

    if not (dist / "index.html").exists():
        raise RuntimeError(f"Front non compile : {dist / 'index.html'} absent. Lancer `npm run build` dans web/.")

    racine.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    pages = (dist / "pages").resolve()

    # HEAD aussi : des robots et des verificateurs de liens testent une adresse par HEAD (405 avant D116).
    @racine.api_route("/{chemin:path}", methods=["GET", "HEAD"], include_in_schema=False)
    async def front(chemin: str):  # async : ne prend pas de thread, le site reste servi si Gemini est lent
        if "\x00" in chemin:  # Path.resolve leve ValueError : 500 au lieu d'un refus (audit du 23/11, B10)
            raise HTTPException(400, "Adresse invalide.")
        # fichiers publics (favicon, sitemap.xml, llms.txt...) ; dist/pages/ n'est servi que par son adresse publique
        fichier = (dist / chemin).resolve()
        if chemin and fichier.is_file() and dist.resolve() in fichier.parents and pages not in fichier.parents:
            # robots.txt, sitemap.xml, llms.txt : relus a chaque publication, pas gardes 4 h par Cloudflare (D11)
            return FileResponse(fichier, headers={"Cache-Control": "no-cache"} if fichier.suffix in (".txt", ".xml") else None)
        if chemin.startswith("api/"):
            raise HTTPException(404)
        # Page publique prerendue a la compilation (D116) : /tarifs -> dist/pages/tarifs/index.html
        prerendue = (pages / chemin.strip("/") / "index.html").resolve()
        if prerendue.is_file() and (prerendue.parent == pages or pages in prerendue.parents):
            return FileResponse(prerendue, headers={"Cache-Control": "no-cache"})
        # sinon index.html : l'application gere elle-meme ses ecrans
        return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})

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
