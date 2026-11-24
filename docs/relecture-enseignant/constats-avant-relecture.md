# Constats avant relecture

Relecture interne des réponses de Lexia du 24 novembre 2026, après la correction D126 (moteur local, code
`60f0f03` : corrections de la recette D122, grands arrêts D124, notions manquantes et note sur l'article 61 D126),
faite avant l'envoi du dossier à l'enseignant. Ce document n'est pas destiné à l'enseignant : il liste ce qui
semble faux ou douteux, pour que l'éditeur décide de corriger Lexia avant l'envoi ou d'envoyer le dossier tel quel.

Les éléments de réponse attendus pour chaque question figurent dans `questions.json` (champ `attendu`). Les
versions précédentes de ce document (23 novembre, code `3353979`, 21 réponses ; 24 novembre matin, code `c9c92cd`,
30 réponses) restent lisibles dans l'historique git.

## 1. Bilan

| | 23 novembre | 24 novembre (`c9c92cd`) | 24 novembre (`60f0f03`) |
|---|---|---|---|
| Réponses obtenues | 21 sur 30 | 30 sur 30 | 30 sur 30, toutes par Gemini |
| Justes (souvent incomplètes) | 14 | 24 | **25** : 1 à 20, 22 à 25, 28 |
| Fausses | 2 (5, 25) | 1 (28) | **0** |
| Douteuses | 5 | 3 (21, 24, 26) | **3** : 21, 26, 29 |
| Abstentions correctes | | 2 | 2 : 27, 30 |

« Juste » veut dire : pas d'erreur de droit relevée et utilisable par un étudiant, même si la réponse est mince.
« Douteuse » : pas d'erreur nette, mais une réponse trop lacunaire, mal ciblée ou mal sourcée pour remplir son
office. « Fausse » : au moins une affirmation de droit inexacte.

Modèles : `gemini-3.5-flash-lite`, ou `gemini-flash-lite-latest` après un 503 du premier ; aucune erreur, aucune
réponse de Groq.

## 2. Ce que D126 a changé

| Q | Avant D126 | Après D126 |
|---|---|---|
| 4 | Juste, mince : 1240 et 1241 seulement | Juste : Derguini et Lemaire (Ass. plén., 9 mai 1984), faute de l'enfant sans discernement ; dommage et lien de causalité nommés |
| 13 | Juste, sans grand arrêt | Juste : Jand'heur (plein droit) et Franck (usage, direction, contrôle) dans la majeure ; Marc écarté, garde transférée à Paul |
| 17 | Juste, sans Benjamin, l'incompétence du maire mise en avant | Juste : Benjamin (mesures moins restrictives), interdiction générale et absolue illégale ; l'incompétence en police d'État reste présentée comme une hypothèse à vérifier |
| 24 | Douteuse : ni 1971 ni limites | Juste : Liberté d'association (16 juillet 1971) et bloc de constitutionnalité au I.A, QPC au I.B, lois référendaires (62-20 DC) et saisine au II. Manque la réforme de la saisine de 1974 |
| 28 | **Fausse** : « les lois ordinaires doivent être soumises » | Juste : le Conseil d'État ne contrôle pas la constitutionnalité des lois (loi-écran), il transmet les QPC et contrôle la conventionnalité (Nicolo) |

## 3. Les 30 réponses

| Q | Classement | Remarques |
|---|---|---|
| 1 | Juste | Art. 55, Jacques Vabre, Nicolo, décision IVG de 1975. Manque Sarran |
| 2 | Juste, mince | Art. 1128 ; ne dit toujours pas que la cause a disparu en 2016 |
| 3 | Juste | Art. 1195 ; Canal de Craponne présenté comme abandonné ; Gaz de Bordeaux |
| 4 | Juste | Voir section 2 |
| 5 | Juste | Art. 143, 144, 146, 147 ; arrêt de 2007 présenté comme abandonné. Met en avant la présence du Français à son mariage (art. 146-1), exacte mais secondaire ; manque la dispense d'âge (art. 145) |
| 6 | Juste | Art. 578, 582, 605, 617. Manquent l'inventaire et la caution (art. 600, 601) |
| 7 | Juste | Art. 61-1, les deux filtres (sérieux, puis nouvelle ou sérieuse), délai de trois mois, écrit distinct. Manque l'effet abrogatif |
| 8 | Juste, mince | Art. 19 seulement : pouvoirs propres énumérés par renvoi |
| 9 | Juste | Pelletier, Anguet, art. L. 134-2 et L. 134-3 CGFP ; manquent Lemonnier et Laruelle |
| 10 | Juste | Art. 111-2 à 111-4, non-rétroactivité ; manquent l'art. 8 DDHC et la rétroactivité in mitius |
| 11 | Juste | Art. 122-5 et 122-6 |
| 12 | Juste | Art. 1355 (triple identité), art. 480 CPC, Cesareo |
| 13 | Juste | Voir section 2 |
| 14 | Juste, mince | Vice du consentement et nullité relative (art. 1130, 1131), mais le dol n'est pas nommé ; manquent le délai de cinq ans et les dommages et intérêts |
| 15 | Juste | Art. 237 et 238 |
| 16 | Juste | Art. 671 à 673, option du propriétaire des arbres ; ne dit pas que la prescription trentenaire n'est pas acquise |
| 17 | Juste | Voir section 2. Recours pour excès de pouvoir seulement : le référé-liberté, cité le matin, n'apparaît plus |
| 18 | Juste, mince | Art. 311-1 seulement ; ni tentative, ni élément moral, ni peine |
| 19 | Juste | Art. 62-2, Ass. plén. 15 avril 2011, QPC du 18 novembre 2011 (aucune condamnation sur les seules déclarations sans avocat) ; manquent les art. 171 et 802 CPP |
| 20 | Juste | Art. 49 al. 3 |
| 21 | **Douteuse** | Voir section 4 |
| 22 | Juste | Jand'heur, Franck, instrument du dommage, cause étrangère, loi de 1985 |
| 23 | Juste | Dame Lamotte, R. 421-1, Danthony, Casanova ; manquent l'acte faisant grief et les cas d'ouverture |
| 24 | Juste | Voir section 2 |
| 25 | Juste | Art. 4 et 5, revirements (Civ. 1re, 9 oct. 2001), modulation (Ass. plén., 21 déc. 2006) |
| 26 | **Douteuse** | Voir section 4 |
| 27 | Abstention | Ne dit pas que le délit de racolage a été abrogé en 2016 |
| 28 | Juste | Voir section 2 |
| 29 | **Douteuse** | Voir section 4 |
| 30 | Abstention | Aucune invention sur le pourvoi inventé ; message générique |

## 4. Réponses douteuses

**Question 21 (fiche : force obligatoire du contrat).** Art. 1103, 1193, 1194 et 1195 justes, mais la
« jurisprudence clé » reste mal choisie : un arrêt sur une indemnité fixée à la cote Argus, et une décision
présentée comme interdisant de « remettre en cause la force obligatoire du contrat par des moyens omis », qui relève
de l'autorité de la chose jugée. Manquent la bonne foi (art. 1104), l'effet relatif (art. 1199) et les sanctions de
l'inexécution (art. 1217). Aucun grand arrêt n'est joint : la notion « force obligatoire » n'existe pas dans le
registre.

**Question 26 (piège : la cause à l'art. 1131).** Aucune invention : l'art. 1131 actuel porte sur la nullité
relative pour vice du consentement, et les conditions de validité sont celles de l'art. 1128. Mais la réponse ne
dit pas que la cause a disparu comme condition de validité en 2016, ni ne renvoie aux art. 1162 et 1169.

**Question 29 (hors champ : destitution du président des États-Unis).** Le matin, Lexia expliquait que le corpus
ne traite que de la destitution du président français (art. 68). Cette fois, la réponse dit bien que la procédure
américaine n'est pas couverte, mais elle remplit le droit positif avec une décision sur l'immunité de juridiction
d'anciens dirigeants américains devant le juge pénal français, sans rapport avec la question. Rien de faux, mais
hors sujet. Même code, même question : l'écart vient du modèle (réponses non déterministes).

## 5. Remarques transversales

1. **Grands arrêts.** Cités avec juridiction et date dans les questions 1, 3, 4, 9, 12, 13, 17, 22, 23, 24, 25 et
   28. Absents seulement là où le registre n'a pas de notion (force obligatoire, 21) ou n'en a pas besoin.
2. **Variabilité du modèle.** Entre les deux passages du 24 novembre, certaines réponses ont maigri sans changement
   de code (14 ne nomme plus le dol, 17 perd le référé-liberté, 18 perd la jurisprudence sur l'appréhension) et 29
   est devenue hors sujet. Un enseignant qui reposerait la même question pourrait obtenir une réponse différente.
3. **Réponses justes mais minces.** 2, 8, 14 et 18.
4. **Rubrique « Exceptions » remplie pour la forme.** Encore dans les questions 2, 4, 7, 8 et 10.
5. **Pièges.** Aucune invention (26 à 30). 27 et 30 donnent le message générique « Reformulez la question » ;
   26 ne corrige pas la prémisse.
6. **Fautes de frappe du modèle.** « par sa imprudence » (4), « corolaire » (10), « leur concordances » (25),
   « de de solides chances » (17), « consummation » (18).

## 6. Vérifications

- Cas de D122, 24 novembre matin (`eval/resultats/20261124-112817.jsonl`, `-113606.jsonl`, `-113714.jsonl`) :
  accidents de la circulation `cp-35` à `cp-37` (loi de 1985, 3/3), garde de la chose `cp-01`, `cp-02`, `cp-33`,
  `cp-34` (4/4), mariage `fam-06`, jurisprudence source du droit `intro-41`, autorité de la chose jugée `proc-06`,
  usufruit `bie-06` : tous justes.
- Après D126 (`eval/resultats/20261124-124728.jsonl`) : `cp-01`, `cp-02`, `cp-33`, `cp-34` toujours justes sur les
  quatre critères (1240 et 1242, auteur, parents, gardien), avec Jand'heur et Franck cités.

## 7. Ce qui reste à faire avant l'envoi

1. Publier sur le site la version `60f0f03` (ou la suivante) : le dossier décrit ce code, le site sert `c3e4b04`
   (sans D125 ni D126).
2. Décider si les questions 21, 26 et 29 justifient une correction avant l'envoi. Elles ne contiennent pas
   d'erreur ; 29 dépend du tirage du modèle.
3. Compléter les passages entre crochets de la lettre (`lettre.md`, puis régénérer `lettre.docx`) : signataire,
   contact, contrepartie, date de retour.
4. Ouvrir `dossier.docx` dans Word pour vérifier la mise en page avant impression (aucun rendu PDF n'a pu être
   fait ici, LibreOffice n'étant pas installé), et ouvrir `grille.xlsx` dans Excel : les moyennes s'y calculent à
   l'ouverture.

Si Lexia est encore corrigée : reposer toutes les questions
(`.venv/bin/python docs/relecture-enseignant/outils/interroger.py --pause 60`), mettre à jour `VERSION` dans
`outils/generer.py`, puis `python3 docs/relecture-enseignant/outils/generer.py`.
