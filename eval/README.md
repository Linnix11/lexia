# Évaluation de Lexia (phase 4)

## Contenu

| Fichier | Rôle |
|---|---|
| `cas.yaml` | Jeu de 150 cas : 40 introduction au droit, 40 droit constitutionnel, 40 droit civil, 30 pièges |
| `cas.py` | Chargement du jeu et correspondance avec les sources du corpus |
| `run.py` | Exécute les cas contre le pipeline réel (recherche, Gemini, contrôle des citations) |
| `rapport.py` | Synthèse (indicateurs, seuils, cas à examiner) et grille de relecture CSV |
| `recherche.py` | Banc d'essai rapide de la recherche seule (sans appel au modèle de réponse) |
| `essai_api.py` | Quelques questions contre une API lancée, pour un contrôle visuel |

## Lancer

```bash
python eval/run.py                                      # ~45 min pour 150 cas (rythme limité pour le quota)
python eval/run.py --reprendre eval/resultats/<run>.jsonl   # compléter les cas en erreur
python eval/rapport.py eval/resultats/<run>.jsonl
```

Le niveau gratuit de Gemini limite fortement le nombre d'appels par jour (20 par jour pour `gemini-3.5-flash`, constaté le 2026-11-11). Chaque cas fait 2 appels (reformulation + réponse). Un run complet nécessite un modèle au quota plus large ou le niveau payant.

## Indicateurs automatiques

| Indicateur | Définition | Seuil |
|---|---|---|
| Citations vers un passage réel | toute source citée existe dans le corpus | 100 % |
| Réponses sourcées | réponse juridique avec au moins une affirmation de droit positif sourcée | ≥ 90 % |
| Pièges | statut attendu (refus, abstention) sur les 30 cas pièges | ≥ 85 % |
| Source attendue fournie | la recherche a transmis au modèle au moins une source attendue | suivi |
| Source attendue citée | la réponse cite au moins une source attendue | suivi |
| Tentatives d'invention bloquées | citations ou références retirées par le contrôle | suivi |

## Relecture par l'enseignant (indispensable)

1. **Valider le jeu de cas** (`cas.yaml`) : questions représentatives du programme de L1, sources attendues correctes, comportement attendu. Le jeu actuel est un brouillon rédigé sans relecture juridique.
2. **Noter les réponses** dans `<run>_grille.csv` (ouvrable dans Excel / LibreOffice, séparateur `;`) :
   - **exactitude** (1 à 5) : 5 = juridiquement exact et complet au regard des sources ; 3 = exact mais incomplet ou imprécis ; 1 = erreur de droit ;
   - **utilité** (1 à 5) : clarté pédagogique pour un étudiant de L1 ;
   - **commentaire** : erreur relevée, source manquante, formulation à revoir.
3. Seuil pour passer au pilote : exactitude moyenne ≥ 4/5, et aucune erreur de droit sur les cas notés 1.
