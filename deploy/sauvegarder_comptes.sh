#!/usr/bin/env bash
# Tache quotidienne du serveur (installee par publier.sh dans /etc/cron.d/lexia, lancee en tant que lexia a 3 h 15) :
#   1. sauvegarde de la base des comptes et des annales ; garde les 14 dernieres dans /opt/lexia/sauvegardes ;
#   2. purge des journaux techniques (/opt/lexia/logs) : lignes de plus de 12 mois supprimees
#      (duree annoncee dans la politique de confidentialite).
set -euo pipefail
echo "$(date -Is) debut"
SRC=/opt/lexia/donnees/lexia.db
DEST=/opt/lexia/sauvegardes
mkdir -p "$DEST" && chmod 700 "$DEST"
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

# Purge des journaux : reecriture atomique, proprietaire conserve (le service ecrit en tant que lexia).
/opt/lexia/.venv/bin/python - /opt/lexia/logs <<'PY'
import json, os, sys, tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
limite = datetime.now(timezone.utc) - timedelta(days=365)
for f in Path(sys.argv[1]).glob("*.jsonl"):
    garde, retire = [], 0
    with f.open(encoding="utf-8") as h:
        for ligne in h:
            try:
                ts = datetime.fromisoformat(json.loads(ligne)["ts"])
            except (ValueError, KeyError, TypeError):
                garde.append(ligne)
                continue
            if ts >= limite:
                garde.append(ligne)
            else:
                retire += 1
    if retire:
        st = f.stat()
        fd, tmp = tempfile.mkstemp(dir=f.parent)
        with os.fdopen(fd, "w", encoding="utf-8") as h:
            h.writelines(garde)
        os.chown(tmp, st.st_uid, st.st_gid)
        os.chmod(tmp, st.st_mode)
        os.replace(tmp, f)
    print(f"journal {f.name} : {retire} ligne(s) de plus de 12 mois retiree(s)")
PY
echo "$(date -Is) fin"
