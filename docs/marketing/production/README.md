# Production marketing du mois 1

Fait le 23 novembre 2026, sur `main` au commit e12128d, à partir de `docs/marketing/plan.md`,
`docs/marketing/contenus-mois-1.md`, `docs/comparatif-notebooklm.md` et du site en ligne. Rien n'est publié, envoyé,
imprimé ni acheté ; aucun compte n'est créé.

## Contenu

| Dossier ou fichier | Quoi |
|---|---|
| `calendrier-mois-1.md` | Les 26 publications du 30 novembre au 27 décembre 2026 : réseau, format, visuels, légendes prêtes à coller, et ce qui a changé depuis `contenus-mois-1.md` |
| `visuels/` | 74 images : carrousels et images en 1080 × 1350, stories et couvertures de vidéos en 1080 × 1920, images LinkedIn en 1200 × 627 ; 4 carrousels en document PDF pour LinkedIn ; `manifeste.json` (liste par publication) ; `AMB/` : bandeau « Publicité » des ambassadeurs, fond transparent |
| `videos/storyboard-V1.pdf` à `V5.pdf` | Storyboards illustrés plan par plan (durée, texte à l'écran, voix off, notes), et en dernière page : tournage, sous-titres, musique gratuite avec licences lues |
| `presse/dossier-de-presse.pdf` | Présentation, chiffres clés datés avec leur source, ce que Lexia ne fait pas encore, captures, fondateur (bio à compléter), contact |
| `presse/captures/` | Captures du site en ligne (accueil, tarifs, inscription, accueil sur téléphone), 23 novembre 2026, en double définition |
| `emails/sequence-inscrits.md` | Bienvenue, première question, questionnaires et cartes, avant les partiels, lettre des partiels ; réservés aux comptes qui ont consenti (D110) |
| `emails/modele-email.html` | Gabarit HTML commun des e-mails |
| `landings/` | Textes des pages : L1 en difficulté, révisions des partiels, associations, ambassadeurs |
| `associations/email-associations.md` et `.txt` | E-mail prêt à envoyer, relance, réponse ; version texte à coller |
| `ambassadeurs/kit-ambassadeur.pdf` | Kit en 5 pages : Lexia en bref, phrases autorisées et interdites, rôle, sept règles obligatoires, mentions à copier, candidature |
| `impression/flyer-a5.pdf` | Flyer A5 recto, avec QR code vers le site |
| `source/` | Générateurs (`visuels.py`, `documents.py`), contrôle des formules interdites (`verifier.py`), polices libres et leurs licences, QR code ; les pages HTML intermédiaires (`source/html/`) sont refaites à chaque rendu et ne sont pas versionnées |

## Avant toute utilisation

1. **API Gemini au niveau payant** (plan, partie 1). En ligne le 23 novembre 2026 : `gemini_payant: false`. Tant que
   ce n'est pas fait, ne rien publier qui fasse venir du public, ne pas envoyer l'e-mail aux associations ni le
   dossier de presse. Si le passage se fait après le 30 novembre, décaler le calendrier.
2. **Avis d'un conseil en propriété industrielle sur « Lexia »** (plan, partie 7.6) : aucune impression du flyer,
   aucune dépense, aucun nom de compte définitif avant. Les générateurs permettent de changer le nom et le logo
   puis de tout refaire en une commande.
3. **Le jour de chaque publication** : relire le chiffre ou la date cités sur le site (`/api/formules`,
   `/api/fraicheur`, `/api/matieres`) et refaire chaque démonstration en vrai avant de la filmer.

## Ce qui a été vérifié, le 23 novembre 2026

| Affirmation | Preuve |
|---|---|
| Plus de 900 000 passages officiels | Index reconstruit le 19 novembre : 926 481 passages dont 10 508 de fiches pratiques (`docs/cours-libres.md`), soit environ 916 000 passages officiels. **Le chiffre « environ 926 000 passages officiels » du brief est inexact** : il compte les fiches de service-public.gouv.fr, qui ne sont pas des sources officielles et ne servent jamais aux réponses. Écrire « plus de 900 000 ». |
| Codes et lois mis à jour chaque nuit | `/api/fraicheur` : textes au 22 novembre 2026, Conseil d'État au 19 novembre ; `/api/sante` : `corpus_a_jour: true` |
| Jurisprudence en retard | `/api/fraicheur` : Cour de cassation 16 et 17 septembre 2026, Conseil constitutionnel 16 octobre 2026. D113 (site du Conseil constitutionnel) est dans `main`, pas encore en ligne |
| 20 matières, leur liste | `/api/matieres` |
| Formules et quotas | `/api/formules` : 0 €, 4,99 €, 9,99 € ; 10, 100, 300 questions ; 2, 20, 100 questionnaires ; 3, 30, 100 cours |
| Paiement en ligne inactif | `/api/config` : `paiement: false` |
| Cartes à retourner en ligne (D104) | Code du site en ligne : « Ajouter aux cartes », « Je savais » présents dans le module de l'espace étudiant |
| Résumés vocaux en ligne (D106) | `/api/resume-vocal/quota` répond 401 (route présente) ; code du site en ligne. 5 par jour (`RESUMES_VOCAUX_PAR_JOUR`) |
| Scans et photos lus par OCR en ligne (D107) | Code du site en ligne : formats JPEG et photo acceptés au dépôt |
| Cartes mentales **pas** en ligne (D112) | `/api/carte-mentale/quota` répond 404 ; absent du code du site en ligne. Exclues de tous les contenus |
| Consentement aux e-mails en ligne (D110) | `/api/auth/infos-email` répond 401 (route présente) ; question « Comment avez-vous connu Lexia ? » présente |
| 64 grands arrêts, 26 anciens numéros | `api/grands_arrets.py` (20 + 44), `api/concordance.py` (26) |
| Textes du Code civil cités (1103, 1104, 1120, 1131, 1134, 1137, 1148, 1178, 1179, 1193, 1199, 1231-1, 1240, 1241, 1382) | Relus dans leur version en vigueur dans le corpus local (`data/passages/code_civil.jsonl`, archive DILA du 8 novembre 2026, mise à jour du 16 novembre) |
| Mentions de l'éditeur | `/api/config` (nom, adresse, statut, contact) |
| Mention de l'imprimeur sur le flyer | Loi du 29 juillet 1881, article 3, lue dans le corpus : tout écrit rendu public porte le nom et le domicile de l'imprimeur |

### Phrases autorisées (mises à jour)

Celles de `contenus-mois-1.md`, plus trois qui sont devenues vraies depuis le 19 novembre :

- « Déposez vos cours (PDF, Word, PowerPoint, OpenDocument, RTF, texte, et même un scan ou une photo) et
  confrontez-les au droit en vigueur. »
- « Questionnaires corrigés avec les sources, et cartes à retourner avec répétition espacée. »
- « Résumés à écouter : une réponse, une fiche ou un cours résumé en 2 à 5 minutes, lu par la voix de votre
  appareil. »

### Phrases interdites (mises à jour)

« Jurisprudence à jour chaque nuit » ; « vos données ne servent jamais à entraîner une IA », « plus respectueux de
vos données » ; « hébergé en France » ; « sans erreur », « fiable à 100 % », « validé par des enseignants » ;
« cartes mentales », « application mobile », « paiement par carte » ou « en ligne » ; « le meilleur », « le seul »,
« n° 1 » et toute comparaison nommée ; « remplace ton manuel », « avocat dans ta poche », « conseil juridique » ;
« offre limitée » sans limite réelle ; tout autre chiffre de passages que « plus de 900 000 ».

Contrôle fait sur tous les textes produits (`source/verifier.py`, recherche des formules interdites) : voir la
dernière partie.

## Publicité et influence

- **Comptes de Lexia** : leur intention commerciale ressort du contexte ; pas de mention à ajouter (loi
  n° 2023-451, article 5-2).
- **Ambassadeurs** : mention « Publicité » ou « Collaboration commerciale » obligatoire (kit, page 4 ; bandeau
  `visuels/AMB/` ; storyboards, dernière page ; page `landings/ambassadeurs.md`).
- **Associations** : si elles publient après avoir reçu un accès offert, même mention (e-mail, réponse type et page
  `landings/associations.md`).
- **Relecteurs rémunérés** (P19) : s'ils parlent ensuite de Lexia en public, même règle.
- Aucun visage ni voix générés par IA, aucune image retouchée de personne, aucun mineur à l'image.

## Identité visuelle

- Couleurs, signet et logotype : artefact « Identité visuelle Lexia » (tokens du 13 novembre 2026). Les logos
  définitifs de la session logos et motion design (`brand/`) n'étaient pas dans `main` au moment du rendu : quand
  ils y seront, remplacer `signet()` et `logotype()` dans `source/visuels.py` et relancer les deux générateurs.
- Polices : l'identité utilise Georgia et Inter. Pour des images publiées sans question de licence, les visuels
  utilisent **Gelasio** (dessinée sur les métriques de Georgia) et **Inter**, toutes deux sous SIL Open Font License
  1.1 (fichiers et licences dans `source/polices/`, paquets npm `@fontsource/gelasio` et `@fontsource/inter`
  5.3.0). Les e-mails utilisent les polices du système, comme le site.
- QR code : bibliothèque `qrcode` 1.5.4 (licence MIT), généré une fois dans `source/qr-site.svg`.
- Musique : aucune fournie ; bibliothèques gratuites et licences lues le 23 novembre 2026 dans la dernière page de
  chaque storyboard. Le plus sûr : ajouter le son de la bibliothèque de chaque réseau au moment de publier.

## Régénérer

Il faut Google Chrome (rendu sans interface) et Python 3, sans autre dépendance.

```bash
cd docs/marketing/production/source && python3 visuels.py && python3 documents.py
```

`python3 visuels.py P4` ne refait que les visuels dont l'identifiant commence par P4 ; `--html` produit seulement
les pages HTML. Captures du site : refaites à la main (Chrome sans interface pour les pages en largeur d'ordinateur,
protocole DevTools pour la largeur de téléphone, voir l'historique du commit).

## Ce qui reste à faire par l'éditeur

1. Lever les prérequis : API Gemini payante, avis sur la marque, puis SIRET, médiateur et Stripe pour les messages
   sur les formules payantes.
2. Créer les comptes (TikTok, Instagram, YouTube, page LinkedIn) en type professionnel, avec la double
   authentification, le lien du site et des mentions légales en bio.
3. Valider l'identité : logos définitifs (`brand/`), polices, couleurs ; relancer les générateurs si quelque chose
   change.
4. Tourner les vidéos par lots avec les storyboards, sur un compte de test ; choisir la musique ; ajouter les
   captures de l'espace étudiant au dossier de presse.
5. Compléter le dossier de presse : biographie, citation et photo du fondateur, date de mise en ligne.
6. Faire développer l'envoi des e-mails d'information (file, désinscription en un clic, quota d'envoi) avant
   d'activer la séquence ; mettre à jour la politique de confidentialité et le registre.
7. Faire intégrer les pages d'atterrissage (session SEO et GEO ou développement).
8. Ambassadeurs : décider de la contrepartie, faire relire le contrat type par un avocat, lire le guide DGCCRF de
   janvier 2026 ; ajouter les traitements au registre.
9. Flyer : choisir un imprimeur, remplir son nom et son adresse, imprimer seulement après l'avis sur la marque.
10. Le jour de chaque publication : relire les dates et chiffres cités, refaire chaque démonstration.

## Contrôle des formules interdites

Résultat de `python3 source/verifier.py` le 23 novembre 2026 : 91 fichiers lus (visuels, documents, e-mails, pages,
calendrier), 0 faute, 11 emplois à la négative relus un par un et justes (« pas d'application mobile », « paiement en
ligne pas encore actif », « ne remplace pas ta réflexion », « pas de conseil juridique personnel », « les cartes
mentales ne sont pas en ligne »). Aucun tiret cadratin ni emoji.
