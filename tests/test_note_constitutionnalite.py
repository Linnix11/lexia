"""Note au modele sur l'article 61 de la Constitution (dossier enseignant du 24/11, question 28)."""

from api import prompts

ART_61 = {"source_id": "constitution_1958", "numero": "61"}
QUESTION_CE = "Comment le Conseil d'État contrôle-t-il la constitutionnalité des lois votées par le Parlement ?"


def test_lois_ordinaires_controlees_seulement_sur_saisine():
    note = prompts.note_constitutionnalite("Comment fonctionne le contrôle a priori des lois ?", [ART_61])
    assert "ne dis jamais que toute loi est soumise" in note
    assert "loi-écran" not in note


def test_premisse_du_controle_par_le_conseil_d_etat_corrigee():
    note = prompts.note_constitutionnalite(QUESTION_CE, [ART_61])
    assert "loi-écran" in note and "corrige cette prémisse" in note


def test_sans_l_article_61_pas_de_note():
    assert prompts.note_constitutionnalite(QUESTION_CE, [{"source_id": "constitution_1958", "numero": "62"}]) == ""

