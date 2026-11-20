# Jurisprudence récente : sources gratuites et officielles (relevé du 20 novembre 2026)

Problème : `/api/fraicheur` affichait des décisions jusqu'au 16 et 17 septembre 2026 pour la Cour de cassation,
jusqu'au 16 octobre pour le Conseil constitutionnel, et jusqu'au 18 novembre pour le Conseil d'État. Le
comparatif avec Gemini Notebook et l'audit du 19 novembre (SRC-4) recommandent d'ajouter la jurisprudence
récente. Contrainte : aucune API payante.

Décision : D113 (`docs/decisions.md`).

## 1. Mesures

Toutes les mesures ont été faites le 20 novembre 2026, sur les pages officielles.

### Archives DILA (echanges.dila.gouv.fr/OPENDATA)

Contenu des archives globales du 8 novembre 2026, lu en entier (date de décision la plus récente) :

| Fonds | Contenu | Décision la plus récente | Décisions depuis le 1er septembre 2026 |
|---|---|---|---|
| CASS (arrêts publiés de la Cour de cassation) | 145 421 arrêts | 17 septembre 2026 | 61 |
| INCA (arrêts inédits de la Cour de cassation) | 387 902 arrêts | 11 septembre 2026 | 244 |
| CAPP (cours d'appel) | 73 050 décisions | 22 décembre 2023 | 0 |
| CONSTIT (Conseil constitutionnel) | 7 423 décisions | 16 octobre 2026 | 23 |
| JADE (Conseil d'État, pour comparaison) | archives quotidiennes | 19 novembre 2026 (archive du soir) | |

Cadence réelle de publication, d'après la liste des fichiers du 20 novembre et ses copies archivées par la
Wayback Machine (web.archive.org) depuis 2023 :

- **CASS et INCA** : une archive globale par an environ (19 novembre 2023, 13 juillet 2025, 8 novembre 2026), puis
  une archive d'ajouts **chaque lundi soir** (`CASS_<date>-<heure>.tar.gz`), sans interruption de novembre 2023 à
  juillet 2026 (dernière vue : `CASS_20260713`). Depuis la globale du 8 novembre 2026, aucune archive d'ajouts
  (les lundis 9 et 16 novembre sont passés sans fichier).
- **CONSTIT** : globale annuelle, puis des archives d'ajouts irrégulières, une à trois par mois (16 entre juillet
  2025 et mai 2026). Aucune depuis la globale du 8 novembre.
- **CAPP** : archives irrégulières jusqu'en juin 2026, mais le contenu s'arrête en décembre 2023 (les cours
  d'appel sont désormais publiées par Judilibre).

Conséquences :

1. D96 disait que la DILA ne publie pour ces fonds « que des archives globales espacées ». C'est inexact : les
   archives hebdomadaires existent, et la mise à jour nocturne de Lexia les télécharge déjà depuis D78 (le motif
   `CASS_<horodatage>.tar.gz` est reconnu par `ingest/mise_a_jour.lister`). Il n'y a rien de plus à en tirer.
2. Le retard vient de la source elle-même : la globale du 8 novembre contient des arrêts jusqu'au 17 septembre
   seulement. Le flux de la Cour de cassation vers la DILA semble arrêté depuis la mi-septembre ; Légifrance montre
   la même date (ci-dessous).

### Légifrance (site, même base que l'API Légifrance)

Recherche triée par date décroissante :

- jurisprudence judiciaire, Cour de cassation : arrêt le plus récent du **17 septembre 2026** ;
- jurisprudence constitutionnelle : décisions du **16 octobre 2026** (2026-1225 à 1227 QPC).

L'API Légifrance sert les mêmes fonds (JURI, CONSTIT, CETAT) : elle ne serait pas plus fraîche que les archives
DILA déjà lues, et elle demande un compte PISTE. Non retenue.

### Judilibre (Cour de cassation)

Le moteur Judilibre du site de la Cour de cassation (`courdecassation.fr/recherche-judilibre`), dont la fiche
data.gouv.fr de l'API dit qu'il expose les mêmes données, montrait le 20 novembre des arrêts **du 19 novembre 2026**
(deuxième et troisième chambres civiles, publiés au Bulletin). Retard : un jour.

Pas de téléchargement en masse sans compte : la fiche data.gouv.fr « API Judilibre » renvoie à l'API, « accessible
gratuitement après inscription » sur PISTE ; le site de la Cour est une page de recherche (JavaScript obligatoire),
pas un export.

### Site du Conseil constitutionnel

La page « Les dernières décisions » (`conseil-constitutionnel.fr/decisions`) montrait le 20 novembre les décisions
2026-1233 et 2026-1234 QPC **du jour même**. Décisions absentes de l'archive DILA et de Légifrance à cette date :
2026-1228 QPC (22 octobre), 2026-1229 QPC et 2026-1230/1231 QPC (23 octobre), 2026-1232 QPC (13 novembre),
2026-1233 et 2026-1234 QPC (20 novembre). Les pages se lisent sans JavaScript ni compte (texte dans
`div.field--name-field-contenu-original`, ECLI en fin de texte).

## 2. Tableau des sources

| Source | Fraîcheur réelle (20/11/2026) | Licence, réutilisation commerciale | Quotas | Compte ou clé |
|---|---|---|---|---|
| Archives DILA CASS | 17 septembre 2026 (2 mois) | Licence Ouverte 2.0 (data.gouv.fr) : oui, avec mention de la source et de la date | aucun | non |
| Archives DILA INCA | 11 septembre 2026 ; arrêts inédits, hors périmètre (D38) | Licence Ouverte 2.0 : oui | aucun | non |
| Archives DILA CAPP | décembre 2023 (figé) ; hors périmètre (D38) | Licence Ouverte 2.0 : oui | aucun | non |
| Archives DILA CONSTIT | 16 octobre 2026 (5 semaines) | Licence Ouverte 2.0 : oui | aucun | non |
| API Légifrance (PISTE) | celle de Légifrance : 17 septembre (Cour de cassation), 16 octobre (Conseil constitutionnel) | Licence Ouverte 2.0 et CGU de l'API Légifrance : oui | par seconde, minute et jour, visibles seulement dans le compte PISTE | compte PISTE et clé |
| **API Judilibre (PISTE)** | **19 novembre 2026 (J+1)** | Licence Ouverte 2.0 complétée par les CGU open data de la Cour de cassation (version du 9 février 2026) : oui, réutilisation commerciale permise sous conditions (ci-dessous) | par seconde, minute et jour, en requêtes ou en bande passante, fixés par application ou par méthode, visibles seulement dans le compte PISTE ; `/export` : 1 000 décisions par lot (10 par lot et 1 000 au total sans authentification, selon la spécification) | **compte PISTE nominatif et clé (KeyId)** |
| Judilibre hors API | consultation seule (site de la Cour) | | | pas d'export sans compte |
| **Site du Conseil constitutionnel** | **20 novembre 2026 (jour même)** | mentions légales : textes « librement reproductibles » à condition de citer le site comme source, de mentionner la nature et l'origine (date, intitulé, auteur) et de ne pas altérer les textes ; voir le point de vigilance | aucun publié ; une page de liste et quelques pages par nuit | **non** |

Conditions des CGU open data de la Cour de cassation (relues le 20 novembre 2026, articles V à XI) :

- ne pas altérer les décisions ; mentionner pour chaque décision la juridiction, la formation, le siège et la date ;
- mentionner que les données viennent de la base open data de la Cour de cassation et la date de leur dernière mise
  à jour ;
- tenir la base à jour (72 heures au plus entre deux mises à jour, recommandé) et retirer les décisions supprimées ;
- interdiction d'évaluer, comparer ou prédire les pratiques des magistrats et greffiers (article L. 111-13 du COJ) ;
- signaler à la Cour les défauts d'occultation (`anonymisation.sder.courdecassation@justice.fr`), occulter à titre
  provisoire les noms qu'on lui signale, et renvoyer vers la Cour toute demande d'occultation ou de levée ;
- l'API est en version bêta : ni disponibilité ni fraîcheur garanties.

## 3. Recommandation

1. **Cour de cassation : API Judilibre.** Seule source à jour (J+1), gratuite, réutilisation commerciale permise.
   Le code est prêt et **désactivé tant que la clé manque** (`ingest/sources/judilibre_api.py`). Périmètre
   identique à l'archive (D38) : arrêts publiés au Bulletin ou au Rapport, toutes chambres. Les arrêts déjà dans
   l'archive DILA (même ECLI, ou même date et même pourvoi) sont ignorés : l'archive reste la source principale,
   Judilibre ne comble que l'écart.
2. **Conseil constitutionnel : site du Conseil, activé directement.** Plus frais que tout le reste, sans compte.
   Six décisions entreront dans l'index la première nuit après publication.
3. **Conseil d'État** : rien à faire, JADE a des archives quotidiennes déjà lues (D78).
4. **Archives DILA** : rien de plus à exploiter, les archives hebdomadaires sont déjà lues dès qu'elles paraissent.
5. **API Légifrance** : non retenue (pas plus fraîche que la DILA).

Point de vigilance sur le site du Conseil constitutionnel : la section « Liens » de ses mentions légales ajoute que
« ces pages ne doivent cependant pas être utilisées à des fins commerciales ou publicitaires ». Elle porte sur les
liens hypertextes vers le site, la section « Reproduction » qui précède autorisant la reproduction des textes sans
réserve commerciale ; la Constitution est déjà reprise de ce site (`constitution_1958`, licence encore notée « à
vérifier » dans le registre). Les décisions sont par ailleurs des documents publics, reproduits sans modification,
avec leur lien et la mention « Site du Conseil constitutionnel ». Si l'éditeur préfère une confirmation écrite du
Conseil, la lecture du site se coupe sans toucher au code : `LEXIA_SITE_CONSEIL_CONSTITUTIONNEL=0` dans `.env` du
serveur (le cache est vidé et l'index revient à l'archive DILA seule la nuit suivante).

## 4. Ce qui a été fait (D113)

- `ingest/sources/judilibre_api.py` : synchronisation par `/export` (première fois : arrêts rendus depuis 180 jours
  avant l'archive DILA CASS ; ensuite : arrêts créés ou modifiés depuis la veille, moins 3 jours de recouvrement),
  retrait des arrêts supprimés (`/transactionalhistory`, `to_be_deleted`), une décision par fichier dans
  `data/raw/judilibre/decisions/`. Découpage comme l'archive : sommaire (titrage et sommaire), motifs, dispositif ;
  le zonage de Judilibre écarte l'introduction (composition de la formation, noms des magistrats) et les moyens
  annexés. Lien vers `courdecassation.fr/decision/<id>`, version « Open data de la Cour de cassation (Judilibre),
  mise à jour du <date> ».
- `ingest/sources/constit_site.py` : lecture de la page des dix dernières décisions ; seules les décisions absentes
  du cache et de l'archive DILA sont téléchargées (numéro lu dans le titre du lien) ; une décision entrée depuis dans
  l'archive est retirée du cache. Version « Site du Conseil constitutionnel, page lue le <date> ».
- `ingest/sources/cass.py` et `constit.py` : l'archive DILA d'abord, puis les décisions récentes absentes de
  l'archive, dans les mêmes sources (`judilibre`, `cass_criminelle`, `cass_sociale`, `cass_commerciale`,
  `decisions_conseil_constitutionnel`) : matières, filtres et recherche inchangés.
- `ingest/mise_a_jour.py` : étape « Jurisprudence récente » après les archives DILA. Un échec garde le cache de la
  veille, envoie un e-mail à l'administrateur et n'arrête jamais la mise à jour. Les décisions récentes entrent
  dans la signature `archives.txt` : une décision ajoutée, modifiée ou retirée suffit à reconstruire l'index.
- Index : la table `fraicheur` garde l'origine de la décision la plus récente de chaque source ; `/api/fraicheur`
  la renvoie (`"origine": "Open data de la Cour de cassation (Judilibre), mise à jour du 2026-11-21"`), ce qui
  répond à l'obligation de citer la source et la date de mise à jour. Le site affiche déjà la date (« Décisions
  jusqu'au ... ») sans changement ; l'origine n'y est pas encore affichée.
- Tests : `tests/test_jurisprudence_recente.py`, sans appel réseau. Les pages du Conseil constitutionnel sont de
  vraies pages enregistrées le 20 novembre. Les réponses de Judilibre sont construites au format de la
  spécification officielle (`JUDILIBRE-public.json` 1.2.5 du dépôt Cour-de-cassation/judilibre-search), faute de
  clé pour en enregistrer de vraies : à vérifier sur la première vraie réponse (bac à sable).

## 5. Démarches qui reviennent à l'éditeur

Aucun compte n'a été créé et aucune clé demandée.

1. Créer un compte PISTE nominatif : `https://piste.gouv.fr/component/apiportal/registration`, puis l'activer par
   le lien reçu par e-mail. Le portail PISTE répondait « 503 » le 20 novembre : réessayer plus tard.
2. Accepter les CGU de PISTE, puis celles de l'API Judilibre dans le catalogue (`consentement CGU API`, chercher
   « Judilibre »), pour la production (et le bac à sable pour un premier essai).
3. Dans l'application de production (menu Applications), cocher l'API Judilibre, enregistrer, puis relever la clé
   « KeyId » de l'application.
4. Relever les quotas : application, « API Sélectionnées », « Actions », « Consulter les quotas ». Une nuit
   ordinaire fait deux requêtes (un lot d'export, l'historique des suppressions) ; la première nuit, un ou deux
   lots de 1 000 arrêts (estimation : six mois d'arrêts publiés).
5. Ajouter dans `.env` du serveur (jamais dans le dépôt) : `JUDILIBRE_KEY_ID=<clé>`. Pour un essai sur le bac à
   sable : `JUDILIBRE_URL=https://sandbox-api.piste.gouv.fr/cassation/judilibre/v1.0`. Si PISTE impose OAuth à
   l'application de production (les CGU parlent d'« authentification par le protocole OAuth 2.0 », le guide du
   dépôt de la Cour d'un en-tête `KeyId`), le signaler : l'en-tête est à adapter dans `judilibre_api.client`.
6. Après publication, la nuit suivante lit Judilibre (ou `lexia-mise-a-jour --forcer`). Vérifier dans le journal
   `/var/log/lexia-mise-a-jour.log` la ligne « Judilibre : N arrêt(s) écrit(s) », puis `/api/fraicheur`.
7. Obligations qui deviennent celles de l'éditeur, réutilisateur au sens des CGU : citer dans les mentions légales
   de Lexia la base open data de la Cour de cassation (Licence Ouverte 2.0) et le site du Conseil constitutionnel ;
   ajouter au registre des traitements (RGPD) la réutilisation de décisions pseudonymisées ; transmettre à la Cour
   tout défaut d'occultation signalé et renvoyer les demandes d'occultation vers
   `occultations.courdecassation@justice.fr` ; ne jamais exploiter les noms de magistrats.
8. Conseil constitutionnel : décider s'il faut une confirmation écrite du Conseil (point de vigilance ci-dessus) ;
   sinon, rien à faire.

## 6. Sources consultées

- Liste des fichiers : `https://echanges.dila.gouv.fr/OPENDATA/CASS/`, `INCA/`, `CAPP/`, `CONSTIT/`, `JADE/`, et
  leurs copies sur `web.archive.org` (2023 à novembre 2026).
- Spécification de l'API : `https://github.com/Cour-de-cassation/judilibre-search` (`public/JUDILIBRE-public.json`,
  `README.md`, `src/taxons/`).
- CGU open data de la Cour de cassation : `https://www.courdecassation.fr/conditions-generales-dutilisation-pour-la-reutilisation-des-donnees-judiciaires-ouvertes-open-data`.
- Fiche data.gouv.fr « API Judilibre » (API data.gouv.fr, `dataservices`).
- Recherche Judilibre : `https://www.courdecassation.fr/recherche-judilibre`.
- Légifrance, recherche triée par date : fonds JURI et CONSTIT.
- Conseil constitutionnel : `https://www.conseil-constitutionnel.fr/decisions` et
  `https://www.conseil-constitutionnel.fr/mentions-legales`.
