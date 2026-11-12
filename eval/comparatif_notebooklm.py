"""Comparatif Lexia / NotebookLM sur 30 cas du jeu d'evaluation, notation a l'aveugle.

Protocole complet : eval/COMPARATIF_NOTEBOOKLM.md

Usage :
    python eval/comparatif_notebooklm.py preparer
        -> eval/comparatif/questions.md          questions a poser a NotebookLM, une par une
        -> eval/comparatif/notebooklm.csv        a remplir : reponse de NotebookLM pour chaque cas

    python eval/run.py --ids <liste affichee par preparer>   # reponses de Lexia, meme jour

    python eval/comparatif_notebooklm.py grille eval/resultats/<run>.jsonl
        -> eval/comparatif/grille_aveugle.csv    a noter par l'enseignant (systemes A / B)
        -> eval/comparatif/cle.json              qui est A, qui est B : ne pas ouvrir avant la fin

    python eval/comparatif_notebooklm.py bilan
        -> eval/comparatif/bilan.md
"""

from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.cas import ROOT, charger  # noqa: E402

DOSSIER = ROOT / "eval" / "comparatif"
GRAINE = 20261112  # tirage A / B reproductible

# 30 cas : 7 introduction, 8 constitutionnel, 8 civil, 7 pieges.
# Melange de questions de cours, de jurisprudence, de methode et de pieges (references inventees,
# articles renumerotes, conseil personnel, injection). Fige pour pouvoir refaire la mesure plus tard.
IDS = [
    "intro-01", "intro-02", "intro-05", "intro-13", "intro-18", "intro-33", "intro-36",
    "const-08", "const-19", "const-23", "const-32", "const-33", "const-35", "const-37", "const-39",
    "civ-03", "civ-05", "civ-15", "civ-19", "civ-24", "civ-33", "civ-34", "civ-38",
    "piege-01", "piege-09", "piege-11", "piege-12", "piege-21", "piege-29", "piege-30",
]

OUI_NON = {"oui", "non"}


def selection() -> list:
    par_id = {c.id: c for c in charger()}
    manquants = [i for i in IDS if i not in par_id]
    if manquants:
        raise ValueError(f"Cas absents de cas.yaml : {manquants}")
    return [par_id[i] for i in IDS]


def ecrire_csv(fichier: Path, entetes: list[str], lignes: list[dict]) -> None:
    with fichier.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=entetes, delimiter=";")
        w.writeheader()
        w.writerows(lignes)


def lire_csv(fichier: Path) -> list[dict]:
    with fichier.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


# ----------------------------------------------------------------------------- preparer

def preparer() -> int:
    DOSSIER.mkdir(exist_ok=True)
    cas = selection()
    md = ["# Questions à poser à NotebookLM", "",
          "Une question par conversation (bouton de nouvelle conversation entre deux questions).",
          "Copier la réponse complète, citations comprises, dans `notebooklm.csv` (colonne `reponse`).", ""]
    for c in cas:
        md.append(f"## {c.id}")
        md.append("")
        md.append(c.question)
        md.append("")
    (DOSSIER / "questions.md").write_text("\n".join(md), encoding="utf-8")

    cible = DOSSIER / "notebooklm.csv"
    if cible.exists():
        print(f"{cible} existe deja : non ecrase.")
    else:
        ecrire_csv(cible, ["id", "question", "reponse"],
                   [{"id": c.id, "question": c.question, "reponse": ""} for c in cas])
    print(f"Ecrit dans {DOSSIER}.")
    print("Reponses de Lexia, a lancer le meme jour :")
    print(f"  python eval/run.py --ids {','.join(IDS)}")
    return 0


# ----------------------------------------------------------------------------- grille

def texte_lexia(r: dict) -> str:
    """Reponse Lexia mise a plat : sans les intitules de blocs ni les identifiants internes,
    pour que la presentation ne trahisse pas trop le systeme."""
    if r["statut"] != "reponse":
        return r.get("message") or f"[{r['statut']}]"
    morceaux = [r.get("titre") or ""]
    for cle in ("droit_positif", "explication", "points_incertains"):
        morceaux += [it["texte"] for it in r.get(cle) or []]
    refs = [s.get("entete", "") for s in r.get("sources") or []]
    texte = "\n".join(m for m in morceaux if m)
    if refs:
        texte += "\n\nSources : " + " ; ".join(refs)
    return texte


def lire_lexia(fichier: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for ligne in fichier.read_text(encoding="utf-8").splitlines():
        if not ligne.strip():
            continue
        d = json.loads(ligne)
        if d.get("erreur") or not isinstance(d.get("reponse"), dict):
            continue
        out[d["id"]] = texte_lexia(d["reponse"])  # la derniere ligne d'un id l'emporte
    return out


def grille(run: Path) -> int:
    cas = selection()
    lexia = lire_lexia(run)
    nb = {l["id"]: l["reponse"].strip() for l in lire_csv(DOSSIER / "notebooklm.csv")}
    manque_l = [c.id for c in cas if c.id not in lexia]
    manque_n = [c.id for c in cas if not nb.get(c.id)]
    if manque_l or manque_n:
        if manque_l:
            print(f"Reponses Lexia manquantes ({len(manque_l)}) : {','.join(manque_l)}")
        if manque_n:
            print(f"Reponses NotebookLM manquantes ({len(manque_n)}) : {','.join(manque_n)}")
        return 1

    tirage = random.Random(GRAINE)
    cle, lignes = {}, []
    for c in cas:
        a_est_lexia = tirage.random() < 0.5
        cle[c.id] = {"A": "lexia" if a_est_lexia else "notebooklm", "B": "notebooklm" if a_est_lexia else "lexia"}
        rep = {"lexia": lexia[c.id], "notebooklm": nb[c.id]}
        lignes.append({
            "id": c.id, "question": c.question,
            "comportement_attendu": " ou ".join(c.attendu),
            "reponse_A": rep[cle[c.id]["A"]], "reponse_B": rep[cle[c.id]["B"]],
            "exactitude_A": "", "utilite_A": "", "references_ok_A": "", "comportement_ok_A": "",
            "exactitude_B": "", "utilite_B": "", "references_ok_B": "", "comportement_ok_B": "",
            "commentaire": "",
        })
    ecrire_csv(DOSSIER / "grille_aveugle.csv", list(lignes[0]), lignes)
    (DOSSIER / "cle.json").write_text(json.dumps(cle, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"Grille : {DOSSIER / 'grille_aveugle.csv'} (a transmettre sans cle.json)")
    return 0


# ----------------------------------------------------------------------------- bilan

def note(v: str, cas_id: str, champ: str) -> int | None:
    v = v.strip()
    if not v:
        return None
    if v not in {"1", "2", "3", "4", "5"}:
        raise ValueError(f"{cas_id} / {champ} : note attendue de 1 a 5, recu {v!r}")
    return int(v)


def oui(v: str, cas_id: str, champ: str) -> bool | None:
    v = v.strip().lower()
    if not v:
        return None
    if v not in OUI_NON:
        raise ValueError(f"{cas_id} / {champ} : oui ou non attendu, recu {v!r}")
    return v == "oui"


def calculer(lignes: list[dict], cle: dict) -> dict:
    stats = {s: {"exactitude": [], "utilite": [], "references_ok": [], "comportement_ok": [],
                 "erreurs_de_droit": []} for s in ("lexia", "notebooklm")}
    victoires = {"lexia": 0, "notebooklm": 0, "egalite": 0}
    for l in lignes:
        i = l["id"]
        notes = {}
        for lettre in ("A", "B"):
            s = cle[i][lettre]
            ex = note(l[f"exactitude_{lettre}"], i, f"exactitude_{lettre}")
            ut = note(l[f"utilite_{lettre}"], i, f"utilite_{lettre}")
            ref = oui(l[f"references_ok_{lettre}"], i, f"references_ok_{lettre}")
            comp = oui(l[f"comportement_ok_{lettre}"], i, f"comportement_ok_{lettre}")
            for champ, v in (("exactitude", ex), ("utilite", ut), ("references_ok", ref), ("comportement_ok", comp)):
                if v is not None:
                    stats[s][champ].append(v)
            if ex == 1:
                stats[s]["erreurs_de_droit"].append(i)
            notes[s] = ex
        if notes["lexia"] is not None and notes["notebooklm"] is not None:
            if notes["lexia"] > notes["notebooklm"]:
                victoires["lexia"] += 1
            elif notes["lexia"] < notes["notebooklm"]:
                victoires["notebooklm"] += 1
            else:
                victoires["egalite"] += 1
    return {"stats": stats, "victoires": victoires}


def bilan() -> int:
    lignes = lire_csv(DOSSIER / "grille_aveugle.csv")
    cle = json.loads((DOSSIER / "cle.json").read_text(encoding="utf-8"))
    r = calculer(lignes, cle)

    def moy(xs):
        return f"{sum(xs) / len(xs):.2f} ({len(xs)})" if xs else "n/a"

    def taux(xs):
        return f"{100 * sum(xs) / len(xs):.0f} % ({sum(xs)}/{len(xs)})" if xs else "n/a"

    s, v = r["stats"], r["victoires"]
    md = ["# Comparatif Lexia / NotebookLM", "",
          "| Indicateur | Lexia | NotebookLM |", "|---|---|---|",
          f"| Exactitude moyenne (1-5) | {moy(s['lexia']['exactitude'])} | {moy(s['notebooklm']['exactitude'])} |",
          f"| Utilité moyenne (1-5) | {moy(s['lexia']['utilite'])} | {moy(s['notebooklm']['utilite'])} |",
          f"| Références exactes et vérifiables | {taux(s['lexia']['references_ok'])} | {taux(s['notebooklm']['references_ok'])} |",
          f"| Comportement attendu | {taux(s['lexia']['comportement_ok'])} | {taux(s['notebooklm']['comportement_ok'])} |",
          f"| Erreurs de droit (note 1) | {len(s['lexia']['erreurs_de_droit'])} | {len(s['notebooklm']['erreurs_de_droit'])} |",
          "",
          f"Cas par cas (exactitude) : Lexia meilleur {v['lexia']}, NotebookLM meilleur {v['notebooklm']}, "
          f"égalité {v['egalite']}.", ""]
    for nom in ("lexia", "notebooklm"):
        if s[nom]["erreurs_de_droit"]:
            md.append(f"Erreurs de droit {nom} : {', '.join(s[nom]['erreurs_de_droit'])}")
    (DOSSIER / "bilan.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[1] == "preparer":
        return preparer()
    if len(argv) == 3 and argv[1] == "grille":
        return grille(Path(argv[2]))
    if len(argv) >= 2 and argv[1] == "bilan":
        return bilan()
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
