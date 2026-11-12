"""Anciens numeros du Code civil (avant la reforme du droit des contrats, du regime general et de la
preuve des obligations, entree en vigueur le 1er octobre 2016) -> articles actuels.

Table redigee a la main et verifiee texte contre texte sur l'archive LEGI (2026-11-12) : un calcul
automatique par similarite se trompait sur des articles importants (1384 vers 1241 au lieu de 1242).
Ne mettre ici que des correspondances certaines ; dans le doute, ne rien mettre.

Usage : un etudiant ecrit « article 1134 » en pensant a la force obligatoire, alors que l'article 1134
actuel traite de l'erreur sur les qualites du cocontractant. Lexia sert les deux et previent le modele.
"""

from __future__ import annotations

from api.references import References

DATE_REFORME = "2016-10-01"

REFORME_2016: dict[str, tuple[str, ...]] = {
    "1101": ("1101",),
    "1108": ("1128",),
    "1109": ("1130",),
    "1110": ("1132", "1133"),
    "1111": ("1142",),
    "1112": ("1140",),
    "1116": ("1137", "1139"),
    "1134": ("1103", "1193", "1104"),
    "1135": ("1194",),
    "1147": ("1231-1",),
    "1148": ("1218",),
    "1156": ("1188",),
    "1165": ("1199",),
    "1184": ("1224", "1227", "1228"),
    "1315": ("1353",),
    "1341": ("1359",),
    "1351": ("1355",),
    "1371": ("1300",),
    "1372": ("1301",),
    "1376": ("1302-1",),
    "1382": ("1240",),
    "1383": ("1241",),
    "1384": ("1242",),
    "1385": ("1243",),
    "1386": ("1244",),
    "1386-1": ("1245",),
}


def vise_code_civil(refs: References) -> bool:
    """Les articles cites peuvent-ils etre ceux du Code civil ?"""
    if refs.lois:
        return False
    if refs.codes:
        return "code_civil" in refs.codes
    return not refs.constitution  # sans code nomme, le Code civil passe en premier (sauf Constitution)


def anciens_numeros(refs: References) -> dict[str, tuple[str, ...]]:
    """{ancien numero cite: articles actuels} pour les articles de la question concernes par la reforme."""
    if not vise_code_civil(refs):
        return {}
    return {a: REFORME_2016[a] for a in refs.articles if a in REFORME_2016}


def ancienne_version(versions: list[dict]) -> dict | None:
    """Version de l'article en vigueur jusqu'a la reforme (parmi les versions d'un numero)."""
    for v in versions:
        if (v.get("meta") or {}).get("date_fin") == DATE_REFORME:
            return v
    return None


def note(concordance: dict[str, list[str] | tuple[str, ...]]) -> str:
    """Consigne ajoutee au prompt quand la question cite un ancien numero."""
    lignes = []
    for ancien, nouveaux in concordance.items():
        if tuple(nouveaux) == (ancien,):
            lignes.append(
                f"Attention : l'article {ancien} du Code civil a été réécrit le 1er octobre 2016. Si la question "
                f"vise l'ancienne rédaction, dis-le et réponds avec la rédaction actuelle, en citant les extraits."
            )
            continue
        art = "à l'article" if len(nouveaux) == 1 else "aux articles"
        lignes.append(
            f"Attention : « article {ancien} du Code civil » désigne peut-être l'ancienne numérotation, en vigueur "
            f"jusqu'au 1er octobre 2016. Son contenu se retrouve aujourd'hui {art} {', '.join(nouveaux)}, et "
            f"le numéro {ancien} ne correspond plus à ce contenu. Déduis de la question lequel est visé ; si c'est "
            f"l'ancien, dis-le clairement et réponds avec l'article actuel, en citant les extraits."
        )
    return "\n".join(lignes)
