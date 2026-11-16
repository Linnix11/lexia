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


def horodatage(path: Path) -> str:
    """'Freemium_legi_global_20261108-140000.tar.gz' ou 'LEGI_20261114-210430.tar.gz' -> '20261108-140000'."""
    m = re.search(r"(\d{8}-\d{6})\.tar\.gz$", path.name)
    return m.group(1) if m else ""


def increments(raw_dir: Path, fonds: str) -> list[Path]:
    """Archives quotidiennes « <FONDS>_<horodatage>.tar.gz » posterieures a l'archive globale, de la plus
    ancienne a la plus recente. La DILA les publie chaque soir avec les seuls documents modifies (D78)."""
    depuis = horodatage(latest_archive(raw_dir, fonds))
    return sorted((p for p in raw_dir.glob(f"{fonds.upper()}_*.tar.gz") if horodatage(p) > depuis), key=horodatage)


def date_corpus(raw_dir: Path, fonds: str) -> str:
    """'2026-11-08', ou '2026-11-08, mise à jour du 2026-11-15' quand des archives quotidiennes s'y ajoutent."""
    base = archive_date(latest_archive(raw_dir, fonds))
    incs = increments(raw_dir, fonds)
    if not incs:
        return base
    h = horodatage(incs[-1])
    return f"{base}, mise à jour du {h[:4]}-{h[4:6]}-{h[6:8]}"


_ID_DILA = re.compile(r"[A-Z]+(?:TEXT|ARTI|SCTA)\d{12}")


def lire_increment(archive: Path) -> tuple[list[str], list[tuple[str, bytes]]]:
    """(chemins supprimes, [(chemin, contenu XML)]) d'une archive quotidienne, chemins sans l'horodatage
    de tete. La liste des suppressions (liste_suppression_*.dat) donne un chemin par ligne, suivi de « D »."""
    supprimes: list[str] = []
    fichiers: list[tuple[str, bytes]] = []
    with tarfile.open(archive, "r:gz") as tar:
        for m in tar.getmembers():
            if not m.isfile():
                continue
            nom = m.name.split("/", 1)[1] if "/" in m.name else m.name
            f = tar.extractfile(m)
            if f is None:
                continue
            if nom.startswith("liste_suppression"):
                supprimes += [ligne.split()[0] for ligne in f.read().decode("utf-8", "replace").splitlines()
                              if ligne.strip()]
            elif nom.endswith(".xml"):
                fichiers.append((nom, f.read()))
    return supprimes, fichiers


def id_document(chemin: str) -> str:
    """Identifiant DILA d'un document ou d'un dossier : dernier identifiant du chemin."""
    ids = _ID_DILA.findall(chemin)
    return ids[-1] if ids else chemin


def iter_xml_a_jour(raw_dir: Path, fonds: str, path_filter=None) -> Iterator[tuple[str, bytes]]:
    """Comme iter_xml sur l'archive globale, mais a jour des archives quotidiennes : un document modifie
    est lu dans sa derniere version, un document supprime est ignore. Les archives quotidiennes sont
    petites (quelques Mo) : leur contenu est garde en memoire, l'archive globale est lue en flux."""
    recents: dict[str, tuple[str, bytes]] = {}
    supprimes: set[str] = set()
    for inc in increments(raw_dir, fonds):
        chemins, fichiers = lire_increment(inc)
        for c in chemins:
            recents.pop(id_document(c), None)
            supprimes.add(id_document(c))
        for nom, raw in fichiers:
            if path_filter is None or path_filter(nom):
                recents[id_document(nom)] = (nom, raw)
                supprimes.discard(id_document(nom))
    for nom, raw in iter_xml(latest_archive(raw_dir, fonds), path_filter):
        if id_document(nom) not in recents and id_document(nom) not in supprimes:
            yield nom, raw
    yield from recents.values()


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
