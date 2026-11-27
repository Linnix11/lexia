"""Pouvoirs propres du President (D143, dossier enseignant du 27/11, question 8)."""

from api import lexique, prompts

ART_19 = {"source_id": "constitution_1958", "numero": "19"}
QUESTION_8 = "Quels sont les pouvoirs propres du Président de la République sous la Ve République ?"


def test_note_dit_que_les_actes_de_l_article_19_sont_dispenses_de_contreseing():
    note = prompts.note_contreseing([ART_19])
    assert "DISPENSÉS de contreseing" in note and "pouvoirs propres" in note
    assert "Ne dis jamais qu'un acte fondé sur l'un de ces articles exige un contreseing" in note


def test_sans_l_article_19_pas_de_note():
    assert prompts.note_contreseing([{"source_id": "constitution_1958", "numero": "20"}]) == ""


def test_note_jointe_au_prompt():
    assert "DISPENSÉS de contreseing" in prompts.prompt_chat(QUESTION_8, "expliquer", [{**ART_19, "id": "constitution_1958:art:19", "type": "article", "texte": "Les actes du Président..."}])


def test_lexique_propose_l_article_19_et_des_pouvoirs_propres():
    numeros = [num for _, num in lexique.suggestions(QUESTION_8)]
    assert numeros[0] == "19" and {"8", "12", "16"} <= set(numeros)
