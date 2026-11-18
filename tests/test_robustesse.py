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
