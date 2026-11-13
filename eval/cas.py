"""Chargement du jeu d'evaluation et resolution des sources attendues."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FICHIER = ROOT / "eval" / "cas.yaml"
# Textes hors codes cites directement par leur identifiant de source
AUTRES_TEXTES = ("ddhc_1789", "preambule_1946", "livre_procedures_fiscales")


@dataclass
class Cas:
    id: str
    question: str
    attendu: list[str]
    matiere: str | None = None
    mode: str = "expliquer"
    sources: list[str] = field(default_factory=list)
    piege: str | None = None


def charger(fichier: Path = FICHIER) -> list[Cas]:
    brut = yaml.safe_load(fichier.read_text(encoding="utf-8"))["cas"]
    cas = [Cas(**{k: v for k, v in c.items()}) for c in brut]
    ids = [c.id for c in cas]
    doublons = {i for i in ids if ids.count(i) > 1}
    if doublons:
        raise ValueError(f"Identifiants en double : {sorted(doublons)}")
    for c in cas:
        if not set(c.attendu) <= {"reponse", "abstention", "hors_champ"}:
            raise ValueError(f"{c.id} : attendu invalide {c.attendu}")
    return cas


def resoudre(ref: str, con: sqlite3.Connection) -> list[dict]:
    """'code_civil:1240' -> passages en vigueur correspondants (via l'index local)."""
    genre, _, valeur = ref.partition(":")
    if genre == "code_civil":
        sql, params = ("SELECT data FROM passages WHERE source_id = 'code_civil' AND numero = ? AND en_vigueur = 1",
                       (valeur,))
    elif genre == "constitution":
        sql, params = ("SELECT data FROM passages WHERE source_id = 'constitution_1958' AND numero = ?", (valeur,))
    elif genre == "cc":
        num, nature = valeur.split()
        sql, params = ("SELECT data FROM passages WHERE source_id = 'decisions_conseil_constitutionnel'"
                       " AND json_extract(data, '$.meta.numero') = ? AND json_extract(data, '$.meta.nature') = ?",
                       (num, nature))
    elif genre.startswith("code_") or genre in AUTRES_TEXTES:  # code_penal:122-5, ddhc_1789:11...
        sql, params = ("SELECT data FROM passages WHERE source_id = ? AND numero = ? AND en_vigueur = 1", (genre, valeur))
    else:
        raise ValueError(f"Type de source inconnu : {ref}")
    return [json.loads(r[0]) for r in con.execute(sql, params).fetchall()]


def correspond(ref: str, passage: dict) -> bool:
    """Le passage (fourni ou cite) correspond-il a la source attendue ?"""
    genre, _, valeur = ref.partition(":")
    if genre.startswith("code_") or genre in AUTRES_TEXTES:
        return passage["source_id"] == genre and passage.get("numero") == valeur
    if genre == "constitution":
        return passage["source_id"] == "constitution_1958" and passage.get("numero") == valeur
    if genre == "cc":
        num, nature = valeur.split()
        meta = passage.get("meta") or {}
        return passage["source_id"] == "decisions_conseil_constitutionnel" and meta.get("numero") == num \
            and meta.get("nature") == nature
    return False
