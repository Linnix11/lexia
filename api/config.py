"""Configuration de l'API, lue dans l'environnement (et .env en developpement)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from ingest.env import load_env

ROOT = Path(__file__).resolve().parent.parent


def _list(name: str, default: str = "") -> tuple[str, ...]:
    return tuple(x.strip() for x in os.environ.get(name, default).split(",") if x.strip())


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str = ""
    gemini_models: tuple[str, ...] = ()        # modele principal puis modeles de secours
    gemini_thinking_level: str = "low"
    gemini_embed_model: str = ""
    llm_timeout: float = 30.0
    retriever: str = "local"                   # "local" (SQLite + numpy) ou "postgres"
    database_url: str = ""
    index_dir: Path = ROOT / "data" / "index"
    logs_dir: Path = ROOT / "logs"
    max_question_chars: int = 2000
    rate_limit_per_minute: int = 10
    cors_origins: tuple[str, ...] = field(default_factory=tuple)


def get_settings() -> Settings:
    load_env(ROOT / ".env")
    principal = os.environ.get("GEMINI_MODEL", "")
    secours = _list("GEMINI_FALLBACK_MODELS")
    return Settings(
        gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
        gemini_models=tuple(m for m in (principal, *secours) if m),
        gemini_thinking_level=os.environ.get("GEMINI_THINKING_LEVEL", "low"),
        gemini_embed_model=os.environ.get("GEMINI_EMBED_MODEL", ""),
        llm_timeout=float(os.environ.get("LLM_TIMEOUT_SECONDS", "30")),
        retriever=os.environ.get("RETRIEVER", "local"),
        database_url=os.environ.get("DATABASE_URL", ""),
        max_question_chars=int(os.environ.get("MAX_QUESTION_CHARS", "2000")),
        rate_limit_per_minute=int(os.environ.get("RATE_LIMIT_PER_MINUTE", "10")),
        cors_origins=_list("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"),
    )
