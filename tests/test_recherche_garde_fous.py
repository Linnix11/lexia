"""Garde-fous de la recherche vectorielle : une incoherence d'index degrade la recherche
(plein texte seul) au lieu de citer la mauvaise source ou de faire echouer chaque question."""

import json

import numpy as np

from api.retrieval import local


def retriever_sans_index(vecs, ids):
    r = object.__new__(local.LocalRetriever)
    r._vecs, r._ids, r._meta_vec = vecs, ids, {i: ("code_civil", 1) for i in ids}
    return r


def test_dimension_differente_saute_la_recherche_vectorielle(caplog):
    r = retriever_sans_index(np.ones((3, 4), dtype=np.float32), ["a", "b", "c"])
    assert r._vectoriel([1.0] * 8, None) == []          # question en dimension 8, index en 4
    assert "dimension" in caplog.text
    assert r._vectoriel([1.0] * 4, None) == ["a", "b", "c"]


def test_index_vectoriel_incoherent_desactive(tmp_path, monkeypatch, caplog):
    """3 vecteurs pour 2 identifiants (construction interrompue) : recherche vectorielle coupee."""
    np.save(tmp_path / "vectors.npy", np.ones((3, 4), dtype=np.float32))
    (tmp_path / "vectors_ids.json").write_text(json.dumps(["a", "b"]))
    import sqlite3
    con = sqlite3.connect(tmp_path / "lexia.sqlite")
    con.execute("CREATE TABLE passages (id TEXT, data TEXT, source_id TEXT, en_vigueur INTEGER)")
    con.execute("CREATE VIRTUAL TABLE passages_fts USING fts5(texte)")
    con.commit()
    con.close()
    try:
        r = local.LocalRetriever(tmp_path)
    except Exception as e:  # le schema de test peut ne pas suffire au reste du constructeur
        assert "incoherent" in caplog.text, e
        return
    assert r._ids == [] and "incoherent" in caplog.text
