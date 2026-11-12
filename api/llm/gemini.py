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
    def __init__(self, *, api_key: str, models: tuple[str, ...], thinking_level: str = "low", timeout: float = 30.0,
                 tentatives: int = 2):
        if not api_key or not models:
            raise ValueError("GEMINI_API_KEY et GEMINI_MODEL sont requis")
        self._models = models
        self._thinking = thinking_level
        self._timeout = timeout
        self._tentatives = tentatives
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
        """Essaie chaque modele une fois, puis refait un tour s'ils ont tous echoue.

        Un modele surcharge (503) ou a court de quota (429) l'est souvent encore une seconde plus tard :
        on passe tout de suite au modele suivant plutot que de le reessayer (niveau gratuit : 503 frequents).
        """
        body = self._body(system, prompt, schema, temperature)
        erreurs: list[str] = []
        exclus: set[str] = set()  # delai depasse ou requete refusee (400, 404...) : pas de second tour
        for tour in range(self._tentatives):
            if tour:
                time.sleep(1.0)
            for model in self._models:
                if model in exclus:
                    continue
                debut = time.monotonic()
                try:
                    r = self._client.post(f"{BASE}/{model}:generateContent", json=body, timeout=self._timeout)
                except httpx.TimeoutException:
                    erreurs.append(f"{model}: delai depasse")
                    exclus.add(model)  # deja 30 s perdues : pas de second essai
                    continue
                except httpx.HTTPError as e:
                    erreurs.append(f"{model}: {type(e).__name__}")
                    continue
                if r.status_code == 200:
                    try:
                        return json.loads(self._texte(r.json())), model
                    except (json.JSONDecodeError, LLMError) as e:
                        erreurs.append(f"{model}: {e}")
                        continue
                erreurs.append(f"{model}: HTTP {r.status_code}")
                log.warning("gemini %s HTTP %s en %.1fs", model, r.status_code, time.monotonic() - debut)
                if r.status_code not in RETRY_STATUS:
                    exclus.add(model)
        raise LLMError("; ".join(erreurs) or "aucun modele configure")
