"""Constats du dossier enseignant du 23/11 (`docs/relecture-enseignant/constats-avant-relecture.md`) : questions 5, 6,
12 et 25 (D122). Chaque test echoue sans la correction."""

from pathlib import Path

import pytest

from api import lexique, prompts
from api.matieres import sources_pour
from api.rag import K_CHAT, Lexia
from api.retrieval.local import LocalRetriever

INDEX_REEL = Path(__file__).resolve().parent.parent / "data" / "index"
reel = pytest.mark.skipif(not (INDEX_REEL / "lexia.sqlite").exists(), reason="index reel absent")

Q25 = "Propose-moi un plan de dissertation sur le sujet : « La jurisprudence est-elle une source du droit ? »"
Q12 = "Qu'est-ce que l'autorité de la chose jugée en matière civile et quelles sont ses conditions ?"
Q6 = "Qu'est-ce que l'usufruit et quels sont les droits et obligations de l'usufruitier ?"
Q5 = "Quelles sont les conditions de fond du mariage en droit français ?"
PLAN = {"plan": ["Livre III : Des différentes manières dont on acquiert la propriété", "Titre III : Des sources d'obligations"]}
SOURCES_OBLIGATIONS = {"meta": PLAN, "source_id": "code_civil", "numero": "1100"}
DOL = {"meta": {"plan": PLAN["plan"] + ["Sous-titre Ier : Le contrat"]}, "source_id": "code_civil", "numero": "1137"}


def test_q25_articles_des_sources_d_obligations_ecartes_hors_sujet():
    assert lexique.hors_matiere(SOURCES_OBLIGATIONS, Q25)
    assert not lexique.hors_matiere(SOURCES_OBLIGATIONS, "Quelles sont les sources des obligations ?")    # intro-30
    assert not lexique.hors_matiere(SOURCES_OBLIGATIONS, "Qu'est-ce qu'un acte juridique et un fait juridique ?")
    assert ("code_civil", "4") in lexique.suggestions(Q25)
    assert not lexique.hors_matiere(DOL, Q25)  # le reste du titre (contrats, responsabilite) n'est pas vise


def test_q12_le_code_civil_est_une_source_de_la_procedure_civile():
    assert "code_civil" in sources_pour("procedure_civile")
    assert ("code_civil", "1355") in lexique.suggestions(Q12, sources=sources_pour("procedure_civile"))


def test_q6_usufruit_droits_obligations_et_extinction():
    s = lexique.suggestions(Q6, sources=sources_pour("droit_des_biens"))
    assert {("code_civil", n) for n in ("578", "582", "605", "617")} <= set(s)


def test_q22_fiche_du_fait_des_choses_avec_la_loi_de_1985():
    s = lexique.suggestions("Fais-moi une fiche sur la responsabilité du fait des choses.")
    assert s[:2] == [("code_civil", "1242"), ("lois", "LEGIARTI000006839396")]
    assert ("lois", "LEGIARTI000006839396") not in lexique.suggestions("Qu'est-ce que la responsabilité du fait d'autrui ?")


def test_q5_note_sur_l_article_148():
    art = {"source_id": "code_civil", "meta": {"en_vigueur": True}, "type": "article", "entete": "Code civil",
           "texte": "..."}
    passages = [{**art, "id": "a", "numero": "143"}, {**art, "id": "b", "numero": "148"}]
    assert "dispense d'âge" in prompts.prompt_chat(Q5, "expliquer", passages)
    assert "dispense d'âge" not in prompts.prompt_chat(Q5, "expliquer", passages[:1])


@reel
@pytest.mark.parametrize("question, matiere, attendus, exclus", [
    (Q25, "introduction_au_droit", {"5", "4"}, {"1100", "1100-1", "1100-2"}),
    (Q12, "procedure_civile", {"1355"}, set()),
    (Q6, "droit_des_biens", {"578", "582", "605", "617"}, set()),
    (Q5, "droit_de_la_famille", {"143", "146", "147"}, set()),
])
def test_recherche_sur_l_index_reel(question, matiere, attendus, exclus):
    """Sans Gemini (ni reformulation ni vecteurs) : le cas le plus defavorable."""
    passages, _ = Lexia(LocalRetriever(INDEX_REEL), llm=None).rechercher(question, matiere, K_CHAT)
    civil = {p.get("numero") for p in passages if p["source_id"] == "code_civil"}
    assert attendus <= civil and not exclus & civil
