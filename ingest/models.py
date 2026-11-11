"""Modele commun des passages indexes (1 passage = 1 article ou 1 motif)."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Passage:
    id: str                 # identifiant stable, ex. "constitution_1958:art:61-1"
    source_id: str          # renvoie a registry/sources.yaml
    type: str               # "article", "preambule", "motif"...
    numero: str | None      # "1", "61-1"... ; None pour le preambule
    titre: str | None       # titre / chapitre de rattachement
    alineas: list[str] = field(default_factory=list)
    url: str = ""           # lien direct vers la source officielle (avec ancre)
    version: str = ""       # mention de version telle que donnee par la source
    date_recuperation: str = ""  # ISO 8601
    # Metadonnees propres a la source : juridiction, date, numero, ECLI, etat de vigueur...
    meta: dict = field(default_factory=dict)
    # Ligne de contexte ajoutee devant le texte pour la recherche (ex. "Cons. const., 2023-1075 QPC, 2024-01-19")
    entete: str = ""

    @property
    def texte(self) -> str:
        return "\n\n".join(self.alineas)

    @property
    def texte_index(self) -> str:
        """Texte envoye au moteur de recherche et aux embeddings."""
        return f"{self.entete}\n\n{self.texte}" if self.entete else self.texte

    @property
    def empreinte(self) -> str:
        """Hash du contenu : permet de detecter un changement de texte entre deux synchros."""
        return hashlib.sha256(self.texte.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict:
        d = asdict(self)
        d["texte"] = self.texte
        d["empreinte"] = self.empreinte
        return d
