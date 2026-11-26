"""Fiches de revision (D139) : consigne du mode fiche, articles et grands arrets de la force obligatoire.

Dossier enseignant, question 21 (« fiche de revision sur la force obligatoire du contrat ») : jurisprudence cle
faite d'arrets d'espece (indemnite fixee a la cote Argus, clause de substitution), ni la bonne foi (art. 1104), ni
l'effet relatif (art. 1199), ni les sanctions de l'inexecution (art. 1217), memo en une longue phrase.
"""

from api import grands_arrets, lexique, prompts
from api.prompts import MODES, RUBRIQUES

CC = "code_civil"
Q21 = "Fais-moi une fiche de révision sur la force obligatoire du contrat."


def test_consigne_fiche_exige_arrets_de_principe_articles_et_memo_court():
    consigne = prompts.prompt_chat(Q21, "fiche", [])
    for attendu in ("articles centraux", "seulement des arrêts de principe", "arrêt d'espèce",
                    "aucun arrêt de principe", "trois à cinq éléments distincts", "jamais un seul", "notion voisine à ne pas confondre",
                    "son article central"):
        assert attendu in consigne, attendu
    # rubriques inchangees : le schema et l'interface s'appuient sur elles
    assert RUBRIQUES["fiche"] == ("Définition", "Règles à retenir", "Jurisprudence clé", "Pièges fréquents", "Mémo")


def test_autres_modes_inchanges():
    for mode in ("expliquer", "cas_pratique", "commentaire", "dissertation"):
        consigne = prompts.prompt_chat("Qu'est-ce que la force obligatoire du contrat ?", mode, [])
        assert "arrêt d'espèce" not in consigne and "Mémo" not in consigne, mode
    assert MODES["expliquer"].startswith("Mode : expliquer un concept.")


def test_force_obligatoire_articles_centraux_proposes():
    # L'ordre compte : MAX_LEXIQUE (4) articles au plus par question.
    assert lexique.suggestions(Q21) == [(CC, "1103"), (CC, "1104"), (CC, "1193"), (CC, "1217")]


def test_force_obligatoire_grands_arrets_de_principe():
    assert grands_arrets.notions_de(Q21) == ["force_obligatoire"]
    # bonne foi et substance des droits (Les Maréchaux), refus ancien de la revision, effet relatif (Boot shop)
    assert [a.id for a in grands_arrets.arrets_pour(Q21)] == ["les-marechaux", "canal-de-craponne", "boot-shop"]
    # Canal de Craponne est abandonne : la note au modele le dit (test_note_cite_date_et_statut_abandonne), il ne
    # peut pas etre presente comme droit positif
    assert grands_arrets.registre().arrets["canal-de-craponne"].statut == "abandonne"


def test_force_obligatoire_hors_contrat_sans_grand_arret():
    for question in ("Quelle est la force obligatoire des arrêts de la Cour européenne des droits de l'homme ?",
                     "La loi a-t-elle force obligatoire avant sa publication ?"):
        assert "force_obligatoire" not in grands_arrets.notions_de(question), question
