# Cours déposés par l'étudiant - conception

Date : 2026-11-12. Validé dans la conversation avec le porteur du projet (« c'est bon tu peux y aller »).

## Intention

L'étudiant dépose ses propres cours (surtout des PDF) pour que Lexia lui fabrique, à partir de ce cours,
des questionnaires, des fiches, des commentaires, des cas pratiques et des explications. Réviser son cours
seul n'a pas toujours d'intérêt : l'étudiant choisit, de façon visible, entre « Mon cours uniquement » et
« Mon cours + textes officiels ».

## Décisions du porteur

- Les cours restent dans le compte, classés par matière, et se retrouvent à chaque connexion.
- Sélecteur visible à chaque demande : **Mon cours uniquement** / **Mon cours + textes officiels**.
- Formats : un peu de tout, surtout des PDF.
- Plus de cours pour les formules payantes.

## Choix faits par Claude (à vérifier par le porteur)

- **Formats V1** : PDF avec texte, Word (.docx), texte (.txt, .md). Photos, scans et notes manuscrites (OCR)
  dans un second temps. Un PDF sans texte (scan) est refusé avec un message clair.
- **Limites** : 3 cours en Gratuit, 30 en Étudiant, 100 en Intensif ; 20 Mo par fichier ; 1 million de
  caractères de texte extrait au plus.
- **Stockage** : seul le texte extrait est conservé (découpé en passages d'environ 1 500 caractères, avec la
  page), dans la base SQLite des comptes ; le fichier d'origine n'est pas gardé. Visible par son seul
  propriétaire, jamais partagé, supprimé quand l'étudiant le retire ou supprime son compte.
- **Traitement** : extraction immédiate, puis calcul des embeddings en arrière-plan (un seul fil, pour ne pas
  saturer les 2 processeurs du VPS). Tant qu'il n'est pas fini, la recherche dans le cours est lexicale.
- **Recherche** : plein texte (FTS5) et vecteurs sur les seuls cours choisis, fusion par rang comme pour le
  corpus. « Cours uniquement » : 8 passages du cours. « Cours + officiels » : 4 du cours et 4 du corpus.
- **Réponse** : les passages du cours sont des extraits comme les autres ([S1]...), marqués « Mon cours » ;
  la consigne au modèle précise qu'ils ne sont pas des sources officielles et qu'une contradiction avec un
  texte officiel doit être signalée dans les points d'attention. Le contrôle des citations est inchangé.
- **Accès** : un passage de cours n'est lisible (`/sources/...`) que par son propriétaire. Pas de cache des
  réponses quand un cours est utilisé.
- **Envoi** : le fichier est envoyé brut (`application/octet-stream`, métadonnées en paramètres), sans
  nouvelle dépendance de formulaire ; nginx accepte 21 Mo sur `/api/cours`.
- **Juridique** : CGU (l'étudiant garantit avoir le droit d'utiliser le cours, usage personnel) et
  politique de confidentialité (contenu conservé, transmis au modèle pour répondre, supprimé à la demande).

## Hors champ (V1)

OCR, partage de cours entre étudiants, dépôt par les enseignants, édition du texte extrait.
