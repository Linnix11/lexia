# Séquence d'accueil des inscrits et lettre des partiels

Version du 23 novembre 2026. Textes prêts ; **aucun envoi n'existe encore dans le code** (D110 : « aucun envoi
n'existe encore, chaque futur envoi devra porter un lien de désinscription »). Gabarit HTML commun :
`modele-email.html`.

## Règle d'envoi (D110) : seulement aux comptes qui ont consenti

- **Destinataires** : uniquement les comptes dont la case « J'accepte de recevoir les e-mails d'information de
  Lexia » a été cochée, c'est-à-dire `infos_email_le` renseigné, et dont l'adresse est confirmée. Jamais les autres,
  même pour l'e-mail de bienvenue : ces e-mails présentent le service et ses fonctions, ce ne sont pas des e-mails de
  service (confirmation d'adresse, sécurité, contrat), qui restent envoyés à tous comme aujourd'hui.
- **Pourquoi** : un compte gratuit n'est pas un client au sens de l'exception des « produits ou services
  analogues » (CNIL, rappelée dans `docs/marketing/plan.md`, partie 7.4) ; il faut donc le consentement préalable
  (Code des postes et des communications électroniques, article L. 34-5). Un inscrit de 15 à 17 ans peut consentir
  seul (loi n° 78-17, article 45).
- **Retrait** : lien de désinscription en un clic dans chaque e-mail, qui fait la même chose que la case de Mon
  compte (`POST /auth/infos-email`). Le retrait arrête la séquence aussitôt, y compris les e-mails déjà
  programmés.
- **Contenu** : aucun profilage ni ciblage fondé sur l'âge (recommandations de la CNIL sur les mineurs). Les
  déclencheurs ci-dessous ne lisent que la date d'inscription, le consentement et, pour l'e-mail 2, le fait qu'au
  moins une question a été posée (compteur déjà tenu pour les quotas).
- **Quota d'envoi** : le quota Resend gratuit (100 e-mails par jour) est déjà partagé entre les e-mails de compte,
  les paiements et les alertes (D105). Une séquence le dépasserait vite : à prévoir avec la session de
  développement (file d'attente, plafond par jour, ou formule Resend payante quand le budget le permettra).
- **Registre** : ajouter ce traitement au registre (`docs/registre-traitements.md`, T10 créé par D110), avec la
  durée de conservation du consentement.

## Déclencheurs

| E-mail | Quand | Condition en plus du consentement |
|---|---|---|
| 1. Bienvenue | Juste après la confirmation de l'adresse (ou au moment du consentement s'il est donné plus tard dans Mon compte) | Aucune |
| 2. Première question | J+2 après l'inscription, à 18 h, heure de Paris | Aucune question posée depuis l'inscription ; sinon, ne pas envoyer |
| 3. Questionnaires et cartes | J+6, à 18 h | Aucune |
| 4. Avant les partiels | Une fois par semestre : 7 jours avant la période type des partiels (1er décembre et 20 avril proposés, à caler sur les calendriers des facultés) | Inscrit depuis au moins 7 jours |
| Lettre des partiels | Une fois en décembre et une fois en mai | Aucune |

Expéditeur : « Lexia » avec l'adresse d'envoi actuelle du site. Réponse : l'adresse de contact des mentions
légales. Vouvoiement, pas de point d'exclamation, pas de superlatif (ton de la marque).

Pied commun à tous les e-mails (obligatoire) :

> Vous recevez cet e-mail parce que vous avez accepté les e-mails d'information de Lexia le {date_consentement}.
> Se désinscrire en un clic : {lien_desinscription} (ou dans Mon compte).
> Lexia, outil d'étude du droit français, pas un avis juridique. Éditeur : Arthur Champagne-Forterre, entrepreneur
> individuel, nom commercial Axion Studio, 5 allée des Pommiers, 95680 Montlignon.

Variables : `{prenom}` (« Bonjour, {prenom}. » ; sans prénom : « Bonjour. »), `{lien_app}`
(https://lexia-axionstudio.cloud/app), `{lien_compte}` (…/compte), `{date_consentement}`, `{lien_desinscription}`.
Le prénom n'est aujourd'hui utilisé ni dans les e-mails ni par l'administration (D100) : l'utiliser ici demande de
mettre à jour la politique de confidentialité ; sinon, garder « Bonjour. ».

---

## E-mail 1. Bienvenue

**Objet** : Bienvenue sur Lexia : trois façons de commencer
**Pré-en-tête** : Une question de cours, un cas pratique ou un cours déposé.

Bonjour, {prenom}.

Votre compte Lexia est prêt. Lexia répond à vos questions de droit à partir des textes officiels : chaque réponse
cite ses sources, avec le texte à un clic, et une affirmation sans source est retirée.

Trois façons de commencer :

1. **Posez une question de cours**, par exemple « Quelles sont les conditions de la responsabilité pour faute ? ».
   Ouvrez la source citée : vous verrez l'article et sa date de vigueur.
2. **Essayez un mode de méthode** : Cas pratique, Commentaire d'arrêt ou Dissertation. La réponse suit les
   rubriques attendues en licence.
3. **Déposez un cours** (PDF, Word, PowerPoint, OpenDocument, et même un scan ou une photo) et interrogez-le avec
   les textes officiels. Un ancien numéro du Code civil y est signalé avec l'article actuel.

Pensez à choisir votre semestre : le niveau d'explication s'y adapte.

[Ouvrir mon espace] → {lien_app}

Avec le compte gratuit : 10 questions et 2 questionnaires par jour, 3 cours déposés.

Lexia est un outil d'étude : vérifiez toujours les sources citées, et suivez la méthode de votre chargé de TD.

L'équipe de Lexia

---

## E-mail 2. Votre première question

**Objet** : Une question de cours, une réponse sourcée
**Pré-en-tête** : Trois exemples à essayer en une minute.

Bonjour, {prenom}.

Vous n'avez pas encore posé de question à Lexia. Voici trois exemples à copier, pour voir comment les sources
s'affichent :

- « Article 1382 : faute et dommage » : Lexia reconnaît l'ancien numéro et vous renvoie à l'article 1240 actuel.
- « Le silence vaut-il acceptation ? » : une question classique de droit des contrats, en mode Expliquer.
- « Arrêt Blanco » : la décision du Tribunal des conflits du 8 février 1873 est reconnue par son nom.

Sous chaque réponse, cliquez sur une source : le texte officiel s'ouvre, avec un bouton pour vérifier la version
en vigueur.

[Poser ma première question] → {lien_app}

Si Lexia ne trouve aucune source pour répondre, il le dit au lieu d'inventer.

L'équipe de Lexia

---

## E-mail 3. Réviser avec les questionnaires et les cartes

**Objet** : Réviser en 2 minutes : questionnaires corrigés et cartes à retourner
**Pré-en-tête** : La correction cite les articles ; les cartes reviennent au bon moment.

Bonjour, {prenom}.

Pour réviser, Lexia propose trois outils :

- **Les questionnaires** : choisissez la matière, le thème et le format (QCM, vrai ou faux, questions ouvertes), de
  1 à 15 questions. La correction cite les sources : vous savez pourquoi une réponse est juste ou fausse.
- **Les cartes à retourner** : après un questionnaire corrigé, ajoutez les questions à vos cartes. Une carte sue
  revient après 1, 3, 7, 14 puis 30 jours ; une carte ratée revient le lendemain. Vos fiches peuvent aussi devenir
  des cartes.
- **Les résumés à écouter** : une réponse, une fiche ou un cours résumé en 2 à 5 minutes, lu par la voix de votre
  appareil.

À savoir : vos fiches et vos cartes sont gardées dans ce navigateur, sur cet appareil ; elles ne passent pas encore
d'un appareil à l'autre.

[Lancer un questionnaire] → {lien_app}

Avec le compte gratuit : 2 questionnaires par jour.

L'équipe de Lexia

---

## E-mail 4. Avant les partiels

**Objet** : Partiels dans une semaine : une méthode en 4 temps
**Pré-en-tête** : Vérifier, s'entraîner, réviser les cartes, relire les sources.

Bonjour, {prenom}.

Les partiels approchent. Une façon d'utiliser Lexia sur la dernière semaine :

1. **Vérifier vos articles** : votre polycopié cite peut-être d'anciens numéros (1382, 1134, 1147). Déposez-le ou
   posez la question : Lexia indique l'article actuel.
2. **S'entraîner sur un cas pratique** en mode Cas pratique : faits et qualification, problème de droit, majeure,
   mineure, conclusion.
3. **Réviser vos cartes** chaque jour : celles qui sont dues apparaissent dans « Pour reprendre ».
4. **Relire les sources** : avant de citer un article dans une copie, un clic vérifie qu'il est en vigueur.

[Ouvrir mon espace] → {lien_app}

Bon courage pour vos partiels.

L'équipe de Lexia

---

## Lettre des partiels (décembre et mai)

**Objet** : Lettre de Lexia : réviser les partiels avec les textes en vigueur
**Pré-en-tête** : Une méthode, un piège à éviter, ce qui change sur Lexia.

Bonjour, {prenom}.

**La méthode du mois : la fiche d'arrêt en 5 cases.**
Les faits ; la procédure ; les prétentions des parties ; le problème de droit ; la solution et son fondement. La
fiche d'arrêt ouvre le commentaire : le mode Commentaire d'arrêt de Lexia vous aide à la faire, avec les textes
cités.

**Le piège du mois : citer un ancien numéro.**
Depuis le 1er octobre 2016, la responsabilité pour faute est à l'article 1240 du Code civil, plus à l'article 1382.
L'article 1382 actuel parle des présomptions laissées à l'appréciation du juge : citer le mauvais numéro, c'est
citer une autre règle.

**Ce qui change sur Lexia.**
{Une à trois nouveautés réellement en ligne le jour de l'envoi, chacune vérifiée sur le site. Ne rien annoncer
avec une date tant que ce n'est pas publié.}

**Ce que Lexia ne fait pas encore.**
La jurisprudence de la Cour de cassation et du Conseil constitutionnel a un retard affiché sous chaque source
(dates à relire sur le site le jour de l'envoi) ; les réponses n'ont pas encore été notées par un enseignant.

[Réviser avec Lexia] → {lien_app}

Bon courage pour vos partiels.

L'équipe de Lexia

---

## Avant d'activer

- [ ] Développer l'envoi : file, déclencheurs, désinscription en un clic, journal des envois (session de
      développement).
- [ ] Mettre à jour la politique de confidentialité (finalité « e-mails d'information », durée, prénom s'il est
      utilisé) et le registre.
- [ ] Relire chaque e-mail sur le site le jour de l'activation : quotas (`/api/formules`), fonctions en ligne.
- [ ] Tester l'affichage du gabarit dans deux messageries (Gmail, Outlook) et sur téléphone.
