"""Recherche plus rapide (audit du 19/11, SRV-7 ; D114) : memes resultats qu'avant, un parcours de l'index par
vecteur et par question, selection sans tri complet, deux reclassements a la fois, durees dans le journal."""

import json
import threading
import time
from pathlib import Path

import numpy as np
import pytest

from api.journal import Journal
from api.rag import Lexia
from api.retrieval import local
from api.retrieval.base import Complement, Hit
from api.retrieval.local import LocalRetriever, meilleurs
from ingest.build_index import build
from ingest.embed import encode
from ingest.sources import cass, constit, legi

FIX = Path(__file__).parent / "fixtures"
CONSTITUTION = Path(__file__).parent.parent / "data" / "passages" / "constitution_1958.jsonl"
DIM = 8


def ancien_vectoriel(self, vecteur, sources, sims=None):
    """`LocalRetriever._vectoriel` avant D114, recopie telle quelle : calcul et tri complet a chaque appel."""
    if not len(self._ids) or vecteur is None:
        return []
    q = np.asarray(vecteur, dtype=np.float32)
    if self._vecs.shape[1] != q.shape[0]:
        return []
    q /= np.linalg.norm(q) or 1.0
    sims = self._vecs @ q
    autorisees = set(sources) if sources else None
    out = []
    for i in np.argsort(-sims):
        pid = self._ids[int(i)]
        src, vig = self._meta_vec.get(pid, ("", None))
        if (autorisees is None or src in autorisees) and vig != 0:
            out.append(pid)
            if len(out) >= local.N_CANDIDATS:
                break
    return out


class AncienRetriever(LocalRetriever):
    _vectoriel = ancien_vectoriel


class ReclasseurFactice:
    model = "factice"

    def reordonner(self, question, hits):
        cle = sorted(hits, key=lambda h: (-len(h.passage.get("texte", "")), h.passage["id"]))
        return [Hit(h.passage, 1.0 / (1 + i), h.via | {"reclasse"}) for i, h in enumerate(cle)]


@pytest.fixture(scope="module")
def petit_index(tmp_path_factory):
    """Fixtures de test et Constitution, un vecteur aleatoire (sans egalite) par passage."""
    base = tmp_path_factory.mktemp("lexia_rapide")
    passages = base / "passages"
    passages.mkdir()
    rows = [p.to_dict() for p in constit.parse_decision((FIX / "constit_2023-1075_QPC.xml").read_bytes(),
                                                         date_recuperation="d", version="v")]
    rows += [p.to_dict() for p in cass.parse_arret((FIX / "cass_moderne.xml").read_bytes(),
                                                   date_recuperation="d", version="v")]
    for f in ("LEGIARTI000032041571.xml", "LEGIARTI000006438819.xml"):
        rows.append(legi.parse_article((FIX / f).read_bytes(), date_recuperation="d", version_archive="a").to_dict())
    (passages / "fixtures.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows))
    (passages / "constitution_1958.jsonl").write_text(CONSTITUTION.read_text(encoding="utf-8"))
    rng = np.random.default_rng(112)
    cache = base / "cache"
    cache.mkdir()
    lignes = []
    for f in passages.glob("*.jsonl"):
        for ligne in f.read_text(encoding="utf-8").splitlines():
            p = json.loads(ligne)
            lignes.append(json.dumps({"id": p["id"], "empreinte": p["empreinte"], "model": "fake-embed", "dim": DIM,
                                      "b64": encode(rng.standard_normal(DIM).tolist())}))
    (cache / "tout.jsonl").write_text("\n".join(lignes))
    build(passages_dir=passages, index_dir=base / "index", cache_dir=cache, model="fake-embed")
    return base / "index"


# --- selection sans tri complet ------------------------------------------------

@pytest.mark.parametrize("egalites", [False, True])
def test_meilleurs_egale_le_tri_complet_filtre(egalites):
    rng = np.random.default_rng(0)
    sims = (rng.permutation(20000) / 20000 - 0.5).astype(np.float32)  # 20 000 scores tous differents
    if egalites:  # nombreux scores egaux, y compris au rang n : ordre de l'index entre eux
        sims = np.round(sims, 2)
    for densite in (0.0, 0.0005, 0.01, 0.5, 1.0):
        masque = rng.random(sims.shape[0]) < densite
        for n in (1, 50, 500, 30000):
            attendu = [i for i in np.argsort(-sims, kind="stable") if masque[i]][:n]
            assert meilleurs(sims, masque, n).tolist() == attendu, (densite, n)
            if not egalites:  # sans egalite, le tri d'avant (non stable) donne le meme ordre
                assert attendu == [i for i in np.argsort(-sims) if masque[i]][:n]


# --- memes resultats qu'avant sur un petit index ---------------------------------

def test_memes_resultats_que_l_ancien_classement(petit_index):
    nouveau, ancien = LocalRetriever(petit_index, "fake-embed"), AncienRetriever(petit_index, "fake-embed")
    assert len(nouveau._ids) > 100
    rng = np.random.default_rng(7)
    questions = ["dommage causé à autrui et responsabilité", "Que dit l'article 1240 du code civil ?",
                 "droit de propriété et liberté d'entreprendre", "pourvoi en cassation", "élection du Président"]
    toutes = nouveau._toutes_sources()
    jeux = [None, ("constitution_1958",), ("code_civil", "constitution_1958"), toutes]
    for question in questions:
        for sources in jeux:
            for reclasseur in (None, ReclasseurFactice()):
                v, vr = rng.standard_normal(DIM).tolist(), rng.standard_normal(DIM).tolist()
                complement = Complement(reformulation="notion juridique : " + question, vecteur_reformulation=vr)
                for comp in (None, complement):
                    a = ancien.search(question, sources=sources, k=8, query_vector=v, complement=comp,
                                      reclasseur=reclasseur)
                    n = nouveau.search(question, sources=sources, k=8, query_vector=v, complement=comp,
                                       reclasseur=reclasseur)
                    assert [(h.passage["id"], h.score, h.via) for h in n] == \
                        [(h.passage["id"], h.score, h.via) for h in a], (question, sources, reclasseur, comp)
                    assert any("vecteur" in h.via for h in n) or sources == ("constitution_1958",)
                    for src in (sources, ("code_civil",), None):  # candidats vectoriels eux-memes
                        assert nouveau._vectoriel(v, src) == ancien_vectoriel(ancien, v, src)


def test_un_parcours_de_l_index_par_vecteur_et_par_question(petit_index, monkeypatch):
    r = LocalRetriever(petit_index, "fake-embed")
    appels = []
    calcul = r._scores
    monkeypatch.setattr(r, "_scores", lambda v: appels.append(1) or calcul(v))
    complement = Complement(reformulation="notion juridique", vecteur_reformulation=[1.0] * DIM)
    r.search("responsabilité et dommage", sources=None, k=8, query_vector=[0.5] * DIM, complement=complement)
    assert len(appels) == 2  # question et reformulation, pour les deux groupes (textes, jurisprudence) : 4 avant


def test_masque_ecarte_les_versions_finies_et_les_autres_sources(petit_index):
    r = LocalRetriever(petit_index, "fake-embed")
    m = r._masque(("code_civil",))
    garde = {r._ids[i] for i in np.flatnonzero(m)}
    assert garde == {pid for pid, (src, vig) in r._meta_vec.items() if src == "code_civil" and vig != 0}
    assert r._masque(("code_civil",)) is m  # garde en memoire
    # aucune source precisee : tout ce qui n'est pas une version finie
    assert int(r._masque(None).sum()) == sum(1 for _, vig in r._meta_vec.values() if vig != 0)


# --- deux reclassements a la fois -----------------------------------------------

def test_deux_reclassements_a_la_fois_au_plus():
    from api import rerank

    en_cours, maximum, verrou = [0], [0], threading.Lock()

    class CrossEncoderLent:
        def predict(self, paires, show_progress_bar=False):
            with verrou:
                en_cours[0] += 1
                maximum[0] = max(maximum[0], en_cours[0])
            time.sleep(0.05)
            with verrou:
                en_cours[0] -= 1
            return [0.0] * len(paires)

    r = object.__new__(rerank.CrossEncoderReclasseur)
    r.model, r._ce = "lent", CrossEncoderLent()
    hits = [Hit({"id": "a", "texte": "x", "source_id": "code_civil"}, 1.0, set())]
    fils = [threading.Thread(target=r.reordonner, args=("q", hits)) for _ in range(6)]
    for f in fils:
        f.start()
    for f in fils:
        f.join()
    assert maximum[0] == rerank.RECLASSEMENTS_SIMULTANES == 2


# --- durees dans le journal -----------------------------------------------------

class EmbedderFactice:
    model, dim = "fake-embed", DIM

    def embed_query(self, texte):
        return np.random.default_rng(len(texte)).standard_normal(DIM).tolist()


class ReformulationLente:
    def etendre(self, texte):
        time.sleep(0.03)
        return Complement(reformulation="responsabilité civile délictuelle")


class LLMLent:
    def generate_json(self, *, system, prompt, schema, temperature=0.2):
        time.sleep(0.02)
        return {"statut": "abstention"}, "fake-model"


def test_durees_par_etape_dans_le_journal(petit_index, tmp_path):
    lexia = Lexia(LocalRetriever(petit_index, "fake-embed"), LLMLent(), Journal(tmp_path), EmbedderFactice(),
                  ReformulationLente(), ReclasseurFactice())
    lexia.chat("Quelles sont les conditions de la responsabilité pour faute ?", "expliquer", None)
    ligne = json.loads((tmp_path / "requetes.jsonl").read_text().splitlines()[-1])
    etapes = ligne["recherche_detail"]["etapes_ms"]
    assert {"reformulation", "vectorisation", "references", "lexicale", "vectorielle", "reclassement"} <= set(etapes)
    assert etapes["reformulation"] >= 30 and all(isinstance(ms, int) for ms in etapes.values())
    assert ligne["generation_ms"] >= 20
