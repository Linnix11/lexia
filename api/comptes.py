"""Comptes etudiants : utilisateurs, sessions et consommation quotidienne (SQLite).

Donnees personnelles conservees : adresse e-mail, prenom et nom (demandes a l'inscription, D102 ; le prenom sert a
saluer l'etudiant dans son espace),
empreinte du mot de passe (scrypt, sel aleatoire), formule, date de creation, compteurs d'usage par jour. Aucune question posee n'est enregistree.
Suppression complete du compte a la demande (supprimer). Durees de conservation (politique de confidentialite,
docs/registre-traitements.md) : compte sans activite supprime apres deux ans, avec un e-mail d'avertissement un
mois avant ; compteurs d'usage gardes 90 jours. La table paiements (api/paiement.py) n'est jamais touchee ici.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import sqlite3
import threading
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from api import coffre, courriel, totp
from api.plans import FORMULE_PAR_DEFAUT, FORMULES, Formule, formule

log = logging.getLogger("lexia")

FUSEAU = ZoneInfo("Europe/Paris")
DUREE_SESSION = timedelta(days=30)
MDP_MIN = 10
MDP_COURANTS = frozenset({
    "1234567890", "0123456789", "12345678910", "123456789a", "azertyuiop", "qwertyuiop", "azerty1234",
    "azerty123456", "qwerty1234", "qwerty123456", "motdepasse", "motdepasse1", "motdepasse12", "motdepasse123",
    "password12", "password123", "password1234", "passwordpassword", "iloveyou12", "jetaime1234", "soleil1234",
    "doudou1234", "loulou1234", "chocolat12", "chocolat123", "marseille13", "lexialexia", "lexia12345",
    "droit12345", "etudiant12", "etudiant123", "bonjour123", "bonjour1234", "azertyuiop1", "abcdefghij",
    "abcdefgh12", "abc1234567", "1q2w3e4r5t", "a1b2c3d4e5", "123456789azerty",
})
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
# scrypt : N=2^14, r=8, p=5, une des combinaisons recommandees par l'OWASP (16 Mo de memoire, ~120 ms).
# p=1 etait sous la recommandation (audit du 2026-11-16, point 10) ; p plutot que N pour garder 16 Mo par
# calcul sur un petit serveur. Les anciennes empreintes sont refaites a la connexion suivante.
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 5

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
-- Dernier numero de compte attribue : un numero n'est jamais reutilise apres une suppression. Sinon le
-- compte suivant heritait des limites gardees en memoire par numero (echecs de double authentification,
-- depots de cours), constate en ligne le 2026-11-16. utilisateurs.id ne peut pas devenir AUTOINCREMENT
-- sans recreer la table.
CREATE TABLE IF NOT EXISTS compteurs (
    nom          TEXT PRIMARY KEY,
    valeur       INTEGER NOT NULL
);
-- Boites dont le titulaire a supprime son compte depuis le site, pendant 24 h : supprimer puis se reinscrire
-- remettait le quota du jour a zero (second audit du 2026-11-16, point 6). Empreinte, pas l'adresse.
CREATE TABLE IF NOT EXISTS suppressions (
    boite        TEXT PRIMARY KEY,
    supprime_le  TEXT NOT NULL
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
# Mot de passe oublie : lien a usage unique envoye a l'adresse du compte, valable une heure.
COLONNES_REINIT = {
    "reinit_jeton": "TEXT",       # empreinte du jeton du dernier lien envoye
    "reinit_envoye_le": "TEXT",   # date d'envoi : limite les renvois et fixe l'expiration
}
DUREE_REINITIALISATION = timedelta(hours=1)
MESSAGE_IDENTITE = "Indiquez votre prénom et votre nom."
DELAI_ENTRE_ENVOIS = timedelta(minutes=2)
# Comptes inactifs (audit du 2026-11-18, E5) : repere de la CNIL, deux ans sans activite, avec avertissement
# prealable. Activite = connexion ou visite avec une session valide (actif_le, une ecriture par jour au plus).
COLONNES_ACTIVITE = {
    "actif_le": "TEXT",           # date (Europe/Paris) de la derniere activite ; NULL = date de creation
    "inactif_avis_le": "TEXT",    # date de l'e-mail annoncant la suppression ; remis a NULL a la visite suivante
}
INACTIVITE = timedelta(days=730)
PREAVIS_INACTIVITE = timedelta(days=30)
# Compteurs d'usage : ne servent qu'au quota du jour et aux statistiques des 30 derniers jours.
USAGE_CONSERVE = timedelta(days=90)
# Prenom (D100) et nom (D102) : demandes a l'inscription depuis le site, vides pour les comptes plus anciens (invites
# a les completer dans Mon compte, sans blocage). Le prenom sert a saluer l'etudiant dans son espace. Jamais envoyes
# au modele, dans un e-mail ni a l'administration ; effaces avec le compte (ligne supprimee).
COLONNES_PROFIL = {"prenom": "TEXT", "nom": "TEXT"}
PRENOM_MAX = 50
NOM_MAX = 50
PONCTUATION_PRENOM = set(" -'’.")


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


def _jour_de(instant: datetime) -> str:
    """Date (Europe/Paris) d'un instant, au format des colonnes jour et actif_le."""
    return instant.astimezone(FUSEAU).date().isoformat()


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


def forme_canonique(email: str) -> str:
    """Boite reelle d'une adresse : « x+cours1@domaine » arrive chez « x@domaine », et Gmail ignore les points.

    Sans cela, une seule boite ouvrait autant de comptes gratuits confirmes que de variantes (second audit
    du 2026-11-16, point 6).
    """
    local, _, domaine = email.strip().lower().partition("@")
    local = local.split("+", 1)[0]
    if domaine in ("gmail.com", "googlemail.com"):
        local, domaine = local.replace(".", ""), "gmail.com"
    return f"{local}@{domaine}"


def _hash_jeton(jeton: str) -> str:
    return hashlib.sha256(jeton.encode()).hexdigest()


def _normaliser_identite(valeur: str | None, libelle: str, maximum: int) -> str | None:
    """Prenom ou nom saisi -> forme gardee (None : vide). Lettres, espaces, traits d'union, apostrophes et points."""
    texte = " ".join(unicodedata.normalize("NFC", valeur or "").split())
    if not texte:
        return None
    if len(texte) > maximum:
        raise ErreurCompte(f"Le {libelle} ne doit pas dépasser {maximum} caractères.")
    if not texte[0].isalpha() or any(not (c.isalpha() or c in PONCTUATION_PRENOM) for c in texte):
        raise ErreurCompte(f"Le {libelle} ne peut contenir que des lettres, des espaces, des traits d'union, "
                           "des apostrophes et des points.")
    return texte


def normaliser_prenom(prenom: str | None) -> str | None:
    return _normaliser_identite(prenom, "prénom", PRENOM_MAX)


def normaliser_nom(nom: str | None) -> str | None:
    return _normaliser_identite(nom, "nom", NOM_MAX)


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
        # Compte supprime (et ses cours, en cascade) ou valeur remplacee : octets mis a zero, pas seulement
        # liberes. Sans cela l'adresse, l'empreinte et le texte des cours restaient lisibles dans le fichier
        # (audit de la base du 2026-11-18, D99 ; meme reglage que api/cours.py, audit C7).
        self._con.execute("PRAGMA secure_delete = ON")
        self._con.executescript(SCHEMA)
        colonnes = {r[1] for r in self._con.execute("PRAGMA table_info(utilisateurs)")}
        if "admin" not in colonnes:  # migration des bases creees avant le role admin
            self._con.execute("ALTER TABLE utilisateurs ADD COLUMN admin INTEGER NOT NULL DEFAULT 0")
            self._con.commit()
        for nom, genre in COLONNES_2FA.items():  # migration : double authentification
            if nom not in colonnes:
                self._con.execute(f"ALTER TABLE utilisateurs ADD COLUMN {nom} {genre}")
        for nom, genre in COLONNES_REINIT.items():  # migration : mot de passe oublie
            if nom not in colonnes:
                self._con.execute(f"ALTER TABLE utilisateurs ADD COLUMN {nom} {genre}")
        for nom, genre in COLONNES_EMAIL.items():  # migration : verification de l'adresse e-mail
            if nom not in colonnes:
                self._con.execute(f"ALTER TABLE utilisateurs ADD COLUMN {nom} {genre}")
                if nom == "email_verifie_le":  # les comptes anterieurs restent utilisables
                    self._con.execute("UPDATE utilisateurs SET email_verifie_le = cree_le")
        for nom, genre in COLONNES_PROFIL.items():  # migration : prenom et nom
            if nom not in colonnes:
                self._con.execute(f"ALTER TABLE utilisateurs ADD COLUMN {nom} {genre}")
        for nom, genre in COLONNES_ACTIVITE.items():  # migration : comptes inactifs
            if nom not in colonnes:
                self._con.execute(f"ALTER TABLE utilisateurs ADD COLUMN {nom} {genre}")
                if nom == "actif_le":  # comptes anterieurs : dernier jour avec un compteur, sinon la creation
                    self._con.execute("UPDATE utilisateurs SET actif_le = COALESCE((SELECT max(jour) FROM usage "
                                      "WHERE utilisateur = utilisateurs.id), substr(cree_le, 1, 10))")
        self._con.commit()
        self._chiffrer_secrets_en_clair()
        self._lock = threading.Lock()
        self._dernier_entretien: str | None = None  # jour de la derniere purge quotidienne (_entretien)
        self._lock_entretien = threading.Lock()
        # Autres taches du jour (renvoi des e-mails de paiement en echec, api/paiement.py), apres les purges
        self.taches_quotidiennes: list = []
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
        # Mots de passe parmi les plus essayes, ou presque sans variete (audit du 19/11, SEC-10)
        if mdp.lower() in MDP_COURANTS or len(set(mdp.lower())) < 4:
            raise ErreurCompte("Ce mot de passe est trop courant : choisissez-en un autre.")

    def creer(self, email: str, mdp: str, depuis_le_site: bool = True, prenom: str | None = None,
              nom: str | None = None) -> Utilisateur:
        """depuis_le_site=False : creation par la commande d'administration (adresses d'administration).
        Prenom et nom : exiges par la route d'inscription (api/auth.py), facultatifs ici."""
        email = normaliser_email(email)
        prenom, nom = normaliser_prenom(prenom), normaliser_nom(nom)
        boite = forme_canonique(email)
        if depuis_le_site and boite in {forme_canonique(a) for a in self._admins}:
            # Une adresse d'ADMIN_EMAILS sans compte, inscrite par un tiers, devenait administrateur des que le
            # vrai titulaire cliquait sur le lien recu (second audit du 2026-11-16, points 4 et 15).
            # Meme message qu'un compte existant : l'ancien revelait les adresses d'administration (SEC-7).
            raise ErreurCompte("Un compte existe déjà avec cette adresse e-mail.")
        self._valider_mdp(mdp)
        maintenant = _maintenant().isoformat(timespec="seconds")
        empreinte = hacher_mdp(mdp)
        try:
            with self._lock, self._con:
                if depuis_le_site:
                    trace = self._con.execute("SELECT supprime_le FROM suppressions WHERE boite = ?",
                                              (_hash_jeton(boite),)).fetchone()
                    if trace and trace[0] > (_maintenant() - timedelta(days=1)).isoformat(timespec="seconds"):
                        raise ErreurCompte("Un compte avec cette adresse vient d'être supprimé : "
                                           "réessayez dans 24 heures.")
                # Adresse « squattee » : un compte cree avec l'adresse d'un tiers, jamais confirme, bloquait a
                # vie l'inscription du vrai titulaire (pas de mot de passe oublie). Passe le delai de validite
                # du lien, il est remplace ; un compte non confirme n'a ni question, ni cours (audit 2, point 6).
                # Meme boite sous une autre forme (« + », points Gmail) : un seul compte.
                # shortcut: parcours de tous les comptes a chaque inscription ; une colonne indexee de la
                # forme canonique s'impose au-dela de quelques dizaines de milliers de comptes.
                limite = (_maintenant() - DUREE_VERIFICATION).isoformat(timespec="seconds")
                for uid_autre, autre, verifie, cree in self._con.execute(
                        "SELECT id, email, email_verifie_le, cree_le FROM utilisateurs").fetchall():
                    if forme_canonique(autre) != boite:
                        continue
                    if courriel.configure() and verifie is None and cree < limite:
                        self._con.execute("DELETE FROM utilisateurs WHERE id = ?", (uid_autre,))
                    else:
                        raise ErreurCompte("Un compte existe déjà avec cette adresse e-mail.")
                # Numero suivant le plus grand jamais attribue (compteur) ou existant (comptes anterieurs).
                # Calcule dans l'INSERT lui-meme : atomique meme si la commande d'administration ecrit en
                # parallele dans la base.
                cur = self._con.execute(
                    "INSERT INTO utilisateurs (id, email, mdp, formule, cree_le, cgu_le, prenom, nom) VALUES ("
                    "MAX(COALESCE((SELECT valeur FROM compteurs WHERE nom = 'utilisateurs'), 0),"
                    "    COALESCE((SELECT MAX(id) FROM utilisateurs), 0)) + 1, ?,?,?,?,?,?,?)",
                    (email, empreinte, FORMULE_PAR_DEFAUT, maintenant, maintenant, prenom, nom))
                self._con.execute("INSERT INTO compteurs (nom, valeur) VALUES ('utilisateurs', ?) "
                                  "ON CONFLICT(nom) DO UPDATE SET valeur = excluded.valeur", (cur.lastrowid,))
        except sqlite3.IntegrityError:
            raise ErreurCompte("Un compte existe déjà avec cette adresse e-mail.") from None
        return self.par_email(email)

    def par_email(self, email: str) -> Utilisateur | None:
        rows = self._q(f"SELECT {COLONNES_U} FROM utilisateurs WHERE email = ?", (email.strip().lower(),))
        return self._utilisateur(rows[0] if rows else None)

    def par_id(self, uid: int) -> Utilisateur | None:
        rows = self._q(f"SELECT {COLONNES_U} FROM utilisateurs WHERE id = ?", (uid,))
        return self._utilisateur(rows[0] if rows else None)

    def identite(self, uid: int) -> tuple[str | None, str | None]:
        """(prenom, nom), lus a part (pas dans Utilisateur) : l'objet compte circule jusqu'aux routes du modele."""
        rows = self._q("SELECT prenom, nom FROM utilisateurs WHERE id = ?", (uid,))
        return (rows[0][0], rows[0][1]) if rows else (None, None)

    def changer_identite(self, uid: int, prenom: str | None, nom: str | None) -> tuple[str, str]:
        prenom, nom = normaliser_prenom(prenom), normaliser_nom(nom)
        if not prenom or not nom:
            raise ErreurCompte(MESSAGE_IDENTITE)
        self._q("UPDATE utilisateurs SET prenom = ?, nom = ? WHERE id = ?", (prenom, nom, uid))
        return prenom, nom

    def authentifier(self, email: str, mdp: str) -> Utilisateur | None:
        rows = self._q("SELECT id, mdp FROM utilisateurs WHERE email = ?", ((email or "").strip().lower(),))
        if not rows:
            verifier_mdp(mdp or "", self._mdp_factice)
            return None
        uid, stocke = rows[0]
        a_jour = stocke.startswith(f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}$")
        if not a_jour:
            # Ancienne empreinte, 5 fois plus rapide a verifier que l'empreinte factice d'une adresse inconnue :
            # le temps de reponse revelait que l'adresse avait un compte (second audit du 2026-11-16, point 9).
            verifier_mdp(mdp or "", self._mdp_factice)
        if not verifier_mdp(mdp or "", stocke):
            return None
        if not a_jour:
            self._q("UPDATE utilisateurs SET mdp = ? WHERE id = ?", (hacher_mdp(mdp), uid))  # parametres a jour
        return self.par_id(uid)

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

    def jeton_reinitialisation(self, email: str) -> tuple[Utilisateur, str] | None:
        """Jeton du lien « mot de passe oublie ». None si aucun compte ou si un lien vient de partir."""
        u = self.par_email(email or "")
        if u is None:
            return None
        rows = self._q("SELECT reinit_envoye_le FROM utilisateurs WHERE id = ?", (u.id,))
        if rows and rows[0][0] and _maintenant() - _lire_date(rows[0][0]) < DELAI_ENTRE_ENVOIS:
            return None
        jeton = secrets.token_urlsafe(32)
        self._q("UPDATE utilisateurs SET reinit_jeton = ?, reinit_envoye_le = ? WHERE id = ?",
                (_hash_jeton(jeton), _maintenant().isoformat(timespec="seconds"), u.id))
        return u, jeton

    def reinitialiser_mdp(self, jeton: str, mdp: str) -> Utilisateur:
        """Nouveau mot de passe depuis le lien recu par e-mail : ferme toutes les sessions.

        Cliquer sur ce lien prouve que l'on possede la boite. Une adresse jamais confirmee l'est donc, et la
        double authentification qu'y aurait mise un tiers (compte cree a l'adresse de quelqu'un d'autre) est
        retiree : le vrai titulaire reprend son adresse (second audit de securite, point 6). Sur un compte deja
        confirme, la double authentification reste : le lien seul ne suffit pas a entrer.
        """
        self._valider_mdp(mdp)
        rows = self._q("SELECT id, reinit_envoye_le, email_verifie_le FROM utilisateurs WHERE reinit_jeton = ?",
                       (_hash_jeton(jeton or ""),))
        if not rows:
            raise ErreurCompte("Ce lien n'est plus valable : demandez un nouvel e-mail.")
        uid, envoye, verifie = rows[0]
        if not envoye or _maintenant() - _lire_date(envoye) > DUREE_REINITIALISATION:
            raise ErreurCompte("Ce lien a expiré : demandez un nouvel e-mail.")
        maintenant = _maintenant().isoformat(timespec="seconds")
        with self._lock, self._con:
            self._con.execute("UPDATE utilisateurs SET mdp = ?, reinit_jeton = NULL, verif_jeton = NULL, "
                              "email_verifie_le = COALESCE(email_verifie_le, ?) WHERE id = ?",
                              (hacher_mdp(mdp), maintenant, uid))
            if not verifie:
                self._con.execute("UPDATE utilisateurs SET totp_secret = NULL, totp_attente = NULL, "
                                  "totp_etape = NULL, totp_secours = NULL WHERE id = ?", (uid,))
            self._con.execute("DELETE FROM sessions WHERE utilisateur = ?", (uid,))
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
        self._q("DELETE FROM sessions WHERE utilisateur = ?", (uid,))  # les autres appareils se reconnectent
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

    def supprimer(self, uid: int, garder_trace: bool = False) -> None:
        """garder_trace : suppression demandee depuis le site, la boite ne peut pas se reinscrire avant 24 h."""
        u = self.par_id(uid)
        with self._lock, self._con:
            if garder_trace and u is not None:
                self._con.execute("INSERT INTO suppressions (boite, supprime_le) VALUES (?, ?) ON CONFLICT(boite) "
                                  "DO UPDATE SET supprime_le = excluded.supprime_le",
                                  (_hash_jeton(forme_canonique(u.email)), _maintenant().isoformat(timespec="seconds")))
            self._con.execute("DELETE FROM utilisateurs WHERE id = ?", (uid,))
        # anciennes versions des pages recopiees dans le journal WAL : journal vide (comme Cours.supprimer)
        with self._lock:
            self._con.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    def confirmer_email(self, uid: int) -> None:
        """Adresse confirmee sans lien (compte cree sur le serveur par la commande d'administration)."""
        self._q("UPDATE utilisateurs SET email_verifie_le = ?, verif_jeton = NULL WHERE id = ?",
                (_maintenant().isoformat(timespec="seconds"), uid))

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
        # Formules en cours avec une date de fin : une formule donnee sans fin n'est pas payee (audit A9)
        revenu = sum(FORMULES[f].prix_mensuel_euros for (f,) in self._q(
            "SELECT formule FROM utilisateurs WHERE formule != 'gratuit' AND formule_fin >= ?",
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
               "COALESCE((SELECT max(jour) FROM usage WHERE utilisateur = u.id AND (questions > 0 OR quiz > 0)), "
               "u.actif_le) "
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
        self._marquer_actif(uid)
        return jeton

    def _marquer_actif(self, uid: int) -> None:
        """Derniere activite du jour ; une visite annule l'avertissement de suppression pour inactivite."""
        self._q("UPDATE utilisateurs SET actif_le = ?, inactif_avis_le = NULL WHERE id = ?",
                (_jour_de(_maintenant()), uid))

    def session(self, jeton: str | None) -> Utilisateur | None:
        if not jeton:
            return None
        rows = self._q("SELECT s.utilisateur, s.expire_le, u.actif_le FROM sessions s "
                       "JOIN utilisateurs u ON u.id = s.utilisateur WHERE s.jeton_hash = ?", (_hash_jeton(jeton),))
        if not rows:
            return None
        uid, expire, actif = rows[0]
        if expire < _maintenant().isoformat(timespec="seconds"):
            self.fermer_session(jeton)
            return None
        if actif != _jour_de(_maintenant()):
            self._marquer_actif(uid)
        self._entretien_si_nouveau_jour()
        return self.par_id(uid)

    def fermer_session(self, jeton: str | None) -> None:
        if jeton:
            self._q("DELETE FROM sessions WHERE jeton_hash = ?", (_hash_jeton(jeton),))

    def purger_sessions(self) -> None:
        """Tache de nuit : sessions expirees, et traces de suppression de plus de 24 h (elles ne servent
        qu'a ce delai ; duree annoncee dans la politique de confidentialite)."""
        maintenant = _maintenant()
        self._q("DELETE FROM sessions WHERE expire_le < ?", (maintenant.isoformat(timespec="seconds"),))
        self._q("DELETE FROM suppressions WHERE supprime_le < ?",
                ((maintenant - timedelta(days=1)).isoformat(timespec="seconds"),))

    # --- durees de conservation (taches quotidiennes) ---------------------------

    def _entretien_si_nouveau_jour(self) -> None:
        """Une fois par jour, a la premiere visite : purges ci-dessous, dans un fil a part pour ne pas faire
        attendre la page. Tourne dans le service, qui a la configuration d'envoi des e-mails (la tache cron
        de deploy/sauvegarder_comptes.sh ne lit pas /opt/lexia/.env)."""
        jour = _jour_de(_maintenant())
        if self._dernier_entretien == jour or not self._lock_entretien.acquire(blocking=False):
            return
        try:
            if self._dernier_entretien == jour:
                return
            self._dernier_entretien = jour
        finally:
            self._lock_entretien.release()
        threading.Thread(target=self._entretien, name="entretien-comptes", daemon=True).start()

    def _entretien(self) -> None:
        try:
            self.purger_usage()
            self.purger_inactifs()
        except Exception:  # une purge ratee se refait le lendemain ; elle ne doit pas casser le service
            log.exception("purge quotidienne des comptes")
        for tache in self.taches_quotidiennes:
            try:
                tache()
            except Exception:
                log.exception("tache quotidienne")

    def purger_usage(self) -> int:
        """Compteurs d'usage de plus de USAGE_CONSERVE (90 jours). Renvoie le nombre de lignes effacees."""
        limite = _jour_de(_maintenant() - USAGE_CONSERVE)
        with self._lock, self._con:
            return self._con.execute("DELETE FROM usage WHERE jour < ?", (limite,)).rowcount

    def purger_inactifs(self) -> dict:
        """Comptes sans activite depuis deux ans (INACTIVITE) : un e-mail les previent un mois avant
        (PREAVIS_INACTIVITE), puis ils sont supprimes comme une suppression demandee (cours, sessions et
        compteurs en cascade). Jamais : un administrateur, une formule payante en cours. Les paiements
        (table paiements, sans cle etrangere) restent : ils sont gardes pour la comptabilite."""
        maintenant = _maintenant()
        aujourd_hui = _jour_de(maintenant)
        seuil_avis = _jour_de(maintenant - INACTIVITE + PREAVIS_INACTIVITE)
        seuil_suppression = _jour_de(maintenant - INACTIVITE)
        avis_assez_ancien = _jour_de(maintenant - PREAVIS_INACTIVITE)
        lignes = self._q(
            "SELECT id, email, COALESCE(actif_le, substr(cree_le, 1, 10)), inactif_avis_le, email_verifie_le "
            "FROM utilisateurs WHERE admin = 0 AND COALESCE(actif_le, substr(cree_le, 1, 10)) < ? "
            "AND NOT (formule != ? AND (formule_fin IS NULL OR formule_fin >= ?))",
            (seuil_avis, FORMULE_PAR_DEFAUT, aujourd_hui))
        avertis = supprimes = 0
        for uid, email, actif, avis, verifie in lignes:
            if email in self._admins:
                continue
            # Adresse jamais confirmee : personne a prevenir (elle peut etre celle d'un tiers).
            if actif < seuil_suppression and (verifie is None or (avis is not None and avis <= avis_assez_ancien)):
                self.supprimer(uid)
                supprimes += 1
            elif avis is None and verifie is not None:
                fin = max(_lire_date(actif + "T12:00:00") + INACTIVITE, maintenant + PREAVIS_INACTIVITE)
                if self._avertir_inactif(email, fin.astimezone(FUSEAU).date()):
                    self._q("UPDATE utilisateurs SET inactif_avis_le = ? WHERE id = ?", (aujourd_hui, uid))
                    avertis += 1
        if avertis or supprimes:
            log.info("comptes inactifs : %d avertis, %d supprimes", avertis, supprimes)
        return {"avertis": avertis, "supprimes": supprimes}

    @staticmethod
    def _avertir_inactif(email: str, fin) -> bool:
        """E-mail d'avertissement. Faux si l'envoi echoue (nouvel essai le lendemain). Sans envoi configure
        (developpement), vrai : aucun moyen de prevenir, le delai d'un mois court quand meme."""
        if not courriel.configure():
            return True
        date_fin = f"{fin.day:02d}/{fin.month:02d}/{fin.year}"
        url = os.environ.get("URL_PUBLIQUE", "").strip().rstrip("/")
        lien = f"{url}/connexion" if url else ""
        texte = (
            "Bonjour,\n\n"
            "Votre compte Lexia n'a pas été utilisé depuis bientôt deux ans. Pour ne pas garder vos données "
            f"inutilement, il sera supprimé le {date_fin}, avec vos cours déposés.\n\n"
            "Pour le garder, il suffit de vous connecter avant cette date"
            + (f" : {lien}" if lien else ".") + "\n\n"
            "Les justificatifs d'un éventuel paiement sont conservés pour la comptabilité, comme l'exige la loi.\n"
        )
        html = "".join(f"<p>{courriel._echapper(ligne)}</p>" for ligne in texte.strip().split("\n\n"))
        try:
            courriel.envoyer(email, f"Votre compte Lexia sera supprimé le {date_fin}", texte, html)
        except courriel.ErreurCourriel:
            return False
        return True

    # --- consommation ---------------------------------------------------------

    def usage(self, uid: int) -> dict:
        rows = self._q("SELECT questions, quiz FROM usage WHERE utilisateur = ? AND jour = ?", (uid, _jour()))
        q, z = rows[0] if rows else (0, 0)
        return {"jour": _jour(), "questions": q, "quiz": z}

    def reserver(self, u: Utilisateur, type_: str) -> str | None:
        """Compte une utilisation si la limite du jour n'est pas atteinte (operation atomique) ; renvoie le jour
        decompte, a rendre a rembourser, ou None si la limite est atteinte."""
        colonne = {"questions": "questions", "quiz": "quiz"}[type_]
        limite = u.formule.questions_par_jour if type_ == "questions" else u.formule.quiz_par_jour
        jour = _jour()
        with self._lock, self._con:
            self._con.execute("INSERT OR IGNORE INTO usage (utilisateur, jour) VALUES (?, ?)", (u.id, jour))
            cur = self._con.execute(
                f"UPDATE usage SET {colonne} = {colonne} + 1 WHERE utilisateur = ? AND jour = ? AND {colonne} < ?",
                (u.id, jour, limite))
            return jour if cur.rowcount == 1 else None

    def rembourser(self, u: Utilisateur, type_: str, jour: str | None = None) -> None:
        """Annule une reservation (le modele n'a pas pu repondre : l'etudiant n'est pas decompte).

        jour : celui de la reservation. Une question posee a 23 h 59 et ratee a minuit etait rendue sur le
        lendemain (audit du 19/11, SRV-13)."""
        colonne = {"questions": "questions", "quiz": "quiz"}[type_]
        self._q(f"UPDATE usage SET {colonne} = MAX({colonne} - 1, 0) WHERE utilisateur = ? AND jour = ?",
                (u.id, jour or _jour()))
