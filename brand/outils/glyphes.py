"""Extrait les contours des glyphes utilises par le logo (lettres de « lexia » et signe §).

Source : Source Serif 4 (SIL Open Font License 1.1), fichier brand/typographies/SourceSerif4[opsz,wght].ttf.
Le logo n'embarque aucune police : les lettres deviennent des tracés, ce que la licence OFL permet
(usage de la police dans un document ou une image). Aucune police modifiee n'est redistribuee.

Sortie : brand/outils/glyphes.json, coordonnees en unites de la police (1000 par cadratin), axe y vers le bas,
ligne de base a y = 0. Chaque tracé ne contient que des commandes M, L, C et Z (les courbes quadratiques
TrueType sont converties en cubiques) pour etre reutilisable tel quel en SVG et en Lottie.

Usage : python3 -I brand/outils/glyphes.py
"""
import json
from pathlib import Path

from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ICI = Path(__file__).resolve().parent
POLICE = ICI.parent / "typographies" / "SourceSerif4[opsz,wght].ttf"

# Reglages du logo : graisse 500 (Medium), taille optique 60 (coupe « Display », la plus fine).
REGLAGES = {"wght": 500, "opsz": 60}
# Le signe § du symbole doit rester lisible a 32 px : graisse 650, taille optique 20 (fûts plus epais).
REGLAGES_SIGNE = {"wght": 650, "opsz": 20}
# Mot du logotype. En cas de changement de nom de la marque, changer ce mot puis relancer les scripts.
GLYPHES_MOT = "lexia"
GLYPHE_SIGNE = "§"


class PlumeCubique(BasePen):
    """Ecrit des contours en sous-chemins M/L/C/Z, y inverse."""

    def __init__(self, glyphset):
        super().__init__(glyphset)
        self.contours = []  # liste de contours ; chaque contour = liste de commandes
        self.courant = None
        self.pos = (0, 0)

    def _moveTo(self, p):
        self.courant = [["M", p]]
        self.contours.append(self.courant)
        self.pos = p

    def _lineTo(self, p):
        self.courant.append(["L", p])
        self.pos = p

    def _curveToOne(self, p1, p2, p3):
        self.courant.append(["C", p1, p2, p3])
        self.pos = p3

    def _qCurveToOne(self, p1, p2):
        p0 = self.pos
        c1 = (p0[0] + 2 / 3 * (p1[0] - p0[0]), p0[1] + 2 / 3 * (p1[1] - p0[1]))
        c2 = (p2[0] + 2 / 3 * (p1[0] - p2[0]), p2[1] + 2 / 3 * (p1[1] - p2[1]))
        self._curveToOne(c1, c2, p2)

    def _closePath(self):
        self.courant.append(["Z"])

    def _endPath(self):
        pass


def contours_de(glyphset, nom):
    plume = PlumeCubique(glyphset)
    glyphset[nom].draw(plume)
    sortie = []
    for contour in plume.contours:
        cmds = []
        for c in contour:
            if c[0] == "Z":
                cmds.append(["Z"])
            else:
                cmds.append([c[0]] + [[round(x, 2), round(-y, 2)] for (x, y) in c[1:]])
        sortie.append(cmds)
    return sortie


def boite(contours):
    xs, ys = [], []
    for contour in contours:
        for c in contour:
            for pt in c[1:]:
                xs.append(pt[0])
                ys.append(pt[1])
    return [min(xs), min(ys), max(xs), max(ys)]


def main():
    statique = instantiateVariableFont(TTFont(POLICE), REGLAGES)
    pour_signe = instantiateVariableFont(TTFont(POLICE), REGLAGES_SIGNE)
    cmap = statique.getBestCmap()
    glyphset = statique.getGlyphSet()
    hmtx = statique["hmtx"]
    resultat = {
        "police": "Source Serif 4",
        "licence": "SIL Open Font License 1.1",
        "reglages": REGLAGES,
        "reglages_signe": REGLAGES_SIGNE,
        "unites_par_cadratin": statique["head"].unitsPerEm,
        "hauteur_x": statique["OS/2"].sxHeight,
        "hauteur_capitale": statique["OS/2"].sCapHeight,
        "mot": GLYPHES_MOT,
        "glyphes": {},
    }
    for car in dict.fromkeys(GLYPHES_MOT + GLYPHE_SIGNE):
        nom = cmap[ord(car)]
        source = pour_signe.getGlyphSet() if car == GLYPHE_SIGNE else glyphset
        contours = contours_de(source, nom)
        resultat["glyphes"][car] = {
            "chasse": hmtx[nom][0],
            "contours": contours,
            "boite": boite(contours),
        }
    (ICI / "glyphes.json").write_text(json.dumps(resultat, ensure_ascii=False))
    print("glyphes.json ecrit :", ", ".join(resultat["glyphes"]))


if __name__ == "__main__":
    main()
