"""Reperage des references juridiques dans un texte (question ou reponse generee).

Sert a deux choses :
  - dans la question : aller chercher directement l'article / la decision cites ;
  - dans la reponse : verifier que chaque numero cite existe bien dans les sources fournies
    (le modele ne doit jamais inventer un numero d'article ou de decision).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from api.grands_arrets import NOMS_ADMINISTRATIFS, decisions_administratives_citees, nom_dans, pourvois_cites
from api.textes import codes_cites, lois_citees, sans_accents

# Prefixe L, R, D, A ou LO (lois organiques), avec ou sans asterisque (R*, D* : decrets en Conseil d'Etat ou en
# conseil des ministres) ; suffixe bis, ter... (audit du 2026-11-18, B2 et B3).
_SUFFIXES = "bis|ter|quater|quinquies|sexies|septies|octies|nonies|decies"
_NUM = rf"(?:L\.?\s?O\.?\s?|[LRDA]\.?\s?\*?\.?\s?)?\d+(?:-\d+)*(?:\s(?:{_SUFFIXES})\b)?"
_ARTICLES_RE = re.compile(
    rf"\b(?:art(?:icle)?s?\.?)\s+({_NUM}(?:\s*(?:,|et|à|ou)\s*{_NUM})*)",
    re.IGNORECASE,
)
_NUM_RE = re.compile(_NUM, re.IGNORECASE)
_ARTICLE_PREMIER_RE = re.compile(r"\barticle\s+(?:premier|1er)\b", re.IGNORECASE)
# « 91-166 L » (nature reglementaire, art. 37) : L majuscule seul, pas « 2005-205 l'article » (B9).
_DECISION_CC_RE = re.compile(r"\b(\d{2,4}-\d{1,4})\s*(QPC|DC|(?-i:L)(?!['’\w]))", re.IGNORECASE)
_POURVOI_RE = re.compile(r"\b(\d{2})[-.](\d{2})\.?(\d{3})\b")


@dataclass(frozen=True)
class References:
    articles: tuple[str, ...]
    decisions_cc: tuple[str, ...]   # "2023-1075 QPC"
    pourvois: tuple[str, ...]       # "21-86.418"
    constitution: bool              # la question parle de la Constitution
    codes: tuple[str, ...] = ()     # codes nommes ("code_penal"...)
    lois: tuple[frozenset[str], ...] = ()  # lois / ordonnances citees, sous forme de cles (voir api.textes)
    decisions_admin: tuple[str, ...] = ()   # grands arrets administratifs nommes, identifiant JADE (CETATEXT...)

    @property
    def vide(self) -> bool:
        return not (self.articles or self.decisions_cc or self.pourvois or self.decisions_admin)


def _norm_num(n: str) -> str:
    """Forme de comparaison : « L. 2223-1 » -> L2223-1, « R.* 421-1 » -> R421-1 (asterisque ignoree, voir
    variantes), « L.O. 119 » -> LO119, « D45-2-1 BIS » -> D45-2-1 bis (l'index ecrit les suffixes en minuscules)."""
    n = re.sub(r"\s+", " ", n.replace(".", "").replace("*", "").strip()).lower()
    m = re.match(r"^(l ?o|[lrda]) ?(?=\d)", n)
    return m.group(1).replace(" ", "").upper() + n[m.end():] if m else n


def variantes(num: str) -> tuple[str, ...]:
    """Numeros a chercher dans l'index pour un numero normalise : R421-1 n'y existe souvent que sous la forme
    R*421-1 (1 058 articles en vigueur, ex. code de l'urbanisme)."""
    m = re.match(r"^([RD])(\d.*)$", num)
    return (num, f"{m.group(1)}*{m.group(2)}") if m else (num,)


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
    # Grand arret nomme (« l'arret Blieck ») : son pourvoi, que le sommaire ne relie jamais au nom (D90).
    pourvois += [p for p in pourvois_cites(texte) if p not in pourvois]
    return References(tuple(articles), tuple(decisions), tuple(pourvois), "constitution" in sans_accents(texte),
                      codes_cites(texte), lois_citees(texte), decisions_administratives_citees(texte))


def _motif(n: str) -> str:
    """'L2223-1' doit aussi reconnaitre 'L. 2223-1' et 'L 2223-1' ; 'R421-1' aussi 'R*421-1', 'LO119' 'L.O. 119'."""
    m = re.match(r"^(LO|[LRDA])(\d.*)$", n)
    if not m:
        return re.escape(n)
    prefixe = r"L\.?\s?O" if m.group(1) == "LO" else m.group(1)
    return rf"{prefixe}\.?\s?\*?\.?\s?{re.escape(m.group(2))}"


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
        elif ref_type == "decision_admin":
            if (p.get("meta") or {}).get("id_dila") == valeur:
                return True
        # Grand arret designe par son nom dans un extrait (cours depose, autre decision) : la citation est
        # couverte, meme sans son numero (audit du 2026-11-18, B6).
        if ref_type in ("pourvoi", "decision_admin") and (nom_dans(valeur, p.get("texte", ""))
                                                          or nom_dans(valeur, p.get("entete", ""))):
            return True
    return False


def references_non_couvertes(texte: str, passages: list[dict]) -> list[str]:
    refs = extraire(texte)
    manquantes = [f"article {a}" for a in refs.articles if not reference_couverte("article", a, passages)]
    manquantes += [d for d in refs.decisions_cc if not reference_couverte("decision", d, passages)]
    manquantes += [f"pourvoi {p}" for p in refs.pourvois if not reference_couverte("pourvoi", p, passages)]
    manquantes += [NOMS_ADMINISTRATIFS[d] for d in refs.decisions_admin
                   if not reference_couverte("decision_admin", d, passages)]
    return manquantes
