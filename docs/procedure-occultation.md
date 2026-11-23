# Procédure : demande d'occultation ou de retrait d'une décision de justice

Rédigée le 23 novembre 2026 (audit du 23 novembre, E10). À faire relire par le juriste. Elle applique la promesse
de la politique de confidentialité, section « Décisions de justice reproduites », et le traitement T11 du
registre (`docs/registre-traitements.md`).

## Ce que dit la politique de confidentialité

Une personne qui se reconnaît dans une décision écrit à l'adresse de contact en indiquant la juridiction, la date
et le numéro de la décision. L'éditeur transmet la demande à la juridiction qui l'a publiée, retire la décision de
Lexia en attendant sa réponse et répond dans un délai d'un mois (RGPD, article 12, paragraphe 3 ; droits
d'effacement et d'opposition, articles 17 et 21).

## Étapes

1. **Accuser réception** le jour même, depuis l'adresse de contact : demande reçue, réponse sous un mois au plus.
   Ne demander une pièce d'identité que si un doute sérieux existe sur l'identité du demandeur (article 12.6).
2. **Identifier la décision** : juridiction, date, numéro (pourvoi, QPC, requête) et, si possible, l'ECLI. La
   retrouver dans Lexia (recherche dans l'espace, ou dans la source officielle : Légifrance, Judilibre, site du
   Conseil constitutionnel). Noter la source qui l'a fournie à Lexia (archive DILA, Judilibre, site du Conseil).
3. **Transmettre à la juridiction** qui l'a publiée, en joignant la demande :
   - Cour de cassation : `occultations.courdecassation@justice.fr` (demande d'occultation ou de levée) ; un défaut
     d'occultation constaté se signale à `anonymisation.sder.courdecassation@justice.fr`
     (`docs/jurisprudence-recente.md`) ;
   - Conseil d'État et juridictions administratives : par le formulaire ou l'adresse indiqués sur le site du
     Conseil d'État (à relever et noter ici à la première demande) ;
   - Conseil constitutionnel : par l'adresse de contact de son site (à relever et noter ici à la première
     demande).
4. **Retirer la décision de Lexia** en attendant la réponse de la juridiction. Aucun outil ne le fait encore (voir
   « Outil manquant ») : en attendant, demander le retrait à la session chargée des sources, avec l'identifiant de
   la décision, et ne pas répondre « retirée » avant de l'avoir vérifié dans Lexia.
5. **Répondre au demandeur** dans le mois : décision retirée de Lexia, demande transmise à telle juridiction le
   tant, et ce qu'il advient ensuite (la décision ne revient dans Lexia que dans la version occultée par la
   juridiction). Si un délai supplémentaire est nécessaire, le dire dans le mois, avec la raison (article 12.3).
6. **Tenir un registre des demandes** (date, décision, juridiction saisie, date du retrait, date de la réponse),
   conservé 3 ans après le dernier échange comme les autres échanges par e-mail (T9).

## Outil manquant

Une **liste d'exclusion lue à l'indexation** : un fichier du dépôt (ECLI ou identifiant de source par ligne, avec
la date de la demande) que la mise à jour nocturne lit pour ne plus indexer la décision, quelle que soit sa source
(archive DILA, Judilibre, site du Conseil constitutionnel), suivi d'une reconstruction de l'index. À écrire dans
`ingest/` par la session chargée des sources, avec un test, avant la première demande (registre, « Actions
restantes », point 7).
