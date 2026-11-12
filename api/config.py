"""Configuration de l'API, lue dans l'environnement (et .env en developpement)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from ingest import embedders
from ingest.env import load_env

ROOT = Path(__file__).resolve().parent.parent


def _list(name: str, default: str = "") -> tuple[str, ...]:
    return tuple(x.strip() for x in os.environ.get(name, default).split(",") if x.strip())


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str = ""
    gemini_models: tuple[str, ...] = ()        # modele principal puis modeles de secours
    gemini_thinking_level: str = "low"
    embed_provider: str = ""                   # "local", "gemini" ou "" (pas de recherche vectorielle)
    embed_model: str = ""
    llm_timeout: float = 30.0
    index_dir: Path = ROOT / "data" / "index"
    logs_dir: Path = ROOT / "logs"
    max_question_chars: int = 2000
    rate_limit_per_minute: int = 10
    appels_modele_simultanes: int = 20         # questions / questionnaires traites en meme temps (sur 40 threads)
    cors_origins: tuple[str, ...] = field(default_factory=tuple)
    expansion_model: str = ""                  # vide = pas de reformulation de la question
    expansion_fallback_models: tuple[str, ...] = ()
    expansion_timeout: float = 8.0
    rerank_model: str = ""                     # vide = pas de reclassement
    groq_api_key: str = ""                     # vide = pas de modele de secours
    groq_model: str = "openai/gpt-oss-120b"
    # Avec un secours : un seul tour de modeles Gemini et ce temps total au plus avant de passer a Groq.
    # Assez long pour une reponse Gemini lente mais reussie (~25 s constatees), assez court pour ne pas
    # attendre six 503 d'affilee (74 s constatees).
    budget_avant_secours: float = 35.0
    # Disjoncteur : apres N echecs de Gemini d'affilee, Groq seul pendant cette pause (secondes)
    disjoncteur_seuil: int = 3
    disjoncteur_pause: float = 300.0
    comptes_actifs: bool = False               # comptes et quotas (actives par defaut hors tests)
    app_db: Path = ROOT / "donnees" / "lexia.db"
    contact_email: str = ""                    # adresse affichee pour demander une formule payante
    admin_emails: tuple[str, ...] = ()         # comptes administrateurs (ADMIN_EMAILS, separes par des virgules)
    # comptes crees par adresse IP sur 24 h (0 = sans limite) ; un campus derriere une seule IP compte pour une
    inscriptions_par_ip_jour: int = 20
    # Pages legales (mentions, CGU, confidentialite) : vide = affiche « a completer »
    legal: dict = field(default_factory=dict)


def get_settings() -> Settings:
    load_env(ROOT / ".env")
    principal = os.environ.get("GEMINI_MODEL", "")
    secours = _list("GEMINI_FALLBACK_MODELS")
    embed_provider, embed_model = embedders.config_env()
    return Settings(
        gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
        gemini_models=tuple(m for m in (principal, *secours) if m),
        gemini_thinking_level=os.environ.get("GEMINI_THINKING_LEVEL", "low"),
        embed_provider=embed_provider,
        embed_model=embed_model,
        llm_timeout=float(os.environ.get("LLM_TIMEOUT_SECONDS", "30")),
        max_question_chars=int(os.environ.get("MAX_QUESTION_CHARS", "2000")),
        rate_limit_per_minute=int(os.environ.get("RATE_LIMIT_PER_MINUTE", "10")),
        cors_origins=_list("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"),
        expansion_model=os.environ.get("QUERY_EXPANSION_MODEL", ""),
        expansion_fallback_models=_list("QUERY_EXPANSION_FALLBACK_MODELS"),
        expansion_timeout=float(os.environ.get("QUERY_EXPANSION_TIMEOUT", "8")),
        rerank_model=os.environ.get("RERANK_MODEL", ""),
        groq_api_key=os.environ.get("GROQ_API_KEY", ""),
        groq_model=os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
        budget_avant_secours=float(os.environ.get("BUDGET_AVANT_SECOURS_SECONDES", "35")),
        disjoncteur_seuil=int(os.environ.get("DISJONCTEUR_SEUIL", "3")),
        disjoncteur_pause=float(os.environ.get("DISJONCTEUR_PAUSE_SECONDES", "300")),
        comptes_actifs=os.environ.get("COMPTES_ACTIFS", "1") not in ("0", "false", "non"),
        app_db=Path(os.environ.get("APP_DB") or ROOT / "donnees" / "lexia.db"),
        contact_email=os.environ.get("CONTACT_EMAIL", ""),
        admin_emails=_list("ADMIN_EMAILS"),
        inscriptions_par_ip_jour=int(os.environ.get("INSCRIPTIONS_PAR_IP_JOUR", "20")),
        legal={
            "editeur": os.environ.get("LEGAL_EDITEUR", ""),
            "statut": os.environ.get("LEGAL_STATUT", ""),
            "adresse": os.environ.get("LEGAL_ADRESSE", ""),
            "siren": os.environ.get("LEGAL_SIREN", ""),
            "directeur": os.environ.get("LEGAL_DIRECTEUR", ""),
            "telephone": os.environ.get("LEGAL_TELEPHONE", ""),
            # LCEN art. 1-1, 4° : nom, adresse et telephone de l'hebergeur (Hostinger ne publie pas de numero)
            "hebergeur_telephone": os.environ.get("LEGAL_HEBERGEUR_TELEPHONE", ""),
            # ex. « TVA non applicable, art. 293 B du CGI » (micro-entreprise) ou « TVA incluse »
            "tva": os.environ.get("LEGAL_TVA", ""),
            "mediateur": os.environ.get("LEGAL_MEDIATEUR", ""),
            # 1 seulement si la cle Gemini est au niveau payant (obligatoire pour des utilisateurs dans l'EEE)
            "gemini_payant": os.environ.get("GEMINI_NIVEAU_PAYANT", "0") in ("1", "true", "oui"),
            # Groq en secours : la politique de confidentialite le mentionne comme destinataire
            "groq": bool(os.environ.get("GROQ_API_KEY")),
        },
    )
