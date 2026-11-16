"""Client Groq (API compatible OpenAI), utilise en secours quand tous les modeles Gemini echouent.

- Sortie JSON demandee par schema (response_format json_schema, mode « best effort » : nos schemas
  n'imposent pas additionalProperties=false). Le JSON est ensuite valide comme celui de Gemini.
- Une tentative par modele, dans l'ordre. Le modele suivant n'est essaye qu'apres un refus immediat
  (modele retire, quota du modele, JSON invalide) : jamais apres un delai depasse, pour ne pas doubler
  l'attente d'une reponse deja retardee.
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


class _Delai(LLMError):
    pass


class GroqLLM:
    def __init__(self, *, api_key: str, models: tuple[str, ...], timeout: float = 30.0):
        if not api_key or not models:
            raise ValueError("GROQ_API_KEY et GROQ_MODELS sont requis")
        self.models = tuple(models)
        self.model = self.models[0]
        self._timeout = timeout
        self._client = httpx.Client(headers={"Authorization": f"Bearer {api_key}"})

    def generate_json(self, *, system, prompt, schema, temperature=0.2):
        erreurs: list[str] = []
        for model in self.models:
            try:
                return self._appeler(model, system, prompt, schema, temperature)
            except _Delai as e:
                erreurs.append(str(e))
                break
            except LLMError as e:
                erreurs.append(str(e))
        raise LLMError("; ".join(erreurs))

    def _appeler(self, model, system, prompt, schema, temperature):
        body = {
            "model": model,
            "messages": [{"role": "system", "content": system + "\nRéponds uniquement en JSON."},
                         {"role": "user", "content": prompt}],
            "temperature": temperature,
            "response_format": {"type": "json_schema", "json_schema": {"name": "reponse", "schema": schema}},
        }
        debut = time.monotonic()
        try:
            r = self._client.post(URL, json=body, timeout=self._timeout)
        except httpx.TimeoutException:
            raise _Delai(f"groq {model}: delai depasse") from None
        except httpx.HTTPError as e:
            raise LLMError(f"groq {model}: {type(e).__name__}") from None
        if r.status_code != 200:
            log.warning("groq %s HTTP %s en %.1fs", model, r.status_code, time.monotonic() - debut)
            raise LLMError(f"groq {model}: HTTP {r.status_code}")
        try:
            texte = r.json()["choices"][0]["message"]["content"]
            brut = json.loads(texte)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as e:
            raise LLMError(f"groq {model}: reponse illisible ({type(e).__name__})") from None
        if not isinstance(brut, dict):
            raise LLMError(f"groq {model}: JSON inattendu")
        return brut, f"groq/{model}"
