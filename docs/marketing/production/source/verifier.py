#!/usr/bin/env python3
"""Cherche les formules interdites, les tirets cadratins et les emojis dans les textes produits.

Les listes de phrases interdites elles-memes (README, kit ambassadeur, documents.py) sont exclues. Une formule
interdite employee a la negative (« pas d'application mobile ») est signalee pour relecture, pas comme une faute :
la sortie montre le contexte.

Usage : python3 verifier.py (depuis source/, apres visuels.py et documents.py)
"""
import re
import sys
from pathlib import Path

PROD = Path(__file__).resolve().parent.parent
FICHIERS = ([p for p in (PROD / "source" / "html").glob("*.html") if not p.name.startswith("kit-")]
            + [p for p in PROD.rglob("*.md") if p.name != "README.md" or p.parent.name == "landings"]
            + [PROD / "associations" / "email-associations.txt", PROD / "emails" / "modele-email.html"])

INTERDITS = {
    "jurisprudence à jour": r"jurisprudence[^.]{0,30}(à jour|chaque nuit)",
    "données et entraînement": r"jamais[^.]{0,40}entra[iî]n|respectueux de vos données",
    "hébergement": r"héberg[ée]+s? en France",
    "fiabilité": r"sans erreur|fiable à 100|100\s?% fiable|validée?s? par des enseignants",
    "superlatifs": r"\ble meilleur\b|\ble seul\b|\bn°\s?1\b|numéro un",
    "comparaison nommée": r"NotebookLM|Gemini Notebook|ChatGPT|Doctrine\.fr|Dalloz",
    "remplacement": r"remplace(?!nt)",
    "conseil": r"avocat dans|conseil juridique",
    "offre limitée": r"offre limitée",
    "chiffre de passages": r"926\s?(000|481)",
    "fonctions absentes": r"cartes? mentales?|application mobile|paiement (par carte|en ligne)",
}
ATTENDUS_A_LA_NEGATIVE = {"fonctions absentes", "remplacement", "conseil", "jurisprudence à jour"}
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-⛿✀-➿]")


def texte(p: Path) -> str:
    t = p.read_text(encoding="utf-8")
    if p.suffix == ".html":
        t = re.sub(r"<style.*?</style>|<svg.*?</svg>", " ", t, flags=re.S)
        t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"[  ]", " ", t)


fautes = relire = 0
for p in sorted(set(FICHIERS)):
    t = texte(p)
    nom = p.relative_to(PROD)
    for m in re.finditer("—", t):
        print(f"FAUTE tiret cadratin : {nom}")
        fautes += 1
    for m in EMOJI.finditer(t):
        if m.group() in "✓→":
            continue
        print(f"FAUTE emoji {m.group()!r} : {nom}")
        fautes += 1
    for cle, motif in INTERDITS.items():
        for m in re.finditer(motif, t, flags=re.I):
            ctx = " ".join(t[max(0, m.start() - 70): m.end() + 50].split())
            if cle in ATTENDUS_A_LA_NEGATIVE:
                relire += 1
                print(f"RELIRE ({cle}) {nom} : ...{ctx}...")
            else:
                fautes += 1
                print(f"FAUTE ({cle}) {nom} : ...{ctx}...")
print(f"\n{len(set(FICHIERS))} fichiers lus, {fautes} faute(s), {relire} emploi(s) à la négative à relire")
sys.exit(1 if fautes else 0)
