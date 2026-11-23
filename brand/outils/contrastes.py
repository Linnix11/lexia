"""Palette de la marque et verification des contrastes WCAG 2.2 (criteres 1.4.3 et 1.4.11).

Formule : luminance relative et rapport (L1 + 0,05) / (L2 + 0,05) de la WCAG 2.2
(https://www.w3.org/TR/WCAG22/#dfn-contrast-ratio). Seuils AA : 4,5:1 pour le texte courant, 3:1 pour le texte
de 24 px et plus (ou 18,66 px en gras) et pour les elements graphiques necessaires (1.4.11).

Sorties : brand/couleurs/palette.json, palette.css et contrastes.md.
Usage : python3 -I brand/outils/contrastes.py
"""
import json
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
SORTIE = KIT / "couleurs"

# nom, hex, role. Valeurs identiques a web/src/index.css (site au 23 novembre 2026), sauf « or-texte », ajoute ici.
PALETTE = [
    ("foret", "#315e4b", "principale", "Couleur de marque : signet, boutons, liens, fonds des visuels pleins."),
    ("papier", "#f5f4ef", "principale", "Fond de page et fond clair des visuels. Jamais de blanc pur en grand aplat."),
    ("encre", "#202724", "principale", "Texte et logotype sur fond clair."),
    ("or", "#bd8951", "principale", "Liseré du signet et filets. Accent rare, jamais pour du texte."),
    ("foret-fonce", "#244735", "secondaire", "Survol des boutons, fond des visuels sombres."),
    ("surface", "#fffefa", "secondaire", "Cartes posées sur papier ; texte et signet sur fond forêt."),
    ("menthe", "#e7efe9", "secondaire", "Fond d'une puce active, d'une citation au survol, d'un badge."),
    ("sauge", "#e2e8e1", "secondaire", "Survol sur fond menthe."),
    ("creme", "#fbf7ef", "secondaire", "Encadrés d'information douce."),
    ("ligne", "#e4e4dc", "secondaire", "Bordures des cartes et champs. Décoratif uniquement."),
    ("gris", "#666e69", "secondaire", "Texte secondaire (« muted » du site)."),
    ("brique", "#8c4a36", "fonctionnelle", "Erreurs et actions destructrices."),
    ("brique-fond", "#f6e9e4", "fonctionnelle", "Fond des messages d'erreur."),
    ("ocre", "#746347", "fonctionnelle", "Texte des encadrés crème."),
    ("or-texte", "#8a6534", "ajout", "Or assombri pour un mot ou un chiffre en or sur fond clair (texte)."),
]
COULEURS = {nom: hexa for nom, hexa, _, _ in PALETTE}

# (texte ou element, fond, usage, seuil)
PAIRES = [
    ("encre", "papier", "Texte courant", 4.5),
    ("encre", "surface", "Texte courant sur carte", 4.5),
    ("encre", "menthe", "Texte sur badge", 4.5),
    ("foret", "papier", "Liens, surtitres, titres verts", 4.5),
    ("foret", "surface", "Liens et boutons secondaires", 4.5),
    ("foret", "menthe", "Puce active", 4.5),
    ("surface", "foret", "Texte et logotype sur fond forêt", 4.5),
    ("surface", "foret-fonce", "Texte sur fond forêt foncé", 4.5),
    ("papier", "encre", "Texte clair sur fond encre", 4.5),
    ("gris", "papier", "Texte secondaire sur papier", 4.5),
    ("gris", "surface", "Texte secondaire sur carte", 4.5),
    ("brique", "surface", "Message d'erreur", 4.5),
    ("brique", "brique-fond", "Message d'erreur sur son fond", 4.5),
    ("ocre", "creme", "Encadré crème", 4.5),
    ("or-texte", "papier", "Mot en or sur papier", 4.5),
    ("or-texte", "surface", "Mot en or sur carte", 4.5),
    ("or", "foret", "Texte or sur forêt : interdit (le liseré reste décoratif)", 3.0),
    ("foret", "papier", "Signet sur papier (élément graphique)", 3.0),
    ("surface", "foret", "Signet clair sur fond forêt (élément graphique)", 3.0),
    ("or", "papier", "Liseré or sur papier (décoratif, non requis)", None),
    ("or", "surface", "Texte or sur blanc : interdit", 4.5),
    ("ligne", "surface", "Bordure de carte (décorative, non requise)", None),
]


def luminance(hexa):
    r, g, b = (int(hexa[i : i + 2], 16) / 255 for i in (1, 3, 5))

    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def rapport(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def virgule(x, n=2):
    return f"{x:.{n}f}".replace(".", ",")


def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    lignes = []
    resultats = []
    for texte, fond, usage, seuil in PAIRES:
        r = rapport(COULEURS[texte], COULEURS[fond])
        if seuil is None:
            verdict = "décoratif"
        elif r >= seuil:
            verdict = "conforme AA"
        else:
            verdict = "non conforme : usage interdit"
        resultats.append({"premier_plan": texte, "fond": fond, "rapport": round(r, 2), "seuil": seuil, "verdict": verdict, "usage": usage})
        seuil_txt = "aucun" if seuil is None else virgule(seuil, 1) + ":1"
        lignes.append(
            f"| `{texte}` {COULEURS[texte]} | `{fond}` {COULEURS[fond]} | {virgule(r)}:1 | {seuil_txt} | {verdict} | {usage} |"
        )

    json.dump(
        {"couleurs": [{"nom": n, "hex": h, "role": r, "usage": u} for n, h, r, u in PALETTE], "contrastes": resultats},
        open(SORTIE / "palette.json", "w"),
        ensure_ascii=False,
        indent=2,
    )
    css = ["/* Palette de la marque Lexia, generee par brand/outils/contrastes.py */", ":root {"]
    css += [f"  --lexia-{n}: {h};" for n, h, _, _ in PALETTE]
    css.append("}")
    (SORTIE / "palette.css").write_text("\n".join(css) + "\n")

    md = [
        "# Contrastes de la palette (WCAG 2.2, niveau AA)",
        "",
        "Fichier généré par `brand/outils/contrastes.py` : ne pas modifier à la main.",
        "Formule de la WCAG 2.2 (https://www.w3.org/TR/WCAG22/#dfn-contrast-ratio). Seuils AA : 4,5:1 pour le texte",
        "courant (critère 1.4.3), 3:1 pour le texte de 24 px et plus et pour les éléments graphiques nécessaires",
        "(critère 1.4.11).",
        "",
        "| Premier plan | Fond | Rapport | Seuil | Verdict | Usage |",
        "|---|---|---|---|---|---|",
        *lignes,
        "",
    ]
    (SORTIE / "contrastes.md").write_text("\n".join(md))
    for r in resultats:
        print(f"{r['premier_plan']:>9} / {r['fond']:<11} {r['rapport']:>5}  {r['verdict']}")


if __name__ == "__main__":
    main()
