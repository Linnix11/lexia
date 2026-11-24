# Grands arrêts (D124) : réponses du modèle, 24 novembre 2026

Conditions : Mac, index du 17 novembre, code de main c3e4b04, après la relance des 30 questions du dossier enseignant
(fin à 11 h 01). `python eval/run.py --fichier eval/cas_grands_arrets_notions.yaml --ids gan-01,gan-06,gan-10,gan-13`
(gan-01 seul d'abord pour tester le quota, puis `--reprendre`). Réponses brutes : `20261124-110151.jsonl`.
Quatre réponses obtenues de Gemini, aucune erreur, aucun élément retiré par le contrôle des citations.

| Cas | Question | Grands arrêts fournis | Cités par juridiction, date et nom d'usage | Arrêt abandonné présenté comme droit positif | Fiche Lexia présentée comme officielle |
|---|---|---|---|---|---|
| gan-01 | Conditions de la responsabilité du fait des choses | Jand'heur, Franck, Teffaine (fiches) | Oui : « Cass., ch. réunies, 13 février 1930, Jand'heur » et « Cass., ch. réunies, 2 décembre 1941, Franck » ; Teffaine non cité | Sans objet | Non (sources « Fiche Lexia (non officielle) ») ; mais un élément de droit positif repose sur la seule fiche Franck |
| gan-06 | Principe de primauté du droit de l'Union | Costa, Simmenthal (fiches), Jacques Vabre (sommaire) | **Non** : les trois arrêts sont dans les sources des éléments, aucun n'est nommé ni daté dans le texte | Sans objet | Non (sources « Fiche Lexia (non officielle) ») |
| gan-10 | Fondements de la responsabilité administrative | Blanco, Pelletier, Couitéas (sommaires officiels) | Oui : « TC, 8 février 1873, Blanco » et « CE, 30 novembre 1923, Couitéas » ; Pelletier non cité | Sans objet | Sans objet |
| gan-13 | Révision du contrat pour imprévision | Canal de Craponne (fiche, abandonné), Gaz de Bordeaux (sommaire) | Oui : « 6 mars 1876, Canal de Craponne » et « 30 mars 1916, Compagnie générale d'éclairage de Bordeaux » | Non : le droit positif est l'article 1195 ; Canal de Craponne est présenté comme le refus d'autrefois (« historiquement », « a autrefois refusé »), limité aux contrats antérieurs au 1er octobre 2016 | Non |

Bilan : arrêt attendu cité avec sa date et son nom dans 3 cas sur 4 (gan-06 non) ; aucun arrêt abandonné présenté
comme droit positif ; aucune fiche présentée comme une décision officielle.

## Défauts relevés (aucune correction appliquée)

1. **Grands arrêts cités en source sans être nommés (gan-06).** Le modèle s'appuie sur Costa, Simmenthal et Jacques
   Vabre mais n'écrit ni leur nom ni leur date : l'étudiant ne voit le nom qu'en ouvrant la source. Correction
   proposée : renforcer la note de `api/grands_arrets.note` (« chaque fois que tu cites un grand arrêt dans
   « sources », écris dans le texte sa juridiction, sa date et son nom d'usage »), puis mesurer sur gan-06 et deux
   autres cas ; un contrôle automatique (signaler dans `points_incertains` un grand arrêt cité sans son nom) est
   possible mais plus lourd.
2. **Droit positif fondé sur une seule fiche Lexia (gan-01).** « La garde est caractérisée par les pouvoirs d'usage,
   de direction et de contrôle » cite uniquement la fiche Franck. La règle est exacte, mais une fiche non officielle
   ne devrait pas être la seule source d'un élément de droit positif (la consigne le demande déjà). Correction
   proposée : dans `grands_arrets.ecarter_abandonnes` (ou une fonction voisine), faire passer dans l'explication
   tout élément de droit positif dont les sources sont toutes des fiches Lexia, comme pour les arrêts abandonnés,
   avec un test.

Non vérifié : les 16 autres cas du jeu, le modèle de secours (Groq absent en local), la relecture juridique des
réponses par un enseignant.
