"""Reponse du modele hors du schema demande (audit du 19/11, SRV-3, TST-5) : modele suivant, ou 503 propre,
jamais d'erreur 500."""

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from api import prompts
from api.citations import Controle, nettoyer_elements
from api.config import Settings
from api.llm.base import LLMError
from api.llm.forme import conforme
from api.llm.gemini import GeminiLLM
from api.llm.groq import GroqLLM
from api.main import create_app
from tests.test_secours import REPONSE, Retriever

SCHEMA = prompts.schema_reponse("expliquer")
HORS_SCHEMA = {**REPONSE, "droit_positif": ["Règle."]}          # liste de chaines au lieu d'objets
QUIZ_HORS_SCHEMA = {"questions": "Trois questions sur le dol."}  # chaine au lieu d'une liste


def test_conforme():
    assert conforme(REPONSE, SCHEMA)
    assert conforme({**REPONSE, "message": None, "explication": None}, SCHEMA)   # nuls toleres par le lecteur
    assert not conforme(HORS_SCHEMA, SCHEMA)
    assert not conforme(["Règle."], SCHEMA)
    assert not conforme({**REPONSE, "droit_positif": [None]}, SCHEMA)
    assert not conforme({**REPONSE, "titre": {"a": 1}}, SCHEMA)
    assert not conforme(QUIZ_HORS_SCHEMA, prompts.SCHEMAS_QUIZ["qcm"])
    assert conforme({"questions": [{"question": "q", "choix": ["a", "b", "c"], "bonne_reponse": "1"}]},
                    prompts.SCHEMAS_QUIZ["qcm"])                            # scalaire mal type : laisse au lecteur


def gemini(reponses: dict[str, dict], appels: list[str]) -> GeminiLLM:
    def repondre(request: httpx.Request) -> httpx.Response:
        modele = request.url.path.rsplit("/", 1)[-1].split(":")[0]
        appels.append(modele)
        texte = json.dumps(reponses[modele])
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": texte}]}}]})

    llm = GeminiLLM(api_key="k", models=tuple(reponses), tentatives=1)
    llm._client = httpx.Client(transport=httpx.MockTransport(repondre))
    return llm


def groq(reponses: dict[str, dict], appels: list[str]) -> GroqLLM:
    def repondre(request: httpx.Request) -> httpx.Response:
        modele = json.loads(request.read())["model"]
        appels.append(modele)
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(reponses[modele])}}]})

    llm = GroqLLM(api_key="k", models=tuple(reponses))
    llm._client = httpx.Client(transport=httpx.MockTransport(repondre))
    return llm


def test_gemini_hors_schema_passe_au_modele_suivant():
    appels: list[str] = []
    llm = gemini({"a": HORS_SCHEMA, "b": REPONSE}, appels)
    assert llm.generate_json(system="s", prompt="p", schema=SCHEMA) == (REPONSE, "b")
    assert appels == ["a", "b"]


def test_groq_hors_schema_passe_au_modele_suivant():
    appels: list[str] = []
    llm = groq({"x": HORS_SCHEMA, "y": REPONSE}, appels)
    assert llm.generate_json(system="s", prompt="p", schema=SCHEMA) == (REPONSE, "groq/y")
    with pytest.raises(LLMError, match="hors du schema"):
        groq({"x": HORS_SCHEMA}, []).generate_json(system="s", prompt="p", schema=SCHEMA)


def client(principal, secours):
    settings = Settings(gemini_models=("a",), logs_dir=None, rate_limit_per_minute=0)
    app = create_app(settings, retriever=Retriever(), llm=principal, secours=secours, journal=None)
    return TestClient(app, raise_server_exceptions=False)


def test_chat_gemini_hors_schema_bascule_sur_le_secours():
    appels: list[str] = []
    r = client(gemini({"a": HORS_SCHEMA}, appels), groq({"y": REPONSE}, appels)).post(
        "/chat", json={"question": "responsabilité"})
    assert r.status_code == 200 and r.json()["statut"] == "reponse" and appels == ["a", "y"]


def test_chat_et_quiz_tout_hors_schema_503_et_non_500():
    c = client(gemini({"a": HORS_SCHEMA}, []), groq({"y": HORS_SCHEMA}, []))
    assert c.post("/chat", json={"question": "responsabilité"}).status_code == 503
    c = client(gemini({"a": QUIZ_HORS_SCHEMA}, []), groq({"y": QUIZ_HORS_SCHEMA}, []))
    assert c.post("/quiz", json={"theme": "le dol"}).status_code == 503


def test_nettoyage_ignore_un_element_qui_n_est_pas_un_objet():
    table = {"S1": {"id": "p1", "texte": "Règle.", "source_id": "code_civil"}}
    controle = Controle()
    out = nettoyer_elements(["Règle.", None, {"texte": "Règle.", "sources": ["S1"]}], table, controle,
                            exiger_source=True)
    assert [e["texte"] for e in out] == ["Règle."] and controle.elements_retires == 2
