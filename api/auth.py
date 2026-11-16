"""Routes de compte : inscription, connexion, deconnexion, profil, suppression.

Session : cookie `lexia_session` HttpOnly, SameSite=Lax, Secure en HTTPS. Les requetes qui
modifient l'etat sont en JSON (pas de formulaire HTML cross-site possible) et l'en-tete Origin,
s'il est present, doit correspondre au site : protection contre les requetes intersites.
"""

from __future__ import annotations

import hashlib
import secrets
import threading
import time
from collections import defaultdict, deque
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from api import courriel, totp
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


class CodeConnexion(BaseModel):
    jeton: str = Field(max_length=100)
    code: str = Field(max_length=20)


class JetonEmail(BaseModel):
    jeton: str = Field(max_length=100)


class MotDePasseEtCode2FA(BaseModel):
    """Activer ou desactiver la double authentification : mot de passe et code de l'application."""
    mot_de_passe: str = Field(max_length=256)
    code: str = Field(max_length=20)


class AttentesDeuxiemeFacteur:
    """Connexions dont le mot de passe est bon mais le code de l'application pas encore saisi (5 min, 5 essais)."""

    DUREE, ESSAIS = 300, 5

    def __init__(self):
        self._items: dict[str, list] = {}  # empreinte du jeton -> [uid, expiration, essais restants]
        self._lock = threading.Lock()

    def creer(self, uid: int) -> str:
        jeton = secrets.token_urlsafe(32)
        with self._lock:
            now = time.monotonic()
            for k in [k for k, v in self._items.items() if v[1] < now]:
                del self._items[k]
            self._items[hashlib.sha256(jeton.encode()).hexdigest()] = [uid, now + self.DUREE, self.ESSAIS]
        return jeton

    def essai(self, jeton: str) -> int | None:
        """uid si le jeton est valable (et decompte un essai), sinon None."""
        cle = hashlib.sha256(jeton.encode()).hexdigest()
        with self._lock:
            v = self._items.get(cle)
            if v is None or v[1] < time.monotonic() or v[2] <= 0:
                self._items.pop(cle, None)
                return None
            v[2] -= 1
            return v[0]

    def terminer(self, jeton: str) -> None:
        with self._lock:
            self._items.pop(hashlib.sha256(jeton.encode()).hexdigest(), None)


class Freins:
    """Limite les essais de connexion : par IP (par minute) et par e-mail (echecs sur 15 min),
    et les comptes crees par IP sur 24 h (sans plafond, le quota gratuit se contourne en creant des comptes)."""

    def __init__(self, par_ip_minute: int = 10, echecs_email: int = 5, inscriptions_ip_jour: int = 20,
                 echecs_compte: int = 50):
        self.par_ip, self.max_echecs = par_ip_minute, echecs_email
        self.max_inscriptions = inscriptions_ip_jour
        # Plafond par compte, toutes adresses IP confondues : la limite de 5 echecs vise l'adresse qui se
        # trompe (sinon 5 faux mots de passe bloquaient le titulaire), celle-ci arrete une attaque repartie.
        self.max_echecs_compte = echecs_compte
        self._ip: dict[str, deque] = defaultdict(deque)
        self._echecs: dict[str, deque] = defaultdict(deque)
        self._inscriptions: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()
        self._derniere_purge = 0.0

    @staticmethod
    def _purger(q: deque, fenetre: float, now: float) -> None:
        while q and now - q[0] > fenetre:
            q.popleft()

    def _oublier(self, now: float) -> None:
        """Retire les adresses et e-mails dont la fenetre est passee, au plus une fois par minute.
        Sans cela, chaque adresse essayee restait en memoire jusqu'au redemarrage du service."""
        if now - self._derniere_purge < 60:
            return
        self._derniere_purge = now
        for d, fenetre in ((self._ip, 60), (self._echecs, 900), (self._inscriptions, 86400)):
            for k in [k for k, q in d.items() if not q or now - q[-1] > fenetre]:
                del d[k]

    def verifier(self, ip: str, email: str, compte: str | None = None) -> None:
        now = time.monotonic()
        with self._lock:
            self._oublier(now)
            q = self._ip[ip]
            self._purger(q, 60, now)
            if len(q) >= self.par_ip:
                raise HTTPException(429, "Trop de tentatives : réessayez dans une minute.")
            q.append(now)
            e = self._echecs[email]
            self._purger(e, 900, now)
            if len(e) >= self.max_echecs:
                raise HTTPException(429, "Trop d'échecs de connexion pour ce compte : réessayez dans 15 minutes.")
            if compte is not None:
                c = self._echecs[compte]
                self._purger(c, 900, now)
                if len(c) >= self.max_echecs_compte:
                    raise HTTPException(429, "Trop d'échecs de connexion pour ce compte : réessayez dans 15 minutes.")

    def verifier_inscription(self, ip: str) -> None:
        if self.max_inscriptions <= 0:
            return
        with self._lock:
            q = self._inscriptions[ip]
            self._purger(q, 86400, time.monotonic())
            if len(q) >= self.max_inscriptions:
                raise HTTPException(429, "Trop de comptes créés depuis cette connexion aujourd'hui : réessayez demain.")

    def inscrit(self, ip: str) -> None:
        with self._lock:
            self._inscriptions[ip].append(time.monotonic())

    def echec(self, email: str, compte: str | None = None) -> None:
        with self._lock:
            self._echecs[email].append(time.monotonic())
            if compte is not None:
                self._echecs[compte].append(time.monotonic())

    def succes(self, email: str, compte: str | None = None) -> None:
        with self._lock:
            self._echecs.pop(email, None)
            if compte is not None:
                self._echecs.pop(compte, None)


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
        "double_authentification": u.double_authentification,
        "email_verifie": u.email_verifie,
        "codes_secours_restants": comptes.codes_secours_restants(u.id) if u.double_authentification else 0,
    }


MESSAGE_ADMIN_2FA = ("Activez la double authentification dans « Mon compte » pour accéder à l'administration.")


def exiger_admin(u: Utilisateur) -> Utilisateur:
    """Administration : role admin ET double authentification active (un mot de passe vole ne suffit pas)."""
    # Adresse confirmee exigee : le role vient aussi d'ADMIN_EMAILS, et une adresse listee sans compte
    # (compte supprime, pas encore cree) pouvait etre prise par le premier venu (audit du 2026-11-16).
    if not u.admin or not u.email_verifie:
        raise HTTPException(403, "Accès réservé aux administrateurs.")
    if not u.double_authentification:
        raise HTTPException(403, MESSAGE_ADMIN_2FA)
    return u


def creer_routes(comptes: Comptes, inscriptions_ip_jour: int = 20) -> tuple[APIRouter, callable]:
    """Renvoie (routes /auth, dependance utilisateur_requis)."""
    router = APIRouter()
    freins = Freins(inscriptions_ip_jour=inscriptions_ip_jour)
    attentes = AttentesDeuxiemeFacteur()

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
        freins.verifier_inscription(_ip(request))
        try:
            u = comptes.creer(req.email, req.mot_de_passe)
        except ErreurCompte as e:
            # Un refus compte dans la limite du jour : « Un compte existe deja » permettait de tester des
            # adresses sans limite (audit du 2026-11-16, point 8 ; reste possible 20 fois par jour et par IP).
            freins.inscrit(_ip(request))
            raise HTTPException(422, str(e)) from None
        freins.inscrit(_ip(request))
        _envoyer_verification(request, u)  # l'echec d'envoi n'empeche pas la creation du compte
        _poser_cookie(request, response, comptes.ouvrir_session(u.id))
        return profil(comptes, comptes.par_id(u.id))

    @router.post("/connexion", dependencies=[Depends(verifier_origine)])
    def connexion(req: Connexion, request: Request, response: Response):
        email = req.email.strip().lower()
        # 5 echecs par compte ET par adresse IP, 50 par compte en tout (audit du 2026-11-16, point 7).
        cle, compte = f"{email}|{_ip(request)}", f"compte:{email}"
        freins.verifier(_ip(request), cle, compte)
        u = comptes.authentifier(email, req.mot_de_passe)
        if u is None:
            freins.echec(cle, compte)
            raise HTTPException(401, "E-mail ou mot de passe incorrect.")
        freins.succes(cle, compte)
        if u.double_authentification:
            # Mot de passe correct : la session ne s'ouvre qu'apres le code de l'application.
            return {"double_authentification_requise": True, "jeton": attentes.creer(u.id)}
        _poser_cookie(request, response, comptes.ouvrir_session(u.id))
        return profil(comptes, u)

    @router.post("/connexion/code", dependencies=[Depends(verifier_origine)])
    def connexion_code(req: CodeConnexion, request: Request, response: Response):
        uid = attentes.essai(req.jeton)
        if uid is None:
            raise HTTPException(401, "Délai dépassé ou trop d'essais : reconnectez-vous.")
        freins.verifier(_ip(request), f"2fa:{uid}")
        if not comptes.verifier_2fa(uid, req.code):
            freins.echec(f"2fa:{uid}")
            raise HTTPException(401, "Code incorrect.")
        attentes.terminer(req.jeton)
        freins.succes(f"2fa:{uid}")
        _poser_cookie(request, response, comptes.ouvrir_session(uid))
        return profil(comptes, comptes.par_id(uid))

    @router.post("/2fa/preparer", dependencies=[Depends(verifier_origine)])
    def preparer_2fa(u: Utilisateur = Depends(utilisateur_requis)):
        if u.double_authentification:
            raise HTTPException(422, "La double authentification est déjà active.")
        secret = comptes.preparer_2fa(u.id)
        return {"secret": secret, "uri": totp.uri(secret, u.email)}

    @router.post("/2fa/activer", dependencies=[Depends(verifier_origine)])
    def activer_2fa(req: MotDePasseEtCode2FA, request: Request, response: Response,
                    u: Utilisateur = Depends(utilisateur_requis)):
        # Mot de passe exige : sans lui, quelqu'un sur une session restee ouverte (poste partage) activait la
        # double authentification avec son propre telephone et le titulaire ne pouvait plus se connecter.
        freins.verifier(_ip(request), f"2fa:{u.id}")  # 5 echecs (mot de passe ou code) par 15 min
        if comptes.authentifier(u.email, req.mot_de_passe) is None:
            freins.echec(f"2fa:{u.id}")
            raise HTTPException(401, "Mot de passe incorrect.")
        try:
            codes = comptes.activer_2fa(u.id, req.code)
        except ErreurCompte as e:
            freins.echec(f"2fa:{u.id}")
            raise HTTPException(422, str(e)) from None
        # activer_2fa ferme toutes les sessions (un mot de passe vole ouvrait une session de 30 jours que
        # l'activation laissait vivre) ; celle-ci est rouverte.
        _poser_cookie(request, response, comptes.ouvrir_session(u.id))
        return {"codes_secours": codes}

    @router.post("/2fa/desactiver", dependencies=[Depends(verifier_origine)])
    def desactiver_2fa(req: MotDePasseEtCode2FA, request: Request, response: Response,
                       u: Utilisateur = Depends(utilisateur_requis)):
        freins.verifier(_ip(request), u.email)
        if comptes.authentifier(u.email, req.mot_de_passe) is None or not comptes.verifier_2fa(u.id, req.code):
            freins.echec(u.email)
            raise HTTPException(401, "Mot de passe ou code incorrect.")
        comptes.desactiver_2fa(u.id)  # ferme toutes les sessions ; celle-ci est rouverte ci-dessous
        _poser_cookie(request, response, comptes.ouvrir_session(u.id))
        return profil(comptes, comptes.par_id(u.id))

    def _envoyer_verification(request: Request, u: Utilisateur, force: bool = False) -> bool:
        """Envoie le lien de confirmation. Faux si rien n'est parti (envoi non configure, trop recent,
        adresse deja confirmee, ou service indisponible)."""
        if not courriel.configure():
            return False
        jeton = comptes.jeton_verification(u.id, force=force)
        if jeton is None:
            return False
        origine = request.headers.get("origin") or f"{request.url.scheme}://{request.headers.get('host', '')}"
        try:
            courriel.envoyer_verification(u.email, f"{origine}/verifier-email?jeton={jeton}")
        except courriel.ErreurCourriel:
            return False
        return True

    @router.post("/email/verifier", dependencies=[Depends(verifier_origine)])
    def verifier_email(req: JetonEmail, request: Request):
        # Compteur d'echecs par adresse IP : une cle commune laissait 5 faux jetons bloquer la
        # confirmation de tous les nouveaux inscrits pendant 15 minutes (audit du 2026-11-16).
        cle = f"verification:{_ip(request)}"
        freins.verifier(_ip(request), cle)
        try:
            u = comptes.verifier_email(req.jeton)
        except ErreurCompte as e:
            freins.echec(cle)
            raise HTTPException(422, str(e)) from None
        # Le lien confirme l'adresse mais n'ouvre jamais de session : il contournait le mot de passe et la
        # double authentification, et connectait la victime au compte d'un tiers inscrit avec son adresse
        # (audit du 2026-11-16). Profil renvoye seulement si ce navigateur est deja connecte a ce compte.
        actuel = comptes.session(request.cookies.get(COOKIE))
        return profil(comptes, comptes.par_id(u.id)) if actuel is not None and actuel.id == u.id else None

    @router.post("/email/renvoyer", status_code=202, dependencies=[Depends(verifier_origine)])
    def renvoyer_verification(request: Request, u: Utilisateur = Depends(utilisateur_requis)):
        if u.email_verifie:
            raise HTTPException(422, "Votre adresse est déjà confirmée.")
        if not _envoyer_verification(request, u, force=False):
            raise HTTPException(429, "Un e-mail vient d'être envoyé : vérifiez vos courriers indésirables, "
                                     "puis réessayez dans deux minutes.")
        return {"envoye": True}

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
