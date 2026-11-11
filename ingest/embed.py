"""Calcule les embeddings Gemini des passages, avec cache et reprise.

Usage :
    python -m ingest.embed --source constitution_1958
    python -m ingest.embed --all
    python -m ingest.embed --all --limit 500      # s'arrete apres 500 nouveaux embeddings

Le cache data/embeddings/<source>.jsonl contient une ligne par passage :
    {"id", "empreinte", "model", "dim", "b64"}   (b64 = float32 little-endian encode en base64)
Un passage deja calcule avec la meme empreinte et le meme modele n'est jamais recalcule :
le script peut etre interrompu et relance a tout moment (quota gratuit limite).

Passages exclus : versions d'articles qui ne sont plus en vigueur (meta.en_vigueur == false).
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import struct
import sys
import time
from pathlib import Path

import httpx

from ingest.env import load_env

ROOT = Path(__file__).resolve().parent.parent
PASSAGES_DIR = ROOT / "data" / "passages"
CACHE_DIR = ROOT / "data" / "embeddings"
API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents"
BATCH = 100          # maximum accepte par batchEmbedContents
DIM = 768
MAX_CHARS = 20000    # garde-fou sous la limite de tokens du modele


def encode(values: list[float]) -> str:
    return base64.b64encode(struct.pack(f"<{len(values)}f", *values)).decode("ascii")


def decode(b64: str) -> list[float]:
    raw = base64.b64decode(b64)
    return list(struct.unpack(f"<{len(raw) // 4}f", raw))


def load_cache(path: Path, model: str) -> dict[str, str]:
    """id -> empreinte des embeddings deja calcules pour ce modele."""
    done: dict[str, str] = {}
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for line in f:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue  # derniere ligne tronquee par une interruption
                if row.get("model") == model:
                    done[row["id"]] = row["empreinte"]
    return done


def a_calculer(passages_file: Path, done: dict[str, str]):
    with passages_file.open(encoding="utf-8") as f:
        for line in f:
            p = json.loads(line)
            if p.get("meta", {}).get("en_vigueur") is False:
                continue
            if done.get(p["id"]) == p["empreinte"]:
                continue
            texte = f"{p['entete']}\n\n{p['texte']}" if p.get("entete") else p["texte"]
            yield p["id"], p["empreinte"], texte[:MAX_CHARS]


def _retry_delay(resp: httpx.Response, attempt: int) -> float:
    try:
        for d in resp.json()["error"].get("details", []):
            if "retryDelay" in d:
                return float(d["retryDelay"].rstrip("s")) + 1
    except Exception:
        pass
    return min(60 * 2**attempt, 600)


def embed_batch(client: httpx.Client, model: str, textes: list[str]) -> list[list[float]]:
    body = {
        "requests": [
            {
                "model": f"models/{model}",
                "content": {"parts": [{"text": t}]},
                "taskType": "RETRIEVAL_DOCUMENT",
                "outputDimensionality": DIM,
            }
            for t in textes
        ]
    }
    for attempt in range(8):
        resp = client.post(API.format(model=model), json=body, timeout=120)
        if resp.status_code == 200:
            return [e["values"] for e in resp.json()["embeddings"]]
        if resp.status_code in (429, 500, 503):
            delay = _retry_delay(resp, attempt)
            print(f"  HTTP {resp.status_code}, nouvelle tentative dans {delay:.0f} s", flush=True)
            time.sleep(delay)
            continue
        raise RuntimeError(f"Erreur API {resp.status_code} : {resp.text[:300]}")
    raise RuntimeError("Quota toujours depasse apres plusieurs tentatives ; relancer plus tard.")


def run(source_id: str, client: httpx.Client, model: str, limit: int | None, batch: int) -> int:
    passages_file = PASSAGES_DIR / f"{source_id}.jsonl"
    cache = CACHE_DIR / f"{source_id}.jsonl"
    cache.parent.mkdir(parents=True, exist_ok=True)
    done = load_cache(cache, model)
    todo = list(a_calculer(passages_file, done))
    if limit is not None:
        todo = todo[:limit]
    print(f"{source_id}: {len(done)} en cache, {len(todo)} a calculer", flush=True)
    n = 0
    with cache.open("a", encoding="utf-8") as out:
        for i in range(0, len(todo), batch):
            chunk = todo[i : i + batch]
            vectors = embed_batch(client, model, [t for _, _, t in chunk])
            for (pid, emp, _), vec in zip(chunk, vectors, strict=True):
                out.write(json.dumps({"id": pid, "empreinte": emp, "model": model, "dim": len(vec), "b64": encode(vec)}) + "\n")
            out.flush()
            n += len(chunk)
            print(f"  {n}/{len(todo)}", flush=True)
    return n


def main(argv: list[str] | None = None) -> int:
    load_env(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--source")
    group.add_argument("--all", action="store_true")
    parser.add_argument("--limit", type=int, help="Nombre maximum de nouveaux embeddings")
    parser.add_argument("--batch", type=int, default=BATCH)
    args = parser.parse_args(argv)

    key = os.environ.get("GEMINI_API_KEY")
    model = os.environ.get("GEMINI_EMBED_MODEL")
    if not key or not model:
        print("GEMINI_API_KEY et GEMINI_EMBED_MODEL doivent etre definis dans .env", file=sys.stderr)
        return 1

    sources = sorted(p.stem for p in PASSAGES_DIR.glob("*.jsonl")) if args.all else [args.source]
    remaining = args.limit
    with httpx.Client(headers={"x-goog-api-key": key}) as client:
        for s in sources:
            n = run(s, client, model, remaining, min(args.batch, BATCH))
            if remaining is not None:
                remaining -= n
                if remaining <= 0:
                    break
    return 0


if __name__ == "__main__":
    sys.exit(main())
