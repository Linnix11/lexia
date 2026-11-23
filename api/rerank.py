"""Reclassement des candidats par un modele cross-encoder (open source, execute localement).

Par defaut : antoinelouis/crossencoder-camembert-base-mmarcoFR (licence MIT, entraine en francais).
Retenu apres comparaison sur des questions de cours (voir docs/decisions.md, D27) : meilleur
compromis gain / vitesse face a mMiniLM et bge-reranker-v2-m3. Reglage (D47) : 10 candidats par groupe,
256 jetons, soit ~4 s par question sur le VPS (2 processeurs) au lieu de ~21 s avec 30 candidats / 512 jetons.
Mesure des reglages (8 candidats, jetons, int8) : eval/reclassement.py, D122.
Configuration : RERANK_MODEL (vide = desactive).
"""

from __future__ import annotations

import logging
import threading

from api.retrieval.base import Hit

log = logging.getLogger("lexia")

MAX_CHARS = 800  # avec max_length=256 : au-dela, le texte serait tronque par le modele (D47)
# Deux reclassements a la fois au plus (audit du 19/11, SRV-7 ; D114) : le VPS n'a que 2 processeurs et chaque
# reclassement les occupe deja ; 10 questions simultanees se partageaient le calcul et finissaient toutes
# ensemble, pres de la coupure de Cloudflare (100 s). Au-dela, les questions attendent leur tour.
RECLASSEMENTS_SIMULTANES = 2
_PLACES = threading.BoundedSemaphore(RECLASSEMENTS_SIMULTANES)
# Attente d'une place bornee (audit du 23/11, A3) : 20 questions d'un TD ensemble attendaient jusqu'a ~40 s avant
# la generation, au-dela des 100 s de Cloudflare une fois Gemini et Groq passes. Au-dela, ordre de la fusion garde.
ATTENTE_MAX = 10.0


class CrossEncoderReclasseur:
    def __init__(self, model: str, max_length: int = 256, device: str | None = None):
        """device : None = choix de sentence-transformers (processeur sur le VPS) ; « cpu » pour mesurer sur un Mac,
        ou le GPU (MPS) serait pris (eval/reclassement.py)."""
        from sentence_transformers import CrossEncoder  # import lourd : seulement si active

        self.model = model
        self._ce = CrossEncoder(model, max_length=max_length, device=device)

    def reordonner(self, question: str, hits: list[Hit]) -> list[Hit]:
        if not hits:
            return hits
        paires = [(question, (h.passage.get("entete", "") + "\n" + h.passage["texte"])[:MAX_CHARS]) for h in hits]
        if not _PLACES.acquire(timeout=ATTENTE_MAX):
            log.info("reclassement : aucune place en %.0f s, ordre de la fusion garde", ATTENTE_MAX)
            return hits
        try:
            scores = self._ce.predict(paires, show_progress_bar=False)
        finally:
            _PLACES.release()
        out = []
        for h, sc in sorted(zip(hits, scores), key=lambda x: -float(x[1])):
            out.append(Hit(h.passage, float(sc), h.via | {"reclasse"}))
        return out
