"""Interface commune des moteurs de recherche et fonctions partagees."""

from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass, field
from typing import Protocol

from api.textes import SOURCES_A_PART, SOURCES_TEXTES  # sources primaires, servies en premier  # noqa: F401

RRF_K = 60
SOURCE_LOIS = "lois"
MAX_PAR_DOCUMENT = 1  # evite qu'une seule decision occupe tous les resultats
# En dessous de cette part de passages vectorises, la recherche vectorielle biaiserait les
# resultats vers le sous-ensemble deja calcule : on reste en lexical pour ce groupe de sources.
SEUIL_COUVERTURE = 0.9
N_RECLASSEMENT = 10  # candidats relus par le modele de reclassement, par groupe de sources (D47)
# Articles de principe (lexique) proches de la question par le sens, ajoutes a la fenetre du reclassement
# quand le lexique ne reconnait aucune notion : un cas pratique raconte sans vocabulaire juridique
# ne les faisait jamais remonter. Gardes seulement si le reclassement les juge pertinents (D73).
N_PRINCIPES = 4
SEUIL_PRINCIPE = 0.10


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


def ajouter_duree(durees: dict[str, float] | None, etape: str, debut: float) -> None:
    """Ajoute a durees[etape] les millisecondes ecoulees depuis debut (time.perf_counter)."""
    if durees is not None:
        durees[etape] = durees.get(etape, 0.0) + (time.perf_counter() - debut) * 1000


class ReclasseurChronometre:
    """Reclasseur dont la duree (attente d'une place comprise, api/rerank.py) s'ajoute a durees["reclassement"]."""

    def __init__(self, reclasseur: Reclasseur, durees: dict[str, float]):
        self._reclasseur, self._durees = reclasseur, durees
        self.model = getattr(reclasseur, "model", "")

    def reordonner(self, question: str, hits: list[Hit]) -> list[Hit]:
        debut = time.perf_counter()
        try:
            return self._reclasseur.reordonner(question, hits)
        finally:
            ajouter_duree(self._durees, "reclassement", debut)


class Retriever(Protocol):
    mode: str

    def search(self, question: str, *, sources: tuple[str, ...] | None, k: int,
               query_vector: list[float] | None = None, complement: Complement | None = None,
               reclasseur: Reclasseur | None = None, durees: dict[str, float] | None = None) -> list[Hit]: ...

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
    """Separe les sources autorisees en (textes officiels, jurisprudence). Les fiches recuperees (SOURCES_A_PART)
    ne sont dans aucun des deux, meme demandees : les reponses ne reposent que sur des sources officielles."""
    autorisees = tuple(s for s in (sources or toutes) if s not in SOURCES_A_PART)
    textes = tuple(s for s in autorisees if s in SOURCES_TEXTES)
    juris = tuple(s for s in autorisees if s not in SOURCES_TEXTES)
    return textes, juris


def assembler(refs: list["Hit"], textes: list["Hit"], juris: list["Hit"], k: int) -> list["Hit"]:
    """References citees d'abord, puis textes (environ la moitie), puis jurisprudence.

    Une place au moins reste a la jurisprudence quand il y en a : une question qui cite plusieurs
    articles (« commentez l'arret au regard des articles 1240 et suivants ») recevait sinon des
    textes seulement, et le commentaire d'arret n'avait aucun arret a commenter. Le total est
    plafonne a k : sans cela, une question citant 159 articles envoyait 159 extraits au modele (D71).
    """
    place_textes = k - 1 if juris else k
    out = list(refs[:place_textes])
    vus = {h.passage["id"] for h in out}

    def ajouter(liste: list["Hit"], limite: int) -> None:
        for h in liste:
            if len(out) >= limite:
                return
            if h.passage["id"] not in vus:
                vus.add(h.passage["id"])
                out.append(h)

    ajouter(textes, min(len(out) + (k + 1) // 2, place_textes))
    ajouter(juris, k)
    ajouter(textes, k)
    return out[:k]


def construire_groupe(classements: dict[str, list[tuple[str, dict]]], k: int, *,
                      question: str = "", suggestions: list[dict] | None = None,
                      reclasseur: Reclasseur | None = None,
                      principes: list[dict] | None = None) -> list[Hit]:
    """Fusionne des classements (RRF), reclasse eventuellement, place les suggestions en tete.

    classements : nom -> [(id, passage)], ex. {"lexical": ..., "vecteur": ..., "lexical_reformulation": ...}
    principes : articles de principe candidats, relus par le reclassement en plus de sa fenetre (D73)
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
        # seuls les articles absents de la fenetre y sont ajoutes, et seuls ceux-la peuvent etre ecartes :
        # un article deja trouve par la recherche garde sa place (tr-13, art. 51 de la Charte des Nations unies)
        fenetre = {h.passage["id"] for h in hits[:N_RECLASSEMENT]}
        ajouts = [p for p in principes or [] if p["id"] not in fenetre]
        ids_a = {p["id"] for p in ajouts}
        hits = [h for h in hits if h.passage["id"] not in ids_a]
        hits = reclasseur.reordonner(question, [Hit(p, 0.0, {"principe"}) for p in ajouts] + hits[:N_RECLASSEMENT]) \
            + hits[N_RECLASSEMENT:]
        hits = [h for h in hits if h.passage["id"] not in ids_a or h.score >= SEUIL_PRINCIPE]
    # Lois et ordonnances non codifiees apres les codes et la Constitution : des milliers d'« article 5 » ou
    # « article 11 » de lois diverses evincaient les articles de principe (backtest du 2026-11-12). Une loi
    # citee dans la question passe toujours en tete (recherche par reference, hors de ce groupe).
    hits = [h for h in hits if h.passage.get("source_id") != SOURCE_LOIS] + \
        [h for h in hits if h.passage.get("source_id") == SOURCE_LOIS]
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
    """Document d'un passage, pour en limiter le nombre par reponse. Un article est son propre document : les
    11 passages de la Charte de l'environnement partagent un id_legi, un seul passait (audit SRC-7)."""
    if p.get("type") == "article":
        return p["id"]
    meta = p.get("meta") or {}   # id_source : decision recente hors archive DILA (D113)
    return meta.get("id_dila") or meta.get("id_legi") or meta.get("id_source") or p["id"]
