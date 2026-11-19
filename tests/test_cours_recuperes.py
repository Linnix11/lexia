"""Page des cours recuperes sous licence libre : catalogue factice, aucun cours reel (docs/cours-libres.md)."""

import json

import pytest
from fastapi.testclient import TestClient

from api.comptes import Comptes
from api.config import Settings
from api.cours_recuperes import AVERTISSEMENT, Catalogue
from api.main import create_app
from tests.test_comptes import LLM, Retriever, inscrire

FACTICE = {
    "id": "cours-factice",
    "titre": "Cours factice de test",
    "matiere": "droit_constitutionnel",
    "auteur": "Auteur factice",
    "source": "Site factice",
    "source_url": "https://exemple.invalid/",
    "url_original": "https://exemple.invalid/cours-factice",
    "licence": "etalab-2.0",
    "mis_a_jour": "2026-01-15",
    "modifications": "Découpé en sections",
    "sections": [{"titre": "I. Première partie", "texte": "Texte factice."}],
}


def ecrire(chemin, entrees):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(entrees, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def env(tmp_path):
    catalogue = tmp_path / "cours_recuperes" / "catalogue.json"
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0,
                              cours_recuperes=catalogue),
                     retriever=Retriever(), llm=LLM(), comptes=Comptes(tmp_path / "comptes.db"))
    return TestClient(app), catalogue


def test_reserve_aux_comptes_et_vide_sans_catalogue(env):
    client, _ = env
    assert client.get("/cours-recuperes").status_code == 401
    inscrire(client)
    r = client.get("/cours-recuperes")
    assert r.status_code == 200 and r.json() == {"avertissement": AVERTISSEMENT, "cours": []}


def test_attribution_complete_et_avertissement(env):
    client, catalogue = env
    ecrire(catalogue, [FACTICE])
    inscrire(client)
    (fiche,) = client.get("/cours-recuperes").json()["cours"]
    assert fiche["auteur"] == "Auteur factice" and fiche["source"] == "Site factice"
    assert fiche["url_original"] == "https://exemple.invalid/cours-factice"
    assert (fiche["licence_libelle"], fiche["mis_a_jour"]) == ("Licence Ouverte 2.0", "2026-01-15")
    assert fiche["licence_url"].startswith("https://") and fiche["libelle_matiere"] == "Droit constitutionnel"
    assert fiche["sections"] == 1  # la liste ne renvoie pas le texte
    r = client.get("/cours-recuperes/cours-factice").json()
    assert r["avertissement"] == AVERTISSEMENT and r["sections"][0]["texte"] == "Texte factice."
    assert client.get("/cours-recuperes/absent").status_code == 404


@pytest.mark.parametrize("champ, valeur", [
    ("licence", "cc-by-nc-4.0"),          # usage commercial interdit
    ("licence", "inconnue"),
    ("matiere", "histoire_du_droit"),
    ("url_original", "http://exemple.invalid/x"),
    ("auteur", ""),
    ("sections", []),
])
def test_entree_invalide_ecartee_sans_perdre_les_autres(tmp_path, champ, valeur):
    chemin = tmp_path / "catalogue.json"
    ecrire(chemin, [{**FACTICE, "id": "mauvais", champ: valeur}, FACTICE])
    assert [c["id"] for c in Catalogue(chemin).lister()] == ["cours-factice"]


def test_catalogue_relu_quand_il_change_et_illisible_tolere(tmp_path):
    chemin = tmp_path / "catalogue.json"
    cat = Catalogue(chemin)
    assert cat.lister() == []
    ecrire(chemin, [FACTICE])
    assert len(cat.lister()) == 1
    ecrire(chemin, [FACTICE, {**FACTICE, "id": "deuxieme", "titre": "Autre cours factice"}])
    assert len(cat.lister()) == 2
    chemin.write_text("{pas du json", encoding="utf-8")
    assert cat.lister() == []
