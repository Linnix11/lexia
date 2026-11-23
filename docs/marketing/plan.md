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
- Âge : la plupart ont 17 à 21 ans ; une partie des nouveaux L1 a 17 ans à la rentrée. L'âge minimum d'inscription
  est fixé par les CGU (article 3) et reste à trancher par l'éditeur entre 15 et 18 ans : les conditions de l'API
  Gemini excluent un service susceptible d'être utilisé par des moins de 18 ans (audit du 23 novembre 2026, E1 et
  EDI-1). D'ici là, aucun support n'écrit d'âge minimum ni ne s'adresse aux mineurs : il renvoie aux CGU. Si l'âge
  reste inférieur à 18 ans, les règles sur les mineurs (partie 7.5) s'appliquent au cœur de cible.

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
  méthodes de la licence.

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
| Âge : aucun âge minimum écrit, renvoi aux CGU (« conditions d'inscription dans les CGU ») | CGU, article 3 ; décision de l'éditeur attendue (EDI-1) | Oui : à revoir après la décision sur l'âge |

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

## 7. Cadre légal

Relevé factuel, pas un avis juridique : à faire relire par un avocat avant la première campagne avec des tiers
(ambassadeurs, créateurs, publicité payante). « Lu » signifie lu dans sa version en vigueur, soit dans le corpus DILA
de Lexia (archive LEGI du 8 novembre 2026, mise à jour du 16 novembre), soit sur la page officielle indiquée, le 19 ou
le 20 novembre 2026.

### 7.1 Influence commerciale (loi n° 2023-451 du 9 juin 2023)

Texte : https://www.legifrance.gouv.fr/loda/id/JORFTEXT000047663185 (modifié par l'ordonnance n° 2024-978 du
6 novembre 2024).

| Règle | Article (lu) | Ce que Lexia doit faire |
|---|---|---|
| Est influenceur quiconque, « à titre onéreux », mobilise sa notoriété auprès de son audience pour promouvoir un bien ou un service en ligne | Art. 1er, version du 8 novembre 2024 : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000050468930 | Traiter comme influenceur tout ambassadeur, créateur ou association qui parle de Lexia en échange d'argent **ou d'un avantage** (formule offerte). L'article ne dit pas en toutes lettres qu'un accès gratuit suffit, mais l'article 8 et le décret comptent les avantages en nature : prudence. |
| Mention claire, lisible et compréhensible de l'intention commerciale, sur tout support, sauf si elle ressort du contexte ; « publicité », « collaboration commerciale » ou équivalent. Sans elle : pratique commerciale trompeuse (L. 121-3) | Art. 5-2 : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000050457275 | Mention obligatoire pour les ambassadeurs et créateurs (kit). Les comptes de Lexia eux-mêmes : l'intention commerciale ressort du contexte. |
| Images retouchées (silhouette, visage) : « Images retouchées » ; images d'IA représentant un visage ou une silhouette : « Images virtuelles ». Sanction : 1 an et 4 500 € | Art. 5 : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000050468897 | Éviter ; sinon mention. |
| Contrat écrit sous peine de nullité entre l'influenceur et l'annonceur, avec identité, coordonnées et résidence fiscale des parties, missions, rémunération et valeur de l'avantage en nature, droits et obligations (propriété intellectuelle), soumission au droit français | Art. 8, I : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000047665811 | Contrat type pour les ambassadeurs, à faire relire. |
| Dispense de contrat écrit sous un seuil fixé par décret | Art. 8, II ; décret n° 2025-1137 du 28 novembre 2025 : https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000052950561 (lu par l'intermédiaire d'une recherche et de commentaires, page non ouverte directement) : 1 000 euros HT de rémunération et d'avantages cumulés, sur une année civile, depuis le 1er janvier 2026 | Un ambassadeur payé seulement en formule Intensif (9,99 € par mois, moins de 120 € par an) est sous le seuil ; faire un contrat écrit quand même (preuve des règles). |
| Responsabilité solidaire de l'annonceur pour les dommages causés aux tiers dans l'exécution du contrat | Art. 8, III | Relire les contenus des ambassadeurs avant publication au début. |

Guide de la DGCCRF « Influence commerciale : l'essentiel de vos droits » (janvier 2026) :
https://www.economie.gouv.fr/files/files/2026/202601-guide-influence-commerciale.pdf (refusé aux robots : **à lire par
l'éditeur** avant de signer avec un ambassadeur).

### 7.2 Pratiques commerciales trompeuses (Code de la consommation)

| Règle | Article (lu) | Conséquence |
|---|---|---|
| Pratique déloyale interdite ; appréciée au regard du groupe visé quand il est vulnérable en raison de son âge | L. 121-1 : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000032227301 | Le public comprend des 15-17 ans : être plus prudent encore. |
| Trompeuse si elle repose sur des allégations fausses ou de nature à induire en erreur, notamment sur les caractéristiques essentielles du service | L. 121-2 : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000044563114 | Liste des phrases interdites (partie 4). |
| Trompeuse aussi par omission d'une information substantielle, ou si l'intention commerciale n'est pas indiquée | L. 121-3 : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000044563111 | Publication « Ce que Lexia ne fait pas (encore) » ; limites citées dans les messages aux prescripteurs. |
| Réputées trompeuses en toutes circonstances, entre autres : contenu rédactionnel financé non signalé (11°) ; « gratuit » si le consommateur doit payer autre chose que les coûts inévitables (19°) ; se présenter faussement comme consommateur (21°) ; avis présentés comme vérifiés sans vérification (27°) ; faux avis ou avis modifiés (28°) | L. 121-4 : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000044563107 | Jamais de faux avis, de faux comptes, de témoignages inventés. « Gratuit » vrai pour la formule Gratuit (compte requis, rien à payer) : l'écrire avec ses limites. |
| Peines : 2 ans et 300 000 € ; jusqu'à 10 % du chiffre d'affaires ou 50 % des dépenses de publicité ; 5 ans et 750 000 € en ligne | L. 132-2 : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000049532070 | |
| Qui publie des avis en ligne doit dire s'ils sont contrôlés et comment | L. 111-7-2 : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000049571119 | Si le site affiche un jour des avis d'étudiants : ajouter cette information. |

### 7.3 Publicité comparative

| Règle | Article (lu) |
|---|---|
| Licite seulement si non trompeuse, pour des biens ou services qui répondent aux mêmes besoins, et si elle compare objectivement des caractéristiques essentielles, pertinentes, vérifiables et représentatives (dont le prix) | L. 122-1 : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000032227222 |
| Interdit de tirer indûment profit de la notoriété d'une marque concurrente, de la dénigrer, de créer une confusion | L. 122-2 : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000039382281 |
| L'annonceur doit pouvoir prouver « dans un bref délai » l'exactitude de la comparaison | L. 122-5 : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000032227214 |

Décision : **pas de publicité comparative** dans ce plan (partie 3). Si l'éditeur en veut une plus tard : dossier de
preuve daté (captures des pages de Google, date, offres comparées) et relecture par un avocat.

### 7.4 Prospection par e-mail et RGPD

| Règle | Source | Ce que Lexia doit faire |
|---|---|---|
| Prospection par e-mail d'une personne physique : consentement préalable, sauf client pour des produits ou services analogues ; identité de l'émetteur et moyen de s'opposer dans chaque message | Code des postes et des communications électroniques, art. L. 34-5 : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000042155961 ; CNIL : https://www.cnil.fr/fr/communication-electronique-quelles-regles | Inscrits : pas d'e-mail promotionnel sans case de consentement **distincte et non cochée** à l'inscription ou dans Mon compte (absente du code au 19 novembre 2026 : à développer). La CNIL précise que créer un compte sans achat ne fait pas de la personne un client : l'exception des produits analogues ne s'applique pas aux comptes gratuits. Les e-mails de service (confirmation, sécurité) restent possibles. |
| Professionnels (B2B) : pas de consentement si le message est en rapport avec la fonction du destinataire, s'il est informé et peut s'opposer ; adresses génériques de personnes morales (contact@) hors de ce régime | CNIL, règles de la prospection par courrier électronique : https://www.cnil.fr/fr/les-regles-dor-de-la-prospection-par-courrier-electronique-0 (page ancienne) | Associations : écrire à leur adresse de contact publique, un par un, identité complète, origine de l'adresse, opposition simple (e-mail type). Liste « ne plus contacter » conservée. |
| Information des personnes (RGPD, art. 13), durée de conservation, registre | CNIL : https://www.cnil.fr/fr/informer-les-personnes ; référentiel « gestion des activités commerciales » : prospects 3 ans à compter du dernier contact actif | Mentions sous le formulaire ambassadeurs ; ajouter au registre (`docs/registre-traitements.md`) : prospection des associations, candidatures d'ambassadeurs, contrats d'ambassadeurs, messages reçus sur les réseaux sociaux. |

### 7.5 Mineurs (si l'âge minimum reste inférieur à 18 ans)

L'éditeur doit trancher entre 15 et 18 ans (EDI-1, audit du 23 novembre 2026). D'ici là, ces règles s'appliquent
à tout inscrit mineur, et aucun support ne mentionne d'âge minimum ni n'invite les mineurs à s'inscrire. Avec un
âge minimum de 18 ans, elles ne servent plus que pour les ambassadeurs et les vidéos.

| Règle | Source | Conséquence |
|---|---|---|
| Un mineur peut consentir seul à un traitement de ses données pour un service en ligne à partir de 15 ans ; informations rédigées en termes clairs et simples, compréhensibles par lui | Loi n° 78-17, art. 45 (lu) : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000037823135 ; RGPD, art. 8 | Un inscrit de 15 à 17 ans peut cocher seul un consentement aux e-mails ; textes de consentement simples. |
| Recommandations de la CNIL sur les mineurs en ligne (2021) : pas de réutilisation commerciale des données de mineurs, profilage désactivé par défaut | https://www.cnil.fr/fr/la-cnil-publie-8-recommandations-pour-renforcer-la-protection-des-mineurs-en-ligne | Aucun ciblage publicitaire fondé sur les données des inscrits mineurs (pas d'audience personnalisée à partir de la liste des inscrits). |
| Les plateformes en ligne ne présentent pas de publicité fondée sur le profilage quand elles savent avec une certitude raisonnable que le destinataire est mineur ; publicité identifiable, avec l'annonceur et les principaux paramètres de ciblage | Règlement (UE) 2022/2065 (DSA), art. 28 et 26 : https://eur-lex.europa.eu/legal-content/FR/TXT/HTML/?uri=CELEX:32022R2065 | Campagnes payantes : cibler les 18 ans et plus ; pour les 15-17 ans, seulement l'organique ou le contextuel. |
| Un mineur non émancipé ne peut contracter seul, sauf actes courants autorisés par la loi ou l'usage, à des conditions normales | Code civil, art. 1146, 1148 (lus) : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000032041065 ; https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000032041055 | Ambassadeurs majeurs uniquement. Formules payantes : accord parental avant 18 ans (déjà dans les CGU, article 3). |
| Diffusion de l'image d'un enfant de moins de 16 ans, sujet principal de contenus en ligne : déclaration au-delà de seuils | Loi n° 2020-1266, art. 3 (lu) : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000047666656 | Ne pas filmer d'étudiant de moins de 16 ans ; en pratique, aucun mineur dans les vidéos. |
| Loi n° 2023-566 du 7 juillet 2023 (majorité numérique) : entrée en vigueur subordonnée à un décret après réponse de la Commission européenne | Art. 7 (lu) : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000047801945 | Aucun décret trouvé : ne pas la présenter comme en vigueur. Elle vise les réseaux sociaux, pas Lexia. Décision n° 2026-911 DC du 14 août 2026 sur la loi n° 2026-813 (accès des moins de 15 ans aux réseaux sociaux) repérée mais non lue : à vérifier avant d'écrire sur ce sujet. |
| ARPP : recommandation « Communication publicitaire numérique » (influence, mention immédiate et explicite ; « #produitremis » pour un produit offert sans obligation de publier) et recommandation « Enfant » (12 ans et moins ; adolescents 13-17) : règles d'autodiscipline, non obligatoires en elles-mêmes, mais référence du Jury de déontologie publicitaire | https://www.arpp.org/nous-consulter/regles/regles-de-deontologie/recommandation-communication-publicitaire-numerique/ ; https://www.arpp.org/nous-consulter/regles/regles-de-deontologie/enfant/ (non ouverte) | Charte ambassadeurs alignée sur l'ARPP ; certificat de l'influence responsable proposé aux créateurs rémunérés (https://www.arpp.org/influence-responsable/faq-certificat-influence-responsable-arpp/). |

### 7.6 Le nom « Lexia » avant la recherche de marque

| Règle | Source (lue) |
|---|---|
| Interdit sans autorisation : signe identique pour des produits ou services identiques ; signe identique ou similaire pour des produits ou services identiques ou similaires s'il existe un risque de confusion, y compris d'association | Code de la propriété intellectuelle, L. 713-2 : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000039381601 |
| Marque renommée : protégée même pour des produits non similaires | L. 713-3 : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000039381598 |
| L'atteinte est une contrefaçon qui engage la responsabilité civile | L. 716-4 : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000039381676 |
| L'INPI conseille, avant d'utiliser un nom, de chercher dans les bases INPI, EUIPO et OMPI et de consulter un conseil en propriété industrielle ou un avocat | https://www.inpi.fr/nos-solutions/defendre-ses-droits/eviter-de-devenir-contrefacteur |
| Dépôt en ligne : 190 € pour une classe, 40 € par classe supplémentaire (page publiée en 2024 ; grille 2026 confirmée seulement indirectement) | https://www.inpi.fr/realiser-demarches/propriete-intellectuelle/deposant-et-cout-dune-marque |
| Opposition par un titulaire antérieur : 2 mois après la publication de la demande ; droits invocables : marque, dénomination, nom commercial, enseigne, nom de domaine | https://www.inpi.fr/realiser-demarches/propriete-intellectuelle/sopposer-lenregistrement-dune-marque |

Ce que le plan en tire, sans conclure sur le risque : le relevé du 17 novembre 2026 montre des marques « LEXIA »
identiques enregistrées dans des classes proches du service (logiciels éducatifs dans l'Union, services juridiques en
France). Tant qu'un conseil ne s'est pas prononcé :

- ne dépenser ni en publicité payante, ni en impression, ni en logo définitif sous ce nom ;
- réserver les noms de comptes sous une forme qui ne figera rien (partie 10), et garder les textes faciles à
  renommer (un remplacement global suffit dans `contenus-mois-1.md`) ;
- préparer avec le conseil un nom de repli, à vérifier dans les mêmes bases avant tout usage.

### 7.7 Contenus générés par IA

- Loi n° 2023-451, art. 5 : « Images virtuelles » pour un visage ou une silhouette produits par IA (partie 7.1).
- Règlement (UE) 2024/1689, art. 50 : obligations de transparence applicables depuis le 2 août 2026 ; un déployeur qui
  diffuse un hypertrucage (image, audio ou vidéo ressemblant à des personnes, lieux ou événements réels et paraissant
  authentique) doit l'indiquer ; source : FAQ de la Commission européenne
  (https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act). Le texte de
  l'article n'a pas pu être relu sur EUR-Lex : à vérifier.
- Décision du plan : pas de visage ni de voix générés par IA dans les contenus. Les réponses de Lexia filmées à
  l'écran sont des textes générés par IA : le site les signale déjà (en-tête `X-AI-Generated`, décision D92) ; dans
  les vidéos, la voix off dit « la réponse de Lexia » plutôt que de la présenter comme écrite par un humain.

### 7.8 Jeux-concours

Les opérations promotionnelles par tirage au sort sont interdites lorsqu'elles sont déloyales
(L. 121-20 : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000032227240). Décision : **pas de jeu-concours**
dans la phase organique. S'il y en a un plus tard : participation gratuite sans achat, règlement écrit, majeurs
seulement, règles de la plateforme lues, relecture par un avocat.

## 8. Phases et budget

### Phase 1 : organique (décembre 2026 à avril 2027 au moins)

Budget en argent : 0 €. Coût réel : le temps de l'éditeur (une demi-journée par semaine de production, plus les
réponses aux commentaires et aux associations). Outils gratuits : éditeurs vidéo intégrés aux plateformes,
planification native de Meta et de TikTok, Canva gratuit ou équivalent (à vérifier selon l'outil retenu).

Objectif : apprendre ce qui fait venir des comptes actifs, avant de payer. Le paiement n'étant pas actif, chaque
compte créé est aujourd'hui un coût (question à 0,0021 $ environ, `docs/avant-la-vente.md`), pas une recette.

### Phase 2 : payante (au plus tôt aux partiels de mai 2027)

Conditions d'entrée : prérequis de la partie 1 levés, paiement Stripe actif, au moins 8 semaines de mesures
organiques. Ciblage : 18 ans et plus, France, intérêts ou contextes liés aux études de droit, sans audience
personnalisée tirée de la liste des inscrits.

Minimums des régies (pages d'aide officielles, consultées par recherche le 20 novembre 2026, à reconfirmer dans
chaque gestionnaire de publicités) :

| Régie | Minimum | Source |
|---|---|---|
| TikTok | Budget journalier supérieur à 50 $ par campagne et 20 $ par groupe d'annonces | https://ads.tiktok.com/help/article/budget |
| LinkedIn | 10 $ par jour quel que soit le format ; 100 $ en budget total pour une nouvelle campagne | https://business.linkedin.com/marketing-solutions/success/best-practices/maximize-your-budget |
| Meta (Instagram) | Environ 1 $ par jour pour une campagne d'impressions ou de clics, davantage pour une optimisation en conversions : chiffres de sites tiers, la page de Meta n'a pas pu être lue ; le minimum exact s'affiche dans le gestionnaire | À vérifier dans le gestionnaire de publicités Meta |
| YouTube (Google Ads) | Non vérifié | À vérifier |

Ordres de grandeur des coûts (sources tierces, non officielles, à prendre comme fourchettes prudentes) : coût pour
mille impressions en France de 3 à 8 € sur TikTok et de 12 à 20 € sur Meta selon Adintime (page non datée,
https://adintime.com/en/blog?id=311) ; d'autres relevés mondiaux en dollars varient du simple au quadruple selon les
mois (Influee, https://influee.co/fr/blog/tiktok-cpm ; Metricool, étude Social Ads 2026,
https://metricool.com/fr/etude-social-ads/). Aucun chiffre fiable trouvé pour LinkedIn et YouTube en France, ni pour
la rémunération des micro-créateurs étudiants : demander des devis.

Paliers proposés :

| Palier | Quand | Budget par mois | Répartition | Ce qu'on attend (ordre de grandeur) |
|---|---|---|---|---|
| 1. Test | Partiels de mai 2027, 4 semaines | 150 à 300 € | Instagram seul : 2 vidéos (V1, V3) et 1 carrousel déjà performants en organique, 5 à 10 € par jour | 10 000 à 25 000 impressions à 12-20 € les mille ; mesurer le coût par compte créé |
| 2. Rentrée | Septembre-octobre 2027, si le coût par compte du palier 1 est acceptable | 500 à 1 000 € | Instagram 60 % ; TikTok 40 % par salves de 7 jours (50 $ par jour minimum, donc environ 350 $ la salve) | Comparer les deux régies sur le coût par compte actif à 7 jours |
| 3. Créateurs | Après le palier 2 | Sur devis, plafonné à 30 % du budget du mois | 2 ou 3 créateurs étudiants en droit, contrat écrit, mention « Publicité », contenus relus | Comptes créés par lien suivi propre à chaque créateur |

Garde-fou économique : la recette nette d'un abonné Étudiant est 4,67 € par mois après frais Stripe
(`docs/avant-la-vente.md`). Proposition : ne pas dépasser un coût d'acquisition d'un abonné payant égal à trois mois
de recette nette (environ 14 € pour Étudiant), tant que la durée moyenne d'abonnement n'est pas mesurée. Le coût par
compte gratuit créé doit être rapporté au taux de passage au payant, inconnu aujourd'hui.

LinkedIn payant : non recommandé pour les étudiants (minimum de 10 $ par jour pour une audience plus chère) ; à
réserver plus tard à une offre pour les établissements, s'il y en a une.

## 9. Indicateurs

| Indicateur | Où le lire | Fréquence | Remarque |
|---|---|---|---|
| Comptes créés par jour | Administration, statistiques sur 30 jours (`comptes.statistiques`, champ « inscriptions ») | Chaque semaine | Indicateur principal de la phase 1 |
| Comptes actifs, questions et questionnaires par jour | Même vue (« actifs », « questions », « quiz ») | Chaque semaine | Rapport questions / compte actif = intérêt réel |
| Rétention : comptes revenus 7 et 30 jours après l'inscription | À développer (la vue actuelle ne la donne pas directement) | Chaque mois | Demander à la session de développement |
| Origine des inscriptions | À développer : question facultative « Comment as-tu connu Lexia ? » à l'inscription, ou liens propres à chaque canal | Chaque semaine | Sans traceur publicitaire ; si une mesure d'audience est ajoutée, suivre les conditions d'exemption de la CNIL |
| Passage au payant, revenu mensuel | Administration (« payants_actifs », « revenu_mensuel_estime ») | Chaque mois | Quand Stripe sera actif |
| Coût par compte créé, par compte actif à 7 jours, par abonné | Gestionnaires de publicités + inscriptions par lien suivi | Pendant chaque campagne | Phase 2 seulement |
| Portée et engagement : vues, enregistrements, partages, commentaires, abonnés | Statistiques natives de chaque plateforme | Chaque semaine | Les enregistrements comptent plus que les « j'aime » pour les carrousels de méthode |
| Associations : contactées, réponses, ateliers tenus | Tableau tenu par l'éditeur | Chaque mois | Avec la liste « ne plus contacter » |
| Qualité perçue : avis « utile / pas utile » | `/feedback` (journal) | Chaque semaine | Une baisse après une campagne signale un public mal ciblé |
| Coût du modèle par question | `eval/cout.py` sur les journaux du serveur | Chaque mois | Une campagne réussie augmente le coût avant la recette |

Objectifs de la phase 1 : à fixer après les deux premières semaines de mesure plutôt qu'à l'avance (aucune base
aujourd'hui). Proposition de revue : un bilan d'une page fin décembre 2026 et fin mars 2027.

## 10. Actions qui reviennent à l'éditeur

Par ordre de priorité.

1. **Passer l'API Gemini au niveau payant** (`docs/avant-la-vente.md`, partie 1), puis prévenir la session de
   développement. Préalable à toute communication qui fait venir du public.
2. **Consulter un conseil en propriété industrielle** sur « Lexia » (relevé : `docs/marque-lexia.md`) ; commander si
   besoin une recherche de similarités ; décider du dépôt (INPI : 190 € la première classe, 40 € par classe
   supplémentaire, à reconfirmer) et, avec le conseil, d'un nom de repli.
3. **Réserver les noms de comptes** sur TikTok, Instagram, YouTube et LinkedIn (page entreprise), avec la même forme
   partout ; vérifier la disponibilité soi-même. La réservation d'un nom de compte ne vaut pas droit sur le nom :
   n'imprimer ni ne payer de visibilité avant le point 2.
4. **Créer les comptes** en type professionnel ou entreprise, avec l'adresse de contact des mentions légales,
   double authentification activée, et les liens vers le site et les mentions légales en bio.
5. **Obtenir le SIRET**, puis choisir et adhérer à un médiateur de la consommation, puis activer Stripe
   (`docs/avant-la-vente.md`, parties 3 et 4).
6. **Valider ou modifier le calendrier du mois 1** (`contenus-mois-1.md`) et tourner les vidéos par lots ; vérifier en
   vrai chaque démonstration avant de la filmer.
7. **Décider du budget** : confirmer la phase 1 à 0 €, puis choisir le palier 1 (150 à 300 €) pour mai 2027 ou non.
8. **Décider de la contrepartie des ambassadeurs** (formule offerte seule, ou rémunération), faire rédiger et relire
   le contrat type (loi n° 2023-451, art. 8), lire le guide DGCCRF de janvier 2026.
9. **Décider si la relecture par des enseignants est bénévole ou rémunérée**, puis publier l'appel (P19).
10. **Demander à la session de développement** : une case de consentement aux e-mails d'information, distincte et
    non cochée ; une question facultative sur l'origine de l'inscription ou des liens par canal ; un indicateur de
    rétention dans l'administration ; l'ajout des nouveaux traitements au registre.
11. **Contacter les associations** soi-même, une par une, avec l'e-mail type, à partir de janvier 2027.

## 11. Limites de ce document

- Pages refusées aux robots et donc non lues directement : guide et fiches de la DGCCRF, page de Meta sur les budgets
  minimums, certaines pages de la CNIL, texte de l'art. 50 du règlement IA, décret n° 2025-1137 (lu par des résumés
  concordants), décision n° 2026-911 DC. Elles sont signalées à l'endroit où elles servent.
- Effectifs étudiants : projection du ministère, pas un effectif observé.
- Coûts publicitaires : sources tierces et variables ; seuls les minimums de TikTok et LinkedIn viennent des régies.
- Dates de partiels : typiques, à vérifier faculté par faculté.
- Aucune conclusion juridique sur le nom « Lexia » ni sur les cas limites (accès gratuit et « titre onéreux ») : à
  faire apprécier par un avocat ou un conseil en propriété industrielle.
