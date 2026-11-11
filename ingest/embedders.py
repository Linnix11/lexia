"""Fournisseurs d'embeddings, partages par l'ingestion et l'API.

- "local"  : modele open source execute sur la machine (sentence-transformers).
             Par defaut intfloat/multilingual-e5-base (licence MIT, 768 dimensions, francais).
             Aucun quota, aucune donnee envoyee a un tiers.
- "gemini" : API Gemini (quota gratuit de 1 000 embeddings par jour).

Configuration : EMBED_PROVIDER, EMBED_MODEL (et GEMINI_API_KEY pour "gemini").
Les vecteurs de modeles differents ne sont jamais melanges : le nom du modele est stocke
avec chaque vecteur et sert de filtre partout.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Protocol

import httpx

log = logging.getLogger("lexia.embeddings")

DIM = 768
DEFAUT_LOCAL = "intfloat/multilingual-e5-base"
GEMINI_API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents"


class Embedder(Protocol):
    model: str
    dim: int

    def embed_documents(self, textes: list[str]) -> list[list[float]]: ...

    def embed_query(self, texte: str) -> list[float] | None: ...


class LocalEmbedder:
    """Modele sentence-transformers charge en memoire (GPU Apple / CUDA si disponible, sinon CPU)."""

    def __init__(self, model: str = DEFAUT_LOCAL, batch_size: int = 32):
        from sentence_transformers import SentenceTransformer  # import lourd : seulement si utilise

        self.model = model
        self._st = SentenceTransformer(model)
        self.dim = self._st.get_embedding_dimension()
        self._batch = batch_size
        # Les modeles E5 attendent ces prefixes (cf. fiche du modele).
        e5 = "e5" in model.lower()
        self._p_doc, self._p_query = ("passage: ", "query: ") if e5 else ("", "")

    def embed_documents(self, textes):
        vecs = self._st.encode([self._p_doc + t for t in textes], batch_size=self._batch,
                               normalize_embeddings=True, show_progress_bar=False)
        return vecs.tolist()

    def embed_query(self, texte):
        return self._st.encode([self._p_query + texte], normalize_embeddings=True)[0].tolist()


class GeminiEmbedder:
    MAX_DELAY = 600

    def __init__(self, model: str, api_key: str, dim: int = DIM):
        if not api_key:
            raise ValueError("GEMINI_API_KEY requis pour EMBED_PROVIDER=gemini")
        self.model, self.dim = model, dim
        self._client = httpx.Client(headers={"x-goog-api-key": api_key})

    def _body(self, textes: list[str], task: str) -> dict:
        return {"requests": [{"model": f"models/{self.model}", "content": {"parts": [{"text": t}]},
                              "taskType": task, "outputDimensionality": self.dim} for t in textes]}

    def _quota(self, resp: httpx.Response, attempt: int) -> tuple[float, str]:
        delay, quota = min(60 * 2**attempt, self.MAX_DELAY), "?"
        try:
            for d in resp.json()["error"].get("details", []):
                if "retryDelay" in d:
                    delay = min(float(d["retryDelay"].rstrip("s")) + 1, self.MAX_DELAY)
                for v in d.get("violations", []):
                    quota = f"{v.get('quotaId')}={v.get('quotaValue')}"
        except Exception:
            pass
        return delay, quota

    def embed_documents(self, textes):
        out: list[list[float]] = []
        for i in range(0, len(textes), 100):  # maximum accepte par batchEmbedContents
            body = self._body(textes[i:i + 100], "RETRIEVAL_DOCUMENT")
            attempt = 0
            while True:
                r = self._client.post(GEMINI_API.format(model=self.model), json=body, timeout=120)
                if r.status_code == 200:
                    out.extend(e["values"] for e in r.json()["embeddings"])
                    break
                if r.status_code not in (429, 500, 503):
                    raise RuntimeError(f"Erreur API {r.status_code} : {r.text[:300]}")
                delay, quota = self._quota(r, attempt)
                print(f"  HTTP {r.status_code} ({quota}), nouvelle tentative dans {delay:.0f} s", flush=True)
                time.sleep(delay)
                attempt = min(attempt + 1, 4)
        return out

    def embed_query(self, texte):
        try:
            r = self._client.post(GEMINI_API.format(model=self.model), json=self._body([texte], "RETRIEVAL_QUERY"),
                                  timeout=10)
            if r.status_code == 200:
                return r.json()["embeddings"][0]["values"]
            log.info("embedding de la question indisponible (HTTP %s)", r.status_code)
        except httpx.HTTPError as e:
            log.info("embedding de la question indisponible (%s)", type(e).__name__)
        return None


def config_env() -> tuple[str, str]:
    """(fournisseur, modele) depuis l'environnement."""
    provider = os.environ.get("EMBED_PROVIDER", "local")
    defaut = DEFAUT_LOCAL if provider == "local" else os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-2")
    return provider, os.environ.get("EMBED_MODEL") or defaut


def creer(provider: str, model: str, api_key: str = "") -> Embedder:
    if provider == "local":
        return LocalEmbedder(model)
    if provider == "gemini":
        return GeminiEmbedder(model, api_key)
    raise ValueError(f"EMBED_PROVIDER inconnu : {provider} (local ou gemini)")
