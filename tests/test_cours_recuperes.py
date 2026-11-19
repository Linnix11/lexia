"""Page des cours recuperes sous licence libre : catalogue factice, aucun cours reel (docs/cours-libres.md)."""

import json

import pytest
from fastapi.testclient import TestClient

from api.comptes import Comptes
from api.config import Settings
from api.cours_recuperes import AVERTISSEMENT, Catalogue, CoursRecupere
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


# --- Ingestion (ingest/cours_recuperes.py), sur des documents factices ---------------------------------------

FICHE_SP = """<?xml version="1.0" encoding="UTF-8"?>
<Publication xmlns:dc="http://purl.org/dc/elements/1.1/" ID="F9999" type="Fiche d'information conditionnée"
  spUrl="https://www.service-public.gouv.fr/particuliers/vosdroits/F9999">
<dc:title>Fiche factice</dc:title><dc:creator>Direction de l'information légale et administrative</dc:creator>
<dc:date>modified 2026-03-02</dc:date><dc:type>Fiche pratique</dc:type>
<SousThemePere ID="N1">Couple</SousThemePere><DossierPere ID="N2"><Titre>Mariage</Titre></DossierPere>
<Introduction><Texte><Paragraphe>Introduction <MiseEnEvidence>factice</MiseEnEvidence>.</Paragraphe></Texte></Introduction>
<Texte><Chapitre><Titre><Paragraphe>Premier chapitre</Paragraphe></Titre>
  <Paragraphe>Le 1<Exposant>er</Exposant> janvier.</Paragraphe>
  <Liste type="puce"><Item><Paragraphe>Point un</Paragraphe></Item></Liste>
  <BlocCas><Cas><Titre>Cas factice</Titre><TitreRiche><Paragraphe>Cas factice</Paragraphe></TitreRiche>
    <Condition><estVrai var="T1"/></Condition><Paragraphe>Texte du cas.</Paragraphe></Cas></BlocCas>
  <ANoter><Titre>À noter</Titre><Paragraphe>Remarque.</Paragraphe></ANoter>
  <Tableau><Rangée type="header"><Cellule><Paragraphe>A</Paragraphe></Cellule><Cellule><Paragraphe>B</Paragraphe></Cellule></Rangée></Tableau>
</Chapitre></Texte>
<OuSAdresser><Titre>Mairie</Titre></OuSAdresser>
<Reference type="Texte de référence" URL="https://www.legifrance.gouv.fr/x"><Titre>Code civil : article 144</Titre></Reference>
</Publication>""".encode()


def test_fiche_service_public_rendue_et_rangee():
    from ingest.cours_recuperes import fiche_service_public
    c = fiche_service_public(FICHE_SP)
    assert (c["id"], c["matiere"], c["mis_a_jour"]) == ("sp-f9999", "droit_de_la_famille", "2026-03-02")
    assert c["source"] == "Service Public / DILA" and c["licence"] == "etalab-2.0"
    assert c["sections"][0] == {"titre": "", "texte": "Introduction factice."}
    chapitre = c["sections"][1]
    assert chapitre["titre"] == "Premier chapitre"
    assert chapitre["texte"].splitlines() == ["Le 1er janvier.", "- Point un", "Cas factice :", "Texte du cas.",
                                              "À noter : Remarque.", "A | B"]
    assert c["sections"][2] == {"titre": "Textes de référence", "texte": "- Code civil : article 144"}
    assert "Mairie" not in str(c)
    CoursRecupere.model_validate(c)
    # Sous-theme non retenu, ou question-reponse : pas reprise
    assert fiche_service_public(FICHE_SP.replace("Couple".encode(), "Vacances".encode())) is None
    assert fiche_service_public(FICHE_SP.replace(b"<dc:type>Fiche pratique", b"<dc:type>Question-r\xc3\xa9ponse")) is None


def test_texte_wiki_par_sections_sans_notes_ni_navigation():
    from ingest.cours_recuperes import texte_wiki
    html = ('<div class="mw-parser-output"><p>Intro <sup class="reference">[1]</sup>du cours.</p>'
            '<div class="navbox"><p>Navigation</p></div>'
            '<div class="mw-heading mw-heading2"><h2>Partie</h2><span class="mw-editsection">modifier</span></div>'
            '<p>Texte.</p><ul><li>Un</li><li>Deux<ul><li>Sous</li></ul></li></ul>'
            '<h3>Sous-partie</h3><table class="wikitable"><tr><td>a</td><td>b</td></tr></table></div>')
    assert texte_wiki(html) == [{"titre": "", "texte": "Intro du cours."},
                                {"titre": "Partie", "texte": "Texte.\n- Un\n- Deux\n- Sous\nSous-partie\na | b"}]


def test_ecrire_ecarte_les_entrees_invalides(tmp_path):
    from ingest.cours_recuperes import ecrire
    cible = tmp_path / "catalogue.json"
    valides = ecrire([FACTICE, {**FACTICE, "id": "nc", "licence": "cc-by-nc-4.0"}, FACTICE], cible)
    assert [c["id"] for c in valides] == ["cours-factice"]
    assert json.loads(cible.read_text(encoding="utf-8")) == valides
