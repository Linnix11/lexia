"""Controle de la forme d'une reponse JSON du modele par rapport au schema demande.

Gemini respecte le schema ; Groq ne l'applique qu'« au mieux ». Une liste de chaines a la place d'une liste
d'objets (`droit_positif: ["texte"]`) ou une chaine a la place d'une liste (`questions: "..."`) faisait lever
AttributeError plus loin : erreur 500 sans essayer le modele suivant (audit du 19/11, SRV-3). Une reponse
non conforme est traitee comme un echec du modele, qui passe la main au suivant.

Seule la structure est controlee (objets et listes) : les champs scalaires et les valeurs nulles sont deja
toleres par le code qui lit la reponse (`str(...)`, `or []`, `isinstance`).
"""

from __future__ import annotations


def conforme(valeur, schema: dict) -> bool:
    type_ = schema.get("type")
    if type_ == "object":
        if not isinstance(valeur, dict):
            return False
        return all(conforme(valeur[cle], sous) for cle, sous in (schema.get("properties") or {}).items()
                   if valeur.get(cle) is not None)
    if type_ == "array":
        if not isinstance(valeur, list):
            return False
        items = schema.get("items") or {}
        return all(conforme(v, items) for v in valeur)
    if type_ is None:   # schema sans type : tout est admis
        return True
    return not isinstance(valeur, (dict, list))
