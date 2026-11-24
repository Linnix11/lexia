# Relecture de Lexia par un enseignant

Dossier préparé le 23 novembre 2026 pour la relecture des réponses de Lexia par un enseignant en droit ; réponses reposées le 24 novembre 2026.

| Fichier | Rôle | Destinataire |
|---|---|---|
| `lettre.md`, `lettre.docx` | Lettre d'accompagnement (passages entre crochets à compléter) | Enseignant |
| `dossier.docx` | Dossier imprimable : présentation, mode d'emploi, grille d'une page, 30 questions et réponses avec cases de notation | Enseignant |
| `grille.xlsx` | Saisie des notes (0 à 3, cinq critères) et moyennes calculées | Enseignant |
| `dossier.md` | Même contenu que `dossier.docx`, lisible dans le dépôt | Éditeur |
| `constats-avant-relecture.md` | Réponses fausses ou douteuses repérées avant l'envoi, et ce qui reste à faire | Éditeur seulement |
| `questions.json` | Les 30 questions, avec les éléments de réponse attendus | Éditeur |
| `reponses.jsonl` | Réponses brutes de Lexia (modèle, sources, contrôle) | Éditeur |
| `outils/interroger.py` | Pose les questions au moteur local (même chemin que `POST /chat`) | Éditeur |
| `outils/generer.py` | Construit `dossier.md`, `dossier.docx`, `grille.xlsx` et `lettre.docx` | Éditeur |

État : 30 réponses sur 30, obtenues le 24 novembre 2026 (code `c9c92cd`). 24 justes, 1 fausse (28), 3 douteuses
(21, 24, 26), 2 abstentions correctes : voir `constats-avant-relecture.md`, sections 1 et 7, avant l'envoi.

Régénérer (depuis la racine du dépôt) :

```bash
.venv/bin/python docs/relecture-enseignant/outils/interroger.py --pause 60
```

```bash
python3 docs/relecture-enseignant/outils/generer.py
```

`interroger.py` a besoin du `.env` du dépôt (clé Gemini) ; il ne l'affiche pas. `generer.py` utilise
python-docx et openpyxl (Python du système).
