#!/usr/bin/env bash
# Tache quotidienne du serveur (installee par publier.sh dans /etc/cron.d/lexia, lancee en tant que lexia a 3 h 15) :
#   1. sauvegarde de la base des comptes et des annales ; garde les 14 dernieres dans /opt/lexia/sauvegardes ;
#   2. suppression des sessions expirees.
# Les journaux techniques de plus de 12 mois sont purges par l'API elle-meme (api/journal.py),
# sous le verrou d'ecriture : une purge ici pourrait perdre les lignes ecrites pendant qu'elle tourne.
# Chemins modifiables par l'environnement pour les tests (tests/test_cours.py).
set -euo pipefail
horodatage() { date '+%Y-%m-%dT%H:%M:%S%z'; }  # « date -Is » n'existe pas sur macOS
echo "$(horodatage) debut"
RACINE=${LEXIA_RACINE:-/opt/lexia}
SRC=${LEXIA_BASE:-$RACINE/donnees/lexia.db}
DEST=${LEXIA_SAUVEGARDES:-$RACINE/sauvegardes}
PY=${LEXIA_PYTHON:-$RACINE/.venv/bin/python}
mkdir -p "$DEST" && chmod 700 "$DEST"
# Base absente (deplacee, renommee) : echec visible. Avant, le script ecrivait « fin » et sortait
# en succes chaque nuit, sans plus rien sauvegarder.
[ -f "$SRC" ] || { echo "$(horodatage) ERREUR : $SRC absente, aucune sauvegarde" >&2; exit 1; }
# Copie coherente meme pendant l'ecriture, par VACUUM INTO : la copie page a page (API de sauvegarde)
# recopiait aussi les pages libres, ou le texte d'un cours retire restait lisible (audit C7).
COPIE="$DEST/lexia-$(date +%Y%m%d).db"
rm -f "$COPIE"
"$PY" - "$SRC" "$COPIE" <<'PY'
import sqlite3, sys
src, dst = sys.argv[1], sys.argv[2]
with sqlite3.connect(src) as a:
    a.execute("VACUUM INTO ?", (dst,))
PY
chmod 600 "$DEST"/lexia-*.db
# sessions expirees : supprimees (duree annoncee dans la politique de confidentialite : 30 jours au plus)
(cd "$RACINE" && "$PY" -c "import sys; from api.comptes import Comptes; Comptes(sys.argv[1]).purger_sessions()" "$SRC")
echo "sessions expirees supprimees"
ls -1t "$DEST"/lexia-*.db | tail -n +15 | while read -r ancienne; do rm -f "$ancienne"; done
echo "sauvegarde : $(ls -1t "$DEST"/lexia-*.db | head -1)"

echo "$(horodatage) fin"
