"""Non-regression des grands arrets par notion (D124) sur les jeux d'evaluation, sans appel au modele de reponse.

Pour chaque cas, la recherche de production (embeddings, reclassement, lexique, sans reformulation par Gemini) est
faite deux fois : sans les grands arrets (recherche d'avant D124) et avec. Verifie que les extraits d'avant sont
identiques et en tete, que le secours recoit les memes extraits (plus un grand arret au plus) et que la source
attendue est toujours trouvee dans les 8 et dans les 4 ; compte les cas qui recoivent des grands arrets.

    python eval/grands_arrets_regression.py            # rapport dans eval/resultats/grands-arrets-regression-<date>.md
"""

from __future__ import annotations

import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.config import get_settings  # noqa: E402
from api.main import _construire_embedder, _construire_reclasseur, _construire_retriever  # noqa: E402
from api.rag import K_CHAT, Lexia, pour_secours  # noqa: E402
from eval.cas import ROOT, charger  # noqa: E402

NOUVEAU = "cas_grands_arrets_notions.yaml"


def main() -> int:
    s = get_settings()
    retriever, embedder, reclasseur = _construire_retriever(s), _construire_embedder(s), _construire_reclasseur(s)
    avant_d124 = Lexia(retriever, None, None, embedder, None, reclasseur, avec_grands_arrets=False)
    d124 = Lexia(retriever, None, None, embedder, None, reclasseur)
    fichiers = [f for f in sorted((ROOT / "eval").glob("*.yaml")) if f.name != NOUVEAU]
    cas = [(f.name, c) for f in fichiers for c in charger(f)]
    ecarts, touches, par_fichier = [], [], Counter()
    sources = {"8 avant": 0, "8 apres": 0, "4 avant": 0, "4 apres": 0, "attendues": 0}
    for i, (nom, c) in enumerate(cas, 1):
        avant, _ = avant_d124.rechercher(c.question, c.matiere, K_CHAT)
        apres, infos = d124.rechercher(c.question, c.matiere, K_CHAT)
        ids_avant = [p["id"] for p in avant]
        if [p["id"] for p in apres[:len(avant)]] != ids_avant:
            ecarts.append(f"| {c.id} | extraits d'avant changes |")
        s_avant, s_apres = [p["id"] for p in pour_secours(avant)], [p["id"] for p in pour_secours(apres)]
        if s_apres[:len(s_avant)] != s_avant or len(s_apres) > len(s_avant) + 1:
            ecarts.append(f"| {c.id} | extraits du secours changes |")
        if c.sources:
            sources["attendues"] += 1
            r = (c.trouve(avant), c.trouve(apres), c.trouve(pour_secours(avant)), c.trouve(pour_secours(apres)))
            sources["8 avant"] += r[0]; sources["8 apres"] += r[1]; sources["4 avant"] += r[2]; sources["4 apres"] += r[3]  # noqa: E702
            if r[1] < r[0] or r[3] < r[2]:
                ecarts.append(f"| {c.id} | source attendue perdue |")
        marques = [p["grand_arret"]["id"] for p in apres if p.get("grand_arret")]
        if marques:
            touches.append(f"| {c.id} | {c.question[:90]} | {infos['grands_arrets']} | {', '.join(marques)} |")
            par_fichier[nom] += 1
        print(f"\r{i}/{len(cas)}", end="", flush=True)
    print()
    lignes = [
        f"# Grands arrêts par notion (D124) : non-régression - {datetime.now():%Y-%m-%d %H:%M}", "",
        f"{len(cas)} cas de {len(fichiers)} jeux (`eval/*.yaml` sauf `{NOUVEAU}`). Recherche de production sans "
        "reformulation par Gemini (embeddings, reclassement, lexique), faite deux fois par cas : sans puis avec les "
        "grands arrêts.", "",
        "| Mesure | Résultat |", "|---|---|",
        f"| Cas dont les extraits d'avant changent (ordre ou contenu) | {sum('avant changes' in e for e in ecarts)} |",
        f"| Cas dont les extraits du secours changent (hors grand arrêt ajouté) | {sum('secours' in e for e in ecarts)} |",
        f"| Source attendue dans les 8 (avant / après), {sources['attendues']} cas | {sources['8 avant']} / {sources['8 apres']} |",
        f"| Source attendue dans les 4 du secours (avant / après) | {sources['4 avant']} / {sources['4 apres']} |",
        f"| Cas qui reçoivent au moins un grand arrêt (ajouté ou signalé) | {len(touches)} |", "",
        "Par jeu : " + ", ".join(f"{k} {v}" for k, v in sorted(par_fichier.items())), "",
        "## Écarts", "", "| Cas | Écart |", "|---|---|", *(ecarts or ["| aucun | |"]), "",
        "## Cas qui reçoivent des grands arrêts", "",
        "| Cas | Question | Ajoutés | Grands arrêts parmi les extraits |", "|---|---|---|---|", *touches,
    ]
    sortie = ROOT / "eval" / "resultats" / f"grands-arrets-regression-{datetime.now():%Y%m%d-%H%M}.md"
    sortie.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes[:14]))
    print(f"-> {sortie}")
    return 1 if ecarts else 0


if __name__ == "__main__":
    sys.exit(main())
