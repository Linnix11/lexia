"""Chiffrement des secrets conserves en base (cles de double authentification, codes de secours).

La cle vit dans l'environnement du service (CLE_SECRETS, fichier .env en 600), jamais dans la base :
une copie volee de lexia.db, ou une sauvegarde egaree, ne permet pas de generer les codes a six
chiffres des comptes. AES-256-GCM : le dechiffrement echoue si la valeur a ete modifiee.

Sans cle configuree, les valeurs sont ecrites en clair, comme avant : le service demarre quand meme
(aucun compte bloque), et api/main.py le signale au demarrage.

Si la cle est perdue, les comptes ne sont pas perdus : l'administrateur desactive la double
authentification du compte concerne (python -m api.admin desactiver2fa <email>), et l'etudiant la
reactive. Sauvegardez quand meme CLE_SECRETS avec le reste de la configuration.
"""

from __future__ import annotations

import base64
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PREFIXE = "v1:"  # marque une valeur chiffree ; sans lui, la valeur date d'avant le chiffrement
VARIABLE = "CLE_SECRETS"


class ErreurCoffre(RuntimeError):
    """Cle illisible ou valeur chiffree avec une autre cle."""


def nouvelle_cle() -> str:
    """Cle a coller dans .env (CLE_SECRETS=...)."""
    return base64.urlsafe_b64encode(AESGCM.generate_key(256)).decode()


def _cle() -> bytes | None:
    brute = os.environ.get(VARIABLE, "").strip()
    if not brute:
        return None
    try:
        cle = base64.urlsafe_b64decode(brute + "=" * (-len(brute) % 4))
    except Exception:  # noqa: BLE001 - toute cle illisible donne le meme message
        raise ErreurCoffre(f"{VARIABLE} n'est pas une cle valide (base64 de 32 octets).") from None
    if len(cle) != 32:
        raise ErreurCoffre(f"{VARIABLE} doit faire 32 octets une fois decode ({len(cle)} trouves).")
    return cle


def cle_configuree() -> bool:
    return _cle() is not None


def chiffrer(valeur: str | None) -> str | None:
    """Valeur chiffree prefixee de v1:, ou la valeur telle quelle si aucune cle n'est configuree."""
    cle = _cle()
    if valeur is None or cle is None:
        return valeur
    nonce = os.urandom(12)
    scelle = AESGCM(cle).encrypt(nonce, valeur.encode(), None)
    return PREFIXE + base64.urlsafe_b64encode(nonce + scelle).decode()


def dechiffrer(valeur: str | None) -> str | None:
    """Valeur en clair. Une valeur sans prefixe est rendue telle quelle : les bases d'avant le
    chiffrement continuent de fonctionner, et Comptes les reecrit chiffrees au demarrage."""
    if valeur is None or not valeur.startswith(PREFIXE):
        return valeur
    cle = _cle()
    if cle is None:
        raise ErreurCoffre(f"Cette base contient des secrets chiffres : renseignez {VARIABLE}.")
    brut = base64.urlsafe_b64decode(valeur[len(PREFIXE):])
    try:
        return AESGCM(cle).decrypt(brut[:12], brut[12:], None).decode()
    except InvalidTag:
        raise ErreurCoffre(f"{VARIABLE} ne correspond pas aux secrets de cette base.") from None
