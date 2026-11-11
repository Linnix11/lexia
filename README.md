# Lexia

Copilote d'étude en droit français pour étudiants (L1 en priorité). Réponses fondées uniquement sur des sources officielles citées.

État : **phase 0** (socle, registre des sources, ingestion de la Constitution).

## Arborescence

```
web/          front (maquette Lexia à porter, phase 3)
api/          backend FastAPI (phase 2) : llm/, retrieval/, schemas/
ingest/       scripts d'import, un module par source (ingest/sources/)
registry/     sources.yaml : registre des sources, licences, statut
data/         passages/*.jsonl (commités), raw/ (copies brutes, non commitées)
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

## Ingestion

```bash
python -m ingest.run --source constitution_1958
```

Produit `data/passages/constitution_1958.jsonl` : 1 ligne par article (+ préambule), avec numéro, titre, alinéas, lien officiel avec ancre, mention de version, date de récupération et empreinte SHA-256.
Le parseur échoue volontairement si la structure de la page change (moins de 100 articles, version absente, doublons).

## Tests

```bash
python -m pytest -q
```
