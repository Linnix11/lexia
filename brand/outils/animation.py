"""Logo anime : SVG autonome (animation CSS) et version Lottie (JSON), sans outil payant.

Sequence commune (2,2 s) :
  0,00 a 0,70 s  le corps du signet se deroule depuis le haut ;
  0,35 a 0,85 s  le liseré or s'etend de gauche a droite ;
  0,70 a 1,20 s  le signe § apparait en remontant de 3 unites ;
  1,00 a 2,20 s  les cinq lettres de « lexia » apparaissent une a une (0,08 s d'ecart, 0,5 s chacune).
Moins de mouvement demande (prefers-reduced-motion) : le SVG affiche directement l'etat final.

Usage, depuis la racine du depot : python3 -I brand/outils/animation.py
"""
import json
import re
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))

import marque as m  # noqa: E402

SORTIE = ICI.parent / "animation"
EASE = "cubic-bezier(.2,.8,.2,1)"


def elements_horizontal():
    base = 47.5
    x_mot = m.D + 10
    lettres, largeur = m.mot_chemins(x_mot, base)
    return {
        "corps": m.CORPS_CHEMIN,
        "lisere": m.LISERE_CHEMIN,
        "signe": m.signe_chemin(),
        "lettres": lettres,
        "boite": (m.G, m.HAUT, x_mot + largeur - m.G, m.BAS - m.HAUT),
    }


def svg_anime():
    e = elements_horizontal()
    x, y, w, h = e["boite"]
    lettres = "".join(
        f'<path class="l" style="animation-delay:{1.0 + i * 0.08:.2f}s" d="{d}"/>' for i, d in enumerate(e["lettres"])
    )
    style = f"""
.corps{{transform-box:fill-box;transform-origin:50% 0;animation:deroule .7s {EASE} both}}
.lisere{{transform-box:fill-box;transform-origin:0 50%;animation:etend .5s {EASE} .35s both}}
.signe{{animation:monte .5s {EASE} .7s both}}
.l{{animation:lettre .5s {EASE} both}}
@keyframes deroule{{from{{transform:scaleY(0)}}to{{transform:scaleY(1)}}}}
@keyframes etend{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
@keyframes monte{{from{{opacity:0;transform:translateY(3px)}}to{{opacity:1;transform:none}}}}
@keyframes lettre{{from{{opacity:0;transform:translateX(-3px)}}to{{opacity:1;transform:none}}}}
@media (prefers-reduced-motion:reduce){{.corps,.lisere,.signe,.l{{animation:none}}}}
"""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x} {y} {w:.2f} {h}" role="img" aria-label="{m.MOT}">'
        f"<title>{m.MOT}</title><style>{style}</style>"
        f'<path class="corps" d="{e["corps"]}" fill="{m.FORET}"/>'
        f'<path class="lisere" d="{e["lisere"]}" fill="{m.OR}"/>'
        f'<path class="signe" d="{e["signe"]}" fill="{m.SURFACE}"/>'
        f'<g fill="{m.ENCRE}">{lettres}</g></svg>\n'
    )


# ---------------------------------------------------------------- Lottie

def _jetons(d):
    return re.findall(r"[MLHVCZ]|-?\d+(?:\.\d+)?", d)


def contours_lottie(d, k, ox, oy):
    """Chemin SVG absolu (M L H V C Z) vers des formes Lottie {i, o, v, c}, coordonnees * k - origine."""
    jet = _jetons(d)
    contours, courant, pos = [], None, (0.0, 0.0)
    i = 0

    def pt(x, y):
        return [round((x - ox) * k, 3), round((y - oy) * k, 3)]

    while i < len(jet):
        c = jet[i]
        i += 1
        if c == "M":
            pos = (float(jet[i]), float(jet[i + 1]))
            i += 2
            courant = {"v": [pt(*pos)], "i": [[0, 0]], "o": [[0, 0]]}
            contours.append(courant)
        elif c in "LHV":
            if c == "L":
                pos = (float(jet[i]), float(jet[i + 1]))
                i += 2
            elif c == "H":
                pos = (float(jet[i]), pos[1])
                i += 1
            else:
                pos = (pos[0], float(jet[i]))
                i += 1
            courant["v"].append(pt(*pos))
            courant["i"].append([0, 0])
            courant["o"].append([0, 0])
        elif c == "C":
            c1 = (float(jet[i]), float(jet[i + 1]))
            c2 = (float(jet[i + 2]), float(jet[i + 3]))
            p = (float(jet[i + 4]), float(jet[i + 5]))
            i += 6
            v_prec = courant["v"][-1]
            a1, a2, b = pt(*c1), pt(*c2), pt(*p)
            courant["o"][-1] = [round(a1[0] - v_prec[0], 3), round(a1[1] - v_prec[1], 3)]
            courant["v"].append(b)
            courant["i"].append([round(a2[0] - b[0], 3), round(a2[1] - b[1], 3)])
            courant["o"].append([0, 0])
            pos = p
        elif c == "Z":
            # Le dernier point repete souvent le premier : on le fusionne.
            if len(courant["v"]) > 1 and courant["v"][-1] == courant["v"][0]:
                courant["i"][0] = courant["i"][-1]
                for cle in ("v", "i", "o"):
                    courant[cle].pop()
    return [{"i": c["i"], "o": c["o"], "v": c["v"], "c": True} for c in contours]


def couleur(hexa):
    return [round(int(hexa[j : j + 2], 16) / 255, 4) for j in (1, 3, 5)] + [1]


def cle(t, valeur, fin=False):
    if fin:
        return {"t": t, "s": valeur}
    n = len(valeur)
    return {"t": t, "s": valeur, "o": {"x": [0.2] * n, "y": [0.8] * n}, "i": {"x": [0.2] * n, "y": [1] * n}}


def statique(v):
    return {"a": 0, "k": v}


def anime(*cles):
    return {"a": 1, "k": list(cles)}


def calque(ind, nom, formes, teinte, ancre, position, echelle=None, opacite=None, op=150):
    groupes = [{"ty": "sh", "nm": f"{nom}-{j}", "ks": statique(f)} for j, f in enumerate(formes)]
    return {
        "ddd": 0, "ind": ind, "ty": 4, "nm": nom, "sr": 1, "ao": 0, "ip": 0, "op": op, "st": 0, "bm": 0,
        "ks": {
            "o": opacite or statique(100),
            "r": statique(0),
            "p": statique((position or [0, 0]) + [0]),
            "a": statique(ancre + [0]),
            "s": echelle or statique([100, 100, 100]),
        },
        "shapes": [{
            "ty": "gr", "nm": nom,
            "it": groupes + [
                {"ty": "fl", "c": statique(couleur(teinte)), "o": statique(100), "r": 1, "nm": "remplissage"},
                {"ty": "tr", "p": statique([0, 0]), "a": statique([0, 0]), "s": statique([100, 100]),
                 "r": statique(0), "o": statique(100), "sk": statique(0), "sa": statique(0)},
            ],
        }],
    }


def lottie():
    FPS = 60
    K = 8  # 1 unite de la grille = 8 px
    MARGE = 4
    e = elements_horizontal()
    x, y, w, h = e["boite"]
    ox, oy = x - MARGE, y - MARGE
    W, H = round((w + 2 * MARGE) * K), round((h + 2 * MARGE) * K)

    def P(px, py):
        return [round((px - ox) * K, 2), round((py - oy) * K, 2)]

    def s(sec):
        return round(sec * FPS)

    calques = []
    # Signe § : opacite et montee de 3 unites.
    pos_signe = [0, 0]  # formes deja en coordonnees de la composition
    calques.append(calque(
        1, "signe", contours_lottie(e["signe"], K, ox, oy), m.SURFACE, [0, 0], None,
        opacite=anime(cle(s(0.7), [0]), cle(s(1.2), [100], True)),
    ))
    calques[-1]["ks"]["p"] = anime(cle(s(0.7), [pos_signe[0], pos_signe[1] + 3 * K, 0]), cle(s(1.2), pos_signe + [0], True))
    # Liseré : echelle horizontale depuis le bord gauche.
    ancre_lisere = P(m.G, (m.HAUT + m.LISERE_BAS) / 2)
    calques.append(calque(
        2, "lisere", contours_lottie(e["lisere"], K, ox, oy), m.OR, ancre_lisere, ancre_lisere,
        echelle=anime(cle(s(0.35), [0, 100, 100]), cle(s(0.85), [100, 100, 100], True)),
    ))
    # Corps : echelle verticale depuis le haut.
    ancre_corps = P(32, m.LISERE_BAS - 0.3)
    calques.append(calque(
        3, "corps", contours_lottie(e["corps"], K, ox, oy), m.FORET, ancre_corps, ancre_corps,
        echelle=anime(cle(0, [100, 0, 100]), cle(s(0.7), [100, 100, 100], True)),
    ))
    # Lettres.
    for j, d in enumerate(e["lettres"]):
        debut = 1.0 + j * 0.08
        cal = calque(
            4 + j, "lettre-" + m.MOT[j], contours_lottie(d, K, ox, oy), m.ENCRE, [0, 0], None,
            opacite=anime(cle(s(debut), [0]), cle(s(debut + 0.5), [100], True)),
        )
        cal["ks"]["p"] = anime(cle(s(debut), [-3 * K, 0, 0]), cle(s(debut + 0.5), [0, 0, 0], True))
        calques.append(cal)

    return {
        "v": "5.7.4", "fr": FPS, "ip": 0, "op": 150, "w": W, "h": H, "nm": "lexia, logo anime", "ddd": 0,
        "assets": [], "layers": calques, "markers": [],
    }


if __name__ == "__main__":
    SORTIE.mkdir(parents=True, exist_ok=True)
    (SORTIE / "logo-anime.svg").write_text(svg_anime(), encoding="utf-8")
    donnees = lottie()
    (SORTIE / "logo-anime.lottie.json").write_text(json.dumps(donnees, separators=(",", ":")), encoding="utf-8")
    print(f"logo-anime.svg, logo-anime.lottie.json ({donnees['w']} x {donnees['h']} px, {len(donnees['layers'])} calques)")
