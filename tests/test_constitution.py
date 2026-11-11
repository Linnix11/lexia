from pathlib import Path

import pytest

from ingest.sources import constitution
from ingest.sources.constitution import ParseError, parse

FIXTURE = Path(__file__).parent / "fixtures" / "constitution_extrait.html"


@pytest.fixture
def passages():
    html = FIXTURE.read_text(encoding="utf-8")
    return {p.id: p for p in parse(html, date_recuperation="2026-11-11T00:00:00+00:00", min_articles=5)}


def test_ids_et_ordre(passages):
    assert list(passages) == [
        "constitution_1958:preambule",
        "constitution_1958:art:1",
        "constitution_1958:art:2",
        "constitution_1958:art:61-1",
        "constitution_1958:art:72-4",
        "constitution_1958:art:89",
    ]


def test_version_et_lien(passages):
    art = passages["constitution_1958:art:61-1"]
    assert art.version == "Texte intégral en vigueur à jour de la révision constitutionnelle du 8 mars 2024"
    assert art.url == f"{constitution.URL}#article_61_1"
    assert art.date_recuperation == "2026-11-11T00:00:00+00:00"


def test_article_premier_hors_titre_et_alineas(passages):
    art1 = passages["constitution_1958:art:1"]
    assert art1.numero == "1"
    assert art1.titre is None
    assert len(art1.alineas) == 2


def test_entete(passages):
    assert passages["constitution_1958:art:61-1"].entete == (
        "Constitution du 4 octobre 1958, article 61-1 - Titre VII - LE CONSEIL CONSTITUTIONNEL")
    assert passages["constitution_1958:preambule"].entete == "Constitution du 4 octobre 1958, préambule"


def test_rattachement_au_titre(passages):
    assert passages["constitution_1958:art:2"].titre == "Titre premier - DE LA SOUVERAINETÉ"
    assert passages["constitution_1958:art:89"].titre == "Titre XVI - DE LA RÉVISION"


def test_nettoyage_espaces_et_retours_ligne(passages):
    alineas = passages["constitution_1958:art:2"].alineas
    assert alineas[0] == "L'hymne national est « La Marseillaise »."
    assert alineas[1] == "Ligne un\nLigne deux"


def test_contenu_hors_bloc_ignore(passages):
    assert all("lire aussi" not in p.texte.lower() for p in passages.values())


def test_empreinte_stable(passages):
    p = passages["constitution_1958:art:89"]
    assert p.empreinte == p.to_dict()["empreinte"]
    assert len(p.empreinte) == 64


def test_seuil_articles_bloque_corpus_incomplet():
    html = FIXTURE.read_text(encoding="utf-8")
    with pytest.raises(ParseError, match="articles trouves"):
        parse(html)  # seuil par defaut : 100 articles


def test_structure_inconnue():
    with pytest.raises(ParseError, match="introuvable"):
        parse("<html><body><p>rien</p></body></html>")
