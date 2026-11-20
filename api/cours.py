"""Cours deposes par les etudiants : extraction du texte, decoupage, embeddings, recherche, routes /cours.

Seul le texte extrait est conserve (decoupe en passages avec la page), dans la base SQLite des comptes ;
le fichier d'origine n'est pas garde. Un cours n'est visible que par son proprietaire et disparait avec
lui (ON DELETE CASCADE). Voir docs/superpowers/specs/2026-11-12-cours-deposes-design.md.
"""

from __future__ import annotations

import bisect
import logging
import re
import sqlite3
import threading
import time
import unicodedata
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Request

from api.auth import verifier_origine
from api import concordance
from api.extraction import (CARACTERES_MAX, FORMATS, ErreurCours, extraire_isole,  # noqa: F401
                            extraire_texte, pages_sans_texte)
from api.matieres import LIBELLES
from api.references import extraire
from api.retrieval.base import fusion_rrf, termes

log = logging.getLogger("lexia.cours")

TAILLE_MAX = 20 * 1024 * 1024       # 20 Mo par fichier
DEPOTS_PAR_JOUR = 20                # depots par compte sur 24 h (deposer/retirer en boucle saturerait le serveur)
DEPOTS_SIMULTANES = 2               # depots lus en meme temps, tous comptes confondus (memoire du serveur)
TAILLE_PASSAGE = 1500               # caracteres par passage (environ)
RELANCE_VECTORISATION = 600         # secondes avant de relancer le calcul des vecteurs d'un cours en erreur
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
    ajoute_le    TEXT NOT NULL,
    avertissement TEXT                                 -- ex. pages sans texte (scan)
);
CREATE TABLE IF NOT EXISTS cours_passages (
    id        INTEGER PRIMARY KEY,
    cours     INTEGER NOT NULL REFERENCES cours(id) ON DELETE CASCADE,
    rang      INTEGER NOT NULL,
    page      INTEGER,                               -- page de debut
    page_fin  INTEGER,
    texte     TEXT NOT NULL,
    vecteur   BLOB                                   -- float32 normalise ; NULL tant que non calcule
);
CREATE INDEX IF NOT EXISTS cours_passages_cours ON cours_passages (cours);
CREATE VIRTUAL TABLE IF NOT EXISTS cours_fts USING fts5(texte, tokenize='unicode61 remove_diacritics 2');
-- passage supprime (cours retire ou compte supprime, y compris par cascade) : texte retire de l'index aussi
CREATE TRIGGER IF NOT EXISTS cours_passages_supprime AFTER DELETE ON cours_passages
BEGIN DELETE FROM cours_fts WHERE rowid = old.id; END;
"""


# --- nettoyage et decoupage ---------------------------------------------------------

# Prefixes gardes avec leur trait d'union en fin de ligne (« non-\nrétroactivité ») : ailleurs, le trait
# d'union de fin de ligne est une cesure (« respon-\nsabilité ») et le mot est recolle.
_PREFIXES = {"non", "quasi", "contre", "sous", "sur", "demi", "semi", "mi", "anti", "ex", "vice", "après", "avant",
             "auto", "co", "inter", "intra", "extra", "post", "pré", "pro", "néo", "porte", "arrière", "grand",
             "petit", "nu", "ayant", "ayants", "soi", "on", "celui", "ci", "là", "dit", "dite", "lui", "elle"}
_CESURE = re.compile(r"(\w+)-[ \t]*\n(\x0c?)[ \t]*(?=[a-zà-öø-ÿœ])")
_NUMERO_PAGE = re.compile(r"(?:page\s*)?\d{1,4}(?:\s*(?:/|sur)\s*\d{1,4})?|[-–]\s*\d{1,4}\s*[-–]", re.IGNORECASE)
# Titres du plan, du plus haut au plus bas : Partie/Titre, Chapitre, Section, Sous-section, §, I., A., 1., a.
_TITRES = [re.compile(m) for m in (r"(?:Partie|Titre|Livre)\b", r"Chapitre\b", r"Section\b", r"Sous-section\b",
                                   r"(?:§|Paragraphe\b)", r"[IVXL]{1,6}[.)-] ", r"[A-Z][.)-] ", r"\d{1,2}[.)-] ",
                                   r"[a-z][.)] ")]
# Coupure de paragraphe : ligne vide, ou ligne qui commence par un titre (« I. », « A. », « Chapitre »...).
_COUPURE = re.compile(r"\n\s*\n|\n(?=\x0c?(?:[A-ZÀ-Ý0-9IVX]{1,6}[.)-] |(?:Chapitre|Section|Partie|Titre|§)\b))")


def nettoyer(pages: list[tuple[int | None, str]]) -> list[tuple[int | None, str]]:
    """Ligatures et caracteres de compatibilite (NFKC : « ﬃ » -> « ffi »), cesures invisibles, puis
    en-tetes, pieds de page et numeros de page repetes de page en page (audit C4 et C11)."""
    pages = [(p, unicodedata.normalize("NFKC", t).replace("­", "")) for p, t in pages]
    if sum(1 for p, _ in pages if p is not None) < 2:
        return pages

    def bords(lignes: list[str]) -> list[int]:
        """Deux premieres et deux dernieres lignes de la page, si elles sont courtes (en-tete, pied de page)."""
        pleines = [i for i, ligne in enumerate(lignes) if ligne.strip()]
        return sorted(i for i in set(pleines[:2] + pleines[-2:]) if len(lignes[i]) <= 100)

    def cle(ligne: str) -> str:
        return re.sub(r"\d+", "#", re.sub(r"\s+", " ", ligne.strip().lower()))

    lignes = [t.split("\n") for _, t in pages]
    compte = Counter(c for ls in lignes for c in {cle(ls[i]) for i in bords(ls)})
    seuil = max(2, -(-len(pages) * 6 // 10))  # sur 60 % des pages au moins
    repetees = {c for c, n in compte.items() if n >= seuil}
    out = []
    for (page, _), ls in zip(pages, lignes):
        retirees = {i for i in bords(ls) if cle(ls[i]) in repetees or _NUMERO_PAGE.fullmatch(ls[i].strip())}
        out.append((page, "\n".join(ligne for i, ligne in enumerate(ls) if i not in retirees)))
    return out


def _rang_titre(ligne: str) -> int | None:
    """Rang dans le plan d'une ligne de titre (« A. La faute »), None pour une ligne de texte."""
    if len(ligne) > 120 or ligne[-1:] in ".;,:":
        return None
    return next((i for i, m in enumerate(_TITRES) if m.match(ligne)), None)


def decouper(pages: list[tuple[int | None, str]]) -> list[tuple[int | None, int | None, str]]:
    """Passages d'environ TAILLE_PASSAGE caracteres : (page de debut, page de fin, texte).

    Le texte est decoupe d'un seul tenant, pas page par page : une phrase a cheval sur deux pages reste
    entiere. Chaque passage commence par le rappel du plan (« [I. Le fait générateur > A. La faute] ») quand
    il ne s'ouvre pas sur son propre titre (audit C3).
    """
    pages = nettoyer(pages)
    numeros = [p for p, _ in pages]
    # \x0c : saut de page, retire du texte des passages. Une page finie par une fin de phrase finit aussi
    # son paragraphe ; sinon la phrase continue sur la page suivante.
    texte = "".join(f"{t}\n\x0c\n" if re.search(r"[.!?:»)]\s*$", t) else f"{t}\n\x0c" for _, t in pages)
    texte = _CESURE.sub(lambda m: m.group(1) + ("-" if m.group(1).lower() in _PREFIXES else "") + m.group(2), texte)
    sauts = [i for i, c in enumerate(texte) if c == "\x0c"]

    def page(position: int) -> int | None:
        return numeros[min(bisect.bisect_left(sauts, position), len(numeros) - 1)] if numeros else None

    def propre(a: int, b: int) -> str:
        return re.sub(r"[ \t]+", " ", texte[a:b].replace("\x0c", "")).strip()

    # Paragraphes (debut, fin) dans le texte entier, eux-memes coupes a une fin de phrase s'ils sont geants.
    morceaux: list[tuple[int, int]] = []
    debut = 0
    for m in [*_COUPURE.finditer(texte), None]:
        a, b = debut, (m.start() if m else len(texte))
        debut = m.end() if m else len(texte)
        while a < b and texte[a] in " \t\n\x0c":
            a += 1
        while b > a and texte[b - 1] in " \t\n\x0c":
            b -= 1
        while b - a > TAILLE_PASSAGE * 2:
            fins = [f.end() for f in re.finditer(r"[.!?»]\s", texte[a:a + TAILLE_PASSAGE * 2])]
            coupe = fins[-1] if fins and fins[-1] > TAILLE_PASSAGE // 2 else TAILLE_PASSAGE * 2
            morceaux.append((a, a + coupe))
            a += coupe
            while a < b and texte[a] in " \t\n\x0c":
                a += 1
        if b > a:
            morceaux.append((a, b))

    out: list[tuple[int | None, int | None, str]] = []
    plan: list[tuple[int, str]] = []
    courant, depart, arrivee, corps = "", None, None, False
    for a, b in morceaux:
        para = propre(a, b)
        if not para:
            continue
        premiere = para.split("\n", 1)[0].strip()
        rang = _rang_titre(premiere)
        if rang is not None:
            plan = [x for x in plan if x[0] < rang]
        # Nouveau passage quand il serait trop long, ou a un titre si le passage en cours a deja du corps.
        if courant and (len(courant) + len(para) > TAILLE_PASSAGE
                        or (rang is not None and corps and len(courant) >= TAILLE_PASSAGE // 3)):
            if corps:  # un passage fait de titres seuls ne sert a rien : ils sont rappeles en tete du suivant
                out.append((depart, arrivee, courant))
            courant = ""
        if not courant:
            contexte = [t for _, t in plan]
            courant = f"[{' > '.join(contexte)}]\n{para}" if contexte else para
            depart, corps = page(a), False
        else:
            courant = f"{courant}\n{para}"
        arrivee = page(b - 1)
        corps = corps or rang is None or "\n" in para
        if rang is not None:
            plan.append((rang, premiere))
    if courant and corps:
        out.append((depart, arrivee, courant))
    return out


# --- stockage et recherche --------------------------------------------------------

class Cours:
    def __init__(self, chemin: Path | str, embedder=None):
        self._con = sqlite3.connect(str(chemin), check_same_thread=False)
        self._con.execute("PRAGMA foreign_keys = ON")
        # Cours retire : pages effacees (mises a zero) au lieu d'etre seulement liberees ; le texte restait
        # lisible dans le fichier de la base (audit C7).
        self._con.execute("PRAGMA secure_delete = ON")
        self._con.executescript(SCHEMA)
        for table, colonne in (("cours", "avertissement TEXT"), ("cours_passages", "page_fin INTEGER")):
            if colonne.split()[0] not in {r[1] for r in self._con.execute(f"PRAGMA table_info({table})")}:
                self._con.execute(f"ALTER TABLE {table} ADD COLUMN {colonne}")
        try:  # index plein texte : un mot supprime disparait aussi de l'index (SQLite 3.44 ou plus)
            self._con.execute("INSERT INTO cours_fts (cours_fts, rank) VALUES ('secure-delete', 1)")
            self._fts_efface = True
        except sqlite3.OperationalError:
            self._fts_efface = False
        self._con.commit()
        self._lock = threading.Lock()
        self.embedder = embedder
        self._fil = ThreadPoolExecutor(max_workers=1, thread_name_prefix="cours")  # un calcul a la fois
        self._depots: dict[int, list[float]] = {}  # uid -> instants des depots des dernieres 24 h
        self._echecs: dict[int, float] = {}        # cours -> instant du dernier echec du calcul des vecteurs
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
            self._depots[uid] = recents
        if self.nombre(uid) >= maximum:
            raise ErreurCours(f"Limite atteinte : {maximum} cours avec votre formule. Retirez un cours ou "
                              "passez à une formule supérieure.")
        # Chaque lecture de fichier compte, reussie ou non : c'est elle qui coute (un fichier refuse a la
        # lecture se renvoyait sans limite, audit du 2026-11-16). Les refus d'avant (limite de la formule,
        # fichier vide ou trop gros) restent gratuits : un etudiant ne s'y bloque pas lui-meme.
        with self._lock:
            self._depots.setdefault(uid, []).append(time.monotonic())
        pages = extraire_isole(fichier, contenu)  # processus a part, borne en duree et en memoire
        if sum(len(t) for _, t in pages) > CARACTERES_MAX:
            raise ErreurCours("Document trop long : découpez-le en plusieurs cours.")
        passages = decouper(pages)
        if not passages:
            raise ErreurCours("Aucun texte exploitable dans ce fichier.")
        maintenant = datetime.now(timezone.utc).isoformat(timespec="seconds")
        nb_pages = max((p for p, _ in pages if p), default=None)
        avertissement = _avertissement_pages(pages_sans_texte(pages) if Path(fichier).suffix.lower() == ".pdf" else [])
        with self._lock, self._con:
            cid = self._con.execute(
                "INSERT INTO cours (utilisateur, matiere, titre, fichier, pages, passages, statut, ajoute_le,"
                " avertissement) VALUES (?,?,?,?,?,?,?,?,?)",
                (uid, matiere, titre, Path(fichier).name[:200], nb_pages, len(passages),
                 "traitement" if self.embedder else "pret", maintenant, avertissement)).lastrowid
            for rang, (page, page_fin, texte) in enumerate(passages):
                pid = self._con.execute("INSERT INTO cours_passages (cours, rang, page, page_fin, texte)"
                                        " VALUES (?,?,?,?,?)", (cid, rang, page, page_fin, texte)).lastrowid
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
            self._echecs[cid] = time.monotonic()
            self._q("UPDATE cours SET statut = 'erreur' WHERE id = ?", (cid,))

    def _relancer(self, uid: int) -> None:
        """Calcul des vecteurs en erreur relance (au plus tous les RELANCE_VECTORISATION s par cours) : avant,
        seul un redemarrage du serveur le relancait (audit C10)."""
        if self.embedder is None:
            return
        maintenant = time.monotonic()
        for (cid,) in self._q("SELECT id FROM cours WHERE utilisateur = ? AND statut = 'erreur'", (uid,)):
            if maintenant - self._echecs.get(cid, float("-inf")) >= RELANCE_VECTORISATION:
                self._echecs[cid] = maintenant
                self._q("UPDATE cours SET statut = 'traitement' WHERE id = ?", (cid,))
                self._fil.submit(self._vectoriser, cid)

    # -- lecture --

    def fiche(self, uid: int, cid: int) -> dict:
        rows = self._q("SELECT id, matiere, titre, fichier, pages, passages, statut, ajoute_le, avertissement"
                       " FROM cours WHERE id = ? AND utilisateur = ?", (cid, uid))
        if not rows:
            raise ErreurCours("Cours introuvable.")
        return self._dict(rows[0])

    @staticmethod
    def _dict(r) -> dict:
        cles = ("id", "matiere", "titre", "fichier", "pages", "passages", "statut", "ajoute_le", "avertissement")
        d = dict(zip(cles, r))
        d["libelle_matiere"] = LIBELLES.get(d["matiere"], d["matiere"])
        return d

    def lister(self, uid: int) -> list[dict]:
        self._relancer(uid)
        rows = self._q("SELECT id, matiere, titre, fichier, pages, passages, statut, ajoute_le, avertissement"
                       " FROM cours WHERE utilisateur = ? ORDER BY matiere, ajoute_le DESC", (uid,))
        return [self._dict(r) for r in rows]

    def supprimer(self, uid: int, cid: int) -> None:
        with self._lock:
            with self._con:
                n = self._con.execute("DELETE FROM cours WHERE id = ? AND utilisateur = ?", (cid, uid)).rowcount
                if n and not self._fts_efface:  # SQLite ancien : index reecrit pour en retirer les mots
                    self._con.execute("INSERT INTO cours_fts (cours_fts) VALUES ('optimize')")
            if n:  # anciennes versions des pages recopiees dans le journal WAL : journal vide
                self._con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        if not n:
            raise ErreurCours("Cours introuvable.")

    def passage(self, uid: int, passage_id: str) -> dict | None:
        """« cours:<id_cours>:<id_passage> », seulement pour le proprietaire."""
        m = re.fullmatch(r"cours:(\d+):(\d+)", passage_id)
        if not m:
            return None
        rows = self._q("SELECT p.id, p.cours, p.rang, p.page, p.page_fin, p.texte, c.titre, c.matiere"
                       " FROM cours_passages p JOIN cours c ON c.id = p.cours"
                       " WHERE p.id = ? AND c.id = ? AND c.utilisateur = ?",
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
            except sqlite3.OperationalError as e:
                log.warning("recherche plein texte des cours indisponible : %s", e)
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
        rows = self._q(f"SELECT p.id, p.cours, p.rang, p.page, p.page_fin, p.texte, c.titre, c.matiere"
                       f" FROM cours_passages p JOIN cours c ON c.id = p.cours"
                       f" WHERE p.id IN ({','.join('?' * len(meilleurs))})",
                       tuple(int(i) for i in meilleurs))
        par_id = {str(r[0]): _vers_passage(r) for r in rows}
        return [par_id[i] for i in meilleurs if i in par_id]


def _avertissement_pages(vides: list[int]) -> str | None:
    if not vides:
        return None
    liste = ", ".join(map(str, vides[:-1])) + f" et {vides[-1]}" if len(vides) > 1 else str(vides[0])
    return (f"Page{'s' if len(vides) > 1 else ''} {liste} sans texte (scan ou image) : "
            f"{'leur' if len(vides) > 1 else 'son'} contenu n'est pas pris en compte.")


def anciens_numeros(passages: list[dict]) -> dict[str, tuple[str, ...]]:
    """Anciens numeros du Code civil (avant le 1er octobre 2016) cites par des passages de cours (audit C6)."""
    trouves: dict[str, tuple[str, ...]] = {}
    for p in passages:
        if p.get("type") == "cours":
            for ancien, nouveaux in concordance.anciens_numeros(extraire(p["texte"])).items():
                if nouveaux != (ancien,):
                    trouves.setdefault(ancien, nouveaux)
    return trouves


def avertir_anciens_numeros(reponse: dict, sources: list[dict], passages: list[dict]) -> None:
    """Point d'attention pour chaque ancien numero du Code civil present dans un passage de cours cite."""
    cites = {s["id"] for s in sources}
    for p in passages:
        if p["id"] not in cites:
            continue
        for ancien, nouveaux in anciens_numeros([p]).items():
            if any(f"article {ancien} " in e["texte"] for e in reponse["points_incertains"]):
                continue
            art = "à l'article" if len(nouveaux) == 1 else "aux articles"
            reponse["points_incertains"].append({
                "texte": (f"Votre cours cite l'article {ancien} du Code civil. S'il s'agit de l'ancienne "
                          f"numérotation (en vigueur jusqu'au 1er octobre 2016), son contenu se trouve aujourd'hui "
                          f"{art} {', '.join(nouveaux)} : le numéro {ancien} vise désormais une autre règle."),
                "sources": [p["id"]]})


def _vers_passage(r) -> dict:
    pid, cid, rang, page, page_fin, texte, titre, matiere = r
    ou = (f", pages {page} à {page_fin}" if page and page_fin and page_fin != page
          else f", page {page}" if page else "")
    return {
        "id": f"cours:{cid}:{pid}", "source_id": SOURCE_ID, "type": "cours", "numero": None,
        "entete": f"Mon cours « {titre} »{ou}", "titre": titre, "url": "", "version": "Cours déposé par l'étudiant",
        "texte": texte, "meta": {"cours": cid, "page": page, "page_fin": page_fin, "rang": rang, "matiere": matiere},
    }


# --- routes ------------------------------------------------------------------------

def creer_routes_cours(cours: Cours, utilisateur_requis) -> APIRouter:
    router = APIRouter()

    def _erreur(e: ErreurCours):
        raise HTTPException(422, str(e)) from None

    @router.get("/cours")
    def lister(u=Depends(utilisateur_requis)):
        return {"cours": cours.lister(u.id), "maximum": u.formule.cours_max, "formats": sorted(set(FORMATS))}

    # Comptes dont un depot est en cours (lecture du corps puis du fichier). Un seul par compte et
    # DEPOTS_SIMULTANES en tout : 40 fichiers de 20 Mo envoyes d'un coup saturaient la memoire, et deux depots
    # paralleles d'un meme compte passaient tous deux la limite de cours de la formule (audit du 2026-11-16).
    # Pas de verrou : la route est asynchrone, ce compteur n'est touche que par la boucle d'evenements.
    en_cours: set[int] = set()

    @router.post("/cours", status_code=201, dependencies=[Depends(verifier_origine)])
    async def deposer(request: Request, matiere: str, u=Depends(utilisateur_requis)):
        # Nom et titre en en-tetes (X-Lexia-Fichier, X-Lexia-Titre, encodes) : dans l'adresse, ils finissaient
        # dans les journaux de nginx et de Cloudflare (audit du 2026-11-16, point 16). Plus de repli sur les
        # parametres d'adresse (second audit, point 16) : un onglet tres ancien doit recharger la page.
        fichier = unquote(request.headers.get("x-lexia-fichier", ""))
        titre = unquote(request.headers.get("x-lexia-titre", ""))
        if not fichier:
            raise HTTPException(422, "Nom de fichier manquant : rechargez la page puis réessayez.")
        if any(ord(c) < 32 or ord(c) == 127 for c in fichier + titre):
            # Octet nul (cours%00.txt) : erreur 500 et depot decompte (audit du 19/11, SEC-8).
            raise HTTPException(422, "Nom de fichier ou titre invalide : renommez le fichier puis réessayez.")
        if not u.email_verifie:
            raise HTTPException(403, "Confirmez votre adresse e-mail pour déposer un cours : "
                                     "le lien vous a été envoyé à l'inscription.")
        longueur = int(request.headers.get("content-length") or 0)
        if longueur > TAILLE_MAX:
            raise HTTPException(413, "Fichier trop volumineux (20 Mo au plus).")
        if u.id in en_cours or len(en_cours) >= DEPOTS_SIMULTANES:
            raise HTTPException(429, "Un dépôt est déjà en cours de lecture : réessayez dans un instant.")
        en_cours.add(u.id)
        try:
            contenu = await request.body()
            from starlette.concurrency import run_in_threadpool

            return await run_in_threadpool(cours.ajouter, u.id, matiere, titre, fichier, contenu, u.formule.cours_max)
        except ErreurCours as e:
            _erreur(e)
        finally:
            en_cours.discard(u.id)

    @router.post("/cours/{cid}/supprimer", status_code=204, dependencies=[Depends(verifier_origine)])
    def supprimer(cid: int, u=Depends(utilisateur_requis)):
        try:
            cours.supprimer(u.id, cid)
        except ErreurCours as e:
            _erreur(e)

    return router
