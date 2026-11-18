# Audit de la base des comptes, 18 novembre 2026 (D99)

Base auditee : `/opt/lexia/donnees/lexia.db` sur le serveur (3 comptes), code de `api/comptes.py`, `api/cours.py`,
`api/paiement.py`, `api/coffre.py` et des scripts de sauvegarde. Verifications sur le serveur en lecture seule
(base ouverte en `mode=ro`, en tant que lexia) : seuls des comptes, des longueurs et des formes ont ete lus,
jamais une valeur. Aucune modification de la production.

## Resume

La base est bien protegee pour ce qui compte le plus : mots de passe haches, jetons haches, secrets de double
authentification chiffres, aucune donnee de carte. Trois faiblesses corrigees dans le code (a publier) :

1. Un compte supprime laissait son adresse, son empreinte et le texte de ses cours lisibles dans le fichier de
   la base (et dans le journal WAL) jusqu'au prochain nettoyage.
2. La base, son journal WAL et les journaux techniques etaient crees lisibles par tout utilisateur du serveur
   (droits 644).
3. Une copie faite a la main dans le dossier des sauvegardes (`lexia-avant-vacuum-20261118.db`, ce matin)
   va faire echouer chaque jour la copie hors serveur sur le Mac, a partir de demain 9 h 30.

## Colonne par colonne

| Donnee | Stockage | En production | Verdict |
|---|---|---|---|
| Mot de passe (`utilisateurs.mdp`) | scrypt, sel aleatoire de 16 octets | 3 sur 3 en scrypt ; 1 aux parametres actuels (N=2^14, r=8, p=5), 2 aux anciens (p=1) | Bon. Les 2 anciennes empreintes sont refaites a la prochaine connexion de ces comptes (impossible sans le mot de passe). |
| Jeton de session (`sessions.jeton_hash`) | SHA-256 d'un jeton aleatoire de 256 bits | 7 sessions, toutes de 64 caracteres hexadecimaux, aucune expiree | Bon. Un hachage rapide suffit pour un jeton aleatoire de cette taille. |
| Lien de verification d'e-mail (`verif_jeton`) | SHA-256 | aucun lien en cours | Bon. Expire en 24 h, usage unique. |
| Lien de mot de passe oublie (`reinit_jeton`) | SHA-256 | aucun lien en cours | Bon. Expire en 1 h, usage unique. |
| Secret de double authentification (`totp_secret`, `totp_attente`) | AES-256-GCM (`api/coffre.py`), prefixe `v1:` | 1 secret actif, prefixe `v1:`, 83 caracteres (3 de prefixe + 80 de base64 : nonce, secret chiffre, etiquette) | Bon. C'est bien le prefixe reel : une valeur en clair ferait 32 caracteres en base32. La cle n'est pas dans la base. |
| Codes de secours (`totp_secours`) | SHA-256 de chaque code, liste JSON chiffree par AES-256-GCM | prefixe `v1:`, 767 caracteres | Bon. Note : sans la cle, une empreinte SHA-256 d'un code de 8 caracteres (environ 40 bits) se retrouverait vite ; c'est le chiffrement qui protege, donc la cle doit rester hors des sauvegardes de la base (c'est le cas). |
| Adresse e-mail (`utilisateurs.email`) | en clair | 3 adresses | Accepte. Necessaire pour la connexion et les envois ; un chiffrement demanderait un index aveugle, disproportionne ici. Protegee par les droits des fichiers. |
| Trace de suppression (`suppressions.boite`) | SHA-256 de l'adresse | aucune | Accepte. Gardee 24 h seulement ; une empreinte sans sel permet de tester une adresse devinee, sans plus. |
| Cours deposes (`cours`, `cours_passages`, `cours_fts`) | texte en clair, fichier d'origine non garde | 2 cours, 870 passages ; index plein texte en mode d'effacement securise | Accepte (recherche dans le texte). Le retrait d'un cours efface deja ses octets (audit C7) ; la suppression d'un compte ne le faisait pas (point 1). |
| Paiements (`paiements`) | adresse, identifiants Stripe (`cs_`, `pi_`), montant ; aucune donnee de carte | table absente : Stripe pas encore active | Bon. A garder 10 ans (comptabilite), sans cle etrangere. |
| Questionnaires (`questionnaires`) | contenu des quiz | 0 ligne | Rien de personnel. |

Recherche dans les octets bruts du fichier et du journal WAL : 3 empreintes `scrypt$` et 3 adresses, celles des
comptes vivants ; aucune page libre (la base a ete compactee ce matin). Pas de reste d'ancien compte aujourd'hui.

## Constats et corrections

### 1. Compte supprime encore lisible dans le fichier (corrige)

`api/cours.py` active `PRAGMA secure_delete` depuis l'audit C7, mais ce reglage vaut par connexion. La
suppression d'un compte passe par la connexion de `api/comptes.py`, qui ne l'activait pas : l'adresse,
l'empreinte du mot de passe et le texte des cours (supprimes en cascade) restaient dans les pages liberees et
dans le journal WAL. Cela vaut pour une suppression demandee depuis le site, par l'administrateur et pour les
comptes inactifs depuis deux ans. Reproduit par un test avant correction.

Correction : `secure_delete` active aussi dans `Comptes` (octets remis a zero a chaque suppression ou
remplacement), et journal WAL vide apres la suppression d'un compte, comme pour un cours. Test :
`test_compte_supprime_absent_des_octets_de_la_base`.

Migration : inutile. La base de production n'a aucune page libre et aucun reste d'ancien compte (verifie).

### 2. Droits des fichiers (corrige)

Sur le serveur : `.env` en 600, dossiers `donnees` et `sauvegardes` en 700, sauvegardes en 600 : bien. Mais
`lexia.db`, `lexia.db-wal`, `lexia.db-shm` et les journaux de `logs/` sont en 644, `logs/` en 755 et
`sauvegarde.log` en 664. Le dossier `donnees` en 700 empeche aujourd'hui la lecture de la base, et `root` est le
seul compte avec un shell ; c'est donc une defense en profondeur, mais un fichier deplace ou un dossier mal
regle exposerait la base.

Correction : `UMask=0077` dans `deploy/lexia.service`, `umask 077` dans `deploy/sauvegarder_comptes.sh`, et
`deploy/publier.sh` remet en 600 les fichiers existants de `donnees`, `logs` et `sauvegardes` (dossiers en 700).
Les journaux techniques ne contiennent aucune adresse e-mail (verifie : 0 ligne sur 342).

### 3. Sauvegardes (corrige en partie, decision a prendre)

- Serveur : une copie par nuit a 3 h 15 par `VACUUM INTO` (sans pages libres), 14 gardees, en 600 dans un
  dossier en 700. Derniere : cette nuit. Non chiffrees : sur le meme disque que la base elle-meme, un
  chiffrement n'ajouterait rien.
- Hors serveur : le Mac rapatrie les copies chaque jour a 9 h 30 (`fr.lexia.sauvegarde` charge, dossier
  `~/Lexia-sauvegardes` en 700, FileVault actif), 60 jours gardes, restauration testee. Bien.
- Bogue : la copie manuelle `lexia-avant-vacuum-20261118.db` faite ce matin sur le serveur serait rapatriee
  demain ; son nom passe apres les copies datees dans le tri, le script la prenait pour la plus recente, le
  controle de fraicheur echouait chaque jour et elle n'etait jamais effacee du Mac. Corrige :
  `deploy/rapatrier_sauvegardes.sh` ne rapatrie que les copies datees (`lexia-AAAAMMJJ.db`). Test :
  `test_rapatriement_ignore_les_copies_manuelles`.
- Les copies ne contiennent pas `CLE_SECRETS` : bien pour la securite, mais si le serveur est perdu, les
  doubles authentifications seront a reactiver (`python -m api.admin desactiver2fa`). Garder la cle dans un
  gestionnaire de mots de passe.

### Autres points verifies

- SSH : connexion par mot de passe refusee, root seulement par cle (configuration effective `sshd -T`).
- Un seul compte systeme avec un shell : root.
- Aucune autre copie de la base sur le serveur.
- `/root/env.avant-nettoyage-resend` (600, root) est une ancienne copie de `.env` qui contient d'anciens
  secrets.

## A faire par l'editeur (rien n'a ete modifie en production)

1. Publier ce changement (`deploy/publier.sh`) : il redemarre le service avec `UMask=0077` et corrige les droits
   des fichiers existants.
2. Avant demain 9 h 30 : recopier `deploy/rapatrier_sauvegardes.sh` vers
   `~/Library/Application Support/Lexia/rapatrier_sauvegardes.sh` (la tache du Mac lance cette copie, identique
   a l'ancienne version), ou supprimer la copie manuelle `/opt/lexia/sauvegardes/lexia-avant-vacuum-20261118.db`
   si elle n'est plus utile (sinon elle disparait seule du serveur apres 14 nuits).
3. Supprimer `/root/env.avant-nettoyage-resend` si ces anciens secrets ne servent plus.
4. Noter `CLE_SECRETS` dans un gestionnaire de mots de passe.
