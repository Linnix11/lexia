"""Charge les passages et leurs embeddings dans PostgreSQL (DATABASE_URL dans .env).

Usage :
    python -m ingest.load_db --schema          # cree / met a jour les tables (db/schema.sql)
    python -m ingest.load_db --all             # charge toutes les sources de data/passages/
    python -m ingest.load_db --source code_civil

Comportement :
  - passage nouveau            -> insere
  - passage dont le texte a change (empreinte differente) -> mis a jour, embedding remis a NULL
  - passage inchange           -> laisse tel quel
  - passage absent du fichier  -> supprime
  - embeddings du cache (data/embeddings/) appliques aux passages dont l'empreinte correspond.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import yaml

from ingest import embedders
from ingest.embed import CACHE_DIR, decode, iter_cache
from ingest.env import load_env

ROOT = Path(__file__).resolve().parent.parent
PASSAGES_DIR = ROOT / "data" / "passages"
SCHEMA = ROOT / "db" / "schema.sql"
REGISTRY = ROOT / "registry" / "sources.yaml"

COLONNES = (
    "id", "source_id", "type", "numero", "titre", "entete", "texte", "url", "version",
    "date_recuperation", "empreinte", "meta", "en_vigueur", "date_debut", "date_fin", "date_decision",
)


def connect():
    import psycopg  # import tardif : seul ce script en a besoin

    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL manquant dans .env")
    return psycopg.connect(url)


def ligne(p: dict) -> tuple:
    meta = p.get("meta") or {}
    est_texte = "en_vigueur" in meta
    return (
        p["id"], p["source_id"], p["type"], p.get("numero"), p.get("titre"), p.get("entete", ""),
        p["texte"], p["url"], p.get("version", ""), p.get("date_recuperation") or None, p["empreinte"],
        json.dumps(meta, ensure_ascii=False),
        meta.get("en_vigueur") if est_texte else (True if p["source_id"] == "constitution_1958" else None),
        meta.get("date_debut"), meta.get("date_fin"),
        None if est_texte else (meta.get("date") or None),
    )


def charger_sources(conn) -> None:
    sources = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))["sources"]
    with conn.cursor() as cur:
        for s in sources:
            cur.execute(
                """INSERT INTO sources (id, nom, type, autorite, url, statut)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (id) DO UPDATE SET nom = EXCLUDED.nom, type = EXCLUDED.type,
                       autorite = EXCLUDED.autorite, url = EXCLUDED.url, statut = EXCLUDED.statut""",
                (s["id"], s["nom"], s["type"], s.get("autorite"), s.get("url"), s["statut"]),
            )


def charger_passages(conn, source_id: str) -> dict:
    fichier = PASSAGES_DIR / f"{source_id}.jsonl"
    with conn.cursor() as cur:
        cur.execute("INSERT INTO synchros (source_id) VALUES (%s) RETURNING id", (source_id,))
        synchro_id = cur.fetchone()[0]
        cur.execute(
            "CREATE TEMP TABLE tmp_passages (LIKE passages INCLUDING DEFAULTS EXCLUDING GENERATED) ON COMMIT DROP"
        )
        cur.execute("ALTER TABLE tmp_passages DROP COLUMN tsv")
        with cur.copy(f"COPY tmp_passages ({', '.join(COLONNES)}) FROM STDIN") as copy:
            with fichier.open(encoding="utf-8") as f:
                for l in f:
                    copy.write_row(ligne(json.loads(l)))

        cur.execute(
            "DELETE FROM passages WHERE source_id = %s AND id NOT IN (SELECT id FROM tmp_passages)",
            (source_id,),
        )
        supprimes = cur.rowcount
        set_cols = ", ".join(f"{c} = EXCLUDED.{c}" for c in COLONNES if c != "id")
        cur.execute(
            f"""INSERT INTO passages ({', '.join(COLONNES)})
                SELECT {', '.join(COLONNES)} FROM tmp_passages
                ON CONFLICT (id) DO UPDATE SET {set_cols},
                    embedding = NULL, embedding_model = NULL, maj_le = now()
                WHERE passages.empreinte <> EXCLUDED.empreinte
                   OR passages.meta <> EXCLUDED.meta
                   OR passages.version <> EXCLUDED.version
                RETURNING (xmax = 0) AS insere"""
        )
        res = [r[0] for r in cur.fetchall()]
        inseres, modifies = sum(res), len(res) - sum(res)
        cur.execute("SELECT count(*) FROM tmp_passages")
        total = cur.fetchone()[0]
        stats = {"inseres": inseres, "modifies": modifies, "inchanges": total - inseres - modifies, "supprimes": supprimes}
        cur.execute(
            """UPDATE synchros SET fin = now(), inseres = %(inseres)s, modifies = %(modifies)s,
                   inchanges = %(inchanges)s, supprimes = %(supprimes)s, statut = 'ok' WHERE id = %(id)s""",
            {**stats, "id": synchro_id},
        )
        cur.execute("UPDATE sources SET derniere_synchro = now() WHERE id = %s", (source_id,))
    return stats


def charger_embeddings(conn, source_id: str, model: str) -> int:
    cache = CACHE_DIR / f"{source_id}.jsonl"
    if not cache.exists():
        return 0
    with conn.cursor() as cur:
        # jamais de melange de modeles : les vecteurs d'un autre modele sont effaces
        cur.execute("UPDATE passages SET embedding = NULL, embedding_model = NULL"
                    " WHERE source_id = %s AND embedding IS NOT NULL AND embedding_model IS DISTINCT FROM %s",
                    (source_id, model))
        cur.execute(
            "CREATE TEMP TABLE tmp_emb (id text, empreinte char(64), model text, embedding vector(768)) ON COMMIT DROP"
        )
        with cur.copy("COPY tmp_emb (id, empreinte, model, embedding) FROM STDIN") as copy:
            for r in iter_cache(cache, model):
                vec = "[" + ",".join(f"{x:.7g}" for x in decode(r["b64"])) + "]"
                copy.write_row((r["id"], r["empreinte"], r["model"], vec))
        cur.execute(
            """UPDATE passages p SET embedding = t.embedding, embedding_model = t.model
               FROM (SELECT DISTINCT ON (id) * FROM tmp_emb ORDER BY id) t
               WHERE p.id = t.id AND p.empreinte = t.empreinte
                 AND (p.embedding IS NULL OR p.embedding_model IS DISTINCT FROM t.model)"""
        )
        return cur.rowcount


def main(argv: list[str] | None = None) -> int:
    load_env(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--schema", action="store_true", help="Appliquer db/schema.sql")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--source")
    group.add_argument("--all", action="store_true")
    args = parser.parse_args(argv)
    if not (args.schema or args.source or args.all):
        parser.error("indiquer --schema, --source ou --all")

    with connect() as conn:
        if args.schema:
            conn.execute(SCHEMA.read_text(encoding="utf-8"))
            conn.commit()
            print("schema applique")
        if args.source or args.all:
            charger_sources(conn)
            conn.commit()
            sources = sorted(p.stem for p in PASSAGES_DIR.glob("*.jsonl")) if args.all else [args.source]
            for s in sources:
                with conn.transaction():
                    stats = charger_passages(conn, s)
                with conn.transaction():
                    n_emb = charger_embeddings(conn, s, embedders.config_env()[1])
                print(f"{s}: {stats}, embeddings appliques : {n_emb}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
