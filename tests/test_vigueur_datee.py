"""Etat « en vigueur » a la date de la question, pas a celle de la construction de l'index.

Audit du 2026-11-19, SRC-3 et TST-8 : le 1er janvier 2027, 1 870 versions commencent et 949 finissent, sans
nouvelle archive DILA ce jour-la. Date simulee : on construit l'index le 19 novembre 2026, on interroge le
31 decembre puis le 1er janvier.
"""

import datetime as dt
import json

import pytest

from api import prompts, textes
from api.rag import Lexia
from api.retrieval.local import LocalRetriever
from ingest import build_index, mise_a_jour

CONSTRUCTION, VEILLE, BASCULE = "2026-11-19", "2026-12-31", "2027-01-01"


def _article(pid: str, numero: str, texte: str, meta: dict, statut: str) -> dict:
    return {"id": pid, "source_id": "code_civil", "type": "article", "numero": numero, "texte": texte,
            "entete": f"Code civil, article {numero} ({statut})", "empreinte": "e" + pid, "url": "u",
            "version": "v", "meta": meta}


ANCIENNE = _article("code_civil:ANCIEN", "9999", "Ancienne regle sur la garde des choses inanimees.",
                    {"en_vigueur": True, "date_debut": "2016-10-01", "date_fin": BASCULE},
                    "en vigueur, abrogation différée")
NOUVELLE = _article("code_civil:NOUVEAU", "9999", "Nouvelle regle sur la garde des choses inanimees.",
                    {"en_vigueur": False, "date_debut": BASCULE, "en_vigueur_le": BASCULE},
                    "pas encore en vigueur")
STABLE = _article("code_civil:STABLE", "1240", "Tout fait quelconque de l'homme qui cause a autrui un dommage.",
                  {"en_vigueur": True, "date_debut": "2016-10-01"}, "en vigueur")


class _Jour(dt.date):
    """date.today() simulee."""
    valeur = CONSTRUCTION

    @classmethod
    def today(cls):
        return dt.date.fromisoformat(cls.valeur)


@pytest.fixture
def jour(monkeypatch):
    monkeypatch.setattr(textes, "date", _Jour)
    monkeypatch.setattr(mise_a_jour, "date", _Jour)

    def regler(valeur: str) -> None:
        _Jour.valeur = valeur
    regler(CONSTRUCTION)
    return regler


@pytest.fixture
def index(tmp_path, jour):
    (tmp_path / "passages").mkdir()
    (tmp_path / "passages" / "code_civil.jsonl").write_text(
        "\n".join(json.dumps(p, ensure_ascii=False) for p in (ANCIENNE, NOUVELLE, STABLE)), encoding="utf-8")
    build_index.build(passages_dir=tmp_path / "passages", index_dir=tmp_path / "index", cache_dir=tmp_path / "vide",
                      model="aucun", aujourdhui=CONSTRUCTION)
    return tmp_path / "index"


def test_en_vigueur_a_une_date_donnee():
    assert textes.en_vigueur_aujourdhui(ANCIENNE["meta"], "code_civil", VEILLE) is True
    assert textes.en_vigueur_aujourdhui(ANCIENNE["meta"], "code_civil", BASCULE) is False
    assert textes.en_vigueur_aujourdhui(NOUVELLE["meta"], "code_civil", VEILLE) is False
    assert textes.en_vigueur_aujourdhui(NOUVELLE["meta"], "code_civil", BASCULE) is True


def test_index_note_sa_prochaine_bascule(index):
    assert (index / build_index.BASCULE).read_text().strip() == BASCULE
    assert not mise_a_jour.bascule_franchie(index, VEILLE)
    assert mise_a_jour.bascule_franchie(index, BASCULE)


def test_index_sans_date_programmee_ou_ancien(tmp_path, index):
    (index / build_index.BASCULE).write_text("\n")
    assert not mise_a_jour.bascule_franchie(index, "2099-01-01")
    (index / build_index.BASCULE).unlink()          # construit avant ce controle : reconstruit une fois
    assert mise_a_jour.bascule_franchie(index, VEILLE)
    assert not mise_a_jour.bascule_franchie(tmp_path / "absent", VEILLE)


def test_citation_trouve_la_version_du_jour(index, jour):
    r = LocalRetriever(index)
    jour(VEILLE)
    assert [p["id"] for p in r._par_numero("code_civil", "9999")] == [ANCIENNE["id"]]
    jour(BASCULE)   # index non reconstruit : la nouvelle version est trouvee, l'ancienne ne l'est plus
    assert [p["id"] for p in r._par_numero("code_civil", "9999")] == [NOUVELLE["id"]]


def test_version_finie_jamais_envoyee_au_modele(index, jour):
    lexia = Lexia(LocalRetriever(index), None)
    jour(VEILLE)
    ids = [p["id"] for p in lexia.rechercher("garde des choses inanimees", None, 8)[0]]
    assert ANCIENNE["id"] in ids
    jour(BASCULE)
    ids = [p["id"] for p in lexia.rechercher("garde des choses inanimees", None, 8)[0]]
    assert ANCIENNE["id"] not in ids
    ids = [p["id"] for p in lexia.rechercher("Que dit l'article 9999 du code civil ?", None, 8)[0]]
    assert ids[0] == NOUVELLE["id"] and ANCIENNE["id"] not in ids


def test_en_tete_des_extraits_corrige(jour):
    jour(BASCULE)
    assert "plus en vigueur depuis le 2027-01-01" in prompts.format_extraits([ANCIENNE])
    assert "[en vigueur depuis le 2027-01-01]" in prompts.format_extraits([NOUVELLE])
    assert "[" not in prompts.format_extraits([STABLE]).split("\n")[0][4:]


def test_mise_a_jour_reconstruit_a_la_bascule_sans_nouvelle_archive(tmp_path, index, jour, monkeypatch):
    """TST-3 : code 3 sans nouveaute ; reconstruction quand la date de bascule est franchie."""
    (index / mise_a_jour.ARCHIVES).write_text("LEGI_1.tar.gz\n")
    monkeypatch.setattr(mise_a_jour, "INDEX", index)
    monkeypatch.setattr(mise_a_jour, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(mise_a_jour, "archives_lues", lambda _: ["LEGI_1.tar.gz"])
    importees = []

    def importer(source, _args):
        importees.append(source)
        raise SystemExit("import lance")
    monkeypatch.setattr(mise_a_jour.run, "ingest", importer)

    jour(VEILLE)
    assert mise_a_jour.main(["--sans-telechargement"]) == mise_a_jour.RIEN_DE_NOUVEAU
    assert importees == []
    jour(BASCULE)
    with pytest.raises(SystemExit, match="import lance"):
        mise_a_jour.main(["--sans-telechargement"])
    assert importees


def test_mise_a_jour_refuse_un_index_trop_petit(tmp_path, index, monkeypatch):
    """TST-3 : code 1 si le nouvel index perd des passages (garde-fous), index en service inchange."""
    monkeypatch.setattr(mise_a_jour, "INDEX", index)
    monkeypatch.setattr(mise_a_jour, "NOUVEAU", tmp_path / "nouveau")
    monkeypatch.setattr(mise_a_jour, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(mise_a_jour, "archives_lues", lambda _: ["LEGI_2.tar.gz"])
    monkeypatch.setattr(mise_a_jour, "sources_dila", lambda: [])
    monkeypatch.setattr(mise_a_jour, "reconstituer", lambda *a: [])
    monkeypatch.setattr(mise_a_jour, "ajouter_nouvelles", lambda *a: ([], []))
    monkeypatch.setattr(mise_a_jour, "rafraichir", lambda *a: ([], []))
    monkeypatch.setattr(mise_a_jour.cours_recuperes, "main", lambda *a: 0)
    monkeypatch.setattr(mise_a_jour.embed, "main", lambda *a: 0)
    vide = tmp_path / "passages_vides"
    vide.mkdir()
    (vide / "code_civil.jsonl").write_text(json.dumps(STABLE), encoding="utf-8")
    construire = build_index.build
    monkeypatch.setattr(mise_a_jour.build_index, "build", lambda index_dir: construire(
        passages_dir=vide, index_dir=index_dir, cache_dir=tmp_path / "vide", model="aucun"))
    assert mise_a_jour.main(["--sans-telechargement"]) == 1
    assert (index / "lexia.sqlite").exists()

