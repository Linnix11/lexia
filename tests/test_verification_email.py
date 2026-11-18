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
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0,
                              url_publique="https://lexia.test"),
                     retriever=Retriever(), llm=LLM(), comptes=comptes)
    return TestClient(app), comptes, envoyes


def jeton_de(lien: str) -> str:
    return lien.split("jeton=")[1]


def test_inscription_envoie_le_lien_et_bloque_les_questions(env):
    client, _, envoyes = env
    r = inscrire(client)
    assert r.status_code == 201 and r.json()["email_verifie"] is False
    assert len(envoyes) == 1 and envoyes[0][0] == "etu@exemple.fr"
    assert "/verifier-email#jeton=" in envoyes[0][1]

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
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0,
                              url_publique="https://lexia.test"),
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


def test_le_lien_ne_suit_jamais_l_en_tete_host(env):
    """Un domaine tiers pointe sur le serveur faisait envoyer, depuis l'adresse de Lexia, des liens vers lui."""
    client, _, envoyes = env
    client.post("/auth/inscription", json={"email": "etu@exemple.fr", "mot_de_passe": "motdepasse-solide",
                                           "accepte_cgu": True},
                headers={"Host": "pirate.example", "Origin": "https://pirate.example"})
    assert envoyes and envoyes[0][1].startswith("https://lexia.test/verifier-email#jeton=")


def test_sans_url_publique_aucun_lien_n_est_envoye(tmp_path, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "cle-de-test")
    envoyes = []
    monkeypatch.setattr(courriel, "envoyer_verification", lambda dest, lien: envoyes.append(lien))
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0),
                     retriever=Retriever(), llm=LLM(), comptes=Comptes(tmp_path / "c.db"))
    assert inscrire(TestClient(app)).status_code == 201 and envoyes == []


def test_renvois_plafonnes_par_compte(env, monkeypatch):
    """Sans plafond, un compte inscrit a l'adresse d'un tiers lui envoyait 720 e-mails par jour (audit 2, point 4)."""
    client, comptes, envoyes = env
    inscrire(client)
    monkeypatch.setattr(comptes, "jeton_verification", lambda uid, force=False: "jeton")  # sans les 2 minutes d'ecart
    codes = [client.post("/auth/email/renvoyer").status_code for _ in range(6)]
    assert codes == [202] * 5 + [429]
    assert len(envoyes) == 1 + 5


def test_adresse_squattee_reprise_apres_le_delai_du_lien(env, tmp_path):
    """Un compte cree avec l'adresse d'un tiers et jamais confirme bloquait a vie son inscription (audit 2, point 6)."""
    client, comptes, envoyes = env
    squatteur = TestClient(client.app)
    inscrire(squatteur, mdp="mot-de-passe-du-squatteur")
    assert inscrire(TestClient(client.app)).status_code == 422          # avant 24 h : l'adresse reste prise
    with sqlite3.connect(comptes.chemin) as c:                          # 25 h plus tard
        c.execute("UPDATE utilisateurs SET cree_le = '2000-01-01T00:00:00+00:00'")
    titulaire = TestClient(client.app)
    assert inscrire(titulaire).status_code == 201                       # le vrai titulaire s'inscrit
    assert squatteur.get("/auth/moi").status_code == 401                # la session du squatteur est fermee
    r = titulaire.post("/auth/connexion", json={"email": "etu@exemple.fr", "mot_de_passe": "motdepasse-solide"})
    assert r.status_code == 200


def test_compte_confirme_jamais_remplace(env):
    client, comptes, envoyes = env
    inscrire(client)
    client.post("/auth/email/verifier", json={"jeton": jeton_de(envoyes[0][1])})
    with sqlite3.connect(comptes.chemin) as c:
        c.execute("UPDATE utilisateurs SET cree_le = '2000-01-01T00:00:00+00:00'")
    assert inscrire(TestClient(client.app), mdp="autre-mot-de-passe").status_code == 422


# --- mot de passe oublie --------------------------------------------------------

def _liens_oubli(monkeypatch):
    liens = []
    monkeypatch.setattr(courriel, "envoyer_reinitialisation", lambda dest, lien: liens.append((dest, lien)))
    return liens


def _attendre(liste, n=1):
    import time
    for _ in range(100):
        if len(liste) >= n:
            return
        time.sleep(0.02)


def test_mot_de_passe_oublie_de_bout_en_bout(env, monkeypatch):
    client, _, envoyes = env
    liens = _liens_oubli(monkeypatch)
    inscrire(client)
    client.post("/auth/email/verifier", json={"jeton": jeton_de(envoyes[0][1])})
    autre = TestClient(client.app)
    # Meme reponse pour une adresse inconnue : la page ne dit pas qui est inscrit.
    assert autre.post("/auth/mot-de-passe/oubli", json={"email": "inconnu@exemple.fr"}).json() == {"envoye": True}
    assert autre.post("/auth/mot-de-passe/oubli", json={"email": "etu@exemple.fr"}).json() == {"envoye": True}
    _attendre(liens)
    assert len(liens) == 1 and liens[0][0] == "etu@exemple.fr"
    assert liens[0][1].startswith("https://lexia.test/nouveau-mot-de-passe#jeton=")
    jeton = liens[0][1].split("jeton=")[1]
    assert autre.post("/auth/mot-de-passe/nouveau", json={"jeton": jeton, "mot_de_passe": "court"}).status_code == 422
    r = autre.post("/auth/mot-de-passe/nouveau", json={"jeton": jeton, "mot_de_passe": "nouveau-mot-de-passe"})
    assert r.status_code == 200 and "lexia_session" not in autre.cookies          # le lien n'ouvre pas de session
    assert client.get("/auth/moi").status_code == 401                             # anciennes sessions fermees
    assert autre.post("/auth/mot-de-passe/nouveau", json={"jeton": jeton, "mot_de_passe": "encore-un-autre"}).status_code == 422
    assert autre.post("/auth/connexion", json={"email": "etu@exemple.fr", "mot_de_passe": "motdepasse-solide"}).status_code == 401
    assert autre.post("/auth/connexion", json={"email": "etu@exemple.fr", "mot_de_passe": "nouveau-mot-de-passe"}).status_code == 200


def test_le_titulaire_reprend_une_adresse_squattee(env, monkeypatch):
    """Un tiers a cree le compte avec l'adresse de la victime et active sa double authentification : le lien
    recu dans la vraie boite rend l'adresse a son titulaire (second audit, point 6)."""
    from api import totp
    client, comptes, _ = env
    liens = _liens_oubli(monkeypatch)
    squatteur = TestClient(client.app)
    inscrire(squatteur, mdp="mot-de-passe-du-squatteur")
    secret = squatteur.post("/auth/2fa/preparer").json()["secret"]
    squatteur.post("/auth/2fa/activer", json={"mot_de_passe": "mot-de-passe-du-squatteur",
                                              "code": totp._code(secret, totp.etape_courante())})
    titulaire = TestClient(client.app)
    titulaire.post("/auth/mot-de-passe/oubli", json={"email": "etu@exemple.fr"})
    _attendre(liens)
    titulaire.post("/auth/mot-de-passe/nouveau", json={"jeton": liens[0][1].split("jeton=")[1],
                                                       "mot_de_passe": "le-vrai-mot-de-passe"})
    r = titulaire.post("/auth/connexion", json={"email": "etu@exemple.fr", "mot_de_passe": "le-vrai-mot-de-passe"})
    assert r.status_code == 200 and r.json()["email_verifie"] is True       # adresse confirmee par le lien
    assert r.json()["double_authentification"] is False                    # celle du squatteur est retiree
    assert squatteur.get("/auth/moi").status_code == 401


def test_un_compte_confirme_garde_sa_double_authentification(env, monkeypatch):
    from api import totp
    client, _, envoyes = env
    liens = _liens_oubli(monkeypatch)
    inscrire(client)
    client.post("/auth/email/verifier", json={"jeton": jeton_de(envoyes[0][1])})
    secret = client.post("/auth/2fa/preparer").json()["secret"]
    client.post("/auth/2fa/activer", json={"mot_de_passe": "motdepasse-solide",
                                           "code": totp._code(secret, totp.etape_courante())})
    client.post("/auth/mot-de-passe/oubli", json={"email": "etu@exemple.fr"})
    _attendre(liens)
    client.post("/auth/mot-de-passe/nouveau", json={"jeton": liens[0][1].split("jeton=")[1],
                                                    "mot_de_passe": "nouveau-mot-de-passe"})
    r = client.post("/auth/connexion", json={"email": "etu@exemple.fr", "mot_de_passe": "nouveau-mot-de-passe"})
    assert r.json().get("double_authentification_requise") is True          # le lien seul ne suffit pas a entrer
