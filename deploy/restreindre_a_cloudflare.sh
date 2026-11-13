#!/usr/bin/env bash
# A lancer sur le serveur, en root, UNIQUEMENT une fois le site passe derriere Cloudflare (DNS en « proxied »,
# SSL/TLS en « Full (strict) ») : les ports 80 et 443 n'acceptent plus que les adresses de Cloudflare, donc
# plus personne ne peut contourner Cloudflare (pare-feu applicatif, protection DDoS) en visant l'IP du serveur.
#
#   bash /opt/lexia/deploy/restreindre_a_cloudflare.sh            # applique
#   bash /opt/lexia/deploy/restreindre_a_cloudflare.sh --annuler  # revient a « ouvert a tous »
#
# Le port 22 (SSH) n'est pas touche. Les plages viennent de https://www.cloudflare.com/ips-v4 et ips-v6.
set -euo pipefail
if [[ "${1:-}" == "--annuler" ]]; then
  ufw allow 80/tcp && ufw allow 443/tcp
  echo "Ports 80 et 443 de nouveau ouverts a tous."
  exit 0
fi
PLAGES=$(curl -fsS https://www.cloudflare.com/ips-v4; echo; curl -fsS https://www.cloudflare.com/ips-v6)
test "$(echo "$PLAGES" | grep -c /)" -ge 10 || { echo "Liste Cloudflare introuvable : rien n'est modifie." >&2; exit 1; }
for p in $PLAGES; do
  ufw allow from "$p" to any port 80 proto tcp comment cloudflare >/dev/null
  ufw allow from "$p" to any port 443 proto tcp comment cloudflare >/dev/null
done
ufw delete allow 80/tcp >/dev/null 2>&1 || true
ufw delete allow 443/tcp >/dev/null 2>&1 || true
echo "Ports 80 et 443 reserves a Cloudflare ($(echo "$PLAGES" | grep -c /) plages)."
