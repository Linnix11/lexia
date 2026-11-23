"""Donnees des pages publiques prerendues (D116) : formules et matieres, ecrites pour le site.

Les pages publiques du site (accueil, tarifs, matieres) sont compilees en HTML a la publication, sans appel a
l'API. Leurs chiffres viennent de ce fichier, tire de `api/plans.py`, `api/matieres.py` et du registre des
sources : une seule verite. Apres une modification des formules, des matieres ou du registre :

    .venv/bin/python -m api.donnees_publiques

puis committer `web/src/site/donnees-publiques.json` et `web/src/site/contenu/noms-sources.json` (le test `tests/test_pages_publiques.py` echoue sinon).

Citations des articles (`contenu/citations.json`) : relues dans l'index (data/index ou LEXIA_INDEX) ; chaque nuit,
le serveur compare la copie publiee a son nouvel index et previent l'administrateur (ecarts_citations).
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path

from api.config import ROOT
from api.matieres import LIBELLES, MATIERES, sources_par_matiere
from api.plans import FORMULES
from api.textes import NOMS
from ingest.sources.legi import url_article

FICHIER = ROOT / "web" / "src" / "site" / "donnees-publiques.json"


def donnees() -> dict:
    return {
        "formules": [f.as_dict() for f in FORMULES.values()],
        # Meme forme que GET /api/matieres (api/main.py), sans les noms des sources : ce fichier est charge par
        # chaque page du site, les noms (noms_sources()) seulement avec les pages des matieres.
        "matieres": [{"id": m, "libelle": LIBELLES.get(m, m), "annee": MATIERES[m].annee, "mots": list(MATIERES[m].mots),
                      "principales": list(MATIERES[m].principales), "sources": list(s)}
                     for m, s in sources_par_matiere().items()],
    }


FICHIER_NOMS = ROOT / "web" / "src" / "site" / "contenu" / "noms-sources.json"


def noms_sources() -> dict[str, str]:
    return {i: NOMS.get(i, i) for s in sources_par_matiere().values() for i in s}


def texte() -> str:
    return json.dumps(donnees(), ensure_ascii=False, indent=1) + "\n"


def texte_noms() -> str:
    return json.dumps(noms_sources(), ensure_ascii=False, indent=1) + "\n"


def ecrire(fichier: Path = FICHIER) -> None:
    fichier.write_text(texte(), encoding="utf-8")
    FICHIER_NOMS.write_text(texte_noms(), encoding="utf-8")


# Articles cites par les pages des matieres et les guides publics, lus dans l'index de recherche (version en
# vigueur). Cle : celle des pages (web/src/site/contenu/) ; valeur : (source, numero), ou l'identifiant du
# passage quand le numero ne suffit pas (plusieurs lois ont un article 23-2).
CITATIONS: dict[str, tuple[str, str] | str] = {
    **{f"code_civil:{n}": ("code_civil", n) for n in (
        "1", "2", "4", "5", "9", "371-1", "544", "1101", "1103", "1104", "1112", "1112-1", "1128", "1130", "1132", "1137", "1140",
        "1178", "1195", "1217", "1219", "1231-1", "1240", "1241", "1242", "1353", "1832")},
    **{f"constitution_1958:{n}": ("constitution_1958", n) for n in (
        "34", "37", "38", "47", "55", "61", "61-1", "62", "64", "66", "88-1")},
    **{f"code_procedure_civile:{n}": ("code_procedure_civile", n) for n in ("12", "455", "542", "561", "604")},
    **{f"code_organisation_judiciaire:{n}": ("code_organisation_judiciaire", n) for n in (
        "L111-1", "L211-3", "L311-1", "L411-1", "L411-2", "L411-3")},
    **{f"code_penal:{n}": ("code_penal", n) for n in ("111-3", "121-1", "121-3", "122-5")},
    "ordonnance_58_1067:23-2": "lois:LEGIARTI000021450778",
    "code_relations_public_administration:L231-1": ("code_relations_public_administration", "L231-1"),
    "code_commerce:L121-1": ("code_commerce", "L121-1"),
    "code_procedure_penale:62-2": ("code_procedure_penale", "62-2"),
    "code_travail:L1221-1": ("code_travail", "L1221-1"),
    **{f"code_justice_administrative:{n}": ("code_justice_administrative", n) for n in ("L111-1", "L211-1", "L211-2")},
    "code_justice_administrative:L521-2": ("code_justice_administrative", "L521-2"),
    "code_justice_administrative:R421-1": ("code_justice_administrative", "R421-1"),
    "code_propriete_personnes_publiques:L2111-1": ("code_propriete_personnes_publiques", "L2111-1"),
    "ddhc_1789:6": ("ddhc_1789", "6"),
    "ddhc_1789:11": ("ddhc_1789", "11"),
    "ddhc_1789:16": ("ddhc_1789", "16"),
    "ddhc_1789:13": ("ddhc_1789", "13"),
}
FICHIER_CITATIONS = ROOT / "web" / "src" / "site" / "contenu" / "citations.json"
# Copie envoyee sur le serveur par deploy/publier.sh (web/src n'y part pas), comparee chaque nuit au nouvel index.
CITATIONS_PUBLIEES = ROOT / "data" / "citations-publiees.json"
# Champs compares : la version cite la date de l'archive DILA, qui change a chaque mise a jour.
CHAMPS_COMPARES = ("texte", "numero", "alineas", "url")
_LIEN_LEGIFRANCE = re.compile(r"^https://www\.legifrance\.gouv\.fr/(?:codes|loda)/article_lc/(LEGIARTI\d+)$")


def _lien(source_id: str, url: str) -> str:
    """Lien Legifrance selon la regle actuelle (ingest.sources.legi.url_article). Un index construit avant B11
    (audit du 2026-11-18) donnait /codes/ a la DDHC et a l'ordonnance 58-1067 (audit du 2026-11-23, D10)."""
    m = _LIEN_LEGIFRANCE.match(url)
    return url_article(source_id, m.group(1)) if m else url


def citations(index: Path) -> dict:
    """Texte, lien officiel et version de chaque article cite, tels que l'index les donne (lien Legifrance
    recalcule selon la regle actuelle)."""
    con = sqlite3.connect(f"file:{index / 'lexia.sqlite'}?mode=ro", uri=True)
    out = {}
    for cle, ref in CITATIONS.items():
        if isinstance(ref, str):
            lignes = con.execute("select data from passages where id = ?", (ref,)).fetchall()
        else:
            lignes = con.execute("select data from passages where source_id = ? and numero = ? and en_vigueur = 1",
                                 ref).fetchall()
        if len(lignes) != 1:
            raise ValueError(f"{cle} : {len(lignes)} versions en vigueur dans l'index au lieu d'une")
        d = json.loads(lignes[0][0])
        out[cle] = {
            "texte": d["entete"].split(", article ")[0].strip(),
            "numero": d["numero"],
            "alineas": [a.strip() for a in d["texte"].split("\n\n") if a.strip()],
            "url": _lien(d["source_id"], d["url"]),
            "version": d.get("version") or "",
        }
    con.close()
    return out


def texte_citations(index: Path) -> str:
    return json.dumps(citations(index), ensure_ascii=False, indent=1) + "\n"


def ecarts_citations(index: Path, fichier: Path = CITATIONS_PUBLIEES) -> list[str]:
    """Articles cites par les pages publiques qui ne sont plus ceux de l'index (texte, numero, lien) ou n'y ont
    plus une seule version en vigueur. Liste vide : pages a jour ; fichier absent : rien a comparer.

    Appele chaque nuit apres la construction de l'index (ingest/mise_a_jour.py) : a une date de bascule, une page
    publique pouvait citer une version finie sans que personne ne le sache (audit du 2026-11-23, C5)."""
    if not fichier.exists():
        return []
    publiees = json.loads(fichier.read_text(encoding="utf-8"))
    try:
        actuelles = citations(index)
    except ValueError as e:
        return [str(e)]
    ecarts = []
    for cle in sorted(set(publiees) | set(actuelles)):
        avant, apres = publiees.get(cle), actuelles.get(cle)
        if avant is None or apres is None:
            ecarts.append(f"{cle} : {'absent des pages publiees' if avant is None else 'plus cite par le depot'}")
            continue
        if champs := [c for c in CHAMPS_COMPARES if avant.get(c) != apres.get(c)]:
            ecarts.append(f"{cle} : {', '.join(champs)} change(s)")
    return ecarts


if __name__ == "__main__":
    ecrire()
    print(f"{FICHIER.relative_to(ROOT)} ecrit")
    index = Path(os.environ.get("LEXIA_INDEX") or ROOT / "data" / "index")
    if (index / "lexia.sqlite").exists():
        FICHIER_CITATIONS.write_text(texte_citations(index), encoding="utf-8")
        print(f"{FICHIER_CITATIONS.relative_to(ROOT)} ecrit depuis {index}")
    else:
        print(f"index absent ({index}) : citations non relues")
