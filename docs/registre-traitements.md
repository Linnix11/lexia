# Registre des activités de traitement de Lexia

Registre tenu par le responsable du traitement (article 30.1 du RGPD). Mis à jour le 23 novembre 2026 (résumés
vocaux, D106 ; cartes mentales, D112 ; décisions de justice, D113 ; D115 ; bêta fermée, D121, fiche T12). Versions précédentes : 18 novembre 2026
(durées de conservation, audit du 18 novembre 2026, point E5 ; prénom, D100 ; nom, D102).

Texte publié de la politique de confidentialité : une seule source, la page Confidentialité de
`web/src/site/Legal.tsx`. Sa copie texte, version par version, est `docs/confidentialite/<version>.json`
(`npm run confidentialite` dans `web/`) ; un test échoue si la page change sans que la copie soit refaite, et un
autre si une table de la base des comptes n'est pas citée ici (`tests/test_rgpd.py`).

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
| T2 | Rédaction des réponses, résumés vocaux et cartes mentales par un modèle de langage | Exécution du contrat | Réponses : mémoire vive 24 h au plus ; questionnaires en cours : base des comptes, 3 h ; résumés et cartes : non conservés |
| T3 | Cours déposés | Exécution du contrat | Jusqu'au retrait du cours ou à la suppression du compte |
| T4 | Limites d'usage et formules | Exécution du contrat | Compteurs de questions et questionnaires : 90 jours ; de résumés vocaux et de cartes mentales : un mois ; formule : comme le compte |
| T5 | Facturation des formules payantes | Obligation légale (comptabilité) | 10 ans (6 ans si activité libérale, à confirmer) |
| T6 | Journaux techniques et avis | Intérêt légitime | 12 mois |
| T7 | Sécurité du service | Intérêt légitime | 14 jours (serveur web), 48 h (empreinte après suppression) |
| T8 | Sauvegardes | Intérêt légitime (continuité du service) | 14 jours sur le serveur, 60 jours hors serveur |
| T9 | Échanges par e-mail (demandes de formule, exercice des droits) | Mesures précontractuelles, obligation légale | 3 ans après le dernier échange (à appliquer par l'éditeur dans sa boîte) |
| T10 | E-mails d'information et origine des inscriptions | Consentement (e-mails) ; intérêt légitime (origine, réponse facultative) | Comme le compte ; consentement effacé dès son retrait |
| T11 | Réutilisation de décisions de justice publiées | Intérêt légitime | Tant que la source publie la décision ; retrait à la mise à jour suivante |
| T12 | Bêta fermée : code d'accès, questionnaire de retour, mesure d'utilisation | Exécution du contrat (code) ; intérêt légitime (avis facultatif, mesure sans identifiant) | Code : comme le compte ; avis : 12 mois ; mesure : 12 mois |

## Fiches

### T1. Comptes utilisateurs

- Finalité : créer et gérer le compte, authentifier (mot de passe, double authentification facultative),
  confirmer l'adresse e-mail, réinitialiser le mot de passe, supprimer le compte à la demande.
- Personnes concernées : utilisateurs du site, étudiants en droit pour l'essentiel, 15 ans ou plus (CGU, article 3).
- Données (`api/comptes.py`, table `utilisateurs`) : adresse e-mail ; empreinte scrypt du mot de passe ; formule
  et date de fin ; dates de création, d'acceptation des CGU et de confirmation de l'adresse ; indicateur
  administrateur ; secret de double authentification chiffré (`CLE_SECRETS`) et empreintes des codes de secours ;
  empreintes des jetons de confirmation et de réinitialisation ; date de la dernière visite (`actif_le`, une
  écriture par jour au plus) et date de l'avertissement d'inactivité (`inactif_avis_le`) ; numéro du code d'accès
  de la bêta utilisé à l'inscription (`code_beta`, T12). Sessions (table `sessions`) : empreinte du jeton et date
  d'expiration.
- Preuve de l'acceptation à l'inscription (D110, note de l'éditeur du 2026-11-20, point 1) : texte de la case d'âge
  cochée (`age_atteste`, « 15 ans ou plus »), version des CGU acceptée (`cgu_version`, même valeur que
  `VERSION_CGU`), date de l'acceptation (`cgu_le`). Vides pour les comptes créés avant D110 et pour un client qui
  ne les envoie pas (app iOS antérieure). Base légale : exécution du contrat (preuve de l'acceptation des
  conditions et de l'âge déclaré).
- Prénom et nom (D100, D102, colonnes `prenom` et `nom`, `Comptes.changer_identite`) : demandés à l'inscription
  depuis le site (refus 422 sans eux, `api/auth.py`), modifiables dans « Mon compte » mais jamais vides une fois
  enregistrés ; 50 caractères au plus chacun (lettres, espaces, traits d'union, apostrophes, points). Comptes créés
  avant D102 : vides, invités à les compléter dans l'espace, jamais bloqués. Finalités : identifier le titulaire du
  compte (pré-remplissage de la déclaration de rétractation) et le saluer par son prénom. Base légale : exécution du
  contrat. Lus à part (`Comptes.identite`, hors de l'objet `Utilisateur` qui circule jusqu'aux routes du modèle) :
  jamais transmis à Google ni à Groq (test `test_prenom_et_nom_jamais_envoyes_au_modele`), jamais dans un e-mail
  (Resend), absents de la liste des comptes de l'administration. Seule exception : le nom et le prénom saisis dans
  une déclaration de rétractation (pré-remplis, modifiables) figurent dans l'accusé de réception (Resend) et restent
  dix ans dans la table des paiements (T5). Effacés avec la ligne du compte. Minimisation :
  le nom n'est pas indispensable au service (demande de l'éditeur du 2026-11-18) ; à confirmer avec le juriste.
- Dans le navigateur seulement (rien n'est envoyé au serveur, D85) : conversation en cours (30 derniers messages)
  et dernier questionnaire dans `sessionStorage`, sous une empreinte du compte, effacés à la fermeture de l'onglet,
  à la déconnexion et à la suppression du compte ; fiches, cartes à réviser (D104), semestre et dernière matière choisie (D100) dans
  `localStorage`, fiches, cartes et matière effacées à la suppression du compte. Décrit dans la
  politique de confidentialité (« Données collectées »).
- Destinataires : éditeur ; Hostinger (hébergement) ; Resend (envoi des e-mails, `api/courriel.py` : confirmation
  d'adresse, réinitialisation, alerte de code de double authentification incorrect (`envoyer_alerte_code_faux`),
  avertissement d'inactivité, confirmation du contrat, paiement qui n'active aucune formule
  (`envoyer_paiement_non_active`), accusé de rétractation ; audit du 2026-11-23, E6) ; Cloudflare (acheminement du
  trafic).
- Export : `GET /compte/export` (bouton « Télécharger mes données » de Mon compte, `api/export.py`) : compte sans
  secret, état de la double authentification et nombre de codes de secours restants, sessions ouvertes (date
  d'expiration), compteurs, cours déposés avec leur texte, paiements (RGPD art. 15 et 20 ; audit du 2026-11-19,
  JUR-11, et du 2026-11-23, E12). Le questionnaire en cours n'est lié à aucun compte (`api/quiz.py`) : l'export
  le dit au lieu de le contenir.
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
- Durée chez l'éditeur : réponses non écrites sur disque, cache en mémoire vive de 24 h au plus, sans lien avec le
  compte. Questionnaires en cours (thème, questions, extraits, correction, numéro du compte) : recopiés dans la base
  des comptes (table `questionnaires`, D5) pour survivre à un redémarrage, 3 heures au plus ; purgés chaque jour et
  avec le compte (`Comptes.purger_questionnaires`, `Comptes.supprimer`) ; une sauvegarde de nuit peut en contenir
  jusqu'à son effacement (audit du 2026-11-19, JUR-12).
  Le journal des jetons (`logs/modele.jsonl`) ne contient aucun texte.
- Résumés vocaux (D106, `api/resumes_vocaux.py`) et cartes mentales (D112, `api/cartes_mentales.py`) : le
  document choisi (texte d'une réponse ou d'une fiche envoyé par le navigateur, avec ses extraits relus par le
  serveur ; cours déposé, 24 000 premiers caractères, pour son seul propriétaire ; cours récupéré ; pour la carte
  d'une matière, la notion saisie) est transmis au modèle comme une question, mêmes destinataires. Le texte du
  résumé et la carte sont renvoyés au navigateur sans être écrits sur le serveur ; le journal des questions ne
  garde que le type de document, le modèle, des nombres (mots, branches, liens) et le contrôle, jamais le texte.
  Compteurs du jour : T4.
- Lecture à voix haute du résumé : synthèse vocale du navigateur (Web Speech API), aucun son produit ni reçu par
  le serveur. Seules les voix installées sur l'appareil sont proposées quand il y en a (`web/src/lib/voix.ts`,
  recette du 2026-11-20, D-11) ; sans voix française locale, une voix en ligne du navigateur (voix Google de
  Chrome, par exemple) peut lire le texte : il part alors chez l'éditeur du navigateur, qui n'est pas un
  sous-traitant de Lexia (choix et conditions du navigateur de l'utilisateur), et le site le signale sous le
  résumé. Décrit dans la politique de confidentialité (« Lecture à voix haute des résumés »).
- Point bloquant avant l'ouverture : les conditions de l'API Gemini n'autorisent que les services payants pour
  une application proposée à des utilisateurs de l'Espace économique européen. Passage au niveau payant :
  `GEMINI_NIVEAU_PAYANT=1` après activation de la facturation (décision D83).

### T3. Cours déposés

- Finalité : permettre à l'utilisateur de réviser avec ses propres cours.
- Données (`api/cours.py`, tables `cours` et `cours_passages`, index plein texte `cours_fts` qui en est la
  copie) : texte extrait découpé en passages, numéro de page, vecteurs de recherche, titre, matière, nom du
  fichier, date d'ajout. Le fichier d'origine n'est pas conservé. Scans et photos : lus sur le
  serveur par Tesseract (logiciel libre, aucun service extérieur), image écrite le temps de la lecture dans un
  dossier temporaire effacé aussitôt (D107).
- Destinataires : éditeur, Hostinger ; Google ou Groq pour les seuls passages retenus pour une réponse (T2).
- Durée : jusqu'au retrait du cours ou à la suppression du compte (suppression en cascade) ; copies dans les
  sauvegardes jusqu'à leur effacement (T8).

### T4. Limites d'usage et formules

- Finalité : appliquer les quotas de la formule (questions, questionnaires, cours) et gérer la formule payante.
- Données : compteurs du jour par compte (table `usage`), formule et date de fin, journal des actions des
  administrateurs (`logs/admin.jsonl` : numéro de l'administrateur, numéro du compte, formule, durée).
- Compteurs des résumés vocaux (table `resumes_vocaux`, D106) et des cartes mentales (table `cartes_mentales`,
  D112) : numéro du compte, jour, nombre ; 5 par jour par défaut (`RESUMES_VOCAUX_PAR_JOUR`,
  `CARTES_MENTALES_PAR_JOUR`), un remboursé si le modèle n'a pas répondu. Aucun texte.
- Durée : compteurs de questions et questionnaires 90 jours (`USAGE_CONSERVE`, `Comptes.purger_usage`) : ils ne
  servent qu'au quota du jour et aux statistiques des 30 derniers jours ; compteurs de résumés vocaux et de
  cartes mentales un mois (`CONSERVATION_JOURS = 31` de `api/resumes_vocaux.py`, lignes plus anciennes effacées à
  chaque nouvelle demande, effacées avec le compte par la clé étrangère) ; tous inclus dans l'export des données
  (`api/export.py`) ; journal administrateur 12 mois (T6). Les statistiques de l'administration excluent les
  comptes des administrateurs (recette du 2026-11-20, D-7).

### T5. Facturation des formules payantes

- Finalité : encaisser le prix, établir les justificatifs, tenir la comptabilité.
- Données chez l'éditeur (`api/paiement.py`, table `paiements`) : numéro de compte, adresse e-mail, formule,
  nombre de mois, montant, devise, statut, date de la demande d'accès immédiat (droit de rétractation), dates de
  création et de paiement, identifiants Stripe de la session et du paiement ; en cas de rétractation en ligne, nom
  et prénom déclarés, date et heure, date d'envoi de l'accusé (et de la confirmation du contrat). Jamais le numéro de carte : il est
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
  `admin.jsonl` (T4), `usage.jsonl` (mesure d'utilisation de la bêta, T12). Le texte des questions n'y figure pas.
- Durée : 12 mois, purge automatique par l'API (`RETENTION_JOURS = 365`).

### T12. Bêta fermée : code d'accès, questionnaire de retour, mesure d'utilisation (D121)

- Finalités : réserver l'inscription aux 10 à 20 étudiants invités avant les partiels de décembre 2026 ; recueillir
  leur avis pour corriger Lexia avant l'ouverture ; mesurer l'usage réel (fonctions utilisées, durées, erreurs).
- Personnes concernées : étudiants invités à la bêta (comptes créés avec un code), et pour la mesure, tout
  utilisateur du service (sans identifiant).
- Code d'accès (`api/beta.py`, table `codes_beta`) : empreinte sha256 du code (le code n'est affiché qu'une fois, à
  sa création dans l'administration), nom du groupe choisi par l'éditeur, nombre de places et d'inscriptions,
  état, date de création. Le compte garde le numéro du code (`utilisateurs.code_beta`, T1). Exigé seulement avec
  `BETA_FERMEE=1` dans le `.env`. Base légale : exécution du contrat (conditions d'accès au service pendant la
  bêta). Durée : comme le compte ; le code lui-même jusqu'à sa désactivation, sans donnée personnelle.
- Questionnaire « Donner mon avis » (`api/beta.py`, table `avis_beta`, route `POST /beta/avis`) : note d'utilité de
  1 à 5, ce qui a aidé, ce qui manque, une réponse fausse repérée et son lien (2 000 caractères au plus par champ,
  lien en `http(s)://`), date du jour. Ni adresse, ni numéro de compte, ni heure : l'avis n'est pas rattaché au
  compte (le formulaire demande de n'y écrire aucune information personnelle). Facultatif ; réservé aux comptes de
  la bêta et aux administrateurs ; 5 avis par compte et par jour (compteur haché de `compteurs_jour`, T7). Lu et
  exporté en CSV par l'administration (cellules commençant par `=`, `+`, `-`, `@` neutralisées). Pas de service
  tiers. Base légale : intérêt légitime (améliorer le service), réponse libre. Durée : 12 mois, purge à chaque
  lecture ou écriture (`AVIS_CONSERVES`). Non rattaché au compte : ni effacé avec lui, ni dans l'export ; une
  demande d'effacement d'un avis précis se traite à la main sur sa date et son texte.
- Mesure d'utilisation (`api/beta.py`, `suivre`, journal `logs/usage.jsonl`) : pour chaque appel de `/chat`
  (question, cas pratique, fiche), `/quiz`, `/resume-vocal`, `/carte-mentale` et du dépôt de cours, la fonction, le
  code HTTP de la réponse et la durée, avec la date et l'heure de la ligne (`ts`, commune aux journaux). Ni texte,
  ni compte, ni adresse IP ; appels des administrateurs non comptés. L'administration n'en lit que des agrégats
  (`GET /admin/beta/usage` : questions par jour, répartition par fonction, médiane et 90e centile des durées par
  étape lues dans `recherche_detail.etapes_ms` de `requetes.jsonl`, D114, taux d'erreur). Sans cookie ni traceur :
  pas de consentement (article 82 de la loi du 6 janvier 1978 non concerné). Base légale : intérêt légitime.
  Durée : 12 mois, comme les journaux techniques (T6).
- Destinataires : éditeur ; Hostinger (hébergement).
- Transferts hors UE : seulement l'acheminement par Cloudflare (États-Unis), comme tout le trafic du site (T7).

### T7. Sécurité du service

- Finalité : protéger le service contre les abus et les attaques.
- Données : journaux du serveur web nginx (adresse IP, date, page demandée, navigateur) ; adresses IP et réseaux
  IPv6 /64 gardés en mémoire par le limiteur de débit ; empreinte de l'adresse e-mail d'un compte supprimé
  depuis le site (table `suppressions`), qui empêche de se réinscrire dans les 24 h pour remettre son quota à zéro ;
  compteurs des e-mails envoyés et des codes de double authentification incorrects (table `compteurs_jour`, D119) :
  empreinte de la clé (numéro du compte, adresse IP ou réseau IPv6 /48, jamais en clair) et instant, pour les
  plafonds sur 24 h qui survivent à un redémarrage.
- Destinataires : éditeur, Hostinger, Cloudflare.
- Durée : journaux nginx 14 jours (rotation à vérifier sur le serveur : `/etc/logrotate.d/nginx`) ; empreinte
  compteurs de `compteurs_jour` : 24 h (lignes plus anciennes effacées au plus tard dix minutes après, à chaque
  nouvel envoi ou code) ; empreinte
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

### T10. E-mails d'information et origine des inscriptions

- Finalités : envoyer les nouveautés de Lexia par e-mail à ceux qui l'ont accepté ; savoir par quels canaux les
  étudiants connaissent Lexia (statistiques d'ensemble).
- Données (`api/comptes.py`, colonnes `infos_email_le` et `origine`) : date du consentement (case distincte, non
  cochée par défaut, à l'inscription ou dans « Mon compte ») ; réponse facultative à « Comment avez-vous connu
  Lexia ? » parmi six choix (réseaux sociaux, association étudiante, ami, enseignant, recherche, autre).
- Base légale : consentement pour les e-mails (C. postes et comm. électr., L. 34-5 ; RGPD art. 6.1.a), retirable à
  tout moment dans « Mon compte » (`POST /auth/infos-email`), le retrait efface la date ; intérêt légitime pour
  l'origine, que l'étudiant peut ne pas donner (« Je préfère ne pas répondre »).
- Destinataires : éditeur ; Resend quand un e-mail d'information sera envoyé (aucun envoi n'existe encore : chaque
  e-mail devra porter un lien de désinscription et ne partir qu'aux comptes dont `infos_email_le` est renseigné).
- Durée : comme le compte (effacées avec lui) ; incluses dans l'export des données (`api/export.py`).

### T11. Réutilisation de décisions de justice publiées

- Finalité : répondre aux questions des étudiants à partir de la jurisprudence publiée (index de recherche, extraits
  cités dans les réponses, liens vers la source).
- Personnes concernées : parties, témoins et autres personnes mentionnées dans les décisions ; membres des
  juridictions.
- Sources (`ingest/sources/`) : archives de la DILA (Cour de cassation `cass.py`, Conseil d'État `jade.py`,
  Conseil constitutionnel) ; depuis D113, API Judilibre de la Cour de cassation (`judilibre_api.py`, inactive tant
  que `JUDILIBRE_KEY_ID` manque) et site du Conseil constitutionnel (`constit_site.py`, actif). Décisions reprises
  telles que publiées, après l'occultation faite par la juridiction ou la DILA ; Lexia n'ajoute ni ne recoupe
  aucune donnée sur les personnes.
- Données : texte des décisions, avec les noms et éléments que la source n'a pas occultés ; métadonnées
  (juridiction, formation, date, numéro, ECLI).
- Base légale : intérêt légitime (mise à disposition de la jurisprudence publiée, réutilisation d'informations
  publiques sous Licence Ouverte 2.0 et CGU open data de la Cour de cassation ; mentions légales du Conseil
  constitutionnel). Information des personnes : section « Décisions de justice reproduites » de la politique de
  confidentialité (une information individuelle exigerait un effort disproportionné, RGPD art. 14.5.b).
- Garanties : jamais d'évaluation, de comparaison ni de prédiction des pratiques des magistrats et greffiers
  (C. org. jud., art. L. 111-13 ; aucune fonction ne classe ou ne regroupe les décisions par magistrat) ; arrêts
  supprimés par Judilibre retirés à la synchronisation suivante ; défauts d'occultation signalés à la Cour
  (`anonymisation.sder.courdecassation@justice.fr`) et demandes d'occultation renvoyées vers
  `occultations.courdecassation@justice.fr` (`docs/jurisprudence-recente.md`).
- Destinataires : utilisateurs de Lexia ; Google ou Groq pour les extraits retenus pour une réponse (T2).
- Durée : tant que la source publie la décision.
- Demande d'occultation ou de retrait : procédure dans `docs/procedure-occultation.md` (audit du 2026-11-23, E10) ;
  réponse dans un mois (RGPD art. 12.3). Aucun outil ne retire encore une décision précise de l'index : la liste
  d'exclusion lue à l'indexation reste à écrire dans `ingest/` (voir « Actions restantes »).

### T9. Échanges par e-mail

- Finalité : répondre aux demandes de formule payante, aux réclamations et aux demandes d'exercice des droits.
- Données : adresse e-mail, contenu des messages.
- Destinataire : fournisseur de la boîte `CONTACT_EMAIL` : iCloud Mail (Apple), cité dans la politique de
  confidentialité depuis le 2026-11-20 (audit JUR-18) ; localisation des données et accord de traitement d'Apple
  à vérifier.
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
| Groq, Inc. | Modèle de secours | Question et quelques extraits | États-Unis | **Non certifié** : clauses contractuelles types intégrées à l'accord de traitement de Groq du 15/10/2025 (§ 8.2, relu à l'audit du 2026-11-19, JUR-10), accord à archiver ; option « Zero Data Retention » demandée (D58), **à vérifier** dans la console et à archiver : la politique de confidentialité dit « demandée » tant que ce n'est pas fait (audit du 2026-11-23, E5) | Accord de traitement des données Groq : à lire et archiver |
| Resend | E-mails : confirmation d'adresse, réinitialisation, alerte de code de double authentification incorrect, avertissement d'inactivité, confirmation du contrat, paiement qui n'active aucune formule, accusé de rétractation | Adresse e-mail, texte du message (nom déclaré dans un accusé de rétractation) | États-Unis | Certifié (« actif, re-certification en cours d'examen » le 17 novembre 2026) | Accord de traitement des données Resend : à vérifier et archiver |
| Apple (iCloud Mail) | Boîte de l'adresse de contact (`CONTACT_EMAIL`) : demandes, réclamations, exercice des droits (T9) | Adresse e-mail et contenu des messages écrits à l'éditeur | À vérifier | À vérifier | Conditions d'iCloud : à lire ; un service grand public n'offre pas toujours d'accord art. 28 (audit du 2026-11-23, E14) |
| Stripe Payments Europe, Limited | Paiement par carte (Stripe Checkout) | T5 | Irlande (UE) ; Stripe, LLC aux États-Unis | Stripe, LLC certifiée (actif) | Contrat de services et accord de traitement des données Stripe, acceptés à l'ouverture du compte : à archiver |

Non sous-traitants : GitHub (surveillance de `/api/sante`, aucune donnée personnelle des utilisateurs).

## Mesures de sécurité (résumé)

Chiffrement en transit (HTTPS) ; empreintes scrypt des mots de passe ; jetons de session et de lien stockés en
empreinte seulement ; secrets de double authentification chiffrés ; accès direct au serveur limité aux adresses
de Cloudflare ; limites de débit par adresse IP ; sauvegardes en 600 ; deux audits de sécurité
(D80 et précédents dans `docs/decisions.md`).

## Actions restantes

1. Passer l'API Gemini au niveau payant et mettre `GEMINI_NIVEAU_PAYANT=1` (bloquant, D83).
2. Groq : archiver l'accord de traitement des données (clauses contractuelles types, § 8.2) et vérifier
   « Zero Data Retention » dans la console (EDI-2) ; une fois la confirmation archivée, remplacer « demandée » par
   « activée » dans la politique de confidentialité (nouvelle version).
3. Archiver les accords de traitement des données de Hostinger, Cloudflare, Google, Groq et Resend.
4. Vérifier la localisation du VPS Hostinger et la rotation des journaux nginx (14 jours).
5. Appliquer la durée des échanges par e-mail (T9, 3 ans) dans la boîte `CONTACT_EMAIL`.
6. Paiement : archiver le contrat Stripe ; confirmer 10 ans ou 6 ans (T5) ; mettre en place la purge des
   paiements au-delà de cette durée.
7. Décisions de justice (T11) : procédure écrite (`docs/procedure-occultation.md`, audit du 2026-11-23, E10) ;
   reste l'outil, une liste d'exclusion lue à l'indexation (`ingest/`, session sources), avant la première
   demande ; faire valider par le juriste la base légale et l'exception d'information de l'article 14.5.b.
9. iCloud Mail (T9) : vérifier la localisation des données et l'existence d'un accord de traitement ; à défaut,
   envisager une boîte professionnelle avec un accord art. 28.
8. Résumés vocaux : faire valider par le juriste la mention des voix en ligne du navigateur (D-11).
