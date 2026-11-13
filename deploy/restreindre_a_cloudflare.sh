#!/usr/bin/env bash
# A lancer sur le serveur, en root, UNIQUEMENT une fois le site passe derriere Cloudflare (DNS en « proxied »,
# SSL/TLS en « Full (strict) ») : nginx ne sert plus Lexia qu'aux connexions venant de Cloudflare, donc plus
# personne ne peut contourner Cloudflare (pare-feu applicatif, protection DDoS) en visant l'IP du serveur.
#
#   bash /opt/lexia/deploy/restreindre_a_cloudflare.sh            # applique (ou met a jour les plages)
#   bash /opt/lexia/deploy/restreindre_a_cloudflare.sh --annuler  # revient a « ouvert a tous »
#
# Le filtre est dans nginx (bloc server de Lexia) et non dans le pare-feu : les autres sites du serveur
# (ex. n8n) restent joignables directement. Les connexions refusees sont fermees sans reponse (444).
# Le port 22 (SSH) n'est pas touche. Les plages viennent de https://www.cloudflare.com/ips-v4 et ips-v6.
set -euo pipefail
SITE=/etc/nginx/sites-available/lexia
GEO=/etc/nginx/conf.d/lexia-cloudflare-geo.conf
FILTRE=/etc/nginx/snippets/lexia-cloudflare-seul.conf
LIGNE="    include $FILTRE;"
SAUVEGARDE="/root/nginx-lexia.avant-cloudflare-seul.$(date +%Y%m%d-%H%M%S).conf"

recharger() {
  if ! nginx -t 2>/dev/null; then
    cp "$SAUVEGARDE" "$SITE"
    # Le fichier geo est dans le contexte http global : invalide, il casse nginx pour tous les sites.
    if [ -f "$GEO.avant" ]; then mv "$GEO.avant" "$GEO"; else rm -f "$GEO"; fi
    nginx -t
    echo "Configuration nginx invalide : sauvegarde restauree, rien n'est change." >&2
    exit 1
  fi
  rm -f "$GEO.avant"
  systemctl reload nginx
}

cp "$SITE" "$SAUVEGARDE"
[ -f "$GEO" ] && cp "$GEO" "$GEO.avant" || rm -f "$GEO.avant"
if [[ "${1:-}" == "--annuler" ]]; then
  sed -i "\#include $FILTRE;#d" "$SITE"
  recharger
  echo "Lexia de nouveau joignable directement (sans passer par Cloudflare)."
  exit 0
fi

PLAGES=$(curl -fsS https://www.cloudflare.com/ips-v4; echo; curl -fsS https://www.cloudflare.com/ips-v6)
test "$(echo "$PLAGES" | grep -c /)" -ge 10 || { echo "Liste Cloudflare introuvable : rien n'est modifie." >&2; exit 1; }
{
  echo "# Genere par deploy/restreindre_a_cloudflare.sh : 1 si la connexion vient de Cloudflare."
  echo "# \$realip_remote_addr = adresse de la connexion, avant remplacement par l'en-tete CF-Connecting-IP."
  echo "geo \$realip_remote_addr \$lexia_depuis_cloudflare {"
  echo "    default 0;"
  for p in $PLAGES; do echo "    $p 1;"; done
  echo "}"
} > "$GEO"
echo 'if ($lexia_depuis_cloudflare = 0) { return 444; }' > "$FILTRE"
# Apres chaque server_name de Lexia (blocs 443 et 80), une seule fois.
grep -qF "include $FILTRE;" "$SITE" || sed -i "/^\s*server_name .*;/a\\$LIGNE" "$SITE"
recharger
echo "Lexia reservee a Cloudflare ($(echo "$PLAGES" | grep -c /) plages). Sauvegarde : $SAUVEGARDE"
