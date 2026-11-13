"""Codes a usage unique (TOTP, RFC 6238) pour la double authentification par application.

Compatible avec Google Authenticator, Microsoft Authenticator, 2FAS, Aegis... : SHA-1, 6 chiffres,
periode de 30 s. Bibliotheque standard uniquement.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote, urlencode

PERIODE = 30
CHIFFRES = 6
FENETRE = 1  # une periode avant / apres : tolere un decalage d'horloge du telephone (+/- 30 s)


def nouveau_secret() -> str:
    """Secret aleatoire de 160 bits, en base32 (format attendu par les applications)."""
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _code(secret: str, etape: int) -> str:
    cle = base64.b32decode(secret + "=" * (-len(secret) % 8), casefold=True)
    empreinte = hmac.new(cle, struct.pack(">Q", etape), hashlib.sha1).digest()
    decalage = empreinte[-1] & 0x0F
    valeur = struct.unpack(">I", empreinte[decalage:decalage + 4])[0] & 0x7FFFFFFF
    return str(valeur % 10 ** CHIFFRES).zfill(CHIFFRES)


def etape_courante(maintenant: float | None = None) -> int:
    return int((time.time() if maintenant is None else maintenant) // PERIODE)


def verifier(secret: str, code: str, derniere_etape: int | None = None, maintenant: float | None = None) -> int | None:
    """Etape TOTP correspondant au code, ou None. Un code deja utilise (etape <= derniere_etape) est refuse :
    un code intercepte ne peut pas resservir."""
    code = "".join(c for c in str(code) if c.isdigit())
    if len(code) != CHIFFRES:
        return None
    courante = etape_courante(maintenant)
    for etape in range(courante - FENETRE, courante + FENETRE + 1):
        if derniere_etape is not None and etape <= derniere_etape:
            continue
        if hmac.compare_digest(_code(secret, etape), code):
            return etape
    return None


def uri(secret: str, compte: str, emetteur: str = "Lexia") -> str:
    """Adresse otpauth:// encodee dans le QR code a scanner."""
    return (f"otpauth://totp/{quote(emetteur)}:{quote(compte)}?"
            + urlencode({"secret": secret, "issuer": emetteur, "digits": CHIFFRES, "period": PERIODE}))


def codes_de_secours(nombre: int = 8) -> list[str]:
    """Codes a usage unique en cas de telephone perdu (ex. 4f9k-2m7q)."""
    alphabet = "23456789abcdefghjkmnpqrstuvwxyz"  # sans 0/o, 1/l/i : pas de confusion a la lecture
    return ["-".join("".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(2)) for _ in range(nombre)]


def empreinte_secours(code: str) -> str:
    return hashlib.sha256(code.strip().lower().replace(" ", "").encode()).hexdigest()
