"""Decisions du Conseil constitutionnel (DC, QPC et L) depuis l'archive DILA CONSTIT, completee des decisions
recentes lues sur le site du Conseil (constit_site, D113)."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from pathlib import Path

from ingest import dila
from ingest.jurisprudence import compact, date_fr, decouper
from ingest.models import Passage
from ingest.sources import constit_site

SOURCE_ID = "decisions_conseil_constitutionnel"
FONDS = "constit"
# L : nature reglementaire d'une disposition de loi (art. 37 al. 2 de la Constitution), 338 decisions (audit B9).
NATURES = {"DC", "QPC", "L"}

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


RAW_SITE = "conseil_constitutionnel"   # data/raw/conseil_constitutionnel : pages des decisions recentes


def cles_dila(raw_dir: Path) -> set[str]:
    """Cles (constit_site.cles) des decisions de l'archive : une decision du site deja dans l'archive est ignoree."""
    out: set[str] = set()
    for _, raw in dila.iter_xml_a_jour(raw_dir, FONDS):
        root = ET.fromstring(raw)
        out |= constit_site.cles({"numero": dila.text_of(root, "META/META_SPEC/META_JURI/NUMERO"),
                                  "nature": dila.text_of(root, "META/META_COMMUN/NATURE"),
                                  "ecli": dila.text_of(root, "META/META_SPEC/META_JURI_CONSTIT/ECLI")})
    return out


def collect_dila(raw_dir: Path, *, date_recuperation: str) -> Iterator[Passage]:
    version = f"Archive DILA CONSTIT du {dila.date_corpus(raw_dir, FONDS)}"
    for _, raw in dila.iter_xml_a_jour(raw_dir, FONDS):
        yield from parse_decision(raw, date_recuperation=date_recuperation, version=version)


def collect(raw_dir: Path, *, date_recuperation: str) -> Iterator[Passage]:
    deja: set[str] = set()
    for p in collect_dila(raw_dir, date_recuperation=date_recuperation):
        deja |= constit_site.cles(p.meta)
        yield p
    yield from constit_site.complements(raw_dir.parent / RAW_SITE, deja, date_recuperation=date_recuperation,
                                        source_id=SOURCE_ID)
