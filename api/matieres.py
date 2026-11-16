"""Correspondance matiere -> sources, derivee du registre (registry/sources.yaml)."""

from __future__ import annotations

from functools import lru_cache

import yaml

from api.config import ROOT

LIBELLES = {
    "introduction_au_droit": "Introduction au droit",
    "droit_constitutionnel": "Droit constitutionnel",
    "droit_civil": "Droit civil",
    "droit_des_contrats": "Droit des contrats",
    "droit_penal": "Droit pénal",
    "procedure_civile": "Procédure civile",
    "droit_des_affaires": "Droit des affaires",
    "droit_social": "Droit social",
    "droit_administratif": "Droit administratif",
    "libertes_fondamentales": "Libertés fondamentales",
    "droit_de_la_famille": "Droit de la famille",
    "droit_des_biens": "Droit des biens",
    "droit_fiscal": "Droit fiscal",
    "finances_publiques": "Finances publiques",
}


@lru_cache(maxsize=1)
def sources_par_matiere() -> dict[str, tuple[str, ...]]:
    registre = yaml.safe_load((ROOT / "registry" / "sources.yaml").read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for s in registre["sources"]:
        if s.get("statut") != "actif" or s.get("type") == "bibliographie":
            continue
        for m in s.get("matieres") or []:
            out.setdefault(m, []).append(s["id"])
    return {m: tuple(ids) for m, ids in out.items()}


def sources_pour(matiere: str | None) -> tuple[str, ...] | None:
    """None = toutes les sources."""
    if not matiere:
        return None
    try:
        return sources_par_matiere()[matiere]
    except KeyError:
        raise ValueError(f"Matière inconnue : {matiere}") from None
