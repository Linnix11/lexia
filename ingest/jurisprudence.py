"""Decoupage des decisions de justice en passages citables.

Regle : 1 passage = un ou plusieurs paragraphes (motifs) consecutifs, sans jamais couper
un paragraphe, jusqu'a ~CHUNK_CHARS caracteres. Le dispositif forme un passage a part.
Les visas (en-tete de procedure) ne sont pas indexes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

CHUNK_CHARS = 2000
PARA_MAX_CHARS = 6000      # au-dela, un paragraphe (souvent une loi citee) est scinde par lignes
HEADING_MAX_CHARS = 250

_NUM_RE = re.compile(r"^(\d+)\s*\.\s+\S")
_CONSIDERANT_RE = re.compile(r"^Consid[ée]rant\b", re.IGNORECASE)

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]


def date_fr(iso: str) -> str:
    """'2024-01-19' -> '19 janvier 2024' (renvoie la chaine telle quelle si format inattendu)."""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", iso or "")
    if not m:
        return iso
    jour = int(m.group(3))
    return f"{'1er' if jour == 1 else jour} {MOIS[int(m.group(2)) - 1]} {m.group(1)}"


@dataclass
class Paragraphe:
    numero: int
    lignes: list[str] = field(default_factory=list)

    @property
    def texte(self) -> str:
        return "\n".join(self.lignes)


@dataclass
class Morceau:
    type: str                 # "motifs" | "dispositif"
    paragraphes: list[Paragraphe]

    @property
    def plage(self) -> str:
        nums = [p.numero for p in self.paragraphes]
        # numero 0 = pas de numerotation officielle : on n'affiche pas de plage inventee
        if not nums or self.type == "dispositif" or 0 in nums:
            return ""
        return str(nums[0]) if nums[0] == nums[-1] else f"{nums[0]}-{nums[-1]}"

    @property
    def alineas(self) -> list[str]:
        return [p.texte for p in self.paragraphes]


def _est_intertitre(lines: list[str], i: int, is_start, max_suite: int = 3) -> bool:
    """Ligne courte suivie (eventuellement via d'autres lignes courtes) d'un debut de paragraphe."""
    if len(lines[i]) > HEADING_MAX_CHARS or lines[i].endswith((";", ":")):
        return False
    for j in range(i + 1, min(i + 1 + max_suite, len(lines))):
        if is_start(lines[j]):
            return True
        if len(lines[j]) > HEADING_MAX_CHARS:
            return False
    return False


def _split_paragraphs(lines: list[str], is_start) -> list[Paragraphe]:
    paras: list[Paragraphe] = []
    pending: list[str] = []  # intertitres a rattacher au paragraphe suivant
    for i, line in enumerate(lines):
        if is_start(line):
            paras.append(Paragraphe(numero=len(paras) + 1, lignes=pending + [line]))
            pending = []
            continue
        if _est_intertitre(lines, i, is_start) or not paras:
            pending.append(line)
        else:
            paras[-1].lignes.append(line)
    if pending and paras:
        paras[-1].lignes.extend(pending)
    return paras


def compact(line: str) -> str:
    """'D E C I D E :' -> 'DECIDE:' ; sert a reperer les intitules ecrits en lettres espacees."""
    return re.sub(r"\s+", "", line).upper()


def _scinder(p: Paragraphe, max_chars: int) -> list[Paragraphe]:
    """Scinde un paragraphe trop long par lignes ; les morceaux gardent le meme numero."""
    if len(p.texte) <= max_chars:
        return [p]
    out: list[Paragraphe] = []
    cur: list[str] = []
    for line in p.lignes:
        while len(line) > max_chars:  # ligne unique demesuree : coupe brute
            if cur:
                out.append(Paragraphe(p.numero, cur))
                cur = []
            out.append(Paragraphe(p.numero, [line[:max_chars]]))
            line = line[max_chars:]
        if cur and len("\n".join(cur)) + len(line) + 1 > max_chars:
            out.append(Paragraphe(p.numero, cur))
            cur = []
        cur.append(line)
    if cur:
        out.append(Paragraphe(p.numero, cur))
    return out


def decouper(lines: list[str], est_dispositif, chunk_chars: int = CHUNK_CHARS,
             ignorer=None) -> list[Morceau]:
    """Decoupe les lignes d'une decision en morceaux (motifs groupes + dispositif).

    est_dispositif(ligne) -> bool : repere la premiere ligne du dispositif.
    ignorer(ligne) -> bool : lignes de formule a ne pas indexer.
    """
    if ignorer is not None:
        lines = [l for l in lines if not ignorer(l)]
    # 1. separer le dispositif
    dispo_idx = next((i for i, l in enumerate(lines) if est_dispositif(l)), None)
    corps = lines if dispo_idx is None else lines[:dispo_idx]
    dispositif = [] if dispo_idx is None else lines[dispo_idx:]

    # 2. reperer le debut des motifs : paragraphes numerotes, sinon "Considerant..."
    if any(_NUM_RE.match(l) for l in corps):
        is_start = lambda l: bool(_NUM_RE.match(l))  # noqa: E731
    elif any(_CONSIDERANT_RE.match(l) for l in corps):
        is_start = lambda l: bool(_CONSIDERANT_RE.match(l))  # noqa: E731
    else:
        is_start = None

    if is_start is not None:
        first = next(i for i, l in enumerate(corps) if is_start(l))
        # garder un eventuel intertitre juste avant le premier motif
        if first > 0 and len(corps[first - 1]) <= HEADING_MAX_CHARS and not corps[first - 1].endswith(";"):
            first -= 1
        paras = _split_paragraphs(corps[first:], is_start)
        # numerotation officielle quand elle existe, sinon 0 (pas de numero affiche)
        for p in paras:
            m = _NUM_RE.match(next((l for l in p.lignes if is_start(l)), ""))
            p.numero = int(m.group(1)) if m else 0
    else:
        paras = [Paragraphe(numero=0, lignes=[l]) for l in corps]

    paras = [q for p in paras for q in _scinder(p, PARA_MAX_CHARS)]

    # 3. regrouper sans couper un paragraphe
    morceaux: list[Morceau] = []
    courant: list[Paragraphe] = []
    taille = 0
    for p in paras:
        n = len(p.texte)
        if courant and taille + n > chunk_chars:
            morceaux.append(Morceau("motifs", courant))
            courant, taille = [], 0
        courant.append(p)
        taille += n
    if courant:
        morceaux.append(Morceau("motifs", courant))
    if dispositif:
        for q in _scinder(Paragraphe(numero=0, lignes=dispositif), PARA_MAX_CHARS):
            morceaux.append(Morceau("dispositif", [q]))
    return morceaux


def decouper_sommaire(alineas: list[str], max_chars: int = PARA_MAX_CHARS) -> list[list[str]]:
    """Un sommaire tres long (analyses multiples) est reparti en plusieurs passages."""
    morceaux: list[list[str]] = []
    courant: list[str] = []
    for a in alineas:
        while len(a) > max_chars:
            if courant:
                morceaux.append(courant)
                courant = []
            morceaux.append([a[:max_chars]])
            a = a[max_chars:]
        if courant and sum(len(x) for x in courant) + len(a) > max_chars:
            morceaux.append(courant)
            courant = []
        courant.append(a)
    if courant:
        morceaux.append(courant)
    return morceaux
