"""Extraction des codes depuis l'archive LEGI : un code ajoute apres la premiere extraction est extrait, puis
mis a jour des archives quotidiennes deja lues pour les autres textes."""

import io
import tarfile

from ingest.sources import codes

CHEMIN = "legi/global/code_et_TNC_en_vigueur/code_en_vigueur/LEGI/TEXT/00/00/{lt}/article/LEGI/ART/{a}.xml"


def archive(chemin, fichiers: dict[str, bytes]):
    with tarfile.open(chemin, "w:gz") as tar:
        for nom, donnees in fichiers.items():
            info = tarfile.TarInfo(nom)
            info.size = len(donnees)
            tar.addfile(info, io.BytesIO(donnees))


def test_code_ajoute_apres_l_extraction_est_extrait_puis_mis_a_jour(tmp_path, monkeypatch):
    c1, c2, c9 = "LEGITEXT000000000001", "LEGITEXT000000000002", "LEGITEXT000000000009"
    archive(tmp_path / "Freemium_legi_global_20261108-140000.tar.gz",
            {CHEMIN.format(lt=c1, a="LEGIARTI1"): b"<v0/>", CHEMIN.format(lt=c2, a="LEGIARTI2"): b"<v0/>",
             CHEMIN.format(lt=c9, a="LEGIARTI9"): b"<v0/>"})
    # Archive quotidienne du 10 novembre, deja lue lors d'une extraction anterieure (journal) : elle modifie
    # un article du code ajoute et un article du code deja extrait.
    archive(tmp_path / "LEGI_20261110-210000.tar.gz",
            {"20261110-210000/" + CHEMIN.format(lt=c2, a="LEGIARTI2"): b"<v1/>",
             "20261110-210000/" + CHEMIN.format(lt=c1, a="LEGIARTI1"): b"<v1/>"})
    dest = tmp_path / "extrait_legi_20261108"
    (dest / c1).mkdir(parents=True)                       # extraction anterieure : seul le premier code
    (dest / ".increments").write_text("20261110-210000\n")
    monkeypatch.setattr(codes, "CODES", (codes.Code("c1", c1, "Code un"), codes.Code("c2", c2, "Code deux")))
    monkeypatch.setattr(codes, "_voulus", lambda *a: {c1, c2})
    monkeypatch.setattr(codes, "_inventaire", lambda *a: {"lois": []})

    assert codes.extraire(tmp_path) == dest
    art2 = list((dest / c2).rglob("LEGIARTI2.xml"))
    assert len(art2) == 1 and art2[0].read_bytes() == b"<v1/>"       # code ajoute : extrait et a jour
    assert not (dest / c9).exists()                                  # texte non voulu : ignore
    assert not list((dest / c1).rglob("*.xml"))                      # code deja la : ni reextrait ni retouche
    assert (dest / ".increments").read_text() == "20261110-210000\n"  # journal inchange par le rattrapage
    assert not (tmp_path / "extrait_legi_20261108.ajout").exists()
    assert codes.extraire(tmp_path) == dest                          # seconde passe : rien a extraire
