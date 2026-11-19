# Cours de droit libres : ce que Lexia peut intégrer à côté des textes officiels

Relevé du 2026-11-19. Statut : **proposition**, rien n'est codé ni téléchargé. Décision attendue de l'éditeur (D103
proposée en partie 8).

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

### Affichage, à part des textes officiels

- Nouveau type de passage `doctrine` (nature « Explication non officielle ») ; jamais compté parmi les textes ni la
  jurisprudence.
- Dans une réponse : rubrique distincte sous les sources, « Pour comprendre (explications non officielles) », avec
  étiquettes propres (E1, E2...) et non S1, S2. Le modèle reçoit la consigne de fonder toute règle sur un texte ou
  une décision ; une affirmation appuyée sur une seule explication passe dans les points d'attention, comme
  « Hors de votre cours, à vérifier » de D93.
- Panneau de source : bandeau « Explication non officielle, ne remplace pas le texte », éditeur ou auteurs, titre,
  date de mise à jour, licence avec lien, lien vers la page d'origine, texte affiché sans modification. Exemples :
  - « Source : Vie-publique.fr, fiche « Qu'est-ce que la QPC ? », mise à jour le JJ/MM/AAAA, Licence Ouverte 2.0 » ;
  - « « Responsabilité délictuelle/... », Wikiversité, auteurs : voir l'historique de la page, CC BY-SA 4.0, extrait
    découpé, mise en forme retirée ».
- Ancienneté : mention visible quand la mise à jour date de plus de deux ans, ou d'avant le 1er octobre 2016 pour une
  explication du droit des contrats et des obligations (entrée en vigueur de l'ordonnance de 2016).
- Aucun logo, aucune formule laissant croire à une caution de la DILA ou de Wikimedia.
- Page « Crédits » (ou mentions légales) : liste des sources réutilisées, licence et lien.
- Réglage de l'étudiant : explications affichées ou non (affichées par défaut). En « Mon cours seulement », aucune
  explication.

### Indexation à côté du corpus DILA

- `registry/sources.yaml` : une entrée par source, `type: doctrine`, licence exacte, texte d'attribution, statut
  `a_verifier` puis `actif` après accord, matières.
- Ingestion :
  - `ingest/sources/vie_publique.py` : pages HTML, rubriques autorisées seulement, date de mise à jour gardée ;
  - `ingest/sources/service_public.py` : archive XML quotidienne, thèmes retenus ;
  - `ingest/sources/wikimedia.py` : API MediaWiki sur une liste fermée de pages, identifiant de révision gardé pour
    l'attribution.

  Passages d'environ 1 500 caractères, plan rappelé en tête comme pour les cours déposés (D93). `meta` : éditeur,
  auteurs ou lien d'historique, licence, URL, date de mise à jour, révision.
- Index SQLite : même table `passages` (`type = 'doctrine'`, `en_vigueur = 1` sauf explication retirée à la source),
  même `passages_fts` filtré par `jeton_source`, vecteurs avec le même modèle. Table `fraicheur` : date de la fiche la
  plus récente par source.
- Recherche : aujourd'hui `groupes()` (`api/retrieval/base.py`) range toute source hors `SOURCES_TEXTES` dans la
  jurisprudence, et `pour_secours()` (`api/rag.py`) fait de même hors type `cours`. Il faut un troisième groupe
  `doctrine`, avec un quota propre (deux extraits au plus sur k, jamais à la place du texte ou de la décision
  attendus) et aucune place dans les 4 extraits du modèle de secours.
- Mise à jour nocturne (D78) :
  - service-public.gouv.fr chaque nuit (empreinte des passages) ;
  - vie-publique.fr chaque semaine ;
  - Wikimedia : nouvelle révision relue avant remplacement.

  Une fiche disparue à la source est retirée de l'index.
- Mesure avant mise en ligne : backtest sans recul (questions de cours 187/187, grands arrêts, matières de licence)
  et nouveau cas de test « une explication n'est jamais citée comme fondement d'une règle ».

## 8. Texte proposé pour la décision

**Numéro à confirmer** : D103 est déjà pris sur la branche `claude/fiches-a-retourner` (cartes à retourner, non
fusionnée). Prendre le premier numéro libre au moment de la fusion.

| D103 | Cours et fiches libres, explications non officielles a cote du corpus (proposition, `docs/cours-libres.md`) | Releve du 2026-11-19 : aucun cours de licence en droit francais a la fois libre pour un usage commercial, complet et a jour (cours ouverts en CC BY-NC-ND ou sans licence libre, aucun cours de licence en droit francais sous licence ouverte dans HAL). Sources retenues, par phases et sur accord de l'editeur : (1) fiches et questions-reponses de vie-publique.fr (Licence Ouverte 2.0, source et date, sans modification ; Dossiers et Paroles d'expert exclus) ; (2) selection thematique des fiches pratiques de service-public.gouv.fr (Licence Ouverte, flux XML quotidien, source « Service Public / DILA » et date) ; (3) pages de Wikiversite et Wikilivres choisies une a une apres relecture (CC BY-SA 4.0, attribution et partage a l'identique ; « Obligation contractuelle », anterieure a la reforme de 2016, et « Droit du travail » exclus). Exclus : manuels, cours de faculte non libres, UNJF (D10), HAL, AUNEGe (CC BY-NC-ND). Affichage : type `doctrine`, rubrique « Pour comprendre (explications non officielles) » distincte des sources, etiquettes E1, E2..., editeur ou auteurs, licence, date de mise a jour et lien ; texte affiche sans modification ; mention d'anciennete ; aucune regle fondee sur une seule explication ; aucune explication en « Mon cours seulement » ni dans les fiches et questionnaires generes. Indexation : meme index SQLite (`passages`, `passages_fts`, vecteurs), troisieme groupe `doctrine` dans la recherche avec deux extraits au plus et aucun dans les 4 du secours. Mise a jour nocturne (D78) et page de credits. A faire par l'editeur : relire la page de vie-publique.fr retablie, demander une licence du manuel « Initiation aux etudes juridiques » (Couperin, BIU Cujas), confirmation ecrite du Conseil d'Etat et du Conseil constitutionnel, avis sur le partage a l'identique avant la phase 3. |

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
