# Relecture de Lexia par un enseignant

Dossier préparé le 23 novembre 2026 pour la relecture des réponses de Lexia par un enseignant en droit.

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

État : 21 réponses sur 30. Les 9 autres n'ont pas pu être obtenues le 23 novembre (Gemini indisponible puis quota
gratuit épuisé). Le dossier ne doit pas être envoyé avant de les avoir complétées : voir la section 5 de
`constats-avant-relecture.md`.

Régénérer (depuis la racine du dépôt) :

```bash
.venv/bin/python docs/relecture-enseignant/outils/interroger.py --n 7,9,10,13,14,19,20,21,26 --pause 60
```

```bash
python3 docs/relecture-enseignant/outils/generer.py
```

`interroger.py` a besoin du `.env` du dépôt (clé Gemini) ; il ne l'affiche pas. `generer.py` utilise
python-docx et openpyxl (Python du système).
