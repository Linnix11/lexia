"""Cours deposes par les etudiants : extraction du texte, decoupage, embeddings, recherche, routes /cours.

Seul le texte extrait est conserve (decoupe en passages avec la page), dans la base SQLite des comptes ;
le fichier d'origine n'est pas garde. Un cours n'est visible que par son proprietaire et disparait avec
lui (ON DELETE CASCADE). Voir docs/superpowers/specs/2026-11-12-cours-deposes-design.md.
"""

from __future__ import annotations

import io
import logging
import re
import sqlite3
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Request

from api.auth import verifier_origine
from api.matieres import LIBELLES
from api.retrieval.base import fusion_rrf, termes

log = logging.getLogger("lexia.cours")

TAILLE_MAX = 20 * 1024 * 1024       # 20 Mo par fichier
CARACTERES_MAX = 1_000_000          # texte extrait au plus
PAGES_MAX = 1000                    # pages d'un PDF
XML_WORD_MAX = 10 * 1024 * 1024     # word/document.xml decompresse : au-dela, archive piegee (« zip bomb »)
DEPOTS_PAR_JOUR = 20                # depots par compte sur 24 h (deposer/retirer en boucle saturerait le serveur)
TAILLE_PASSAGE = 1500               # caracteres par passage (environ)
FORMATS = {".pdf": "PDF", ".docx": "Word", ".txt": "texte", ".md": "texte"}
SOURCE_ID = "cours_perso"

SCHEMA = """
CREATE TABLE IF NOT EXISTS cours (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,   -- jamais reutilise apres suppression
    utilisateur  INTEGER NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    matiere      TEXT NOT NULL,
    titre        TEXT NOT NULL,
    fichier      TEXT NOT NULL,
    pages        INTEGER,
    passages     INTEGER NOT NULL DEFAULT 0,
    statut       TEXT NOT NULL DEFAULT 'traitement',  -- traitement | pret | erreur
    ajoute_le    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cours_passages (
    id        INTEGER PRIMARY KEY,
    cours     INTEGER NOT NULL REFERENCES cours(id) ON DELETE CASCADE,
    rang      INTEGER NOT NULL,
    page      INTEGER,
    texte     TEXT NOT NULL,
    vecteur   BLOB                                   -- float32 normalise ; NULL tant que non calcule
);
CREATE INDEX IF NOT EXISTS cours_passages_cours ON cours_passages (cours);
CREATE VIRTUAL TABLE IF NOT EXISTS cours_fts USING fts5(texte, tokenize='unicode61 remove_diacritics 2');
-- passage supprime (cours retire ou compte supprime, y compris par cascade) : texte retire de l'index aussi
CREATE TRIGGER IF NOT EXISTS cours_passages_supprime AFTER DELETE ON cours_passages
BEGIN DELETE FROM cours_fts WHERE rowid = old.id; END;
"""


class ErreurCours(ValueError):
    """Erreur presentable a l'etudiant."""


# --- extraction ----------------------------------------------------------------

def extraire_texte(nom: str, contenu: bytes) -> list[tuple[int | None, str]]:
    """[(page, texte)] ; page = None quand le format n'a pas de pages."""
    ext = Path(nom).suffix.lower()
    if ext not in FORMATS:
        raise ErreurCours("Format non pris en charge : déposez un PDF, un fichier Word (.docx) ou un texte (.txt).")
    if ext == ".pdf":
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError

        try:
            lecteur = PdfReader(io.BytesIO(contenu))
            if lecteur.is_encrypted:
                raise ErreurCours("Ce PDF est protégé par un mot de passe : déposez une version sans protection.")
            if len(lecteur.pages) > PAGES_MAX:
                raise ErreurCours(f"Document trop long ({len(lecteur.pages)} pages, {PAGES_MAX} au plus) : "
                                  "découpez-le en plusieurs cours.")
            pages, total = [], 0
            for i, p in enumerate(lecteur.pages, start=1):
                texte = p.extract_text() or ""
                total += len(texte)
                if total > CARACTERES_MAX:
                    raise ErreurCours("Document trop long : découpez-le en plusieurs cours.")
                pages.append((i, texte))
        except (PdfReadError, ValueError, KeyError) as e:
            if isinstance(e, ErreurCours):
                raise
            raise ErreurCours("Ce PDF est illisible ou endommagé.") from None
        if sum(len(t.strip()) for _, t in pages) < 200:
            raise ErreurCours("Ce PDF ne contient pas de texte (scan ou photo) : la lecture des documents "
                              "scannés n'est pas encore disponible.")
        return pages
    if ext == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(contenu)) as z, z.open("word/document.xml") as f:
                brut = f.read(XML_WORD_MAX + 1)  # lecture bornee : jamais plus que la limite en memoire
            if len(brut) > XML_WORD_MAX:
                raise ErreurCours("Ce fichier Word est anormalement volumineux une fois décompressé : il est refusé.")
            xml = brut.decode("utf-8", "replace")
        except (zipfile.BadZipFile, KeyError):
            raise ErreurCours("Ce fichier Word est illisible ou endommagé.") from None
        paragraphes = [re.sub(r"<[^>]+>", "", p) for p in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)]
        texte = "\n".join(_entites(p) for p in paragraphes)
        return [(None, texte)]
    try:
        return [(None, contenu.decode("utf-8"))]
    except UnicodeDecodeError:
        return [(None, contenu.decode("latin-1"))]


def _entites(t: str) -> str:
    return t.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'").replace("&amp;", "&")


def decouper(pages: list[tuple[int | None, str]]) -> list[tuple[int | None, str]]:
    """Passages d'environ TAILLE_PASSAGE caracteres, coupes entre paragraphes, avec leur page de depart."""
    out: list[tuple[int | None, str]] = []
    courant, page_courante = "", None
    for page, texte in pages:
        for para in re.split(r"\n\s*\n|\n(?=[A-ZÀ-Ý0-9IVX]{1,6}[.)-] )", texte):
            para = re.sub(r"[ \t]+", " ", para).strip()
            if not para:
                continue
            while len(para) > TAILLE_PASSAGE * 2:  # paragraphe geant : coupe a une fin de phrase
                coupe = para.rfind(". ", 0, TAILLE_PASSAGE * 2)
                coupe = coupe + 1 if coupe > TAILLE_PASSAGE // 2 else TAILLE_PASSAGE * 2
                if courant:
                    out.append((page_courante, courant))
                    courant = ""
                out.append((page, para[:coupe].strip()))
                para = para[coupe:].strip()
            if not courant:
                page_courante = page
            if len(courant) + len(para) > TAILLE_PASSAGE and courant:
                out.append((page_courante, courant))
                courant, page_courante = "", page
            courant = f"{courant}\n{para}" if courant else para
    if courant:
        out.append((page_courante, courant))
    return out


# --- stockage et recherche --------------------------------------------------------

class Cours:
    def __init__(self, chemin: Path | str, embedder=None):
        self._con = sqlite3.connect(str(chemin), check_same_thread=False)
        self._con.execute("PRAGMA foreign_keys = ON")
        self._con.executescript(SCHEMA)
        self._lock = threading.Lock()
        self.embedder = embedder
        self._fil = ThreadPoolExecutor(max_workers=1, thread_name_prefix="cours")  # un calcul a la fois
        self._depots: dict[int, list[float]] = {}  # uid -> instants des depots des dernieres 24 h
        if embedder is not None:
            for (cid,) in self._q("SELECT DISTINCT cours FROM cours_passages WHERE vecteur IS NULL"):
                self._fil.submit(self._vectoriser, cid)  # reprise apres redemarrage

    def _q(self, sql: str, params: tuple = ()) -> list[tuple]:
        with self._lock, self._con:
            return self._con.execute(sql, params).fetchall()

    # -- depot --

    def nombre(self, uid: int) -> int:
        return self._q("SELECT count(*) FROM cours WHERE utilisateur = ?", (uid,))[0][0]

    def ajouter(self, uid: int, matiere: str, titre: str, fichier: str, contenu: bytes, maximum: int) -> dict:
        if matiere not in LIBELLES:
            raise ErreurCours("Matière inconnue.")
        titre = (titre or Path(fichier).stem).strip()[:120]
        if not titre:
            raise ErreurCours("Donnez un titre au cours.")
        if len(contenu) > TAILLE_MAX:
            raise ErreurCours("Fichier trop volumineux (20 Mo au plus).")
        if not contenu:
            raise ErreurCours("Le fichier est vide.")
        maintenant_s = time.monotonic()
        with self._lock:
            recents = [t for t in self._depots.get(uid, []) if maintenant_s - t < 86400]
            if len(recents) >= DEPOTS_PAR_JOUR:
                raise ErreurCours(f"Trop de dépôts aujourd'hui ({DEPOTS_PAR_JOUR} au plus sur 24 h) : réessayez demain.")
            self._depots[uid] = recents + [maintenant_s]
        if self.nombre(uid) >= maximum:
            raise ErreurCours(f"Limite atteinte : {maximum} cours avec votre formule. Retirez un cours ou "
                              "passez à une formule supérieure.")
        pages = extraire_texte(fichier, contenu)
        if sum(len(t) for _, t in pages) > CARACTERES_MAX:
            raise ErreurCours("Document trop long : découpez-le en plusieurs cours.")
        passages = decouper(pages)
        if not passages:
            raise ErreurCours("Aucun texte exploitable dans ce fichier.")
        maintenant = datetime.now(timezone.utc).isoformat(timespec="seconds")
        nb_pages = max((p for p, _ in pages if p), default=None)
        with self._lock, self._con:
            cid = self._con.execute(
                "INSERT INTO cours (utilisateur, matiere, titre, fichier, pages, passages, statut, ajoute_le)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (uid, matiere, titre, Path(fichier).name[:200], nb_pages, len(passages),
                 "traitement" if self.embedder else "pret", maintenant)).lastrowid
            for rang, (page, texte) in enumerate(passages):
                pid = self._con.execute("INSERT INTO cours_passages (cours, rang, page, texte) VALUES (?,?,?,?)",
                                        (cid, rang, page, texte)).lastrowid
                self._con.execute("INSERT INTO cours_fts (rowid, texte) VALUES (?,?)", (pid, texte))
        if self.embedder is not None:
            self._fil.submit(self._vectoriser, cid)
        return self.fiche(uid, cid)

    def _vectoriser(self, cid: int) -> None:
        try:
            rows = self._q("SELECT id, texte FROM cours_passages WHERE cours = ? AND vecteur IS NULL ORDER BY rang", (cid,))
            for i in range(0, len(rows), 32):
                bloc = rows[i:i + 32]
                vecs = self.embedder.embed_documents([t for _, t in bloc])
                with self._lock, self._con:
                    for (pid, _), v in zip(bloc, vecs):
                        self._con.execute("UPDATE cours_passages SET vecteur = ? WHERE id = ?",
                                          (np.asarray(v, dtype=np.float32).tobytes(), pid))
            self._q("UPDATE cours SET statut = 'pret' WHERE id = ?", (cid,))
        except Exception:  # noqa: BLE001 - le cours reste utilisable en recherche lexicale
            log.exception("embeddings du cours %s", cid)
            self._q("UPDATE cours SET statut = 'erreur' WHERE id = ?", (cid,))

    # -- lecture --

    def fiche(self, uid: int, cid: int) -> dict:
        rows = self._q("SELECT id, matiere, titre, fichier, pages, passages, statut, ajoute_le FROM cours"
                       " WHERE id = ? AND utilisateur = ?", (cid, uid))
        if not rows:
            raise ErreurCours("Cours introuvable.")
        return self._dict(rows[0])

    @staticmethod
    def _dict(r) -> dict:
        cles = ("id", "matiere", "titre", "fichier", "pages", "passages", "statut", "ajoute_le")
        d = dict(zip(cles, r))
        d["libelle_matiere"] = LIBELLES.get(d["matiere"], d["matiere"])
        return d

    def lister(self, uid: int) -> list[dict]:
        rows = self._q("SELECT id, matiere, titre, fichier, pages, passages, statut, ajoute_le FROM cours"
                       " WHERE utilisateur = ? ORDER BY matiere, ajoute_le DESC", (uid,))
        return [self._dict(r) for r in rows]

    def supprimer(self, uid: int, cid: int) -> None:
        with self._lock, self._con:
            n = self._con.execute("DELETE FROM cours WHERE id = ? AND utilisateur = ?", (cid, uid)).rowcount
        if not n:
            raise ErreurCours("Cours introuvable.")

    def passage(self, uid: int, passage_id: str) -> dict | None:
        """« cours:<id_cours>:<id_passage> », seulement pour le proprietaire."""
        m = re.fullmatch(r"cours:(\d+):(\d+)", passage_id)
        if not m:
            return None
        rows = self._q("SELECT p.id, p.cours, p.rang, p.page, p.texte, c.titre, c.matiere FROM cours_passages p"
                       " JOIN cours c ON c.id = p.cours WHERE p.id = ? AND c.id = ? AND c.utilisateur = ?",
                       (int(m.group(2)), int(m.group(1)), uid))
        return _vers_passage(rows[0]) if rows else None

    def rechercher(self, uid: int, cours_ids: list[int], question: str, k: int,
                   vecteur: list[float] | None = None) -> list[dict]:
        """Passages des cours choisis (appartenant a uid) : plein texte + vecteurs, fusion par rang."""
        ids = [r[0] for r in self._q(
            f"SELECT id FROM cours WHERE utilisateur = ? AND id IN ({','.join('?' * len(cours_ids))})",
            (uid, *cours_ids))] if cours_ids else []
        if not ids:
            return []
        marques = ",".join("?" * len(ids))
        classements: list[list[int]] = []
        mots = termes(question)
        if mots:
            try:
                classements.append([r[0] for r in self._q(
                    f"SELECT f.rowid FROM cours_fts f JOIN cours_passages p ON p.id = f.rowid"
                    f" WHERE cours_fts MATCH ? AND p.cours IN ({marques}) ORDER BY bm25(cours_fts) LIMIT 40",
                    (" OR ".join(f'"{m}"*' for m in mots), *ids))])
            except sqlite3.OperationalError:
                pass
        if vecteur is not None:
            rows = self._q(f"SELECT id, vecteur FROM cours_passages WHERE cours IN ({marques}) AND vecteur IS NOT NULL", tuple(ids))
            if rows:
                mat = np.frombuffer(b"".join(v for _, v in rows), dtype=np.float32).reshape(len(rows), -1)
                q = np.asarray(vecteur, dtype=np.float32)
                q /= np.linalg.norm(q) or 1.0
                ordre = np.argsort(-(mat @ q))[:40]
                classements.append([rows[int(i)][0] for i in ordre])
        if not classements:  # question sans mot utile ni vecteur : debut du cours
            classements.append([r[0] for r in self._q(
                f"SELECT id FROM cours_passages WHERE cours IN ({marques}) ORDER BY cours, rang LIMIT ?", (*ids, k))])
        meilleurs = [pid for pid, _ in sorted(fusion_rrf(*[[str(i) for i in c] for c in classements]).items(),
                                              key=lambda x: -x[1])][:k]
        if not meilleurs:
            return []
        rows = self._q(f"SELECT p.id, p.cours, p.rang, p.page, p.texte, c.titre, c.matiere FROM cours_passages p"
                       f" JOIN cours c ON c.id = p.cours WHERE p.id IN ({','.join('?' * len(meilleurs))})",
                       tuple(int(i) for i in meilleurs))
        par_id = {str(r[0]): _vers_passage(r) for r in rows}
        return [par_id[i] for i in meilleurs if i in par_id]


def _vers_passage(r) -> dict:
    pid, cid, rang, page, texte, titre, matiere = r
    ou = f", page {page}" if page else ""
    return {
        "id": f"cours:{cid}:{pid}", "source_id": SOURCE_ID, "type": "cours", "numero": None,
        "entete": f"Mon cours « {titre} »{ou}", "titre": titre, "url": "", "version": "Cours déposé par l'étudiant",
        "texte": texte, "meta": {"cours": cid, "page": page, "rang": rang, "matiere": matiere},
    }


# --- routes ------------------------------------------------------------------------

def creer_routes_cours(cours: Cours, utilisateur_requis) -> APIRouter:
    router = APIRouter()

    def _erreur(e: ErreurCours):
        raise HTTPException(422, str(e)) from None

    @router.get("/cours")
    def lister(u=Depends(utilisateur_requis)):
        return {"cours": cours.lister(u.id), "maximum": u.formule.cours_max, "formats": sorted(set(FORMATS))}

    @router.post("/cours", status_code=201, dependencies=[Depends(verifier_origine)])
    async def deposer(request: Request, matiere: str, fichier: str, titre: str = "", u=Depends(utilisateur_requis)):
        longueur = int(request.headers.get("content-length") or 0)
        if longueur > TAILLE_MAX:
            raise HTTPException(413, "Fichier trop volumineux (20 Mo au plus).")
        contenu = await request.body()
        try:
            from starlette.concurrency import run_in_threadpool

            return await run_in_threadpool(cours.ajouter, u.id, matiere, titre, fichier, contenu, u.formule.cours_max)
        except ErreurCours as e:
            _erreur(e)

    @router.post("/cours/{cid}/supprimer", status_code=204, dependencies=[Depends(verifier_origine)])
    def supprimer(cid: int, u=Depends(utilisateur_requis)):
        try:
            cours.supprimer(u.id, cid)
        except ErreurCours as e:
            _erreur(e)

    return router
