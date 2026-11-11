"""Tests de l'API avec un index construit a partir des fixtures et un modele simule."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.config import Settings
from api.llm.base import LLMError
from api.main import create_app
from api.references import extraire, references_non_couvertes
from api.retrieval.local import LocalRetriever
from ingest.build_index import build
from ingest.sources import cass, constit, legi

FIX = Path(__file__).parent / "fixtures"
CONSTITUTION = Path(__file__).parent.parent / "data" / "passages" / "constitution_1958.jsonl"


class FakeLLM:
    """Renvoie des reponses preparees ; garde les prompts recus."""

    def __init__(self):
        self.reponses: list = []
        self.prompts: list[str] = []

    def generate_json(self, *, system, prompt, schema, temperature=0.2):
        self.prompts.append(prompt)
        r = self.reponses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r, "fake-model"

    def embed_query(self, text):
        return None


@pytest.fixture(scope="module")
def index_dir(tmp_path_factory):
    base = tmp_path_factory.mktemp("lexia")
    passages = base / "passages"
    passages.mkdir()
    rows = []
    rows += [p.to_dict() for p in constit.parse_decision((FIX / "constit_2023-1075_QPC.xml").read_bytes(),
                                                          date_recuperation="d", version="v")]
    rows += [p.to_dict() for p in cass.parse_arret((FIX / "cass_moderne.xml").read_bytes(),
                                                    date_recuperation="d", version="v")]
    for f in ("LEGIARTI000032041571.xml", "LEGIARTI000006438819.xml"):
        rows.append(legi.parse_article((FIX / f).read_bytes(), date_recuperation="d", version_archive="a").to_dict())
    (passages / "fixtures.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows))
    (passages / "constitution_1958.jsonl").write_text(CONSTITUTION.read_text(encoding="utf-8"))
    build(passages_dir=passages, index_dir=base / "index", cache_dir=base / "vide")
    return base / "index"


@pytest.fixture
def env(index_dir, tmp_path):
    llm = FakeLLM()
    settings = Settings(gemini_models=("fake",), index_dir=index_dir, logs_dir=tmp_path / "logs",
                        rate_limit_per_minute=100, max_question_chars=500)
    app = create_app(settings, retriever=LocalRetriever(index_dir), llm=llm)
    return TestClient(app), llm, tmp_path / "logs"


# --- Recherche ---------------------------------------------------------------

def test_recherche_reference_article(index_dir):
    r = LocalRetriever(index_dir)
    hits = r.search("Que dit l'article 1240 du code civil ?", sources=None, k=5)
    assert hits[0].passage["id"] == "code_civil:LEGIARTI000032041571"
    assert "reference" in hits[0].via
    # l'ancienne version (1382 avant 2016) n'est pas proposee par defaut
    assert all(h.passage["meta"].get("en_vigueur") is not False for h in hits)


def test_recherche_textes_avant_jurisprudence(index_dir):
    r = LocalRetriever(index_dir)
    hits = r.search("dommage causé à autrui et responsabilité", sources=None, k=4)
    assert hits[0].passage["source_id"] in ("code_civil", "constitution_1958")


# --- Chat ----------------------------------------------------------------------

def test_chat_valide_et_filtre_les_citations(env):
    client, llm, logs = env

    def reponse_modele():
        s1 = "S1"  # l'article 1240, cite dans la question, est toujours le premier extrait
        return {
            "statut": "reponse", "titre": "Responsabilité pour faute",
            "droit_positif": [
                {"texte": "Tout fait de l'homme qui cause un dommage oblige son auteur fautif à le réparer.",
                 "sources": [s1, "S99"]},
                {"texte": "Règle sans source.", "sources": []},
                {"texte": "Selon l'article 9999 du code civil, tout est permis.", "sources": [s1]},
            ],
            "explication": [{"texte": "Il faut une faute, un dommage et un lien de causalité.", "sources": [s1]}],
            "points_incertains": [],
            "message": "",
        }

    llm.reponses.append(reponse_modele())
    r = client.post("/chat", json={"question": "Que dit l'article 1240 du code civil ?", "mode": "expliquer"})
    assert r.status_code == 200
    data = r.json()
    assert data["statut"] == "reponse"
    assert len(data["droit_positif"]) == 1
    assert data["controle"]["citations_retirees"] == 1          # S99 inconnu
    assert data["controle"]["elements_retires"] == 2            # sans source + article inventé
    assert "article 9999" in data["controle"]["references_non_verifiees"]
    assert data["sources"][0]["id"] == "code_civil:LEGIARTI000032041571"
    assert data["sources"][0]["label"] == "S1"
    assert data["avertissement"]
    # la question n'apparait pas dans les journaux
    journal = (logs / "requetes.jsonl").read_text()
    assert "1240 du code civil ?" not in journal and data["reponse_id"] in journal


def test_chat_sans_affirmation_sourcee_devient_abstention(env):
    client, llm, _ = env
    llm.reponses.append({"statut": "reponse", "titre": "t", "droit_positif": [{"texte": "x", "sources": []}],
                         "explication": [{"texte": "y", "sources": []}], "points_incertains": [], "message": ""})
    data = client.post("/chat", json={"question": "responsabilité du fait d'autrui"}).json()
    assert data["statut"] == "abstention" and data["message"] and data["sources"] == []


def test_chat_hors_champ(env):
    client, llm, _ = env
    llm.reponses.append({"statut": "hors_champ", "titre": "", "droit_positif": [], "explication": [],
                         "points_incertains": [], "message": ""})
    data = client.post("/chat", json={"question": "Mon voisin a abîmé ma voiture, que dois-je faire ?"}).json()
    assert data["statut"] == "hors_champ" and "professionnel" in data["message"]


def test_chat_sans_resultat_ne_sollicite_pas_le_modele(env):
    client, llm, _ = env
    data = client.post("/chat", json={"question": "zzqqwx yyvvkk"}).json()
    assert data["statut"] == "abstention" and llm.prompts == []


def test_chat_modele_indisponible(env):
    client, llm, _ = env
    llm.reponses.append(LLMError("503"))
    r = client.post("/chat", json={"question": "article 1240"})
    assert r.status_code == 503 and "indisponible" in r.json()["detail"]


def test_chat_entrees_invalides(env):
    client, _, _ = env
    assert client.post("/chat", json={"question": "x" * 501}).status_code == 413
    assert client.post("/chat", json={"question": "article 1240", "mode": "inconnu"}).status_code == 422
    assert client.post("/chat", json={"question": "article 1240", "matiere": "droit_fiscal"}).status_code == 422


def test_limite_de_requetes(index_dir, tmp_path):
    llm = FakeLLM()
    settings = Settings(gemini_models=("fake",), index_dir=index_dir, logs_dir=tmp_path, rate_limit_per_minute=2)
    client = TestClient(create_app(settings, retriever=LocalRetriever(index_dir), llm=llm))
    codes = [client.post("/chat", json={"question": "zzqqwx"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


# --- Quiz ----------------------------------------------------------------------

def test_quiz_qcm_generation_et_correction(env):
    client, llm, _ = env
    llm.reponses.append({"questions": [
        {"question": "Que faut-il pour engager la responsabilité pour faute ?",
         "choix": ["Une faute", "Un contrat", "Un notaire", "Un jugement"], "bonne_reponse": 0,
         "explication": "L'article 1240 exige une faute.", "sources": ["S1"]},
        {"question": "Question sans source", "choix": ["a", "b", "c", "d"], "bonne_reponse": 1,
         "explication": "", "sources": []},
        {"question": "Indice invalide", "choix": ["a", "b", "c", "d"], "bonne_reponse": 7,
         "explication": "", "sources": ["S1"]},
    ]})
    r = client.post("/quiz", json={"theme": "article 1240 responsabilité", "format": "qcm", "nombre": 3})
    data = r.json()
    assert r.status_code == 200 and data["obtenu"] == 1 and data["demande"] == 3
    assert "bonne_reponse" not in data["questions"][0]           # la reponse n'est pas envoyee
    assert data["controle"]["elements_retires"] == 2

    c = client.post("/quiz/correct", json={"quiz_id": data["quiz_id"], "reponses": [{"index": 0, "valeur": 0}]}).json()
    assert c["score"] == 1 and c["resultats"][0]["statut"] == "correct"
    assert c["resultats"][0]["sources"] == ["code_civil:LEGIARTI000032041571"]

    assert client.post("/quiz/correct", json={"quiz_id": "inconnu", "reponses": []}).status_code == 404


def test_quiz_vrai_faux_non_repondu(env):
    client, llm, _ = env
    llm.reponses.append({"questions": [
        {"affirmation": "La faute est une condition de l'article 1240.", "reponse": True,
         "explication": "Oui.", "sources": ["S1"]}]})
    data = client.post("/quiz", json={"theme": "article 1240", "format": "vrai_faux", "nombre": 1}).json()
    c = client.post("/quiz/correct", json={"quiz_id": data["quiz_id"], "reponses": []}).json()
    assert c["resultats"][0]["statut"] == "non_repondu" and c["score"] == 0


def test_quiz_ouvertes_correction_par_le_modele(env):
    client, llm, _ = env
    llm.reponses.append({"questions": [
        {"question": "Quelles sont les conditions de la responsabilité pour faute ?",
         "elements_attendus": ["une faute", "un dommage", "un lien de causalité"],
         "explication": "Article 1240.", "sources": ["S1"]}]})
    data = client.post("/quiz", json={"theme": "article 1240", "format": "ouvertes", "nombre": 1}).json()
    llm.reponses.append({"corrections": [{"index": 0, "evaluation": "partiel",
                                          "commentaire": "Il manque le lien de causalité.",
                                          "elements_manquants": ["un lien de causalité"]}]})
    c = client.post("/quiz/correct", json={"quiz_id": data["quiz_id"],
                                           "reponses": [{"index": 0, "valeur": "Une faute et un dommage."}]}).json()
    assert c["resultats"][0]["statut"] == "partiel" and c["score"] == 0.5
    assert "<reponse_etudiant>" in llm.prompts[-1]


# --- Sources, vigueur, retours -----------------------------------------------

def test_source_et_vigueur(env):
    client, _, _ = env
    s = client.get("/sources/code_civil:LEGIARTI000032041571").json()
    assert s["numero"] == "1240" and s["texte"].startswith("Tout fait")
    v = client.get("/sources/code_civil:LEGIARTI000006438819/vigueur").json()
    assert v["applicable"] and v["en_vigueur"] is False and "Légifrance" in v["message"]
    v = client.get("/sources/code_civil:LEGIARTI000032041571/vigueur").json()
    assert v["en_vigueur"] is True
    j = client.get("/sources/decisions_conseil_constitutionnel:CONSTEXT000049184152:1/vigueur").json()
    assert j["applicable"] is False
    assert client.get("/sources/inconnu:1").status_code == 404


def test_feedback_et_sante(env):
    client, _, logs = env
    assert client.post("/feedback", json={"reponse_id": "12345678-aaaa", "utile": False,
                                          "motif": "source_incorrecte"}).status_code == 204
    assert "source_incorrecte" in (logs / "feedback.jsonl").read_text()
    assert client.post("/feedback", json={"reponse_id": "12345678", "utile": True, "commentaire": "x"}).status_code == 204
    sante = client.get("/sante").json()
    assert sante["statut"] == "ok" and sante["passages"] > 100
    assert {m["id"] for m in client.get("/matieres").json()} >= {"droit_civil", "droit_constitutionnel"}


# --- References ------------------------------------------------------------------

def test_references_verification():
    p = [{"numero": "1240", "texte": "", "entete": "Code civil, article 1240"},
         {"numero": None, "texte": "voir l'article L. 2223-18-1-1", "entete": "",
          "meta": {"numero": "2023-1075", "nature": "QPC"}}]
    assert references_non_couvertes("articles 1240 et L. 2223-18-1-1 ; décision 2023-1075 QPC", p) == []
    assert references_non_couvertes("article 1241 ; 2020-1 QPC ; pourvoi 21-86.418", p) == [
        "article 1241", "2020-1 QPC", "pourvoi 21-86.418"]
    assert extraire("l'article premier de la Constitution").articles == ("1",)
