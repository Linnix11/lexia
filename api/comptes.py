"""Comptes etudiants : utilisateurs, sessions et consommation quotidienne (SQLite).

Donnees personnelles conservees : adresse e-mail, empreinte du mot de passe (scrypt, sel aleatoire),
formule, date de creation, compteurs d'usage par jour. Aucune question posee n'est enregistree.
Suppression complete du compte a la demande (supprimer_compte).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from api import coffre, courriel, totp
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
    cgu_le       TEXT NOT NULL,                -- acceptation des CGU
    admin        INTEGER NOT NULL DEFAULT 0
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


COLONNES_U = "id, email, formule, formule_fin, cree_le, admin, totp_secret IS NOT NULL, email_verifie_le"
# Double authentification par application (api/totp.py) : colonnes ajoutees aux bases existantes.
COLONNES_2FA = {
    "totp_secret": "TEXT",        # secret actif (NULL = double authentification desactivee)
    "totp_attente": "TEXT",       # secret en cours d'activation (le temps de scanner le QR code)
    "totp_etape": "INTEGER",      # derniere etape acceptee : un code ne sert qu'une fois
    "totp_secours": "TEXT",       # empreintes JSON des codes de secours restants
}
# Verification de l'adresse e-mail (api/courriel.py) : colonnes ajoutees aux bases existantes.
COLONNES_EMAIL = {
    "email_verifie_le": "TEXT",   # date de confirmation (NULL = adresse non confirmee)
    "verif_jeton": "TEXT",        # empreinte du jeton du dernier lien envoye
    "verif_envoye_le": "TEXT",    # date d'envoi : limite les renvois et fixe l'expiration
}
DUREE_VERIFICATION = timedelta(hours=24)
DELAI_ENTRE_ENVOIS = timedelta(minutes=2)


@dataclass
class Utilisateur:
    id: int
    email: str
    formule_id: str
    formule_fin: str | None
    cree_le: str
    admin: bool = False
    double_authentification: bool = False
    email_verifie: bool = True   # vrai aussi quand la verification est desactivee (pas d'envoi configure)

    @property
    def formule(self) -> Formule:
        if self.formule_fin and self.formule_fin < datetime.now(FUSEAU).date().isoformat():
            return FORMULES[FORMULE_PAR_DEFAUT]  # formule payante expiree
        return formule(self.formule_id)


def _maintenant() -> datetime:
    return datetime.now(timezone.utc)


def _lire_date(valeur: str) -> datetime:
    """Date ISO de la base, toujours rendue avec un fuseau (les plus anciennes n'en ont pas)."""
    d = datetime.fromisoformat(valeur)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


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
    def __init__(self, chemin: Path | str, admins: tuple[str, ...] = ()):
        self.chemin = str(chemin)
        if str(chemin) != ":memory:":
            Path(chemin).parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(str(chemin), check_same_thread=False)
        self._con.execute("PRAGMA foreign_keys = ON")
        self._con.execute("PRAGMA journal_mode = WAL")
        self._con.executescript(SCHEMA)
        colonnes = {r[1] for r in self._con.execute("PRAGMA table_info(utilisateurs)")}
        if "admin" not in colonnes:  # migration des bases creees avant le role admin
            self._con.execute("ALTER TABLE utilisateurs ADD COLUMN admin INTEGER NOT NULL DEFAULT 0")
            self._con.commit()
        for nom, genre in COLONNES_2FA.items():  # migration : double authentification
            if nom not in colonnes:
                self._con.execute(f"ALTER TABLE utilisateurs ADD COLUMN {nom} {genre}")
        for nom, genre in COLONNES_EMAIL.items():  # migration : verification de l'adresse e-mail
            if nom not in colonnes:
                self._con.execute(f"ALTER TABLE utilisateurs ADD COLUMN {nom} {genre}")
                if nom == "email_verifie_le":  # les comptes anterieurs restent utilisables
                    self._con.execute("UPDATE utilisateurs SET email_verifie_le = cree_le")
        self._con.commit()
        self._chiffrer_secrets_en_clair()
        self._lock = threading.Lock()
        # adresses declarees administrateur dans la configuration (ADMIN_EMAILS)
        self._admins = {a.strip().lower() for a in admins if a.strip()}
        # empreinte factice : meme duree de verification pour un e-mail inconnu (pas d'enumeration)
        self._mdp_factice = hacher_mdp(secrets.token_hex(8))

    def _q(self, sql: str, params: tuple = ()) -> list[tuple]:
        with self._lock, self._con:
            return self._con.execute(sql, params).fetchall()

    # --- utilisateurs ---------------------------------------------------------

    def _utilisateur(self, row) -> Utilisateur | None:
        if not row:
            return None
        u = Utilisateur(*row[:5], admin=bool(row[5]), double_authentification=bool(row[6]),
                        email_verifie=bool(row[7]) or not courriel.configure())
        u.admin = u.admin or u.email in self._admins
        return u

    @staticmethod
    def _valider_mdp(mdp: str) -> None:
        if len(mdp or "") < MDP_MIN:
            raise ErreurCompte(f"Le mot de passe doit contenir au moins {MDP_MIN} caractères.")
        if len(mdp) > 256:
            raise ErreurCompte("Mot de passe trop long.")

    def creer(self, email: str, mdp: str) -> Utilisateur:
        email = normaliser_email(email)
        self._valider_mdp(mdp)
        maintenant = _maintenant().isoformat(timespec="seconds")
        try:
            self._q("INSERT INTO utilisateurs (email, mdp, formule, cree_le, cgu_le) VALUES (?,?,?,?,?)",
                    (email, hacher_mdp(mdp), FORMULE_PAR_DEFAUT, maintenant, maintenant))
        except sqlite3.IntegrityError:
            raise ErreurCompte("Un compte existe déjà avec cette adresse e-mail.") from None
        return self.par_email(email)

    def par_email(self, email: str) -> Utilisateur | None:
        rows = self._q(f"SELECT {COLONNES_U} FROM utilisateurs WHERE email = ?", (email.strip().lower(),))
        return self._utilisateur(rows[0] if rows else None)

    def par_id(self, uid: int) -> Utilisateur | None:
        rows = self._q(f"SELECT {COLONNES_U} FROM utilisateurs WHERE id = ?", (uid,))
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

    def changer_mdp(self, email: str, mdp: str) -> Utilisateur:
        """Nouveau mot de passe ; toutes les sessions ouvertes du compte sont fermees."""
        self._valider_mdp(mdp)
        u = self.par_email(email)
        if u is None:
            raise ErreurCompte(f"Aucun compte pour {email}")
        with self._lock, self._con:
            self._con.execute("UPDATE utilisateurs SET mdp = ? WHERE id = ?", (hacher_mdp(mdp), u.id))
            self._con.execute("DELETE FROM sessions WHERE utilisateur = ?", (u.id,))
        return u

    # --- double authentification ---------------------------------------------

    # --- verification de l'adresse e-mail ---------------------------------------------------

    def jeton_verification(self, uid: int, force: bool = False) -> str | None:
        """Nouveau jeton a mettre dans le lien envoye par e-mail. None si un envoi est trop recent
        (DELAI_ENTRE_ENVOIS) : evite qu'un clic repete serve a inonder une adresse."""
        rows = self._q("SELECT email_verifie_le, verif_envoye_le FROM utilisateurs WHERE id = ?", (uid,))
        if not rows or rows[0][0]:
            return None
        if not force and rows[0][1] and _maintenant() - _lire_date(rows[0][1]) < DELAI_ENTRE_ENVOIS:
            return None
        jeton = secrets.token_urlsafe(32)
        self._q("UPDATE utilisateurs SET verif_jeton = ?, verif_envoye_le = ? WHERE id = ?",
                (_hash_jeton(jeton), _maintenant().isoformat(timespec="seconds"), uid))
        return jeton

    def verifier_email(self, jeton: str) -> Utilisateur:
        """Confirme l'adresse. Le jeton ne sert qu'une fois et expire au bout de DUREE_VERIFICATION."""
        rows = self._q("SELECT id, verif_envoye_le FROM utilisateurs WHERE verif_jeton = ?",
                       (_hash_jeton(jeton),))
        if not rows:
            raise ErreurCompte("Ce lien n'est plus valable : demandez un nouvel e-mail de confirmation.")
        uid, envoye = rows[0]
        if not envoye or _maintenant() - _lire_date(envoye) > DUREE_VERIFICATION:
            raise ErreurCompte("Ce lien a expiré : demandez un nouvel e-mail de confirmation.")
        self._q("UPDATE utilisateurs SET email_verifie_le = ?, verif_jeton = NULL WHERE id = ?",
                (_maintenant().isoformat(timespec="seconds"), uid))
        return self.par_id(uid)

    def _chiffrer_secrets_en_clair(self) -> None:
        """Secrets ecrits avant la mise en place du chiffrement : reecrits chiffres au demarrage,
        pour qu'aucune valeur lisible ne subsiste dans la base ni dans les sauvegardes suivantes."""
        if not coffre.cle_configuree():
            return
        champs = ("totp_secret", "totp_attente", "totp_secours")
        lignes = self._con.execute(f"SELECT id, {', '.join(champs)} FROM utilisateurs").fetchall()
        for ligne in lignes:
            clairs = {c: v for c, v in zip(champs, ligne[1:]) if v and not v.startswith(coffre.PREFIXE)}
            if clairs:
                self._con.execute(f"UPDATE utilisateurs SET {', '.join(f'{c} = ?' for c in clairs)} WHERE id = ?",
                                  (*(coffre.chiffrer(v) for v in clairs.values()), ligne[0]))
        self._con.commit()

    def preparer_2fa(self, uid: int) -> str:
        """Nouveau secret en attente : il ne devient actif qu'apres un premier code correct (activer_2fa)."""
        secret = totp.nouveau_secret()
        self._q("UPDATE utilisateurs SET totp_attente = ? WHERE id = ?", (coffre.chiffrer(secret), uid))
        return secret

    def activer_2fa(self, uid: int, code: str) -> list[str]:
        rows = self._q("SELECT totp_attente FROM utilisateurs WHERE id = ?", (uid,))
        attente = coffre.dechiffrer(rows[0][0]) if rows else None
        if not attente:
            raise ErreurCompte("Commencez par afficher le QR code.")
        etape = totp.verifier(attente, code)
        if etape is None:
            raise ErreurCompte("Code incorrect : vérifiez l'heure de votre téléphone et réessayez.")
        secours = totp.codes_de_secours()
        self._q("UPDATE utilisateurs SET totp_secret = ?, totp_attente = NULL, totp_etape = ?, totp_secours = ? "
                "WHERE id = ?", (coffre.chiffrer(attente), etape,
                                 coffre.chiffrer(json.dumps([totp.empreinte_secours(c) for c in secours])), uid))
        return secours

    def desactiver_2fa(self, uid: int) -> None:
        self._q("UPDATE utilisateurs SET totp_secret = NULL, totp_attente = NULL, totp_etape = NULL, "
                "totp_secours = NULL WHERE id = ?", (uid,))
        self._q("DELETE FROM sessions WHERE utilisateur = ?", (uid,))  # les autres appareils se reconnectent

    def verifier_2fa(self, uid: int, code: str) -> bool:
        """Code de l'application (une seule fois) ou code de secours (consomme)."""
        with self._lock, self._con:
            row = self._con.execute("SELECT totp_secret, totp_etape, totp_secours FROM utilisateurs WHERE id = ?",
                                    (uid,)).fetchone()
            if not row or not row[0]:
                return False
            secret, derniere, secours = coffre.dechiffrer(row[0]), row[1], coffre.dechiffrer(row[2])
            etape = totp.verifier(secret, code, derniere)
            if etape is not None:
                self._con.execute("UPDATE utilisateurs SET totp_etape = ? WHERE id = ?", (etape, uid))
                return True
            restants = json.loads(secours or "[]")
            emp = totp.empreinte_secours(code)
            if emp in restants:
                restants.remove(emp)
                self._con.execute("UPDATE utilisateurs SET totp_secours = ? WHERE id = ?",
                                  (coffre.chiffrer(json.dumps(restants)), uid))
                return True
            return False

    def codes_secours_restants(self, uid: int) -> int:
        rows = self._q("SELECT totp_secours FROM utilisateurs WHERE id = ?", (uid,))
        return len(json.loads(coffre.dechiffrer(rows[0][0]) or "[]")) if rows else 0

    def supprimer(self, uid: int) -> None:
        self._q("DELETE FROM utilisateurs WHERE id = ?", (uid,))

    def lister(self) -> list[Utilisateur]:
        rows = self._q(f"SELECT {COLONNES_U} FROM utilisateurs ORDER BY id")
        return [self._utilisateur(r) for r in rows]

    def definir_admin(self, email: str, admin: bool) -> Utilisateur:
        u = self.par_email(email)
        if u is None:
            raise ErreurCompte(f"Aucun compte pour {email}")
        self._q("UPDATE utilisateurs SET admin = ? WHERE id = ?", (int(admin), u.id))
        return self.par_id(u.id)

    # --- statistiques (tableau de bord admin) ----------------------------------

    def statistiques(self, jours: int = 30) -> dict:
        aujourd_hui = datetime.now(FUSEAU).date()
        debut = (aujourd_hui - timedelta(days=jours - 1)).isoformat()
        par_formule = dict(self._q("SELECT formule, count(*) FROM utilisateurs GROUP BY formule"))
        expirees = self._q("SELECT count(*) FROM utilisateurs WHERE formule != 'gratuit' AND formule_fin < ?",
                           (aujourd_hui.isoformat(),))[0][0]
        total = self._q("SELECT count(*) FROM utilisateurs")[0][0]
        nouveaux = lambda n: self._q("SELECT count(*) FROM utilisateurs WHERE cree_le >= ?",  # noqa: E731
                                     ((datetime.now(timezone.utc) - timedelta(days=n)).isoformat(timespec="seconds"),))[0][0]
        usage = {r[0]: r[1:] for r in self._q(
            "SELECT jour, sum(questions), sum(quiz), count(*) FROM usage WHERE jour >= ? GROUP BY jour", (debut,))}
        inscriptions: dict[str, int] = {}
        for (cree,) in self._q("SELECT cree_le FROM utilisateurs WHERE cree_le >= ?", (debut,)):
            j = datetime.fromisoformat(cree).astimezone(FUSEAU).date().isoformat()
            inscriptions[j] = inscriptions.get(j, 0) + 1
        serie = []
        for i in range(jours):
            j = (aujourd_hui - timedelta(days=jours - 1 - i)).isoformat()
            q, z, actifs = usage.get(j, (0, 0, 0))
            serie.append({"jour": j, "questions": q, "quiz": z, "actifs": actifs, "inscriptions": inscriptions.get(j, 0)})
        payants = sum(n for f, n in par_formule.items() if f != "gratuit") - expirees
        revenu = sum(FORMULES[f].prix_mensuel_euros * n for f, n in par_formule.items() if f in FORMULES) \
            - sum(FORMULES[f].prix_mensuel_euros for (f,) in self._q(
                "SELECT formule FROM utilisateurs WHERE formule != 'gratuit' AND formule_fin < ?",
                (aujourd_hui.isoformat(),)) if f in FORMULES)
        return {
            "comptes": {"total": total, "par_formule": {f: par_formule.get(f, 0) for f in FORMULES},
                        "payants_actifs": payants, "formules_expirees": expirees,
                        "nouveaux_7j": nouveaux(7), "nouveaux_30j": nouveaux(30)},
            "revenu_mensuel_estime": round(revenu, 2),
            "aujourd_hui": serie[-1],
            "serie": serie,
        }

    def clients(self, recherche: str = "") -> list[dict]:
        jour = _jour()
        il_y_a_30j = (datetime.now(FUSEAU).date() - timedelta(days=29)).isoformat()
        sql = (f"SELECT {COLONNES_U}, "
               "(SELECT questions FROM usage WHERE utilisateur = u.id AND jour = ?), "
               "(SELECT quiz FROM usage WHERE utilisateur = u.id AND jour = ?), "
               "(SELECT sum(questions) FROM usage WHERE utilisateur = u.id AND jour >= ?), "
               "(SELECT max(jour) FROM usage WHERE utilisateur = u.id AND (questions > 0 OR quiz > 0)) "
               "FROM utilisateurs u")
        params: tuple = (jour, jour, il_y_a_30j)
        if recherche:
            sql += " WHERE email LIKE ?"
            params += (f"%{recherche.strip().lower()}%",)
        out = []
        n = len(COLONNES_U.split(","))  # les colonnes du compte, puis les quatre agregats ci-dessus
        for r in self._q(sql + " ORDER BY cree_le DESC", params):
            u = self._utilisateur(r[:n])
            f = u.formule
            out.append({
                "id": u.id, "email": u.email, "admin": u.admin,
                "double_authentification": u.double_authentification, "email_verifie": u.email_verifie,
                "formule": f.id, "formule_enregistree": u.formule_id,
                "formule_fin": u.formule_fin, "cree_le": u.cree_le,
                "questions_aujourdhui": r[n] or 0, "quiz_aujourdhui": r[n + 1] or 0,
                "questions_30j": r[n + 2] or 0, "derniere_activite": r[n + 3],
                "limite_questions": f.questions_par_jour,
            })
        return out

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
