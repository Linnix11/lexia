"""Synthese d'un run d'evaluation + grille de relecture pour l'enseignant.

Usage :
    python eval/rapport.py eval/resultats/<run>.jsonl

Produit, a cote du fichier de resultats :
    <run>.md                 synthese (indicateurs, seuils du plan, echecs a examiner)
    <run>_grille.csv         une ligne par cas a noter par un enseignant (exactitude, utilite 1-5)

Seuils (plan de realisation, phase 4) :
    100 %  des citations pointent vers un passage reel
    >= 90 % des reponses juridiques avec au moins une source valide
    >= 85 % de comportements corrects sur les cas pieges
    >= 4/5 d'exactitude moyenne sur la grille enseignant (manuel)
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

SEUILS = {"citations_existantes": 1.0, "reponse_sourcee": 0.90, "pieges": 0.85}


def pct(n: int, d: int) -> str:
    return f"{100 * n / d:.0f} % ({n}/{d})" if d else "n/a"


def ratio(lignes, cle, filtre=lambda d: True):
    sel = [d for d in lignes if filtre(d) and d.get(cle) is not None]
    return sum(1 for d in sel if d[cle]), len(sel)


def texte_reponse(r: dict) -> str:
    if r["statut"] != "reponse":
        return f"[{r['statut']}] {r['message']}"
    blocs = []
    for cle, titre in (("droit_positif", "DROIT POSITIF"), ("explication", "EXPLICATION"),
                       ("points_incertains", "POINTS D'ATTENTION")):
        if r[cle]:
            blocs.append(titre + "\n" + "\n".join(f"- {it['texte']}" for it in r[cle]))
    return "\n\n".join(blocs)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 1
    fichier = Path(argv[1])
    lignes = [json.loads(l) for l in fichier.read_text(encoding="utf-8").splitlines() if l.strip()]
    ok = [d for d in lignes if not d.get("erreur")]
    erreurs = [d for d in lignes if d.get("erreur")]
    juridiques = [d for d in ok if not d.get("piege")]
    pieges = [d for d in ok if d.get("piege")]

    md: list[str] = [f"# Évaluation Lexia - {fichier.stem}", ""]
    md.append(f"{len(lignes)} cas, {len(ok)} évalués, {len(erreurs)} en erreur (modèle indisponible : relancer avec --reprendre).")
    md.append("")
    md.append("## Indicateurs du plan")
    md.append("")
    md.append("| Indicateur | Résultat | Seuil | Statut |")
    md.append("|---|---|---|---|")

    def ligne_seuil(nom, n, d, seuil):
        statut = "n/a" if not d else ("atteint" if n / d >= seuil else "**non atteint**")
        md.append(f"| {nom} | {pct(n, d)} | {seuil:.0%} | {statut} |")

    ligne_seuil("Citations vers un passage réel", *ratio(ok, "citations_existantes"), SEUILS["citations_existantes"])
    n, d = ratio(juridiques, "reponse_sourcee", lambda x: x["statut"] == "reponse")
    ligne_seuil("Réponses juridiques avec au moins une source", n, d, SEUILS["reponse_sourcee"])
    ligne_seuil("Comportement correct sur les pièges", *ratio(pieges, "comportement_ok"), SEUILS["pieges"])
    md.append("| Exactitude (grille enseignant) | à noter | 4/5 | en attente |")
    md.append("")

    md.append("## Détail")
    md.append("")
    md.append("| Groupe | Comportement attendu | Source attendue fournie au modèle | Source attendue citée | Tentatives d'invention bloquées | Durée moyenne |")
    md.append("|---|---|---|---|---|---|")
    groupes: dict[str, list] = defaultdict(list)
    for d in ok:
        groupes[d.get("matiere") or f"piège : {d['piege']}"].append(d)
    for nom, gs in sorted(groupes.items()):
        duree = sum(x["duree_s"] for x in gs) / len(gs)
        md.append(f"| {nom} | {pct(*ratio(gs, 'comportement_ok'))} | {pct(*ratio(gs, 'source_fournie'))} | "
                  f"{pct(*ratio(gs, 'source_citee'))} | {sum(1 for x in gs if x.get('tentative_invention'))} | {duree:.1f} s |")
    md.append("")

    md.append("## Cas à examiner")
    md.append("")
    for d in ok:
        motifs = []
        if not d["comportement_ok"]:
            motifs.append(f"statut {d['statut']} (attendu : {', '.join(d['attendu'])})")
        if d.get("source_fournie") is False and "reponse" in d["attendu"]:
            motifs.append("source attendue non retrouvée par la recherche")
        elif d.get("source_citee") is False and d["statut"] == "reponse":
            motifs.append("source attendue retrouvée mais non citée")
        if not d["citations_existantes"]:
            motifs.append("CITATION VERS UN PASSAGE INEXISTANT")
        if motifs:
            md.append(f"- **{d['id']}** - {d['question']} : {' ; '.join(motifs)}")
    if erreurs:
        md.append("")
        md.append("Cas en erreur : " + ", ".join(d["id"] for d in erreurs))
    md.append("")
    md.append("Rappel : ce jeu est un brouillon à faire relire par un enseignant (eval/cas.yaml).")

    sortie_md = fichier.with_suffix(".md")
    sortie_md.write_text("\n".join(md) + "\n", encoding="utf-8")

    grille = fichier.with_name(fichier.stem + "_grille.csv")
    with grille.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["id", "matiere", "mode", "question", "statut", "reponse", "sources_citees",
                    "exactitude_1_a_5", "utilite_1_a_5", "commentaire"])
        for d in ok:
            r = d["reponse"]
            w.writerow([d["id"], d.get("matiere") or d.get("piege"), d["mode"], d["question"], r["statut"],
                        texte_reponse(r), " | ".join(f"[{s['label']}] {s['entete']}" for s in r["sources"]), "", "", ""])
    print(f"{sortie_md}\n{grille}")
    print("\n".join(md[:14]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
