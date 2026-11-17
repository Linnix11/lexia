# Backtest de la recherche - 2026-11-17 11:04

cas_pratiques_controle3.yaml : 15 cas au total, dont 15 attendent une source. Sans reformulation par Gemini ; embeddings, reclassement et lexique actifs. Temps moyen de recherche : 1.5 s.

| Groupe | Cas | Source parmi les 8 extraits (Gemini) | Source parmi les 4 premiers (Groq) |
|---|---|---|---|
| droit_administratif | 1 | 1/1 (100 %) | 1/1 (100 %) |
| droit_civil | 2 | 2/2 (100 %) | 2/2 (100 %) |
| droit_de_la_famille | 1 | 1/1 (100 %) | 1/1 (100 %) |
| droit_des_biens | 2 | 2/2 (100 %) | 2/2 (100 %) |
| droit_des_contrats | 4 | 4/4 (100 %) | 3/4 (75 %) |
| droit_penal | 3 | 3/3 (100 %) | 3/3 (100 %) |
| droit_social | 2 | 2/2 (100 %) | 2/2 (100 %) |
| **Total** | 15 | **15/15 (100 %)** | **14/15 (93 %)** |

## Cas à examiner

| Cas | Question | Source attendue | Dans les 8 | Dans les 4 | Premiers extraits fournis |
|---|---|---|---|---|---|
| ctl3-03 | Un antiquaire achète à une vieille dame un tableau pour 200 euros alors qu’il sait qu’il en vaut 50 000. La vente peut-elle être annulée ? | code_civil:1137, code_civil:1112-1 | oui | **non** | civil:1115, civil:1116, civil:1644, civil:1112-1, judilibre:1-4, judilibre:déc. |
