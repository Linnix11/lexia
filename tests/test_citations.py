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
