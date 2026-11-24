# Passer Gemini au niveau payant avant la bêta ?

Note de décision pour l'éditeur, 24 novembre 2026. Prix et conditions lus en ligne le 24 novembre 2026 (liens en
fin de note). Aucun appel à l'API Gemini n'a été fait pour la préparer.

## Recommandation

**Oui : activer la facturation Gemini avant d'envoyer le moindre code de bêta.** Pour 20 à 60 testeurs, le coût
attendu est de l'ordre de 10 à 35 dollars par mois ; un prépaiement de 25 dollars suffit pour démarrer et plafonne
la dépense. Sans cela, la bêta se ferait hors des conditions de Google, en partie sur le modèle de secours, et
les vérifications de qualité resteraient bloquées.

## Constat

- Le 23 novembre, le quota gratuit a été épuisé (réponses 429 sur les trois modèles Gemini) et, aux heures
  chargées, le niveau gratuit répond 503 : le site bascule alors sur Groq (`docs/recette-2026-11-23.md`,
  remarques). La réponse fausse de la recette (R-1, cas pratique sans la loi Badinter) venait du modèle de secours.
- Les vérifications de qualité attendent ce quota : réponses à revérifier après les corrections de D122,
  dossier enseignant (`docs/relecture-enseignant/`), réglage R-3 du reclassement, jeux d'`eval/` (environ
  330 cas).
- En ligne le 24 novembre : `gemini_payant: false` (`/api/config`), encarts « à régulariser » dans la politique de
  confidentialité (audit du 23/11, E2 et EDI-2).
- Modèles configurés (`deploy/env.production.exemple` ; le `.env` du serveur n'a pas été lu) : réponse
  `gemini-3.5-flash-lite`, secours `gemini-flash-lite-latest` puis `gemini-3.8-flash`, reformulation
  `gemini-3.5-flash-lite` ; en dernier recours Groq (`qwen/qwen3.8-27b`, puis `openai/gpt-oss-120b`).

## Ce que change le niveau payant

| | Niveau gratuit | Niveau payant |
|---|---|---|
| Prix, `gemini-3.5-flash-lite` (par million de jetons) | Gratuit | 0,30 $ en entrée, 2,50 $ en sortie (réflexion comprise) ; aucun changement annoncé |
| Prix, `gemini-3.8-flash` (secours) | Gratuit | 0,75 $ et 3,75 $ jusqu'à fin 2026, puis 1,50 $ et 7,50 $ à partir de janvier 2027 |
| `gemini-flash-lite-latest` | Alias absent des pages de tarifs et de modèles lues : prix non vérifiable, à retirer de la configuration ou à remplacer par un nom de modèle de la grille | idem |
| Questions et réponses des étudiants | « Used to improve our products » : oui ; des relecteurs humains peuvent lire, annoter et traiter les entrées et sorties | Non utilisées pour améliorer les produits ; journalisées pour une durée limitée, seulement pour détecter les abus (durée non chiffrée dans la page lue) |
| Étudiants dans l'Espace économique européen | Non autorisé : pour un service accessible dans l'EEE, en Suisse ou au Royaume-Uni, « You may use only Paid Services » | Autorisé |
| Quotas | 429 et 503 constatés le 23/11 ; limites par minute et par jour non publiées sur la page publique, visibles dans AI Studio | Niveau 1 dès qu'un compte de facturation est lié, sans dépense minimale ; dépense limitée à 10 $ par fenêtre de 10 minutes et plafond de 250 $ au niveau 1 ; niveau 2 après 100 $ payés et 3 jours. Limites par minute à lire dans AI Studio |
| Âge | 18 ans minimum, y compris pour un service susceptible d'être utilisé par des moins de 18 ans | Identique : **le niveau payant ne règle pas la question des 15-17 ans** (note du 20/11, point 1) |

Le passage au payant ne supprime pas les 503 dus à la charge chez Google, mais les 429 de quota disparaissent aux
volumes d'une bêta, et Groq reste le secours.

## Coût mensuel estimé

Coût d'une question (réponse plus reformulation dans 74 % des cas, D88), avec les jetons mesurés sur 20 appels
d'essai (`logs/modele.jsonl`, 13 au 17 novembre : 2 036 jetons d'entrée et 538 de sortie par réponse, 136 et 60 par
reformulation) :

| Modèle qui répond | Coût d'une question |
|---|---|
| `gemini-3.5-flash-lite` (cas normal) | 0,0021 $ |
| `gemini-3.8-flash` (secours), prix 2027 | 0,0076 $ |
| Groq `qwen/qwen3.8-27b` payant, sans reformulation | 0,0038 $ |

On ajoute 25 % pour les questionnaires, résumés vocaux et cartes mentales (hypothèse : aucun journal ne les
mesure). Un résumé vocal ou une carte mentale coûte au plus environ 0,009 $ (3 072 jetons de sortie au plus).

Coût par mois, en dollars, tout sur `gemini-3.5-flash-lite`. Les niveaux d'usage sont des hypothèses : 45 et
220 questions par mois sont celles du business plan pour un compte gratuit et un abonné Étudiant ; 600 correspond
à une vingtaine de questions par jour en période de partiels ; 3 000 est le plafond de la formule Étudiant
(100 par jour), que les testeurs auront (`docs/beta/message-recrutement.md`, point 4).

| Étudiants actifs | 45 questions par mois | 220 questions | 600 questions | Plafond (3 000) |
|---|---|---|---|---|
| 20 | 2,4 $ | 11,5 $ | 31,5 $ | 157 $ |
| 60 | 7,1 $ | 34,6 $ | 94,4 $ | 472 $ |
| 200 | 23,6 $ | 115 $ | 315 $ | 1 573 $ |

Si toutes les réponses passaient par `gemini-3.8-flash` (panne durable de flash-lite), multiplier par 3,6. Une
passe complète des jeux d'évaluation (330 cas, deux passages) coûte environ 1,4 $. En euros, diviser par 1,0968
(Banque de France, 18 novembre 2026).

Lecture : pour une bêta de 20 à 60 étudiants pendant les partiels, compter 10 à 35 $ par mois en usage normal,
jusqu'à 100 $ si tous révisent intensément. Le plafond de 3 000 questions par mois n'est qu'une borne.

## Et Groq seul, en secours ?

| | Gemini payant (Groq en secours) | Groq seul |
|---|---|---|
| Coût d'une question | 0,0021 $ | 0,0038 $ au prix payant de Qwen (0,80 $ et 4,00 $ par million, lu le 23/11), soit presque le double ; 0,0006 $ avec `gpt-oss-120b` (0,15 $ et 0,60 $) |
| Extraits envoyés au modèle | 8 | 4 (D51), et pas de reformulation de la question (elle passe par Gemini) : la recherche retrouve moins bien l'article attendu (D27, D47) |
| Qualité constatée | Référence des évaluations | gpt-oss-120b : fautes de français et repères « S1 » dans le texte (D76) ; la réponse fausse de la recette du 23/11 (R-1) venait du secours |
| Niveau gratuit de Groq | Sans objet | Limites relevées le 23/11 sur la page de Groq, présentées comme celles du plan Developer : 30 requêtes par minute, 1 000 par jour, 8 000 jetons par minute, 200 000 par jour ; environ 2 600 jetons par question, donc de l'ordre de 3 questions par minute et 75 par jour pour tout le site si elles valent pour le plan gratuit |
| Stabilité | Modèles « Stable » chez Google | Qwen en préversion chez Groq, « may be discontinued at short notice » (D76) |
| Données | Pas d'amélioration des produits ; conforme pour l'EEE | Traitement aux États-Unis, « Zero Data Retention » à vérifier dans la console (EDI-2 de la note du 20/11) |

Les pages de Groq ont refusé la lecture automatique le 24 novembre (403) : les chiffres Groq sont ceux lus le
23 novembre (`docs/business/sources.md`), à revérifier dans un navigateur. Conclusion : Groq seul ne tient pas
une bêta (débit gratuit trop bas, recherche dégradée, qualité inférieure) et, en payant, coûte plus cher que
Gemini pour une moins bonne réponse. Il reste utile comme secours.

## Ce qu'il faut faire (par l'éditeur, personne d'autre)

Personne d'autre que l'éditeur ne crée de compte ni n'entre de moyen de paiement.

1. Google AI Studio, page des clés API ou des projets : sur le projet de la clé de production, colonne du niveau
   de facturation, « Set up billing ». Choisir ou créer un compte Cloud Billing.
2. Prépaiement : 5 $ au minimum ; **25 $ conseillés** (bêta de 20 à 60 étudiants pendant un mois, plus les
   évaluations). Ne pas activer la recharge automatique au début : le prépaiement sert de plafond.
3. Facultatif : régler un plafond de dépense du projet (page « Spend », fonction expérimentale).
4. Vérifier dans AI Studio que la clé affiche le niveau payant (une clé hérite du niveau de son projet : la clé
   actuelle reste valable) et noter les limites par minute affichées.
5. Prévenir la session de développement : elle met `GEMINI_NIVEAU_PAYANT=1` dans `/opt/lexia/.env`, remplace
   l'alias `gemini-flash-lite-latest`, redémarre le service ; la politique de confidentialité passe d'elle-même au
   texte du niveau payant.
6. Utiliser une clé distincte (autre projet) pour les évaluations, comme le demandait D88, afin qu'une mesure ne
   consomme pas le budget de la bêta.
7. Surveiller le solde : **à 0 $, toutes les clés des projets liés s'arrêtent (erreur 402)**, sans retour au
   gratuit ; Lexia bascule alors sur Groq. Recharger avant épuisement ; coût réel à rapprocher du nombre de
   questions avec `eval/cout.py` après quelques jours.
8. Reste à décider à part : l'âge minimum (15 ou 18 ans), que le niveau payant ne règle pas.

## Sources (lues le 24 novembre 2026)

- Tarifs : https://aistudio.google.com/docs/pricing (l'ancienne adresse ai.google.dev/gemini-api/docs/pricing y
  redirige), onglet Standard.
- Modèles : https://aistudio.google.com/docs/models (3.5 Flash-Lite et 3.8 Flash « Stable » ; seul alias cité :
  `gemini-flash-latest`).
- Limites et niveaux : https://aistudio.google.com/docs/rate-limits.
- Conditions : https://aistudio.google.com/docs/terms (données des services gratuits et payants, EEE, âge).
- Facturation : https://aistudio.google.com/docs/billing (activation, 5 $ minimum, arrêt à solde nul, plafonds,
  héritage du niveau par les clés).
- Groq (lu le 23/11, refusé le 24/11) : https://console.groq.com/docs/models et
  https://console.groq.com/docs/rate-limits.
- Taux de change : Banque de France, parités du 18 novembre 2026 (via une recherche).

Les pages ont été lues par un outil qui résume leur contenu : relire dans un navigateur les passages sur l'âge,
l'EEE et les données avant de les citer à un tiers. Ce n'est pas un avis juridique.
