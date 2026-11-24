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

Grands arrets par notion (D124) : `registry/grands_arrets.yaml` liste 122 grands arrets des matieres de licence,
relies a des notions (fait des choses, exces de pouvoir, primaute du droit de l'Union...). Une question qui porte sur
une notion, ou qui nomme l'arret, recoit ses grands arrets parmi les extraits, apres ceux de la recherche : la
decision de l'index quand elle y est (sommaire officiel, considerant de principe), sinon une fiche redigee par
Lexia (source `fiches_grands_arrets`, jamais presentee comme une decision officielle). Le modele recoit une note
qui demande de les citer avec leur date et de ne jamais presenter un arret abandonne comme le droit positif.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from functools import lru_cache

import yaml

from api import lexique
from api.config import ROOT
from api.textes import sans_accents

FICHIER = ROOT / "registry" / "grands_arrets.yaml"
SOURCE_FICHES = "fiches_grands_arrets"   # registry/sources.yaml, statut fiche_lexia
MAX_PAR_QUESTION = 3                     # grands arrets ajoutes aux extraits d'une question
STATUTS = {
    "actuel": "toujours appliqué",
    "consacre": "solution reprise par un texte",
    "nuance": "solution corrigée ou limitée depuis",
    "abandonne": "ABANDONNÉ : n'est plus le droit positif",
}
AVERTISSEMENT_FICHE = ("Fiche rédigée par Lexia : résumé pédagogique non officiel d'un grand arrêt absent du corpus, "
                       "à relire par un enseignant. Ce n'est pas le texte de la décision.")

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

# « 2031-9999 QPC », « 71-44 DC », « 89-15.231 » : la question vise une decision precise
_NUMERO_DECISION = re.compile(r"\b\d{2,4}-\d{1,4}(?:/\d{1,4})?\s*(?:qpc|dc)\b|\b\d{2}-\d{2}\.\d{3}\b")
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


# --- Grands arrets par notion (D124) ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Arret:
    id: str
    citation: str
    date: str
    statut: str
    portee: str
    matieres: tuple[str, ...]
    reference: str | None = None
    index: str | None = None        # passage de l'index qui porte la decision
    fiche: dict | None = None       # faits, question, solution, apport, portee (arret absent de l'index)
    motif: re.Pattern | None = None
    seul: bool = True


@dataclass(frozen=True)
class Notion:
    id: str
    libelle: str
    motifs: tuple[re.Pattern, ...]
    avec: re.Pattern | None
    sauf: re.Pattern | None
    arrets: tuple[str, ...]


@dataclass(frozen=True)
class Registre:
    version: str
    arrets: dict[str, Arret]
    notions: dict[str, Notion]


@lru_cache(maxsize=1)
def registre() -> Registre:
    brut = yaml.safe_load(FICHIER.read_text(encoding="utf-8"))
    arrets: dict[str, Arret] = {}
    for a in brut["arrets"]:
        nom = a.get("nom") or {}
        arrets[a["id"]] = Arret(
            id=a["id"], citation=a["citation"], date=str(a["date"]), statut=a["statut"], portee=a["portee"],
            matieres=tuple(a.get("matieres") or ()), reference=a.get("reference"), index=a.get("index"),
            fiche=a.get("fiche"), motif=re.compile(nom["motif"]) if nom.get("motif") else None,
            seul=bool(nom.get("seul", True)))
    notions = {n: Notion(n, v["libelle"], tuple(re.compile(m) for m in v["motifs"]),
                         re.compile(v["avec"]) if v.get("avec") else None,
                         re.compile(v["sauf"]) if v.get("sauf") else None, tuple(v["arrets"]))
               for n, v in brut["notions"].items()}
    return Registre(str(brut["version"]), arrets, notions)


def notions_de(texte: str) -> list[str]:
    """Notions dont parle la question, dans l'ordre du registre. Aucune quand la question cite un numero de
    decision ou de pourvoi : elle porte sur cette decision (une decision inventee doit mener a l'abstention, et
    non a des grands arrets voisins : piege-11)."""
    t = sans_accents(texte).lower()
    if _NUMERO_DECISION.search(t):
        return []
    # Cas pratique ou une chose cause le dommage (« le ballon frappe Lea ») sans les mots « fait des choses » :
    # meme detection que la note sur la garde (D119) ; un vehicule a moteur releve de la loi de 1985 (dossier
    # enseignant, question 13, 24/11).
    chose = lexique.chose_en_cause(texte) is not None and lexique.vehicule_en_cause(texte) is None
    return [n.id for n in registre().notions.values()
            if (any(m.search(t) for m in n.motifs) or (chose and n.id == "fait_des_choses"))
            and (n.avec is None or n.avec.search(t)) and (n.sauf is None or not n.sauf.search(t))]


def arrets_pour(texte: str) -> list[Arret]:
    """Grands arrets a joindre aux extraits : ceux que la question nomme, puis ceux de ses notions, pris a tour de
    role (le premier de chaque notion, puis le deuxieme...) : une notion large (contrat administratif) ne prend pas
    toutes les places d'une notion precise (recours des tiers contre le contrat)."""
    reg = registre()
    t = sans_accents(texte).lower()
    contexte = bool(_CONTEXTE.search(t))
    ids = [a.id for a in reg.arrets.values() if a.motif is not None and (a.seul or contexte) and a.motif.search(t)]
    listes = [reg.notions[n].arrets for n in notions_de(texte)]
    for rang in range(max(map(len, listes), default=0)):
        ids += [liste[rang] for liste in listes if rang < len(liste)]
    return [reg.arrets[i] for i in dict.fromkeys(ids)]


def passage_fiche(a: Arret) -> dict:
    """Fiche redigee par Lexia, sous la forme d'un passage (source a part, type « fiche »)."""
    f = a.fiche or {}
    texte = "\n".join([
        AVERTISSEMENT_FICHE,
        f"Faits : {f.get('faits', '')}",
        f"Question de droit : {f.get('question', '')}",
        f"Solution : {f.get('solution', '')}",
        f"Apport : {f.get('apport', '')}",
        f"Portée actuelle : {f.get('portee', '')}",
        f"Statut : {STATUTS[a.statut]}.",
    ])
    return {
        "id": f"{SOURCE_FICHES}:{a.id}",
        "source_id": SOURCE_FICHES,
        "type": "fiche",
        "numero": None,
        "titre": a.citation,
        "entete": f"Fiche Lexia (non officielle) : {a.citation}",
        "url": "",
        "version": f"Fiche rédigée par Lexia le {_date_fr(registre().version)}, à relire par un enseignant",
        "meta": {"date": a.date, "grand_arret": a.id, "reference": a.reference, "statut": a.statut},
        "texte": texte,
    }


def fiche(passage_id: str) -> dict | None:
    """Passage d'une fiche Lexia par son identifiant (« fiches_grands_arrets:jand-heur »), None sinon."""
    source, _, ident = passage_id.partition(":")
    a = registre().arrets.get(ident) if source == SOURCE_FICHES else None
    return passage_fiche(a) if a is not None and a.fiche else None


def marquer(p: dict, a: Arret, ajoute: bool) -> dict:
    """Copie du passage avec son grand arret (nom d'usage dans l'en-tete, statut pour la note au modele)."""
    p = copy.deepcopy(p)
    p["grand_arret"] = {"id": a.id, "citation": a.citation, "statut": a.statut, "portee": a.portee,
                        "ajoute": ajoute}
    if p["source_id"] != SOURCE_FICHES:
        p["entete"] = f"{p.get('entete') or p.get('titre') or p['id']} (grand arrêt : {a.citation})"
    return p


def ecarter_abandonnes(reponse: dict, passages: list[dict]) -> int:
    """Un element de droit positif (ou de la reponse directe) qui ne s'appuie que sur des grands arrets abandonnes
    n'est pas du droit positif : il passe dans l'explication (la reponse directe le perd). passages : extraits
    envoyes au modele. Renvoie le nombre d'elements deplaces ou retires."""
    abandonnes = {p["id"] for p in passages if (p.get("grand_arret") or {}).get("statut") == "abandonne"}
    if not abandonnes or reponse.get("statut") != "reponse":
        return 0
    seul = [e for e in reponse.get("droit_positif", []) if e["sources"] and set(e["sources"]) <= abandonnes]
    directe = [e for e in reponse.get("reponse_directe", []) if e["sources"] and set(e["sources"]) <= abandonnes]
    if seul:
        reponse["droit_positif"] = [e for e in reponse["droit_positif"] if e not in seul]
        reponse["explication"] = list(reponse.get("explication", [])) + seul
    if directe:
        reponse["reponse_directe"] = [e for e in reponse["reponse_directe"] if e not in directe]
    return len(seul) + len(directe)


def ecarter_fiches_seules(reponse: dict, passages: list[dict]) -> int:
    """Un element de droit positif qui ne s'appuie que sur des fiches Lexia passe dans l'explication : une fiche
    non officielle presente l'arret, elle ne fonde pas seule la regle actuelle (D128 ; gan-01 du 24/11 : la garde
    n'etait sourcee que par la fiche Franck). La reponse directe, resume de la reponse, n'est pas touchee."""
    fiches = {p["id"] for p in passages if p.get("source_id") == SOURCE_FICHES}
    if not fiches or reponse.get("statut") != "reponse":
        return 0
    seules = [e for e in reponse.get("droit_positif", []) if e["sources"] and set(e["sources"]) <= fiches]
    if seules:
        reponse["droit_positif"] = [e for e in reponse["droit_positif"] if e not in seules]
        reponse["explication"] = list(reponse.get("explication", [])) + seules
    return len(seules)


_DATE = re.compile(r"\b(\d{1,2}(?:er)? [a-z]+ \d{4})\b")


def _nomme(a: dict, texte: str) -> bool:
    """Le texte cite-t-il ce grand arret (sa date, ou le nom d'usage reconnu par le registre) ?"""
    t = sans_accents(texte).lower().replace("\u2019", "'")
    date = _DATE.search(sans_accents(a["citation"]).lower())
    if date and date.group(1) in t:
        return True
    arret = registre().arrets.get(a["id"])
    return bool(arret and arret.motif and arret.motif.search(t))


def nommer_grands_arrets(reponse: dict, passages: list[dict]) -> int:
    """Un element qui s'appuie sur un grand arret sans le nommer recoit sa citation entre parentheses : l'etudiant
    ne voyait le nom qu'en ouvrant la source (D128 ; gan-06 du 24/11 : Costa, Simmenthal et Jacques Vabre cites en
    source, jamais nommes). Renvoie le nombre d'elements completes."""
    grands = {p["id"]: p["grand_arret"] for p in passages if p.get("grand_arret")}
    if not grands or reponse.get("statut") != "reponse":
        return 0
    n = 0
    for cle in ("reponse_directe", "droit_positif", "explication"):
        for e in reponse.get(cle, []):
            manquants = [grands[s]["citation"] for s in e.get("sources", [])
                         if s in grands and not _nomme(grands[s], e["texte"])]
            if manquants:
                e["texte"] = f"{e['texte'].rstrip().rstrip('.')} ({' ; '.join(dict.fromkeys(manquants))})."
                n += 1
    return n


def note(passages: list[dict]) -> str:
    """Note au modele quand des grands arrets figurent parmi les extraits (S1, S2... dans l'ordre des passages)."""
    lignes = [f"- [S{i}] {p['grand_arret']['citation']} : {STATUTS[p['grand_arret']['statut']]}. "
              f"{p['grand_arret']['portee']}"
              for i, p in enumerate(passages, start=1) if p.get("grand_arret")]
    if not lignes:
        return ""
    return ("Note : les extraits contiennent des grands arrêts que l'étudiant doit connaître sur cette question :\n"
            + "\n".join(lignes) + "\n"
            "Quand ils éclairent la réponse, cite-les par leur juridiction, leur date et leur nom d'usage (par exemple "
            "« Cass., ch. réunies, 13 février 1930, Jand'heur »), avec l'extrait correspondant dans « sources ». Un "
            "arrêt ABANDONNÉ n'est jamais présenté comme le droit positif : dis qu'il a été abandonné et par quoi, "
            "dans l'explication. Une « Fiche Lexia » est un résumé non officiel : la règle actuelle s'énonce d'abord "
            "avec le texte (article, loi) ou la décision officielle fournis, la fiche sert à présenter l'arrêt.")


_MOIS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
         "novembre", "décembre")


def _date_fr(iso: str) -> str:
    a, m, j = iso.split("-")
    return f"{int(j)}{'er' if j == '01' else ''} {_MOIS[int(m) - 1]} {a}"


# --- Document de relecture (docs/relecture-enseignant/grands-arrets.md) ---------------------------------------

DOCUMENT = ROOT / "docs" / "relecture-enseignant" / "grands-arrets.md"
_STATUT_COURT = {"actuel": "actuel", "consacre": "consacré", "nuance": "nuancé", "abandonne": "abandonné"}
_MATIERES_ORDRE = ("droit_civil", "droit_des_contrats", "droit_des_biens", "droit_de_la_famille", "introduction_au_droit",
                   "droit_penal", "procedure_civile", "procedure_penale", "droit_administratif",
                   "contentieux_administratif", "droit_administratif_des_biens", "droit_constitutionnel",
                   "libertes_fondamentales", "droit_europeen")


def document() -> str:
    """Liste des grands arrets et fiches Lexia, pour la relecture par un enseignant (regeneree par
    `python -m api.grands_arrets` ; tests/test_grands_arrets_notions.py echoue si elle n'est plus a jour)."""
    from api.matieres import LIBELLES
    reg = registre()
    notions: dict[str, list[str]] = {}
    for n in reg.notions.values():
        for i in n.arrets:
            notions.setdefault(i, []).append(n.libelle)
    arrets = list(reg.arrets.values())
    fiches = [a for a in arrets if a.fiche]
    lignes = [
        "# Grands arrêts : liste et fiches Lexia (à relire par un enseignant)", "",
        f"Version du {_date_fr(reg.version)}, tirée de `registry/grands_arrets.yaml` (D124). {len(arrets)} arrêts, "
        f"dont {len(arrets) - len(fiches)} dont la décision est dans l'index de Lexia (sommaire officiel ou considérant "
        f"de principe) et {len(fiches)} absents de l'index, pour lesquels Lexia a rédigé une fiche.", "",
        "**À relire par un enseignant.** Les fiches sont écrites par Lexia, sans reprise d'un recueil de grands arrêts, "
        "d'une note d'arrêt ou d'un manuel. Elles sont montrées à l'étudiant comme « Fiche Lexia (non officielle) », "
        "jamais comme une décision. Pour chaque arrêt, merci de vérifier la date, la solution, le statut (toujours "
        "appliqué, consacré par un texte, nuancé, abandonné) et la portée actuelle.", "",
        "Statuts : actuel = toujours appliqué ; consacré = solution reprise par un texte ; nuancé = corrigée ou limitée "
        "depuis ; abandonné = n'est plus le droit positif (Lexia ne doit jamais le présenter comme tel).", "",
        "## 1. Liste des arrêts", "",
    ]
    for m in _MATIERES_ORDRE:
        du = [a for a in arrets if a.matieres and a.matieres[0] == m]
        if not du:
            continue
        lignes += [f"### {LIBELLES.get(m, m)}", "",
                   "| Arrêt | Juridiction et formation | Date | Numéro | Notions | Dans l'index | Statut |",
                   "|---|---|---|---|---|---|---|"]
        for a in du:
            brut = _brut(a.id)
            juridiction = brut["juridiction"] + (f", {brut['formation']}" if brut.get("formation") else "")
            index = "non : fiche Lexia" if a.fiche else f"oui (`{a.index}`)"
            lignes.append(f"| {a.citation} | {juridiction} | {a.date} | {a.reference or 'sans numéro'} | "
                          f"{', '.join(notions.get(a.id, []))} | {index} | {_STATUT_COURT[a.statut]} |")
        lignes.append("")
    lignes += ["## 2. Fiches Lexia (arrêts absents de l'index)", ""]
    for a in fiches:
        f = a.fiche
        lignes += [f"### {a.citation}", "", "*À relire par un enseignant.*", "",
                   f"- **Faits.** {f['faits']}", f"- **Question de droit.** {f['question']}",
                   f"- **Solution.** {f['solution']}", f"- **Apport.** {f['apport']}",
                   f"- **Portée actuelle.** {f['portee']}", f"- **Statut.** {_STATUT_COURT[a.statut]}", ""]
    lignes += ["## 3. Portée des arrêts présents dans l'index", "",
               "Phrase transmise au modèle avec la décision officielle.", ""]
    lignes += [f"- **{a.citation}** ({_STATUT_COURT[a.statut]}) : {a.portee}" for a in arrets if not a.fiche]
    return "\n".join(lignes) + "\n"


@lru_cache(maxsize=1)
def _bruts() -> dict[str, dict]:
    return {a["id"]: a for a in yaml.safe_load(FICHIER.read_text(encoding="utf-8"))["arrets"]}


def _brut(ident: str) -> dict:
    return _bruts()[ident]


if __name__ == "__main__":
    DOCUMENT.write_text(document(), encoding="utf-8")
    print(f"{DOCUMENT.relative_to(ROOT)} : {len(registre().arrets)} arrêts")
