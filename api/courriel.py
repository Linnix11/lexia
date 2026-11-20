"""Envoi des e-mails de verification d'adresse, par Resend (https://resend.com).

Sans RESEND_API_KEY, aucun e-mail n'est envoye et la verification d'adresse est desactivee :
les comptes restent utilisables (api/comptes.py : verification_active).

Resend est un service americain : seules l'adresse du destinataire et le texte du message lui sont
transmis, jamais le mot de passe ni les questions posees (politique de confidentialite, D68).
"""

from __future__ import annotations

import base64
import logging
import os
import re

import httpx

from api.cgu_texte import fichier_version

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


def envoyer(destinataire: str, sujet: str, texte: str, html: str,
            pieces_jointes: list[tuple[str, bytes]] | None = None) -> None:
    """Envoie un e-mail. Leve ErreurCourriel si Resend refuse ou ne repond pas. Pieces jointes : (nom du fichier,
    contenu), envoyees en Base64 ; Resend deduit le type du nom du fichier."""
    cle = os.environ.get("RESEND_API_KEY", "").strip()
    if not cle:
        raise ErreurCourriel("L'envoi d'e-mails n'est pas configuré.")
    try:
        r = httpx.post(API, timeout=DELAI, headers={"Authorization": f"Bearer {cle}"},
                       json={"from": _expediteur(), "to": [destinataire], "subject": sujet,
                             "text": texte, "html": html,
                             **({"attachments": [{"filename": nom, "content": base64.b64encode(contenu).decode()}
                                                 for nom, contenu in pieces_jointes]} if pieces_jointes else {})})
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


def envoyer_reinitialisation(destinataire: str, lien: str) -> None:
    """E-mail « mot de passe oublie ». Le lien contient le jeton a usage unique, valable une heure."""
    lien_sur = _echapper(lien)
    texte = (
        "Vous avez demandé à changer le mot de passe de votre compte Lexia.\n\n"
        f"Choisissez un nouveau mot de passe ici :\n{lien}\n\n"
        "Ce lien est valable une heure et ne sert qu'une fois.\n"
        "Si vous n'êtes pas à l'origine de cette demande, ignorez ce message : votre mot de passe ne change pas.\n"
    )
    html = (
        '<div style="font-family:-apple-system,Segoe UI,sans-serif;color:#202724;max-width:480px">'
        "<p>Vous avez demandé à changer le mot de passe de votre compte Lexia.</p>"
        f'<p><a href="{lien_sur}" style="display:inline-block;background:#315e4b;color:#fff;'
        'padding:12px 20px;border-radius:8px;text-decoration:none">Choisir un nouveau mot de passe</a></p>'
        f'<p style="font-size:12px;color:#707873">Ou copiez ce lien : {lien_sur}</p>'
        '<p style="font-size:12px;color:#707873">Ce lien est valable une heure et ne sert qu\'une fois. '
        "Si vous n'êtes pas à l'origine de cette demande, ignorez ce message : votre mot de passe ne change pas.</p></div>"
    )
    envoyer(destinataire, "Nouveau mot de passe — Lexia", texte, html)


def envoyer_alerte_code_faux(destinataire: str) -> None:
    """Code de l'application faux juste apres un bon mot de passe : le titulaire est prevenu (audit du 19/11,
    SEC-2). Une fois par 24 h au plus (api/auth.py)."""
    _envoyer_texte(destinataire, "Lexia : code de connexion incorrect", (
        "Quelqu'un a saisi le bon mot de passe de votre compte Lexia, puis un code de double authentification "
        "incorrect.\n\n"
        "Si c'était vous, ignorez ce message.\n"
        "Sinon, votre mot de passe est connu d'un tiers : changez-le dès maintenant dans « Mon compte », ou avec "
        "« Mot de passe oublié » sur la page de connexion. La double authentification protège encore votre compte.\n"
    ))


# --- vente en ligne (api/paiement.py) ---------------------------------------------------------------------

FORMULAIRE_RETRACTATION = (
    "Modèle de formulaire de rétractation (annexe à l'article R. 221-1 du Code de la consommation)\n"
    "(Veuillez compléter et renvoyer le présent formulaire uniquement si vous souhaitez vous rétracter du contrat.)\n"
    "À l'attention de {vendeur} :\n"
    "Je/nous (*) vous notifie/notifions (*) par la présente ma/notre (*) rétractation du contrat portant sur la "
    "prestation de services ci-dessous :\n"
    "Commandé le :\n"
    "Nom du (des) consommateur(s) :\n"
    "Adresse du (des) consommateur(s) :\n"
    "Signature du (des) consommateur(s) (uniquement en cas de notification du présent formulaire sur papier) :\n"
    "Date :\n"
    "(*) Rayez la mention inutile.\n"
)


def _envoyer_texte(destinataire: str, sujet: str, texte: str, pieces_jointes: list[tuple[str, bytes]] | None = None) -> None:
    """E-mail sans lien a cliquer : le HTML reprend le texte, ligne par ligne."""
    html = ('<div style="font-family:-apple-system,Segoe UI,sans-serif;color:#202724;max-width:560px">'
            + "<br>".join(_echapper(ligne) for ligne in texte.splitlines()) + "</div>")
    envoyer(destinataire, sujet, texte, html, pieces_jointes)


def envoyer_confirmation_paiement(destinataire: str, *, formule: str, mois: int, prix: str, fin: str,
                                  cgu_version: str, acces_immediat_le: str, retractation_jusquau: str,
                                  url_publique: str, vendeur: str, identite: str = "",
                                  cgu_texte: str | None = None) -> None:
    """Confirmation du contrat sur support durable (art. L. 221-13 du Code de la consommation), avec les
    informations de L. 221-5 : identite et coordonnees de l'editeur, garantie legale, mediateur (audit JUR-8)."""
    texte = (
        "Bonjour,\n\n"
        "Votre paiement est confirmé. Cet e-mail confirme votre contrat avec Lexia : gardez-le.\n\n"
        f"Formule : {formule}\n"
        f"Durée : {mois} mois, sans reconduction automatique\n"
        f"Prix payé : {prix} TTC, en une fois\n"
        f"Formule active jusqu'au : {fin}\n"
        f"Conditions générales d'utilisation et de vente acceptées : version du {cgu_version}"
        + (", texte complet joint à cet e-mail (fichier texte à conserver)\n" if cgu_texte else f" ({url_publique}/cgu)\n")
        + f"Demande d'accès immédiat : {acces_immediat_le}. Vous avez demandé que la formule commence avant la fin "
        "du délai de rétractation.\n\n"
        f"Droit de rétractation : vous pouvez vous rétracter sans motif jusqu'au {retractation_jusquau} inclus, "
        f"avec le bouton « Renoncer au contrat ici » de la page Mon compte ({url_publique}/compte) ou en "
        "renvoyant le formulaire ci-dessous. Comme vous avez demandé l'accès immédiat, vous payez la part de la "
        "période déjà écoulée et le reste vous est remboursé dans les 14 jours, par le moyen de paiement utilisé. "
        "Ce droit est perdu si la formule a été entièrement exécutée avant la fin du délai.\n\n"
        "Garantie légale de conformité : le service doit être conforme au contrat pendant toute la durée de la "
        "formule (articles L. 224-25-12 et suivants du Code de la consommation). En cas de défaut, vous avez droit "
        "à sa mise en conformité sans frais, à défaut à une réduction du prix ou à la résolution du contrat "
        "(articles L. 224-25-17 à L. 224-25-23).\n\n"
        + (f"{identite}\n\n" if identite else "")
        + FORMULAIRE_RETRACTATION.format(vendeur=vendeur or "Lexia")
    )
    # CGU jointes : un lien vers la page n'est pas un support durable (audit JUR-8, D111)
    jointes = None
    if cgu_texte:
        nom = "CGU-Lexia-" + fichier_version(cgu_version).removesuffix(".json") + ".txt"
        jointes = [(nom, (f"Lexia, conditions générales d'utilisation et de vente acceptées, version du {cgu_version}\n\n"
                          + cgu_texte).encode("utf-8"))]
    _envoyer_texte(destinataire, "Confirmation de votre formule Lexia", texte, jointes)


def envoyer_accuse_retractation(destinataire: str, *, nom: str, envoye_le: str, contrats: list[str]) -> None:
    """Accuse de reception de la declaration de retractation faite en ligne : contenu, date et heure
    (art. L. 221-21 et D. 221-5 du Code de la consommation)."""
    texte = (
        "Bonjour,\n\n"
        "Nous avons bien reçu votre déclaration de rétractation, faite en ligne sur Lexia.\n\n"
        "Contenu de la déclaration :\n"
        f"Nom et prénom : {nom}\n"
        + "".join(f"Contrat : {c}\n" for c in contrats)
        + f"Accusé de réception envoyé à : {destinataire}\n"
        f"Envoyée le : {envoye_le}\n\n"
        "La formule concernée est retirée de votre compte. Le remboursement, déduction faite de la part de la "
        "période déjà écoulée (accès immédiat demandé), vous parviendra dans les 14 jours, par le moyen de "
        "paiement utilisé.\n"
    )
    _envoyer_texte(destinataire, "Accusé de réception de votre rétractation — Lexia", texte)


def envoyer_paiement_non_active(destinataire: str, *, formule: str, prix: str) -> None:
    """Paiement recu alors qu'une autre formule est en cours : rien n'est active, le paiement sera rembourse."""
    texte = (
        "Bonjour,\n\n"
        f"Nous avons reçu votre paiement de {prix} pour la formule {formule}, mais elle n'a pas été activée : "
        "une autre formule est déjà en cours sur votre compte, ou ce compte n'existe plus. Ce paiement vous sera "
        "remboursé intégralement dans les 14 jours, par le moyen de paiement utilisé. Vous n'avez rien à faire.\n"
    )
    _envoyer_texte(destinataire, "Paiement reçu, formule non activée — Lexia", texte)
