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
# Variables LEXIA_* : seulement pour les tests (tests/test_mise_a_jour_shell.py).
APP="${LEXIA_APP:-/opt/lexia}"
SANTE=http://127.0.0.1:8000/api/sante

exec 9>"${LEXIA_VERROU_MAJ:-/run/lexia-mise-a-jour.lock}"
flock -n 9 || { echo "$(date -Is) deja en cours"; exit 0; }
cd "$APP"

en_lexia() { runuser -u lexia -- env HF_HOME="$APP/.cache/huggingface" TOKENIZERS_PARALLELISM=false "$@"; }
attendre() {
  for _ in $(seq 1 60); do curl -sf "$SANTE" >/dev/null && return 0; sleep 5; done
  return 1
}
# Passage reussi : date lue par /api/sante (corpus_a_jour) et la surveillance GitHub (audit B8).
reussi() { en_lexia bash -c 'date -Is > data/mise_a_jour_reussie'; }
# Echec : e-mail aux ADMIN_EMAILS (le 17/11/2026, un echec est passe inapercu).
alerte() { en_lexia .venv/bin/python -m ingest.fraicheur --alerte "$(hostname) $(date -Is) : $1" || true; }

# Bascule de l'index. Sous set -e, un echec du second mv laissait le serveur sans data/index : le prochain
# redemarrage echouait, sans alerte (audit du 19/11, SRV-8). Ici, l'ancien index revient a sa place.
basculer() {
  en_lexia bash -c 'rm -rf data/index.precedent && mv data/index data/index.precedent' || return 1
  if ! en_lexia mv data/index.nouveau data/index; then
    en_lexia mv data/index.precedent data/index || true
    return 1
  fi
}

echo "$(date -Is) debut"
# Espace disque : l'index en service, le precedent et le nouveau coexistent pendant la reconstruction, sur le
# disque de la base des comptes. Le reste d'un echec ancien (deja signale) est efface, puis il faut au moins la
# taille d'un index de plus, et 2 Go pour les archives et les embeddings (audit du 19/11, SRV-8).
en_lexia rm -rf data/index.echec
if [ -d data/index ]; then
  besoin=$(( $(du -sk data/index | cut -f1) + 2 * 1024 * 1024 ))
  libre=$(df -Pk "$APP" | awk 'NR == 2 { print $4 }')
  if [ "$libre" -lt "$besoin" ]; then
    echo "$(date -Is) ERREUR : ${libre} Ko libres, ${besoin} necessaires : index inchange" >&2
    alerte "espace disque insuffisant (${libre} Ko libres, ${besoin} Ko necessaires), index inchange"
    exit 1
  fi
fi
code=0
# Priorite basse : le service garde le processeur et le disque pendant la reconstruction.
en_lexia nice -n 19 ionice -c3 .venv/bin/python -m ingest.mise_a_jour "$@" || code=$?
if [ "$code" -eq 3 ]; then
  echo "$(date -Is) rien de nouveau"
  reussi
  exit 0
fi
if [ "$code" -ne 0 ]; then
  echo "$(date -Is) ERREUR ($code) : index inchange" >&2
  alerte "ingest.mise_a_jour a echoue (code $code), index inchange"
  exit "$code"
fi

if ! basculer; then
  echo "$(date -Is) ERREUR : bascule impossible, index precedent garde" >&2
  alerte "bascule de l'index impossible (mv), index precedent garde"
  exit 1
fi
systemctl restart lexia
if attendre; then
  echo "$(date -Is) nouvel index en service : $(curl -s "$SANTE")"
  reussi
  exit 0
fi
echo "$(date -Is) ERREUR : le service ne repond plus, retour a l'index precedent" >&2
alerte "le service ne repondait plus avec le nouvel index, retour a l'index precedent"
en_lexia bash -c 'rm -rf data/index.echec && mv data/index data/index.echec && mv data/index.precedent data/index'
systemctl restart lexia
attendre && echo "$(date -Is) index precedent remis en service" || echo "$(date -Is) ERREUR : service toujours muet" >&2
exit 1
