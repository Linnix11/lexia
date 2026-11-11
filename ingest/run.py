"""Lance l'ingestion d'une source et ecrit les passages en JSONL.

Usage :
    python -m ingest.run --source constitution_1958
    python -m ingest.run --source constitution_1958 --html chemin/vers/page.html   # hors ligne

Sorties :
    data/raw/<source>/<date>.html        copie brute (non commitee)
    data/passages/<source>.jsonl         1 passage par ligne, ordre stable
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

from ingest.sources import constitution

ROOT = Path(__file__).resolve().parent.parent
SOURCES = {constitution.SOURCE_ID: constitution}
USER_AGENT = "LexiaIngest/0.1"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True, choices=sorted(SOURCES))
    parser.add_argument("--html", type=Path, help="Fichier HTML local au lieu du telechargement")
    args = parser.parse_args(argv)

    module = SOURCES[args.source]
    now = datetime.now(timezone.utc)

    if args.html:
        html = args.html.read_text(encoding="utf-8")
    else:
        with httpx.Client(headers={"User-Agent": USER_AGENT}) as client:
            html = module.fetch(client)
        raw_dir = ROOT / "data" / "raw" / args.source
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / f"{now:%Y%m%dT%H%M%SZ}.html").write_text(html, encoding="utf-8")

    passages = module.parse(html, date_recuperation=now.isoformat(timespec="seconds"))

    out = ROOT / "data" / "passages" / f"{args.source}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for p in passages:
            f.write(json.dumps(p.to_dict(), ensure_ascii=False) + "\n")

    n_art = sum(1 for p in passages if p.type == "article")
    print(f"{args.source}: {len(passages)} passages ({n_art} articles) -> {out.relative_to(ROOT)}")
    print(f"version : {passages[0].version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
