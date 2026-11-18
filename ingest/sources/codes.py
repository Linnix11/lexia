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
    # Ajouts du 2026-11-16 (identifiants verifies dans l'archive LEGI du 2026-11-08, TITREFULL).
    Code("code_route", "LEGITEXT000006074228", "Code de la route"),
    Code("code_sante_publique", "LEGITEXT000006072665", "Code de la santé publique"),
    Code("code_rural", "LEGITEXT000006071367", "Code rural et de la pêche maritime"),
    Code("code_douanes", "LEGITEXT000006071570", "Code des douanes"),
    Code("code_impositions_biens_services", "LEGITEXT000044595989", "Code des impositions sur les biens et services"),
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
        _extraire_textes(archive, tmp, voulus)
        tmp.rename(dest)
    else:
        # Code ajoute a CODES apres l'extraction (sur le Mac comme sur le serveur, D78) : seuls les codes
        # absents du dossier sont extraits. Les lois ne sont pas concernees (inventaire et increments).
        manquants = {c.legitext for c in CODES} - {d.name for d in dest.iterdir() if d.is_dir()}
        if manquants:
            print(f"  extraction de {len(manquants)} code(s) ajoute(s) depuis {archive.name}...", flush=True)
            tmp = dest.with_name(dest.name + ".ajout")
            shutil.rmtree(tmp, ignore_errors=True)
            _extraire_textes(archive, tmp, manquants)
            for lt in sorted(manquants):
                if (tmp / lt).is_dir():
                    (tmp / lt).rename(dest / lt)
            shutil.rmtree(tmp, ignore_errors=True)
            # Archive globale = etat du jour de l'archive : les archives quotidiennes deja notees dans le
            # journal sont reappliquees a ces seuls codes, sinon ils resteraient a cette date.
            appliquer_increments(raw_dir, dest, date, seulement=manquants)
    appliquer_increments(raw_dir, dest, date)
    return dest


def _extraire_textes(archive: Path, dest: Path, voulus: set[str]) -> None:
    """Articles des textes voulus, ecrits sous dest/<identifiant du texte>/ (une passe sur l'archive)."""
    dest.mkdir(parents=True, exist_ok=True)
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
            cible = dest / mm.group(1) / mm.group(2)
            cible.parent.mkdir(parents=True, exist_ok=True)
            cible.write_bytes(f.read())


def appliquer_increments(raw_dir: Path, dest: Path, date: str, seulement: set[str] | None = None) -> list[str]:
    """Applique a l'extraction les archives quotidiennes pas encore lues (liste dans dest/.increments) :
    nouvelles lois ajoutees a l'inventaire, articles ecrits par-dessus, dossiers supprimes retires (D78).
    seulement : rattrapage de textes tout juste extraits de l'archive globale. Toutes les archives
    quotidiennes leur sont appliquees, journal ignore et laisse tel quel, inventaire inchange.
    Renvoie les horodatages appliques."""
    journal = dest / ".increments"
    deja = set(journal.read_text().split()) if journal.exists() and seulement is None else set()
    appliques = []
    for inc in dila.increments(raw_dir, "legi"):
        h = dila.horodatage(inc)
        if h in deja:
            continue
        supprimes, fichiers = dila.lire_increment(inc)
        if seulement is None:
            inventaire = _inventaire(raw_dir, date)
            connues = {loi[0] for loi in inventaire["lois"]}
            nouvelles = [loi for nom, raw in fichiers if (loi := _loi(nom, raw)) and loi[0] not in connues]
            if nouvelles:
                inventaire["lois"] += nouvelles
                _fichier_inventaire(raw_dir, date).write_text(json.dumps(inventaire, ensure_ascii=False),
                                                              encoding="utf-8")
        voulus = _voulus(raw_dir, date) if seulement is None else seulement
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
        if seulement is None:
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
                if texte_id == CHARTE_TEXTE and p is not None and p.numero == CHARTE_ARTICLE:
                    continue   # Charte de l'environnement : source a part (SourceCharte)
                if p is not None and p.meta["en_vigueur"] and p.id not in vus:
                    vus.add(p.id)
                    articles.append(p)
            n += len(articles)
            yield from sorted(articles, key=legi._cle_num)
        if n < 1000:
            raise RuntimeError(f"Seulement {n} articles de lois en vigueur : extraction incomplete ?")


# --- Charte de l'environnement (audit du 2026-11-18, B9) ------------------------------------------
# Adossee a la Constitution, elle n'existe dans l'archive LEGI que comme article 2 de la loi constitutionnelle
# n° 2005-205 du 1er mars 2005 : un seul passage de 2 900 caracteres, introuvable par « article 5 de la Charte ».
# Elle est decoupee en preambule et articles 1er a 10, source a part ; l'article 2 de la loi n'est plus repris
# dans « lois » (meme texte en double).
CHARTE_SOURCE = "charte_environnement"
CHARTE_NOM = "Charte de l'environnement"
CHARTE_TEXTE = "JORFTEXT000000790249"  # loi constitutionnelle n° 2005-205 (verifie dans l'archive du 2026-11-08)
CHARTE_ARTICLE = "2"
_ART_CHARTE = re.compile(r"^Art\.\s*(\d+)(?:er)?\.?\s*[-–]\s*(.+)$", re.DOTALL)


def decouper_charte(p: legi.Passage) -> list[legi.Passage]:
    """Article 2 de la loi 2005-205 -> preambule (numero PREAMBULE) et articles 1 a 10 de la Charte."""
    preambule: list[str] = []
    articles: list[tuple[str, list[str]]] = []
    for a in p.alineas[1:]:   # le premier : « La Charte de l'environnement de 2004 est ainsi redigee : »
        m = _ART_CHARTE.match(a.strip())
        if m:
            articles.append((m.group(1), [m.group(2).strip()]))
        elif articles:
            articles[-1][1].append(a)
        else:
            preambule.append(a)
    statut = p.entete[p.entete.index("("):] if "(" in p.entete else ""
    out = []
    for num, alineas in ([("PREAMBULE", preambule)] if preambule else []) + articles:
        libelle = "préambule" if num == "PREAMBULE" else f"article {num}"
        out.append(legi.Passage(
            id=f"{CHARTE_SOURCE}:{p.meta['id_legi']}:{num}", source_id=CHARTE_SOURCE, type="article", numero=num,
            titre=CHARTE_NOM, alineas=alineas, url=p.url, version=p.version, date_recuperation=p.date_recuperation,
            meta={**p.meta, "code": CHARTE_NOM, "plan": []}, entete=f"{CHARTE_NOM}, {libelle} {statut}".strip()))
    return out


class SourceCharte:
    SOURCE_ID = CHARTE_SOURCE

    def collect(self, raw_dir: Path, *, date_recuperation: str) -> Iterator[legi.Passage]:
        version = f"archive DILA LEGI du {dila.date_corpus(raw_dir, 'legi')}"
        out: list[legi.Passage] = []
        for f in (extraire(raw_dir) / CHARTE_TEXTE).rglob("LEGIARTI*.xml"):
            p = legi.parse_article(f.read_bytes(), date_recuperation=date_recuperation, version_archive=version,
                                   source_id=SOURCE_LOIS, nom=None)
            if p is not None and p.numero == CHARTE_ARTICLE and p.meta["en_vigueur"]:
                out += decouper_charte(p)
        if len([p for p in out if p.numero != "PREAMBULE"]) != 10:
            raise RuntimeError(f"Charte de l'environnement : {len(out)} passages au lieu de 11 (texte modifie ?)")
        yield from out


SOURCES = [SourceCode(c) for c in CODES] + [SourceLois(), SourceCharte()]
