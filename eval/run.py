"""Execute le jeu d'evaluation contre le pipeline reel (recherche + Gemini + controle des citations).

Usage :
    python eval/run.py                              # tous les cas -> eval/resultats/<horodatage>.jsonl
    python eval/run.py --ids civ-32,piege-09        # quelques cas
    python eval/run.py --reprendre eval/resultats/X.jsonl   # complete un run interrompu
    python eval/rapport.py eval/resultats/X.jsonl   # synthese + grille de relecture enseignant

Le run est lent a dessein (pause entre les cas) pour rester dans le quota gratuit de Gemini.
Chaque cas fait 2 appels au modele (reformulation + reponse). Les cas en erreur (503, quota) sont
reessayes, puis notes "erreur" : relancer avec --reprendre pour les completer.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from api.config import get_settings  # noqa: E402
from api.main import create_app  # noqa: E402
from eval.cas import ROOT, charger, correspond  # noqa: E402

RESULTATS = ROOT / "eval" / "resultats"


def lire_journal(dossier: Path) -> dict[str, dict]:
    f = dossier / "requetes.jsonl"
    if not f.exists():
        return {}
    out = {}
    for line in f.read_text(encoding="utf-8").splitlines():
        d = json.loads(line)
        if d.get("route") == "chat":
            out[d["reponse_id"]] = d
    return out


def evaluer(cas, data: dict, journal: dict, retriever) -> dict:
    statut = data["statut"]
    cites = [s["id"] for s in data["sources"]]
    fournis = journal.get("passages_fournis", [])
    p_fournis = [p for p in (retriever.get(pid) for pid in fournis) if p]
    p_cites = [p for p in (retriever.get(pid) for pid in cites) if p]
    res = {
        "comportement_ok": statut in cas.attendu,
        "citations_existantes": len(p_cites) == len(cites),
        "reponse_sourcee": statut != "reponse" or any(it["sources"] for it in data["droit_positif"])
        or (cas.mode in ("cas_pratique", "commentaire", "dissertation") and not data["droit_positif"]),
        "tentative_invention": bool(data["controle"]["elements_retires"] or data["controle"]["citations_retirees"]),
    }
    if cas.sources:
        res["source_fournie"] = any(correspond(ref, p) for ref in cas.sources for p in p_fournis)
        res["source_citee"] = statut == "reponse" and any(correspond(ref, p) for ref in cas.sources for p in p_cites)
    return res


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ids", help="Liste d'identifiants separes par des virgules")
    parser.add_argument("--reprendre", type=Path, help="Fichier de resultats a completer")
    parser.add_argument("--refaire", help="Avec --reprendre : identifiants a rejouer (separes par des virgules)")
    parser.add_argument("--pause", type=float, default=4.0, help="Secondes entre deux cas (quota)")
    parser.add_argument("--essais", type=int, default=3, help="Essais par cas en cas d'erreur du modele")
    args = parser.parse_args(argv)

    cas = charger()
    if args.ids:
        voulus = set(args.ids.split(","))
        cas = [c for c in cas if c.id in voulus]

    sortie = args.reprendre or RESULTATS / f"{datetime.now():%Y%m%d-%H%M%S}.jsonl"
    sortie.parent.mkdir(parents=True, exist_ok=True)
    deja = set()
    if sortie.exists():
        for line in sortie.read_text(encoding="utf-8").splitlines():
            d = json.loads(line)
            if not d.get("erreur"):
                deja.add(d["id"])
        # on ne garde que les lignes reussies : les erreurs seront rejouees
        refaire = set(args.refaire.split(",")) if args.refaire else set()
        deja -= refaire
        lignes = [l for l in sortie.read_text(encoding="utf-8").splitlines()
                  if not json.loads(l).get("erreur") and json.loads(l)["id"] not in refaire]
        sortie.write_text("\n".join(lignes) + ("\n" if lignes else ""), encoding="utf-8")
    a_faire = [c for c in cas if c.id not in deja]
    print(f"{len(a_faire)} cas a evaluer ({len(deja)} deja faits) -> {sortie}", flush=True)

    logs = Path(tempfile.mkdtemp(prefix="lexia-eval-"))
    settings = dataclasses.replace(get_settings(), logs_dir=logs, rate_limit_per_minute=0, comptes_actifs=False)
    app = create_app(settings)
    client = TestClient(app)
    retriever = app.state.retriever

    for i, c in enumerate(a_faire, start=1):
        ligne: dict = {"id": c.id, "matiere": c.matiere, "piege": c.piege, "mode": c.mode, "question": c.question,
                       "attendu": c.attendu, "sources_attendues": c.sources}
        for essai in range(args.essais):
            debut = time.monotonic()
            r = client.post("/chat", json={"question": c.question, "mode": c.mode, "matiere": c.matiere})
            ligne["duree_s"] = round(time.monotonic() - debut, 1)
            if r.status_code == 200:
                data = r.json()
                journal = lire_journal(logs).get(data["reponse_id"], {})
                ligne.update(statut=data["statut"], reponse=data, passages_fournis=journal.get("passages_fournis", []),
                             **evaluer(c, data, journal, retriever))
                ligne.pop("erreur", None)
                break
            ligne["erreur"] = f"HTTP {r.status_code}"
            time.sleep(20 * (essai + 1))
        with sortie.open("a", encoding="utf-8") as f:
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
        etat = ligne.get("erreur") or (f"{ligne['statut']}" + ("" if ligne["comportement_ok"] else " (INATTENDU)"))
        print(f"[{i}/{len(a_faire)}] {c.id}: {etat} en {ligne['duree_s']} s", flush=True)
        time.sleep(args.pause)
    print(f"termine -> {sortie}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
