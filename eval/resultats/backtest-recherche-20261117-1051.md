# Backtest de la recherche - 2026-11-17 10:51

cas_grands_arrets.yaml : 12 cas au total, dont 12 attendent une source. Sans reformulation par Gemini ; embeddings, reclassement et lexique actifs. Temps moyen de recherche : 9.9 s.

| Groupe | Cas | Source parmi les 8 extraits (Gemini) | Source parmi les 4 premiers (Groq) |
|---|---|---|---|
| droit_civil | 8 | 3/8 (38 %) | 2/8 (25 %) |
| droit_des_contrats | 3 | 2/3 (67 %) | 1/3 (33 %) |
| toutes matières | 1 | 1/1 (100 %) | 0/1 (0 %) |
| **Total** | 12 | **6/12 (50 %)** | **3/12 (25 %)** |

## Cas à examiner

| Cas | Question | Source attendue | Dans les 8 | Dans les 4 | Premiers extraits fournis |
|---|---|---|---|---|---|
| ga-01 | Que décide l'arrêt Blieck sur la responsabilité générale du fait d'autrui ? | cass:89-15231 | **non** | **non** | civil:1242, assurances:L175-11, assurances:L121-12, sante_publique:R4235-2, judilibre:déc., judilibre:déc. |
| ga-03 | Que juge l'arrêt Bertrand de 1997 sur la responsabilité des parents ? | cass:94-21111 | **non** | **non** | civil:371-5, civil:373-2-5, civil:373-2-11, civil:1242, judilibre:déc., judilibre:déc. |
| ga-04 | Les parents peuvent-ils s'exonérer de leur responsabilité du fait de leur enfant mineur en prouvant qu'ils n'ont commis aucune faute ? | cass:94-21111 | **non** | **non** | civil:1242, civil:373-2-11, civil:372-1, civil:376-1, judilibre:25-29, judilibre:déc. |
| ga-05 | Que décide l'arrêt Chronopost sur la clause limitative de responsabilité ? | cass:93-18632 | **non** | **non** | civil:1245-14, civil:1953, consommation:L512-55, civil:1792-5, cass_commerciale:déc., cass_commerciale:déc. |
| ga-06 | Une clause limitative de responsabilité qui contredit l'obligation essentielle du contrat est-elle valable ? | cass:93-18632 | oui | **non** | civil:1170, civil:1245-14, civil:1792-5, civil:1186, cass_commerciale:déc., cass_commerciale:déc. |
| ga-07 | Que juge l'arrêt Jacques Vabre de 1975 sur le traité et la loi postérieure ? | cass:73-13556 | oui | **non** | procedure_penale:695-55, penal:112-4, civil:2413, sante_publique:R4031-21, judilibre:déc., judilibre:déc. |
| ga-08 | Que décide l'arrêt Gabillet sur la garde d'une chose par un jeune enfant ? | cass:80-14994 | oui | **non** | sante_publique:D6124-177-63, sante_publique:D6124-177-65, sante_publique:D6124-177-66, sante_publique:R2111-1, judilibre:déc., judilibre:déc. |
| ga-09 | Que juge l'arrêt Fullenwarth sur la responsabilité des père et mère ? | cass:79-16612 | **non** | **non** | sante_publique:R3711-13, civil:373-1, civil:211, civil:373, judilibre:déc., judilibre:déc. |
| ga-10 | Faut-il qu'un enfant ait du discernement pour commettre une faute civile (arrêts Derguini et Lemaire) ? | cass:80-93481, cass:80-93031 | **non** | **non** | civil:388-1, civil:375-1, civil:1254, judilibre:déc., judilibre:déc., judilibre:déc. |
