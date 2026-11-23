# Grands arrêts par notion (D124) : non-régression - 2026-11-23 21:17

420 cas de 12 jeux (`eval/*.yaml` sauf `cas_grands_arrets_notions.yaml`). Recherche de production sans reformulation par Gemini (embeddings, reclassement, lexique), faite deux fois par cas : sans puis avec les grands arrêts.

| Mesure | Résultat |
|---|---|
| Cas dont les extraits d'avant changent (ordre ou contenu) | 0 |
| Cas dont les extraits du secours changent (hors grand arrêt ajouté) | 0 |
| Source attendue dans les 8 (avant / après), 392 cas | 366 / 366 |
| Source attendue dans les 4 du secours (avant / après) | 362 / 362 |
| Cas qui reçoivent au moins un grand arrêt (ajouté ou signalé) | 46 |

Par jeu : cas.yaml 27, cas_grands_arrets.yaml 10, cas_matieres_licence.yaml 8, cas_traites.yaml 1

## Écarts

| Cas | Écart |
|---|---|
| aucun | |

## Cas qui reçoivent des grands arrêts

| Cas | Question | Ajoutés | Grands arrêts parmi les extraits |
|---|---|---|---|
| intro-22 | Qu'est-ce que la hiérarchie des normes ? | 3 | jacques-vabre, nicolo, cc-74-54-dc |
| intro-41 | Propose-moi un plan de dissertation sur le sujet : « La jurisprudence est-elle une source  | 2 | revirement-2001, revirement-2006 |
| const-23 | Qu'est-ce que la question prioritaire de constitutionnalité ? | 3 | cc-2009-595-dc, cc-2010-605-dc, cc-2010-14-qpc |
| const-33 | Que dit la décision Liberté d'association du 16 juillet 1971 ? | 0 | cc-71-44-dc |
| const-34 | Le Conseil constitutionnel contrôle-t-il la conformité des lois aux traités ? (décision IV | 0 | cc-74-54-dc |
| const-35 | Que juge la première décision QPC de 2010 sur la cristallisation des pensions ? | 3 | cc-2009-595-dc, cc-2010-605-dc, cc-2010-14-qpc |
| const-38 | Fais-moi une fiche sur le contrôle de constitutionnalité des lois | 3 | cc-71-44-dc, cc-62-20-dc, cc-85-197-dc |
| civ-04 | Quelle place tient la bonne foi dans les contrats ? | 2 | les-marechaux, huard |
| civ-05 | Peut-on rompre librement des négociations précontractuelles ? | 1 | manoukian |
| civ-06 | Qu'est-ce que le devoir d'information précontractuel ? | 2 | poussin, baldus |
| civ-10 | Qu'est-ce qu'un pacte de préférence ? | 0 | pacte-preference-2006 |
| civ-11 | Qu'est-ce qu'une promesse unilatérale de contrat ? | 1 | consorts-cruz |
| civ-19 | Qu'advient-il d'une clause qui prive de sa substance l'obligation essentielle du débiteur  | 2 | chronopost, faurecia |
| civ-24 | Qu'est-ce que la révision pour imprévision ? | 2 | canal-de-craponne, gaz-de-bordeaux |
| civ-25 | Qu'est-ce que l'effet relatif du contrat ? | 1 | boot-shop |
| civ-33 | Qu'est-ce que la responsabilité du fait des choses ? | 3 | jand-heur, franck, teffaine |
| civ-34 | Les parents sont-ils responsables des dommages causés par leurs enfants ? | 3 | bertrand, fullenwarth, levert |
| piege-17 | Comment fonctionne le recours pour excès de pouvoir devant le juge administratif ? | 3 | dame-lamotte, casanova, danthony |
| pen-02 | Qu'est-ce que l'état de nécessité en droit pénal ? | 1 | menard |
| pen-08 | Qui est considéré comme complice d'une infraction ? | 1 | lacour |
| adm-07 | L'administration peut-elle retirer une décision créatrice de droits ? | 1 | ternon, alitalia |
| ctr-02 | Qu'est-ce que la réticence dolosive ? | 2 | poussin, baldus |
| ctr-03 | Qu'est-ce que le devoir précontractuel d'information ? | 2 | poussin, baldus |
| ctr-06 | Qu'est-ce qu'un pacte de préférence ? | 0 | pacte-preference-2006 |
| ctr-07 | Qu'est-ce qu'une promesse unilatérale de contrat ? | 1 | consorts-cruz |
| proc-06 | Qu'est-ce que l'autorité de la chose jugée en matière civile et quelles sont ses condition | 1 | cesareo |
| lib-03 | Quels droits sociaux le préambule de 1946 garantit-il ? | 3 | cc-71-44-dc, cc-81-132-dc, kone |
| ga-01 | Que décide l'arrêt Blieck sur la responsabilité générale du fait d'autrui ? | 2 | blieck, bertrand, costedoat |
| ga-03 | Que juge l'arrêt Bertrand de 1997 sur la responsabilité des parents ? | 3 | bertrand, fullenwarth, levert, parents-2002 |
| ga-05 | Que décide l'arrêt Chronopost sur la clause limitative de responsabilité ? | 1 | chronopost, faurecia |
| ga-06 | Une clause limitative de responsabilité qui contredit l'obligation essentielle du contrat  | 0 | faurecia, chronopost |
| ga-07 | Que juge l'arrêt Jacques Vabre de 1975 sur le traité et la loi postérieure ? | 3 | jacques-vabre, nicolo, cc-74-54-dc, semoules |
| ga-08 | Que décide l'arrêt Gabillet sur la garde d'une chose par un jeune enfant ? | 3 | gabillet, jand-heur, franck, teffaine |
| ga-09 | Que juge l'arrêt Fullenwarth sur la responsabilité des père et mère ? | 3 | fullenwarth, bertrand, levert, parents-2002 |
| ga-10 | Faut-il qu'un enfant ait du discernement pour commettre une faute civile (arrêts Derguini  | 2 | derguini, lemaire, gabillet, trichard |
| ga-11 | Que décide l'arrêt Desmares de 1982 sur l'exonération partielle du gardien par la faute de | 0 | desmares, faute-victime-1987 |
| ga-12 | Que décide l'Assemblée plénière le 1er décembre 1995 sur la détermination du prix dans les | 0 | prix-1995 |
| pp-02 | Quels sont les droits de la personne placée en garde à vue ? | 2 | cc-2010-14-qpc, garde-a-vue-2011 |
| pp-12 | À partir de quel âge un mineur est-il pénalement responsable ? | 1 | laboube |
| dab-01 | Quels sont les critères du domaine public ? | 1 | le-beton |
| dab-02 | Pourquoi le domaine public est-il inaliénable ? | 1 | le-beton |
| dab-03 | Faut-il une autorisation pour occuper le domaine public ? | 1 | le-beton |
| dab-04 | L'occupation du domaine public est-elle gratuite ? | 1 | le-beton |
| dab-05 | Comment un bien sort-il du domaine public ? | 1 | le-beton |
| fam-06 | Quelles sont les conditions de fond du mariage en droit français ? | 1 | mariage-2007, mariage-2013 |
| ti-03 | Que se passe-t-il si un traité contient une clause contraire à la Constitution ? | 3 | sarran, fraisse, cc-92-308-dc |
