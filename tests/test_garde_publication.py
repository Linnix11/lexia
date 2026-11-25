"""Garde-fous de publication (deploy/garde_publication.sh) : arbre commite, pas de retour en arriere sur la
version en ligne, un seul envoi a la fois. Le serveur est simule : « ssh » execute la commande en local."""

import os
import subprocess
from pathlib import Path

GARDE = Path(__file__).resolve().parent.parent / "deploy" / "garde_publication.sh"


def git(depot, *args):
    return subprocess.run(["git", "-C", str(depot), *args], check=True, capture_output=True, text=True).stdout.strip()


def preparer(tmp_path):
    depot = tmp_path / "depot"
    depot.mkdir()
    git(depot, "init", "-q")
    git(depot, "config", "user.email", "t@t")
    git(depot, "config", "user.name", "t")
    (depot / "a.py").write_text("1\n")
    git(depot, "add", "a.py")
    git(depot, "commit", "-qm", "un")
    serveur = tmp_path / "serveur"
    serveur.mkdir()
    faux = tmp_path / "bin"
    faux.mkdir()
    (faux / "ssh").write_text('#!/usr/bin/env bash\nshift\nexec bash -c "$*"\n')   # ssh <serveur> <commande>
    (faux / "ssh").chmod(0o755)
    env = os.environ | {"PATH": f"{faux}:{os.environ['PATH']}", "SERVEUR": "faux", "APP": str(serveur),
                        "LEXIA_VERROU": str(tmp_path / "verrou"), "LEXIA_PAUSE_VERROU": "0"}
    return depot, serveur, env


def lancer(depot, env, script, **plus):
    return subprocess.run(["bash", "-c", f"set -euo pipefail; source '{GARDE}'; {script}"], cwd=depot,
                          env=env | plus, capture_output=True, text=True)


def test_arbre_modifie_refuse_sauf_dossiers_non_envoyes(tmp_path):
    depot, _, env = preparer(tmp_path)
    assert lancer(depot, env, "arbre_propre").returncode == 0
    (depot / "tests").mkdir()
    (depot / "tests" / "t.py").write_text("x")                 # jamais envoye : sans effet
    assert lancer(depot, env, "arbre_propre").returncode == 0
    (depot / "a.py").write_text("2\n")                         # modifie, non commite
    r = lancer(depot, env, "arbre_propre")
    assert r.returncode == 1 and "a.py" in r.stderr
    assert lancer(depot, env, "arbre_propre", LEXIA_FORCER="1").returncode == 0


def test_pas_de_retour_en_arriere_sur_la_version_en_ligne(tmp_path):
    depot, serveur, env = preparer(tmp_path)
    assert lancer(depot, env, "contient_le_serveur").returncode == 0        # pas de VERSION : premier envoi
    ancien = git(depot, "rev-parse", "--short", "HEAD")
    (depot / "a.py").write_text("2\n")
    git(depot, "commit", "-qam", "deux")
    recent = git(depot, "rev-parse", "--short", "HEAD")
    (serveur / "VERSION").write_text(f"{ancien}+abcdef1 (essai)\n")         # ancienne version en ligne : ok
    assert lancer(depot, env, "contient_le_serveur").returncode == 0
    (serveur / "VERSION").write_text(recent + "\n")
    git(depot, "checkout", "-q", ancien)                                    # publier l'ancien commit : refus
    r = lancer(depot, env, "contient_le_serveur")
    assert r.returncode == 1 and "ne contient pas" in r.stderr
    assert lancer(depot, env, "contient_le_serveur", LEXIA_FORCER="1").returncode == 0
    (serveur / "VERSION").write_text("0123456789abc\n")                     # commit inconnu du depot : refus
    assert lancer(depot, env, "contient_le_serveur").returncode == 1


def test_un_seul_envoi_a_la_fois(tmp_path):
    depot, _, env = preparer(tmp_path)
    verrou = tmp_path / "verrou"
    r = lancer(depot, env, 'prendre_verrou; echo "jeton=$JETON_VERROU"')
    assert r.returncode == 0 and (verrou / "qui").exists()
    # une seconde publication attend puis renonce ; elle ne libere pas le verrou d'une autre
    r = lancer(depot, env, "prendre_verrou", LEXIA_ATTENTE_VERROU="0")
    assert r.returncode == 1 and "tient le verrou" in r.stderr
    assert lancer(depot, env, 'JETON_VERROU=autre-1-1; rendre_verrou').returncode == 0 and verrou.exists()
    # le titulaire le libere, puis un nouvel envoi peut le prendre
    jeton = (verrou / "qui").read_text().split()[0]
    assert lancer(depot, env, f"JETON_VERROU={jeton}; rendre_verrou").returncode == 0 and not verrou.exists()
    r = lancer(depot, env, "prendre_verrou; rendre_verrou")
    assert r.returncode == 0 and not verrou.exists()


PUBLIER = GARDE.parent / "publier.sh"


def commande_rsync():
    """La commande rsync de publier.sh, telle quelle, envoyee vers un dossier local au lieu du serveur."""
    lignes = PUBLIER.read_text().splitlines()
    debut = next(i for i, l in enumerate(lignes) if l.startswith("rsync "))
    fin = next(i for i in range(debut, len(lignes)) if '"$SERVEUR:$APP/"' in lignes[i])
    return "\n".join(lignes[debut:fin + 1]).replace('"$SERVEUR:$APP/"', '"$APP/"')


def test_publication_garde_les_fichiers_ecrits_par_le_serveur(tmp_path):
    """SRV-1 : une copie propre n'a ni le catalogue des cours recuperes ni la date de la derniere mise a jour
    reussie ; rsync --delete ne doit pas les effacer sur le serveur."""
    copie = tmp_path / "copie"
    (copie / "api").mkdir(parents=True)
    (copie / "api" / "main.py").write_text("code\n")
    serveur = tmp_path / "serveur"
    gardes = ["data/cours_recuperes/catalogue.json", "data/mise_a_jour_reussie", "data/index/lexia.sqlite",
              "data/index.precedent/lexia.sqlite", "donnees/lexia.db", ".env", "logs/questions.jsonl"]
    for chemin in gardes + ["ancien.py"]:
        (serveur / chemin).parent.mkdir(parents=True, exist_ok=True)
        (serveur / chemin).write_text("serveur\n")
    script = "EXCLURE_INDEX=(--exclude 'data/index.*' --exclude 'data/index')\n" + commande_rsync()
    r = subprocess.run(["bash", "-c", script], cwd=copie, env=os.environ | {"APP": str(serveur)},
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (serveur / "api" / "main.py").read_text() == "code\n"
    assert not (serveur / "ancien.py").exists()                 # --delete agit bien sur le reste
    for chemin in gardes:
        assert (serveur / chemin).read_text() == "serveur\n", chemin


# Beta fermee ecrite dans le HTML prerendu (web/src/site/beta-publiee.json, D132) : la publication refuse si elle ne
# suit pas BETA_FERMEE du serveur, lue sur /api/config du service en marche (jamais dans le .env).
def preparer_beta(tmp_path, publiee, serveur_ferme):
    depot, serveur, env = preparer(tmp_path)
    (depot / "web" / "src" / "site").mkdir(parents=True)
    (depot / "web" / "src" / "site" / "beta-publiee.json").write_text(f'{{"beta_fermee": {str(publiee).lower()}}}\n')
    config = serveur / "config.json"
    if serveur_ferme is not None:
        config.write_text(f'{{"comptes": true, "beta_fermee": {str(serveur_ferme).lower()}}}')
    return depot, env | {"LEXIA_CONFIG_URL": f"file://{config}"}


def test_beta_publiee_identique_au_serveur(tmp_path):
    depot, env = preparer_beta(tmp_path, True, True)
    assert lancer(depot, env, "beta_concorde").returncode == 0


def test_beta_publiee_differente_du_serveur_refusee(tmp_path):
    depot, env = preparer_beta(tmp_path, True, False)
    r = lancer(depot, env, "beta_concorde")
    assert r.returncode == 1 and "beta-publiee.json" in r.stderr
    assert lancer(depot, env, "beta_concorde", LEXIA_FORCER="1").returncode == 0
    (tmp_path / "b").mkdir()
    depot2, env2 = preparer_beta(tmp_path / "b", False, True)
    assert lancer(depot2, env2, "beta_concorde").returncode == 1


def test_configuration_du_serveur_illisible_avertit_sans_bloquer(tmp_path):
    depot, env = preparer_beta(tmp_path, True, None)       # service arrete ou premier deploiement
    r = lancer(depot, env, "beta_concorde")
    assert r.returncode == 0 and "non comparee" in r.stderr


def test_dependances_du_front_installees_avant_ses_tests():
    # Copie propre (git worktree add --detach) : sans node_modules, « npm test » echouait (vitest introuvable)
    # avant que « npm ci » ne soit lance pour la compilation (publication du 25/11).
    code = [l.split("#")[0] for l in (GARDE.parent / "publier.sh").read_text().splitlines()]
    texte = "\n".join(code)
    assert texte.count("npm ci") == 1                       # une seule installation
    assert texte.index("npm ci") < texte.index("npm test")
