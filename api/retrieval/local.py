"""Moteur de recherche local : SQLite FTS5 (BM25) + similarite cosinus numpy.

Lit l'index produit par `python -m ingest.build_index`. Utilise en developpement comme en production.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from pathlib import Path

import numpy as np

from api import lexique
from api.references import extraire, variantes
from api.textes import SOURCES_A_PART, SOURCES_CASSATION, cibles_article, meme_loi
from api.retrieval.base import (N_PRINCIPES, SEUIL_COUVERTURE, Complement, Hit, Reclasseur, assembler,
                                construire_groupe,
                                groupes, jeton_source, paires, termes)

N_CANDIDATS = 50
log = logging.getLogger("lexia.recherche")


class LocalRetriever:
    mode = "local"

    def __init__(self, index_dir: Path, embed_model: str | None = None):
        db = index_dir / "lexia.sqlite"
        if not db.exists():
            raise FileNotFoundError(f"Index absent : {db}. Lancer `python -m ingest.build_index`.")
        # Une connexion en lecture seule par fil : un verrou unique faisait attendre toutes les questions
        # derriere la plus lente (audit du 2026-11-18, B4).
        self._db = db
        self._local = threading.local()
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
                # memoire mappee : le systeme ne garde en RAM que les pages lues
                self._vecs = np.load(vec_file, mmap_mode="r")
                self._ids = json.loads(ids_file.read_text())
                # Fichiers de deux constructions differentes (construction interrompue entre deux
                # ecritures) : un indice de vecteur designerait le mauvais passage, donc la mauvaise source.
                if len(self._ids) != self._vecs.shape[0]:
                    log.warning("Index vectoriel incoherent (%d identifiants, %d vecteurs) : recherche vectorielle "
                                "desactivee (relancer ingest.build_index)", len(self._ids), self._vecs.shape[0])
                    self._ids, self._vecs = [], np.zeros((0, 0), dtype=np.float32)
        # metadonnees minimales des passages vectorises (filtrage sans relire le JSON)
        self._meta_vec: dict[str, tuple[str, int | None]] = {}
        if self._ids:
            rows = self._q("SELECT id, source_id, en_vigueur FROM passages")
            known = set(self._ids)
            self._meta_vec = {r[0]: (r[1], r[2]) for r in rows if r[0] in known}
        # index anterieur sans colonne source : ancienne requete (filtre apres jointure)
        self._fts_source = any(r[1] == "source" for r in self._q("PRAGMA table_info(passages_fts)"))
        # table des numeros de pourvoi (B4) ; index anterieur : recherche dans le JSON, plusieurs secondes
        self._table_pourvois = bool(self._q("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'pourvois'"))
        # nombre de passages indexables (en vigueur) par source, pour mesurer la couverture
        self._totaux = dict(self._q(
            "SELECT source_id, count(*) FROM passages WHERE en_vigueur IS NULL OR en_vigueur = 1 GROUP BY source_id"))
        self._vectorises: dict[str, int] = {}
        for src, vig in self._meta_vec.values():
            if vig != 0:
                self._vectorises[src] = self._vectorises.get(src, 0) + 1
        # articles de principe du lexique, version en vigueur et vectorisee, avec leurs vecteurs (D73)
        self._principes: list[tuple[str, str]] = []
        self._vecs_principes = np.zeros((0, 0), dtype=np.float32)
        if self._ids:
            rang = {pid: i for i, pid in enumerate(self._ids)}
            arts = sorted({a for _, liste in lexique.NOTIONS for a in liste})
            for src, num in arts:
                for (pid,) in self._q("SELECT id FROM passages WHERE source_id = ? AND numero = ? AND en_vigueur = 1",
                                      (src, num)):
                    if pid in rang:
                        self._principes.append((pid, src))
            if self._principes:
                self._vecs_principes = np.asarray(self._vecs[[rang[pid] for pid, _ in self._principes]],
                                                  dtype=np.float32)

    def couverture(self, sources: tuple[str, ...] | None) -> float:
        srcs = sources or tuple(s for s in self._totaux if s not in SOURCES_A_PART)
        total = sum(self._totaux.get(s, 0) for s in srcs)
        return sum(self._vectorises.get(s, 0) for s in srcs) / total if total else 0.0

    # --- outils SQL ----------------------------------------------------------

    @property
    def _con(self) -> sqlite3.Connection:
        con = getattr(self._local, "con", None)
        if con is None:
            con = self._local.con = sqlite3.connect(f"file:{self._db}?mode=ro", uri=True)
        return con

    def _q(self, sql: str, params: tuple = ()) -> list[tuple]:
        return self._con.execute(sql, params).fetchall()

    def _par_numero(self, src: str, num: str) -> list[dict]:
        """Versions en vigueur d'un article (R421-1 trouve aussi R*421-1, B3)."""
        nums = variantes(num)
        rows = self._q(f"SELECT data FROM passages WHERE source_id = ? AND numero IN ({','.join('?' * len(nums))})"
                       " AND (en_vigueur IS NULL OR en_vigueur = 1)", (src, *nums))
        return [json.loads(r[0]) for r in rows]

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
            # Loi ou ordonnance nommee : l'article est cherche dans ce texte, pas dans les codes.
            if refs.lois and ok("lois"):
                trouves = [p for p in self._par_numero("lois", num)
                           if any(meme_loi(c, (p.get("meta") or {}).get("code") or "") for c in refs.lois)]
                if trouves:
                    out.extend(trouves)
                    continue
                if not refs.codes:
                    continue  # loi citee mais article absent : ne pas servir l'article homonyme d'un code
            for src in cibles_article(num, refs.codes, refs.constitution):
                if not ok(src):
                    continue
                if trouves := self._par_numero(src, num):
                    out.extend(trouves)
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
            for src in SOURCES_CASSATION:
                if not ok(src):
                    continue
                if self._table_pourvois:
                    rows = self._q("SELECT p.data FROM pourvois v JOIN passages p ON p.rowid = v.passage"
                                   " WHERE v.numero = ? AND p.source_id = ? ORDER BY p.rowid LIMIT 3",
                                   (pv.replace(".", ""), src))
                else:
                    rows = self._q("SELECT data FROM passages WHERE source_id = ? AND data LIKE ? ORDER BY rowid"
                                   " LIMIT 3", (src, f'%"{pv.replace(".", "")}"%'))
                out.extend(json.loads(r[0]) for r in rows)
        # Grand arret administratif nomme (« arret Blanco ») : sommaire et debut de la decision (B5).
        for doc in refs.decisions_admin if ok("conseil_etat") else ():
            rows = self._q("SELECT data FROM passages WHERE doc_id = ? AND source_id = 'conseil_etat'"
                           " ORDER BY rowid LIMIT 3", (doc,))
            out.extend(json.loads(r[0]) for r in rows)
        return out

    def _fts(self, requete: str, sources: tuple[str, ...]) -> list[tuple[str, dict]]:
        if self._fts_source:
            # Filtre et classement dans l'index plein texte, lecture des seules lignes retenues.
            filtre = " OR ".join(jeton_source(s) for s in sources)
            try:
                rows = self._q(
                    "SELECT p.id, p.data FROM (SELECT rowid, rank FROM passages_fts"
                    " WHERE passages_fts MATCH ? AND rank MATCH 'bm25(3.0, 1.0, 0.0)' ORDER BY rank LIMIT ?) f"
                    " JOIN passages p ON p.rowid = f.rowid ORDER BY f.rank",
                    (f"source : ({filtre}) AND ({requete})", N_CANDIDATS),
                )
            except sqlite3.OperationalError as e:
                # Sans journal, un index casse se lisait comme « aucune source ».
                log.warning("recherche plein texte indisponible : %s", e)
                return []
            return [(r[0], json.loads(r[1])) for r in rows]
        clause, params = self._filtre_sql(sources)
        try:
            rows = self._q(
                "SELECT p.id, p.data FROM passages_fts f JOIN passages p ON p.rowid = f.rowid"
                f" WHERE passages_fts MATCH ? {clause} ORDER BY bm25(passages_fts, 3.0, 1.0) LIMIT ?",
                (requete, *params, N_CANDIDATS),
            )
        except sqlite3.OperationalError as e:
            # Sans journal, un index casse se lisait comme « aucune source ».
            log.warning("recherche plein texte indisponible : %s", e)
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
        if self._vecs.shape[1] != q.shape[0]:
            # EMBED_MODEL change sans reconstruire l'index : la recherche par sens est sautee
            # (le plein texte continue) au lieu de faire echouer chaque question.
            log.warning("vecteur de la question en dimension %d, index en %d : recherche vectorielle sautee",
                        q.shape[0], self._vecs.shape[1])
            return []
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

    def _suggestions(self, complement: Complement | None, sources: tuple[str, ...]) -> list[dict]:
        if not complement or not complement.suggestions or not sources:
            return []
        out: list[dict] = []
        for src, num in complement.suggestions:
            if src in sources:
                out.extend(self._par_numero(src, num))
        return out

    def _par_ids(self, ids: list[str]) -> list[tuple[str, dict]]:
        out = []
        for pid in ids:
            p = self.get(pid)
            if p:
                out.append((pid, p))
        return out

    def _groupe(self, question, sources, k, query_vector, complement=None, reclasseur=None) -> list[Hit]:
        if not sources:
            return []
        classements: dict[str, list[tuple[str, dict]]] = {}
        for i, c in enumerate(self._lexical(question, sources)):
            classements[f"lexical_{i}"] = c
        vectoriel = self.couverture(sources) >= SEUIL_COUVERTURE
        if query_vector is not None and vectoriel:
            classements["vecteur"] = self._par_ids(self._vectoriel(query_vector, sources))
        if complement and complement.reformulation:
            for i, c in enumerate(self._lexical(complement.reformulation, sources)):
                classements[f"lexical_reformulation_{i}"] = c
            if complement.vecteur_reformulation is not None and vectoriel:
                classements["vecteur_reformulation"] = self._par_ids(
                    self._vectoriel(complement.vecteur_reformulation, sources))
        suggestions = self._suggestions(complement, sources)
        principes = [] if suggestions or reclasseur is None or not vectoriel \
            else self._principes_proches(query_vector, sources)
        return construire_groupe(classements, k, question=question, reclasseur=reclasseur,
                                 suggestions=suggestions, principes=principes)

    def _principes_proches(self, vecteur, sources) -> list[dict]:
        """Les N_PRINCIPES articles de principe de ces sources les plus proches de la question par le sens."""
        sel = [i for i, (_, src) in enumerate(self._principes) if src in sources]
        if vecteur is None or not sel:
            return []
        q = np.asarray(vecteur, dtype=np.float32)
        if self._vecs_principes.shape[1] != q.shape[0]:
            return []
        q /= np.linalg.norm(q) or 1.0
        sims = self._vecs_principes[sel] @ q
        return [p for i in np.argsort(-sims)[:N_PRINCIPES] if (p := self.get(self._principes[sel[int(i)]][0]))]

    def search(self, question, *, sources, k, query_vector=None, complement: Complement | None = None,
               reclasseur: Reclasseur | None = None):
        refs = [Hit(p, float("inf"), {"reference"}) for p in self._par_reference(question, sources)]
        textes, juris = groupes(sources, self._toutes_sources())
        return assembler(
            refs,
            self._groupe(question, textes, k, query_vector, complement, reclasseur),
            self._groupe(question, juris, k, query_vector, complement, reclasseur),
            k,
        )

    def rechercher_a_part(self, question: str, k: int = 30) -> list[dict]:
        """Passages des fiches recuperees (SOURCES_A_PART) les plus proches de la question, plein texte seul.
        Pour la page « Cours recuperes » ; jamais utilise pour une reponse."""
        sources = tuple(s for s in self._toutes_sources() if s in SOURCES_A_PART)
        classements = self._lexical(question, sources)
        vus, out = set(), []
        for _, p in (classements[0] if classements else [])[:k]:
            if p["id"] not in vus:
                vus.add(p["id"])
                out.append(p)
        return out

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
        stats = {"moteur": self.mode, "passages": n, "embeddings": len(self._ids),
                 "couverture": round(self.couverture(None), 3)}
        if derniere := self.dernieres_decisions():
            stats["derniere_decision"] = derniere
        return stats

    def dernieres_decisions(self) -> dict[str, str]:
        """Date de la decision la plus recente de chaque source de jurisprudence (B7), calculee une fois.
        Table `fraicheur` de l'index ; index anterieur : lecture des sommaires et des decisions (quelques
        secondes, une seule fois par processus)."""
        if not hasattr(self, "_dernieres"):
            if self._q("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'fraicheur'"):
                rows = self._q("SELECT source_id, date FROM fraicheur ORDER BY source_id")
            else:
                rows = self._q(
                    "SELECT source_id, max(json_extract(data, '$.meta.date')) FROM passages WHERE type <> 'article'"
                    " AND json_extract(data, '$.meta.date') < '2999' GROUP BY source_id ORDER BY source_id")
            self._dernieres = {src: d for src, d in rows if d and str(d)[:4].isdigit()}
        return self._dernieres
