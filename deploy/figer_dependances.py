"""Fige les dependances du serveur avec leurs empreintes (audit du 2026-11-23, B5).

    .venv/bin/python deploy/figer_dependances.py

Lit deploy/requirements-serveur.in (dependances directes), resout l'arbre complet pour le serveur (Linux x86_64,
Python 3.12 d'Ubuntu 24.04) aux versions installees dans le .venv du Mac, celles que les tests ont vues, puis
ecrit :
- deploy/requirements-torch.txt : PyTorch CPU seul, empreintes de l'index de PyTorch ;
- deploy/requirements-serveur.txt : tout le reste, empreintes publiees par PyPI.
Le serveur installe chaque fichier avec un seul index (--index-url) et --require-hashes (deploy/publier.sh) :
avec --extra-index-url, pip prenait la plus haute version entre PyPI et l'index de PyTorch (confusion de
dependances ; Jinja2 en venait deja). Reseau necessaire (pypi.org, download.pytorch.org), rien d'installe.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx

DEPLOY = Path(__file__).resolve().parent
ENTREE = DEPLOY / "requirements-serveur.in"
SORTIE = DEPLOY / "requirements-serveur.txt"
SORTIE_TORCH = DEPLOY / "requirements-torch.txt"
INDEX_TORCH = "https://download.pytorch.org/whl/cpu"
PYTHON_SERVEUR = "3.12"
PLATEFORMES = ("manylinux_2_39_x86_64", "manylinux_2_28_x86_64", "manylinux_2_17_x86_64", "manylinux2014_x86_64",
               "linux_x86_64")
ENTETE = """# FICHIER GENERE par deploy/figer_dependances.py a partir de deploy/requirements-serveur.in : ne pas modifier
# a la main. Linux x86_64, Python {py}, versions du .venv du Mac. Installation : deploy/publier.sh
# (--require-hashes --no-deps, un seul index).
"""


def nom_normal(nom: str) -> str:
    return re.sub(r"[-_.]+", "-", nom).lower()


def lire_json(url: str) -> dict:
    r = httpx.get(url, timeout=60, follow_redirects=True)
    r.raise_for_status()
    return r.json()


def empreintes_pypi(nom: str, version: str) -> list[str]:
    fichiers = lire_json(f"https://pypi.org/pypi/{nom}/{version}/json")["urls"]
    return sorted({f["digests"]["sha256"] for f in fichiers})


def empreintes_torch(version: str) -> list[str]:
    r = httpx.get(f"{INDEX_TORCH}/torch/", timeout=60, follow_redirects=True)
    r.raise_for_status()
    page = r.text
    motif = re.escape(f"torch-{version}".replace("+", "%2B")) + r"-[^\"#]*#sha256=([0-9a-f]{64})"
    vues = sorted(set(re.findall(motif, page)) | set(re.findall(motif.replace("%2B", r"\+"), page)))
    if not vues:
        raise SystemExit(f"torch {version} introuvable sur {INDEX_TORCH}")
    return vues


def resoudre(dossier: Path) -> list[tuple[str, str]]:
    """[(nom, version)] de l'arbre complet pour le serveur, aux versions du .venv quand elles existent."""
    contraintes = dossier / "contraintes.txt"
    gel = subprocess.run([sys.executable, "-m", "pip", "list", "--format=freeze", "--exclude-editable"],
                         capture_output=True, text=True, check=True).stdout
    contraintes.write_text(gel)
    rapport = dossier / "rapport.json"
    commande = [sys.executable, "-m", "pip", "install", "-q", "--dry-run", "--ignore-installed",
                "--report", str(rapport), "--implementation", "cp", "--python-version", PYTHON_SERVEUR,
                "--only-binary=:all:", "--target", str(dossier / "cible"), "--extra-index-url", INDEX_TORCH,
                "-c", str(contraintes), "-r", str(ENTREE)]
    for p in PLATEFORMES:
        commande += ["--platform", p]
    subprocess.run(commande, check=True)
    return sorted(((i["metadata"]["name"], i["metadata"]["version"]) for i in json.loads(rapport.read_text())["install"]),
                  key=lambda nv: nom_normal(nv[0]))


def ligne(nom: str, version: str, empreintes: list[str]) -> str:
    return " \\\n".join([f"{nom}=={version}"] + [f"    --hash=sha256:{e}" for e in empreintes])


def main() -> None:
    with tempfile.TemporaryDirectory() as d:
        paquets = resoudre(Path(d))
    entete = ENTETE.format(py=PYTHON_SERVEUR)
    torch = [(n, v) for n, v in paquets if nom_normal(n) == "torch"]
    if len(torch) != 1 or not torch[0][1].endswith("+cpu"):
        raise SystemExit(f"PyTorch CPU attendu, trouve : {torch}")
    SORTIE_TORCH.write_text(entete + f"# Index : {INDEX_TORCH}\n" + ligne(*torch[0], empreintes_torch(torch[0][1]))
                            + "\n")
    lignes = [ligne(n, v, empreintes_pypi(n, v)) for n, v in paquets if nom_normal(n) != "torch"]
    SORTIE.write_text(entete + "# Index : PyPI seul\n" + "\n".join(lignes) + "\n")
    print(f"{len(lignes)} paquets dans {SORTIE.name}, {torch[0][0]} {torch[0][1]} dans {SORTIE_TORCH.name}")


if __name__ == "__main__":
    main()
