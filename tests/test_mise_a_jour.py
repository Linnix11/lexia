"""Mise a jour du corpus par les archives quotidiennes de la DILA (D78)."""

import io
import json
import sqlite3
import tarfile
from pathlib import Path

import numpy as np

from ingest import dila, mise_a_jour
from ingest.sources import codes

GLOBALE = "Freemium_jade_global_20261108-140000.tar.gz"


def archive(chemin: Path, fichiers: dict[str, bytes | str]) -> Path:
    with tarfile.open(chemin, "w:gz") as tar:
        for nom, contenu in fichiers.items():
            data = contenu.encode() if isinstance(contenu, str) else contenu
            info = tarfile.TarInfo(nom)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return chemin


def jade(n: int) -> str:
    return f"jade/global/publie/CETA/TEXT/00/00/00/00/00/CETATEXT{n:012d}.xml"


def test_archives_quotidiennes_dans_l_ordre_apres_la_globale(tmp_path):
    archive(tmp_path / GLOBALE, {})
    for h in ("20261110-213159", "20261107-210000", "20261109-212854"):
        archive(tmp_path / f"JADE_{h}.tar.gz", {})
    assert [dila.horodatage(p) for p in dila.increments(tmp_path, "jade")] == ["20261109-212854", "20261110-213159"]
    assert dila.date_corpus(tmp_path, "jade") == "2026-11-08, mise à jour du 2026-11-10"


def test_jurisprudence_a_jour_des_archives_quotidiennes(tmp_path):
    archive(tmp_path / GLOBALE, {jade(1): "A", jade(2): "B ancien", jade(3): "C"})
    archive(tmp_path / "JADE_20261109-210000.tar.gz", {
        f"20261109-210000/{jade(2)}": "B nouveau",
        "20261109-210000/liste_suppression_jade.dat": f"{jade(3)[:-4]} D\n",
    })
    archive(tmp_path / "JADE_20261110-210000.tar.gz", {f"20261110-210000/{jade(4)}": "D"})
    lus = {dila.id_document(nom): raw.decode() for nom, raw in dila.iter_xml_a_jour(tmp_path, "jade")}
    assert lus == {"CETATEXT000000000001": "A", "CETATEXT000000000002": "B nouveau", "CETATEXT000000000004": "D"}


VERSION_LOI = """<TEXTE_VERSION><META><META_COMMUN><NATURE>LOI</NATURE></META_COMMUN><META_SPEC>
<META_TEXTE_CHRONICLE><DATE_TEXTE>2026-11-12</DATE_TEXTE></META_TEXTE_CHRONICLE><META_TEXTE_VERSION>
<TITREFULL>Loi n° 2026-1 du 12 novembre 2026</TITREFULL></META_TEXTE_VERSION></META_SPEC></META></TEXTE_VERSION>"""


def test_codes_et_lois_mis_a_jour_par_les_archives_quotidiennes(tmp_path, monkeypatch):
    monkeypatch.setattr(codes, "CODES", (codes.Code("code_test", "LEGITEXT000000000010", "Code test"),))
    archive(tmp_path / "Freemium_legi_global_20261108-140000.tar.gz", {})
    (tmp_path / "inventaire_legi_20261108.json").write_text(json.dumps({"lois": [
        ["JORFTEXT000000000020", "LOI", "2000-01-01", "Loi supprimee"],
        ["JORFTEXT000000000030", "LOI", "2000-01-01", "Loi qui entre en vigueur"]]}))
    dest = tmp_path / "extrait_legi_20261108"
    for texte in ("LEGITEXT000000000010", "JORFTEXT000000000020", "JORFTEXT000000000030"):
        f = dest / texte / "article" / "LEGIARTI000000000001.xml"
        f.parent.mkdir(parents=True)
        f.write_text("ancien")
    vig, non_vig = "legi/global/code_et_TNC_en_vigueur", "legi/global/code_et_TNC_non_vigueur"
    h = "20261112-210000"
    archive(tmp_path / f"LEGI_{h}.tar.gz", {
        f"{h}/{vig}/code_en_vigueur/LEGI/TEXT/LEGITEXT000000000010/article/LEGIARTI000000000001.xml": "modifie",
        f"{h}/{vig}/code_en_vigueur/LEGI/TEXT/LEGITEXT000000000010/article/LEGIARTI000000000002.xml": "nouveau",
        # loi deplacee de non_vigueur vers en_vigueur : supprimee puis republiee dans la meme archive
        f"{h}/{vig}/TNC_en_vigueur/JORF/TEXT/JORFTEXT000000000030/article/LEGIARTI000000000001.xml": "en vigueur",
        # nouvelle loi : inventoriee, ses articles extraits
        f"{h}/{vig}/TNC_en_vigueur/JORF/TEXT/JORFTEXT000000000040/texte/version/LEGITEXT000000000041.xml": VERSION_LOI,
        f"{h}/{vig}/TNC_en_vigueur/JORF/TEXT/JORFTEXT000000000040/article/LEGIARTI000000000042.xml": "loi nouvelle",
        f"{h}/liste_suppression_legi_dossier.dat": (f"{vig}/TNC_en_vigueur/JORF/TEXT/JORFTEXT000000000020 D\n"
                                                    f"{non_vig}/TNC_non_vigueur/JORF/TEXT/JORFTEXT000000000030 D\n"),
    })
    assert codes.appliquer_increments(tmp_path, dest, "20261108") == [h]
    assert (dest / "LEGITEXT000000000010/article/LEGIARTI000000000001.xml").read_text() == "modifie"
    assert (dest / "LEGITEXT000000000010/article/LEGIARTI000000000002.xml").read_text() == "nouveau"
    assert not (dest / "JORFTEXT000000000020").exists()
    assert (dest / "JORFTEXT000000000030/article/LEGIARTI000000000001.xml").read_text() == "en vigueur"
    assert (dest / "JORFTEXT000000000040/article/LEGIARTI000000000042.xml").read_text() == "loi nouvelle"
    inventaire = json.loads((tmp_path / "inventaire_legi_20261108.json").read_text())
    assert ["JORFTEXT000000000040", "LOI", "2026-11-12", "Loi n° 2026-1 du 12 novembre 2026"] in inventaire["lois"]
    assert codes.appliquer_increments(tmp_path, dest, "20261108") == []   # deja appliquee


def index(dossier: Path, passages: list[tuple[str, str]], vecteurs: int) -> Path:
    dossier.mkdir()
    con = sqlite3.connect(dossier / "lexia.sqlite")
    con.execute("CREATE TABLE passages (rowid INTEGER PRIMARY KEY, id TEXT, source_id TEXT, empreinte TEXT, data TEXT)")
    con.executemany("INSERT INTO passages (id, source_id, empreinte, data) VALUES (?,?,?,?)",
                    [(pid, src, "e" + pid, json.dumps({"id": pid})) for pid, src in passages])
    con.commit()
    con.close()
    np.save(dossier / "vectors.npy", np.eye(vecteurs, 4, dtype=np.float32))
    (dossier / "vectors_ids.json").write_text(json.dumps([pid for pid, _ in passages[:vecteurs]]))
    (dossier / "vectors_model.txt").write_text("modele")
    return dossier


def test_garde_fous_du_nouvel_index(tmp_path):
    actuel = index(tmp_path / "actuel", [(f"p{i}", "code_civil") for i in range(100)] + [("c1", "constitution")], 100)
    assert mise_a_jour.verifier(actuel, index(tmp_path / "bon", [(f"p{i}", "code_civil") for i in range(101)]
                                              + [("c1", "constitution")], 100)) == []
    ecarts = mise_a_jour.verifier(actuel, index(tmp_path / "mauvais", [(f"p{i}", "code_civil") for i in range(50)], 50))
    assert len(ecarts) == 3   # passages, embeddings, source disparue


def test_cache_amorce_depuis_l_index_et_sources_hors_dila_reconstituees(tmp_path):
    actuel = index(tmp_path / "index", [("a", "code_civil"), ("b", "constitution_1958")], 2)
    cache, passages = tmp_path / "embeddings", tmp_path / "passages"
    passages.mkdir()
    assert mise_a_jour.amorcer_cache(actuel, cache) == 2
    lignes = [json.loads(x) for x in (cache / "constitution_1958.jsonl").read_text().splitlines()]
    assert lignes[0]["id"] == "b" and lignes[0]["empreinte"] == "eb" and lignes[0]["model"] == "modele"
    assert mise_a_jour.amorcer_cache(actuel, cache) == 0   # deja amorce pour ce modele : rien a faire
    assert mise_a_jour.reconstituer(actuel, passages, a_garder={"code_civil"}) == ["constitution_1958"]
    assert json.loads((passages / "constitution_1958.jsonl").read_text()) == {"id": "b"}


def test_amorce_additive_avec_des_lignes_calculees_sur_le_mac(tmp_path):
    actuel = index(tmp_path / "index", [("a", "code_civil"), ("b", "code_civil"), ("c", "judilibre")], 3)
    cache = tmp_path / "embeddings"
    cache.mkdir()
    # Envoye du Mac avant le premier passage : une nouvelle source, et « b » deja present (meme empreinte)
    mac = [{"id": "n", "empreinte": "en", "model": "modele", "dim": 4, "b64": ""},
           {"id": "b", "empreinte": "eb", "model": "modele", "dim": 4, "b64": ""}]
    (cache / "code_civil.jsonl").write_text("".join(json.dumps(r) + "\n" for r in mac))
    assert mise_a_jour.amorcer_cache(actuel, cache) == 2   # a et c ajoutes, b deja la
    civil = [json.loads(x)["id"] for x in (cache / "code_civil.jsonl").read_text().splitlines()]
    assert civil == ["n", "b", "a"]   # lignes du Mac gardees, celles de l'index ajoutees a la suite
    assert [json.loads(x)["id"] for x in (cache / "judilibre.jsonl").read_text().splitlines()] == ["c"]


def test_traites_de_l_union_ajoutes_une_fois_cedh_et_onu_jamais(tmp_path):
    """D98 : une source hors DILA active mais absente est telechargee une nuit ; un echec ne bloque rien ; une
    source en attente d'autorisation (Convention EDH, Charte des Nations unies) n'est jamais lue."""
    passages = tmp_path / "passages"
    passages.mkdir()
    (passages / "constitution_1958.jsonl").write_text("{}\n")
    actives = mise_a_jour.sources_actives()
    assert {"tue", "tfue", "charte_droits_fondamentaux_ue"} <= actives and not {"cedh", "charte_onu"} & actives
    lus = []

    def importer(s):
        lus.append(s)
        if s == "tfue":
            raise RuntimeError("site indisponible")
        (passages / f"{s}.jsonl").write_text("{}\n")

    ajoutees, echecs = mise_a_jour.ajouter_nouvelles(passages, actives, importer)
    assert ajoutees == ["charte_droits_fondamentaux_ue", "tue"] and echecs == ["tfue"]
    assert "cedh" not in lus and "charte_onu" not in lus and "constitution_1958" not in lus
    lus.clear()
    assert mise_a_jour.ajouter_nouvelles(passages, actives, importer) == ([], ["tfue"])   # seul l'echec est retente
    assert lus == ["tfue"]
