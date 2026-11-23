"""Reglages du reclassement : duree et qualite de la recherche (recette du 23/11, R-3).

    python eval/reclassement.py                         # tous les reglages, rapport dans eval/resultats/
    python eval/reclassement.py --reglages base,n8      # quelques reglages

Pipeline reel de `Lexia.rechercher` sur l'index de `data/index`, avec les modeles d'embedding et de reclassement de
la configuration, sans reformulation (Gemini indisponible : le cas le plus defavorable, comme backtest_recherche.py).
Reclassement sur le processeur (pas le GPU du Mac), limite a 2 fils comme le VPS (2 processeurs) ; les durees du Mac restent plus courtes que celles du VPS
(4 a 7 s par question en production) : seul le rapport entre reglages compte.

Pour chaque reglage : source attendue parmi les 8 extraits et parmi les 4 du secours, duree du reclassement (moyenne,
90e centile), et extraits identiques au reglage de base (memes 8 passages, dans n'importe quel ordre).
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_var, "2")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch  # noqa: E402

from api import rerank  # noqa: E402
from api.config import get_settings  # noqa: E402
from api.main import _construire_embedder, _construire_retriever  # noqa: E402
from api.rag import K_CHAT, Lexia, pour_secours  # noqa: E402
from api.retrieval import base  # noqa: E402
from eval.cas import ROOT, charger  # noqa: E402

JEUX = ("cas.yaml", "cas_pratiques.yaml", "cas_pratiques_controle.yaml", "cas_pratiques_controle2.yaml")

# nom -> (candidats par groupe, jetons, caracteres, quantification int8)
REGLAGES = {
    "base": (10, 256, 800, False),
    "jetons192": (10, 192, 600, False),
    "jetons128": (10, 128, 400, False),
    "n8": (8, 256, 800, False),
    "n6": (6, 256, 800, False),
    "int8": (10, 256, 800, True),
}


def reclasseur(modele: str, jetons: int, int8: bool) -> rerank.CrossEncoderReclasseur:
    r = rerank.CrossEncoderReclasseur(modele, max_length=jetons, device="cpu")  # comme le VPS, pas le GPU du Mac
    if int8:
        # moteur de quantification de la machine : qnnpack sur un Mac (ARM), fbgemm/x86 sur le VPS. La vitesse de
        # l'int8 mesuree sur le Mac ne dit donc rien de celle du VPS ; seule la qualite se compare.
        moteurs = torch.backends.quantized.supported_engines
        torch.backends.quantized.engine = "x86" if "x86" in moteurs else "fbgemm" if "fbgemm" in moteurs else "qnnpack"
        r._ce.model = torch.ao.quantization.quantize_dynamic(r._ce.model, {torch.nn.Linear}, dtype=torch.qint8)
    return r


def mesurer(nom: str, lexia: Lexia, cas: list) -> dict:
    n, jetons, caracteres, int8 = REGLAGES[nom]
    base.N_RECLASSEMENT = n
    rerank.MAX_CHARS = caracteres
    lexia.reclasseur = reclasseur(lexia.reclasseur.model, jetons, int8)
    lexia.rechercher("Quelles sont les conditions de la responsabilité civile ?", None, K_CHAT)  # premier appel
    ok8 = ok4 = 0
    durees, extraits = [], {}
    for c in cas:
        passages, infos = lexia.rechercher(c.question, c.matiere, K_CHAT)
        durees.append(infos["etapes_ms"].get("reclassement", 0))
        ok8 += c.trouve(passages)
        ok4 += c.trouve(pour_secours(passages))
        extraits[c.id] = {p["id"] for p in passages}
    durees.sort()
    return {"nom": nom, "ok8": ok8, "ok4": ok4, "moyenne": statistics.mean(durees),
            "p90": durees[int(0.9 * (len(durees) - 1))], "extraits": extraits}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reglages", default=",".join(REGLAGES))
    args = ap.parse_args()
    torch.set_num_threads(2)
    s = get_settings()
    if not s.rerank_model:
        print("RERANK_MODEL absent de la configuration : rien a mesurer")
        return 1
    lexia = Lexia(_construire_retriever(s), None, None, _construire_embedder(s), None,
                  rerank.CrossEncoderReclasseur(s.rerank_model, device="cpu"))
    cas = [c for f in JEUX for c in charger(ROOT / "eval" / f) if c.sources]
    print(f"{len(cas)} cas")
    resultats = []
    for nom in args.reglages.split(","):
        t = time.monotonic()
        try:
            resultats.append(mesurer(nom, lexia, cas))
        except Exception as e:  # noqa: BLE001 - un reglage en echec (int8 selon la machine) n'arrete pas les autres
            print(f"{nom} : echec ({type(e).__name__}: {e})")
            continue
        r = resultats[-1]
        print(f"{nom} : {r['ok8']}/{len(cas)} dans les 8, {r['ok4']}/{len(cas)} dans les 4, reclassement "
              f"{r['moyenne']:.0f} ms en moyenne, {r['p90']:.0f} ms au 90e centile ({time.monotonic() - t:.0f} s)")
    ref = next((r for r in resultats if r["nom"] == "base"), resultats[0])
    lignes = [f"# Reglages du reclassement - {datetime.now():%Y-%m-%d %H:%M}", "",
              f"{len(cas)} cas qui attendent une source ({', '.join(JEUX)}). Sans reformulation ; 2 fils de calcul ; "
              "Mac (durees plus courtes que sur le VPS, seul le rapport compte).", "",
              "| Reglage | Candidats / jetons / caracteres / int8 | Dans les 8 | Dans les 4 | Reclassement moyen (ms) "
              "| 90e centile (ms) | Memes 8 extraits que la base |", "|---|---|---|---|---|---|---|"]
    for r in resultats:
        n, j, c, q = REGLAGES[r["nom"]]
        memes = sum(r["extraits"][k] == ref["extraits"][k] for k in ref["extraits"])
        lignes.append(f"| {r['nom']} | {n} / {j} / {c} / {'oui' if q else 'non'} | {r['ok8']}/{len(cas)} | "
                      f"{r['ok4']}/{len(cas)} | {r['moyenne']:.0f} | {r['p90']:.0f} | {memes}/{len(cas)} |")
    sortie = ROOT / "eval" / "resultats" / f"reclassement-{datetime.now():%Y%m%d-%H%M}.md"
    sortie.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print(f"-> {sortie}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
