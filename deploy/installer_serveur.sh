#!/usr/bin/env bash
# Installation initiale de Lexia sur un VPS Ubuntu 24.04 (a lancer UNE fois, en root, sur le serveur).
#
#   sudo bash installer_serveur.sh lexia.mondomaine.fr
#
# Ensuite, depuis votre Mac : deploy/publier.sh (envoie le code, le front compile et l'index).
set -euo pipefail

DOMAINE="${1:?Usage : sudo bash installer_serveur.sh <domaine>}"
APP=/opt/lexia

if [[ $EUID -ne 0 ]]; then
  echo "A lancer en root (sudo)." >&2
  exit 1
fi

echo "== Paquets systeme"
apt-get update
apt-get install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx rsync \
  tesseract-ocr tesseract-ocr-fra poppler-utils  # OCR des cours scannes (D107)

echo "== Utilisateur et dossiers"
id lexia >/dev/null 2>&1 || useradd --system --home "$APP" --shell /usr/sbin/nologin lexia
mkdir -p "$APP"/{logs,.cache/huggingface,data/index,web/dist}
chown -R lexia:lexia "$APP"

echo "== Fichier .env"
if [[ ! -f "$APP/.env" ]]; then
  echo "  /opt/lexia/.env absent : il sera envoye par publier.sh (ou copiez deploy/env.production.exemple et remplissez-le)."
fi

echo "== Service systemd et nginx (les fichiers arrivent avec publier.sh ; on les installe s'ils sont deja la)"
if [[ -f "$APP/deploy/lexia@.service" ]]; then
  # Une instance par port, basculees sans coupure par lexia-basculer (D145) ; la premiere sur le port 8000
  install -m 644 "$APP/deploy/lexia@.service" /etc/systemd/system/lexia@.service
  install -m 755 -o root -g root "$APP/deploy/basculer.sh" /usr/local/sbin/lexia-basculer
  # Lecteur de fichiers isole (B3, D120)
  install -m 644 "$APP/deploy/lexia-lecteur.socket" /etc/systemd/system/lexia-lecteur.socket
  install -m 644 "$APP/deploy/lexia-lecteur@.service" /etc/systemd/system/lexia-lecteur@.service
  systemctl daemon-reload
  systemctl enable --now lexia-lecteur.socket
  systemctl enable lexia@8000
fi
if [[ -f "$APP/deploy/nginx-lexia.conf" ]]; then
  test -f /etc/nginx/conf.d/lexia-amont.conf || install -m 644 "$APP/deploy/nginx-lexia-amont.conf" /etc/nginx/conf.d/lexia-amont.conf
  sed "s/lexia.exemple.fr/$DOMAINE/" "$APP/deploy/nginx-lexia.conf" > /etc/nginx/sites-available/lexia
  ln -sf /etc/nginx/sites-available/lexia /etc/nginx/sites-enabled/lexia
  rm -f /etc/nginx/sites-enabled/default
  nginx -t && systemctl reload nginx
fi

echo "== Pare-feu (si ufw est actif)"
if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then
  ufw allow 'Nginx Full'
fi

cat <<EOF

Etapes suivantes :
  1. Depuis votre Mac :   LEXIA_SERVEUR=root@<ip-du-vps> LEXIA_DOMAINE=$DOMAINE deploy/publier.sh
  2. Sur le serveur, HTTPS : certbot --nginx -d $DOMAINE
  3. Verifier :             curl https://$DOMAINE/api/sante
EOF
