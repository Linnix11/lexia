# Backtest de la recherche - 2026-11-17 11:14

cas_grands_arrets.yaml : 12 cas au total, dont 12 attendent une source. Sans reformulation par Gemini ; embeddings, reclassement et lexique actifs. Temps moyen de recherche : 2.8 s.

| Groupe | Cas | Source parmi les 8 extraits (Gemini) | Source parmi les 4 premiers (Groq) |
|---|---|---|---|
| droit_civil | 8 | 7/8 (88 %) | 7/8 (88 %) |
| droit_des_contrats | 3 | 3/3 (100 %) | 2/3 (67 %) |
| toutes matières | 1 | 1/1 (100 %) | 1/1 (100 %) |
| **Total** | 12 | **11/12 (92 %)** | **10/12 (83 %)** |

## Cas à examiner

| Cas | Question | Source attendue | Dans les 8 | Dans les 4 | Premiers extraits fournis |
|---|---|---|---|---|---|
| ga-04 | Les parents peuvent-ils s'exonérer de leur responsabilité du fait de leur enfant mineur en prouvant qu'ils n'ont commis aucune faute ? | cass:94-21111 | **non** | **non** | civil:1242, civil:373-2-11, civil:372-1, civil:376-1, judilibre:25-29, judilibre:déc. |
| ga-06 | Une clause limitative de responsabilité qui contredit l'obligation essentielle du contrat est-elle valable ? | cass:93-18632 | oui | **non** | civil:1170, civil:1245-14, civil:1792-5, civil:1186, cass_commerciale:déc., cass_commerciale:déc. |
