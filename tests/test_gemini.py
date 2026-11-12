"""Client Gemini : bascule vers le modele suivant sans reessayer un modele surcharge."""

import httpx
import pytest

from api.llm.base import LLMError
from api.llm.gemini import GeminiLLM

OK = {"candidates": [{"content": {"parts": [{"text": '{"statut": "reponse"}'}]}}]}


def client(reponses: dict[str, list[int]], appels: list[str], tentatives: int = 2) -> GeminiLLM:
    """reponses : modele -> codes HTTP renvoyes successivement."""
    def repondre(request: httpx.Request) -> httpx.Response:
        modele = request.url.path.rsplit("/", 1)[-1].split(":")[0]
        appels.append(modele)
        code = reponses[modele].pop(0)
        return httpx.Response(code, json=OK if code == 200 else {})

    llm = GeminiLLM(api_key="k", models=("a", "b", "c"), tentatives=tentatives)
    llm._client = httpx.Client(transport=httpx.MockTransport(repondre))
    return llm


def test_modele_surcharge_bascule_tout_de_suite(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    appels: list[str] = []
    llm = client({"a": [503], "b": [200], "c": []}, appels)
    assert llm.generate_json(system="s", prompt="p", schema={}) == ({"statut": "reponse"}, "b")
    assert appels == ["a", "b"]                       # « a » n'est pas reessaye avant « b »


def test_second_tour_puis_echec(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    appels: list[str] = []
    llm = client({"a": [503, 200], "b": [400], "c": [429, 503]}, appels)
    assert llm.generate_json(system="s", prompt="p", schema={})[1] == "a"
    assert appels == ["a", "b", "c", "a"]            # « b » a refuse la requete : exclu du second tour

    appels.clear()
    llm = client({"a": [503], "b": [503], "c": [503]}, appels, tentatives=1)
    with pytest.raises(LLMError, match="HTTP 503"):
        llm.generate_json(system="s", prompt="p", schema={})
    assert appels == ["a", "b", "c"]
