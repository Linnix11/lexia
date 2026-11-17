"""Durees de conservation annoncees dans la politique de confidentialite (docs/registre-traitements.md)."""

from __future__ import annotations

from datetime import timedelta

from api import comptes as module_comptes
from api.comptes import Comptes


def test_trace_de_suppression_effacee_apres_24_h(tmp_path, monkeypatch):
    c = Comptes(tmp_path / "lexia.db")
    u = c.creer("etudiant@exemple.fr", "un mot de passe solide 2026")
    c.supprimer(u.id, garder_trace=True)
    assert c._q("SELECT count(*) FROM suppressions")[0][0] == 1

    c.purger_sessions()  # moins de 24 h : la trace reste (elle bloque la reinscription immediate)
    assert c._q("SELECT count(*) FROM suppressions")[0][0] == 1

    maintenant = module_comptes._maintenant()
    monkeypatch.setattr(module_comptes, "_maintenant", lambda: maintenant + timedelta(days=1, minutes=1))
    c.purger_sessions()
    assert c._q("SELECT count(*) FROM suppressions")[0][0] == 0
