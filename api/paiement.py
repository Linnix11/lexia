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
from datetime import date, datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from api import courriel
from api.comptes import FUSEAU, Comptes, Utilisateur
from api.plans import FORMULE_PAR_DEFAUT, FORMULES

log = logging.getLogger(__name__)

API = "https://api.stripe.com/v1/checkout/sessions"
TOLERANCE_SECONDES = 300   # tolerance par defaut des bibliotheques Stripe
MOIS_MAX = 12
EVENEMENTS_PAYES = ("checkout.session.completed", "checkout.session.async_payment_succeeded")
# Version des conditions generales (date de derniere modification), acceptee avant chaque paiement et gardee
# avec lui. A changer avec web/src/lib/cgu.ts a chaque modification des conditions.
VERSION_CGU = "17 novembre 2026"
DUREE_SESSION = 31 * 60     # page de paiement valable 30 min (minimum de Stripe) + 1 min de marge d'horloge
SESSIONS_PAR_JOUR = 10      # pages de paiement ouvertes par compte en 24 h
DELAI_RETRACTATION = 14     # jours (art. L. 221-18 du Code de la consommation)
# Paiements dont le resultat demande une action de l'editeur (remboursement, verification dans Stripe)
A_TRAITER = ("ecarte", "a_rembourser", "litige", "rembourse_partiel")

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
    -- ouvert | en_attente (paiement differe) | paye | expire | echec | ecarte (montant inattendu)
    -- | a_rembourser | rembourse | rembourse_partiel | litige
    statut                 TEXT NOT NULL DEFAULT 'ouvert',
    execution_immediate_le TEXT NOT NULL,            -- demande expresse d'execution avant 14 jours
    cgu_version            TEXT,                     -- version des conditions acceptee avant le paiement
    cree_le                TEXT NOT NULL,
    paye_le                TEXT,
    paiement_stripe        TEXT,                     -- identifiant du PaymentIntent (pi_...), pour un remboursement
    motif                  TEXT,                     -- pourquoi a rembourser, ecarte ou en litige
    retractation_le        TEXT                      -- retractation faite en ligne (Mon compte)
);
"""
# Colonnes ajoutees aux tables creees avant elles
COLONNES_AJOUTEES = ("cgu_version", "motif", "retractation_le")


class ErreurPaiement(Exception):
    """Stripe injoignable ou refus de creer la session."""


def ajouter_mois(depart: date, mois: int) -> date:
    """Meme jour N mois plus tard (ou plus tot si N < 0), ou dernier jour du mois s'il n'existe pas
    (31 janvier + 1 = 28 ou 29 fevrier)."""
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


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _il_y_a(**duree) -> str:
    return (datetime.now(timezone.utc) - timedelta(**duree)).isoformat(timespec="seconds")


def _jour_paris(horodatage: str) -> date:
    return datetime.fromisoformat(horodatage).astimezone(FUSEAU).date()


def retractable(paye_le: str | None) -> bool:
    return bool(paye_le) and datetime.now(FUSEAU).date() <= _jour_paris(paye_le) + timedelta(days=DELAI_RETRACTATION)


MOIS_FR = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
           "novembre", "décembre")


def date_fr(d: date) -> str:
    return f"{d.day} {MOIS_FR[d.month - 1]} {d.year}"


def euros(centimes: int) -> str:
    return f"{centimes // 100},{centimes % 100:02d} €"


class Paiements:
    """Table des paiements, dans la base des comptes : l'activation de la formule et le passage du paiement a
    « paye » se font dans une seule transaction (un webhook rejoue n'active jamais deux fois)."""

    def __init__(self, comptes: Comptes):
        self.comptes = comptes
        # shortcut: connexion et verrou de Comptes reutilises pour une transaction commune aux deux tables
        with comptes._lock, comptes._con:
            comptes._con.executescript(SCHEMA)
            colonnes = {r[1] for r in comptes._con.execute("PRAGMA table_info(paiements)")}
            for col in COLONNES_AJOUTEES:
                if col not in colonnes:
                    comptes._con.execute(f"ALTER TABLE paiements ADD COLUMN {col} TEXT")

    def ouvrir(self, session: str, u: Utilisateur, formule: str, mois: int, montant: int,
               cgu_version: str = VERSION_CGU) -> None:
        maintenant = _maintenant()
        self.comptes._q("INSERT INTO paiements (session, utilisateur, email, formule, mois, montant_centimes, devise, "
                        "execution_immediate_le, cgu_version, cree_le) VALUES (?, ?, ?, ?, ?, ?, 'eur', ?, ?, ?)",
                        (session, u.id, u.email, formule, mois, montant, maintenant, cgu_version, maintenant))

    def _dicts(self, sql: str, params: tuple = ()) -> list[dict]:
        with self.comptes._lock:
            cur = self.comptes._con.execute(sql, params)
            noms = [c[0] for c in cur.description]
            return [dict(zip(noms, r)) for r in cur.fetchall()]

    def ligne(self, session: str) -> dict | None:
        lignes = self._dicts("SELECT * FROM paiements WHERE session = ?", (session,))
        return lignes[0] if lignes else None

    def marquer(self, session: str, statut: str, depuis: tuple[str, ...]) -> bool:
        """Change le statut d'un paiement s'il est encore dans l'un des statuts « depuis »."""
        marques = ",".join("?" * len(depuis))
        with self.comptes._lock, self.comptes._con:
            return self.comptes._con.execute(f"UPDATE paiements SET statut = ? WHERE session = ? AND statut IN "
                                             f"({marques})", (statut, session, *depuis)).rowcount == 1

    def purger(self) -> None:
        """Pages de paiement jamais payees de plus de 30 jours : rien a garder (pas une piece comptable)."""
        self.comptes._q("DELETE FROM paiements WHERE statut IN ('ouvert', 'expire', 'echec') AND cree_le < ?",
                        (_il_y_a(days=30),))

    def recentes(self, uid: int) -> list[tuple[str, str]]:
        """(session, statut) des paiements du compte ouverts ces dernieres 24 h ou encore en attente."""
        return self.comptes._q("SELECT session, statut FROM paiements WHERE utilisateur = ? AND (cree_le >= ? OR "
                               "(statut = 'en_attente' AND cree_le >= ?))", (uid, _il_y_a(days=1), _il_y_a(days=14)))

    def etat(self, uid: int) -> dict:
        lignes = self.comptes._q("SELECT statut, formule, mois, paye_le FROM paiements WHERE utilisateur = ? "
                                 "ORDER BY id DESC", (uid,))
        dernier = dict(zip(("statut", "formule", "mois", "paye_le"), lignes[0])) if lignes else None
        return {"dernier": dernier, "retractable": any(s == "paye" and retractable(p) for s, _, _, p in lignes)}

    def a_traiter(self) -> list[dict]:
        return self._dicts("SELECT session, email, formule, mois, montant_centimes, statut, motif, cree_le, paye_le, "
                           "retractation_le, paiement_stripe FROM paiements WHERE statut IN "
                           f"({','.join('?' * len(A_TRAITER))}) ORDER BY id DESC", A_TRAITER)

    @staticmethod
    def _retirer(con, uid: int, formule: str, mois: int) -> None:
        """Retire les mois d'un paiement annule (retractation, remboursement, litige) de la formule du compte."""
        u = con.execute("SELECT formule, formule_fin FROM utilisateurs WHERE id = ?", (uid,)).fetchone()
        if u is None or u[0] != formule or u[1] is None:
            return   # compte supprime, autre formule, ou formule donnee sans fin : rien a retirer
        fin = ajouter_mois(date.fromisoformat(u[1]), -mois)
        if fin <= datetime.now(FUSEAU).date():
            con.execute("UPDATE utilisateurs SET formule = ?, formule_fin = NULL WHERE id = ?", (FORMULE_PAR_DEFAUT, uid))
        else:
            con.execute("UPDATE utilisateurs SET formule_fin = ? WHERE id = ?", (fin.isoformat(), uid))

    def encaisser(self, session: str, montant: int | None, devise: str | None, paiement_stripe: str | None) -> str:
        """Paiement confirme par Stripe : active la formule. Renvoie ce qui a ete fait (pour le journal).

        Jamais d'activation par-dessus une autre formule en cours, payee ou donnee sans fin (audit A1, A2) :
        le paiement passe a « a_rembourser » et apparait dans l'administration."""
        c = self.comptes
        with c._lock, c._con:
            ligne = c._con.execute("SELECT utilisateur, formule, mois, montant_centimes, devise, statut FROM paiements "
                                   "WHERE session = ?", (session,)).fetchone()
            if ligne is None:
                return "inconnu"
            uid, formule, mois, attendu, devise_attendue, statut = ligne
            if statut not in ("ouvert", "en_attente"):
                return "deja_traite"
            maintenant = _maintenant()

            def classer(statut: str, motif: str | None) -> str:
                c._con.execute("UPDATE paiements SET statut = ?, motif = ?, paye_le = ?, paiement_stripe = ? "
                               "WHERE session = ?", (statut, motif, maintenant, paiement_stripe, session))
                if motif:
                    log.warning("paiement %s : %s (%s)", session, statut, motif)
                return motif or "active"

            if montant != attendu or (devise or "").lower() != devise_attendue:
                log.warning("paiement %s : montant %s %s, attendu %s %s", session, montant, devise, attendu,
                            devise_attendue)
                return classer("ecarte", "montant_inattendu")
            u = c._con.execute("SELECT formule, formule_fin FROM utilisateurs WHERE id = ?", (uid,)).fetchone()
            if u is None:  # compte supprime entre le paiement et le signal
                return classer("a_rembourser", "compte_absent")
            aujourd_hui = datetime.now(FUSEAU).date()
            en_cours = u[0] != FORMULE_PAR_DEFAUT and (u[1] is None or u[1] >= aujourd_hui.isoformat())
            if en_cours and u[0] != formule:
                return classer("a_rembourser", "autre_formule")
            if en_cours and u[1] is None:
                return classer("a_rembourser", "deja_sans_fin")  # meme formule donnee sans fin : rien a prolonger
            depart = date.fromisoformat(u[1]) if en_cours else aujourd_hui  # meme formule en cours : prolongee
            c._con.execute("UPDATE utilisateurs SET formule = ?, formule_fin = ? WHERE id = ?",
                           (formule, ajouter_mois(depart, mois).isoformat(), uid))
            return classer("paye", None)

    def retracter(self, uid: int) -> list[dict]:
        """Retractation en ligne : chaque paiement de moins de 14 jours est annule et passe « a_rembourser »."""
        c = self.comptes
        faits = []
        with c._lock, c._con:
            for session, formule, mois, montant, paye_le in c._con.execute(
                    "SELECT session, formule, mois, montant_centimes, paye_le FROM paiements "
                    "WHERE utilisateur = ? AND statut = 'paye' ORDER BY id DESC", (uid,)).fetchall():
                if not retractable(paye_le):
                    continue
                self._retirer(c._con, uid, formule, mois)
                c._con.execute("UPDATE paiements SET statut = 'a_rembourser', motif = 'retractation', "
                               "retractation_le = ? WHERE session = ?", (_maintenant(), session))
                faits.append({"session": session, "formule": formule, "mois": mois, "montant_centimes": montant})
        return faits

    def rembourser(self, paiement_stripe: str, complet: bool) -> str:
        """Remboursement fait dans Stripe (charge.refunded)."""
        c = self.comptes
        with c._lock, c._con:
            ligne = c._con.execute("SELECT session, utilisateur, formule, mois, statut FROM paiements "
                                   "WHERE paiement_stripe = ?", (paiement_stripe,)).fetchone()
            if ligne is None:
                return "inconnu"
            session, uid, formule, mois, statut = ligne
            if statut == "a_rembourser" or (statut == "ecarte" and complet):
                nouveau = "rembourse"           # remboursement attendu (retractation, formule non activee)
            elif statut in ("paye", "rembourse_partiel"):
                nouveau = "rembourse" if complet else "rembourse_partiel"
                if complet:
                    self._retirer(c._con, uid, formule, mois)
            else:
                return "deja_traite"
            c._con.execute("UPDATE paiements SET statut = ? WHERE session = ?", (nouveau, session))
            return nouveau

    def contester(self, paiement_stripe: str, raison: str) -> str:
        """Contestation du paiement aupres de la banque (charge.dispute.created) : la formule est retiree."""
        c = self.comptes
        with c._lock, c._con:
            ligne = c._con.execute("SELECT session, utilisateur, formule, mois, statut FROM paiements "
                                   "WHERE paiement_stripe = ?", (paiement_stripe,)).fetchone()
            if ligne is None:
                return "inconnu"
            session, uid, formule, mois, statut = ligne
            if statut in ("paye", "rembourse_partiel"):
                self._retirer(c._con, uid, formule, mois)
            c._con.execute("UPDATE paiements SET statut = 'litige', motif = ? WHERE session = ?",
                           (f"litige : {raison}", session))
            return "litige"


def _formule_en_cours(u: Utilisateur) -> str | None:
    """Formule payante encore active, avec ou sans date de fin (u.formule tient compte de l'echeance)."""
    f = u.formule
    return f.id if f.prix_mensuel_euros > 0 else None


class DemandePaiement(BaseModel):
    formule: str
    mois: int = Field(ge=1, le=MOIS_MAX)
    execution_immediate: bool
    cgu_version: str = ""   # version des conditions acceptee (case cochee), egale a VERSION_CGU


INDISPONIBLE = "Le paiement est momentanément indisponible. Réessayez dans quelques instants."
EN_COURS = ("Un paiement précédent est en cours de confirmation : attendez quelques minutes, puis rechargez "
            "la page Mon compte.")


def creer_routes_paiement(paiements: Paiements, utilisateur_requis, verifier_origine, *, cle: str, secret_webhook: str,
                          url_publique: str, journal=None, client: httpx.Client | None = None,
                          admin_requis=None, vendeur: str = "") -> APIRouter:
    router = APIRouter()
    http = client or httpx.Client(timeout=15)

    def noter(**champs) -> None:
        if journal is not None:
            journal.ecrire("admin", action="paiement", **champs)

    def expirer(session: str) -> bool:
        """Ferme une page de paiement ouverte. Faux si elle a deja ete payee (signal de Stripe pas encore recu)."""
        try:
            r = http.post(f"{API}/{session}/expire", auth=(cle, ""))
            if r.status_code == 200:
                return True
            r = http.get(f"{API}/{session}", auth=(cle, ""))
        except httpx.HTTPError as e:
            log.warning("stripe injoignable : %s", e)
            raise HTTPException(503, INDISPONIBLE)
        # 404 : session d'un autre compte Stripe (cles de test remplacees par les cles reelles)
        return r.status_code == 404 or (r.status_code == 200 and r.json().get("status") == "expired")

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
            fin = f" jusqu'au {date_fr(date.fromisoformat(u.formule_fin))}" if u.formule_fin else ""
            raise HTTPException(409, f"Votre formule {u.formule.nom} est en cours{fin} : "
                                     "vous pourrez en changer à son échéance.")
        if en_cours and not u.formule_fin:
            raise HTTPException(422, f"La formule {f.nom} vous est déjà acquise sans limite de durée.")
        paiements.purger()
        recentes = paiements.recentes(u.id)
        if len(recentes) >= SESSIONS_PAR_JOUR:
            raise HTTPException(429, "Trop de tentatives de paiement aujourd'hui. Réessayez demain ou écrivez-nous.")
        if any(statut == "en_attente" for _, statut in recentes):
            raise HTTPException(409, EN_COURS)
        # Une seule page de paiement ouverte par compte : deux onglets ne peuvent pas payer deux fois (audit A1)
        for ancienne, statut in recentes:
            if statut == "ouvert":
                if not expirer(ancienne):
                    raise HTTPException(409, EN_COURS)
                paiements.marquer(ancienne, "expire", depuis=("ouvert",))
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
            "expires_at": str(int(time.time()) + DUREE_SESSION),
            "success_url": f"{url_publique}/compte?paiement=ok",
            "cancel_url": f"{url_publique}/tarifs",
        }
        try:
            r = http.post(API, data=donnees, auth=(cle, ""))
        except httpx.HTTPError as e:
            log.warning("stripe injoignable : %s", e)
            raise HTTPException(503, INDISPONIBLE)
        if r.status_code != 200:
            log.warning("stripe a refuse la session (%s) : %s", r.status_code, r.text[:300])
            raise HTTPException(503, INDISPONIBLE)
        s = r.json()
        paiements.ouvrir(s["id"], u, f.id, req.mois, unitaire * req.mois)
        return {"url": s["url"]}

    @router.get("/etat")
    def etat(u: Utilisateur = Depends(utilisateur_requis)):
        """Dernier paiement du compte (retour de la page Stripe) et retractation possible."""
        return paiements.etat(u.id)

    @router.post("/retractation", dependencies=[Depends(verifier_origine)])
    def retractation(u: Utilisateur = Depends(utilisateur_requis)):
        """Fonction de retractation en ligne (art. L. 221-21 du Code de la consommation)."""
        faits = paiements.retracter(u.id)
        if not faits:
            raise HTTPException(409, "Aucun achat de moins de 14 jours à annuler.")
        noter(resultat="retractation", sessions=[p["session"] for p in faits])
        try:
            courriel.envoyer_accuse_retractation(
                u.email, date=date_fr(datetime.now(FUSEAU).date()),
                formules=", ".join(f"formule {FORMULES[p['formule']].nom}, {p['mois']} mois, "
                                   f"{euros(p['montant_centimes'])}" for p in faits))
        except courriel.ErreurCourriel:
            log.warning("accuse de retractation non envoye")
        return {"retractes": len(faits)}

    if admin_requis is not None:
        @router.get("/a-traiter")
        def a_traiter(_: Utilisateur = Depends(admin_requis)):
            return paiements.a_traiter()

    def confirmer(session: str, resultat: str) -> None:
        """E-mail apres l'encaissement : confirmation du contrat (L. 221-13), ou paiement a rembourser."""
        p = paiements.ligne(session)
        f = FORMULES.get(p["formule"]) if p else None
        if f is None:
            return
        try:
            if resultat == "active":
                u = paiements.comptes.par_id(p["utilisateur"])
                courriel.envoyer_confirmation_paiement(
                    p["email"], formule=f.nom, mois=p["mois"], prix=euros(p["montant_centimes"]),
                    fin=date_fr(date.fromisoformat(u.formule_fin)) if u and u.formule_fin else "",
                    cgu_version=p["cgu_version"] or "",
                    acces_immediat_le=datetime.fromisoformat(p["execution_immediate_le"]).astimezone(FUSEAU)
                    .strftime("le %d/%m/%Y à %H:%M"),
                    retractation_jusquau=date_fr(_jour_paris(p["paye_le"]) + timedelta(days=DELAI_RETRACTATION)),
                    url_publique=url_publique, vendeur=vendeur)
            elif p["statut"] == "a_rembourser":
                courriel.envoyer_paiement_non_active(p["email"], formule=f.nom, prix=euros(p["montant_centimes"]))
        except courriel.ErreurCourriel:
            log.warning("e-mail du paiement %s non envoye", session)

    def traiter(evenement: dict) -> None:
        type_ = evenement.get("type")
        o = evenement.get("data", {}).get("object", {})
        if type_ in EVENEMENTS_PAYES and o.get("payment_status") == "paid":
            resultat = paiements.encaisser(o.get("id", ""), o.get("amount_total"), o.get("currency"),
                                           o.get("payment_intent"))
            noter(session=o.get("id"), resultat=resultat)
            if resultat != "deja_traite":
                confirmer(o.get("id", ""), resultat)
        elif type_ == "checkout.session.completed":   # moyen de paiement differe : confirme plus tard
            paiements.marquer(o.get("id", ""), "en_attente", depuis=("ouvert",))
        elif type_ == "checkout.session.async_payment_failed":
            paiements.marquer(o.get("id", ""), "echec", depuis=("ouvert", "en_attente"))
        elif type_ == "checkout.session.expired":
            paiements.marquer(o.get("id", ""), "expire", depuis=("ouvert",))
        elif type_ == "charge.refunded" and o.get("payment_intent"):
            noter(paiement=o["payment_intent"], resultat=paiements.rembourser(o["payment_intent"], bool(o.get("refunded"))))
        elif type_ == "charge.dispute.created" and o.get("payment_intent"):
            noter(paiement=o["payment_intent"], resultat=paiements.contester(o["payment_intent"], o.get("reason", "")))

    @router.post("/webhook")
    async def webhook(request: Request):
        corps = await request.body()
        if not verifier_signature(corps, request.headers.get("stripe-signature"), secret_webhook):
            raise HTTPException(400, "Signature invalide.")
        # SQLite et Resend bloquent : hors de la boucle d'evenements (audit A8)
        await run_in_threadpool(traiter, json.loads(corps))
        return {"recu": True}

    return router
