"""Routes de compte : inscription, connexion, deconnexion, profil, suppression.

Session : cookie `lexia_session` HttpOnly, SameSite=Lax, Secure en HTTPS. Les requetes qui
modifient l'etat sont en JSON (pas de formulaire HTML cross-site possible) et l'en-tete Origin,
s'il est present, doit correspondre au site : protection contre les requetes intersites.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from api.comptes import DUREE_SESSION, Comptes, ErreurCompte, Utilisateur
from api.plans import FORMULES

COOKIE = "lexia_session"


class Inscription(BaseModel):
    email: str = Field(max_length=254)
    mot_de_passe: str = Field(max_length=256)
    accepte_cgu: bool


class Connexion(BaseModel):
    email: str = Field(max_length=254)
    mot_de_passe: str = Field(max_length=256)


class Suppression(BaseModel):
    mot_de_passe: str = Field(max_length=256)


class Freins:
    """Limite les essais de connexion : par IP (par minute) et par e-mail (echecs sur 15 min)."""

    def __init__(self, par_ip_minute: int = 10, echecs_email: int = 5):
        self.par_ip, self.max_echecs = par_ip_minute, echecs_email
        self._ip: dict[str, deque] = defaultdict(deque)
        self._echecs: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    @staticmethod
    def _purger(q: deque, fenetre: float, now: float) -> None:
        while q and now - q[0] > fenetre:
            q.popleft()

    def verifier(self, ip: str, email: str) -> None:
        now = time.monotonic()
        with self._lock:
            q = self._ip[ip]
            self._purger(q, 60, now)
            if len(q) >= self.par_ip:
                raise HTTPException(429, "Trop de tentatives : réessayez dans une minute.")
            q.append(now)
            e = self._echecs[email]
            self._purger(e, 900, now)
            if len(e) >= self.max_echecs:
                raise HTTPException(429, "Trop d'échecs de connexion pour ce compte : réessayez dans 15 minutes.")

    def echec(self, email: str) -> None:
        with self._lock:
            self._echecs[email].append(time.monotonic())

    def succes(self, email: str) -> None:
        with self._lock:
            self._echecs.pop(email, None)


def verifier_origine(request: Request) -> None:
    origine = request.headers.get("origin")
    if origine and urlparse(origine).netloc != request.headers.get("host", ""):
        raise HTTPException(403, "Origine de la requête non autorisée.")


def profil(comptes: Comptes, u: Utilisateur) -> dict:
    f = u.formule
    return {
        "email": u.email,
        "cree_le": u.cree_le,
        "formule": f.as_dict(),
        "formule_fin": u.formule_fin if u.formule_id == f.id else None,
        "usage": comptes.usage(u.id),
        "admin": u.admin,
    }


def creer_routes(comptes: Comptes) -> tuple[APIRouter, callable]:
    """Renvoie (routes /auth, dependance utilisateur_requis)."""
    router = APIRouter()
    freins = Freins()

    def utilisateur_requis(request: Request) -> Utilisateur:
        u = comptes.session(request.cookies.get(COOKIE))
        if u is None:
            raise HTTPException(401, "Connectez-vous pour utiliser l'assistant.")
        return u

    def _poser_cookie(request: Request, response: Response, jeton: str) -> None:
        response.set_cookie(COOKIE, jeton, max_age=int(DUREE_SESSION.total_seconds()), httponly=True,
                            samesite="lax", secure=request.url.scheme == "https", path="/")

    def _ip(request: Request) -> str:
        return request.client.host if request.client else "inconnu"

    @router.post("/inscription", status_code=201, dependencies=[Depends(verifier_origine)])
    def inscription(req: Inscription, request: Request, response: Response):
        if not req.accepte_cgu:
            raise HTTPException(422, "Vous devez accepter les conditions générales d'utilisation.")
        freins.verifier(_ip(request), "inscription")
        try:
            u = comptes.creer(req.email, req.mot_de_passe)
        except ErreurCompte as e:
            raise HTTPException(422, str(e)) from None
        _poser_cookie(request, response, comptes.ouvrir_session(u.id))
        return profil(comptes, u)

    @router.post("/connexion", dependencies=[Depends(verifier_origine)])
    def connexion(req: Connexion, request: Request, response: Response):
        email = req.email.strip().lower()
        freins.verifier(_ip(request), email)
        u = comptes.authentifier(email, req.mot_de_passe)
        if u is None:
            freins.echec(email)
            raise HTTPException(401, "E-mail ou mot de passe incorrect.")
        freins.succes(email)
        _poser_cookie(request, response, comptes.ouvrir_session(u.id))
        return profil(comptes, u)

    @router.post("/deconnexion", status_code=204, dependencies=[Depends(verifier_origine)])
    def deconnexion(request: Request, response: Response):
        comptes.fermer_session(request.cookies.get(COOKIE))
        response.delete_cookie(COOKIE, path="/")

    @router.get("/session")
    def session(request: Request):
        """Profil si connecte, sinon null (sans erreur : appele a chaque chargement du site)."""
        u = comptes.session(request.cookies.get(COOKIE))
        return profil(comptes, u) if u else None

    @router.get("/moi")
    def moi(u: Utilisateur = Depends(utilisateur_requis)):
        return profil(comptes, u)

    @router.post("/supprimer", status_code=204, dependencies=[Depends(verifier_origine)])
    def supprimer(req: Suppression, request: Request, response: Response,
                  u: Utilisateur = Depends(utilisateur_requis)):
        freins.verifier(_ip(request), u.email)
        if comptes.authentifier(u.email, req.mot_de_passe) is None:
            freins.echec(u.email)
            raise HTTPException(401, "Mot de passe incorrect.")
        comptes.supprimer(u.id)
        response.delete_cookie(COOKIE, path="/")

    return router, utilisateur_requis


def routes_formules() -> APIRouter:
    router = APIRouter()

    @router.get("/formules")
    def formules():
        return [f.as_dict() for f in FORMULES.values()]

    return router
