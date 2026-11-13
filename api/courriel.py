"""Envoi des e-mails de verification d'adresse, par Resend (https://resend.com).

Sans RESEND_API_KEY, aucun e-mail n'est envoye et la verification d'adresse est desactivee :
les comptes restent utilisables (api/comptes.py : verification_active).

Resend est un service americain : seules l'adresse du destinataire et le texte du message lui sont
transmis, jamais le mot de passe ni les questions posees (politique de confidentialite, D68).
"""

from __future__ import annotations

import logging
import os
import re

import httpx

log = logging.getLogger("lexia")

API = "https://api.resend.com/emails"
DELAI = 10.0
# L'adresse d'expedition doit appartenir a un domaine verifie dans Resend (enregistrements DNS).
EXPEDITEUR_DEFAUT = "Lexia <verification@axionstudio.fr>"


class ErreurCourriel(RuntimeError):
    """L'e-mail n'est pas parti : a presenter a l'utilisateur comme un incident temporaire."""


def configure() -> bool:
    return bool(os.environ.get("RESEND_API_KEY", "").strip())


def _expediteur() -> str:
    return os.environ.get("RESEND_EXPEDITEUR", "").strip() or EXPEDITEUR_DEFAUT


def envoyer(destinataire: str, sujet: str, texte: str, html: str) -> None:
    """Envoie un e-mail. Leve ErreurCourriel si Resend refuse ou ne repond pas."""
    cle = os.environ.get("RESEND_API_KEY", "").strip()
    if not cle:
        raise ErreurCourriel("L'envoi d'e-mails n'est pas configuré.")
    try:
        r = httpx.post(API, timeout=DELAI, headers={"Authorization": f"Bearer {cle}"},
                       json={"from": _expediteur(), "to": [destinataire], "subject": sujet,
                             "text": texte, "html": html})
    except httpx.HTTPError as e:
        log.warning("resend injoignable : %s", e)
        raise ErreurCourriel("Service d'envoi indisponible.") from None
    if r.status_code >= 400:
        # Le detail de Resend peut nommer l'adresse : il reste dans les journaux, pas dans la reponse HTTP.
        log.warning("resend a refuse l'envoi (%s) : %s", r.status_code, r.text[:200])
        raise ErreurCourriel("Service d'envoi indisponible.")


def _echapper(valeur: str) -> str:
    return re.sub(r"[<>&\"]", lambda m: {"<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;"}[m.group()], valeur)


def envoyer_verification(destinataire: str, lien: str) -> None:
    """E-mail de confirmation d'adresse. Le lien contient le jeton a usage unique."""
    lien_sur = _echapper(lien)
    texte = (
        "Bienvenue sur Lexia.\n\n"
        "Confirmez votre adresse e-mail pour commencer à poser vos questions de droit :\n"
        f"{lien}\n\n"
        "Ce lien est valable 24 heures et ne sert qu'une fois.\n"
        "Si vous n'avez pas créé de compte sur Lexia, ignorez ce message.\n"
    )
    html = (
        '<div style="font-family:-apple-system,Segoe UI,sans-serif;color:#202724;max-width:480px">'
        '<p style="font-size:16px">Bienvenue sur Lexia.</p>'
        "<p>Confirmez votre adresse e-mail pour commencer à poser vos questions de droit.</p>"
        f'<p><a href="{lien_sur}" style="display:inline-block;background:#315e4b;color:#fff;'
        'padding:12px 20px;border-radius:8px;text-decoration:none">Confirmer mon adresse</a></p>'
        f'<p style="font-size:12px;color:#707873">Ou copiez ce lien : {lien_sur}</p>'
        '<p style="font-size:12px;color:#707873">Ce lien est valable 24 heures et ne sert qu\'une fois. '
        "Si vous n'avez pas créé de compte sur Lexia, ignorez ce message.</p></div>"
    )
    envoyer(destinataire, "Confirmez votre adresse e-mail — Lexia", texte, html)
