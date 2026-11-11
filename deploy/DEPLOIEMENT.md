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
1. lance les tests (API et front) ;
2. compile le front (`web/dist`) ;
3. envoie le code, le front et l'index (`data/index`) avec rsync ;
4. installe les dépendances Python (PyTorch en version CPU) ;
5. installe le service systemd et la configuration nginx, puis redémarre le service ;
6. attend que `/api/sante` réponde.

**Premier lancement** : le service télécharge les modèles (~1,6 Go), compter quelques minutes.

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
certbot --nginx -d lexia.mondomaine.fr
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

Mettre à jour le corpus : sur le Mac, `python -m ingest.run --all`, `python -m ingest.embed --all`, `python -m ingest.build_index`, puis `deploy/publier.sh`.

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

Sauvegarde quotidienne de la base des comptes (14 jours conservés) :

```bash
crontab -e
# ajouter la ligne :
15 3 * * * /opt/lexia/deploy/sauvegarder_comptes.sh
```

## Variante : base PostgreSQL

Si une base PostgreSQL avec l'extension **pgvector** est disponible (sur le VPS ou ailleurs) :

```bash
# sur le Mac, avec DATABASE_URL pointant vers la base
python -m ingest.load_db --schema
python -m ingest.load_db --all
```

Puis dans `/opt/lexia/.env` : `RETRIEVER=postgres` et `DATABASE_URL=postgresql://...`. Cette variante n'a pas encore été testée sur une vraie base ; l'index SQLite local suffit pour le pilote.

## Sécurité

- L'API n'écoute que sur `127.0.0.1` : seul nginx est exposé.
- Limite de requêtes par IP côté nginx (20 par minute) et côté application (`RATE_LIMIT_PER_MINUTE`).
- Le service tourne sous un utilisateur système sans shell, avec un durcissement systemd minimal.
- Aucune donnée personnelle collectée : pas de compte, journaux sans le texte des questions, favoris stockés dans le navigateur.
