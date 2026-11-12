#!/usr/bin/env bash
# Publie Lexia sur le VPS depuis la machine de developpement (Mac).
#
#   LEXIA_SERVEUR=root@1.2.3.4 LEXIA_DOMAINE=lexia.mondomaine.fr deploy/publier.sh
#
# Etapes : tests, compilation du front, envoi du code + front + index de recherche,
# installation des dependances, redemarrage du service. Le .env n'est envoye que s'il
# n'existe pas encore sur le serveur (deploy/env.production.exemple sert de modele).
set -euo pipefail

SERVEUR="${LEXIA_SERVEUR:?Definir LEXIA_SERVEUR, ex. root@1.2.3.4}"
DOMAINE="${LEXIA_DOMAINE:-}"
APP=/opt/lexia
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RACINE"

echo "== Tests"
.venv/bin/python -m pytest -q
(cd web && npm test)

echo "== Compilation du front"
(cd web && npm ci && npm run build)

echo "== Index de recherche"
test -f data/index/lexia.sqlite || { echo "data/index absent : lancer python -m ingest.build_index" >&2; exit 1; }

echo "== Version"
git rev-parse --short HEAD > VERSION 2>/dev/null && echo "  $(cat VERSION)" || echo "inconnue" > VERSION

echo "== Envoi du code, du front et de l'index (rsync)"
rsync -az --delete \
  --exclude '.git' --exclude '.venv' --exclude '.cache' --exclude 'node_modules' --exclude '.env' \
  --exclude 'donnees' --exclude '.claude' --exclude 'sauvegardes' \
  --exclude 'data/raw' --exclude 'data/embeddings' --exclude 'data/passages' \
  --exclude 'logs' --exclude 'eval/resultats' --exclude '__pycache__' --exclude '.pytest_cache' \
  --exclude 'web/src' --exclude 'tests' \
  ./ "$SERVEUR:$APP/"

echo "== .env (seulement s'il manque sur le serveur)"
if ! ssh "$SERVEUR" "test -f $APP/.env"; then
  scp deploy/env.production.exemple "$SERVEUR:$APP/.env"
  echo "  ATTENTION : /opt/lexia/.env cree depuis le modele. Renseignez GEMINI_API_KEY sur le serveur puis relancez."
fi

echo "== Dependances Python et service"
ssh "$SERVEUR" bash -s <<EOF
set -euo pipefail
cd $APP
chmod 600 .env
mkdir -p donnees sauvegardes && chmod 700 donnees sauvegardes
test -d .venv || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r deploy/requirements-serveur.txt
chown -R lexia:lexia $APP
cp deploy/lexia.service /etc/systemd/system/lexia.service
chmod 755 deploy/sauvegarder_comptes.sh
install -m 644 deploy/lexia.cron /etc/cron.d/lexia
if [ -n "$DOMAINE" ] && [ ! -f /etc/nginx/sites-available/lexia ]; then
  sed "s/lexia.exemple.fr/$DOMAINE/" deploy/nginx-lexia.conf > /etc/nginx/sites-available/lexia
  ln -sf /etc/nginx/sites-available/lexia /etc/nginx/sites-enabled/lexia
  rm -f /etc/nginx/sites-enabled/default
  nginx -t && systemctl reload nginx
fi
systemctl daemon-reload
systemctl enable lexia >/dev/null
systemctl restart lexia
EOF

echo "== Attente du demarrage (le premier lancement telecharge les modeles)"
for i in $(seq 1 60); do
  if ssh "$SERVEUR" "curl -sf http://127.0.0.1:8000/api/sante" >/dev/null; then
    ssh "$SERVEUR" "curl -s http://127.0.0.1:8000/api/sante"; echo
    echo "Publie."
    exit 0
  fi
  sleep 10
done
echo "Le service ne repond pas encore : ssh $SERVEUR journalctl -u lexia -n 50" >&2
exit 1
