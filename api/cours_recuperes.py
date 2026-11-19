"""Cours recuperes sur des sites tiers sous licence libre, affiches sur une page a part (docs/cours-libres.md).

Ce ne sont pas des sources officielles : ils ne servent pas aux reponses de l'assistant et chaque cours est
presente avec son avertissement et son attribution (auteur, source, licence, date, lien vers l'original), qui sont
les obligations des licences retenues. Le catalogue est un fichier JSON ecrit par l'ingestion ; tant que l'editeur
n'a pas donne son accord sur les sources, il n'existe pas et la page est vide.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ValidationError, field_validator

from api.matieres import LIBELLES

log = logging.getLogger(__name__)

AVERTISSEMENT = ("Cours récupérés sur des sites tiers sous licence libre. Ils ne sont pas rédigés par Lexia et "
                 "peuvent contenir des erreurs ou être dépassés. Vérifiez toujours avec les textes officiels.")

# Licences qui permettent un usage commercial (Lexia est payante) : aucune clause NC. Libelle et texte officiel.
LICENCES: dict[str, tuple[str, str]] = {
    "etalab-2.0": ("Licence Ouverte 2.0", "https://github.com/etalab/licence-ouverte/blob/master/LO.md"),
    # Adresse donnee par data.gouv.fr (licence « fr-lo » du jeu des fiches Particuliers de service-public)
    "etalab-1.0": ("Licence Ouverte 1.0", "https://www.etalab.gouv.fr/wp-content/uploads/2014/05/Licence_Ouverte.pdf"),
    "cc-by-sa-4.0": ("CC BY-SA 4.0", "https://creativecommons.org/licenses/by-sa/4.0/deed.fr"),
    "cc-by-4.0": ("CC BY 4.0", "https://creativecommons.org/licenses/by/4.0/deed.fr"),
}


def _https(url: str) -> str:
    u = urlparse(url)
    if u.scheme != "https" or not u.netloc:
        raise ValueError("adresse https:// complete attendue")
    return url


class Section(BaseModel):
    titre: str = Field(default="", max_length=300)
    texte: str = Field(min_length=1)


class CoursRecupere(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,99}$")
    titre: str = Field(min_length=2, max_length=300)
    matiere: str
    auteur: str = Field(min_length=1, max_length=300)      # auteurs, ou « Contributeurs de Wikiversité »
    source: str = Field(min_length=1, max_length=120)      # nom du site : « Vie-publique.fr »
    source_url: str                                        # accueil du site
    url_original: str                                      # page d'origine du cours
    historique_url: str = ""                               # liste des auteurs (wikis), facultatif
    licence: str
    mis_a_jour: date                                       # derniere mise a jour indiquee par la source
    modifications: str = Field(default="", max_length=300)  # « Decoupe en sections, mise en forme retiree »
    sections: list[Section] = Field(min_length=1)

    _https_source = field_validator("source_url", "url_original")(_https)

    @field_validator("historique_url")
    @classmethod
    def _historique(cls, v: str) -> str:
        return _https(v) if v else v

    @field_validator("matiere")
    @classmethod
    def _matiere(cls, v: str) -> str:
        if v not in LIBELLES:
            raise ValueError("matiere inconnue")
        return v

    @field_validator("licence")
    @classmethod
    def _licence(cls, v: str) -> str:
        if v not in LICENCES:
            raise ValueError("licence non admise (usage commercial non permis ou inconnue)")
        return v


def _fiche(c: CoursRecupere) -> dict:
    libelle, url = LICENCES[c.licence]
    d = c.model_dump(mode="json", exclude={"sections"})
    d.update(libelle_matiere=LIBELLES[c.matiere], licence_libelle=libelle, licence_url=url,
             sections=len(c.sections))
    return d


class Catalogue:
    """Relu quand le fichier change (mise a jour nocturne) ; une entree invalide est ecartee, pas le catalogue."""

    def __init__(self, chemin: Path | str):
        self.chemin = Path(chemin)
        self._lock = threading.Lock()
        self._cle: tuple[int, int] | None = None
        self._cours: dict[str, CoursRecupere] = {}

    def _charger(self) -> dict[str, CoursRecupere]:
        try:
            st = self.chemin.stat()
        except FileNotFoundError:
            return {}
        with self._lock:
            if self._cle != (st.st_mtime_ns, st.st_size):
                cours: dict[str, CoursRecupere] = {}
                try:
                    brut = json.loads(self.chemin.read_text(encoding="utf-8"))
                except (OSError, ValueError) as e:
                    log.error("catalogue des cours recuperes illisible : %s", e)
                    brut = []
                for i, entree in enumerate(brut if isinstance(brut, list) else []):
                    try:
                        c = CoursRecupere.model_validate(entree)
                    except ValidationError as e:
                        log.warning("cours recupere %s ecarte : %s", i, e.errors()[0].get("msg"))
                        continue
                    cours[c.id] = c
                self._cours, self._cle = cours, (st.st_mtime_ns, st.st_size)
            return self._cours

    def lister(self) -> list[dict]:
        cours = sorted(self._charger().values(), key=lambda c: (LIBELLES[c.matiere], c.titre.casefold()))
        return [_fiche(c) for c in cours]

    def lire(self, cid: str) -> dict | None:
        c = self._charger().get(cid)
        if c is None:
            return None
        return {**_fiche(c), "sections": [s.model_dump() for s in c.sections]}


def creer_routes_cours_recuperes(catalogue: Catalogue, utilisateur_requis, retriever=None) -> APIRouter:
    """retriever : index de recherche ; seule sa recherche a part (`rechercher_a_part`) est utilisee ici."""
    routes = APIRouter()

    @routes.get("/cours-recuperes")
    def lister(_=Depends(utilisateur_requis)):
        return {"avertissement": AVERTISSEMENT, "cours": catalogue.lister()}

    @routes.get("/cours-recuperes/recherche")
    def rechercher(q: str = Query(min_length=3, max_length=200), _=Depends(utilisateur_requis)):
        """Cours dont le texte repond a la recherche (index plein texte, sources a part), du plus pertinent au moins."""
        chercher = getattr(retriever, "rechercher_a_part", None)
        ids: list[str] = []
        for p in chercher(q) if chercher else []:
            cid = (p.get("meta") or {}).get("cours_id")
            if cid and cid not in ids and catalogue.lire(cid) is not None:
                ids.append(cid)
        return {"cours": ids[:50]}

    @routes.get("/cours-recuperes/{cid}")
    def lire(cid: str, _=Depends(utilisateur_requis)):
        c = catalogue.lire(cid)
        if c is None:
            raise HTTPException(404, "Cours introuvable.")
        return {"avertissement": AVERTISSEMENT, **c}

    return routes
