"""Accident de la circulation : loi n° 85-677 du 5 juillet 1985 avant les articles 1240 a 1242 (recette du 23/11, R-1).

Une voiture mal garee devale une pente et blesse une pietonne : Lexia repondait sur 1240, 1241 et 1242 et citait
un arret de 1984, anterieur a la loi. La recherche ne remontait pas la loi, et le modele n'y pensait pas.
"""

from pathlib import Path

import pytest

from api import lexique, prompts
from api.rag import K_CHAT, Lexia
from api.retrieval.local import LocalRetriever
from eval.cas import charger, correspond

INDEX_REEL = Path(__file__).resolve().parent.parent / "data" / "index"
reel = pytest.mark.skipif(not (INDEX_REEL / "lexia.sqlite").exists(), reason="index reel absent")

ART_1_LOI_1985 = ("lois", "LEGIARTI000006839396")
RECETTE = ("Marc gare sa voiture dans une rue en pente sans serrer le frein à main. La voiture dévale la pente et "
           "renverse Julie, une piétonne, qui est blessée. Julie peut-elle obtenir réparation, et auprès de qui ?")
LOI_1985 = {"id": "lois:LEGIARTI000006839396", "source_id": "lois", "numero": "1", "type": "article",
            "entete": "LOI n° 85-677 du 5 juillet 1985, article 1", "texte": "Les dispositions du présent chapitre...",
            "meta": {"code": "LOI n° 85-677 du 5 juillet 1985"}}
ART_1242 = {"id": "code_civil:1242", "source_id": "code_civil", "numero": "1242", "type": "article",
            "entete": "Code civil, article 1242", "texte": "On est responsable...", "meta": {}}


@pytest.mark.parametrize("question", [
    RECETTE,
    "Un automobiliste renverse un piéton sur un passage protégé. Le piéton blessé peut-il être indemnisé ?",
    "Lucas, passager de la moto de son ami, est blessé quand la moto percute un muret. Qui doit l'indemniser ?",
    "Une cycliste est fauchée par une camionnette à un carrefour. Peut-elle obtenir réparation ?",
    "Après un accident de la route, la victime peut-elle demander réparation au conducteur ?",
])
def test_vehicule_a_moteur_en_cause_le_lexique_propose_la_loi_de_1985(question):
    assert lexique.vehicule_en_cause(question)
    assert ART_1_LOI_1985 in lexique.suggestions(question)


@pytest.mark.parametrize("question", [
    # la voiture subit le dommage, elle ne le cause pas (cp-06, cp-34)
    "Des tuiles mal entretenues tombent du toit d’une maison et abîment une voiture garée devant. Le propriétaire "
    "est-il responsable ?",
    "En faisant du skate sur le parking, une collégienne de 14 ans heurte une voiture et raye la carrosserie. Le "
    "propriétaire de la voiture veut être indemnisé : contre qui peut-il agir ?",
    # pas de moteur (cp-04) ; pas de dommage
    "Par inattention, un cycliste renverse un piéton qui se casse le bras. Le piéton peut-il demander des dommages "
    "et intérêts ?",
    "Paul a vendu sa voiture à Marie sans lui dire que le moteur était usé. La vente est-elle valable ?",
])
def test_vehicule_victime_ou_sans_moteur_pas_de_loi_de_1985(question):
    assert lexique.vehicule_en_cause(question) is None
    assert ART_1_LOI_1985 not in lexique.suggestions(question)


def test_note_regime_special_et_pas_de_note_garde():
    prompt = prompts.prompt_chat(RECETTE, "cas_pratique", [LOI_1985, ART_1242])
    assert "5 juillet 1985" in prompt and "régime spécial" in prompt and "1240 à 1242" in prompt
    # un camion et un velo : la garde du velo (1242 al. 1) n'est pas le fondement, la note garde n'est pas ajoutee
    q = "Un camion percute un vélo à un carrefour et blesse la cycliste. Peut-elle obtenir réparation ?"
    prompt = prompts.prompt_chat(q, "cas_pratique", [LOI_1985, ART_1242])
    assert "garde de la chose" not in prompt and "5 juillet 1985" in prompt
    # sans la loi dans les extraits, pas de note (le modele ne cite que ce qui lui est fourni)
    assert "5 juillet 1985" not in prompts.prompt_chat(RECETTE, "cas_pratique", [ART_1242])


def test_seuls_les_cas_d_accident_changent():
    """Les autres cas des jeux d'evaluation gardent un prompt et des suggestions identiques."""
    touches = {c.id for f in sorted(Path("eval").glob("*.yaml")) for c in charger(f)
               if lexique.vehicule_en_cause(c.question)}
    assert touches == {"cp-35", "cp-36", "cp-37"}


def test_source_attendue_loi_par_identifiant():
    assert correspond("lois:LEGIARTI000006839396", LOI_1985)
    assert not correspond("lois:LEGIARTI000006839396", {**LOI_1985, "id": "lois:LEGIARTI000006842643"})


@reel
def test_recette_la_recherche_remonte_la_loi_de_1985():
    """Sans Gemini (ni reformulation ni vecteurs) : le cas le plus defavorable."""
    r = LocalRetriever(INDEX_REEL)
    passages, _ = Lexia(r, llm=None).rechercher(RECETTE, "droit_civil", K_CHAT)
    assert "lois:LEGIARTI000006839396" in [p["id"] for p in passages]
    # garde de la chose hors vehicule (D119) : 1242 toujours fourni
    q = "Paul, 17 ans, joue au ballon dans la rue et casse la vitre du voisin. Le voisin peut-il obtenir réparation ?"
    passages, _ = Lexia(r, llm=None).rechercher(q, "droit_civil", K_CHAT)
    assert any(p["source_id"] == "code_civil" and p.get("numero") == "1242" for p in passages)
    assert not any("85-677" in ((p.get("meta") or {}).get("code") or "") for p in passages)
