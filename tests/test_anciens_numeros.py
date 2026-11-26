"""D136 (audit du 25/11 sur les reponses) : ancien numero du Code civil donne pour le droit actuel (R4), la cause
des anciens articles 1131 a 1133 (R6), reperes S1, S3 ecrits dans le texte des reponses (R10). Sans appel au modele."""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import concordance, lexique
from api.citations import Controle, nettoyer_elements, retirer_reperes, valider_reponse
from api.config import Settings
from api.main import create_app
from api.prompts import prompt_chat
from api.rag import K_CHAT, Lexia, table_extraits
from api.references import extraire
from api.retrieval.local import LocalRetriever
from tests.test_api import FakeLLM, index_dir  # noqa: F401  (fixture partagee)

CC = "code_civil"
INDEX_REEL = Path(__file__).resolve().parent.parent / "data" / "index"
reel = pytest.mark.skipif(not (INDEX_REEL / "lexia.sqlite").exists(), reason="index reel absent")


def article(numero: str, texte: str, *, avant_reforme: bool = False) -> dict:
    meta = ({"en_vigueur": False, "date_debut": "1985-10-15", "date_fin": concordance.DATE_REFORME} if avant_reforme
            else {"en_vigueur": True, "date_debut": "2016-10-01"})
    return {"id": f"{CC}:{numero}{'-ancien' if avant_reforme else ''}", "source_id": CC, "type": "article",
            "numero": numero, "entete": f"Code civil, article {numero}", "texte": texte, "url": "", "meta": meta}


def decision(i: int, texte: str) -> dict:
    return {"id": f"cass:{i}", "source_id": "cass", "type": "decision", "numero": None,
            "entete": f"Cour de cassation, 2e chambre civile, 31 mars 2022, n° 20-23.28{i}", "texte": texte,
            "url": "", "meta": {}}


# --- R4 : table completee ----------------------------------------------------------------------------------

def test_table_completee():
    attendu = {"1121": ("1205",), "1146": ("1344",), "1150": ("1231-3",), "1152": ("1231-5",),
               "1166": ("1341-1",), "1167": ("1341-2",), "1386-1": ("1245",), "1386-2": ("1245-1",),
               "1386-11": ("1245-10",), "1386-18": ("1245-17",)}
    assert {a: concordance.REFORME_2016[a] for a in attendu} == attendu
    assert "1386-19" not in concordance.REFORME_2016 and concordance.REFORME_2016["1386"] == ("1244",)


# --- R4 : cas de l'article 1152 (clause penale), reponse du 25/11 rejouee sans le modele -------------------

# Extraits du cas : l'article 1152 actuel (prescription, mineurs) et un arret sur l'ancien 1152 ; pas de 1231-5.
EXTRAITS_1152 = [
    article("1152", "La prescription ne court pas contre les mineurs non émancipés..."),
    decision(4, "Constitue une clause pénale, au sens de l'article 1152 du code civil dans sa rédaction antérieure "
                "à celle de l'ordonnance n° 2016-131 du 10 février 2016, la clause..."),
]
REPONSE_1152 = {
    "statut": "reponse", "titre": "La clause pénale",
    "reponse_directe": [{"texte": "Constitue une clause pénale au sens de l'article 1152 du Code civil la stipulation "
                                  "par laquelle les parties évaluent forfaitairement et d'avance l'indemnité due en "
                                  "cas d'inexécution.", "sources": ["S2"]}],
    "droit_positif": [{"texte": "Constitue une clause pénale au sens de l'article 1152 du Code civil la stipulation "
                                "par laquelle les parties évaluent forfaitairement l'indemnité.", "sources": ["S2"]}],
    "explication": [{"texte": "L'article 1152 du Code civil prévoit que la prescription ne court pas contre les "
                              "mineurs.", "sources": ["S1"]}],
    "points_incertains": [],
}


def test_cas_1152_signale_l_ancienne_numerotation():
    table = table_extraits(EXTRAITS_1152)
    reponse, _ = valider_reponse(REPONSE_1152, table)
    assert reponse["statut"] == "reponse"
    assert concordance.signaler_anciens_numeros(reponse, EXTRAITS_1152) == 2
    mention = "article 1152 du Code civil (ancienne numérotation, aujourd'hui article 1231-5) la stipulation"
    assert mention in reponse["reponse_directe"][0]["texte"]
    assert mention in reponse["droit_positif"][0]["texte"]
    # element appuye sur l'article 1152 actuel (prescription) : rien a signaler
    assert "ancienne" not in reponse["explication"][0]["texte"]
    # sources intactes, et une seconde passe n'ajoute rien
    assert reponse["droit_positif"][0]["sources"] == ["cass:4"]
    assert concordance.signaler_anciens_numeros(reponse, EXTRAITS_1152) == 0


@pytest.mark.parametrize("texte, actuels, attendu", [
    # le texte donne deja le numero actuel
    ("L'ancien article 1152 du Code civil, devenu l'article 1231-5, permet au juge de réduire la peine.", set(), None),
    # autre code nomme
    ("L'article 1134 du code de commerce.", set(), None),
    ("Le code de commerce, en son article 1134, dispose...", set(), None),
    # article seulement reecrit (meme numero) : pas une renumerotation
    ("L'article 1101 du Code civil définit le contrat.", set(), None),
    # version actuelle parmi les sources de l'element
    ("Selon l'article 1382 du Code civil, les présomptions...", {"1382"}, None),
    ("Les articles 1382 et 1383 du Code civil posent la faute.", set(),
     "Les articles 1382 et 1383 du Code civil (ancienne numérotation : 1382, aujourd'hui article 1240 ; 1383, "
     "aujourd'hui article 1241) posent la faute."),
    ("La formule de l'arrêt Jand'heur vise l'article 1384, alinéa 1er, du Code civil.", set(),
     "La formule de l'arrêt Jand'heur vise l'article 1384, alinéa 1er, du Code civil (ancienne numérotation, "
     "aujourd'hui article 1242)."),
    ("Le producteur répond du défaut (article 1386-4 du Code civil).", set(),
     "Le producteur répond du défaut (article 1386-4 du Code civil, ancienne numérotation, aujourd'hui article "
     "1245-3)."),
])
def test_annotation(texte, actuels, attendu):
    assert concordance.annoter(texte, actuels) == (attendu or texte)


def test_element_sans_source_juge_sur_tous_les_extraits():
    """Une explication sans source qui parle de l'article 1152 alors que sa version actuelle est un extrait : on ne
    sait pas laquelle est visee, rien n'est ajoute."""
    reponse = {"explication": [{"texte": "L'article 1152 du Code civil s'applique.", "sources": []}]}
    assert concordance.signaler_anciens_numeros(reponse, EXTRAITS_1152) == 0
    assert concordance.signaler_anciens_numeros(reponse, EXTRAITS_1152[1:]) == 1


def test_chat_annote_la_reponse(index_dir, tmp_path):  # noqa: F811
    """Chaine complete avec l'index de test (1382 ancien et 1240 actuel) et un modele simule."""
    llm = FakeLLM()
    llm.reponses.append({"statut": "reponse", "titre": "Faute", "droit_positif": [
        {"texte": "La faute engage la responsabilité de son auteur (article 1382 du Code civil).",
         "sources": ["S1", "S2"]}], "explication": [], "points_incertains": [], "message": ""})
    settings = Settings(gemini_models=("fake",), index_dir=index_dir, logs_dir=tmp_path)
    client = TestClient(create_app(settings, retriever=LocalRetriever(index_dir), llm=llm))
    data = client.post("/chat", json={"question": "Que dit l'article 1382 du Code civil ?"}).json()
    assert data["droit_positif"][0]["texte"] == ("La faute engage la responsabilité de son auteur (article 1382 du "
                                                 "Code civil, ancienne numérotation, aujourd'hui article 1240).")


def test_carte_mentale_garde_sa_mention():
    from api.cartes_mentales import _ancien_numero
    assert _ancien_numero("Article 1152", EXTRAITS_1152[1:]) == ("1152", ("1231-5",))
    assert _ancien_numero("Article 1152", EXTRAITS_1152) is None
    assert _ancien_numero("Article 1131", []) is None     # sans equivalent : pas de « aujourd'hui article » sur la carte


def test_lexique_clause_penale():
    for q in ("Qu'est-ce que la clause pénale ?", "Le juge peut-il réduire une clause pénale manifestement excessive ?"):
        assert (CC, "1231-5") in lexique.suggestions(q)


# --- R6 : la cause -----------------------------------------------------------------------------------------

Q26 = "Quelles sont les conditions de validité de la cause d'un contrat prévues par l'article 1131 du Code civil ?"


def test_cause_sans_equivalent():
    assert concordance.anciens_numeros(extraire(Q26)) == {"1131": ("1128", "1162", "1169")}
    assert concordance.a_servir({"1108": ("1128",)}) == ["1128", "1162", "1169"]
    note = concordance.note({"1131": concordance.CAUSE})
    assert "pas d'équivalent" in note and "1162" in note and "1169" in note and "1er octobre 2016" in note
    assert "une cause licite" in concordance.note({"1108": ("1128",)})
    p = prompt_chat(Q26, "expliquer", [], anciens={"1131": list(concordance.CAUSE)})
    assert "la cause n'est plus une condition de validité" in p
    # dans une reponse : signale sans « aujourd'hui article »
    texte = concordance.annoter("La cause illicite (article 1133 du Code civil) rendait le contrat nul.", set())
    assert "ancienne numérotation, sans équivalent aujourd'hui, voir les articles 1128, 1162, 1169" in texte
    assert "1131" not in concordance.REFORME_2016 and "1132" not in concordance.REFORME_2016


@pytest.fixture(scope="module")
def retriever_reel():
    if not (INDEX_REEL / "lexia.sqlite").exists():
        pytest.skip("index reel absent")
    return LocalRetriever(INDEX_REEL)


@reel
def test_sans_equivalent_verifie(retriever_reel):
    for ancien, actuels in concordance.SANS_EQUIVALENT.items():
        assert concordance.ancienne_version(retriever_reel.versions(CC, ancien)), ancien
        for n in actuels:
            assert any((v.get("meta") or {}).get("en_vigueur") for v in retriever_reel.versions(CC, n)), n


@reel
def test_question_26_sert_l_ancien_1131_et_les_articles_1162_1169(retriever_reel):
    lexia = Lexia(retriever_reel, llm=None)
    passages, infos = lexia.rechercher(Q26, "droit_des_contrats", K_CHAT)
    civil = [(p.get("numero"), (p.get("meta") or {}).get("date_fin")) for p in passages if p["source_id"] == CC]
    assert ("1131", concordance.DATE_REFORME) in civil
    assert {"1162", "1169"} <= {n for n, fin in civil if fin != concordance.DATE_REFORME}
    assert infos["concordance"] == {"1131": ["1128", "1162", "1169"]}
    ancien = next(p for p in passages if p.get("numero") == "1131"
                  and (p.get("meta") or {}).get("date_fin") == concordance.DATE_REFORME)
    v = lexia.vigueur(ancien["id"])
    assert v["en_vigueur"] is False and v["version_en_vigueur"] is None and "1169" in v["message"]


@reel
def test_question_1152_sert_l_article_1231_5(retriever_reel):
    passages, _ = Lexia(retriever_reel, llm=None).rechercher(
        "Que prévoit l'article 1152 du Code civil sur la clause pénale ?", None, K_CHAT)
    assert "1231-5" in {p.get("numero") for p in passages if p["source_id"] == CC}


# --- R10 : reperes S1, S3 dans le texte --------------------------------------------------------------------

TABLE = {f"S{i}": {"id": f"p{i}", "texte": "", "source_id": "x"} for i in range(1, 9)}


@pytest.mark.parametrize("texte, attendu", [
    ("I. A. L'interdiction des arrêts de règlement (article 5 du Code civil). Sources mobilisables : S1. B. "
     "L'obligation de juger. Sources mobilisables : S3. II. Une source vivante.",
     "I. A. L'interdiction des arrêts de règlement (article 5 du Code civil). B. L'obligation de juger. II. Une "
     "source vivante."),
    ("que la dissolution et les pouvoirs exceptionnels (sources : S3, S4).",
     "que la dissolution et les pouvoirs exceptionnels."),
    ("euros (articles 1245-1 du Code civil et décret n° 2005-113, S2 et S5).",
     "euros (articles 1245-1 du Code civil et décret n° 2005-113)."),
    ("écarter (Cour de cassation, Chambre civile 1, 13 mars 2024, S5).",
     "écarter (Cour de cassation, Chambre civile 1, 13 mars 2024)."),
    ("I. Une source contestée ; sources : S1, S2. II. Une source admise.", "I. Une source contestée. II. Une source admise."),
    ("Plan en deux parties : S7", "Plan en deux parties"),
])
def test_reperes_nus_retires(texte, attendu):
    assert retirer_reperes(texte, TABLE) == attendu


@pytest.mark.parametrize("texte", [
    "Voir S. 1902, 1, 25 (Sirey) et D. 1903.",
    "L'article L. 1152-1 du Code du travail et l'article R*421-1 du code de l'urbanisme.",
    "La loi n° 2016-1547 du 18 novembre 2016, article 4.",
    "Ce cours est enseigné au semestre S1, en L2 S3.",
    "Le repère S12 n'est pas un extrait de la table.",
    "Les sources du droit : la loi, la coutume, la jurisprudence.",
])
def test_reperes_sans_faux_positif(texte):
    assert retirer_reperes(texte, TABLE) == texte


def test_sources_de_l_element_inchangees():
    items = [{"texte": "Le juge ne peut statuer par voie de disposition générale. Sources mobilisables : S1, S3.",
               "sources": ["S2"]}]
    out = nettoyer_elements(items, TABLE, Controle(), exiger_source=False)
    assert out == [{"texte": "Le juge ne peut statuer par voie de disposition générale.", "sources": ["p2"]}]
    assert not re.search(r"\bS\d", out[0]["texte"])
