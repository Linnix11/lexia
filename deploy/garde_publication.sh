# Garde-fous de deploy/publier.sh (source par lui, teste par tests/test_garde_publication.py).
#
# Plusieurs sessions publient sur le meme serveur depuis le meme depot. Sans garde-fou, deux envois
# simultanes s'ecrasent, une copie plus ancienne efface du code deja en ligne, et un arbre de travail
# modifie envoie en production du code jamais commite (constate le 2026-11-16).
#
#   - arbre_propre        : refuse si des fichiers suivis ou nouveaux, hors dossiers non envoyes, ne sont
#                           pas commites ;
#   - contient_le_serveur : refuse si le commit publie ne contient pas celui deja en ligne (VERSION) ;
#   - prendre_verrou      : un seul envoi a la fois (dossier /run/lexia-publication sur le serveur, efface
#                           au redemarrage de la machine) ; attend qu'il se libere, 30 min au plus ;
#   - rendre_verrou       : le libere, seulement s'il est a nous ;
#   - nginx_a_jour        : signale les limites de debit et routes protegees du depot absentes de la
#                           configuration nginx en service (fichier modifie par certbot, jamais remplace) ;
#   - beta_concorde       : refuse si la beta ecrite dans le HTML prerendu (web/src/site/beta-publiee.json)
#                           differe de celle du serveur (BETA_FERMEE, lue sur /api/config, jamais dans le .env).
# LEXIA_FORCER=1 passe outre arbre_propre, contient_le_serveur et beta_concorde (jamais le verrou).

VERROU="${LEXIA_VERROU:-/run/lexia-publication}"
ATTENTE_VERROU="${LEXIA_ATTENTE_VERROU:-1800}"   # secondes
JETON_VERROU=""

# Dossiers jamais envoyes par le rsync de publier.sh : leurs fichiers non commites ne genent pas.
_hors_envoi() { grep -vE '^(eval/resultats|tests|logs|data|donnees|sauvegardes|web/src|\.claude)/'; }

arbre_propre() {
  [ "${LEXIA_FORCER:-}" = 1 ] && return 0
  local sales
  sales=$(git status --porcelain | cut -c4- | sed 's/^"//; s/"$//' | _hors_envoi || true)
  if [ -n "$sales" ]; then
    echo "Refus : ces fichiers ne sont pas commites et partiraient en production :" >&2
    printf '  %s\n' $sales >&2
    echo "Publiez depuis une copie propre (git worktree add --detach <dossier> <commit>), ou LEXIA_FORCER=1." >&2
    return 1
  fi
}

contient_le_serveur() {
  [ "${LEXIA_FORCER:-}" = 1 ] && return 0
  local en_ligne
  # Premier identifiant de VERSION (« 5f9ba65+649ff41 (citations) » donne 5f9ba65).
  en_ligne=$(ssh "$SERVEUR" "cat $APP/VERSION 2>/dev/null" | head -1 | grep -oE '^[0-9a-f]{7,40}' || true)
  [ -z "$en_ligne" ] && return 0                 # premier deploiement ou VERSION illisible
  if ! git cat-file -e "$en_ligne^{commit}" 2>/dev/null; then
    echo "Refus : la version en ligne ($en_ligne) est inconnue de ce depot (git fetch ?). LEXIA_FORCER=1 pour passer outre." >&2
    return 1
  fi
  if ! git merge-base --is-ancestor "$en_ligne" HEAD; then
    echo "Refus : $(git rev-parse --short HEAD) ne contient pas $en_ligne, deja en ligne : la publication" >&2
    echo "effacerait du code publie par une autre session. Partez de main a jour, ou LEXIA_FORCER=1." >&2
    return 1
  fi
}

prendre_verrou() {
  JETON_VERROU="$(hostname -s)-$$-$(date +%s)"
  local qui="$JETON_VERROU $(git rev-parse --short HEAD 2>/dev/null || echo '?') $(date '+%Y-%m-%d %H:%M:%S')"
  local debut=$SECONDS
  while ! ssh "$SERVEUR" "mkdir '$VERROU' 2>/dev/null && printf '%s\n' '$qui' > '$VERROU/qui'"; do
    if [ $((SECONDS - debut)) -ge "$ATTENTE_VERROU" ]; then
      echo "Refus : une autre publication tient le verrou depuis plus de $ATTENTE_VERROU s :" >&2
      ssh "$SERVEUR" "cat '$VERROU/qui' 2>/dev/null" >&2 || true
      echo "S'il est orphelin : ssh $SERVEUR rm -r $VERROU" >&2
      JETON_VERROU=""
      return 1
    fi
    echo "  verrou pris par : $(ssh "$SERVEUR" "cat '$VERROU/qui' 2>/dev/null" || echo '?') ; nouvel essai dans 30 s"
    sleep "${LEXIA_PAUSE_VERROU:-30}"
  done
  echo "  verrou de publication pris"
}

rendre_verrou() {
  [ -z "$JETON_VERROU" ] && return 0
  ssh "$SERVEUR" "grep -q '^$JETON_VERROU ' '$VERROU/qui' 2>/dev/null && rm -r '$VERROU'" || true
  JETON_VERROU=""
}

# Lignes de deploy/nginx-lexia.conf a retrouver telles quelles dans « nginx -T » du serveur : table des cles de
# limite (B9), zones, route des codes de connexion (SEC-10) et rafales. Avant, elles n'arrivaient sur le serveur
# que recopiees a la main, sans que rien ne le rappelle (audit du 2026-11-23, B9). Avertit, ne bloque pas.
_lignes_nginx() {
  grep -E '^[[:space:]]*(map |"~|default \$binary_remote_addr|limit_req_zone |limit_req |location ~ |proxy_pass )' \
    "${LEXIA_NGINX_DEPOT:-deploy/nginx-lexia.conf}" | sed -E 's/[[:space:]]+/ /g; s/^ //; s/ $//'
}

nginx_a_jour() {
  local en_ligne manque=""
  en_ligne=$(ssh "$SERVEUR" "nginx -T 2>/dev/null" | sed -E 's/[[:space:]]+/ /g; s/^ //; s/ $//') || true
  while IFS= read -r ligne; do
    grep -qxF -- "$ligne" <<<"$en_ligne" || manque+="  $ligne"$'\n'
  done < <(_lignes_nginx)
  if [ -n "$manque" ]; then
    echo "ATTENTION : configuration nginx du serveur differente du depot (deploy/nginx-lexia.conf). Absent :" >&2
    printf '%s' "$manque" >&2
    echo "Recopier ces lignes dans /etc/nginx/sites-available/lexia, puis : nginx -t && systemctl reload nginx" >&2
    return 1
  fi
  echo "  limites nginx identiques au depot"
}

# Beta fermee des pages prerendues (D132) : le HTML est compile sans la configuration du serveur. Une valeur qui ne
# suit pas BETA_FERMEE montrerait « Demander une invitation » sur un site ouvert (ou l'inverse) aux moteurs et au
# premier affichage. Le service en marche fait foi : son /api/config reflete le .env qu'il a lu.
beta_concorde() {
  [ "${LEXIA_FORCER:-}" = 1 ] && return 0
  local fichier="${LEXIA_BETA_DEPOT:-web/src/site/beta-publiee.json}" lire='import json, sys; print(1 if json.load(sys.stdin).get("beta_fermee") else 0)'
  local depot serveur
  # Port de l'instance en service (8000 ou 8001, D145), lu sur le serveur ; 8000 avant la premiere bascule
  local url="${LEXIA_CONFIG_URL:-http://127.0.0.1:\$(/usr/local/sbin/lexia-basculer --port 2>/dev/null || echo 8000)/api/config}"
  depot=$(python3 -c "$lire" < "$fichier")
  if ! serveur=$(ssh "$SERVEUR" "curl -sf --max-time 10 \"$url\"" | python3 -c "$lire" 2>/dev/null); then
    echo "  ATTENTION : configuration du serveur illisible (service arrete ?) : beta non comparee" >&2
    return 0
  fi
  if [ "$depot" != "$serveur" ]; then
    echo "Refus : $fichier annonce beta_fermee=$([ "$depot" = 1 ] && echo true || echo false), le serveur" >&2
    echo "$([ "$serveur" = 1 ] && echo true || echo false) : corrigez le fichier, committez, puis publiez. LEXIA_FORCER=1 pour passer outre." >&2
    return 1
  fi
  echo "  beta fermee du HTML prerendu identique au serveur"
}
