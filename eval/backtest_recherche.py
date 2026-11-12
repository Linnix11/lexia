"""Backtest de la recherche sur le jeu d'evaluation (eval/cas.yaml), sans appel au modele de reponse.

Pour chaque cas qui attend une source : la source attendue est-elle parmi les extraits envoyes au modele ?
  - « 8 extraits »  : ce que recoit Gemini ;
  - « 4 pour Groq » : ce que recoit Groq quand il prend le relais (2 textes + 2 decisions, api.rag.pour_secours).
Reglage de production : embeddings + reclassement + lexique local, sans reformulation par Gemini
(le cas le plus defavorable, et celui qui se produit quand Gemini est sature).

    python eval/backtest_recherche.py                 # rapport dans eval/resultats/backtest-recherche-<date>.md
"""

from __future__ import annotations

import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.config import get_settings  # noqa: E402
from api.main import _construire_embedder, _construire_reclasseur, _construire_retriever  # noqa: E402
from api.rag import K_CHAT, Lexia, pour_secours  # noqa: E402
from eval.cas import ROOT, charger, correspond  # noqa: E402


def main() -> int:
    s = get_settings()
    lexia = Lexia(_construire_retriever(s), None, None, _construire_embedder(s), None, _construire_reclasseur(s))
    cas = [c for c in charger() if c.sources]
    groupes: dict[str, list] = defaultdict(list)
    echecs: list[str] = []
    durees: list[float] = []
    for i, c in enumerate(cas, 1):
        t = time.monotonic()
        passages, _ = lexia.rechercher(c.question, c.matiere, K_CHAT)
        durees.append(time.monotonic() - t)
        dans = lambda ps: any(correspond(ref, p) for ref in c.sources for p in ps)  # noqa: E731
        ok8, ok4 = dans(passages), dans(pour_secours(passages))
        groupe = c.piege and f"piège : {c.piege}" or (c.matiere or "toutes matières")
        groupes[groupe].append((ok8, ok4))
        if not ok8 or not ok4:
            fournis = ", ".join(f"{p['source_id'].replace('code_', '')}:{p.get('numero') or 'déc.'}" for p in passages[:6])
            echecs.append(f"| {c.id} | {c.question} | {', '.join(c.sources)} | {'oui' if ok8 else '**non**'} | "
                          f"{'oui' if ok4 else '**non**'} | {fournis} |")
        print(f"\r{i}/{len(cas)}", end="", flush=True)
    print()

    tot8 = sum(o8 for v in groupes.values() for o8, _ in v)
    tot4 = sum(o4 for v in groupes.values() for _, o4 in v)
    n = len(cas)
    lignes = [
        f"# Backtest de la recherche - {datetime.now():%Y-%m-%d %H:%M}", "",
        f"{len(charger())} cas au total, dont {n} attendent une source. Sans reformulation par Gemini ; "
        f"embeddings, reclassement et lexique actifs. Temps moyen de recherche : {sum(durees) / n:.1f} s.", "",
        "| Groupe | Cas | Source parmi les 8 extraits (Gemini) | Source parmi les 4 premiers (Groq) |",
        "|---|---|---|---|",
    ]
    for g in sorted(groupes):
        v = groupes[g]
        lignes.append(f"| {g} | {len(v)} | {sum(a for a, _ in v)}/{len(v)} ({100 * sum(a for a, _ in v) / len(v):.0f} %) | "
                      f"{sum(b for _, b in v)}/{len(v)} ({100 * sum(b for _, b in v) / len(v):.0f} %) |")
    lignes.append(f"| **Total** | {n} | **{tot8}/{n} ({100 * tot8 / n:.0f} %)** | **{tot4}/{n} ({100 * tot4 / n:.0f} %)** |")
    lignes += ["", "## Cas à examiner", "",
               "| Cas | Question | Source attendue | Dans les 8 | Dans les 4 | Premiers extraits fournis |",
               "|---|---|---|---|---|---|", *echecs]
    sortie = ROOT / "eval" / "resultats" / f"backtest-recherche-{datetime.now():%Y%m%d-%H%M}.md"
    sortie.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes[:6 + len(groupes) + 2]))
    print(f"\n{len(echecs)} cas à examiner -> {sortie}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
