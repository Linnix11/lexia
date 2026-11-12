# Backtest de la recherche - 2026-11-12 20:07

200 cas au total, dont 172 attendent une source. Sans reformulation par Gemini ; embeddings, reclassement et lexique actifs. Temps moyen de recherche : 0.7 s.

| Groupe | Cas | Source parmi les 8 extraits (Gemini) | Source parmi les 4 premiers (Groq) |
|---|---|---|---|
| droit_administratif | 10 | 9/10 (90 %) | 9/10 (90 %) |
| droit_civil | 40 | 40/40 (100 %) | 40/40 (100 %) |
| droit_constitutionnel | 40 | 35/40 (88 %) | 30/40 (75 %) |
| droit_des_affaires | 5 | 5/5 (100 %) | 5/5 (100 %) |
| droit_des_contrats | 8 | 7/8 (88 %) | 7/8 (88 %) |
| droit_penal | 12 | 12/12 (100 %) | 12/12 (100 %) |
| droit_social | 10 | 9/10 (90 %) | 9/10 (90 %) |
| introduction_au_droit | 40 | 36/40 (90 %) | 35/40 (88 %) |
| piège : version | 2 | 2/2 (100 %) | 2/2 (100 %) |
| procedure_civile | 5 | 3/5 (60 %) | 3/5 (60 %) |
| **Total** | 172 | **158/172 (92 %)** | **152/172 (88 %)** |

## Cas à examiner

| Cas | Question | Source attendue | Dans les 8 | Dans les 4 | Premiers extraits fournis |
|---|---|---|---|---|---|
| intro-01 | Quand une loi entre-t-elle en vigueur ? | code_civil:1 | **non** | **non** | lois:99, lois:15, lois:16, lois:33, lois:3, lois:225 |
| intro-25 | Quelles sont les conditions d'âge pour se marier ? | code_civil:144 | **non** | **non** | civil:413-6, lois:41, civil:370-1, lois:6, lois:7, lois:45 |
| intro-27 | Qu'est-ce que la possession en droit des biens ? | code_civil:2255 | **non** | **non** | lois:L221-3, lois:L231-3, civil:1738, civil:544, lois:21 |
| intro-34 | Fais-moi une fiche sur les principes du droit des personnes | code_civil:16, code_civil:9, code_civil:16-1 | **non** | **non** | lois:6, lois:L213-2, lois:L213-3, lois:20, lois:23-4, lois:21 |
| intro-35 | Fais-moi une fiche sur la preuve en droit civil | code_civil:1353, code_civil:1358 | oui | **non** | civil:259, civil:1362, civil:259-1, civil:1381, civil:1361, civil:1358 |
| const-10 | Qu'est-ce que le contreseing ministériel ? | constitution:19 | **non** | **non** | lois:95, lois:12, lois:106, lois:1, decisions_conseil_constitutionnel:147-149, decisions_conseil_constitutionnel:déc. |
| const-12 | Un ministre peut-il être en même temps député ? | constitution:23 | **non** | **non** | electoral:R308, electoral:LO151-2, electoral:LO144, electoral:LO151-3, decisions_conseil_constitutionnel:31-33, decisions_conseil_constitutionnel:5-6 |
| const-13 | Quelle est la composition du Parlement ? | constitution:24 | **non** | **non** | lois:5, lois:6, constitution_1958:25, electoral:LO119, decisions_conseil_constitutionnel:1-2, decisions_conseil_constitutionnel:1-2 |
| const-18 | Qu'est-ce qu'une loi organique ? | constitution:46 | **non** | **non** | lois:11, lois:24, lois:5, lois:2, decisions_conseil_constitutionnel:déc., decisions_conseil_constitutionnel:déc. |
| const-21 | Quelle est la composition du Conseil constitutionnel ? | constitution:56 | **non** | **non** | lois:11, lois:13, lois:14, lois:10, decisions_conseil_constitutionnel:déc., decisions_conseil_constitutionnel:déc. |
| const-33 | Que dit la décision Liberté d'association du 16 juillet 1971 ? | cc:71-44 DC | oui | **non** | lois:4, lois:22, lois:7, lois:9, decisions_conseil_constitutionnel:1-3, decisions_conseil_constitutionnel:40 |
| const-34 | Le Conseil constitutionnel contrôle-t-il la conformité des lois aux traités ? (décision IVG de 1975) | cc:74-54 DC, constitution:55 | oui | **non** | constitution_1958:61, lois:22, lois:18, lois:17, decisions_conseil_constitutionnel:1-5, decisions_conseil_constitutionnel:1-5 |
| const-35 | Que juge la première décision QPC de 2010 sur la cristallisation des pensions ? | cc:2010-1 QPC | oui | **non** | constitution_1958:61-1, lois:16, lois:21 ter, lois:62, decisions_conseil_constitutionnel:4-6, decisions_conseil_constitutionnel:déc. |
| const-36 | Quelle valeur a la Charte de l'environnement selon le Conseil constitutionnel (décision OGM 2008) ? | cc:2008-564 DC | oui | **non** | lois:2, constitution_1958:déc., lois:12, lois:4, decisions_conseil_constitutionnel:18-19, decisions_conseil_constitutionnel:79-81 |
| const-37 | Qu'a décidé le Conseil constitutionnel sur la loi ouvrant le mariage aux couples de même sexe ? | cc:2013-669 DC | oui | **non** | lois:204, lois:105, lois:14, lois:5, decisions_conseil_constitutionnel:80, decisions_conseil_constitutionnel:9-11 |
| soc-10 | Un salarié gréviste peut-il être licencié ? | code_travail:L2511-1 | **non** | **non** | travail:L1132-2, lois:30 bis, travail:L1235-3-1, travail:L1233-61, cass_sociale:déc., cass_sociale:déc. |
| adm-01 | Dans quel délai former un recours contre une décision administrative ? | code_justice_administrative:R421-1 | **non** | **non** | justice_administrative:R421-2, justice_administrative:R821-1-1, relations_public_administration:L411-2, justice_administrative:R911-3, conseil_etat:2, conseil_etat:1 |
| ctr-03 | Qu'est-ce que le devoir précontractuel d'information ? | code_civil:1112-1 | **non** | **non** | consommation:D111-12, consommation:L131-1, consommation:L111-5, consommation:L131-1-1, cass_commerciale:déc., cass_commerciale:6-9 |
| proc-02 | Qu'est-ce que l'action en justice ? | code_procedure_civile:30 | **non** | **non** | procedure_civile:32-1, procedure_civile:1263-1, lois:13, lois:11, judilibre:déc., judilibre:déc. |
| proc-04 | Que doit contenir une assignation ? | code_procedure_civile:56 | **non** | **non** | procedure_civile:855, lois:157, lois:144, procedure_civile:665, judilibre:3, judilibre:déc. |
