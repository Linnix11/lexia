"""Arrets publies de la Cour de cassation depuis l'archive DILA CASS.

Perimetre : toutes les chambres, arrets publies depuis DATE_MIN (2000).
Passages produits par arret :
  - "sommaire" : titrage + analyse officiels (resume redige par la Cour)
  - "motifs"   : paragraphes de motivation regroupes
  - "dispositif"
Les moyens annexes (arguments des parties) ne sont pas indexes.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from pathlib import Path

from ingest import dila
from ingest.jurisprudence import compact, decouper, decouper_sommaire
from ingest.models import Passage

SOURCE_ID = "judilibre"  # meme id que le registre : jurisprudence de la Cour de cassation
FONDS = "cass"
FORMATIONS = {
    "CHAMBRE_CIVILE_1": "Première chambre civile",
    "CHAMBRE_CIVILE_2": "Deuxième chambre civile",
    "CHAMBRE_CIVILE_3": "Troisième chambre civile",
    "CHAMBRE_CIVILE": "Chambre civile",
    "ASSEMBLEE_PLENIERE": "Assemblée plénière",
    "CHAMBRE_MIXTE": "Chambre mixte",
    "CHAMBRES_REUNIES": "Chambres réunies",
    "CHAMBRE_CRIMINELLE": "Chambre criminelle",
    "CHAMBRE_SOCIALE": "Chambre sociale",
    "CHAMBRE_COMMERCIALE": "Chambre commerciale",
}
# Une source par grande famille de chambres (filtrage par matiere) ; les chambres civiles,
# l'Assemblee pleniere et la chambre mixte gardent l'identifiant historique "judilibre".
SOURCE_PAR_FORMATION = {
    "CHAMBRE_CRIMINELLE": "cass_criminelle",
    "CHAMBRE_SOCIALE": "cass_sociale",
    "CHAMBRE_COMMERCIALE": "cass_commerciale",
}
DATE_MIN = "2000-01-01"

# Lien Legifrance construit a partir de l'identifiant DILA (format a confirmer en navigateur).
URL_LEGIFRANCE = "https://www.legifrance.gouv.fr/juri/id/{id}"

_DEBUT_RE = re.compile(
    r"^(\d+\s*\.\s|Faits et proc[ée]dure|Attendu|Vu |Sur le |Sur les |Sur la |Sur l'|Donne acte)",
    re.IGNORECASE,
)


def est_dispositif(line: str) -> bool:
    return compact(line).startswith("PARCESMOTIFS")


_FIN_PREFIXES = ("MOYENANNEX", "MOYENSANNEX", "MOYENPRODUIT", "MOYENSPRODUIT")


def est_fin(line: str) -> bool:
    """Debut des moyens annexes (arguments des parties, places apres le dispositif)."""
    return compact(line).startswith(_FIN_PREFIXES)


def est_formule(line: str) -> bool:
    return line.startswith("Ainsi fait et jugé") or compact(line).startswith("RÉPUBLIQUEFRANÇAISE")


def lignes_utiles(lines: list[str]) -> list[str]:
    """Retire l'en-tete de procedure et les moyens annexes."""
    debut = next((i for i, l in enumerate(lines) if _DEBUT_RE.match(l)), 0)
    dispo = next((i for i, l in enumerate(lines) if i > debut and est_dispositif(l)), debut)
    fin = next((i for i, l in enumerate(lines) if i > dispo and est_fin(l)), len(lines))
    return lines[debut:fin]


def _sommaire(root: ET.Element) -> list[str]:
    som = root.find("TEXTE/SOMMAIRE")
    if som is None:
        return []
    out = []
    for el in som:
        if el.tag in ("SCT", "ANA") and el.get("TYPE", "PRINCIPAL") == "PRINCIPAL":
            t = dila.clean("".join(el.itertext()))
            if t and t not in out:
                out.append(t)
    return out


def parse_arret(raw: bytes, *, date_recuperation: str, version: str, seulement: str | None = None) -> list[Passage]:
    """seulement : ne garder que les arrets d'une source (ex. "cass_sociale")."""
    root = ET.fromstring(raw)
    formation = dila.text_of(root, "META/META_SPEC/META_JURI_JUDI/FORMATION")
    date = dila.text_of(root, "META/META_SPEC/META_JURI/DATE_DEC")
    if formation not in FORMATIONS or date < DATE_MIN:
        return []
    source_id = SOURCE_PAR_FORMATION.get(formation, SOURCE_ID)
    if seulement is not None and source_id != seulement:
        return []
    doc_id = dila.text_of(root, "META/META_COMMUN/ID")
    titre = dila.text_of(root, "META/META_SPEC/META_JURI/TITRE")
    meta = {
        "juridiction": "Cour de cassation",
        "formation": FORMATIONS[formation],
        "date": date,
        "numeros_pourvoi": [
            dila.clean(e.text or "") for e in root.findall("META/META_SPEC/META_JURI_JUDI/NUMEROS_AFFAIRES/NUMERO_AFFAIRE")
        ],
        "solution": dila.text_of(root, "META/META_SPEC/META_JURI/SOLUTION"),
        "ecli": dila.text_of(root, "META/META_SPEC/META_JURI_JUDI/ECLI"),
        "id_dila": doc_id,
    }
    common = dict(
        source_id=source_id,
        titre=titre,
        url=URL_LEGIFRANCE.format(id=doc_id),
        version=version,
        date_recuperation=date_recuperation,
        meta=meta,
        entete=titre,
    )

    passages = []
    som = _sommaire(root)
    if som:
        for k, bloc in enumerate(decouper_sommaire(som)):
            suffixe = "sommaire" if k == 0 else f"sommaire-{k + 1}"
            passages.append(Passage(id=f"{source_id}:{doc_id}:{suffixe}", type="sommaire", numero=None, alineas=bloc, **common))

    lines = lignes_utiles(dila.contenu_lines(raw.decode("utf-8")))
    for i, m in enumerate(decouper(lines, est_dispositif, ignorer=est_formule), start=1):
        passages.append(
            Passage(id=f"{source_id}:{doc_id}:{i}", type=m.type, numero=m.plage or None, alineas=m.alineas, **common)
        )
    return passages


def collect(raw_dir: Path, *, date_recuperation: str, seulement: str = SOURCE_ID) -> Iterator[Passage]:
    archive = dila.latest_archive(raw_dir, FONDS)
    version = f"Archive DILA CASS du {dila.archive_date(archive)}"
    for _, raw in dila.iter_xml(archive):
        yield from parse_arret(raw, date_recuperation=date_recuperation, version=version, seulement=seulement)


class SourceChambre:
    """Chambres criminelle, sociale et commerciale : une source chacune (interface de ingest.run)."""

    def __init__(self, source_id: str):
        self.SOURCE_ID = source_id

    def collect(self, raw_dir: Path, *, date_recuperation: str) -> Iterator[Passage]:
        return collect(raw_dir, date_recuperation=date_recuperation, seulement=self.SOURCE_ID)


SOURCES = [SourceChambre(s) for s in sorted(set(SOURCE_PAR_FORMATION.values()))]
