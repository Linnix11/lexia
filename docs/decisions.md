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
| D9 | Front | Reprise de la maquette Lexia (`panel-ia-droit-v1.html`) en React / Next.js | proposé |
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

### Point ouvert : quota d'embeddings

Le niveau gratuit de l'API Gemini limite les embeddings à 1 000 par jour (et 100 par minute). Vectoriser tout le corpus (~41 700 passages) prendrait environ 42 jours, et chaque question d'étudiant consomme aussi ce quota. À trancher avant le pilote : passer au niveau payant, utiliser un modèle d'embeddings open source hébergé sur le serveur, ou réduire le périmètre vectorisé.

## Journal des changements

- 2026-11-11 : création du document.
- 2026-11-11 : phase 1, ajout de D12 à D18.
- 2026-11-11 : phase 2, ajout de D19 à D24 et du point ouvert sur le quota d'embeddings.
