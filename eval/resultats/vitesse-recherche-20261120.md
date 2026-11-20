# Vitesse de la recherche avant et après D114 (2026-11-20)

Audit du 19 novembre, constat SRV-7. Mesure sur le Mac (8 processeurs, numpy limité à 2 fils comme sur le VPS),
index du 17/11 (`data/index`, 637 869 vecteurs de 768 dimensions), par `eval/vitesse_recherche.py`.

Avant : `main` à 42a1cfe. Après : branche `claude/recherche-rapide`. Même machine, même index, l'un après l'autre.

## Méthode

Pipeline réel de la recherche (`Lexia.rechercher`), avec trois remplaçants déterministes, car les modèles
d'embedding et de reclassement ne sont pas sur le Mac et aucune API payante n'est appelée :

- vecteur de la question : moyenne des vecteurs des 3 premiers passages trouvés en plein texte (le parcours de
  l'index est le même qu'avec un vrai vecteur) ;
- reformulation : « notion juridique : » + la question (sa propre recherche plein texte et son propre vecteur) ;
- reclassement : ordre par longueur du texte (même chemin, articles de principe compris).

La reformulation est présente pour toutes les questions sans citation : c'est le cas le plus lourd, 4 parcours de
l'index par question avant la modification.

## Vitesse : 20 questions de `eval/cas.yaml`, 3 passages chacune (médiane par question), après un passage à vide

| Étape | Avant, médiane | Après, médiane | Avant, 90e centile | Après, 90e centile |
|---|---|---|---|---|
| Recherche vectorielle (parcours, sélection, lecture des passages) | 313,5 ms | 66,0 ms | 362,1 ms | 82,0 ms |
| Plein texte (inchangé) | 384,5 ms | 374,1 ms | 1 267,7 ms | 1 293,6 ms |
| Total, embedding factice compris | 955,1 ms | 721,8 ms | 2 215,6 ms | 1 952,3 ms |
| Total sans l'embedding factice | 664,2 ms | 456,7 ms | | |

Gain : la partie vectorielle passe de 313 à 66 ms par question (4,7 fois plus rapide, 247 ms de moins) ; la
recherche hors modèles baisse de 31 % en médiane. Le plein texte devient la plus grosse part.

Sur les 348 cas des jeux (un passage, sans passage à vide) : vectorielle 339,3 ms avant, 80,5 ms après en médiane.

## Mêmes résultats

- 20 questions : 20 listes de passages identiques, dans le même ordre.
- Jeux `cas.yaml`, `cas_pratiques_controle.yaml` à `cas_pratiques_controle4.yaml`, `cas_pratiques_reserve.yaml`,
  `cas_traites.yaml`, `cas_matieres_licence.yaml` : 348 cas, 348 listes identiques, 0 différence.
- `tests/test_recherche_rapide.py` : ancien et nouveau classement comparés sur un petit index (passages des
  fixtures et Constitution, vecteurs aléatoires), avec et sans reformulation, avec et sans reclassement, pour
  plusieurs jeux de sources : mêmes passages, mêmes scores, même ordre.

## Non mesuré ici

- Reclassement et embedding réels : modèles absents du Mac. Le sémaphore de 2 ne change pas la durée d'une
  question seule ; son effet (questions simultanées) se lira dans `recherche_detail.etapes_ms.reclassement` sur
  le serveur.
- Durée sur le VPS : les nouveaux champs du journal (`etapes_ms`, `generation_ms`) la donneront après publication.
