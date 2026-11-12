"""Modele de secours (Groq) : appele seulement si Gemini echoue, avec moins d'extraits."""

import httpx
import pytest
from fastapi.testclient import TestClient

from api.config import Settings
from api.llm.base import LLMError
from api.llm.groq import GroqLLM
from api.main import create_app
from api.retrieval.base import Hit

REPONSE = {"statut": "reponse", "titre": "t", "droit_positif": [{"texte": "Règle.", "sources": ["S1"]}],
           "explication": [], "points_incertains": [], "message": ""}


def passage(i):
    return {"id": f"code_civil:A{i}", "source_id": "code_civil", "type": "article", "numero": str(1000 + i),
            "entete": f"Code civil, article {1000 + i}", "texte": "Texte de l'article.", "url": "u",
            "version": "v", "meta": {"en_vigueur": True}}


class Retriever:
    mode = "test"

    def search(self, question, **kw):
        return [Hit(passage(i), 1.0, {"lexical"}) for i in range(8)]

    def get(self, pid):
        return None

    def versions(self, s, n):
        return []

    def couverture(self, s):
        return 0.0

    def stats(self):
        return {"moteur": "test"}


class LLM:
    def __init__(self, echec: bool):
        self.echec, self.prompts = echec, []

    def generate_json(self, *, prompt, **kw):
        self.prompts.append(prompt)
        if self.echec:
            raise LLMError("HTTP 503")
        return REPONSE, "fake"


def client(principal, secours):
    settings = Settings(gemini_models=("fake",), logs_dir=None, rate_limit_per_minute=0)
    return TestClient(create_app(settings, retriever=Retriever(), llm=principal, secours=secours, journal=None))


def test_secours_appele_seulement_si_gemini_echoue_avec_moins_d_extraits():
    principal, secours = LLM(echec=False), LLM(echec=False)
    assert client(principal, secours).post("/chat", json={"question": "responsabilité"}).status_code == 200
    assert secours.prompts == []                                           # Gemini a repondu

    principal, secours = LLM(echec=True), LLM(echec=False)
    r = client(principal, secours).post("/chat", json={"question": "responsabilité"}).json()
    assert r["statut"] == "reponse" and len(secours.prompts) == 1
    assert "[S8]" in principal.prompts[0] and "[S4]" in secours.prompts[0] and "[S5]" not in secours.prompts[0]
    assert r["controle"]["passages_consultes"] == 4                       # citations validees sur 4 extraits


def test_tout_echoue_reponse_503():
    r = client(LLM(echec=True), LLM(echec=True)).post("/chat", json={"question": "responsabilité"})
    assert r.status_code == 503


def test_client_groq(monkeypatch):
    def repondre(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer k"
        corps = request.read().decode()
        assert '"json_schema"' in corps and "openai/gpt-oss-120b" in corps
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"statut": "reponse"}'}}]})

    llm = GroqLLM(api_key="k", model="openai/gpt-oss-120b")
    llm._client = httpx.Client(transport=httpx.MockTransport(repondre), headers={"Authorization": "Bearer k"})
    assert llm.generate_json(system="s", prompt="p", schema={}) == ({"statut": "reponse"}, "groq/openai/gpt-oss-120b")

    llm._client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(429, json={})))
    with pytest.raises(LLMError, match="HTTP 429"):
        llm.generate_json(system="s", prompt="p", schema={})


def test_disjoncteur():
    from api.rag import Disjoncteur
    t = [0.0]
    d = Disjoncteur(seuil=3, pause=300, horloge=lambda: t[0])
    d.echec(), d.echec()
    assert not d.ouvert()
    d.succes()                                   # un succes remet le compteur a zero
    d.echec(), d.echec()
    assert not d.ouvert()
    d.echec()
    assert d.ouvert()                            # 3 echecs d'affilee
    t[0] = 301
    assert not d.ouvert()                        # fin de la pause : on reessaie
    d.echec()
    assert d.ouvert()                            # nouvel echec : rouvert aussitot
    t[0] = 700
    d.succes()
    assert not d.ouvert()


def test_disjoncteur_ouvert_le_principal_n_est_plus_appele():
    principal, secours = LLM(echec=True), LLM(echec=False)
    settings = Settings(gemini_models=("fake",), logs_dir=None, rate_limit_per_minute=0, disjoncteur_seuil=2)
    app = create_app(settings, retriever=Retriever(), llm=principal, secours=secours, journal=None)
    client = TestClient(app)
    for i in range(4):
        assert client.post("/chat", json={"question": f"responsabilité {i}"}).json()["statut"] == "reponse"
    assert len(principal.prompts) == 2 and len(secours.prompts) == 4       # 2 echecs, puis Groq directement
    assert client.get("/sante").json()["disjoncteur"] == "ouvert"
