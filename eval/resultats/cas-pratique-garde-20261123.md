# Cas pratique : garde de la chose (art. 1242 al. 1), mesure du 23 novembre 2026 (D119)

Suite de D115 : la responsabilité du gardien de la chose n'était développée dans aucun des 6 cas pratiques de
responsabilité (`cp-01`, `cp-02`, `cp-31` à `cp-34`), alors que l'article 1242 était fourni.

Conditions : Mac, index du 17 novembre, clé Gemini gratuite locale (`eval/run.py --fichier eval/cas_pratiques.yaml
--ids ...`), une réponse par cas et par exécution. Aucune API payante. Comptage par `eval/responsables.py`
(expressions), relu à la main pour `cp-01`, `cp-02`, `cp-33` et `cp-34`.

## Changements

1. Note au modèle (`api/prompts.py`, `note_garde`) en mode cas pratique, seulement quand les faits nomment une
   chose sans moteur dans un dommage (`api/lexique.py`, `chose_en_cause` : ballon, skate, vélo, pierre...) et que
   l'article 1242 est parmi les extraits. Même principe que la note des anciens numéros (D53).
2. Lexique : chose et dommage, sans âge dit, proposent 1242 et 1240 (« Léo brise la vitrine en jouant au ballon »
   ne recevait pas l'article 1242 à chaque exécution, donc pas la note).

## Effet sur les autres jeux

Sur les 413 cas des jeux d'évaluation (`eval/*.yaml`), la note ne s'ajoute qu'à `cp-01`, `cp-02`, `cp-33` et
`cp-34` (test `tests/test_cas_pratique_garde.py`) et l'entrée du lexique ne change les articles proposés que pour
`cp-01`. Pour tous les autres cas, recherche et prompt sont identiques : leurs résultats ne peuvent pas baisser
(hors hasard du modèle). Banc de recherche des cas pratiques : 34/34 avant (D115) et après
(`backtest-recherche-20261123-1131.md`), dans les 8 extraits et dans les 4 du secours.

## Résultats

| Exécution | 1240 et 1242 cités | Auteur traité | Parents traités | Gardien traité | Indicateurs des 4 autres cas |
|---|---|---|---|---|---|
| Avant (`20261123-111057-garde-avant`) | 5/6 | 4/6 | 6/6 | 0/6 | 4/4 |
| Note seule (`20261123-111911-garde-note-seule`) | 5/6 | 6/6 | 6/6 | 3/6 | 4/4 |
| Après, 1 (`20261123-113153-garde-apres-1`) | 6/6 | 6/6 | 6/6 | 4/6 | 4/4 |
| Après, 2 (`20261123-113712-garde-apres-2`) | 4/6 | 4/6 | 6/6 | 4/6 | 4/4 |

Gardien : 4/6 dans les deux exécutions finales, soit les 4 cas où une chose est en cause ; `cp-31` et `cp-32`
(tags, graffitis) n'en nomment pas. Avec la note seule, `cp-01` n'avait pas reçu l'article 1242 (pas d'âge dit,
reformulation différente) : d'où l'entrée du lexique. Les écarts de `cp-31` et `cp-32` pour l'auteur (4/6 contre
6/6) viennent du hasard : leur prompt est identique dans les trois exécutions.

Relecture à la main :
- `cp-33` et `cp-34` : garde développée dans la majeure (art. 1242 al. 1), la mineure (le mineur avait l'usage et
  le contrôle du ballon ou du skate, il en était gardien) et la conclusion (contre qui agir sur ce fondement).
- `cp-01` et `cp-02` : garde dans la majeure et la conclusion ; la mineure l'applique moins nettement (une
  exécution sur deux pour `cp-01`).

Remarque de fond, hors de ce changement : une réponse de `cp-33` subordonne la faute du mineur à son discernement
(« s'il est doté de discernement »), alors que la faute d'un enfant s'apprécie sans discernement depuis 1984
(Ass. plén., 9 mai 1984). À vérifier par un enseignant sur plus d'exécutions.
