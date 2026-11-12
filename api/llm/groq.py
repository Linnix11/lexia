"""Client Groq (API compatible OpenAI), utilise en secours quand tous les modeles Gemini echouent.

- Sortie JSON demandee par schema (response_format json_schema, mode « best effort » : nos schemas
  n'imposent pas additionalProperties=false). Le JSON est ensuite valide comme celui de Gemini.
- Une seule tentative : le secours ne doit pas allonger une reponse deja retardee.
- La cle ne quitte jamais le serveur et n'est jamais journalisee.
"""

from __future__ import annotations

import json
import logging
import time

import httpx

from api.llm.base import LLMError

log = logging.getLogger("lexia.llm")
URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqLLM:
    def __init__(self, *, api_key: str, model: str, timeout: float = 30.0):
        if not api_key or not model:
            raise ValueError("GROQ_API_KEY et GROQ_MODEL sont requis")
        self.model = model
        self._timeout = timeout
        self._client = httpx.Client(headers={"Authorization": f"Bearer {api_key}"})

    def generate_json(self, *, system, prompt, schema, temperature=0.2):
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system + "\nRéponds uniquement en JSON."},
                         {"role": "user", "content": prompt}],
            "temperature": temperature,
            "response_format": {"type": "json_schema", "json_schema": {"name": "reponse", "schema": schema}},
        }
        debut = time.monotonic()
        try:
            r = self._client.post(URL, json=body, timeout=self._timeout)
        except httpx.TimeoutException:
            raise LLMError(f"groq {self.model}: delai depasse") from None
        except httpx.HTTPError as e:
            raise LLMError(f"groq {self.model}: {type(e).__name__}") from None
        if r.status_code != 200:
            log.warning("groq %s HTTP %s en %.1fs", self.model, r.status_code, time.monotonic() - debut)
            raise LLMError(f"groq {self.model}: HTTP {r.status_code}")
        try:
            texte = r.json()["choices"][0]["message"]["content"]
            brut = json.loads(texte)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
            raise LLMError(f"groq {self.model}: reponse illisible ({type(e).__name__})") from None
        if not isinstance(brut, dict):
            raise LLMError(f"groq {self.model}: JSON inattendu")
        return brut, f"groq/{self.model}"
