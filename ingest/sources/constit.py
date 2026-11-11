"""Decisions du Conseil constitutionnel (DC et QPC) depuis l'archive DILA CONSTIT."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from pathlib import Path

from ingest import dila
from ingest.jurisprudence import compact, date_fr, decouper
from ingest.models import Passage

SOURCE_ID = "decisions_conseil_constitutionnel"
FONDS = "constit"
NATURES = {"DC", "QPC"}

_DISPOSITIF_RE = re.compile(r"^(LECONSEILCONSTITUTIONNEL)?D[ÉE]CIDE:?$")
_FORMULE_RE = re.compile(r"S.EST FOND[ÉE] SUR CE QUI SUIT", re.IGNORECASE)


def est_dispositif(line: str) -> bool:
    return len(line) < 60 and bool(_DISPOSITIF_RE.match(compact(line)))


def est_formule(line: str) -> bool:
    return len(line) < 80 and bool(_FORMULE_RE.search(line))


def parse_decision(raw: bytes, *, date_recuperation: str, version: str) -> list[Passage]:
    text = raw.decode("utf-8")
    root = ET.fromstring(raw)
    nature = dila.text_of(root, "META/META_COMMUN/NATURE")
    if nature not in NATURES:
        return []
    doc_id = dila.text_of(root, "META/META_COMMUN/ID")
    meta = {
        "juridiction": "Conseil constitutionnel",
        "nature": nature,
        "numero": dila.text_of(root, "META/META_SPEC/META_JURI/NUMERO"),
        "date": dila.text_of(root, "META/META_SPEC/META_JURI/DATE_DEC"),
        "titre": dila.text_of(root, "META/META_SPEC/META_JURI/TITRE"),
        "solution": dila.text_of(root, "META/META_SPEC/META_JURI/SOLUTION"),
        "ecli": dila.text_of(root, "META/META_SPEC/META_JURI_CONSTIT/ECLI"),
        "id_dila": doc_id,
    }
    url = dila.text_of(root, "META/META_SPEC/META_JURI_CONSTIT/URL_CC").replace("http://", "https://", 1)
    entete = (
        f"Conseil constitutionnel, décision n° {meta['numero']} {nature} du {date_fr(meta['date'])}"
        f" - {meta['titre']}"
    )

    passages = []
    for i, m in enumerate(decouper(dila.contenu_lines(text), est_dispositif, ignorer=est_formule), start=1):
        passages.append(
            Passage(
                id=f"{SOURCE_ID}:{doc_id}:{i}",
                source_id=SOURCE_ID,
                type=m.type,
                numero=m.plage or None,
                titre=meta["titre"],
                alineas=m.alineas,
                url=url,
                version=version,
                date_recuperation=date_recuperation,
                meta=meta,
                entete=entete,
            )
        )
    return passages


def collect(raw_dir: Path, *, date_recuperation: str) -> Iterator[Passage]:
    archive = dila.latest_archive(raw_dir, FONDS)
    version = f"Archive DILA CONSTIT du {dila.archive_date(archive)}"
    for _, raw in dila.iter_xml(archive):
        yield from parse_decision(raw, date_recuperation=date_recuperation, version=version)
