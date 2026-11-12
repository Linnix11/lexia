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
from ingest.embed import encode
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
    build(passages_dir=passages, index_dir=base / "index", cache_dir=base / "vide", model="aucun")
    return base / "index"


@pytest.fixture(scope="module")
def index_vectorise(tmp_path_factory, index_dir):
    """Meme corpus, avec un vecteur factice par passage : l'article 1240 pointe dans la direction (1, 0, 0)."""
    base = tmp_path_factory.mktemp("lexia_vec")
    passages = index_dir.parent / "passages"
    cache = base / "cache"
    cache.mkdir()
    lignes = []
    for f in passages.glob("*.jsonl"):
        for l in f.read_text(encoding="utf-8").splitlines():
            p = json.loads(l)
            vec = [1.0, 0.0, 0.0] if p["numero"] == "1240" else [0.0, 1.0, 0.0]
            lignes.append(json.dumps({"id": p["id"], "empreinte": p["empreinte"], "model": "fake-embed",
                                      "dim": 3, "b64": encode(vec)}))
    (cache / "tout.jsonl").write_text("\n".join(lignes))
    build(passages_dir=passages, index_dir=base / "index", cache_dir=cache, model="fake-embed")
    return base / "index"


class FakeEmbedder:
    model, dim = "fake-embed", 3

    def __init__(self):
        self.appels = 0

    def embed_query(self, texte):
        self.appels += 1
        return [1.0, 0.0, 0.0]


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


def test_recherche_hybride(index_vectorise, tmp_path):
    llm, emb = FakeLLM(), FakeEmbedder()
    settings = Settings(gemini_models=("fake",), index_dir=index_vectorise, logs_dir=tmp_path)
    client = TestClient(create_app(settings, retriever=LocalRetriever(index_vectorise, embed_model="fake-embed"),
                                   llm=llm, embedder=emb))
    llm.reponses.append({"statut": "abstention", "titre": "", "droit_positif": [], "explication": [],
                         "points_incertains": [], "message": ""})
    data = client.post("/chat", json={"question": "dommage causé par une faute"}).json()
    assert emb.appels == 1 and data["controle"]["recherche"] == "hybride"
    assert "Code civil, article 1240" in llm.prompts[-1]


def test_vecteurs_d_un_autre_modele_ignores(index_vectorise):
    r = LocalRetriever(index_vectorise, embed_model="autre-modele")
    assert r.stats()["embeddings"] == 0 and r.couverture(None) == 0


def test_sans_couverture_pas_d_appel_au_modele_d_embeddings(index_dir, tmp_path):
    llm, emb = FakeLLM(), FakeEmbedder()
    settings = Settings(gemini_models=("fake",), index_dir=index_dir, logs_dir=tmp_path)
    client = TestClient(create_app(settings, retriever=LocalRetriever(index_dir), llm=llm, embedder=emb))
    client.post("/chat", json={"question": "zzqqwx"})
    assert emb.appels == 0


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

    # Une nouvelle correction du meme questionnaire ne rappelle pas le modele (appel payant).
    appels = len(llm.prompts)
    c2 = client.post("/quiz/correct", json={"quiz_id": data["quiz_id"],
                                            "reponses": [{"index": 0, "valeur": "Autre réponse."}]}).json()
    assert len(llm.prompts) == appels and c2 == c


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


# --- Reformulation et reclassement ------------------------------------------------

from api.expansion import Expanseur  # noqa: E402
from api.retrieval.base import Complement, Hit, construire_groupe  # noqa: E402


class ExpanseurFixe:
    def __init__(self, complement):
        self.complement = complement

    def etendre(self, question):
        return self.complement


class ReclasseurInverse:
    model = "inverse"

    def __init__(self):
        self.appels = 0

    def reordonner(self, question, hits):
        self.appels += 1
        return [Hit(h.passage, -i, h.via | {"reclasse"}) for i, h in enumerate(reversed(hits))]


def test_expanseur_filtre_les_suggestions():
    llm = FakeLLM()
    llm.reponses.append({"articles": [
        {"code": "code_civil", "numero": "1240"},
        {"code": "code_civil", "numero": "1240"},            # doublon
        {"code": "constitution", "numero": "61-1"},
        {"code": "code_penal", "numero": "121-3"},
        {"code": "code_minier", "numero": "1"},              # code hors corpus
        {"code": "code_civil", "numero": "art. 1241 ; DROP"},  # numero invalide
    ], "reformulation": "Responsabilité civile extracontractuelle pour faute"})
    c = Expanseur(llm).etendre("conditions de la responsabilité pour faute")
    assert c.suggestions == [("code_civil", "1240"), ("constitution_1958", "61-1"), ("code_penal", "121-3")]
    assert c.reformulation.startswith("Responsabilité")
    llm.reponses.append(LLMError("503"))
    assert Expanseur(llm).etendre("question") is None


def test_suggestion_ajoute_le_texte_officiel_de_l_article(index_dir, tmp_path):
    llm = FakeLLM()
    exp = ExpanseurFixe(Complement(reformulation="", suggestions=[("code_civil", "1240"), ("code_civil", "99999")]))
    settings = Settings(gemini_models=("fake",), index_dir=index_dir, logs_dir=tmp_path)
    client = TestClient(create_app(settings, retriever=LocalRetriever(index_dir), llm=llm, expanseur=exp))
    llm.reponses.append({"statut": "abstention", "titre": "", "droit_positif": [], "explication": [],
                         "points_incertains": [], "message": ""})
    data = client.post("/chat", json={"question": "quel est le principe en matière de faute civile ?"}).json()
    assert "Code civil, article 1240" in llm.prompts[-1]  # retrouve grace a la suggestion
    assert data["controle"]["reformulation"] is True and data["controle"]["suggestions_retenues"] == 1


def test_reformulation_en_echec_ne_bloque_pas(index_dir, tmp_path):
    llm = FakeLLM()
    settings = Settings(gemini_models=("fake",), index_dir=index_dir, logs_dir=tmp_path)
    client = TestClient(create_app(settings, retriever=LocalRetriever(index_dir), llm=llm, expanseur=ExpanseurFixe(None)))
    llm.reponses.append({"statut": "abstention", "titre": "", "droit_positif": [], "explication": [],
                         "points_incertains": [], "message": ""})
    r = client.post("/chat", json={"question": "article 1240"})
    assert r.status_code == 200 and r.json()["controle"]["reformulation"] is False


def test_construire_groupe_reclasse_puis_place_les_suggestions():
    p = lambda i: {"id": f"p{i}", "texte": "", "meta": {}}  # noqa: E731
    rec = ReclasseurInverse()
    hits = construire_groupe({"lexical": [(f"p{i}", p(i)) for i in range(3)]}, 10,
                             question="q", reclasseur=rec, suggestions=[p(9)])
    assert [h.passage["id"] for h in hits] == ["p9", "p2", "p1", "p0"]
    assert rec.appels == 1 and "suggestion" in hits[0].via and "reclasse" in hits[1].via


def test_mode_methode_accepte_une_explication_sans_source():
    from api.citations import valider_reponse
    table = {"S1": {"id": "code_civil:x", "numero": "1103", "texte": "", "entete": ""}}
    brut = {"statut": "reponse", "titre": "Méthode", "droit_positif": [],
            "explication": [{"texte": "1. Lire l'arrêt. 2. Dégager le problème de droit.", "sources": []}],
            "points_incertains": [], "message": ""}
    assert valider_reponse(brut, table, "commentaire")[0]["statut"] == "reponse"
    assert valider_reponse(brut, table, "expliquer")[0]["statut"] == "abstention"
    # une regle de droit inventee reste bloquee meme en mode methode
    brut["explication"] = [{"texte": "Selon l'article 9999 du Code civil, tout est permis.", "sources": []}]
    assert valider_reponse(brut, table, "commentaire")[0]["statut"] == "abstention"


def test_references_reconnaissent_les_codes():
    from api.references import extraire
    from api.textes import cibles_article

    r = extraire("Que prévoit l'article 121-3 du code pénal ?")
    assert r.articles == ("121-3",) and r.codes == ("code_penal",)
    r = extraire("article L. 1232-1 du Code du travail")
    assert r.articles == ("L1232-1",) and r.codes == ("code_travail",)
    assert extraire("art. 1240 C. civ.").codes == ("code_civil",)
    assert cibles_article("34", (), True) == ("constitution_1958",)
    assert cibles_article("1240", (), False)[0] == "code_civil"
    assert "code_civil" not in cibles_article("L121-1", (), False)


def test_annales_catalogue(tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from api.annales import Annales, creer_routes_annales
    from api.journal import Journal

    class Admin:
        id = 1

    annales = Annales(tmp_path / "a.db")
    public, admin = creer_routes_annales(annales, lambda: Admin(), Journal(tmp_path / "logs"))
    app = FastAPI()
    app.include_router(public)
    app.include_router(admin, prefix="/admin")
    c = TestClient(app)
    base = {"titre": "Introduction au droit, partiel", "matiere": "introduction_au_droit", "niveau": "L1",
            "annee": 2025, "universite": "Université X", "url": "https://exemple.fr/sujet.pdf"}
    assert c.post("/admin/annales", json={**base, "url": "http://exemple.fr"}).status_code == 422
    assert c.post("/admin/annales", json={**base, "matiere": "inconnue"}).status_code == 422
    r = c.post("/admin/annales", json=base)
    assert r.status_code == 200 and r.json()["libelle_matiere"] == "Introduction au droit"
    assert len(c.get("/annales").json()["annales"]) == 1
    assert c.get("/annales", params={"matiere": "droit_civil"}).json()["annales"] == []
    rec = c.post("/admin/annales", json={**base, "matiere": "recueil", "titre": "Recueil L1 S1"})
    assert rec.status_code == 200 and rec.json()["libelle_matiere"] == "Recueil, toutes matières"
    # un recueil apparait quel que soit le filtre de matiere
    assert [a["titre"] for a in c.get("/annales", params={"matiere": "droit_civil"}).json()["annales"]] == ["Recueil L1 S1"]
    assert c.post(f"/admin/annales/{rec.json()['id']}/supprimer").status_code == 204
    assert c.post(f"/admin/annales/{r.json()['id']}/supprimer").status_code == 204
    assert c.get("/annales").json()["annales"] == []


def test_lois_citees_et_meme_texte():
    from api.references import extraire
    from api.textes import cles_texte_loi, lois_citees, meme_loi

    r = extraire("Que dit l'article 29 de la loi du 29 juillet 1881 ?")
    assert r.articles == ("29",) and r.lois == (frozenset({"date:1881-07-29"}),)
    # « n° » perd son symbole sans accents ; numero et date sont reconnus
    assert extraire("article 1er de la loi n° 90-14 du 2 janvier 1990").lois == (
        frozenset({"num:90-14", "date:1990-01-02"}),)
    assert extraire("la loi est dure mais c'est la loi").lois == ()
    assert cles_texte_loi("Ordonnance no 92-1069 du 1er octobre 1992 portant") == {"num:92-1069", "date:1992-10-01"}
    c = lois_citees("loi n°90-14")[0]
    assert meme_loi(c, "Loi n°90-14 du 2 janvier 1990") and not meme_loi(c, "Loi n°90-140 du 2 janvier 1990")
    d = lois_citees("loi du 29 juillet 1881")[0]
    assert meme_loi(d, "LOI du 29 juillet 1881") and not meme_loi(d, "Loi du 30 juin 1881")
