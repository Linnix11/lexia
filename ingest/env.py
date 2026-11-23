"""Chargement minimal d'un fichier .env (sans dependance externe)."""

from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

FUSEAU = ZoneInfo("Europe/Paris")


def aujourdhui_paris() -> date:
    """Date du jour a Paris, quel que soit le fuseau de la machine : un VPS en UTC passait au 1er janvier une
    heure apres la France, et l'etat « en vigueur » des articles avec lui (audit du 2026-11-23, C4)."""
    return datetime.now(FUSEAU).date()


def load_env(path: Path) -> None:
    """Ajoute les variables du fichier a os.environ sans ecraser celles deja definies."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip('"').strip("'")
        if value:
            os.environ.setdefault(key.strip(), value)
