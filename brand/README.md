# Kit de marque Lexia

Identité visuelle finalisée le 23 novembre 2026 : le signet § (marque-page vert forêt, liseré or, signe § en
réserve) et le logotype « lexia » en Source Serif 4. Règles d'usage : `charte.md`. Le nom « Lexia » n'est pas
encore vérifié comme marque (`charte.md`, partie 0) : rien n'est publié, imprimé ni déposé avec ce kit avant
l'avis d'un conseil.

Présentation visuelle de tout le kit, avec les animations et les vidéos : page claude.ai privée « Kit de marque
Lexia », https://claude.ai/artifact/FY4UyEAcFJEDTGTGzkGX4y (à partager depuis son menu Partager).

## Contenu

| Dossier | Contenu |
|---|---|
| `logos/svg/` | 12 logos : `principal` (empilé), `horizontal`, `symbole`, chacun en `couleur`, `inverse` (sur forêt), `mono-clair` (encre seule) et `mono-fonce` (blanc seul). |
| `logos/png/` | Les mêmes en PNG transparent : symbole 64 à 1024 px, horizontal 320 à 2560 px de large, principal 256 à 1024 px de large. |
| `icones/` | `favicon.svg`, `favicon.ico` (16, 32, 48), `favicon-16/32/48.png`, `apple-touch-icon.png` (180), `icone-64` à `icone-1024.png` (fond forêt), `icone-maskable-192/512.png`, sources SVG, `manifest-exemple.json`. |
| `open-graph/` | `og-image-1200x630.png` (partage de liens). |
| `reseaux/profils/` | Avatars : `profil-1080.png` (fichier maître), TikTok 200, Instagram 320, YouTube 800, LinkedIn 400. |
| `reseaux/couvertures/` | Bannière YouTube 2560 x 1440 (texte dans la zone sûre centrale de 1235 x 338), couverture de page LinkedIn 1128 x 191, bannière de profil LinkedIn 1584 x 396. |
| `reseaux/modeles/` | Instagram : publication 1080 x 1350, story 1080 x 1920, trois couvertures « à la une ». Couvertures TikTok et Reels : `videos/couvertures/`. |
| `couleurs/` | `palette.css`, `palette.json`, `contrastes.md` (WCAG 2.2 AA). |
| `typographies/` | Source Serif 4 et Inter (OFL 1.1) avec leurs licences ; `LICENCES.md`. |
| `animation/` | `logo-anime.svg` (SVG et CSS), `logo-anime.lottie.json` (Lottie), `logo-anime.html` (démonstration). |
| `videos/` | Trois vidéos verticales 9:16 (6, 14 et 7 s) : pages HTML animées, MP4 dans `videos/mp4/`, couvertures, `enregistrer.md`. |
| `outils/` | Scripts qui produisent tout le kit à partir d'une seule géométrie (`marque.py`). |
| `charte.md` | Charte : logo, zone de protection, interdits, couleurs, typographie, mouvement, ton. |
| `integration-site.md` | Fichiers à remplacer dans `web/public/` et `web/src/components/Logo.tsx`, pour une session ultérieure. |

## Régénérer le kit

Besoins : Python 3 avec fontTools et Pillow, Google Chrome (rendu des PNG, sans interface). Depuis la racine du
dépôt :

```bash
python3 -I brand/outils/glyphes.py
python3 -I brand/outils/generer.py
python3 -I brand/outils/images.py
python3 -I brand/outils/animation.py
python3 -I brand/outils/videos.py
python3 -I brand/outils/contrastes.py
```

Export MP4 des vidéos (nécessite ffmpeg, installé par `brew install ffmpeg`) :

```bash
python3 -I brand/outils/videos_mp4.py
```

Pour changer de nom de marque : modifier `GLYPHES_MOT` dans `outils/glyphes.py`, relancer les commandes, puis
revoir les textes des visuels (`outils/images.py`, `outils/videos.py`).
