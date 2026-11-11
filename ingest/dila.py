"""Outils communs aux archives open data de la DILA (LEGI, CONSTIT, CASS).

Les archives "Freemium_<fonds>_global_<date>.tar.gz" sont publiees sur
https://echanges.dila.gouv.fr/OPENDATA/<FONDS>/ et contiennent un fichier XML par document.
"""

from __future__ import annotations

import html
import re
import tarfile
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from pathlib import Path

BASE_URL = "https://echanges.dila.gouv.fr/OPENDATA"


def latest_archive(raw_dir: Path, fonds: str) -> Path:
    """Renvoie l'archive globale la plus recente pour un fonds (ex. 'constit')."""
    candidates = sorted(raw_dir.glob(f"Freemium_{fonds}_global_*.tar.gz"))
    if not candidates:
        raise FileNotFoundError(
            f"Aucune archive Freemium_{fonds}_global_*.tar.gz dans {raw_dir}. "
            f"Telecharger depuis {BASE_URL}/{fonds.upper()}/"
        )
    return candidates[-1]


def archive_date(path: Path) -> str:
    """'Freemium_constit_global_20261108-140000.tar.gz' -> '2026-11-08'."""
    m = re.search(r"_(\d{4})(\d{2})(\d{2})-\d{6}\.tar\.gz$", path.name)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""


def iter_xml(archive: Path, path_filter=None) -> Iterator[tuple[str, bytes]]:
    """Parcourt l'archive en flux (sans tout extraire) et renvoie (chemin, contenu XML)."""
    with tarfile.open(archive, "r|gz") as tar:
        for member in tar:
            if not member.isfile() or not member.name.endswith(".xml"):
                continue
            if path_filter is not None and not path_filter(member.name):
                continue
            f = tar.extractfile(member)
            if f is not None:
                yield member.name, f.read()


def text_of(root: ET.Element, path: str) -> str:
    el = root.find(path)
    return clean("".join(el.itertext())) if el is not None else ""


def clean(text: str) -> str:
    text = text.replace(" ", " ").replace(" ", " ")
    return re.sub(r"[ \t\r\f\v]+", " ", text).strip()


_TAG_RE = re.compile(r"<[^>]+>")
_BR_RE = re.compile(r"<\s*br\s*/?\s*>|</p\s*>|<p[^>]*>", re.IGNORECASE)


def contenu_lines(raw_xml: str, tag: str = "CONTENU") -> list[str]:
    """Extrait le bloc <CONTENU> (HTML simplifie) et le decoupe en lignes non vides."""
    start = raw_xml.find(f"<{tag}")
    end = raw_xml.find(f"</{tag}>")
    if start == -1 or end == -1:
        return []
    body = raw_xml[raw_xml.find(">", start) + 1 : end]
    body = _BR_RE.sub("\n", body)
    body = html.unescape(_TAG_RE.sub("", body))
    return [line for line in (clean(x) for x in body.split("\n")) if line]
