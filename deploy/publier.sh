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
# --partial-dir : une coupure pendant les 4 Go d'index laisse le morceau deja recu dans un dossier
# a part et reprend au prochain envoi. Sans « -dir », rsync ecrit dans le fichier de destination et
# une coupure laisse l'index de production tronque (constate le 2026-11-14).
# --timeout : une connexion muette est abandonnee au lieu de rester bloquee.
rsync -az --delete --partial-dir=.rsync-partiel --timeout=120 \
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

# Cle de chiffrement des secrets en base : generee une seule fois, puis conservee telle quelle.
ssh "$SERVEUR" bash -s <<'EOF'
set -euo pipefail
if ! grep -q '^CLE_SECRETS=.\+' /opt/lexia/.env 2>/dev/null; then
  CLE=$(python3 -c 'import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())')
  sed -i '/^CLE_SECRETS=/d' /opt/lexia/.env
  printf 'CLE_SECRETS=%s\n' "$CLE" >> /opt/lexia/.env
  chmod 600 /opt/lexia/.env
  echo "  CLE_SECRETS generee dans /opt/lexia/.env (a sauvegarder avec la configuration)."
fi
EOF

echo "== Dependances Python et service"
ssh "$SERVEUR" bash -s <<EOF
set -euo pipefail
cd $APP
chmod 600 .env
mkdir -p donnees sauvegardes && chmod 700 donnees sauvegardes
chown -R lexia:lexia $APP
# Python et pip tournent en tant que lexia : root n'execute jamais du code modifiable par le service.
runuser -u lexia -- bash -c 'test -d .venv || python3 -m venv .venv'
runuser -u lexia -- .venv/bin/pip install -q --no-cache-dir --upgrade pip
runuser -u lexia -- .venv/bin/pip install -q --no-cache-dir -r deploy/requirements-serveur.txt
cp deploy/lexia.service /etc/systemd/system/lexia.service
chmod 755 deploy/sauvegarder_comptes.sh
install -m 644 deploy/lexia.cron /etc/cron.d/lexia
# Adresse reelle des visiteurs derriere Cloudflare (inclus par la configuration nginx)
install -m 644 deploy/nginx-cloudflare.conf /etc/nginx/snippets/lexia-cloudflare.conf
if [ -n "$DOMAINE" ] && [ ! -f /etc/nginx/sites-available/lexia ]; then
  sed "s/lexia.exemple.fr/$DOMAINE/g" deploy/nginx-lexia.conf > /etc/nginx/sites-available/lexia
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
