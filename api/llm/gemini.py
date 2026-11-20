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

from api.llm.base import ContenuRefuse, LLMError
from api.llm.forme import conforme

log = logging.getLogger("lexia.llm")
BASE = "https://generativelanguage.googleapis.com/v1beta/models"
# Fins de generation qui signalent un blocage du contenu, pas une panne du service.
FINS_REFUS = {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION"}
RETRY_STATUS = {429, 500, 503}
# Plafond de la reponse : la plus longue des 92 reponses relevees en production faisait 1 393 jetons
# (16 novembre 2026, logs/modele.jsonl). Sans plafond, une question piegee (« developpe 40 elements tres
# longs ») faisait ecrire le modele jusqu'au delai, a nos frais. Une reponse coupee est du JSON invalide :
# le modele suivant, puis le secours, prennent le relais.
MAX_JETONS_SORTIE = 4096


class GeminiLLM:
    def __init__(self, *, api_key: str, models: tuple[str, ...], thinking_level: str = "low", timeout: float = 30.0,
                 tentatives: int = 2, releve=None, budget: float | None = None,
                 max_jetons: int = MAX_JETONS_SORTIE):
        if not api_key or not models:
            raise ValueError("GEMINI_API_KEY et GEMINI_MODEL sont requis")
        self._models = models
        self._thinking = thinking_level
        self._timeout = timeout
        self._tentatives = tentatives
        self._releve = releve  # releve(modele, usageMetadata) apres chaque reponse : mesure du cout
        # Temps total accorde a Gemini (tous modeles confondus) ; None = sans limite. Avec un modele de secours,
        # mieux vaut lui passer la main vite que d'attendre une serie de 503 (jusqu'a 26 s chacun, constate).
        self._budget = budget
        self._max_jetons = max_jetons  # plus bas pour les resumes vocaux (api/resumes_vocaux.py)
        self._client = httpx.Client(headers={"x-goog-api-key": api_key})

    # --- generation ----------------------------------------------------------

    def _body(self, system: str, prompt: str, schema: dict, temperature: float) -> dict:
        config: dict = {
            "responseMimeType": "application/json",
            "responseJsonSchema": schema,
            "temperature": temperature,
            "maxOutputTokens": self._max_jetons,
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
            blocage = reponse.get("promptFeedback", {}).get("blockReason")
            raise (ContenuRefuse if blocage else LLMError)(f"Aucune reponse (blocage : {blocage})")
        parts = [p for p in cands[0].get("content", {}).get("parts", []) if not p.get("thought")]
        texte = "".join(p.get("text", "") for p in parts)
        if not texte:
            fin = cands[0].get("finishReason")
            raise (ContenuRefuse if fin in FINS_REFUS else LLMError)(f"Reponse vide (fin : {fin})")
        return texte

    def generate_json(self, *, system, prompt, schema, temperature=0.2):
        """Essaie chaque modele une fois, puis refait un tour s'ils ont tous echoue.

        Un modele surcharge (503) ou a court de quota (429) l'est souvent encore une seconde plus tard :
        on passe tout de suite au modele suivant plutot que de le reessayer (niveau gratuit : 503 frequents).
        """
        body = self._body(system, prompt, schema, temperature)
        erreurs: list[str] = []
        refus = 0  # modeles qui ont bloque la question (filtre de securite) plutot qu'echoue
        exclus: set[str] = set()  # delai depasse ou requete refusee (400, 404...) : pas de second tour
        fin = time.monotonic() + self._budget if self._budget else None
        for tour in range(self._tentatives):
            if tour:
                if fin is not None and time.monotonic() + 1.0 >= fin:
                    break
                time.sleep(1.0)
            for model in self._models:
                if model in exclus:
                    continue
                debut = time.monotonic()
                delai = self._timeout
                if fin is not None:
                    if debut >= fin:
                        erreurs.append(f"temps accorde a Gemini ({self._budget:.0f} s) ecoule")
                        raise LLMError("; ".join(erreurs))
                    delai = min(delai, fin - debut)
                try:
                    r = self._client.post(f"{BASE}/{model}:generateContent", json=body,
                                          timeout=httpx.Timeout(delai, connect=min(5.0, delai)))
                except httpx.TimeoutException:
                    erreurs.append(f"{model}: delai depasse")
                    exclus.add(model)  # deja 30 s perdues : pas de second essai
                    continue
                except httpx.HTTPError as e:
                    erreurs.append(f"{model}: {type(e).__name__}")
                    continue
                if r.status_code == 200:
                    try:
                        donnees = r.json()
                    except json.JSONDecodeError as e:
                        erreurs.append(f"{model}: {e}")
                        continue
                    # Releve avant la lecture du JSON : une reponse illisible est payee quand meme.
                    if self._releve is not None:
                        try:
                            self._releve(model, donnees.get("usageMetadata") or {})
                        except Exception:  # la mesure ne doit jamais faire echouer une reponse
                            log.exception("releve des jetons impossible")
                    try:
                        resultat = json.loads(self._texte(donnees))
                    except (json.JSONDecodeError, LLMError) as e:
                        erreurs.append(f"{model}: {e}")
                        if isinstance(e, ContenuRefuse):
                            refus += 1
                            exclus.add(model)  # la meme question serait bloquee au second tour
                        continue
                    if not conforme(resultat, schema):
                        erreurs.append(f"{model}: reponse hors du schema")
                        continue
                    return resultat, model
                erreurs.append(f"{model}: HTTP {r.status_code}")
                log.warning("gemini %s HTTP %s en %.1fs", model, r.status_code, time.monotonic() - debut)
                if r.status_code not in RETRY_STATUS:
                    exclus.add(model)
        if erreurs and refus == len(erreurs):
            raise ContenuRefuse("; ".join(erreurs))  # tous ont bloque la question : Gemini n'est pas en panne
        raise LLMError("; ".join(erreurs) or "aucun modele configure")
