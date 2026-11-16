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
import shutil
import tarfile
import xml.etree.ElementTree as ET
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
    # Ajouts du 2026-11-13. DDHC et Preambule de 1946 : textes non codifies (dossier JORFTEXT de l'archive LEGI).
    Code("ddhc_1789", "JORFTEXT000000697056", "Déclaration des droits de l'homme et du citoyen de 1789"),
    Code("preambule_1946", "JORFTEXT000000868390", "Préambule de la Constitution du 27 octobre 1946"),
    Code("code_general_impots", "LEGITEXT000006069577", "Code général des impôts"),
    Code("livre_procedures_fiscales", "LEGITEXT000006069583", "Livre des procédures fiscales"),
    Code("code_juridictions_financieres", "LEGITEXT000006070249", "Code des juridictions financières"),
    Code("code_securite_interieure", "LEGITEXT000025503132", "Code de la sécurité intérieure"),
    Code("code_action_sociale_familles", "LEGITEXT000006074069", "Code de l'action sociale et des familles"),
    Code("code_penitentiaire", "LEGITEXT000045476241", "Code pénitentiaire"),
    Code("code_expropriation", "LEGITEXT000006074224", "Code de l'expropriation pour cause d'utilité publique"),
)
NATURES_LOIS = {"LOI", "LOI_ORGANIQUE", "ORDONNANCE", "LOI_CONSTIT"}
SOURCE_LOIS = "lois"


# Dossier d'un texte dans un chemin de l'archive, et la suite du chemin (absente pour le dossier lui-meme).
_MOTIF = re.compile(r"/((?:LEGITEXT|JORFTEXT)\d+)(?:/(.+))?$")


def _fichier_inventaire(raw_dir: Path, date: str) -> Path:
    return raw_dir / f"inventaire_legi_{date}.json"


def _loi(nom: str, raw: bytes) -> list[str] | None:
    """[dossier, nature, date, titre] si ce fichier texte/version est celui d'une loi ou ordonnance."""
    mm = _MOTIF.search("/" + nom)
    if not mm or "/TNC_" not in nom or "/texte/version/" not in nom:
        return None
    root = ET.fromstring(raw)
    nature = dila.text_of(root, ".//NATURE")
    if nature not in NATURES_LOIS:
        return None
    return [mm.group(1), nature, dila.text_of(root, ".//DATE_TEXTE"), dila.text_of(root, ".//TITREFULL")]


def inventorier(raw_dir: Path) -> Path:
    """Liste les lois, lois organiques et ordonnances de l'archive globale (une passe, quelques minutes)."""
    archive, _, date = _dossier(raw_dir)
    print(f"  inventaire des lois de {archive.name}...", flush=True)
    lois = {}
    for nom, raw in dila.iter_xml(archive, lambda n: "/TNC_" in n and "/texte/version/" in n):
        if loi := _loi(nom, raw):
            lois[loi[0]] = loi
    f = _fichier_inventaire(raw_dir, date)
    f.write_text(json.dumps({"lois": sorted(lois.values())}, ensure_ascii=False), encoding="utf-8")
    return f


def _inventaire(raw_dir: Path, date: str) -> dict:
    f = _fichier_inventaire(raw_dir, date)
    if not f.exists():
        inventorier(raw_dir)
    return json.loads(f.read_text(encoding="utf-8"))


def _ids_lois(raw_dir: Path, date: str) -> set[str]:
    return {i for i, nature, *_ in _inventaire(raw_dir, date)["lois"] if nature in NATURES_LOIS}


def _voulus(raw_dir: Path, date: str) -> set[str]:
    return {c.legitext for c in CODES} | {legi.CODE_ID} | _ids_lois(raw_dir, date)


def _dossier(raw_dir: Path) -> tuple[Path, Path, str]:
    archive = dila.latest_archive(raw_dir, "legi")
    date = archive.name.split("_")[-1][:8]
    return archive, raw_dir / f"extrait_legi_{date}", date


def extraire(raw_dir: Path) -> Path:
    """Extrait les codes retenus et les lois (une passe d'environ 6 minutes sur l'archive globale, faite
    une fois), puis applique les archives quotidiennes pas encore lues."""
    archive, dest, date = _dossier(raw_dir)
    if not dest.exists():
        voulus = _voulus(raw_dir, date)
        tmp = dest.with_name(dest.name + ".partiel")
        tmp.mkdir(parents=True, exist_ok=True)
        print(f"  extraction de {len(voulus)} textes depuis {archive.name} (environ 6 minutes)...", flush=True)
        with tarfile.open(archive, "r|gz") as tar:
            for m in tar:
                if not (m.isfile() and m.name.endswith(".xml") and "/article/" in m.name):
                    continue
                mm = _MOTIF.search(m.name)
                if not mm or mm.group(1) not in voulus:
                    continue
                f = tar.extractfile(m)
                if f is None:
                    continue
                cible = tmp / mm.group(1) / mm.group(2)
                cible.parent.mkdir(parents=True, exist_ok=True)
                cible.write_bytes(f.read())
        tmp.rename(dest)
    appliquer_increments(raw_dir, dest, date)
    return dest


def appliquer_increments(raw_dir: Path, dest: Path, date: str) -> list[str]:
    """Applique a l'extraction les archives quotidiennes pas encore lues (liste dans dest/.increments) :
    nouvelles lois ajoutees a l'inventaire, articles ecrits par-dessus, dossiers supprimes retires (D78).
    Renvoie les horodatages appliques."""
    journal = dest / ".increments"
    deja = set(journal.read_text().split()) if journal.exists() else set()
    appliques = []
    for inc in dila.increments(raw_dir, "legi"):
        h = dila.horodatage(inc)
        if h in deja:
            continue
        supprimes, fichiers = dila.lire_increment(inc)
        inventaire = _inventaire(raw_dir, date)
        connues = {loi[0] for loi in inventaire["lois"]}
        nouvelles = [loi for nom, raw in fichiers if (loi := _loi(nom, raw)) and loi[0] not in connues]
        if nouvelles:
            inventaire["lois"] += nouvelles
            _fichier_inventaire(raw_dir, date).write_text(json.dumps(inventaire, ensure_ascii=False), encoding="utf-8")
        voulus = _voulus(raw_dir, date)
        republies = {mm.group(1) for nom, _ in fichiers if (mm := _MOTIF.search("/" + nom))}
        for chemin in supprimes:
            mm = _MOTIF.search("/" + chemin)
            if not mm or mm.group(1) not in voulus:
                continue
            # Un texte qui change d'etat (en vigueur / non en vigueur) change de dossier dans l'archive :
            # la DILA supprime l'ancien et republie le texte dans la meme archive quotidienne.
            if mm.group(2) is None and mm.group(1) in republies:
                continue
            cible = dest / mm.group(1) / (mm.group(2) or "")
            if cible.is_dir():
                shutil.rmtree(cible)
            else:
                cible.unlink(missing_ok=True)
        for nom, raw in fichiers:
            mm = _MOTIF.search("/" + nom)
            if mm and mm.group(2) and "/article/" in nom and mm.group(1) in voulus:
                cible = dest / mm.group(1) / mm.group(2)
                cible.parent.mkdir(parents=True, exist_ok=True)
                cible.write_bytes(raw)
        with journal.open("a", encoding="utf-8") as f:
            f.write(h + "\n")
        appliques.append(h)
    return appliques


class SourceCode:
    """Une source par code (interface attendue par ingest.run : SOURCE_ID + collect)."""

    def __init__(self, code: Code):
        self.code = code
        self.SOURCE_ID = code.source_id

    def collect(self, raw_dir: Path, *, date_recuperation: str) -> Iterator[legi.Passage]:
        dossier = extraire(raw_dir) / self.code.legitext
        version = f"archive DILA LEGI du {dila.date_corpus(raw_dir, 'legi')}"
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
        _, _, date = _dossier(raw_dir)
        racine = extraire(raw_dir)
        version = f"archive DILA LEGI du {dila.date_corpus(raw_dir, 'legi')}"
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
