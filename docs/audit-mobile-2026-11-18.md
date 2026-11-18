# Audit mobile de Lexia, 18 novembre 2026 (D101)

Deux parties : le site sur téléphone (`web/`) et l'application iOS en Swift (`/Users/arthur./Desktop/lexia/lexia-ios`).
Classement : Critique (bloque l'usage ou la publication), Important (gêne réelle ou risque de refus), Mineur.
État : « corrigé » (dans ce commit pour le site, dans le dossier de l'app pour iOS) ou « à faire ».
Les références fichier:ligne renvoient au code d'avant correction (site : commit 4e1d3ea ; app : état du 16 novembre).

## Méthode

- Site : lecture de `web/src` et de `web/index.html`. Rendu à 375 x 812 px en émulation tactile (Chromium du
  panneau navigateur) avec un faux serveur d'API reprenant les données des tests : `/app` (Mon espace,
  Assistant, réponse, panneau de source), `/compte`, `/tarifs`. Mesure des zones tactiles et du débordement.
  Pas d'essai sur un vrai iPhone ni un vrai Android : Safari iOS (barre d'outils flottante, clavier) n'est
  pas reproduit par l'émulation.
- App iOS : lecture des 2 182 lignes Swift, du manifeste de confidentialité, d'`Info.plist` et de
  `PUBLICATION.md` ; comparaison de chaque appel avec `api/` et `web/src/lib/api.ts`. Compilation avec Xcode 16.1
  (contournement du catalogue d'images décrit dans le README de l'app), écrans de connexion et d'inscription
  vérifiés au simulateur (iPhone 16, iOS 18.1). Les parcours connectés n'ont pas été rejoués.

## Partie 1 : le site sur téléphone

Ce qui va bien : pas de débordement horizontal à 375 px ; champs à 16 px sur écran tactile (pas de zoom
d'iOS, `index.css`) ; attributs `autocomplete` et `inputmode` justes (e-mail, mots de passe, code à usage
unique) ; JavaScript de 115 ko compressé, aucune police à télécharger, administration et QR code chargés à la
demande, fichiers `/assets` compressés et mis en cache un an par nginx : correct en 4G.

| # | Gravité | Constat et scénario | Référence | État |
|---|---|---|---|---|
| W1 | Important | Barre du bas sans marge pour la barre d'accueil de l'iPhone : `viewport-fit=cover` absent, donc `env(safe-area-inset-bottom)` vaut 0. Site ajouté à l'écran d'accueil ou Safari barre repliée : les onglets « Espace » à « Biblio » passent sous le trait d'accueil et se touchent mal. Même chose pour les boutons du bas du panneau de source. | `web/index.html:6`, `web/src/components/Layout.tsx:51`, `SourcePanel.tsx:123` | corrigé |
| W2 | Important | Ni manifeste, ni icône Apple, ni couleur de thème. « Ajouter à l'écran d'accueil » donne une capture de page en guise d'icône et le site s'ouvre dans un onglet. | `web/index.html` | corrigé : `manifest.json` (plein écran, départ sur `/app`), icônes 180, 192 et 512 px tirées de l'icône de l'app iOS, `theme-color` |
| W3 | Mineur | Clavier du téléphone : la touche Entrée envoie la question, impossible d'aller à la ligne (pas de Maj), et l'aide « Maj + Entrée » est fausse sur téléphone. | `web/src/components/Chat.tsx:67-71`, `:233` | corrigé : sur écran tactile Entrée va à la ligne, le bouton envoie, l'aide est masquée |
| W4 | Mineur | Clavier ouvert : la barre du bas (fixe) peut recouvrir le champ de saisie quand on fait défiler. | `Layout.tsx:51` | corrigé : barre masquée tant qu'un champ de texte a le focus (téléphone seulement, `index.css`) |
| W5 | Mineur | Mon espace : la conversation est une zone de 560 px qui défile dans la page qui défile ; sur un écran de 812 px le doigt reste piégé dans l'une ou l'autre. | `Chat.tsx:163` | corrigé : zone limitée à partir de 621 px seulement |
| W6 | Mineur | Questionnaire limité à `90vh` : sur iOS, `vh` ignore les barres de Safari et le bas de la fenêtre est coupé. | `QuizModal.tsx:89` | corrigé (`90dvh`) |
| W7 | Mineur | Zones tactiles sous 44 px : boutons de fermeture 33 x 35 px, flèches des cartes Sources et Bibliothèque 11 x 21 px. | `SourcePanel.tsx:76`, `QuizModal.tsx:98`, `Cartes.tsx:21` | corrigé (44 px) |
| W8 | Mineur | Autres zones sous 44 px : pastille du compte (31 px), suggestions et types d'aide (35 px), lignes des réponses du questionnaire. | `Layout.tsx:148`, `Chat.tsx:114`, `:155`, `QuizModal.tsx:184` | à faire |
| W9 | Mineur | iPhone à l'horizontale avec `viewport-fit=cover` : le contenu pourrait passer sous l'encoche. | `index.css` | traité avec W1 : marges `safe-area-inset-left/right` sur la page et le panneau de source |

## Partie 2 : l'application iOS

Dossier : `/Users/arthur./Desktop/lexia/lexia-ios` (projet `Lexia.xcodeproj`, SwiftUI, iOS 17). Ce dossier n'a pas
de dépôt git à lui : il est seulement couvert par un dépôt créé à la racine du dossier personnel (distant
`Linnix11/day2`). Les corrections ci-dessous n'y sont donc pas versionnées ; une copie de l'état d'avant est
dans le dossier temporaire de la session.

Ce qui va bien : aucun décodage cassé par les changements du 18 novembre (champs ajoutés ignorés, champs
obligatoires toujours présents) ; aucun prix, bouton d'achat, ni écran de paiement ou de rétractation ;
suppression du compte dans l'app (règle 5.1.1(v)) ; avertissement « réponses générées par une intelligence
artificielle » et signalement d'une réponse (motifs) ; pas d'exception ATS ; adresse d'API modifiable en
Debug seulement ; favoris chiffrés au repos et rangés par compte ; textes en styles système (Dynamic Type),
sauf le logo ; manifeste de confidentialité cohérent avec le code (e-mail, contenu, UserDefaults CA92.1,
aucun pistage, aucune API d'horodatage de fichier).

| # | Gravité | Constat et scénario | Référence | État |
|---|---|---|---|---|
| I0 | Critique (publication) | Un étudiant qui a payé sur le site retrouve ses limites plus hautes dans l'app, sans achat intégré : cas de la règle 3.1.3(b), refus probable. Décision de l'éditeur (achat intégré, app limitée à la formule gratuite, ou relecture en l'état). | `PUBLICATION.md`, section 1 | à décider |
| I1 | Important | Lien de confirmation collé jamais reconnu : depuis D94 le jeton est après `#`, l'app ne lit que `?jeton=`. Le bouton « Confirmer avec ce lien » reste grisé ; sans adresse confirmée, questions, quiz et dépôts sont refusés (403). | `Vues/AuthView.swift:211-218` ; `api/auth.py:360` | corrigé (`#` et `?` lus) |
| I2 | Important | Une erreur passagère (502 au rafraîchissement du profil après une réponse) déconnecte l'étudiant et fait perdre la réponse. Même défaut que D3, corrigé sur le site. | `Modele/AppModel.swift:60`, appelé par `QuestionView.swift:108`, `QuizView.swift:63` | corrigé (seuls une session absente ou un 401 déconnectent) |
| I3 | Important | Réponse directe jamais affichée : la synthèse sourcée de tête (D89) manque, favoris et partage la perdent. | `Modele/Modeles.swift:100-113`, `Vues/QuestionView.swift:137` ; `web/src/components/Reponse.tsx:169` | corrigé (bloc « L’essentiel » en tête, partage compris) |
| I4 | Important | Cours .odt et .pptx impossibles à choisir, aide « PDF, Word ou texte ». | `Vues/MonEspaceView.swift:16-18`, `:45` ; `api/extraction.py:33` | corrigé |
| I5 | Important | Pas de « mot de passe oublié » : un étudiant qui l'a oublié reste bloqué. | `Vues/AuthView.swift` ; `api/auth.py:414` | corrigé (envoi depuis l'app ; le lien s'ouvre sur le site) |
| I6 | Important | Inscription sans la case « J’ai 15 ans ou plus » que le site exige (CGU, article 3) : un enfant de 12 ans crée un compte sans rien déclarer. | `Vues/AuthView.swift:71-78` ; `web/src/site/Auth.tsx:119`, `:174` | corrigé |
| I7 | Important (règle 3.1.1) | Le message de limite de l'API (« ou passez à une formule supérieure ») s'affiche tel quel dans l'app : invitation à acheter hors de l'app. | `Modele/API.swift:100-103` ; `api/main.py:232-233`, `api/cours.py:250-251` | corrigé dans l'app (phrase retirée) |
| I8 | Important (règle 3.1.1) | CGU, confidentialité et mentions légales s'ouvrent sur le site, dont l'en-tête montre « Tarifs » et mène au paiement. Un relecteur peut y voir un renvoi vers un achat extérieur. | `Vues/AuthView.swift:76-77`, `Vues/CompteView.swift:33-35` | à faire : version des pages légales sans en-tête de vente (paramètre `?app=1` par exemple) ou texte dans l'app |
| M1 | Mineur | Erreurs 502, 504 et 524 affichées « Erreur inattendue (504) ». | `Modele/API.swift:31-39` ; `web/src/lib/api.ts:311-320` | corrigé |
| M2 | Mineur | Citations lues « crochet S1 crochet » par VoiceOver ; en grand texte, la rangée de citations déborde ; boutons « mini » difficiles à toucher. | `Vues/QuestionView.swift:181-189` | corrigé (libellé « Source : article… », passage à la ligne, taille « small ») |
| M3 | Mineur | Codes de secours et clé de double authentification copiés dans le presse-papiers universel, sans expiration. | `Vues/CompteView.swift:116`, `:150` | corrigé (cet appareil seulement, effacés après 2 minutes) |
| M4 | Mineur | Avis envoyé en silence : un 403 (adresse non confirmée) est avalé, l'étudiant croit son avis reçu. | `Vues/QuestionView.swift:322` | à faire |
| M5 | Mineur | Fraîcheur des sources absente (`/fraicheur`, mention d'une source ancienne). | `api/main.py:302-312` ; `web/src/components/Reponse.tsx:68-99` | à faire |
| M6 | Mineur | Les 20 matières dans une seule liste, sans regroupement L1, L2, L3. | `Vues/Style.swift:106-108` ; `api/main.py:320-325` | à faire |
| M7 | Mineur | Avertissement « pages scannées » d'un cours déposé non affiché. | `Modele/Modeles.swift:237-247` ; `web/src/components/MesCours.tsx:32` | à faire |
| M8 | Mineur | Cookie de session (30 jours) gardé par `HTTPCookieStorage`, hors du trousseau : inclus dans les sauvegardes de l'appareil. | `Modele/API.swift:65-67` | à faire : garder le jeton dans le trousseau (`AfterFirstUnlockThisDeviceOnly`) et le remettre dans les requêtes |
| M9 | Mineur | Démarrage sans réseau : écran de connexion au lieu d'un message « hors ligne ». Déconnexion hors réseau : session encore valide côté serveur. | `Modele/AppModel.swift:43-47`, `Modele/API.swift:190-192` | à faire |

## Ce qui reste à l'éditeur

1. Décider de la voie App Store pour les formules payantes (I0), puis traiter I8.
2. Créer un dépôt git propre au dossier `lexia-ios` (les corrections du jour n'y sont pas versionnées).
3. Essayer le site sur un vrai iPhone (Safari, puis ajouté à l'écran d'accueil) et un vrai Android après la
   prochaine publication : barre du bas, clavier, icône.
4. Rejouer l'app avec un compte (question, quiz, dépôt d'un .pptx, lien de confirmation collé) sur une API locale.
