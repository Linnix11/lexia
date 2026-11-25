#!/usr/bin/env bash
# Publie Lexia sur le VPS depuis la machine de developpement (Mac).
#
#   LEXIA_SERVEUR=root@1.2.3.4 LEXIA_DOMAINE=lexia.mondomaine.fr deploy/publier.sh
#
# Etapes : tests, compilation du front, envoi du code + front + index de recherche,
# installation des dependances, redemarrage du service, puis IndexNow si LEXIA_INDEXNOW=1 (D134, desactive par
# defaut). Le .env n'est envoye que s'il n'existe pas encore sur le serveur (deploy/env.production.exemple
# sert de modele).
set -euo pipefail

SERVEUR="${LEXIA_SERVEUR:?Definir LEXIA_SERVEUR, ex. root@1.2.3.4}"
DOMAINE="${LEXIA_DOMAINE:-}"
APP=/opt/lexia
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RACINE"
# Garde-fous entre sessions (deploy/garde_publication.sh) : arbre commite, pas de retour en arriere sur
# la version en ligne, un seul envoi a la fois. Verifies des le depart pour echouer avant les tests.
source deploy/garde_publication.sh
arbre_propre
contient_le_serveur
beta_concorde        # beta du HTML prerendu = beta du serveur (D132)

echo "== Tests"
.venv/bin/python -m pytest -q
# npm ci avant les tests du front : une copie propre n'a pas de node_modules (vitest introuvable, 25/11)
(cd web && npm ci && npm test)

echo "== Compilation du front"
(cd web && npm run build)

echo "== Index de recherche"
# Le serveur met son index a jour chaque nuit depuis la DILA (D78, deploy/mettre_a_jour_corpus.sh) : par
# defaut il est garde tel quel et seuls le code et le front partent. LEXIA_AVEC_INDEX=1 envoie l'index
# du Mac a la place (4 Go, et il remplace un index peut-etre plus recent). LEXIA_SANS_INDEX est ignore.
# Les dossiers data/index.* (index en preparation ou precedent) du serveur ne sont jamais touches.
EXCLURE_INDEX=(--exclude 'data/index.*')
if [ "${LEXIA_AVEC_INDEX:-}" = 1 ]; then
  test -f data/index/lexia.sqlite || { echo "data/index absent : lancer python -m ingest.build_index" >&2; exit 1; }
  echo "  index du Mac envoye (LEXIA_AVEC_INDEX=1)"
else
  EXCLURE_INDEX+=(--exclude 'data/index')
  echo "  index du serveur conserve"
fi

echo "== Verrou de publication"
prendre_verrou
trap rendre_verrou EXIT
contient_le_serveur   # une autre session a pu publier pendant nos tests

echo "== Version"
git rev-parse --short HEAD > VERSION 2>/dev/null && echo "  $(cat VERSION)" || echo "inconnue" > VERSION

echo "== Envoi du code, du front et de l'index (rsync)"
# --partial-dir : une coupure pendant les 4 Go d'index laisse le morceau deja recu dans un dossier
# a part et reprend au prochain envoi. Sans « -dir », rsync ecrit dans le fichier de destination et
# une coupure laisse l'index de production tronque (constate le 2026-11-14).
# --timeout : une connexion muette est abandonnee au lieu de rester bloquee.
# data/cours_recuperes et data/mise_a_jour_reussie sont ecrits par la mise a jour nocturne du serveur et
# absents d'une copie propre : sans exclusion, --delete les effacerait (audit du 19/11, SRV-1).
rsync -az --delete --partial-dir=.rsync-partiel --timeout=120 \
  --exclude '.git' --exclude '.venv' --exclude '.cache' --exclude 'node_modules' --exclude '.env' \
  --exclude 'donnees' --exclude '.claude' --exclude 'sauvegardes' \
  --exclude 'data/raw' --exclude 'data/embeddings' --exclude 'data/passages' \
  --exclude 'data/cours_recuperes' --exclude 'data/mise_a_jour_reussie' --exclude 'data/citations-publiees.json' \
  --exclude 'logs' --exclude 'eval/resultats' --exclude '__pycache__' --exclude '.pytest_cache' \
  --exclude 'web/src' --exclude 'tests' \
  ${EXCLURE_INDEX[@]+"${EXCLURE_INDEX[@]}"} \
  ./ "$SERVEUR:$APP/"

# Articles cites par les pages publiques : web/src ne part pas, la copie est comparee chaque nuit au nouvel index
# (api.donnees_publiques.ecarts_citations, audit du 2026-11-23, C5).
rsync -az --timeout=120 web/src/site/contenu/citations.json "$SERVEUR:$APP/data/citations-publiees.json"

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
mkdir -p donnees sauvegardes logs && chmod 700 donnees sauvegardes logs
# Base, journal WAL et journaux crees en 644 avant UMask=0077 (audit de la base du 2026-11-18, D99)
find donnees logs sauvegardes -maxdepth 1 -type f -exec chmod 600 {} +
chown -R lexia:lexia $APP
# OCR des cours scannes et des photos (D107) : installe une seule fois, seulement s'il manque.
dpkg -s tesseract-ocr tesseract-ocr-fra poppler-utils >/dev/null 2>&1 || { apt-get update -q && apt-get install -y -q tesseract-ocr tesseract-ocr-fra poppler-utils; }
# Python et pip tournent en tant que lexia : root n'execute jamais du code modifiable par le service.
runuser -u lexia -- bash -c 'test -d .venv || python3 -m venv .venv'
runuser -u lexia -- .venv/bin/pip install -q --no-cache-dir --upgrade pip
# Versions figees avec empreintes (deploy/figer_dependances.py, audit du 2026-11-23, B5) : un seul index par
# fichier (plus de --extra-index-url, qui laissait pip choisir entre PyPI et l'index de PyTorch), --no-deps
# (l'arbre complet est deja dans les fichiers), roues seulement, puis pip check.
runuser -u lexia -- .venv/bin/pip install -q --no-cache-dir --require-hashes --no-deps --only-binary=:all: \
  --index-url https://download.pytorch.org/whl/cpu -r deploy/requirements-torch.txt
runuser -u lexia -- .venv/bin/pip install -q --no-cache-dir --require-hashes --no-deps --only-binary=:all: \
  --index-url https://pypi.org/simple -r deploy/requirements-serveur.txt
# Paquet ancien reste dans le .venv (plus dans la liste) : avertissement, sans arreter la publication en route.
runuser -u lexia -- .venv/bin/pip check || echo "  ATTENTION : pip check signale des dependances incoherentes (ci-dessus)"
cp deploy/lexia.service /etc/systemd/system/lexia.service
# Lecteur de fichiers isole (B3, D120) : code et .venv lisibles par son utilisateur dynamique (le code est public),
# .env, donnees, logs et sauvegardes restent en 600 et 700 et lui sont en plus masques par l'unite.
install -m 644 deploy/lexia-lecteur.socket /etc/systemd/system/lexia-lecteur.socket
install -m 644 deploy/lexia-lecteur@.service /etc/systemd/system/lexia-lecteur@.service
chmod 755 $APP && chmod -R go+rX $APP/api $APP/.venv
grep -q '^LEXIA_LECTEUR_SOCKET=' .env || printf 'LEXIA_LECTEUR_SOCKET=/run/lexia-lecteur.sock\n' >> .env
chmod 755 deploy/sauvegarder_comptes.sh
# Mise a jour nocturne du corpus (D78) : lancee par root, donc copie appartenant a root, hors de /opt/lexia.
install -m 755 -o root -g root deploy/mettre_a_jour_corpus.sh /usr/local/sbin/lexia-mise-a-jour
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
systemctl enable --now lexia-lecteur.socket >/dev/null
systemctl enable lexia >/dev/null
systemctl restart lexia
EOF

echo "== Configuration nginx"
# Le fichier du site est modifie par certbot sur le serveur : publier.sh ne le remplace pas. Les limites de
# debit (B9) et la route des codes de connexion (SEC-10) sont donc comparees a celles du depot.
nginx_a_jour || true

echo "== Attente du demarrage (le premier lancement telecharge les modeles)"
for i in $(seq 1 60); do
  if ssh "$SERVEUR" "curl -sf http://127.0.0.1:8000/api/sante" >/dev/null; then
    ssh "$SERVEUR" "curl -s http://127.0.0.1:8000/api/sante"; echo
    echo "Publie."
    # IndexNow (D134) : prepare, desactive par defaut. LEXIA_INDEXNOW=1 signale les adresses du sitemap aux
    # moteurs qui suivent le protocole (Bing...) ; un refus n'annule pas la publication (docs/seo-geo.md, partie 7).
    if [ "${LEXIA_INDEXNOW:-}" = 1 ]; then
      python3 deploy/indexnow.py --envoyer || echo "  ATTENTION : IndexNow n'a pas accepte l'envoi (ci-dessus)" >&2
    fi
    exit 0
  fi
  sleep 10
done
echo "Le service ne repond pas encore : ssh $SERVEUR journalctl -u lexia -n 50" >&2
exit 1
