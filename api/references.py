"""Reperage des references juridiques dans un texte (question ou reponse generee).

Sert a deux choses :
  - dans la question : aller chercher directement l'article / la decision cites ;
  - dans la reponse : verifier que chaque numero cite existe bien dans les sources fournies
    (le modele ne doit jamais inventer un numero d'article ou de decision).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from api.textes import codes_cites, sans_accents

_NUM = r"(?:[LRDA]\.?\s?)?\d+(?:-\d+)*(?:\s(?:bis|ter|quater))?"
_ARTICLES_RE = re.compile(
    rf"\b(?:art(?:icle)?s?\.?)\s+({_NUM}(?:\s*(?:,|et|à|ou)\s*{_NUM})*)",
    re.IGNORECASE,
)
_NUM_RE = re.compile(_NUM, re.IGNORECASE)
_ARTICLE_PREMIER_RE = re.compile(r"\barticle\s+(?:premier|1er)\b", re.IGNORECASE)
_DECISION_CC_RE = re.compile(r"\b(\d{2,4}-\d{1,4})\s*(QPC|DC)\b", re.IGNORECASE)
_POURVOI_RE = re.compile(r"\b(\d{2})[-.](\d{2})\.?(\d{3})\b")


@dataclass(frozen=True)
class References:
    articles: tuple[str, ...]
    decisions_cc: tuple[str, ...]   # "2023-1075 QPC"
    pourvois: tuple[str, ...]       # "21-86.418"
    constitution: bool              # la question parle de la Constitution
    codes: tuple[str, ...] = ()     # codes nommes ("code_penal"...)

    @property
    def vide(self) -> bool:
        return not (self.articles or self.decisions_cc or self.pourvois)


def _norm_num(n: str) -> str:
    return re.sub(r"\s+", " ", n.replace(".", "").strip()).upper().replace("L ", "L").replace("R ", "R")


def extraire(texte: str) -> References:
    articles: list[str] = ["1"] if _ARTICLE_PREMIER_RE.search(texte) else []
    for m in _ARTICLES_RE.finditer(texte):
        for n in _NUM_RE.findall(m.group(1)):
            n = _norm_num(n)
            if n not in articles:
                articles.append(n)
    decisions = []
    for m in _DECISION_CC_RE.finditer(texte):
        d = f"{m.group(1)} {m.group(2).upper()}"
        if d not in decisions:
            decisions.append(d)
    pourvois = []
    for m in _POURVOI_RE.finditer(texte):
        p = f"{m.group(1)}-{m.group(2)}.{m.group(3)}"
        if p not in pourvois:
            pourvois.append(p)
    return References(tuple(articles), tuple(decisions), tuple(pourvois), "constitution" in sans_accents(texte),
                      codes_cites(texte))


def _motif(n: str) -> str:
    """'L2223-1' doit aussi reconnaitre 'L. 2223-1' et 'L 2223-1'."""
    m = re.match(r"^([LRDA])(\d.*)$", n)
    return rf"{m.group(1)}\.?\s?{re.escape(m.group(2))}" if m else re.escape(n)


def _mot(n: str, texte: str) -> bool:
    return re.search(rf"(?<![\w-]){_motif(n)}(?![\w-]|\.\d)", texte, re.IGNORECASE) is not None


def reference_couverte(ref_type: str, valeur: str, passages: list[dict]) -> bool:
    """La reference apparait-elle dans au moins un des passages (numero, en-tete ou texte) ?"""
    for p in passages:
        if ref_type == "article":
            if _norm_num(p.get("numero") or "") == valeur:
                return True
            if _mot(valeur, p.get("texte", "")) or _mot(valeur, p.get("entete", "")):
                return True
        elif ref_type == "decision":
            num, nature = valeur.split()
            meta = p.get("meta") or {}
            if meta.get("numero") == num and meta.get("nature") == nature:
                return True
            if _mot(num, p.get("texte", "")) or _mot(num, p.get("entete", "")):
                return True
        elif ref_type == "pourvoi":
            meta = p.get("meta") or {}
            compact = valeur.replace(".", "")
            if compact in (meta.get("numeros_pourvoi") or []) or valeur in p.get("entete", ""):
                return True
            if valeur in p.get("texte", ""):
                return True
    return False


def references_non_couvertes(texte: str, passages: list[dict]) -> list[str]:
    refs = extraire(texte)
    manquantes = [f"article {a}" for a in refs.articles if not reference_couverte("article", a, passages)]
    manquantes += [d for d in refs.decisions_cc if not reference_couverte("decision", d, passages)]
    manquantes += [f"pourvoi {p}" for p in refs.pourvois if not reference_couverte("pourvoi", p, passages)]
    return manquantes
