# Charte graphique de Lexia

Version 1, 23 novembre 2026. Elle prolonge la direction choisie le 13 novembre 2026 (système de design
« Identité visuelle Lexia » et planche « Logos Lexia », proposition 6 « Le signet ») et les couleurs du site
(`web/src/index.css`). Tous les fichiers cités sont dans `brand/` ; l'index du kit est `brand/README.md`.

## 0. Avertissement : la marque n'est pas vérifiée

Le nom « Lexia » n'a pas été apprécié par un conseil en propriété industrielle. Le relevé du 17 novembre 2026
(`docs/marque-lexia.md`) trouve des marques « LEXIA » enregistrées pour des logiciels et services éducatifs dans
l'Union européenne (EUIPO 015377401 et OMPI 1647070, Lexia Learning Systems LLC, classes 9, 41 et 42) et pour des
services juridiques en France (INPI 4010966, classe 45). Conséquences pour l'identité :

- **Rien n'est imprimé, déposé, acheté ni publié** avec ce logo (comptes de réseaux, goodies, publicité) avant
  l'avis d'un conseil, comme le prévoit déjà le plan marketing (`docs/marketing/plan.md`, partie 1).
- **Le symbole ne dépend pas du nom.** Le signet porte le signe § et non plus la lettre L : il reste valable si la
  marque change de nom. Seul le logotype (le mot) serait à refaire.
- **Changer de nom coûte une commande.** Remplacer le mot dans `brand/outils/glyphes.py` (constante
  `GLYPHES_MOT`), puis relancer les scripts (`brand/README.md`, partie « Régénérer le kit ») : logos, icônes,
  images, animations et vidéos sont recalculés. Les textes des visuels qui citent l'adresse du site sont à revoir
  à la main.
- Le symbole lui-même (signet et §) est une forme simple ; s'il devait être déposé comme marque figurative, le
  faire examiner en même temps que le nom.

## 1. Le symbole : le signet §

Un marque-page vert forêt, un liseré or en tête, le signe § en réserve. Il dit ce que fait Lexia : garder la bonne
page d'un code, d'un manuel ou d'une fiche, et renvoyer à l'article de loi. Le § est le signe que le site affiche
déjà devant chaque article cité ; il remplace le « L » du signet du 13 novembre pour que le symbole survive à un
changement de nom.

Construction (grille de 64 unités, `brand/outils/marque.py`) : signet de 34 x 56 unités, coins supérieurs
arrondis de 2 unités, encoche dont la pointe remonte de 13 unités, liseré de 6 unités, signe § de 24,5 unités en
Source Serif 4 (graisse 650, taille optique 20) centré à 28,2 unités du haut.

Sous 24 px de haut, le § disparaît (`icones/favicon-16.png`) : la silhouette et le liseré suffisent.

## 2. Les versions du logo

| Version | Fichier SVG (`logos/svg/`) | Usage |
|---|---|---|
| Horizontal | `lexia-horizontal-couleur.svg` | En-tête du site, signatures, documents, bas de visuels. Version par défaut. |
| Principal (empilé) | `lexia-principal-couleur.svg` | Formats hauts ou carrés : story, carte de fin, couverture, affiche. |
| Symbole seul | `lexia-symbole-couleur.svg` | Avatar, favicon, icône d'application, tampon discret, quand le nom est déjà écrit à côté. |
| Inverse | `…-inverse.svg` | Sur fond forêt `#315e4b` ou forêt foncé `#244735` : signet clair, § vert, mot clair. |
| Monochrome sur clair | `…-mono-clair.svg` | Une seule encre `#202724` : impression noir et blanc, tampon, gravure, fax. Le § et une fente sous le liseré sont évidés. |
| Monochrome sur foncé | `…-mono-fonce.svg` | Blanc seul sur photo sombre, vidéo ou fond très foncé. |

Exports PNG à fond transparent dans `logos/png/` : symbole en 64, 128, 256, 512 et 1024 px ; horizontal en 320,
640, 1280 et 2560 px de large ; principal en 256, 512 et 1024 px de large. Toujours préférer le SVG à l'écran.

Dans un texte, le nom s'écrit « Lexia » ; le logotype seul s'écrit « lexia », en minuscules.

## 3. Zone de protection et tailles minimales

- **Zone de protection** : autour du logo, un espace libre au moins égal à la moitié de la largeur du signet
  (17 unités de la grille de 64). Aucun texte, bord de
  page ni autre logo dans cette zone.
- **Tailles minimales** :

| Version | Écran | Impression |
|---|---|---|
| Horizontal | 96 px de large | 25 mm de large |
| Principal | 64 px de large | 18 mm de large |
| Symbole avec § | 24 px de haut | 7 mm de haut |
| Symbole sans § (silhouette) | 16 px de haut | non imprimé |

## 4. Usages interdits

- Recolorer le logo hors des quatre versions prévues, ajouter un dégradé, une ombre, un contour, un effet 3D.
- Étirer, comprimer, incliner, faire pivoter le logo ou le symbole.
- Changer la police du mot, l'écrire en capitales (« LEXIA ») ou avec une majuscule dans le logotype.
- Déplacer le symbole par rapport au mot, changer leur rapport de taille, recomposer le logo à la main.
- Remettre une lettre dans le signet, ou reprendre l'ancien monogramme (« L » dans un carré).
- Poser le logo couleur sur le fond forêt (utiliser l'inverse) ou sur une photo chargée sans aplat papier.
- Écrire du texte en or `#bd8951` : 2,78:1 sur papier, 3,03:1 sur surface (voir partie 5).
- Animer le logo autrement que par l'animation officielle (`animation/`), ou le faire clignoter.
- Utiliser le logo avant l'avis sur la marque (partie 0) pour un dépôt, un objet imprimé ou un compte public.

## 5. Couleurs

Valeurs du site (`web/src/index.css`), sauf « or texte », ajouté pour un mot en or sur fond clair. Fichiers :
`couleurs/palette.css` (variables CSS), `couleurs/palette.json`, contrastes calculés dans
`couleurs/contrastes.md` (formule WCAG 2.2, script `outils/contrastes.py`).

| Nom | Hex | Rôle |
|---|---|---|
| Forêt | `#315e4b` | Couleur de marque : signet, boutons, liens, fonds pleins |
| Papier | `#f5f4ef` | Fond de page et des visuels clairs ; pas de blanc pur en grand aplat |
| Encre | `#202724` | Texte et logotype sur fond clair |
| Or | `#bd8951` | Liseré du signet et filets ; jamais pour du texte |
| Forêt foncé | `#244735` | Survol, fonds sombres |
| Surface | `#fffefa` | Cartes posées sur papier ; texte et signet sur fond forêt |
| Menthe | `#e7efe9` | Puce active, citation au survol, badge |
| Sauge | `#e2e8e1` | Survol sur menthe |
| Crème | `#fbf7ef` | Encadrés d'information douce |
| Ligne | `#e4e4dc` | Bordures décoratives |
| Gris | `#666e69` | Texte secondaire |
| Brique | `#8c4a36` | Erreurs, actions destructrices |
| Brique fond | `#f6e9e4` | Fond des messages d'erreur |
| Ocre | `#746347` | Texte des encadrés crème |
| Or texte | `#8a6534` | Mot ou chiffre en or sur papier ou surface |

Contrastes vérifiés (niveau AA : 4,5:1 pour le texte, 3:1 pour le grand texte et les éléments graphiques) :

| Paire | Rapport | Verdict |
|---|---|---|
| Encre sur papier | 13,85:1 | conforme |
| Forêt sur papier | 6,73:1 | conforme |
| Forêt sur surface | 7,34:1 | conforme |
| Surface sur forêt (texte, logo inverse) | 7,34:1 | conforme |
| Surface sur forêt foncé | 10,26:1 | conforme |
| Gris sur papier | 4,77:1 | conforme |
| Brique sur surface | 6,61:1 | conforme |
| Ocre sur crème | 5,43:1 | conforme |
| Or texte sur papier | 4,78:1 | conforme |
| Or sur papier | 2,78:1 | décoratif seulement (liseré, filet) |
| Or sur forêt | 2,42:1 | décoratif seulement |

Le liseré or n'est pas porteur d'information : le logo reste reconnaissable sans lui (versions monochromes), ce
qui respecte le critère 1.4.11. Proportions conseillées d'un visuel : papier ou forêt en fond (environ 70 %),
encre et forêt pour le texte, or en touche (moins de 5 %).

## 6. Typographie

| Rôle | Police | Licence | Réglages |
|---|---|---|---|
| Titres, signature, logotype | Source Serif 4 | SIL Open Font License 1.1 | Graisse 400 pour les titres (jamais de gras), taille optique 60 pour les grands titres ; logotype en 500 converti en tracés |
| Texte, interface, légendes | Inter | SIL Open Font License 1.1 | 400 pour le texte, 600 pour les renvois et l'adresse, 700 en capitales espacées (0,14 em) pour les surtitres |
| Site (en attendant) | Georgia, puis police système | Polices installées sur l'appareil, non redistribuées | Le site ne charge aucune police (politique de contenu stricte) ; Georgia reste sa police de titres tant que l'intégration n'est pas décidée (`brand/integration-site.md`) |

Fichiers et licences : `typographies/` (polices d'origine, textes de licence et `LICENCES.md`). La licence OFL
autorise l'usage commercial, l'intégration dans des images, PDF, vidéos et sites, et la redistribution avec le
texte de licence ; elle interdit la vente de la police seule. Le logotype converti en tracés n'est pas une police
et n'est pas soumis à la licence.

Tailles conseillées en 1080 px de large (publication, story, vidéo) : titre 64 à 76 px, texte 32 à 42 px,
légende 26 à 28 px, jamais moins de 24 px. Espace fine insécable avant « ? », « ! », « : » et « ; », guillemets
français « », apostrophe typographique ’, « 1<sup>er</sup> » en exposant.

## 7. Mouvement

- Animation officielle (2,2 s) : le corps du signet se déroule depuis le haut, le liseré s'étend, le § apparaît,
  puis les lettres une à une. Courbe d'accélération `cubic-bezier(.2, .8, .2, 1)`, sans rebond.
- Fichiers : `animation/logo-anime.svg` (SVG et CSS, autonome), `animation/logo-anime.lottie.json` (Lottie, lu
  par lottie-web, licence MIT), page de démonstration `animation/logo-anime.html`.
- Vidéos verticales : `videos/` (procédure d'export dans `videos/enregistrer.md`).
- Moins de mouvement : si le système le demande (`prefers-reduced-motion: reduce`), le SVG, la page Lottie et les
  vidéos HTML affichent directement l'état final. Pas de clignotement, pas plus de trois changements par seconde.

## 8. Ton

- Sérieux et fiable, jamais solennel : des phrases courtes, le vocabulaire juridique exact, une source citée pour
  chaque affirmation de droit (« Code civil, article 1137 », comme sur Légifrance).
- Site et e-mails : vouvoiement. TikTok et Instagram : tutoiement. LinkedIn : vouvoiement
  (`docs/marketing/plan.md`, partie 3).
- Pas de point d'exclamation, pas de superlatif (« le meilleur », « le seul », « n°1 »), pas d'emoji décoratif.
- Signature : « Le droit, sources à l'appui. » Phrase d'appui : « Réviser le droit avec les textes officiels. »
- N'écrire que des phrases autorisées par `docs/marketing/contenus-mois-1.md` (« Phrases autorisées ») ; les
  phrases interdites y sont listées. Relire chaque article cité le jour de la publication.
- Transparence : une reconstitution d'interface le dit à l'écran ; un visuel généré par IA le dit en légende.

## 9. Formats prêts à l'emploi

Voir `brand/README.md` pour la liste complète : icônes et favicon, avatars des réseaux, bannière YouTube,
couvertures LinkedIn, modèles Instagram (publication 4:5, story, couvertures « à la une »), image Open Graph
1200 x 630 et couvertures des trois vidéos. Les dimensions des réseaux viennent de guides publiés en 2026
(Hootsuite, Sprout Social, Buffer) qui ne concordent pas toujours : vérifier dans l'aide de chaque réseau avant
la mise en ligne.
