# Backtest de la recherche - 2026-11-17 11:05

cas_pratiques_controle4.yaml : 15 cas au total, dont 15 attendent une source. Sans reformulation par Gemini ; embeddings, reclassement et lexique actifs. Temps moyen de recherche : 1.2 s.

| Groupe | Cas | Source parmi les 8 extraits (Gemini) | Source parmi les 4 premiers (Groq) |
|---|---|---|---|
| droit_administratif | 1 | 0/1 (0 %) | 0/1 (0 %) |
| droit_civil | 2 | 2/2 (100 %) | 2/2 (100 %) |
| droit_de_la_famille | 1 | 0/1 (0 %) | 0/1 (0 %) |
| droit_des_biens | 2 | 2/2 (100 %) | 2/2 (100 %) |
| droit_des_contrats | 4 | 3/4 (75 %) | 3/4 (75 %) |
| droit_penal | 3 | 1/3 (33 %) | 1/3 (33 %) |
| droit_social | 2 | 1/2 (50 %) | 1/2 (50 %) |
| **Total** | 15 | **9/15 (60 %)** | **9/15 (60 %)** |

## Cas à examiner

| Cas | Question | Source attendue | Dans les 8 | Dans les 4 | Premiers extraits fournis |
|---|---|---|---|---|---|
| ctl4-04 | La propriétaire d’un appartement loué ne fait rien malgré une fuite du toit qui inonde la chambre. Quelles sont ses obligations ? | code_civil:1719, code_civil:1720 | **non** | **non** | civil:1217, civil:1231-1, civil:1224, civil:1221, judilibre:10, judilibre:déc. |
| ctl4-07 | Une grand-mère ne peut plus voir ses petits-enfants depuis que sa fille s’est fâchée avec elle. Peut-elle agir ? | code_civil:371-4 | **non** | **non** | action_sociale_familles:R232-5, action_sociale_familles:L132-6, civil:373-2-10, judilibre:déc., judilibre:déc., judilibre:déc. |
| ctl4-10 | Un salarié emporte chez lui des ordinateurs de l’entreprise et les revend. Quelle infraction commet-il ? | code_penal:311-1, code_penal:314-1 | **non** | **non** | penal:323-3-1, penal:225-12-8, penal:R643-2, penal:R625-9, cass_criminelle:déc., cass_criminelle:déc. |
| ctl4-12 | Une femme se présente comme infirmière pour obtenir les codes de carte bancaire de personnes âgées. Qu’encourt-elle ? | code_penal:313-1 | **non** | **non** | procedure_penale:R15-33-68, procedure_penale:R49-17, penitentiaire:D216-19, penitentiaire:D216-20, cass_criminelle:déc., cass_criminelle:déc. |
| ctl4-14 | Un employeur refuse d’embaucher une candidate parce qu’elle porte le voile. Est-ce permis ? | code_travail:L1132-1 | **non** | **non** | travail:L1142-1, travail:L1225-1, travail:R6411-3, travail:L3132-25-4, cass_sociale:déc., cass_sociale:déc. |
| ctl4-15 | Une commune refuse un permis de construire sans donner la moindre raison. Le demandeur peut-il contester ? | code_relations_public_administration:L211-2, code_justice_administrative:R421-1 | **non** | **non** | urbanisme:L600-3, justice_administrative:L554-10, urbanisme:L431-6, urbanisme:L471-2, conseil_etat:déc., conseil_etat:déc. |
