"""Amorce au demarrage (recette du 23/11, R-2) : la premiere question apres une publication payait 17 s de recherche
vectorielle (vecteurs en memoire mappee, lus du disque au premier parcours) et 7 s de reclassement."""

import threading

from fastapi.testclient import TestClient

from api.config import Settings
from api.main import create_app
from api.rag import Lexia
from api.retrieval.local import LocalRetriever
from api.serveur import demarrer_amorce
from tests.test_api import FakeEmbedder, FakeLLM, index_dir, index_vectorise  # noqa: F401  (fixtures partagees)


class Reclasseur:
    def __init__(self):
        self.appels = 0

    def reordonner(self, question, hits):
        self.appels += 1
        return hits


def test_amorce_parcourt_vecteurs_plein_texte_et_reclassement(index_vectorise):
    emb, rec = FakeEmbedder(), Reclasseur()
    lexia = Lexia(LocalRetriever(index_vectorise, embed_model="fake-embed"), llm=None, embedder=emb, reclasseur=rec)
    assert lexia.amorce is None
    etat = lexia.amorcer()
    assert etat["etat"] == "terminee" and lexia.amorce == etat
    assert emb.appels == 1 and rec.appels >= 1
    assert {"vectorisation", "lexicale", "vectorielle", "reclassement"} <= set(etat["etapes_ms"])


def test_amorce_en_echec_ne_leve_pas(index_dir):
    class Casse(LocalRetriever):
        def search(self, *a, **k):
            raise RuntimeError("index illisible")

    lexia = Lexia(Casse(index_dir), llm=None)
    assert lexia.amorcer()["etat"] == "echec"


def test_amorce_dans_le_detail_local_de_sante_et_fil_au_demarrage(index_dir, tmp_path):
    settings = Settings(gemini_models=("fake",), index_dir=index_dir, logs_dir=tmp_path / "logs")
    app = create_app(settings, retriever=LocalRetriever(index_dir), llm=FakeLLM())
    local = TestClient(app, client=("127.0.0.1", 50000))
    assert local.get("/sante").json()["amorce"] is None
    fil = demarrer_amorce(app)
    assert isinstance(fil, threading.Thread) and fil.daemon
    fil.join(30)
    assert local.get("/sante").json()["amorce"]["etat"] == "terminee"
    assert "amorce" not in TestClient(app).get("/sante").json()  # en public : rien de plus
