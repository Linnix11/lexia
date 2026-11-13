"""Comptes, sessions, formules et quotas."""

import pytest
from fastapi.testclient import TestClient

from api.admin import main as admin
from api.comptes import Comptes, ErreurCompte, hacher_mdp, verifier_mdp
from api.config import Settings
from api.llm.base import LLMError
from api.main import create_app
from api.retrieval.base import Hit

PASSAGE = {"id": "code_civil:A1240", "source_id": "code_civil", "type": "article", "numero": "1240",
           "entete": "Code civil, article 1240", "texte": "Tout fait quelconque de l'homme...",
           "url": "https://exemple", "version": "v", "meta": {"en_vigueur": True}}
REPONSE = {"statut": "reponse", "titre": "t", "droit_positif": [{"texte": "Règle.", "sources": ["S1"]}],
           "explication": [], "points_incertains": [], "message": ""}


class Retriever:
    mode = "test"

    def search(self, question, **kw):
        return [Hit(PASSAGE, 1.0, {"lexical"})]

    def get(self, pid):
        return PASSAGE if pid == PASSAGE["id"] else None

    def versions(self, s, n):
        return [PASSAGE]

    def couverture(self, s):
        return 0.0

    def stats(self):
        return {"moteur": "test", "passages": 1, "embeddings": 0}


class LLM:
    def __init__(self):
        self.echec = False

    def generate_json(self, **kw):
        if self.echec:
            raise LLMError("503")
        return REPONSE, "fake"


@pytest.fixture
def env(tmp_path):
    comptes = Comptes(tmp_path / "comptes.db")
    llm = LLM()
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0),
                     retriever=Retriever(), llm=llm, comptes=comptes)
    return TestClient(app), comptes, llm


def inscrire(client, email="etu@exemple.fr", mdp="motdepasse-solide"):
    return client.post("/auth/inscription", json={"email": email, "mot_de_passe": mdp, "accepte_cgu": True})


def test_mot_de_passe_hache():
    h = hacher_mdp("motdepasse-solide")
    assert h.startswith("scrypt$") and "motdepasse" not in h
    assert verifier_mdp("motdepasse-solide", h) and not verifier_mdp("autre", h)


def test_inscription_connexion_deconnexion(env):
    client, _, _ = env
    assert client.get("/auth/session").json() is None
    r = inscrire(client)
    assert client.get("/auth/session").json()["email"] == "etu@exemple.fr"
    assert r.status_code == 201 and r.json()["formule"]["id"] == "gratuit"
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert client.get("/auth/moi").json()["email"] == "etu@exemple.fr"
    assert client.post("/auth/deconnexion").status_code == 204
    assert client.get("/auth/moi").status_code == 401
    r = client.post("/auth/connexion", json={"email": "ETU@exemple.fr ", "mot_de_passe": "motdepasse-solide"})
    assert r.status_code == 200
    assert client.post("/auth/connexion", json={"email": "etu@exemple.fr", "mot_de_passe": "faux"}).status_code == 401


def test_inscription_refusee(env):
    client, _, _ = env
    assert client.post("/auth/inscription", json={"email": "a@b.fr", "mot_de_passe": "motdepasse-solide",
                                                  "accepte_cgu": False}).status_code == 422
    assert inscrire(client, email="pas-un-email").status_code == 422
    assert inscrire(client, mdp="court").status_code == 422
    inscrire(client)
    assert "existe déjà" in inscrire(client).json()["detail"]


def test_plafond_d_inscriptions_par_ip(tmp_path):
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0,
                              inscriptions_par_ip_jour=2),
                     retriever=Retriever(), llm=LLM(), comptes=Comptes(tmp_path / "comptes.db"))
    client = TestClient(app)
    assert inscrire(client, email="pris@exemple.fr").status_code == 201
    assert inscrire(client, email="pris@exemple.fr").status_code == 422   # echec : non compte
    assert inscrire(client, email="b@exemple.fr").status_code == 201
    r = inscrire(client, email="c@exemple.fr")
    assert r.status_code == 429 and "demain" in r.json()["detail"]


def test_origine_etrangere_refusee(env):
    client, _, _ = env
    r = client.post("/auth/inscription", headers={"Origin": "https://pirate.exemple"},
                    json={"email": "x@y.fr", "mot_de_passe": "motdepasse-solide", "accepte_cgu": True})
    assert r.status_code == 403


def test_retour_exige_un_compte(env):
    client, _, _ = env
    retour = {"reponse_id": "12345678-aaaa", "utile": True}
    assert client.post("/feedback", json=retour).status_code == 401
    inscrire(client)
    assert client.post("/feedback", json=retour).status_code == 204


def test_chat_exige_un_compte(env):
    client, _, _ = env
    assert client.post("/chat", json={"question": "article 1240"}).status_code == 401
    assert client.get("/sources/code_civil:A1240").status_code == 200   # les sources restent publiques
    assert client.get("/formules").json()[1]["id"] == "etudiant"


def test_quota_gratuit_et_remboursement(env):
    client, comptes, llm = env
    inscrire(client)
    llm.echec = True
    assert client.post("/chat", json={"question": "article 1240"}).status_code == 503
    assert client.get("/auth/moi").json()["usage"]["questions"] == 0      # echec du modele : pas decompte
    llm.echec = False
    for _ in range(10):
        assert client.post("/chat", json={"question": "article 1240"}).status_code == 200
    r = client.post("/chat", json={"question": "article 1240"})
    assert r.status_code == 402 and "Limite du jour" in r.json()["detail"]
    assert client.get("/auth/moi").json()["usage"]["questions"] == 10


def test_sans_extrait_ni_appel_au_modele_rien_n_est_decompte(tmp_path):
    class RetrieverVide(Retriever):
        def search(self, question, **kw):
            return []

    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0),
                     retriever=RetrieverVide(), llm=LLM(), comptes=Comptes(tmp_path / "comptes.db"))
    client = TestClient(app)
    inscrire(client)
    assert client.post("/chat", json={"question": "question hors corpus"}).json()["statut"] == "abstention"
    assert client.post("/quiz", json={"theme": "theme hors corpus"}).json()["obtenu"] == 0
    assert client.get("/auth/moi").json()["usage"] | {"jour": None} == {"jour": None, "questions": 0, "quiz": 0}


def test_plafond_d_appels_modele_simultanes(tmp_path):
    import threading

    entre, libere = threading.Event(), threading.Event()

    class LLMLent(LLM):
        def generate_json(self, **kw):
            entre.set()
            libere.wait(5)
            return super().generate_json(**kw)

    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0,
                              appels_modele_simultanes=1),
                     retriever=Retriever(), llm=LLMLent(), comptes=Comptes(tmp_path / "comptes.db"))
    client = TestClient(app)
    inscrire(client)
    premier = {}
    t = threading.Thread(target=lambda: premier.setdefault("r", client.post("/chat", json={"question": "article 1240"})))
    t.start()
    assert entre.wait(5)
    r = client.post("/chat", json={"question": "article 1240"})
    assert r.status_code == 503                                            # plafond atteint : refus immediat
    assert client.get("/auth/moi").json()["usage"]["questions"] == 1       # le refus n'est pas decompte
    libere.set()
    t.join(5)
    assert premier["r"].status_code == 200


def test_formule_payante_par_l_admin(env, tmp_path, monkeypatch, capsys):
    client, comptes, _ = env
    inscrire(client)
    monkeypatch.setenv("APP_DB", str(tmp_path / "comptes.db"))
    assert admin(["formule", "etu@exemple.fr", "etudiant", "--jours", "31"]) == 0
    moi = client.get("/auth/moi").json()
    assert moi["formule"]["id"] == "etudiant" and moi["formule"]["questions_par_jour"] == 100
    assert moi["formule_fin"] is not None
    assert admin(["formule", "inconnu@exemple.fr", "intensif"]) == 1
    assert admin(["liste"]) == 0 and "etu@exemple.fr" in capsys.readouterr().out


def test_nouveau_mot_de_passe_par_l_admin(env, tmp_path, monkeypatch):
    client, _, _ = env
    inscrire(client)
    monkeypatch.setenv("APP_DB", str(tmp_path / "comptes.db"))
    saisies = iter(["nouveau-mot-de-passe", "nouveau-mot-de-passe"])
    monkeypatch.setattr("getpass.getpass", lambda *_: next(saisies))
    assert admin(["motdepasse", "etu@exemple.fr"]) == 0
    assert client.get("/auth/moi").status_code == 401                     # sessions fermees
    connexion = lambda mdp: client.post("/auth/connexion", json={"email": "etu@exemple.fr", "mot_de_passe": mdp})  # noqa: E731
    assert connexion("motdepasse-solide").status_code == 401
    assert connexion("nouveau-mot-de-passe").status_code == 200
    saisies = iter(["un-mot-de-passe", "different-du-premier"])
    assert admin(["motdepasse", "etu@exemple.fr"]) == 1                   # confirmation differente


def test_formule_expiree_repasse_en_gratuit(tmp_path):
    comptes = Comptes(tmp_path / "c.db")
    comptes.creer("a@b.fr", "motdepasse-solide")
    u = comptes.changer_formule("a@b.fr", "intensif", jours=-1)
    assert u.formule.id == "gratuit"
    with pytest.raises(ErreurCompte):
        comptes.changer_formule("a@b.fr", "platine")


def test_suppression_du_compte(env):
    client, comptes, _ = env
    inscrire(client)
    client.post("/chat", json={"question": "article 1240"})
    assert client.post("/auth/supprimer", json={"mot_de_passe": "faux"}).status_code == 401
    assert client.post("/auth/supprimer", json={"mot_de_passe": "motdepasse-solide"}).status_code == 204
    assert comptes.par_email("etu@exemple.fr") is None
    assert client.get("/auth/moi").status_code == 401


def test_freins_aux_tentatives(env):
    client, _, _ = env
    inscrire(client)
    client.post("/auth/deconnexion")
    codes = [client.post("/auth/connexion", json={"email": "etu@exemple.fr", "mot_de_passe": "faux"}).status_code
             for _ in range(6)]
    assert codes[:5] == [401] * 5 and codes[5] == 429


def test_freins_oublient_les_adresses_expirees():
    """Chaque adresse essayee etait gardee en memoire jusqu'au redemarrage : un balayage d'e-mails
    faisait grossir le service sans fin."""
    import time

    from api.auth import Freins

    f = Freins()
    for i in range(300):
        f.verifier(f"10.0.{i // 100}.{i % 100}", f"inconnu{i}@exemple.fr")
        f.echec(f"inconnu{i}@exemple.fr")
    assert len(f._echecs) == 300
    f._derniere_purge = 0
    f._oublier(time.monotonic() + 16 * 60)  # la fenetre de 15 minutes est passee
    assert not f._echecs and not f._ip
