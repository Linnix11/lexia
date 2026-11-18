"""Lance l'ingestion d'une source et ecrit les passages en JSONL.

Usage :
    python -m ingest.run --source constitution_1958
    python -m ingest.run --source constitution_1958 --html chemin/vers/page.html   # hors ligne
    python -m ingest.run --source decisions_conseil_constitutionnel                # archive DILA CONSTIT
    python -m ingest.run --source judilibre                                         # archive DILA CASS
    python -m ingest.run --source code_civil                                        # archive DILA LEGI
    python -m ingest.run --all

Les sources DILA lisent l'archive la plus recente dans data/raw/dila/
(telecharger depuis https://echanges.dila.gouv.fr/OPENDATA/<FONDS>/).

Sorties :
    data/raw/<source>/<date>.html        copie brute des pages HTML (non commitee)
    data/passages/<source>.jsonl         1 passage par ligne, ordre stable
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import httpx

from ingest.sources import cass, codes, constit, constitution, jade, legi, traites

ROOT = Path(__file__).resolve().parent.parent
DILA_DIR = ROOT / "data" / "raw" / "dila"
SOURCES = {m.SOURCE_ID: m for m in (constitution, constit, cass, legi, jade, *codes.SOURCES, *cass.SOURCES,
                                         *traites.SOURCES)}
USER_AGENT = "LexiaIngest/0.1"


def _passages_html(module, args, now):
    if args.html:
        html = args.html.read_text(encoding="utf-8")
    else:
        with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
            html = module.fetch(client)
        raw_dir = ROOT / "data" / "raw" / module.SOURCE_ID
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / f"{now:%Y%m%dT%H%M%SZ}.html").write_text(html, encoding="utf-8")
    return module.parse(html, date_recuperation=now.isoformat(timespec="seconds"))


def ingest(source_id: str, args) -> Path:
    module = SOURCES[source_id]
    now = datetime.now(timezone.utc)
    if hasattr(module, "fetch"):
        passages = _passages_html(module, args, now)
    else:
        passages = module.collect(DILA_DIR, date_recuperation=now.isoformat(timespec="seconds"))

    out = ROOT / "data" / "passages" / f"{source_id}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".jsonl.tmp")
    types: Counter = Counter()
    seen: set[str] = set()
    version = ""
    with tmp.open("w", encoding="utf-8") as f:
        for p in passages:
            if p.id in seen:
                raise RuntimeError(f"Identifiant en double : {p.id}")
            seen.add(p.id)
            types[p.type] += 1
            version = p.version
            f.write(json.dumps(p.to_dict(), ensure_ascii=False) + "\n")
    if not seen:
        tmp.unlink()
        raise RuntimeError(f"Aucun passage produit pour {source_id}")
    tmp.replace(out)  # le fichier final n'est remplace qu'en cas de succes complet

    detail = ", ".join(f"{n} {t}" for t, n in types.most_common())
    print(f"{source_id}: {len(seen)} passages ({detail}) -> {out.relative_to(ROOT)}")
    print(f"  version : {version}")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--source", choices=sorted(SOURCES))
    group.add_argument("--all", action="store_true", help="Toutes les sources")
    parser.add_argument("--html", type=Path, help="Fichier HTML local au lieu du telechargement (sources HTML)")
    args = parser.parse_args(argv)

    for source_id in (sorted(SOURCES) if args.all else [args.source]):
        ingest(source_id, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
