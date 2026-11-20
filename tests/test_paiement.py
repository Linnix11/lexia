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
from api.paiement import VERSION_CGU, Paiements, ajouter_mois, verifier_signature
from tests.test_comptes import LLM, Retriever, inscrire

SECRET = "whsec_essai"


class Stripe:
    """Faux Stripe : creation, lecture et expiration des sessions Checkout."""

    def __init__(self):
        self.demandes = []
        self.expirees = []
        self.statuts = {}   # identifiant -> open | complete | expired
        self.n = 0

    def transport(self):
        def repondre(requete: httpx.Request) -> httpx.Response:
            self.auth = requete.headers.get("authorization")
            chemin = requete.url.path
            if chemin.endswith("/expire"):
                sid = chemin.split("/")[-2]
                if self.statuts.get(sid) != "open":
                    return httpx.Response(400, json={"error": {"message": "not open"}})
                self.statuts[sid] = "expired"
                self.expirees.append(sid)
                return httpx.Response(200, json={"id": sid, "status": "expired"})
            if requete.method == "GET":
                sid = chemin.split("/")[-1]
                return httpx.Response(200, json={"id": sid, "status": self.statuts.get(sid, "expired")})
            self.n += 1
            self.demandes.append(dict(httpx.QueryParams(requete.content.decode())))
            sid = f"cs_test_{self.n}"
            self.statuts[sid] = "open"
            return httpx.Response(200, json={"id": sid, "url": f"https://checkout.stripe.com/c/pay/{sid}"})
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
    r = client.post("/paiement/session", json={"formule": "etudiant", "mois": 3, "execution_immediate": True, "cgu_version": VERSION_CGU})
    assert r.status_code == 200 and r.json()["url"].startswith("https://checkout.stripe.com/")
    d = stripe.demandes[0]
    assert d["mode"] == "payment" and d["line_items[0][price_data][unit_amount]"] == "499"
    assert d["line_items[0][quantity]"] == "3" and d["line_items[0][price_data][currency]"] == "eur"
    assert d["customer_email"] == "etu@exemple.fr" and d["success_url"] == "https://lexia.exemple/compte?paiement=ok"
    assert stripe.auth.startswith("Basic ")
    ligne = comptes._q("SELECT formule, mois, montant_centimes, statut, execution_immediate_le, cgu_version FROM paiements")[0]
    assert ligne[:4] == ("etudiant", 3, 1497, "ouvert") and ligne[4] and ligne[5] == VERSION_CGU


@pytest.mark.parametrize("corps, code", [
    ({"formule": "etudiant", "mois": 1, "execution_immediate": False, "cgu_version": VERSION_CGU}, 422),
    ({"formule": "gratuit", "mois": 1, "execution_immediate": True, "cgu_version": VERSION_CGU}, 422),
    ({"formule": "inconnue", "mois": 1, "execution_immediate": True, "cgu_version": VERSION_CGU}, 422),
    ({"formule": "etudiant", "mois": 0, "execution_immediate": True, "cgu_version": VERSION_CGU}, 422),
    ({"formule": "etudiant", "mois": 13, "execution_immediate": True, "cgu_version": VERSION_CGU}, 422),
    # conditions non acceptees, ou acceptees dans une version qui n'est plus en vigueur
    ({"formule": "etudiant", "mois": 1, "execution_immediate": True}, 422),
    ({"formule": "etudiant", "mois": 1, "execution_immediate": True, "cgu_version": "12 novembre 2026"}, 422),
])
def test_demandes_refusees(env, corps, code):
    client, _, stripe = env
    assert client.post("/paiement/session", json=corps).status_code == code
    assert stripe.demandes == []


def test_session_exige_une_connexion(env):
    client, _, _ = env
    client.cookies.clear()
    assert client.post("/paiement/session", json={"formule": "etudiant", "mois": 1,
                                                  "execution_immediate": True, "cgu_version": VERSION_CGU}).status_code == 401


def test_webhook_active_la_formule_une_seule_fois(env):
    client, comptes, _ = env
    client.post("/paiement/session", json={"formule": "etudiant", "mois": 2, "execution_immediate": True, "cgu_version": VERSION_CGU})
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
        client.post("/paiement/session", json={"formule": "intensif", "mois": 1, "execution_immediate": True, "cgu_version": VERSION_CGU})
        payer(client, evenement(f"cs_test_{n}", 999))
    attendu = ajouter_mois(ajouter_mois(datetime.now(FUSEAU).date(), 1), 1).isoformat()
    assert comptes.par_email("etu@exemple.fr").formule_fin == attendu


def test_autre_formule_en_cours_refusee(env):
    client, comptes, _ = env
    comptes.changer_formule("etu@exemple.fr", "intensif", 10)
    r = client.post("/paiement/session", json={"formule": "etudiant", "mois": 1, "execution_immediate": True, "cgu_version": VERSION_CGU})
    assert r.status_code == 409


def test_signature_fausse_ou_ancienne_refusee(env):
    client, comptes, _ = env
    client.post("/paiement/session", json={"formule": "etudiant", "mois": 1, "execution_immediate": True, "cgu_version": VERSION_CGU})
    corps = evenement("cs_test_1", 499)
    assert payer(client, corps, signer(corps, secret="whsec_autre")).status_code == 400
    assert payer(client, corps, signer(corps, t=int(time.time()) - 600)).status_code == 400
    assert payer(client, corps, "t=1").status_code == 400
    assert comptes.par_email("etu@exemple.fr").formule_id == "gratuit"


def test_montant_inattendu_ou_non_paye(env):
    client, comptes, _ = env
    client.post("/paiement/session", json={"formule": "etudiant", "mois": 1, "execution_immediate": True, "cgu_version": VERSION_CGU})
    payer(client, evenement("cs_test_1", 499, statut="unpaid"))
    assert comptes.par_email("etu@exemple.fr").formule_id == "gratuit"
    payer(client, evenement("cs_test_1", 100))
    assert comptes.par_email("etu@exemple.fr").formule_id == "gratuit"
    assert comptes._q("SELECT statut FROM paiements")[0] == ("ecarte",)


def test_paiement_garde_apres_suppression_du_compte(env):
    client, comptes, _ = env
    client.post("/paiement/session", json={"formule": "etudiant", "mois": 1, "execution_immediate": True, "cgu_version": VERSION_CGU})
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


# --- audit du 18 novembre 2026, lot A ------------------------------------------------------------------------

def demander(client, formule="etudiant", mois=1):
    return client.post("/paiement/session", json={"formule": formule, "mois": mois, "execution_immediate": True,
                                                  "cgu_version": VERSION_CGU})


def statut(comptes, session):
    return comptes._q("SELECT statut FROM paiements WHERE session = ?", (session,))[0][0]


@pytest.fixture
def courriels(monkeypatch):
    envoyes = []
    monkeypatch.setattr("api.courriel.envoyer", lambda dest, sujet, texte, html: envoyes.append((dest, sujet, texte)))
    return envoyes


def test_a1_paiement_tardif_n_ecrase_pas_une_autre_formule(env):
    """Deux onglets : Intensif 3 mois puis Etudiant 1 mois, payes tous les deux. L'Intensif reste."""
    client, comptes, _ = env
    paiements = Paiements(comptes)
    u = comptes.par_email("etu@exemple.fr")
    paiements.ouvrir("cs_a", u, "intensif", 3, 2997)
    paiements.ouvrir("cs_b", u, "etudiant", 1, 499)
    payer(client, evenement("cs_a", 2997))
    fin = ajouter_mois(datetime.now(FUSEAU).date(), 3).isoformat()
    payer(client, evenement("cs_b", 499))
    u = comptes.par_email("etu@exemple.fr")
    assert (u.formule_id, u.formule_fin) == ("intensif", fin)
    assert statut(comptes, "cs_b") == "a_rembourser"


def test_a1_formule_donnee_sans_fin_jamais_remplacee(env):
    client, comptes, _ = env
    comptes.changer_formule("etu@exemple.fr", "intensif")   # donnee par un administrateur, sans fin
    assert demander(client, "etudiant").status_code == 409
    Paiements(comptes).ouvrir("cs_x", comptes.par_email("etu@exemple.fr"), "etudiant", 1, 499)
    payer(client, evenement("cs_x", 499))
    u = comptes.par_email("etu@exemple.fr")
    assert (u.formule_id, u.formule_fin) == ("intensif", None)
    assert statut(comptes, "cs_x") == "a_rembourser"


def test_a1_nouvelle_session_expire_la_precedente(env):
    client, comptes, stripe = env
    assert demander(client, "intensif", 3).status_code == 200
    assert demander(client, "etudiant", 1).status_code == 200
    assert stripe.expirees == ["cs_test_1"] and statut(comptes, "cs_test_1") == "expire"
    assert payer(client, evenement("cs_test_1", 2997)).status_code == 200   # signal tardif : ignore
    assert comptes.par_email("etu@exemple.fr").formule_id == "gratuit"


def test_a1_session_precedente_deja_payee_bloque(env):
    client, _, stripe = env
    demander(client, "intensif", 3)
    stripe.statuts["cs_test_1"] = "complete"   # payee chez Stripe, signal pas encore recu
    assert demander(client, "etudiant", 1).status_code == 409
    assert len(stripe.demandes) == 1


def test_a2_meme_formule_sans_fin_refusee(env):
    client, comptes, stripe = env
    comptes.changer_formule("etu@exemple.fr", "etudiant")
    assert demander(client, "etudiant").status_code == 422
    assert stripe.demandes == []
    Paiements(comptes).ouvrir("cs_y", comptes.par_email("etu@exemple.fr"), "etudiant", 1, 499)
    payer(client, evenement("cs_y", 499))
    assert statut(comptes, "cs_y") == "a_rembourser"


def test_a2_compte_supprime_a_rembourser(env):
    client, comptes, _ = env
    demander(client)
    comptes.supprimer(comptes.par_email("etu@exemple.fr").id)
    payer(client, evenement("cs_test_1", 499))
    assert statut(comptes, "cs_test_1") == "a_rembourser"


def test_a3_etat_du_dernier_paiement(env):
    client, _, _ = env
    assert client.get("/paiement/etat").json() == {"dernier": None, "retractable": False, "retractables": []}
    demander(client, "etudiant", 2)
    assert client.get("/paiement/etat").json()["dernier"]["statut"] == "ouvert"
    payer(client, evenement("cs_test_1", 998))
    etat = client.get("/paiement/etat").json()
    assert etat["dernier"]["statut"] == "paye" and etat["dernier"]["formule"] == "etudiant" and etat["retractable"]


def retracter(client, sessions=("cs_test_1",), nom="Camille Martin"):
    return client.post("/paiement/retractation", json={"nom": nom, "sessions": list(sessions)})


def test_a4_retractation_en_ligne(env, courriels):
    """Declaration de retractation en ligne (C. consom. L. 221-21, D. 221-5) : nom, contrat vise, accuse."""
    client, comptes, _ = env
    demander(client, "intensif", 2)
    payer(client, evenement("cs_test_1", 1998))
    etat = client.get("/paiement/etat").json()
    assert [(p["session"], p["formule"], p["montant_centimes"]) for p in etat["retractables"]] == [
        ("cs_test_1", "intensif", 1998)]
    courriels.clear()
    assert retracter(client, nom=" ").status_code == 422          # nom et prenom obligatoires
    assert retracter(client, sessions=()).status_code == 422      # contrat vise obligatoire
    assert retracter(client).status_code == 200
    u = comptes.par_email("etu@exemple.fr")
    assert u.formule.id == "gratuit"
    ligne = comptes._q("SELECT statut, motif, retractation_le, retractation_nom FROM paiements")[0]
    assert ligne[:2] == ("a_rembourser", "retractation") and ligne[2] and ligne[3] == "Camille Martin"
    assert len(courriels) == 1 and courriels[0][0] == "etu@exemple.fr" and "rétractation" in courriels[0][1].lower()
    texte = courriels[0][2]
    heure = datetime.fromisoformat(ligne[2]).astimezone(FUSEAU).strftime("%H:%M")
    for attendu in ("Camille Martin", "Intensif", "2 mois", "19,98", "etu@exemple.fr", heure):
        assert attendu in texte, attendu
    assert client.get("/paiement/etat").json()["retractable"] is False
    assert retracter(client).status_code == 409


def test_a4_retractation_d_un_seul_contrat(env):
    """Le contrat vise est choisi : un autre achat de moins de 14 jours reste en place."""
    client, comptes, _ = env
    for n in (1, 2):
        demander(client, "etudiant", 1)
        payer(client, evenement(f"cs_test_{n}", 499))
    assert retracter(client, sessions=("cs_test_2",)).status_code == 200
    assert (statut(comptes, "cs_test_1"), statut(comptes, "cs_test_2")) == ("paye", "a_rembourser")
    assert comptes.par_email("etu@exemple.fr").formule_fin == ajouter_mois(datetime.now(FUSEAU).date(), 1).isoformat()


def test_a4_retractation_d_un_autre_compte_refusee(env):
    client, comptes, _ = env
    demander(client)
    payer(client, evenement("cs_test_1", 499))
    autre = TestClient(client.app)
    inscrire(autre, "autre@exemple.fr")
    assert retracter(autre).status_code == 409
    assert statut(comptes, "cs_test_1") == "paye"


def test_a4_retractation_garde_la_periode_deja_payee(env):
    """Deux mois achetes l'un apres l'autre : se retracter du second retire seulement le second."""
    client, comptes, _ = env
    demander(client, "etudiant", 1)
    payer(client, evenement("cs_test_1", 499))
    comptes._q("UPDATE paiements SET paye_le = '2026-01-01T10:00:00+00:00' WHERE session = 'cs_test_1'")
    demander(client, "etudiant", 1)
    payer(client, evenement("cs_test_2", 499))
    assert retracter(client, sessions=("cs_test_1", "cs_test_2")).status_code == 200
    attendu = ajouter_mois(datetime.now(FUSEAU).date(), 1).isoformat()
    assert comptes.par_email("etu@exemple.fr").formule_fin == attendu
    assert statut(comptes, "cs_test_1") == "paye"


def test_a4_retractation_hors_delai_refusee(env):
    client, comptes, _ = env
    demander(client)
    payer(client, evenement("cs_test_1", 499))
    comptes._q("UPDATE paiements SET paye_le = '2026-01-01T10:00:00+00:00'")
    assert retracter(client).status_code == 409
    assert comptes.par_email("etu@exemple.fr").formule_id == "etudiant"


def test_a5_confirmation_du_contrat_par_email(env, courriels):
    client, _, _ = env
    demander(client, "intensif", 3)
    payer(client, evenement("cs_test_1", 2997))
    assert len(courriels) == 1
    dest, sujet, texte = courriels[0]
    assert dest == "etu@exemple.fr"
    for attendu in ("Intensif", "3 mois", "29,97", VERSION_CGU, "accès immédiat", "Renoncer au contrat ici",
                    "formulaire de rétractation",
                    "Rayez la mention inutile"):
        assert attendu in texte, attendu
    payer(client, evenement("cs_test_1", 2997))   # rejoue : pas de second e-mail
    assert len(courriels) == 1


def test_a5_email_en_panne_n_empeche_pas_l_activation(env):
    client, comptes, _ = env   # pas de cle Resend : l'envoi echoue
    demander(client)
    assert payer(client, evenement("cs_test_1", 499)).status_code == 200
    assert comptes.par_email("etu@exemple.fr").formule_id == "etudiant"


def charge(type_: str, pi: str = "pi_1", rembourse: bool = True) -> bytes:
    objet = {"id": "ch_1", "object": "charge", "payment_intent": pi, "refunded": rembourse, "amount_refunded": 499}
    if type_ == "charge.dispute.created":
        objet = {"id": "du_1", "object": "dispute", "payment_intent": pi, "charge": "ch_1", "reason": "fraudulent"}
    return json.dumps({"id": "evt_2", "type": type_, "data": {"object": objet}}).encode()


def test_a6_remboursement_complet_retire_la_formule(env):
    client, comptes, _ = env
    demander(client)
    payer(client, evenement("cs_test_1", 499))
    assert payer(client, charge("charge.refunded")).status_code == 200
    assert comptes.par_email("etu@exemple.fr").formule.id == "gratuit"
    assert statut(comptes, "cs_test_1") == "rembourse"


def test_a6_remboursement_partiel_apres_retractation(env):
    client, comptes, _ = env
    demander(client)
    payer(client, evenement("cs_test_1", 499))
    retracter(client)
    payer(client, charge("charge.refunded", rembourse=False))
    assert statut(comptes, "cs_test_1") == "rembourse"


def test_a6_remboursement_partiel_signale(env):
    client, comptes, _ = env
    demander(client)
    payer(client, evenement("cs_test_1", 499))
    payer(client, charge("charge.refunded", rembourse=False))
    assert statut(comptes, "cs_test_1") == "rembourse_partiel"
    assert comptes.par_email("etu@exemple.fr").formule_id == "etudiant"


def test_a6_contestation_retire_la_formule(env):
    client, comptes, _ = env
    demander(client)
    payer(client, evenement("cs_test_1", 499))
    payer(client, charge("charge.dispute.created"))
    assert statut(comptes, "cs_test_1") == "litige"
    assert comptes.par_email("etu@exemple.fr").formule.id == "gratuit"


def test_a6_administration_liste_les_paiements_a_traiter(tmp_path):
    from tests.test_admin import client_connecte
    comptes = Comptes(tmp_path / "c.db", admins=("chef@exemple.fr",))
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0,
                              stripe_secret_key="sk_test_essai", stripe_webhook_secret=SECRET,
                              url_publique="https://lexia.exemple"),
                     retriever=Retriever(), llm=LLM(), comptes=comptes,
                     client_stripe=httpx.Client(transport=Stripe().transport()))
    etu = client_connecte(app, "etu@exemple.fr")
    assert etu.get("/paiement/a-traiter").status_code == 403
    p = Paiements(comptes)
    u = comptes.par_email("etu@exemple.fr")
    for s in ("cs_1", "cs_2", "cs_3"):
        p.ouvrir(s, u, "etudiant", 1, 499)
    comptes.changer_formule("etu@exemple.fr", "intensif")
    payer(etu, evenement("cs_1", 499))   # autre formule en cours : a rembourser
    payer(etu, evenement("cs_2", 100))   # montant inattendu : ecarte
    chef = client_connecte(app, "chef@exemple.fr")
    lignes = chef.get("/paiement/a-traiter").json()
    assert {(l["session"], l["statut"], l["motif"]) for l in lignes} == {
        ("cs_1", "a_rembourser", "autre_formule"), ("cs_2", "ecarte", "montant_inattendu")}
    assert lignes[0]["email"] == "etu@exemple.fr"


def test_a7_session_courte_et_expiree(env):
    client, comptes, stripe = env
    demander(client)
    expire = int(stripe.demandes[0]["expires_at"])
    assert 30 * 60 <= expire - time.time() <= 35 * 60
    corps = json.dumps({"id": "evt_3", "type": "checkout.session.expired",
                        "data": {"object": {"id": "cs_test_1", "payment_status": "unpaid"}}}).encode()
    payer(client, corps)
    assert statut(comptes, "cs_test_1") == "expire"


def test_a7_paiement_differe_en_attente(env):
    client, comptes, _ = env
    demander(client)
    payer(client, evenement("cs_test_1", 499, statut="unpaid"))
    assert statut(comptes, "cs_test_1") == "en_attente"
    assert demander(client, "intensif").status_code == 409   # paiement en cours de traitement
    payer(client, evenement("cs_test_1", 499, type_="checkout.session.async_payment_succeeded"))
    assert comptes.par_email("etu@exemple.fr").formule_id == "etudiant"


def test_a7_menage_et_limite_par_compte(env):
    client, comptes, stripe = env
    u = comptes.par_email("etu@exemple.fr")
    Paiements(comptes).ouvrir("cs_vieux", u, "etudiant", 1, 499)
    comptes._q("UPDATE paiements SET cree_le = '2026-01-01T10:00:00+00:00'")
    codes = [demander(client).status_code for _ in range(11)]
    assert codes[:10] == [200] * 10 and codes[10] == 429
    assert not comptes._q("SELECT 1 FROM paiements WHERE session = 'cs_vieux'")


def test_a8_webhook_n_ecrit_pas_dans_la_boucle(env, monkeypatch):
    import asyncio
    client, _, _ = env
    demander(client)
    hors_boucle = []
    origine = Paiements.encaisser

    def encaisser(self, *args):
        try:
            asyncio.get_running_loop()
            hors_boucle.append(False)
        except RuntimeError:
            hors_boucle.append(True)
        return origine(self, *args)

    monkeypatch.setattr(Paiements, "encaisser", encaisser)
    payer(client, evenement("cs_test_1", 499))
    assert hors_boucle == [True]


def test_a9_revenu_sans_les_formules_donnees_sans_fin(env):
    _, comptes, _ = env
    comptes.changer_formule("etu@exemple.fr", "intensif")
    assert comptes.statistiques(1)["revenu_mensuel_estime"] == 0
    comptes.changer_formule("etu@exemple.fr", "intensif", 10)
    assert comptes.statistiques(1)["revenu_mensuel_estime"] == 9.99


# --- audit du 2026-11-19 : JUR-6 (prorogation du delai), JUR-7 et JUR-8 (renvoi des e-mails) ---------------

def test_jur6_fin_du_delai_prorogee_au_premier_jour_ouvrable():
    """C. consom. L. 221-19 3° : un delai qui expire un samedi, un dimanche ou un jour ferie est proroge."""
    from api.paiement import fin_retractation, jours_feries
    paris = lambda jour: datetime.fromisoformat(f"{jour}T12:00:00+01:00").isoformat()  # noqa: E731
    assert fin_retractation(paris("2026-12-02")) == date(2026, 12, 16)   # mercredi : pas de report
    assert fin_retractation(paris("2026-12-05")) == date(2026, 12, 21)   # 19 = samedi -> lundi 21
    assert fin_retractation(paris("2026-12-06")) == date(2026, 12, 21)   # 20 = dimanche -> lundi 21
    assert fin_retractation(paris("2026-12-11")) == date(2026, 12, 28)   # vendredi 25 = Noel, puis week-end
    assert fin_retractation(paris("2027-03-15")) == date(2027, 3, 30)    # 29 = lundi de Paques 2027
    assert fin_retractation(paris("2027-04-22")) == date(2027, 5, 7)     # 6 = jeudi de l'Ascension
    # paiement le 4 a 23 h 30 UTC, deja le 5 a Paris (0 h 30) : le jour compte est celui de Paris
    assert fin_retractation("2026-12-04T23:30:00+00:00") == date(2026, 12, 21)
    assert fin_retractation("2026-12-04T22:30:00+00:00") == date(2026, 12, 18)
    assert date(2026, 4, 6) in jours_feries(2026) and date(2026, 5, 25) in jours_feries(2026)  # Paques, Pentecote
    assert len(jours_feries(2027)) == 11
    from api.paiement import _paques
    assert [_paques(a) for a in (2024, 2025, 2026, 2027, 2038)] == [
        date(2024, 3, 31), date(2025, 4, 20), date(2026, 4, 5), date(2027, 3, 28), date(2038, 4, 25)]


def test_jur6_bouton_encore_la_le_lundi_apres_un_delai_qui_finit_un_samedi(env, monkeypatch):
    client, comptes, _ = env
    demander(client)
    payer(client, evenement("cs_test_1", 499))
    comptes._q("UPDATE paiements SET paye_le = '2026-12-05T10:00:00+00:00'")

    class Lundi(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 12, 21, 18, 0, tzinfo=FUSEAU).astimezone(tz)

    monkeypatch.setattr("api.paiement.datetime", Lundi)
    etat = client.get("/paiement/etat").json()
    assert etat["retractable"] and etat["retractables"][0]["fin"] == "2026-12-21"
    assert retracter(client).status_code == 200


def test_jur7_accuse_en_echec_dit_a_l_ecran_puis_renvoye(env, monkeypatch):
    client, comptes, _ = env   # pas de cle Resend : l'accuse ne part pas
    demander(client)
    payer(client, evenement("cs_test_1", 499))
    r = retracter(client)
    assert r.status_code == 200 and r.json()["accuse_envoye"] is False
    paiements = Paiements(comptes)
    assert [p["accuse_envoye_le"] for p in paiements.a_traiter()] == [None]
    # Le lendemain, Resend repond : l'accuse part (avec le contenu de la declaration) et n'est plus renvoye
    envoyes = []
    monkeypatch.setenv("RESEND_API_KEY", "re_essai")
    monkeypatch.setattr("api.courriel.envoyer", lambda dest, sujet, texte, html: envoyes.append((dest, sujet, texte)))
    for tache in comptes.taches_quotidiennes:
        tache()
    assert len(envoyes) == 1   # l'accuse ; pas de confirmation pour un contrat dont on s'est retracte
    accuse = envoyes[0]
    assert "Camille Martin" in accuse[2] and "Étudiant" in accuse[2]
    assert paiements.a_traiter()[0]["accuse_envoye_le"]
    for tache in comptes.taches_quotidiennes:
        tache()
    assert len(envoyes) == 1


def test_jur8_confirmation_complete(env, courriels):
    client, _, _ = env
    demander(client, "etudiant", 1)
    payer(client, evenement("cs_test_1", 499))
    texte = courriels[0][2]
    assert "Garantie légale de conformité" in texte and "L. 224-25-12" in texte


def test_jur8_identite_du_vendeur():
    from api.main import identite_vendeur
    s = Settings(gemini_models=("fake",), contact_email="contact@exemple.fr",
                 legal={"editeur": "Jean Dupont", "statut": "entrepreneur individuel", "adresse": "1 rue A, Paris",
                        "telephone": "01 02 03 04 05", "mediateur": "Médiateur X, https://mediateur.exemple"})
    bloc = identite_vendeur(s)
    for attendu in ("Jean Dupont, entrepreneur individuel", "1 rue A", "contact@exemple.fr", "01 02 03 04 05",
                    "Médiateur X"):
        assert attendu in bloc
    assert "Immatriculation" not in bloc   # champ vide : ligne absente


def test_jur11_export_des_donnees_du_compte(env):
    """RGPD art. 15 et 20 : compte (sans secret), compteurs, cours et paiements dans un fichier JSON."""
    client, comptes, _ = env
    demander(client)
    payer(client, evenement("cs_test_1", 499))
    r = client.get("/compte/export")
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    d = r.json()
    assert d["compte"]["email"] == "etu@exemple.fr" and d["compte"]["prenom"] == "Léa" and d["compte"]["nom"] == "Martin"
    assert "mdp" not in d["compte"] and "mdp" not in r.text and "scrypt" not in r.text
    assert [p["formule"] for p in d["paiements"]] == ["etudiant"] and d["paiements"][0]["statut"] == "paye"
    assert d["cours_deposes"] == [] and "navigateur" in d["dans_votre_navigateur"]
    assert TestClient(client.app).get("/compte/export").status_code == 401   # sans session
