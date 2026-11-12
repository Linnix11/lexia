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


def test_releve_des_jetons_apres_une_reponse(tmp_path):
    from api.journal import Journal
    from api.main import releve_jetons
    from eval.cout import calculer, lire

    usage = {"promptTokenCount": 1200, "candidatesTokenCount": 300, "thoughtsTokenCount": 50}

    def repondre(request):
        return httpx.Response(200, json={**OK, "usageMetadata": usage})

    journal = Journal(tmp_path)
    llm = GeminiLLM(api_key="k", models=("m",), releve=releve_jetons(journal, "generation"))
    llm._client = httpx.Client(transport=httpx.MockTransport(repondre))
    llm.generate_json(system="s", prompt="p", schema={})
    ligne = lire(tmp_path / "modele.jsonl")[0]
    assert (ligne["modele"], ligne["role"], ligne["entree"], ligne["sortie"], ligne["reflexion"]) == \
        ("m", "generation", 1200, 300, 50)
    assert "p" not in ligne.values()                   # aucun texte de prompt journalise

    r = calculer([ligne], [{"route": "chat", "modele": "m"}, {"route": "chat", "modele": "m", "cache": True}],
                 {"m": (1.0, 2.0)})
    assert r["questions"] == 1 and abs(r["cout_par_question"] - (1200 * 1 + 350 * 2) / 1e6) < 1e-12


def test_releve_en_erreur_ne_bloque_pas_la_reponse():
    def releve(modele, usage):
        raise RuntimeError("disque plein")

    llm = GeminiLLM(api_key="k", models=("m",), releve=releve)
    llm._client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=OK)))
    assert llm.generate_json(system="s", prompt="p", schema={}) == ({"statut": "reponse"}, "m")
