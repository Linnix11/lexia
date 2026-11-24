# Constats avant relecture

Relecture interne des réponses de Lexia du 24 novembre 2026 (moteur local, code `c9c92cd` : corrections de la
recette D122, grands arrêts D124), faite avant l'envoi du dossier à l'enseignant. Ce document n'est pas destiné à
l'enseignant : il liste ce qui semble faux ou douteux, pour que l'éditeur décide de corriger Lexia avant l'envoi ou
d'envoyer le dossier tel quel. Le code de Lexia n'a pas été modifié.

Les éléments de réponse attendus pour chaque question figurent dans `questions.json` (champ `attendu`). La version
précédente de ce document (23 novembre, version `3353979`, 21 réponses) reste lisible dans l'historique git.

## 1. Bilan

| | Nombre | Questions |
|---|---|---|
| Réponses obtenues | 30 sur 30 | toutes par Gemini (`gemini-3.5-flash-lite`, ou `gemini-flash-lite-latest` après un 503) ; aucune par Groq |
| Justes (souvent incomplètes) | 24 | 1 à 20, 22, 23, 25, 29 |
| Fausses | 1 | 28 |
| Douteuses | 3 | 21, 24, 26 |
| Abstentions correctes | 2 | 27, 30 |

« Juste » veut dire : pas d'erreur de droit relevée et utilisable par un étudiant, même si la réponse est mince.
« Douteuse » : pas d'erreur nette, mais une réponse trop lacunaire, mal ciblée ou mal sourcée pour remplir son
office. « Fausse » : au moins une affirmation de droit inexacte.

Par rapport au 23 novembre : les deux réponses fausses (5 et 25) sont devenues justes, quatre des cinq douteuses
(6, 12, 22, 23) aussi, et les 9 réponses manquantes sont obtenues (7 justes, 2 douteuses). En revanche la
question 28, jugée juste le 23, contient maintenant une erreur.

## 2. Comparaison question par question

| Q | 23 novembre | 24 novembre | Ce qui a changé |
|---|---|---|---|
| 1 | Juste, mince | Juste | Jacques Vabre et Nicolo cités avec date ; Conseil constitutionnel incompétent pour la conventionnalité. Manque Sarran |
| 2 | Juste, mince | Juste, mince | Inchangé : art. 1128 ; ne dit pas que la cause a disparu en 2016 |
| 3 | Juste | Juste | Ajout de Canal de Craponne (présenté comme abandonné) et de Gaz de Bordeaux |
| 4 | Juste, mince | Juste, mince | Art. 1240 et 1241 ; ni dommage ni lien de causalité détaillés, pas de Derguini |
| 5 | **Fausse** | Juste | Art. 143, 144, 146, 147 ; l'arrêt de 2007 est présenté comme abandonné depuis la loi de 2013. Manquent la dispense d'âge (art. 145) et les empêchements de parenté |
| 6 | Douteuse | Juste | Art. 578, 582, 605, 617 ; plus de confusion sur le quasi-usufruit. Manquent l'inventaire et la caution (art. 600, 601) |
| 7 | Non obtenue | Juste | Art. 61-1 et conditions de l'art. 23-2. Manquent le second filtre (question nouvelle ou sérieuse), le délai de trois mois et l'effet abrogatif |
| 8 | Juste, mince | Juste, mince | Art. 19 seulement : les pouvoirs propres sont énumérés par renvoi, sans dire ce que sont les art. 8, 11, 12, 16 |
| 9 | Non obtenue | Juste | Pelletier et Anguet cités ; manquent Lemonnier et Laruelle |
| 10 | Non obtenue | Juste | Art. 111-2 à 111-4 ; manquent l'art. 8 DDHC et la rétroactivité in mitius (art. 112-1) |
| 11 | Juste | Juste | Complète : art. 122-5 et 122-6, proportionnalité |
| 12 | Douteuse | Juste | Triple identité de l'art. 1355 et Cesareo (2006) : le cœur de la question est maintenant traité |
| 13 | Non obtenue | Juste | Paul responsable sur 1240-1241 et comme gardien (art. 1242 al. 1 : usage, direction, contrôle), pas Marc. Jand'heur et Franck non nommés, exonération non traitée |
| 14 | Non obtenue | Juste | Dol, nullité relative (art. 1130, 1131), option indemnitaire. Manquent la définition du dol (art. 1137), le délai de cinq ans (art. 1144) et les restitutions |
| 15 | Juste | Juste | Art. 237 et 238, délai d'un an rempli |
| 16 | Juste | Juste | Art. 671 à 673 ; ne dit pas que la prescription trentenaire n'est pas acquise |
| 17 | Juste, sans référé | Juste | Référé-liberté (L. 521-2 CJA) et interdiction générale et absolue. Mais pas Benjamin, et l'argument mis en avant reste l'incompétence du maire en police d'État, simple hypothèse |
| 18 | Juste, mince | Juste, mince | Inchangé : appréhension caractérisée ; ni tentative, ni élément moral, ni peine |
| 19 | Non obtenue | Juste | Art. 63-3-1, Ass. plén. 15 avril 2011, QPC du 30 juillet 2010 ; manquent la nullité (art. 171 et 802 CPP) et le délai de deux heures |
| 20 | Non obtenue | Juste | Art. 49 al. 3 : un seul autre texte par session. Complète |
| 21 | Non obtenue | **Douteuse** | Voir section 4 |
| 22 | Douteuse | Juste | Teffaine, Jand'heur, Franck, cause étrangère, exclusion des accidents de la circulation (loi de 1985) |
| 23 | Douteuse | Juste | Dame Lamotte, délai de deux mois, Danthony, Casanova. Manquent l'acte faisant grief, les cas d'ouverture et les effets de l'annulation |
| 24 | Douteuse | **Douteuse** | Voir section 4 |
| 25 | **Fausse** | Juste | Plus de confusion avec l'art. 1100 : art. 4, 5, 1355, revirements (Civ. 1re, 9 oct. 2001) et modulation dans le temps (Ass. plén., 21 déc. 2006) |
| 26 | Non obtenue | **Douteuse** | Voir section 4 |
| 27 | Abstention | Abstention | Inchangé : ne dit pas que le délit de racolage a été abrogé en 2016 |
| 28 | Juste (abstention partielle) | **Fausse** | Voir section 3 |
| 29 | Juste | Juste | Explique que le corpus ne traite que la destitution du président français (art. 68) |
| 30 | Abstention | Abstention | Aucune invention sur le pourvoi inventé ; message générique |

## 3. Réponse fausse

**Question 28 (contrôle de constitutionnalité par le Conseil d'État, question piège).** La réponse rectifie
en partie la prémisse (le contrôle appartient au Conseil constitutionnel), mais la rubrique « Conditions » affirme
que « les lois ordinaires et organiques doivent être soumises au Conseil constitutionnel avant leur promulgation »,
et l'exemple dit qu'une loi votée « est transmise » au Conseil. C'est inexact : seules les lois organiques (avec les
propositions de l'art. 11 et les règlements des assemblées) sont soumises d'office ; les lois ordinaires ne le sont
que si une autorité de l'art. 61 al. 2 les défère. Rien non plus sur la loi-écran, ni sur le contrôle de
conventionnalité exercé par le Conseil d'État (Nicolo) : les grands arrêts joints à la question étaient des
décisions du Conseil constitutionnel.

## 4. Réponses douteuses

**Question 21 (fiche : force obligatoire du contrat).** Art. 1103, 1193, 1194 et 1195 justes, mais la
« jurisprudence clé » est mal choisie : un arrêt de 1985 sur l'application de la loi contractuelle et un arrêt du
28 mars 1995 présenté comme interdisant « de remettre en cause la force obligatoire du contrat par de nouveaux moyens
omis », qui relève en réalité de l'autorité de la chose jugée. Manquent la bonne foi (art. 1104, mentionnée dans la
réponse directe sans être sourcée), l'effet relatif (art. 1199) et les sanctions de l'inexécution (art. 1217).

**Question 24 (plan : le Conseil constitutionnel, gardien des droits et libertés ?).** Inchangé pour l'essentiel :
ni la décision Liberté d'association du 16 juillet 1971, ni la réforme de la saisine de 1974. Le II.B annonce
désormais des limites, mais vagues (« pouvoir d'appréciation du législateur »). Aucun grand arrêt n'a été joint
(`grands_arrets: 0`) : la question ne déclenche aucune notion du registre D124.

**Question 26 (piège : la cause à l'art. 1131).** Aucune invention : Lexia dit que l'art. 1131 actuel porte sur
la nullité relative pour vice du consentement. Mais elle ne dit pas que la cause a disparu comme condition de
validité en 2016, ni ne renvoie aux art. 1162 et 1169, ce qui était l'intérêt du piège. Quatre rubriques sur cinq
disent seulement que « les extraits ne permettent pas ».

## 5. Remarques transversales

1. **Grands arrêts.** Nette amélioration (D124) : Jacques Vabre et Nicolo (1), Canal de Craponne et Gaz de Bordeaux
   (3), Pelletier et Anguet (9), Cesareo (12), Teffaine, Jand'heur et Franck (22), Dame Lamotte et Danthony (23)
   sont cités avec juridiction et date. Restent absents Derguini (4), Benjamin (17), Liberté d'association (24), et
   Jand'heur et Franck dans le cas pratique 13. Dans ces quatre réponses, `grands_arrets` vaut 0 : les questions
   ne déclenchent aucune notion du registre (cas pratique sans les mots « fait des choses » ou « garde », police
   des manifestations, Conseil constitutionnel et libertés, faute de l'infans). C'est la piste de correction la
   plus rentable avant l'envoi.
2. **Réponses justes mais minces.** Questions 2, 4, 8 et 18 inchangées : un ou deux articles paraphrasés. La
   question 2 ne dit toujours pas que la cause a disparu en 2016.
3. **Rubrique « Exceptions » remplie pour la forme.** Encore dans les questions 2, 4, 7, 8 et 10 (« les extraits
   ne permettent pas ... »), parfois sans aucune source.
4. **Pièges.** Aucune invention (27, 28, 29, 30). Mais 27 et 30 donnent le message générique « Reformulez la
   question », 26 ne corrige pas la prémisse, et 28 rectifie la prémisse en ajoutant une erreur.
5. **Fautes de frappe du modèle.** « non dissout » pour « non dissous » (5), « corolaire » pour « corollaire » (10),
   « d' recevabilité » (23). Moins nombreuses que le 23 novembre.
6. **Disponibilité.** Gemini a répondu 503 sur son premier modèle pour 7 questions ; le second modèle a chaque fois
   pris le relais. Le matin même, la tâche programmée avait échoué (503 sur les trois modèles à 10 h 58). Groq
   n'est toujours pas configuré sur la machine locale.

## 6. Vérification des corrections de la recette (D122)

Le 24 novembre, `eval/run.py` sur les cas de D122 (`eval/resultats/20261124-112817.jsonl`, `-113606.jsonl`,
`-113714.jsonl`, synthèse par `eval/responsables.py`) :

| Cas | Attendu | Résultat |
|---|---|---|
| `cp-01`, `cp-02`, `cp-33`, `cp-34` (garde de la chose hors véhicule) | 1240 et 1242, auteur, parents, gardien | Juste (4/4) |
| `cp-35`, `cp-36`, `cp-37` (accident de la circulation) | Loi du 5 juillet 1985 appliquée, pas 1240 à 1242 | Juste (3/3) : articles 1er, 2 et 3 de la loi cités |
| `fam-06` (mariage) | 143, 144, 146, 147, pas de différence de sexe | Juste : l'arrêt de 2007 est présenté comme abandonné |
| `intro-41` (jurisprudence source du droit) | Art. 1100 non présenté comme source du droit | Juste : art. 4 et 5, ni 1100 ni 1100-1 |
| `proc-06` (autorité de la chose jugée) | Art. 1355 | Juste |
| `bie-06` (usufruit) | Droits et extinction | Juste : 578, 582, 605, 617 |

## 7. Ce qui reste à faire avant l'envoi

1. Décider s'il faut corriger avant l'envoi la question 28 (contrôle obligatoire des lois ordinaires) et les
   notions de grands arrêts manquantes (questions 4, 13, 17, 24). Si Lexia est corrigée, reposer toutes les
   questions (`.venv/bin/python docs/relecture-enseignant/outils/interroger.py --pause 60`, puis
   `python3 docs/relecture-enseignant/outils/generer.py`) pour que le dossier reflète la version évaluée, et
   mettre à jour `VERSION` et `DATE` dans `outils/generer.py`.
2. Le dossier décrit le code `c9c92cd`. Le site sert `c3e4b04` : les réponses sont les mêmes (D125, seule
   différence de code, ne touche que les adresses de l'espace étudiant).
3. Compléter les passages entre crochets de la lettre (`lettre.md`, puis régénérer `lettre.docx`) : signataire,
   contact, contrepartie, date de retour.
4. Ouvrir `dossier.docx` dans Word pour vérifier la mise en page avant impression (aucun rendu PDF n'a pu être
   fait ici, LibreOffice n'étant pas installé), et ouvrir `grille.xlsx` dans Excel : les moyennes s'y calculent à
   l'ouverture.
