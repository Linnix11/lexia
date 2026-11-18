"""Mise a jour automatique du corpus depuis l'open data de la DILA (D78).

Usage (chaque nuit sur le serveur, par deploy/mettre_a_jour_corpus.sh) :
    python -m ingest.mise_a_jour             # prepare data/index.nouveau s'il y a du nouveau
    python -m ingest.mise_a_jour --forcer    # meme sans nouvelle archive

Etapes :
  1. telecharge dans data/raw/dila les archives LEGI, CASS, JADE et CONSTIT absentes : l'archive globale
     la plus recente et les archives quotidiennes publiees depuis. Une nouvelle archive globale remplace
     l'ancienne, ses archives quotidiennes et son extraction ;
  2. s'arrete (code 3) si l'index actuel a deja ete construit avec exactement ces archives ;
  3. reimporte les sources DILA (data/passages). Les autres (Constitution, page du Conseil constitutionnel)
     gardent leur fichier, reconstitue depuis l'index actuel s'il manque ; une source hors DILA active dans
     le registre mais absente de l'index (traites de l'Union, D98) est telechargee une fois, sans bloquer la
     mise a jour si son site ne repond pas ;
  4. calcule les embeddings des seuls passages nouveaux ou modifies (cache data/embeddings, amorce depuis
     l'index actuel s'il est vide) ;
  5. construit data/index.nouveau et le compare a l'index actuel (garde-fous, code 1 en cas d'ecart).

Le remplacement de data/index et le redemarrage du service sont faits par le script shell, qui revient
a l'index precedent si le service ne repond plus.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import sqlite3
import sys
from argparse import Namespace
from pathlib import Path

import httpx
import numpy as np
import yaml

from ingest import build_index, dila, embed, run

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "dila"
INDEX = ROOT / "data" / "index"
NOUVEAU = ROOT / "data" / "index.nouveau"
FONDS = ("legi", "cass", "jade", "constit")
ARCHIVES = "archives.txt"  # archives DILA lues pour construire un index, ecrit a cote de lui
RIEN_DE_NOUVEAU = 3
SEUIL = 0.98  # le nouvel index garde au moins 98 % des passages et des embeddings de l'actuel


def lister(client: httpx.Client, fonds: str) -> list[str]:
    """Noms des archives publiees pour un fonds (globale et quotidiennes), dans l'ordre chronologique."""
    r = client.get(f"{dila.BASE_URL}/{fonds.upper()}/")
    r.raise_for_status()
    motif = rf'href="((?:Freemium_{fonds}_global|{fonds.upper()})_\d{{8}}-\d{{6}}\.tar\.gz)"'
    return sorted(set(re.findall(motif, r.text)), key=lambda n: dila.horodatage(Path(n)))


def telecharger(client: httpx.Client, url: str, cible: Path) -> None:
    partiel = cible.with_name(cible.name + ".partiel")
    with client.stream("GET", url) as r:
        r.raise_for_status()
        attendu = int(r.headers.get("content-length") or 0)
        with partiel.open("wb") as f:
            for bloc in r.iter_bytes(1 << 20):
                f.write(bloc)
    if attendu and partiel.stat().st_size != attendu:
        partiel.unlink()
        raise RuntimeError(f"{cible.name} : telechargement incomplet")
    partiel.rename(cible)


def synchroniser(client: httpx.Client, raw_dir: Path, fonds: str) -> list[str]:
    """Telecharge les archives manquantes d'un fonds ; renvoie les noms telecharges."""
    noms = lister(client, fonds)
    globales = [n for n in noms if n.startswith("Freemium_")]
    if not globales:
        raise RuntimeError(f"Aucune archive globale publiee pour {fonds.upper()}")
    globale = globales[-1]
    depuis = dila.horodatage(Path(globale))
    voulues = [globale] + [n for n in noms if not n.startswith("Freemium_") and dila.horodatage(Path(n)) > depuis]
    nouvelles = []
    for nom in voulues:
        if not (raw_dir / nom).exists():
            print(f"  telechargement de {nom}", flush=True)
            telecharger(client, f"{dila.BASE_URL}/{fonds.upper()}/{nom}", raw_dir / nom)
            nouvelles.append(nom)
    if globale in nouvelles:
        purger(raw_dir, fonds, depuis)
    return nouvelles


def purger(raw_dir: Path, fonds: str, depuis: str) -> None:
    """Retire ce qui precede la nouvelle archive globale : ancienne globale, ses archives quotidiennes,
    son extraction et son inventaire."""
    for p in [*raw_dir.glob(f"Freemium_{fonds}_global_*.tar.gz"), *raw_dir.glob(f"{fonds.upper()}_*.tar.gz")]:
        if dila.horodatage(p) < depuis:
            p.unlink()
    if fonds == "legi":
        for p in [*raw_dir.glob("extrait_legi_*"), *raw_dir.glob("inventaire_legi_*.json")]:
            if re.search(r"_(\d{8})", p.name).group(1) < depuis[:8]:
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()


def archives_lues(raw_dir: Path) -> list[str]:
    return sorted(p.name for f in FONDS for p in [dila.latest_archive(raw_dir, f), *dila.increments(raw_dir, f)])


def sources_dila() -> list[str]:
    return sorted(s for s, m in run.SOURCES.items() if not hasattr(m, "fetch"))


def reconstituer(index_dir: Path, passages_dir: Path, a_garder: set[str]) -> list[str]:
    """Recree depuis l'index le fichier des sources hors DILA qui n'en ont pas (premier passage sur le
    serveur, ou ne sont envoyes que les index)."""
    if not (index_dir / "lexia.sqlite").exists():
        return []
    faits = []
    con = sqlite3.connect(index_dir / "lexia.sqlite")
    for (src,) in con.execute("SELECT DISTINCT source_id FROM passages"):
        f = passages_dir / f"{src}.jsonl"
        if src in a_garder or f.exists():
            continue
        with f.open("w", encoding="utf-8") as out:
            for (data,) in con.execute("SELECT data FROM passages WHERE source_id = ? ORDER BY rowid", (src,)):
                out.write(data + "\n")
        faits.append(src)
    con.close()
    return faits


def sources_actives() -> set[str]:
    registre = yaml.safe_load((ROOT / "registry" / "sources.yaml").read_text(encoding="utf-8"))
    return {s["id"] for s in registre["sources"] if s.get("statut") == "actif"}


def ajouter_nouvelles(passages_dir: Path, actives: set[str], importer=None) -> tuple[list[str], list[str]]:
    """Sources hors DILA actives sans fichier de passages (ni dans l'index, sinon reconstituer() l'a recree) :
    telechargees une fois. Un echec n'arrete pas la mise a jour : la source sera retentee la nuit suivante.
    Renvoie (ajoutees, en echec). Une source en attente d'autorisation (statut non actif) n'est jamais lue."""
    importer = importer or (lambda s: run.ingest(s, Namespace(html=None)))
    ajoutees, echecs = [], []
    for s, m in sorted(run.SOURCES.items()):
        if not hasattr(m, "fetch") or s not in actives or (passages_dir / f"{s}.jsonl").exists():
            continue
        try:
            importer(s)
            ajoutees.append(s)
        except Exception as e:  # site indisponible, structure changee (ParseError)...
            print(f"  {s} non ajoutee : {e}", file=sys.stderr)
            echecs.append(s)
    return ajoutees, echecs


def amorcer_cache(index_dir: Path, cache_dir: Path) -> int:
    """Premier passage sur une machine (le serveur) : ajoute au cache les vecteurs de l'index en service
    qui y manquent (meme id, meme empreinte), pour ne calculer ensuite que les passages nouveaux ou modifies.
    Additif : le cache peut deja contenir des lignes calculees ailleurs (Mac) pour de nouvelles sources.
    Fait une fois par modele (marqueur .amorce_*) : ensuite, l'index est toujours construit depuis le cache.
    Les vecteurs de l'index sont normalises, ce que build_index refait de toute facon. Renvoie le nombre ajoute."""
    if not (index_dir / "vectors.npy").exists():
        return 0
    model = (index_dir / "vectors_model.txt").read_text().strip()
    marqueur = cache_dir / f".amorce_{model.replace('/', '_')}"
    if marqueur.exists():
        return 0
    cache_dir.mkdir(parents=True, exist_ok=True)
    presents = {(r["id"], r["empreinte"]) for f in cache_dir.glob("*.jsonl") for r in embed.iter_cache(f, model)}
    ids = json.loads((index_dir / "vectors_ids.json").read_text())
    vecs = np.load(index_dir / "vectors.npy", mmap_mode="r")
    con = sqlite3.connect(index_dir / "lexia.sqlite")
    infos = {pid: (src, emp) for pid, src, emp in con.execute("SELECT id, source_id, empreinte FROM passages")}
    con.close()
    fichiers: dict[str, object] = {}
    ajoutes = 0
    try:
        for i, pid in enumerate(ids):
            if pid not in infos or (pid, infos[pid][1]) in presents:
                continue
            src, emp = infos[pid]
            if src not in fichiers:
                fichiers[src] = (cache_dir / f"{src}.jsonl").open("a", encoding="utf-8")
            ajoutes += 1
            b64 = base64.b64encode(np.asarray(vecs[i], dtype="<f4").tobytes()).decode("ascii")
            fichiers[src].write(json.dumps({"id": pid, "empreinte": emp, "model": model, "dim": vecs.shape[1],
                                            "b64": b64}) + "\n")
    finally:
        for f in fichiers.values():
            f.close()
    marqueur.write_text(f"{ajoutes}\n")
    return ajoutes


def compter(index_dir: Path) -> tuple[int, int, set[str]]:
    con = sqlite3.connect(index_dir / "lexia.sqlite")
    n = con.execute("SELECT count(*) FROM passages").fetchone()[0]
    sources = {s for (s,) in con.execute("SELECT DISTINCT source_id FROM passages")}
    con.close()
    return n, len(json.loads((index_dir / "vectors_ids.json").read_text())), sources


def verifier(actuel: Path, nouveau: Path) -> list[str]:
    """Ecarts qui empechent de mettre le nouvel index en service (liste vide : tout va bien)."""
    n2, e2, s2 = compter(nouveau)
    if not (actuel / "lexia.sqlite").exists():
        return [] if n2 else ["nouvel index vide"]
    n1, e1, s1 = compter(actuel)
    ecarts = []
    if n2 < SEUIL * n1:
        ecarts.append(f"passages : {n2} contre {n1} dans l'index actuel")
    if e2 < SEUIL * e1:
        ecarts.append(f"embeddings : {e2} contre {e1} dans l'index actuel")
    if s1 - s2:
        ecarts.append(f"sources disparues : {', '.join(sorted(s1 - s2))}")
    return ecarts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--forcer", action="store_true", help="Reconstruire meme sans nouvelle archive")
    parser.add_argument("--sans-telechargement", action="store_true", help="Utiliser les archives deja presentes")
    args = parser.parse_args(argv)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not args.sans_telechargement:
        print("== Archives DILA", flush=True)
        with httpx.Client(headers={"User-Agent": run.USER_AGENT}, timeout=120, follow_redirects=True) as client:
            for f in FONDS:
                synchroniser(client, RAW_DIR, f)
    lues = archives_lues(RAW_DIR)
    deja = (INDEX / ARCHIVES).read_text().split() if (INDEX / ARCHIVES).exists() else []
    if lues == deja and not args.forcer:
        print("Rien de nouveau : l'index actuel a ete construit avec ces archives.")
        return RIEN_DE_NOUVEAU

    print("== Import des sources", flush=True)
    for s in sources_dila():
        run.ingest(s, Namespace(html=None))
    if refaits := reconstituer(INDEX, build_index.PASSAGES_DIR, set(sources_dila())):
        print(f"  reconstitues depuis l'index actuel : {', '.join(refaits)}")
    ajoutees, _ = ajouter_nouvelles(build_index.PASSAGES_DIR, sources_actives())
    if ajoutees:
        print(f"  nouvelles sources : {', '.join(ajoutees)}")

    print("== Embeddings des passages nouveaux ou modifies", flush=True)
    if n := amorcer_cache(INDEX, embed.CACHE_DIR):
        print(f"  cache amorce avec les {n} vecteurs de l'index actuel")
    embed.main(["--all"])

    print("== Nouvel index", flush=True)
    build_index.build(index_dir=NOUVEAU)
    (NOUVEAU / ARCHIVES).write_text("\n".join(lues) + "\n")
    if ecarts := verifier(INDEX, NOUVEAU):
        print("Nouvel index refuse : " + " ; ".join(ecarts), file=sys.stderr)
        return 1
    n, e, _ = compter(NOUVEAU)
    print(f"Nouvel index pret : {n} passages, {e} embeddings ({dila.date_corpus(RAW_DIR, 'legi')} pour les textes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
