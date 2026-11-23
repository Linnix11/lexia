"""Decisions recentes du Conseil constitutionnel lues sur son site, en complement de l'archive DILA CONSTIT.

Pourquoi (docs/jurisprudence-recente.md, D113) : l'archive DILA CONSTIT du 2026-11-08, comme Legifrance,
s'arrete aux decisions du 16 octobre 2026 ; le site du Conseil publie chaque decision le jour meme. Aucun compte
ni cle. Mentions legales du site (relues le 2026-11-20) : textes « librement reproductibles » avec citation du site
comme source, mentions de nature et d'origine (date, intitule), et sans alteration ; c'est deja la source de la
Constitution (constitution_1958).

Chaque nuit (ingest/mise_a_jour.py), synchroniser() lit la page des dernieres decisions (les dix plus recentes)
et telecharge celles qui manquent au cache (data/raw/conseil_constitutionnel/, une page HTML par decision) et a
l'archive DILA ; une decision entree depuis dans l'archive est retiree du cache. constit.collect() lit le cache
apres l'archive et n'en garde que les decisions absentes de celle-ci (meme ECLI ou meme numero).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from ingest.jurisprudence import MOIS, date_fr, decouper
from ingest.models import Passage

SITE = "https://www.conseil-constitutionnel.fr"
VARIABLE_ARRET = "LEXIA_SITE_CONSEIL_CONSTITUTIONNEL"   # « 0 » dans .env : plus de lecture du site, cache vide
URL_LISTE = f"{SITE}/decisions"
_LIEN_RE = re.compile(r"^/decision/(\d{4})/([0-9_]+(?:DC|QPC|L))\.htm$")
_TITRE_RE = re.compile(r"Décision n°\s*(\d{4}-[\d/]+)\s+(DC|QPC|L)\s+du\s+(\d{1,2})(?:er)?\s+(\S+)\s+(\d{4})")


class ParseError(RuntimeError):
    pass


class PagesEnEchec(ParseError):
    """Pages de decision illisibles ou injoignables ; les autres decisions de la liste ont ete telechargees."""

    def __init__(self, echecs: list[str], ajoutes: list[str]):
        self.echecs, self.ajoutes = echecs, ajoutes
        super().__init__(f"{len(echecs)} page(s) de decision en echec, {len(ajoutes)} decision(s) ajoutee(s) "
                         f"quand meme : " + " ; ".join(echecs))


def liste(html: str) -> dict[str, str]:
    """{chemin: cle} des decisions DC, QPC et L de la page des dernieres decisions, dans l'ordre de la page.
    La cle (numero|nature, comme cles()) est lue dans le titre du lien : une decision deja dans l'archive DILA
    n'est pas telechargee."""
    soup = BeautifulSoup(html, "html.parser")
    out: dict[str, str] = {}
    for a in soup.select('a[href^="/decision/"]'):
        if _LIEN_RE.match(a["href"]) and (m := _TITRE_RE.search(a.get("title") or a.get_text(" "))):
            out.setdefault(a["href"], f"{m.group(1).split('/')[0]}|{m.group(2)}")
    return out


def code(chemin: str) -> str:
    """'/decision/2026/20261230_1231QPC.htm' -> '20261230_1231QPC' (nom du fichier en cache)."""
    return chemin.rsplit("/", 1)[-1].removesuffix(".htm")


def synchroniser(http: httpx.Client, raw_dir: Path, deja: set[str]) -> list[str]:
    """Telecharge les decisions recentes absentes du cache et de l'archive DILA ; retire du cache celles que
    l'archive contient desormais. deja : cles des decisions de l'archive (cles()). Renvoie les codes ajoutes.

    Une page illisible (maintenance, format nouveau) ou injoignable ne bloque plus les suivantes : la liste va de
    la plus recente a la plus ancienne, et la page fautive restait en tete plusieurs nuits sans qu'aucune nouvelle
    decision n'entre (audit du 2026-11-23, C1). Les echecs sont listes ensemble a la fin (PagesEnEchec)."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    for f in raw_dir.glob("*.htm"):
        if cles(lire(f.read_text(encoding="utf-8"))) & deja:
            f.unlink()
    r = http.get(URL_LISTE)
    r.raise_for_status()
    chemins = liste(r.text)
    if not chemins:
        raise ParseError("Aucune decision dans la page des dernieres decisions : structure du site changee ?")
    ajoutes, echecs = [], []
    for chemin, cle in chemins.items():
        f = raw_dir / f"{code(chemin)}.htm"
        if f.exists() or cle in deja:
            continue
        try:
            page = http.get(SITE + chemin)
            page.raise_for_status()
            if cles(lire(page.text)) & deja:
                continue
        except (ParseError, httpx.HTTPError) as e:
            echecs.append(f"{chemin} ({type(e).__name__} : {e})")
            continue
        tmp = f.with_suffix(".tmp")
        tmp.write_text(page.text, encoding="utf-8")
        tmp.replace(f)
        ajoutes.append(code(chemin))
    if echecs:
        raise PagesEnEchec(echecs, ajoutes)
    return ajoutes


def _lignes(bloc) -> list[str]:
    for br in bloc.find_all("br"):
        br.replace_with("\n")
    lignes: list[str] = []
    for el in bloc.find_all(["p", "li"]):
        if el.find_parent(["p", "li"]) is not None:
            continue
        for x in el.get_text().splitlines():
            x = re.sub(r"\s+", " ", x.replace(" ", " ")).strip()
            if x:
                lignes.append(x)
    return lignes


def lire(html: str) -> dict:
    """Metadonnees et lignes du texte d'une page de decision."""
    soup = BeautifulSoup(html, "html.parser")
    article = soup.select_one("article.node--view-mode-full")
    titre_page = soup.find("meta", property="og:title")
    m = _TITRE_RE.search(titre_page["content"] if titre_page else "")
    corps = article.select_one("div.field--name-field-contenu-original") if article else None
    if article is None or m is None or corps is None or m.group(4).lower() not in MOIS:
        raise ParseError("Page de decision du Conseil constitutionnel non reconnue")

    def champ(nom: str) -> str:
        el = article.select_one(f"div.field--name-field-{nom}")
        return re.sub(r"\s+", " ", el.get_text(" ")).strip() if el else ""

    lignes = _lignes(corps)
    ecli = next((re.sub(r"\s+", "", l) for l in lignes if l.replace(" ", "").startswith("ECLI:FR:CC:")), "")
    iso = date(int(m.group(5)), MOIS.index(m.group(4).lower()) + 1, int(m.group(3))).isoformat()
    url = soup.find("meta", property="og:url")
    return {"numero": m.group(1), "nature": m.group(2), "date": iso, "titre": champ("titre-complet"),
            "solution": champ("solution-normalisee"), "ecli": ecli, "lignes": lignes,
            "url": url["content"] if url else ""}


def cles(d: dict) -> set[str]:
    """ECLI et numero (premier numero d'une decision jointe) avec la nature, communs au site et a l'archive."""
    out = {f"{d['numero'].split('/')[0]}|{d['nature']}"}
    return out | ({d["ecli"]} if d.get("ecli") else set())


def parse_page(html: str, *, date_recuperation: str, version: str, source_id: str) -> list[Passage]:
    from ingest.sources import constit

    d = lire(html)
    if d["nature"] not in constit.NATURES:
        return []
    ident = code(d["url"]) if d["url"] else f"{d['numero'].replace('-', '').replace('/', '_')}{d['nature']}"
    meta = {"juridiction": "Conseil constitutionnel", "nature": d["nature"], "numero": d["numero"],
            "date": d["date"], "titre": d["titre"], "solution": d["solution"], "ecli": d["ecli"],
            "id_source": f"cc:{ident}", "origine": "Site du Conseil constitutionnel"}
    entete = f"Conseil constitutionnel, décision n° {d['numero']} {d['nature']} du {date_fr(d['date'])} - {d['titre']}"
    return [Passage(id=f"{source_id}:{ident}:{i}", source_id=source_id, type=m.type, numero=m.plage or None,
                    titre=d["titre"], alineas=m.alineas, url=d["url"], version=version,
                    date_recuperation=date_recuperation, meta=meta, entete=entete)
            for i, m in enumerate(decouper(d["lignes"], constit.est_dispositif, ignorer=constit.est_formule),
                                  start=1)]


def complements(raw_dir: Path, deja: set[str], *, date_recuperation: str, source_id: str) -> Iterator[Passage]:
    """Passages des decisions du cache absentes de l'archive DILA, dans l'ordre des codes."""
    for f in sorted(raw_dir.glob("*.htm")):
        html = f.read_text(encoding="utf-8")
        if cles(lire(html)) & deja:
            continue
        lu = date.fromtimestamp(f.stat().st_mtime).isoformat()
        yield from parse_page(html, date_recuperation=date_recuperation, source_id=source_id,
                              version=f"Site du Conseil constitutionnel, page lue le {lu}")
