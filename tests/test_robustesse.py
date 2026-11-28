"""Lot D de l'audit du 2026-11-18 : robustesse du serveur."""

from api.llm.base import LLMError
from tests.test_secours import client

QUESTION = {"question": "Quelles sont les conditions de la responsabilité ?", "elements_attendus": ["une faute"],
            "explication": "Voir l'article.", "sources": ["S1"]}
CORRECTION = {"corrections": [{"index": 0, "evaluation": "partiel", "commentaire": "Incomplet.",
                               "elements_manquants": []}]}


class Script:
    """Modele de test : echoue toujours, ou renvoie les reponses prevues dans l'ordre."""

    def __init__(self, reponses=None):
        self.reponses, self.prompts = list(reponses or []), []

    def generate_json(self, *, prompt, **kw):
        self.prompts.append(prompt)
        if not self.reponses:
            raise LLMError("HTTP 503")
        return self.reponses.pop(0), "fake"


def test_d1_correction_des_questions_ouvertes_par_le_secours():
    """Gemini en panne : la correction passait directement en « a verifier », sans essayer Groq."""
    principal, secours = Script(), Script([{"questions": [QUESTION]}, CORRECTION])
    c = client(principal, secours)
    quiz = c.post("/quiz", json={"theme": "responsabilité", "format": "ouvertes", "nombre": 1}).json()
    r = c.post("/quiz/correct", json={"quiz_id": quiz["quiz_id"],
                                      "reponses": [{"index": 0, "valeur": "Une faute."}]}).json()
    assert r["resultats"][0]["statut"] == "partiel"
    assert "<reponse_etudiant>" in secours.prompts[-1] and "Extraits : S1" in secours.prompts[-1]
    assert "[S5]" not in secours.prompts[-1]                   # secours : extraits reduits


def test_d5_questionnaires_gardes_en_base_au_redemarrage(tmp_path):
    """Un redemarrage du service (publication) perdait tous les questionnaires en cours."""
    from api.quiz import Quiz, QuizService, QuizStore

    class Lexia:
        def generer(self, *, construire, passages, **kw):
            construire(passages)
            return CORRECTION, "fake", passages

    base = tmp_path / "lexia.db"
    QuizStore(chemin=base).ajouter(Quiz(id="q1", format="ouvertes", theme="t", questions=[QUESTION], table={},
                                        proprietaire=7))
    service = QuizService(lexia=Lexia(), llm=None, store=QuizStore(chemin=base))     # redemarrage
    r = service.corriger("q1", [{"index": 0, "valeur": "Une faute."}], uid=7)
    assert r["resultats"][0]["statut"] == "partiel"
    relu = QuizStore(chemin=base).get("q1")                                           # second redemarrage
    assert relu.proprietaire == 7 and relu.questions == [QUESTION] and relu.correction == r
    assert QuizStore(ttl=-1, chemin=base).get("q1") is None                           # expire : efface
    assert QuizStore(chemin=base).get("q1") is None


def test_d5_l_application_garde_les_questionnaires_dans_la_base_des_comptes(tmp_path):
    import sqlite3

    from api.comptes import Comptes
    from api.config import Settings
    from api.main import create_app
    from tests.test_secours import Retriever

    create_app(Settings(gemini_models=("fake",), logs_dir=None, rate_limit_per_minute=0), retriever=Retriever(),
               llm=Script(), comptes=Comptes(tmp_path / "c.db"), journal=None)
    with sqlite3.connect(tmp_path / "c.db") as con:
        assert con.execute("SELECT 1 FROM sqlite_master WHERE name = 'questionnaires'").fetchone()


def test_d5_le_service_lit_les_modeles_dans_le_cache():
    from pathlib import Path
    service = (Path(__file__).parent.parent / "deploy" / "lexia@.service").read_text()
    assert "Environment=HF_HUB_OFFLINE=1" in service


def test_d6_la_reformulation_tient_dans_un_budget_global():
    """Delai par modele : un premier modele lent faisait appeler le second alors que la recherche etait partie."""
    import time

    import httpx

    from api.config import Settings
    from api.main import _construire_expanseur

    appels = []

    def repondre(request):
        appels.append(request.url.path)
        time.sleep(0.25)
        return httpx.Response(503, json={})

    exp = _construire_expanseur(Settings(gemini_api_key="k", expansion_model="m1", expansion_fallback_models=("m2",),
                                         expansion_timeout=0.2))
    exp.llm._client = httpx.Client(transport=httpx.MockTransport(repondre))
    assert exp.etendre("Qu'est-ce que le dol ?") is None
    assert len(appels) == 1                                 # budget de 0,2 s epuise : pas de second modele


def test_d6_sous_charge_la_recherche_n_attend_pas_la_reformulation(monkeypatch):
    import threading

    from api import rag
    from tests.test_secours import Retriever

    class Expanseur:
        appels = 0

        def etendre(self, texte):
            Expanseur.appels += 1

    plein = threading.BoundedSemaphore(1)
    plein.acquire()                                        # tous les fils de reformulation occupes
    monkeypatch.setattr(rag, "_FILS_REFORMULATION", plein)
    lexia = rag.Lexia(Retriever(), Script(), expanseur=Expanseur(), delai_reformulation=5)
    passages, _ = lexia.rechercher("Qu'est-ce que le dol ?", None, 8)
    assert passages and Expanseur.appels == 0

    monkeypatch.setattr(rag, "_FILS_REFORMULATION", threading.BoundedSemaphore(1))
    lexia.rechercher("Qu'est-ce que le dol ?", None, 8)
    assert Expanseur.appels == 1
