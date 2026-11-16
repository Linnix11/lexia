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


def test_budget_de_temps_avant_le_secours():
    """Avec un budget, Gemini rend la main des que le temps est ecoule, sans finir le tour."""
    import time as _time

    appels: list[str] = []

    def lent(request: httpx.Request) -> httpx.Response:
        appels.append(request.url.path.rsplit("/", 1)[-1].split(":")[0])
        _time.sleep(0.3)
        return httpx.Response(503, json={})

    llm = GeminiLLM(api_key="k", models=("a", "b", "c"), tentatives=1, budget=0.5)
    llm._client = httpx.Client(transport=httpx.MockTransport(lent))
    debut = _time.monotonic()
    with pytest.raises(LLMError, match="ecoule"):
        llm.generate_json(system="s", prompt="p", schema={})
    assert appels == ["a", "b"] and _time.monotonic() - debut < 1.0      # « c » n'est pas tente


def test_question_bloquee_par_le_filtre_est_un_refus_et_pas_une_panne(monkeypatch):
    """Second audit du 2026-11-16, point 11 : trois questions bloquees ouvraient le disjoncteur."""
    from api.llm.base import ContenuRefuse
    monkeypatch.setattr("time.sleep", lambda s: None)
    appels: list[str] = []

    def bloque(request: httpx.Request) -> httpx.Response:
        appels.append(request.url.path.rsplit("/", 1)[-1].split(":")[0])
        return httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}})

    llm = GeminiLLM(api_key="k", models=("a", "b"), tentatives=2)
    llm._client = httpx.Client(transport=httpx.MockTransport(bloque))
    with pytest.raises(ContenuRefuse):
        llm.generate_json(system="s", prompt="p", schema={})
    assert appels == ["a", "b"]                       # pas de second tour pour une question bloquee


def test_reponse_plafonnee_et_releve_meme_si_le_json_est_illisible():
    """Sans plafond, une question piegee faisait ecrire le modele jusqu'au delai ; une reponse illisible etait
    payee mais pas relevee (second audit de securite, points 15 et 17)."""
    import json as _json
    corps, releves = [], []

    def repondre(request):
        corps.append(_json.loads(request.read()))
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "{coupe"}]}}],
                                         "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 4096}})

    llm = GeminiLLM(api_key="k", models=("m",), tentatives=1, releve=lambda m, u: releves.append((m, u)))
    llm._client = httpx.Client(transport=httpx.MockTransport(repondre))
    with pytest.raises(LLMError):
        llm.generate_json(system="s", prompt="p", schema={})
    assert corps[0]["generationConfig"]["maxOutputTokens"] == 4096
    assert releves == [("m", {"promptTokenCount": 10, "candidatesTokenCount": 4096})]
