"""Tests sur de vrais documents des archives DILA (copies dans tests/fixtures/)."""

import json
import re
from pathlib import Path

import pytest

from ingest import embed, jurisprudence
from ingest.jurisprudence import date_fr, decouper
from ingest.load_db import COLONNES, ligne
from ingest.sources import cass, constit, legi

FIX = Path(__file__).parent / "fixtures"


def lire(nom: str) -> bytes:
    return (FIX / nom).read_bytes()


# --- Conseil constitutionnel -------------------------------------------------

@pytest.fixture
def qpc_2023_1075():
    return constit.parse_decision(lire("constit_2023-1075_QPC.xml"), date_recuperation="d", version="v")


def test_constit_metadonnees(qpc_2023_1075):
    p = qpc_2023_1075[0]
    assert p.meta["numero"] == "2023-1075"
    assert p.meta["nature"] == "QPC"
    assert p.meta["ecli"].startswith("ECLI:FR:CC:")
    assert p.entete.startswith("Conseil constitutionnel, décision n° 2023-1075 QPC du 18 janvier 2024")
    assert p.url.startswith("https://www.conseil-constitutionnel.fr/decision/")


def test_constit_decoupage(qpc_2023_1075):
    types = [p.type for p in qpc_2023_1075]
    assert types[-1] == "dispositif" and set(types[:-1]) == {"motifs"}
    assert qpc_2023_1075[0].numero == "1-2"
    assert qpc_2023_1075[-1].texte.startswith("LE CONSEIL CONSTITUTIONNEL DÉCIDE")
    # visas et formule d'introduction non indexes
    tout = " ".join(p.texte for p in qpc_2023_1075)
    assert "Au vu des textes suivants" not in tout
    assert "FONDÉ SUR CE QUI SUIT" not in tout.upper()
    # ids uniques et numerotation continue
    assert len({p.id for p in qpc_2023_1075}) == len(qpc_2023_1075)


def test_constit_dispositif_en_lettres_espacees():
    ps = constit.parse_decision(lire("constit_2013-332_QPC.xml"), date_recuperation="d", version="v")
    assert ps[-1].type == "dispositif"
    assert ps[-1].texte.startswith("D É C I D E")


def test_constit_contentieux_electoral_exclu():
    assert constit.parse_decision(lire("constit_93-1615_AN.xml"), date_recuperation="d", version="v") == []


# --- Cour de cassation -------------------------------------------------------

def test_cass_arret_moderne():
    ps = cass.parse_arret(lire("cass_moderne.xml"), date_recuperation="d", version="v")
    assert [p.type for p in ps] == ["sommaire", "motifs", "motifs", "dispositif"]
    assert [p.numero for p in ps] == [None, "1-3", "4-9", None]
    assert ps[0].entete.startswith("Cour de cassation, civile, Chambre civile 1")
    assert ps[2].texte.startswith("Réponse de la Cour\nRecevabilité du moyen\n4.")
    assert ps[-1].texte.startswith("PAR CES MOTIFS")
    assert all("MOYEN ANNEX" not in p.texte.upper() for p in ps)
    assert ps[0].meta["formation"] == "Première chambre civile"
    assert ps[0].url == f"https://www.legifrance.gouv.fr/juri/id/{ps[0].meta['id_dila']}"


def test_cass_arret_ancien_sans_numeros_inventes():
    ps = cass.parse_arret(lire("cass_civ1_2016_ancien.xml"), date_recuperation="d", version="v")
    assert ps[0].type == "sommaire" and ps[-1].type == "dispositif"
    assert all(p.numero is None for p in ps)
    assert all("MOYEN ANNEX" not in p.texte.upper() for p in ps)


def test_cass_perimetre(monkeypatch):
    # toutes les chambres depuis 2000 : la 2e chambre civile n'est plus filtree par theme
    ps = cass.parse_arret(lire("cass_civ2_secu.xml"), date_recuperation="d", version="v")
    assert ps and {p.source_id for p in ps} == {"judilibre"}
    # filtre par source : un arret civil n'appartient pas a la chambre sociale
    assert cass.parse_arret(lire("cass_civ2_secu.xml"), date_recuperation="d", version="v", seulement="cass_sociale") == []
    # arret de 2009 : dans le perimetre (>= 2000), exclu si la date minimale est plus recente
    assert cass.parse_arret(lire("cass_civ1_avant_2016.xml"), date_recuperation="d", version="v")
    monkeypatch.setattr(cass, "DATE_MIN", "2010-01-01")
    assert cass.parse_arret(lire("cass_civ1_avant_2016.xml"), date_recuperation="d", version="v") == []


# --- Code civil (LEGI) -------------------------------------------------------

def test_legi_article_en_vigueur():
    p = legi.parse_article(lire("LEGIARTI000032041571.xml"), date_recuperation="d", version_archive="a")
    assert p.id == "code_civil:LEGIARTI000032041571"
    assert p.numero == "1240"
    assert p.meta["en_vigueur"] is True
    assert p.meta["date_debut"] == "2016-10-01" and p.meta["date_fin"] is None
    assert "Sous-titre II : La responsabilité extracontractuelle" in p.titre
    assert p.texte.startswith("Tout fait quelconque de l'homme")
    assert p.entete.startswith("Code civil, article 1240 (en vigueur, depuis le 1er octobre 2016)")


def test_legi_ancienne_version():
    p = legi.parse_article(lire("LEGIARTI000006438819.xml"), date_recuperation="d", version_archive="a")
    assert p.numero == "1382"
    assert p.meta["en_vigueur"] is False and p.meta["etat"] == "MODIFIE"
    assert p.meta["date_fin"] == "2016-10-01"
    # le plan retenu est celui applicable a la date de la version, pas le plan actuel
    assert "Titre IV : Des engagements qui se forment sans convention" in p.titre
    assert "modifié, du 21 mars 1804 au 1er octobre 2016" in p.entete


# --- Decoupage generique -----------------------------------------------------

def test_date_fr():
    assert date_fr("2024-01-01") == "1er janvier 2024"
    assert date_fr("2016-10-15") == "15 octobre 2016"
    assert date_fr("inconnue") == "inconnue"


def test_decouper_regroupe_sans_couper_et_scinde_les_geants():
    lignes = [f"{i}. " + "x" * 900 for i in range(1, 6)] + ["7. " + "y" * 20]
    morceaux = decouper(lignes, lambda l: l.startswith("DÉCIDE"), chunk_chars=2000)
    assert [m.plage for m in morceaux] == ["1-2", "3-4", "5-7"]

    geant = ["1. debut"] + ["z" * 1000 for _ in range(10)]
    morceaux = decouper(geant, lambda l: False)
    assert all(len(m.alineas[0]) <= jurisprudence.PARA_MAX_CHARS for m in morceaux)
    assert {m.plage for m in morceaux} == {"1"}


# --- Embeddings et chargement ------------------------------------------------

def test_embed_encodage_aller_retour():
    v = [0.25, -1.5, 3.0]
    assert embed.decode(embed.encode(v)) == v


def test_embed_selection(tmp_path):
    f = tmp_path / "s.jsonl"
    rows = [
        {"id": "a", "empreinte": "1", "texte": "A", "entete": "", "meta": {}},
        {"id": "b", "empreinte": "2", "texte": "B", "entete": "E", "meta": {"en_vigueur": False}},
        {"id": "c", "empreinte": "3", "texte": "C", "entete": "E", "meta": {"en_vigueur": True}},
        {"id": "d", "empreinte": "4", "texte": "D", "entete": "", "meta": {}},
    ]
    f.write_text("\n".join(json.dumps(r) for r in rows))
    todo = list(embed.a_calculer(f, done={"a": "1", "d": "ancienne"}))
    assert [(i, t) for i, _, t in todo] == [("c", "E\n\nC"), ("d", "D")]


def test_load_db_ligne():
    p = legi.parse_article(lire("LEGIARTI000006438819.xml"), date_recuperation="2026-11-11T00:00:00+00:00",
                           version_archive="a").to_dict()
    row = dict(zip(COLONNES, ligne(p)))
    assert row["en_vigueur"] is False
    assert row["date_debut"] == "1804-03-21" and row["date_fin"] == "2016-10-01"
    assert row["date_decision"] is None
    j = constit.parse_decision(lire("constit_2023-1075_QPC.xml"), date_recuperation="d", version="v")[0].to_dict()
    row = dict(zip(COLONNES, ligne(j)))
    assert row["en_vigueur"] is None and row["date_decision"] == "2024-01-18"
