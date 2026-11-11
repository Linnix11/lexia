"""Ingestion de la Constitution de 1958 depuis la page du Conseil constitutionnel.

Structure attendue de la page (verifiee le 2026-11-11) :
  div.field--name-field-texte
    <p>Texte integral en vigueur a jour de la revision ... </p>
    <h2 id="preambule">PREAMBULE</h2> <p>...</p>
    <h3 id="article_premier" data-summary="ARTICLE PREMIER.">  <p>alinea</p> ...
    <h2 id="titre_..." data-summary="Titre premier - ...">
    <h3 id="article_61_1" data-summary="ARTICLE 61-1."> ...

Si cette structure change, parse() leve une erreur plutot que de produire un corpus incomplet.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup, Tag

from ingest.models import Passage

SOURCE_ID = "constitution_1958"
URL = (
    "https://www.conseil-constitutionnel.fr/le-bloc-de-constitutionnalite/"
    "texte-integral-de-la-constitution-du-4-octobre-1958-en-vigueur"
)
MIN_ARTICLES = 100  # la Constitution en vigueur compte un peu plus de 100 articles

_NUM_RE = re.compile(r"^ARTICLE\s+(PREMIER|[0-9]+(?:-[0-9]+)?)\.?$", re.IGNORECASE)


class ParseError(RuntimeError):
    pass


def _clean(text: str) -> str:
    text = text.replace(" ", " ").replace(" ", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


def _paragraph_text(p: Tag) -> str:
    for br in p.find_all("br"):
        br.replace_with("\n")
    return _clean(p.get_text())


def _article_number(label: str) -> str:
    m = _NUM_RE.match(_clean(label))
    if not m:
        raise ParseError(f"Intitule d'article non reconnu : {label!r}")
    num = m.group(1)
    return "1" if num.upper() == "PREMIER" else num


def parse(html: str, *, date_recuperation: str | None = None, min_articles: int = MIN_ARTICLES) -> list[Passage]:
    soup = BeautifulSoup(html, "html.parser")
    body = soup.select_one("div.field--name-field-texte")
    if body is None:
        raise ParseError("Bloc de texte introuvable (div.field--name-field-texte)")

    date_recuperation = date_recuperation or datetime.now(timezone.utc).isoformat(timespec="seconds")
    version = ""
    titre: str | None = None
    current: dict | None = None
    passages: list[Passage] = []

    def flush() -> None:
        if current is None:
            return
        if not current["alineas"]:
            raise ParseError(f"Passage vide : {current['id']}")
        passages.append(
            Passage(
                id=current["id"],
                source_id=SOURCE_ID,
                type=current["type"],
                numero=current["numero"],
                titre=current["titre"],
                alineas=current["alineas"],
                url=f"{URL}#{current['ancre']}",
                version=version,
                date_recuperation=date_recuperation,
            )
        )

    for el in body.find_all(["h2", "h3", "p"], recursive=False):
        if el.name == "h2":
            flush()
            label = _clean(el.get("data-summary") or el.get_text())
            if el.get("id") == "preambule":
                titre = None
                current = {
                    "id": f"{SOURCE_ID}:preambule",
                    "type": "preambule",
                    "numero": None,
                    "titre": None,
                    "ancre": "preambule",
                    "alineas": [],
                }
            else:
                titre = label
                current = None
        elif el.name == "h3":
            flush()
            numero = _article_number(el.get("data-summary") or el.get_text())
            current = {
                "id": f"{SOURCE_ID}:art:{numero}",
                "type": "article",
                "numero": numero,
                "titre": titre,
                "ancre": el.get("id", ""),
                "alineas": [],
            }
        else:  # <p>
            text = _paragraph_text(el)
            if not text:
                continue
            if current is None:
                # Paragraphes d'en-tete avant le preambule (mention de version, lien PDF)
                if "jour de la" in text.lower():
                    version = text
                continue
            current["alineas"].append(text)
    flush()

    _check(passages, version, min_articles)
    return passages


def _check(passages: list[Passage], version: str, min_articles: int) -> None:
    if not version:
        raise ParseError("Mention de version introuvable en tete de texte")
    articles = [p for p in passages if p.type == "article"]
    if len(articles) < min_articles:
        raise ParseError(f"Seulement {len(articles)} articles trouves (minimum attendu {min_articles})")
    ids = [p.id for p in passages]
    doublons = {i for i in ids if ids.count(i) > 1}
    if doublons:
        raise ParseError(f"Identifiants en double : {sorted(doublons)}")
    if not any(p.numero == "1" for p in articles) or not any(p.numero == "89" for p in articles):
        raise ParseError("Article 1 ou article 89 manquant")


def fetch(client) -> str:
    resp = client.get(URL, follow_redirects=True, timeout=30)
    resp.raise_for_status()
    return resp.text
