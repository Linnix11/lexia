"""Geometrie et couleurs de la marque : une seule source pour tous les fichiers du kit.

Le symbole (« le signet ») est dessine sur une grille de 64 unites. Il ne contient aucune lettre du nom :
un marque-page vert foret, un liseré or en tete et le signe § en reserve. Il survit a un changement de nom.
Le logotype « lexia » est en Source Serif 4, converti en tracés (aucune police a charger).
"""
import json
from pathlib import Path

ICI = Path(__file__).resolve().parent
GLYPHES = json.loads((ICI / "glyphes.json").read_text())
MOT = GLYPHES["mot"]  # « lexia », defini dans glyphes.py

# Couleurs (valeurs du site, web/src/index.css, et du systeme de design du 13 novembre 2026).
FORET = "#315e4b"
FORET_FONCE = "#244735"
OR = "#bd8951"
PAPIER = "#f5f4ef"
SURFACE = "#fffefa"
ENCRE = "#202724"
BLANC = "#ffffff"

# Signet, grille de 64 : bords 15 et 49, tete a 4, pied a 60, encoche dont la pointe remonte a 47.
G, D, HAUT, BAS, ENCOCHE = 15, 49, 4, 60, 47
R = 2  # arrondi des deux coins du haut
K = 0.5523 * R  # poignees d'un quart de cercle en cubique
LISERE_BAS = 10  # le liseré or occupe la tete, de 4 a 10
JOINT = 1.4  # en monochrome, une fente separe le liseré du corps

CORPS_CHEMIN = f"M{G} {LISERE_BAS - 0.3}H{D}V{BAS}L32 {ENCOCHE}L{G} {BAS}Z"
CORPS_MONO_CHEMIN = f"M{G} {LISERE_BAS + JOINT}H{D}V{BAS}L32 {ENCOCHE}L{G} {BAS}Z"
LISERE_CHEMIN = (
    f"M{G} {LISERE_BAS}V{HAUT + R}C{G} {HAUT + R - K} {G + R - K} {HAUT} {G + R} {HAUT}"
    f"H{D - R}C{D - R + K} {HAUT} {D} {HAUT + R - K} {D} {HAUT + R}V{LISERE_BAS}Z"
)
# Silhouette complete (pour les tailles minuscules et les masques).
SILHOUETTE_CHEMIN = (
    f"M{G} {BAS}V{HAUT + R}C{G} {HAUT + R - K} {G + R - K} {HAUT} {G + R} {HAUT}"
    f"H{D - R}C{D - R + K} {HAUT} {D} {HAUT + R - K} {D} {HAUT + R}V{BAS}L32 {ENCOCHE}Z"
)

# Signe § : 25 unites de haut, centre horizontalement, centre optique a 28 (entre le liseré et l'encoche).
SIGNE_HAUTEUR = 24.5
SIGNE_CENTRE_Y = 28.2


def _chemin(contours, k, dx, dy):
    """Contours de glyphes.json vers un attribut d (echelle k, translation dx, dy)."""
    morceaux = []
    for contour in contours:
        for c in contour:
            if c[0] == "Z":
                morceaux.append("Z")
            else:
                pts = " ".join(f"{p[0] * k + dx:.2f} {p[1] * k + dy:.2f}" for p in c[1:])
                morceaux.append(c[0] + pts)
    return "".join(morceaux)


def signe_transform():
    g = GLYPHES["glyphes"]["§"]
    x0, y0, x1, y1 = g["boite"]
    k = SIGNE_HAUTEUR / (y1 - y0)
    dx = 32 - (x0 + x1) / 2 * k
    dy = SIGNE_CENTRE_Y - (y0 + y1) / 2 * k
    return k, dx, dy


def signe_chemin():
    k, dx, dy = signe_transform()
    return _chemin(GLYPHES["glyphes"]["§"]["contours"], k, dx, dy)


# Logotype : la hampe du « l » mesure 31 unites (55 % du signet) ; leger resserrement des lettres.
MOT_HAUTEUR_L = 31.0
MOT_APPROCHE = -14  # unites de police ajoutees entre deux lettres


def mot_echelle():
    # Echelle fixee sur la hampe du « l » (hauteur d'ascendante), quel que soit le mot.
    l = GLYPHES["glyphes"]["l"]["boite"] if "l" in GLYPHES["glyphes"] else [0, -741]
    return MOT_HAUTEUR_L / (0 - l[1])


def mot_chemins(x, ligne_de_base, echelle=None):
    """Renvoie (liste de d par lettre, largeur) du mot du logotype, la premiere lettre calee sur x."""
    k = echelle or mot_echelle()
    chemins = []
    curseur = 0.0
    premiere = GLYPHES["glyphes"][MOT[0]]["boite"][0]
    for i, car in enumerate(MOT):
        g = GLYPHES["glyphes"][car]
        chemins.append(_chemin(g["contours"], k, x + (curseur - premiere) * k, ligne_de_base))
        if i < len(MOT) - 1:
            curseur += g["chasse"] + MOT_APPROCHE
    derniere = GLYPHES["glyphes"][MOT[-1]]["boite"][2]
    largeur = (curseur + derniere - premiere) * k
    return chemins, largeur


# ---------------------------------------------------------------- symbole

def symbole_groupe(variante="couleur", identifiant="s"):
    """Elements SVG du symbole (grille 64). variantes : couleur, inverse, mono-clair, mono-fonce, silhouette."""
    if variante == "couleur":
        return (
            f'<path d="{CORPS_CHEMIN}" fill="{FORET}"/>'
            f'<path d="{LISERE_CHEMIN}" fill="{OR}"/>'
            f'<path d="{signe_chemin()}" fill="{SURFACE}"/>'
        )
    if variante == "inverse":
        return (
            f'<path d="{CORPS_CHEMIN}" fill="{SURFACE}"/>'
            f'<path d="{LISERE_CHEMIN}" fill="{OR}"/>'
            f'<path d="{signe_chemin()}" fill="{FORET}"/>'
        )
    if variante == "silhouette":  # 16 px : plus de §, liseré conserve
        return f'<path d="{CORPS_CHEMIN}" fill="{FORET}"/><path d="{LISERE_CHEMIN}" fill="{OR}"/>'
    couleur = ENCRE if variante == "mono-clair" else BLANC
    return (
        f'<mask id="{identifiant}-m" maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64">'
        f'<path d="{CORPS_MONO_CHEMIN}" fill="#fff"/><path d="{LISERE_CHEMIN}" fill="#fff"/>'
        f'<path d="{signe_chemin()}" fill="#000"/></mask>'
        f'<rect width="64" height="64" fill="{couleur}" mask="url(#{identifiant}-m)"/>'
    )


def couleur_mot(variante):
    return {"couleur": ENCRE, "inverse": SURFACE, "mono-clair": ENCRE, "mono-fonce": BLANC}[variante]


def svg(viewbox, contenu, titre, largeur=None, hauteur=None):
    dims = f' width="{largeur}" height="{hauteur}"' if largeur else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}"{dims} role="img" aria-label="{titre}">'
        f"<title>{titre}</title>{contenu}</svg>\n"
    )


def logo_symbole(variante):
    # Boite serree autour du signet (15..49 x 4..60), carree pour servir d'icone : 4..60 en hauteur.
    return svg("4 4 56 56", symbole_groupe(variante, "s"), "Symbole de la marque : signet §")


def logo_horizontal(variante):
    base = 47.5
    x_mot = D + 10
    chemins, largeur = mot_chemins(x_mot, base)
    mot = "".join(f'<path d="{d}"/>' for d in chemins)
    contenu = symbole_groupe(variante, "h") + f'<g fill="{couleur_mot(variante)}">{mot}</g>'
    droite = x_mot + largeur
    return svg(f"{G} {HAUT} {droite - G:.2f} {BAS - HAUT}", contenu, MOT)


def logo_principal(variante):
    """Logo empile : signet agrandi (x1,5) au-dessus, mot centre dessous."""
    k = 1.5
    _, largeur = mot_chemins(0, 0)
    haut_signet = HAUT * k
    bas_signet = BAS * k
    base = bas_signet + 14 + MOT_HAUTEUR_L
    x_mot = 32 * k - largeur / 2
    chemins, _ = mot_chemins(x_mot, base)
    mot = "".join(f'<path d="{d}"/>' for d in chemins)
    contenu = (
        f'<g transform="scale({k})">{symbole_groupe(variante, "p")}</g>'
        f'<g fill="{couleur_mot(variante)}">{mot}</g>'
    )
    largeur_totale = max(largeur, (D - G) * k)
    x0 = 32 * k - largeur_totale / 2
    bas = base + 0.7  # « lexia » n'a pas de descendante ; 0,7 pour les arrondis du « e » et du « a »
    return svg(f"{x0:.2f} {haut_signet:.2f} {largeur_totale:.2f} {bas - haut_signet:.2f}", contenu, MOT)


# ---------------------------------------------------------------- icones

def icone_app(taille_signet=0.66, fond=FORET, variante="inverse", rayon=0):
    """Icone carree pleine (Apple, manifeste). Le signet occupe taille_signet de la hauteur."""
    h = 56 * taille_signet
    k = h / 56
    tx = 32 - 32 * k
    ty = 32 - 32 * k
    r = f' rx="{rayon}"' if rayon else ""
    contenu = (
        f'<rect width="64" height="64" fill="{fond}"{r}/>'
        f'<g transform="translate({tx:.3f} {ty:.3f}) scale({k:.4f})">{symbole_groupe(variante, "i")}</g>'
    )
    return svg("0 0 64 64", contenu, "Icone de l'application")


def favicon(petit=False):
    variante = "silhouette" if petit else "couleur"
    return svg("4 4 56 56", symbole_groupe(variante, "f"), MOT)
