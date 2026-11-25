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
    # Texte, numero et lien de chaque article (le lien n'etait pas compare : audit du 2026-11-23, D10 et T16) ;
    # pas la version, qui cite la date de l'archive DILA.
    attendu = donnees_publiques.texte_citations(_index())
    ecrit = donnees_publiques.FICHIER_CITATIONS.read_text(encoding="utf-8")
    champs = lambda t: {k: {c: v[c] for c in donnees_publiques.CHAMPS_COMPARES}  # noqa: E731
                        for k, v in json.loads(t).items()}
    assert champs(ecrit) == champs(attendu)


def test_liens_legifrance_selon_la_regle_actuelle():
    """D10 : un index d'avant B11 donnait /codes/ a la DDHC et a l'ordonnance 58-1067."""
    lien = donnees_publiques._lien
    assert lien("ddhc_1789", "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000006527432") == \
        "https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000006527432"
    assert lien("lois", "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000021450778").startswith(
        "https://www.legifrance.gouv.fr/loda/")
    assert lien("code_civil", "https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000032041571") == \
        "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000032041571"
    autre = "https://www.conseil-constitutionnel.fr/le-bloc-de-constitutionnalite/texte-integral-de-la-constitution"
    assert lien("constitution_1958", autre) == autre
    ecrites = json.loads(donnees_publiques.FICHIER_CITATIONS.read_text(encoding="utf-8"))
    for cle in ("ddhc_1789:6", "ddhc_1789:11", "ddhc_1789:13", "ddhc_1789:16", "ordonnance_58_1067:23-2"):
        assert "/loda/article_lc/" in ecrites[cle]["url"], cle
    assert all("/codes/" in c["url"] for k, c in ecrites.items() if k.startswith("code_"))


def test_ecarts_des_citations_publiees(tmp_path, monkeypatch):
    """C5 : chaque nuit, la copie publiee est comparee au nouvel index ; la version (date d'archive) est ignoree."""
    publiees = json.loads(donnees_publiques.FICHIER_CITATIONS.read_text(encoding="utf-8"))
    fichier = tmp_path / "citations-publiees.json"
    fichier.write_text(json.dumps(publiees), encoding="utf-8")
    actuelles = json.loads(json.dumps(publiees))
    for c in actuelles.values():
        c["version"] = "archive DILA LEGI du 2027-01-02"
    monkeypatch.setattr(donnees_publiques, "citations", lambda _index: actuelles)
    assert donnees_publiques.ecarts_citations(tmp_path, fichier) == []
    actuelles["code_civil:1240"]["alineas"] = ["Texte nouveau."]
    actuelles["ddhc_1789:6"]["url"] = "https://www.legifrance.gouv.fr/loda/article_lc/AUTRE"
    del actuelles["code_penal:121-3"]
    assert donnees_publiques.ecarts_citations(tmp_path, fichier) == [
        "code_civil:1240 : alineas change(s)", "code_penal:121-3 : plus cite par le depot",
        "ddhc_1789:6 : url change(s)"]
    assert donnees_publiques.ecarts_citations(tmp_path, tmp_path / "absent.json") == []

    def deux_versions(_index):
        raise ValueError("code_civil:1240 : 2 versions en vigueur dans l'index au lieu d'une")
    monkeypatch.setattr(donnees_publiques, "citations", deux_versions)
    assert donnees_publiques.ecarts_citations(tmp_path, fichier) == [
        "code_civil:1240 : 2 versions en vigueur dans l'index au lieu d'une"]


def test_mise_a_jour_previent_si_une_page_publique_cite_une_version_finie(tmp_path, monkeypatch):
    from ingest import mise_a_jour
    alertes = []
    monkeypatch.setattr(mise_a_jour.fraicheur, "alerter", alertes.append)
    monkeypatch.setattr(donnees_publiques, "ecarts_citations", lambda _i: [])
    assert mise_a_jour.citations_publiques(tmp_path) == [] and alertes == []
    monkeypatch.setattr(donnees_publiques, "ecarts_citations", lambda _i: ["code_civil:1240 : alineas change(s)"])
    assert mise_a_jour.citations_publiques(tmp_path) == ["code_civil:1240 : alineas change(s)"]
    assert len(alertes) == 1 and "recompiler" in alertes[0] and "code_civil:1240" in alertes[0]

    def casse(_i):
        raise OSError("index illisible")
    monkeypatch.setattr(donnees_publiques, "ecarts_citations", casse)
    assert mise_a_jour.citations_publiques(tmp_path) == ["controle impossible : index illisible"]


def _serveur(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>coquille</html>")
    (dist / "introuvable.html").write_text("<html>introuvable</html>")
    (dist / "chemins-application.json").write_text('["/", "/tarifs", "/app"]')
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
    # dist/pages/ n'est pas une seconde adresse des memes pages (404 depuis D134)
    assert c.get("/pages/tarifs/index.html").status_code == 404
    assert "ne pas servir" not in c.get("/../secret").text
    assert "ne pas servir" not in c.get("/%2e%2e/secret").text


def test_head_accepte(tmp_path):
    c = _serveur(tmp_path)
    assert c.head("/").status_code == 200
    assert c.head("/tarifs").status_code == 200
    assert c.head("/sitemap.xml").status_code == 200
