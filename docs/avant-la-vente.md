# Avant de vendre les formules payantes (bloc 2)

État au 17 novembre 2026. Livrés : registre des traitements (`docs/registre-traitements.md`), politique de
confidentialité corrigée (`web/src/site/Legal.tsx`), relevé des marques (`docs/marque-lexia.md`). Ce document
réunit les points qui attendent une action ou un choix de l'éditeur.

## 1. Niveau payant de Gemini (bloquant)

Les conditions additionnelles de l'API Gemini (https://ai.google.dev/gemini-api/terms) n'autorisent que les
services payants pour une application proposée à des utilisateurs de l'Espace économique européen, de la Suisse
ou du Royaume-Uni. Au niveau payant, Google n'utilise pas les questions pour améliorer ses produits et ne les
conserve qu'un temps limité (détection des abus, obligations légales).

À faire par l'éditeur :
1. Google AI Studio, page des projets (ou des clés API) : « Set up billing » sur le projet de la clé de production ;
   choisir ou créer un compte de facturation Cloud ; prépaiement minimum de 5 dollars
   (https://ai.google.dev/gemini-api/docs/billing). La documentation dit que les clés héritent du niveau du
   projet : la clé actuelle devrait rester valable, à vérifier dans la colonne « Plan » (« Paid »).
2. Prévenir la session de développement : elle mettra `GEMINI_NIVEAU_PAYANT=1` dans `/opt/lexia/.env` et publiera.
   La politique de confidentialité bascule alors d'elle-même sur le texte du niveau payant.

Modèles : rester sur `gemini-3.5-flash-lite`. Le « modèle complet » `gemini-3.5-flash` prévu par D29 n'est plus
sur la grille tarifaire (vérifié le 17 novembre 2026, https://ai.google.dev/gemini-api/docs/pricing).

### Coût par question (estimation avant activation)

Prix du niveau payant, dollars par million de jetons (entrée / sortie, réflexion comprise) : gemini-3.5-flash-lite
0,30 / 2,50 ; gemini-3.8-flash (dernier secours) 0,75 / 3,75 jusqu'au 31 décembre 2026, puis 1,50 / 7,50.

Mesure sur `logs/modele.jsonl` du Mac (20 appels, du 13 au 17 novembre 2026 : échantillon d'essais, pas de
trafic réel ; les questionnaires sont comptés avec les réponses, rôle « generation ») :

| Appel | Jetons d'entrée (moyenne) | Jetons de sortie (moyenne) | Coût, flash-lite | Coût, 3.8-flash 2026 | Coût, 3.8-flash 2027 |
|---|---|---|---|---|---|
| Réponse (12 appels) | 2 036 | 538 | 0,00196 $ | 0,00355 $ | 0,00709 $ |
| Reformulation (8 appels) | 136 | 60 | 0,00019 $ | 0,00033 $ | 0,00066 $ |
| **Question complète** | | | **0,0021 $** | 0,0039 $ | 0,0077 $ |

Pire appel relevé : 4 045 jetons d'entrée et 1 558 de sortie, soit 0,0051 $ avec flash-lite.

### Comparaison avec le prix des formules (`api/plans.py`)

Calcul sur 30 jours, à 0,0021 $ la question, et à 1 € = 1 $ (si l'euro vaut plus d'un dollar, les seuils réels
sont plus hauts). Recette nette après frais de paiement Stripe Checkout (option A ci-dessous).

| Formule | Prix | Recette nette | Quota par jour | Coût si le quota est épuisé chaque jour | Seuil de rentabilité |
|---|---|---|---|---|---|
| Gratuit | 0 € | 0 € | 10 | 0,64 $ par mois | |
| Étudiant | 4,99 € | 4,67 € | 100 | 6,44 $ par mois | 2 170 questions par mois, environ 72 par jour |
| Intensif | 9,99 € | 9,59 € | 300 | 19,32 $ par mois | 4 460 questions par mois, environ 149 par jour |

Lecture : les deux formules payantes perdent de l'argent sur un abonné qui épuise son quota tous les jours, et en
gagnent tant que l'usage moyen reste sous 72 (Étudiant) ou 149 (Intensif) questions par jour. Un passage
fréquent sur gemini-3.8-flash (pannes de flash-lite) doublerait le coût en 2026 et le quadruplerait en 2027.

Mesure réelle, une fois le niveau payant actif et quelques jours de trafic : copier `/opt/lexia/logs/modele.jsonl`
et `requetes.jsonl` du serveur sur le Mac (la session n'a pas reçu l'autorisation de les lire), puis :

    python eval/cout.py <dossier> --prix gemini-3.5-flash-lite=0.30,2.50 --prix gemini-3.8-flash=0.75,3.75

Le coût facturé par Google se lit aussi dans la console Cloud (Facturation), à rapprocher du nombre de questions.

## 2. Téléphone de l'hébergeur (variable `LEGAL_HEBERGEUR_TELEPHONE`)

Aucune page officielle de Hostinger consultée ne publie de numéro de téléphone pour HOSTINGER INTERNATIONAL
LIMITED : conditions d'utilisation (https://www.hostinger.com/tos, qui confirment la dénomination et l'adresse de
Larnaca et donnent compliance@hostinger.com), politique de confidentialité, pages « Contact » et « About ».
Un numéro lituanien figure dans les enregistrements RIPE (registre des adresses IP), qui ne sont pas un site de
Hostinger : il n'a pas été retenu.

À faire par l'éditeur : demander par écrit au support Hostinger (ou à compliance@hostinger.com) le numéro de
téléphone à faire figurer dans des mentions légales françaises, puis le donner à renseigner dans
`/opt/lexia/.env`. D'ici là, la page affiche « à compléter ».

## 3. Médiateur de la consommation (variable `LEGAL_MEDIATEUR`)

Liste officielle : https://www.economie.gouv.fr/mediation-conso/vous-etes-un-professionnel/choisir-un-mediateur-de-la-consommation/mediateurs-references
(jeu de données de la CECMC mis à jour le 26 octobre 2026). Elle ne connaît pas de secteur « logiciel » : les
médiateurs ci-dessous y sont référencés à la fois pour « Vente en ligne, vente à distance » et pour
« Enseignement à distance ». Tarifs relevés sur les sites des médiateurs le 17 novembre 2026, à reconfirmer
avant d'adhérer.

| Médiateur | Site | Tarif publié pour une petite entreprise |
|---|---|---|
| Société de la Médiation Professionnelle (SMP) | https://www.mediateur-consommation-smp.fr/ | Chiffre d'affaires sous 60 000 € : 25 € HT pour 3 ans, sans droit d'entrée ; médiation 150 € HT (simple) ou 350 € HT (complexe), facturée seulement si elle a lieu (https://www.mediateur-consommation-smp.fr/grille-tarifaire/) |
| Médiation de la Consommation & Patrimoine (MCP) | https://www.mcpmediation.org/ | 40 € HT par an sous 50 000 € de chiffre d'affaires, engagement de 3 ans ; le tarif le plus bas (25 €) ne vise pas la vente en ligne ; médiation sur devis de 0 à 300 € HT (https://mcpmediation.org/nos-tarifs/) |
| NotreAccord | https://www.mediation-consommation.notreaccord.com/ | Non publié (adhésion : https://adhesion.notreaccord.com/pro-general) |
| Avenir Conso (anciennement AME Conso) | https://www.avenir-conso.com/ | Non publié |
| ANM Consommation | https://www.anm-conso.com/ | Non publié |
| Médiation Solution | https://sasmediationsolution-conso.fr/ | Non publié |

À faire par l'éditeur : choisir, adhérer (convention signée), puis donner le nom, l'adresse postale et le site du
médiateur à renseigner dans `LEGAL_MEDIATEUR`. Les CGU (article 8) l'affichent alors.

## 4. Paiement en ligne : Stripe Checkout (choix de l'éditeur, 17 novembre 2026, D86)

Intégré dans le code, inactif tant que les clés Stripe ne sont pas renseignées (le site garde alors la demande
par e-mail). Fonctionnement : sur la page Tarifs, l'abonné choisit la durée (1, 2, 3, 6 ou 12 mois), coche la
demande d'accès immédiat (droit de rétractation, article L. 221-25), puis paie sur la page de Stripe ; le webhook
signé active la formule (prolongée si c'est la même formule encore en cours). Changer de formule payante en
cours de période est refusé (à l'échéance seulement). Un paiement reçu alors qu'une autre formule est en cours
(deux onglets, formule donnée sans fin) n'active rien : il passe « à rembourser » (audit du 18 novembre 2026, lot A).
La page de paiement expire après 30 minutes ; en ouvrir une nouvelle ferme la précédente. Après paiement, l'abonné
reçoit par e-mail la confirmation du contrat (formule, durée, prix, version des CGU, accès immédiat, formulaire de
rétractation). Il peut se rétracter en ligne depuis Mon compte pendant 14 jours (« Renoncer au contrat ici », nom et
prénom, contrat visé, « Confirmer la rétractation ») : la formule est retirée et un accusé de réception daté lui est
envoyé.

À faire par l'éditeur pour l'activer :
1. Ouvrir le compte Stripe (identité, IBAN, description du service) ; dans les réglages, activer les reçus par
   e-mail pour les paiements réussis.
2. Tableau de bord Stripe, Développeurs : créer un endpoint de webhook
   `https://lexia-axionstudio.cloud/api/paiement/webhook` avec les événements `checkout.session.completed`,
   `checkout.session.async_payment_succeeded`, `checkout.session.async_payment_failed`,
   `checkout.session.expired`, `charge.refunded` et `charge.dispute.created`, puis noter son secret (`whsec_...`).
   Sans les quatre derniers, les remboursements et contestations ne retirent pas la formule.
3. Donner à la session de développement, sans les écrire dans une conversation, l'emplacement où les valeurs
   ont été placées, ou les mettre soi-même dans `/opt/lexia/.env` : `STRIPE_SECRET_KEY` et
   `STRIPE_WEBHOOK_SECRET` (voir `deploy/env.production.exemple`), puis redémarrer le service.
4. Essai de bout en bout en mode test d'abord (clés `sk_test_`, carte de test de Stripe), puis en réel avec un
   petit paiement remboursé. Vérifier aussi que Cloudflare laisse passer les appels de Stripe vers le webhook
   (envoi d'un événement de test depuis le tableau de bord).

Paiements à traiter : la vue d'ensemble de l'administration liste les paiements « à rembourser » (rétractation,
autre formule en cours, compte supprimé), « écartés » (montant inattendu), « remboursés en partie » et « en
litige », avec l'identifiant `pi_...` à chercher dans Stripe. Rétractation : la formule est déjà retirée ;
rembourser depuis le tableau de bord Stripe le montant payé moins la part de la période écoulée (accès immédiat
demandé). Le remboursement fait passer le paiement à « remboursé ». Un remboursement complet fait hors
rétractation, ou une contestation bancaire, retire aussi la formule.

Comparatif ayant servi au choix. Frais relevés sur les grilles officielles le 17 novembre 2026, cartes de
l'Espace économique européen.

| | A. Stripe Checkout (paiement unique) | B. Mollie | C. Paddle (vendeur officiel, « merchant of record ») |
|---|---|---|---|
| Frais par paiement | 1,5 % + 0,25 € (cartes premium EEE 2,8 % + 0,25 €) | 1,80 % + 0,25 € ; cartes du réseau CB 1,20 % + 0,25 € | 5 % + 0,50 $ ; tarif sur mesure sous 10 $ |
| Sur 4,99 € | 0,32 € (6,5 %) | 0,34 € (CB : 0,31 €) | environ 0,75 € (15 %) |
| Sur 9,99 € | 0,40 € (4,0 %) | 0,43 € (CB : 0,37 €) | environ 1,00 € (10 %) |
| Abonnement récurrent | Stripe Billing, + 0,7 % | Possible (non vérifié) | Oui |
| Frais fixes | Aucun | Aucun ; versements : 5 gratuits par mois, puis 0,25 € | Aucun |
| Litige (rejet de paiement) | 20 € | Non publié | Inclus, non chiffré |
| Activation automatique | Webhook `checkout.session.completed` | Webhook puis lecture du statut `paid` | Webhook `transaction.completed` |
| Factures | Reçus automatiques ; facture PDF en option (payante), mention « TVA non applicable, art. 293 B du CGI » à saisir | Non vérifié | Paddle facture à sa place |
| Ouverture du compte | Informations sur l'entreprise et le service, compte bancaire, vérification d'identité (liste exacte pour un entrepreneur individuel français non publiée) | Coordonnées de l'entreprise et du représentant, site, IBAN, pièce d'identité (liste française non confirmée) | Revue du site et du produit, vérification d'identité |

Sources : https://stripe.com/fr/pricing, https://docs.stripe.com/checkout/fulfillment, https://www.mollie.com/fr/pricing,
https://docs.mollie.com/docs/webhooks, https://www.paddle.com/pricing, https://developer.paddle.com/webhooks/overview.
Lemon Squeezy n'accepte plus d'inscriptions (fermeture annoncée au 31 mars 2027) : écarté.

Lecture : A et B coûtent à peu près pareil ; C coûte deux à trois fois plus, et son atout principal (gérer la TVA
européenne) ne sert pas à une micro-entreprise en franchise de TVA. Le paiement unique pour N mois correspond aux
CGU actuelles (pas de reconduction) et évite le supplément de Stripe Billing.
