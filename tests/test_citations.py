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
