# Référencement de Lexia : moteurs de recherche (SEO) et moteurs de réponse (GEO)

Document du 23 novembre 2026 (décision D116). Site audité : https://lexia-axionstudio.cloud, version en ligne à
cette date ; code audité : `main` au commit e12128d. Rien n'a été publié sur le serveur : les changements décrits
en partie 3 attendent la prochaine publication (`deploy/publier.sh`).

Les actions sont classées par impact attendu, puis par coût. Aucun outil payant n'a été utilisé : les volumes de
recherche sont des estimations qualitatives, signalées comme telles.

## 1. Résumé

- Avant D116, un robot qui ne lance pas JavaScript (GPTBot, ClaudeBot, PerplexityBot, OAI-SearchBot, et Bingbot
  pour une partie de ses passages) recevait la même page de 1 080 octets pour toutes les adresses : une balise
  `<div id="root">` vide, le même titre et la même description. Google lit le JavaScript, mais en différé.
- Le site n'avait que 4 pages publiques utiles (accueil, tarifs, deux pages légales), sans aucune page qui réponde
  à une recherche d'étudiant (« cas pratique droit des contrats », « méthode commentaire d'arrêt »...).
- D116 compile en HTML, à la publication, 34 pages publiques (accueil, tarifs, 20 matières, 10 guides, 2 index) avec
  titre, description, adresse canonique, Open Graph, carte Twitter et données structurées, et ajoute `sitemap.xml`
  (37 adresses), `llms.txt` et une image de partage.
- Ce qui reste à l'éditeur (partie 8) : Google Search Console, Bing Webmaster Tools, vérification des réglages
  Cloudflare pour les robots, premiers liens entrants. Rien de cela ne coûte d'argent.

## 2. Audit du 23 novembre 2026 (avant D116)

Mesures faites avec `curl` depuis le Mac, sur le site en ligne, avec l'agent d'un robot de Google.

| Point | Constat | Effet |
|---|---|---|
| Rendu sans JavaScript | 1 080 octets, `<div id="root"></div>` vide, sur `/`, `/tarifs` et toute autre adresse | Robots des assistants (ChatGPT, Claude, Perplexity) : aucun contenu lisible |
| Titres et descriptions | Un seul titre (« Lexia · Espace d'étude ») et une seule description pour tout le site dans le HTML reçu ; le titre change ensuite par JavaScript (WEB-5) | Résultats de recherche identiques, pas de mot-clé par page |
| Adresse canonique, Open Graph, Twitter | Absents | Doublons possibles (`/tarifs` et `/tarifs/`), partage sans aperçu |
| Données structurées (JSON-LD) | Absentes | Ni éditeur, ni application, ni prix lisibles par les moteurs |
| `sitemap.xml`, `llms.txt` | Réponse 200 avec la page de l'application (faux fichier) | Le moteur croit trouver un sitemap, n'en lit rien |
| Adresse inexistante | 200 avec la page de l'application (« soft 404 ») | Pages vides indexables ; reste vrai après D116 (partie 6) |
| Requête HEAD | 405 | Certains robots et vérificateurs de liens concluent à une erreur |
| `robots.txt` | Exclusions correctes de l'espace des comptes et de l'API, pas de ligne `Sitemap` | Le sitemap n'est pas annoncé |
| Robots des assistants | 200 pour GPTBot, ClaudeBot, PerplexityBot, OAI-SearchBot, Google-Extended et Bingbot ; `robots.txt` non modifié par Cloudflare | Accès ouvert, à garder (partie 8) |
| Prix des formules | Chargés par `/api/formules` après le JavaScript | Aucune offre lisible sans JavaScript |
| Vitesse | Réponse du HTML en 50 à 130 ms par Cloudflare ; JavaScript principal de 279 Ko (85,6 Ko compressés), CSS de 35 Ko (9,4 Ko compressés) ; le texte n'apparaît qu'après le JavaScript | Premier affichage du contenu retardé, surtout sur mobile |
| Lighthouse | Non installé sur le Mac (pas de téléchargement fait) | Score non mesuré : voir partie 7 |

Le manifeste (`manifest.json`), la langue (`lang="fr"`), le HTTPS, la compression et les en-têtes de sécurité
sont corrects. La politique de sécurité du contenu (`script-src 'self'`) n'empêche pas le JSON-LD : un bloc
`application/ld+json` n'est pas exécuté.

## 3. Ce que fait D116 (gratuit, dans le dépôt)

| Action | Impact | Coût | Fait |
|---|---|---|---|
| Pages publiques compilées en HTML à la publication (prérendu), reprises par React sans redessin (`hydrateRoot`) | Très fort : contenu lisible par tous les robots, affichage immédiat | Moyen | Oui |
| Une page par matière (20) : présentation, notions, question de cours avec l'article officiel cité, sources, questions fréquentes, lien d'inscription | Fort : répond aux recherches « droit X L1 », « fiche droit X » | Moyen | Oui |
| 10 guides sourcés (partie 5) | Fort : requêtes de méthode, saisonnières aux partiels | Moyen | Oui |
| Titre, description et adresse canonique uniques par page | Fort | Faible | Oui |
| JSON-LD : Organization, WebSite, WebApplication (avec les 3 offres), LearningResource, FAQPage, Article (avec les articles cités en `Legislation`), BreadcrumbList, CollectionPage | Moyen (compréhension, extraits enrichis possibles) | Faible | Oui |
| Open Graph et carte Twitter, image 1200 x 630 (`web/public/og-lexia.png`) | Moyen (partages sur les réseaux, messageries) | Faible | Oui |
| `sitemap.xml` (37 adresses) et `robots.txt` avec la ligne `Sitemap` | Moyen | Faible | Oui |
| `llms.txt` (format llmstxt.org) | Faible à moyen, adoption encore inégale par les assistants | Faible | Oui |
| Liens Matières et Guides dans l'en-tête (tablette et ordinateur) et le pied de page (partout) | Moyen : maillage interne | Faible | Oui |
| HEAD accepté par le serveur | Faible | Faible | Oui |

Avant et après, sur la compilation locale :

| Mesure | Avant | Après |
|---|---|---|
| Pages avec contenu lisible sans JavaScript | 0 | 34 avec les 10 guides (3 pages légales : tête seule, partie 6) |
| Mots lisibles sans JavaScript, accueil | 0 | 512 |
| Mots lisibles sans JavaScript, toutes pages | 0 | environ 18 000 |
| Adresses dans le sitemap | 0 | 37 |
| JavaScript principal (compressé) | 86,6 Ko | 89,9 Ko (titres et chemins des pages publiques, formules) |
| Texte des matières et des guides | sans objet | fichier à part de 22 Ko compressés, chargé par ces pages seulement |

### Fonctionnement

- `npm run build` (dans `web/`) compile le site, puis l'entrée serveur (`src/entree-serveur.tsx`), puis lance
  `scripts/prerendu.mjs` : pour chaque page de `src/site/seo.ts`, le site est rendu dans un document jsdom à
  l'adresse de la page, et le HTML est écrit dans `dist/pages/<chemin>/index.html` avec ses balises de tête.
- `api/serveur.py` sert `dist/pages/<chemin>/index.html` à l'adresse publique (`/tarifs`), sinon la coquille
  `dist/index.html` comme avant. `dist/pages/` n'est pas une seconde adresse des mêmes pages.
- Les prix et les matières des pages viennent de `web/src/site/donnees-publiques.json`, écrit par
  `python -m api.donnees_publiques` à partir de `api/plans.py`, `api/matieres.py` et du registre des sources. Le
  test `tests/test_pages_publiques.py` échoue si le fichier n'est plus à jour.
- Le texte des articles cités (`web/src/site/contenu/citations.json`) est lu dans l'index de recherche par la même
  commande, avec son lien officiel et sa version. Le même test compare ce fichier à l'index quand l'index est
  présent : une loi nouvelle qui modifie un article cité le fait échouer, il faut alors relire la page.
- Le domaine est écrit à un seul endroit (`ORIGINE` dans `web/src/site/seo.ts`), plus la ligne `Sitemap` de
  `web/public/robots.txt` (un test vérifie qu'elles concordent).

## 4. Mots-clés visés

Estimations sans outil payant : demande et concurrence sont jugées d'après la structure de la licence, la
saisonnalité des partiels (décembre et janvier, avril et mai) et les sites qui se positionnent habituellement sur
ces requêtes (sites de fiches établis, plateformes de cours, blogs d'étudiants, Légifrance pour les numéros
d'articles). À confirmer avec Google Trends (gratuit) puis avec les requêtes réelles de la Search Console après
quelques semaines.

| Requête | Intention | Page de Lexia | Demande estimée | Concurrence estimée | Priorité |
|---|---|---|---|---|---|
| cas pratique droit des contrats | Méthode, exercice | /guides/methode-cas-pratique-droit-des-contrats | Moyenne, pic aux partiels | Forte | 1 |
| méthode commentaire d'arrêt, fiche d'arrêt | Méthode | /guides/methode-commentaire-arret | Forte | Forte | 1 |
| cas pratique droit pénal | Méthode | /guides/methode-cas-pratique-droit-penal | Moyenne | Moyenne | 1 |
| fiche droit L1, fiche introduction au droit | Révision | /matieres/introduction-au-droit, /guides | Moyenne | Forte | 2 |
| responsabilité civile pour faute fiche, article 1240 code civil | Révision, article | /guides/fiche-responsabilite-civile-pour-faute | Moyenne | Forte (Légifrance en tête sur le numéro) | 2 |
| méthode dissertation juridique, plan en deux parties droit | Méthode | /guides/methode-dissertation-juridique, /guides/methode-plan-en-deux-parties | Forte, pic aux partiels | Forte | 1 |
| fiche d'arrêt méthode, faire une fiche d'arrêt | Méthode | /guides/methode-fiche-arret | Forte | Forte | 1 |
| hiérarchie des normes fiche, sources du droit L1 | Révision | /guides/fiche-sources-du-droit-hierarchie-des-normes | Forte | Forte | 2 |
| organisation juridictionnelle française, ordre judiciaire et administratif | Révision | /guides/fiche-organisation-juridictionnelle | Moyenne | Forte | 2 |
| QPC fiche, question prioritaire de constitutionnalité conditions | Révision | /guides/fiche-question-prioritaire-de-constitutionnalite | Moyenne | Moyenne | 2 |
| conditions de validité du contrat, dol article 1137 | Question de cours | /matieres/droit-des-contrats, guide contrats | Moyenne | Forte | 2 |
| droit administratif L2, contentieux administratif L3 | Découverte de la matière | pages des matières | Faible à moyenne | Moyenne | 3 |
| IA droit étudiant, assistant IA droit, révision droit IA | Outil | / | Faible mais en hausse, très qualifiée | Moyenne | 1 (conversion) |
| Lexia droit | Marque | / | Faible au départ | Faible, sous réserve de la marque | 1 |

La requête de marque dépend du nom : la marque « Lexia » n'est pas encore vérifiée (docs/marque-lexia.md). Avant
tout effort sur les liens entrants, attendre l'avis d'un conseil en propriété industrielle ; si le nom change,
seuls `ORIGINE`, `NOM` (`web/src/site/seo.ts`) et `robots.txt` sont à modifier, avec des redirections 301.

## 5. Architecture et contenu

### Arborescence publique

```
/                         accueil (Organization, WebSite, WebApplication)
/tarifs                   formules (offres en JSON-LD)
/matieres                 20 matières par année (CollectionPage)
/matieres/<matiere>       ex. /matieres/droit-des-contrats (LearningResource, FAQPage)
/guides                   guides et fiches (CollectionPage)
/guides/<guide>           ex. /guides/methode-commentaire-arret (Article, FAQPage)
/mentions-legales, /cgu, /confidentialite   tête seule (partie 6)
/inscription, /connexion  coquille de l'application, indexables mais sans contenu propre
/app, /compte, /admin, /cours-recuperes, /api/, /verifier-email, /nouveau-mot-de-passe,
/mot-de-passe-oublie, /pages/                exclus par robots.txt
```

Maillage : chaque matière renvoie à ses guides, aux autres matières de la même année et à l'inscription ; chaque
guide renvoie aux matières concernées et liste ses textes cités ; l'en-tête et le pied de page relient Matières,
Guides et Tarifs.

### Guides publiés (D116 ; 5 premiers le 23 novembre 2026, 5 suivants le même jour)

| Guide | Niveau | Articles cités (version en vigueur lue dans l'index) |
|---|---|---|
| Méthode du cas pratique en droit des contrats | L2 | C. civ. 1101, 1103, 1104, 1112, 1112-1, 1128, 1130, 1132, 1137, 1140, 1178, 1217, 1219, 1231-1, 1353 |
| Méthode du commentaire d'arrêt | L1, L2 | COJ L. 411-1 à L. 411-3 ; CPC 455, 604 |
| Fiche : la responsabilité civile pour faute | L1, L2 | C. civ. 1240, 1241, 1242 (version du 25 juin 2025) |
| Fiche : la question prioritaire de constitutionnalité | L1 | Constitution 61, 61-1, 62 ; ordonnance n° 58-1067, art. 23-2 |
| Méthode du cas pratique en droit pénal | L2 | C. pén. 111-3, 121-1, 121-3, 122-5 |
| Méthode de la dissertation juridique | L1, L2 | C. civ. 4, 5 ; CPC 12 |
| Méthode de la fiche d'arrêt | L1 | COJ L. 411-2 ; CPC 455, 542, 561, 604 ; C. civ. 1241 |
| Le plan en deux parties : méthode et exemples | L1 à L3 | C. pén. 122-5 ; C. civ. 1195 |
| Fiche : les sources du droit et la hiérarchie des normes | L1 | DDHC 6, 16 ; Constitution 34, 37, 38, 55, 61-1, 88-1 ; C. civ. 1, 2, 4, 5 |
| Fiche : l'organisation juridictionnelle française | L1 | COJ L. 111-1, L. 211-3, L. 311-1, L. 411-1, L. 411-2 ; CJA L. 111-1, L. 211-1, L. 211-2 ; Constitution 61-1, 64, 66 ; CPC 542, 604 |

Chaque guide commence par un paragraphe « En bref » qui répond directement à la question, puis suit des sections
numérotées, un exemple quand il est utile, des questions fréquentes et la liste des textes cités avec leur lien
officiel. Les conseils de méthode sont ceux enseignés en licence ; les guides signalent que les attentes varient
selon les enseignants. Une relecture par un enseignant de droit reste à faire avant toute communication qui les
mettrait en avant.

### Plan de contenu (suite)

Par ordre de priorité, au rythme d'un ou deux guides par semaine avant les partiels :

1. Fait le 23 novembre 2026 : méthode de la dissertation juridique, fiche d'arrêt, plan en deux parties, fiches
   sur les sources du droit et la hiérarchie des normes et sur l'organisation juridictionnelle.
2. Fiches de L1 restantes : Ve République (Président, Gouvernement, Parlement), personnalité juridique.
3. Cas pratiques de L2 : responsabilité administrative, inexécution du contrat, droit de la famille (divorce,
   autorité parentale).
4. Pages des grands arrêts déjà désignés par leur nom dans Lexia (D90), avec le texte officiel de la décision et
   un résumé original (les décisions de justice ne sont pas protégées par le droit d'auteur, les commentaires
   publiés le sont : ne jamais les reprendre).
5. Glossaire : une page courte par notion du lexique (`api/lexique.py`), reliée à l'article qui la fonde.

Règles pour tout nouveau contenu : n'écrire que ce qui se vérifie dans le dépôt ou dans un texte officiel ; citer
l'article par sa clé dans `api/donnees_publiques.py` (`CITATIONS`) puis relancer `python -m api.donnees_publiques` ;
respecter la liste « À ne pas écrire aujourd'hui » de `docs/comparatif-notebooklm.md` (un test la vérifie sur
tout le texte des pages publiques et de `llms.txt`).

## 6. Limites connues

- Pages légales : leurs mentions (éditeur, SIRET, hébergeur) viennent de la configuration du serveur, absente à
  la compilation. Un prérendu aurait montré des encarts « à compléter » aux robots ; ces pages reçoivent donc
  seulement leur titre, leur description et leur adresse canonique, le texte restant affiché par le navigateur.
  Piste : faire injecter ces valeurs par le serveur au moment de la réponse.
- Adresses inexistantes : toujours 200 avec la coquille de l'application. Répondre 404 demanderait au serveur de
  connaître toutes les routes de l'application ; à faire en même temps que la piste précédente.
- Les extraits enrichis « FAQ » ne sont plus affichés par Google Search depuis le 7 mai 2026 (documentation
  Google relue à l'audit du 23 novembre 2026, D7) : le balisage FAQPage ne sert qu'à la compréhension par les
  moteurs et les assistants. Il ne reprend plus que la question de cours propre à chaque matière ; la question
  promotionnelle commune aux 20 matières et aux guides est retirée.
- Tarifs et accueil : tant que la configuration du serveur n'est pas lue (HTML prérendu), les formules payantes
  proposent « Créer un compte » au lieu du bouton de demande, et la mention de TVA n'apparaît pas (audit du
  23 novembre, D1). Les citations sont lues dans l'index du Mac : les relire depuis l'index du serveur après
  chaque reconstruction (audit du 23 novembre, C5 et D10, non fait).
- Inscription, connexion et mot de passe oublié ne sont pas prérendus (leur écran dépend de la session).
- Pas de date de mise à jour dans le sitemap pour les pages qui n'en ont pas de fiable (seuls les guides en ont).

## 7. Stratégie GEO (moteurs de réponse)

Les assistants (ChatGPT, Perplexity, Gemini et les aperçus IA de Google, Copilot) citent des pages qu'ils peuvent
lire sans JavaScript, qui répondent en une ou deux phrases à la question posée, et dont les affirmations sont
vérifiables. Ce qui est en place :

- HTML complet sans JavaScript (partie 3), robots des assistants autorisés par `robots.txt`.
- Réponse directe en tête : « En bref » dans les guides, question de cours en tête de chaque matière, questions
  fréquentes rédigées comme des questions d'étudiant.
- Sources officielles citées et datées : chaque règle renvoie à l'article (lien Légifrance ou site du Conseil
  constitutionnel), avec sa version ; le JSON-LD des guides liste ces articles (`citation`, type `Legislation`).
- Faits sur Lexia stables et vérifiables, repris à l'identique dans l'accueil, `llms.txt` et le JSON-LD :
  sources, nombre de matières, formules et prix, limite « outil d'étude, pas de conseil juridique ».
- `llms.txt` à la racine : résumé, matières, guides, pages d'information.

À faire, sans coût :

1. Bing Webmaster Tools en priorité : Copilot et, en partie, la recherche de ChatGPT s'appuient sur l'index de Bing.
2. IndexNow (protocole gratuit de Bing et d'autres moteurs) : prévenir les moteurs à chaque publication. Demande un
   fichier de clé à la racine et un appel après `deploy/publier.sh` ; à décider par l'éditeur.
3. Suivi : une fois par mois, poser les mêmes 10 questions (celles de la partie 4) à ChatGPT, Perplexity, Gemini
   et Copilot, et noter si Lexia est cité et quelle page. Compter dans les statistiques Cloudflare les visites
   venant de chatgpt.com, perplexity.ai, gemini.google.com et copilot.microsoft.com.
4. Lighthouse : pas installé sur le Mac. Après publication, mesurer l'accueil, une matière et un guide avec
   PageSpeed Insights (gratuit, en ligne), sur mobile, et noter les scores dans ce document. Attendu : meilleur
   affichage du premier contenu, puisque le texte est dans le HTML.

## 8. Actions de l'éditeur

Par ordre de priorité. Aucune ne coûte d'argent.

1. Publier (`deploy/publier.sh`), puis vérifier : `curl -s https://lexia-axionstudio.cloud/matieres/droit-penal`
   doit contenir le titre « Droit pénal » ; `/sitemap.xml` et `/llms.txt` doivent répondre en XML et en texte.
2. Google Search Console : propriété de domaine (enregistrement TXT dans le DNS de Cloudflare), envoi de
   `https://lexia-axionstudio.cloud/sitemap.xml`, inspection de l'accueil et d'une matière.
3. Bing Webmaster Tools : import depuis la Search Console, envoi du même sitemap.
4. Cloudflare : laisser désactivés le blocage des robots d'IA (« AI Scrapers and Crawlers ») et la réécriture
   gérée de `robots.txt`, et vérifier que le « Bot Fight Mode » ne bloque pas Googlebot ni Bingbot (au
   23 novembre, tous reçoivent une réponse 200).
5. Liens entrants, sans achat de liens : associations étudiantes de droit (BDE, associations de tutorat),
   bibliothèques universitaires qui recensent des ressources numériques, enseignants qui utilisent Lexia,
   annuaires d'outils d'IA et d'outils pour étudiants (vérifier que l'inscription est gratuite), profils de Lexia
   sur les réseaux du plan marketing (docs/marketing/plan.md). Attendre l'avis sur la marque avant d'en faire
   beaucoup.
6. Mesure : chaque mois, impressions, clics, taux de clic et position des requêtes de la partie 4 dans la Search
   Console ; pages indexées (37 attendues) ; inscriptions dont l'origine déclarée est un moteur ou un assistant
   (question facultative sur l'origine de l'inscription, D110).
7. Faire relire les cinq guides par un enseignant de droit, puis valider le plan de contenu (partie 5).
