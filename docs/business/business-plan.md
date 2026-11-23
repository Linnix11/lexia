# Business plan de Lexia

Axion Studio, 23 novembre 2026. Document de planification : il ne constitue ni une prévision certaine, ni un
conseil financier, juridique ou d'investissement. Les chiffres vérifiés sont sourcés dans
[sources.md](sources.md) (pages lues le 23 novembre 2026) ; les projections sont dans
[projections.xlsx](projections.xlsx), où chaque hypothèse est modifiable. **Toute hypothèse sans source est
signalée comme telle** (mention « hypothèse » dans le texte, fond orange dans le classeur).
Pitch deck : [pitch.pptx](pitch.pptx) (12 diapositives, avec notes) et sa version [pitch.pdf](pitch.pdf). Les trois
fichiers se régénèrent avec les scripts de [outils/](outils/).

Lu pour ce document : `README.md`, `docs/decisions.md` (D1 à D114), `docs/avant-la-vente.md`,
`docs/marketing/plan.md`, `docs/comparatif-notebooklm.md`, `docs/note-editeur-2026-11-20.md`,
`docs/marque-lexia.md`, `api/plans.py`, `logs/modele.jsonl` (Mac), et le site en ligne (`/api/formules`,
`/api/config`, `/api/fraicheur`, `/api/sante`, page Tarifs) le 23 novembre 2026.

## 0. Résumé

- **Ce que c'est.** Lexia est un assistant d'étude pour les étudiants de licence en droit
  (https://lexia-axionstudio.cloud). Il répond à partir d'un corpus officiel déjà chargé (environ 916 000 passages :
  Constitution, 36 codes, lois, Conseil constitutionnel, Cour de cassation, Conseil d'État, traités de l'Union),
  cite chaque source et retire côté serveur toute affirmation de droit non sourcée. Cinq modes : expliquer, fiche,
  cas pratique, commentaire d'arrêt, dissertation.
- **Où on en est.** Phase de développement. Site complet en ligne, aucun abonné payant, paiement en ligne codé mais
  inactif, API Gemini au niveau gratuit, pas de SIRET attribué, pas de médiateur, nom « Lexia » non validé par un
  conseil. Aucune donnée de vente ni de fidélité : toutes les hypothèses commerciales sont à mesurer.
- **Marché.** 141 600 étudiants en licence de droit dans les universités en 2025-2026 (observé, SIES). Marché
  théorique d'environ 7,6 M€ par an au prix moyen de 5,99 € sur 9 mois ; marché accessible estimé à 1,9 M€
  (hypothèse : un quart des étudiants prêts à payer un outil spécialisé).
- **Modèle.** Freemium : Gratuit (10 questions par jour), Étudiant 4,99 €/mois, Intensif 9,99 €/mois, paiement
  unique de 1 à 12 mois sans reconduction. Coût estimé d'une question : environ 0,0028 € (jetons mesurés sur des essais, grille de prix et trois hypothèses), soit environ
  0,13 € par mois pour un compte gratuit actif et 0,61 € pour un abonné Étudiant (hypothèses d'usage).
- **Projections sur 3 ans** (2027 à 2029, micro-entreprise, avant rémunération de l'éditeur) : chiffre d'affaires de
  l'année 3 de 1,5 k€ (prudent), 19 k€ (central) et 133 k€ (ambitieux). Résultat cumulé sur 36 mois : −16 k€,
  −18 k€ et +30 k€. La publicité payante coûte plus qu'elle ne rapporte dans les trois scénarios : **sans
  publicité, le scénario central finit à +1,1 k€ avec un besoin de trésorerie de 3,8 k€, et l'ambitieux à
  +64,5 k€ au lieu de +30,2 k€** (un abonné apporté par la publicité y coûte 35 à 68 €, pour une LTV de 36 à
  40 €).
- **Leviers décisifs** (analyse de sensibilité) : la conversion vers le payant, le coût des comptes gratuits
  (quota de questions) et la discipline publicitaire (ne payer qu'une fois le CAC marginal mesuré sous la moitié de la LTV).
- **Besoin de financement.** De 3 à 4 k€ (frais juridiques et de marque, déficit des premiers mois) si la
  publicité attend des mesures, jusqu'à 18 k€ si le plan publicitaire est suivi avec les hypothèses centrales.
- **Risques majeurs** : conditions de l'API Gemini (âge minimum de 18 ans, niveau payant obligatoire pour
  l'Espace économique européen), marques « LEXIA » antérieures, fiabilité des réponses non encore notée par un
  enseignant, frontière avec la consultation juridique (D77), concurrence gratuite de Google.

## 1. Problème

1. **Le droit change, les supports d'étude vieillissent.** Un polycopié ou un manuel imprimé peut citer des numéros
   d'avant la réforme du droit des contrats de 2016 (1134, 1382...), ou une version d'article qui n'est plus en
   vigueur. L'étudiant de L1 ne sait pas encore vérifier.
2. **Les assistants généralistes ne prouvent pas ce qu'ils disent.** Un outil d'IA général peut inventer un
   numéro d'article ou une décision ; pour un étudiant en droit, une citation fausse coûte des points et de la
   confiance. Ce constat est l'hypothèse de départ du produit ; il n'a pas été mesuré sur les outils concurrents
   dans ce document.
3. **La méthode de la licence est exigeante et peu outillée.** Cas pratique (faits, problème de droit, majeure,
   mineure, conclusion), commentaire d'arrêt et dissertation suivent des plans attendus ; les retours individuels
   en TD sont rares (hypothèse non chiffrée).
4. **Les sources officielles sont gratuites mais difficiles d'accès pour un débutant.** Légifrance et les bases
   ouvertes de la DILA contiennent tout, mais il faut savoir quoi chercher.

## 2. Solution

État vérifié dans le dépôt (décisions D1 à D114) et en ligne le 23 novembre 2026.

| Fonction | Ce que fait Lexia | Référence |
|---|---|---|
| Corpus officiel | Environ 916 000 passages, mis à jour chaque nuit pour les codes et les lois (textes au 22 novembre 2026 sur `/api/fraicheur`) ; jurisprudence de la Cour de cassation au 16-17 septembre 2026 et du Conseil constitutionnel au 16 octobre 2026 (archives DILA), complétée par le site du Conseil constitutionnel et bientôt Judilibre | D78, D95, D113 |
| Citations contrôlées | Une source citée doit être un extrait fourni ; une affirmation de droit positif sans source est retirée ; un numéro absent des extraits fait retirer l'élément ; sinon abstention | D22, D109 |
| Version en vigueur | Un clic vérifie la version d'un article ; 26 anciens numéros du Code civil reliés aux actuels | D53, D61, D95 |
| Méthodes | Cinq modes avec rubriques imposées, niveau adapté au semestre (L1 S1 à L3 S6), réponse directe en tête | D49, D66, D89 |
| Révision | Questionnaires (QCM, vrai ou faux, questions ouvertes), fiches, cartes à retourner avec répétition espacée, résumés vocaux, cartes mentales | D104, D106, D112 |
| Cours de l'étudiant | Dépôt de PDF, Word, PowerPoint, OpenDocument, photos (OCR), confrontés aux textes en vigueur | D57, D93, D107 |
| 20 matières | De la L1 à la L3, tirées des maquettes de 8 facultés | D97, D98 |
| Garde-fous | Refus des demandes de pur conseil (rédiger un courrier, prédire l'issue, chiffrer, décider) ; faits racontés expliqués avec un rappel | D77 |
| Sécurité et données | Double authentification, secrets chiffrés, effacement réel, export des données, registre des traitements | D67, D68, D99, D108 |

Qualité mesurée, avec ses limites : sur les jeux d'évaluation internes, la recherche retrouve la source attendue
pour 187 questions de cours sur 187 ; sur des cas pratiques écrits avant les règles qui les corrigent, environ un
sur deux au départ (D79, D84), 7 sur 15 sur le jeu témoin jamais utilisé pour régler (D109). Ces jeux sont écrits
par l'auteur du produit : **la notation par un enseignant n'est pas faite** (D11, D87). Aucune phrase sur la
fiabilité ne peut s'appuyer sur autre chose aujourd'hui.

Démonstration : captures du site en ligne dans [captures/](captures/) (accueil avec un exemple de réponse, tarifs ; page d'accueil complète).

## 3. Marché

### Population (sources : partie 1 de sources.md)

| Indicateur | Valeur | Statut |
|---|---|---|
| Étudiants en licence de droit, universités, 2025-2026 | 141 600 | Observé |
| Même périmètre, 2026-2027 | 142 900 | Projeté par le ministère |
| L1 « Droit, sciences politiques », 2024-2025 | 66 079 | Observé (somme calculée sur SISE) |
| Master de droit, 2025-2026 | 82 700 | Observé, hors cible actuelle |

### TAM, SAM, SOM

| Niveau | Définition | Calcul | Résultat |
|---|---|---|---|
| TAM (marché total) | Tous les étudiants en licence de droit des universités, s'ils payaient Lexia pendant l'année universitaire | 141 600 × 5,99 € × 9 mois | **7,63 M€ par an** |
| SAM (marché accessible) | Étudiants prêts à payer un outil d'étude spécialisé, joignables par les canaux du plan marketing | 141 600 × 25 % (hypothèse non sourcée) = 35 400 étudiants ; 35 400 × 5,99 € × 9 mois | **1,91 M€ par an** |
| SOM (part atteignable à 3 ans) | Abonnés payants et chiffre d'affaires de l'année 3 selon les projections | Feuille Synthèse de `projections.xlsx` | Prudent : 24 abonnés en fin d'année 3, 1,5 k€ ; central : 325 abonnés, 19,2 k€ (1,0 % du SAM) ; ambitieux : 2 781 abonnés, 132,8 k€ (7,0 % du SAM) |

Hypothèses du calcul : 5,99 € est la recette moyenne d'un abonné avec 80 % d'Étudiant et 20 % d'Intensif
(hypothèse de mix) ; 9 mois payés par an est une hypothèse (pas de cours en été, D86 n'impose pas d'abonnement
continu). Avec 12 mois, le TAM serait de 10,2 M€. Les 25 % du SAM ne reposent sur aucune étude : à remplacer par
une enquête auprès d'étudiants ou par les premiers taux de conversion mesurés.

Extensions possibles, non chiffrées ici : master de droit (82 700), capacité en droit, préparation aux concours
(CRFPA, ENM : exclue tant que la jurisprudence n'est pas à jour, plan marketing partie 2), établissements privés,
offre pour les facultés.

## 4. Concurrence

| Alternative | Prix pour l'étudiant | Force | Faiblesse face à Lexia | Source |
|---|---|---|---|---|
| Gemini Notebook (ex-NotebookLM) | Gratuit ; AI Plus offert 12 mois aux étudiants majeurs en France jusqu'au 31/12/2026 ; AI Pro à 5,49 €/mois pour les étudiants | Riche en révision (audio, vidéo, cartes mentales), formats nombreux, applications mobiles, marque Google | Outil général : l'étudiant doit apporter ses documents ; pas de corpus juridique officiel ni de contrôle de la version en vigueur | `docs/comparatif-notebooklm.md`, pages Google du 19/11/2026 |
| Assistants d'IA généralistes | Gratuits ou payants (non vérifiés ici) | Notoriété, polyvalence | Pas de garantie de citation, risque d'article inventé (hypothèse, non mesurée dans ce document) | Non vérifié |
| Légifrance, bases ouvertes de la DILA | Gratuit | Source officielle complète | Recherche à la main, pas d'explication ni de méthode | Usage public |
| Bases juridiques éditoriales des bibliothèques universitaires | Souvent fournies par l'université (non vérifié) | Doctrine, commentaires, manuels | Pas d'assistant de méthode pensé pour la L1 (hypothèse) | Non vérifié |
| Manuels, fiches, annales, tutorat | Payant ou gratuit selon les cas | Référence du cours | Pas interrogeable ; peut dater d'avant une réforme | Plan marketing, partie 3 |

Lecture honnête (comparatif du 19 novembre 2026) : sur le prix, la révision multimédia, les formats et le mobile,
Lexia ne gagne pas face à Gemini Notebook et ne doit pas prétendre gagner. Ses atouts propres sont le droit
positif sans rien préparer, des citations qui prouvent la règle, la version en vigueur et les méthodes de la
licence. Une publicité comparative nommée est écartée (C. consom. L. 122-1 et L. 122-5, plan marketing 7.3).

## 5. Positionnement

**Pour l'étudiant de licence en droit, Lexia est l'espace d'étude qui répond à partir du droit en vigueur, cite
chaque source et applique les méthodes de la licence, sans rien avoir à préparer.**

- Complément du cours et du manuel, jamais leur remplacement (« vérifie avant de citer »).
- Transparence sur les limites comme argument de confiance : fraîcheur de chaque source affichée, abstention
  plutôt qu'invention.
- Prix d'entrée bas (4,99 €), du même ordre que les offres payantes de Google pour les étudiants ; mais la gratuité
  temporaire d'AI Plus pour les étudiants majeurs pèse sur la sensibilité au prix jusqu'à fin 2027 au moins.

## 6. Modèle économique

### Formules (en ligne, `api/plans.py`)

| Formule | Prix | Questions par jour | Questionnaires par jour | Cours déposés |
|---|---|---|---|---|
| Gratuit (compte requis) | 0 € | 10 | 2 | 3 |
| Étudiant | 4,99 € par mois | 100 | 20 | 30 |
| Intensif | 9,99 € par mois | 300 | 100 | 100 |

Paiement : Stripe Checkout, paiement unique de 1 à 12 mois, sans reconduction automatique (D86) ; 1,5 % + 0,25 €
par paiement. Micro-entreprise en franchise de TVA : le prix affiché est le chiffre d'affaires tant que les seuils
ne sont pas franchis.

### Économie unitaire (formules dans le classeur)

Coût estimé d'une question : 0,00306 $ soit **0,00279 €**. Seuls les jetons sont mesurés, sur 20 appels
d'essai ; le reste vient de la grille de prix et d'hypothèses. Calcul à partir des jetons mesurés (2 036 en entrée et 538 en
sortie par réponse, 136 et 60 par reformulation, 0,74 reformulation par question), de la grille du niveau payant
de Gemini, de 5 % de questions sur Gemini 3.8 Flash et 5 % sur Groq payant (hypothèses) et de 25 % d'appels annexes
(questionnaires, résumés vocaux, cartes mentales ; hypothèse).

| Par mois | Compte gratuit actif | Abonné Étudiant | Abonné Intensif |
|---|---|---|---|
| Questions (hypothèse centrale) | 45 | 220 | 600 |
| Prix encaissé | 0 € | 4,99 € | 9,99 € |
| Coût du modèle | 0,13 € | 0,61 € | 1,67 € |
| Frais Stripe (achat moyen de 2 mois, hypothèse) | 0 € | 0,20 € | 0,27 € |
| Marge brute | −0,13 € | 4,18 € | 8,04 € |
| Cotisations et formation professionnelle (25,8 % du CA) | 0 € | 1,29 € | 2,58 € |
| Contribution nette | −0,13 € | 2,89 € | 5,47 € |

Conséquences :

- Un abonné Étudiant couvre le coût du modèle d'environ 33 comptes gratuits actifs (4,18 € / 0,13 €).
- Seuil de perte d'un abonné Étudiant : environ 1 700 questions par mois (57 par jour) avant que le modèle et Stripe
  dépassent le prix ; Intensif : environ 3 480 (116 par jour). Les plafonds (100 et 300 par jour) dépassent ces
  seuils : un abonné qui épuise son quota chaque jour coûte plus qu'il ne rapporte, comme le notait déjà
  `docs/avant-la-vente.md` avec un autre taux de change et sans appels annexes.
- Le 1er janvier 2027, le prix de Gemini 3.8 Flash (secours) double : chaque point de questions servies par ce
  secours renchérit la question.

## 7. Stratégie d'acquisition

Reprise de `docs/marketing/plan.md`, avec les enseignements chiffrés du modèle.

1. **Phase organique (décembre 2026 à avril 2027 au moins, 0 € de publicité)** : vidéos courtes (TikTok, Reels,
   Shorts), carrousels Instagram, LinkedIn pour les enseignants et associations, Discord de promo, associations et
   corpos une par une, ambassadeurs majeurs sous contrat écrit à partir de janvier 2027. Prérequis : Gemini au
   niveau payant avant toute communication qui fait venir du public.
2. **Phase payante (au plus tôt aux partiels de mai 2027)** : palier test de 150 à 300 € sur Instagram, puis 500 à
   1 000 € par mois à la rentrée 2027 si le coût par compte est acceptable ; ciblage 18 ans et plus, sans audience
   tirée de la liste des inscrits.
3. **Garde-fou issu des projections** : le bon indicateur est le **CAC marginal**, la publicité divisée par les
   abonnés en plus qu'elle apporte (feuille Synthèse, lignes « apportés par la publicité »). Le CAC moyen divise
   la publicité par tous les nouveaux abonnés, organiques compris : il sous-estime le coût d'un abonné acquis
   de 4 à 14 fois selon l'année et le scénario. Dans le scénario central, le CAC marginal vaut 185, 103 et 106 € (années 1 à 3) pour une
   LTV de 8 à 23 € ; dans l'ambitieux (coût d'inscription de 2,5 €, conversion de 2 %), 68, 38 et 35 € pour une
   LTV de 36 à 40 €, soit un rapport LTV / CAC marginal d'environ 0,5 puis 1,0. **Même dans le scénario
   ambitieux, la publicité rapporte moins qu'elle ne coûte** : sans elle, le résultat cumulé sur 36 mois passe de
   −18,4 à +1,1 k€ (central) et de +30,2 à +64,5 k€ (ambitieux). **Règle proposée : ne passer au palier suivant
   que si le CAC marginal mesuré (abonnés venus des campagnes, repérés par l'origine des inscriptions, D110) est
   inférieur à la moitié de la LTV mesurée**, la LTV étant calculée avec le vrai taux de rachat. La LTV du
   classeur est nette du coût des comptes gratuits (taux de marge de l'ensemble, 51 % l'année 3 du central) ; la
   marge propre d'un abonné est de 80 à 84 % (partie 6).
4. **Indicateurs** : inscriptions, fidélité à 7 et 30 jours (déjà dans l'administration, D111), origine des
   inscriptions (D110), questions par compte actif, conversion, rachat, coût par question (`eval/cout.py`).

## 8. Équipe

- **Arthur Champagne-Forterre**, fondateur, entrepreneur individuel sous le nom commercial Axion Studio : produit,
  développement (assisté par des outils d'IA de programmation), contenu et marketing. Seul à temps partiel ou
  plein (non précisé dans les documents lus).
- **Manques identifiés** : enseignant référent pour noter les réponses (D11, ouvert depuis le 11 novembre 2026) ;
  avocat pour les CGU et la frontière de la consultation juridique (D77) ; conseil en propriété industrielle pour
  le nom ; ambassadeurs étudiants.
- **Risque de personne clé** : tout repose sur une personne (code, serveur, support, comptes). Atténuation : code
  versionné, sauvegardes hors serveur (D56, D80), décisions écrites dans `docs/decisions.md`.

## 9. Montage juridique

### Statut actuel

Entrepreneur individuel en micro-entreprise, nom commercial Axion Studio, TVA non applicable (article 293 B du
CGI) ; déclaration au guichet unique de l'INPI en novembre 2026, SIRET en cours d'attribution (`/api/config` le
23 novembre 2026).

| Règle (2026) | Valeur | Effet pour Lexia |
|---|---|---|
| Cotisations sociales | 25,6 % du CA (BNC non réglementé) ou 21,2 % (BIC prestations de services) | Le classement d'un abonnement à un logiciel en ligne n'est tranché par aucune page lue : **à faire confirmer par l'Urssaf** (EDI-13). Le modèle retient 25,6 % par prudence (`Hypothèses!C57`) ; avec 21,2 % et 0,1 % de formation professionnelle, le scénario ambitieux finit à +39,9 k€ au lieu de +30,2 k€ et le central à −16,9 k€ au lieu de −18,4 k€. Changer C57 (et la formation professionnelle) seulement après la réponse de l'Urssaf |
| Formation professionnelle | 0,2 % du CA (activité libérale), 0,1 % (activité commerciale), page F23459 | Ajoutée par prudence (0,2 %) |
| Versement libératoire (option) | 2,2 % (BNC) ou 1,7 % (BIC) | Option avant le 30 septembre de l'année précédente, sous condition de revenu fiscal |
| Plafond du régime | 83 600 € HT de CA (services) | Dépassé l'année 3 du scénario ambitieux (132,8 k€) : sortie du régime après deux années consécutives |
| Franchise de TVA | 37 500 € (année précédente) et 41 250 € (année en cours) | Perdue l'année 2 du scénario ambitieux, dès le mois du dépassement (mois 20, août 2028) : le prix affiché inclut alors 20 % de TVA (recette moyenne de 6,24 € à 5,20 €) |
| Ventes à des particuliers d'autres pays de l'UE | Seuil de 10 000 € HT, guichet OSS au-delà | Marginal tant que la cible est française |

### Passage en société (SASU) : quand y penser

Éléments lus : impôt sur les sociétés à 15 % jusqu'à 42 500 € de bénéfice puis 25 % ; dividendes au prélèvement
forfaitaire unique de 31,4 % en 2026 ; cotisations d'environ 60 % de la rémunération brute du président ; annonce
légale de 142 € HT (frais de greffe non chiffrés). Déclencheurs à surveiller, sans conclusion à ce stade : chiffre
d'affaires qui approche le plafond micro (scénario ambitieux, année 2 ou 3), besoin d'accueillir un investisseur au
capital, besoin de séparer le patrimoine ou de déduire des charges réelles importantes. À arbitrer avec un
expert-comptable.

### Obligations avant de vendre (déjà listées dans `docs/avant-la-vente.md`)

- Médiateur de la consommation : obligatoire ; SMP à 25 € HT pour 3 ans sous 60 000 € de CA (médiation facturée en
  plus si elle a lieu) ; amende administrative jusqu'à 3 000 € pour une personne physique (L. 641-1).
- API Gemini au niveau payant (bloquant), téléphone de l'hébergeur, SIRET, Stripe en mode réel.
- Marque : dépôt INPI à 190 € pour une classe et 40 € par classe supplémentaire, soit 270 € pour les classes 9, 41
  et 42 ; seulement après l'avis d'un conseil (partie 11).
- CGU et politique de confidentialité à faire relire par un avocat (D92, D108).
- AI Act, article 50 : marquage des contenus générés (en-tête `X-AI-Generated`, D92) ; DSA : modération et point de
  contact (D92).
- App iOS : commission App Store de 15 % (Small Business Program) si les formules y sont vendues, cotisation
  Apple de 99 $ par an ; voie de vente non tranchée (D101).

## 10. Projections financières

Classeur : [projections.xlsx](projections.xlsx) (feuilles Lisez-moi, Synthèse, Graphiques, Hypothèses, Prudent,
Central, Ambitieux). Année 1 = 2027. 36 mois calculés mois par mois ; aucune valeur saisie dans les sorties.
Vérification : les 6 130 formules ont été recalculées par Microsoft Excel le 23 novembre 2026, sans erreur, et le
classeur est enregistré avec ses valeurs en cache (`outils/enregistrer_excel.sh`) : il s'affiche aussi dans
l'aperçu du Mac, sur GitHub et dans une messagerie. Le coût par question et les premiers mois du scénario central
ont été recalculés à la main. Corrections de l'audit du 23 novembre 2026 : CAC marginal (F1), LTV nommée nette du
coût des gratuits (F3), TVA due dès le mois du dépassement du seuil (F9), Resend Pro dès que le jour le plus chargé
dépasse 100 e-mails, avec une hypothèse non sourcée de 3 fois la moyenne quotidienne (F10).

### Hypothèses de scénario (toutes non sourcées, à remplacer par des mesures)

| Hypothèse | Prudent | Central | Ambitieux |
|---|---|---|---|
| Paiement en ligne actif à partir de | avril 2027 | février 2027 | janvier 2027 |
| Inscriptions organiques par mois, année 1, avant saisonnalité | 150 | 400 | 1 000 |
| Croissance annuelle des inscriptions organiques | 20 % | 50 % | 80 % |
| Coût d'une inscription par la publicité | 6 € | 4 € | 2,5 € |
| Comptes gratuits actifs perdus par mois | 35 % | 25 % | 20 % |
| Conversion mensuelle des gratuits actifs vers le payant | 0,6 % | 1,2 % | 2,0 % |
| Part de l'Intensif parmi les nouveaux payants | 15 % | 20 % | 25 % |
| Abonnés perdus par mois (non-rachat) | 15 % | 10 % | 7 % |
| Perte supplémentaire en juillet et août | 25 points | 20 points | 15 points |
| Questions par mois : gratuit, Étudiant, Intensif | 60, 300, 800 | 45, 220, 600 | 40, 180, 500 |
| Publicité : année 1, année 2, année 3 | 1 150, 3 000, 5 000 € | 2 400, 6 000, 12 000 € | 3 450, 15 000, 30 000 € |

### Résultats (arrondis)

| | Prudent | Central | Ambitieux |
|---|---|---|---|
| Inscriptions, année 1 / 2 / 3 | 2 000 / 2 700 / 3 400 | 5 400 / 8 700 / 13 800 | 13 400 / 27 600 / 50 900 |
| Abonnés payants en fin d'année 1 / 2 / 3 | 13 / 19 / 24 | 98 / 201 / 325 | 501 / 1 411 / 2 781 |
| Chiffre d'affaires HT, année 1 / 2 / 3 | 0,3 / 1,1 / 1,5 k€ | 2,9 / 11,2 / 19,2 k€ | 15,4 / 67,3 / 132,8 k€ |
| Taux de marge brute, année 1 / 2 / 3 | négatif | 18 % / 48 % / 51 % | 54 % / 66 % / 65 % |
| Résultat net, année 1 / 2 / 3 | −5,4 / −4,2 / −6,3 k€ | −6,3 / −4,2 / −7,9 k€ | −2,7 / +11,3 / +21,6 k€ |
| Trésorerie en fin d'année 3 (départ à 0 €) | −15,9 k€ | −18,4 k€ | +30,2 k€ |
| Point mort (premier mois à résultat positif) | non atteint | juillet 2028 (mois 19), non durable | juin 2027 (mois 6) |
| Besoin de financement (trésorerie la plus basse) | 15,9 k€ | 18,4 k€ | 3,7 k€ |
| LTV nette / CAC moyen, année 3 (organiques compris) | négatif | 23 € / 22 € = 1,0 | 36 € / 8 € = 4,4 |
| LTV nette / CAC marginal, année 3 (abonnés dus à la publicité) | négatif | 23 € / 106 € = 0,2 | 36 € / 35 € = 1,0 |
| Résultat cumulé sur 36 mois sans publicité | −6,4 k€ | +1,1 k€ | +64,5 k€ |

Charges de l'année 1 hors publicité : environ 3 060 € de frais ponctuels (conseil en propriété industrielle et
avocat, hypothèses de 800 et 1 500 € HT ; médiateur ; dépôt de marque) et environ 50 € par mois de charges fixes
(serveur 14,99 €, domaine, assurance et banque en hypothèse).

### Sensibilité du scénario central (résultat cumulé sur 36 mois)

Calculée en modifiant une hypothèse à la fois dans une copie du classeur, puis en recalculant.

| Variante | Abonnés fin année 3 | Résultat cumulé | Besoin de trésorerie |
|---|---|---|---|
| Central tel quel | 325 | −18,4 k€ | 18,4 k€ |
| Conversion mensuelle de 2 % au lieu de 1,2 % | 529 | −6,2 k€ | 6,2 k€ |
| Perte mensuelle des abonnés de 7 % au lieu de 10 % | 388 | −15,2 k€ | 15,2 k€ |
| Aucune publicité payante | 258 | +1,1 k€ | 3,8 k€ |
| Gratuit limité à 25 questions par mois en moyenne (au lieu de 45) | 325 | −13,2 k€ | 13,2 k€ |
| Conversion de 2 % et gratuit à 25 questions | 529 | −1,2 k€ | 4,6 k€ |
| Conversion de 2 %, gratuit à 25 questions, sans publicité | 419 | +15,3 k€ | 3,2 k€ |

Enseignements :

1. **La conversion est le premier levier** ; elle est inconnue. La mesurer est la priorité du premier semestre
   2027.
2. **Avec les hypothèses actuelles, la publicité ne se justifie dans aucun scénario** : même dans l'ambitieux,
   un abonné apporté par la publicité coûte 35 à 68 € pour une LTV de 36 à 40 €, et le résultat cumulé passe de
   +30,2 k€ à +64,5 k€ sans elle. Elle ne deviendrait rentable qu'avec un coût d'inscription nettement plus bas ou
   une conversion plus élevée, mesurés ; la règle du CAC marginal inférieur à la moitié de la LTV (partie 7)
   l'écarte tant que ce n'est pas le cas.
3. **Le gratuit coûte** : à 45 questions par mois, un compte gratuit actif coûte 0,13 € ; le quota de
   10 questions par jour pourrait être revu si la conversion reste basse (décision produit, pas une
   recommandation ferme).
4. Même dans le meilleur cas, Lexia reste un petit revenu à 3 ans tant que la conversion n'est pas mesurée ; le
   scénario ambitieux suppose des hypothèses qu'aucune donnée ne soutient aujourd'hui.

## 11. Risques

| Risque | Probabilité | Impact | Atténuation |
|---|---|---|---|
| **Conditions de l'API Gemini : âge.** Les conditions interdisent un service susceptible d'être utilisé par des moins de 18 ans (« Age Requirements », lu par l'audit du 19/11/2026) ; Lexia accepte les inscriptions dès 15 ans. Risque de coupure de la clé, sans recours | Moyenne | Très élevé (service arrêté) | Trancher entre 18 ans (simple, ferme Lexia aux bacheliers de 17 ans) et un fournisseur dont les conditions acceptent les mineurs, par exemple Vertex AI, à vérifier (`docs/note-editeur-2026-11-20.md`, point 1) |
| **Conditions de l'API Gemini : niveau payant.** Le niveau gratuit n'est pas autorisé pour des utilisateurs de l'EEE ; en ligne le 23/11/2026 : `gemini_payant: false` | Certaine tant que rien n'est fait | Élevé (conformité, confidentialité) | Activer la facturation (5 $ de prépaiement minimum) avant toute communication publique |
| **Dépendance à Google** : prix, modèles retirés (Gemini 3.5 Flash a disparu de la grille, D83), doublement du prix du secours au 1er janvier 2027 | Élevée | Moyen | Secours Groq déjà en place (D51, D76), mesure mensuelle du coût (`eval/cout.py`), coût par question suivi dans le classeur |
| **Marque.** Marques « LEXIA » identiques enregistrées pour des logiciels éducatifs dans l'Union (EUIPO 015377401, OMPI 1647070) et pour des services juridiques en France (INPI 4010966) (`docs/marque-lexia.md`) | Non évaluée (pas d'avis de conseil) | Élevé (renommage, contrefaçon, L. 713-2 et L. 716-4 du CPI) | Avis d'un conseil en propriété industrielle avant toute dépense de visibilité ; nom de repli préparé ; dépôt seulement après l'avis |
| **Fiabilité des réponses juridiques.** Erreur de droit, article mal appliqué, jurisprudence non à jour (retard de 2 à 3 mois pour la Cour de cassation) | Moyenne | Élevé (confiance, réputation) | Contrôle des citations, abstention, fraîcheur affichée ; notation par un enseignant à faire ; jeu témoin à ne pas corriger (D109) ; aucune promesse « sans erreur » (plan marketing partie 4) |
| **Consultation juridique (D77).** Lexia explique le droit applicable à des faits racontés à la première personne ; dans un service payant, cela peut ressembler à une consultation juridique rémunérée par une personne non autorisée (loi n° 71-1130, article 54, non relu ici) | Faible à moyenne (non évaluée) | Élevé | Avis d'un avocat (questions prêtes dans la note du 20/11/2026) ; option : reformuler les faits en exercice neutre pour les comptes payants ; refus déjà codé des quatre demandes de pur conseil |
| **Concurrence gratuite** (Gemini Notebook, AI Plus offert aux étudiants) | Élevée | Élevé sur la conversion | Positionnement spécialisé, pas de comparaison nommée ; vérifier en août 2027 si l'offre étudiante de Google est renouvelée |
| **Vente sans médiateur ni SIRET** : bouton de demande par e-mail actif en ligne | Certaine aujourd'hui | Moyen (amende jusqu'à 3 000 €) | Masquer le bouton tant que médiateur et SIREN manquent, ou adhérer vite (note du 20/11/2026, point 2) |
| **Saisonnalité** : creux de juillet-août, rachat non automatique | Élevée | Moyen | Paiement de plusieurs mois, offres de rentrée et de partiels ; trésorerie de précaution |
| **Capacité du serveur** (2 processeurs, 8 Go ; reclassement local limité à 2 à la fois, D114) | Moyenne en cas de succès | Moyen (lenteur) | Durées par étape dans le journal (D114) ; passage à un serveur plus gros, coût à chiffrer |
| **Personne clé** | Permanente | Élevé | Documentation, sauvegardes, accès de secours à prévoir |
| **Données personnelles et mineurs** | Faible | Élevé | Registre, minimisation, pas de ciblage des mineurs, avis d'avocat sur le nom obligatoire (D102) |

## 12. Feuille de route sur 12 mois (décembre 2026 à novembre 2027)

| Période | Produit et conformité | Commercial | Indicateur de passage |
|---|---|---|---|
| Décembre 2026 | Gemini au niveau payant ; décision âge 15 ou 18 ans ; SIRET ; médiateur ; avis du conseil en propriété industrielle ; clé Judilibre | Mois 1 organique (26 publications prêtes, `contenus-mois-1.md`) | Prérequis levés |
| Janvier 2027 | Stripe en réel (essai remboursé) ; relecture des CGU et avis sur D77 par un avocat ; appel à des enseignants pour la notation | Associations et corpos ; ambassadeurs | Premiers paiements ; fidélité à 7 jours mesurée |
| Février à mars 2027 | Dépôt de marque (si l'avis est favorable) ; notation par un enseignant ; ajustement du quota gratuit selon le coût mesuré | Contenus de méthode (commentaire, dissertation) | Taux de conversion et de rachat mesurés sur 8 semaines |
| Avril à mai 2027 | Mesure du coût réel par question (`eval/cout.py`) et mise à jour du classeur | Palier publicitaire 1 (150 à 300 €) seulement si la règle CAC / LTV est tenue | CAC mesuré |
| Juin à août 2027 | Décision sur l'app iOS et la voie App Store ; fiches et cartes synchronisées entre appareils | Bilan ; préparation de la rentrée ; vérifier le renouvellement de l'offre étudiante de Google | LTV mesurée sur un semestre |
| Septembre à octobre 2027 | Capacité du serveur selon les durées du journal | Rentrée : palier 2 (500 à 1 000 € par mois) si justifié ; semaines d'intégration | Coût par abonné, abonnés actifs |
| Novembre 2027 | Revue des prix et des formules ; choix du statut (micro ou société) selon le chiffre d'affaires | Bilan annuel ; projections remplacées par les mesures | Comparaison réel et scénarios |

## 13. Besoin de financement

Calcul : trésorerie la plus basse sur 36 mois dans le classeur, avec un apport de départ à 0 €.

| Cas | Besoin |
|---|---|
| Ambitieux | 3,7 k€ (au mois 10) |
| Central sans publicité payante | 3,8 k€ |
| Central avec le plan publicitaire | 18,4 k€ (toujours en baisse au mois 36) |
| Prudent | 15,9 k€ (toujours en baisse au mois 36) |

Lecture : environ 3 à 4 k€ couvrent les frais juridiques et de marque de l'année 1 et le déficit des premiers mois,
à condition de ne financer la publicité qu'une fois le CAC marginal et la LTV mesurés. Au-delà, le besoin dépend surtout de
la politique publicitaire. Pistes de financement à étudier, sans recommandation : apport personnel, prêts d'honneur
de réseaux d'accompagnement à la création, aides publiques à l'innovation (aucune n'a été vérifiée dans ce
document). Une levée de fonds au capital supposerait une société (partie 9).

## 14. Limites de ce document

- Aucune donnée réelle de vente, de conversion ni de rachat : les scénarios sont des ordres de grandeur.
- Coût par question estimé : jetons tirés de 20 appels d'essai, pas de trafic réel ; prix de la grille et trois
  hypothèses non sourcées (part des secours, appels annexes).
- E-mails : le jour le plus chargé est supposé valoir 3 fois la moyenne quotidienne (non mesuré).
- Chiffres de concurrence de Google repris du comparatif du 19 novembre 2026, non relus le 23.
- Plusieurs pages officielles n'ont pas pu être lues directement (Urssaf, economie.gouv.fr) ; le classement BIC ou
  BNC de l'activité et le calendrier de l'ACRE restent à confirmer.
- Aucune conclusion juridique (marque, consultation juridique, âge) : à faire apprécier par un avocat ou un
  conseil en propriété industrielle.
