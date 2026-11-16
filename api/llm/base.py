"""Interface du modele de langage : permet de changer de fournisseur sans toucher au reste."""

from __future__ import annotations

from typing import Protocol


class LLMError(RuntimeError):
    """Le modele n'a pas pu produire de reponse exploitable (quota, indisponibilite, JSON invalide)."""


class ContenuRefuse(LLMError):
    """Le modele a bloque la question elle-meme (filtre de securite) : ce n'est pas une panne.

    Compter ces refus comme des pannes laissait n'importe qui ouvrir le disjoncteur avec trois questions
    bloquees d'affilee et basculer tout le site sur le secours (second audit du 2026-11-16, point 11).
    """


class LLM(Protocol):
    def generate_json(self, *, system: str, prompt: str, schema: dict, temperature: float = 0.2) -> tuple[dict, str]:
        """Renvoie (objet JSON conforme au schema, nom du modele utilise)."""
        ...
