"""Cas pratiques de responsabilite : quels responsables la reponse examine-t-elle ? (D115, D119, D122)

Usage :
    python eval/responsables.py eval/resultats/X.jsonl [Y.jsonl ...]

Pour chaque cas : articles cites, et si l'analyse (explication, droit positif, reponse directe) traite la
responsabilite propre de l'auteur (1240), celle des parents (1242 al. 4) et celle du gardien de la chose
(1242 al. 1) ; pour les accidents de la circulation, si la loi du 5 juillet 1985 est appliquee (R-1). Reperage par expressions, a relire a la main : un « oui » dit que le fondement est nomme et
applique, pas que le raisonnement est juste.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RESPONSABILITE = {"cp-01", "cp-02", "cp-31", "cp-32", "cp-33", "cp-34"}
ACCIDENTS = {"cp-35", "cp-36", "cp-37"}  # vehicule terrestre a moteur : loi du 5 juillet 1985 (D122)

# Auteur : 1240 cite et responsabilite propre de l'auteur nommee dans l'analyse
_AUTEUR = re.compile(r"responsabilit[ée] (?:personnelle|propre|du fait personnel)|(?:lui|elle)-m[êe]me"
                     r"|articles? 1240\b", re.I)
_PARENTS = re.compile(r"parents|p[èe]re et m[èe]re|1242,? (?:al\.|alin[ée]a) ?4|quatri[èe]me alin[ée]a", re.I)
_GARDIEN = re.compile(r"gardien|garde (?:de|du|d'une|de la) (?:la |le |l')?(?:chose|ballon|skate|planche)"
                      r"|fait des choses|1242,? (?:al\.|alin[ée]a) ?(?:1|premier)\b|premier alin[ée]a", re.I)
_LOI_1985 = re.compile(r"85-677|5 juillet 1985|loi Badinter", re.I)


def texte(reponse: dict) -> str:
    parties = [reponse.get("titre") or ""]
    for cle in ("reponse_directe", "droit_positif", "explication", "points_incertains"):
        parties += [e.get("texte", "") for e in reponse.get(cle) or []]
    return "\n".join(parties)


def ligne(d: dict) -> dict:
    r = d.get("reponse") or {}
    cites = sorted({s.get("numero") if s.get("source_id") == "code_civil" and s.get("numero") else s["id"]
                    for s in r.get("sources") or []})
    t = texte(r)
    return {"id": d["id"], "statut": d.get("statut") or d.get("erreur"), "cites": cites,
            "1240_1242": "1240" in cites and "1242" in cites,
            "auteur": "1240" in cites and bool(_AUTEUR.search(t)), "parents": bool(_PARENTS.search(t)), "gardien": bool(_GARDIEN.search(t)),
            "loi_1985": any("lois:LEGIARTI00000683" in (s.get("id") or "") for s in r.get("sources") or [])
            and bool(_LOI_1985.search(t)),
            "ok": bool(d.get("comportement_ok")) and bool(d.get("citations_existantes"))
            and bool(d.get("reponse_sourcee"))}


def main(chemins: list[str]) -> int:
    oui = lambda b: "oui" if b else "non"  # noqa: E731
    for chemin in chemins:
        lignes = [ligne(json.loads(x)) for x in Path(chemin).read_text(encoding="utf-8").splitlines() if x.strip()]
        print(f"\n## {Path(chemin).name}\n")
        print("| Cas | Statut | Articles cites | 1240 et 1242 | Auteur | Parents | Gardien | Loi de 1985 | Indicateurs |")
        print("|---|---|---|---|---|---|---|---|---|")
        for x in lignes:
            print(f"| {x['id']} | {x['statut']} | {', '.join(x['cites'])} | {oui(x['1240_1242'])} | {oui(x['auteur'])} "
                  f"| {oui(x['parents'])} | {oui(x['gardien'])} | {oui(x['loi_1985'])} | {oui(x['ok'])} |")
        resp = [x for x in lignes if x["id"] in RESPONSABILITE]
        acc = [x for x in lignes if x["id"] in ACCIDENTS]
        autres = [x for x in lignes if x["id"] not in RESPONSABILITE | ACCIDENTS]
        n = len(resp)
        print(f"\nResponsabilite ({n} cas) : 1240 et 1242 {sum(x['1240_1242'] for x in resp)}/{n}, auteur "
              f"{sum(x['auteur'] for x in resp)}/{n}, parents {sum(x['parents'] for x in resp)}/{n}, gardien "
              f"{sum(x['gardien'] for x in resp)}/{n} ; autres cas : indicateurs {sum(x['ok'] for x in autres)}"
              f"/{len(autres)}")
        if acc:
            print(f"Accidents de la circulation ({len(acc)} cas) : loi de 1985 citee et appliquee "
                  f"{sum(x['loi_1985'] for x in acc)}/{len(acc)}, indicateurs {sum(x['ok'] for x in acc)}/{len(acc)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
