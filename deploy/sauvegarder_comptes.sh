#!/usr/bin/env bash
# Tache quotidienne du serveur (installee par publier.sh dans /etc/cron.d/lexia, lancee en tant que lexia a 3 h 15) :
#   1. sauvegarde de la base des comptes et des annales ; garde les 14 dernieres dans /opt/lexia/sauvegardes ;
#   2. suppression des sessions expirees.
# Les journaux techniques de plus de 12 mois sont purges par l'API elle-meme (api/journal.py),
# sous le verrou d'ecriture : une purge ici pourrait perdre les lignes ecrites pendant qu'elle tourne.
set -euo pipefail
echo "$(date -Is) debut"
SRC=/opt/lexia/donnees/lexia.db
DEST=/opt/lexia/sauvegardes
mkdir -p "$DEST" && chmod 700 "$DEST"
# Base absente (deplacee, renommee) : echec visible. Avant, le script ecrivait « fin » et sortait
# en succes chaque nuit, sans plus rien sauvegarder.
[ -f "$SRC" ] || { echo "$(date -Is) ERREUR : $SRC absente, aucune sauvegarde" >&2; exit 1; }
# copie coherente meme pendant l'ecriture (API de sauvegarde de SQLite)
if [ -f "$SRC" ]; then
  /opt/lexia/.venv/bin/python - "$SRC" "$DEST/lexia-$(date +%Y%m%d).db" <<'PY'
import sqlite3, sys
src, dst = sys.argv[1], sys.argv[2]
with sqlite3.connect(src) as a, sqlite3.connect(dst) as b:
    a.backup(b)
PY
  chmod 600 "$DEST"/lexia-*.db
  # sessions expirees : supprimees (duree annoncee dans la politique de confidentialite : 30 jours au plus)
  (cd /opt/lexia && /opt/lexia/.venv/bin/python -c "from api.comptes import Comptes; Comptes('$SRC').purger_sessions()")
  echo "sessions expirees supprimees"
  ls -1t "$DEST"/lexia-*.db | tail -n +15 | xargs -r rm -f
  echo "sauvegarde : $(ls -1t "$DEST"/lexia-*.db | head -1)"
fi

echo "$(date -Is) fin"
