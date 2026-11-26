# Cartes mentales (v1)

L'étudiant obtient une carte mentale d'une réponse, d'un cours déposé, d'une fiche récupérée ou d'une notion
d'une matière, comme les cartes mentales de NotebookLM (Gemini Notebook), avec une exigence de plus : chaque
article affiché vient des textes fournis et renvoie au texte officiel quand Lexia le connaît. Décision : D112
(`docs/decisions.md`). Comparatif : `docs/comparatif-notebooklm.md` (branche `claude/comparatif-notebooklm-v2`).

## Ce qu'on cartographie

| Quoi | Où dans le site | Texte envoyé au modèle |
| --- | --- | --- |
| Réponse de l'assistant, fiche enregistrée | Sous chaque réponse, à côté du résumé vocal (`Reponse.tsx`) | Le texte de la réponse (12 000 caractères au plus) et les extraits qu'elle cite, relus par le serveur |
| Cours déposé | « Mes cours » (`MesCours.tsx`) | Le texte du cours, lu en base pour son seul propriétaire, 24 000 premiers caractères |
| Fiche récupérée | Page « Cours récupérés » (`CoursRecuperes.tsx`) | Les sections de la fiche, 24 000 premiers caractères |
| Matière | Carte de la matière (« Mes matières », `Vues.tsx`) | 12 extraits officiels trouvés par la recherche habituelle dans les sources de la matière, sur la notion saisie (facultative ; à défaut, l'intitulé de la matière et ses thèmes) |

Lecture des documents : la même que les résumés vocaux (`ResumesVocaux.document`, D106), sans copie.

## Structure

- **Notion centrale** : le sujet, en quelques mots (`titre`).
- **Branches** : 3 à 7 idées principales, dans l'ordre logique du document (conditions, effets, exceptions,
  régime...).
- **Sous-branches** : 0 à 5 par branche, quelques mots chacune.
- **Feuilles « articles »** : sous une branche ou une sous-branche, 3 références au plus (article, décision,
  pourvoi), écrites comme le document les écrit (« article 1240 du Code civil »).

Lien des feuilles vers le texte : extrait officiel fourni qui porte ce numéro (son adresse Légifrance ou
juridiction), sinon article cherché dans l'index par son code et son numéro, version en vigueur aujourd'hui ;
sans code nommé ni extrait, la feuille reste sans lien.

## Génération

- Modèle déjà en place : Gemini au niveau actuel, Groq en secours, même disjoncteur que les réponses
  (`Lexia.generer`).
- Plan hiérarchique en JSON, schéma imposé (`SCHEMA_CARTE_MENTALE`) : objets et listes contrôlés par
  `api/llm/forme.py` (une réponse hors schéma passe au modèle suivant), bornes appliquées par le serveur.
- Bornes : 3 072 jetons de sortie (réflexion comprise chez Gemini), 25 secondes par appel au modèle
  (`CARTES_MENTALES_DELAI_SECONDES`).
- Contrôle (même règle que les citations, `citations.verifier_texte`) : une branche ou une sous-branche dont le
  libellé cite un article, une décision ou un pourvoi absent des extraits envoyés est retirée ; une feuille
  n'est gardée que si elle contient une référence et que cette référence figure dans les extraits envoyés.
  Moins de deux branches vérifiables : pas de carte, rien de décompté.
- Grands arrêts (D138) : une feuille qui désigne un grand arrêt du registre (`registry/grands_arrets.yaml` : nom
  d'usage, pourvoi, requête) parmi les extraits envoyés, ou nommé par le document, prend sa citation d'usage
  (« CE, 30 mars 1916, Compagnie générale d'éclairage de Bordeaux (Gaz de Bordeaux) ») ; un arrêt abandonné est
  suivi de « (arrêt abandonné : n'est plus le droit positif) », un arrêt nuancé de « (solution nuancée depuis) »
  (champ `statut`). Une référence déjà portée par la branche n'est pas répétée sous ses sous-idées.

## Rendu

- SVG maison (`CarteMentale.tsx`, `lib/carteMentale.ts`) : aucune dépendance. Bibliothèques libres examinées
  le 2026-11-20 (`npm view`) : markmap-view 0.18.13 (MIT, dépend de d3 7 entier), react-d3-tree 3.6.7 (MIT,
  d3-zoom, d3-shape, d3-hierarchy, d3-selection et trois autres paquets), mind-elixir 6.0.3 (MIT, 480 Ko
  décompressés), d3-hierarchy 3.1.3 seul (ISC, mise en page sans rendu ni zoom). Toutes ajoutent du poids pour
  un arbre de profondeur 3 que quelques dizaines de lignes disposent. Mesure : +11,7 Ko minifiés (+3,8 Ko gzip)
  pour tout le site (`vite build` avant et après).
- Disposition en arbre horizontal : notion à gauche, branches, sous-branches, feuilles « articles » en
  pastilles soulignées quand elles ont un lien. Couleur par branche, libellés coupés en lignes de 20 à 25
  caractères (6 lignes au plus). Arrêt abandonné : bordure en tirets.
- Zoom (boutons + et -, 50 à 200 %), défilement dans le cadre, repli d'une branche d'un clic (un rond « +n »
  dit combien d'éléments sont cachés), « Tout replier » et « Tout déplier ».
- Export en image PNG (SVG dessiné dans un canvas, deux fois plus net, fond blanc, sans bibliothèque).
- « Imprimer ou PDF » (D138) : dessin entier sur une page A4 paysage, puis plan en liste, liens gardés, mention IA.
- « Copier le plan » (D138) : plan numéroté en texte, avec les références.
- « Réviser » (D138) : sous-idées et références masquées (« ? »), révélées une à une ou toutes, avec un compteur.
- Mobile : cadre défilant de la largeur de l'écran ; la vue en liste est proposée d'abord sous 640 px.
- Accessibilité : le dessin est `aria-hidden` (ses liens hors de l'ordre de tabulation) ; la même carte en
  listes imbriquées est toujours présente pour les lecteurs d'écran, masquée visuellement quand le dessin est
  affiché et révélée dès qu'on y entre au clavier ; branches repliables par des boutons `aria-expanded`,
  feuilles en vrais liens. Bouton « Vue en liste » pour tous.
- Avertissement sous chaque carte : « Carte générée automatiquement : vérifiez avec les textes. »

## Accès et limites

- Route `POST /carte-mentale`, réservée aux comptes à l'adresse confirmée, limite par minute, origine vérifiée,
  place parmi les appels au modèle (comme `/resume-vocal`).
- 5 cartes par jour et par compte (`CARTES_MENTALES_PAR_JOUR`), table `cartes_mentales` de la base des comptes
  (compte, jour, nombre ; effacée après un mois), remboursée si le modèle n'a pas répondu ou si rien n'est
  vérifiable.
- Coût nul : niveaux gratuits des modèles, aucune API payante, aucune bibliothèque ajoutée.

## Plus tard

- Garder les cartes dans « Fiches & révisions » (navigateur) : fait (« Mes cartes mentales », D123), avec une
  recherche dès quatre cartes (D138).
- Une carte qui réunit plusieurs cours déposés d'une même matière.
