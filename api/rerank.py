"""Reclassement des candidats par un modele cross-encoder (open source, execute localement).

Par defaut : antoinelouis/crossencoder-camembert-base-mmarcoFR (licence MIT, entraine en francais).
Retenu apres comparaison sur des questions de cours (voir docs/decisions.md, D27) : meilleur
compromis gain / vitesse face a mMiniLM et bge-reranker-v2-m3. Reglage (D47) : 10 candidats par groupe,
256 jetons, soit ~4 s par question sur le VPS (2 processeurs) au lieu de ~21 s avec 30 candidats / 512 jetons.
Configuration : RERANK_MODEL (vide = desactive).
"""

from __future__ import annotations

from api.retrieval.base import Hit

MAX_CHARS = 800  # avec max_length=256 : au-dela, le texte serait tronque par le modele (D47)


class CrossEncoderReclasseur:
    def __init__(self, model: str, max_length: int = 256):
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
