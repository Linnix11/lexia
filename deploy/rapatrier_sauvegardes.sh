#!/usr/bin/env bash
# Copie hors serveur des sauvegardes de la base des comptes (A5 du plan d'amelioration, complete D45).
#
# A lancer sur le Mac (ou toute machine qui a la cle SSH du serveur) :
#   LEXIA_SERVEUR=root@IP_DU_VPS deploy/rapatrier_sauvegardes.sh
#
# 1. rapatrie /opt/lexia/sauvegardes/lexia-*.db dans LEXIA_COPIES (defaut : ~/Lexia-sauvegardes) ;
# 2. verifie la plus recente : integrite SQLite et presence de la table des comptes (restauration testee) ;
# 3. garde les JOURS_CONSERVES dernieres copies (defaut 60).
#
# Les copies contiennent des adresses e-mail et des empreintes de mots de passe : dossier en 700, fichiers
# en 600, disque chiffre (FileVault) indispensable. Lancement automatique : voir deploy/fr.lexia.sauvegarde.plist.
set -euo pipefail

: "${LEXIA_SERVEUR:?definir LEXIA_SERVEUR, ex. root@IP_DU_VPS}"
COPIES="${LEXIA_COPIES:-$HOME/Lexia-sauvegardes}"
SOURCE="${LEXIA_SOURCE:-$LEXIA_SERVEUR:/opt/lexia/sauvegardes/}"  # LEXIA_SOURCE : dossier local, pour les essais
JOURS="${JOURS_CONSERVES:-60}"

mkdir -p "$COPIES" && chmod 700 "$COPIES"
echo "$(date -Iseconds) rapatriement depuis $LEXIA_SERVEUR"
# (pas d'option --chmod : le rsync fourni avec macOS ne la connait pas)
rsync -a -e "ssh -o BatchMode=yes -o ConnectTimeout=20" --include='lexia-*.db' --exclude='*' "$SOURCE" "$COPIES/"
chmod 600 "$COPIES"/lexia-*.db 2>/dev/null || true

# la date est dans le nom (lexia-AAAAMMJJ.db) : tri par nom, plus sur que la date de modification
DERNIERE="$(ls -1 "$COPIES"/lexia-*.db 2>/dev/null | sort | tail -1 || true)"
if [ -z "$DERNIERE" ]; then
  echo "ERREUR : aucune sauvegarde recue" >&2
  exit 1
fi

# Fraicheur : si le serveur ne sauvegarde plus, rsync ne ramene rien et la plus recente copie locale
# vieillit sans que rien ne le signale. Plus de 2 jours : echec.
JOUR_COPIE="$(basename "$DERNIERE" .db | sed 's/^lexia-//')"
AGE_JOURS=$(( ( $(date +%s) - $(date -j -f %Y%m%d "$JOUR_COPIE" +%s 2>/dev/null || date -d "$JOUR_COPIE" +%s) ) / 86400 ))
if [ "$AGE_JOURS" -gt 2 ]; then
  echo "ERREUR : la plus recente sauvegarde ($JOUR_COPIE) a $AGE_JOURS jours : le serveur ne sauvegarde plus" >&2
  exit 1
fi

# Restauration testee sur une copie temporaire : la sauvegarde s'ouvre, est integre et contient les comptes.
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cp "$DERNIERE" "$TMP/essai.db"
INTEGRITE="$(sqlite3 "$TMP/essai.db" 'PRAGMA integrity_check;' 2>&1 || true)"
COMPTES="$(sqlite3 "$TMP/essai.db" 'SELECT count(*) FROM utilisateurs;' 2>/dev/null || echo "absente")"
if [ "$INTEGRITE" != "ok" ] || [ "$COMPTES" = "absente" ]; then
  echo "ERREUR : $DERNIERE illisible (integrite : $INTEGRITE, table utilisateurs : $COMPTES)" >&2
  exit 1
fi
echo "verifiee : $(basename "$DERNIERE") ($COMPTES comptes, integrite ok)"

# Anciennes copies : seules les JOURS dernieres sont gardees
ls -1 "$COPIES"/lexia-*.db | sort -r | tail -n +"$((JOURS + 1))" | xargs -r rm -f
echo "$(date -Iseconds) fin : $(ls -1 "$COPIES"/lexia-*.db | wc -l | tr -d ' ') copies dans $COPIES"
