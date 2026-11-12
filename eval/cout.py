"""Cout du modele par question, a partir des journaux (aucun texte de question n'y figure).

Usage :
    python eval/cout.py [dossier_logs] [--prix MODELE=ENTREE,SORTIE ...]

    dossier_logs : par defaut logs/ (en production, copier /opt/lexia/logs/modele.jsonl et requetes.jsonl)
    --prix       : prix en dollars par million de jetons, a recopier depuis la grille tarifaire officielle
                   de Gemini (ne pas deviner). Les jetons de reflexion sont comptes au prix de sortie :
                   a confirmer sur la grille du modele utilise.

Exemple :
    python eval/cout.py logs --prix gemini-3.5-flash=PRIX_ENTREE,PRIX_SORTIE
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def lire(chemin: Path) -> list[dict]:
    if not chemin.exists():
        return []
    out = []
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(ligne))
        except json.JSONDecodeError:
            continue
    return out


def prix(valeurs: list[str]) -> dict[str, tuple[float, float]]:
    out = {}
    for v in valeurs:
        modele, _, chiffres = v.partition("=")
        entree, _, sortie = chiffres.partition(",")
        out[modele.strip()] = (float(entree), float(sortie))
    return out


def calculer(appels: list[dict], requetes: list[dict], tarifs: dict[str, tuple[float, float]]) -> dict:
    par_modele: dict[tuple[str, str], dict] = defaultdict(lambda: {"appels": 0, "entree": 0, "sortie": 0, "reflexion": 0})
    for a in appels:
        s = par_modele[(a.get("modele", "?"), a.get("role", "?"))]
        s["appels"] += 1
        for k in ("entree", "sortie", "reflexion"):
            s[k] += int(a.get(k) or 0)
    cout_total, inconnu = 0.0, set()
    for (modele, _), s in par_modele.items():
        if modele in tarifs:
            pe, ps = tarifs[modele]
            s["cout"] = (s["entree"] * pe + (s["sortie"] + s["reflexion"]) * ps) / 1e6
            cout_total += s["cout"]
        else:
            inconnu.add(modele)
    # questions qui ont reellement appele le modele (hors cache et abstentions sans appel)
    questions = sum(1 for r in requetes if r.get("route") == "chat" and r.get("modele") and not r.get("cache"))
    return {"par_modele": dict(par_modele), "questions": questions, "cout_total": cout_total,
            "cout_par_question": cout_total / questions if questions and not inconnu else None,
            "sans_tarif": sorted(inconnu)}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("logs", nargs="?", type=Path, default=ROOT / "logs")
    ap.add_argument("--prix", action="append", default=[], metavar="MODELE=ENTREE,SORTIE")
    a = ap.parse_args(argv)
    r = calculer(lire(a.logs / "modele.jsonl"), lire(a.logs / "requetes.jsonl"), prix(a.prix))
    if not r["par_modele"]:
        print(f"Aucun appel releve dans {a.logs / 'modele.jsonl'}.")
        return 1
    print("| Modèle | Rôle | Appels | Jetons entrée / appel | Sortie / appel | Réflexion / appel | Coût ($) |")
    print("|---|---|---|---|---|---|---|")
    for (modele, role), s in sorted(r["par_modele"].items()):
        n = s["appels"]
        cout = f"{s['cout']:.4f}" if "cout" in s else "tarif ?"
        print(f"| {modele} | {role} | {n} | {s['entree'] / n:.0f} | {s['sortie'] / n:.0f} | {s['reflexion'] / n:.0f} | {cout} |")
    print()
    print(f"Questions ayant appelé le modèle : {r['questions']}")
    if r["cout_par_question"] is not None:
        print(f"Coût total : {r['cout_total']:.4f} $ ; coût moyen par question : {r['cout_par_question']:.5f} $")
    elif r["sans_tarif"]:
        print("Tarif manquant pour : " + ", ".join(r["sans_tarif"]) + " (option --prix).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
