# Héberger Lexia sur un VPS Hostinger

Lexia tourne en **un seul service** : FastAPI sert l'API sous `/api` et le panel étudiant (React + Vite compilé) sur `/`. nginx est placé devant pour le HTTPS.

```
Navigateur ──HTTPS──> nginx (443) ──> uvicorn 127.0.0.1:8000 ──> /api/*  (recherche, Gemini, contrôle des citations)
                                                              └─> /*      (panel React compilé : web/dist)
```

## 1. Choisir l'offre

- **Un VPS est obligatoire** : l'hébergement mutualisé ne peut pas faire tourner Python ni les modèles d'embeddings.
- Système : **Ubuntu 24.04**.
- Mémoire : **4 Go minimum, 8 Go conseillés** (modèle d'embeddings + modèle de reclassement ≈ 2 Go, plus le système).
- Disque : ~6 Go (dépendances Python ≈ 2 Go, modèles ≈ 1,6 Go, index de recherche ≈ 320 Mo).
- Un nom de domaine (ou sous-domaine) pointant vers l'IP du VPS (enregistrement DNS de type A).

## 2. Préparer le serveur (une seule fois)

Sur le VPS, en root :

```bash
apt-get update && apt-get install -y rsync
```

Depuis le Mac, envoyer le script d'installation puis le lancer :

```bash
scp deploy/installer_serveur.sh root@IP_DU_VPS:/root/
ssh root@IP_DU_VPS "bash /root/installer_serveur.sh lexia.mondomaine.fr"
```

Il installe Python, nginx et certbot, crée l'utilisateur système `lexia` et le dossier `/opt/lexia`.

## 3. Publier depuis le Mac

Prérequis sur le Mac : l'environnement `.venv`, Node 20.19+ et l'index de recherche (`python -m ingest.build_index`).

```bash
LEXIA_SERVEUR=root@IP_DU_VPS LEXIA_DOMAINE=lexia.mondomaine.fr deploy/publier.sh
```

Le script :
0. vérifie, avant tout, que rien de non commité ne partirait en production et que le commit publié contient la version déjà en ligne (fichier `VERSION` du serveur) : une copie plus ancienne effacerait le travail publié entre-temps par une autre session. `LEXIA_FORCER=1` passe outre ces deux vérifications. Plusieurs sessions travaillant dans le même dépôt, publiez de préférence depuis une copie propre : `git worktree add --detach <dossier> <commit>` ;
1. lance les tests (API et front) ;
2. compile le front (`web/dist`) ;
3. prend le verrou de publication du serveur (`/run/lexia-publication`) : un seul envoi à la fois, les autres attendent 30 minutes au plus ; il est rendu à la fin, même en cas d'échec. Puis il envoie le code et le front avec rsync. L'index de recherche du serveur est gardé tel quel, puisqu'il est mis à jour chaque nuit (voir « Mise à jour du corpus »). `LEXIA_AVEC_INDEX=1` envoie à la place celui du Mac (4 Go) ;
4. installe les dépendances Python (PyTorch en version CPU) ;
5. installe le service systemd et la configuration nginx, puis redémarre le service ;
6. attend que `/api/sante` réponde.

**Premier lancement** : ajouter `HF_HUB_OFFLINE=0` à `/opt/lexia/.env` pour que le service télécharge les modèles (~1,6 Go, compter quelques minutes), puis retirer la ligne : ensuite, le service les lit dans le cache sans interroger Hugging Face.

## 4. Renseigner le `.env` de production

Au premier envoi, `/opt/lexia/.env` est créé à partir de `deploy/env.production.exemple`. Sur le serveur :

```bash
nano /opt/lexia/.env        # renseigner GEMINI_API_KEY
systemctl restart lexia
```

- Utiliser une **clé Gemini dédiée à la production**, de préférence au **niveau payant** : le gratuit plafonne à 20 requêtes par jour sur `gemini-3.5-flash` et sature souvent sur les modèles « lite ».
- Ne jamais commiter ce fichier ; il reste en `chmod 600`.

## 5. Activer le HTTPS

```bash
certbot --nginx -d lexia.mondomaine.fr -d www.lexia.mondomaine.fr
```

Certbot modifie la configuration nginx et renouvelle le certificat automatiquement.

## 6. Vérifier

```bash
curl https://lexia.mondomaine.fr/api/sante
```

Puis ouvrir `https://lexia.mondomaine.fr` : le panel doit afficher « Mon espace » et répondre à une question.

## Exploitation

| Action | Commande (sur le serveur) |
|---|---|
| État du service | `systemctl status lexia` |
| Journaux du service | `journalctl -u lexia -n 100 -f` |
| Redémarrer | `systemctl restart lexia` |
| Journaux applicatifs (sans texte des questions) | `/opt/lexia/logs/requetes.jsonl`, `/opt/lexia/logs/feedback.jsonl` |
| Mettre à jour | relancer `deploy/publier.sh` depuis le Mac |

### Mise à jour du corpus (automatique, chaque nuit)

La DILA publie chaque soir vers 21 h les textes et décisions modifiés du jour (archives quotidiennes de `https://echanges.dila.gouv.fr/OPENDATA/`). À 4 h 30, `/etc/cron.d/lexia` lance `/usr/local/sbin/lexia-mise-a-jour`, une copie de `deploy/mettre_a_jour_corpus.sh` appartenant à root et installée par `publier.sh`. Le script :

1. télécharge les nouvelles archives LEGI, CASS, JADE et CONSTIT dans `/opt/lexia/data/raw/dila` ;
2. s'il y a du nouveau, réimporte les sources, calcule les embeddings des seuls passages nouveaux ou modifiés et construit `data/index.nouveau` (`python -m ingest.mise_a_jour`, en tant que `lexia`, en priorité basse) ;
3. refuse le nouvel index s'il perd plus de 2 % des passages ou des embeddings, ou une source entière ;
4. le met en service (l'ancien est gardé dans `data/index.precedent`), redémarre le service (une trentaine de secondes) et revient à l'ancien si `/api/sante` ne répond plus ; un e-mail part à chaque échec, et un second si le service reste muet avec l'ancien index ;
5. compare les articles cités par les pages publiques (`data/citations-publiees.json`, envoyé par `publier.sh`) au nouvel index et prévient par e-mail si l'un d'eux a changé (pages à recompiler sur le Mac).

| Action | Commande (sur le serveur) |
|---|---|
| Journal | `tail -50 /var/log/lexia-mise-a-jour.log` |
| Lancer tout de suite | `/usr/local/sbin/lexia-mise-a-jour` (`--forcer` pour reconstruire sans nouvelle archive) |
| Revenir à l'index précédent | `cd /opt/lexia && sudo -u lexia bash -c 'mv data/index data/index.echec && mv data/index.precedent data/index' && systemctl restart lexia` |

Espace disque utilisé sur le serveur : environ 25 Go (archives DILA, extraction, passages, embeddings, trois index).

## Administration

Le tableau de bord `https://<domaine>/admin` est réservé aux comptes administrateurs :

- **Vue d'ensemble** : comptes, abonnés payants, revenu mensuel théorique, questions du jour, erreurs du modèle, satisfaction, graphique des questions par jour sur 30 jours, répartition par formule, activité des dernières 24 h ;
- **Clients** : recherche, changement de formule (avec durée), rôle administrateur, suppression ;
- **Activité** : dernières requêtes (sans le texte des questions) et erreurs du modèle ;
- **Serveur** : version, durée de fonctionnement, mémoire, disque, charge, corpus, modèles.

Devenir administrateur : ajouter son adresse dans `ADMIN_EMAILS` de `/opt/lexia/.env` (puis `systemctl restart lexia`), ou `sudo -u lexia .venv/bin/python -m api.admin admin <email>`. Les actions effectuées depuis le tableau de bord sont tracées dans `/opt/lexia/logs/admin.jsonl`.

## Comptes et formules

Les comptes étudiants sont stockés dans `/opt/lexia/donnees/lexia.db` (SQLite). `publier.sh` n'envoie ni n'efface jamais ce dossier.

Attribuer une formule payante (en attendant le paiement en ligne), sur le serveur :

```bash
cd /opt/lexia
sudo -u lexia .venv/bin/python -m api.admin liste
sudo -u lexia .venv/bin/python -m api.admin formule etudiant@exemple.fr etudiant --jours 31
sudo -u lexia .venv/bin/python -m api.admin infos etudiant@exemple.fr
```

Formules : `gratuit`, `etudiant`, `intensif` (limites dans `api/plans.py`). À l'échéance de `--jours`, le compte repasse en gratuit. Renseigner `CONTACT_EMAIL` dans `/opt/lexia/.env` pour afficher « Demander cette formule » sur la page Tarifs.

Cours déposés par les étudiants : seul leur texte est gardé, dans la même base (`donnees/lexia.db`), donc dans les mêmes sauvegardes. nginx doit accepter 21 Mo sur `/api/cours` (bloc `location /api/cours` de `deploy/nginx-lexia.conf`) : `publier.sh` n'installe la configuration nginx que si elle manque, il faut donc ajouter ce bloc à la main sur un serveur déjà en place.

Sauvegarde quotidienne de la base des comptes (14 jours conservés) : `publier.sh` installe `/etc/cron.d/lexia`, qui lance `deploy/sauvegarder_comptes.sh` à 3 h 15 en tant que `lexia` (journal : `/opt/lexia/logs/sauvegarde.log`).

### Sauvegarde hors serveur

Les sauvegardes du serveur sont sur le même disque que la base : elles ne protègent pas d'une perte du VPS. Le Mac en garde une copie :

```bash
LEXIA_SERVEUR=root@IP_DU_VPS deploy/rapatrier_sauvegardes.sh
```

Le script rapatrie les sauvegardes dans `~/Lexia-sauvegardes` (60 conservées), puis **teste la restauration** de la plus récente (intégrité SQLite, lecture de la table des comptes) et s'arrête en erreur sinon. Ces copies contiennent des e-mails et des empreintes de mots de passe : FileVault doit être activé.

Lancement quotidien : renseigner `deploy/fr.lexia.sauvegarde.plist` (chemin du dépôt, IP), le copier dans `~/Library/LaunchAgents/`, puis `launchctl load ~/Library/LaunchAgents/fr.lexia.sauvegarde.plist`. La clé SSH doit fonctionner sans saisie (agent ou trousseau). Journal : `/tmp/lexia-sauvegarde.log`.

Restaurer : arrêter le service (`systemctl stop lexia`), supprimer `/opt/lexia/donnees/lexia.db-wal` et `/opt/lexia/donnees/lexia.db-shm` s'ils existent (sinon SQLite rejoue sur la copie un journal qui ne lui appartient pas), remplacer `/opt/lexia/donnees/lexia.db` par la copie (propriétaire `lexia`, droits 600), redémarrer.

`CLE_SECRETS` (dans `/opt/lexia/.env`) chiffre les secrets de double authentification : sans elle, une sauvegarde restaurée sur un nouveau serveur laisse les comptes avec 2FA bloqués. La garder aussi dans un gestionnaire de mots de passe, hors du VPS.

Échecs : la sauvegarde du serveur envoie un e-mail aux `ADMIN_EMAILS` (`python -m ingest.fraicheur --sujet ... --alerte ...`), le rapatriement affiche une notification sur le Mac. Après une mise à jour de `deploy/rapatrier_sauvegardes.sh`, recopier le script là où le lance `fr.lexia.sauvegarde.plist`.

## Sécurité

- L'API n'écoute que sur `127.0.0.1` : seul nginx est exposé.
- Limite de requêtes côté nginx (par adresse IPv4, par réseau /64 en IPv6 : 120 par minute sur l'API, 5 par minute sur la connexion et les codes) et côté application (`RATE_LIMIT_PER_MINUTE`). `publier.sh` signale les lignes de `deploy/nginx-lexia.conf` absentes du serveur (fichier modifié par certbot, jamais remplacé) : les recopier, puis `nginx -t && systemctl reload nginx`.
- Le service tourne sous un utilisateur système sans shell, durci par systemd (`deploy/lexia.service`, à vérifier avec `systemd-analyze security lexia`), mémoire limitée à 75 % du VPS, date de Paris (`TZ=Europe/Paris`).
- Dépendances Python figées avec empreintes (`deploy/requirements-serveur.txt` et `deploy/requirements-torch.txt`, générés par `.venv/bin/python deploy/figer_dependances.py` à partir de `deploy/requirements-serveur.in`) et installées avec `--require-hashes`, un seul index par fichier.
- Aucune donnée personnelle collectée : pas de compte, journaux sans le texte des questions, favoris stockés dans le navigateur.

## Sécurité du serveur (audit du 2026-11-13)

- SSH par clé seulement (`/etc/ssh/sshd_config.d/00-lexia-securite.conf`), pare-feu `ufw` (22, 80, 443), fail2ban.
- n8n publié sur `127.0.0.1:32768` seulement, accessible en HTTPS via nginx.
- nginx : HSTS, CSP stricte (`script-src 'self'`), X-Frame-Options, Permissions-Policy, `server_tokens off` ;
  120 requêtes par minute sur l'API, 5 par minute sur la connexion, l'inscription et la suppression de compte.

## Passer derrière Cloudflare

Cloudflare protège le site des attaques par saturation, filtre les robots et met en cache les fichiers du front.

1. Créer un compte Cloudflare (offre gratuite) et y ajouter le domaine.
2. Chez le registraire du domaine, remplacer les serveurs DNS par ceux indiqués par Cloudflare.
3. Dans Cloudflare : enregistrement `A` vers l'IP du serveur, nuage orange (« proxied ») ;
   SSL/TLS en **Full (strict)** (le certificat Let's Encrypt du serveur reste valable) ;
   activer « Always Use HTTPS », le pare-feu géré gratuit et le mode « Bot Fight ».
4. Vérifier que le site répond, puis, sur le serveur : `bash /opt/lexia/deploy/restreindre_a_cloudflare.sh`
   (nginx ne sert plus Lexia qu'aux connexions venant de Cloudflare, les autres sites du serveur comme n8n
   ne sont pas touchés ; `--annuler` pour revenir en arrière ; relancer le script pour mettre à jour les plages).

L'adresse réelle des visiteurs (limites par adresse, journaux) est déjà lue dans l'en-tête de Cloudflare :
`/etc/nginx/snippets/lexia-cloudflare.conf` (copie de `deploy/nginx-cloudflare.conf`).

