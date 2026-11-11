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

## Journal des changements

- 2026-11-11 : création du document.
