# Cours de droit libres : ce que Lexia peut intégrer à côté des textes officiels

Relevé du 2026-11-19. Décision de l'éditeur : phases 1 et 2 (vie-publique.fr et service-public.gouv.fr), sans les
wikis ; décision D103 de `docs/decisions.md`. Phase 2 faite, phase 1 bloquée (partie 7).

Question de l'éditeur : Lexia peut-elle récupérer des cours entiers, en plus des textes, pour un service payant ?

## 1. Réponse courte

- **Il n'existe presque pas de cours de licence en droit français à la fois libres pour un usage commercial, complets
  et à jour.** Les cours universitaires ouverts trouvés sont en CC BY-NC-ND (usage commercial interdit) ou en accès
  libre sans licence libre. HAL ne contient aucun cours de licence en droit français sous licence ouverte.
- **Les seules sources volumineuses, à jour et réutilisables commercialement sont les fiches de la DILA** :
  vie-publique.fr (institutions, droit public, environ 1 200 fiches, Licence Ouverte 2.0, **sans modification**) et
  service-public.gouv.fr (fiches pratiques, environ 36 000 passages, Licence Ouverte, flux XML quotidien). Ce sont des
  fiches explicatives, pas des cours.
- **Wikiversité et Wikilivres sont bien en CC BY-SA 4.0** (usage commercial permis, attribution et partage à
  l'identique), mais le volume est faible (environ 2,3 Mo de wikitexte en tout, soit environ 1 500 passages, à
  comparer aux 916 000 du corpus) et la qualité inégale : la leçon de Wikiversité sur le contrat est antérieure à la
  réforme de 2016, le livre de droit du travail de Wikilivres ne cite rien après 2008.
- Recommandation : intégrer d'abord les fiches de vie-publique.fr, ensuite une sélection de fiches de
  service-public.gouv.fr, puis seulement des pages choisies une à une de Wikiversité et Wikilivres ; toutes affichées
  comme **explications non officielles**, à part des textes, avec auteur, licence et date. Demander par écrit une
  licence pour le manuel libre « Initiation aux études juridiques » (BIU Cujas), seule vraie piste de cours de L1.

## 2. Méthode

- Licences lues sur la page officielle de chaque source (ou son API) le 2026-11-19, citées en partie 3. Aucune
  licence n'est supposée : quand une page est muette, c'est écrit.
- Volumes mesurés par des requêtes ponctuelles aux API (MediaWiki, HAL, data.gouv.fr, Hugging Face) et par les
  en-têtes HTTP des fichiers, **sans téléchargement en masse**. Seuls les textes de quatre leçons de Wikiversité et
  sept livres de Wikilivres ont été lus par l'API pour juger de leur date (compte des anciens et nouveaux numéros du
  Code civil, année la plus récente citée).
- Exclus par principe (D10), sans téléchargement : manuels d'éditeurs (Dalloz, LGDJ, Lextenso...), cours de faculté
  non libres, UNJF.
- Limites : vie-publique.fr était en maintenance le 2026-11-19 (erreur 503) ; sa page « Utiliser nos contenus » a été
  lue dans la copie de l'Internet Archive du 2026-01-17 (page datée du 1er mars 2023). À relire sur le site avant
  toute intégration. Le nombre de fiches de vie-publique.fr est une estimation tirée de l'index de l'Internet Archive.

## 3. Tableau des sources

Les 20 matières de Lexia (`api/matieres.py`) : L1 Introduction au droit, Droit constitutionnel, Droit civil, Droit de
la famille, Droit des biens ; L2 Droit des contrats, Droit administratif, Droit européen, Droit pénal, Droit des
affaires, Finances publiques ; L3 Procédure civile, Procédure pénale, Droit social, Droit des sociétés, Contentieux
administratif, Droit administratif des biens, Droit international, Libertés fondamentales, Droit fiscal.

| Source | URL | Licence exacte (où elle est lue) | Usage commercial | Obligations | Matières Lexia couvertes | Volume | Qualité | Format | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| Wikiversité, faculté de droit | https://fr.wikiversity.org/wiki/Faculté:Droit | CC BY-SA 4.0 (API `siteinfo` du site : « Creative Commons Attribution-Share Alike 4.0 » ; conditions d'utilisation Wikimedia, section 7, en vigueur depuis le 7 juin 2023) | Oui | Attribution (auteurs ou lien vers la page, mention de la licence, lien, indication des modifications) ; partage à l'identique des œuvres dérivées | Introduction au droit (juridictions, méthodologie de l'arrêt), Droit civil (personnes, nom, responsabilité délictuelle), Droit des biens (2 pages), Droit des contrats, Droit des affaires (droit commercial général), Droit social, Droit administratif (fonction publique), Droit administratif des biens (6 Ko), Finances publiques, Droit fiscal (TVA), Droit international (humanitaire). Rien en constitutionnel, famille, pénal, procédures, sociétés, contentieux administratif, européen, libertés | 22 leçons, environ 620 Ko de wikitexte balisage compris, environ 400 passages | Inégale. « Obligation contractuelle » (76 Ko) antérieure à la réforme : 20 mentions de la cause, articles 1108 et 1134, aucun article 1103, pas d'ordonnance de 2016. « Responsabilité délictuelle » à moitié reprise (1384 cité 19 fois, 1242 20 fois). Pages principales datées de 2013 à 2016 pour la plupart | API MediaWiki ; dump mensuel `frwikiversity-latest-pages-articles.xml.bz2` (46 Mo, 2026-11-01) ; HTML | Retenir page par page seulement, après relecture (phase 3) |
| Wikilivres, catégorie Droit | https://fr.wikibooks.org/wiki/Catégorie:Droit | CC BY-SA 4.0 (API `siteinfo`, mêmes conditions Wikimedia) | Oui | Comme Wikiversité | Droit constitutionnel (15 Ko), Droit administratif (institutions administratives, droit de l'administration publique, droit administratif), Droit administratif des biens (domaine public), Finances publiques (finances locales), Droit fiscal, Droit social (droit du travail), Droit des sociétés, Droit européen (systèmes juridiques communautaires), Droit international (public) | 11 livres, environ 1,6 Mo de wikitexte, environ 1 100 passages | Souvent ancienne. Année la plus récente citée : droit du travail 2008 (avant les ordonnances de 2017), sociétés 2015 (avant la loi PACTE), droit international public 2005, institutions administratives 2008, droit administratif 2011 ; seul le droit fiscal cite 2025 | API MediaWiki ; dump mensuel `frwikibooks-latest-pages-articles.xml.bz2` (41 Mo, 2026-11-01) ; HTML | Retenir page par page seulement (droit fiscal, domaine public après relecture) (phase 3) |
| vie-publique.fr, fiches | https://www.vie-publique.fr/fiches | Licence Ouverte 2.0 pour les rubriques Fiches, Éclairages, Questions-réponses, Lois, Brèves (page « Utiliser nos contenus », copie du 2026-01-17 ; mentions légales : « licence etalab-2.0 ») ; **Dossiers, Paroles d'expert, contenus des livres et revues : autorisation préalable** ; rapports et discours : droits non gérés par la DILA | Oui (Licence Ouverte 2.0 : « à des fins commerciales ou non ») | Mentionner « Vie-publique.fr » et la date de création ou de mise à jour de la fiche ; **ne pas modifier le contenu** ; pas de logo ; ne pas suggérer une caution de la DILA | Droit constitutionnel, Libertés fondamentales, Droit administratif, Contentieux administratif (juge administratif), Finances publiques, Droit européen, Introduction au droit (loi, justice), un peu de Droit fiscal et de Droit social. Pas de droit privé | Environ 1 200 fiches (estimation par l'index de l'Internet Archive), de l'ordre de 6 000 passages | Bonne a priori : rédaction de la DILA, date de création ou de mise à jour affichée sur chaque contenu. Actualité non vérifiée fiche par fiche (site en maintenance) | HTML seulement (aucun jeu de fiches sur data.gouv.fr, seulement les métadonnées des rapports et discours) | **Retenir (phase 1)** |
| service-public.gouv.fr, fiches pratiques | https://www.data.gouv.fr/datasets/fiches-pratiques-et-ressources-de-service-public-gouv-fr-particuliers | Site : « Sauf mention contraire, tous les contenus de ce site sont sous licence etalab-2.0 » (pied de page, page « Mise à disposition des données ») ; data.gouv.fr indique « fr-lo » (Licence Ouverte 1.0) pour le jeu Particuliers et « lov2 » pour le jeu vectorisé | Oui | Mentionner « Service Public / DILA » et la date de mise à jour ; marques et logos interdits sans accord écrit | Thèmes de l'espace Particuliers : « Famille - Scolarité », « Justice », « Travail - Formation », « Logement », « Argent - Impôts - Consommation », plus le volet Entreprendre. Rapprochement probable avec Droit de la famille, Droit social, Droit des biens, Droit des contrats (consommation), Procédure civile et pénale, Droit fiscal, Droit des sociétés : à confirmer au tri par sous-thème | Environ 36 100 passages de 1 024 caractères au plus (jeu dérivé `AgentPublic/service-public`, Particuliers et Entreprendre) ; archive Particuliers de 24 Mo | Bonne et à jour (flux refait chaque jour, dernier fichier du 2026-11-19), mais niveau pratique et non universitaire | XML quotidien (`lecomarquage.service-public.gouv.fr/vdd/3.5/part/zip/vosdroits-latest.zip`), schéma 3.5 publié | **Retenir une sélection (phase 2)** |
| HAL, droit | https://hal.science (API `api.archives-ouvertes.fr/search`) | Licence choisie par chaque auteur (champ `licence_s`). Défaut « HAL authorisation v1 » : les tiers doivent « demander une autorisation à l'auteur ou à l'ayant droit pour reproduire, adapter ou utiliser l'œuvre » | Seulement pour CC BY, CC BY-SA, CC BY-ND, CC0 et Licence Ouverte | Selon la licence de chaque dépôt | Cours (type LECTURE) en droit : 64 dépôts, 5 en CC BY et 1 en CC BY-SA, **aucun cours de licence en droit français** (le seul « Cours de droit notarial » en CC BY vient de l'université de Douala) | Textes intégraux en droit : 25 039, dont 1 074 en français sous licence permettant l'usage commercial (545 articles, 173 chapitres, 24 ouvrages, 4 cours) | Recherche, pas enseignement de licence | API Solr (JSON) + PDF | Exclure pour les cours ; articles CC BY à revoir plus tard, au cas par cas |
| Cours universitaires ouverts | AUNEGe (https://aunege.fr), FUN-MOOC, manuel « Initiation aux études juridiques » (BIU Cujas, IRJS, Couperin) | AUNEGe, « Droit des contrats » (C. Lisanti) : « CC BY NC ND » écrit en pied de page du document. FUN-MOOC : licence propre à chaque cours, aucun cours de droit français en CC BY trouvé. Manuel Couperin : « Manuel numérique de droit en accès libre », **aucune licence libre indiquée** dans la plaquette du projet, édition papier vendue (Nouveau Monde) | AUNEGe : non. Manuel Couperin : non sans accord écrit | - | Manuel Couperin : Introduction au droit, plusieurs chapitres (dont « Les sociétés et le commerce ») | - | Manuel Couperin récent (chapitres maquettés en 2025) | Liseuse en ligne | Exclure ; **écrire à Couperin pour une licence du manuel** |
| Exclus par D10 | Dalloz, LGDJ, Lextenso ; cours de faculté non libres ; UNJF (https://univ-droit.fr) | Droits réservés. UNJF : « Tous les droits de reproduction sont réservés, y compris pour les documents téléchargeables » (mentions légales de univ-droit.fr) | Non | - | - | Non mesuré (rien téléchargé) | - | - | Exclure (D10) |

Pistes hors de la liste demandée, relevées en passant :

| Source | Licence lue | Usage commercial | Remarque |
|---|---|---|---|
| Wikipédia en français | CC BY-SA 4.0 (API `siteinfo`) | Oui | Encyclopédie, pas un cours ; énorme et inégal. Non retenue : le corpus officiel couvre déjà les notions, le lexique les explique |
| Conseil d'État, conseil-etat.fr | Mentions légales : « informations publiques librement réutilisables » ; intégrité, date, lien et « Source : site internet du Conseil d'État » ; logo interdit | Non abordé par la page ; le CRPA (L321-1) permet la réutilisation « à d'autres fins que celles de la mission de service public » | Analyses des grandes décisions et dossiers utiles en Droit administratif et Contentieux administratif. À confirmer par écrit avant intégration |
| Conseil constitutionnel, conseil-constitutionnel.fr | Mentions légales : textes « librement reproductibles », sauf ceux signés par des personnalités extérieures ; citation du site, date, intitulé, auteur ; pas d'altération | Non abordé pour les textes (interdit pour les liens) | Commentaires des décisions très utiles en Droit constitutionnel et Libertés fondamentales. À confirmer par écrit avant intégration |

## 4. Couverture des 20 matières par les sources retenues

V = vie-publique.fr, S = service-public.gouv.fr (rapprochement par thème, à confirmer au tri des sous-thèmes),
W = Wikiversité ou Wikilivres (pages à choisir une à une).

| Matière | V | S | W | Remarque |
|---|---|---|---|---|
| Introduction au droit | oui | - | oui | W : juridictions, méthodologie de l'arrêt |
| Droit constitutionnel | oui | - | peu (15 Ko, 2012) | V couvre bien les institutions |
| Droit civil | - | peu | oui | W : personnes, nom ; responsabilité à revoir |
| Droit de la famille | - | oui | - | S : niveau pratique |
| Droit des biens | - | peu | peu | Aucune source satisfaisante |
| Droit des contrats | - | peu (consommation) | **non** | La leçon W est antérieure à 2016 : à exclure |
| Droit administratif | oui | - | oui | |
| Droit européen | oui | - | ancien (2012) | |
| Droit pénal | - | peu | - | |
| Droit des affaires | - | oui (Entreprendre) | peu | |
| Finances publiques | oui | - | oui (2008, 2016) | |
| Procédure civile | - | peu | - | |
| Procédure pénale | - | peu | - | |
| Droit social | peu | oui | ancien (2008, 2013) | W à exclure tant qu'il n'est pas à jour |
| Droit des sociétés | - | oui (Entreprendre) | ancien (2015) | |
| Contentieux administratif | oui | - | peu | |
| Droit administratif des biens | - | - | oui (domaine public) | |
| Droit international | - | - | ancien (2005) | |
| Libertés fondamentales | oui | - | - | |
| Droit fiscal | peu | oui | oui (cite 2025) | |

Le droit privé de L1 et L2 (contrats, biens, pénal, procédures) reste sans cours libre de qualité. Pour ces matières,
les cours déposés par l'étudiant (D57, D93) restent la seule source de cours.

## 5. Ce que les licences imposent à Lexia

- **Licence Ouverte 2.0** (vie-publique.fr, service-public.gouv.fr) : réutilisation commerciale permise ; mentionner la
  source (au moins le concédant) et la date de dernière mise à jour, un lien suffit ; ne pas suggérer « une
  quelconque reconnaissance ou caution » du concédant.
- **vie-publique.fr ajoute « de ne pas modifier le contenu »** : les passages doivent être affichés mot pour mot. Le
  découpage en passages ne change pas le texte ; un résumé par le modèle ne doit jamais être présenté comme la fiche.
- **CC BY-SA 4.0** (Wikiversité, Wikilivres) : attribution complète (auteurs ou lien vers la page et son historique,
  mention et lien de la licence, lien vers l'œuvre, indication des modifications : découpage, balisage retiré) ; une
  œuvre dérivée partagée doit être sous CC BY-SA. Points à faire relire par un juriste avant la phase 3 :
  - une réponse de Lexia qui reprend mot pour mot un passage CC BY-SA pourrait être une œuvre dérivée ;
  - une fiche de révision de l'étudiant faite à partir de cette réponse aussi.

  Précaution proposée : passages CC BY-SA affichés seulement comme extraits attribués, jamais recopiés dans les
  fiches ou questionnaires générés.
- **Rien de tout cela n'est une source officielle** : ces textes ne disent pas le droit, ils l'expliquent. Ils ne
  doivent ni remplacer ni contredire un article ou une décision dans une réponse.

## 6. Recommandation

1. **Phase 1, vie-publique.fr (fiches et questions-réponses seulement)** : licence claire, contenu à jour, couvre le
   droit public de L1 à L3 où les étudiants manquent d'explications. Relire la page « Utiliser nos contenus » sur le
   site rétabli avant de commencer. Pas de dump : lecture des pages au rythme d'une par seconde au plus, rubriques
   Dossiers et Paroles d'expert exclues.
2. **Phase 2, service-public.gouv.fr** : flux XML officiel et quotidien, mais niveau pratique. Ne garder que les
   thèmes qui recoupent les matières (famille, justice, travail, logement, consommation, fiscalité, création
   d'entreprise) et les rattacher aux matières par thème.
3. **Phase 3, Wikiversité et Wikilivres, page par page** : liste fermée de pages relues (date, articles cités en
   vigueur), révision figée dans le registre, après avis sur le partage à l'identique. Exclure « Obligation
   contractuelle » et « Droit du travail » tant qu'ils ne sont pas à jour.
4. **Démarches écrites** (à faire par l'éditeur) :
   - Couperin et la BIU Cujas : licence du manuel « Initiation aux études juridiques » ;
   - Conseil d'État et Conseil constitutionnel : confirmation d'une réutilisation dans un service payant pour leurs
     analyses et commentaires.
5. HAL, AUNEGe, FUN-MOOC, manuels, UNJF : rien à intégrer.

Ordre de grandeur : environ 6 000 passages en phase 1, au plus 36 000 en phase 2, environ 1 500 en phase 3, soit au
plus 5 % de passages en plus dans l'index.

## 7. Intégration proposée

### Récupération (décision de l'éditeur du 2026-11-19 : phases 1 et 2)

Commande : `python -m ingest.cours_recuperes`. Elle télécharge si besoin, puis réécrit le catalogue de la page
(`data/cours_recuperes/catalogue.json`) et les passages de l'index (`data/passages/fiches_service_public.jsonl`).
Avec `--hors-ligne`, elle réutilise ce qui est déjà téléchargé. La mise à jour nocturne la lance avant l'index.

| Source | État | Détail |
|---|---|---|
| service-public.gouv.fr (phase 2) | **Récupéré : 781 fiches pratiques, 6 498 passages** | Archive XML Particuliers du 2026-11-19 ; fiches mises à jour entre le 2022-01-27 et le 2026-11-18 |
| vie-publique.fr (phase 1) | **Bloqué** | Licence relue sur le site rétabli le 2026-11-19 : Licence Ouverte 2.0, inchangée (source « Vie publique », date, sans modification). Mais le site refuse les clients automatiques (protection anti-robots : page JavaScript et cookies, robots.txt lui-même illisible sans navigateur) et ne publie aucun export de ses fiches. Contourner cette protection est exclu |
| Wikiversité, Wikilivres (phase 3) | **Non retenu** | Décision de l'éditeur. L'ingestion sait les lire (liste `WIKI` vide), mais l'API Wikimedia exigerait un contact dans le User-Agent (`WIKIMEDIA_CONTACT`) |

Pour vie-publique.fr, demander à la DILA un export des fiches (formulaire de contact du site ou DILA, Département de
l'édition et du débat public).

Fiches de service-public.gouv.fr :
- seules les fiches pratiques sont reprises, pas les questions-réponses ;
- elles sont rangées par sous-thème, parfois par dossier : table `SP_MATIERES` de `ingest/cours_recuperes.py` ;
- le texte est repris sans modification, chapitre par chapitre, avec les textes de référence cités par la fiche ;
- la mise en forme, les liens, les simulateurs et les blocs pratiques (adresses, services en ligne) ne sont pas
  repris, et c'est indiqué sur chaque fiche.

| Matière | Fiches | Passages |
|---|---|---|
| Contentieux administratif | 12 | 138 |
| Droit administratif | 10 | 83 |
| Droit administratif des biens | 6 | 62 |
| Droit civil | 14 | 104 |
| Droit constitutionnel | 13 | 88 |
| Droit de la famille | 73 | 669 |
| Droit des biens | 38 | 383 |
| Droit des contrats | 116 | 1 193 |
| Droit fiscal | 80 | 512 |
| Droit pénal | 54 | 523 |
| Droit social | 282 | 1 913 |
| Introduction au droit | 12 | 161 |
| Libertés fondamentales | 9 | 112 |
| Procédure civile | 31 | 200 |
| Procédure pénale | 31 | 357 |
| **Total** | **781** | **6 498** |

Aucune fiche pour Droit des affaires, Droit des sociétés, Droit européen, Droit international, Finances publiques :
- les deux premières relèvent du volet Entreprendre de service-public.gouv.fr, qui n'est pas encore repris (jeu
  « Fiches pratiques et ressources Entreprendre », même licence) ;
- les trois autres n'ont pas de sous-thème qui leur corresponde.

Reste à faire :
- publier : copier le catalogue et les passages sur le serveur, ou y lancer la commande (la nuit suivante le fait) ;
- demander l'export de vie-publique.fr à la DILA ;
- reprendre le volet Entreprendre de service-public.gouv.fr si l'éditeur le souhaite.

### Page « Cours récupérés » (construite le 2026-11-19)

Volume : une matière à la fois (celle de l'espace par défaut), 20 cours par page. La recherche porte sur toutes
les matières : titres d'abord, puis fiches dont le texte répond (index plein texte, `GET /cours-recuperes/recherche`).

Demande de l'éditeur : une page à part pour les cours récupérés, qui dit bien qu'ils sont récupérés et peuvent
contenir des erreurs. Elle affiche le catalogue écrit par l'ingestion (partie précédente) et reste vide sans lui.

- Site : page `/cours-recuperes` (réservée aux comptes, `web/src/site/CoursRecuperes.tsx`), dans le cadre de
  l'espace étudiant ; on l'ouvre depuis la carte « Cours récupérés » de la Bibliothèque.
- Barre de recherche facultative en haut de la Bibliothèque (`web/src/components/RechercheBibliotheque.tsx`,
  demande de l'éditeur du 2026-11-19). Rien n'est chargé tant que l'étudiant n'écrit pas. Elle cherche :
  - dans les cours récupérés, titres puis texte ; chaque résultat ouvre la page avec la recherche remplie (`?q=`) ;
  - dans les annales et les sources officielles ;
  - et propose la même recherche dans le catalogue Sudoc.
- Avertissement en haut de la page : « Cours récupérés sur des sites tiers sous licence libre. Ils ne sont pas
  rédigés par Lexia et peuvent contenir des erreurs ou être dépassés. Vérifiez toujours avec les textes officiels. »
  Il est rappelé sur chaque cours, et en tête du texte du cours ouvert.
- Cours rangés par matière, filtre par matière. Chaque cours affiche :
  - l'auteur, avec un lien vers la liste des contributeurs pour les wikis ;
  - la source avec un lien ;
  - la licence avec un lien vers son texte ;
  - la date de dernière mise à jour ;
  - le lien vers l'original ;
  - les modifications faites, quand il y en a.

  Le texte s'ouvre avec « Lire le cours ».
- API : `GET /cours-recuperes` (liste sans le texte) et `GET /cours-recuperes/{id}` (texte par sections), réservés
  aux comptes (`api/cours_recuperes.py`). Catalogue : `data/cours_recuperes/catalogue.json` (réglage
  `cours_recuperes`, hors du dépôt), relu quand il change.
- Contrôles du catalogue : une entrée est écartée, sans perdre les autres, si :
  - sa licence n'est pas dans la liste admise (Licence Ouverte 1.0 et 2.0, CC BY 4.0, CC BY-SA 4.0 ; aucune clause
    NC) ;
  - sa matière n'est pas l'une des 20 matières ;
  - un lien n'est pas en https ;
  - l'auteur ou le texte manque.
- Tests : `tests/test_cours_recuperes.py` et `web/src/site/CoursRecuperes.test.tsx`, avec un cours factice
  seulement.
- Ces cours ne servent pas aux réponses de l'assistant (partie suivante).

### Index : à part du corpus officiel (fait)

Exigence de l'éditeur : rangé à part des textes officiels dans l'index, sans jamais remplacer ni contredire un
article ou une décision dans une réponse. Le choix le plus sûr est retenu : **les fiches n'entrent pas du tout dans
les réponses**.
- Index SQLite : même table `passages`, source `fiches_service_public`, type `doctrine`, passages de 1 500 caractères
  au plus coupés aux fins de ligne, en-tête « titre > chapitre », sans `meta.date` (elles n'entrent pas dans la
  fraîcheur des sources officielles).
- `api.textes.SOURCES_A_PART` (`fiches_service_public`, `fiches_vie_publique`) :
  - `groupes()` les retire des deux groupes de la recherche des réponses, même quand on les demande ;
  - `embed --all` ne les vectorise pas ;
  - la couverture de l'index ne les compte pas ;
  - le registre leur donne le statut `a_part` : elles ne figurent dans aucune matière.
- Seule `LocalRetriever.rechercher_a_part` (plein texte) les lit, pour la recherche de la page.
- Tests : `tests/test_cours_recuperes.py`. Sur un petit index où un article et une fiche emploient les mêmes mots, la
  recherche des réponses ne renvoie que l'article, et la recherche de la page que la fiche.
- Une intégration aux réponses (rubrique « Pour comprendre », étiquettes E1, E2...) reste possible plus tard ; elle
  demanderait une nouvelle décision.

Reconstruction du 2026-11-19 sur le Mac, à côté de l'index en service (laissé intact), avec les passages du
dépôt principal et ceux des fiches :
- 922 471 passages, soit 916 158 dans l'index du 17 novembre, plus les 6 498 des fiches, moins 185. Ces 185
  passages (chambre criminelle 172, Conseil d'État 11, chambres commerciale et sociale 1 chacune) viennent des
  fichiers de la DILA modifiés depuis le 17 novembre, pas de ce changement.
- 637 684 embeddings (aucun pour les fiches).
- Contrôle de la mise à jour nocturne (`verifier`) : aucun écart.
- Recherche des réponses sur 30 questions et 5 matières (famille, travail, garde à vue, bail, succession) : aucun
  passage de fiche parmi les extraits. La recherche de la page trouve les fiches attendues.
- Backtest de la recherche (`eval/backtest_recherche.py`, 187 cas) sur l'ancien et le nouvel index, mêmes réglages
  (embeddings locaux, sans reformulation ni reclassement par Gemini) : résultats identiques, 182/187 dans les
  8 extraits et 176/187 dans les 4 du secours. Ces chiffres sont plus bas que ceux de production, faute de
  reclassement ; seule la comparaison compte ici.

## 8. Décision

Écrite dans `docs/decisions.md` (D103). Attention : le numéro D103 est aussi pris sur la branche
`claude/fiches-a-retourner` (cartes à retourner), qui n'est pas encore fusionnée. Il faudra renuméroter l'une des
deux au moment de la fusion.

## 9. Pages lues

- Conditions d'utilisation Wikimedia : https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use (sections 7.1, 7.7, 7.8)
- Licence des wikis : API `meta=siteinfo&siprop=rightsinfo` de fr.wikiversity.org, fr.wikibooks.org, fr.wikipedia.org
- CC BY-SA 4.0, texte juridique : https://creativecommons.org/licenses/by-sa/4.0/legalcode.fr (articles 1, 3(a), 3(b), 4)
- vie-publique.fr : https://www.vie-publique.fr/utiliser-nos-contenus et https://www.vie-publique.fr/mentions-legales
  (copies de l'Internet Archive du 2026-01-17 et du 2025-12-17, site en maintenance le 2026-11-19)
- service-public.gouv.fr : https://www.service-public.gouv.fr/P10025 (mentions légales) et
  https://www.service-public.gouv.fr/P10004 (mise à disposition des données) ; jeux data.gouv.fr par l'API
- Licence Ouverte 2.0 : https://github.com/etalab/licence-ouverte/blob/master/LO.md
- HAL : https://about.hal.science/hal-authorisation-v1/ et API https://api.archives-ouvertes.fr/search/
- AUNEGe : https://aunege.fr/wp-content/uploads/2023/04/droit-des-contrats-plan-cours.pdf
- Manuel Couperin : https://ceb.couperin.org/wp-content/uploads/2023/03/plaquette_INITIATION-ETUDES-JURIDIQUES_A4_web-pap.pdf
- UNJF : https://univ-droit.fr/mentions-legales
- Conseil d'État : https://www.conseil-etat.fr/mentions-legales ; Conseil constitutionnel :
  https://www.conseil-constitutionnel.fr/mentions-legales
- CRPA, articles L321-1, L321-2, L322-1, L323-2 : index local de Lexia
