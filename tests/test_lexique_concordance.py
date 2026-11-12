"""Phase B du plan d'amelioration : lexique local, anciens numeros (reforme 2016), modes methode,
et non-regression de la recherche sur les cas de l'evaluation qui echouaient."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import concordance, lexique
from api.config import Settings
from api.main import create_app
from api.prompts import prompt_chat
from api.rag import Lexia
from api.references import extraire
from api.retrieval.local import LocalRetriever
from tests.test_api import ABSTENTION, FakeLLM, index_dir  # noqa: F401  (fixture partagee)

CC, CONST = "code_civil", "constitution_1958"
INDEX_REEL = Path(__file__).resolve().parent.parent / "data" / "index"


# --- lexique ------------------------------------------------------------------

@pytest.mark.parametrize("question, attendu", [
    ("Pourquoi les juges ne peuvent-ils pas rendre d'arrêts de règlement ?", (CC, "5")),
    ("Le juge est-il lié par ses propres décisions antérieures ?", (CC, "5")),
    ("Propose un plan de dissertation sur la non-rétroactivité de la loi", (CC, "2")),
    ("Quels principes ne peuvent pas faire l'objet d'une révision constitutionnelle ?", (CONST, "89")),
    ("Quelles sont les conditions de la responsabilité pour faute ?", (CC, "1240")),
    ("Explique la méthode du commentaire d'arrêt en droit des contrats", (CC, "1103")),
    ("Quel est le principe de la force obligatoire du contrat ?", (CC, "1103")),
    ("Qu’est-ce que le devoir d’information ?", (CC, "1112-1")),  # apostrophes typographiques
    ("Qu'est-ce que la violence économique ?", (CC, "1143")),
])
def test_lexique_reconnait_les_notions(question, attendu):
    assert attendu in lexique.suggestions(question)


@pytest.mark.parametrize("question, exclu", [
    ("Qu'est-ce que la force majeure en matière contractuelle ?", (CC, "414")),   # « majeure » != majorité
    ("Comment se passe la dissolution du PACS ?", (CONST, "12")),
    ("Que dit l'article précédent ?", (CC, "5")),
])
def test_lexique_sans_faux_positif(question, exclu):
    assert exclu not in lexique.suggestions(question)


def test_lexique_plafonne():
    q = "force obligatoire, bonne foi dans le contrat, vices du consentement, dol, violence, lésion"
    assert len(lexique.suggestions(q)) == lexique.MAX_LEXIQUE


# --- concordance --------------------------------------------------------------

def test_anciens_numeros_seulement_pour_le_code_civil():
    assert concordance.anciens_numeros(extraire("Que dit l'article 1134 du Code civil ?")) == {
        "1134": ("1103", "1193", "1104")}
    assert concordance.anciens_numeros(extraire("article 1382")) == {"1382": ("1240",)}
    assert concordance.anciens_numeros(extraire("article 1134 du code pénal")) == {}
    assert concordance.anciens_numeros(extraire("article 1240 du Code civil")) == {}


def test_note_de_concordance_dans_le_prompt():
    p = prompt_chat("Que dit l'article 1134 ?", "expliquer", [], anciens={"1134": ["1103", "1193", "1104"]})
    assert "1er octobre 2016" in p and "1103, 1193, 1104" in p
    assert "réécrit" in concordance.note({"1101": ["1101"]})
    assert "1134" not in prompt_chat("q", "expliquer", [])


def test_ancien_numero_sert_l_ancien_texte_et_l_article_actuel(index_dir, tmp_path):  # noqa: F811
    llm = FakeLLM()
    llm.reponses.append(ABSTENTION)
    settings = Settings(gemini_models=("fake",), index_dir=index_dir, logs_dir=tmp_path)
    client = TestClient(create_app(settings, retriever=LocalRetriever(index_dir), llm=llm))
    data = client.post("/chat", json={"question": "Que dit l'article 1382 du Code civil ?"}).json()
    prompt = llm.prompts[-1]
    assert "du 21 mars 1804 au 1er octobre 2016" in prompt          # ancienne version de 1382
    assert "Code civil, article 1240" in prompt                       # article actuel
    assert "jusqu'au 1er octobre 2016" in prompt                      # consigne au modele
    assert data["controle"]["concordance"] == {"1382": ["1240"]}

    ancien = "code_civil:LEGIARTI000006438819"
    v = client.get(f"/sources/{ancien}/vigueur").json()
    assert v["en_vigueur"] is False and "1240" in v["message"]
    assert v["version_en_vigueur"]["id"] == "code_civil:LEGIARTI000032041571"


# --- modes methode ------------------------------------------------------------

def test_methode_sans_extrait_appelle_quand_meme_le_modele(index_dir, tmp_path):  # noqa: F811
    llm = FakeLLM()
    llm.reponses.append({"statut": "reponse", "titre": "Méthode", "droit_positif": [],
                         "explication": [{"texte": "1. Définir les termes du sujet.", "sources": []}],
                         "points_incertains": [], "message": ""})
    settings = Settings(gemini_models=("fake",), index_dir=index_dir, logs_dir=tmp_path)
    client = TestClient(create_app(settings, retriever=LocalRetriever(index_dir), llm=llm))
    data = client.post("/chat", json={"question": "zzqqwx yyvvkk", "mode": "dissertation"}).json()
    assert len(llm.prompts) == 1 and data["statut"] == "reponse"
    assert "n'utilise pas le statut 'abstention'" in llm.prompts[0]
    # hors mode methode, toujours aucune sollicitation du modele
    data = client.post("/chat", json={"question": "zzqqwx yyvvkk"}).json()
    assert data["statut"] == "abstention" and len(llm.prompts) == 1


# --- index reel : articles du lexique, concordance et cas de l'evaluation ----------

reel = pytest.mark.skipif(not (INDEX_REEL / "lexia.sqlite").exists(), reason="index reel absent")


@pytest.fixture(scope="module")
def retriever_reel():
    return LocalRetriever(INDEX_REEL)


def _en_vigueur(r, src, num):
    return [v for v in r.versions(src, num) if (v.get("meta") or {}).get("en_vigueur") or src == CONST]


@reel
def test_articles_du_lexique_existent(retriever_reel):
    absents = [(s, n) for _, arts in lexique.NOTIONS for s, n in arts if not _en_vigueur(retriever_reel, s, n)]
    assert absents == []


@reel
def test_table_de_concordance_verifiee(retriever_reel):
    for ancien, nouveaux in concordance.REFORME_2016.items():
        assert concordance.ancienne_version(retriever_reel.versions(CC, ancien)), ancien
        for n in nouveaux:
            assert _en_vigueur(retriever_reel, CC, n), (ancien, n)


# Cas de eval/cas.yaml dont la source attendue n'etait pas transmise au modele (run 20261111-153059).
# Recherche sans Gemini (ni reformulation ni vecteurs) : le cas le plus defavorable.
CAS_REGRESSION = ["intro-04", "intro-36", "intro-37", "const-32", "civ-32", "civ-40", "piege-29", "piege-30"]


@reel
@pytest.mark.parametrize("cas_id", CAS_REGRESSION)
def test_source_attendue_retrouvee_sans_gemini(retriever_reel, cas_id):
    from eval.cas import charger, correspond
    from api.rag import K_CHAT
    cas = {c.id: c for c in charger()}[cas_id]
    passages, _ = Lexia(retriever_reel, llm=None).rechercher(cas.question, cas.matiere, K_CHAT)
    assert any(correspond(ref, p) for ref in cas.sources for p in passages), \
        [f"{p['source_id']}:{p.get('numero')}" for p in passages]
