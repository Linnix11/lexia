# Lexia et NotebookLM (devenu Gemini Notebook) : comparatif pour un étudiant en licence de droit

État au 19 novembre 2026, refait de zéro.

- **Lexia** : branche `main` au commit 1442ad6 (décisions D1 à D103), lue dans le dépôt, et site
  https://lexia-axionstudio.cloud interrogé le même jour (`/api/sante`, `/api/formules`, `/api/matieres`,
  `/api/fraicheur`, `/api/config`, codes de réponse des routes). Ce qui n'est pas dans `main` ou pas en ligne est
  marqué « prévu » ou « non publié ».
- **Google** : uniquement des pages officielles (centre d'aide, blog, pages Google One et Workspace) lues le
  19 novembre 2026, liens en partie 7. Rien n'est affirmé de mémoire. Quand une page est muette, c'est écrit.

## 0. Avant de comparer

- **NotebookLM s'appelle désormais Gemini Notebook.** Annonce du 16 juillet 2026 sur le blog de Google
  (« We're renaming NotebookLM to Gemini Notebook », même produit autonome). notebooklm.google redirige vers
  notebook.google ; l'aide est passée sous support.google.com/gemininotebook (en français, elle s'appelle encore
  « Aide NotebookLM »). La suite écrit « Gemini Notebook ».
- Les deux outils ne font pas la même chose. Gemini Notebook est un outil général : il travaille sur les documents
  que l'étudiant lui donne. Lexia est un outil spécialisé : il travaille sur un corpus juridique officiel déjà
  chargé, et accessoirement sur les cours de l'étudiant.

## 1. Lexia aujourd'hui (en ligne et dans `main`)

### Sources

- Environ 916 000 passages officiels (916 158 dans l'index du 17 novembre, `docs/cours-libres.md`) : Constitution
  de 1958, DDHC, Préambule de 1946, Charte de l'environnement, 36 codes, lois et ordonnances en vigueur, Conseil
  constitutionnel (DC, QPC, L), Cour de cassation (arrêts publiés complets depuis 2000, sommaires officiels de 1960
  à 1999), Conseil d'État et Tribunal des conflits (Lebon, tables depuis 2010), traités de l'Union (TUE, TFUE,
  Charte des droits fondamentaux, D98).
- 20 matières classées L1, L2, L3 (vérifié en ligne : 20), dont Droit européen et Droit international.
- Hors corpus : jurisprudence de la CJUE et de la Cour EDH ; Convention EDH et Charte des Nations unies prêtes mais
  désactivées faute d'autorisation écrite (D98) ; décisions non publiées et cours administratives d'appel (D38) ;
  manuels et doctrine (D10).

### Fraîcheur, à dire avec précision

- Mise à jour automatique chaque nuit depuis les archives quotidiennes de la DILA (D78). En ligne le 19 novembre :
  codes et lois au 18 novembre 2026, Conseil d'État au 17 novembre 2026, `corpus_a_jour: true`.
- **Mais** la DILA ne publie pas d'archive quotidienne pour la Cour de cassation et le Conseil constitutionnel
  (D95, B7) : décisions jusqu'au 16 ou 17 septembre 2026 pour la Cour de cassation, jusqu'au 16 octobre 2026 pour le
  Conseil constitutionnel. Le site l'affiche (« Décisions jusqu'au ... ») et prévient sous une réponse quand une
  source citée date de plus de 30 jours (D96).
- Donc : « textes mis à jour chaque nuit » est vrai ; « toute la jurisprudence à jour chaque nuit » est faux.

### Réponses

- Cinq modes : Expliquer, Fiche, Cas pratique, Commentaire d'arrêt, Dissertation, avec des rubriques imposées
  (cas pratique : faits et qualification, problème de droit, majeure, mineure, conclusion ; D66). Niveau adapté au
  semestre choisi, de L1 S1 à L3 S6 (D49). Réponse directe de 1 à 3 phrases en tête (D89).
- Citations contrôlées par le serveur après le modèle : une source citée doit être un des extraits fournis, une
  affirmation de droit positif sans source est retirée, un numéro d'article, de décision ou de pourvoi absent des
  extraits fait retirer l'élément ; sans affirmation sourcée, Lexia s'abstient (D22).
- Chaque citation ouvre le passage, avec son lien officiel et ses dates de vigueur ; un clic vérifie la version
  en vigueur (`/sources/{id}/vigueur`). 26 anciens numéros du Code civil (1134, 1382...) sont reliés aux articles
  actuels (D53). Articles à abrogation différée et états DILA contradictoires recalculés par les dates (D61, D95).
- Références reconnues : « article X du code Y », abréviations, lois par numéro ou date, pourvois, articles bis,
  R*, LO ; 20 grands arrêts judiciaires et 44 administratifs par leur nom (D39, D43, D90, D95).
- Refus de quatre demandes de pur conseil (rédiger un courrier, prédire l'issue, chiffrer, décider des démarches) ;
  des faits racontés à la première personne sont expliqués avec un rappel (D77).
- Modèles : Gemini (`gemini-3.5-flash-lite`), secours Groq (D83, D76). Évaluation sur des jeux internes
  (187 questions de cours, cas pratiques, grands arrêts) ; **la notation par un enseignant n'est pas faite**
  (D11, D87).

### Révision

- Questionnaires de 1 à 15 questions : QCM, vrai ou faux, questions ouvertes ; correction automatique ou par le
  modèle, avec les sources (`api/quiz.py`).
- Fiches : le mode Fiche enregistre la réponse dans « Fiches & révisions », gardée dans le navigateur seulement
  (100 au plus), export Markdown (D85, D94).
- **Non publié** : cartes à retourner avec répétition espacée, sur la branche `claude/fiches-a-retourner`
  (commit d7262db), absente de `main`.
- Absents du code : résumé audio, résumé vidéo, carte mentale, infographie.

### Bibliothèque et cours récupérés

- Bibliothèque : annales (liens vers les sujets publiés par les facultés, D40), sources officielles, et une barre
  de recherche qui cherche dans les cours récupérés (titres puis texte), les annales et les sources
  (`RechercheBibliotheque.tsx`).
- Page « Cours récupérés » (D103, en ligne, réservée aux comptes) : 1 149 fiches de service-public.gouv.fr
  (781 Particuliers, 368 Entreprendre) sous Licence Ouverte, dans 17 matières, avec auteur, source, licence, date
  et lien vers l'original, et l'avertissement « Ils ne sont pas rédigés par Lexia et peuvent contenir des erreurs
  ou être dépassés ». Index à part (10 508 passages) : **jamais utilisé dans les réponses**, une fiche ne peut ni
  remplacer ni contredire un article.
- Prévu, bloqué : fiches de vie-publique.fr (export demandé à la DILA).

### Cours déposés

- Formats : PDF, Word (.docx), OpenDocument (.odt), PowerPoint (.pptx), texte (.txt, .md) ; 20 Mo par fichier
  (`api/extraction.py`, `api/cours.py`). Numérotation Word, notes de bas de page et plan conservés (D93).
- 3, 30 ou 100 cours selon la formule ; plusieurs cours interrogeables ensemble ; « Mon cours uniquement » ou
  « Mon cours + textes officiels » (D57, D93). Un ancien numéro du Code civil cité dans un cours est signalé avec
  l'article actuel (D93).
- Pas d'OCR : un PDF dont plus de la moitié des pages est sans texte (scan) est refusé.

### Mobile

- Site adapté au téléphone et installable sur l'écran d'accueil (manifeste vérifié en ligne, D101).
- Application iOS : en préparation hors du dépôt, non publiée (D101). Pas d'application Android.

### Compte et accueil

- Inscription avec prénom et nom (D102) ; l'espace dit « Bonjour, Prénom. » ; carte « Pour reprendre »,
  dernière matière gardée (D100). Prénom et nom jamais envoyés au modèle (test).
- Âge : 15 ans et plus, déclaré à l'inscription (D92).

### Prix (en ligne le 19 novembre 2026)

| Formule | Prix | Questions par jour | Questionnaires par jour | Cours déposés |
|---|---|---|---|---|
| Gratuit (compte requis) | 0 € | 10 | 2 | 3 |
| Étudiant | 4,99 € par mois | 100 | 20 | 30 |
| Intensif | 9,99 € par mois | 300 | 100 | 100 |

Paiement Stripe codé (D86, D91) mais **inactif en ligne** (`paiement: false`, route `/api/paiement/etat` en 404) :
la formule se demande par e-mail et s'active à la main.

### Données personnelles et hébergement

- Serveur chez Hostinger (société à Chypre ; emplacement du centre de données « à vérifier » dans le registre),
  trafic par Cloudflare (D83).
- Mots de passe en scrypt, double authentification facultative, secrets chiffrés, effacement réel des comptes et
  cours supprimés (D67, D68, D93, D99).
- **Point faible actuel** : la configuration en ligne indique `gemini_payant: false`. La politique de
  confidentialité affichée le dit : au niveau gratuit de l'API Gemini, « Google peut utiliser les questions et les
  réponses pour améliorer ses produits, et des relecteurs humains peuvent les lire », et elle signale que c'est
  à régulariser avant toute ouverture (les conditions de Google réservent le niveau payant aux services destinés à
  l'Espace économique européen, D50, D83). Les passages des cours déposés transmis au modèle sont concernés aussi.
  Secours Groq aux États-Unis, sans conservation (« Zero Data Retention »).

## 2. Gemini Notebook aujourd'hui (pages Google du 19 novembre 2026)

### Fonctions

- **Sources** : PDF, Word, PowerPoint, Google Docs, Slides, Sheets, texte, Markdown, CSV, ePub, images, audio
  (transcrit, français compris), pages web (texte seul, pas de pages payantes), vidéos YouTube publiques sous-titrées,
  texte collé, livres Play Books, chats Gemini. Fichiers Drive synchronisés automatiquement.
- **Recherche intégrée** : « Fast Research » (Web ou Drive) et « Deep Research » (des centaines de sites, rapport,
  import des sources ; 18 ans et plus). Chat « agentique » expérimental : recherche web, exécution de code, création
  de fichiers, avec ou sans sources.
- **Citations** : le chat cite des passages des sources ; survol pour lire, clic pour ouvrir le passage dans son
  contexte. Google écrit que les réponses du chat n'utilisent que les sources, et qu'il ne répond pas si
  l'information n'y est pas.
- **Sorties d'étude** : résumés audio (4 formats, plus de 80 langues dont le français d'Europe ; mode interactif et
  format long en anglais seulement), résumés vidéo (Explainer et Short en français ; Cinematic en anglais et pour
  les 18 ans et plus), quiz et fiches à retourner (difficulté, nombre, bouton « Explain », suivi de progression,
  export CSV), cartes mentales, rapports et guides d'étude, infographies, présentations, tableaux.
- **Mobile** : applications Android et iOS, disponibles en France, avec moins de fonctions que le Web (pas de
  cartes mentales, rapports ni réglage du chat ; sources limitées à PDF, site, YouTube, audio, texte) ; résumés audio
  hors ligne.

### Limites

- Par source : 500 000 mots ou 200 Mo, sans limite de pages.
- Comptes personnels : sans forfait 100 notebooks et 50 sources par notebook ; AI Plus 200 et 100 ; AI Pro 500 et
  300 ; Ultra jusqu'à 600 sources.
- Quotas d'usage des comptes personnels non chiffrés : limites « de calcul » rechargées toutes les 5 heures jusqu'à
  une limite hebdomadaire, ×2 (Plus), ×4 (Pro). Des chiffres par jour ne sont publiés que pour Workspace (par
  exemple, niveau standard : 50 chats, 3 résumés audio, 10 quiz ou fiches par jour). Une autre page parle encore de
  quotas quotidiens : les pages se contredisent. Toutes ces limites sont « susceptibles de changer ».

### Formules et prix en France (pages affichant « France », en euros par mois)

- Gratuit avec un compte Google.
- Google AI Plus : 4,99 € (400 Go) ; une variante à 9,99 € (2 To) est aussi affichée.
- Google AI Pro : 21,99 €. Google AI Ultra : à partir de 99,99 €.
- **Offre étudiante en France** : Google AI Plus à 0 € pendant 12 mois, à prendre au plus tard le
  31 décembre 2026 ; ou Google AI Pro à 5,49 € par mois (−75 %) pendant 4 ans au plus. Conditions : 18 ans au
  moins, étudiant du supérieur vérifié par SheerID, compte Google personnel, moyen de paiement.
- **Éducation** : Gemini Notebook inclus sans frais dans toutes les éditions Google Workspace for Education,
  activé par l'administrateur de l'établissement.

### Français

- Langue de sortie réglable (chat, guides, audio, vidéo), par défaut celle du compte ; français d'Europe proposé.
- Interface web en français : pas de phrase officielle trouvée ; l'application mobile liste le français d'Europe.

### Données et entraînement

- Comptes personnels : les contenus ne servent pas à entraîner Gemini Notebook, sauf si l'utilisateur envoie un
  avis (pouce) : la conversation, les sources et les sorties peuvent alors être relues par des personnes, après
  dissociation du compte, et gardées jusqu'à 3 ans.
- Workspace et Workspace for Education : ni relecture humaine ni entraînement.
- Hébergement dans l'Union : seule l'offre entreprise sur Google Cloud mentionne une région « eu ». Pour les
  comptes personnels et Workspace : non trouvé sur les pages officielles.

### Mises en garde de Google

- « Gemini Notebook can make mistakes » ; consulter un professionnel pour les questions juridiques. Résumés, quiz,
  fiches et cartes mentales « may contain inaccuracies ».
- Aucune page d'aide ne parle de corpus juridique, de version en vigueur ou de méthode juridique.

## 3. Tableau point par point

| Critère | Lexia | Gemini Notebook | Avantage |
|---|---|---|---|
| Sources | Corpus officiel prêt à l'emploi, environ 916 000 passages (codes, lois, Constitution, CC, Cass., CE, traités UE), filtré par matière. Textes et CE à jour chaque nuit ; Cass. et CC à la date de la dernière archive DILA (septembre et octobre 2026), affichée | Uniquement ce que l'étudiant ajoute (50 sources par notebook en gratuit, 500 000 mots chacune), ou trouve par la recherche web intégrée. Aucun texte juridique fourni | Lexia pour le droit positif ; Gemini Notebook pour la variété des supports personnels |
| Citations vérifiables | Chaque citation renvoie au texte officiel daté, avec lien Légifrance ou juridiction ; contrôle serveur qui retire les affirmations non sourcées et les numéros inventés, abstention sinon | Citation cliquable vers le passage de la source déposée ; la citation est exacte par rapport au document, pas par rapport au droit | Lexia : la citation prouve la règle, pas seulement le document |
| Risque de texte abrogé | Seules les versions en vigueur sont cherchées ; version vérifiable en un clic ; anciens numéros du Code civil reliés aux actuels, y compris dans un cours déposé. Reste : jurisprudence récente de Cass. et CC absente pendant 2 à 3 mois | Aucun mécanisme décrit : un cours ou un PDF ancien est repris tel quel | Lexia, nettement |
| Méthode juridique | Modes cas pratique, commentaire d'arrêt, dissertation, fiche, avec rubriques imposées et niveau par semestre ; 64 grands arrêts reconnus par leur nom. Qualité non encore notée par un enseignant | Styles de chat génériques (« Learning Guide », personnalisé) ; rien de propre au droit | Lexia |
| Quiz et révision | Quiz QCM, vrai ou faux, questions ouvertes, corrigés avec sources ; fiches dans le navigateur (100), export Markdown. Pas de cartes à retourner en ligne (branche non publiée) | Quiz et fiches à retourner avec difficulté et suivi de progression, export CSV ; résumés audio et vidéo en français, cartes mentales, guides d'étude, infographies | Gemini Notebook |
| Dépôt de cours | PDF, Word, ODT, PowerPoint, texte ; 20 Mo ; 3, 30 ou 100 cours ; « mon cours seul » ou « mon cours + textes officiels » ; pas d'OCR | Bien plus de formats (Google Docs, images, audio, YouTube, web, ePub) ; 200 Mo ou 500 000 mots par source ; synchronisation Drive | Gemini Notebook pour le dépôt ; Lexia pour croiser le cours avec le droit en vigueur |
| Mobile | Site adapté et installable ; pas d'application publiée | Applications iOS et Android (fonctions réduites), audio hors ligne | Gemini Notebook |
| Prix | Gratuit : 10 questions et 2 quiz par jour ; 4,99 € et 9,99 € par mois ; paiement en ligne pas encore actif | Gratuit, quotas non chiffrés mais larges en apparence ; AI Plus offert 12 mois aux étudiants de 18 ans et plus en France (jusqu'au 31 décembre 2026), puis 4,99 € ; AI Pro étudiant 5,49 € | Gemini Notebook pour le prix ; Lexia reste bon marché pour un outil spécialisé |
| RGPD et hébergement | Données de compte minimales, prénom et nom jamais envoyés au modèle, sécurité soignée. **Aujourd'hui** : API Gemini au niveau gratuit (Google peut utiliser questions et réponses, relecture humaine possible, irrégulier pour l'EEE selon les conditions Google) ; centre de données Hostinger à vérifier ; Groq aux États-Unis | Compte personnel : pas d'entraînement sauf avis envoyé ; Education : ni relecture ni entraînement. Région de stockage non publiée pour les particuliers | Gemini Notebook tant que Lexia n'est pas passée au niveau payant ; à rééquilibrer ensuite |
| Ergonomie | Tout en français, pensé pour la licence (matières par année, semestre, modes) ; un seul usage, rien à préparer : on pose la question | Outil riche et général ; il faut constituer et entretenir ses notebooks ; certaines fonctions en anglais ou réservées aux 18 ans et plus | Lexia pour démarrer vite en droit ; Gemini Notebook pour la richesse |
| Âge | 15 ans et plus | Âge du consentement du pays pour un compte personnel ; 18 ans et plus pour l'offre étudiante et plusieurs fonctions | Lexia (plus large pour les L1 mineurs) |

## 4. Conclusions

### Où Lexia gagne

- **Le droit positif sans rien préparer** : la règle vient du texte officiel en vigueur, pas d'un polycopié qui
  peut dater d'avant la réforme de 2016.
- **Des citations qui prouvent la règle** : contrôle serveur, abstention plutôt qu'invention, version en vigueur
  vérifiable.
- **La méthode de la licence** : cas pratique, commentaire d'arrêt, dissertation, avec les rubriques attendues.
- **Le croisement du cours et des textes** : un cours déposé est confronté au droit actuel, un ancien numéro
  est signalé.
- **L'accès dès 15 ans** et une interface entièrement en français.

### Où Gemini Notebook gagne

- **Le prix** : gratuit, et AI Plus offert 12 mois aux étudiants majeurs en France.
- **La révision** : fiches à retourner, résumés audio et vidéo en français, cartes mentales, guides d'étude.
- **Les supports** : presque tous les formats, scans d'images compris, YouTube, audio, web, Drive.
- **Le mobile** : applications iOS et Android.
- **Les données aujourd'hui** : pas d'entraînement pour un compte personnel sans avis envoyé, alors que Lexia
  tourne encore sur le niveau gratuit de l'API Gemini.
- **La notoriété et la solidité** d'un produit Google.

### Ce que Lexia devrait ajouter, classé

Classement par intérêt pour l'étudiant, puis par coût (faible d'abord).

| Rang | Ajout | Intérêt pour l'étudiant | Coût | Remarque |
|---|---|---|---|---|
| 1 | Passer l'API Gemini au niveau payant (`GEMINI_NIVEAU_PAYANT=1`) | Très élevé (confidentialité, conformité) | Faible (environ 0,0021 $ par question, D83) | Préalable à toute vente et à tout argument sur les données |
| 2 | Publier les cartes à retourner avec répétition espacée | Élevé | Faible (branche prête) | Comble le plus gros manque en révision |
| 3 | Faire noter les réponses par un enseignant (`eval/cas_pratiques_enseignant.yaml`) | Élevé (confiance) | Moyen (temps humain) | Seule mesure indépendante de la qualité |
| 4 | Jurisprudence récente de la Cour de cassation et du Conseil constitutionnel (API Judilibre, site du Conseil) | Élevé en L2-L3 | Moyen | Supprime le retard de 2 à 3 mois |
| 5 | Activer le paiement Stripe | Moyen (souscription sans e-mail) | Faible (code fait, D86, D91) | Après le rang 1 et le médiateur |
| 6 | Fiches et quiz gardés dans le compte, entre appareils | Moyen | Moyen | Aujourd'hui, navigateur seul |
| 7 | OCR des cours scannés | Moyen | Moyen | Beaucoup de polycopiés sont scannés |
| 8 | Plan visuel (carte mentale) tiré d'une fiche ou d'une dissertation | Moyen | Moyen | Le plan en deux parties s'y prête |
| 9 | Publication de l'application iOS, puis Android | Moyen | Élevé (règles App Store pour les formules, D101) | Le site installable couvre déjà l'essentiel |
| 10 | Résumé audio d'une fiche | Faible à moyen | Élevé (synthèse vocale, qualité en français) | Gemini Notebook fait déjà très bien cela |
| 11 | Jurisprudence de la CJUE et de la Cour EDH | Moyen en L2-L3 | Élevé (licences, D98) | Convention EDH en attente d'autorisation |

### Arguments vrais et vérifiables pour la page d'accueil

Sans nommer de concurrent et sans dénigrement. Chaque phrase est vérifiable dans le site ou le dépôt au
19 novembre 2026.

- « Plus de 900 000 passages officiels : codes, lois, Constitution, Cour de cassation, Conseil d'État,
  Conseil constitutionnel et traités de l'Union. »
- « Codes et lois mis à jour chaque nuit depuis les données ouvertes de la DILA ; la date de chaque source est
  affichée. »
- « Chaque réponse cite ses sources, avec le texte officiel à un clic. Une affirmation sans source est retirée. »
- « Vérifiez en un clic qu'un article est en vigueur. Les anciens numéros du Code civil sont reliés aux
  nouveaux. »
- « Les méthodes de la licence : cas pratique, commentaire d'arrêt, dissertation. »
- « 20 matières, de la L1 à la L3, et un niveau d'explication adapté à votre semestre. »
- « Déposez vos cours (PDF, Word, PowerPoint, OpenDocument) et confrontez-les au droit en vigueur. »
- « Gratuit avec un compte : 10 questions et 2 questionnaires par jour. »
- « Ouvert dès 15 ans. »

À ne pas écrire aujourd'hui :

- « Jurisprudence à jour chaque nuit » (faux pour Cass. et CC).
- « Vos données ne servent jamais à entraîner une IA » ou « plus respectueux de vos données » (faux tant que le
  niveau gratuit de Gemini est utilisé).
- « Données hébergées en France » (non vérifié).
- « Sans erreur », « fiable à 100 % », « validé par des enseignants » (pas de notation enseignant).
- « Fiches à retourner », « application mobile », « paiement par carte » (non publiés).
- Toute comparaison nommée avec Gemini Notebook : les prix et quotas de Google changent souvent et une comparaison
  publicitaire doit rester objective et vérifiable à tout moment.

## 5. Ce qui a changé depuis le comparatif précédent

Ancien document : branche `claude/comparatif-notebooklm` (commit 59a69ff), fondé sur `main` au commit 9157a57.

- Lexia : page « Cours récupérés » passée de 781 à 1 149 fiches avec le volet Entreprendre (D103) ; barre de
  recherche de la Bibliothèque ; prénom et nom à l'inscription (D102) ; cartes à retourner faites mais non
  publiées. Rien d'autre de nouveau en ligne.
- Google : variante AI Plus 2 To à 9,99 € affichée ; offre étudiante AI Pro à 5,49 € par mois pendant 4 ans ;
  export CSV des fiches ; chat « agentique » (code, fichiers) annoncé avec le changement de nom.

## 6. Limites de ce document

- Prix Google vus sur des pages réglées sur la France, sans compte connecté ; quotas des comptes personnels non
  chiffrés par Google ; pages officielles parfois contradictoires (quotas quotidiens ou fenêtres de 5 heures).
- Disponibilité en France des fonctions annoncées le 16 juillet 2026 (exécution de code) non confirmée.
- Nombre de passages de Lexia tiré de l'index du 17 novembre, non recompté sur le serveur ; emplacement du centre
  de données Hostinger non vérifié.
- Qualité des réponses des deux outils non mesurée par un tiers.

## 7. Sources Google (consultées le 19 novembre 2026)

- Changement de nom : https://blog.google/innovation-and-ai/products/gemini-notebook/notebooklm-gemini-notebook/
- Présentation et âge : https://support.google.com/gemininotebook/answer/16164461
- Sources acceptées, Fast et Deep Research : https://support.google.com/gemininotebook/answer/16215270
- Chat, citations, fonctions agentiques : https://support.google.com/gemininotebook/answer/16179559
- FAQ (taille des sources, réponses limitées aux sources) : https://support.google.com/gemininotebook/answer/16269187
- Résumés audio : https://support.google.com/gemininotebook/answer/16212820
- Résumés vidéo : https://support.google.com/gemininotebook/answer/16454555
- Quiz et fiches : https://support.google.com/gemininotebook/answer/16958963
- Cartes mentales : https://support.google.com/gemininotebook/answer/16212283
- Rapports : https://support.google.com/gemininotebook/answer/18323649
- Application mobile : https://support.google.com/gemininotebook/answer/16296687
- Langues de sortie : https://support.google.com/gemininotebook/answer/16261963
- Forfaits, limites de notebooks et de sources, données : https://support.google.com/gemininotebook/answer/16213268
- Limites d'usage : https://support.google.com/gemininotebook/answer/17670842
- Workspace et quotas chiffrés : https://support.google.com/gemininotebook/answer/16337734
- Avis et relecture humaine : https://support.google.com/gemininotebook/answer/17004255
- Prix Google AI en France : https://one.google.com/about/google-ai-plans/?hl=fr&gl=FR
- Forfaits Google One : https://one.google.com/about/plans?hl=fr&gl=FR
- Pays des forfaits Google AI : https://support.google.com/gemini/answer/16275805
- Offre étudiante : https://one.google.com/ai-student?hl=fr-FR&gl=FR
- Conditions de l'offre étudiante : https://one.google.com/offer/studentoffer8?hl=fr-FR
- Pays et conditions des offres étudiantes : https://support.google.com/googleone/answer/17422238?hl=fr-FR
- Workspace, prix : https://workspace.google.com/pricing?hl=fr
- Workspace for Education : https://knowledge.workspace.google.com/admin/getting-started/editions/quickstart-guide-to-gemini-and-gemini-notebook-for-education?hl=en
- Région des données (Google Cloud) : https://docs.cloud.google.com/gemini/enterprise/docs/locations
