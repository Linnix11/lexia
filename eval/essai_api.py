"""Essai manuel de l'API en marche (appels reels a Gemini).

Usage : python eval/essai_api.py [http://localhost:8000]
Affiche les reponses de facon lisible ; ne remplace pas le jeu d'evaluation de la phase 4.
"""

from __future__ import annotations

import sys
import time

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
QUESTIONS = [
    ("Quelles sont les conditions de la responsabilité pour faute ?", "expliquer", "droit_civil"),
    ("Fais-moi une fiche sur la force obligatoire du contrat", "fiche", "droit_civil"),
    ("À quoi sert l'article 61-1 de la Constitution ?", "expliquer", "droit_constitutionnel"),
    ("Mon propriétaire refuse de me rendre ma caution, que dois-je faire ?", "expliquer", None),
    ("Quel est le régime fiscal des plus-values immobilières ?", "expliquer", None),
]


def afficher_chat(d: dict) -> None:
    print(f"  statut={d['statut']} titre={d['titre']!r} recherche={d['controle']['recherche']}")
    for cle in ("droit_positif", "explication", "points_incertains"):
        for it in d[cle]:
            print(f"   [{cle[:6]}] {it['texte'][:200]}  <- {len(it['sources'])} source(s)")
    if d["message"]:
        print(f"   message : {d['message'][:250]}")
    print(f"   controle : {d['controle']}")
    for s in d["sources"]:
        print(f"   {s['label']} {s['entete'][:100]}")


def main() -> int:
    with httpx.Client(base_url=BASE, timeout=180) as c:
        print(c.get("/sante").json())
        for q, mode, matiere in QUESTIONS:
            t = time.monotonic()
            r = c.post("/chat", json={"question": q, "mode": mode, "matiere": matiere})
            print(f"\n### {q} ({mode}) -> HTTP {r.status_code} en {time.monotonic() - t:.1f} s")
            if r.status_code == 200:
                afficher_chat(r.json())
            else:
                print("  ", r.text[:300])

        t = time.monotonic()
        r = c.post("/quiz", json={"theme": "les vices du consentement", "format": "qcm", "nombre": 4,
                                  "matiere": "droit_civil"})
        print(f"\n### QUIZ vices du consentement -> HTTP {r.status_code} en {time.monotonic() - t:.1f} s")
        if r.status_code == 200:
            quiz = r.json()
            print(f"  obtenu {quiz['obtenu']}/{quiz['demande']} controle={quiz['controle']}")
            for q in quiz["questions"]:
                print(f"   {q['index']}. {q['question']}")
                for i, ch in enumerate(q["choix"]):
                    print(f"      {i}) {ch}")
            if quiz["quiz_id"]:
                rep = [{"index": q["index"], "valeur": 0} for q in quiz["questions"]]
                corr = c.post("/quiz/correct", json={"quiz_id": quiz["quiz_id"], "reponses": rep}).json()
                print(f"  correction (toujours la reponse 0) : score {corr['score']}/{corr['total']}")
                for res in corr["resultats"]:
                    print(f"   {res['index']}: {res['statut']} (bonne : {res['bonne_reponse']}) {res['explication'][:150]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
