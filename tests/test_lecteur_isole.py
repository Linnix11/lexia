"""Lecteur des fichiers deposes dans un service a part (audit du 23/11, B3 ; D120)."""

import socket
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from api import extraction

RACINE = Path(__file__).resolve().parent.parent
TEXTE = ("Introduction au droit des obligations. " * 20).encode()


def _service(chemin: Path, repondre=True):
    """Imite lexia-lecteur.socket (Accept=yes) : une connexion, un lecteur dont stdin et stdout sont la socket."""
    serveur = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    serveur.bind(str(chemin))
    serveur.listen(4)

    def boucle():
        while True:
            try:
                conn, _ = serveur.accept()
            except OSError:
                return
            if repondre:
                subprocess.run([sys.executable, "-m", "api.extraction", "--socket"], stdin=conn.fileno(),
                               stdout=conn.fileno(), cwd=RACINE, timeout=60)
                conn.close()
            else:
                threading.Timer(5, conn.close).start()   # lecteur bloque (OCR trop long)
    threading.Thread(target=boucle, daemon=True).start()
    return serveur


@pytest.fixture
def chemin(tmp_path_factory):
    # chemin court : une socket Unix est limitee a ~100 caracteres
    import tempfile
    d = Path(tempfile.mkdtemp(prefix="lx", dir="/tmp"))
    yield d / "l.sock"
    for f in d.iterdir():
        f.unlink()
    d.rmdir()


def test_lecture_par_la_socket_du_service(chemin, monkeypatch):
    serveur = _service(chemin)
    monkeypatch.setenv("LEXIA_LECTEUR_SOCKET", str(chemin))
    monkeypatch.setattr(extraction, "_commande_lecteur", lambda nom: pytest.fail("processus fils lance"))
    try:
        lecture = extraction.lire_isole("cours.txt", TEXTE)
        assert "droit des obligations" in lecture.pages[0][1]
        with pytest.raises(extraction.ErreurCours, match="Format non pris en charge"):
            extraction.lire_isole("cours.exe", TEXTE)              # erreur du lecteur rendue telle quelle
    finally:
        serveur.close()


def test_service_absent_refus_clair_sans_repli_sur_le_processus_fils(chemin, monkeypatch):
    monkeypatch.setenv("LEXIA_LECTEUR_SOCKET", str(chemin))       # configure mais non demarre
    monkeypatch.setattr(extraction, "_commande_lecteur", lambda nom: pytest.fail("repli sous l'utilisateur lexia"))
    with pytest.raises(extraction.ErreurCours, match="momentanément indisponible"):
        extraction.lire_isole("cours.txt", TEXTE)


def test_lecteur_bloque_delai_respecte(chemin, monkeypatch):
    import time
    serveur = _service(chemin, repondre=False)
    monkeypatch.setenv("LEXIA_LECTEUR_SOCKET", str(chemin))
    try:
        debut = time.monotonic()
        with pytest.raises(extraction.ErreurCours, match="trop de temps"):
            extraction.lire_isole("cours.txt", TEXTE, delai=1)
        assert time.monotonic() - debut < 3
    finally:
        serveur.close()


def _directives(fichier: str) -> dict[str, str]:
    out = {}
    for ligne in (RACINE / "deploy" / fichier).read_text().splitlines():
        if "=" in ligne and not ligne.startswith("#"):
            cle, valeur = ligne.split("=", 1)
            out[cle.strip()] = valeur.strip()
    return out


def test_unites_systemd_isolent_le_lecteur():
    socket_ = _directives("lexia-lecteur.socket")
    assert socket_["Accept"] == "yes" and socket_["SocketUser"] == "lexia" and socket_["SocketMode"] == "0600"
    service = _directives("lexia-lecteur@.service")
    assert service["DynamicUser"] == "yes" and service["PrivateNetwork"] == "true"
    assert service["RestrictAddressFamilies"] == "AF_UNIX" and "--socket" in service["ExecStart"]
    masques = service["InaccessiblePaths"].split()
    for chemin in ("/opt/lexia/.env", "/opt/lexia/donnees", "/opt/lexia/logs", "/opt/lexia/sauvegardes"):
        assert f"-{chemin}" in masques
    assert int(service["RuntimeMaxSec"]) > extraction.DELAI_LECTURE_OCR
    assert "User" not in service and "EnvironmentFile" not in service   # ni lexia ni le .env


def test_publication_installe_et_active_le_lecteur():
    publier = (RACINE / "deploy" / "publier.sh").read_text()
    assert "lexia-lecteur.socket /etc/systemd/system/" in publier
    assert "lexia-lecteur@.service /etc/systemd/system/" in publier
    assert "systemctl enable --now lexia-lecteur.socket" in publier
    assert "LEXIA_LECTEUR_SOCKET=/run/lexia-lecteur.sock" in publier
    assert "systemctl enable --now lexia-lecteur.socket" in (RACINE / "deploy" / "installer_serveur.sh").read_text()
    assert "LEXIA_LECTEUR_SOCKET=/run/lexia-lecteur.sock" in (RACINE / "deploy" / "env.production.exemple").read_text()
