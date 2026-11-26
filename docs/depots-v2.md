# Dépôt de cours, version 2

État au 19 novembre 2026 (branche `claude/depots-v2`). Contrainte : aucune API payante, tout tourne sur le VPS.

## Point de départ

- Déjà en place (D57, D93) : PDF, Word (.docx), OpenDocument (.odt), PowerPoint (.pptx), texte (.txt, .md) ;
  20 Mo par fichier ; 3, 30 ou 100 cours selon la formule ; e-mail vérifié ; une lecture à la fois par compte,
  deux en tout ; 20 lectures par jour ; nombre de pages affiché ; glisser-déposer de plusieurs fichiers (et d'un
  dossier) dans l'assistant.
- Lecture dans un processus à part (`api/extraction.py`) : 60 s, 768 Mo, refus de DOCTYPE et ENTITY, imbrication
  et taille décompressée bornées.
- Manques relevés par le comparatif avec Gemini Notebook (`docs/comparatif-notebooklm.md`) : pas d'OCR (un PDF
  scanné est refusé), pas de photos, peu de retour pendant et après le dépôt.

## Pistes classées

Classement par intérêt pour l'étudiant, puis par coût (faible d'abord).

| Rang | Piste | Intérêt | Coût | Décision |
| --- | --- | --- | --- | --- |
| 1 | PDF scannés et photos de cours (JPEG, PNG) lus par OCR (Tesseract, français) | Très fort : polycopiés scannés, photos de fiches et de cours manuscrits propres | Moyen : paquets libres sur le VPS, calcul (2 à 3 s par page) | Fait |
| 2 | Messages d'erreur clairs (taille, format, page illisible) et barre de progression | Fort : on sait ce qui se passe et pourquoi un fichier est refusé | Faible | Fait |
| 3 | Nombre de passages et aperçu du texte lu | Fort avec l'OCR : vérifier ce que Lexia a compris | Faible | Fait (aperçu après dépôt, voir plus bas) |
| 4 | Renommer un cours, le changer de matière | Moyen : erreurs de rangement fréquentes au premier dépôt | Faible | Fait |
| 5 | Plusieurs fichiers d'un coup et glisser-déposer dans « Mes cours » | Moyen : existait dans l'assistant, pas dans la page Mes cours | Faible | Fait |
| 6 | RTF | Faible à moyen : exports d'anciens traitements de texte | Faible (lecteur maison borné) | Fait |
| 7 | ODT, PPTX, Markdown | Moyen | Déjà fait (D93) | Rien à faire |
| 8 | Relancer l'extraction | Faible : le fichier d'origine n'est pas gardé (D57, seul le texte l'est) | Moyen si l'on gardait le fichier | Non : on redépose ; le calcul des vecteurs est déjà relancé seul (D93) |
| 9 | Aperçu avant validation | Moyen | Moyen : garder le texte lu entre deux requêtes | Remplacé par l'aperçu après dépôt et « Retirer » |

Plus tard, dans cet ordre :

1. Lecture en arrière-plan pour les longs scans (au-delà de 20 pages) : le dépôt répond tout de suite, le cours
   passe « en lecture » puis « prêt ». Cloudflare coupe une requête à 100 s, d'où la limite actuelle.
2. Plusieurs photos réunies en un seul cours (une page par photo).
3. Photos HEIC de l'iPhone (Safari les convertit déjà en JPEG à l'envoi dans la plupart des cas).
4. Ancien Word (.doc) : aucun lecteur libre sûr et léger ; on demande d'enregistrer en .docx.
5. Taille par fichier : 20 Mo gardés. Gemini Notebook accepte 200 Mo, mais le VPS lit en mémoire et un cours
   de droit en texte dépasse rarement 5 Mo ; seuls les scans sont lourds, et ils sont bornés en pages.

## Conception retenue

### OCR

- Paquets Ubuntu 24.04 (vérifiés sur packages.ubuntu.com le 19 novembre 2026) : `tesseract-ocr` 5.3.4
  (universe), `tesseract-ocr-fra` (universe), `poppler-utils` 24.02 (main, pour `pdftoppm`). Ajoutés à
  `deploy/publier.sh` (installés seulement s'ils manquent).
- Tout se passe dans le processus de lecture isolé, qui lance lui-même `pdftoppm` et `tesseract` : ils héritent de
  ses limites (mémoire, temps de calcul). Le processus de lecture est lancé dans son propre groupe : au-delà du
  délai, tout le groupe est tué, `tesseract` compris (avant, seul le processus Python l'aurait été).
- PDF : seules les pages sans texte passent à l'OCR, rendues en niveaux de gris, côté le plus long borné à
  3 300 pixels quelle que soit la taille de page déclarée. 20 pages scannées au plus par fichier, 75 s d'OCR au
  plus : au-delà, refus avec le conseil de découper.
- Photos : JPEG ou PNG reconnus à leurs premiers octets (pas seulement à l'extension) ; dimensions lues dans
  l'en-tête avant tout décodage, 40 mégapixels et 12 000 pixels de côté au plus (une image géante de quelques Ko
  ne peut pas réclamer des Go de mémoire).
- Un seul fil de calcul par OCR (`OMP_THREAD_LIMIT=1`) : deux lectures en même temps ne prennent que deux cœurs.
- Le cours garde un avertissement : pages lues par OCR (« à vérifier dans l'aperçu ») et pages restées
  illisibles.
- Sans Tesseract sur la machine (développement), le comportement d'avant reste : PDF scanné refusé avec un
  message clair, photo refusée.

### RTF

Lecteur maison dans le processus isolé : groupes imbriqués bornés (200), groupes de mise en forme ignorés
(polices, couleurs, styles, images), `\binN` sauté sans être lu en mémoire au-delà du fichier, caractères `\'hh`
et `\uN` décodés.

### Site

- Page « Mes cours » : plusieurs fichiers à la fois, zone de glisser-déposer, barre de progression de l'envoi puis
  « Lecture du fichier » ; formats et taille vérifiés avant l'envoi avec le nom du fichier en cause.
- Liste des cours : pages, passages, statut, avertissement ; « Aperçu » (5 passages à la fois, précédents et
  suivants), « Modifier » (titre et matière), « Retirer ».
- Pages lues par OCR gardées avec le cours (`pages_ocr`, D141) : « Vérifier la page 3 » ouvre l'aperçu sur cette
  page (`GET /cours/{id}/apercu?page=3`), pastilles des pages scannées et passages concernés encadrés.
- Zone de glisser-déposer visible et « Formats, scans et limites » sous le formulaire (D141).

### Limites inchangées

20 Mo, 3 / 30 / 100 cours, e-mail vérifié, une lecture par compte et deux en tout, 20 lectures par jour,
1 000 pages, 1 000 000 de caractères, 60 s et 768 Mo pour la lecture d'un fichier sans OCR.
