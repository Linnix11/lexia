"""Autres codes et lois en vigueur depuis l'archive DILA LEGI.

Chaque code est une source a part (filtrage par matiere, references « article X du code Y »).
Les lois, lois organiques et ordonnances en vigueur (textes non codifies) forment la source « lois ».

Identifiants verifies dans l'archive (TITREFULL du texte) le 2026-11-11.
Une seule passe sur l'archive (~6 min) extrait tous les textes retenus dans
data/raw/dila/extrait_legi_<date>/<identifiant du texte>/ ; les imports suivants relisent le disque.
"""

from __future__ import annotations

import json
import re
import tarfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from ingest import dila
from ingest.sources import legi


@dataclass(frozen=True)
class Code:
    source_id: str
    legitext: str
    nom: str


CODES: tuple[Code, ...] = (
    Code("code_penal", "LEGITEXT000006070719", "Code pénal"),
    Code("code_procedure_penale", "LEGITEXT000006071154", "Code de procédure pénale"),
    Code("code_justice_penale_mineurs", "LEGITEXT000039086952", "Code de la justice pénale des mineurs"),
    Code("code_procedure_civile", "LEGITEXT000006070716", "Code de procédure civile"),
    Code("code_organisation_judiciaire", "LEGITEXT000006071164", "Code de l'organisation judiciaire"),
    Code("code_procedures_civiles_execution", "LEGITEXT000025024948", "Code des procédures civiles d'exécution"),
    Code("code_commerce", "LEGITEXT000005634379", "Code de commerce"),
    Code("code_monetaire_financier", "LEGITEXT000006072026", "Code monétaire et financier"),
    Code("code_consommation", "LEGITEXT000006069565", "Code de la consommation"),
    Code("code_propriete_intellectuelle", "LEGITEXT000006069414", "Code de la propriété intellectuelle"),
    Code("code_assurances", "LEGITEXT000006073984", "Code des assurances"),
    Code("code_travail", "LEGITEXT000006072050", "Code du travail"),
    Code("code_securite_sociale", "LEGITEXT000006073189", "Code de la sécurité sociale"),
    Code("code_justice_administrative", "LEGITEXT000006070933", "Code de justice administrative"),
    Code("code_relations_public_administration", "LEGITEXT000031366350", "Code des relations entre le public et l'administration"),
    Code("code_collectivites_territoriales", "LEGITEXT000006070633", "Code général des collectivités territoriales"),
    Code("code_propriete_personnes_publiques", "LEGITEXT000006070299", "Code général de la propriété des personnes publiques"),
    Code("code_commande_publique", "LEGITEXT000037701019", "Code de la commande publique"),
    Code("code_fonction_publique", "LEGITEXT000044416551", "Code général de la fonction publique"),
    Code("code_urbanisme", "LEGITEXT000006074075", "Code de l'urbanisme"),
    Code("code_environnement", "LEGITEXT000006074220", "Code de l'environnement"),
    Code("code_construction_habitation", "LEGITEXT000006074096", "Code de la construction et de l'habitation"),
    Code("code_entree_sejour_etrangers", "LEGITEXT000006070158", "Code de l'entrée et du séjour des étrangers et du droit d'asile"),
    Code("code_electoral", "LEGITEXT000006070239", "Code électoral"),
)
NATURES_LOIS = {"LOI", "LOI_ORGANIQUE", "ORDONNANCE", "LOI_CONSTIT"}
SOURCE_LOIS = "lois"


def _inventaire(raw_dir: Path, date: str) -> dict:
    f = raw_dir / f"inventaire_legi_{date}.json"
    if not f.exists():
        raise FileNotFoundError(f"{f} absent : inventaire des textes LEGI a produire (voir docs).")
    return json.loads(f.read_text(encoding="utf-8"))


def _ids_lois(raw_dir: Path, date: str) -> set[str]:
    return {i for i, nature, *_ in _inventaire(raw_dir, date)["lois"] if nature in NATURES_LOIS}


def _dossier(raw_dir: Path) -> tuple[Path, Path, str]:
    archive = dila.latest_archive(raw_dir, "legi")
    date = archive.name.split("_")[-1][:8]
    return archive, raw_dir / f"extrait_legi_{date}", date


def extraire(raw_dir: Path) -> Path:
    """Extrait en une passe les codes retenus et les lois en vigueur (si pas deja fait)."""
    archive, dest, date = _dossier(raw_dir)
    if dest.exists():
        return dest
    voulus = {c.legitext for c in CODES} | _ids_lois(raw_dir, date)
    tmp = dest.with_name(dest.name + ".partiel")
    tmp.mkdir(parents=True, exist_ok=True)
    motif = re.compile(r"/((?:LEGITEXT|JORFTEXT)\d+)/(.+)$")
    print(f"  extraction de {len(voulus)} textes depuis {archive.name} (environ 6 minutes)...", flush=True)
    with tarfile.open(archive, "r|gz") as tar:
        for m in tar:
            if not (m.isfile() and m.name.endswith(".xml") and "/article/" in m.name):
                continue
            mm = motif.search(m.name)
            if not mm or mm.group(1) not in voulus:
                continue
            f = tar.extractfile(m)
            if f is None:
                continue
            cible = tmp / mm.group(1) / mm.group(2)
            cible.parent.mkdir(parents=True, exist_ok=True)
            cible.write_bytes(f.read())
    tmp.rename(dest)
    return dest


class SourceCode:
    """Une source par code (interface attendue par ingest.run : SOURCE_ID + collect)."""

    def __init__(self, code: Code):
        self.code = code
        self.SOURCE_ID = code.source_id

    def collect(self, raw_dir: Path, *, date_recuperation: str) -> Iterator[legi.Passage]:
        archive, _, _ = _dossier(raw_dir)
        dossier = extraire(raw_dir) / self.code.legitext
        version = f"archive DILA LEGI du {dila.archive_date(archive)}"
        passages: dict[str, legi.Passage] = {}
        for f in dossier.rglob("LEGIARTI*.xml"):
            p = legi.parse_article(f.read_bytes(), date_recuperation=date_recuperation, version_archive=version,
                                   source_id=self.code.source_id, nom=self.code.nom)
            if p is not None:
                passages.setdefault(p.id, p)
        if not any(p.meta["en_vigueur"] for p in passages.values()):
            raise RuntimeError(f"{self.code.nom} : aucun article en vigueur (extraction incomplete ?)")
        yield from sorted(passages.values(), key=legi._cle_num)


class SourceLois:
    """Lois, lois organiques et ordonnances en vigueur : seules les versions d'articles en vigueur."""

    SOURCE_ID = SOURCE_LOIS

    def collect(self, raw_dir: Path, *, date_recuperation: str) -> Iterator[legi.Passage]:
        archive, _, date = _dossier(raw_dir)
        racine = extraire(raw_dir)
        version = f"archive DILA LEGI du {dila.archive_date(archive)}"
        n = 0
        vus: set[str] = set()  # un meme article peut etre range sous deux textes (loi et texte JORF)
        for texte_id in sorted(_ids_lois(raw_dir, date)):
            dossier = racine / texte_id
            if not dossier.exists():
                continue
            articles = []
            for f in dossier.rglob("LEGIARTI*.xml"):
                p = legi.parse_article(f.read_bytes(), date_recuperation=date_recuperation, version_archive=version,
                                       source_id=SOURCE_LOIS, nom=None)
                if p is not None and p.meta["en_vigueur"] and p.id not in vus:
                    vus.add(p.id)
                    articles.append(p)
            n += len(articles)
            yield from sorted(articles, key=legi._cle_num)
        if n < 1000:
            raise RuntimeError(f"Seulement {n} articles de lois en vigueur : extraction incomplete ?")


SOURCES = [SourceCode(c) for c in CODES] + [SourceLois()]
