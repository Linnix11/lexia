"""Journal : purge quotidienne des lignes de plus de 12 mois, sans perte des lignes recentes."""

import json

from api.journal import Journal


def test_purge_au_premier_ecrit_du_jour(tmp_path):
    ancien = {"ts": "2020-01-01T00:00:00+00:00", "route": "chat"}
    recent = {"ts": "2099-01-01T00:00:00+00:00", "route": "chat"}
    (tmp_path / "requetes.jsonl").write_text(f"{json.dumps(ancien)}\npas du json\n{json.dumps(recent)}\n")
    (tmp_path / "admin.jsonl").write_text(f"{json.dumps(ancien)}\n")

    j = Journal(tmp_path)
    j.ecrire("requetes", route="quiz")
    lignes = (tmp_path / "requetes.jsonl").read_text().splitlines()
    assert len(lignes) == 3 and "2020-01-01" not in "".join(lignes)       # ancienne retiree
    assert lignes[0] == "pas du json" and json.loads(lignes[-1])["route"] == "quiz"
    assert (tmp_path / "admin.jsonl").read_text() == ""                    # tous les journaux

    (tmp_path / "admin.jsonl").write_text(f"{json.dumps(ancien)}\n")
    j.ecrire("requetes", route="chat")                                     # meme jour : pas de nouvelle purge
    assert "2020-01-01" in (tmp_path / "admin.jsonl").read_text()
