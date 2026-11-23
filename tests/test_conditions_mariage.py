"""Conditions de fond du mariage : la difference de sexe n'en est plus une depuis la loi n° 2013-404 du 17 mai 2013
(article 143 du Code civil). Dossier enseignant, question 5 : Lexia la citait comme condition ; l'article 143 n'etait
pas fourni (aucune entree du lexique) et un arret de 2007 sur le mariage de deux hommes l'etait."""

from pathlib import Path

import pytest

from api import lexique, prompts
from api.rag import K_CHAT, Lexia
from api.retrieval.local import LocalRetriever

INDEX_REEL = Path(__file__).resolve().parent.parent / "data" / "index"
reel = pytest.mark.skipif(not (INDEX_REEL / "lexia.sqlite").exists(), reason="index reel absent")

QUESTION = "Quelles sont les conditions de fond du mariage en droit français ?"
ART_143 = {"id": "code_civil:LEGIARTI000027431993", "source_id": "code_civil", "numero": "143", "type": "article",
           "entete": "Code civil, article 143", "meta": {"en_vigueur": True},
           "texte": "Le mariage est contracté par deux personnes de sexe différent ou de même sexe."}
ART_144 = {**ART_143, "id": "code_civil:LEGIARTI000027431990", "numero": "144", "entete": "Code civil, article 144",
           "texte": "Le mariage ne peut être contracté avant dix-huit ans révolus."}


@pytest.mark.parametrize("question", [
    QUESTION,
    "Quels sont les empêchements à mariage ?",
    "Deux femmes peuvent-elles se marier en France ?",
    "Quelles conditions faut-il remplir pour se marier ?",
])
def test_le_lexique_propose_l_article_143(question):
    assert ("code_civil", "143") in lexique.suggestions(question)


def test_loi_applicable_au_mariage_garde_202_1():
    """ti-06 : question internationale, suggestions inchangees (regle de conflit seule)."""
    s = lexique.suggestions("Quelle loi s'applique aux conditions du mariage d'époux de nationalités différentes ?")
    assert s == [("code_civil", "202-1")]


def test_note_sur_la_difference_de_sexe():
    prompt = prompts.prompt_chat(QUESTION, "expliquer", [ART_143, ART_144])
    assert "même sexe" in prompt and "n'est plus une condition" in prompt
    assert "n'est plus une condition" not in prompts.prompt_chat(QUESTION, "expliquer", [ART_144])
    assert "n'est plus une condition" not in prompts.prompt_chat("Qu'est-ce que le dol ?", "expliquer", [ART_143])


@reel
def test_question_5_la_recherche_fournit_l_article_143():
    """Sans Gemini (ni reformulation ni vecteurs)."""
    passages, _ = Lexia(LocalRetriever(INDEX_REEL), llm=None).rechercher(QUESTION, "droit_de_la_famille", K_CHAT)
    assert "code_civil:LEGIARTI000027431993" in [p["id"] for p in passages]
