"""Chargement minimal d'un fichier .env (sans dependance externe)."""

from __future__ import annotations

import os
from pathlib import Path


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
