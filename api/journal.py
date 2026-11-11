"""Journalisation en JSONL : identifiants et metriques uniquement, jamais le texte des questions."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path


class Journal:
    def __init__(self, dossier: Path | None):
        self._dossier = dossier
        self._lock = threading.Lock()
        if dossier is not None:
            dossier.mkdir(parents=True, exist_ok=True)

    def ecrire(self, fichier: str, **champs) -> None:
        if self._dossier is None:
            return
        ligne = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **champs}
        with self._lock, (self._dossier / f"{fichier}.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
