# Lot sources de l'audit du 19 novembre : mesures avant et après (2026-11-20)

Recherche seule (`eval/backtest_recherche.py`), sans reformulation par Gemini : embeddings locaux
(`intfloat/multilingual-e5-base`), reclassement (`antoinelouis/crossencoder-camembert-base-mmarcoFR`), lexique.
Même index local pour les deux mesures (celui du 17 novembre, construit avant les traités de l'Union, D98 : d'où
9/20 sur `cas_traites.yaml`). « Avant » : code de main au commit b5304bd ; « après » : branche
`claude/sources-audit-2026-11-19`. Les deux mesures lisent les mêmes fichiers de cas (cas du tag et jeu réservé
compris). Entre parenthèses : source attendue parmi les 4 premiers extraits (modèle de secours).

| Jeu | Cas avec source | Avant | Après |
|---|---|---|---|
| cas.yaml (questions de cours) | 187 | 187 (185) | 187 (185) |
| cas_grands_arrets.yaml | 12 | 11 (10) | 11 (10) |
| cas_matieres_licence.yaml | 51 | 51 (50) | 51 (50) |
| cas_pratiques.yaml (avec cp-31 et cp-32, tag et graffitis) | 32 | 31 (31) | **32 (32)** |
| cas_pratiques_controle.yaml à controle4.yaml | 4 x 15 | 60 (60) | 60 (60) |
| cas_pratiques_reserve.yaml (nouveau, témoin, SRC-6) | 15 | 7 (6) | 7 (6) |
| cas_traites.yaml | 20 | 9 (9) | 9 (9) |

Échec corrigé : cp-32 (« Des adolescents ont fait des graffitis sur la façade de mon magasin... ») ramenait 2398,
377 et le Code de la santé publique ; il ramène 1242 et 1240. Formulation de l'audit (« Le fils de 15 ans des
voisins tague le garage ») : testée dans `tests/test_lexique_concordance.py`.

Jeu réservé : 7/15 sur des questions jamais vues, contre 100 % sur les jeux qui ont servi à régler le lexique. Les
8 échecs (coups et blessures, licenciement sans entretien, divorce par consentement mutuel, succession déficitaire,
prescription commerciale, vol, garde à vue dans les 4, rétractation en ligne, prescription civile) ne sont PAS
corrigés : la règle du fichier l'interdit, c'est le témoin des prochains réglages.

## Contrôle des citations (SRC-2)

Rejoué sur les réponses enregistrées (`eval/resultats/20261111-153059*.jsonl`, `reponse-directe-*.jsonl`) : 2 083
éléments déjà acceptés par l'ancien contrôle, avec les extraits réellement fournis relus dans l'index. Premier
passage : 1 retrait, un faux positif (const-10 : « articles 8 (1er alinéa), 11, 12, 16 » de l'article 19 de la
Constitution, liste coupée par la parenthèse), corrigé. Second passage : **0 retrait**. Aucune de ces réponses ne
contenait d'attribution au mauvais code ; les cas de l'audit (« article 9 du Code civil » contre « 9 juillet »,
« article 16 de la DDHC » contre « 16 octobre », « article 1240 du Code pénal » contre C. civ. 1240) sont retirés
(`tests/test_citations.py`, 17 cas).
