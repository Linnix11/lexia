"""Matieres tirees des maquettes de licence (D97) : registre, route /matieres, lexique, recherche sur l'index reel."""

from pathlib import Path

import pytest
import yaml

from api import lexique
from api.config import ROOT
from api.matieres import ANNEES, MATIERES, sources_par_matiere
from tests.test_api import env, index_dir  # noqa: F401  (fixtures partagees)

INDEX_REEL = Path(__file__).resolve().parent.parent / "data" / "index"
NOUVELLES = ("procedure_penale", "contentieux_administratif", "droit_des_societes", "droit_administratif_des_biens")


def test_registre_et_matieres_concordent():
    registre = yaml.safe_load((ROOT / "registry" / "sources.yaml").read_text(encoding="utf-8"))
    citees = {m for s in registre["sources"] for m in s.get("matieres") or []}
    assert citees <= set(MATIERES)          # une matiere du registre sans intitule ferait echouer /matieres
    par_matiere = sources_par_matiere()
    assert list(par_matiere) == list(MATIERES)  # ordre du site : annee de licence
    for m, info in MATIERES.items():
        assert info.annee in ANNEES, m
        assert info.principales and set(info.principales) <= set(par_matiere[m]), m
    annees = [MATIERES[m].annee for m in par_matiere]
    assert annees == sorted(annees)


def test_nouvelles_matieres_et_leurs_sources():
    s = sources_par_matiere()
    assert {"code_procedure_penale", "code_justice_penale_mineurs", "cass_criminelle"} <= set(s["procedure_penale"])
    assert {"code_justice_administrative", "conseil_etat"} <= set(s["contentieux_administratif"])
    assert {"code_commerce", "code_civil", "cass_commerciale"} <= set(s["droit_des_societes"])
    assert {"code_propriete_personnes_publiques", "code_expropriation"} <= set(s["droit_administratif_des_biens"])
    # le droit pénal garde le Code de procédure pénale
    assert "code_procedure_penale" in s["droit_penal"]


def test_route_matieres_annee_et_sources_principales(env):  # noqa: F811
    client, _, _ = env
    par_id = {m["id"]: m for m in client.get("/matieres").json()}
    pp = par_id["procedure_penale"]
    assert pp["libelle"] == "Procédure pénale" and pp["annee"] == "L3"
    assert pp["principales"] == ["code_procedure_penale", "cass_criminelle"]
    assert pp["noms_sources"]["code_procedure_penale"] == "Code de procédure pénale"
    assert "garde à vue" in pp["mots"]
    assert par_id["droit_constitutionnel"]["annee"] == "L1"


@pytest.mark.parametrize("question, attendu", [
    ("Qu'est-ce que l'enquête de flagrance ?", ("code_procedure_penale", "53")),
    ("Quels sont les droits en garde à vue ?", ("code_procedure_penale", "63-1")),
    ("Qu'est-ce que la détention provisoire ?", ("code_procedure_penale", "144")),
    ("Le principe d'opportunité des poursuites", ("code_procedure_penale", "40-1")),
    ("Comment contester une décision implicite de rejet ?", ("code_justice_administrative", "R421-2")),
    ("Qu'est-ce que le rapporteur public ?", ("code_justice_administrative", "L7")),
    ("Le préfet peut-il déférer un arrêté municipal ?", ("code_collectivites_territoriales", "L2131-6")),
    ("Qu'est-ce que l'abus de biens sociaux ?", ("code_commerce", "L241-3")),
    ("Qu'est-ce qu'une SARL ?", ("code_commerce", "L223-1")),
    ("Le domaine public est-il inaliénable ?", ("code_propriete_personnes_publiques", "L3111-1")),
    ("Quel est le délai de rétractation ?", ("code_consommation", "L221-18")),
    ("Qu'est-ce que la réserve héréditaire ?", ("code_civil", "912")),
    ("Qu'est-ce que la faute inexcusable de l'employeur ?", ("code_securite_sociale", "L452-1")),
])
def test_lexique_des_nouvelles_notions(question, attendu):
    assert attendu in lexique.suggestions(question)


@pytest.mark.parametrize("question, exclu", [
    ("Sa société a été placée en liquidation", ("code_civil", "1832")),        # pas une question sur le contrat de société
    ("Il ne paie plus ses loyers depuis trois mois", ("code_securite_sociale", "L411-1")),
    ("La tierce opposition en procédure civile", ("code_justice_administrative", "R832-1")),
    ("Elle a acheté une voiture d'occasion en ligne qui tombe en panne", ("code_consommation", "L221-1")),
])
def test_nouvelles_notions_sans_faux_positif(question, exclu):
    assert exclu not in lexique.suggestions(question)


def test_suggestions_limitees_aux_sources_de_la_matiere():
    q = "Qu'est-ce que la présomption d'innocence ?"
    assert lexique.suggestions(q)[0] == ("code_civil", "9-1")
    # en procedure penale, l'article du Code civil ne prend plus de place parmi les 4 suggestions
    filtrees = lexique.suggestions(q, sources=sources_par_matiere()["procedure_penale"])
    assert filtrees and all(s in sources_par_matiere()["procedure_penale"] for s, _ in filtrees)


@pytest.mark.skipif(not (INDEX_REEL / "lexia.sqlite").exists(), reason="index reel absent")
@pytest.mark.parametrize("question, matiere, attendu", [
    ("Qu'est-ce que l'enquête de flagrance ?", "procedure_penale", ("code_procedure_penale", "53")),
    ("Quand une personne peut-elle être mise en examen ?", "procedure_penale", ("code_procedure_penale", "80-1")),
    ("Quel est le rôle du rapporteur public ?", "contentieux_administratif", ("code_justice_administrative", "L7")),
    ("Comment le Code civil définit-il la société ?", "droit_des_societes", ("code_civil", "1832")),
    ("Quels sont les critères du domaine public ?", "droit_administratif_des_biens",
     ("code_propriete_personnes_publiques", "L2111-1")),
])
def test_article_de_principe_des_nouvelles_matieres(question, matiere, attendu):
    from api.rag import K_CHAT, Lexia
    from api.retrieval.local import LocalRetriever
    passages, _ = Lexia(LocalRetriever(INDEX_REEL), llm=None).rechercher(question, matiere, K_CHAT)
    trouves = [(p["source_id"], p.get("numero")) for p in passages]
    assert attendu in trouves, trouves
