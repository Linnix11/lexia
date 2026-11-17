"""Grands arrets de la Cour de cassation designes par leur nom d'usage (D90).

Un sommaire officiel ne contient jamais le nom sous lequel les etudiants connaissent l'arret (« Blieck »,
« Chronopost ») : la recherche ne le retrouvait pas (6 grands arrets sur 12, eval/cas_grands_arrets.yaml).
Le nom cite dans la question est traduit en numero de pourvoi, puis la recherche par reference existante
sert l'arret (api/references.py).

Chaque numero a ete verifie dans l'archive DILA CASS (date, formation et objet du sommaire) le 2026-11-17.
Un nom courant (Bertrand, Cousin...) n'est reconnu que si la question parle d'un arret ou de jurisprudence :
« Paul Bertrand casse une vitre » ne doit pas appeler l'arret de 1997.
"""

from __future__ import annotations

import re

from api.textes import sans_accents

# (motif sans accents, minuscules ; pourvois ; nom seul suffisant)
GRANDS_ARRETS: tuple[tuple[str, tuple[str, ...], bool], ...] = (
    (r"\bblieck\b", ("89-15.231",), True),                       # Ass. plen., 29 mars 1991
    (r"\bbertrand\b", ("94-21.111",), False),                    # Civ. 2e, 19 fevrier 1997
    (r"\bchronopost\b", ("93-18.632",), True),                   # Com., 22 octobre 1996
    (r"\bjacques vabre\b|\bcafes jacques vabre\b", ("73-13.556",), True),   # Ch. mixte, 24 mai 1975
    (r"\bgabillet\b", ("80-14.994",), True),                     # Ass. plen., 9 mai 1984
    (r"\bfullenwarth\b", ("79-16.612",), True),                  # Ass. plen., 9 mai 1984
    (r"\bderguini\b", ("80-93.481",), True),                     # Ass. plen., 9 mai 1984
    (r"\blemaire\b", ("80-93.031",), False),                     # Ass. plen., 9 mai 1984
    (r"\bdesmares\b", ("81-12.850",), True),                     # Civ. 2e, 21 juillet 1982
    (r"\bperruche\b", ("99-13.701",), False),                    # Ass. plen., 17 novembre 2000
    (r"\bcostedoat\b", ("97-17.378", "97-20.152"), True),        # Ass. plen., 25 fevrier 2000
    (r"\blevert\b", ("99-11.287",), False),                      # Civ. 2e, 10 mai 2001
    (r"\bcousin\b", ("00-82.066",), False),                      # Ass. plen., 14 decembre 2001
    (r"\bbaldus\b", ("98-11.381",), True),                       # Civ. 1re, 3 mai 2000
    (r"\bpoussin\b", ("76-11.551",), False),                     # Civ. 1re, 22 fevrier 1978
    (r"\bhuard\b", ("90-18.547",), False),                       # Com., 3 novembre 1992
    (r"\bmanoukian\b", ("00-10.243", "00-10.949"), True),        # Com., 26 novembre 2003
    (r"\bfaurecia\b", ("09-11.841",), True),                     # Com., 29 juin 2010
    (r"\bboot shop\b|\bmyr'?ho\b", ("05-13.255",), True),        # Ass. plen., 6 octobre 2006
    (r"\b1er decembre 1995\b", ("91-15.578", "91-15.999", "91-19.653", "93-13.688"), False),  # Ass. plen., prix
)
_CONTEXTE = re.compile(r"\barrets?\b|\bjurisprudence\b|\bcassation\b|\bjuge\b|\bdecide\b")
_MOTIFS = tuple((re.compile(m), pv, seul) for m, pv, seul in GRANDS_ARRETS)


def pourvois_cites(texte: str) -> tuple[str, ...]:
    """Numeros de pourvoi (« 89-15.231 ») des grands arrets nommes dans la question."""
    t = sans_accents(texte).lower()
    contexte = bool(_CONTEXTE.search(t))
    out: list[str] = []
    for motif, pourvois, seul in _MOTIFS:
        if (seul or contexte) and motif.search(t):
            out += [p for p in pourvois if p not in out]
    return tuple(out)
