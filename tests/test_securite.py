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

    class Lexia:  # correction par lexia.generer (audit du 2026-11-18, D1)
        def generer(self, *, construire, passages, **kw):
            return (*llm.generate_json(prompt=construire(passages), **kw), passages)

    llm, store = LLMLent(), QuizStore()
    service = QuizService(lexia=Lexia(), llm=None, store=store)
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


# --- Second audit du 2026-11-16 : points 6 a 16 ---------------------------------------------------------

def test_second_audit_6_une_boite_un_compte(env):  # noqa: F811
    """« x+1@ », « x+2@ » ou les points Gmail ouvraient autant de comptes gratuits que de variantes."""
    from api.comptes import forme_canonique
    assert forme_canonique("Jean.Dupont+td3@gmail.com") == forme_canonique("jeandupont@googlemail.com")
    assert forme_canonique("a.b+x@univ.fr") == "a.b@univ.fr"                 # points gardes hors Gmail
    client, _, _ = env
    assert inscrire(client, email="x@exemple.fr").status_code == 201
    r = inscrire(TestClient(client.app), email="x+cours@exemple.fr")
    assert r.status_code == 422 and "existe déjà" in r.json()["detail"]


def test_second_audit_6_supprimer_puis_se_reinscrire_attend_24_h(env):  # noqa: F811
    """Supprimer son compte puis se reinscrire remettait le quota du jour a zero."""
    client, comptes, _ = env
    inscrire(client)
    assert client.post("/auth/supprimer", json={"mot_de_passe": MDP}).status_code in (200, 204)
    r = inscrire(TestClient(client.app))
    assert r.status_code == 422 and "24 heures" in r.json()["detail"]
    # suppression par l'administration (compte de test, demande de l'etudiant) : pas de delai
    autre = comptes.creer("autre@exemple.fr", MDP)
    comptes.supprimer(autre.id)
    assert comptes.creer("autre@exemple.fr", MDP) is not None


def test_second_audit_7_ipv6_compte_par_reseau_64():
    from types import SimpleNamespace

    from api.auth import cle_ip
    req = lambda h: SimpleNamespace(client=SimpleNamespace(host=h))  # noqa: E731
    assert cle_ip(req("2001:db8:1:2::1")) == cle_ip(req("2001:db8:1:2:ffff::9")) == "2001:db8:1:2::/64"
    assert cle_ip(req("2001:db8:1:3::1")) != cle_ip(req("2001:db8:1:2::1"))
    assert cle_ip(req("203.0.113.9")) == "203.0.113.9"


def test_second_audit_8_le_limiteur_oublie_les_adresses_anciennes(monkeypatch):
    from types import SimpleNamespace

    from api.main import LimiteRequetes
    horloge = [1000.0]
    monkeypatch.setattr("api.main.time.monotonic", lambda: horloge[0])
    lim = LimiteRequetes(10)
    for i in range(500):
        lim(SimpleNamespace(cookies={}, client=SimpleNamespace(host=f"10.0.{i // 250}.{i % 250}")))
    assert len(lim._hits) == 500
    horloge[0] += 120
    lim(SimpleNamespace(cookies={}, client=SimpleNamespace(host="10.9.9.9")))
    assert len(lim._hits) == 1


def test_second_audit_9_ancienne_empreinte_meme_cout_qu_une_adresse_inconnue(tmp_path, monkeypatch):
    import hashlib
    import secrets

    import api.comptes as mod
    comptes = Comptes(tmp_path / "c.db")
    u = comptes.creer("etu@exemple.fr", MDP)
    sel = secrets.token_bytes(16)
    ancienne = hashlib.scrypt(MDP.encode(), salt=sel, n=2**14, r=8, p=1, dklen=32)
    with sqlite3.connect(tmp_path / "c.db") as c:
        c.execute("UPDATE utilisateurs SET mdp = ? WHERE id = ?", (f"scrypt${2**14}$8$1${sel.hex()}${ancienne.hex()}", u.id))
    verifies = []
    original = mod.verifier_mdp
    monkeypatch.setattr(mod, "verifier_mdp", lambda m, s: verifies.append(s.split("$")[3]) or original(m, s))
    assert comptes.authentifier("etu@exemple.fr", "faux-mot-de-passe") is None
    assert str(SCRYPT_P) in verifies                     # l'empreinte factice au cout actuel est aussi calculee


def test_second_audit_14_avis_exige_une_adresse_confirmee(tmp_path, monkeypatch):
    from api import courriel
    from api.config import Settings
    from api.main import create_app
    from tests.test_comptes import LLM, Retriever
    monkeypatch.setenv("RESEND_API_KEY", "cle-de-test")
    monkeypatch.setattr(courriel, "envoyer_verification", lambda dest, lien: None)
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0),
                     retriever=Retriever(), llm=LLM(), comptes=Comptes(tmp_path / "c.db"))
    client = TestClient(app)
    inscrire(client)
    r = client.post("/feedback", json={"reponse_id": "12345678-aaaa", "utile": False})
    assert r.status_code == 403


def test_second_audit_16_nom_de_fichier_refuse_dans_l_adresse(env):  # noqa: F811
    client, _, _ = env
    inscrire(client)
    r = client.post("/cours", params={"matiere": "droit_civil", "fichier": "Dupont.txt", "titre": "t"},
                    content=b"Le dol est une manoeuvre.", headers={"Content-Type": "application/octet-stream"})
    assert r.status_code == 422 and "rechargez" in r.json()["detail"]


def test_audit_19_11_sec3_le_lecteur_de_fichiers_n_herite_d_aucune_cle(monkeypatch):
    import subprocess
    from api import extraction
    vus = {}

    def faux_run(cmd, **kw):
        vus.update(kw)
        return subprocess.CompletedProcess(cmd, 0, stdout=b'{"pages": [[null, "texte"]]}', stderr=b"")

    monkeypatch.setenv("GEMINI_API_KEY", "secret")
    monkeypatch.setattr(extraction.subprocess, "run", faux_run)
    extraction.extraire_isole("c.txt", b"texte")
    assert vus["env"] is not None and not any("KEY" in k or "SECRET" in k for k in vus["env"])


def test_audit_19_11_sec4_cookie_secure_pour_le_site_public_meme_vu_en_http(tmp_path):
    from api.config import Settings
    from api.main import create_app
    from tests.test_comptes import LLM, Retriever
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0,
                              url_publique="https://lexia.test"),
                     retriever=Retriever(), llm=LLM(), comptes=Comptes(tmp_path / "c.db"))
    r = inscrire(TestClient(app, base_url="http://lexia.test"))
    assert r.status_code == 201 and "secure" in r.headers["set-cookie"].lower()
    r = inscrire(TestClient(app), email="autre@exemple.fr")             # autre hote (tests, adresse IP) : inchange
    assert r.status_code == 201 and "secure" not in r.headers["set-cookie"].lower()


def test_audit_19_11_sec5_et_sec9_api_sans_cache_et_origine_controlee(env):  # noqa: F811
    client, _, _ = env
    inscrire(client)
    assert client.get("/auth/moi").headers["cache-control"] == "no-store"
    question = {"question": "article 1240"}
    assert client.post("/chat", json=question, headers={"Origin": "https://pirate.example"}).status_code == 403
    assert client.post("/quiz", json={"theme": "le dol"}, headers={"Origin": "https://pirate.example"}).status_code == 403
    assert client.post("/chat", json=question, headers={"Origin": "http://testserver"}).status_code == 200


def test_audit_19_11_srv6_une_salle_de_td_derriere_une_seule_adresse():
    """SRV-6 : par IP seulement, toute une salle partageait 10 questions par minute."""
    from types import SimpleNamespace

    from api.main import LimiteRequetes
    lim = LimiteRequetes(2)
    salle = lambda cookie: SimpleNamespace(cookies={"lexia_session": cookie} if cookie else {},  # noqa: E731
                                           client=SimpleNamespace(host="192.0.2.10"))
    for etudiant in ("jeton-a", "jeton-b", "jeton-c"):
        lim(salle(etudiant))
        lim(salle(etudiant))
    with pytest.raises(HTTPException):
        lim(salle("jeton-a"))
    lim(salle(None))
    lim(salle(None))
    with pytest.raises(HTTPException):
        lim(salle(None))
    assert not any("jeton" in k for k in lim._hits)          # empreinte seulement, jamais le cookie
