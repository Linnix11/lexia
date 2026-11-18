"""Grands arrets designes par leur nom d'usage : Cour de cassation (D90), Conseil d'Etat et Tribunal des conflits.

Un sommaire officiel ne contient jamais le nom sous lequel les etudiants connaissent l'arret (« Blieck »,
« Chronopost ») : la recherche ne le retrouvait pas (6 grands arrets sur 12, eval/cas_grands_arrets.yaml).
Le nom cite dans la question est traduit en numero de pourvoi, puis la recherche par reference existante
sert l'arret (api/references.py).

Chaque numero a ete verifie dans l'archive DILA CASS (date, formation et objet du sommaire) le 2026-11-17.
Un nom courant (Bertrand, Cousin...) n'est reconnu que si la question parle d'un arret ou de jurisprudence :
« Paul Bertrand casse une vitre » ne doit pas appeler l'arret de 1997.

Juridiction administrative (audit du 2026-11-18, B5) : le nom est traduit en identifiant de la decision dans
l'archive JADE (CETATEXT...), chacun verifie le 2026-11-18 dans l'index (juridiction, formation, date, numero et
objet du sommaire). Le nom d'un grand arret present dans un extrait (cours depose, decision) couvre aussi sa
citation dans la reponse (B6).
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

# (motif, identifiant JADE, nom seul suffisant, nom affiche si la citation n'est pas couverte)
GRANDS_ARRETS_ADMINISTRATIFS: tuple[tuple[str, str, bool, str], ...] = (
    (r"\bblanco\b", "CETATEXT000007605886", False, "TC, 8 février 1873, Blanco"),                    # 00012
    (r"\bpelletier\b", "CETATEXT000007607581", False, "TC, 30 juillet 1873, Pelletier"),             # 00035
    (r"\bterrier\b", "CETATEXT000007634922", False, "CE, 6 février 1903, Terrier"),                  # 07496
    (r"\bfeutry\b", "CETATEXT000007607588", True, "TC, 29 février 1908, Feutry"),                    # 00624
    (r"\b(?:compagnie generale (?:francaise )?des )?tramways\b", "CETATEXT000007635472", False,
     "CE, 11 mars 1910, Compagnie générale française des tramways"),                               # 16178
    (r"\banguet\b", "CETATEXT000007633783", True, "CE, 3 février 1911, Anguet"),                     # 34922
    (r"\bgranits porphyroides\b", "CETATEXT000007634187", True,
     "CE, 31 juillet 1912, Société des granits porphyroïdes des Vosges"),                          # 30701
    (r"\bgomel\b", "CETATEXT000007634222", True, "CE, 4 avril 1914, Gomel"),                         # 55125
    (r"\bgaz de bordeaux\b", "CETATEXT000007629465", True, "CE, 30 mars 1916, Gaz de Bordeaux"),     # 59928
    (r"\bheyries\b", "CETATEXT000007637204", True, "CE, 28 juin 1918, Heyriès"),                     # 63412
    (r"\blabonne\b", "CETATEXT000007635800", False, "CE, 8 août 1919, Labonne"),                     # 56377
    (r"\bbac d'eloka\b|\bsociete commerciale de l'ouest africain\b", "CETATEXT000007607592", True,
     "TC, 22 janvier 1921, Société commerciale de l'Ouest africain"),                             # 00706
    (r"\bseptfonds\b", "CETATEXT000007604199", True, "TC, 16 juin 1923, Septfonds"),                 # 00732
    (r"\bcouiteas\b", "CETATEXT000007637236", True, "CE, 30 novembre 1923, Couitéas"),               # 38284
    (r"\bbenjamin\b", "CETATEXT000007636694", False, "CE, 19 mai 1933, Benjamin"),                   # 17413
    (r"\bjamart\b", "CETATEXT000007637062", True, "CE, sect., 7 février 1936, Jamart"),              # 43321
    (r"\bla fleurette\b", "CETATEXT000007637158", True, "CE, ass., 14 janvier 1938, Société La Fleurette"),  # 51704
    (r"\baide et protection\b", "CETATEXT000007637161", True,
     "CE, ass., 13 mai 1938, Caisse primaire Aide et protection"),                                 # 57302
    (r"\blamotte\b", "CETATEXT000007636577", False, "CE, ass., 17 février 1950, Dame Lamotte"),      # 86949
    (r"\bdehaene\b", "CETATEXT000007636579", True, "CE, ass., 7 juillet 1950, Dehaene"),             # 01645
    (r"\bbarel\b", "CETATEXT000007637425", True, "CE, ass., 28 mai 1954, Barel"),                    # 28238
    (r"\bbertin\b", "CETATEXT000007636583", False, "CE, sect., 20 avril 1956, Époux Bertin"),         # 98637
    (r"\bsociete le beton\b", "CETATEXT000007636499", True, "CE, sect., 19 octobre 1956, Société Le Béton"),  # 20180
    (r"\barret canal\b|\bcanal,? robin\b", "CETATEXT000007636272", True, "CE, ass., 19 octobre 1962, Canal"),  # 58502
    (r"\bfabricants de semoules\b", "CETATEXT000007633957", True,
     "CE, sect., 1er mars 1968, Syndicat général des fabricants de semoules"),                     # 62814
    (r"\bville nouvelle[- ]est\b", "CETATEXT000007643558", True, "CE, ass., 28 mai 1971, Ville Nouvelle Est"),  # 78825
    (r"\bgisti\b", "CETATEXT000007666513", False, "CE, ass., 8 décembre 1978, GISTI"),               # 10097
    (r"\bcohn[- ]bendit\b", "CETATEXT000007666522", True, "CE, ass., 22 décembre 1978, Cohn-Bendit"),  # 11604
    (r"\balitalia\b", "CETATEXT000007754163", True, "CE, ass., 3 février 1989, Alitalia"),           # 74052
    (r"\bnicolo\b", "CETATEXT000007742504", True, "CE, ass., 20 octobre 1989, Nicolo"),              # 108243
    (r"\bepoux v\b", "CETATEXT000007813790", False, "CE, ass., 10 avril 1992, Époux V."),             # 79027
    (r"\bhardouin\b", "CETATEXT000007869052", False, "CE, ass., 17 février 1995, Hardouin"),         # 107766
    (r"\bhardouin et marie\b|\barret marie\b", "CETATEXT000007840249", False,
     "CE, ass., 17 février 1995, Marie"),                                                          # 97754
    (r"\bmorsang\b", "CETATEXT000007877723", True, "CE, ass., 27 octobre 1995, Commune de Morsang-sur-Orge"),  # 136727
    (r"\bkone\b", "CETATEXT000007939580", False, "CE, ass., 3 juillet 1996, Koné"),                  # 169219
    (r"\bsarran\b", "CETATEXT000008008495", True, "CE, ass., 30 octobre 1998, Sarran"),              # 200286
    (r"\bternon\b", "CETATEXT000008072768", True, "CE, ass., 26 octobre 2001, Ternon"),              # 197018
    (r"\bkpmg\b", "CETATEXT000008241143", True, "CE, ass., 24 mars 2006, Société KPMG"),             # 288460
    (r"\barcelor\b", "CETATEXT000018259414", True, "CE, ass., 8 février 2007, Arcelor"),             # 287110
    (r"\bville d'aix(?:-en-provence)?\b", "CETATEXT000032698859", False,
     "CE, sect., 6 avril 2007, Commune d'Aix-en-Provence"),                                        # 284736
    (r"\btropic travaux\b", "CETATEXT000018744539", True, "CE, ass., 16 juillet 2007, Tropic Travaux"),  # 291545
    (r"\bperreux\b", "CETATEXT000021219388", False, "CE, ass., 30 octobre 2009, Dame Perreux"),      # 298348
    (r"\bdanthony\b", "CETATEXT000025041089", True, "CE, ass., 23 décembre 2011, Danthony"),         # 335033
    (r"\btarn[- ]et[- ]garonne\b", "CETATEXT000028823786", False,
     "CE, ass., 4 avril 2014, Département de Tarn-et-Garonne"),                                    # 358994
)
NOMS_ADMINISTRATIFS: dict[str, str] = {d: nom for _, d, _, nom in GRANDS_ARRETS_ADMINISTRATIFS}

_CONTEXTE = re.compile(r"\barrets?\b|\bjurisprudence\b|\bcassation\b|\bjuge\b|\bdecide\b"
                       r"|\bconseil d'etat\b|\btribunal des conflits\b")
_MOTIFS = tuple((re.compile(m), pv, seul) for m, pv, seul in GRANDS_ARRETS)
_MOTIFS_ADMIN = tuple((re.compile(m), d, seul) for m, d, seul, _ in GRANDS_ARRETS_ADMINISTRATIFS)


def pourvois_cites(texte: str) -> tuple[str, ...]:
    """Numeros de pourvoi (« 89-15.231 ») des grands arrets nommes dans la question."""
    return tuple(_cites(texte, _MOTIFS))


def _cites(texte: str, motifs) -> list[str]:
    t = sans_accents(texte).lower()
    contexte = bool(_CONTEXTE.search(t))
    out: list[str] = []
    for motif, refs, seul in motifs:
        if (seul or contexte) and motif.search(t):
            out += [r for r in ((refs,) if isinstance(refs, str) else refs) if r not in out]
    return out


def decisions_administratives_citees(texte: str) -> tuple[str, ...]:
    """Identifiants JADE (« CETATEXT000007605886 ») des grands arrets administratifs nommes dans le texte."""
    return tuple(_cites(texte, _MOTIFS_ADMIN))


def nom_dans(ref: str, texte: str) -> bool:
    """Le nom d'usage du grand arret (pourvoi ou identifiant JADE) figure-t-il dans ce texte ? (B6)"""
    t = sans_accents(texte).lower()
    return any(motif.search(t) for motif, refs, _ in (*_MOTIFS, *_MOTIFS_ADMIN)
               if ref == refs or (not isinstance(refs, str) and ref in refs))
