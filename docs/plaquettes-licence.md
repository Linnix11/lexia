# Maquettes de la licence en droit et couverture de Lexia

Relevé du 18 novembre 2026 (décision D97). Point de départ : une étudiante a signalé des matières « manquantes »
(procédure pénale, droit international, droit des contrats, droit administratif) et conseillé de partir des
maquettes officielles des licences de droit.

Constat sur ce signalement :

- **Droit des contrats** et **Droit administratif** existaient déjà. Elle ne les a pas trouvés : le choix de matière
  était une liste plate de 14 intitulés, sans classement ni recherche. Corrigé (partie 4).
- **Procédure pénale** était rangée sous Droit pénal (le Code de procédure pénale et la chambre criminelle sont dans
  le corpus). C'est désormais une matière à part, en L3.
- **Droit international et européen** : retiré par D74, rétabli le même jour par décision de l'éditeur (D98) avec
  les sources dont la réutilisation est autorisée. Voir partie 5.

## 1. Maquettes consultées

Toutes consultées le 18 novembre 2026, sur les sites officiels des universités.

| Faculté | Maquette (URL) | Date indiquée dans le document |
|---|---|---|
| Paris 1 Panthéon-Sorbonne, École de droit de la Sorbonne | L1 : https://droit.pantheonsorbonne.fr/sites/default/files/inline-files/Maquette_Licence%201%20Droit_2025-29_0.pdf ; L2 : https://droit.pantheonsorbonne.fr/sites/default/files/inline-files/Maquette_Licence%202%20Droit_2025-29_0.pdf ; L3 : https://droit.pantheonsorbonne.fr/sites/default/files/inline-files/Maquette_Licence%203%20Droit_2026-29_0.pdf | L1 « Rentrée 2025-2026 », L2 et L3 « Rentrée 2026-2027 », « Document modifié le 28/01/25 » |
| Paris-Panthéon-Assas (Paris 2), parcours classique | https://cio-baip.assas-universite.fr/sites/default/files/licencedroit2025_0.pdf et, pour la L3, https://www.assas-universite.fr/fr/troisieme-annee-licence-en-droit | Aucune année imprimée (fichier « 2025 », créé le 18/12/2025) |
| Toulouse Capitole, parcours-type Droit | https://formations.univ-toulouse.fr/plugins/odf-web/www/_content/subprogram-cdmfr-fruai0311382j74906788dr000-fr/Licence%20(L1-%20L2%20-%20L3)%20mention%20Droit%20parcours-type%20Droit.pdf | « Programme 2026-2027 », mis à jour le 29 juin 2026 |
| Bordeaux, Faculté de droit et science politique (Pessac) | L1 : https://droit.u-bordeaux.fr/download_file/view/c6ba8013-8e03-4205-9d57-a0a575010316/547 ; L2 : https://droit.u-bordeaux.fr/download_file/view/de248b3a-4bc3-4cb9-bc6d-1dea468ed7bf/547 ; L3 droit privé : https://droit.u-bordeaux.fr/download_file/view/22cd3bd2-4b65-426f-98ca-025691176f44/547 ; L3 droit public : https://droit.u-bordeaux.fr/download_file/view/0fe7fedb-64e7-4112-864a-f2da279e7eb5/547 ; L3 judiciaire : https://droit.u-bordeaux.fr/download_file/view/1e579d7c-f644-4314-a5f1-8800d8f2833c/547 ; L3 entreprise : https://droit.u-bordeaux.fr/download_file/view/d4287489-648a-4849-aaeb-0a29ad7ad28d/547 | « 2026-2028 », adoptée par le conseil de faculté le 23/03/2026 (L3 judiciaire : 23/02/2026) |
| Aix-Marseille, Faculté de droit et de science politique | https://facdedroit.univ-amu.fr/sites/default/files/media-ressource/Plaquette_Licence_2025_pages.pdf | « Programme 2025-2026 donné à titre indicatif », en révision pour 2026-2027 |
| Lille, Faculté des sciences juridiques, politiques et sociales | https://droit.univ-lille.fr/filedroit/user_upload/Maquettes_Masters_2026_2030/Maquette_Licence_Droit_01.pdf | Aucune année imprimée (dossier « 2026_2030 », créé le 03/09/2026) |
| Lyon 3 Jean Moulin, Faculté de droit | https://www.univ-lyon3.fr/medias/fichier/faculte-de-droit-remccc-25-26-licence-droit-droit_1762167716881-pdf (maquettes en annexe, p. 20 à 29) | « Année 2025-2026 », CFVU du 30/09/2025 ; pas de version 2026-2027 trouvée |
| Caen Normandie, UFR de droit (syllabus, pas une maquette) | https://ufr-droit.unicaen.fr/wp-content/uploads/sites/39/2025/02/Licence-Droit-S1.pdf, puis S2 à S6 au même chemin | Aucune année (dossier 2025/02) |

Limites : Lyon 3 ne donne pas le semestre des matières de sa « majeure » ; Aix-Marseille distingue matières
fondamentales et complémentaires par la couleur seulement ; les syllabus de Caen ne disent pas ce qui est
obligatoire. Le relevé détaillé, faculté par faculté et semestre par semestre, est dans le compte rendu de la
session du 18 novembre ; ce document n'en garde que la synthèse.

## 2. Matières de droit positif : où, quand, et ce que Lexia couvre

« Moment » : année et semestre les plus fréquents parmi les facultés qui enseignent la matière. Matières de Lexia :
`api/matieres.py` ; sources : `registry/sources.yaml`.

| Matière (intitulés des maquettes) | Facultés | Moment | Textes et jurisprudence nécessaires | Couverture Lexia |
|---|---|---|---|---|
| Introduction au droit, institutions juridictionnelles | 8/8 | L1 S1 | Code civil (titre préliminaire), Constitution, COJ ; Cour de cassation | Matière Introduction au droit (L1) |
| Droit constitutionnel | 8/8 | L1 S1-S2 | Constitution, DDHC, Préambule 1946, Charte de l'environnement, Code électoral ; Conseil constitutionnel | Matière Droit constitutionnel (L1) |
| Droit civil : personnes et famille | 8/8 | L1 S1-S2 | Code civil, CASF ; chambres civiles | Matières Droit civil et Droit de la famille (L1) |
| Droit des biens | 7/8 | L1 S2 (P1, P2, Lille, Caen) ; L2-L3 ailleurs | Code civil livre II, Code rural ; chambres civiles | Matière Droit des biens (L1) |
| Droit des obligations (contrat, responsabilité, régime général) | 8/8 | L2 S3 et S4 | Code civil livre III ; chambres civiles et commerciale | Matière Droit des contrats (L2) ; « droit des obligations » et « régime général » trouvent cette matière dans la recherche du site |
| Droit administratif général | 8/8 | L2 S3-S4 | CRPA, CJA, CGCT ; Conseil d'État, Tribunal des conflits | Matière Droit administratif (L2) |
| Droit pénal général | 8/8 | L2 S3 | Code pénal ; chambre criminelle | Matière Droit pénal (L2) |
| Droit commercial, droit des affaires | 8/8 | L2 S3 | Code de commerce, CMF ; chambre commerciale | Matière Droit des affaires (L2) |
| Finances publiques | 8/8 | L2 S3-S4 | Constitution (art. 47, 47-2), CJF, LOLF (loi organique, source « lois ») ; Conseil constitutionnel | Matière Finances publiques (L2) |
| Droit des sociétés | 8/8 | L3 S5 (droit commun) et S6 (droit spécial) ; L2 S4 à Paris 1 et Toulouse | Code civil art. 1832 s., Code de commerce livre II, CMF ; chambre commerciale | **Nouvelle matière Droit des sociétés (L3)** |
| Droit du travail | 8/8 | L3 S5 (individuel) et S6 (collectif) | Code du travail, Préambule 1946 ; chambre sociale | Matière Droit social (L3) |
| Libertés fondamentales | 8/8 | L3 S5 | DDHC, Préambule 1946, Constitution, CSI ; Conseil constitutionnel, Conseil d'État | Matière Libertés fondamentales (L3). Charte des droits fondamentaux de l'Union (D98) ; Convention EDH en attente d'autorisation |
| Droit fiscal | 8/8 | L3 S6 | CGI, LPF, CIBS ; Conseil d'État, chambre commerciale | Matière Droit fiscal (L3) |
| Procédure civile, droit judiciaire privé | 8/8 | L3 S5 | CPC, COJ, CPCE ; chambres civiles | Matière Procédure civile (L3) |
| Procédure pénale | 7/8 | L3 S6 (Assas, Bordeaux, AMU, Lille) ; L2 à Paris 1 (S3) et Toulouse (S4) | CPP, Code de la justice pénale des mineurs, Constitution art. 66, DDHC art. 9 ; chambre criminelle, Conseil constitutionnel (QPC garde à vue) | **Nouvelle matière Procédure pénale (L3)** ; reste aussi consultée depuis Droit pénal |
| Contentieux administratif | 6/8 | L3 S5 ou S6, surtout en option droit public | CJA, CRPA, CGCT (déféré préfectoral) ; Conseil d'État | **Nouvelle matière Contentieux administratif (L3)** |
| Contrats spéciaux | 6/8 | L3 S5 | Code civil (vente, bail, mandat...), Code de la consommation | Dans Droit des contrats et Droit civil (recherche « contrats spéciaux ») |
| Droit administratif des biens (domaine, expropriation) | 5/8 | L3 S5 | CG3P, Code de l'expropriation, CGCT ; Conseil d'État | **Nouvelle matière Droit administratif des biens (L3)** |
| Droit public des affaires | 5/8 | L3 S5-S6 | Code de la commande publique, Code de commerce (concurrence), CG3P | Pas de matière propre ; sources présentes (Droit administratif, Droit des affaires) |
| Droit de l'environnement | 4/8 | L2-L3, souvent court | Code de l'environnement, Charte de l'environnement | Dans Droit administratif |
| Droit des sûretés | 3/8 | L3 S6 | Code civil livre IV (art. 2284 s.) | Dans Droit civil (recherche « sûretés ») |
| Droit pénal spécial | 2/8 | L2 S4 (Paris 1), L3 (Caen) | Code pénal livres II à IV | Dans Droit pénal |
| Droit de la consommation | 2/8 | L3 S6 | Code de la consommation ; chambres civiles | Dans Droit des contrats et Droit des affaires ; notions ajoutées au lexique |
| Régimes matrimoniaux, successions et libéralités | 1/8 chacune (Caen, Toulouse) | L3 S6 ; surtout master 1 | Code civil livre III titres I, II et V | Dans Droit de la famille (recherche « régimes matrimoniaux », « successions ») ; notions ajoutées au lexique |
| Sécurité sociale, protection sociale | 1/8 (Lille, 9 h en option) | L3 S5 ; surtout master 1 | Code de la sécurité sociale ; 2e chambre civile, chambre sociale | Dans Droit social ; notions ajoutées au lexique |
| Fonction publique, collectivités territoriales, urbanisme | 1/8 chacune | L3, option droit public | CGFP, CGCT, Code de l'urbanisme | Dans Droit administratif |
| Entreprises en difficulté, propriété intellectuelle | 0/8 | master 1 | Code de commerce livre VI, CPI | Sources présentes (Droit des affaires) |

Droit international public (8/8), droit de l'Union européenne (8/8) et droit international privé (3/8) : matières
Droit européen (L2) et Droit international (L3) depuis D98. Voir partie 5.

## 3. Ce qui a été ajouté (D97)

- Quatre matières, toutes avec des sources déjà dans l'index : Procédure pénale, Contentieux administratif,
  Droit des sociétés, Droit administratif des biens. Elles ne sont que des filtres sur des sources existantes :
  aucun passage n'a été ajouté au corpus.
- Pour chaque matière : une année de licence (la plus fréquente dans les maquettes), d'autres intitulés pour la
  recherche du site, deux sources principales affichées.
- Lexique (`api/lexique.py`) : notions de procédure pénale, de contentieux administratif, de droit des sociétés, de
  droit administratif des biens, et, rangées dans les matières existantes, de droit de la consommation, de régimes
  matrimoniaux, de successions et de sécurité sociale. Chaque article est vérifié en vigueur dans l'index
  (`tests/test_lexique_concordance.py::test_articles_du_lexique_existent`).
- Questions d'essai : `eval/cas_matieres_licence.yaml` (51 questions de cours, brouillon à relire par un enseignant).

## 4. Trouver une matière dans le site

- « Mes matières » : matières classées en Licence 1, Licence 2, Licence 3 ; l'année choisie par l'étudiant est
  signalée ; filtre par année ; champ de recherche qui lit l'intitulé, les autres intitulés des maquettes et le nom
  des sources (« procédure pénale » trouve Procédure pénale et Droit pénal, « régimes matrimoniaux » trouve Droit de
  la famille). Chaque carte montre ses sources principales.
- Recherche sans résultat (« histoire du droit ») : le site rappelle ce que Lexia couvre (droit français et traités de
  l'Union) et propose la matière « Toutes ».
- Les listes de choix de matière (assistant, dépôt de cours) sont groupées par année.

## 5. Droit international et européen (D98)

Historique : D72 (14 novembre) avait ajouté TUE, TFUE, Charte des droits fondamentaux de l'Union, Convention EDH avec
ses protocoles 1, 4, 6 et 7, et Charte des Nations unies (673 passages, `ingest/sources/traites.py`), deux matières,
un lexique et 14 questions d'essai. D74 (16 novembre) les a retirés : Lexia ne citait plus que le droit français. Le
18 novembre, après ce relevé des maquettes et le retour d'une étudiante, l'éditeur a demandé de les remettre (D98).

Besoin d'après les maquettes : droit de l'Union (8/8, institutionnel en L2, matériel ou contentieux en L3), droit
international public (8/8, introduction en L2, cours de fond en L3 S5), droit international privé (3/8, L3 S5),
Convention EDH (aucun cours propre, traitée dans les libertés fondamentales et le procès).

Conditions de réutilisation, lues le 18 novembre 2026 sur les sites officiels :

| Texte | Source officielle | Réutilisation | Dans Lexia |
|---|---|---|---|
| TUE, TFUE, Charte des droits fondamentaux de l'Union | Versions consolidées du JOUE C 202 du 7 juin 2016, dépôt Cellar de l'Office des publications (CELEX 12016M, 12016E, 12016P) | Réutilisation, y compris commerciale, avec mention de la source (décision 2011/833/UE de la Commission ; vérifiée sur eur-lex.europa.eu en D72) | **Oui** : 470 passages, matière Droit européen |
| Convention EDH et protocoles ratifiés | Texte publié par la Cour (echr.coe.int) | « sous réserve que leur source soit mentionnée (© ECHR-CEDH) », gratuitement et pour un usage privé, d'information ou d'éducation ; tout autre usage, notamment commercial, demande une autorisation écrite préalable (echr.coe.int/fr/disclaimer) | **Non** : prête (code, registre, questions d'essai), statut « en attente d'accès » |
| Charte des Nations unies | Page de l'ONU (un.org) | Copie autorisée « à des fins personnelles et non commerciales », sans droit de redistribuer ni de créer des ouvrages dérivés (un.org/fr/about-us/terms-of-use) | **Non** : prête, statut « en attente d'accès » |
| Règles françaises de droit international | Constitution (art. 52 à 55, 88-1 s.), Code civil (art. 3, 14, 15, 202-1, 309, 311-14, 370-3) | Déjà dans le corpus (Conseil constitutionnel, Licence Ouverte) | **Oui** : matière Droit international |
| Règlements européens de droit international privé (Rome I, Rome II, Bruxelles I bis...) | EUR-Lex | Comme les traités | Non : seules les versions d'origine ont la structure lue par l'import ; plusieurs ont été modifiés, il faut les versions consolidées (autre format) pour ne pas montrer un texte dépassé comme en vigueur |
| Jurisprudence de la CJUE | EUR-Lex ou curia.europa.eu | À vérifier (curia) ; EUR-Lex comme les traités | Non : volume important, import à écrire |
| Jurisprudence de la Cour EDH | HUDOC | Pas de téléchargement en masse trouvé (D72) ; mêmes conditions que le site de la Cour | Non |

Pourquoi la Convention EDH et la Charte de l'ONU ne sont pas actives : Lexia est un service payant, et ces deux sites
réservent la copie à un usage non commercial. Pour les activer, il faut soit l'accord écrit de la Cour (formulaire du
site) et de l'ONU, soit une autre source officielle réutilisable. Le décret n° 74-360 du 3 mai 1974, qui publie la
Convention au Journal officiel, n'est pas dans l'archive LEGI (D72). Une fois l'accord obtenu, il suffit de passer
leur statut à `actif` dans `registry/sources.yaml` et d'ajouter leurs noms à `api/textes.py` ; le lexique de D72 et les
questions `eval/cas_traites_en_attente.yaml` sont prêts.

Mise à jour du serveur : les traités ne viennent pas de la DILA, la mise à jour nocturne (D78) ne les connaissait
pas. Depuis D98, elle télécharge une fois toute source active du registre qui manque (`ingest/mise_a_jour.py`,
`ajouter_nouvelles`) : après la prochaine publication, la première nuit où la DILA publie une archive, le serveur
télécharge les trois traités depuis Cellar, calcule leurs 470 embeddings et les met dans son index. Un échec du
téléchargement n'arrête pas la mise à jour : il est retenté la nuit suivante. Pour ne pas attendre la nuit :
`ssh root@2.25.3.128 lexia-mise-a-jour --forcer` après la publication.

## 6. Matières sans texte à citer (proposition, rien n'est fait)

Enseignées partout, surtout en L1 : histoire du droit et des institutions (8/8), science politique et histoire des
idées politiques (8/8), économie (7/8), théorie et philosophie du droit (7/8), langues et anglais juridique (7/8),
méthodologie (6/8), sociologie du droit (3/8). Lexia ne peut pas les traiter comme les autres : il n'y a pas de
source officielle à citer et vérifier. Propositions :

- Ne pas créer de matière, et le dire dans la recherche du site quand l'étudiant les cherche (c'est déjà le cas : le
  message de recherche sans résultat).
- Pour l'histoire du droit, s'appuyer sur les cours déposés par l'étudiant : la fonction existe déjà, les réponses
  citeraient alors son cours et non un texte officiel.
- Pour la méthodologie (cas pratique, commentaire, dissertation), les modes méthode existent déjà (D54) ; on peut
  les rendre plus visibles depuis « Mes matières ».
