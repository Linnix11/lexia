"""Catalogue d'annales d'examens : metadonnees et liens uniquement.

Les sujets restent sur le site qui les publie (faculte ou association etudiante) : Lexia ne copie ni ne reheberge
aucun sujet ni corrige. Les administrateurs ajoutent et retirent les entrees depuis /admin.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.auth import verifier_origine
from api.matieres import LIBELLES

NIVEAUX = ("L1", "L2", "L3", "M1", "M2")
# Recueil couvrant toutes les matieres d'un semestre : affiche quel que soit le filtre de matiere.
RECUEIL = "recueil"
LIBELLE_RECUEIL = "Recueil, toutes matières"

SCHEMA = """
CREATE TABLE IF NOT EXISTS annales (
    id          INTEGER PRIMARY KEY,
    titre       TEXT NOT NULL,
    matiere     TEXT NOT NULL,
    niveau      TEXT NOT NULL,
    annee       INTEGER NOT NULL,
    universite  TEXT NOT NULL,
    session     TEXT NOT NULL DEFAULT '',
    url         TEXT NOT NULL,
    corrige     INTEGER NOT NULL DEFAULT 0,
    ajoute_le   TEXT NOT NULL
);
"""


class Annale(BaseModel):
    titre: str = Field(min_length=3, max_length=200)
    matiere: str
    niveau: str
    annee: int = Field(ge=1990, le=2100)
    universite: str = Field(min_length=2, max_length=120)
    session: str = Field(default="", max_length=60)
    url: str = Field(max_length=500)
    corrige: bool = False


def _valider(a: Annale) -> None:
    if a.matiere not in LIBELLES and a.matiere != RECUEIL:
        raise HTTPException(422, "Matière inconnue.")
    if a.niveau not in NIVEAUX:
        raise HTTPException(422, "Niveau inconnu.")
    u = urlparse(a.url)
    if u.scheme != "https" or not u.netloc:
        raise HTTPException(422, "Le lien doit être une adresse https:// complète.")


class Annales:
    def __init__(self, chemin: Path | str):
        if str(chemin) != ":memory:":
            Path(chemin).parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(str(chemin), check_same_thread=False)
        self._con.execute("PRAGMA journal_mode = WAL")
        self._con.executescript(SCHEMA)
        self._lock = threading.Lock()

    def _q(self, sql: str, params: tuple = ()) -> list[tuple]:
        with self._lock, self._con:
            return self._con.execute(sql, params).fetchall()

    def lister(self, matiere: str | None = None) -> list[dict]:
        sql = "SELECT id, titre, matiere, niveau, annee, universite, session, url, corrige, ajoute_le FROM annales"
        params: tuple = ()
        if matiere:
            sql += " WHERE matiere IN (?, ?)"
            params = (matiere, RECUEIL)
        sql += " ORDER BY annee DESC, niveau, titre"
        cles = ("id", "titre", "matiere", "niveau", "annee", "universite", "session", "url", "corrige", "ajoute_le")
        out = []
        for r in self._q(sql, params):
            d = dict(zip(cles, r))
            d["corrige"] = bool(d["corrige"])
            d["libelle_matiere"] = LIBELLE_RECUEIL if d["matiere"] == RECUEIL else LIBELLES.get(d["matiere"], d["matiere"])
            out.append(d)
        return out

    def ajouter(self, a: Annale) -> dict:
        with self._lock, self._con:
            cur = self._con.execute(
                "INSERT INTO annales (titre, matiere, niveau, annee, universite, session, url, corrige, ajoute_le)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (a.titre.strip(), a.matiere, a.niveau, a.annee, a.universite.strip(), a.session.strip(), a.url.strip(),
                 int(a.corrige), datetime.now(timezone.utc).isoformat(timespec="seconds")))
            nid = cur.lastrowid
        return next(x for x in self.lister() if x["id"] == nid)

    def supprimer(self, aid: int) -> bool:
        with self._lock, self._con:
            return self._con.execute("DELETE FROM annales WHERE id = ?", (aid,)).rowcount > 0


def creer_routes_annales(annales: Annales, admin_requis, journal) -> tuple[APIRouter, APIRouter]:
    """(routes publiques /annales, routes d'administration /admin/annales)."""
    public = APIRouter()
    admin = APIRouter()

    @public.get("/annales")
    def lister(matiere: str | None = None):
        return {"niveaux": list(NIVEAUX), "recueil": {"id": RECUEIL, "libelle": LIBELLE_RECUEIL}, "annales": annales.lister(matiere)}

    @admin.post("/annales", dependencies=[Depends(verifier_origine)])
    def ajouter(a: Annale, moi=Depends(admin_requis)):
        _valider(a)
        res = annales.ajouter(a)
        journal.ecrire("admin", action="annale_ajout", par=moi.id, cible=res["id"])
        return res

    @admin.post("/annales/{aid}/supprimer", status_code=204, dependencies=[Depends(verifier_origine)])
    def supprimer(aid: int, moi=Depends(admin_requis)):
        if not annales.supprimer(aid):
            raise HTTPException(404, "Annale introuvable.")
        journal.ecrire("admin", action="annale_suppression", par=moi.id, cible=aid)

    return public, admin
