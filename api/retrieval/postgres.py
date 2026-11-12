"""Moteur de recherche PostgreSQL : plein texte francais (tsvector) + pgvector, fusion RRF.

Meme comportement que LocalRetriever (references citees d'abord, textes avant jurisprudence,
une entree par decision). Schema : db/schema.sql. Active avec RETRIEVER=postgres.
"""

from __future__ import annotations

from api.references import extraire
from api.textes import SOURCES_CASSATION, cibles_article, meme_loi
from api.retrieval.base import (SEUIL_COUVERTURE, Complement, Hit, Reclasseur, assembler, construire_groupe,
                                groupes, termes)

N_CANDIDATS = 50
COLONNES = "id, source_id, type, numero, titre, entete, texte, url, version, date_recuperation, empreinte, meta"


def _ligne(r) -> dict:
    return {
        "id": r[0], "source_id": r[1], "type": r[2], "numero": r[3], "titre": r[4], "entete": r[5],
        "texte": r[6], "url": r[7], "version": r[8],
        "date_recuperation": r[9].isoformat() if r[9] else None, "empreinte": r[10], "meta": r[11] or {},
    }


class PostgresRetriever:
    mode = "postgres"

    def __init__(self, database_url: str):
        from psycopg_pool import ConnectionPool  # dependance optionnelle

        if not database_url:
            raise ValueError("DATABASE_URL requis pour RETRIEVER=postgres")
        self._pool = ConnectionPool(database_url, min_size=1, max_size=5, open=True)

    def _q(self, sql: str, params: tuple | dict = ()) -> list[tuple]:
        with self._pool.connection() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def _toutes_sources(self) -> tuple[str, ...]:
        if not hasattr(self, "_sources_cache"):
            self._sources_cache = tuple(r[0] for r in self._q("SELECT DISTINCT source_id FROM passages"))
        return self._sources_cache

    def _par_reference(self, question: str, sources) -> list[dict]:
        refs = extraire(question)
        autorisees = set(sources) if sources else None
        ok = lambda s: autorisees is None or s in autorisees  # noqa: E731
        out: list[dict] = []
        for num in refs.articles:
            if refs.lois and ok("lois"):
                rows = self._q(f"SELECT {COLONNES} FROM passages WHERE source_id = 'lois' AND numero = %s"
                               " AND en_vigueur IS NOT FALSE", (num,))
                trouves = [p for p in map(_ligne, rows)
                           if any(meme_loi(c, (p.get("meta") or {}).get("code") or "") for c in refs.lois)]
                if trouves:
                    out.extend(trouves)
                    continue
                if not refs.codes:
                    continue
            for src in cibles_article(num, refs.codes, refs.constitution):
                if not ok(src):
                    continue
                rows = self._q(f"SELECT {COLONNES} FROM passages WHERE source_id = %s AND numero = %s"
                               " AND en_vigueur IS NOT FALSE", (src, num))
                if rows:
                    out.extend(_ligne(r) for r in rows)
                    break
        for dec in refs.decisions_cc:
            num, nature = dec.split()
            if ok("decisions_conseil_constitutionnel"):
                rows = self._q(f"SELECT {COLONNES} FROM passages WHERE source_id = 'decisions_conseil_constitutionnel'"
                               " AND meta->>'numero' = %s AND meta->>'nature' = %s ORDER BY id LIMIT 3", (num, nature))
                out.extend(_ligne(r) for r in rows)
        for pv in refs.pourvois:
            for src in SOURCES_CASSATION:
                if ok(src):
                    rows = self._q(f"SELECT {COLONNES} FROM passages WHERE source_id = %s"
                                   " AND meta->'numeros_pourvoi' ? %s ORDER BY id LIMIT 3", (src, pv.replace(".", "")))
                    out.extend(_ligne(r) for r in rows)
        return out

    def _lexical(self, texte: str, sources: tuple[str, ...]) -> list[tuple[str, dict]]:
        mots = termes(texte, garder_accents=True)
        if not mots:
            return []
        rows = self._q(
            f"SELECT {COLONNES} FROM passages, websearch_to_tsquery('french', %s) q"
            " WHERE tsv @@ q AND source_id = ANY(%s) AND en_vigueur IS NOT FALSE"
            " ORDER BY ts_rank_cd(tsv, q) DESC LIMIT %s",
            (" or ".join(mots), list(sources), N_CANDIDATS),
        )
        return [(r[0], _ligne(r)) for r in rows]

    def _vectoriel(self, vecteur: list[float], sources: tuple[str, ...]) -> list[tuple[str, dict]]:
        lit = "[" + ",".join(f"{x:.7g}" for x in vecteur) + "]"
        rows = self._q(
            f"SELECT {COLONNES} FROM passages WHERE embedding IS NOT NULL AND source_id = ANY(%s)"
            " AND en_vigueur IS NOT FALSE ORDER BY embedding <=> %s::vector LIMIT %s",
            (list(sources), lit, N_CANDIDATS),
        )
        return [(r[0], _ligne(r)) for r in rows]

    def _suggestions(self, complement: Complement | None, sources: tuple[str, ...]) -> list[dict]:
        out: list[dict] = []
        for src, num in (complement.suggestions if complement else []):
            if src in sources:
                rows = self._q(f"SELECT {COLONNES} FROM passages WHERE source_id = %s AND numero = %s"
                               " AND en_vigueur IS NOT FALSE", (src, num))
                out.extend(_ligne(r) for r in rows)
        return out

    def _groupe(self, question: str, sources: tuple[str, ...], k: int, vecteur,
                complement: Complement | None = None, reclasseur: Reclasseur | None = None) -> list[Hit]:
        if not sources:
            return []
        classements: dict[str, list[tuple[str, dict]]] = {"lexical": self._lexical(question, sources)}
        vectoriel = self.couverture(sources) >= SEUIL_COUVERTURE
        if vecteur is not None and vectoriel:
            classements["vecteur"] = self._vectoriel(vecteur, sources)
        if complement and complement.reformulation:
            classements["lexical_reformulation"] = self._lexical(complement.reformulation, sources)
            if complement.vecteur_reformulation is not None and vectoriel:
                classements["vecteur_reformulation"] = self._vectoriel(complement.vecteur_reformulation, sources)
        return construire_groupe(classements, k, question=question, reclasseur=reclasseur,
                                 suggestions=self._suggestions(complement, sources))

    def search(self, question, *, sources, k, query_vector=None, complement: Complement | None = None,
               reclasseur: Reclasseur | None = None):
        refs = [Hit(p, float("inf"), {"reference"}) for p in self._par_reference(question, sources)]
        textes, juris = groupes(sources, self._toutes_sources())
        return assembler(refs, self._groupe(question, textes, k, query_vector, complement, reclasseur),
                         self._groupe(question, juris, k, query_vector, complement, reclasseur), k)

    def couverture(self, sources: tuple[str, ...] | None) -> float:
        srcs = list(sources or self._toutes_sources())
        total, vect = self._q("SELECT count(*), count(embedding) FROM passages"
                              " WHERE source_id = ANY(%s) AND en_vigueur IS NOT FALSE", (srcs,))[0]
        return vect / total if total else 0.0

    def get(self, passage_id: str) -> dict | None:
        rows = self._q(f"SELECT {COLONNES} FROM passages WHERE id = %s", (passage_id,))
        return _ligne(rows[0]) if rows else None

    def versions(self, source_id: str, numero: str) -> list[dict]:
        rows = self._q(f"SELECT {COLONNES} FROM passages WHERE source_id = %s AND numero = %s ORDER BY date_debut",
                       (source_id, numero))
        return [_ligne(r) for r in rows]

    def stats(self) -> dict:
        n, e = self._q("SELECT count(*), count(embedding) FROM passages")[0]
        return {"moteur": self.mode, "passages": n, "embeddings": e, "couverture": round(self.couverture(None), 3)}
