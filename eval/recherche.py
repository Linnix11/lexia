"""Banc d'essai de la recherche : les articles attendus sont-ils dans les extraits envoyes au modele ?

Usage :
    python eval/recherche.py                 # 4 configurations : base, reclassement, reformulation, les deux

Mesure, pour chaque question, si un des articles attendus figure parmi les K passages transmis
au modele, et le temps de recherche. Premier embryon du jeu d'evaluation de la phase 4.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.config import get_settings  # noqa: E402
from api.main import _construire_expanseur, _construire_reclasseur  # noqa: E402
from api.rag import K_CHAT, Lexia  # noqa: E402
from api.retrieval.local import LocalRetriever  # noqa: E402
from ingest import embedders  # noqa: E402

CAS = [
    ("Quelles sont les conditions de la responsabilité pour faute ?", "droit_civil", {"1240", "1241"}),
    ("Quelles sont les conditions de validité du contrat ?", "droit_civil", {"1128"}),
    ("Qu'est-ce que la responsabilité du fait des choses ?", "droit_civil", {"1242"}),
    ("Qu'est-ce que le dol ?", "droit_civil", {"1137"}),
    ("Quel est le principe de la force obligatoire du contrat ?", "droit_civil", {"1103", "1193"}),
    ("Comment se forme le contrat ?", "droit_civil", {"1113"}),
    ("Qu'est-ce que la hiérarchie des normes ?", "droit_constitutionnel", {"55", "61", "62"}),
    ("Qui peut saisir le Conseil constitutionnel avant la promulgation d'une loi ?", "droit_constitutionnel", {"61"}),
]


def main() -> int:
    s = get_settings()
    retriever = LocalRetriever(s.index_dir, embed_model=s.embed_model)
    emb = embedders.creer(s.embed_provider, s.embed_model, s.gemini_api_key) if s.embed_provider else None
    configs = {
        "base": (None, None),
        "reclassement": (None, _construire_reclasseur(s)),
        "reformulation": (_construire_expanseur(s), None),
        "les deux": (_construire_expanseur(s), _construire_reclasseur(s)),
    }
    for nom, (exp, rec) in configs.items():
        if (nom != "base" and nom != "reformulation" and rec is None) or (nom in ("reformulation", "les deux") and exp is None):
            print(f"{nom}: non configure, ignore")
            continue
        lexia = Lexia(retriever, llm=None, embedder=emb, expanseur=exp, reclasseur=rec)
        trouves, durees, details = 0, [], []
        for q, matiere, attendus in CAS:
            t = time.monotonic()
            passages, _ = lexia.rechercher(q, matiere, K_CHAT)
            durees.append(time.monotonic() - t)
            nums = [p.get("numero") for p in passages if p["source_id"] in ("code_civil", "constitution_1958")]
            ok = bool(attendus & set(nums))
            trouves += ok
            details.append("ok" if ok else "KO")
        print(f"{nom:14s} {trouves}/{len(CAS)} trouvés  temps moyen {sum(durees) / len(durees):.1f} s  max {max(durees):.1f} s  {details}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
