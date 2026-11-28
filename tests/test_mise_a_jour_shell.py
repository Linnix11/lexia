"""Bascule de l'index par deploy/mettre_a_jour_corpus.sh (audit du 19/11, SRV-8, TST-4 ; audit du 23/11, C2, T8).

Le serveur est simule : dossiers temporaires, et faux runuser, flock, ionice, df, date, python (le vrai calcul de
l'index n'est pas lance) et lexia-basculer (deploy/basculer.sh, D145, teste dans tests/test_basculer.py)."""

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "deploy" / "mettre_a_jour_corpus.sh"


def outil(dossier: Path, nom: str, corps: str) -> None:
    (dossier / nom).write_text("#!/usr/bin/env bash\n" + corps + "\n")
    (dossier / nom).chmod(0o755)


@pytest.fixture
def serveur(tmp_path):
    app = tmp_path / "opt"
    (app / "data" / "index").mkdir(parents=True)
    (app / "data" / "index" / "lexia.sqlite").write_text("ancien")
    (app / ".venv" / "bin").mkdir(parents=True)
    # python : « -m ingest.mise_a_jour » prepare data/index.nouveau, « --alerte » note le message
    outil(app / ".venv" / "bin", "python", """
if [ "$2" = ingest.fraicheur ]; then echo "$4" >> "$JOURNAL/alertes"; exit 0; fi
mkdir -p data/index.nouveau && echo nouveau > data/index.nouveau/lexia.sqlite
exit "${CODE_MAJ:-0}\"""")
    faux = tmp_path / "bin"
    faux.mkdir()
    outil(faux, "runuser", 'shift 3; exec "$@"')                     # runuser -u lexia -- commande
    outil(faux, "flock", "exit 0")
    outil(faux, "ionice", 'shift; exec "$@"')
    outil(faux, "date", "echo 2026-11-20T04:30:00+01:00")
    # BASCULE=ok : nouvelle instance en service ; refus : refusee, l'ancienne repond (code 1) ; muet : plus rien ne
    # repond (code 2) ; ancien : ne demarre qu'avec l'ancien index (retour reussi apres un code 2)
    outil(faux, "basculer", 'echo "$(cat data/index/lexia.sqlite)" >> "$JOURNAL/basculer"; '
                            'case "${BASCULE:-ok}" in ok) echo "{}";; refus) exit 1;; muet) exit 2;; '
                            'ancien) grep -qx ancien data/index/lexia.sqlite && echo "{}" || exit 2;; esac')
    outil(faux, "sleep", "exit 0")
    outil(faux, "df", 'echo "Filesystem 1024-blocks Used Available Capacity Mounted"; '
                      'echo "disque 100000000 0 ${LIBRE_KO:-99999999} 0% /"')
    outil(faux, "mv", 'for a; do last="$a"; done; [ "$last" = data/index ] && [ "${MV_ECHOUE:-}" = 1 ] '
                      '&& [ "$1" = data/index.nouveau ] && exit 1; exec /bin/mv "$@"')
    env = os.environ | {"PATH": f"{faux}:{os.environ['PATH']}", "LEXIA_APP": str(app), "JOURNAL": str(tmp_path),
                        "LEXIA_VERROU_MAJ": str(tmp_path / "verrou"),
                        "LEXIA_BASCULER": str(faux / "basculer")}
    return app, env, tmp_path


def lancer(env, **plus):
    return subprocess.run(["bash", str(SCRIPT)], env=env | plus, capture_output=True, text=True)


def contenu(app, dossier):
    return (app / "data" / dossier / "lexia.sqlite").read_text().strip()


def bascules(journal):
    """Index en service a chaque appel de lexia-basculer."""
    f = journal / "basculer"
    return f.read_text().split() if f.exists() else []


def alertes(journal):
    f = journal / "alertes"
    return f.read_text() if f.exists() else ""


def test_bascule_reussie(serveur):
    app, env, journal = serveur
    (app / "data" / "index.echec").mkdir()
    r = lancer(env)
    assert r.returncode == 0, r.stderr
    assert contenu(app, "index") == "nouveau" and contenu(app, "index.precedent") == "ancien"
    assert not (app / "data" / "index.echec").exists() and (app / "data" / "mise_a_jour_reussie").exists()
    assert bascules(journal) == ["nouveau"] and alertes(journal) == ""


def test_mv_rate_l_ancien_index_revient_et_alerte(serveur):
    app, env, journal = serveur
    r = lancer(env, MV_ECHOUE="1")
    assert r.returncode == 1
    assert contenu(app, "index") == "ancien"                                 # jamais de serveur sans index
    assert "bascule" in alertes(journal) and bascules(journal) == []


def test_service_muet_retour_a_l_index_precedent(serveur):
    app, env, journal = serveur
    r = lancer(env, BASCULE="ancien")
    assert r.returncode == 1
    assert contenu(app, "index") == "ancien" and contenu(app, "index.echec") == "nouveau"
    assert "ne repondait plus" in alertes(journal) and "toujours" not in alertes(journal)
    assert "index precedent remis en service" in r.stdout
    assert bascules(journal) == ["nouveau", "ancien"]


def test_nouvel_index_refuse_l_ancienne_instance_sert_toujours(serveur):
    """D145 : code 1, l'instance en service n'a pas quitte l'ancien index : index remis, pas de seconde bascule."""
    app, env, journal = serveur
    r = lancer(env, BASCULE="refus")
    assert r.returncode == 1
    assert contenu(app, "index") == "ancien" and contenu(app, "index.echec") == "nouveau"
    assert bascules(journal) == ["nouveau"] and "index precedent remis en service" in r.stdout
    assert len(alertes(journal).splitlines()) == 1


def test_service_toujours_muet_apres_le_retour_alerte_aussi(serveur):
    """C2 : le premier e-mail laissait croire que tout etait rentre dans l'ordre (audit du 2026-11-23)."""
    app, env, journal = serveur
    r = lancer(env, BASCULE="muet")
    assert r.returncode == 1 and contenu(app, "index") == "ancien"
    lignes = alertes(journal).splitlines()
    assert len(lignes) == 2 and "ne repondait plus" in lignes[0]
    assert "toujours" in lignes[1] and "hors service" in lignes[1]


def test_rien_de_nouveau_code_3_pas_de_bascule(serveur):
    """T8 : code 3 de Python, rien a faire : ni bascule ni redemarrage ni alerte, passage note reussi."""
    app, env, journal = serveur
    r = lancer(env, CODE_MAJ="3")
    assert r.returncode == 0, r.stderr
    assert contenu(app, "index") == "ancien" and not (app / "data" / "index.precedent").exists()
    assert bascules(journal) == [] and alertes(journal) == ""
    assert (app / "data" / "mise_a_jour_reussie").exists()


def test_echec_de_python_code_1_alerte_index_inchange(serveur):
    """T8 : code 1 de Python : alerte avec le code, index en service inchange, passage non note reussi."""
    app, env, journal = serveur
    r = lancer(env, CODE_MAJ="1")
    assert r.returncode == 1
    assert contenu(app, "index") == "ancien" and not (app / "data" / "index.precedent").exists()
    assert "code 1" in alertes(journal) and bascules(journal) == []
    assert not (app / "data" / "mise_a_jour_reussie").exists()


def test_disque_trop_plein_rien_n_est_lance(serveur):
    app, env, journal = serveur
    r = lancer(env, LIBRE_KO="1000")
    assert r.returncode == 1 and not (app / "data" / "index.nouveau").exists()
    assert "espace disque" in alertes(journal) and contenu(app, "index") == "ancien"
