"""Points mineurs de l'audit de securite du 2026-11-16 (7 a 16) : un test par correctif."""

import sqlite3

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api import totp
from api.auth import Freins
from api.comptes import SCRYPT_P, Comptes, hacher_mdp
from api.quiz import Quiz, QuizService, QuizStore
from tests.test_comptes import env, inscrire  # noqa: F401  (fixture partagee)

MDP = "motdepasse-solide"


def connexion(client, mdp=MDP):
    return client.post("/auth/connexion", json={"email": "etu@exemple.fr", "mot_de_passe": mdp})


def test_7_cinq_faux_mots_de_passe_ne_bloquent_pas_le_titulaire(env):  # noqa: F811
    client, _, _ = env
    inscrire(client)
    attaquant = TestClient(client.app, client=("203.0.113.9", 50000))
    for _ in range(5):
        assert connexion(attaquant, "faux-mot-de-passe").status_code == 401
    assert connexion(attaquant).status_code == 429             # l'adresse qui se trompe est bloquee...
    titulaire = TestClient(client.app, client=("198.51.100.4", 50000))
    assert connexion(titulaire).status_code == 200             # ...pas le titulaire, depuis chez lui


def test_7_plafond_par_compte_toutes_adresses_confondues():
    f = Freins(echecs_compte=3)
    for i in range(3):
        f.verifier(f"10.0.0.{i}", f"e|10.0.0.{i}", "compte:e")
        f.echec(f"e|10.0.0.{i}", "compte:e")
    with pytest.raises(HTTPException) as e:
        f.verifier("10.0.0.99", "e|10.0.0.99", "compte:e")      # une attaque repartie finit par etre arretee
    assert e.value.status_code == 429


def test_8_tester_des_adresses_a_l_inscription_est_plafonne(tmp_path):
    from api.config import Settings
    from api.main import create_app
    from tests.test_comptes import LLM, Retriever
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0,
                              inscriptions_par_ip_jour=3),
                     retriever=Retriever(), llm=LLM(), comptes=Comptes(tmp_path / "c.db"))
    client = TestClient(app)
    assert inscrire(client).status_code == 201
    for _ in range(2):
        assert inscrire(TestClient(app)).status_code == 422            # « un compte existe deja » : compte
    assert inscrire(TestClient(app), email="autre@exemple.fr").status_code == 429


def test_9_chiffres_non_ascii_refuses_sans_erreur_serveur(env):  # noqa: F811
    assert totp.verifier("GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ", "١٢٣٤٥٦") is None
    assert totp.verifier("GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ", "²²²²²²") is None
    client, _, _ = env
    inscrire(client)
    secret = client.post("/auth/2fa/preparer").json()["secret"]
    code = totp._code(secret, totp.etape_courante())
    client.post("/auth/2fa/activer", json={"mot_de_passe": MDP, "code": code})
    client.post("/auth/deconnexion")
    jeton = connexion(client).json()["jeton"]
    assert client.post("/auth/connexion/code", json={"jeton": jeton, "code": "١٢٣٤٥٦"}).status_code == 401


def test_10_ancienne_empreinte_refaite_a_la_connexion(tmp_path):
    import hashlib
    import secrets
    comptes = Comptes(tmp_path / "c.db")
    u = comptes.creer("etu@exemple.fr", MDP)
    sel = secrets.token_bytes(16)
    ancienne = hashlib.scrypt(MDP.encode(), salt=sel, n=2**14, r=8, p=1, dklen=32)
    with sqlite3.connect(tmp_path / "c.db") as c:
        c.execute("UPDATE utilisateurs SET mdp = ? WHERE id = ?", (f"scrypt${2**14}$8$1${sel.hex()}${ancienne.hex()}", u.id))
    assert comptes.authentifier("etu@exemple.fr", MDP) is not None
    with sqlite3.connect(tmp_path / "c.db") as c:
        stocke = c.execute("SELECT mdp FROM utilisateurs WHERE id = ?", (u.id,)).fetchone()[0]
    assert stocke.split("$")[3] == str(SCRYPT_P) and SCRYPT_P >= 5
    assert comptes.authentifier("etu@exemple.fr", MDP) is not None   # toujours valable apres la mise a jour
    assert hacher_mdp(MDP).startswith(f"scrypt${2**14}$8${SCRYPT_P}$")


def test_12_un_questionnaire_ne_se_corrige_que_par_son_auteur():
    store = QuizStore()
    service = QuizService(lexia=None, llm=None, store=store)
    q = {"question": "?", "choix": ["a", "b"], "bonne_reponse": 0, "explication": "", "sources": []}
    store.ajouter(Quiz(id="q1", format="qcm", theme="t", questions=[q], table={}, proprietaire=7))
    assert service.corriger("q1", [{"index": 0, "valeur": 0}], uid=8) is None      # autre compte : introuvable
    assert service.corriger("q1", [{"index": 0, "valeur": 0}], uid=None) is None   # visiteur : introuvable
    assert service.corriger("q1", [{"index": 0, "valeur": 0}], uid=7)["score"] == 1


def test_second_audit_12_corrections_simultanees_un_seul_appel_au_modele():
    """Plusieurs /quiz/correct simultanes sur un questionnaire ouvert lancaient chacun un appel payant."""
    import threading
    import time as t

    class LLMLent:
        def __init__(self):
            self.appels = 0

        def generate_json(self, **kw):
            self.appels += 1
            t.sleep(0.3)
            return {"corrections": [{"index": 0, "evaluation": "correct", "commentaire": "Bien.",
                                     "elements_manquants": []}]}, "fake"

    llm, store = LLMLent(), QuizStore()
    service = QuizService(lexia=None, llm=llm, store=store)
    q = {"question": "?", "elements_attendus": ["a"], "explication": "", "sources": []}
    store.ajouter(Quiz(id="q1", format="ouvertes", theme="t", questions=[q], table={}, proprietaire=7))
    resultats = []
    fils = [threading.Thread(target=lambda: resultats.append(
        service.corriger("q1", [{"index": 0, "valeur": "ma reponse"}], uid=7))) for _ in range(4)]
    for f in fils:
        f.start()
    for f in fils:
        f.join()
    assert llm.appels == 1 and len(resultats) == 4 and all(r == resultats[0] for r in resultats)
