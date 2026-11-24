"""Cas pratique : note sur la garde de la chose (art. 1242 al. 1) quand les faits mettent en cause une chose."""

from pathlib import Path

from api import lexique, prompts
from eval.cas import charger

ART_1242 = {"id": "code_civil:1242", "source_id": "code_civil", "numero": "1242", "type": "article",
            "entete": "Code civil, article 1242", "texte": "On est responsable...", "meta": {}}
ART_1240 = {**ART_1242, "id": "code_civil:1240", "numero": "1240", "entete": "Code civil, article 1240"}
CP_33 = ("Paul, 17 ans, joue au ballon dans la rue et casse la vitre du voisin. Le voisin peut-il obtenir "
         "réparation, et auprès de qui ?")


def test_note_ajoutee_aux_faits_qui_mettent_en_cause_une_chose():
    prompt = prompts.prompt_chat(CP_33, "cas_pratique", [ART_1240, ART_1242])
    assert "garde de la chose" in prompt and "(ballon)" in prompt
    assert lexique.chose_en_cause("une collégienne de 14 ans fait du skate, heurte une voiture et raye la "
                                  "carrosserie") == "skate"


def test_pas_de_note_sans_1242_ni_hors_du_cas_pratique_ni_sans_chose():
    assert "garde de la chose" not in prompts.prompt_chat(CP_33, "cas_pratique", [ART_1240])
    assert "garde de la chose" not in prompts.prompt_chat(CP_33, "expliquer", [ART_1240, ART_1242])
    tags = "Le fils de 15 ans des voisins a tagué notre garage. À qui peut-on réclamer réparation ?"
    assert "garde de la chose" not in prompts.prompt_chat(tags, "cas_pratique", [ART_1240, ART_1242])
    assert lexique.chose_en_cause("Paul a vendu son vélo à Marie. La vente est-elle valable ?") is None  # pas de dommage


def test_seuls_les_cas_d_une_chose_en_cause_changent():
    """Les autres cas des jeux d'evaluation gardent un prompt identique : leurs resultats ne peuvent pas baisser."""
    touches = {c.id for f in sorted(Path("eval").glob("*.yaml")) for c in charger(f)
               if c.mode == "cas_pratique" and lexique.chose_en_cause(c.question)}
    # gan-22 : cas du ballon du dossier enseignant (D126), ajoute pour la notion du fait des choses
    assert touches == {"cp-01", "cp-02", "cp-33", "cp-34", "gan-22"}


def test_chose_et_dommage_sans_age_le_lexique_propose_1242():
    """cp-01 : « Leo brise la vitrine en jouant au ballon » ne recevait pas l'article 1242 (pas d'age dit)."""
    q = "Léo brise la vitrine d’un commerçant en jouant au ballon dans la rue. Le commerçant peut-il obtenir réparation ?"
    assert ("code_civil", "1242") in lexique.suggestions(q)
