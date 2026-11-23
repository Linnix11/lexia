# Vidéos verticales : lecture et enregistrement en MP4

Trois vidéos au format 9:16 (1080 x 1920 px), écrites en HTML et CSS. Les MP4 sont fournis dans `mp4/` (H.264,
30 images par seconde, exportés image par image le 23 novembre 2026 avec ffmpeg 9.0.2). Pour les refaire après une
modification, suivre la méthode 1 ci-dessous.

| Fichier | Durée | Contenu | Couverture et MP4 |
|---|---|---|---|
| `01-intro-logo.html` | 6 s | Le signet se déroule, « lexia » apparaît lettre par lettre, puis la signature « Le droit, sources à l'appui. » | `couvertures/01-intro-logo.png`, `mp4/01-intro-logo.mp4` |
| `02-demo-question-reponse.html` | 14 s | « Une question, une réponse sourcée » : la question sur le dol est tapée, la réponse arrive avec ses renvois [S1] et [S2], la source (Code civil, article 1137) s'ouvre. | `couvertures/02-demo-question-reponse.png`, `mp4/02-demo-question-reponse.mp4` |
| `03-carte-de-fin.html` | 7 s | Logo sur fond forêt, signature, adresse `lexia-axionstudio.cloud`, offre gratuite. | `couvertures/03-carte-de-fin.png`, `mp4/03-carte-de-fin.mp4` |

Textes : uniquement des phrases autorisées par `docs/marketing/contenus-mois-1.md`. Articles cités relus pour le
plan marketing : article 1137 (https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000036829827) et
article 1131 (https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000032040836). Les relire le jour de la
publication. La vidéo 2 est une reconstitution de l'interface : elle le dit en bas d'écran, et elle ne montre que
des fonctions qui existent (renvois numérotés, panneau de la source, lien Légifrance).

## Lire une vidéo

Ouvrir le fichier HTML dans Chrome, Safari ou Firefox (double-clic). La scène s'adapte à la fenêtre ; « Rejouer »
relance l'animation. Si le système demande moins de mouvement (Réglages Système > Accessibilité > Affichage >
Réduire les animations), la page affiche la dernière image ; ajouter `?mouvement` à l'adresse pour la lire.

Paramètres d'adresse : `?t=4.5` fige la scène à 4,5 s ; `?capture` affiche la scène à l'échelle 1 sans commandes ;
`?enregistrer` prépare l'enregistrement d'écran (ci-dessous).

## Méthode 1 (recommandée) : export automatique avec ffmpeg

Image par image, donc sans saccade ni dépendance à la vitesse de la machine.

1. Installer ffmpeg (logiciel libre, gratuit ; déjà installé sur ce Mac depuis le 23 novembre 2026) :

   ```bash
   brew install ffmpeg
   ```

2. Depuis la racine du dépôt :

   ```bash
   python3 -I brand/outils/videos_mp4.py
   ```

3. Les fichiers arrivent dans `brand/videos/mp4/` (H.264, 30 images par seconde, compatibles TikTok, Instagram
   Reels et YouTube Shorts). Compter environ 10 minutes pour les trois vidéos.

## Méthode 2 : sans ffmpeg, enregistrement d'écran sur Mac

Avec un écran Retina, la scène en mode enregistrement mesure 540 x 960 points, soit exactement 1080 x 1920 pixels.

1. Ouvrir la vidéo avec `?enregistrer` à la fin de l'adresse, par exemple
   `file:///…/brand/videos/01-intro-logo.html?enregistrer` (ou cliquer « Mode enregistrement »). Mettre le
   navigateur en plein écran (Ctrl + Cmd + F) : la scène est centrée sur fond noir, figée à la première image.
2. Appuyer sur Maj + Cmd + 5, choisir « Enregistrer la partie sélectionnée », ajuster le rectangle exactement sur
   la scène (bords de la zone claire ou verte), puis cliquer « Enregistrer ».
3. Revenir sur la page et appuyer sur la barre d'espace : l'animation démarre.
4. Arrêter l'enregistrement une demi-seconde après la fin (bouton d'arrêt dans la barre des menus). Le fichier
   `.mov` arrive sur le Bureau.
5. Couper le début et la fin dans QuickTime Player (Édition > Découper, Cmd + T), puis Fichier > Exporter en >
   1080p. TikTok, Instagram et YouTube acceptent le `.mov` ; pour un `.mp4`, iMovie (gratuit) : Fichier > Partager >
   Fichier, ou la méthode 1.

Vérifier la taille obtenue (Cmd + I dans le Finder) : 1080 x 1920. Sur un écran non Retina, la scène fait 540 x 960
pixels : préférer alors la méthode 1.

## Zones sûres des réseaux

Les interfaces de TikTok, Reels et Shorts recouvrent le bas (légende, environ 400 px) et la droite (boutons,
environ 140 px). Les textes importants des trois vidéos sont placés entre 190 et 1 620 px de haut et à 84 px des
bords, y compris la mention « Reconstitution de l'interface » de la vidéo 2 (en haut à droite).
