"""Interface commune des moteurs de recherche et fonctions partagees."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Protocol

RRF_K = 60
MAX_PAR_DOCUMENT = 1  # evite qu'une seule decision occupe tous les resultats
SOURCES_TEXTES = ("constitution_1958", "code_civil")  # sources primaires, servies en premier
# En dessous de cette part de passages vectorises, la recherche vectorielle biaiserait les
# resultats vers le sous-ensemble deja calcule : on reste en lexical pour ce groupe de sources.
SEUIL_COUVERTURE = 0.9


@dataclass
class Hit:
    passage: dict
    score: float
    via: set[str] = field(default_factory=set)   # "reference", "lexical", "vecteur"


class Retriever(Protocol):
    mode: str

    def search(self, question: str, *, sources: tuple[str, ...] | None, k: int,
               query_vector: list[float] | None = None) -> list[Hit]: ...

    def get(self, passage_id: str) -> dict | None: ...

    def versions(self, source_id: str, numero: str) -> list[dict]: ...

    def couverture(self, sources: tuple[str, ...] | None) -> float:
        """Part des passages (en vigueur) de ces sources qui ont un embedding."""
        ...

    def stats(self) -> dict: ...


STOPWORDS = set("""
a afin ai aie aient alors au aucun aussi autre aux avec avoir bon c ca car ce ceci cela celle celles celui
ces cet cette ceux chaque ci comme comment d dans de des du donc dont elle elles en encore est et etc
eu faut il ils je l la le les leur leurs lui m ma mais me meme mes moi mon n ne ni nos notre
nous on ont ou par parce pas peu peut plus pour pourquoi qu quand que quel quelle quelles quels qui quoi
s sa sans se ses si son sont sous sur t ta te tes toi ton tous tout toute toutes tu un une vos votre vous
y est-ce explique expliquer expliquez moi dis donne donner fiche resume resumer peux pouvez definition
definir exemple exemples droit question cours aide aider dit dire article code civil alinea selon
""".split())


def sans_accents(texte: str) -> str:
    return unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode("ascii")


def termes(question: str, garder_accents: bool = False) -> list[str]:
    """Mots significatifs de la question, en minuscules.

    Par defaut : sans accents et sans pluriel simple (index SQLite, qui ignore les accents).
    garder_accents=True : mots tels quels, pour le stemmer francais de PostgreSQL.
    """
    out: list[str] = []
    for brut in re.findall(r"[\w]+", question.lower()):
        m = sans_accents(brut)
        if len(m) < 3 or m in STOPWORDS or m.isdigit() or not m.isalnum():
            continue
        if garder_accents:
            mot = brut
        else:
            mot = m[:-1] if len(m) > 4 and m.endswith(("s", "x")) else m
        if mot not in out:
            out.append(mot)
    return out[:24]


def paires(mots: list[str]) -> list[tuple[str, str]]:
    """Paires de termes consecutifs : servent a favoriser les passages ou ils sont proches."""
    return list(zip(mots, mots[1:]))


def groupes(sources: tuple[str, ...] | None, toutes: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Separe les sources autorisees en (textes officiels, jurisprudence)."""
    autorisees = sources or toutes
    textes = tuple(s for s in autorisees if s in SOURCES_TEXTES)
    juris = tuple(s for s in autorisees if s not in SOURCES_TEXTES)
    return textes, juris


def assembler(refs: list["Hit"], textes: list["Hit"], juris: list["Hit"], k: int) -> list["Hit"]:
    """References citees d'abord, puis textes (au moins la moitie si disponibles), puis jurisprudence."""
    out = list(refs)
    vus = {h.passage["id"] for h in out}

    def ajouter(liste: list["Hit"], limite: int) -> None:
        for h in liste:
            if len(out) >= limite:
                return
            if h.passage["id"] not in vus:
                vus.add(h.passage["id"])
                out.append(h)

    ajouter(textes, max(len(out), 0) + (k + 1) // 2)
    ajouter(juris, k)
    ajouter(textes, k)
    return out[:max(k, len(refs))]


def fusion_rrf(*classements: list[str]) -> dict[str, float]:
    scores: dict[str, float] = {}
    for classement in classements:
        for rang, pid in enumerate(classement):
            scores[pid] = scores.get(pid, 0.0) + 1.0 / (RRF_K + rang + 1)
    return scores


def diversifier(hits: list[Hit], k: int, cle_doc) -> list[Hit]:
    out: list[Hit] = []
    compte: dict[str, int] = {}
    for h in hits:
        doc = cle_doc(h.passage)
        if "reference" not in h.via and compte.get(doc, 0) >= MAX_PAR_DOCUMENT:
            continue
        compte[doc] = compte.get(doc, 0) + 1
        out.append(h)
        if len(out) >= k:
            break
    return out


def doc_de(p: dict) -> str:
    meta = p.get("meta") or {}
    return meta.get("id_dila") or meta.get("id_legi") or p["id"]
