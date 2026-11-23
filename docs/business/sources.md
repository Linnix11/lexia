# Sources des chiffres du business plan

Relevé du 23 novembre 2026. Chaque chiffre a été lu sur la page indiquée ce jour-là, sauf mention « non lu
directement » (page refusée aux robots, chiffre connu par une recherche). Les pages ont été lues par un outil qui
résume le contenu : les citations sont à revérifier avant tout usage contractuel. Les hypothèses sans source sont
listées en partie 6.

## 1. Marché

| Chiffre | Valeur | Observé ou projeté | Source | Lu directement |
|---|---|---|---|---|
| Étudiants en licence, discipline Droit, universités, 2025-2026 | 141 600 | Observé (colonne « Constat ») | Note Flash du SIES n° 25, octobre 2026, tableau des effectifs universitaires par cursus : https://www.enseignementsup-recherche.gouv.fr/sites/default/files/2026-10/2026_10_NF_SIES_25_projections.pdf | Oui |
| Même périmètre, 2026-2027 | 142 900 (+0,9 %) | Projeté | Même note | Oui |
| Même périmètre, 2027-2028 | 143 100 (+0,1 %) | Projeté | Même note | Oui |
| Droit, cursus master, 2025-2026 | 82 700 | Observé | Même note | Oui |
| Droit, doctorat, 2025-2026 | 5 000 | Observé | Même note | Oui |
| Étudiants du supérieur en France, 2025-2026 | 3 049 600 | Observé | Même note | Oui |
| L1 « Droit, sciences politiques », 2024-2025 | 66 079 (dont 61 351 en sciences juridiques) | Observé, somme calculée | Jeu SISE des effectifs, data.enseignementsup-recherche.gouv.fr, identifiant `fr-esr-sise-effectifs-d-etudiants-inscrits-esr-public` (API, regroupement par niveau) | Oui |
| L2 et L3 « Droit, sciences politiques », 2024-2025 | 37 812 et 31 498 | Observé, sommes calculées | Même jeu | Oui |

Limites : la note n° 25 ne dit pas si les sciences politiques sont comprises dans « Droit » ; le jeu SISE les
regroupe. Les établissements privés (instituts catholiques) et la capacité en droit ne sont pas comptés. La note
Flash n° 11 citée par le plan marketing renvoie une erreur 404 au 23 novembre 2026.

## 2. Coûts techniques

| Élément | Valeur | Source | Lu directement |
|---|---|---|---|
| Gemini 3.5 Flash-Lite, niveau payant | 0,30 $ entrée, 2,50 $ sortie par million de jetons (réflexion comprise) | https://aistudio.google.com/docs/pricing (l'ancienne adresse ai.google.dev/gemini-api/docs/pricing y redirige) | Oui |
| Gemini 3.8 Flash (secours) | 0,75 / 3,75 $ jusqu'au 31 décembre 2026, puis 1,50 / 7,50 $ au 1er janvier 2027 | Même page | Oui |
| Prépaiement minimum Gemini | 5 $ | https://aistudio.google.com/docs/billing | Oui |
| Groq `qwen/qwen3.8-27b` | 0,80 $ entrée, 4,00 $ sortie par million | https://console.groq.com/docs/models (groq.com/pricing n'affiche pas de prix) | Oui |
| Groq `openai/gpt-oss-120b` | 0,15 $ entrée, 0,60 $ sortie par million | Même page | Oui |
| Groq, niveau gratuit | Existe ; limites exactes non distinguées de celles du plan Developer | https://console.groq.com/docs/rate-limits | Oui, ambigu |
| Hostinger VPS KVM 2 (2 processeurs, 8 Go) | 7,79 €/mois en promotion sur 24 mois (186,96 € payés d'avance), renouvellement 14,99 €/mois ; TTC ou HT non précisé | https://www.hostinger.com/fr/vps-hosting | Oui |
| Domaine .cloud chez Hostinger | 1,99 € la première année, renouvellement 24,99 €/an | https://www.hostinger.com/fr/domaines | Oui |
| Resend | Gratuit : 100 e-mails par jour, 3 000 par mois ; Pro : 20 $/mois pour 50 000, sans limite quotidienne (relu le 23/11/2026) | https://resend.com/pricing | Oui |
| Stripe, cartes standard de l'EEE | 1,5 % + 0,25 € | https://stripe.com/fr/pricing | Oui |
| Stripe, cartes premium de l'EEE | 2,8 % + 0,25 € | Même page | Oui |
| Stripe, cartes hors EEE | 3,15 % + 0,25 € (+2 % en cas de conversion) | Même page | Oui |
| Stripe, litige | 20 € | Même page | Oui |
| Stripe Billing (abonnement récurrent) | 0,7 % du volume | Même page | Oui |
| Cloudflare | Free : 0 $ ; Pro : 20 $/mois (annuel) ou 25 $/mois | https://www.cloudflare.com/plans/network-cdn.md | Oui |
| Apple Developer Program | 99 $ par an (montant en euros affiché seulement à l'inscription) | https://developer.apple.com/programs/ | Oui |
| Commission App Store, Small Business Program | 15 % sous 1 million de dollars de revenus nets | https://developer.apple.com/app-store/small-business-program/ | Oui |
| Taux de change | 1,0968 $ pour 1 € le 18 novembre 2026 | Banque de France, parités quotidiennes : https://www.banque-france.fr/fr/statistiques/taux-et-cours/taux-de-change-parites-quotidiennes-2026-11-18 | Non lu directement (résultat de recherche) |

Mesure interne du coût par question : `logs/modele.jsonl` du Mac, 20 appels du 13 au 17 novembre 2026 (essais, pas
de trafic réel). Réponse : 2 036 jetons d'entrée et 538 de sortie en moyenne (12 appels, réflexion 0) ;
reformulation : 136 et 60 (8 appels). Recalculé le 23 novembre 2026, identique à `docs/avant-la-vente.md`. Part des
questions reformulées en ligne : 82 sur 111 (D88).

## 3. Statut, fiscalité, social

| Élément | Valeur | Source | Lu directement |
|---|---|---|---|
| Cotisations micro, prestations de services commerciales (BIC) | 21,2 % (22,9 % avec versement libératoire) | https://entreprendre.service-public.gouv.fr/vosdroits/F36232 (vérifiée au 1er janvier 2026) | Oui |
| Cotisations micro, libéral non réglementé (BNC, SSI) | 25,6 % (27,8 % avec versement libératoire) | Même page | Oui |
| Cotisations micro, CIPAV | 23,2 % (professions réglementées, hors sujet) | Même page | Oui |
| Taux BNC à 26,1 % | Cité par une recherche sur une page economie.gouv.fr | economie.gouv.fr (HTTP 403) | Non lu directement |
| Classement d'un abonnement à un logiciel en ligne (BIC ou BNC) | Aucune page officielle lue ne tranche | À faire confirmer par l'Urssaf | Non |
| Contribution à la formation professionnelle | 0,2 % (libéral), 0,1 % (commerçant) | https://entreprendre.service-public.gouv.fr/vosdroits/F23459 | Oui |
| Versement libératoire | 1,7 % (BIC services), 2,2 % (BNC) ; revenu fiscal de référence N-2 sous 29 579 € pour une personne seule ; option avant le 30 septembre de l'année précédente | https://entreprendre.service-public.gouv.fr/vosdroits/F23267 | Oui |
| Plafond micro, prestations de services | 83 600 € HT ; sortie après deux années consécutives de dépassement | Même page | Oui |
| ACRE | Taux minoré égal à 75 % du taux normal, conditions d'éligibilité limitées à des catégories listées | https://entreprendre.service-public.gouv.fr/vosdroits/F11677 | Oui (le calendrier du décret n° 2026-69 n'est pas lu directement) |
| Franchise en base de TVA, services | 37 500 € (année précédente) ; 41 250 € (perte immédiate en cours d'année) ; réforme du seuil unique de 25 000 € abandonnée | https://entreprendre.service-public.gouv.fr/vosdroits/F21746 | Oui |
| Mention sur facture | « TVA non applicable - article 293 B du CGI » | Même page | Oui |
| Services électroniques à des particuliers d'autres pays de l'UE | Seuil de 10 000 € HT ; au-delà, TVA du pays du client (guichet OSS facultatif) | https://www.impots.gouv.fr/professionnel/suis-je-concerne-0 | Oui |
| Impôt sur les sociétés | 25 % ; 15 % jusqu'à 42 500 € de bénéfice sous conditions (CA sous 10 M€, capital libéré et détenu à 75 % par des personnes physiques) | https://entreprendre.service-public.gouv.fr/vosdroits/F23575 | Oui |
| Prélèvement forfaitaire unique sur les dividendes, 2026 | 31,4 % (12,8 % d'impôt et 18,6 % de prélèvements sociaux) | https://entreprendre.service-public.gouv.fr/actualites/A18796 | Oui |
| Cotisations d'un président de SASU rémunéré | Environ 60 % de la rémunération brute, sans assurance chômage | https://entreprendre.service-public.gouv.fr/vosdroits/F23844 | Oui (ordre de grandeur) |
| Annonce légale de constitution d'une SASU | 142 € HT en métropole | https://entreprendre.service-public.gouv.fr/actualites/A18724 | Oui |
| Frais d'immatriculation d'une SASU (greffe) | Non chiffrés | https://www.inpi.fr/realiser-demarches/formalites-dentreprises/tarifs-formalites-dentreprises | Oui, sans montant |

## 4. Consommation et marque

| Élément | Valeur | Source | Lu directement |
|---|---|---|---|
| Obligation de désigner un médiateur de la consommation | Tout professionnel qui vend à des consommateurs | https://entreprendre.service-public.gouv.fr/vosdroits/F33338 | Oui |
| Amende administrative (C. consom. L. 641-1) | 3 000 € au plus pour une personne physique, 15 000 € pour une personne morale ; elle vise le manquement à l'information sur le médiateur (L. 616-1 et L. 616-2) | https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000032224624 | Oui |
| Médiateur SMP, vente en ligne, CA sous 60 000 € | 25 € HT pour 3 ans ; médiation 150 € HT (simple) ou 350 € HT (complexe), facturée si elle a lieu | https://www.mediateur-consommation-smp.fr/grille-tarifaire/ | Oui |
| Médiateur MCP | Vente en ligne sur devis (pas de prix public) | https://mcpmediation.org/nos-tarifs/ | Oui |
| Dépôt de marque INPI en ligne | 190 € la première classe, 40 € par classe supplémentaire | https://www.inpi.fr/realiser-demarches/propriete-intellectuelle/deposant-et-cout-dune-marque | Oui |
| Marques « LEXIA » antérieures | Voir `docs/marque-lexia.md` (relevé TMview du 17 novembre 2026) | TMview | Repris, non relu |

## 5. Concurrence

Repris de `docs/comparatif-notebooklm.md` (pages Google lues le 19 novembre 2026), non relu le 23 novembre :
Gemini Notebook gratuit ; Google AI Plus à 4,99 €/mois ; offre étudiante en France : AI Plus à 0 € pendant
12 mois, à prendre au plus tard le 31 décembre 2026, ou AI Pro à 5,49 €/mois pendant 4 ans au plus, pour les
étudiants majeurs vérifiés.

## 6. Hypothèses sans source

Toutes figurent sur fond orange dans `projections.xlsx`, feuille Hypothèses.

- Inscriptions organiques par mois (150, 400, 1 000 selon le scénario) et leur croissance annuelle.
- Saisonnalité des inscriptions (pics à la rentrée et aux partiels).
- Coût d'une inscription obtenue par la publicité (6 €, 4 €, 2,5 €).
- Taux d'abandon des comptes gratuits, conversion mensuelle vers le payant, part de l'Intensif, perte mensuelle des
  abonnés et perte supplémentaire en été.
- Nombre de questions par compte et par formule.
- Part des questions servies par les modèles de secours (5 % et 5 %) et appels annexes (+25 %).
- Durée moyenne achetée par paiement (2 mois).
- Assurance responsabilité civile professionnelle (25 €/mois), compte bancaire (5 €/mois), conseil en propriété
  industrielle (800 € HT), avocat (1 500 € HT).
- Part du marché disposée à payer un outil spécialisé (25 %, partie « Marché » du business plan).
- Mois d'activation du paiement et de publication de l'app iOS.
