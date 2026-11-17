"""Paiement en ligne des formules par Stripe Checkout (D86).

Paiement unique de N mois, sans reconduction (CGU, article 4). Le numero de carte reste chez Stripe :
Lexia ne recoit que le resultat du paiement.

1. POST /paiement/session : l'abonne choisit la formule et le nombre de mois et demande l'execution
   immediate (droit de retractation, art. L. 221-25 du Code de la consommation) ; une session Checkout est
   creee et son adresse renvoyee au navigateur.
2. POST /paiement/webhook : Stripe signale le paiement (checkout.session.completed, ou
   checkout.session.async_payment_succeeded pour un moyen de paiement differe). La signature est verifiee
   (HMAC-SHA256 de « t.corps » avec le secret whsec_, tolerance de 5 minutes), puis la formule est activee
   une seule fois par session, dans la meme transaction que le passage du paiement a « paye ».

Les paiements sont gardes 10 ans (pieces comptables), meme apres la suppression du compte : pas de cle
etrangere vers utilisateurs, l'adresse e-mail est recopiee.

Documentation suivie (2026-11-17) : https://docs.stripe.com/api/checkout/sessions/create,
https://docs.stripe.com/checkout/fulfillment, https://docs.stripe.com/webhooks (verification manuelle).
"""

from __future__ import annotations

import calendar
import hashlib
import hmac
import json
import logging
import time
from datetime import date, datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from api.comptes import FUSEAU, Comptes, Utilisateur
from api.plans import FORMULES

log = logging.getLogger(__name__)

API = "https://api.stripe.com/v1/checkout/sessions"
TOLERANCE_SECONDES = 300   # tolerance par defaut des bibliotheques Stripe
MOIS_MAX = 12
EVENEMENTS_PAYES = ("checkout.session.completed", "checkout.session.async_payment_succeeded")
# Version des conditions generales (date de derniere modification), acceptee avant chaque paiement et gardee
# avec lui. A changer avec web/src/lib/cgu.ts a chaque modification des conditions.
VERSION_CGU = "17 novembre 2026"

SCHEMA = """
CREATE TABLE IF NOT EXISTS paiements (
    id                     INTEGER PRIMARY KEY,
    session                TEXT UNIQUE NOT NULL,     -- identifiant de la session Checkout (cs_...)
    utilisateur            INTEGER NOT NULL,         -- sans cle etrangere : garde 10 ans apres suppression
    email                  TEXT NOT NULL,
    formule                TEXT NOT NULL,
    mois                   INTEGER NOT NULL,
    montant_centimes       INTEGER NOT NULL,
    devise                 TEXT NOT NULL,
    statut                 TEXT NOT NULL DEFAULT 'ouvert',   -- ouvert | paye | ecarte
    execution_immediate_le TEXT NOT NULL,            -- demande expresse d'execution avant 14 jours
    cgu_version            TEXT,                     -- version des conditions acceptee avant le paiement
    cree_le                TEXT NOT NULL,
    paye_le                TEXT,
    paiement_stripe        TEXT                      -- identifiant du PaymentIntent (pi_...), pour un remboursement
);
"""


class ErreurPaiement(Exception):
    """Stripe injoignable ou refus de creer la session."""


def ajouter_mois(depart: date, mois: int) -> date:
    """Meme jour N mois plus tard, ou dernier jour du mois s'il n'existe pas (31 janvier + 1 = 28 ou 29 fevrier)."""
    m = depart.month - 1 + mois
    annee, mois_cible = depart.year + m // 12, m % 12 + 1
    return date(annee, mois_cible, min(depart.day, calendar.monthrange(annee, mois_cible)[1]))


def verifier_signature(corps: bytes, entete: str | None, secret: str, maintenant: float | None = None) -> bool:
    """En-tete Stripe-Signature : t=<horodatage>,v1=<signature>[,v1=...][,autres entrees ignorees]."""
    if not entete or not secret:
        return False
    horodatage, signatures = None, []
    for element in entete.split(","):
        prefixe, _, valeur = element.strip().partition("=")
        if prefixe == "t":
            horodatage = valeur
        elif prefixe == "v1":
            signatures.append(valeur)
    if not horodatage or not horodatage.isdigit() or not signatures:
        return False
    attendue = hmac.new(secret.encode(), horodatage.encode() + b"." + corps, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(attendue, s) for s in signatures):
        return False
    return abs((maintenant if maintenant is not None else time.time()) - int(horodatage)) <= TOLERANCE_SECONDES


class Paiements:
    """Table des paiements, dans la base des comptes : l'activation de la formule et le passage du paiement a
    « paye » se font dans une seule transaction (un webhook rejoue n'active jamais deux fois)."""

    def __init__(self, comptes: Comptes):
        self.comptes = comptes
        # shortcut: connexion et verrou de Comptes reutilises pour une transaction commune aux deux tables
        with comptes._lock, comptes._con:
            comptes._con.executescript(SCHEMA)
            colonnes = {r[1] for r in comptes._con.execute("PRAGMA table_info(paiements)")}
            if "cgu_version" not in colonnes:  # table creee avant l'acceptation des conditions au paiement
                comptes._con.execute("ALTER TABLE paiements ADD COLUMN cgu_version TEXT")

    def ouvrir(self, session: str, u: Utilisateur, formule: str, mois: int, montant: int,
               cgu_version: str = VERSION_CGU) -> None:
        maintenant = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.comptes._q("INSERT INTO paiements (session, utilisateur, email, formule, mois, montant_centimes, devise, "
                        "execution_immediate_le, cgu_version, cree_le) VALUES (?, ?, ?, ?, ?, ?, 'eur', ?, ?, ?)",
                        (session, u.id, u.email, formule, mois, montant, maintenant, cgu_version, maintenant))

    def encaisser(self, session: str, montant: int | None, devise: str | None, paiement_stripe: str | None) -> str:
        """Paiement confirme par Stripe : active la formule. Renvoie ce qui a ete fait (pour le journal)."""
        c = self.comptes
        with c._lock, c._con:
            ligne = c._con.execute("SELECT utilisateur, formule, mois, montant_centimes, devise, statut FROM paiements "
                                   "WHERE session = ?", (session,)).fetchone()
            if ligne is None:
                return "inconnu"
            uid, formule, mois, attendu, devise_attendue, statut = ligne
            if statut != "ouvert":
                return "deja_traite"
            if montant != attendu or (devise or "").lower() != devise_attendue:
                c._con.execute("UPDATE paiements SET statut = 'ecarte' WHERE session = ?", (session,))
                log.warning("paiement %s ecarte : montant %s %s, attendu %s %s", session, montant, devise,
                            attendu, devise_attendue)
                return "montant_inattendu"
            maintenant = datetime.now(timezone.utc).isoformat(timespec="seconds")
            c._con.execute("UPDATE paiements SET statut = 'paye', paye_le = ?, paiement_stripe = ? WHERE session = ?",
                           (maintenant, paiement_stripe, session))
            u = c._con.execute("SELECT formule, formule_fin FROM utilisateurs WHERE id = ?", (uid,)).fetchone()
            if u is None:  # compte supprime entre le paiement et le signal : a rembourser a la main
                log.warning("paiement %s : compte %s supprime, formule non activee", session, uid)
                return "compte_absent"
            if u[0] == formule and u[1] is None:
                return "deja_sans_fin"  # formule donnee sans fin par un administrateur : rien a prolonger
            aujourd_hui = datetime.now(FUSEAU).date()
            depart = aujourd_hui
            if u[0] == formule and u[1] and u[1] >= aujourd_hui.isoformat():
                depart = date.fromisoformat(u[1])  # meme formule encore en cours : prolongee
            fin = ajouter_mois(depart, mois).isoformat()
            c._con.execute("UPDATE utilisateurs SET formule = ?, formule_fin = ? WHERE id = ?", (formule, fin, uid))
            return "active"


def _formule_en_cours(u: Utilisateur) -> str | None:
    """Formule payante encore active (autre que celle demandee : refus, pas de melange de deux formules)."""
    f = u.formule
    return f.id if f.prix_mensuel_euros > 0 and u.formule_fin else None


class DemandePaiement(BaseModel):
    formule: str
    mois: int = Field(ge=1, le=MOIS_MAX)
    execution_immediate: bool
    cgu_version: str = ""   # version des conditions acceptee (case cochee), egale a VERSION_CGU


def creer_routes_paiement(paiements: Paiements, utilisateur_requis, verifier_origine, *, cle: str, secret_webhook: str,
                          url_publique: str, journal=None, client: httpx.Client | None = None) -> APIRouter:
    router = APIRouter()
    http = client or httpx.Client(timeout=15)

    @router.post("/session", dependencies=[Depends(verifier_origine)])
    def session(req: DemandePaiement, u: Utilisateur = Depends(utilisateur_requis)):
        f = FORMULES.get(req.formule)
        if f is None or f.prix_mensuel_euros <= 0:
            raise HTTPException(422, "Formule inconnue.")
        if not u.email_verifie:
            raise HTTPException(403, "Confirmez votre adresse e-mail avant de souscrire une formule.")
        if not req.execution_immediate:
            raise HTTPException(422, "Cochez la demande d'accès immédiat pour continuer.")
        if req.cgu_version != VERSION_CGU:
            raise HTTPException(422, "Acceptez les conditions générales en vigueur pour continuer "
                                     "(rechargez la page si elles viennent de changer).")
        en_cours = _formule_en_cours(u)
        if en_cours and en_cours != f.id:
            raise HTTPException(409, f"Votre formule {u.formule.nom} est en cours jusqu'au {u.formule_fin} : "
                                     "vous pourrez en changer à son échéance.")
        unitaire = round(f.prix_mensuel_euros * 100)
        donnees = {
            "mode": "payment",
            "locale": "fr",
            "line_items[0][price_data][currency]": "eur",
            "line_items[0][price_data][unit_amount]": str(unitaire),
            "line_items[0][price_data][product_data][name]": f"Lexia, formule {f.nom} (1 mois)",
            "line_items[0][price_data][product_data][description]": "Sans reconduction automatique.",
            "line_items[0][quantity]": str(req.mois),
            "customer_email": u.email,
            "client_reference_id": str(u.id),
            "metadata[formule]": f.id,
            "metadata[mois]": str(req.mois),
            "success_url": f"{url_publique}/compte?paiement=ok",
            "cancel_url": f"{url_publique}/tarifs",
        }
        try:
            r = http.post(API, data=donnees, auth=(cle, ""))
        except httpx.HTTPError as e:
            log.warning("stripe injoignable : %s", e)
            raise HTTPException(503, "Le paiement est momentanément indisponible. Réessayez dans quelques instants.")
        if r.status_code != 200:
            log.warning("stripe a refuse la session (%s) : %s", r.status_code, r.text[:300])
            raise HTTPException(503, "Le paiement est momentanément indisponible. Réessayez dans quelques instants.")
        s = r.json()
        paiements.ouvrir(s["id"], u, f.id, req.mois, unitaire * req.mois)
        return {"url": s["url"]}

    @router.post("/webhook")
    async def webhook(request: Request):
        corps = await request.body()
        if not verifier_signature(corps, request.headers.get("stripe-signature"), secret_webhook):
            raise HTTPException(400, "Signature invalide.")
        evenement = json.loads(corps)
        if evenement.get("type") in EVENEMENTS_PAYES:
            s = evenement.get("data", {}).get("object", {})
            if s.get("payment_status") == "paid":
                resultat = paiements.encaisser(s.get("id", ""), s.get("amount_total"), s.get("currency"),
                                               s.get("payment_intent"))
                if journal is not None:
                    journal.ecrire("admin", action="paiement", session=s.get("id"), resultat=resultat)
        return {"recu": True}

    return router
