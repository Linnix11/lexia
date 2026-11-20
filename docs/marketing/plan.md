# Plan marketing et réseaux sociaux de Lexia

Rédigé les 19 et 20 novembre 2026, sur `main` au commit b5304bd. Document de travail : rien n'est publié, aucun
compte n'est créé, rien n'est acheté, personne n'est contacté. Contenus prêts du premier mois :
`docs/marketing/contenus-mois-1.md`.

Sources lues : `README.md`, `docs/decisions.md`, `docs/avant-la-vente.md`, `docs/marque-lexia.md`, le comparatif
`docs/comparatif-notebooklm.md` (branche `claude/comparatif-notebooklm-v2`, état du 19 novembre 2026), et le site en
ligne (`/api/sante`, `/api/formules`, `/api/config`, `/api/fraicheur`, `/api/matieres`, interrogés le 19 novembre).
Les textes de loi cités ont été lus dans leur version en vigueur dans le corpus de Lexia (archive DILA LEGI du
8 novembre 2026, mise à jour du 16 novembre), avec le lien Légifrance de chaque article, et complétés par des pages
officielles (CNIL, INPI, ARPP, EUR-Lex) dont la liste est en partie 7.

## 0. En bref

- **D'abord lever trois prérequis** (partie 1) : passer l'API Gemini au niveau payant, faire apprécier le nom
  « Lexia » par un conseil en propriété industrielle, obtenir le SIRET. Sans le premier, inviter du public contrevient
  aux conditions de Google et contredit la politique de confidentialité affichée.
- **Cible** : étudiants de L1 à L3 en droit (environ 140 000 inscrits en licence de droit selon une projection du
  ministère, partie 2), avec la L1 comme cœur de cible et trois moments forts : rentrée, partiels de
  décembre-janvier, partiels de mai.
- **Positionnement** : « le droit en vigueur, cité et vérifiable, avec les méthodes de la licence ». Face à Gemini
  Notebook : spécialisé et prêt à l'emploi, pas un outil général où il faut apporter ses documents. Face aux manuels :
  à jour et interrogeable, mais complément, pas remplacement.
- **Canaux** : vidéos courtes (TikTok, Reels, Shorts) et carrousels Instagram pour la portée ; LinkedIn pour la
  crédibilité auprès des enseignants et associations ; associations, corpos, Discord de promo et ambassadeurs pour la
  confiance.
- **Phase organique gratuite** jusqu'à ce que le paiement soit actif ; **publicité payante ensuite**, par paliers de
  150 à 1 000 € par mois, testée d'abord sur Instagram (partie 8).
- **Indicateurs** : comptes créés, comptes actifs à 7 et 30 jours, questions par compte actif, passage au payant
  quand il existera, coût par compte créé pour la partie payante (partie 9).

## 1. Prérequis avant toute communication publique

| Prérequis | Pourquoi | Bloque | Qui |
|---|---|---|---|
| API Gemini au niveau payant (`GEMINI_NIVEAU_PAYANT=1`) | Les conditions additionnelles de l'API Gemini réservent les services payants aux applications proposées dans l'Espace économique européen (`docs/avant-la-vente.md`, partie 1). En ligne le 19 novembre : `gemini_payant: false`, et la politique de confidentialité dit que Google peut utiliser les questions et les réponses. Attirer du public dans cet état, dont des mineurs de 15 à 17 ans, est le risque le plus sérieux du plan. | Toute campagne qui vise à faire venir du monde, y compris organique | Éditeur (facturation Google), puis session de développement |
| Avis d'un conseil en propriété industrielle sur « Lexia » | Des marques « LEXIA » identiques sont enregistrées pour des logiciels éducatifs dans l'Union (EUIPO 015377401, OMPI 1647070 désignant l'Union, classes 9, 41, 42) et pour des services juridiques en France (INPI 4010966, classe 45) (`docs/marque-lexia.md`). Ce plan ne conclut pas sur le risque : il appartient à un conseil de l'apprécier (partie 7.6). | Dépense payante, impression, dépôt de marque, noms de comptes définitifs | Éditeur |
| SIRET attribué | Les mentions légales affichent « SIRET en cours d'attribution » (`/api/config`). Les régies publicitaires demandent les informations de l'entreprise pour un compte annonceur. | Publicité payante | Éditeur |
| Médiateur de la consommation et paiement Stripe actif | Nécessaires pour vendre en ligne (`docs/avant-la-vente.md`, parties 3 et 4). | Messages sur les formules payantes, publicité de conversion | Éditeur |
| Notation des réponses par un enseignant | Pas obligatoire, mais c'est la seule mesure indépendante de la qualité ; sans elle, aucune phrase sur la fiabilité. | Rien ; renforce la crédibilité | Éditeur, avec relecteurs (publication P19) |

Ce qui peut commencer tout de suite sans risque : réserver les noms de comptes (partie 10), préparer les visuels,
filmer les démonstrations sur un compte de test, écrire aux associations seulement après le premier prérequis.

## 2. Cible

### Population

- Licence de droit : la note Flash du SIES n° 25 (octobre 2026) projette environ 141 600 étudiants en licence de
  droit en 2025-2026 et 142 900 en 2026-2027 ; c'est une **projection**, pas un effectif observé
  (https://www.enseignementsup-recherche.gouv.fr/sites/default/files/2026-10/2026_10_NF_SIES_25_projections.pdf).
  La note Flash n° 11 (juin 2026) donne les effectifs universitaires observés en 2025-2026
  (https://www.enseignementsup-recherche.gouv.fr/sites/default/files/2026-06/nf-sies-2026-11-40399.pdf) ; son
  périmètre « Droit » est à relire avant de citer un chiffre.
- Âge : la plupart ont 17 à 21 ans. Lexia accepte les inscriptions dès 15 ans (CGU, article 3) : une partie des
  nouveaux L1 a 17 ans à la rentrée. Les règles sur les mineurs (partie 7.5) s'appliquent donc au cœur de cible.

### Sous-cibles

| Sous-cible | Moment | Besoin | Message | Canal principal |
|---|---|---|---|---|
| Nouveaux L1 | Août à octobre | Comprendre la méthode, ne pas se perdre dans les sources | « Les méthodes de la licence, avec le texte officiel à un clic » | TikTok, Reels, ambassadeurs, associations (semaines d'intégration) |
| L1 en difficulté | Janvier (premiers résultats), juin (rattrapages) | Rattraper la méthode, s'entraîner | Cas pratiques résolus, quiz, « 3 erreurs en L1 » | Vidéos courtes, Discord de promo, tutorat des associations |
| Tous niveaux en partiels | Décembre-janvier, avril-mai | Réviser vite, vérifier un article | Quiz, fiches, vérification de la version en vigueur | Vidéos courtes, stories |
| L2-L3 | Toute l'année | Droit administratif, européen, affaires, procédure ; jurisprudence | Grands arrêts reconnus par leur nom, 20 matières | Carrousels, Shorts, LinkedIn |
| Prescripteurs : chargés de TD, enseignants, bureaux d'associations, corpos | Septembre, janvier | Savoir si l'outil est fiable | Transparence sur le contrôle des citations et les limites | LinkedIn, e-mail aux associations |

À exclure : les lycéens (avant la L1) comme cible de publicité payante ; les candidats aux concours (CRFPA, ENM)
tant que le corpus n'a pas la jurisprudence récente à jour.

## 3. Positionnement

**Phrase de positionnement (interne)** : pour un étudiant de licence en droit, Lexia est l'espace d'étude qui répond
à partir du droit en vigueur, cite chaque source et applique les méthodes de la licence, sans rien avoir à préparer.

### Face à Gemini Notebook (ex-NotebookLM)

Constat du comparatif du 19 novembre 2026 :

- Gemini Notebook est gratuit, très riche en révision (fiches à retourner, résumés audio et vidéo, cartes mentales),
  accepte presque tous les formats, a des applications mobiles, et Google offre AI Plus 12 mois aux étudiants majeurs
  en France jusqu'au 31 décembre 2026. Sur ces points, Lexia ne gagne pas et ne doit pas prétendre gagner.
- Lexia gagne sur : le corpus officiel déjà chargé (environ 916 000 passages), la citation qui prouve la règle et pas
  seulement le document, la version en vigueur vérifiable, les anciens numéros du Code civil reliés aux actuels, les
  méthodes de la licence, l'ouverture dès 15 ans.

Conséquence pour la communication : **ne jamais nommer Gemini Notebook** (ni un autre outil) dans une publicité.
Une publicité comparative n'est licite que si elle compare objectivement des caractéristiques vérifiables et
représentatives, et l'annonceur doit pouvoir le prouver « dans un bref délai » (articles L. 122-1 et L. 122-5,
partie 7.3) ; les prix et quotas de Google changent souvent. On montre plutôt ce que fait Lexia, dans un usage
juridique que l'étudiant reconnaît : « ton polycopié cite 1382 ; voici ce que dit 1382 aujourd'hui ».

À surveiller : l'offre étudiante de Google doit être prise avant le 31 décembre 2026. Vérifier en août 2027 si elle
est renouvelée pour la rentrée suivante ; cela change la sensibilité au prix des nouveaux L1.

### Face aux manuels, fiches et annales

- Les manuels et polycopiés restent la référence du cours : Lexia ne doit pas dire qu'il les remplace.
- Ce qu'il apporte en plus : le texte en vigueur (un manuel imprimé peut dater d'avant une réforme), la recherche par
  question, l'entraînement (quiz, cas pratiques), et le croisement d'un cours déposé avec le droit actuel.
- Ton : « complète ton cours », « vérifie avant de citer », jamais « plus besoin de manuel ».

### Ton de la marque

Sérieux mais simple, tutoiement sur TikTok et Instagram, vouvoiement sur LinkedIn et par e-mail. Toujours un
article cité. Transparence sur les limites (publication P25 du mois 1) : pour des étudiants en droit, c'est un
argument de confiance.

## 4. Messages clés

Seuls les messages vrais et vérifiables au jour de la publication. La liste de référence est celle du comparatif
(partie « Arguments vrais et vérifiables »), recopiée dans `contenus-mois-1.md`.

| Message | Vérifiable où | À revérifier avant chaque usage |
|---|---|---|
| Plus de 900 000 passages officiels : codes, lois, Constitution, Cour de cassation, Conseil d'État, Conseil constitutionnel, traités de l'Union | Index du 17 novembre 2026 (916 158 passages) | Oui, si le corpus change |
| Codes et lois mis à jour chaque nuit ; la date de chaque source est affichée | `/api/fraicheur` (textes au 18 novembre 2026) | Oui : vérifier que la mise à jour tourne |
| Chaque réponse cite ses sources, avec le texte officiel à un clic ; une affirmation sans source est retirée | README, Garde-fous ; décision D22 | Non, sauf changement du contrôle |
| Vérifiez en un clic qu'un article est en vigueur ; anciens numéros du Code civil reliés aux nouveaux | `/sources/{id}/vigueur` ; `api/concordance.py` (26 numéros) | Non |
| Cas pratique, commentaire d'arrêt, dissertation | Modes de `/chat` | Non |
| 20 matières de la L1 à la L3, niveau adapté au semestre | `/api/matieres` (20) ; décision D49 | Oui |
| Déposez vos cours (PDF, Word, PowerPoint, OpenDocument) et confrontez-les au droit en vigueur | `api/extraction.py` ; décision D93 | Non |
| Gratuit avec un compte : 10 questions et 2 questionnaires par jour | `/api/formules` | Oui, à chaque changement de formule |
| Ouvert dès 15 ans | CGU, article 3 ; décision D92 | Non |

**À ne pas écrire aujourd'hui** (comparatif, partie 4, et brief) : « jurisprudence à jour chaque nuit » (faux pour la
Cour de cassation et le Conseil constitutionnel, décisions jusqu'aux 16-17 septembre et 16 octobre 2026) ;
« données jamais utilisées pour l'entraînement » ou « plus respectueux de vos données » (faux tant que le niveau
gratuit de Gemini est utilisé) ; « hébergé en France » (non vérifié : Hostinger, société à Chypre, centre de données
à vérifier) ; « sans erreur », « fiable à 100 % », « validé par des enseignants » ; « fiches à retourner »,
« résumés vocaux », « application mobile », « paiement par carte » (en développement ou non publiés) ; « le
meilleur », « le seul », « n° 1 » ; toute comparaison nommée.

Messages qui deviendront possibles, une fois le fait établi et vérifié : « questions non utilisées pour entraîner
les modèles de Google » (après le passage au niveau payant, en reprenant exactement les termes de Google) ;
« fiches à retourner » et « résumés vocaux » (après publication) ; « réponses notées par des enseignants » (après
la notation, avec le résultat réel) ; « paiement par carte » (après activation de Stripe).

Toute affirmation fausse ou de nature à induire en erreur sur les caractéristiques du service est une pratique
commerciale trompeuse (article L. 121-2), punie de deux ans d'emprisonnement et 300 000 euros d'amende, portés à
cinq ans et 750 000 euros quand elle est commise en ligne (article L. 132-2).

## 5. Canaux

| Canal | Rôle | Formats | Rythme proposé (phase organique) | Remarques |
|---|---|---|---|---|
| TikTok | Portée auprès des L1 | Vidéos courtes 15-60 s : cas pratiques, erreurs, démonstrations | 3 par semaine | Compte professionnel ; bibliothèque de sons libres pour les marques |
| Instagram | Portée et enregistrement (carrousels de méthode) | Reels (mêmes vidéos), carrousels, stories (sondages, questions) | 3 Reels + 2 carrousels + stories par semaine | Lien en bio ; carrousels « à enregistrer » pour les révisions |
| YouTube Shorts | Recherche et durée de vie longue | Mêmes vidéos, titres clairs (« Article 1240 en 30 s ») | 3 par semaine | Puis vidéos longues (méthode du commentaire) si les Shorts prennent |
| LinkedIn | Crédibilité : enseignants, chargés de TD, associations, futurs partenaires | Posts du fondateur, carrousels PDF | 1 à 2 par semaine | Transparence sur les limites ; appel à relecteurs |
| Discord et groupes d'étudiants | Confiance, retours, entraide | Présence d'un ambassadeur, réponses aux questions de cours | À la demande | Ne jamais poster sans l'accord des modérateurs ; pas de messages en masse |
| Associations de droit et corpos | Prescription, accès aux promos | Atelier méthode, accès Intensif pour le bureau, contenu pour leurs réseaux | 5 à 10 associations par mois, une par une | E-mail type dans `contenus-mois-1.md` ; règles de la partie 7.4 |
| Ambassadeurs sur les campus | Bouche à oreille, retours terrain | Leurs propres comptes, présentations en TD ou en association | 1 à 2 par faculté, à partir de janvier 2027 | Majeurs, contrat écrit, mention « Publicité » (partie 7.1) ; kit dans `contenus-mois-1.md` |

Pas de priorité à Facebook, X ni Snapchat dans la phase organique : moins de temps de production pour plus de
régularité sur les trois formats qui se recyclent (une vidéo verticale sert sur TikTok, Reels et Shorts).

Production : une demi-journée par semaine suffit pour le rythme proposé si les vidéos sont tournées par lots (4 à 6 à
la fois) et déclinées sur les trois plateformes.

## 6. Calendrier de l'année universitaire

Les dates d'examens varient selon les facultés : relever en septembre le calendrier officiel des 5 à 10 facultés
visées et caler les dates. Périodes typiques ci-dessous, à confirmer.

| Période | Moment des étudiants | Actions |
|---|---|---|
| Fin novembre 2026 | Avant les partiels | Lever les prérequis ; réserver les comptes ; tourner les premières vidéos |
| 30 novembre 2026 au 27 décembre 2026 | Révisions et partiels du premier semestre | Mois 1 : 26 publications (`contenus-mois-1.md`) |
| Janvier 2027 | Fin des partiels, premiers résultats, second semestre | Sous-cible « L1 en difficulté » ; appel à ambassadeurs ; e-mails aux associations ; notation par des enseignants |
| Février à mars 2027 | Cours du second semestre, TD | Méthode : commentaire d'arrêt, dissertation ; grands arrêts L2 ; régularité |
| Avril à mai 2027 | Partiels du second semestre | Deuxième pic ; si paiement actif et prérequis levés : premier test payant (palier 1) |
| Juin à juillet 2027 | Rattrapages ; résultats | Cas pratiques pour le rattrapage ; bilan ; préparer la rentrée |
| Août 2027 | Préparation de la L1 | « Préparer sa L1 de droit » (contenus organiques, pas de publicité ciblée vers des mineurs) ; vérifier l'offre étudiante de Google |
| Septembre à octobre 2027 | Rentrée, intégration, premiers TD | Plus gros pic d'acquisition : associations (semaines d'intégration), ambassadeurs, palier 2 payant si les mesures du printemps le justifient |
| Novembre à décembre 2027 | Partiels du premier semestre | Reprendre et mettre à jour les contenus du mois 1 |
