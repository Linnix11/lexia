# Décisions - Phase 0

Statut : **proposées, à valider**. Changer une ligne = noter la date et la raison en dessous du tableau.

| # | Sujet | Décision | Statut |
|---|---|---|---|
| D1 | Droit | Droit français | proposé |
| D2 | Niveau | L1 | proposé |
| D3 | Matières pilotes | Introduction au droit, Droit constitutionnel, Droit civil (contrats + responsabilité) | proposé |
| D4 | Sources officielles V1 | Constitution 1958, Code civil, décisions du Conseil constitutionnel, arrêts publiés de la Cour de cassation | proposé |
| D5 | Modèle | Gemini Flash via API Gemini Developer ; nom du modèle en variable `GEMINI_MODEL` | proposé |
| D6 | Données personnelles | Aucune en V1 : pas de compte, pas d'historique serveur, favoris en localStorage | proposé |
| D7 | Backend | Python + FastAPI | proposé |
| D8 | Base | PostgreSQL + pgvector + plein texte français (recherche hybride) | proposé |
| D9 | Front | Reprise de la maquette Lexia (`panel-ia-droit-v1.html`) en **Vite + React + TypeScript + Tailwind CSS** (décidé le 2026-11-11) | validé |
| D10 | Manuels | Métadonnées + liens uniquement ; aucun texte intégral sans licence écrite | proposé |
| D11 | Référent pédagogique | 1 enseignant ou chargé de TD, à trouver | ouvert |

## Source de la Constitution (phase 0)

Le texte est récupéré depuis la page officielle du Conseil constitutionnel (« Texte intégral de la Constitution du 4 octobre 1958 en vigueur »). Légifrance bloque les requêtes automatiques hors API : la bascule vers l'API Légifrance (PISTE) se fera en phase 1 quand les identifiants seront obtenus, pour harmoniser avec le Code civil.

## Phase 1 - choix retenus

| # | Sujet | Décision |
|---|---|---|
| D12 | Accès aux données | Archives open data DILA (LEGI, CONSTIT, CASS) au lieu de l'API PISTE : utilisables sans compte. PISTE reste une option pour les mises à jour fines. |
| D13 | Périmètre Conseil constitutionnel | Décisions DC et QPC uniquement (contentieux électoral exclu). |
| D14 | Périmètre Cour de cassation | Arrêts publiés depuis 2016 : 1re et 3e civ., Ass. plén., ch. mixte ; 2e civ. limitée à responsabilité / accidents / assurance / indemnisation. |
| D15 | Versions du Code civil | Toutes les versions d'articles sont conservées ; seules celles en vigueur sont vectorisées. |
| D16 | Embeddings | `gemini-embedding-2`, 768 dimensions, cache local par empreinte. |
| D17 | Modèle de génération | `gemini-3.8-flash` (nom vérifié dans la liste des modèles de l'API), configurable. |
| D18 | Base | PostgreSQL + pgvector hébergée par l'équipe (Hostinger) ; pas de Docker. |

## Phase 2 - choix retenus

| # | Sujet | Décision |
|---|---|---|
| D19 | Modèle de génération | `gemini-3.5-flash` (le plus rapide aux essais), secours `gemini-3.8-flash`, raisonnement `low`, délai 30 s. Remplace D17. |
| D20 | Recherche sans base | Index local SQLite FTS5 + numpy pour le développement ; même interface que PostgreSQL. |
| D21 | Recherche vectorielle | Utilisée seulement si au moins 90 % des passages concernés ont un embedding. |
| D22 | Contrôle des citations | Côté serveur, après le modèle : sources inconnues, affirmations non sourcées et numéros absents des extraits sont retirés. |
| D23 | Questionnaires | Réponses gardées en mémoire du serveur 3 h, jamais envoyées avant correction. |
| D24 | Retours | Utile oui / non + motif dans une liste fermée, pas de texte libre (aucune donnée personnelle). |

### Embeddings (tranché le 2026-11-11)

| # | Sujet | Décision |
|---|---|---|
| D25 | Modèle d'embeddings | Modèle open source local `intfloat/multilingual-e5-base` (MIT, 768 dimensions) à la place de Gemini, dont le niveau gratuit plafonne à 1 000 embeddings par jour. Remplace D16. Gemini reste disponible via `EMBED_PROVIDER=gemini`. |
| D26 | Calcul en production | Embeddings du corpus calculés hors serveur puis chargés en base ; le serveur ne vectorise que les questions. |

### Classement des résultats (2026-11-11)

Mesure sur 8 questions de cours (`eval/recherche.py`) : l'article de principe attendu figure-t-il parmi les extraits envoyés au modèle ?

| Configuration | Trouvés | Temps de recherche moyen |
|---|---|---|
| Hybride seul | 5/8 | 0,2 s |
| + reclassement | 7/8 | 2,5 s |
| + reformulation | 8/8 | 1,8 s (si Gemini répond) |

| # | Sujet | Décision |
|---|---|---|
| D27 | Reclassement | Cross-encoder local `antoinelouis/crossencoder-camembert-base-mmarcoFR` (MIT, français) sur les 30 meilleurs candidats. Comparé à `mmarco-mMiniLMv2` (plus rapide, moins bon) et `bge-reranker-v2-m3` (meilleur sur certains cas mais ~4x plus lent). `RERANK_MODEL` vide = désactivé. |
| D28 | Reformulation | `gemini-3.5-flash` reformule la question et propose au plus 4 articles ; seul leur texte officiel du corpus est utilisé. Une tentative, 8 s maximum, sinon recherche sans reformulation. Double l'usage du quota Gemini par question. `QUERY_EXPANSION_MODEL` vide = désactivé. |

### Phase 4 - évaluation (2026-11-11)

| # | Sujet | Décision |
|---|---|---|
| D29 | Modèles Gemini | Niveau gratuit de `gemini-3.5-flash` limité à 20 requêtes par jour (constaté) : génération et reformulation passées sur `gemini-3.5-flash-lite`, secours `gemini-flash-lite-latest` puis `gemini-3.8-flash`. Remplace D19. **Pour le pilote, passer au niveau payant** : le gratuit ne tient pas une journée de tests. |
| D30 | Modes méthode | En cas pratique, commentaire et dissertation, la méthode peut être expliquée sans extrait ; le droit positif exige toujours une source et les numéros inventés restent bloqués. |
| D31 | Jeu d'évaluation | 150 cas (`eval/cas.yaml`), brouillon à faire valider par l'enseignant référent (D11) avant toute conclusion. |

### Site et formules (2026-11-11)

| # | Sujet | Décision |
|---|---|---|
| D32 | Formules | Gratuit (compte requis) : 10 questions + 2 questionnaires par jour ; Étudiant 4,99 €/mois : 100 + 20 ; Intensif 9,99 €/mois : 300 + 100. Limites dans `api/plans.py`, remise à zéro à minuit (Paris). Une question n'est décomptée que si le modèle a répondu. |
| D33 | Paiement | Pas de paiement en ligne pour l'instant : formules payantes attribuées par l'administrateur (`python -m api.admin`), demande par e-mail (`CONTACT_EMAIL`). |
| D34 | Comptes | E-mail + mot de passe (scrypt), cookie de session HttpOnly / SameSite=Lax / Secure, contrôle de l'en-tête Origin, freins aux tentatives, suppression du compte en libre-service. Base SQLite `donnees/lexia.db`, jamais versionnée ni écrasée au déploiement. |
| D36 | Administration | Rôle admin (colonne `admin` ou `ADMIN_EMAILS`) et tableau de bord `/admin` : indicateurs, clients et formules, activité, état du serveur. Actions tracées dans `logs/admin.jsonl` ; aucun texte de question exposé. |
| D35 | Pages légales | Mentions légales, CGU, confidentialité : modèles à compléter ([À COMPLÉTER]) et à faire relire avant l'ouverture publique. |
| D37 | Corpus élargi | 24 codes (pénal, procédures, commerce, travail, sécurité sociale, justice administrative, CGCT, urbanisme...) depuis LEGI, une source par code ; lois, lois organiques et ordonnances en vigueur (source `lois`, versions en vigueur seulement). Identifiants LEGITEXT vérifiés dans l'archive. |
| D38 | Jurisprudence élargie | Cour de cassation : toutes les chambres, arrêts publiés depuis 2000, une source par chambre criminelle / sociale / commerciale (civiles, Assemblée plénière et chambre mixte restent `judilibre`). Conseil d'État et Tribunal des conflits (JADE) : recueil Lebon toutes années, tables depuis 2010. Sommaires découpés en blocs. Cours administratives d'appel et décisions non publiées exclues. |
| D39 | Références multi-codes | « article X du code Y » et abréviations usuelles (C. civ., C. pén., CPC, CGCT...) reconnus dans la question ; sans code nommé, ordre code civil, Constitution, code pénal, procédures ; filtrage par matière inchangé. Liste dans `api/textes.py`. |
| D40 | Annales | Catalogue de liens vers les sujets publiés par les facultés (métadonnées seulement, aucun sujet copié ni hébergé), géré par les administrateurs, affiché dans la Bibliothèque. |
| D41 | Index volumineux | Vecteurs chargés en mémoire mappée et construits par blocs float32 : environ 1,5 Go pour ~480 000 passages, compatible avec le VPS (7,8 Go). |
| D42 | Filtre par source dans l'index plein texte | La table FTS porte une colonne « source » et ne contient que les passages en vigueur : le filtre par matière se fait dans l'index, sans relire chaque passage. Recherche plein texte passée de 8-13 s à 0,2-0,3 s sur 667 000 passages. |
| D43 | Lois citées | « article 29 de la loi du 29 juillet 1881 » ou « loi n° 90-14 » : la loi est reconnue (numéro, date) et l'article cherché dans ce texte, jamais l'article homonyme d'un code. La recherche de version en vigueur reste dans le même texte (id_texte). |
| D44 | Pages légales configurables | Éditeur, adresse, SIREN, directeur de publication, médiateur et contact viennent du .env (LEGAL_*, CONTACT_EMAIL) ; un encart « à compléter » s'affiche tant qu'une valeur manque. Hébergeur vérifié sur les conditions Hostinger. Les conditions Gemini n'autorisent que le niveau payant pour des utilisateurs de l'EEE : GEMINI_NIVEAU_PAYANT=1 une fois la clé passée en payant. |
| D45 | Tâche quotidienne du serveur | /etc/cron.d/lexia (installé par publier.sh) : sauvegarde SQLite de la base des comptes (14 jours) et purge des journaux de plus de 12 mois. Sauvegardes sur le même disque : une copie hors serveur reste à prévoir. |
| D46 | Moteur de recherche | Index local SQLite FTS5 + numpy en développement comme en production. La variante PostgreSQL + pgvector (jamais utilisée ni testée) est supprimée. Remplace D8 et D18. |
| D47 | Reglage du reclassement | 10 candidats par groupe de sources, 256 jetons (au lieu de 30 / 512). Mesure sur le VPS (2 processeurs, 8 questions de `eval/recherche.py`) : avec reformulation, 7/8 dans tous les cas (sans reclassement, 10/256 ou 30/512) ; sans reformulation (Gemini indisponible), 3/8 sans reclassement, 5/8 en 10/256, 6/8 en 30/512. Temps de recherche moyen 4,0 s au lieu de 20,8 s. Complete D27. |
| D48 | Gemini sans clé payante | Un modèle en 503 / 429 n'est plus réessayé : bascule immédiate vers le suivant, puis un second tour. Reformulation lancée en parallèle de la vectorisation, plafonnée à `QUERY_EXPANSION_TIMEOUT` au total, et sautée quand la question cite un article, une décision ou un pourvoi. Réponses identiques (question normalisée, mode, matière, semestre) servies depuis un cache mémoire de 24 h (500 entrées), sans appel au modèle ; elles restent décomptées. |
| D49 | Semestres | Choix parmi les 6 semestres de licence (L1 S1-S2, L2 S3-S4, L3 S5-S6), gardé dans le navigateur, envoyé à l'API (`niveau`, `semestre`). La consigne du modèle (réponses et questionnaires) adapte le niveau d'explication à l'année. Les matières ne sont pas filtrées par semestre : les programmes varient selon les facultés. |
| D50 | Conformité du site | Mention claire de l'IA (AI Act, art. 50, applicable depuis le 2 août 2026) dans le chat et chaque réponse ; téléphone de l'hébergeur (LCEN art. 1-1 4°, `LEGAL_HEBERGEUR_TELEPHONE`) ; prix TTC et mention TVA (`LEGAL_TVA`) ; CGV des formules payantes (souscription par écrit, sans reconduction, rétractation 14 jours, L. 221-18 et L. 221-25) ; politique de confidentialité complétée (journaux nginx 14 jours, cache mémoire 24 h, stockage local, destinataires, directives post-mortem) ; licence Ouverte des données DILA vérifiée ; interdiction de réidentification. Restent bloquants hors code : clé Gemini payante (conditions du 23 mars 2026 : niveau gratuit interdit pour des utilisateurs de l'EEE), médiateur de la consommation, téléphone de l'hébergeur, mention TVA, relecture par un juriste. |
| D51 | Modèle de secours | Groq (`openai/gpt-oss-120b`, API compatible OpenAI, sortie JSON par schéma) appelé seulement si tous les modèles Gemini échouent, avec 4 extraits au lieu de 8 (quota gratuit d'environ 8 000 jetons par minute). Groq ne conserve pas les données par défaut (journaux de sécurité 30 jours au plus), stockage aux États-Unis : mentionné dans la politique de confidentialité quand `GROQ_API_KEY` est renseignée. Conditions d'usage commercial de l'offre gratuite à vérifier. |
| D58 | Bascule plus rapide vers Groq | Quand `GROQ_API_KEY` est renseignée : un seul tour des modèles Gemini, borné à `BUDGET_AVANT_SECOURS_SECONDES` (35 s par défaut) au total, puis Groq. Constaté en ligne le 2026-11-12 : six 503 Gemini d'affilée ont coûté 74 s avant que Groq réponde en 3 s. 35 s laissent passer une réponse Gemini lente mais réussie (environ 25 s constatées). Sans Groq, comportement inchangé (deux tours, sans limite globale). |
| D62 | Disjoncteur | Après 3 échecs de Gemini d'affilée (`DISJONCTEUR_SEUIL`), Groq répond seul pendant 5 minutes (`DISJONCTEUR_PAUSE_SECONDES`), reformulation comprise désactivée ; à la fin de la pause, un essai Gemini est refait et un nouvel échec rouvre aussitôt le disjoncteur. Constaté le 2026-11-12 : Gemini saturé à presque chaque question, chacune attendait 35 s avant Groq. État visible dans `/api/sante`. |
| D63 | Backtest de la recherche (200 cas) | Jeu d'évaluation porté à 200 cas (+50 : pénal, social, administratif, contrats, affaires, procédure civile ; sources vérifiées dans l'index) et `eval/backtest_recherche.py` (recherche seule, sans Gemini). Corrections tirées du backtest : lois non codifiées après les codes et la Constitution ; le secours reçoit 3 textes et la meilleure décision au lieu des 4 premiers textes ; lexique complété (contreseing, art. 23, 24, 46, 56 de la Constitution, procédure civile, formulations « gréviste », « devoir précontractuel d'information », « délai de recours »). Résultat sur les 172 cas avec source : 172/172 parmi les 8 extraits (Gemini), 169/172 parmi les 4 de Groq (au départ : 158 et 152). |
| D64 | Audit de sécurité du 2026-11-13 | Serveur : SSH par clé seulement (`/etc/ssh/sshd_config.d/00-lexia-securite.conf`, root sans mot de passe, X11 coupé), pare-feu ufw (22, 80, 443), fail2ban ; n8n publié sur 127.0.0.1:32768 seulement (accessible en HTTPS via nginx) ; en-têtes HSTS, CSP `frame-ancestors`, X-Frame-Options, Permissions-Policy, `server_tokens off`. Code : fichier Word refusé au-delà de 10 Mo décompressés (un .docx de 0,29 Mo occupait 1,2 Go), PDF limités à 1 000 pages et lus en s'arrêtant au million de caractères, 20 dépôts de cours par compte sur 24 h, documentation de l'API désactivée hors `API_DOCS=1`. |
| D65 | Nouvelles sources et matières | Ajout de la Déclaration des droits de l'homme de 1789 et du Préambule de 1946 (textes non codifiés de l'archive LEGI), du Code général des impôts, du Livre des procédures fiscales, du Code des juridictions financières, du Code de la sécurité intérieure, du Code de l'action sociale et des familles, du Code pénitentiaire et du Code de l'expropriation. Nouvelles matières : libertés fondamentales, droit fiscal, finances publiques, droit de la famille, droit des biens (14 au total). Index : 719 398 passages, 506 656 embeddings. Restent hors corpus : droit de l'Union européenne et droit international (EUR-Lex, traités), jurisprudence de la CEDH et de la CJUE. |
| D66 | Rubriques par mode | L'explication suit des rubriques imposées, propres à chaque mode (ex. cas pratique : faits et qualification, problème de droit, majeure, mineure, conclusion), demandées au modèle dans la consigne et le schéma JSON, conservées par le contrôle si elles appartiennent au mode, affichées en sous-titres. Backtest du 2026-11-13 (`eval/backtest_modes.py`, 20 questions, vrai modèle) : 20 réponses, 100 % des rubriques remplies dans chaque mode, 0 élément retiré par le contrôle. |
| D67 | Double authentification par application | Codes TOTP (RFC 6238 : SHA-1, 6 chiffres, 30 s, tolérance ±30 s), bibliothèque standard seule, compatibles Google Authenticator, Microsoft Authenticator, 2FAS, Aegis. Facultative pour les étudiants (« Mon compte », QR code généré dans le navigateur), obligatoire pour l'administration (403 sinon). Connexion en deux étapes : le mot de passe donne un jeton en mémoire (5 min, 5 essais), le code ouvre la session. Un code déjà accepté est refusé (rejeu). 8 codes de secours à usage unique, stockés en empreinte SHA-256, affichés une seule fois. Désactivation : mot de passe et code, toutes les sessions fermées. Dernier recours : `python -m api.admin desactiver2fa <email>`. |
| D68 | Secrets de double authentification chiffres en base | Les cles TOTP et les empreintes des codes de secours sont chiffrees en AES-256-GCM (`api/coffre.py`), cle `CLE_SECRETS` dans `.env` (jamais dans la base) : une copie volee de `lexia.db`, ou une sauvegarde egaree, ne permet plus de generer les codes a six chiffres. Les valeurs ecrites avant sont rechiffrees au demarrage. Sans cle, le service demarre en clair et l'avertit dans les journaux ; `deploy/publier.sh` en genere une au premier deploiement. Cle perdue : `python -m api.admin desactiver2fa <email>` debloque un compte. |
| D69 | Verification de l'adresse e-mail (Resend) | A l'inscription, un lien a usage unique valable 24 h est envoye par Resend (`api/courriel.py`) ; tant que l'adresse n'est pas confirmee, les questions et questionnaires sont refuses (403) : sans cela le quota gratuit se contourne en creant des comptes avec des adresses inventees. Renvoi limite a un e-mail toutes les deux minutes. Sans `RESEND_API_KEY`, la verification est desactivee et le site reste utilisable ; les comptes anterieurs sont consideres confirmes. Resend recoit l'adresse et le texte du message, jamais le mot de passe ni les questions (mentionne dans la politique de confidentialite). |
| D70 | Clause Groq « not for consumer use » levee, n8n durci, acces direct referme | Le contrat de service Groq (lu le 2026-11-13) reserve les services « aux developpeurs, entreprises et organisations », et prevoit expressement les « End Users of a Customer Application » : Lexia est le client, les etudiants sont des utilisateurs finaux, usage conforme. Le contrat impose 18 ans au client (l'editeur) et laisse a sa charge la conformite si des mineurs utilisent l'application : les CGU precisent donc 15 ans, age du consentement numerique en France (art. 45 loi Informatique et Libertes). n8n : limite de 10 tentatives de connexion par minute et par adresse, en-tetes de securite ; aucun workflow n'utilise de webhook entrant, rien d'externe n'appelle l'instance. Lexia de nouveau reservee a Cloudflare. |
| D72 | Droit europeen et droit international | Comparaison avec la maquette de licence de Paris 1 (2025-2030), recoupee avec cinq facultes : le droit de l'Union, la Convention EDH et le droit international public (obligatoires en L2-L3) n'avaient aucune source, alors que 16 000 passages citent l'Union et 3 000 la Convention. Ajouts (`ingest/sources/traites.py`, 673 passages) : TUE, TFUE et Charte des droits fondamentaux (versions consolidees du JOUE C 202 du 7 juin 2016, XHTML du depot Cellar de l'Office des publications, les pages EUR-Lex exigeant un navigateur) ; Convention EDH (texte de la Cour, Protocole additionnel et protocoles 4, 6 et 7 ; le 12 n'est pas ratifie par la France, les 13 et 16 sont ecartes car l'extraction du livret melange leurs pages ; numeros « P1-1 » pour ne pas se confondre avec un article de la Convention ; date d'entree en vigueur des protocoles non affichee faute de verification) ; Charte des Nations unies (page de l'ONU). Le texte de la Convention n'est pas dans l'archive LEGI (decret de publication de 1974, anterieur a sa couverture). Matieres Droit europeen et Droit international ; la jurisprudence qui applique ce droit (Conseil d'Etat, Cour de cassation, Conseil constitutionnel) y est rattachee. « TUE » n'est reconnu que precede de « du », pour que « Paul tue Jean » ne detourne pas la recherche du Code penal. Lexique : renvoi prejudiciel, concurrence, libertes de circulation, proces equitable, recours a la force... Recherche : 13 questions europeennes et internationales sur 13 retrouvees (12 au premier rang). Licences : reutilisation EUR-Lex autorisee avec mention de la source ; pour la Convention et la Charte de l'ONU, textes officiels de traites, conditions des deux sites a verifier. Reste a faire : jurisprudence de la CJUE et de la Cour EDH (pas de telechargement en masse trouve pour HUDOC). |

### Qualité des réponses, phase B du plan d'amélioration (2026-11-12)

| # | Sujet | Décision |
|---|---|---|
| D52 | Lexique local | `api/lexique.py` : 69 notions du programme de licence reliées à leurs articles de principe (numérotation actuelle), ajoutées aux candidats comme les suggestions de la reformulation, sans appel au modèle. Au plus 4 articles ajoutés par question (lexique, concordance, reformulation confondus). Banc `eval/recherche.py` sans reformulation : 8/8 au lieu de 5/8 (une partie de ces questions relève directement du lexique). |
| D53 | Anciens numéros du Code civil | `api/concordance.py` : table écrite à la main de 26 articles d'avant la réforme du 1er octobre 2016 (1134 → 1103, 1193, 1104 ; 1382 → 1240...), vérifiée texte contre texte sur l'archive LEGI ; le calcul automatique par similarité a été écarté (1384 donnait 1241). Une question qui cite un ancien numéro reçoit l'article actuel du même numéro, l'ancienne version et les articles actuels correspondants, et le modèle est prévenu. « Vérifier la version en vigueur » sur une ancienne version renvoie vers l'article actuel correspondant. |
| D54 | Modes méthode | Cas pratique, commentaire, dissertation : le modèle est appelé même sans extrait, ne doit pas s'abstenir, et des faits présentés comme un exercice ne sont pas une situation personnelle (« hors champ » réservé à la propre situation de l'étudiant). Le droit positif exige toujours une source. |
| D59 | Matières spéciales du Code civil | Un article des successions, des libéralités ou des régimes matrimoniaux n'est gardé que si la question parle de cette matière (sauf s'il est cité) : l'article 777 (nullité de l'option successorale pour dol) remontait sur toute question sur le dol, et le modèle en tirait une règle des contrats (constaté en ligne le 2026-11-12). Lexique : dol → 1137, 1131, 1138, 1139 ; réticence dolosive → 1137, 1112-1 ; vice du consentement dans une succession → 777 ; « droit des contrats » passe en dernier pour ne plus évincer la notion précise. |
| D60 | Matière « Droit des contrats » | Sources : Code civil, Code de la consommation, Cour de cassation (chambres civiles et commerciale), lois. Vérification du 2026-11-12 : les 33 sources actives du registre sont dans l'index, 100 % des passages en vigueur ont un embedding, archives DILA du 2026-11-08 ; une ordonnance du Conseil d'État porte la date de remplacement « 2999-01-01 » de la DILA, désormais jamais affichée. |
| D61 | Abrogation différée et lexique des matières de L2-L3 | Un article à l'état DILA « ABROGE_DIFF » (applicable aujourd'hui, abrogation programmée, ex. refonte du Code de procédure pénale au 1er janvier 2029) est en vigueur jusqu'à sa date de fin : 3 718 articles actuels (dont 2 601 du Code de procédure pénale, 114 du Code du travail, 88 du Code pénal comme l'art. 122-1) et 442 articles de lois étaient exclus de la recherche. Index après ré-ingestion : 667 286 passages, 493 157 embeddings. Lexique étendu au droit pénal (122-1 à 122-8, 111-3, 121-x, infractions courantes, CPP 7, 8, 62-2), au droit social (L1233-3, L1232-1, L1237-11, CDD, CDI...) et au droit administratif (CJA R421-1, L521-1 à 3, L911-1 ; CRPA L231-1, L211-2, L242-1, L311-1). |
| D57 | Cours déposés | Dépôt par l'étudiant de ses cours (PDF, Word, texte ; OCR plus tard), rangés par matière dans son compte : 3 / 30 / 100 cours selon la formule, 20 Mo par fichier. Seul le texte est gardé (passages d'environ 1 500 caractères avec la page, base SQLite des comptes, index FTS5 nettoyé par déclencheur, embeddings calculés en arrière-plan sur un fil). Choix visible « Mon cours uniquement » (8 passages du cours) ou « Mon cours + textes officiels » (4 + 4 entrelacés). Passages de cours lisibles par leur seul propriétaire, jamais mis en cache. CGU (droits sur le cours, usage personnel) et confidentialité mises à jour. Conception : `docs/superpowers/specs/2026-11-12-cours-deposes-design.md`. |

### Phase A du plan d'amélioration (2026-11-12)

| # | Sujet | Décision |
|---|---|---|
| D55 | Mesure du coût | Chaque réponse Gemini écrit ses jetons (entrée, sortie, réflexion), le modèle et le rôle (génération ou reformulation) dans `logs/modele.jsonl`, sans aucun texte. `eval/cout.py` en tire le coût moyen par question, avec les prix fournis en argument (grille officielle, jamais en dur). |
| D56 | Sauvegarde hors serveur | `deploy/rapatrier_sauvegardes.sh` copie les sauvegardes du serveur sur le Mac (60 conservées), teste la restauration de la plus récente et échoue sinon ; lancement quotidien par launchd (`deploy/fr.lexia.sauvegarde.plist`). Complète D45. |
| D58 | Groq en production | Conservé en secours de Gemini (D51), avec l'option « Zero Data Retention » activée dans la console Groq (ouverte à tous les comptes) : plus de journaux de fiabilité ni d'abus. Données traitées aux États-Unis, contrat avec Groq UK pour les clients de l'EEE. À vérifier avant l'ouverture publique : la clause du contrat Groq « not for consumer use » face à un service destiné à des étudiants, et le contenu de l'accord de traitement des données (transferts hors UE). |

## Journal des changements

- 2026-11-11 : création du document.
- 2026-11-11 : phase 1, ajout de D12 à D18.
- 2026-11-11 : phase 2, ajout de D19 à D24 et du point ouvert sur le quota d'embeddings.
- 2026-11-11 : embeddings open source en local (D25, D26).
- 2026-11-11 : D9 validé, front en Vite + React + TypeScript + Tailwind.
- 2026-11-11 : reclassement et reformulation de la question (D27, D28).
- 2026-11-11 : phase 4, évaluation (D29 à D31).
- 2026-11-11 : site complet, comptes et formules (D32 à D35).
- 2026-11-11 : tableau de bord administrateur (D36).
- 2026-11-11 : corpus élargi, références multi-codes, annales (D37 à D41).
- 2026-11-12 : filtre par source dans l'index plein texte (D42).
- 2026-11-12 : lois citées, pages légales configurables, tâche quotidienne (D43 à D45).
- 2026-11-12 : moteur PostgreSQL supprimé, index local seul (D46) ; quotas non décomptés sans appel au modèle.
- 2026-11-12 : reclassement allege, 10 candidats / 256 jetons (D47).
- 2026-11-12 : Gemini plus rapide sans clé payante, cache des réponses (D48) ; six semestres et consignes adaptées au niveau (D49).
- 2026-11-12 : conformité du site (D50).
- 2026-11-12 : Groq en secours de Gemini (D51).
- 2026-11-12 : lexique local, anciens numéros du Code civil, modes méthode (D52 à D54).
- 2026-11-12 : mesure du coût par question et sauvegarde hors serveur (D55, D56) ; Groq conservé avec ZDR (D58).
- 2026-11-12 : cours déposés par les étudiants (D57).
- 2026-11-12 : bascule plus rapide vers Groq (D58).
- 2026-11-12 : article 777 écarté des questions de contrats, lexique du dol complété (D59).
- 2026-11-12 : matière Droit des contrats, vérification du corpus (D60).
- 2026-11-12 : articles à abrogation différée remis en vigueur, lexique pénal, social et administratif (D61).
- 2026-11-12 : disjoncteur Gemini / Groq (D62).
- 2026-11-12 : backtest de la recherche sur 200 cas et corrections (D63).
- 2026-11-13 : audit de sécurité et corrections (D64).
- 2026-11-13 : nouvelles sources et matières (D65), rubriques par mode (D66).
- 2026-11-13 : double authentification par application (D67) ; secrets chiffres en base (D68), verification de l'adresse e-mail (D69) et revue des points ouverts (D70).
- 2026-11-14 : droit europeen et droit international, cinq traites ajoutes (D72).
