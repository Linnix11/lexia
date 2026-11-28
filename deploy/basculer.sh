#!/usr/bin/env bash
# Redemarrage sans coupure de Lexia (D145).
#
# Avant : « systemctl restart lexia » coupait le site environ 2 minutes (chargement des modeles et de l'index,
# 89 a 104 s mesurees les 27 et 28/11 ; 15 coupures de 121 a 141 s vues par la veille du Mac du 18 au 27/11, toutes
# a une publication ou a la mise a jour de la nuit). Ici, la nouvelle version demarre sur l'autre port (8000 ou
# 8001) pendant que l'ancienne sert, nginx passe dessus quand elle repond et a fini son amorce, puis l'ancienne
# s'arrete apres avoir termine ses reponses en cours. Si la nouvelle ne demarre pas, l'ancienne continue.
#
# Installe par publier.sh en copie appartenant a root (/usr/local/sbin/lexia-basculer). Appele par publier.sh et
# par la mise a jour nocturne (deploy/mettre_a_jour_corpus.sh).
#
#   lexia-basculer          # bascule ; affiche /api/sante de la nouvelle instance
#   lexia-basculer --port   # port de l'instance en service (lu dans la configuration nginx)
#
# Codes de sortie : 0 bascule faite ; 1 nouvelle version refusee, l'ancienne repond toujours ; 2 plus rien ne repond.
set -euo pipefail
# Variables LEXIA_* : seulement pour les tests (tests/test_basculer.py).
AMONT="${LEXIA_AMONT:-/etc/nginx/conf.d/lexia-amont.conf}"
ATTENTE="${LEXIA_ATTENTE:-300}"        # secondes pour que la nouvelle instance reponde
AMORCE_MAX="${LEXIA_AMORCE_MAX:-120}"  # secondes d'amorce au plus (premier parcours des vecteurs, R-2)
PAUSE="${LEXIA_PAUSE:-3}"              # anciens processus nginx : finir d'envoyer leurs requetes a l'ancienne
SYSTEMD="${LEXIA_SYSTEMD:-/etc/systemd/system}"

port_en_service() {
  local p
  p=$(sed -nE 's/^[[:space:]]*server 127\.0\.0\.1:([0-9]+);.*/\1/p' "$AMONT" 2>/dev/null | head -1) || true
  echo "${p:-8000}"
}
sante() { curl -sf --max-time 5 "http://127.0.0.1:$1/api/sante"; }
journal() { echo "$(date -Is) $*" >&2; }   # stdout : seulement /api/sante, lu par les appelants

if [ "${1:-}" = --port ]; then port_en_service; exit 0; fi

# Une bascule a la fois (publication et mise a jour nocturne)
exec 8>"${LEXIA_VERROU_BASCULE:-/run/lexia-bascule.lock}"
flock -w 900 8 || { journal "ERREUR : une autre bascule ne finit pas" >&2; exit 1; }

ancien=$(port_en_service)
nouveau=$([ "$ancien" = 8000 ] && echo 8001 || echo 8000)
# Service d'avant D145 (lexia.service, port 8000) : remplace par lexia@8001 a la premiere bascule.
ancienne_unite="lexia@$ancien.service"
if [ "$ancien" = 8000 ] && systemctl is-active --quiet lexia.service; then ancienne_unite=lexia.service; fi
unite="lexia@$nouveau.service"

refuser() {
  journal "ERREUR : $1 ; journalctl -u $unite -n 50" >&2
  systemctl stop "$unite" || true
  if sante "$ancien" >/dev/null; then
    journal "l'ancienne version (port $ancien) reste en service" >&2
    exit 1
  fi
  journal "ERREUR : l'ancienne version (port $ancien) ne repond pas non plus" >&2
  exit 2
}

journal "demarrage de la nouvelle version sur le port $nouveau (port $ancien en service)"
# Reste d'une bascule ratee : cette instance ne recoit rien (nginx envoie tout a l'ancienne)
systemctl stop "$unite" 2>/dev/null || true
systemctl reset-failed "$unite" 2>/dev/null || true
systemctl start "$unite" || refuser "systemctl start a echoue"

debut=$SECONDS
until reponse=$(sante "$nouveau"); do
  # Arret ou relance en boucle (Restart=on-failure) : inutile d'attendre la fin du delai
  systemctl is-active --quiet "$unite" || refuser "la nouvelle version s'est arretee au demarrage"
  [ $((SECONDS - debut)) -lt "$ATTENTE" ] || refuser "la nouvelle version ne repond pas apres $ATTENTE s"
  sleep 2
done
journal "la nouvelle version repond apres $((SECONDS - debut)) s"

# Amorce (premier parcours des vecteurs, ~17 s) : sans elle, la premiere question paierait ce parcours.
etat_amorce() { python3 -c 'import json, sys; print((json.load(sys.stdin).get("amorce") or {}).get("etat", ""))' 2>/dev/null || true; }
debut=$SECONDS
while [ "$(etat_amorce <<<"$reponse")" = en_cours ] && [ $((SECONDS - debut)) -lt "$AMORCE_MAX" ]; do
  sleep 2
  reponse=$(sante "$nouveau") || refuser "la nouvelle version ne repond plus pendant son amorce"
done

# nginx : ecriture atomique, verification, rechargement en douceur (les requetes en cours se terminent)
sauvegarde=$(mktemp)
cp "$AMONT" "$sauvegarde" 2>/dev/null || : > "$sauvegarde"
printf '%s\n' "# Ecrit par lexia-basculer le $(date -Is) (D145) : instance en service. Ne pas modifier a la main." \
  "upstream lexia_amont {" "    server 127.0.0.1:$nouveau;" "}" > "$AMONT.tmp"
mv "$AMONT.tmp" "$AMONT"
if ! nginx -t -q || ! systemctl reload nginx; then
  if [ -s "$sauvegarde" ]; then cp "$sauvegarde" "$AMONT"; else rm -f "$AMONT"; fi
  rm -f "$sauvegarde"
  nginx -t -q && systemctl reload nginx || true
  refuser "nginx refuse la nouvelle configuration"
fi
rm -f "$sauvegarde"
journal "nginx envoie les requetes au port $nouveau"

systemctl enable --quiet "$unite"
sleep "$PAUSE"
# Arret en douceur : uvicorn n'accepte plus de requete et termine celles en cours (130 s au plus)
systemctl disable --quiet --now "$ancienne_unite" || true
if [ "$ancienne_unite" = lexia.service ]; then
  rm -f "$SYSTEMD/lexia.service"
  systemctl daemon-reload
fi
journal "ancienne version arretee ($ancienne_unite)"
echo "$reponse"
