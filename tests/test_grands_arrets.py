"""Grands arrets nommes dans la question (api/grands_arrets.py, D90)."""

import pytest

from api.grands_arrets import GRANDS_ARRETS, pourvois_cites
from api.references import _POURVOI_RE, extraire


@pytest.mark.parametrize("question, attendu", [
    ("Que décide l'arrêt Blieck ?", ("89-15.231",)),
    ("Chronopost et la clause limitative de responsabilité", ("93-18.632",)),       # nom seul suffisant
    ("Que juge l'arrêt Bertrand de 1997 ?", ("94-21.111",)),
    ("Paul Bertrand casse la vitre de son voisin. Doit-il réparer ?", ()),          # nom courant, sans arret
    ("Le cousin de Léa lui prête sa voiture", ()),
    ("Que décide l'arrêt Costedoat ?", ("97-17.378", "97-20.152")),
    ("Comparez les arrêts Derguini et Lemaire", ("80-93.481", "80-93.031")),
    ("Arrêts d'Assemblée plénière du 1er décembre 1995 sur le prix", ("91-15.578", "91-15.999", "91-19.653",
                                                                      "93-13.688")),
])
def test_noms_d_arrets_reconnus(question, attendu):
    assert pourvois_cites(question) == attendu


def test_pourvois_au_format_des_references():
    # meme format que les pourvois cites en toutes lettres, pour la recherche par reference
    for _, pourvois, _ in GRANDS_ARRETS:
        for p in pourvois:
            assert _POURVOI_RE.fullmatch(p), p
    assert extraire("L'arrêt Blieck, pourvoi 89-15.231").pourvois == ("89-15.231",)   # pas de doublon
    assert extraire("Que décide l'arrêt Blieck ?").vide is False
