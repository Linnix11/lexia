# Registre des activités de traitement de Lexia

Registre tenu par le responsable du traitement (article 30.1 du RGPD). Mis à jour le 18 novembre 2026 (durées de
conservation, audit du 18 novembre 2026, point E5 ; prénom, D100 ; nom, D102).

L'entreprise compte moins de 250 salariés, mais la dérogation de l'article 30.5 ne couvre pas les traitements
non occasionnels : la gestion des comptes, des formules et des journaux de Lexia l'est. La CNIL recommande
d'inscrire un traitement au registre en cas de doute (https://www.cnil.fr/fr/RGPD-le-registre-des-activites-de-traitement).
Modèle de la CNIL : https://www.cnil.fr/sites/cnil/files/atoms/files/registre_rgpd_basique.pdf

Document de travail, à faire relire par un juriste. Chaque affirmation sur le fonctionnement du service renvoie
au code (chemin entre parenthèses) ; ce qui n'a pas pu être vérifié est marqué « à vérifier ».

## Responsable du traitement

- Éditeur de Lexia : Axion Studio, micro-entreprise (identité, adresse et SIREN : variables `LEGAL_*` de
  `/opt/lexia/.env`, affichées dans les mentions légales).
- Délégué à la protection des données : aucun (non obligatoire : pas de suivi régulier et systématique à grande
  échelle, pas de données sensibles à grande échelle).
- Contact pour l'exercice des droits : adresse `CONTACT_EMAIL`, affichée dans la politique de confidentialité.

## Vue d'ensemble

| N° | Traitement | Base légale | Durée de conservation |
|---|---|---|---|
| T1 | Comptes utilisateurs | Exécution du contrat (CGU) | Jusqu'à la suppression du compte, ou deux ans sans visite (avertissement un mois avant) |
| T2 | Rédaction des réponses par un modèle de langage | Exécution du contrat | Non conservé (mémoire vive 24 h au plus) |
| T3 | Cours déposés | Exécution du contrat | Jusqu'au retrait du cours ou à la suppression du compte |
| T4 | Limites d'usage et formules | Exécution du contrat | Compteurs : 90 jours ; formule : comme le compte |
| T5 | Facturation des formules payantes | Obligation légale (comptabilité) | 10 ans (6 ans si activité libérale, à confirmer) |
| T6 | Journaux techniques et avis | Intérêt légitime | 12 mois |
| T7 | Sécurité du service | Intérêt légitime | 14 jours (serveur web), 48 h (empreinte après suppression) |
| T8 | Sauvegardes | Intérêt légitime (continuité du service) | 14 jours sur le serveur, 60 jours hors serveur |
| T9 | Échanges par e-mail (demandes de formule, exercice des droits) | Mesures précontractuelles, obligation légale | 3 ans après le dernier échange (à appliquer par l'éditeur dans sa boîte) |

## Fiches

### T1. Comptes utilisateurs

- Finalité : créer et gérer le compte, authentifier (mot de passe, double authentification facultative),
  confirmer l'adresse e-mail, réinitialiser le mot de passe, supprimer le compte à la demande.
- Personnes concernées : utilisateurs du site, étudiants en droit pour l'essentiel, 15 ans ou plus (CGU, article 3).
- Données (`api/comptes.py`, table `utilisateurs`) : adresse e-mail ; empreinte scrypt du mot de passe ; formule
  et date de fin ; dates de création, d'acceptation des CGU et de confirmation de l'adresse ; indicateur
  administrateur ; secret de double authentification chiffré (`CLE_SECRETS`) et empreintes des codes de secours ;
  empreintes des jetons de confirmation et de réinitialisation ; date de la dernière visite (`actif_le`, une
  écriture par jour au plus) et date de l'avertissement d'inactivité (`inactif_avis_le`). Sessions : empreinte du
  jeton et date d'expiration.
- Prénom et nom (D100, D102, colonnes `prenom` et `nom`, `Comptes.changer_identite`) : demandés à l'inscription
  depuis le site (refus 422 sans eux, `api/auth.py`), modifiables dans « Mon compte » mais jamais vides une fois
  enregistrés ; 50 caractères au plus chacun (lettres, espaces, traits d'union, apostrophes, points). Comptes créés
  avant D102 : vides, invités à les compléter dans l'espace, jamais bloqués. Finalités : identifier le titulaire du
  compte (pré-remplissage de la déclaration de rétractation) et le saluer par son prénom. Base légale : exécution du
  contrat. Lus à part (`Comptes.identite`, hors de l'objet `Utilisateur` qui circule jusqu'aux routes du modèle) :
  jamais transmis à Google ni à Groq (test `test_prenom_et_nom_jamais_envoyes_au_modele`), jamais dans un e-mail
  (Resend), absents de la liste des comptes de l'administration. Effacés avec la ligne du compte. Minimisation :
  le nom n'est pas indispensable au service (demande de l'éditeur du 2026-11-18) ; à confirmer avec le juriste.
- Dans le navigateur seulement (rien n'est envoyé au serveur, D85) : conversation en cours (30 derniers messages)
  et dernier questionnaire dans `sessionStorage`, sous une empreinte du compte, effacés à la fermeture de l'onglet,
  à la déconnexion et à la suppression du compte ; fiches, cartes à réviser (D104), semestre et dernière matière choisie (D100) dans
  `localStorage`, fiches, cartes et matière effacées à la suppression du compte. Décrit dans la
  politique de confidentialité (« Données collectées »).
- Destinataires : éditeur ; Hostinger (hébergement) ; Resend (envoi des e-mails de confirmation et de
  réinitialisation, `api/courriel.py`) ; Cloudflare (acheminement du trafic).
- Transferts hors UE : Resend et Cloudflare, États-Unis (voir « Sous-traitants »).
- Durée : jusqu'à la suppression du compte (depuis « Mon compte » ou par l'éditeur), ou deux ans sans aucune
  visite : la CNIL juge proportionné ce délai, avec avertissement préalable
  (https://www.cnil.fr/sites/cnil/files/atoms/files/guide_durees_de_conservation.pdf). Mise en œuvre
  (`Comptes.purger_inactifs`, tests `tests/test_rgpd.py`) : e-mail d'avertissement après 23 mois sans visite,
  suppression au plus tôt un mois après cet e-mail et après deux ans d'inactivité ; une visite annule
  l'avertissement ; jamais pour un administrateur ni une formule payante en cours ; une adresse jamais confirmée
  n'est pas prévenue (elle peut appartenir à un tiers). La suppression emporte cours, sessions et compteurs, pas
  les paiements (T5). Tâche lancée une fois par jour par le service lui-même, à la première visite (il a la
  configuration d'envoi des e-mails). Sessions : 30 jours au plus, purgées chaque nuit
  (`deploy/sauvegarder_comptes.sh`).

### T2. Rédaction des réponses, fiches et questionnaires

- Finalité : produire la réponse demandée à partir des sources officielles et, si l'utilisateur le choisit,
  de passages de son cours.
- Données : texte de la question (il peut contenir des données personnelles si l'utilisateur en écrit, ce que la
  politique déconseille) et extraits retrouvés.
- Destinataires : Google (API Gemini) ; Groq en secours si `GROQ_API_KEY` est renseignée (`api/main.py`).
- Transferts hors UE : États-Unis (voir « Sous-traitants »).
- Durée chez l'éditeur : non écrit sur disque ; cache en mémoire vive de 24 h au plus, sans lien avec le compte.
  Le journal des jetons (`logs/modele.jsonl`) ne contient aucun texte.
- Point bloquant avant l'ouverture : les conditions de l'API Gemini n'autorisent que les services payants pour
  une application proposée à des utilisateurs de l'Espace économique européen. Passage au niveau payant :
  `GEMINI_NIVEAU_PAYANT=1` après activation de la facturation (décision D83).

### T3. Cours déposés

- Finalité : permettre à l'utilisateur de réviser avec ses propres cours.
- Données (`api/cours.py`) : texte extrait découpé en passages, numéro de page, vecteurs de recherche, titre,
  matière, nom du fichier, date d'ajout. Le fichier d'origine n'est pas conservé. Scans et photos : lus sur le
  serveur par Tesseract (logiciel libre, aucun service extérieur), image écrite le temps de la lecture dans un
  dossier temporaire effacé aussitôt (D107).
- Destinataires : éditeur, Hostinger ; Google ou Groq pour les seuls passages retenus pour une réponse (T2).
- Durée : jusqu'au retrait du cours ou à la suppression du compte (suppression en cascade) ; copies dans les
  sauvegardes jusqu'à leur effacement (T8).

### T4. Limites d'usage et formules

- Finalité : appliquer les quotas de la formule (questions, questionnaires, cours) et gérer la formule payante.
- Données : compteurs du jour par compte (table `usage`), formule et date de fin, journal des actions des
  administrateurs (`logs/admin.jsonl` : numéro de l'administrateur, numéro du compte, formule, durée).
- Durée : compteurs 90 jours (`USAGE_CONSERVE`, `Comptes.purger_usage`) : ils ne servent qu'au quota du jour et
  aux statistiques des 30 derniers jours ; journal administrateur 12 mois (T6).

### T5. Facturation des formules payantes

- Finalité : encaisser le prix, établir les justificatifs, tenir la comptabilité.
- Données chez l'éditeur (`api/paiement.py`, table `paiements`) : numéro de compte, adresse e-mail, formule,
  nombre de mois, montant, devise, statut, date de la demande d'accès immédiat (droit de rétractation), dates de
  création et de paiement, identifiants Stripe de la session et du paiement. Jamais le numéro de carte : il est
  saisi sur la page de Stripe. Chez Stripe : données de carte, nom, adresse e-mail.
- Base légale : exécution du contrat (paiement), obligation légale (comptabilité).
- Destinataires : éditeur ; Stripe Payments Europe, Limited (Irlande), contractant pour l'Espace économique
  européen, également responsable de traitement pour ses propres obligations (lutte contre la fraude,
  réglementation) ; administration fiscale sur demande.
- Transferts hors UE : Stripe, LLC (États-Unis), certifiée au cadre UE-États-Unis (liste officielle consultée le
  17 novembre 2026).
- Durée : 10 ans en archivage intermédiaire (obligation comptable ; référentiel CNIL « gestion des activités
  commerciales » : https://www.cnil.fr/sites/cnil/files/atoms/files/referentiel_traitements-donnees-caractere-personnel_gestion-activites-commerciales.pdf).
  Fondement vérifié dans LEGI le 18 novembre 2026 : C. com., art. L. 123-22 (documents comptables et pièces
  justificatives, dix ans), qui vise les commerçants. Si l'activité est déclarée en libéral (BNC), seule
  s'applique a priori la durée fiscale de six ans (LPF, art. L. 102 B) : à confirmer par l'éditeur avec son
  expert-comptable ou un avocat, puis ajuster la politique de confidentialité.
  La ligne de paiement est gardée après la suppression du compte (pas de suppression en cascade). Purge au-delà
  de 10 ans : à mettre en place avant 2036.
- État : paiement en ligne par Stripe Checkout (D86), actif dès que `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
  et `URL_PUBLIQUE` sont renseignées ; sinon activation à la main (`python -m api.admin formule`).

### T6. Journaux techniques et avis

- Finalité : suivre la qualité, la fiabilité et le coût du service.
- Données (`api/journal.py`, dossier `logs/`) : `requetes.jsonl` (identifiant de réponse, mode, matière, statut,
  modèle, identifiants des passages fournis et cités, dont `cours:<n°>` pour un cours déposé), `modele.jsonl`
  (modèle, rôle, nombre de jetons), `erreurs.jsonl`, `feedback.jsonl` (avis utile ou non, motif dans une liste),
  `admin.jsonl` (T4). Le texte des questions n'y figure pas.
- Durée : 12 mois, purge automatique par l'API (`RETENTION_JOURS = 365`).

### T7. Sécurité du service

- Finalité : protéger le service contre les abus et les attaques.
- Données : journaux du serveur web nginx (adresse IP, date, page demandée, navigateur) ; adresses IP et réseaux
  IPv6 /64 gardés en mémoire par le limiteur de débit ; empreinte de l'adresse e-mail d'un compte supprimé
  depuis le site (table `suppressions`), qui empêche de se réinscrire dans les 24 h pour remettre son quota à zéro.
- Destinataires : éditeur, Hostinger, Cloudflare.
- Durée : journaux nginx 14 jours (rotation à vérifier sur le serveur : `/etc/logrotate.d/nginx`) ; empreinte
  après suppression : effacée par la tâche de nuit une fois les 24 h écoulées, donc 48 h au plus
  (`Comptes.purger_sessions`, test `tests/test_rgpd.py`). La CNIL recommande de conserver les journaux de
  sécurité entre six mois et un an (https://www.cnil.fr/fr/la-cnil-publie-une-recommandation-relative-aux-mesures-de-journalisation) :
  cette recommandation vise surtout les accès aux données ; 14 jours pour les journaux du serveur web est un
  choix de minimisation à confirmer par l'éditeur.

### T8. Sauvegardes

- Finalité : restaurer le service après une panne ou une erreur.
- Données : copie complète de la base des comptes (T1, T3, T4).
- Lieux et durées : `/opt/lexia/sauvegardes` sur le serveur, 14 copies quotidiennes
  (`deploy/sauvegarder_comptes.sh`) ; copie hors serveur sur l'ordinateur de l'éditeur, 60 copies
  (`deploy/rapatrier_sauvegardes.sh`, dossier en 700, fichiers en 600, disque chiffré FileVault requis : à
  vérifier sur la machine).

### T9. Échanges par e-mail

- Finalité : répondre aux demandes de formule payante, aux réclamations et aux demandes d'exercice des droits.
- Données : adresse e-mail, contenu des messages.
- Destinataire : fournisseur de la boîte `CONTACT_EMAIL` (à renseigner ici avec sa localisation).
- Durée : 3 ans après le dernier échange (repère CNIL pour un prospect), annoncée dans la politique de
  confidentialité. Rien d'automatique : l'éditeur trie sa boîte au moins une fois par an. Les signalements de
  contenu illicite (CGU, article 5 bis) et les échanges sur une mesure de suspension (article 6) suivent la même
  durée. À faire valider : une durée plus longue pour la preuve d'une réponse à une demande d'exercice des droits.

## Sous-traitants (article 28)

Vérification de la certification au cadre de protection des données UE-États-Unis (décision d'adéquation du
10 juillet 2023) sur la liste officielle https://www.dataprivacyframework.gov/list le 17 novembre 2026, comme le
recommande la CNIL (https://www.cnil.fr/fr/adequation-des-etats-unis-les-premieres-questions-reponses).

| Sous-traitant | Rôle | Données | Pays | Garantie de transfert | Contrat (art. 28) |
|---|---|---|---|---|---|
| Hostinger International Ltd | Hébergement du serveur (VPS) | Toutes les données du serveur | Chypre (UE) ; centre de données du VPS à vérifier dans le panneau Hostinger | Sans objet si le centre de données est dans l'UE | Accord de traitement des données de Hostinger : à vérifier et archiver |
| Cloudflare, Inc. | Acheminement et protection du trafic (proxy) | Adresse IP, requêtes et réponses qui transitent | États-Unis | Certifié (actif) | Accord de traitement des données Cloudflare : à vérifier et archiver |
| Google LLC | API Gemini (rédaction des réponses) | Questions, extraits, passages de cours | États-Unis | Certifié (actif) | Conditions de l'API Gemini et avenant sur le traitement des données : le niveau payant est requis (T2) |
| Groq, Inc. | Modèle de secours | Question et quelques extraits | États-Unis | **Non certifié** : clauses contractuelles types à vérifier dans l'accord de traitement de Groq (D58) ; option « Zero Data Retention » activée (D58) | Accord de traitement des données Groq : à lire et archiver |
| Resend | E-mails de confirmation et de réinitialisation | Adresse e-mail, texte du message | États-Unis | Certifié (« actif, re-certification en cours d'examen » le 17 novembre 2026) | Accord de traitement des données Resend : à vérifier et archiver |
| Stripe Payments Europe, Limited | Paiement par carte (Stripe Checkout) | T5 | Irlande (UE) ; Stripe, LLC aux États-Unis | Stripe, LLC certifiée (actif) | Contrat de services et accord de traitement des données Stripe, acceptés à l'ouverture du compte : à archiver |

Non sous-traitants : GitHub (surveillance de `/api/sante`, aucune donnée personnelle des utilisateurs).

## Mesures de sécurité (résumé)

Chiffrement en transit (HTTPS) ; empreintes scrypt des mots de passe ; jetons de session et de lien stockés en
empreinte seulement ; secrets de double authentification chiffrés ; accès direct au serveur limité aux adresses
de Cloudflare ; limites de débit par adresse IP ; sauvegardes en 600 ; deux audits de sécurité
(D80 et précédents dans `docs/decisions.md`).

## Actions restantes

1. Passer l'API Gemini au niveau payant et mettre `GEMINI_NIVEAU_PAYANT=1` (bloquant, D83).
2. Groq : lire l'accord de traitement des données et noter la garantie de transfert (clauses contractuelles
   types) ; à défaut, retirer `GROQ_API_KEY`.
3. Archiver les accords de traitement des données de Hostinger, Cloudflare, Google, Groq et Resend.
4. Vérifier la localisation du VPS Hostinger et la rotation des journaux nginx (14 jours).
5. Appliquer la durée des échanges par e-mail (T9, 3 ans) dans la boîte `CONTACT_EMAIL`.
6. Paiement : archiver le contrat Stripe ; confirmer 10 ans ou 6 ans (T5) ; mettre en place la purge des
   paiements au-delà de cette durée.
