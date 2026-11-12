"""Jurisprudence administrative depuis l'archive DILA JADE.

Perimetre : decisions du Conseil d'Etat (et du Tribunal des conflits s'il figure dans l'archive)
  - publiees au recueil Lebon (categorie A), toutes annees : les grands arrets du programme ;
  - mentionnees aux tables (categorie B) depuis DATE_MIN_TABLES.
Les cours administratives d'appel et les decisions non publiees (C) sont ecartees.

Passages : sommaire officiel (titrage + analyse), motifs regroupes, dispositif.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from pathlib import Path

from ingest import dila
from ingest.jurisprudence import compact, decouper, decouper_sommaire
from ingest.models import Passage

SOURCE_ID = "conseil_etat"
FONDS = "jade"
JURIDICTIONS = {"Conseil d'Etat", "Conseil d'État", "Tribunal des conflits", "Tribunal des Conflits"}
DATE_MIN_TABLES = "2010-01-01"
# Lien Legifrance construit a partir de l'identifiant DILA (format a confirmer en navigateur).
URL_LEGIFRANCE = "https://www.legifrance.gouv.fr/ceta/id/{id}"

_FORMULE_RE = re.compile(r"^(Vu |Après avoir entendu|Considérant ce qui suit|-{3,})", re.IGNORECASE)


def est_dispositif(line: str) -> bool:
    c = compact(line)
    return len(line) < 60 and (c.startswith("DECIDE") or c.startswith("DÉCIDE"))


def est_formule(line: str) -> bool:
    return bool(_FORMULE_RE.match(line)) and len(line) < 200


def _sommaire(root: ET.Element) -> list[str]:
    som = root.find("TEXTE/SOMMAIRE")
    out: list[str] = []
    if som is None:
        return out
    for el in som:
        if el.tag in ("SCT", "ANA") and el.get("TYPE", "PRINCIPAL") == "PRINCIPAL":
            t = dila.clean("".join(el.itertext()))
            if t and t not in out:
                out.append(t)
    return out


def _lignes_motifs(lines: list[str]) -> list[str]:
    """Retire la procedure et les visas : la motivation commence au premier paragraphe numerote
    ou au premier « Considérant »."""
    for i, l in enumerate(lines):
        if re.match(r"^(\d+\s*\.\s|Considérant|Sur )", l):
            return lines[i:]
    return lines


def parse_decision(raw: bytes, *, date_recuperation: str, version: str) -> list[Passage]:
    root = ET.fromstring(raw)
    juridiction = dila.text_of(root, "META/META_SPEC/META_JURI/JURIDICTION")
    if juridiction not in JURIDICTIONS:
        return []
    publication = dila.text_of(root, "META/META_SPEC/META_JURI_ADMIN/PUBLI_RECUEIL")
    date = dila.text_of(root, "META/META_SPEC/META_JURI/DATE_DEC")
    if not (publication == "A" or (publication == "B" and date >= DATE_MIN_TABLES)):
        return []
    doc_id = dila.text_of(root, "META/META_COMMUN/ID")
    titre = dila.text_of(root, "META/META_SPEC/META_JURI/TITRE")
    meta = {
        "juridiction": "Conseil d'État" if "Conseil" in juridiction else "Tribunal des conflits",
        "formation": dila.text_of(root, "META/META_SPEC/META_JURI_ADMIN/FORMATION"),
        "date": date,
        "numero": dila.text_of(root, "META/META_SPEC/META_JURI/NUMERO"),
        "publication": {"A": "Recueil Lebon", "B": "Tables du recueil Lebon"}[publication],
        "type_recours": dila.text_of(root, "META/META_SPEC/META_JURI_ADMIN/TYPE_REC"),
        "ecli": dila.text_of(root, "META/META_SPEC/META_JURI_ADMIN/ECLI"),
        "id_dila": doc_id,
    }
    common = dict(source_id=SOURCE_ID, titre=titre, url=URL_LEGIFRANCE.format(id=doc_id), version=version,
                  date_recuperation=date_recuperation, meta=meta, entete=titre)
    passages = []
    som = _sommaire(root)
    if som:
        for k, bloc in enumerate(decouper_sommaire(som)):
            suffixe = "sommaire" if k == 0 else f"sommaire-{k + 1}"
            passages.append(Passage(id=f"{SOURCE_ID}:{doc_id}:{suffixe}", type="sommaire", numero=None, alineas=bloc, **common))
    lignes = _lignes_motifs(dila.contenu_lines(raw.decode("utf-8", errors="replace")))
    for i, m in enumerate(decouper(lignes, est_dispositif, ignorer=est_formule), start=1):
        passages.append(Passage(id=f"{SOURCE_ID}:{doc_id}:{i}", type=m.type, numero=m.plage or None, alineas=m.alineas, **common))
    return passages


def collect(raw_dir: Path, *, date_recuperation: str) -> Iterator[Passage]:
    archive = dila.latest_archive(raw_dir, FONDS)
    version = f"Archive DILA JADE du {dila.archive_date(archive)}"
    for _, raw in dila.iter_xml(archive):
        yield from parse_decision(raw, date_recuperation=date_recuperation, version=version)
