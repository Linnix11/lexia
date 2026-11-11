"""Moteur de recherche local : SQLite FTS5 (BM25) + similarite cosinus numpy.

Lit l'index produit par `python -m ingest.build_index`. Pour le developpement et les tests ;
la production utilise PostgresRetriever.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from pathlib import Path

import numpy as np

from api.references import extraire
from api.retrieval.base import SEUIL_COUVERTURE, Hit, assembler, diversifier, doc_de, fusion_rrf, groupes, paires, termes

N_CANDIDATS = 50
log = logging.getLogger("lexia.recherche")


class LocalRetriever:
    mode = "local"

    def __init__(self, index_dir: Path, embed_model: str | None = None):
        db = index_dir / "lexia.sqlite"
        if not db.exists():
            raise FileNotFoundError(f"Index absent : {db}. Lancer `python -m ingest.build_index`.")
        self._con = sqlite3.connect(db, check_same_thread=False)
        self._lock = threading.Lock()
        self._ids: list[str] = []
        self._vecs = np.zeros((0, 0), dtype=np.float32)
        vec_file, ids_file = index_dir / "vectors.npy", index_dir / "vectors_ids.json"
        if vec_file.exists() and ids_file.exists():
            modele_index = (index_dir / "vectors_model.txt").read_text().strip() \
                if (index_dir / "vectors_model.txt").exists() else None
            if embed_model and modele_index and modele_index != embed_model:
                log.warning("Index vectorise avec %s mais EMBED_MODEL=%s : recherche vectorielle desactivee "
                            "(relancer ingest.build_index)", modele_index, embed_model)
            else:
                self._vecs = np.load(vec_file)
                self._ids = json.loads(ids_file.read_text())
        # metadonnees minimales des passages vectorises (filtrage sans relire le JSON)
        self._meta_vec: dict[str, tuple[str, int | None]] = {}
        if self._ids:
            with self._lock:
                rows = self._con.execute("SELECT id, source_id, en_vigueur FROM passages").fetchall()
            known = set(self._ids)
            self._meta_vec = {r[0]: (r[1], r[2]) for r in rows if r[0] in known}
        # nombre de passages indexables (en vigueur) par source, pour mesurer la couverture
        self._totaux = dict(self._q(
            "SELECT source_id, count(*) FROM passages WHERE en_vigueur IS NULL OR en_vigueur = 1 GROUP BY source_id"))
        self._vectorises: dict[str, int] = {}
        for src, vig in self._meta_vec.values():
            if vig != 0:
                self._vectorises[src] = self._vectorises.get(src, 0) + 1

    def couverture(self, sources: tuple[str, ...] | None) -> float:
        srcs = sources or tuple(self._totaux)
        total = sum(self._totaux.get(s, 0) for s in srcs)
        return sum(self._vectorises.get(s, 0) for s in srcs) / total if total else 0.0

    # --- outils SQL ----------------------------------------------------------

    def _q(self, sql: str, params: tuple = ()) -> list[tuple]:
        with self._lock:
            return self._con.execute(sql, params).fetchall()

    @staticmethod
    def _filtre_sql(sources: tuple[str, ...]) -> tuple[str, tuple]:
        clause = " AND (p.en_vigueur IS NULL OR p.en_vigueur = 1)"
        if sources:
            clause += f" AND p.source_id IN ({','.join('?' * len(sources))})"
            return clause, tuple(sources)
        return clause, ()

    # --- recherche -----------------------------------------------------------

    def _par_reference(self, question: str, sources: tuple[str, ...] | None) -> list[dict]:
        refs = extraire(question)
        out: list[dict] = []
        autorisees = set(sources) if sources else None

        def ok(src: str) -> bool:
            return autorisees is None or src in autorisees

        for num in refs.articles:
            cibles = ["constitution_1958"] if refs.constitution else ["code_civil", "constitution_1958"]
            for src in cibles:
                if not ok(src):
                    continue
                rows = self._q(
                    "SELECT data FROM passages p WHERE source_id = ? AND numero = ?"
                    " AND (en_vigueur IS NULL OR en_vigueur = 1)",
                    (src, num),
                )
                if rows:
                    out.extend(json.loads(r[0]) for r in rows)
                    break
        for dec in refs.decisions_cc:
            num, nature = dec.split()
            if ok("decisions_conseil_constitutionnel"):
                rows = self._q(
                    "SELECT data FROM passages WHERE source_id = 'decisions_conseil_constitutionnel'"
                    " AND json_extract(data, '$.meta.numero') = ? AND json_extract(data, '$.meta.nature') = ?"
                    " ORDER BY rowid LIMIT 3",
                    (num, nature),
                )
                out.extend(json.loads(r[0]) for r in rows)
        for pv in refs.pourvois:
            if ok("judilibre"):
                rows = self._q(
                    "SELECT data FROM passages WHERE source_id = 'judilibre' AND data LIKE ? ORDER BY rowid LIMIT 3",
                    (f'%"{pv.replace(".", "")}"%',),
                )
                out.extend(json.loads(r[0]) for r in rows)
        return out

    def _fts(self, requete: str, sources: tuple[str, ...]) -> list[tuple[str, dict]]:
        clause, params = self._filtre_sql(sources)
        try:
            rows = self._q(
                "SELECT p.id, p.data FROM passages_fts f JOIN passages p ON p.rowid = f.rowid"
                f" WHERE passages_fts MATCH ? {clause} ORDER BY bm25(passages_fts, 3.0, 1.0) LIMIT ?",
                (requete, *params, N_CANDIDATS),
            )
        except sqlite3.OperationalError:
            return []
        return [(r[0], json.loads(r[1])) for r in rows]

    def _lexical(self, question: str, sources: tuple[str, ...]) -> list[list[tuple[str, dict]]]:
        """Deux classements : tous les termes (OU), et termes consecutifs proches (NEAR)."""
        mots = termes(question)
        if not mots or not sources:
            return []
        classements = [self._fts(" OR ".join(f'"{m}"*' for m in mots), sources)]
        if len(mots) > 1:
            near = " OR ".join(f'NEAR("{a}"* "{b}"*, 4)' for a, b in paires(mots))
            classements.append(self._fts(near, sources))
        return classements

    def _vectoriel(self, vecteur: list[float], sources: tuple[str, ...] | None) -> list[str]:
        if not len(self._ids) or vecteur is None:
            return []
        q = np.asarray(vecteur, dtype=np.float32)
        q /= np.linalg.norm(q) or 1.0
        sims = self._vecs @ q
        autorisees = set(sources) if sources else None
        out: list[str] = []
        for i in np.argsort(-sims):
            pid = self._ids[int(i)]
            src, vig = self._meta_vec.get(pid, ("", None))
            if (autorisees is None or src in autorisees) and vig != 0:
                out.append(pid)
                if len(out) >= N_CANDIDATS:
                    break
        return out

    def _groupe(self, question, sources, k, query_vector) -> list[Hit]:
        if not sources:
            return []
        classements = self._lexical(question, sources)
        vec_ids = []
        if query_vector is not None and self.couverture(sources) >= SEUIL_COUVERTURE:
            vec_ids = self._vectoriel(query_vector, sources)
        par_id: dict[str, dict] = {}
        for c in classements:
            par_id.update({pid: p for pid, p in c})
        for pid in vec_ids:
            if pid not in par_id:
                p = self.get(pid)
                if p:
                    par_id[pid] = p
        lex_ids = set(par_id) - set(vec_ids) | {pid for c in classements for pid, _ in c}
        scores = fusion_rrf(*[[pid for pid, _ in c] for c in classements], vec_ids)
        hits = []
        for pid, sc in sorted(scores.items(), key=lambda x: -x[1]):
            via = ({"lexical"} if pid in lex_ids else set()) | ({"vecteur"} if pid in vec_ids else set())
            hits.append(Hit(par_id[pid], sc, via))
        return diversifier(hits, k, doc_de)

    def search(self, question, *, sources, k, query_vector=None):
        refs = [Hit(p, float("inf"), {"reference"}) for p in self._par_reference(question, sources)]
        textes, juris = groupes(sources, self._toutes_sources())
        return assembler(
            refs,
            self._groupe(question, textes, k, query_vector),
            self._groupe(question, juris, k, query_vector),
            k,
        )

    def _toutes_sources(self) -> tuple[str, ...]:
        if not hasattr(self, "_sources_cache"):
            self._sources_cache = tuple(r[0] for r in self._q("SELECT DISTINCT source_id FROM passages"))
        return self._sources_cache

    # --- acces direct ----------------------------------------------------------

    def get(self, passage_id: str) -> dict | None:
        rows = self._q("SELECT data FROM passages WHERE id = ?", (passage_id,))
        return json.loads(rows[0][0]) if rows else None

    def versions(self, source_id: str, numero: str) -> list[dict]:
        rows = self._q("SELECT data FROM passages WHERE source_id = ? AND numero = ? ORDER BY rowid", (source_id, numero))
        return [json.loads(r[0]) for r in rows]

    def stats(self) -> dict:
        n = self._q("SELECT count(*) FROM passages")[0][0]
        return {"moteur": self.mode, "passages": n, "embeddings": len(self._ids),
                "couverture": round(self.couverture(None), 3)}
