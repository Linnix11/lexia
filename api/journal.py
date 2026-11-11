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

    def lire(self, fichier: str, max_lignes: int = 20000) -> list[dict]:
        """Dernieres lignes d'un journal (les plus recentes a la fin)."""
        if self._dossier is None:
            return []
        chemin = self._dossier / f"{fichier}.jsonl"
        if not chemin.exists():
            return []
        from collections import deque

        with self._lock, chemin.open(encoding="utf-8") as f:
            lignes = deque(f, maxlen=max_lignes)
        out = []
        for line in lignes:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out
