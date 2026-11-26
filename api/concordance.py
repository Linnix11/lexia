"""Anciens numeros du Code civil (avant la reforme du droit des contrats, du regime general et de la
preuve des obligations, entree en vigueur le 1er octobre 2016) -> articles actuels.

Table redigee a la main et verifiee texte contre texte sur l'archive LEGI (2026-11-12 ; ajouts de D136 le
2026-11-26 : 1121, 1146, 1150, 1152, 1166, 1167, 1386-2 a 1386-18) : un calcul
automatique par similarite se trompait sur des articles importants (1384 vers 1241 au lieu de 1242).
Ne mettre ici que des correspondances certaines ; dans le doute, ne rien mettre.

Usage : un etudiant ecrit « article 1134 » en pensant a la force obligatoire, alors que l'article 1134
actuel traite de l'erreur sur les qualites du cocontractant. Lexia sert les deux et previent le modele.
"""

from __future__ import annotations

import re

from api.references import References, _norm_num as _norm, citations_d_articles
from api.textes import codes_cites

DATE_REFORME = "2016-10-01"

REFORME_2016: dict[str, tuple[str, ...]] = {
    "1101": ("1101",),
    "1108": ("1128",),
    "1121": ("1205",),
    "1109": ("1130",),
    "1110": ("1132", "1133"),
    "1111": ("1142",),
    "1112": ("1140",),
    "1116": ("1137", "1139"),
    "1134": ("1103", "1193", "1104"),
    "1135": ("1194",),
    "1146": ("1344",),
    "1147": ("1231-1",),
    "1148": ("1218",),
    "1150": ("1231-3",),
    "1152": ("1231-5",),
    "1156": ("1188",),
    "1165": ("1199",),
    "1166": ("1341-1",),
    "1167": ("1341-2",),
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
    # responsabilite du fait des produits defectueux : meme texte, renumerote (« titre » devenu « chapitre »)
    "1386-1": ("1245",),
    **{f"1386-{i}": (f"1245-{i - 1}",) for i in range(2, 19)},
}

# Anciens articles sans equivalent : la cause (anciens 1131 a 1133) n'est plus une condition de validite du contrat.
# {ancien numero: articles actuels a lire a la place}. L'article 1131 actuel (nullite relative pour vice du
# consentement) n'a rien a voir : la reponse le decrivait sans dire que la cause a disparu (audit du 25/11, R6).
CAUSE = ("1128", "1162", "1169")
SANS_EQUIVALENT: dict[str, tuple[str, ...]] = {"1131": CAUSE, "1132": CAUSE, "1133": CAUSE}
NOTE_CAUSE = ("la cause n'est plus une condition de validité du contrat depuis le 1er octobre 2016 : voir les "
              "articles 1128 (conditions de validité), 1162 (le contrat ne peut déroger à l'ordre public ni par ses "
              "stipulations ni par son but) et 1169 (contrepartie illusoire ou dérisoire)")
# Note propre a un ancien numero : l'ancien 1108 listait la cause parmi les quatre conditions de validite.
NOTES: dict[str, str] = {
    **{n: NOTE_CAUSE for n in SANS_EQUIVALENT},
    "1108": "l'ancien article 1108 exigeait aussi « une cause licite » : " + NOTE_CAUSE,
}
# Articles actuels servis en plus de la correspondance (la recherche les ajoute aux extraits)
VOIR_AUSSI: dict[str, tuple[str, ...]] = {"1108": ("1162", "1169")}


def vise_code_civil(refs: References) -> bool:
    """Les articles cites peuvent-ils etre ceux du Code civil ?"""
    if refs.lois:
        return False
    if refs.codes:
        return "code_civil" in refs.codes
    return not refs.constitution  # sans code nomme, le Code civil passe en premier (sauf Constitution)


def anciens_numeros(refs: References) -> dict[str, tuple[str, ...]]:
    """{ancien numero cite: articles actuels} pour les articles de la question concernes par la reforme. Pour un
    ancien article sans equivalent (SANS_EQUIVALENT), les articles actuels a lire a la place."""
    if not vise_code_civil(refs):
        return {}
    return {a: REFORME_2016.get(a) or SANS_EQUIVALENT[a] for a in refs.articles
            if a in REFORME_2016 or a in SANS_EQUIVALENT}


def a_servir(anciens: dict[str, tuple[str, ...]]) -> list[str]:
    """Articles actuels a ajouter aux extraits pour ces anciens numeros, sans doublon."""
    return list(dict.fromkeys(n for a, ns in anciens.items() for n in (*ns, *VOIR_AUSSI.get(a, ()))))


def devenir(ancien: str) -> str:
    """Ce qu'est devenu un ancien numero, pour l'etudiant : « son contenu se trouve aujourd'hui a l'article 1240 »."""
    if ancien in SANS_EQUIVALENT:
        return f"cet article n'a pas d'équivalent : {NOTE_CAUSE}"
    nouveaux = REFORME_2016[ancien]
    art = "à l'article" if len(nouveaux) == 1 else "aux articles"
    return f"son contenu se trouve aujourd'hui {art} {', '.join(nouveaux)}"


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
        if ancien in SANS_EQUIVALENT:
            lignes.append(
                f"Attention : « article {ancien} du Code civil » désigne sans doute l'ancienne numérotation, en "
                f"vigueur jusqu'au 1er octobre 2016 : l'ancien article {ancien} traitait de la cause, et il n'a pas "
                f"d'équivalent dans le droit actuel ; {NOTE_CAUSE}. L'article {ancien} actuel traite d'autre chose. "
                f"Si la question vise l'ancien, dis-le dès la réponse directe, ne présente pas la cause comme une "
                f"condition actuelle et réponds avec les articles actuels, en citant les extraits."
            )
            continue
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
            + (f" Précision : {NOTES[ancien]}." if ancien in NOTES else "")
        )
    return "\n".join(lignes)


# --- anciens numeros ecrits dans un texte genere (reponse, carte mentale) ----------------------------------

def numeros_actuels(passages: list[dict]) -> set[str]:
    """Numeros des passages qui sont une version actuelle (ni close, ni celle d'avant la reforme)."""
    return {_norm(p.get("numero") or "") for p in passages if p.get("numero")
            and (p.get("meta") or {}).get("en_vigueur") is not False
            and (p.get("meta") or {}).get("date_fin") != DATE_REFORME}


def _devenu(ancien: str) -> tuple[str, ...]:
    """Articles actuels d'un ancien numero renumerote ou sans equivalent ; () pour un article seulement reecrit."""
    nouveaux = REFORME_2016.get(ancien) or SANS_EQUIVALENT.get(ancien) or ()
    return () if nouveaux == (ancien,) else nouveaux


def anciens_cites(texte: str, actuels: set[str]) -> list[tuple[int, list[tuple[str, tuple[str, ...]]]]]:
    """[(fin de la citation, [(ancien numero, articles actuels)])] pour chaque citation « article N (du Code civil) »
    d'un ancien numero dont aucune version actuelle n'est parmi `actuels`, et dont le texte ne donne pas deja un des
    numeros actuels (« l'ancien article 1152, devenu 1231-5 »). Une citation rattachee a un autre texte (« article
    1134 du code de commerce »), ou sans texte nomme dans une phrase qui ne nomme pas le Code civil mais un autre
    code, n'est pas concernee."""
    codes = codes_cites(texte)
    out = []
    for fin, numeros, code in citations_d_articles(texte):
        if code not in (None, "code_civil") or (code is None and codes and "code_civil" not in codes):
            continue
        anciens = [(n, ns) for n in numeros if (ns := _devenu(n)) and n not in actuels
                   and not any(re.search(rf"(?<![\w-]){re.escape(x)}(?![\w-])", texte) for x in ns)]
        if anciens:
            out.append((fin, anciens))
    return out


_NOM_DU_CODE = re.compile(r"(?:er\b)?\s*,?\s*(?:(?:alin[ée]a|al\.)\s*\d+(?:er)?\s*,?\s*)?(?:du|de)\s+"
                          r"(?:code\s+civil|c\.\s?civ\.?)", re.IGNORECASE)
MENTION = "ancienne numérotation"


def _mention(anciens: list[tuple[str, tuple[str, ...]]]) -> str:
    def actuel(ancien: str, nouveaux: tuple[str, ...]) -> str:
        if ancien in SANS_EQUIVALENT:
            return f"sans équivalent aujourd'hui, voir les articles {', '.join(nouveaux)}"
        return f"aujourd'hui {'article' if len(nouveaux) == 1 else 'articles'} {', '.join(nouveaux)}"
    if len(anciens) == 1:
        return f" ({MENTION}, {actuel(*anciens[0])})"
    return f" ({MENTION} : " + " ; ".join(f"{a}, {actuel(a, ns)}" for a, ns in anciens) + ")"


def annoter(texte: str, actuels: set[str]) -> str:
    """Ajoute « (ancienne numérotation, aujourd'hui article X) » apres chaque ancien numero du Code civil cite sans
    sa version actuelle (audit du 25/11, R4 : « au sens de l'article 1152 du Code civil », clause penale, donne pour
    le droit actuel). La mention suit le nom du code quand il est ecrit juste apres le numero."""
    if MENTION in texte:
        return texte
    for fin, anciens in reversed(anciens_cites(texte, actuels)):
        if m := _NOM_DU_CODE.match(texte, fin):
            fin = m.end()
        mention = _mention(anciens)
        if texte[fin:].startswith(")"):   # « (article 1131 du Code civil) » : pas de parentheses imbriquees
            mention = ", " + mention[2:-1]
        texte = texte[:fin] + mention + texte[fin:]
    return texte


CHAMPS = ("reponse_directe", "droit_positif", "explication", "points_incertains")


def signaler_anciens_numeros(reponse: dict, passages: list[dict]) -> int:
    """Apres la validation : annote les elements de la reponse qui citent un ancien numero du Code civil sans
    s'appuyer sur sa version actuelle. Un element source est juge sur ses propres sources (l'article 1152 actuel,
    sur la prescription, etait parmi les extraits du cas de R4 sans que l'element s'y rapporte) ; un element sans
    source, sur tous les extraits. Renvoie le nombre d'elements annotes."""
    par_id = {p["id"]: p for p in passages}
    tous = numeros_actuels(passages)
    annotes = 0
    for champ in CHAMPS:
        for e in reponse.get(champ) or []:
            sources = [par_id[i] for i in e.get("sources") or [] if i in par_id]
            texte = annoter(e["texte"], numeros_actuels(sources) if sources else tous)
            if texte != e["texte"]:
                e["texte"] = texte
                annotes += 1
    return annotes
