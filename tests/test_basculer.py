"""Redemarrage sans coupure (deploy/basculer.sh, D145) : nouvelle instance sur l'autre port, nginx bascule quand elle
repond, l'ancienne s'arrete ensuite ; en cas d'echec, l'ancienne reste en service.

Le serveur est simule : faux systemctl (unites actives = fichiers), curl (repond pour les ports dont l'unite est
active), nginx, flock, sleep et date."""

import json
import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "deploy" / "basculer.sh"


def outil(dossier: Path, nom: str, corps: str) -> None:
    (dossier / nom).write_text("#!/usr/bin/env bash\n" + corps + "\n")
    (dossier / nom).chmod(0o755)


@pytest.fixture
def serveur(tmp_path):
    faux = tmp_path / "bin"
    faux.mkdir()
    (tmp_path / "actives").mkdir()
    (tmp_path / "activees").mkdir()
    (tmp_path / "systemd").mkdir()
    outil(faux, "systemctl", r'''
echo "$*" >> "$ETAT/systemctl"
args=(); for a; do [ "$a" = --quiet ] || [ "$a" = --now ] || args+=("$a"); done
case "${args[0]}" in
  is-active) test -f "$ETAT/actives/${args[1]}" ;;
  start) [ "${DEMARRAGE_ECHOUE:-}" = 1 ] || touch "$ETAT/actives/${args[1]}" ;;
  stop) rm -f "$ETAT/actives/${args[1]}" ;;
  enable) touch "$ETAT/activees/${args[1]}" ;;
  disable) rm -f "$ETAT/activees/${args[1]}"; [[ "$*" == *--now* ]] && rm -f "$ETAT/actives/${args[1]}"; true ;;
  reload) [ "${RELOAD_ECHOUE:-}" != 1 ] ;;
  *) true ;;
esac''')
    # /api/sante : seulement si l'unite du port est active ; ANCIEN_MUET=1 : l'ancienne ne repond plus ;
    # AMORCE_EN_COURS=n : les n premieres reponses annoncent une amorce en cours
    outil(faux, "curl", r'''
for a; do url="$a"; done
port=$(sed -E 's#.*127\.0\.0\.1:([0-9]+)/.*#\1#' <<<"$url")
echo "$port" >> "$ETAT/curl"
actif=0
[ -f "$ETAT/actives/lexia@$port.service" ] && actif=1
[ "$port" = 8000 ] && [ -f "$ETAT/actives/lexia.service" ] && actif=1
[ "$actif" = 1 ] || exit 7
[ "${ANCIEN_MUET:-}" = "$port" ] && exit 7
n=$(grep -c . "$ETAT/curl")
etat=pret; [ "$n" -le "${AMORCE_EN_COURS:-0}" ] && etat=en_cours
echo "{\"statut\": \"ok\", \"port\": $port, \"amorce\": {\"etat\": \"$etat\"}}"''')
    outil(faux, "nginx", '[ "${NGINX_REFUSE:-}" = 1 ] && exit 1; echo "nginx $*" >> "$ETAT/systemctl"; exit 0')
    outil(faux, "flock", "exit 0")
    outil(faux, "sleep", "exit 0")
    outil(faux, "date", "echo 2026-11-28T14:00:00+01:00")
    env = os.environ | {"PATH": f"{faux}:{os.environ['PATH']}", "ETAT": str(tmp_path),
                        "LEXIA_AMONT": str(tmp_path / "lexia-amont.conf"), "LEXIA_VERROU_BASCULE": str(tmp_path / "v"),
                        "LEXIA_SYSTEMD": str(tmp_path / "systemd"), "LEXIA_ATTENTE": "0", "LEXIA_PAUSE": "0"}
    return tmp_path, env


def amont(port: int) -> str:
    return f"upstream lexia_amont {{\n    server 127.0.0.1:{port};\n}}\n"


def en_service(etat: Path, *unites: str, port: int | None = 8000) -> None:
    for u in unites:
        (etat / "actives" / u).touch()
    if port:
        (etat / "lexia-amont.conf").write_text(amont(port))


def lancer(env, *args, **plus):
    return subprocess.run(["bash", str(SCRIPT), *args], env=env | plus, capture_output=True, text=True)


def actives(etat: Path) -> set[str]:
    return {f.name for f in (etat / "actives").iterdir()}


def port_amont(etat: Path) -> str:
    return (etat / "lexia-amont.conf").read_text().split("127.0.0.1:")[1].split(";")[0]


def appels(etat: Path) -> list[str]:
    return (etat / "systemctl").read_text().splitlines()


def test_bascule_de_8000_vers_8001(serveur):
    etat, env = serveur
    en_service(etat, "lexia@8000.service")
    r = lancer(env)
    assert r.returncode == 0, r.stderr
    assert port_amont(etat) == "8001" and actives(etat) == {"lexia@8001.service"}
    assert {f.name for f in (etat / "activees").iterdir()} == {"lexia@8001.service"}
    assert json.loads(r.stdout)["port"] == 8001          # stdout : seulement /api/sante de la nouvelle instance
    # nginx passe sur la nouvelle avant l'arret de l'ancienne : jamais de requete vers une instance arretee
    lignes = appels(etat)
    assert lignes.index("reload nginx") < lignes.index("disable --quiet --now lexia@8000.service")


def test_retour_de_8001_vers_8000(serveur):
    etat, env = serveur
    en_service(etat, "lexia@8001.service", port=8001)
    assert lancer(env).returncode == 0
    assert port_amont(etat) == "8000" and actives(etat) == {"lexia@8000.service"}


def test_premiere_bascule_remplace_l_ancien_lexia_service(serveur):
    etat, env = serveur
    en_service(etat, "lexia.service", port=None)          # serveur d'avant D145 : pas encore de fichier d'amont
    (etat / "systemd" / "lexia.service").write_text("[Unit]\n")
    r = lancer(env)
    assert r.returncode == 0, r.stderr
    assert port_amont(etat) == "8001" and actives(etat) == {"lexia@8001.service"}
    assert not (etat / "systemd" / "lexia.service").exists() and "daemon-reload" in appels(etat)


def test_nouvelle_version_qui_ne_demarre_pas_l_ancienne_reste(serveur):
    etat, env = serveur
    en_service(etat, "lexia@8000.service")
    r = lancer(env, DEMARRAGE_ECHOUE="1")
    assert r.returncode == 1
    assert port_amont(etat) == "8000" and actives(etat) == {"lexia@8000.service"}
    assert "reste en service" in r.stderr and "reload nginx" not in appels(etat)


def test_rien_ne_repond_code_2(serveur):
    etat, env = serveur
    en_service(etat, "lexia@8000.service")
    r = lancer(env, DEMARRAGE_ECHOUE="1", ANCIEN_MUET="8000")
    assert r.returncode == 2 and "ne repond pas non plus" in r.stderr


def test_nginx_refuse_ancienne_configuration_remise(serveur):
    etat, env = serveur
    en_service(etat, "lexia@8000.service")
    r = lancer(env, NGINX_REFUSE="1")
    assert r.returncode == 1
    assert (etat / "lexia-amont.conf").read_text() == amont(8000)
    assert actives(etat) == {"lexia@8000.service"}       # la nouvelle est arretee, l'ancienne sert toujours


def test_rechargement_de_nginx_rate(serveur):
    etat, env = serveur
    en_service(etat, "lexia@8000.service")
    r = lancer(env, RELOAD_ECHOUE="1")
    assert r.returncode == 1 and (etat / "lexia-amont.conf").read_text() == amont(8000)
    assert actives(etat) == {"lexia@8000.service"}


def test_attend_la_fin_de_l_amorce(serveur):
    etat, env = serveur
    en_service(etat, "lexia@8000.service")
    r = lancer(env, AMORCE_EN_COURS="3", LEXIA_AMORCE_MAX="60")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["amorce"]["etat"] == "pret"
    assert (etat / "curl").read_text().split().count("8001") == 4


def test_port_en_service(serveur):
    etat, env = serveur
    assert lancer(env, "--port").stdout.strip() == "8000"    # avant la premiere bascule
    en_service(etat, port=8001)
    assert lancer(env, "--port").stdout.strip() == "8001"


def test_fichier_d_amont_du_depot_lisible_par_la_bascule(serveur):
    etat, env = serveur
    depot = SCRIPT.parent / "nginx-lexia-amont.conf"
    (etat / "lexia-amont.conf").write_text(depot.read_text())
    assert lancer(env, "--port").stdout.strip() == "8000"
    assert "proxy_pass http://127.0.0.1:8000;" not in (SCRIPT.parent / "nginx-lexia.conf").read_text()


def test_l_instance_en_service_garde_son_index_apres_le_remplacement(tmp_path):
    """La mise a jour nocturne met le nouvel index a la place de l'ancien ~2 minutes avant l'arret de l'instance en
    service : ses nouveaux fils lisent toujours l'ancienne base (api/retrieval/local.py, fichier_epingle)."""
    import sqlite3
    import threading

    from api.retrieval.local import fichier_epingle

    def creer(dossier: Path, valeur: str) -> Path:
        dossier.mkdir()
        with sqlite3.connect(dossier / "lexia.sqlite") as con:
            con.execute("create table t(v)")
            con.execute("insert into t values (?)", (valeur,))
        return dossier / "lexia.sqlite"

    chemin = fichier_epingle(creer(tmp_path / "index", "ancien"))
    if not Path("/proc/self/fd").is_dir():
        pytest.skip("sans /proc (Mac) : le chemin est garde tel quel ; verifie sur Linux (serveur, CI)")
    (tmp_path / "index").rename(tmp_path / "index.precedent")
    creer(tmp_path / "index", "nouveau")
    lu = {}
    fil = threading.Thread(target=lambda: lu.setdefault(
        "v", sqlite3.connect(f"file:{chemin}?mode=ro", uri=True).execute("select v from t").fetchone()[0]))
    fil.start()
    fil.join()
    assert lu["v"] == "ancien"
