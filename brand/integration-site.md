# Note d'intégration du nouveau logo dans le site (pour une session ultérieure)

Rédigée le 23 novembre 2026. Rien n'est intégré : les sessions « recette » et « SEO et GEO » modifient `web/` en ce
moment. À faire après leur fusion dans `main`, et après l'avis sur la marque (`brand/charte.md`, partie 0) pour
tout ce qui est public et durable (icône d'application installée, image de partage).

## Fichiers à remplacer dans `web/public/`

| Fichier actuel | Remplacer par | Remarque |
|---|---|---|
| `favicon.svg` (signet avec « L ») | `brand/icones/favicon.svg` | Même principe, le § remplace le L ; cadre 56 x 56 au lieu de 40 x 64. |
| `apple-touch-icon.png` (L crème sur forêt, tiré de l'app iOS) | `brand/icones/apple-touch-icon.png` (180 x 180, opaque) | |
| `icone-192.png`, `icone-512.png` | `brand/icones/icone-192.png`, `brand/icones/icone-512.png` | |
| `manifest.json` | reprendre `brand/icones/manifest-exemple.json` | Ajoute les icônes `maskable` ; garder le `name`, `start_url` et `theme_color` actuels si la recette les a changés. |
| (nouveau) | `brand/icones/icone-maskable-192.png`, `brand/icones/icone-maskable-512.png` | Référencés par le manifeste. |
| (nouveau) | `brand/icones/favicon.ico` (16, 32 et 48 px) | Pour les navigateurs et lecteurs de flux qui demandent `/favicon.ico` sans lire le HTML. |
| `og-lexia.png` (créé par la session SEO, D116, référencé par `IMAGE_PARTAGE` dans `web/src/site/seo.ts`, balises écrites par `web/src/site/publication.ts`) | `brand/open-graph/og-image-1200x630.png`, copié sous le nom `og-lexia.png` | Aucun changement de code : même nom, même taille 1200 x 630. Les balises `og:image:width` (1200), `og:image:height` (630) et `og:image:alt` restent justes. |

## Autres fichiers à aligner hors du site

- `docs/marketing/production/source/visuels.py` (production marketing du mois 1) dessine encore le signet avec
  « L » et le mot en Gelasio dans ses fonctions `signet()` et `logotype()`. Les remplacer par les SVG de
  `brand/logos/svg/` (le script le prévoit dans son en-tête), puis relancer la production des visuels.
- `docs/business/` (pitch deck) : reprendre `brand/logos/svg/lexia-horizontal-couleur.svg` ou
  `lexia-principal-inverse.svg` si le deck affiche un logo.

## Lignes à vérifier dans `web/index.html`

```html
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/manifest.json">
```

## Logo dans les pages

- Le symbole du site est le composant `Signet` de `web/src/components/Logo.tsx` (signet avec « L » en texte
  Georgia), importé par `components/Layout.tsx`, `Site.tsx`, `site/Public.tsx` et `site/Admin.tsx`. Remplacer ses
  trois éléments par les trois tracés de `brand/logos/svg/lexia-symbole-couleur.svg` (corps, liseré, §), avec
  `viewBox="15 4 34 56"` et une largeur égale à `hauteur * 34 / 56`. Le § devient un tracé : plus de dépendance à
  la police installée.
- À côté, le mot « lexia » est du texte (`font-display`, donc Georgia, 21 px, dans `site/Public.tsx`). Le garder en
  texte (accessible, net) ou le remplacer par `lexia-horizontal-couleur.svg` en ligne (`role="img"`,
  `aria-label="Lexia"`), hauteur 28 à 32 px. Les deux restent cohérents.
- Sur fond forêt (pied de page éventuel) : `lexia-horizontal-inverse.svg`.
- Écran de chargement : `brand/animation/logo-anime.svg` (s'arrête de lui-même, respecte « moins de mouvement »).

## Police des titres

Le site affiche ses titres en Georgia sans charger de police. Deux options, à trancher par une décision :

1. Garder Georgia (aucun changement, aucune requête). Les visuels en Source Serif 4 restent très proches.
2. Héberger Source Serif 4 en WOFF2 sur le serveur de Lexia (pas de Google Fonts, la politique de contenu reste
   `font-src 'self'`), en sous-ensemble latin et une seule graisse (400) : environ 60 à 90 Ko. Voir
   `brand/typographies/LICENCES.md` pour le nom à donner à une version allégée.

## Contrôles après intégration

- `npm test` dans `web/`, puis la page d'accueil et `/app` sur téléphone : icône d'onglet, ajout à l'écran
  d'accueil (iOS et Android), icône masquée correcte sur Android (zone sûre respectée : le signet occupe 56 % de
  la hauteur).
- Partage d'un lien sur LinkedIn ou dans une messagerie : l'image 1200 x 630 doit apparaître.
- L'application iOS (hors dépôt) garde son icône « L » tant qu'elle n'est pas refaite ; sa nouvelle icône peut
  partir de `brand/icones/icone-1024.png` (1024 x 1024, format demandé par l'App Store) ou de
  `brand/icones/icone-app.svg`.
