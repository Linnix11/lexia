#!/usr/bin/env bash
# Sauvegarde quotidienne de la base des comptes (a lancer par cron sur le serveur, en root).
#   crontab -e  ->  15 3 * * * /opt/lexia/deploy/sauvegarder_comptes.sh
# Garde les 14 dernieres sauvegardes dans /opt/lexia/sauvegardes.
set -euo pipefail
SRC=/opt/lexia/donnees/lexia.db
DEST=/opt/lexia/sauvegardes
test -f "$SRC" || exit 0
mkdir -p "$DEST" && chmod 700 "$DEST"
# copie coherente meme pendant l'ecriture (API de sauvegarde de SQLite)
/opt/lexia/.venv/bin/python - "$SRC" "$DEST/lexia-$(date +%Y%m%d).db" <<'PY'
import sqlite3, sys
src, dst = sys.argv[1], sys.argv[2]
with sqlite3.connect(src) as a, sqlite3.connect(dst) as b:
    a.backup(b)
PY
chmod 600 "$DEST"/lexia-*.db
ls -1t "$DEST"/lexia-*.db | tail -n +15 | xargs -r rm -f
