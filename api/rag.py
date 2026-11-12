"""Pipeline de reponse : recherche -> extraits -> generation JSON -> validation des citations."""

from __future__ import annotations

import time
import uuid

from api import prompts
from api.citations import valider_reponse
from api.journal import Journal
from api.llm.base import LLM
from api.matieres import sources_pour
from api.matieres import sources_par_matiere
from api.retrieval.base import SEUIL_COUVERTURE, Retriever, groupes
from api.textes import SOURCES_TEXTES

AVERTISSEMENT = (
    "Lexia est un outil d'étude, pas un avis juridique. Vérifiez toujours les sources citées, "
    "en particulier la version en vigueur des textes."
)
K_CHAT = 8


def table_extraits(passages: list[dict]) -> dict[str, dict]:
    return {f"S{i}": p for i, p in enumerate(passages, start=1)}


def fiche_source(p: dict, label: str | None = None) -> dict:
    meta = p.get("meta") or {}
    en_vigueur = meta.get("en_vigueur", True if p["source_id"] == "constitution_1958" else None)
    return {
        "id": p["id"],
        "label": label,
        "source_id": p["source_id"],
        "type": p["type"],
        "numero": p.get("numero"),
        "entete": p.get("entete") or p.get("titre"),
        "url": p["url"],
        "version": p.get("version", ""),
        "en_vigueur": en_vigueur,
        "date": meta.get("date") or meta.get("date_debut"),
        "extrait": p["texte"][:400] + ("…" if len(p["texte"]) > 400 else ""),
    }


def sources_citees(reponse: dict, table: dict[str, dict]) -> list[dict]:
    """Fiches des passages effectivement cites, dans l'ordre de premiere citation."""
    par_id = {p["id"]: (label, p) for label, p in table.items()}
    ordre: list[str] = []
    for cle in ("droit_positif", "explication", "points_incertains"):
        for it in reponse.get(cle, []):
            for pid in it["sources"]:
                if pid not in ordre:
                    ordre.append(pid)
    return [fiche_source(par_id[pid][1], par_id[pid][0]) for pid in ordre if pid in par_id]


class Lexia:
    def __init__(self, retriever: Retriever, llm: LLM, journal: Journal | None = None, embedder=None,
                 expanseur=None, reclasseur=None):
        self.retriever = retriever
        self.llm = llm
        self.journal = journal or Journal(None)
        self.embedder = embedder      # None : recherche lexicale seule
        self.expanseur = expanseur    # None : pas de reformulation de la question
        self.reclasseur = reclasseur  # None : pas de reclassement

    def rechercher(self, texte: str, matiere: str | None, k: int) -> tuple[list[dict], dict]:
        """Renvoie les passages et un resume de la recherche (pour le controle et les journaux)."""
        sources = sources_pour(matiere)
        toutes = tuple(sorted({s for ids in sources_par_matiere().values() for s in ids}))
        textes, juris = groupes(sources, toutes)
        vectoriel = self.embedder is not None and any(
            g and self.retriever.couverture(g) >= SEUIL_COUVERTURE for g in (textes, juris))
        complement = self.expanseur.etendre(texte) if self.expanseur is not None else None
        vecteur = self.embedder.embed_query(texte) if vectoriel else None
        if complement and complement.reformulation and vectoriel:
            complement.vecteur_reformulation = self.embedder.embed_query(complement.reformulation)
        hits = self.retriever.search(texte, sources=sources, k=k, query_vector=vecteur,
                                     complement=complement, reclasseur=self.reclasseur)
        infos = {
            "recherche": "hybride" if any("vecteur" in h.via for h in hits) else "lexicale",
            "reformulation": complement is not None,
            "reclassement": self.reclasseur is not None,
            "suggestions_retenues": sum(1 for h in hits if "suggestion" in h.via),
        }
        return [h.passage for h in hits], infos

    def chat(self, question: str, mode: str, matiere: str | None) -> dict:
        debut = time.monotonic()
        reponse_id = str(uuid.uuid4())
        passages, infos = self.rechercher(question, matiere, K_CHAT)
        recherche = infos["recherche"]
        table = table_extraits(passages)
        modele = None
        if not passages:
            reponse, controle = valider_reponse({"statut": "abstention"}, table)
        else:
            brut, modele = self.llm.generate_json(
                system=prompts.SYSTEME,
                prompt=prompts.prompt_chat(question, mode, passages),
                schema=prompts.SCHEMA_REPONSE,
            )
            reponse, controle = valider_reponse(brut, table, mode)
        sources = sources_citees(reponse, table)
        self.journal.ecrire(
            "requetes", route="chat", reponse_id=reponse_id, mode=mode, matiere=matiere,
            statut=reponse["statut"], recherche=recherche, modele=modele,
            passages_fournis=[p["id"] for p in passages], passages_cites=[s["id"] for s in sources],
            controle=controle.as_dict(), recherche_detail=infos, duree_ms=int((time.monotonic() - debut) * 1000),
        )
        return {
            "reponse_id": reponse_id,
            **reponse,
            "sources": sources,
            "avertissement": AVERTISSEMENT,
            "controle": {**controle.as_dict(), **infos, "passages_consultes": len(passages)},
        }

    # --- verification de vigueur ----------------------------------------------

    def vigueur(self, passage_id: str) -> dict | None:
        p = self.retriever.get(passage_id)
        if p is None:
            return None
        meta = p.get("meta") or {}
        base = {"id": p["id"], "source_id": p["source_id"], "version": p.get("version", ""), "url": p["url"]}
        if p["source_id"] in SOURCES_TEXTES and p["source_id"] != "constitution_1958":
            en_vigueur = bool(meta.get("en_vigueur"))
            actuelle = None
            if not en_vigueur:
                texte = meta.get("id_texte")
                for v in self.retriever.versions(p["source_id"], p.get("numero") or ""):
                    vm = v.get("meta") or {}
                    # « article 14 » existe dans des centaines de lois : rester dans le meme texte.
                    if texte and vm.get("id_texte") and vm["id_texte"] != texte:
                        continue
                    if vm.get("en_vigueur"):
                        actuelle = {"id": v["id"], "version": v["version"], "url": v["url"]}
                        break
            message = ("Cette version est en vigueur selon la dernière synchronisation."
                       if en_vigueur else
                       "Cette version n'est plus en vigueur." + (" Une version en vigueur existe." if actuelle else
                                                                " Aucune version en vigueur de cet article n'a été trouvée (abrogé ou transféré)."))
            return {**base, "applicable": True, "en_vigueur": en_vigueur, "version_en_vigueur": actuelle,
                    "message": message + " Confirmez sur Légifrance avant de vous y fier."}
        if p["source_id"] == "constitution_1958":
            return {**base, "applicable": True, "en_vigueur": True, "version_en_vigueur": None,
                    "message": "Texte en vigueur selon la dernière synchronisation. Confirmez sur le site du Conseil constitutionnel."}
        return {**base, "applicable": False, "en_vigueur": None, "version_en_vigueur": None,
                "message": ("Une décision de justice n'a pas de version en vigueur. Vérifiez sa portée actuelle : "
                            "revirement de jurisprudence, réforme des textes appliqués.")}

