# Cas pratique à plusieurs responsables : mesure du 23 novembre 2026 (D115)

Défaut relevé par la recette du 20 novembre (section 8) : « Paul, 17 ans, casse la vitre du voisin » ne traitait que
la responsabilité des parents (art. 1242 al. 4), pas celle du mineur lui-même (art. 1240) ni celle du gardien de la
chose (art. 1242 al. 1). Cas ajoutés : `cp-33` (l'énoncé de la recette) et `cp-34` (variante), avec `toutes: true`.

Conditions : Mac, index du 17 novembre, clé Gemini gratuite locale (`eval/run.py --fichier eval/cas_pratiques.yaml`),
une réponse par cas, donc une part de hasard d'une exécution à l'autre. Aucune API payante.

## Recherche (sans modèle de réponse)

`backtest-recherche-20261123-1015.md` : 34/34 cas pratiques, y compris dans les 4 premiers extraits ; 1240 et 1242
sont déjà fournis tous les deux pour `cp-33` et `cp-34`. Le défaut est dans la rédaction : la recherche n'est pas
modifiée, les autres jeux ne peuvent donc pas en être affectés.

## Réponses

Colonnes : articles cités ; « Auteur », « Gardien » : le texte de l'analyse (majeure, mineure, conclusion) traite la
responsabilité propre de l'auteur, celle du gardien de la chose (repérage par expressions, relu à la main pour
`cp-33` et `cp-34`).

| Exécution | 1240 et 1242 cités (6 cas de responsabilité) | Auteur traité | Parents traités | Gardien traité | Indicateurs automatiques (comportement, sources) des 4 autres cas |
|---|---|---|---|---|---|
| Avant (consigne d'origine) | 2/6 | 1/6 | 6/6 | 0/6 | 4/4 |
| Après (consigne retenue) | 4/6 | 3/6 (dont `cp-33` et `cp-34`) | 6/6 | 0/6 | 4/4 |
| Variante écartée (phrase sur la garde ajoutée) | 3/6 | 2/6 | 6/6 | 1/6 | 2/2 |

Consigne retenue (`api/prompts.py`, mode cas pratique) : examiner chaque fondement et chaque personne qui peut
répondre du dommage (l'auteur, celui qui répond de lui, le gardien de la chose), pour chacun la règle sourcée et son
application, conclusion qui dit contre qui agir. La variante qui ajoutait une phrase sur la garde d'une chose a fait
perdre l'article 1240 à `cp-33` : écartée.

Reste : la responsabilité du gardien de la chose n'est toujours pas développée (0/6), alors que l'article 1242
(alinéa 1 compris) est fourni. Piste non essayée : une note au modèle quand le lexique reconnaît une chose dans un
dommage, comme la note des anciens numéros (D53), à mesurer sur plusieurs exécutions.

## Détail par cas

## 20261123-101511-avant.jsonl
| Cas | Statut | Articles cites | 1240 et 1242 cites | Auteur (1240) | Parents (1242 al. 4) | Gardien (1242 al. 1) |
|---|---|---|---|---|---|---|
| cp-01 | reponse | 1240, 1241, 1242 | oui | non | oui | non |
| cp-02 | reponse | 1242 | non | non | oui | non |
| cp-31 | reponse | 1242 | non | non | oui | non |
| cp-32 | reponse | 1242, judilibre:JURITEXT000007048896:sommaire | non | non | oui | non |
| cp-33 | reponse | 1240, 1241, 1242 | oui | oui | oui | non |
| cp-34 | reponse | 1242, judilibre:JURITEXT000023607505:1 | non | non | oui | non |

## 20261123-101757-avant-autres.jsonl
| Cas | Statut | Articles cites | 1240 et 1242 cites | Auteur (1240) | Parents (1242 al. 4) | Gardien (1242 al. 1) |
|---|---|---|---|---|---|---|
| cp-08 | reponse | 1112-1, 1130, 1131, 1137, judilibre:JURITEXT000007044296:1 | non | non | non | non |
| cp-11 | reponse | 1217, 1221, 1224, 1231-1 | non | non | non | non |
| cp-13 | reponse | 1224, 1341, 1728, 1741 | non | non | non | non |
| cp-18 | reponse | 3-4, 371-2, 373-2-2, judilibre:JURITEXT000037676915:1 | non | non | oui | non |

## 20261123-101946-apres.jsonl
| Cas | Statut | Articles cites | 1240 et 1242 cites | Auteur (1240) | Parents (1242 al. 4) | Gardien (1242 al. 1) |
|---|---|---|---|---|---|---|
| cp-01 | reponse | 1240, 1241, 1242 | oui | oui | oui | non |
| cp-02 | reponse | 1242, 15-19, judilibre:JURITEXT000007071045:sommaire | non | non | oui | non |
| cp-31 | reponse | 1242 | non | non | oui | non |
| cp-32 | reponse | 1240, 1242, 20-24 | oui | non | oui | non |
| cp-33 | reponse | 1240, 1242 | oui | oui | oui | non |
| cp-34 | reponse | 1240, 1242 | oui | oui | oui | non |
| cp-08 | reponse | 1130, 1131, 1137 | non | non | non | non |
| cp-11 | reponse | 1217, 1221, 1231-1 | non | non | non | non |
| cp-13 | reponse | 1224, 1231-1, 1728, 1741 | non | non | non | non |
| cp-18 | reponse | 3-4, 371-2, 373-2-2 | non | non | oui | non |

## 20261123-102643-apres-variante-ecartee.jsonl
| Cas | Statut | Articles cites | 1240 et 1242 cites | Auteur (1240) | Parents (1242 al. 4) | Gardien (1242 al. 1) |
|---|---|---|---|---|---|---|
| cp-01 | reponse | 1240, 1241, 1242 | oui | oui | oui | non |
| cp-02 | reponse | 1242, 15-19, judilibre:JURITEXT000007043305:2, judilibre:JURITEXT000007048896:sommaire, judilibre:JURITEXT000007071045:sommaire | non | non | oui | non |
| cp-31 | reponse | 1240, 1242 | oui | non | oui | non |
| cp-32 | reponse | 1242, 20-24 | non | non | oui | non |
| cp-33 | reponse | 1241, 1242, judilibre:JURITEXT000007013643:sommaire, judilibre:JURITEXT000007051361:sommaire | non | non | oui | non |
| cp-34 | reponse | 1240, 1242 | oui | oui | oui | oui |
| cp-08 | reponse | 1130, 1131, 1137, 1641 | non | non | non | non |
| cp-13 | reponse | 1224, 1227, 1728, 1741, judilibre:JURITEXT000053679063:sommaire | non | non | non | non |

