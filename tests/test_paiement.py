"""Paiement par Stripe Checkout (D86) : session, webhook signe, activation unique de la formule."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import date, datetime

import httpx
import pytest
from fastapi.testclient import TestClient

from api.comptes import FUSEAU, Comptes
from api.config import Settings
from api.main import create_app
from api.paiement import ajouter_mois, verifier_signature
from tests.test_comptes import LLM, Retriever, inscrire

SECRET = "whsec_essai"


class Stripe:
    """Faux Stripe : enregistre la demande de session et renvoie une session ouverte."""

    def __init__(self):
        self.demandes = []
        self.n = 0

    def transport(self):
        def repondre(requete: httpx.Request) -> httpx.Response:
            self.n += 1
            self.demandes.append(dict(httpx.QueryParams(requete.content.decode())))
            self.auth = requete.headers.get("authorization")
            return httpx.Response(200, json={"id": f"cs_test_{self.n}", "url": f"https://checkout.stripe.com/c/pay/cs_test_{self.n}"})
        return httpx.MockTransport(repondre)


@pytest.fixture
def env(tmp_path):
    comptes = Comptes(tmp_path / "comptes.db")
    stripe = Stripe()
    settings = Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0,
                        stripe_secret_key="sk_test_essai", stripe_webhook_secret=SECRET,
                        url_publique="https://lexia.exemple")
    app = create_app(settings, retriever=Retriever(), llm=LLM(), comptes=comptes,
                     client_stripe=httpx.Client(transport=stripe.transport()))
    client = TestClient(app)
    inscrire(client)
    return client, comptes, stripe


def signer(corps: bytes, t: int | None = None, secret: str = SECRET) -> str:
    t = int(time.time()) if t is None else t
    sig = hmac.new(secret.encode(), f"{t}.".encode() + corps, hashlib.sha256).hexdigest()
    return f"t={t},v1={sig}"


def evenement(session: str, montant: int, statut: str = "paid", type_: str = "checkout.session.completed") -> bytes:
    return json.dumps({"id": "evt_1", "type": type_, "data": {"object": {
        "id": session, "payment_status": statut, "amount_total": montant, "currency": "eur",
        "payment_intent": "pi_1"}}}).encode()


def payer(client, corps: bytes, entete: str | None = None):
    return client.post("/paiement/webhook", content=corps,
                       headers={"Stripe-Signature": entete or signer(corps), "Content-Type": "application/json"})


def test_config_annonce_le_paiement(env):
    client, _, _ = env
    assert client.get("/config").json()["paiement"] is True


def test_paiement_inactif_sans_cles(tmp_path):
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs"), retriever=Retriever(),
                     llm=LLM(), comptes=Comptes(tmp_path / "c.db"))
    client = TestClient(app)
    assert client.get("/config").json()["paiement"] is False
    assert client.post("/paiement/webhook", content=b"{}").status_code == 404


def test_session_creee_avec_le_bon_montant(env):
    client, comptes, stripe = env
    r = client.post("/paiement/session", json={"formule": "etudiant", "mois": 3, "execution_immediate": True})
    assert r.status_code == 200 and r.json()["url"].startswith("https://checkout.stripe.com/")
    d = stripe.demandes[0]
    assert d["mode"] == "payment" and d["line_items[0][price_data][unit_amount]"] == "499"
    assert d["line_items[0][quantity]"] == "3" and d["line_items[0][price_data][currency]"] == "eur"
    assert d["customer_email"] == "etu@exemple.fr" and d["success_url"] == "https://lexia.exemple/compte?paiement=ok"
    assert stripe.auth.startswith("Basic ")
    ligne = comptes._q("SELECT formule, mois, montant_centimes, statut, execution_immediate_le FROM paiements")[0]
    assert ligne[:4] == ("etudiant", 3, 1497, "ouvert") and ligne[4]


@pytest.mark.parametrize("corps, code", [
    ({"formule": "etudiant", "mois": 1, "execution_immediate": False}, 422),
    ({"formule": "gratuit", "mois": 1, "execution_immediate": True}, 422),
    ({"formule": "inconnue", "mois": 1, "execution_immediate": True}, 422),
    ({"formule": "etudiant", "mois": 0, "execution_immediate": True}, 422),
    ({"formule": "etudiant", "mois": 13, "execution_immediate": True}, 422),
])
def test_demandes_refusees(env, corps, code):
    client, _, stripe = env
    assert client.post("/paiement/session", json=corps).status_code == code
    assert stripe.demandes == []


def test_session_exige_une_connexion(env):
    client, _, _ = env
    client.cookies.clear()
    assert client.post("/paiement/session", json={"formule": "etudiant", "mois": 1,
                                                  "execution_immediate": True}).status_code == 401


def test_webhook_active_la_formule_une_seule_fois(env):
    client, comptes, _ = env
    client.post("/paiement/session", json={"formule": "etudiant", "mois": 2, "execution_immediate": True})
    corps = evenement("cs_test_1", 998)
    assert payer(client, corps).status_code == 200
    attendu = ajouter_mois(datetime.now(FUSEAU).date(), 2).isoformat()
    u = comptes.par_email("etu@exemple.fr")
    assert (u.formule_id, u.formule_fin) == ("etudiant", attendu)
    assert payer(client, corps).status_code == 200  # rejoue par Stripe : rien de plus
    assert comptes.par_email("etu@exemple.fr").formule_fin == attendu
    assert comptes._q("SELECT statut, paiement_stripe FROM paiements")[0] == ("paye", "pi_1")


def test_meme_formule_prolongee(env):
    client, comptes, _ = env
    for n in (1, 2):
        client.post("/paiement/session", json={"formule": "intensif", "mois": 1, "execution_immediate": True})
        payer(client, evenement(f"cs_test_{n}", 999))
    attendu = ajouter_mois(ajouter_mois(datetime.now(FUSEAU).date(), 1), 1).isoformat()
    assert comptes.par_email("etu@exemple.fr").formule_fin == attendu


def test_autre_formule_en_cours_refusee(env):
    client, comptes, _ = env
    comptes.changer_formule("etu@exemple.fr", "intensif", 10)
    r = client.post("/paiement/session", json={"formule": "etudiant", "mois": 1, "execution_immediate": True})
    assert r.status_code == 409


def test_signature_fausse_ou_ancienne_refusee(env):
    client, comptes, _ = env
    client.post("/paiement/session", json={"formule": "etudiant", "mois": 1, "execution_immediate": True})
    corps = evenement("cs_test_1", 499)
    assert payer(client, corps, signer(corps, secret="whsec_autre")).status_code == 400
    assert payer(client, corps, signer(corps, t=int(time.time()) - 600)).status_code == 400
    assert payer(client, corps, "t=1").status_code == 400
    assert comptes.par_email("etu@exemple.fr").formule_id == "gratuit"


def test_montant_inattendu_ou_non_paye(env):
    client, comptes, _ = env
    client.post("/paiement/session", json={"formule": "etudiant", "mois": 1, "execution_immediate": True})
    payer(client, evenement("cs_test_1", 499, statut="unpaid"))
    assert comptes.par_email("etu@exemple.fr").formule_id == "gratuit"
    payer(client, evenement("cs_test_1", 100))
    assert comptes.par_email("etu@exemple.fr").formule_id == "gratuit"
    assert comptes._q("SELECT statut FROM paiements")[0] == ("ecarte",)


def test_paiement_garde_apres_suppression_du_compte(env):
    client, comptes, _ = env
    client.post("/paiement/session", json={"formule": "etudiant", "mois": 1, "execution_immediate": True})
    payer(client, evenement("cs_test_1", 499))
    comptes.supprimer(comptes.par_email("etu@exemple.fr").id)
    assert comptes._q("SELECT email, statut FROM paiements") == [("etu@exemple.fr", "paye")]


def test_ajouter_mois_fin_de_mois():
    assert ajouter_mois(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert ajouter_mois(date(2026, 11, 17), 2) == date(2027, 1, 17)
    assert ajouter_mois(date(2027, 12, 31), 12) == date(2028, 12, 31)


def test_signature_entrees_inconnues_ignorees():
    corps = b'{"a":1}'
    t = int(time.time())
    entete = signer(corps, t) + ",v0=abc,secret=whsec_****,destination=we_1,payload=a2"
    assert verifier_signature(corps, entete, SECRET)
    assert not verifier_signature(corps + b" ", entete, SECRET)
