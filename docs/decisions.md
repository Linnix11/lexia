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

## Journal des changements

- 2026-11-11 : création du document.
- 2026-11-11 : phase 1, ajout de D12 à D18.
