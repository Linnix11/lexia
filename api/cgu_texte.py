"""Texte des conditions generales joint a la confirmation du contrat (C. consom. L. 221-13 : support durable ;
audit du 2026-11-19, JUR-8 ; D111).

Une seule source : la page Cgu de web/src/site/Legal.tsx. Le test web/src/site/cguTexte.test.tsx la rend et ecrit
api/cgu/<version>.json (`npm run cgu` dans web/), une variante par etat de la configuration qui change le texte
(niveau Gemini, secours Groq) ; il echoue si la page change sans que le fichier soit regenere. Les fichiers des
versions precedentes restent : une confirmation renvoyee plus tard joint la version acceptee par l'acheteur.
Les reperes {{editeur}}, {{contact}}, {{url}}... sont remplaces ici par la configuration du serveur.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

DOSSIER = Path(__file__).parent / "cgu"
NON_RENSEIGNE = "[non renseigné]"


def fichier_version(version: str) -> str:
    """« 20 novembre 2026 » -> 20-novembre-2026.json (meme regle que le test du site)."""
    sans_accents = "".join(c for c in unicodedata.normalize("NFD", version) if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", sans_accents.lower()).strip("-") + ".json"


def texte_cgu(version: str, legal: dict, contact: str, url_publique: str, dossier: Path = DOSSIER) -> str | None:
    """Texte des CGU de cette version avec les valeurs de l'editeur, ou None si la version n'a pas de fichier."""
    chemin = dossier / fichier_version(version)
    if not version or not chemin.is_file():
        return None
    variantes = json.loads(chemin.read_text(encoding="utf-8"))["variantes"]
    cle = f"gemini_payant={int(bool(legal.get('gemini_payant')))},groq={int(bool(legal.get('groq')))}"
    texte = variantes.get(cle) or next(iter(variantes.values()))
    valeurs = {**{k: str(v) for k, v in legal.items() if isinstance(v, str)}, "contact": contact or "",
               "url": url_publique or ""}

    def remplacer(m: re.Match) -> str:
        return valeurs.get(m.group(1), "").strip() or NON_RENSEIGNE

    return re.sub(r"\{\{(\w+)\}\}", remplacer, texte)
