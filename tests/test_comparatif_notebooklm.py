import json

import pytest

from eval import comparatif_notebooklm as comp


def test_selection_30_cas_existants():
    cas = comp.selection()
    assert len(cas) == 30 == len(set(comp.IDS))
    assert sum(1 for c in cas if c.piege) == 7


def test_texte_lexia_sans_identifiants_internes():
    r = {"statut": "reponse", "titre": "T", "droit_positif": [{"texte": "Règle.", "sources": ["code_civil:X"]}],
         "explication": [{"texte": "Explication.", "sources": []}], "points_incertains": [],
         "sources": [{"id": "code_civil:X", "entete": "Code civil, article 1170"}]}
    t = comp.texte_lexia(r)
    assert "Règle." in t and "Code civil, article 1170" in t
    assert "code_civil:X" not in t and "DROIT POSITIF" not in t
    assert comp.texte_lexia({"statut": "abstention", "message": "Rien trouvé."}) == "Rien trouvé."


def ligne(i, exa, exb, refa="oui", refb="non"):
    return {"id": i, "exactitude_A": exa, "utilite_A": "4", "references_ok_A": refa, "comportement_ok_A": "oui",
            "exactitude_B": exb, "utilite_B": "3", "references_ok_B": refb, "comportement_ok_B": "non"}


def test_calculer_retrouve_les_systemes_via_la_cle():
    cle = {"c1": {"A": "lexia", "B": "notebooklm"}, "c2": {"A": "notebooklm", "B": "lexia"}}
    r = comp.calculer([ligne("c1", "5", "1"), ligne("c2", "4", "4")], cle)
    s = r["stats"]
    assert s["lexia"]["exactitude"] == [5, 4]
    assert s["notebooklm"]["erreurs_de_droit"] == ["c1"]
    assert s["lexia"]["references_ok"] == [True, False]
    assert r["victoires"] == {"lexia": 1, "notebooklm": 0, "egalite": 1}


def test_calculer_refuse_une_note_invalide():
    with pytest.raises(ValueError):
        comp.calculer([ligne("c1", "6", "1")], {"c1": {"A": "lexia", "B": "notebooklm"}})


def test_chaine_complete(tmp_path, monkeypatch):
    monkeypatch.setattr(comp, "DOSSIER", tmp_path)
    assert comp.preparer() == 0
    nb = comp.lire_csv(tmp_path / "notebooklm.csv")
    for l in nb:
        l["reponse"] = f"Réponse NB {l['id']}"
    comp.ecrire_csv(tmp_path / "notebooklm.csv", ["id", "question", "reponse"], nb)
    run = tmp_path / "run.jsonl"
    run.write_text("\n".join(json.dumps({"id": i, "reponse": {"statut": "abstention", "message": f"L {i}"}})
                             for i in comp.IDS), encoding="utf-8")

    assert comp.grille(run) == 0
    lignes = comp.lire_csv(tmp_path / "grille_aveugle.csv")
    cle = json.loads((tmp_path / "cle.json").read_text(encoding="utf-8"))
    assert len(lignes) == 30
    for l in lignes:
        lettre_lexia = "A" if cle[l["id"]]["A"] == "lexia" else "B"
        assert l[f"reponse_{lettre_lexia}"] == f"L {l['id']}"
    assert {c["A"] for c in cle.values()} == {"lexia", "notebooklm"}  # le tirage alterne

    for l in lignes:
        l.update({"exactitude_A": "4", "exactitude_B": "3"})
    comp.ecrire_csv(tmp_path / "grille_aveugle.csv", list(lignes[0]), lignes)
    assert comp.bilan() == 0
    assert "Exactitude moyenne" in (tmp_path / "bilan.md").read_text(encoding="utf-8")


def test_grille_signale_les_reponses_manquantes(tmp_path, monkeypatch):
    monkeypatch.setattr(comp, "DOSSIER", tmp_path)
    comp.preparer()
    run = tmp_path / "run.jsonl"
    run.write_text("", encoding="utf-8")
    assert comp.grille(run) == 1
