# Lexia

Copilote d'étude en droit français pour étudiants (L1 en priorité). Réponses fondées uniquement sur des sources officielles citées.

État : **phase 1** (corpus officiel, embeddings, schéma de base). Phase suivante : backend RAG.

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

## 3. Calculer les embeddings (Gemini)

```bash
python -m ingest.embed --all
```

Modèle et dimension : `GEMINI_EMBED_MODEL` (768 dimensions). Le niveau gratuit est limité à 100 embeddings par minute : compter ~7 h pour tout le corpus. Le script attend automatiquement quand le quota est atteint, et peut être interrompu puis relancé sans rien recalculer (cache par empreinte). Les versions d'articles qui ne sont plus en vigueur ne sont pas vectorisées.

## 4. Charger dans PostgreSQL

Prérequis : PostgreSQL 15+ avec l'extension **pgvector**, `DATABASE_URL` dans `.env`.

```bash
python -m ingest.load_db --schema   # crée les tables
python -m ingest.load_db --all      # insère / met à jour / supprime + applique les embeddings
```

Rejouable : seuls les passages modifiés sont réécrits (et leur embedding remis à zéro), chaque exécution est tracée dans la table `synchros`.

## Tests

```bash
python -m pytest -q
```

Les tests utilisent de vrais documents extraits des archives (`tests/fixtures/`).
