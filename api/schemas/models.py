"""Modeles des requetes HTTP (validation des entrees)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Mode = Literal["expliquer", "fiche", "cas_pratique", "commentaire", "dissertation"]
FormatQuiz = Literal["qcm", "vrai_faux", "ouvertes"]
Niveau = Literal["L1", "L2", "L3"]


class ChatRequest(BaseModel):
    question: str = Field(min_length=3)
    mode: Mode = "expliquer"
    matiere: str | None = None
    niveau: Niveau = "L1"
    semestre: int | None = Field(default=None, ge=1, le=6)
    cours: list[int] = Field(default_factory=list, max_length=10)  # cours deposes a utiliser (api/cours.py)
    avec_officiel: bool = True  # False : « Mon cours uniquement »


class QuizRequest(BaseModel):
    theme: str = Field(min_length=3)
    format: FormatQuiz = "qcm"
    nombre: int = Field(default=5, ge=1, le=15)
    matiere: str | None = None
    niveau: Niveau = "L1"
    semestre: int | None = Field(default=None, ge=1, le=6)
    cours: list[int] = Field(default_factory=list, max_length=10)  # cours deposes a utiliser (api/cours.py)
    avec_officiel: bool = True  # False : « Mon cours uniquement »


class ReponseQuiz(BaseModel):
    index: int = Field(ge=0)
    valeur: int | bool | str | None = None


class CorrectionRequest(BaseModel):
    quiz_id: str
    reponses: list[ReponseQuiz] = Field(max_length=15)


class FeedbackRequest(BaseModel):
    reponse_id: str = Field(min_length=8, max_length=64)
    utile: bool
    # Pas de champ texte libre : on ne collecte aucune donnee personnelle en V1.
    motif: Literal["inexact", "source_incorrecte", "source_manquante", "incomplet", "hors_sujet", "autre"] | None = None
