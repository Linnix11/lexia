"""Pose les 30 questions du dossier de relecture au moteur local de Lexia (meme chemin que POST /chat).

Usage (depuis la racine du depot, .venv actif) :
    python docs/relecture-enseignant/outils/interroger.py            # toutes les questions
    python docs/relecture-enseignant/outils/interroger.py --n 3,17   # quelques-unes (remplace leur ligne)

Ecrit docs/relecture-enseignant/reponses.jsonl : une ligne par question, avec la reponse complete, le modele
qui a repondu (lu dans le journal des requetes, jamais dans .env) et les sources citees. Une pause separe les
questions pour rester dans le niveau gratuit de Gemini (deux appels par question : reformulation et reponse).
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import tempfile
import time
from pathlib import Path

ICI = Path(__file__).resolve().parent
DOSSIER = ICI.parent
RACINE = DOSSIER.parent.parent
sys.path.insert(0, str(RACINE))

from fastapi.testclient import TestClient  # noqa: E402

from api.config import get_settings  # noqa: E402
from api.main import create_app  # noqa: E402

SORTIE = DOSSIER / "reponses.jsonl"


def journal(dossier: Path) -> dict[str, dict]:
    f = dossier / "requetes.jsonl"
    if not f.exists():
        return {}
    out = {}
    for line in f.read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        if d.get("route") == "chat":
            out[d["reponse_id"]] = d
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--n", help="numeros a (re)poser, separes par des virgules")
    p.add_argument("--pause", type=float, default=25.0)
    p.add_argument("--essais", type=int, default=3)
    a = p.parse_args()

    questions = json.loads((DOSSIER / "questions.json").read_text(encoding="utf-8"))
    voulus = {int(x) for x in a.n.split(",")} if a.n else None
    if voulus:
        questions = [q for q in questions if q["n"] in voulus]
    anciennes = {}
    if SORTIE.exists():
        for line in SORTIE.read_text(encoding="utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                anciennes[d["n"]] = d

    logs = Path(tempfile.mkdtemp(prefix="lexia-relecture-"))
    settings = dataclasses.replace(get_settings(), logs_dir=logs, rate_limit_per_minute=0, comptes_actifs=False)
    app = create_app(settings)
    client = TestClient(app)

    for i, q in enumerate(questions, start=1):
        ligne = {k: q[k] for k in ("n", "categorie", "matiere", "niveau", "mode", "question")}
        for essai in range(a.essais):
            debut = time.monotonic()
            corps = {"question": q["question"], "mode": q["mode"], "niveau": q["niveau"]}
            if q["matiere"]:
                corps["matiere"] = q["matiere"]
            r = client.post("/chat", json=corps)
            ligne["duree_s"] = round(time.monotonic() - debut, 1)
            if r.status_code == 200:
                data = r.json()
                j = journal(logs).get(data["reponse_id"], {})
                ligne.update(statut=data["statut"], modele=j.get("modele"), reponse=data,
                             passages_fournis=j.get("passages_fournis", []))
                ligne.pop("erreur", None)
                break
            ligne["erreur"] = f"HTTP {r.status_code} {r.text[:200]}"
            time.sleep(30 * (essai + 1))
        anciennes[q["n"]] = ligne
        SORTIE.write_text("".join(json.dumps(anciennes[n], ensure_ascii=False) + "\n" for n in sorted(anciennes)),
                          encoding="utf-8")
        etat = ligne.get("erreur") or f"{ligne['statut']} ({ligne.get('modele')})"
        print(f"[{i}/{len(questions)}] Q{q['n']} : {etat} en {ligne['duree_s']} s", flush=True)
        if i < len(questions):
            time.sleep(a.pause)
    return 0


if __name__ == "__main__":
    sys.exit(main())
