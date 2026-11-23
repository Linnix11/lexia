"""Fichiers de deploiement (audit du 2026-11-23, lot 3) : limites nginx par reseau /64 (B9), durcissement systemd
(B4), dependances figees avec empreintes (B5), date du jour a l'heure de Paris (C4), comparaison de la
configuration nginx du serveur avec le depot."""

import ipaddress
import os
import random
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

DEPLOY = Path(__file__).resolve().parent.parent / "deploy"
NGINX = DEPLOY / "nginx-lexia.conf"


# --- B9 : cle des limites nginx ---------------------------------------------------------------------------

def table_nginx() -> list[tuple[re.Pattern, str]]:
    bloc = re.search(r"map \$remote_addr \$lexia_cle_limite \{(.*?)\n\}", NGINX.read_text(), re.S).group(1)
    regles = re.findall(r'^\s*"~(.+?)" (\S+);', bloc, re.M)
    assert len(regles) == 5 and "default $binary_remote_addr;" in bloc
    return [(re.compile(m), v) for m, v in regles]


def cle(adresse: str) -> str:
    """Valeur de $lexia_cle_limite pour une adresse ecrite comme nginx l'ecrit (forme courte de la RFC 5952,
    identique a ipaddress : plus longue suite d'au moins deux groupes nuls, la premiere en cas d'egalite)."""
    for motif, valeur in table_nginx():
        m = motif.search(adresse)
        if m:
            return re.sub(r"\$(\d)", lambda g: m.group(int(g.group(1))), valeur)
    return "binaire:" + adresse


def test_ipv6_meme_reseau_64_meme_cle_et_reseaux_differents_cles_differentes():
    hasard = random.Random(23)
    for _ in range(3000):
        # Prefixes avec et sans suites de zeros, pour passer par chaque regle de la table
        groupes = [hasard.choice([0, 0, 1, hasard.randrange(1 << 16)]) for _ in range(4)]
        prefixe = sum(g << (16 * (7 - i)) for i, g in enumerate(groupes))
        if prefixe >> 112 == 0:
            continue                                     # adresse en « :: » : adresse entiere, voir plus bas
        a = ipaddress.IPv6Address(prefixe | hasard.choice([0, 1, hasard.randrange(1 << 64)]))
        b = ipaddress.IPv6Address(prefixe | hasard.randrange(1 << 64))
        assert cle(a.compressed) == cle(b.compressed), (a, b)
        attendu = ipaddress.ip_network(f"{a}/64", strict=False).network_address.exploded.split(":")[:4]
        assert cle(a.compressed).split(":") == [g.lstrip("0") or "0" for g in attendu]
        autre = ipaddress.IPv6Address(int(a) ^ (1 << 64))
        assert cle(autre.compressed) != cle(a.compressed)


def test_cas_connus_ipv6():
    assert cle("2001:db8:1:2:aaaa:bbbb:cccc:dddd") == cle("2001:db8:1:2::1") == "2001:db8:1:2"
    assert cle("2001:db8::1") == cle("2001:db8:0:0:1:2:3:4") == "2001:db8:0:0"
    assert cle("1::f756:1513:6429:1d42:d810") == "1:0:0:f756"      # « :: » de deux groupes avant le 4e


def test_ipv4_et_adresses_en_deux_points_gardent_l_adresse_entiere():
    for adresse in ("203.0.113.7", "::1", "::ffff:203.0.113.7", "::"):
        assert cle(adresse) == "binaire:" + adresse        # jamais de cle vide (nginx ne compterait rien)


def test_les_deux_zones_utilisent_la_cle_par_reseau():
    zones = re.findall(r"^limit_req_zone (\S+) zone=(\w+)", NGINX.read_text(), re.M)
    assert zones == [("$lexia_cle_limite", "lexia_api"), ("$lexia_cle_limite", "lexia_auth")]


# --- Comparaison de la configuration nginx du serveur (garde_publication.sh) ------------------------------

def nginx_a_jour(tmp_path, en_ligne: str):
    faux = tmp_path / "bin"
    faux.mkdir(exist_ok=True)
    (tmp_path / "en_ligne.conf").write_text(en_ligne)
    (faux / "ssh").write_text(f'#!/usr/bin/env bash\ncat "{tmp_path}/en_ligne.conf"\n')
    (faux / "ssh").chmod(0o755)
    env = os.environ | {"PATH": f"{faux}:{os.environ['PATH']}", "SERVEUR": "faux"}
    return subprocess.run(["bash", "-c", f"source '{DEPLOY / 'garde_publication.sh'}'; nginx_a_jour"],
                          cwd=DEPLOY.parent, env=env, capture_output=True, text=True)


def test_nginx_identique_au_depot_aucun_avertissement(tmp_path):
    # Domaine remplace, indentation et lignes de certbot en plus : sans effet
    conf = NGINX.read_text().replace("lexia.exemple.fr", "lexia.exemple.org").replace("    ", "\t")
    r = nginx_a_jour(tmp_path, "# configuration file /etc/nginx/sites-enabled/lexia:\n" + conf
                     + "\n    listen 443 ssl; # managed by Certbot\n")
    assert r.returncode == 0, r.stderr
    assert "identiques" in r.stdout


def test_nginx_ancien_les_lignes_absentes_sont_listees(tmp_path):
    ancien = (NGINX.read_text().replace("$lexia_cle_limite zone=", "$binary_remote_addr zone=")
              .replace("burst=10 nodelay", "burst=3 nodelay"))
    r = nginx_a_jour(tmp_path, ancien)
    assert r.returncode == 1
    assert "limit_req_zone $lexia_cle_limite zone=lexia_auth:10m rate=5r/m;" in r.stderr
    assert "limit_req zone=lexia_auth burst=10 nodelay;" in r.stderr
    assert "nginx -t && systemctl reload nginx" in r.stderr


def test_publier_compare_nginx_sans_arreter_la_publication():
    assert "nginx_a_jour || true" in (DEPLOY / "publier.sh").read_text()


# --- B4 : durcissement systemd ----------------------------------------------------------------------------

def test_service_durci():
    service = (DEPLOY / "lexia.service").read_text()
    for ligne in ("PrivateDevices=true", "ProtectKernelTunables=true", "ProtectKernelModules=true",
                  "ProtectKernelLogs=true", "ProtectControlGroups=true", "RestrictNamespaces=true",
                  "RestrictSUIDSGID=true", "LockPersonality=true", "CapabilityBoundingSet=",
                  "SystemCallArchitectures=native", "TasksMax=", "MemoryMax=", "OOMPolicy=continue",
                  "Environment=TZ=Europe/Paris"):
        assert re.search(rf"^{re.escape(ligne)}", service, re.M), ligne
    familles = re.search(r"^RestrictAddressFamilies=(.*)$", service, re.M).group(1).split()
    assert {"AF_UNIX", "AF_INET", "AF_INET6"} <= set(familles)
    assert "MemoryDenyWriteExecute" not in service.replace("Pas de MemoryDenyWriteExecute", "")


# --- B5 : dependances figees ------------------------------------------------------------------------------

def exigences(fichier: Path) -> dict[str, tuple[str, list[str]]]:
    texte = re.sub(r"\\\n\s*", " ", fichier.read_text())
    paquets = {}
    for ligne in texte.splitlines():
        ligne = ligne.split("#")[0].strip() if not ligne.lstrip().startswith("--hash") else ligne
        if not ligne:
            continue
        assert not ligne.startswith("-"), f"option dans {fichier.name} : {ligne}"
        nom, version = re.match(r"([A-Za-z0-9_.-]+)==(\S+)", ligne).groups()
        paquets[re.sub(r"[-_.]+", "-", nom).lower()] = (version, re.findall(r"--hash=sha256:([0-9a-f]{64})", ligne))
    return paquets


def test_dependances_figees_avec_empreintes_sans_second_index():
    serveur, torch = exigences(DEPLOY / "requirements-serveur.txt"), exigences(DEPLOY / "requirements-torch.txt")
    assert list(torch) == ["torch"] and torch["torch"][0].endswith("+cpu") and torch["torch"][1]
    assert "torch" not in serveur and len(serveur) > 40
    for nom, (version, empreintes) in serveur.items():
        assert empreintes, f"{nom} sans empreinte"
    # Toutes les dependances directes, a la version demandee
    directes = {}
    for ligne in (DEPLOY / "requirements-serveur.in").read_text().splitlines():
        ligne = ligne.split("#")[0].strip()
        if ligne:
            nom, version = ligne.split("==")
            directes[re.sub(r"[-_.]+", "-", nom).lower()] = version
    for nom, version in directes.items():
        assert (serveur | torch)[nom][0] == version, nom
    # Dependances de PyTorch prises sur PyPI, pas sur son index (Jinja2 en venait)
    assert {"jinja2", "sympy", "networkx", "filelock", "fsspec"} <= set(serveur)


def test_publier_installe_avec_empreintes_et_un_seul_index():
    publier = (DEPLOY / "publier.sh").read_text()
    assert "--extra-index-url" not in re.sub(r"#.*", "", publier)
    installs = [ligne for ligne in re.sub(r"\\\n\s*", " ", publier).splitlines() if "pip install" in ligne
                and "-r deploy/" in ligne]
    assert len(installs) == 2
    for ligne in installs:
        assert "--require-hashes" in ligne and "--no-deps" in ligne and "--index-url" in ligne
    assert "download.pytorch.org/whl/cpu -r deploy/requirements-torch.txt" in installs[0]
    assert "pypi.org/simple -r deploy/requirements-serveur.txt" in installs[1]


# --- C4 : date du jour a l'heure de Paris -----------------------------------------------------------------

@pytest.fixture
def minuit_a_paris(monkeypatch):
    """31 decembre 2026, 23 h 30 UTC : deja le 1er janvier 2027 a Paris."""
    import ingest.env

    class Horloge(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 12, 31, 23, 30, tzinfo=timezone.utc).astimezone(tz)

    monkeypatch.setattr(ingest.env, "datetime", Horloge)


def test_date_de_paris_et_non_du_serveur(minuit_a_paris):
    from ingest.env import aujourdhui_paris
    assert aujourdhui_paris().isoformat() == "2027-01-01"


def test_en_vigueur_bascule_a_minuit_a_paris(minuit_a_paris):
    from api.textes import en_vigueur_aujourdhui
    meta = {"en_vigueur": True, "date_fin": "2027-01-01"}
    assert en_vigueur_aujourdhui(meta, "code_civil") is False
    assert en_vigueur_aujourdhui(meta, "code_civil", aujourdhui="2026-12-31") is True


def test_bascule_franchie_a_minuit_a_paris(minuit_a_paris, tmp_path):
    from ingest import build_index
    from ingest.mise_a_jour import bascule_franchie
    (tmp_path / "lexia.sqlite").write_text("")
    (tmp_path / build_index.BASCULE).write_text("2027-01-01\n")
    assert bascule_franchie(tmp_path) is True
    assert bascule_franchie(tmp_path, aujourdhui="2026-12-31") is False
