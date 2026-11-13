"""Backtest des reponses par mode, avec le vrai modele : la forme de la reponse change-t-elle selon le mode ?

Pour chaque mode, quelques questions (dont une notion commune, « le dol », posee dans les 5 modes) :
  - statut obtenu ;
  - rubriques imposees presentes / attendues (api.prompts.RUBRIQUES) ;
  - elements retires par le controle des citations ;
  - nombre de sources citees et duree.
Appelle le modele principal (Gemini) : une vingtaine de questions, a lancer hors des heures d'usage.

    python eval/backtest_modes.py        # rapport dans eval/resultats/backtest-modes-<date>.md
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.config import get_settings  # noqa: E402
from api.llm.base import LLMError  # noqa: E402
from api.main import (_construire_embedder, _construire_expanseur, _construire_llm,  # noqa: E402
                      _construire_reclasseur, _construire_retriever, _construire_secours)
from api.prompts import RUBRIQUES  # noqa: E402
from api.rag import Lexia  # noqa: E402
from eval.cas import ROOT  # noqa: E402

QUESTIONS = {
    "expliquer": [("droit_des_contrats", "Qu'est-ce que le dol ?"),
                  ("droit_penal", "Qu'est-ce que la légitime défense ?"),
                  ("droit_social", "Qu'est-ce que la rupture conventionnelle ?"),
                  ("droit_administratif", "Qu'est-ce que le référé-liberté ?")],
    "fiche": [("droit_des_contrats", "Fais-moi une fiche sur le dol"),
              ("droit_civil", "Fais-moi une fiche sur la responsabilité pour faute"),
              ("droit_de_la_famille", "Fais-moi une fiche sur l'autorité parentale"),
              ("droit_penal", "Fais-moi une fiche sur la complicité")],
    "cas_pratique": [("droit_des_contrats", "Paul a vendu sa voiture à Marie en lui cachant qu'elle avait été gravement "
                                            "accidentée. Marie peut-elle obtenir l'annulation de la vente ?"),
                     ("droit_civil", "En jouant au ballon, Léo brise la vitrine d'un commerçant. Le commerçant peut-il "
                                     "obtenir réparation, et de qui ?"),
                     ("droit_social", "Un salarié est licencié pour avoir participé à une grève sans commettre de faute "
                                      "lourde. Que peut-il faire ?"),
                     ("droit_penal", "Agressé dans la rue, Hugo frappe son agresseur qui est blessé. Hugo est-il "
                                     "pénalement responsable ?")],
    "commentaire": [("droit_des_contrats", "Méthode du commentaire d'arrêt appliquée au dol par réticence"),
                    ("droit_social", "Commente l'arrêt de la chambre sociale du 9 mai 2012, n° 10-24.307, sur le "
                                     "licenciement d'un salarié gréviste"),
                    ("droit_constitutionnel", "Commente la décision du Conseil constitutionnel n° 71-44 DC du "
                                              "16 juillet 1971 sur la liberté d'association"),
                    ("droit_civil", "Commente un arrêt sur la responsabilité du fait des choses")],
    "dissertation": [("droit_des_contrats", "Sujet de dissertation : le dol"),
                     ("droit_des_contrats", "Sujet de dissertation : la force obligatoire du contrat"),
                     ("introduction_au_droit", "Sujet de dissertation : le juge et la loi"),
                     ("droit_constitutionnel", "Sujet de dissertation : le contrôle de constitutionnalité des lois")],
}


def main() -> int:
    s = get_settings()
    lexia = Lexia(_construire_retriever(s), _construire_llm(s), None, _construire_embedder(s), _construire_expanseur(s),
                  _construire_reclasseur(s), secours=_construire_secours(s))
    lignes = [f"# Backtest des réponses par mode - {datetime.now():%Y-%m-%d %H:%M}", "",
              "| Mode | Question | Statut | Rubriques présentes / attendues | Éléments retirés | Sources citées | Durée |",
              "|---|---|---|---|---|---|---|"]
    exemples: dict[str, list[str]] = {}
    bilan: dict[str, list[float]] = {}
    for mode, questions in QUESTIONS.items():
        attendues = RUBRIQUES[mode]
        for matiere, q in questions:
            t = time.monotonic()
            try:
                r = lexia.chat(q, mode, matiere, "L2", 3)
            except LLMError as e:
                lignes.append(f"| {mode} | {q[:70]} | modèle indisponible | - | - | - | {time.monotonic() - t:.0f} s |")
                print(f"{mode:13s} indisponible : {str(e)[:80]}", flush=True)
                continue
            presentes = [x for x in attendues if any(e.get("rubrique") == x for e in r["explication"])]
            taux = len(presentes) / len(attendues)
            bilan.setdefault(mode, []).append(taux if r["statut"] == "reponse" else 0.0)
            retires = r["controle"]["elements_retires"] + r["controle"]["citations_retirees"]
            lignes.append(f"| {mode} | {q[:70]} | {r['statut']} | {len(presentes)}/{len(attendues)} | {retires} | "
                          f"{len(r['sources'])} | {time.monotonic() - t:.0f} s |")
            print(f"{mode:13s} {r['statut']:10s} rubriques {len(presentes)}/{len(attendues)}  retires {retires}  "
                  f"{q[:50]}", flush=True)
            if "dol" in q.lower() and mode not in exemples and r["statut"] == "reponse":
                exemples[mode] = [f"- **{e.get('rubrique', '(sans rubrique)')}** : {e['texte'][:220]}"
                                  for e in r["explication"]]
    lignes += ["", "## Bilan par mode", "", "| Mode | Rubriques remplies (moyenne) |", "|---|---|"]
    for mode, v in bilan.items():
        lignes.append(f"| {mode} | {100 * sum(v) / len(v):.0f} % sur {len(v)} réponse(s) |")
    lignes += ["", "## Même notion (le dol), cinq modes", ""]
    for mode, ex in exemples.items():
        lignes += [f"### {mode}", "", *ex, ""]
    sortie = ROOT / "eval" / "resultats" / f"backtest-modes-{datetime.now():%Y%m%d-%H%M}.md"
    sortie.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print(f"-> {sortie}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
