"""Comptes etudiants : utilisateurs, sessions et consommation quotidienne (SQLite).

Donnees personnelles conservees : adresse e-mail, empreinte du mot de passe (scrypt, sel aleatoire),
formule, date de creation, compteurs d'usage par jour. Aucune question posee n'est enregistree.
Suppression complete du compte a la demande (supprimer_compte).
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from api.plans import FORMULE_PAR_DEFAUT, FORMULES, Formule, formule

FUSEAU = ZoneInfo("Europe/Paris")
DUREE_SESSION = timedelta(days=30)
MDP_MIN = 10
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
# scrypt : parametres recommandes pour un usage interactif (~50 ms, 16 Mo)
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS utilisateurs (
    id           INTEGER PRIMARY KEY,
    email        TEXT UNIQUE NOT NULL,
    mdp          TEXT NOT NULL,
    formule      TEXT NOT NULL DEFAULT 'gratuit',
    formule_fin  TEXT,                         -- date ISO de fin d'une formule payante (NULL = sans fin)
    cree_le      TEXT NOT NULL,
    cgu_le       TEXT NOT NULL                 -- acceptation des CGU
);
CREATE TABLE IF NOT EXISTS sessions (
    jeton_hash   TEXT PRIMARY KEY,             -- sha256 du jeton : le jeton lui-meme n'est jamais stocke
    utilisateur  INTEGER NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    expire_le    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS usage (
    utilisateur  INTEGER NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    jour         TEXT NOT NULL,
    questions    INTEGER NOT NULL DEFAULT 0,
    quiz         INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (utilisateur, jour)
);
"""


class ErreurCompte(ValueError):
    """Erreur presentable a l'utilisateur (message en francais)."""


@dataclass
class Utilisateur:
    id: int
    email: str
    formule_id: str
    formule_fin: str | None
    cree_le: str

    @property
    def formule(self) -> Formule:
        if self.formule_fin and self.formule_fin < datetime.now(FUSEAU).date().isoformat():
            return FORMULES[FORMULE_PAR_DEFAUT]  # formule payante expiree
        return formule(self.formule_id)


def _maintenant() -> datetime:
    return datetime.now(timezone.utc)


def _jour() -> str:
    return datetime.now(FUSEAU).date().isoformat()


def hacher_mdp(mdp: str) -> str:
    sel = secrets.token_bytes(16)
    h = hashlib.scrypt(mdp.encode(), salt=sel, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${sel.hex()}${h.hex()}"


def verifier_mdp(mdp: str, stocke: str) -> bool:
    try:
        _, n, r, p, sel, h = stocke.split("$")
        calcule = hashlib.scrypt(mdp.encode(), salt=bytes.fromhex(sel), n=int(n), r=int(r), p=int(p), dklen=32)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(calcule.hex(), h)


def _hash_jeton(jeton: str) -> str:
    return hashlib.sha256(jeton.encode()).hexdigest()


def normaliser_email(email: str) -> str:
    email = (email or "").strip().lower()
    if not EMAIL_RE.match(email) or len(email) > 254:
        raise ErreurCompte("Adresse e-mail invalide.")
    return email


class Comptes:
    def __init__(self, chemin: Path | str):
        if str(chemin) != ":memory:":
            Path(chemin).parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(str(chemin), check_same_thread=False)
        self._con.execute("PRAGMA foreign_keys = ON")
        self._con.execute("PRAGMA journal_mode = WAL")
        self._con.executescript(SCHEMA)
        self._lock = threading.Lock()
        # empreinte factice : meme duree de verification pour un e-mail inconnu (pas d'enumeration)
        self._mdp_factice = hacher_mdp(secrets.token_hex(8))

    def _q(self, sql: str, params: tuple = ()) -> list[tuple]:
        with self._lock, self._con:
            return self._con.execute(sql, params).fetchall()

    # --- utilisateurs ---------------------------------------------------------

    def _utilisateur(self, row) -> Utilisateur | None:
        return Utilisateur(*row) if row else None

    def creer(self, email: str, mdp: str) -> Utilisateur:
        email = normaliser_email(email)
        if len(mdp or "") < MDP_MIN:
            raise ErreurCompte(f"Le mot de passe doit contenir au moins {MDP_MIN} caractères.")
        if len(mdp) > 256:
            raise ErreurCompte("Mot de passe trop long.")
        maintenant = _maintenant().isoformat(timespec="seconds")
        try:
            self._q("INSERT INTO utilisateurs (email, mdp, formule, cree_le, cgu_le) VALUES (?,?,?,?,?)",
                    (email, hacher_mdp(mdp), FORMULE_PAR_DEFAUT, maintenant, maintenant))
        except sqlite3.IntegrityError:
            raise ErreurCompte("Un compte existe déjà avec cette adresse e-mail.") from None
        return self.par_email(email)

    def par_email(self, email: str) -> Utilisateur | None:
        rows = self._q("SELECT id, email, formule, formule_fin, cree_le FROM utilisateurs WHERE email = ?",
                       (email.strip().lower(),))
        return self._utilisateur(rows[0] if rows else None)

    def par_id(self, uid: int) -> Utilisateur | None:
        rows = self._q("SELECT id, email, formule, formule_fin, cree_le FROM utilisateurs WHERE id = ?", (uid,))
        return self._utilisateur(rows[0] if rows else None)

    def authentifier(self, email: str, mdp: str) -> Utilisateur | None:
        rows = self._q("SELECT id, mdp FROM utilisateurs WHERE email = ?", ((email or "").strip().lower(),))
        if not rows:
            verifier_mdp(mdp or "", self._mdp_factice)
            return None
        uid, stocke = rows[0]
        return self.par_id(uid) if verifier_mdp(mdp or "", stocke) else None

    def changer_formule(self, email: str, id_formule: str, jours: int | None = None) -> Utilisateur:
        if id_formule not in FORMULES:
            raise ErreurCompte(f"Formule inconnue : {id_formule} ({', '.join(FORMULES)})")
        u = self.par_email(email)
        if u is None:
            raise ErreurCompte(f"Aucun compte pour {email}")
        fin = (datetime.now(FUSEAU).date() + timedelta(days=jours)).isoformat() if jours else None
        self._q("UPDATE utilisateurs SET formule = ?, formule_fin = ? WHERE id = ?", (id_formule, fin, u.id))
        return self.par_id(u.id)

    def supprimer(self, uid: int) -> None:
        self._q("DELETE FROM utilisateurs WHERE id = ?", (uid,))

    def lister(self) -> list[Utilisateur]:
        rows = self._q("SELECT id, email, formule, formule_fin, cree_le FROM utilisateurs ORDER BY id")
        return [Utilisateur(*r) for r in rows]

    # --- sessions -------------------------------------------------------------

    def ouvrir_session(self, uid: int) -> str:
        jeton = secrets.token_urlsafe(32)
        expire = (_maintenant() + DUREE_SESSION).isoformat(timespec="seconds")
        self._q("INSERT INTO sessions (jeton_hash, utilisateur, expire_le) VALUES (?,?,?)",
                (_hash_jeton(jeton), uid, expire))
        return jeton

    def session(self, jeton: str | None) -> Utilisateur | None:
        if not jeton:
            return None
        rows = self._q("SELECT utilisateur, expire_le FROM sessions WHERE jeton_hash = ?", (_hash_jeton(jeton),))
        if not rows:
            return None
        uid, expire = rows[0]
        if expire < _maintenant().isoformat(timespec="seconds"):
            self.fermer_session(jeton)
            return None
        return self.par_id(uid)

    def fermer_session(self, jeton: str | None) -> None:
        if jeton:
            self._q("DELETE FROM sessions WHERE jeton_hash = ?", (_hash_jeton(jeton),))

    def purger_sessions(self) -> None:
        self._q("DELETE FROM sessions WHERE expire_le < ?", (_maintenant().isoformat(timespec="seconds"),))

    # --- consommation ---------------------------------------------------------

    def usage(self, uid: int) -> dict:
        rows = self._q("SELECT questions, quiz FROM usage WHERE utilisateur = ? AND jour = ?", (uid, _jour()))
        q, z = rows[0] if rows else (0, 0)
        return {"jour": _jour(), "questions": q, "quiz": z}

    def reserver(self, u: Utilisateur, type_: str) -> bool:
        """Compte une utilisation si la limite du jour n'est pas atteinte (operation atomique)."""
        colonne = {"questions": "questions", "quiz": "quiz"}[type_]
        limite = u.formule.questions_par_jour if type_ == "questions" else u.formule.quiz_par_jour
        jour = _jour()
        with self._lock, self._con:
            self._con.execute("INSERT OR IGNORE INTO usage (utilisateur, jour) VALUES (?, ?)", (u.id, jour))
            cur = self._con.execute(
                f"UPDATE usage SET {colonne} = {colonne} + 1 WHERE utilisateur = ? AND jour = ? AND {colonne} < ?",
                (u.id, jour, limite))
            return cur.rowcount == 1

    def rembourser(self, u: Utilisateur, type_: str) -> None:
        """Annule une reservation (le modele n'a pas pu repondre : l'etudiant n'est pas decompte)."""
        colonne = {"questions": "questions", "quiz": "quiz"}[type_]
        self._q(f"UPDATE usage SET {colonne} = MAX({colonne} - 1, 0) WHERE utilisateur = ? AND jour = ?",
                (u.id, _jour()))
