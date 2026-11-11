"""Construit l'index de recherche local (sans base de donnees) utilise par l'API en developpement.

Usage :
    python -m ingest.build_index

Sorties (data/index/, non commite) :
    lexia.sqlite   passages + index plein texte SQLite FTS5 (BM25, accents ignores)
    vectors.npy    embeddings float32 des passages dont l'empreinte correspond au cache
    vectors_ids.json

A relancer apres ingest.run ou quand de nouveaux embeddings ont ete calcules.
En production, l'API utilise PostgreSQL (db/schema.sql) a la place de cet index.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import numpy as np

from ingest.embed import CACHE_DIR, decode

ROOT = Path(__file__).resolve().parent.parent
PASSAGES_DIR = ROOT / "data" / "passages"
INDEX_DIR = ROOT / "data" / "index"

SCHEMA = """
CREATE TABLE passages (
    rowid       INTEGER PRIMARY KEY,
    id          TEXT UNIQUE NOT NULL,
    source_id   TEXT NOT NULL,
    type        TEXT NOT NULL,
    numero      TEXT,
    doc_id      TEXT,
    en_vigueur  INTEGER,
    empreinte   TEXT NOT NULL,
    data        TEXT NOT NULL
);
CREATE INDEX passages_num ON passages (source_id, numero);
CREATE INDEX passages_doc ON passages (doc_id);
CREATE VIRTUAL TABLE passages_fts USING fts5(
    entete, texte, content='', tokenize='unicode61 remove_diacritics 2'
);
"""


def doc_id(p: dict) -> str:
    meta = p.get("meta") or {}
    return meta.get("id_dila") or meta.get("id_legi") or p["id"]


def en_vigueur(p: dict):
    meta = p.get("meta") or {}
    if "en_vigueur" in meta:
        return int(bool(meta["en_vigueur"]))
    return 1 if p["source_id"] == "constitution_1958" else None


def build(passages_dir: Path = PASSAGES_DIR, index_dir: Path = INDEX_DIR, cache_dir: Path = CACHE_DIR) -> None:
    index_dir.mkdir(parents=True, exist_ok=True)
    tmp = index_dir / "lexia.sqlite.tmp"
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    con.executescript(SCHEMA)
    empreintes: dict[str, str] = {}
    n = 0
    for f in sorted(passages_dir.glob("*.jsonl")):
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                p = json.loads(line)
                p.pop("alineas", None)
                n += 1
                con.execute(
                    "INSERT INTO passages (rowid, id, source_id, type, numero, doc_id, en_vigueur, empreinte, data)"
                    " VALUES (?,?,?,?,?,?,?,?,?)",
                    (n, p["id"], p["source_id"], p["type"], p.get("numero"), doc_id(p), en_vigueur(p),
                     p["empreinte"], json.dumps(p, ensure_ascii=False)),
                )
                con.execute("INSERT INTO passages_fts (rowid, entete, texte) VALUES (?,?,?)",
                            (n, p.get("entete", ""), p["texte"]))
                empreintes[p["id"]] = p["empreinte"]
    con.commit()
    con.close()
    tmp.replace(index_dir / "lexia.sqlite")

    ids: list[str] = []
    vecs: list[list[float]] = []
    for f in sorted(cache_dir.glob("*.jsonl")) if cache_dir.exists() else []:
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if empreintes.get(r["id"]) == r["empreinte"]:
                    ids.append(r["id"])
                    vecs.append(decode(r["b64"]))
    arr = np.asarray(vecs, dtype=np.float32).reshape(len(vecs), -1 if vecs else 0)
    if len(arr):
        arr /= np.linalg.norm(arr, axis=1, keepdims=True)
    np.save(index_dir / "vectors.npy", arr)
    (index_dir / "vectors_ids.json").write_text(json.dumps(ids))
    print(f"index : {n} passages, {len(ids)} embeddings -> {index_dir}")


def main() -> int:
    build()
    return 0


if __name__ == "__main__":
    sys.exit(main())
