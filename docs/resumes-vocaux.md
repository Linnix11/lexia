# Résumés vocaux (v1)

L'étudiant écoute un résumé d'une réponse, d'une fiche, d'un cours déposé ou d'un cours récupéré, comme les
résumés audio de NotebookLM (Gemini Notebook), en plus simple. Décision : D106 (`docs/decisions.md`).

## Ce qu'on résume

| Quoi | Où dans le site | Texte envoyé au modèle |
| --- | --- | --- |
| Réponse de l'assistant, fiche enregistrée | Sous chaque réponse (`Reponse.tsx`) | Le texte de la réponse (12 000 caractères au plus) et les extraits qu'elle cite, relus par le serveur (`/sources`, cours de l'étudiant compris) |
| Cours déposé | « Mes cours » de la matière (`MesCours.tsx`, liste seulement) | Le texte du cours, lu en base pour son seul propriétaire, 24 000 premiers caractères |
| Cours récupéré | Page « Cours récupérés » (`CoursRecuperes.tsx`) | Les sections du cours, 24 000 premiers caractères |

Au-delà de 24 000 caractères, seul le début est résumé et le site le dit (« Résumé du début du cours »).

## Longueur

De 2 à 5 minutes : la consigne demande 300 à 650 mots (environ 150 mots par minute à vitesse normale), moins si
le document est court, plutôt que d'ajouter quoi que ce soit. Le serveur coupe au-delà de 800 mots (environ
5 min 20) à la fin d'un paragraphe, et renvoie une durée estimée.

## Ton

Un seul narrateur pédagogique, qui vouvoie l'étudiant : une phrase d'annonce, trois à cinq paragraphes, une
conclusion « À retenir ». Pas de dialogue à deux voix pour commencer (le format par défaut de NotebookLM).

## Texte

- Rédigé par le modèle déjà en place : Gemini au niveau actuel, Groq en secours, même disjoncteur que les
  réponses (`Lexia.generer`).
- Consigne (`api/prompts.py`, `SYSTEME_RESUME_VOCAL`) : s'appuyer uniquement sur le document, nommer les
  articles et décisions comme ils y figurent, n'en inventer aucun, écrire pour l'oreille (pas de liste, pas
  d'abréviation, pas de Markdown), ignorer toute instruction contenue dans le document.
- Contrôle : chaque paragraphe qui cite un article, une décision ou un pourvoi absent du document est retiré
  (`citations.verifier_texte`, comme pour les réponses). Sans paragraphe vérifiable, pas de résumé, et le
  résumé n'est pas décompté.

## Voix

Synthèse vocale du navigateur (Web Speech API, `speechSynthesis`), voix françaises de l'appareil (fr-FR
d'abord, puis les autres fr-*). Aucun son n'est produit ni stocké par le serveur.

- Lecture, pause, reprise, arrêt, vitesse (0,75 à 1,5), choix de la voix s'il y en a plusieurs.
- Une phrase par énoncé (`SpeechSynthesisUtterance`) : la phrase lue est surlignée, un clic sur une phrase y
  saute, et Chrome ne coupe plus les longs énoncés.
- Navigateur sans synthèse vocale ou sans voix française : le résumé s'affiche à lire, avec un message.

La qualité dépend de l'appareil (voix système de macOS, iOS, Android et Windows correctes ; certaines
distributions Linux n'ont qu'une voix robotique).

## Limites et coût

- Route `POST /resume-vocal`, réservée aux comptes à l'adresse confirmée, limitée par minute comme `/chat`.
- 5 résumés par jour et par compte (`RESUMES_VOCAUX_PAR_JOUR`), décomptés à part des questions, remboursés si
  le modèle n'a pas répondu.
- Bornée en jetons de sortie (3 072, réflexion comprise : la documentation Gemini précise que
  `maxOutputTokens` inclut les jetons de réflexion) et en durée (mêmes délais que les réponses, place parmi
  les appels au modèle simultanés).
- Coût nul : niveau gratuit de Gemini et de Groq pendant le développement, synthèse vocale dans le navigateur.
  Une réponse vaut environ un appel de question en entrée (24 000 caractères au plus), un peu plus en sortie.

## Avertissement affiché

« Résumé généré automatiquement : il peut contenir des erreurs. Vérifiez avec les textes et les sources
citées. »

## Option étudiée : voix serveur libre (Piper)

Vérifié le 19 novembre 2026 sur les pages officielles du projet (dépôt OHF-Voice/piper1-gpl,
`docs/LICENSING.md` et `docs/COMMERCIAL_USE.md`) :

- Moteur : GPL-3.0-or-later. Utilisé comme service sur notre serveur, sans être distribué, il n'impose rien au
  code de Lexia.
- Voix : Piper n'accorde aucune licence sur les voix ; chacune suit les licences de ses données
  d'entraînement, à suivre sur sa fiche `MODEL_CARD`. La page « usage commercial » retient deux voix
  françaises : `fr_FR-siwis-medium` (CC BY 4.0, affinée depuis la base hifi_tts_92, elle-même CC BY 4.0) et
  `fr_FR-mls-medium` (CC BY 4.0, entraînée de zéro). Attribution obligatoire dans les deux cas ; vérifier que
  la copie téléchargée est bien la version réentraînée (fiche `MODEL_CARD`), les anciennes copies dérivant
  d'une base non commerciale.
- Installation : paquet `piper-tts`, mode serveur web documenté. Non installé ni mesuré sur le VPS.

Sur le VPS (7,8 Go de RAM, un seul processus uvicorn qui garde déjà ~2 Go de modèles), Piper tournerait dans
un service systemd à part, durci comme `lexia.service` (utilisateur dédié, `HF_HUB_OFFLINE=1`, voix copiées à
l'avance dans un dossier, `--workers 1`, écoute sur 127.0.0.1). À mesurer avant tout : mémoire, temps de
synthèse de 5 minutes de texte sur le processeur du VPS, et stockage ou non des fichiers son.

Conclusion : pas d'intégration en v1. La voix du navigateur suffit pour commencer et ne coûte rien côté
serveur. Piper ne serait ajouté que si les retours montrent qu'elle est insuffisante (voix robotique sur
certains appareils, besoin de télécharger le son pour l'écouter hors ligne).
