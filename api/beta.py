"""Beta fermee (D121) : codes d'acces a l'inscription, questionnaire de retour, suivi d'usage anonyme.

Codes d'acces : actifs seulement avec BETA_FERMEE=1 dans le .env (desactive par defaut). Le code n'est jamais
stocke en clair : son empreinte (sha256 du code normalise) seulement ; il n'est affiche qu'une fois, a sa
creation dans l'administration. Il est pris dans la meme transaction SQLite que la creation du compte
(api/comptes.py, Comptes.creer) : le plafond tient meme avec deux inscriptions simultanees, et un compte refuse
(adresse deja inscrite...) ne consomme pas de place. Compteur d'inscriptions jamais decremente : un compte
supprime ne rend pas sa place.

Avis : note, ce qui a aide, ce qui manque, une reponse fausse et son lien. Ni l'adresse, ni le numero du compte,
ni l'heure : seulement le jour. Conserves 12 mois (docs/registre-traitements.md).

Suivi d'usage : journal logs/usage.jsonl (fonction, code HTTP, duree ; ni texte, ni compte, ni adresse IP),
agrege avec les durees par etape du journal des requetes (recherche_detail.etapes_ms, D114).
"""

from __future__ import annotations

import csv
import hashlib
import hmac
import io
import math
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator

from api.auth import Compteurs, verifier_origine
from api.comptes import Comptes, ErreurCompte, Utilisateur
from api.journal import Journal

FUSEAU = ZoneInfo("Europe/Paris")
SCHEMA_BETA = """
CREATE TABLE IF NOT EXISTS codes_beta (
    id            INTEGER PRIMARY KEY,
    empreinte     TEXT UNIQUE NOT NULL,      -- sha256 du code normalise ; le code n'est pas garde
    libelle       TEXT NOT NULL,             -- nom choisi par l'editeur (« L1 Assas, groupe 3 »)
    plafond       INTEGER NOT NULL,
    inscriptions  INTEGER NOT NULL DEFAULT 0,
    actif         INTEGER NOT NULL DEFAULT 1,
    cree_le       TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS avis_beta (
    id      INTEGER PRIMARY KEY,
    jour    TEXT NOT NULL,                   -- date seulement (Europe/Paris), jamais l'heure
    note    INTEGER NOT NULL CHECK (note BETWEEN 1 AND 5),
    aide    TEXT NOT NULL DEFAULT '',
    manque  TEXT NOT NULL DEFAULT '',
    erreur  TEXT NOT NULL DEFAULT '',
    lien    TEXT NOT NULL DEFAULT ''
);
"""
# Sans 0, O, 1, I, L : un code recopie a la main ne se trompe pas de lettre. 10 caracteres sur 31 : ~49 bits,
# hors de portee avec 10 essais par minute et 20 inscriptions par jour et par adresse (api/auth.py, Freins).
ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LONGUEUR_CODE = 10
# Code choisi par l'editeur (« ASSAS-L1-2026 ») : 8 lettres ou chiffres au moins, plus facile a deviner qu'un code
# tire au hasard ; le plafond de places et les freins de l'inscription bornent le risque.
LONGUEUR_PERSO_MIN = 8
LONGUEUR_PERSO_MAX = 30
PLAFOND_MAX = 500
AVIS_CONSERVES = timedelta(days=365)
AVIS_PAR_COMPTE_JOUR = 5
TEXTE_AVIS_MAX = 2000
MESSAGE_CODE_ABSENT = "Lexia est en bêta fermée : saisissez le code d’accès que vous avez reçu."
MESSAGE_CODE_INVALIDE = "Code d’accès invalide : vérifiez-le (lettres et chiffres, sans espace)."
MESSAGE_CODE_EPUISE = "Ce code d’accès n’est plus valable : demandez-en un nouveau à l’équipe Lexia."


class CodeIndisponible(ValueError):
    """Code personnalise trop court, trop long ou deja pris : refuse a la creation (admin)."""


class CodeRefuse(ErreurCompte):
    """Code d'acces absent, inconnu, desactive ou plein : 403 a l'inscription."""


def creer_tables(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA_BETA)


def normaliser_code(code: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (code or "").upper())


def empreinte_code(code: str) -> str:
    return hashlib.sha256(normaliser_code(code).encode()).hexdigest()


def generer_code() -> str:
    brut = "".join(secrets.choice(ALPHABET) for _ in range(LONGUEUR_CODE))
    return f"{brut[:5]}-{brut[5:]}"


def prendre_place(con: sqlite3.Connection, code: str | None) -> int:
    """Prend une place du code dans la transaction en cours (appelee par Comptes.creer) ; renvoie son numero.

    Comparaison en temps constant : l'empreinte saisie est comparee a toutes celles de la table avec
    hmac.compare_digest, sans s'arreter a la premiere egale. Place prise par un UPDATE conditionnel
    (inscriptions < plafond) : deux inscriptions simultanees ne depassent jamais le plafond."""
    if not normaliser_code(code or ""):
        raise CodeRefuse(MESSAGE_CODE_ABSENT)
    saisie = empreinte_code(code).encode()
    trouve = None
    for cid, empreinte in con.execute("SELECT id, empreinte FROM codes_beta").fetchall():
        egal = hmac.compare_digest(empreinte.encode(), saisie)
        trouve = cid if egal and trouve is None else trouve
    if trouve is None:
        raise CodeRefuse(MESSAGE_CODE_INVALIDE)
    cur = con.execute("UPDATE codes_beta SET inscriptions = inscriptions + 1 "
                      "WHERE id = ? AND actif = 1 AND inscriptions < plafond", (trouve,))
    if cur.rowcount != 1:
        raise CodeRefuse(MESSAGE_CODE_EPUISE)
    return trouve


# --- codes (administration) -----------------------------------------------------------

def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def creer_code(comptes: Comptes, libelle: str, plafond: int, code: str | None = None) -> dict:
    """Code tire au hasard, ou celui choisi par l'editeur (code), garde seulement par son empreinte."""
    if code is None or not code.strip():
        code = generer_code()
    else:
        code = re.sub(r"\s+", "", code).upper()
        n = len(normaliser_code(code))
        if re.search(r"[^A-Z0-9-]", code):  # un accent ou un signe serait retire a la saisie : code ambigu
            raise CodeIndisponible("Code personnalisé : lettres sans accent, chiffres et tirets seulement.")
        if n < LONGUEUR_PERSO_MIN or n > LONGUEUR_PERSO_MAX:
            raise CodeIndisponible(f"Code personnalisé : {LONGUEUR_PERSO_MIN} à {LONGUEUR_PERSO_MAX} lettres ou chiffres "
                                   "(les tirets et espaces ne comptent pas).")
    try:
        with comptes._lock, comptes._con:
            cur = comptes._con.execute("INSERT INTO codes_beta (empreinte, libelle, plafond, cree_le) "
                                       "VALUES (?, ?, ?, ?)", (empreinte_code(code), libelle, plafond, _maintenant()))
    except sqlite3.IntegrityError:  # empreinte UNIQUE : meme code, meme apres un code desactive
        raise CodeIndisponible("Ce code existe déjà : choisissez-en un autre.") from None
    return {**lire_code(comptes, cur.lastrowid), "code": code}


def lire_code(comptes: Comptes, cid: int) -> dict | None:
    return next((c for c in lister_codes(comptes) if c["id"] == cid), None)


def lister_codes(comptes: Comptes) -> list[dict]:
    """Codes avec les inscriptions faites et les comptes qui existent encore (un compte supprime ne rend pas
    sa place). Aucune adresse : des nombres."""
    rows = comptes._q("SELECT c.id, c.libelle, c.plafond, c.inscriptions, c.actif, c.cree_le, "
                      "(SELECT COUNT(*) FROM utilisateurs u WHERE u.code_beta = c.id) "
                      "FROM codes_beta c ORDER BY c.id DESC")
    return [{"id": r[0], "libelle": r[1], "plafond": r[2], "inscriptions": r[3], "actif": bool(r[4]),
             "cree_le": r[5], "comptes": r[6]} for r in rows]


def desactiver_code(comptes: Comptes, cid: int) -> dict | None:
    comptes._q("UPDATE codes_beta SET actif = 0 WHERE id = ?", (cid,))
    return lire_code(comptes, cid)


# --- avis ------------------------------------------------------------------------------

def _jour() -> str:
    return datetime.now(FUSEAU).date().isoformat()


def purger_avis(comptes: Comptes) -> int:
    limite = (datetime.now(FUSEAU).date() - AVIS_CONSERVES).isoformat()
    with comptes._lock, comptes._con:
        return comptes._con.execute("DELETE FROM avis_beta WHERE jour < ?", (limite,)).rowcount


def enregistrer_avis(comptes: Comptes, note: int, aide: str, manque: str, erreur: str, lien: str) -> None:
    purger_avis(comptes)
    comptes._q("INSERT INTO avis_beta (jour, note, aide, manque, erreur, lien) VALUES (?, ?, ?, ?, ?, ?)",
               (_jour(), note, aide, manque, erreur, lien))


def lister_avis(comptes: Comptes) -> list[dict]:
    purger_avis(comptes)
    rows = comptes._q("SELECT id, jour, note, aide, manque, erreur, lien FROM avis_beta ORDER BY id DESC")
    return [dict(zip(("id", "jour", "note", "aide", "manque", "erreur", "lien"), r)) for r in rows]


def _cellule(v) -> str:
    """Cellule de tableur sans formule : un texte qui commence par =, +, -, @ serait execute par Excel ou
    LibreOffice a l'ouverture du fichier (injection de formule)."""
    s = str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


def avis_csv(avis: list[dict]) -> str:
    sortie = io.StringIO()
    w = csv.writer(sortie, delimiter=";")   # point-virgule : ouverture directe dans un tableur francais
    w.writerow(["jour", "note", "ce qui a aide", "ce qui manque", "reponse fausse", "lien"])
    for a in reversed(avis):
        w.writerow([_cellule(a[k]) for k in ("jour", "note", "aide", "manque", "erreur", "lien")])
    return "﻿" + sortie.getvalue()   # BOM : accents lus correctement par Excel


# --- suivi d'usage ---------------------------------------------------------------------

FONCTIONS = {"question": "Question", "cas_pratique": "Cas pratique", "fiche": "Fiche", "quiz": "Questionnaire",
             "resume_vocal": "Résumé vocal", "carte_mentale": "Carte mentale", "depot": "Dépôt de cours"}
FONCTION_DU_MODE = {"cas_pratique": "cas_pratique", "fiche": "fiche"}   # autres modes : « question »
ROUTES_SUIVIES = {("POST", "/chat"): "question", ("POST", "/quiz"): "quiz", ("POST", "/resume-vocal"): "resume_vocal",
                  ("POST", "/carte-mentale"): "carte_mentale", ("POST", "/cours"): "depot"}
ETAPES = ("reformulation", "vectorisation", "references", "lexicale", "vectorielle", "reclassement")


def fonction_du_mode(mode: str | None) -> str:
    return FONCTION_DU_MODE.get(mode or "", "question")


def centile(valeurs: list[int], p: float) -> int | None:
    """Rang le plus proche : la plus petite valeur au-dessus de laquelle restent (1 - p) des mesures."""
    if not valeurs:
        return None
    v = sorted(valeurs)
    return v[max(0, math.ceil(p * len(v)) - 1)]


def _jour_local(ts: str) -> str | None:
    try:
        d = datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None
    return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(FUSEAU).date().isoformat()


def _durees(valeurs: list[int]) -> dict:
    return {"mesures": len(valeurs), "mediane_ms": centile(valeurs, 0.5), "p90_ms": centile(valeurs, 0.9)}


def resume_usage(journal: Journal, jours: int = 14) -> dict:
    """Agregats seulement : nombres par jour et par fonction, durees, taux d'erreur. Le journal d'usage ne
    contient ni texte, ni compte, ni adresse ; le journal des requetes n'est lu que pour ses durees."""
    aujourd_hui = datetime.now(FUSEAU).date()
    liste_jours = [(aujourd_hui - timedelta(days=i)).isoformat() for i in range(jours - 1, -1, -1)]
    debut = liste_jours[0]
    par_jour = {j: {"jour": j, "questions": 0, "total": 0} for j in liste_jours}
    fonctions = {f: {"fonction": f, "libelle": l, "appels": 0, "erreurs": 0, "refus": 0, "durees": []}
                 for f, l in FONCTIONS.items()}
    for ligne in journal.lire("usage", max_lignes=50000):
        jour = _jour_local(ligne.get("ts", ""))
        f = fonctions.get(ligne.get("fonction"))
        if jour is None or jour < debut or f is None:
            continue
        code = ligne.get("code") if isinstance(ligne.get("code"), int) else 500
        f["appels"] += 1
        f["erreurs"] += code >= 500
        f["refus"] += 400 <= code < 500
        if code < 400 and isinstance(ligne.get("duree_ms"), int):
            f["durees"].append(ligne["duree_ms"])
        par_jour[jour]["total"] += 1
        if code < 400 and ligne["fonction"] in ("question", "cas_pratique", "fiche"):
            par_jour[jour]["questions"] += 1
    etapes: dict[str, list[int]] = {e: [] for e in ("recherche", *ETAPES, "generation", "totale")}
    for r in journal.lire("requetes", max_lignes=50000):
        jour = _jour_local(r.get("ts", ""))
        if r.get("route") != "chat" or r.get("cache") or jour is None or jour < debut:
            continue
        detail = r.get("recherche_detail") or {}
        for e, ms in (detail.get("etapes_ms") or {}).items():
            if e in etapes and isinstance(ms, int):
                etapes[e].append(ms)
        for cle, valeur in (("recherche", detail.get("duree_ms")), ("generation", r.get("generation_ms")),
                            ("totale", r.get("duree_ms"))):
            if isinstance(valeur, int):
                etapes[cle].append(valeur)
    appels = sum(f["appels"] for f in fonctions.values())
    erreurs = sum(f["erreurs"] for f in fonctions.values())
    return {
        "jours": jours,
        "par_jour": list(par_jour.values()),
        "fonctions": [{**{k: v for k, v in f.items() if k != "durees"}, **_durees(f["durees"]),
                       "taux_erreur": round(f["erreurs"] / f["appels"], 3) if f["appels"] else None}
                      for f in fonctions.values()],
        "etapes": [{"etape": e, **_durees(v)} for e, v in etapes.items()],
        "appels": appels,
        "taux_erreur": round(erreurs / appels, 3) if appels else None,
    }


# --- routes ----------------------------------------------------------------------------

class NouveauCode(BaseModel):
    libelle: str = Field(min_length=2, max_length=80)
    plafond: int = Field(ge=1, le=PLAFOND_MAX)
    code: str | None = Field(default=None, max_length=60)  # vide : code tire au hasard


def _texte(v: str) -> str:
    return v.strip()


class Avis(BaseModel):
    note: int = Field(ge=1, le=5)
    aide: str = Field(default="", max_length=TEXTE_AVIS_MAX)
    manque: str = Field(default="", max_length=TEXTE_AVIS_MAX)
    erreur: str = Field(default="", max_length=TEXTE_AVIS_MAX)
    lien: str = Field(default="", max_length=500)

    _nettoyer = field_validator("aide", "manque", "erreur", "lien")(_texte)

    @field_validator("lien")
    @classmethod
    def lien_web(cls, v: str) -> str:
        if v and not re.match(r"^https?://\S+$", v):
            raise ValueError("Le lien doit commencer par https://")
        return v


def creer_routes_beta(comptes: Comptes, utilisateur_requis, admin_requis, journal: Journal) -> APIRouter:
    router = APIRouter()
    compteurs = Compteurs(comptes.chemin)

    @router.post("/beta/avis", status_code=201, dependencies=[Depends(verifier_origine)])
    def donner_avis(req: Avis, u: Utilisateur = Depends(utilisateur_requis)):
        if not (comptes.compte_beta(u.id) or u.admin):
            raise HTTPException(403, "Le questionnaire est réservé aux comptes de la bêta.")
        if not u.email_verifie:
            raise HTTPException(403, "Confirmez votre adresse e-mail pour donner votre avis.")
        if compteurs.reserver((f"avis:{u.id}", AVIS_PAR_COMPTE_JOUR)) is None:
            raise HTTPException(429, "Vous avez déjà envoyé plusieurs avis aujourd’hui : merci, réessayez demain.")
        enregistrer_avis(comptes, req.note, req.aide, req.manque, req.erreur, req.lien)
        return {"enregistre": True}

    @router.get("/admin/beta/codes")
    def codes(_: Utilisateur = Depends(admin_requis)):
        return lister_codes(comptes)

    @router.post("/admin/beta/codes", status_code=201, dependencies=[Depends(verifier_origine)])
    def nouveau_code(req: NouveauCode, moi: Utilisateur = Depends(admin_requis)):
        try:
            res = creer_code(comptes, req.libelle.strip(), req.plafond, req.code)
        except CodeIndisponible as e:
            raise HTTPException(409, str(e)) from None
        journal.ecrire("admin", action="code_beta", par=moi.id, cible=res["id"], plafond=req.plafond)
        return res

    @router.post("/admin/beta/codes/{cid}/desactiver", dependencies=[Depends(verifier_origine)])
    def desactiver(cid: int, moi: Utilisateur = Depends(admin_requis)):
        res = desactiver_code(comptes, cid)
        if res is None:
            raise HTTPException(404, "Code introuvable.")
        journal.ecrire("admin", action="code_beta_desactive", par=moi.id, cible=cid)
        return res

    @router.get("/admin/beta/avis")
    def avis(_: Utilisateur = Depends(admin_requis)):
        liste = lister_avis(comptes)
        notes = [a["note"] for a in liste]
        return {"avis": liste, "note_moyenne": round(sum(notes) / len(notes), 2) if notes else None}

    @router.get("/admin/beta/avis.csv")
    def avis_en_csv(_: Utilisateur = Depends(admin_requis)):
        return Response(avis_csv(lister_avis(comptes)), media_type="text/csv; charset=utf-8", headers={
            "Content-Disposition": f'attachment; filename="avis-beta-{_jour()}.csv"', "Cache-Control": "no-store"})

    @router.get("/admin/beta/usage")
    def usage(jours: int = 14, _: Utilisateur = Depends(admin_requis)):
        return resume_usage(journal, max(1, min(jours, 90)))

    return router


def suivre(journal: Journal, comptes: Comptes | None, cookie: str):
    """Middleware du suivi d'usage : une ligne par appel d'une fonction suivie (ROUTES_SUIVIES), sans texte,
    sans compte, sans adresse IP. Les appels des administrateurs ne sont pas comptes (essais de l'editeur)."""
    import time

    async def middleware(request: Request, call_next):
        fonction = ROUTES_SUIVIES.get((request.method, request.url.path))
        if fonction is None:
            return await call_next(request)
        debut = time.monotonic()
        code = 500
        try:
            reponse = await call_next(request)
            code = reponse.status_code
            return reponse
        finally:
            u = comptes.session(request.cookies.get(cookie)) if comptes is not None else None
            if u is None or not u.admin:
                journal.ecrire("usage", fonction=request.scope.get("lexia_fonction", fonction), code=code,
                               duree_ms=int((time.monotonic() - debut) * 1000))
    return middleware
