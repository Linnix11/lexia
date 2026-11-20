"""Vitesse de la recherche locale, sans aucun appel a un modele en ligne (audit du 19/11, SRV-7 ; D114).

    python eval/vitesse_recherche.py mesure --sortie avant.json            # 20 questions, 3 passages chacune
    python eval/vitesse_recherche.py mesure --sortie avant.json --jeux eval/cas.yaml eval/cas_pratiques_controle.yaml --tous
    python eval/vitesse_recherche.py comparer avant.json apres.json

Le pipeline reel de la recherche (`Lexia.rechercher` : lexique, references, plein texte, vecteurs, fusion,
reclassement, articles de principe) tourne sur l'index de `data/index`, avec trois remplacants deterministes :
  - embedding : vecteur moyen des 3 premiers passages trouves en plein texte pour ce texte, lus dans l'index
    (le modele multilingual-e5-base n'est pas sur le Mac) ; le parcours de l'index est le meme qu'avec un vrai vecteur ;
  - reformulation : « notion juridique : » + la question (pas d'appel a Gemini) ;
  - reclassement : ordre par longueur du texte (pas de modele CamemBERT), pour parcourir le meme chemin.
Les durees par etape viennent de chronometres poses sur les methodes du moteur (memes points avant et apres la
modification). Les identifiants des passages trouves sont enregistres : `comparer` dit si deux runs ont trouve
exactement les memes passages, dans le meme ordre.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

# Comme sur le VPS (2 processeurs) : 2 fils de calcul pour numpy. A fixer avant d'importer numpy.
for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_var, "2")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402

from api.rag import K_CHAT, Lexia  # noqa: E402
from api.retrieval.base import Complement, Hit, groupes  # noqa: E402
from api.retrieval.local import LocalRetriever  # noqa: E402
from eval.cas import ROOT, charger  # noqa: E402

INDEX = ROOT / "data" / "index"
JEU_DEFAUT = ROOT / "eval" / "cas.yaml"
# Methodes chronometrees, par etape. Une methode appelee depuis une autre deja chronometree n'est pas recomptee.
ETAPES = {
    "_lexical": "lexicale",
    "_par_reference": "references",
    "_scores": "vectorielle",
    "_vectoriel": "vectorielle",
    "_par_ids": "vectorielle",
    "_principes_proches": "vectorielle",
}


class Chronos:
    def __init__(self):
        self.durees: dict[str, float] = {}
        self._profondeur = 0

    def poser(self, objet, nom: str, etape: str) -> None:
        if not hasattr(objet, nom):
            return
        methode = getattr(objet, nom)

        def chronometree(*a, **kw):
            self._profondeur += 1
            debut = time.perf_counter()
            try:
                return methode(*a, **kw)
            finally:
                self._profondeur -= 1
                if self._profondeur == 0:
                    self.durees[etape] = self.durees.get(etape, 0.0) + (time.perf_counter() - debut) * 1000
        setattr(objet, nom, chronometree)


class EmbeddingFactice:
    """Vecteur moyen des 3 premiers passages trouves en plein texte pour ce texte (textes officiels)."""

    def __init__(self, r: LocalRetriever):
        self._r = r
        self._rang = {pid: i for i, pid in enumerate(r._ids)}
        self._textes = groupes(None, r._toutes_sources())[0]

    def embed_query(self, texte: str) -> list[float]:
        classements = LocalRetriever._lexical(self._r, texte, self._textes)
        lignes = [self._rang[pid] for pid, _ in (classements[0] if classements else []) if pid in self._rang][:3]
        if not lignes:
            v = np.random.default_rng(len(texte)).standard_normal(self._r._vecs.shape[1]).astype(np.float32)
        else:
            v = np.asarray(self._r._vecs[lignes], dtype=np.float32).mean(axis=0)
        return (v / (np.linalg.norm(v) or 1.0)).tolist()


class ReformulationFactice:
    def etendre(self, texte: str) -> Complement:
        return Complement(reformulation="notion juridique : " + texte)


class ReclasseurFactice:
    model = "factice"

    def reordonner(self, question: str, hits: list[Hit]) -> list[Hit]:
        cle = sorted(hits, key=lambda h: (-len(h.passage.get("texte", "")), h.passage["id"]))
        return [Hit(h.passage, 1.0 / (1 + i), h.via | {"reclasse"}) for i, h in enumerate(cle)]


def questions(jeux: list[Path], n: int | None) -> list:
    cas = [c for j in jeux for c in charger(j)]
    if n is None or n >= len(cas):
        return cas
    pas = len(cas) / n  # reparties sur tout le jeu (matieres et pieges)
    return [cas[int(i * pas)] for i in range(n)]


def mesurer(args) -> int:
    debut = time.monotonic()
    r = LocalRetriever(args.index)
    print(f"index charge en {time.monotonic() - debut:.1f} s : {len(r._ids)} vecteurs", flush=True)
    emb = EmbeddingFactice(r)
    chronos = Chronos()
    for nom, etape in ETAPES.items():
        chronos.poser(r, nom, etape)
    chronos.poser(emb, "embed_query", "embedding_factice")  # remplacant, a retirer du total pour comparer
    lexia = Lexia(r, llm=None, embedder=emb, expanseur=ReformulationFactice(), reclasseur=ReclasseurFactice())
    cas = questions(args.jeux, None if args.tous else args.questions)
    repetitions = 1 if args.tous else args.repetitions
    # Premier passage non compte : charge en memoire les pages de l'index lues par ces questions.
    if not args.tous:
        for c in cas:
            lexia.rechercher(c.question, c.matiere, K_CHAT)
    resultats: dict[str, dict] = {}
    for i, c in enumerate(cas, 1):
        essais = []
        for _ in range(repetitions):
            chronos.durees = {}
            t = time.perf_counter()
            passages, _ = lexia.rechercher(c.question, c.matiere, K_CHAT)
            total = (time.perf_counter() - t) * 1000
            essais.append({"total": total, **chronos.durees})
        etapes = sorted({k for e in essais for k in e})
        resultats[c.id] = {
            "question": c.question,
            "ids": [p["id"] for p in passages],
            "ms": {k: round(statistics.median(e.get(k, 0.0) for e in essais), 1) for k in etapes},
        }
        print(f"\r{i}/{len(cas)}", end="", flush=True)
    print()
    args.sortie.write_text(json.dumps({"index": str(args.index), "repetitions": repetitions,
                                       "cas": resultats}, ensure_ascii=False, indent=1))
    resumer(resultats)
    return 0


def resumer(resultats: dict) -> None:
    etapes = sorted({k for v in resultats.values() for k in v["ms"]})
    for k in etapes:
        xs = sorted(v["ms"].get(k, 0.0) for v in resultats.values())
        p90 = xs[min(len(xs) - 1, int(0.9 * len(xs)))]
        print(f"{k:12s} mediane {statistics.median(xs):7.1f} ms  90e centile {p90:7.1f} ms  max {xs[-1]:7.1f} ms")


def comparer(args) -> int:
    a, b = (json.loads(Path(f).read_text())["cas"] for f in (args.avant, args.apres))
    communs = [c for c in a if c in b]
    differents = [c for c in communs if a[c]["ids"] != b[c]["ids"]]
    print(f"{len(communs)} cas communs : {len(communs) - len(differents)} identiques, {len(differents)} differents")
    for c in differents:
        print(f"  {c} : {a[c]['question'][:70]}\n    avant {a[c]['ids']}\n    apres {b[c]['ids']}")
    for nom, res in (("avant", a), ("apres", b)):
        print(f"--- {nom}")
        resumer({c: res[c] for c in communs})
    return 1 if differents else 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = p.add_subparsers(dest="commande", required=True)
    m = sp.add_parser("mesure")
    m.add_argument("--sortie", type=Path, required=True)
    m.add_argument("--index", type=Path, default=INDEX)
    m.add_argument("--jeux", type=Path, nargs="+", default=[JEU_DEFAUT])
    m.add_argument("--questions", type=int, default=20)
    m.add_argument("--repetitions", type=int, default=3)
    m.add_argument("--tous", action="store_true", help="tous les cas des jeux, un passage chacun (comparaison)")
    c = sp.add_parser("comparer")
    c.add_argument("avant", type=Path)
    c.add_argument("apres", type=Path)
    args = p.parse_args()
    return mesurer(args) if args.commande == "mesure" else comparer(args)


if __name__ == "__main__":
    sys.exit(main())
