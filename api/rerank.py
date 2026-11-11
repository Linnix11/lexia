"""Reclassement des candidats par un modele cross-encoder (open source, execute localement).

Par defaut : antoinelouis/crossencoder-camembert-base-mmarcoFR (licence MIT, entraine en francais).
Retenu apres comparaison sur des questions de cours (voir docs/decisions.md, D27) : meilleur
compromis gain / vitesse (~0,9 s pour 30 candidats sur Mac M3) face a mMiniLM et bge-reranker-v2-m3.
Configuration : RERANK_MODEL (vide = desactive).
"""

from __future__ import annotations

from api.retrieval.base import Hit

MAX_CHARS = 1500


class CrossEncoderReclasseur:
    def __init__(self, model: str, max_length: int = 512):
        from sentence_transformers import CrossEncoder  # import lourd : seulement si active

        self.model = model
        self._ce = CrossEncoder(model, max_length=max_length)

    def reordonner(self, question: str, hits: list[Hit]) -> list[Hit]:
        if not hits:
            return hits
        paires = [(question, (h.passage.get("entete", "") + "\n" + h.passage["texte"])[:MAX_CHARS]) for h in hits]
        scores = self._ce.predict(paires, show_progress_bar=False)
        out = []
        for h, sc in sorted(zip(hits, scores), key=lambda x: -float(x[1])):
            out.append(Hit(h.passage, float(sc), h.via | {"reclasse"}))
        return out
