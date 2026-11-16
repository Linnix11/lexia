#!/usr/bin/env bash
# Mise a jour nocturne du corpus depuis l'open data de la DILA (D78).
#
# Installe par publier.sh en copie appartenant a root (/usr/local/sbin/lexia-mise-a-jour) et lance par
# /etc/cron.d/lexia a 4 h 30, apres la publication quotidienne de la DILA (vers 21 h). Root ne fait que
# redemarrer le service : tout le reste tourne en tant que lexia, qui possede /opt/lexia. Journal :
# /var/log/lexia-mise-a-jour.log (hors de /opt/lexia, que lexia pourrait remplacer par un lien).
#
#   lexia-mise-a-jour            # rien a faire s'il n'y a pas de nouvelle archive
#   lexia-mise-a-jour --forcer   # reconstruit quand meme
set -euo pipefail
APP=/opt/lexia
SANTE=http://127.0.0.1:8000/api/sante

exec 9>/run/lexia-mise-a-jour.lock
flock -n 9 || { echo "$(date -Is) deja en cours"; exit 0; }
cd "$APP"

en_lexia() { runuser -u lexia -- env HF_HOME="$APP/.cache/huggingface" TOKENIZERS_PARALLELISM=false "$@"; }
attendre() {
  for _ in $(seq 1 60); do curl -sf "$SANTE" >/dev/null && return 0; sleep 5; done
  return 1
}

echo "$(date -Is) debut"
code=0
# Priorite basse : le service garde le processeur et le disque pendant la reconstruction.
en_lexia nice -n 19 ionice -c3 .venv/bin/python -m ingest.mise_a_jour "$@" || code=$?
if [ "$code" -eq 3 ]; then
  echo "$(date -Is) rien de nouveau"
  exit 0
fi
if [ "$code" -ne 0 ]; then
  echo "$(date -Is) ERREUR ($code) : index inchange" >&2
  exit "$code"
fi

en_lexia bash -c 'rm -rf data/index.precedent && mv data/index data/index.precedent && mv data/index.nouveau data/index'
systemctl restart lexia
if attendre; then
  echo "$(date -Is) nouvel index en service : $(curl -s "$SANTE")"
  exit 0
fi
echo "$(date -Is) ERREUR : le service ne repond plus, retour a l'index precedent" >&2
en_lexia bash -c 'rm -rf data/index.echec && mv data/index data/index.echec && mv data/index.precedent data/index'
systemctl restart lexia
attendre && echo "$(date -Is) index precedent remis en service" || echo "$(date -Is) ERREUR : service toujours muet" >&2
exit 1
