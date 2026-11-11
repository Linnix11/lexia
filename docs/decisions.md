# Décisions - Phase 0

Statut : **proposées, à valider**. Changer une ligne = noter la date et la raison en dessous du tableau.

| # | Sujet | Décision | Statut |
|---|---|---|---|
| D1 | Droit | Droit français | proposé |
| D2 | Niveau | L1 | proposé |
| D3 | Matières pilotes | Introduction au droit, Droit constitutionnel, Droit civil (contrats + responsabilité) | proposé |
| D4 | Sources officielles V1 | Constitution 1958, Code civil, décisions du Conseil constitutionnel, arrêts publiés de la Cour de cassation | proposé |
| D5 | Modèle | Gemini Flash via API Gemini Developer ; nom du modèle en variable `GEMINI_MODEL` | proposé |
| D6 | Données personnelles | Aucune en V1 : pas de compte, pas d'historique serveur, favoris en localStorage | proposé |
| D7 | Backend | Python + FastAPI | proposé |
| D8 | Base | PostgreSQL + pgvector + plein texte français (recherche hybride) | proposé |
| D9 | Front | Reprise de la maquette Lexia (`panel-ia-droit-v1.html`) en **Vite + React + TypeScript + Tailwind CSS** (décidé le 2026-11-11) | validé |
| D10 | Manuels | Métadonnées + liens uniquement ; aucun texte intégral sans licence écrite | proposé |
| D11 | Référent pédagogique | 1 enseignant ou chargé de TD, à trouver | ouvert |

## Source de la Constitution (phase 0)

Le texte est récupéré depuis la page officielle du Conseil constitutionnel (« Texte intégral de la Constitution du 4 octobre 1958 en vigueur »). Légifrance bloque les requêtes automatiques hors API : la bascule vers l'API Légifrance (PISTE) se fera en phase 1 quand les identifiants seront obtenus, pour harmoniser avec le Code civil.

## Phase 1 - choix retenus

| # | Sujet | Décision |
|---|---|---|
| D12 | Accès aux données | Archives open data DILA (LEGI, CONSTIT, CASS) au lieu de l'API PISTE : utilisables sans compte. PISTE reste une option pour les mises à jour fines. |
| D13 | Périmètre Conseil constitutionnel | Décisions DC et QPC uniquement (contentieux électoral exclu). |
| D14 | Périmètre Cour de cassation | Arrêts publiés depuis 2016 : 1re et 3e civ., Ass. plén., ch. mixte ; 2e civ. limitée à responsabilité / accidents / assurance / indemnisation. |
| D15 | Versions du Code civil | Toutes les versions d'articles sont conservées ; seules celles en vigueur sont vectorisées. |
| D16 | Embeddings | `gemini-embedding-2`, 768 dimensions, cache local par empreinte. |
| D17 | Modèle de génération | `gemini-3.8-flash` (nom vérifié dans la liste des modèles de l'API), configurable. |
| D18 | Base | PostgreSQL + pgvector hébergée par l'équipe (Hostinger) ; pas de Docker. |

## Phase 2 - choix retenus

| # | Sujet | Décision |
|---|---|---|
| D19 | Modèle de génération | `gemini-3.5-flash` (le plus rapide aux essais), secours `gemini-3.8-flash`, raisonnement `low`, délai 30 s. Remplace D17. |
| D20 | Recherche sans base | Index local SQLite FTS5 + numpy pour le développement ; même interface que PostgreSQL. |
| D21 | Recherche vectorielle | Utilisée seulement si au moins 90 % des passages concernés ont un embedding. |
| D22 | Contrôle des citations | Côté serveur, après le modèle : sources inconnues, affirmations non sourcées et numéros absents des extraits sont retirés. |
| D23 | Questionnaires | Réponses gardées en mémoire du serveur 3 h, jamais envoyées avant correction. |
| D24 | Retours | Utile oui / non + motif dans une liste fermée, pas de texte libre (aucune donnée personnelle). |

### Embeddings (tranché le 2026-11-11)

| # | Sujet | Décision |
|---|---|---|
| D25 | Modèle d'embeddings | Modèle open source local `intfloat/multilingual-e5-base` (MIT, 768 dimensions) à la place de Gemini, dont le niveau gratuit plafonne à 1 000 embeddings par jour. Remplace D16. Gemini reste disponible via `EMBED_PROVIDER=gemini`. |
| D26 | Calcul en production | Embeddings du corpus calculés hors serveur puis chargés en base ; le serveur ne vectorise que les questions. |

### Classement des résultats (2026-11-11)

Mesure sur 8 questions de cours (`eval/recherche.py`) : l'article de principe attendu figure-t-il parmi les extraits envoyés au modèle ?

| Configuration | Trouvés | Temps de recherche moyen |
|---|---|---|
| Hybride seul | 5/8 | 0,2 s |
| + reclassement | 7/8 | 2,5 s |
| + reformulation | 8/8 | 1,8 s (si Gemini répond) |

| # | Sujet | Décision |
|---|---|---|
| D27 | Reclassement | Cross-encoder local `antoinelouis/crossencoder-camembert-base-mmarcoFR` (MIT, français) sur les 30 meilleurs candidats. Comparé à `mmarco-mMiniLMv2` (plus rapide, moins bon) et `bge-reranker-v2-m3` (meilleur sur certains cas mais ~4x plus lent). `RERANK_MODEL` vide = désactivé. |
| D28 | Reformulation | `gemini-3.5-flash` reformule la question et propose au plus 4 articles ; seul leur texte officiel du corpus est utilisé. Une tentative, 8 s maximum, sinon recherche sans reformulation. Double l'usage du quota Gemini par question. `QUERY_EXPANSION_MODEL` vide = désactivé. |

### Phase 4 - évaluation (2026-11-11)

| # | Sujet | Décision |
|---|---|---|
| D29 | Modèles Gemini | Niveau gratuit de `gemini-3.5-flash` limité à 20 requêtes par jour (constaté) : génération et reformulation passées sur `gemini-3.5-flash-lite`, secours `gemini-flash-lite-latest` puis `gemini-3.8-flash`. Remplace D19. **Pour le pilote, passer au niveau payant** : le gratuit ne tient pas une journée de tests. |
| D30 | Modes méthode | En cas pratique, commentaire et dissertation, la méthode peut être expliquée sans extrait ; le droit positif exige toujours une source et les numéros inventés restent bloqués. |
| D31 | Jeu d'évaluation | 150 cas (`eval/cas.yaml`), brouillon à faire valider par l'enseignant référent (D11) avant toute conclusion. |

### Site et formules (2026-11-11)

| # | Sujet | Décision |
|---|---|---|
| D32 | Formules | Gratuit (compte requis) : 10 questions + 2 questionnaires par jour ; Étudiant 4,99 €/mois : 100 + 20 ; Intensif 9,99 €/mois : 300 + 100. Limites dans `api/plans.py`, remise à zéro à minuit (Paris). Une question n'est décomptée que si le modèle a répondu. |
| D33 | Paiement | Pas de paiement en ligne pour l'instant : formules payantes attribuées par l'administrateur (`python -m api.admin`), demande par e-mail (`CONTACT_EMAIL`). |
| D34 | Comptes | E-mail + mot de passe (scrypt), cookie de session HttpOnly / SameSite=Lax / Secure, contrôle de l'en-tête Origin, freins aux tentatives, suppression du compte en libre-service. Base SQLite `donnees/lexia.db`, jamais versionnée ni écrasée au déploiement. |
| D36 | Administration | Rôle admin (colonne `admin` ou `ADMIN_EMAILS`) et tableau de bord `/admin` : indicateurs, clients et formules, activité, état du serveur. Actions tracées dans `logs/admin.jsonl` ; aucun texte de question exposé. |
| D35 | Pages légales | Mentions légales, CGU, confidentialité : modèles à compléter ([À COMPLÉTER]) et à faire relire avant l'ouverture publique. |

## Journal des changements

- 2026-11-11 : création du document.
- 2026-11-11 : phase 1, ajout de D12 à D18.
- 2026-11-11 : phase 2, ajout de D19 à D24 et du point ouvert sur le quota d'embeddings.
- 2026-11-11 : embeddings open source en local (D25, D26).
- 2026-11-11 : D9 validé, front en Vite + React + TypeScript + Tailwind.
- 2026-11-11 : reclassement et reformulation de la question (D27, D28).
- 2026-11-11 : phase 4, évaluation (D29 à D31).
- 2026-11-11 : site complet, comptes et formules (D32 à D35).
- 2026-11-11 : tableau de bord administrateur (D36).
