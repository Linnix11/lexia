from api.citations import Controle, nettoyer_elements

TABLE = {f"S{i}": {"id": f"p{i}", "numero": None, "texte": "", "entete": ""} for i in (1, 2, 5)}


def test_labels_ecrits_dans_le_texte_retires_et_rattaches_aux_sources():
    c = Controle()
    out = nettoyer_elements([
        {"texte": "Il faut avoir la garde de la chose [S1].", "sources": ["S1"]},
        {"texte": "Le dol peut resulter d'une dissimulation (S2). Voir aussi [S1, S5].", "sources": []},
        {"texte": "Source inconnue (S9).", "sources": ["S1"]},
    ], TABLE, c, exiger_source=True)
    assert out[0] == {"texte": "Il faut avoir la garde de la chose.", "sources": ["p1"]}
    assert out[1] == {"texte": "Le dol peut resulter d'une dissimulation. Voir aussi.", "sources": ["p2", "p1", "p5"]}
    assert out[2] == {"texte": "Source inconnue.", "sources": ["p1"]}
    assert c.citations_retirees == 1    # S9 n'est pas un extrait fourni


# --- Reponse directe (audit d'interface du 2026-11-16, point 3) -------------------------------------------------

from api.citations import valider_reponse  # noqa: E402
from api.prompts import MAX_REPONSE_DIRECTE, prompt_chat, schema_reponse  # noqa: E402

DROIT = [{"texte": "Le dol est une cause de nullité.", "sources": ["S1"]}]


def test_reponse_directe_sourcee_gardee_et_limitee():
    brut = {"statut": "reponse", "titre": "Le dol", "droit_positif": DROIT, "explication": [], "points_incertains": [],
            "reponse_directe": [{"texte": f"Phrase {i}.", "sources": ["S1"]} for i in range(5)], "message": ""}
    r, c = valider_reponse(brut, TABLE)
    assert [e["texte"] for e in r["reponse_directe"]] == ["Phrase 0.", "Phrase 1.", "Phrase 2."]
    assert len(r["reponse_directe"]) == MAX_REPONSE_DIRECTE and c.elements_retires == 0


def test_reponse_directe_meme_controle_que_le_droit_positif():
    brut = {"statut": "reponse", "titre": "t", "droit_positif": DROIT, "explication": [], "points_incertains": [],
            "reponse_directe": [{"texte": "Sans source.", "sources": []},
                                {"texte": "Source inventée.", "sources": ["S9"]},
                                {"texte": "Selon l'article 9999 du Code civil, tout est permis.", "sources": ["S1"]},
                                {"texte": "Le dol rend le contrat annulable.", "sources": ["S2"]}],
            "message": ""}
    r, c = valider_reponse(brut, TABLE)
    assert r["reponse_directe"] == [{"texte": "Le dol rend le contrat annulable.", "sources": ["p2"]}]
    assert c.elements_retires == 3 and c.citations_retirees == 1
    assert "9999" in " ".join(c.references_non_verifiees)


def test_reponse_directe_seule_ne_sauve_pas_de_l_abstention():
    brut = {"statut": "reponse", "titre": "t", "droit_positif": [], "explication": [], "points_incertains": [],
            "reponse_directe": [{"texte": "Le dol est une cause de nullité.", "sources": ["S1"]}], "message": ""}
    r, _ = valider_reponse(brut, TABLE)
    assert r["statut"] == "abstention" and r["reponse_directe"] == []


def test_reponse_directe_absente_ou_refus():
    brut = {"statut": "reponse", "titre": "t", "droit_positif": DROIT, "explication": [], "points_incertains": [],
            "message": ""}
    assert valider_reponse(brut, TABLE)[0]["reponse_directe"] == []
    assert valider_reponse({"statut": "hors_champ"}, TABLE)[0]["reponse_directe"] == []


def test_consigne_et_schema_de_la_reponse_directe():
    passages = [{"id": "p1", "type": "article", "texte": "Texte.", "entete": "Art. 1137"}]
    assert "la définition et la règle essentielle" in prompt_chat("Le dol ?", "expliquer", passages)
    assert "la solution du cas" in prompt_chat("Faits.", "cas_pratique", passages)
    assert "laisse 'reponse_directe' vide" in prompt_chat("Sujet.", "dissertation", passages)
    for mode in ("expliquer", "commentaire"):
        assert "reponse_directe" in schema_reponse(mode)["required"]


# --- Couple code et article (audit du 2026-11-19, SRC-2, TST-7) -------------------------------------------------

import pytest  # noqa: E402

from api.references import articles_cites, references_non_couvertes  # noqa: E402

LOI_1991 = {"source_id": "lois", "numero": "1", "texte": "La présente loi s'applique aux procédures civiles.",
            "entete": "Loi n° 91-650 du 9 juillet 1991, article 1 (en vigueur)"}
CIV_1240 = {"source_id": "code_civil", "numero": "1240", "texte": "Tout fait quelconque de l'homme, qui cause...",
            "entete": "Code civil, article 1240 (en vigueur, depuis le 1er octobre 2016)"}
DDHC_16 = {"source_id": "ddhc_1789", "numero": "16", "texte": "Toute société dans laquelle la garantie des droits...",
           "entete": "Déclaration des droits de l'homme et du citoyen de 1789, article 16"}
QPC = {"source_id": "decisions_conseil_constitutionnel", "numero": None, "texte":
       "Décision du 16 octobre 2026. Vu l'article 61-1 de la Constitution ; vu l'article 9 de la loi du 9 juillet 1991.",
       "entete": "Conseil constitutionnel, décision n° 2026-1100 QPC du 16 octobre 2026"}
CASS = {"source_id": "judilibre", "numero": None, "texte": "Vu l'article 1242, alinéa 1er, du code civil ; vu l'article 9 ;",
        "entete": "Cass. 2e civ., 9 juillet 2026"}


@pytest.mark.parametrize("phrase, passages", [
    ("Selon l'article 9 du Code civil, chacun a droit au respect de sa vie privée.", [LOI_1991]),   # « 9 juillet »
    ("L'article 16 de la DDHC garantit la séparation des pouvoirs.", [QPC]),                       # « 16 octobre »
    ("L'article 1 du Code civil fixe l'entrée en vigueur des lois.", [LOI_1991]),                   # loi, pas code
    ("L'article 1240 du Code pénal oblige à réparer le dommage.", [CIV_1240]),                     # mauvais code
    ("L'article 2 de la Constitution fixe la langue.", [CIV_1240, DDHC_16]),
    ("Selon le Code pénal, en son article 1240, le dommage se répare.", [CIV_1240]),               # code avant
    ("L'article 9 de la DDHC pose la présomption d'innocence.", [QPC]),                           # 9 d'une loi
    ("Les articles 1240 et 1241 du Code civil fondent la responsabilité.", [CIV_1240]),           # 1241 absent
])
def test_citation_retiree_petit_numero_ou_mauvais_code(phrase, passages):
    assert references_non_couvertes(phrase, passages)


@pytest.mark.parametrize("phrase, passages", [
    ("L'article 1240 du Code civil oblige à réparer.", [CIV_1240]),
    ("L'article 1240 C. civ. oblige à réparer.", [CIV_1240]),
    ("Selon le Code civil, en son article 1240, le dommage se répare.", [CIV_1240]),
    ("L'article 1240 oblige à réparer.", [CIV_1240]),
    ("L'article 16 de la Déclaration des droits de l'homme et du citoyen protège les droits.", [DDHC_16]),
    ("L'article 61-1 de la Constitution ouvre la question prioritaire.", [QPC]),                  # cite par la decision
    ("L'article 1242, alinéa 1er, du Code civil vise les choses que l'on a sous sa garde.", [CASS]),
    ("L'article 1er de la loi du 9 juillet 1991 et l'article 1240 du Code civil.", [CIV_1240, LOI_1991]),
    ("L'article 9 de la loi du 9 juillet 1991 est visé.", [QPC]),
])
def test_citation_gardee(phrase, passages):
    assert references_non_couvertes(phrase, passages) == []


def test_articles_cites_et_texte_rattache():
    assert articles_cites("loi du 9 juillet 1991 ; le 16 octobre") == ()
    assert articles_cites("articles 1240 et 1241, alinéa 2, du Code civil ; article 1er de la Constitution ; "
                          "art. 267 TFUE ; article 3 de la loi") == (
        ("1240", "code_civil"), ("1241", "code_civil"), ("1", "constitution_1958"), ("267", "tfue"), ("3", ""))


def test_element_retire_quand_le_code_ne_correspond_pas():
    c = Controle()
    out = nettoyer_elements([{"texte": "L'article 1240 du Code pénal impose réparation.", "sources": ["S1"]},
                             {"texte": "L'article 1240 du Code civil impose réparation.", "sources": ["S1"]}],
                            {"S1": {"id": "civ", **CIV_1240}}, c, exiger_source=True)
    assert [e["texte"] for e in out] == ["L'article 1240 du Code civil impose réparation."]
    assert c.elements_retires == 1 and c.references_non_verifiees == ["article 1240"]


# --- Numeros avec espace, « 1er », Charte (audit du 2026-11-19, SRC-7, SRC-8) -----------------------------------

from api.references import _norm_num, reference_couverte, variantes  # noqa: E402
from api.retrieval.base import Hit, diversifier, doc_de  # noqa: E402


def test_numeros_avec_espace_et_premier():
    assert "R 1424-59" in variantes("R1424-59") and "R*1424-59" in variantes("R1424-59")
    assert variantes("1") == ("1", "1er") and variantes("1240") == ("1240",)
    assert _norm_num("R 1424-59") == "R1424-59" and _norm_num("1er") == "1" and _norm_num("A 1er") == "A1"
    assert reference_couverte("article", "R1424-59", [{"source_id": "code_collectivites_territoriales",
                                                       "numero": "R 1424-59", "texte": "", "entete": ""}])
    assert reference_couverte("article", "1", [{"source_id": "lois", "numero": "1er", "texte": "", "entete": ""}])
    assert not reference_couverte("article", "11", [{"source_id": "lois", "numero": "1er", "texte": "", "entete": ""}])


def test_charte_plusieurs_articles_par_reponse():
    charte = [{"id": f"charte_environnement:LEGIARTI1:{n}", "type": "article", "meta": {"id_legi": "LEGIARTI1"}}
              for n in ("1", "5", "7")]
    assert len({doc_de(p) for p in charte}) == 3
    assert len(diversifier([Hit(p, 1.0) for p in charte], 8, doc_de)) == 3
    arret = [{"id": f"judilibre:X:{i}", "type": "motifs", "meta": {"id_dila": "JURITEXT1"}} for i in range(3)]
    assert len(diversifier([Hit(p, 1.0) for p in arret], 8, doc_de)) == 1     # une decision : un passage
