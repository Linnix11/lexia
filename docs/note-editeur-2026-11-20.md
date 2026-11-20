# Décisions de l'éditeur après l'audit du 19 novembre 2026 (lots site et juridique)

Note préparée le 20 novembre 2026 avec la décision D108. Rien n'est tranché ici : chaque point attend un choix de
l'éditeur. Ce n'est pas un avis d'avocat.

## 1. Âge minimum : 15 ans ou 18 ans (JUR-2, JUR-15)

Constat. Lexia accepte les inscriptions dès 15 ans (case « J'ai 15 ans ou plus », CGU article 3). Les conditions de
l'API Gemini interdisent un service susceptible d'être utilisé par des moins de 18 ans (« Age Requirements »,
https://aistudio.google.com/docs/terms, lu par l'audit le 19/11). Le niveau payant de Gemini ne lève pas cette
règle. Risque : coupure de la clé, sans recours.

Choix possibles :

- A. Passer à 18 ans : case « J'ai 18 ans ou plus », CGU article 3 et résumé, registre T1. Simple et sûr vis-à-vis de
  Google ; ferme Lexia aux bacheliers de 17 ans qui entrent en L1.
- B. Garder 15 ans et changer de fournisseur pour les mineurs, par exemple Vertex AI (Google Cloud), dont les
  conditions sont à vérifier ; travail technique et contractuel à prévoir.
- C. Garder 15 ans en l'état : non recommandé, contraire aux conditions de Gemini.

Déjà fait (D108) : l'article des CGU sur les mineurs cite désormais l'article 1146 du Code civil (incapacité du
mineur non émancipé) et l'article 1148 (actes courants), vérifiés dans LEGI.

Reste à faire quel que soit le choix : enregistrer la case d'âge cochée et la version des CGU acceptée à
l'inscription. Cela touche `api/auth.py` (modèle de la requête d'inscription), tenu par la session sécurité et
serveur : à lui confier.

## 2. Vente par e-mail sans médiateur, SIRET et téléphone de l'hébergeur (JUR-3, JUR-4, JUR-8)

Constat. Le bouton « Demander cette formule » de la page Tarifs est actif : la vente par e-mail est ouverte. Or :

- aucun médiateur de la consommation n'est désigné (`LEGAL_MEDIATEUR` vide) : obligation de C. consom. L. 612-1,
  amende jusqu'à 3 000 euros (L. 641-1) ; liste et tarifs dans `docs/avant-la-vente.md`, section 3 ;
- le numéro d'immatriculation (SIRET) est « en cours d'attribution » et le téléphone de l'hébergeur manque
  (`LEGAL_HEBERGEUR_TELEPHONE`) : mentions de la LCEN, article 1-1 ; voir `docs/avant-la-vente.md`, section 2.

Choix possibles :

- A. Retirer le bouton de demande par e-mail jusqu'à l'adhésion au médiateur et à l'immatriculation (le code peut
  l'afficher seulement quand `LEGAL_MEDIATEUR` et `LEGAL_SIREN` sont renseignés : une demi-heure de travail).
- B. Garder le bouton et adhérer au médiateur rapidement. Tarifs relevés le 17/11 dans `docs/avant-la-vente.md` :
  25 euros HT pour 3 ans (SMP) ou 40 euros HT par an (MCP) sous un petit chiffre d'affaires, médiation facturée en plus
  si elle a lieu ; à reconfirmer avant d'adhérer.

Déjà fait (D108) : la confirmation du contrat par e-mail reprend l'identité de l'éditeur, son adresse, son
immatriculation, son e-mail, son téléphone et le médiateur dès qu'ils sont renseignés dans la configuration, ainsi
que la garantie légale de conformité ; le corps du mail de demande contient la demande expresse d'accès immédiat
(L. 221-25) et la version des CGU.

Fait le 20 novembre (D111) : la confirmation du contrat joint le texte complet des CGU de la version acceptée
(fichier texte produit à partir de `web/src/site/Legal.tsx`).

## 3. Avis d'un avocat sur l'analyse de faits personnels (D77, JUR-5, EDI-6)

Constat. Selon D77, Lexia explique le droit applicable à des faits racontés à la première personne (« mon
propriétaire garde ma caution »), avec un rappel qu'une situation réelle doit être examinée par un professionnel. Dans
un service payant, cela peut ressembler à une consultation juridique rémunérée par une personne non autorisée (loi
71-1130, article 54, non relu par l'audit).

Déjà fait (D108) : le texte de l'accueil, qui disait l'inverse (« ne donne pas de conseil sur une situation
personnelle »), décrit maintenant le comportement réel. Le comportement lui-même (`api/prompts.py`, règle 8) n'a pas
changé.

Questions à poser à l'avocat :

1. Une analyse générale de faits racontés par l'utilisateur, avec ce rappel, est-elle une consultation juridique au
   sens de l'article 54 quand l'utilisateur paie une formule ?
2. Faut-il, pour les comptes payants, reformuler ces faits en exercice neutre (« Pierre loue un appartement… ») ?
3. Le nom demandé à tous à l'inscription (D102) est-il compatible avec la minimisation (RGPD art. 5.1.c), alors
   qu'il ne sert qu'à la rétractation (JUR-13) ? Option : le demander seulement au paiement ou à la rétractation.
4. La rétractation en ligne derrière une connexion au compte respecte-t-elle « directement accessible »
   (C. consom. D. 221-5) ?
5. Relecture générale des CGU (version du 20 novembre 2026) et de la politique de confidentialité.

## 4. Autres actions de l'éditeur rappelées par l'audit

- Gemini au niveau payant (EDI-1, bloquant) : sans lui, la politique de confidentialité affiche un encart
  « à régulariser ».
- Groq (EDI-2) : archiver l'accord de traitement (clauses contractuelles types, § 8.2) et vérifier « Zero Data
  Retention » dans la console. La politique ne dit plus « à vérifier » pour les clauses (D108).
- iCloud Mail (boîte de contact) : désormais cité comme destinataire ; vérifier la localisation des données et
  l'accord de traitement d'Apple (registre, T9).
- Marquage IA (JUR-20) : vérifier que l'en-tête `X-AI-Generated` traverse Cloudflare (non vérifié).
