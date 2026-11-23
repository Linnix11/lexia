# Polices et bibliothèques du kit : licences vérifiées

Vérification du 23 novembre 2026, sur les fichiers eux-mêmes (table `name` des polices) et les textes de licence
joints. Aucun outil ni service payant n'est utilisé.

| Élément | Fichier | Licence | Titulaire | Provenance |
|---|---|---|---|---|
| Source Serif 4 (police variable, axes graisse 200 à 900 et taille optique 8 à 60) | `SourceSerif4-Variable.ttf`, licence `SourceSerif4-OFL.txt` | SIL Open Font License 1.1 | Table `name` de la police : « © 2014 - 2021 Adobe Systems Incorporated, with Reserved Font Name ‘Source’ ». Texte OFL joint (copie du dépôt google/fonts) : « Copyright 2014 The Source Serif 4 Project Authors », sans nom réservé | Dépôt google/fonts, dossier `ofl/sourceserif4` (https://github.com/google/fonts/tree/main/ofl/sourceserif4), projet d'origine https://github.com/adobe-fonts/source-serif |
| Inter (police variable, axes graisse 100 à 900 et taille optique 14 à 32) | `Inter-Variable.ttf`, licence `Inter-OFL.txt` | SIL Open Font License 1.1 | Table `name` de la police : « Copyright 2016 The Inter Project Authors ». Texte OFL joint (copie du dépôt google/fonts) : « Copyright 2020 The Inter Project Authors ». Aucun nom réservé | Dépôt google/fonts, dossier `ofl/inter` (https://github.com/google/fonts/tree/main/ofl/inter), projet d'origine https://github.com/rsms/inter |
| lottie-web 5.12.2 (lecture du logo Lottie dans les pages de démonstration) | chargé depuis https://cdnjs.cloudflare.com/ajax/libs/lottie-web/5.12.2/lottie.min.js, non copié | MIT | Airbnb | https://github.com/airbnb/lottie-web |
| Georgia (titres du site actuel) | aucun : police installée sur l'appareil du lecteur | Police système de Microsoft, non redistribuable | Microsoft | Non utilisée dans les fichiers du kit |

Écarts entre les fichiers (relevés par l'audit du 23 novembre 2026, D15, revérifiés le même jour) : les mentions
du tableau sont celles de la table `name` des polices. Le texte de licence joint à Inter (copie du dépôt
google/fonts) date le copyright de 2020, la police de 2016 ; celui de Source Serif 4 ne reprend pas le nom réservé
« Source », que la police déclare (« with Reserved Font Name ‘Source’ »). Par prudence, le nom réservé est
respecté : une version modifiée ne s'appelle pas « Source ».

## Ce que permet la licence OFL 1.1

Texte complet : https://openfontlicense.org (copie jointe pour chaque police).

- Usage libre, y compris commercial : visuels, vidéos, PDF, site web (en fichier hébergé par Lexia).
- Redistribution permise avec le texte de licence et la mention du titulaire, ce que fait ce dossier.
- Interdit : vendre la police seule. Une version modifiée de la police ne peut pas porter un nom réservé : pour
  Source Serif 4, le nom « Source », déclaré dans la table `name` de la police (le texte OFL joint ne le reprend
  pas, on le respecte quand même).
- Les documents et images créés avec la police ne sont pas soumis à la licence. Le logotype « lexia » et le signe §
  du symbole sont des tracés extraits de Source Serif 4 par `brand/outils/glyphes.py` : ce sont des images, pas une
  police modifiée ; aucune police modifiée n'est redistribuée.
- Pour le site, une version allégée (sous-ensemble de caractères, WOFF2) est une version modifiée : elle reste sous
  OFL et ne doit pas s'appeler « Source Serif 4 » si elle est produite par Lexia (par exemple « Lexia Serif »), sauf
  à utiliser les fichiers WOFF2 distribués tels quels par le projet d'origine.
