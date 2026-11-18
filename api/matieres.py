"""Matieres : intitule, annee de licence, autres intitules des maquettes, sources (registry/sources.yaml)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import yaml

from api.config import ROOT

ANNEES = ("L1", "L2", "L3")


@dataclass(frozen=True)
class Matiere:
    libelle: str
    # Annee ou la matiere est le plus souvent enseignee, d'apres les maquettes de 8 facultes
    # (docs/plaquettes-licence.md, D97). Sert au classement du site, pas a la recherche.
    annee: str
    # Autres intitules des maquettes, pour retrouver la matiere dans le site (« procédure pénale »...).
    mots: tuple[str, ...] = ()
    # Sources montrees d'abord dans le site (les autres restent consultees par la recherche).
    principales: tuple[str, ...] = ()


MATIERES: dict[str, Matiere] = {
    "introduction_au_droit": Matiere("Introduction au droit", "L1", (
        "institutions juridictionnelles", "sources du droit", "méthodologie"), ("code_civil", "constitution_1958")),
    "droit_constitutionnel": Matiere("Droit constitutionnel", "L1", (
        "Ve République", "institutions politiques", "contentieux constitutionnel", "QPC"),
        ("constitution_1958", "decisions_conseil_constitutionnel")),
    "droit_civil": Matiere("Droit civil", "L1", (
        "droit des personnes", "droit privé", "responsabilité civile", "contrats spéciaux", "sûretés"),
        ("code_civil", "judilibre")),
    "droit_de_la_famille": Matiere("Droit de la famille", "L1", (
        "mariage", "divorce", "filiation", "autorité parentale", "régimes matrimoniaux", "successions",
        "libéralités", "droit patrimonial de la famille"), ("code_civil", "judilibre")),
    "droit_des_biens": Matiere("Droit des biens", "L1", ("propriété", "possession", "servitudes", "usufruit"),
                               ("code_civil", "judilibre")),
    "droit_des_contrats": Matiere("Droit des contrats", "L2", (
        "droit des obligations", "régime général de l'obligation", "contrats spéciaux", "droit de la consommation"),
        ("code_civil", "judilibre")),
    "droit_administratif": Matiere("Droit administratif", "L2", (
        "actes administratifs", "service public", "police administrative", "responsabilité administrative",
        "contrats administratifs"), ("code_relations_public_administration", "conseil_etat")),
    "droit_penal": Matiere("Droit pénal", "L2", (
        "droit pénal général", "droit pénal spécial", "infractions", "peines", "sciences criminelles"),
        ("code_penal", "cass_criminelle")),
    "droit_des_affaires": Matiere("Droit des affaires", "L2", (
        "droit commercial", "commerçant", "fonds de commerce", "concurrence", "consommation"),
        ("code_commerce", "cass_commerciale")),
    "finances_publiques": Matiere("Finances publiques", "L2", ("droit budgétaire", "lois de finances", "Cour des comptes"),
                                  ("constitution_1958", "code_juridictions_financieres")),
    "procedure_civile": Matiere("Procédure civile", "L3", ("droit judiciaire privé", "procès civil", "voies d'exécution"),
                                ("code_procedure_civile", "judilibre")),
    "procedure_penale": Matiere("Procédure pénale", "L3", (
        "procès pénal", "enquête", "garde à vue", "instruction", "action publique", "justice pénale des mineurs"),
        ("code_procedure_penale", "cass_criminelle")),
    "droit_social": Matiere("Droit social", "L3", (
        "droit du travail", "relations individuelles", "relations collectives", "sécurité sociale", "protection sociale"),
        ("code_travail", "cass_sociale")),
    "droit_des_societes": Matiere("Droit des sociétés", "L3", (
        "sociétés commerciales", "SARL", "SAS", "société anonyme", "groupements"), ("code_commerce", "code_civil")),
    "contentieux_administratif": Matiere("Contentieux administratif", "L3", (
        "juge administratif", "recours pour excès de pouvoir", "référés", "justice administrative"),
        ("code_justice_administrative", "conseil_etat")),
    "droit_administratif_des_biens": Matiere("Droit administratif des biens", "L3", (
        "domaine public", "propriétés publiques", "expropriation", "biens publics"),
        ("code_propriete_personnes_publiques", "code_expropriation")),
    "libertes_fondamentales": Matiere("Libertés fondamentales", "L3", ("droits fondamentaux", "droits de l'homme"),
                                      ("ddhc_1789", "decisions_conseil_constitutionnel")),
    "droit_fiscal": Matiere("Droit fiscal", "L3", ("impôts", "fiscalité", "contentieux fiscal"),
                            ("code_general_impots", "livre_procedures_fiscales")),
}
LIBELLES = {m: i.libelle for m, i in MATIERES.items()}


@lru_cache(maxsize=1)
def sources_par_matiere() -> dict[str, tuple[str, ...]]:
    """Matieres dans l'ordre de MATIERES (annee de licence, puis intitule courant)."""
    registre = yaml.safe_load((ROOT / "registry" / "sources.yaml").read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {m: [] for m in MATIERES}
    for s in registre["sources"]:
        if s.get("statut") != "actif" or s.get("type") == "bibliographie":
            continue
        for m in s.get("matieres") or []:
            out.setdefault(m, []).append(s["id"])
    return {m: tuple(ids) for m, ids in out.items() if ids}


def sources_pour(matiere: str | None) -> tuple[str, ...] | None:
    """None = toutes les sources."""
    if not matiere:
        return None
    try:
        return sources_par_matiere()[matiere]
    except KeyError:
        raise ValueError(f"Matière inconnue : {matiere}") from None
