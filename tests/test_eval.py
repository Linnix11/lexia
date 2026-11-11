"""Le jeu d'evaluation est bien forme et ses sources se resolvent dans les fixtures."""

from eval.cas import charger, correspond


def test_jeu_bien_forme():
    cas = charger()
    assert len(cas) == 150
    assert sum(1 for c in cas if c.piege) == 30
    for c in cas:
        assert c.attendu and c.question.strip()
        if not c.piege:
            assert c.sources, f"{c.id} sans source attendue"
        for ref in c.sources:
            assert ref.split(":")[0] in ("code_civil", "constitution", "cc"), ref


def test_correspondance_des_sources():
    article = {"source_id": "code_civil", "numero": "1240", "meta": {}}
    decision = {"source_id": "decisions_conseil_constitutionnel", "numero": "1-2",
                "meta": {"numero": "71-44", "nature": "DC"}}
    assert correspond("code_civil:1240", article)
    assert not correspond("code_civil:1241", article)
    assert not correspond("constitution:1240", article)
    assert correspond("cc:71-44 DC", decision)
    assert not correspond("cc:71-44 QPC", decision)
