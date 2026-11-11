"""Interface du modele de langage : permet de changer de fournisseur sans toucher au reste."""

from __future__ import annotations

from typing import Protocol


class LLMError(RuntimeError):
    """Le modele n'a pas pu produire de reponse exploitable (quota, indisponibilite, JSON invalide)."""


class LLM(Protocol):
    def generate_json(self, *, system: str, prompt: str, schema: dict, temperature: float = 0.2) -> tuple[dict, str]:
        """Renvoie (objet JSON conforme au schema, nom du modele utilise)."""
        ...
