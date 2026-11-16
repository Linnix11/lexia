"""Verification de l'adresse e-mail : envoi, confirmation, blocage des questions."""

import sqlite3

import pytest

from api import courriel
from api.comptes import COLONNES_EMAIL, Comptes
from api.config import Settings
from api.main import create_app
from fastapi.testclient import TestClient
from tests.test_comptes import LLM, Retriever, inscrire


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Envoi configure : les e-mails partent vers une liste au lieu de Resend."""
    monkeypatch.setenv("RESEND_API_KEY", "cle-de-test")
    envoyes: list[tuple[str, str]] = []
    monkeypatch.setattr(courriel, "envoyer_verification", lambda dest, lien: envoyes.append((dest, lien)))
    comptes = Comptes(tmp_path / "comptes.db")
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0),
                     retriever=Retriever(), llm=LLM(), comptes=comptes)
    return TestClient(app), comptes, envoyes


def jeton_de(lien: str) -> str:
    return lien.split("jeton=")[1]


def test_inscription_envoie_le_lien_et_bloque_les_questions(env):
    client, _, envoyes = env
    r = inscrire(client)
    assert r.status_code == 201 and r.json()["email_verifie"] is False
    assert len(envoyes) == 1 and envoyes[0][0] == "etu@exemple.fr"
    assert "/verifier-email?jeton=" in envoyes[0][1]

    # Tant que l'adresse n'est pas confirmee, aucune question n'est possible.
    r = client.post("/chat", json={"question": "Qu'est-ce que le dol ?", "mode": "expliquer",
                                   "matiere": None, "niveau": "L1", "semestre": 1})
    assert r.status_code == 403 and "Confirmez votre adresse" in r.json()["detail"]

    r = client.post("/auth/email/verifier", json={"jeton": jeton_de(envoyes[0][1])})
    assert r.status_code == 200 and r.json()["email_verifie"] is True
    assert client.post("/chat", json={"question": "Qu'est-ce que le dol ?", "mode": "expliquer",
                                      "matiere": None, "niveau": "L1", "semestre": 1}).status_code == 200


def test_jeton_invalide_ou_deja_utilise(env):
    client, _, envoyes = env
    inscrire(client)
    jeton = jeton_de(envoyes[0][1])
    assert client.post("/auth/email/verifier", json={"jeton": "inconnu"}).status_code == 422
    assert client.post("/auth/email/verifier", json={"jeton": jeton}).status_code == 200
    assert client.post("/auth/email/verifier", json={"jeton": jeton}).status_code == 422  # ne sert qu'une fois


def test_le_lien_confirme_sans_ouvrir_de_session(env):
    """Le lien contournait mot de passe et double authentification, et connectait la victime au compte
    d'un tiers inscrit avec son adresse (audit du 2026-11-16)."""
    client, _, envoyes = env
    inscrire(client)
    autre_appareil = TestClient(client.app)
    r = autre_appareil.post("/auth/email/verifier", json={"jeton": jeton_de(envoyes[0][1])})
    assert r.status_code == 200 and r.json() is None
    assert "lexia_session" not in autre_appareil.cookies
    assert autre_appareil.get("/auth/session").json() is None
    assert client.get("/auth/session").json()["email_verifie"] is True       # l'adresse est bien confirmee


def test_faux_jetons_ne_bloquent_pas_les_autres_inscrits(env):
    """Le compteur d'echecs etait commun : 5 faux jetons bloquaient la confirmation pour tout le monde."""
    client, _, envoyes = env
    attaquant = TestClient(client.app, client=("203.0.113.9", 50000))
    for _ in range(6):
        attaquant.post("/auth/email/verifier", json={"jeton": "faux"})
    assert attaquant.post("/auth/email/verifier", json={"jeton": "faux"}).status_code == 429
    inscrire(client)
    assert client.post("/auth/email/verifier", json={"jeton": jeton_de(envoyes[0][1])}).status_code == 200


def test_renvoi_limite_puis_refuse_si_deja_confirme(env):
    client, _, envoyes = env
    inscrire(client)
    # Un envoi vient d'avoir lieu (inscription) : le renvoi immediat est refuse.
    assert client.post("/auth/email/renvoyer").status_code == 429
    assert len(envoyes) == 1
    client.post("/auth/email/verifier", json={"jeton": jeton_de(envoyes[0][1])})
    assert client.post("/auth/email/renvoyer").status_code == 422  # deja confirmee


def test_sans_envoi_configure_rien_ne_bloque(tmp_path, monkeypatch):
    """Sans RESEND_API_KEY, la verification est desactivee : le site reste utilisable."""
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    comptes = Comptes(tmp_path / "comptes.db")
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0),
                     retriever=Retriever(), llm=LLM(), comptes=comptes)
    client = TestClient(app)
    assert inscrire(client).json()["email_verifie"] is True
    assert client.post("/chat", json={"question": "Qu'est-ce que le dol ?", "mode": "expliquer",
                                      "matiere": None, "niveau": "L1", "semestre": 1}).status_code == 200


def test_comptes_anterieurs_restent_utilisables(tmp_path, monkeypatch):
    """Une base d'avant la verification (colonnes absentes) : ses comptes sont consideres confirmes,
    sinon la mise a jour bloquerait tout le monde du jour au lendemain."""
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    chemin = tmp_path / "comptes.db"
    u = Comptes(chemin).creer("ancien@exemple.fr", "motdepasse-solide")
    con = sqlite3.connect(chemin)  # on retire les colonnes pour retrouver l'etat d'avant
    for colonne in COLONNES_EMAIL:
        con.execute(f"ALTER TABLE utilisateurs DROP COLUMN {colonne}")
    con.commit()
    con.close()

    monkeypatch.setenv("RESEND_API_KEY", "cle-de-test")
    assert Comptes(chemin).par_id(u.id).email_verifie is True
