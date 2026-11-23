# Corrections de la recette du 23 novembre 2026 : mesures (D122)

Conditions : Mac, index du 17 novembre, modèles de la configuration locale (`intfloat/multilingual-e5-base`,
`antoinelouis/crossencoder-camembert-base-mmarcoFR`). Aucune API payante. Rien n'a été mesuré sur le VPS.

## R-1. Accident de la circulation : loi n° 85-677 du 5 juillet 1985

Avant (sonde sur le code de `main`, cas de la recette, matière « Droit civil ») : extraits 1240, 1241, L421-12 du
Code des assurances, L621-9 du Code de la consommation et quatre sommaires de la Cour de cassation ; aucun article
de la loi de 1985.

Après : le lexique propose les articles 1er, 3 et 2 de la loi (par identifiant LEGIARTI : des milliers de lois ont un
« article 1 ») et une note dit au modèle de vérifier ce régime spécial avant les articles 1240 à 1242, la note
« garde de la chose » n'étant plus ajoutée quand un véhicule à moteur cause le dommage.

| Mesure | Résultat |
|---|---|
| Banc de recherche des cas pratiques (`backtest-recherche-20261123-1814.md`), 37 cas dont `cp-35` à `cp-37` | 37/37 dans les 8 extraits et dans les 4 du secours |
| Cas des jeux d’évaluation (417) dont les suggestions changent | `cp-35`, `cp-36`, `cp-37` seulement (`tests/test_accident_circulation.py`) |
| Garde de la chose hors véhicule (D119) | prompts et suggestions de `cp-01`, `cp-02`, `cp-33`, `cp-34` identiques ; 1242 toujours fourni |
| Faux positifs écartés | voiture abîmée (`cp-06`, `cp-34`), cycliste (`cp-04`), vente d'une voiture, question pénale (`ctl4-11`) |

**Non vérifié : les réponses du modèle.** Les deux exécutions de `eval/run.py` sur `cp-01`, `cp-02`, `cp-33`,
`cp-34` et `cp-35` à `cp-37` ont échoué en entier (quota gratuit de Gemini épuisé, 429 sur les trois modèles ;
pas de clé Groq dans la configuration locale). À relancer, puis `python eval/responsables.py <fichiers>` (colonne
« Loi de 1985 »).

## Question 5 du dossier enseignant : conditions de fond du mariage

Cause : aucune entrée du lexique pour les conditions de fond du mariage ; la reformulation avait proposé 144, 148, 161
et 184, jamais l'article 143 ; parmi les extraits, Civ. 1re, 13 mars 2007, n° 05-16.627 (mariage de Bègles, antérieur
à la loi du 17 mai 2013). La réponse donnait, de mémoire, « l'exigence de la différence de sexe » comme condition.

Correction : entrée du lexique (143, 146, 144, 147), hors questions internationales, et note au modèle quand
l'article 143 actuel est fourni. Cas `fam-06` ajouté (`eval/cas_matieres_licence.yaml`). Suggestions changées dans
les jeux : `intro-25`, `intro-26`, `fam-06` seulement ; `ti-06` (loi applicable) inchangé. Réponse du modèle non
vérifiée (même quota).

## R-2. Première question après un redémarrage

Sonde : processus neuf, puis trois questions (cas de la recette, cas d'un automobiliste, cas `cp-33`), deux fois
chacun. 2 fils de calcul.

| | Première question | dont vectorielle | Questions suivantes |
|---|---|---|---|
| Sans amorce (1) | 6,0 s | 3 535 ms | 2,0 s ; 1,0 s |
| Sans amorce (2) | 6,6 s | 4 072 ms | 1,1 s ; 0,8 s |
| Avec amorce (1) | 1,2 s | 117 ms | 2,8 s ; 1,6 s (évaluation en parallèle) |
| Avec amorce (2) | 0,9 s | 81 ms | 0,9 s ; 0,7 s |

L'amorce elle-même dure 6,9 à 7,1 s (vectorielle 3,7 à 4,0 s, plein texte 1,2 s, reclassement 0,6 à 0,8 s), dans un
fil à part : le service répond pendant ce temps. Sur le VPS, la recette mesurait 17 s de vectorielle à la première
question et 753 ms ensuite ; l'effet attendu y est donc plus grand, mais il n'est pas mesuré. Après publication :
`curl -s http://127.0.0.1:8000/api/sante` sur le serveur donne `amorce.etat` et `amorce.etapes_ms`.

Mémoire : les vecteurs restent en mémoire mappée. L'amorce lit les mêmes pages que la première question lisait déjà ;
ce sont des pages de cache de fichier, que le noyau peut reprendre sous `MemoryHigh`. Aucune mémoire de plus qu'après
la première question d'aujourd'hui.

## R-3. Reclassement

`eval/reclassement.py` : pipeline réel de la recherche, sans reformulation, reclassement forcé sur le processeur (le
premier passage avait pris le GPU du Mac, sans rapport avec le VPS) et 2 fils de calcul. 257 cas de `cas.yaml`,
`cas_pratiques.yaml`, `cas_pratiques_controle.yaml` et `cas_pratiques_controle2.yaml`.

| Réglage (candidats par groupe / jetons) | Dans les 8 | Dans les 4 | Reclassement moyen | 90e centile |
|---|---|---|---|---|
| 10 / 256, passage 1 (processeur) | 257/257 | 255/257 | 978 ms | 1 181 ms |
| 8 / 256, passage 1 (processeur) | 257/257 | 255/257 | 696 ms (-29 %) | 867 ms |
| 10 / 256, passage 2 (processeur) | 257/257 | 255/257 | 836 ms | 1 012 ms |
| 8 / 256, passage 2 (processeur) | 257/257 | 255/257 | 681 ms (-19 %) | 841 ms |
| 10 / 256, passage 3 (processeur) | 257/257 | 255/257 | 854 ms | 1 016 ms |
| 8 / 256, passage 3 (processeur) | 257/257 | 255/257 | 679 ms (-20 %) | 828 ms |

Passage 3 (`reclassement-20261123-1943.md`) : avec 8 candidats, **88 cas sur 257 seulement gardent les mêmes 8
extraits** que le réglage actuel. L'indicateur ne regarde qu'une source attendue par cas : il ne dit pas si les
extraits remplacés étaient utiles.

Écartés, d'après le premier passage (GPU du Mac, 254 cas : seule la qualité compte) : 192 jetons (252/254 dans les 4
au lieu de 253), 128 jetons (251/254), 6 candidats (253/254 dans les 8). La quantification int8 dynamique a échoué
sur ce modèle (erreur de PyTorch au moment de quantifier puis d'exécuter) ; sa vitesse sur le Mac (moteur ARM) ne
dirait de toute façon rien du VPS (moteur x86) : à essayer sur le VPS si le gain de 8 candidats ne suffit pas.

**Rien n'est appliqué** : 8 candidats changeraient les extraits de deux réponses sur trois, et la qualité des
réponses n'a pas pu être évaluée (quota Gemini épuisé). Proposition : évaluer les réponses de 8 contre 10 candidats
sur un jeu (par exemple `eval/cas_pratiques.yaml`) quand le quota le permet, puis passer `N_RECLASSEMENT` à 8 si les
indicateurs ne baissent pas. Gain attendu sur le VPS : environ 20 % des 4 à 7 s de la recette, soit 0,8 à 1,4 s par
question, non mesuré. L'amorce (R-2) supprime aussi le surcoût du premier reclassement après une publication.

## Constats du dossier enseignant (questions 6, 12, 22, 23, 25)

| Question | Cause trouvée | Correction | Vérifié |
|---|---|---|---|
| 25 (jurisprudence source du droit) | Articles 1100 à 1100-2 (sources des obligations) remontés par le mot « source » | Écartés quand la question ne parle ni d'obligation ni d'acte ou de fait juridique ; article 4 ajouté au lexique | Recherche sur l'index réel : 5 et 4 fournis, ni 1100 ni 1100-1 ni 1100-2 ; cas `intro-41` |
| 12 (autorité de la chose jugée) | Le Code civil n'était pas une source de la procédure civile : l'article 1355 proposé par le lexique était refusé | `procedure_civile` ajoutée aux matières du Code civil (`registry/sources.yaml`) | 1355 fourni ; cas `proc-06` |
| 6 (usufruit) | Le lexique ne proposait que l'article 578 | 578, 582, 605, 617 | Les quatre fournis ; cas `bie-06` |
| 5 (mariage, suite) | 146 et 147 absents ; 148 mis en avant | 143, 146, 144, 147 proposés ; note sur la dispense d'âge quand 148 est fourni | 143, 146, 147 fournis |
| 22 (fiche du fait des choses) | Seul 1242 proposé | 1242 et article 1er de la loi de 1985 | Suggestions ; grands arrêts : chantier à part |
| 23 (fiche du REP) | Les notions attendues (intérêt à agir, acte faisant grief, cas d'ouverture, Dame Lamotte) sont jurisprudentielles | Aucune : relève du chantier des grands arrêts | Non |

Cause commune : des articles centraux absents de la recherche (lexique incomplet, matière sans la bonne source), pas
le nombre d'extraits. Garder plus d'extraits pour une fiche ou un plan n'a pas été essayé : seule une évaluation des
réponses (impossible ce soir) pourrait le confirmer.

## Bancs de recherche après toutes les corrections

| Jeu | Dans les 8 | Dans les 4 du secours | Écarts |
|---|---|---|---|
| `cas.yaml` (190 cas avec source) | 190/190 | 188/190 | `intro-35` (déjà en échec le 18/11) ; `bie-06` exigeait 578, 582 et 617 ensemble, le secours n'a que trois textes : source attendue ramenée à 578 et 582 |
| `cas_matieres_licence.yaml` (52) | 52/52 | 51/52 | `pp-02` (déjà en échec le 18/11) |
| `cas_pratiques.yaml` (37) | 37/37 | 37/37 | aucun |
