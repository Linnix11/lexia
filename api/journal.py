"""Journalisation en JSONL : identifiants et metriques uniquement, jamais le texte des questions.

Les lignes de plus de RETENTION_JOURS sont supprimees une fois par jour, au premier ecrit du jour,
sous le meme verrou que les ecritures : aucune ligne ne peut se perdre pendant la purge.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from collections import deque
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

RETENTION_JOURS = 365  # duree annoncee dans la politique de confidentialite


class Journal:
    def __init__(self, dossier: Path | None, retention_jours: int = RETENTION_JOURS):
        self._dossier = dossier
        self._retention = timedelta(days=retention_jours)
        self._derniere_purge: date | None = None
        self._lock = threading.Lock()
        if dossier is not None:
            dossier.mkdir(parents=True, exist_ok=True)

    def ecrire(self, fichier: str, **champs) -> None:
        if self._dossier is None:
            return
        ligne = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **champs}
        with self._lock:
            self._purger_si_nouveau_jour()
            with (self._dossier / f"{fichier}.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(ligne, ensure_ascii=False) + "\n")

    def lire(self, fichier: str, max_lignes: int = 20000) -> list[dict]:
        """Dernieres lignes d'un journal (les plus recentes a la fin)."""
        if self._dossier is None:
            return []
        chemin = self._dossier / f"{fichier}.jsonl"
        if not chemin.exists():
            return []
        with self._lock, chemin.open(encoding="utf-8") as f:
            lignes = deque(f, maxlen=max_lignes)
        out = []
        for line in lignes:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def _purger_si_nouveau_jour(self) -> None:
        """Appelee sous self._lock : les ecritures attendent la fin de la purge."""
        aujourd_hui = date.today()
        if self._derniere_purge == aujourd_hui:
            return
        self._derniere_purge = aujourd_hui
        limite = datetime.now(timezone.utc) - self._retention
        for chemin in self._dossier.glob("*.jsonl"):
            garde, retire = [], 0
            with chemin.open(encoding="utf-8") as f:
                for line in f:
                    try:
                        ancienne = datetime.fromisoformat(json.loads(line)["ts"]) < limite
                    except (ValueError, KeyError, TypeError):
                        ancienne = False  # ligne illisible : conservee
                    if ancienne:
                        retire += 1
                    else:
                        garde.append(line)
            if retire:
                mode = chemin.stat().st_mode
                fd, tmp = tempfile.mkstemp(dir=self._dossier)
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.writelines(garde)
                os.chmod(tmp, mode)
                os.replace(tmp, chemin)
