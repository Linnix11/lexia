# Lexia · panel étudiant

Vite + React + TypeScript + Tailwind CSS. Reprend la maquette `panel-ia-droit-v1.html`.

```bash
npm install
npm run dev      # http://localhost:5173 ; /api est relayé vers l'API (http://localhost:8000)
npm test         # tests (Vitest + Testing Library)
npm run build    # production : définir VITE_API_URL=https://… avant le build
```

L'API doit tourner à côté : depuis la racine du dépôt, `uvicorn api.main:app --port 8000`.
Autre adresse en développement : `LEXIA_API=http://… npm run dev`.

## Écrans

- **Mon espace** : assistant, boîte à outils, sources de confiance, bibliothèque.
- **Assistant IA** : 5 modes (expliquer, fiche, cas pratique, commentaire d'arrêt, dissertation), filtre par matière.
- **Mes matières** : matières et sources associées, accès direct à l'assistant ou au quiz.
- **Fiches & révisions** : réponses enregistrées (stockées dans le navigateur uniquement).
- **Bibliothèque** : sources officielles et références de manuels.

Chaque réponse affiche le droit positif, l'explication et les points d'attention ; les références `[S1]` ouvrent le texte de la source avec « Vérifier la version en vigueur ». Le quiz (QCM, vrai/faux, questions ouvertes) est corrigé par l'API.
