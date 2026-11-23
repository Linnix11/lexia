"""Pages publiques prerendues (D116) : donnees du site a jour, articles cites conformes a l'index, service des pages."""

import json
import os
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import donnees_publiques
from api.config import ROOT
from api.serveur import creer_serveur


def test_donnees_du_site_a_jour():
    # Apres une modification des formules, des matieres ou du registre : python -m api.donnees_publiques
    assert donnees_publiques.FICHIER.read_text(encoding="utf-8") == donnees_publiques.texte()
    assert donnees_publiques.FICHIER_NOMS.read_text(encoding="utf-8") == donnees_publiques.texte_noms()


def test_toutes_les_citations_sont_ecrites():
    ecrites = json.loads(donnees_publiques.FICHIER_CITATIONS.read_text(encoding="utf-8"))
    assert list(ecrites) == list(donnees_publiques.CITATIONS)
    for cle, c in ecrites.items():
        assert c["alineas"] and c["url"].startswith("https://"), cle


def _index() -> Path | None:
    # LEXIA_INDEX, l'index du depot, ou celui du depot principal quand les tests tournent dans .claude/worktrees/<nom>
    for d in (os.environ.get("LEXIA_INDEX"), ROOT / "data" / "index", ROOT.parent.parent.parent / "data" / "index"):
        if d and (Path(d) / "lexia.sqlite").exists():
            return Path(d)
    return None


@pytest.mark.skipif(_index() is None, reason="index de recherche absent (data/index ou LEXIA_INDEX)")
def test_citations_conformes_a_l_index():
    # Un article modifie par une loi nouvelle fait echouer ce test : relancer python -m api.donnees_publiques
    # et relire les pages qui le citent (web/src/site/contenu/).
    attendu = donnees_publiques.texte_citations(_index())
    ecrit = donnees_publiques.FICHIER_CITATIONS.read_text(encoding="utf-8")
    textes = lambda t: {k: v["alineas"] for k, v in json.loads(t).items()}  # noqa: E731
    assert textes(ecrit) == textes(attendu)


def _serveur(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>coquille</html>")
    (dist / "sitemap.xml").write_text("<urlset/>")
    (dist / "pages" / "tarifs").mkdir(parents=True)
    (dist / "pages" / "index.html").write_text("<html>accueil prerendu</html>")
    (dist / "pages" / "tarifs" / "index.html").write_text("<html>tarifs prerendus</html>")
    (tmp_path / "secret").mkdir()
    (tmp_path / "secret" / "index.html").write_text("ne pas servir")
    return TestClient(creer_serveur(dist, FastAPI()))


def test_pages_prerendues_servies_a_leur_adresse(tmp_path):
    c = _serveur(tmp_path)
    assert c.get("/").text == "<html>accueil prerendu</html>"
    assert c.get("/tarifs").text == "<html>tarifs prerendus</html>"
    assert c.get("/tarifs/").text == "<html>tarifs prerendus</html>"
    assert c.get("/tarifs").headers["cache-control"] == "no-cache"
    assert c.get("/app").text == "<html>coquille</html>"            # page non prerendue : coquille de l'application
    assert c.get("/sitemap.xml").text == "<urlset/>"
    assert c.get("/sitemap.xml").headers["cache-control"] == "no-cache"   # audit du 2026-11-23, D11
    # dist/pages/ n'est pas une seconde adresse des memes pages
    assert c.get("/pages/tarifs/index.html").text == "<html>coquille</html>"
    assert "ne pas servir" not in c.get("/../secret").text
    assert "ne pas servir" not in c.get("/%2e%2e/secret").text


def test_head_accepte(tmp_path):
    c = _serveur(tmp_path)
    assert c.head("/").status_code == 200
    assert c.head("/tarifs").status_code == 200
    assert c.head("/sitemap.xml").status_code == 200
