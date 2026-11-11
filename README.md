# Lexia

Copilote d'étude en droit français pour étudiants (L1 en priorité). Réponses fondées uniquement sur des sources officielles citées.

État : **phase 2** (API de réponse sourcée et questionnaires). Phase suivante : brancher le front (maquette Lexia).

## Corpus actuel

| Source | Origine | Passages | Découpage |
|---|---|---|---|
| Constitution de 1958 | page du Conseil constitutionnel | 109 | 1 article |
| Code civil | archive DILA LEGI | 6 395 (2 897 en vigueur) | 1 version d'article, datée |
| Conseil constitutionnel | archive DILA CONSTIT, décisions DC + QPC | ~17 400 | motifs groupés (~2 000 car.) + dispositif |
| Cour de cassation | archive DILA CASS, arrêts publiés depuis 2016, chambres civiles | ~21 400 | sommaire + motifs groupés + dispositif |

Chaque passage garde : lien officiel, version / dates de vigueur, date de récupération, empreinte SHA-256, métadonnées (juridiction, date, numéro, ECLI, plan du code...). Les numéros de paragraphe ne sont indiqués que lorsqu'ils sont officiels.

## Arborescence

```
web/          front (maquette Lexia à porter, phase 3)
api/          backend FastAPI (phase 2) : llm/, retrieval/, schemas/
ingest/       import (sources/), embeddings (embed.py), chargement en base (load_db.py)
db/           schema.sql (PostgreSQL + pgvector)
registry/     sources.yaml : registre des sources, licences, périmètre, statut
data/         passages/*.jsonl, embeddings/ (cache), raw/ (archives) - seule la Constitution est commitée
eval/         jeu d'évaluation (phase 4)
docs/         decisions.md
tests/
```

## Installation

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # puis remplir ; .env n'est jamais commité
```

## 1. Télécharger les archives DILA

Dans `data/raw/dila/`, depuis https://echanges.dila.gouv.fr/OPENDATA/ : `LEGI/Freemium_legi_global_*.tar.gz` (~1,2 Go), `CONSTIT/Freemium_constit_global_*.tar.gz`, `CASS/Freemium_cass_global_*.tar.gz`. Le script prend toujours l'archive la plus récente présente.

## 2. Produire les passages

```bash
python -m ingest.run --all
```

La première exécution extrait les fichiers du Code civil de l'archive LEGI (quelques minutes), ensuite tout prend ~20 s.
Chaque source échoue volontairement si son format change (articles manquants, structure inconnue).

## 3. Calculer les embeddings

```bash
python -m ingest.embed --all
```

Par défaut, modèle open source exécuté en local : `intfloat/multilingual-e5-base` (licence MIT, 768 dimensions, multilingue). Environ 40 minutes pour tout le corpus sur un Mac M3 (GPU Apple), sans quota et sans envoyer les textes à un tiers. Le modèle (~1 Go) est téléchargé au premier lancement.

Le script peut être interrompu puis relancé sans rien recalculer (cache par empreinte et par modèle). Les versions d'articles qui ne sont plus en vigueur ne sont pas vectorisées. Les vecteurs de modèles différents ne sont jamais mélangés : changer `EMBED_MODEL` impose de recalculer.

`EMBED_PROVIDER=gemini` reste possible, mais le niveau gratuit est limité à 1 000 embeddings par jour.

**En production** : calculer les embeddings sur une machine avec GPU (ou un Mac), puis les charger en base avec `ingest.load_db`. Le serveur n'a besoin du modèle que pour vectoriser les questions (rapide, même sur CPU).

## 4. Charger dans PostgreSQL

Prérequis : PostgreSQL 15+ avec l'extension **pgvector**, `DATABASE_URL` dans `.env`.

```bash
python -m ingest.load_db --schema   # crée les tables
python -m ingest.load_db --all      # insère / met à jour / supprime + applique les embeddings
```

Rejouable : seuls les passages modifiés sont réécrits (et leur embedding remis à zéro), chaque exécution est tracée dans la table `synchros`.

## 5. Lancer l'API

```bash
python -m ingest.build_index          # index local (SQLite FTS5 + vecteurs), sans base de données
uvicorn api.main:app --port 8000      # documentation interactive : http://localhost:8000/docs
python eval/essai_api.py http://localhost:8000   # essai rapide avec de vraies questions
```

En production : `RETRIEVER=postgres` et `DATABASE_URL` (base chargée par `ingest.load_db`).

| Route | Rôle |
|---|---|
| `POST /chat` | question + mode (`expliquer`, `fiche`, `cas_pratique`, `commentaire`, `dissertation`) + matière |
| `POST /quiz` | thème, `format` (`qcm`, `vrai_faux`, `ouvertes`), `nombre` (1-15) ; les réponses restent côté serveur |
| `POST /quiz/correct` | correction (automatique pour QCM / vrai-faux, par le modèle pour les questions ouvertes) |
| `GET /sources/{id}` | texte complet et métadonnées d'un passage |
| `GET /sources/{id}/vigueur` | version en vigueur d'un article (ou « non applicable » pour une décision) |
| `POST /feedback` | utile oui / non + motif (pas de texte libre) |
| `GET /matieres`, `GET /sante` | listes et état du service |

### Garde-fous

- **Citations contrôlées côté serveur** : une source citée doit être un des extraits fournis ; une affirmation de droit positif sans source valide est retirée ; tout numéro d'article, de décision ou de pourvoi absent des extraits fait retirer l'élément. Sans affirmation sourcée restante, la réponse devient une abstention. Le détail est renvoyé dans `controle`.
- **Abstention** si rien n'est trouvé (le modèle n'est alors pas appelé) et **hors champ** pour les demandes de conseil personnel.
- **Recherche** : modèle d'embeddings local chargé au démarrage de l'API ; références citées (article, décision, pourvoi) d'abord, puis textes officiels avant jurisprudence, une entrée par décision. La recherche vectorielle n'est utilisée que si au moins 90 % des passages concernés ont un embedding (sinon elle fausserait le classement) ; sinon recherche lexicale seule.
- **Modèle** : principal puis secours (`GEMINI_FALLBACK_MODELS`) en cas de 429 / 503 / délai dépassé ; réponse 503 claire si tous échouent.
- **Données** : clé côté serveur uniquement ; journaux `logs/*.jsonl` sans le texte des questions ; limite de requêtes par IP et de taille des questions.

## Tests

```bash
python -m pytest -q
```

Les tests utilisent de vrais documents extraits des archives (`tests/fixtures/`) et un modèle simulé pour l'API.
