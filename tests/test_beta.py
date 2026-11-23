"""Beta fermee (D121) : code d'acces a l'inscription, questionnaire de retour, suivi d'usage anonyme."""

import json
import threading

import pytest
from fastapi.testclient import TestClient

from api import beta
from api.comptes import Comptes
from api.config import Settings
from api.main import create_app
from tests.test_admin import MDP, client_connecte
from tests.test_comptes import LLM, Retriever


def creer_app(tmp_path, beta_fermee=True):
    comptes = Comptes(tmp_path / "c.db", admins=("chef@exemple.fr",))
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0,
                              url_publique="https://lexia.test", beta_fermee=beta_fermee),
                     retriever=Retriever(), llm=LLM(), comptes=comptes)
    return app, comptes


@pytest.fixture
def env(tmp_path):
    return creer_app(tmp_path)


def inscrire(app, email, code=None):
    corps = {"email": email, "mot_de_passe": MDP, "accepte_cgu": True, "prenom": "Léa", "nom": "Martin"}
    if code is not None:
        corps["code_beta"] = code
    c = TestClient(app)
    return c, c.post("/auth/inscription", json=corps)


def nouveau_code(chef, plafond=2, libelle="L1 groupe 3"):
    r = chef.post("/admin/beta/codes", json={"libelle": libelle, "plafond": plafond})
    assert r.status_code == 201
    return r.json()


# --- code d'acces ----------------------------------------------------------------------

def test_inscription_refusee_sans_code_ou_avec_un_code_faux(env):
    """Echoue sans le controle du code : en beta fermee, aucun compte ne se cree sans code valable."""
    app, comptes = env
    chef = client_connecte(app, "chef@exemple.fr")
    code = nouveau_code(chef)["code"]
    for valeur in (None, "", "ABCDE-FGHJK", code[:-1] + ("A" if code[-1] != "A" else "B")):
        _, r = inscrire(app, "etu@exemple.fr", valeur)
        assert r.status_code == 403, valeur
    assert comptes.par_email("etu@exemple.fr") is None
    # Le code tel qu'affiche, ou saisi en minuscules et sans tiret, ouvre l'inscription
    _, r = inscrire(app, "etu@exemple.fr", code.lower().replace("-", " "))
    assert r.status_code == 201 and r.json()["beta"] is True


def test_plafond_du_code_respecte(env):
    """Echoue sans le plafond : un code a 2 places ouvre 2 comptes, pas 3."""
    app, comptes = env
    chef = client_connecte(app, "chef@exemple.fr")
    code = nouveau_code(chef, plafond=2)["code"]
    assert inscrire(app, "a@exemple.fr", code)[1].status_code == 201
    assert inscrire(app, "b@exemple.fr", code)[1].status_code == 201
    _, r = inscrire(app, "c@exemple.fr", code)
    assert r.status_code == 403 and r.json()["detail"] == beta.MESSAGE_CODE_EPUISE
    assert comptes.par_email("c@exemple.fr") is None
    (c,) = chef.get("/admin/beta/codes").json()
    assert (c["inscriptions"], c["plafond"], c["comptes"]) == (2, 2, 2)


def test_plafond_tenu_avec_des_inscriptions_simultanees(tmp_path):
    """Deux processus (deux connexions SQLite a la meme base) inscrivent en meme temps avec un code a une
    place : un seul compte est cree. La place est prise dans la transaction de l'INSERT du compte."""
    chemin = tmp_path / "c.db"
    premier = Comptes(chemin)
    with premier._lock, premier._con:
        premier._con.execute("INSERT INTO codes_beta (empreinte, libelle, plafond, cree_le) VALUES (?, ?, 1, ?)",
                             (beta.empreinte_code("ABCDE-FGHJK"), "essai", "2026-11-23"))
    instances = [premier, Comptes(chemin)]
    depart = threading.Barrier(len(instances) * 4)
    resultats = []

    def inscription(comptes, i):
        depart.wait()
        try:
            comptes.creer(f"etu{i}@exemple.fr", MDP, exiger_code=True, code_beta="ABCDE-FGHJK")
            resultats.append("cree")
        except beta.CodeRefuse:
            resultats.append("refuse")

    fils = [threading.Thread(target=inscription, args=(instances[i % 2], i)) for i in range(8)]
    for f in fils:
        f.start()
    for f in fils:
        f.join()
    assert sorted(resultats) == ["cree"] + ["refuse"] * 7
    assert premier._q("SELECT inscriptions FROM codes_beta")[0][0] == 1
    assert premier._q("SELECT COUNT(*) FROM utilisateurs")[0][0] == 1


def test_compte_refuse_ne_consomme_pas_de_place_et_code_desactive(env):
    app, _ = env
    chef = client_connecte(app, "chef@exemple.fr")
    cree = nouveau_code(chef, plafond=1)
    # Adresse deja prise : refus du compte, la place reste libre
    assert inscrire(app, "a@exemple.fr", cree["code"])[1].status_code == 201
    chef.post(f"/admin/beta/codes/{cree['id']}/desactiver")
    autre = nouveau_code(chef, plafond=5)
    assert inscrire(app, "a@exemple.fr", autre["code"])[1].status_code == 422
    assert chef.get("/admin/beta/codes").json()[0]["inscriptions"] == 0
    # Code desactive : refuse meme avec des places
    r = chef.post(f"/admin/beta/codes/{autre['id']}/desactiver")
    assert r.status_code == 200 and r.json()["actif"] is False
    assert inscrire(app, "b@exemple.fr", autre["code"])[1].status_code == 403


def test_code_jamais_stocke_en_clair_et_affiche_une_seule_fois(env):
    app, comptes = env
    chef = client_connecte(app, "chef@exemple.fr")
    cree = nouveau_code(chef)
    assert len(beta.normaliser_code(cree["code"])) == beta.LONGUEUR_CODE
    assert "code" not in chef.get("/admin/beta/codes").json()[0]
    contenu = comptes._q("SELECT * FROM codes_beta")
    assert all(cree["code"] not in str(v) and beta.normaliser_code(cree["code"]) not in str(v)
               for ligne in contenu for v in ligne)


def test_routes_beta_reservees_aux_administrateurs(env):
    app, _ = env
    chef = client_connecte(app, "chef@exemple.fr")
    code = nouveau_code(chef)["code"]
    etu, _ = inscrire(app, "etu@exemple.fr", code)
    for route in ("/admin/beta/codes", "/admin/beta/avis", "/admin/beta/avis.csv", "/admin/beta/usage"):
        assert etu.get(route).status_code == 403
        assert TestClient(app).get(route).status_code == 401
    assert etu.post("/admin/beta/codes", json={"libelle": "pirate", "plafond": 500}).status_code == 403


def test_hors_beta_inscription_inchangee(tmp_path):
    """BETA_FERMEE absent (par defaut) : inscription sans code, comme avant ; compte non marque beta."""
    app, _ = creer_app(tmp_path, beta_fermee=False)
    assert TestClient(app).get("/config").json()["beta_fermee"] is False
    _, r = inscrire(app, "etu@exemple.fr")
    assert r.status_code == 201 and r.json()["beta"] is False


def test_comparaison_en_temps_constant(monkeypatch):
    """Toutes les empreintes sont comparees avec hmac.compare_digest, sans arret a la premiere egale."""
    import sqlite3
    con = sqlite3.connect(":memory:")
    beta.creer_tables(con)
    for i, code in enumerate(("AAAAA-AAAAA", "BBBBB-BBBBB", "CCCCC-CCCCC")):
        con.execute("INSERT INTO codes_beta (empreinte, libelle, plafond, cree_le) VALUES (?, ?, 5, '')",
                    (beta.empreinte_code(code), str(i)))
    appels = []
    vrai = beta.hmac.compare_digest
    monkeypatch.setattr(beta.hmac, "compare_digest", lambda a, b: appels.append(1) or vrai(a, b))
    assert beta.prendre_place(con, "aaaaaaaaaa") == 1
    assert len(appels) == 3


# --- questionnaire de retour --------------------------------------------------------------

def test_avis_des_comptes_beta_lus_et_exportes(env):
    app, comptes = env
    chef = client_connecte(app, "chef@exemple.fr")
    code = nouveau_code(chef)["code"]
    etu, _ = inscrire(app, "etu@exemple.fr", code)
    r = etu.post("/beta/avis", json={"note": 4, "aide": "Les fiches", "manque": "=HYPERLIEN(\"x\")",
                                     "erreur": "Article 1240 mal cite", "lien": "https://www.legifrance.gouv.fr/x"})
    assert r.status_code == 201
    assert etu.post("/beta/avis", json={"note": 6}).status_code == 422
    assert etu.post("/beta/avis", json={"note": 3, "lien": "javascript:alert(1)"}).status_code == 422
    lu = chef.get("/admin/beta/avis").json()
    assert lu["note_moyenne"] == 4 and lu["avis"][0]["aide"] == "Les fiches"
    # Aucun lien avec le compte : ni adresse, ni numero, ni heure
    (ligne,) = comptes._q("SELECT * FROM avis_beta")
    assert "etu@exemple.fr" not in str(ligne) and len(ligne[1]) == 10
    csv = chef.get("/admin/beta/avis.csv")
    assert csv.status_code == 200 and csv.headers["content-type"].startswith("text/csv")
    assert "attachment" in csv.headers["content-disposition"]
    assert "'=HYPERLIEN" in csv.text and "Article 1240 mal cite" in csv.text   # pas de formule executee


def test_avis_refuse_hors_beta_et_plafonne(tmp_path):
    app, _ = creer_app(tmp_path, beta_fermee=False)
    etu, _ = inscrire(app, "etu@exemple.fr")
    assert etu.post("/beta/avis", json={"note": 4}).status_code == 403
    assert TestClient(app).post("/beta/avis", json={"note": 4}).status_code == 401
    app, _ = creer_app(tmp_path / "b")
    chef = client_connecte(app, "chef@exemple.fr")
    etu, _ = inscrire(app, "etu@exemple.fr", nouveau_code(chef)["code"])
    codes = [etu.post("/beta/avis", json={"note": 5}).status_code for _ in range(beta.AVIS_PAR_COMPTE_JOUR + 1)]
    assert codes == [201] * beta.AVIS_PAR_COMPTE_JOUR + [429]


# --- suivi d'usage ---------------------------------------------------------------------------

def test_suivi_d_usage_anonyme(env, tmp_path):
    app, _ = env
    chef = client_connecte(app, "chef@exemple.fr")
    etu, _ = inscrire(app, "etu@exemple.fr", nouveau_code(chef)["code"])
    assert etu.post("/chat", json={"question": "article 1240 (1)"}).status_code == 200
    assert etu.post("/chat", json={"question": "article 1240 (2)", "mode": "cas_pratique"}).status_code == 200
    assert etu.post("/chat", json={"question": "article 1240 (3)", "mode": "fiche"}).status_code == 200
    assert etu.post("/chat", json={"question": "x"}).status_code == 422
    chef.post("/chat", json={"question": "article 1240 (4)"})   # essai de l'editeur : pas compte
    lignes = [json.loads(l) for l in (tmp_path / "logs" / "usage.jsonl").read_text().splitlines()]
    assert [l["fonction"] for l in lignes] == ["question", "cas_pratique", "fiche", "question"]
    assert all(set(l) == {"ts", "fonction", "code", "duree_ms"} for l in lignes)   # ni texte, ni compte
    u = chef.get("/admin/beta/usage").json()
    assert u["par_jour"][-1]["questions"] == 3 and u["par_jour"][-1]["total"] == 4 and len(u["par_jour"]) == 14
    f = {x["fonction"]: x for x in u["fonctions"]}
    assert f["question"]["appels"] == 2 and f["question"]["refus"] == 1 and f["cas_pratique"]["appels"] == 1
    assert u["taux_erreur"] == 0
    totale = next(e for e in u["etapes"] if e["etape"] == "totale")
    assert totale["mesures"] >= 3 and totale["mediane_ms"] is not None
    assert "etu@exemple.fr" not in json.dumps(u)


def test_erreurs_du_modele_comptees_dans_le_taux(tmp_path):
    from api.llm.base import LLMError

    class Panne(LLM):
        def generate_json(self, *a, **k):
            raise LLMError("indisponible")

    comptes = Comptes(tmp_path / "c.db", admins=("chef@exemple.fr",))
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0,
                              url_publique="https://lexia.test", beta_fermee=True),
                     retriever=Retriever(), llm=Panne(), comptes=comptes)
    chef = client_connecte(app, "chef@exemple.fr")
    etu, _ = inscrire(app, "etu@exemple.fr", nouveau_code(chef)["code"])
    assert etu.post("/chat", json={"question": "article 1240"}).status_code == 503
    u = chef.get("/admin/beta/usage").json()
    assert u["taux_erreur"] == 1 and next(x for x in u["fonctions"] if x["fonction"] == "question")["erreurs"] == 1


def test_centiles():
    assert beta.centile([], 0.5) is None
    assert beta.centile([5], 0.9) == 5
    v = list(range(1, 11))
    assert beta.centile(v, 0.5) == 5 and beta.centile(v, 0.9) == 9


def test_code_personnalise_accepte_une_fois_et_valable_a_l_inscription(env):
    app, _ = env
    chef = client_connecte(app, "chef@exemple.fr")
    r = chef.post("/admin/beta/codes", json={"libelle": "Assas L1", "plafond": 3, "code": " assas-l1-2026 "})
    assert r.status_code == 201 and r.json()["code"] == "ASSAS-L1-2026"
    assert "code" not in chef.get("/admin/beta/codes").json()[0]
    # Meme code, ecrit autrement : refuse (empreinte du code normalise)
    r = chef.post("/admin/beta/codes", json={"libelle": "Doublon", "plafond": 3, "code": "ASSASL12026"})
    assert r.status_code == 409 and "existe déjà" in r.json()["detail"]
    _, r = inscrire(app, "lea@exemple.fr", code="Assas-L1-2026")
    assert r.status_code in (200, 201)
    assert chef.get("/admin/beta/codes").json()[0]["inscriptions"] == 1


@pytest.mark.parametrize("code", ["COURT-1", "ÉTÉ-2026-LEXIA", "A" * 31, "assas_2026!"])
def test_code_personnalise_trop_court_long_ou_ambigu_refuse(env, code):
    app, comptes = env
    chef = client_connecte(app, "chef@exemple.fr")
    r = chef.post("/admin/beta/codes", json={"libelle": "Groupe", "plafond": 3, "code": code})
    assert r.status_code == 409
    assert comptes._q("SELECT COUNT(*) FROM codes_beta") == [(0,)]


def test_code_vide_tire_au_hasard(env):
    app, _ = env
    chef = client_connecte(app, "chef@exemple.fr")
    r = chef.post("/admin/beta/codes", json={"libelle": "Groupe", "plafond": 3, "code": "  "})
    assert r.status_code == 201 and len(beta.normaliser_code(r.json()["code"])) == beta.LONGUEUR_CODE
