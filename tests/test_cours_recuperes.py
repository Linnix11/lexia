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


# --- Index : fiches rangees a part du corpus officiel (D103) ------------------------------------------------

def test_passages_d_index_decoupes_et_sans_date_de_fraicheur():
    from ingest.cours_recuperes import passages
    long = "\n".join(f"Ligne {i} " + "x" * 90 for i in range(40))  # environ 4 000 caracteres
    fiche = {**FACTICE, "source": "Service Public / DILA", "sections": [{"titre": "I. Partie", "texte": long}]}
    (liste,) = passages([fiche, {**FACTICE, "id": "autre-site"}], "2026-11-19T10:00:00").values()
    assert len(liste) == 3 and all(len(p.texte) <= 1500 for p in liste)
    assert "\n".join(p.texte for p in liste) == long  # texte repris mot pour mot
    p = liste[0]
    assert (p.source_id, p.type, p.id) == ("fiches_service_public", "doctrine", "fiches_service_public:cours-factice:1")
    assert p.entete == "Cours factice de test > I. Partie" and p.url == FACTICE["url_original"]
    assert p.meta["cours_id"] == "cours-factice" and "date" not in p.meta


def test_groupes_n_ouvrent_jamais_les_fiches_aux_reponses():
    from api.retrieval.base import groupes
    toutes = ("code_civil", "judilibre", "fiches_service_public")
    assert groupes(None, toutes) == (("code_civil",), ("judilibre",))
    assert groupes(("fiches_service_public", "code_civil"), toutes) == (("code_civil",), ())


@pytest.fixture(scope="module")
def index_mixte(tmp_path_factory):
    """Un article et une fiche qui emploient les memes mots."""
    from ingest.build_index import build
    from ingest.cours_recuperes import passages
    from ingest.models import Passage
    base = tmp_path_factory.mktemp("cours_recuperes")
    (base / "p").mkdir()
    article = Passage(id="code_civil:art:229", source_id="code_civil", type="article", numero="229",
                      titre="Du divorce", alineas=["Le divorce peut être prononcé en cas de consentement mutuel."],
                      url="https://www.legifrance.gouv.fr/x", meta={"en_vigueur": True})
    fiche = {**FACTICE, "source": "Service Public / DILA", "matiere": "droit_de_la_famille",
             "sections": [{"titre": "", "texte": "Le divorce accepté se déroule devant le juge aux affaires familiales."}]}
    lignes = [article.to_dict()] + [p.to_dict() for p in passages([fiche], "d")["fiches_service_public"]]
    (base / "p" / "a.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in lignes), encoding="utf-8")
    build(passages_dir=base / "p", index_dir=base / "i", cache_dir=base / "vide", model="aucun")
    return base / "i"


def test_recherche_des_reponses_sans_fiches_et_recherche_a_part(index_mixte):
    from api.retrieval.local import LocalRetriever
    r = LocalRetriever(index_mixte)
    for sources in (None, ("code_civil", "fiches_service_public"), ("fiches_service_public",)):
        hits = r.search("divorce juge", sources=sources, k=8)
        assert all(h.passage["source_id"] != "fiches_service_public" for h in hits), sources
    assert [h.passage["id"] for h in r.search("divorce", sources=None, k=8)] == ["code_civil:art:229"]
    assert [p["meta"]["cours_id"] for p in r.rechercher_a_part("divorce juge")] == ["cours-factice"]
    assert r.couverture(None) == 0.0  # calculee sur les seules sources officielles (aucun vecteur ici)


def test_route_de_recherche_dans_le_texte(tmp_path):
    class Index:
        def rechercher_a_part(self, q, k=30):
            return [{"meta": {"cours_id": "cours-factice"}}, {"meta": {"cours_id": "absent-du-catalogue"}},
                    {"meta": {"cours_id": "cours-factice"}}]

    catalogue = tmp_path / "catalogue.json"
    ecrire(catalogue, [FACTICE])
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0,
                              cours_recuperes=catalogue),
                     retriever=Retriever(), llm=LLM(), comptes=Comptes(tmp_path / "comptes.db"))
    client = TestClient(app)
    inscrire(client)
    # Le retriever de test n'a pas de recherche a part : liste vide, sans erreur.
    assert client.get("/cours-recuperes/recherche", params={"q": "divorce"}).json() == {"cours": []}
    assert client.get("/cours-recuperes/recherche", params={"q": "di"}).status_code == 422
    from api.cours_recuperes import creer_routes_cours_recuperes
    from fastapi import FastAPI
    seule = FastAPI()
    seule.include_router(creer_routes_cours_recuperes(Catalogue(catalogue), lambda: None, Index()))
    assert TestClient(seule).get("/cours-recuperes/recherche", params={"q": "divorce"}).json() == {"cours": ["cours-factice"]}


def test_embeddings_sautent_les_fiches(tmp_path, monkeypatch):
    from ingest import embed
    for nom in ("code_civil", "fiches_service_public"):
        (tmp_path / f"{nom}.jsonl").write_text("", encoding="utf-8")
    vus = []
    monkeypatch.setattr(embed, "PASSAGES_DIR", tmp_path)
    monkeypatch.setattr(embed, "load_env", lambda *a: None)
    monkeypatch.setattr(embed.embedders, "config_env", lambda: ("local", "m"))
    monkeypatch.setattr(embed.embedders, "creer", lambda *a: None)
    monkeypatch.setattr(embed, "run", lambda s, emb, limite: vus.append(s) or 0)
    embed.main(["--all"])
    assert vus == ["code_civil"]


@pytest.mark.parametrize("theme, dossier, titre, attendu", [
    ("Fonctionnement de l'entreprise", "Formes juridiques", "Société anonyme (SA) : ce qu'il faut savoir", "droit_des_societes"),
    ("Fonctionnement de l'entreprise", "Formes juridiques", "Micro-entrepreneur : ce qu'il faut savoir", "droit_des_affaires"),
    ("Fonctionnement de l'entreprise", "Litiges commerciaux", "Arbitrage", "droit_des_affaires"),
    ("Étapes de vie", "Je crée", "Fiscalité de la société anonyme (SA) : ce qu'il faut savoir", "droit_fiscal"),
    ("Étapes de vie", "Je clos", "Conséquences fiscales de la cessation d'activité", "droit_fiscal"),
    ("Étapes de vie", "Je crée", "Cotisations sociales d'une SAS : ce qu'il faut savoir", "droit_social"),
    ("Étapes de vie", "Je transmets", "Cession du fonds de commerce à un tiers", "droit_des_affaires"),
    ("Étapes de vie", "Je crée", "Projet de création d'entreprise : comment concevoir un business plan", ""),
    ("Baux", "Bail commercial", "Renouvellement du bail commercial", "droit_des_affaires"),
    ("Pratiques commerciales", "Marchés publics", "Exécuter le marché public", "droit_administratif"),
    ("Ressources humaines", "Licenciement", "Licenciement pour motif économique", "droit_social"),
    ("Ressources humaines", "Aides à l'embauche", "Aide à l'embauche d'un jeune", ""),
    ("Environnement", "Publicité", "Publicité extérieure", ""),
])
def test_matiere_des_fiches_entreprendre(theme, dossier, titre, attendu):
    from ingest.cours_recuperes import matiere_entreprendre
    assert matiere_entreprendre(theme, dossier, titre) == attendu


def test_fiche_entreprendre_lien_vers_son_site():
    from ingest.cours_recuperes import fiche_service_public
    xml = (FICHE_SP.replace("<SousThemePere ID=\"N1\">Couple</SousThemePere>".encode(), b"")
           .replace("<DossierPere ID=\"N2\"><Titre>Mariage</Titre></DossierPere>".encode(),
                    "<Theme><Titre>Baux</Titre></Theme><DossierPere><Titre>Bail commercial</Titre></DossierPere>".encode()))
    c = fiche_service_public(xml, entreprendre=True)
    assert c["matiere"] == "droit_des_affaires" and c["source_url"] == "https://entreprendre.service-public.gouv.fr/"
    assert c["source"] == "Service Public / DILA" and c["licence"] == "etalab-2.0"
