"""Tableau de bord administrateur."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

from api.comptes import Comptes
from api.config import Settings
from api.main import create_app
from tests.test_comptes import LLM, Retriever

MDP = "motdepasse-solide"


@pytest.fixture
def env(tmp_path):
    comptes = Comptes(tmp_path / "c.db", admins=("chef@exemple.fr",))
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0,
                              url_publique="https://lexia.test"),
                     retriever=Retriever(), llm=LLM(), comptes=comptes)
    app.state.logs = tmp_path / "logs"
    return app, comptes


def activer_2fa(c) -> str:
    """Active la double authentification du compte connecte ; renvoie le secret."""
    from api import totp
    secret = c.post("/auth/2fa/preparer").json()["secret"]
    assert c.post("/auth/2fa/activer", json={"mot_de_passe": MDP, "code": totp._code(secret, totp.etape_courante())}).status_code == 200
    return secret


def client_connecte(app, email):
    c = TestClient(app)
    if email.startswith("chef"):
        # Adresse d'ADMIN_EMAILS : creee sur le serveur (commande d'administration), jamais depuis le site.
        comptes = app.state.comptes
        comptes.confirmer_email(comptes.creer(email, MDP, depuis_le_site=False).id)
        assert c.post("/auth/connexion", json={"email": email, "mot_de_passe": MDP}).status_code == 200
    else:
        r = c.post("/auth/inscription", json={"email": email, "mot_de_passe": MDP, "accepte_cgu": True,
                                                   "prenom": "Léa", "nom": "Martin"})
        assert r.status_code == 201
    if email.startswith("chef") or email.startswith("adjoint"):
        activer_2fa(c)  # l'administration exige la double authentification
    return c


def test_admin_par_configuration_et_acces_refuse(env):
    app, _ = env
    etu = client_connecte(app, "etu@exemple.fr")
    chef = client_connecte(app, "chef@exemple.fr")
    assert etu.get("/auth/moi").json()["admin"] is False
    assert chef.get("/auth/moi").json()["admin"] is True
    for route in ("/admin/stats", "/admin/clients", "/admin/serveur", "/admin/activite"):
        assert etu.get(route).status_code == 403
        assert TestClient(app).get(route).status_code == 401
        assert chef.get(route).status_code == 200


def test_adresse_admin_ne_s_inscrit_pas_depuis_le_site(env, monkeypatch):
    """Une adresse d'ADMIN_EMAILS sans compte, inscrite par un tiers, devenait administrateur au premier clic du
    vrai titulaire sur le lien recu (second audit du 2026-11-16, points 4 et 15)."""
    from api import courriel
    monkeypatch.setenv("RESEND_API_KEY", "cle-de-test")
    monkeypatch.setattr(courriel, "envoyer_verification", lambda dest, lien: None)
    app, comptes = env
    for adresse in ("chef@exemple.fr", "Chef+admin@exemple.fr"):
        r = TestClient(app).post("/auth/inscription", json={"email": adresse, "mot_de_passe": MDP, "accepte_cgu": True,
                                                   "prenom": "Léa", "nom": "Martin"})
        # Meme message qu'un compte existant : la reponse ne revele pas les adresses d'administration (SEC-7).
        assert r.status_code == 422 and r.json()["detail"] == "Un compte existe déjà avec cette adresse e-mail."
    assert comptes.par_email("chef@exemple.fr") is None


def test_statistiques_et_clients(env):
    app, _ = env
    etu = client_connecte(app, "etu@exemple.fr")
    for _ in range(3):
        assert etu.post("/chat", json={"question": "article 1240"}).status_code == 200
    chef = client_connecte(app, "chef@exemple.fr")
    s = chef.get("/admin/stats").json()
    assert s["comptes"]["total"] == 2 and s["comptes"]["par_formule"]["gratuit"] == 2
    assert s["aujourd_hui"]["questions"] == 3 and s["aujourd_hui"]["actifs"] == 1
    assert len(s["serie"]) == 30 and s["serie"][-1]["inscriptions"] == 2
    assert s["activite"]["dernieres_24h"]["questions"] == 3
    clients = chef.post("/admin/clients/recherche", json={"q": "etu"}).json()   # dans le corps, pas l'URL (D110)
    assert [c["email"] for c in clients] == ["etu@exemple.fr"]
    assert clients[0]["questions_aujourdhui"] == 3 and clients[0]["limite_questions"] == 10


def test_changer_formule_role_et_suppression(env):
    app, comptes = env
    client_connecte(app, "etu@exemple.fr")
    chef = client_connecte(app, "chef@exemple.fr")
    uid = comptes.par_email("etu@exemple.fr").id
    r = chef.post(f"/admin/clients/{uid}/formule", json={"formule": "intensif", "jours": 31})
    assert r.status_code == 200 and r.json()["formule"] == "intensif" and r.json()["formule_fin"]
    assert chef.post(f"/admin/clients/{uid}/formule", json={"formule": "platine"}).status_code == 422
    assert chef.get("/admin/stats").json()["revenu_mensuel_estime"] == 9.99
    assert chef.post(f"/admin/clients/{uid}/admin", json={"admin": True}).json()["admin"] is True
    moi = comptes.par_email("chef@exemple.fr").id
    assert chef.post(f"/admin/clients/{moi}/admin", json={"admin": False}).status_code == 422
    assert chef.post(f"/admin/clients/{moi}/supprimer").status_code == 422
    assert chef.post(f"/admin/clients/{uid}/supprimer").status_code == 204
    assert comptes.par_email("etu@exemple.fr") is None
    assert chef.post("/admin/clients/9999/supprimer").status_code == 404
    journal = (app.state.logs / "admin.jsonl").read_text()
    assert '"action": "formule"' in journal and '"action": "suppression"' in journal


def test_origine_etrangere_refusee(env):
    app, comptes = env
    client_connecte(app, "etu@exemple.fr")
    chef = client_connecte(app, "chef@exemple.fr")
    uid = comptes.par_email("etu@exemple.fr").id
    r = chef.post(f"/admin/clients/{uid}/formule", json={"formule": "intensif"}, headers={"Origin": "https://pirate.exemple"})
    assert r.status_code == 403


def test_etat_serveur(env):
    app, _ = env
    chef = client_connecte(app, "chef@exemple.fr")
    s = chef.get("/admin/serveur").json()
    assert s["uptime_service_s"] >= 0 and s["disque"]["total"] > 0 and s["index"]["moteur"] == "test"
    assert s["etat_modele"] in ("ok", "inconnu", "degrade")


def test_migration_ancienne_base(tmp_path):
    chemin = tmp_path / "ancienne.db"
    con = sqlite3.connect(chemin)
    con.executescript("""CREATE TABLE utilisateurs (id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, mdp TEXT NOT NULL,
        formule TEXT NOT NULL DEFAULT 'gratuit', formule_fin TEXT, cree_le TEXT NOT NULL, cgu_le TEXT NOT NULL);
        INSERT INTO utilisateurs (email, mdp, cree_le, cgu_le) VALUES ('a@b.fr', 'x', '2026-01-01T00:00:00+00:00', 'x');""")
    con.commit()
    con.close()
    comptes = Comptes(chemin)
    assert comptes.par_email("a@b.fr").admin is False
    assert comptes.definir_admin("a@b.fr", True).admin is True



def test_d110_recherche_de_clients_sans_adresse_dans_l_url(env):
    app, _ = env
    client_connecte(app, "etu@exemple.fr")
    chef = client_connecte(app, "chef@exemple.fr")
    # l'ancien parametre d'URL est ignore : la liste complete revient, jamais un filtre sur l'adresse
    assert len(chef.get("/admin/clients", params={"q": "etu"}).json()) == 2
    assert [c["email"] for c in chef.post("/admin/clients/recherche", json={"q": "etu"}).json()] == ["etu@exemple.fr"]
    assert chef.post("/admin/clients/recherche", json={"q": "x" * 101}).status_code == 422
    assert chef.post("/admin/clients/recherche", json={"q": "etu"},
                     headers={"Origin": "https://pirate.exemple"}).status_code == 403
    assert client_connecte(app, "autre@exemple.fr").post("/admin/clients/recherche", json={"q": ""}).status_code == 403


def test_d110_fidelite_par_semaine_d_inscription(env, monkeypatch):
    from datetime import date, datetime, timedelta

    from api import comptes as module
    app, comptes = env
    aujourd_hui = datetime.now(module.FUSEAU).date()
    lundi = aujourd_hui - timedelta(days=aujourd_hui.weekday())
    il_y_a_6 = lundi - timedelta(weeks=4)   # semaine assez ancienne pour 7 jours, pas pour 30
    il_y_a_8 = lundi - timedelta(weeks=8)   # assez ancienne pour les deux

    def compte(email: str, inscrit: date, vu: date | None):
        u = comptes.creer(email, "motdepasse-solide")
        comptes._q("UPDATE utilisateurs SET cree_le = ?, actif_le = ? WHERE id = ?",
                   (f"{inscrit.isoformat()}T10:00:00+00:00", vu.isoformat() if vu else None, u.id))

    compte("a@exemple.fr", il_y_a_6, il_y_a_6 + timedelta(days=8))     # revenu apres 7 jours
    compte("b@exemple.fr", il_y_a_6 + timedelta(days=2), il_y_a_6 + timedelta(days=3))   # pas revenu
    compte("c@exemple.fr", lundi - timedelta(weeks=20), aujourd_hui)    # hors des 12 semaines
    compte("d@exemple.fr", il_y_a_8, il_y_a_8 + timedelta(days=31))     # revenu apres 30 jours
    compte("e@exemple.fr", il_y_a_8 + timedelta(days=6), None)          # jamais revenu
    f = comptes.fidelite(12)
    assert len(f) == 12 and f[-1]["semaine"] == lundi.isoformat()
    ligne = next(x for x in f if x["semaine"] == il_y_a_6.isoformat())
    assert ligne == {"semaine": il_y_a_6.isoformat(), "inscrits": 2, "revenus_7j": 1, "revenus_30j": None}
    assert next(x for x in f if x["semaine"] == il_y_a_8.isoformat()) == {
        "semaine": il_y_a_8.isoformat(), "inscrits": 2, "revenus_7j": 1, "revenus_30j": 1}
    assert f[-1]["revenus_7j"] is None   # semaine en cours
    assert all("email" not in x for x in f)
    chef = client_connecte(app, "chef@exemple.fr")
    assert len(chef.get("/admin/stats").json()["fidelite"]) == 12
