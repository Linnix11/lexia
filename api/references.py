"""Reperage des references juridiques dans un texte (question ou reponse generee).

Sert a deux choses :
  - dans la question : aller chercher directement l'article / la decision cites ;
  - dans la reponse : verifier que chaque numero cite existe bien dans les sources fournies
    (le modele ne doit jamais inventer un numero d'article ou de decision).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from api.grands_arrets import NOMS_ADMINISTRATIFS, decisions_administratives_citees, nom_dans, pourvois_cites
from api.textes import SOURCES_TEXTES, TEXTES, codes_cites, lois_citees, sans_accents

# Prefixe L, R, D, A ou LO (lois organiques), avec ou sans asterisque (R*, D* : decrets en Conseil d'Etat ou en
# conseil des ministres) ; suffixe bis, ter... (audit du 2026-11-18, B2 et B3).
_SUFFIXES = "bis|ter|quater|quinquies|sexies|septies|octies|nonies|decies"
_NUM = rf"(?:L\.?\s?O\.?\s?|[LRDA]\.?\s?\*?\.?\s?)?\d+(?:-\d+)*(?:\s(?:{_SUFFIXES})\b)?"
# « articles 8 (1er alinéa), 11, 12, 16 » (Constitution, art. 19) : une precision entre parentheses ne coupe pas la
# liste ; elle est retiree avant de lire les numeros.
_PRECISION = r"(?:\s*\([^()]{0,40}\))?"
_ARTICLES_RE = re.compile(
    rf"\b(?:art(?:icle)?s?\.?)\s+({_NUM}{_PRECISION}(?:\s*(?:,|et|à|ou)\s*{_NUM}{_PRECISION})*)",
    re.IGNORECASE,
)
_PRECISION_RE = re.compile(r"\([^()]*\)")
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
    if n.endswith("1er") and not n[-4:-3].isdigit():
        n = n[:-2]   # « 1er » des lois (SRC-8)
    m = re.match(r"^(l ?o|[lrda]) ?(?=\d)", n)
    return m.group(1).replace(" ", "").upper() + n[m.end():] if m else n


def variantes(num: str) -> tuple[str, ...]:
    """Numeros a chercher dans l'index pour un numero normalise : R421-1 n'y existe souvent que sous la forme
    R*421-1 (1 058 articles en vigueur, ex. code de l'urbanisme), parfois « R 1424-59 » (21 articles du CGCT et
    du code de l'environnement) ; l'article 1 parfois « 1er » (lois, SRC-8)."""
    if num == "1":
        return ("1", "1er")
    m = re.match(r"^(LO|[LRDA])(\d.*)$", num)
    if not m:
        return (num,)
    out = (num, f"{m.group(1)} {m.group(2)}")
    return out + ((f"{m.group(1)}*{m.group(2)}",) if m.group(1) in "RD" else ())


def extraire(texte: str) -> References:
    articles: list[str] = ["1"] if _ARTICLE_PREMIER_RE.search(texte) else []
    for m in _ARTICLES_RE.finditer(texte):
        for n in _NUM_RE.findall(_PRECISION_RE.sub(" ", m.group(1))):
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


# Texte nomme juste apres un numero d'article : « article 1240 du Code civil », « art. 1242, al. 4, C. civ. »,
# « article 1er de la Constitution », « article 267 TFUE ». Lu sur le texte sans accents.
_LIAISON = r"(?:er\b)?\s*,?\s*(?:(?:alinea|al\.)\s*\d+(?:er)?\s*,?\s*)?(?:du|de la|de l'|des|de|d')?\s*"
_RATTACHEMENTS = [(re.compile(_LIAISON + rf"(?:{m})(?!\w)"), t.source_id) for t in TEXTES for m in t.motifs]
# Autre texte nomme (« article 1er de la loi du 29 juillet 1881 », « du meme code ») : marque "" ; l'article ne
# doit alors pas venir d'un code nomme ailleurs dans la phrase.
_AUTRE_TEXTE = re.compile(_LIAISON + r"(?:lois?|ordonnances?|decrets?|conventions?|traites?|reglements?|directives?"
                          r"|accords?|protocoles?|arretes?|meme|present|presente)\b")


def _texte_rattache(suite: str) -> str | None:
    """source_id du texte nomme au debut de `suite`, "" pour un autre texte, None si aucun."""
    suite = sans_accents(suite[:120])
    return next((src for r, src in _RATTACHEMENTS if r.match(suite)), "" if _AUTRE_TEXTE.match(suite) else None)


@lru_cache(maxsize=4096)
def articles_cites(texte: str) -> tuple[tuple[str, str | None], ...]:
    """Numeros cites COMME articles (« article 9 », « art. 1240 », « articles 1240 et 1241 »), chacun avec le texte
    nomme juste apres lui (None sinon). Un nombre isole (« loi du 9 juillet 1991 », « 16 octobre ») n'en est pas un :
    le controle des citations l'acceptait comme « article 9 » (audit du 2026-11-19, SRC-2)."""
    out: list[tuple[str, str | None]] = []
    for m in _ARTICLES_RE.finditer(texte):
        code = _texte_rattache(texte[m.end():])
        out += [(_norm_num(n), code) for n in _NUM_RE.findall(_PRECISION_RE.sub(" ", m.group(1)))]
    out += [("1", _texte_rattache(texte[m.end():])) for m in _ARTICLE_PREMIER_RE.finditer(texte)]
    return tuple(dict.fromkeys(out))


def citations_d_articles(texte: str) -> list[tuple[int, tuple[str, ...], str | None]]:
    """(fin de la citation, numeros, texte nomme juste apres) pour chaque « article(s) N » du texte, dans l'ordre :
    la position sert a ecrire une precision juste apres la citation (api/concordance.py, annoter)."""
    return [(m.end(), tuple(dict.fromkeys(_norm_num(n) for n in _NUM_RE.findall(_PRECISION_RE.sub(" ", m.group(1))))),
             _texte_rattache(texte[m.end():])) for m in _ARTICLES_RE.finditer(texte)]


def _motif(n: str) -> str:
    """'L2223-1' doit aussi reconnaitre 'L. 2223-1' et 'L 2223-1' ; 'R421-1' aussi 'R*421-1', 'LO119' 'L.O. 119'."""
    m = re.match(r"^(LO|[LRDA])(\d.*)$", n)
    if not m:
        return re.escape(n)
    prefixe = r"L\.?\s?O" if m.group(1) == "LO" else m.group(1)
    return rf"{prefixe}\.?\s?\*?\.?\s?{re.escape(m.group(2))}"


def _mot(n: str, texte: str) -> bool:
    return re.search(rf"(?<![\w-]){_motif(n)}(?![\w-]|\.\d)", texte, re.IGNORECASE) is not None


def _article_couvert(valeur: str, codes: frozenset[str], passages: list[dict]) -> bool:
    """L'article est-il dans un extrait, et dans l'un des `codes` quand la reponse en nomme (vide : tout texte) ?

    Couvert par le numero de l'extrait, ou par une citation « article N » dans son texte ou son en-tete. Une
    citation sans texte nomme renvoie au texte de l'extrait lui-meme (article d'un code, d'une loi) ; dans une
    decision ou un cours, le texte vise reste inconnu et la citation est acceptee."""
    for p in passages:
        src = p.get("source_id") or ""
        if _norm_num(p.get("numero") or "") == valeur and (not codes or src in codes):
            return True
        propre = src if src in SOURCES_TEXTES else None
        for champ in (p.get("texte") or "", p.get("entete") or ""):
            for num, code in articles_cites(champ):
                code = propre if code is None else code
                if num == valeur and (not codes or code is None or code in codes):
                    return True
    return False


def reference_couverte(ref_type: str, valeur: str, passages: list[dict],
                       codes: frozenset[str] = frozenset()) -> bool:
    """La reference apparait-elle dans au moins un des passages (numero, en-tete ou texte) ?
    codes : pour un article, textes ou il doit se trouver (ceux que la reponse nomme)."""
    if ref_type == "article":
        return _article_couvert(valeur, codes, passages)
    for p in passages:
        if ref_type == "decision":
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
    rattaches = articles_cites(texte)
    # Article cite sans texte juste apres lui (« le Code civil prevoit, a son article 1240 ») : il doit venir d'un
    # des codes que la phrase nomme, s'il y en a (SRC-2).
    nommes = frozenset(codes_cites(texte))
    manquantes = []
    for a in refs.articles:
        lies = {c for n, c in rattaches if n == a}
        if (any(not reference_couverte("article", a, passages, frozenset({c})) for c in lies if c)
                or ("" in lies and not reference_couverte("article", a, passages))
                or ((None in lies or not lies) and not reference_couverte("article", a, passages, nommes))):
            manquantes.append(f"article {a}")
    manquantes += [d for d in refs.decisions_cc if not reference_couverte("decision", d, passages)]
    manquantes += [f"pourvoi {p}" for p in refs.pourvois if not reference_couverte("pourvoi", p, passages)]
    manquantes += [NOMS_ADMINISTRATIFS[d] for d in refs.decisions_admin
                   if not reference_couverte("decision_admin", d, passages)]
    return manquantes
