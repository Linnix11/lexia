"""Client Gemini (API Gemini Developer) via HTTP.

- Sortie JSON imposee par schema (generationConfig.responseJsonSchema).
- Modele principal puis modeles de secours en cas de 429 / 503 / delai depasse.
- La cle ne quitte jamais le serveur et n'est jamais journalisee.
"""

from __future__ import annotations

import json
import logging
import time

import httpx

from api.llm.base import LLMError

log = logging.getLogger("lexia.llm")
BASE = "https://generativelanguage.googleapis.com/v1beta/models"
RETRY_STATUS = {429, 500, 503}


class GeminiLLM:
    def __init__(self, *, api_key: str, models: tuple[str, ...], embed_model: str = "",
                 thinking_level: str = "low", timeout: float = 45.0, embed_dim: int = 768):
        if not api_key or not models:
            raise ValueError("GEMINI_API_KEY et GEMINI_MODEL sont requis")
        self._models = models
        self._embed_model = embed_model
        self._thinking = thinking_level
        self._timeout = timeout
        self._embed_dim = embed_dim
        self._client = httpx.Client(headers={"x-goog-api-key": api_key})

    # --- generation ----------------------------------------------------------

    def _body(self, system: str, prompt: str, schema: dict, temperature: float) -> dict:
        config: dict = {
            "responseMimeType": "application/json",
            "responseJsonSchema": schema,
            "temperature": temperature,
        }
        if self._thinking:
            config["thinkingConfig"] = {"thinkingLevel": self._thinking}
        return {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": config,
        }

    @staticmethod
    def _texte(reponse: dict) -> str:
        cands = reponse.get("candidates") or []
        if not cands:
            raise LLMError(f"Aucune reponse (blocage : {reponse.get('promptFeedback', {}).get('blockReason')})")
        parts = [p for p in cands[0].get("content", {}).get("parts", []) if not p.get("thought")]
        texte = "".join(p.get("text", "") for p in parts)
        if not texte:
            raise LLMError(f"Reponse vide (fin : {cands[0].get('finishReason')})")
        return texte

    def generate_json(self, *, system, prompt, schema, temperature=0.2):
        body = self._body(system, prompt, schema, temperature)
        erreurs: list[str] = []
        for model in self._models:
            for tentative in range(2):
                debut = time.monotonic()
                try:
                    r = self._client.post(f"{BASE}/{model}:generateContent", json=body, timeout=self._timeout)
                except httpx.TimeoutException:
                    erreurs.append(f"{model}: delai depasse")
                    break  # inutile de reessayer le meme modele : on passe au suivant
                except httpx.HTTPError as e:
                    erreurs.append(f"{model}: {type(e).__name__}")
                    break
                duree = time.monotonic() - debut
                if r.status_code == 200:
                    try:
                        return json.loads(self._texte(r.json())), model
                    except (json.JSONDecodeError, LLMError) as e:
                        erreurs.append(f"{model}: {e}")
                        continue
                erreurs.append(f"{model}: HTTP {r.status_code}")
                log.warning("gemini %s HTTP %s en %.1fs", model, r.status_code, duree)
                if r.status_code not in RETRY_STATUS:
                    break
                time.sleep(1.5 * (tentative + 1))
        raise LLMError("; ".join(erreurs) or "aucun modele configure")

    # --- embeddings ----------------------------------------------------------

    def embed_query(self, text):
        if not self._embed_model:
            return None
        body = {"requests": [{
            "model": f"models/{self._embed_model}",
            "content": {"parts": [{"text": text}]},
            "taskType": "RETRIEVAL_QUERY",
            "outputDimensionality": self._embed_dim,
        }]}
        try:
            r = self._client.post(f"{BASE}/{self._embed_model}:batchEmbedContents", json=body, timeout=10)
            if r.status_code == 200:
                return r.json()["embeddings"][0]["values"]
            log.info("embedding de la question indisponible (HTTP %s), recherche lexicale seule", r.status_code)
        except httpx.HTTPError as e:
            log.info("embedding de la question indisponible (%s)", type(e).__name__)
        return None
