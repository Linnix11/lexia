"""Interface commune des moteurs de recherche et fonctions partagees."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Protocol

from api.textes import SOURCES_TEXTES  # sources primaires, servies en premier  # noqa: F401

RRF_K = 60
MAX_PAR_DOCUMENT = 1  # evite qu'une seule decision occupe tous les resultats
# En dessous de cette part de passages vectorises, la recherche vectorielle biaiserait les
# resultats vers le sous-ensemble deja calcule : on reste en lexical pour ce groupe de sources.
SEUIL_COUVERTURE = 0.9
N_RECLASSEMENT = 30  # candidats relus par le modele de reclassement, par groupe de sources


def jeton_source(source_id: str) -> str:
    """Mot unique representant une source dans l'index plein texte (colonne « source »)."""
    return "src" + re.sub(r"[^a-z0-9]", "", source_id.lower())


@dataclass
class Hit:
    passage: dict
    score: float
    via: set[str] = field(default_factory=set)   # "reference", "suggestion", "lexical", "vecteur", "reclasse"


@dataclass
class Complement:
    """Informations ajoutees a la question avant la recherche (voir api/expansion.py)."""
    reformulation: str = ""
    vecteur_reformulation: list[float] | None = None
    # (source_id, numero) d'articles proposes par le modele : on n'en garde que le texte officiel du corpus
    suggestions: list[tuple[str, str]] = field(default_factory=list)


class Reclasseur(Protocol):
    model: str

    def reordonner(self, question: str, hits: list[Hit]) -> list[Hit]: ...


class Retriever(Protocol):
    mode: str

    def search(self, question: str, *, sources: tuple[str, ...] | None, k: int,
               query_vector: list[float] | None = None, complement: Complement | None = None,
               reclasseur: Reclasseur | None = None) -> list[Hit]: ...

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


def termes(question: str) -> list[str]:
    """Mots significatifs de la question, en minuscules, sans accents et sans pluriel simple
    (l'index SQLite ignore les accents)."""
    out: list[str] = []
    for brut in re.findall(r"[\w]+", question.lower()):
        m = sans_accents(brut)
        if len(m) < 3 or m in STOPWORDS or m.isdigit() or not m.isalnum():
            continue
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


def construire_groupe(classements: dict[str, list[tuple[str, dict]]], k: int, *,
                      question: str = "", suggestions: list[dict] | None = None,
                      reclasseur: Reclasseur | None = None) -> list[Hit]:
    """Fusionne des classements (RRF), reclasse eventuellement, place les suggestions en tete.

    classements : nom -> [(id, passage)], ex. {"lexical": ..., "vecteur": ..., "lexical_reformulation": ...}
    """
    par_id: dict[str, dict] = {}
    via: dict[str, set[str]] = {}
    for nom, liste in classements.items():
        famille = "vecteur" if nom.startswith("vecteur") else "lexical"
        for pid, p in liste:
            par_id.setdefault(pid, p)
            via.setdefault(pid, set()).add(famille)
    scores = fusion_rrf(*[[pid for pid, _ in liste] for liste in classements.values()])
    hits = [Hit(par_id[pid], sc, via[pid]) for pid, sc in sorted(scores.items(), key=lambda x: -x[1])]
    if reclasseur is not None and hits:
        hits = reclasseur.reordonner(question, hits[:N_RECLASSEMENT]) + hits[N_RECLASSEMENT:]
    if suggestions:
        ids = {p["id"] for p in suggestions}
        hits = [Hit(p, float("inf"), {"suggestion"}) for p in suggestions] + [h for h in hits if h.passage["id"] not in ids]
    return diversifier(hits, k, doc_de)


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
