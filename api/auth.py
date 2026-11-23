"""Routes de compte : inscription, connexion, deconnexion, profil, prenom et nom, suppression.

Session : cookie `lexia_session` HttpOnly, SameSite=Lax, Secure en HTTPS. Les requetes qui
modifient l'etat sont en JSON (pas de formulaire HTML cross-site possible) et l'en-tete Origin,
s'il est present, doit correspondre au site : protection contre les requetes intersites.
"""

from __future__ import annotations

import hashlib
import ipaddress
import logging
import re
import secrets
import sqlite3
import threading
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from typing import Literal
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from api import courriel, totp
from api.comptes import (AGE_MINIMUM, DUREE_SESSION, MESSAGE_IDENTITE, Comptes, ErreurCompte, Utilisateur,
                         normaliser_nom, normaliser_prenom)
from api.paiement import VERSION_CGU
from api.plans import FORMULES

COOKIE = "lexia_session"
RENVOIS_PAR_COMPTE_JOUR = 5   # renvois du lien de confirmation par compte sur 24 h
# Quota Resend : 100 e-mails par jour. Deux budgets separes sur 24 h (audit du 19/11, SEC-1) : un visiteur qui cree
# des comptes a des adresses inventees n'epuise que celui des comptes non confirmes, et les etudiants confirmes
# recoivent encore leur lien « mot de passe oublie ». Les 20 restants servent aux paiements, retractations et alertes.
ENVOIS_NON_CONFIRMES_JOUR = 40   # lien d'inscription, renvoi du lien, mot de passe oublie d'un compte non confirme
ENVOIS_CONFIRMES_JOUR = 40       # mot de passe oublie d'un compte confirme
# Plafonds par adresse (IPv4, ou reseau /48 en IPv6) et par compte : sans eux, un seul visiteur avec quelques
# adresses videait les budgets en quelques minutes ; pendant 24 h, plus aucun lien d'inscription ni « mot de passe
# oublie » ne partait (audit du 23/11, B1). Les budgets restent communs : un visiteur qui dispose de dizaines
# d'adresses peut encore les vider ; une formule Resend payante a l'ouverture les rend trop grands pour etre une cible.
LIENS_PAR_IP_JOUR = 3            # liens d'inscription vers une meme adresse ; autant de renvois du lien
OUBLIS_PAR_COMPTE_JOUR = 2       # liens « mot de passe oublie » par compte
OUBLIS_PAR_IP_JOUR = 3           # liens « mot de passe oublie » demandes depuis une meme adresse
ALERTES_PAR_IP_JOUR = 3          # alertes « code incorrect » provoquees depuis une meme adresse
ECHECS_2FA_JOUR = 20             # codes faux par compte sur 24 h, connexion, desactivation et suppression comprises
log = logging.getLogger("lexia.auth")


class Inscription(BaseModel):
    email: str = Field(max_length=254)
    mot_de_passe: str = Field(max_length=256)
    accepte_cgu: bool
    # Exiges (D102) ; limites fines dans normaliser_prenom et normaliser_nom
    prenom: str | None = Field(default=None, max_length=100)
    nom: str | None = Field(default=None, max_length=100)
    # Note de l'editeur du 2026-11-20, point 1 (api/comptes.py, COLONNES_INSCRIPTION). None : client ancien
    # (app iOS) qui n'envoie pas la case ou la version ; rien n'est alors enregistre pour ce champ.
    age_atteste: bool | None = None
    cgu_version: str | None = Field(default=None, max_length=40)
    infos_email: bool = False
    origine: Literal["reseaux_sociaux", "association", "ami", "enseignant", "recherche", "autre"] | None = None
    # Beta fermee (BETA_FERMEE=1, D121) : code d'acces exige ; ignore sinon
    code_beta: str | None = Field(default=None, max_length=40)


class InfosEmail(BaseModel):
    accepte: bool


class Identite(BaseModel):
    prenom: str | None = Field(default=None, max_length=100)
    nom: str | None = Field(default=None, max_length=100)


class Connexion(BaseModel):
    email: str = Field(max_length=254)
    mot_de_passe: str = Field(max_length=256)


class Suppression(BaseModel):
    mot_de_passe: str = Field(max_length=256)
    code: str = Field(default="", max_length=20)   # exige quand la double authentification est active (SEC-6)


class CodeConnexion(BaseModel):
    jeton: str = Field(max_length=100)
    code: str = Field(max_length=20)


class JetonEmail(BaseModel):
    jeton: str = Field(max_length=100)


class OubliMdp(BaseModel):
    email: str = Field(max_length=254)


class NouveauMdp(BaseModel):
    jeton: str = Field(max_length=100)
    mot_de_passe: str = Field(max_length=256)


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


class Compteurs:
    """Evenements sur 24 h glissantes, par cle, gardes dans la base des comptes (table compteurs_jour).

    En memoire, les budgets d'e-mails et le plafond des codes 2FA du jour repartaient de zero a chaque redemarrage
    (bascule d'index de 4 h 30, publication) : 40 liens partis le soir, 40 de plus apres la bascule, dans la meme
    journee Resend de 100 e-mails (audit du 23/11, B6 ; B2). Cles hachees : ni adresse IP ni identifiant en clair ;
    lignes effacees apres 24 h. Horloge murale (time.time) : elle continue apres un redemarrage.
    chemin None : base en memoire (tests, Freins seul)."""

    FENETRE = 86400.0

    def __init__(self, chemin=None, horloge=time.time):
        self._horloge = horloge
        self._con = sqlite3.connect(str(chemin) if chemin else ":memory:", check_same_thread=False)
        with self._con:
            self._con.execute("CREATE TABLE IF NOT EXISTS compteurs_jour (cle TEXT NOT NULL, le REAL NOT NULL)")
            self._con.execute("CREATE INDEX IF NOT EXISTS compteurs_jour_cle ON compteurs_jour (cle, le)")
        self._lock = threading.Lock()
        self._purge = 0.0

    @staticmethod
    def _h(cle: str) -> str:
        return hashlib.sha256(cle.encode()).hexdigest()[:32]

    def _n(self, cle: str, maintenant: float) -> int:
        return self._con.execute("SELECT COUNT(*) FROM compteurs_jour WHERE cle = ? AND le > ?",
                                 (self._h(cle), maintenant - self.FENETRE)).fetchone()[0]

    def _purger(self, maintenant: float) -> None:
        if maintenant - self._purge > 600:
            self._purge = maintenant
            self._con.execute("DELETE FROM compteurs_jour WHERE le <= ?", (maintenant - self.FENETRE,))

    def reserver(self, *plafonds: tuple[str, int]) -> float | None:
        """Note un evenement dans chaque cle si aucune n'a atteint son plafond ; renvoie son instant, sinon None."""
        maintenant = self._horloge()
        with self._lock, self._con:
            self._purger(maintenant)
            if any(self._n(cle, maintenant) >= plafond for cle, plafond in plafonds):
                return None
            self._con.executemany("INSERT INTO compteurs_jour (cle, le) VALUES (?, ?)",
                                  [(self._h(cle), maintenant) for cle, _ in plafonds])
            return maintenant

    def annuler(self, t: float, *plafonds: tuple[str, int]) -> None:
        """Rend une reservation (e-mail qui n'est pas parti)."""
        with self._lock, self._con:
            for cle, _ in plafonds:
                self._con.execute("DELETE FROM compteurs_jour WHERE rowid = (SELECT rowid FROM compteurs_jour "
                                  "WHERE cle = ? AND le = ? LIMIT 1)", (self._h(cle), t))

    def compter(self, cle: str) -> int:
        with self._lock:
            return self._n(cle, self._horloge())

    def ajouter(self, cle: str) -> int:
        """Note un evenement sans plafond ; renvoie le nombre de la fenetre."""
        maintenant = self._horloge()
        with self._lock, self._con:
            self._purger(maintenant)
            self._con.execute("INSERT INTO compteurs_jour (cle, le) VALUES (?, ?)", (self._h(cle), maintenant))
            return self._n(cle, maintenant)


_CODE_SECOURS = re.compile(r"^[a-z0-9]{4}-[a-z0-9]{4}$")


def forme_code_secours(code: str) -> bool:
    """Forme d'un code de secours (4f9k-2m7q, api/totp.py), pas un code de l'application."""
    return bool(_CODE_SECOURS.match(code.strip().lower().replace(" ", "")))


class Freins:
    """Limite les essais de connexion : par IP (par minute) et par e-mail (echecs sur 15 min),
    et les comptes crees par IP sur 24 h (sans plafond, le quota gratuit se contourne en creant des comptes)."""

    def __init__(self, par_ip_minute: int = 10, echecs_email: int = 5, inscriptions_ip_jour: int = 20,
                 echecs_compte: int = 50, echecs_jour: int | None = None, compteurs: Compteurs | None = None):
        self.par_ip, self.max_echecs = par_ip_minute, echecs_email
        # Plafond sur 24 h, que la connexion reussie du titulaire ne remet pas a zero : avec 5 echecs par
        # 15 minutes seulement, un code a 6 chiffres se devinait en un an dans 40 % des cas (audit du 19/11, SEC-2).
        self.max_echecs_jour = ECHECS_2FA_JOUR if echecs_jour is None else echecs_jour
        # En base (B2, B6) : un redemarrage remettait ce plafond a zero.
        self._jour = compteurs if compteurs is not None else Compteurs()
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

    def verifier_jour(self, cle: str, code: str = "") -> None:
        """Plafond des codes faux du jour. Atteint, il laisse encore passer un code de secours : sinon quelqu'un
        qui connait le mot de passe bloquait le titulaire 24 h, code de secours en main (audit du 23/11, B2)."""
        if self._jour.compter(cle) >= self.max_echecs_jour and not forme_code_secours(code):
            raise HTTPException(429, "Trop de codes incorrects pour ce compte aujourd'hui : utilisez un code de "
                                     "secours, ou réessayez demain.")

    def plafond_jour_atteint(self, cle: str) -> bool:
        return self._jour.compter(cle) >= self.max_echecs_jour

    def echec_jour(self, cle: str) -> int:
        """Note un echec sur 24 h ; renvoie le nombre d'echecs de la fenetre."""
        return self._jour.ajouter(cle)

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


def cle_ip(request: Request) -> str:
    """Adresse du client pour les limites de debit ; en IPv6, son reseau /64.

    Un abonnement IPv6 recoit au moins un /64 (des milliards d'adresses) : limiter par adresse entiere
    laissait creer des comptes et essayer des mots de passe sans limite (second audit du 2026-11-16, point 7).
    """
    hote = request.client.host if request.client else "inconnu"
    if ":" in hote:
        try:
            return str(ipaddress.ip_network(f"{hote}/64", strict=False))
        except ValueError:
            return hote
    return hote


def cle_ip_envois(request: Request) -> str:
    """Adresse pour les plafonds d'e-mails : IPv4 entiere, reseau /48 en IPv6.

    Un abonnement IPv6 recoit souvent un /56 ou un /48 : par /64, un seul abonne disposait de 256 adresses ou
    plus pour vider les budgets (audit du 23/11, B1)."""
    hote = request.client.host if request.client else "inconnu"
    if ":" in hote:
        try:
            return str(ipaddress.ip_network(f"{hote}/48", strict=False))
        except ValueError:
            return hote
    return hote


def verifier_origine(request: Request) -> None:
    origine = request.headers.get("origin")
    if origine and urlparse(origine).netloc != request.headers.get("host", ""):
        raise HTTPException(403, "Origine de la requête non autorisée.")


def profil(comptes: Comptes, u: Utilisateur) -> dict:
    f = u.formule
    prenom, nom = comptes.identite(u.id)
    return {
        "email": u.email,
        "prenom": prenom,
        "nom": nom,
        "cree_le": u.cree_le,
        "formule": f.as_dict(),
        "formule_fin": u.formule_fin if u.formule_id == f.id else None,
        "usage": comptes.usage(u.id),
        "admin": u.admin,
        "double_authentification": u.double_authentification,
        "email_verifie": u.email_verifie,
        "codes_secours_restants": comptes.codes_secours_restants(u.id) if u.double_authentification else 0,
        "infos_email": comptes.infos_email(u.id),
        "beta": comptes.compte_beta(u.id),   # questionnaire de retour propose (D121)
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


def creer_routes(comptes: Comptes, inscriptions_ip_jour: int = 20,
                 url_publique: str = "", beta_fermee: bool = False) -> tuple[APIRouter, callable]:
    """Renvoie (routes /auth, dependance utilisateur_requis). beta_fermee : inscription avec un code d'acces
    seulement (api/beta.py, D121)."""
    from api.beta import CodeRefuse
    router = APIRouter()
    # E-mails envoyes et codes 2FA faux sur 24 h glissantes, en base (B6) : cles « compte:<id> », « oubli:<id> »,
    # « lien_ip:<ip> », « renvoi_ip:<ip> », « oubli_ip:<ip> », « alerte_ip:<ip> », « 2fa:<id> » et les deux budgets
    # « non_confirmes » et « confirmes ». Sans plafond, un compte inscrit a l'adresse d'un tiers lui envoyait 720
    # e-mails par jour (audit 2, point 4) ; avec un plafond commun, un seul visiteur privait tout le monde du lien
    # « mot de passe oublie » pendant 24 h (audit du 19/11, SEC-1) ; sans plafond par adresse, il le pouvait encore
    # avec quelques adresses (audit du 23/11, B1).
    compteurs = Compteurs(comptes.chemin)
    freins = Freins(inscriptions_ip_jour=inscriptions_ip_jour, compteurs=compteurs)
    attentes = AttentesDeuxiemeFacteur()
    _reserver, _annuler = compteurs.reserver, compteurs.annuler

    def utilisateur_requis(request: Request) -> Utilisateur:
        u = comptes.session(request.cookies.get(COOKIE))
        if u is None:
            raise HTTPException(401, "Connectez-vous pour utiliser l'assistant.")
        return u

    public = urlparse(url_publique)

    def _poser_cookie(request: Request, response: Response, jeton: str) -> None:
        # Secure aussi quand la requete vise le site public en HTTPS, quel que soit le schema vu derriere nginx :
        # Cloudflare repasse en « Flexible », et le cookie partait sans Secure sans signe visible (SEC-4).
        secure = request.url.scheme == "https" or (public.scheme == "https"
                                                   and request.headers.get("host") == public.netloc)
        response.set_cookie(COOKIE, jeton, max_age=int(DUREE_SESSION.total_seconds()), httponly=True,
                            samesite="lax", secure=secure, path="/")

    def _ip(request: Request) -> str:
        return cle_ip(request)

    @router.post("/inscription", status_code=201, dependencies=[Depends(verifier_origine)])
    def inscription(req: Inscription, request: Request, response: Response):
        if not req.accepte_cgu:
            raise HTTPException(422, "Vous devez accepter les conditions générales d'utilisation.")
        if req.age_atteste is False:
            raise HTTPException(422, f"Lexia est réservé aux personnes de {AGE_MINIMUM} ans ou plus.")
        if req.cgu_version is not None and req.cgu_version != VERSION_CGU:
            # Onglet ouvert avant une modification des conditions : l'etudiant accepterait une autre version
            raise HTTPException(422, "Les conditions d'utilisation ont changé : rechargez la page pour lire la "
                                     "nouvelle version, puis réessayez.")
        try:
            if not normaliser_prenom(req.prenom) or not normaliser_nom(req.nom):
                raise ErreurCompte(MESSAGE_IDENTITE)
        except ErreurCompte as e:
            raise HTTPException(422, str(e)) from None
        freins.verifier(_ip(request), "inscription")
        freins.verifier_inscription(_ip(request))
        try:
            u = comptes.creer(req.email, req.mot_de_passe, prenom=req.prenom, nom=req.nom,
                              age_atteste=f"{AGE_MINIMUM} ans ou plus" if req.age_atteste else None,
                              cgu_version=req.cgu_version, infos_email=req.infos_email, origine=req.origine,
                              exiger_code=beta_fermee, code_beta=req.code_beta)
        except ErreurCompte as e:
            # Un refus compte dans la limite du jour : « Un compte existe deja » permettait de tester des
            # adresses sans limite (audit du 2026-11-16, point 8 ; reste possible 20 fois par jour et par IP).
            # Un code d'acces faux aussi : 20 essais par jour et par adresse, 10 par minute (D121).
            freins.inscrit(_ip(request))
            raise HTTPException(403 if isinstance(e, CodeRefuse) else 422, str(e)) from None
        freins.inscrit(_ip(request))
        # L'echec d'envoi n'empeche pas la creation du compte ; le lien compte dans le budget des non confirmes.
        # Plafond par adresse avant le budget commun (B1) : au-dela, le compte est cree et le site propose
        # « Renvoyer le lien » (lien_envoye faux).
        plafonds = ((f"lien_ip:{cle_ip_envois(request)}", LIENS_PAR_IP_JOUR),
                    ("non_confirmes", ENVOIS_NON_CONFIRMES_JOUR))
        envoye = False
        t = _reserver(*plafonds) if courriel.configure() else None
        if t is None:
            if courriel.configure():
                log.warning("plafond atteint (adresse ou comptes non confirmes) : lien d'inscription non envoye")
        elif not (envoye := _envoyer_verification(request, u)):
            _annuler(t, *plafonds)
        _poser_cookie(request, response, comptes.ouvrir_session(u.id))
        return {**profil(comptes, comptes.par_id(u.id)), "lien_envoye": envoye}

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
        if not _code_2fa_valable(uid, req.code, request):
            freins.echec(f"2fa:{uid}")
            raise HTTPException(401, "Code incorrect.")
        attentes.terminer(req.jeton)
        freins.succes(f"2fa:{uid}")
        _poser_cookie(request, response, comptes.ouvrir_session(uid))
        return profil(comptes, comptes.par_id(uid))

    def _code_2fa_valable(uid: int, code: str, request: Request) -> bool:
        """Code de l'application ou de secours, apres un bon mot de passe : connexion, desactivation de la 2FA,
        suppression du compte. Plafond du jour commun aux trois (B7) ; atteint, seul un code de secours est
        encore essaye (B2, 429 sinon). Un code faux compte dans ce plafond et previent le titulaire."""
        cle = f"2fa:{uid}"
        freins.verifier_jour(cle, code)
        if comptes.verifier_2fa(uid, code, secours_seul=freins.plafond_jour_atteint(cle)):
            return True
        freins.echec_jour(cle)
        _prevenir_code_faux(uid, request)
        return False

    def _prevenir_code_faux(uid: int, request: Request) -> None:
        """E-mail au titulaire au premier code faux apres un bon mot de passe, une fois par 24 h au plus."""
        u = comptes.par_id(uid)
        if u is None or not u.email_verifie or not courriel.configure():
            return
        plafonds = ((f"alerte2fa:{uid}", 1), (f"alerte_ip:{cle_ip_envois(request)}", ALERTES_PAR_IP_JOUR),
                    ("confirmes", ENVOIS_CONFIRMES_JOUR))
        if _reserver(*plafonds) is not None:
            envois_oubli.submit(_envoyer_alerte_code_faux, u.email)

    def _envoyer_alerte_code_faux(email: str) -> None:
        try:
            courriel.envoyer_alerte_code_faux(email)
        except courriel.ErreurCourriel:
            log.warning("e-mail « code incorrect » non envoye")

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
        # Code dans le plafond du jour et titulaire prevenu, comme a la connexion (audit du 23/11, B7).
        if comptes.authentifier(u.email, req.mot_de_passe) is None or not _code_2fa_valable(u.id, req.code, request):
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
        if not url_publique:
            # Jamais l'en-tete Host ou Origin : il est choisi par l'expediteur de la requete (audit 2, point 3).
            log.error("URL_PUBLIQUE absente du .env : e-mail de confirmation non envoye")
            return False
        jeton = comptes.jeton_verification(u.id, force=force)
        if jeton is None:
            return False
        try:
            # Jeton apres « # » : jamais envoye au serveur, donc absent des journaux d'acces de nginx et uvicorn
            # (audit du 2026-11-18, D2).
            courriel.envoyer_verification(u.email, f"{url_publique}/verifier-email#jeton={jeton}")
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
        plafonds = ((f"compte:{u.id}", RENVOIS_PAR_COMPTE_JOUR),
                    (f"renvoi_ip:{cle_ip_envois(request)}", LIENS_PAR_IP_JOUR),   # B1
                    ("non_confirmes", ENVOIS_NON_CONFIRMES_JOUR))
        t = _reserver(*plafonds)
        if t is None:
            raise HTTPException(429, "Trop d'e-mails de confirmation envoyés aujourd'hui : réessayez demain, "
                                     "ou écrivez-nous si le message n'arrive pas.")
        if not _envoyer_verification(request, u, force=False):
            _annuler(t, *plafonds)
            raise HTTPException(429, "Un e-mail vient d'être envoyé : vérifiez vos courriers indésirables, "
                                     "puis réessayez dans deux minutes.")
        return {"envoye": True}

    # --- mot de passe oublie -------------------------------------------------
    # Meme reponse et meme duree qu'il existe un compte ou non (l'e-mail part dans un fil a part) : la page ne
    # dit pas quelles adresses sont inscrites. Envois plafonnes par compte, par IP, et dans le budget du compte
    # (confirme ou non) : des comptes inventes ne privent plus les etudiants confirmes de leur lien (SEC-1).
    envois_oubli = ThreadPoolExecutor(max_workers=2, thread_name_prefix="oubli")

    def _envoyer_oubli(email: str, lien: str) -> None:
        try:
            courriel.envoyer_reinitialisation(email, lien)
        except courriel.ErreurCourriel:
            log.warning("e-mail « mot de passe oublie » non envoye")

    @router.post("/mot-de-passe/oubli", status_code=202, dependencies=[Depends(verifier_origine)])
    def mot_de_passe_oublie(req: OubliMdp, request: Request):
        freins.verifier(_ip(request), f"oubli:{_ip(request)}")
        email = req.email.strip().lower()
        u = comptes.par_email(email) if courriel.configure() and url_publique else None
        if u is None:
            return {"envoye": True}
        budget = (("confirmes", ENVOIS_CONFIRMES_JOUR) if u.email_verifie
                  else ("non_confirmes", ENVOIS_NON_CONFIRMES_JOUR))
        plafonds = ((f"oubli:{u.id}", OUBLIS_PAR_COMPTE_JOUR),
                    (f"oubli_ip:{cle_ip_envois(request)}", OUBLIS_PAR_IP_JOUR), budget)
        t = _reserver(*plafonds)
        if t is None:
            log.warning("plafond atteint : lien « mot de passe oublie » non envoye (%s)", budget[0])
            return {"envoye": True}
        r = comptes.jeton_reinitialisation(email)
        if r is None:   # un lien vient de partir (2 minutes)
            _annuler(t, *plafonds)
            return {"envoye": True}
        envois_oubli.submit(_envoyer_oubli, r[0].email, f"{url_publique}/nouveau-mot-de-passe#jeton={r[1]}")
        return {"envoye": True}

    @router.post("/mot-de-passe/nouveau", dependencies=[Depends(verifier_origine)])
    def nouveau_mot_de_passe(req: NouveauMdp, request: Request):
        cle = f"reinit:{_ip(request)}"
        freins.verifier(_ip(request), cle)
        try:
            comptes.reinitialiser_mdp(req.jeton, req.mot_de_passe)
        except ErreurCompte as e:
            freins.echec(cle)
            raise HTTPException(422, str(e)) from None
        # Pas de session ouverte par le lien : l'etudiant se connecte (code de l'application compris).
        return {"modifie": True}

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

    @router.post("/infos-email", dependencies=[Depends(verifier_origine)])
    def changer_infos_email(req: InfosEmail, u: Utilisateur = Depends(utilisateur_requis)):
        comptes.changer_infos_email(u.id, req.accepte)
        return profil(comptes, comptes.par_id(u.id))

    @router.post("/identite", dependencies=[Depends(verifier_origine)])
    def changer_identite(req: Identite, u: Utilisateur = Depends(utilisateur_requis)):
        try:
            comptes.changer_identite(u.id, req.prenom, req.nom)
        except ErreurCompte as e:
            raise HTTPException(422, str(e)) from None
        return profil(comptes, u)

    @router.post("/supprimer", status_code=204, dependencies=[Depends(verifier_origine)])
    def supprimer(req: Suppression, request: Request, response: Response,
                  u: Utilisateur = Depends(utilisateur_requis)):
        freins.verifier(_ip(request), u.email)
        if comptes.authentifier(u.email, req.mot_de_passe) is None:
            freins.echec(u.email)
            raise HTTPException(401, "Mot de passe incorrect.")
        # Comme la desactivation de la 2FA : avec une session restee ouverte et le mot de passe, un tiers
        # supprimait le compte sans le code (audit du 19/11, SEC-6). Code de secours accepte aussi.
        if u.double_authentification:
            if not req.code.strip():
                raise HTTPException(401, "Saisissez le code de votre application d'authentification.")
            if not _code_2fa_valable(u.id, req.code, request):   # plafond du jour et alerte (B7)
                freins.echec(u.email)
                raise HTTPException(401, "Code incorrect.")
        comptes.supprimer(u.id, garder_trace=True)  # pas de reinscription avant 24 h (quota remis a zero)
        response.delete_cookie(COOKIE, path="/")

    return router, utilisateur_requis


def routes_formules() -> APIRouter:
    router = APIRouter()

    @router.get("/formules")
    def formules():
        return [f.as_dict() for f in FORMULES.values()]

    return router
