"""Code civil depuis l'archive DILA LEGI (toutes les versions d'articles, datees).

1 passage = 1 version d'article (identifiant LEGIARTI). Les versions anciennes sont
conservees avec en_vigueur = false pour pouvoir repondre "dans sa redaction applicable
au litige" ; la recherche filtre par defaut sur les versions en vigueur.

L'archive LEGI complete (~1,2 Go) n'est parcourue qu'une fois : les fichiers du Code civil
sont extraits dans data/raw/dila/extrait_code_civil_<date>/ puis relus depuis le disque.
"""

from __future__ import annotations

import re
import tarfile
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from datetime import date
from pathlib import Path

from ingest import dila
from ingest.jurisprudence import date_fr
from ingest.models import Passage

SOURCE_ID = "code_civil"
FONDS = "legi"
CODE_ID = "LEGITEXT000006070721"  # Code civil (verifie : TITREFULL = "Code civil")
CODE_NOM = "Code civil"
DATE_INFINIE = "2999-01-01"

ETATS = {
    "VIGUEUR": "en vigueur",
    "MODIFIE": "modifié",
    "ABROGE": "abrogé",
    "TRANSFERE": "transféré",
    "MODIFIE_MORT_NE": "jamais entré en vigueur",
    "VIGUEUR_DIFF": "entrée en vigueur différée",
    "ABROGE_DIFF": "en vigueur, abrogation différée",
}

# Lien Legifrance vers une version d'article (format a confirmer en navigateur).
URL_ARTICLE = "https://www.legifrance.gouv.fr/codes/article_lc/{id}"


def extraire(archive: Path, dest: Path) -> None:
    """Extrait les seuls fichiers du code depuis l'archive LEGI (operation longue, faite une fois)."""
    tmp = dest.with_name(dest.name + ".partiel")
    tmp.mkdir(parents=True, exist_ok=True)
    marqueur = f"/{CODE_ID}/"
    with tarfile.open(archive, "r|gz") as tar:
        for m in tar:
            if m.isfile() and marqueur in m.name and m.name.endswith(".xml"):
                f = tar.extractfile(m)
                if f is None:
                    continue
                cible = tmp / m.name
                cible.parent.mkdir(parents=True, exist_ok=True)
                cible.write_bytes(f.read())
    tmp.rename(dest)


def _couvre(el: ET.Element, date: str) -> bool:
    return el.get("debut", "") <= date < el.get("fin", DATE_INFINIE)


def plan(root: ET.Element, date: str) -> list[str]:
    """Chemin Livre > Titre > Chapitre... applicable a la date de debut de la version."""
    chemin: list[str] = []
    noeud = root.find("CONTEXTE/TEXTE")
    while noeud is not None:
        tm = noeud.find("TM")
        if tm is None:
            break
        titres = tm.findall("TITRE_TM")
        choisi = next((t for t in titres if _couvre(t, date)), titres[-1] if titres else None)
        if choisi is not None:
            chemin.append(dila.clean("".join(choisi.itertext())))
        noeud = tm
    return chemin


def parse_article(raw: bytes, *, date_recuperation: str, version_archive: str,
                  source_id: str = SOURCE_ID, nom: str | None = CODE_NOM) -> Passage | None:
    """nom=None : nom du texte lu dans l'article (lois et ordonnances)."""
    root = ET.fromstring(raw)
    if root.tag != "ARTICLE":
        return None
    art_id = dila.text_of(root, "META/META_COMMUN/ID")
    num = dila.text_of(root, "META/META_SPEC/META_ARTICLE/NUM")
    etat = dila.text_of(root, "META/META_SPEC/META_ARTICLE/ETAT")
    debut = dila.text_of(root, "META/META_SPEC/META_ARTICLE/DATE_DEBUT")
    fin = dila.text_of(root, "META/META_SPEC/META_ARTICLE/DATE_FIN")
    # le fichier contient aussi un CONTENU de NOTA : on cible BLOC_TEXTUEL
    bloc = root.find("BLOC_TEXTUEL/CONTENU")
    alineas = dila.contenu_lines(ET.tostring(bloc, encoding="unicode")) if bloc is not None else []
    if not num or not alineas:
        return None
    nota_el = root.find("NOTA/CONTENU")
    nota = " ".join(dila.contenu_lines(ET.tostring(nota_el, encoding="unicode"))) if nota_el is not None else ""

    # ABROGE_DIFF : version applicable aujourd'hui dont l'abrogation est deja programmee (ex. refonte du Code de
    # procedure penale au 1er janvier 2029). Elle est en vigueur jusqu'a cette date : la compter hors vigueur
    # retirait 3 718 articles actuels de la recherche (constate le 2026-11-12). VIGUEUR_DIFF : pas encore en vigueur.
    en_vigueur = etat == "VIGUEUR" or (etat == "ABROGE_DIFF" and bool(fin) and fin > date.today().isoformat())
    chemin = plan(root, debut)
    if nom is None:
        titre_txt = root.find("CONTEXTE/TEXTE/TITRE_TXT")
        nom = (titre_txt.get("c_titre_court") or dila.clean("".join(titre_txt.itertext()))) if titre_txt is not None else "Texte"
        texte_id = titre_txt.get("id_txt") if titre_txt is not None else None
    else:
        texte_id = None
    # DATE_FIN absente : traitee comme « sans date de fin » (sinon l'entete affichait « du ... au »).
    sans_fin = not fin or fin == DATE_INFINIE
    fin_txt = "" if sans_fin else f" au {date_fr(fin)}"
    periode = f"depuis le {date_fr(debut)}" if not fin_txt else f"du {date_fr(debut)}{fin_txt}"
    statut = ETATS.get(etat, etat.lower())
    meta = {
        "code": nom,
        "id_legi": art_id,
        "etat": etat,
        "en_vigueur": en_vigueur,
        "date_debut": debut,
        "date_fin": None if sans_fin else fin,
        "plan": chemin,
    }
    if nota:
        meta["nota"] = nota
    if texte_id:
        meta["id_texte"] = texte_id
    return Passage(
        id=f"{source_id}:{art_id}",
        source_id=source_id,
        type="article",
        numero=num,
        titre=" > ".join(chemin) or None,
        alineas=alineas,
        url=URL_ARTICLE.format(id=art_id),
        version=f"Version {periode}, article {statut} ({version_archive})",
        date_recuperation=date_recuperation,
        meta=meta,
        entete=f"{nom}, article {num} ({statut}, {periode})" + (f" - {chemin[-1]}" if chemin else ""),
    )


def _cle_num(p: Passage):
    parts = re.split(r"(\d+)", p.numero or "")
    return ([int(x) if x.isdigit() else x for x in parts], p.meta["date_debut"])


def collect(raw_dir: Path, *, date_recuperation: str) -> Iterator[Passage]:
    archive = dila.latest_archive(raw_dir, FONDS)
    date = archive.name.split("_")[-1][:8]
    dossier = raw_dir / f"extrait_code_civil_{date}"
    if not dossier.exists():
        print(f"  extraction du Code civil depuis {archive.name} (quelques minutes)...", flush=True)
        extraire(archive, dossier)
    version_archive = f"archive DILA LEGI du {dila.archive_date(archive)}"

    passages: dict[str, Passage] = {}
    for f in dossier.rglob("LEGIARTI*.xml"):
        p = parse_article(f.read_bytes(), date_recuperation=date_recuperation, version_archive=version_archive)
        if p is not None:
            passages.setdefault(p.id, p)
    if sum(1 for p in passages.values() if p.meta["en_vigueur"]) < 2000:
        raise RuntimeError("Moins de 2000 articles en vigueur : extraction incomplete ?")
    yield from sorted(passages.values(), key=_cle_num)
