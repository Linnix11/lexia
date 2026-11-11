"""Serveur de production : API sous /api, front compile sur /, retour a index.html pour les ecrans."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.serveur import creer_serveur


def _serveur(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>Lexia</html>")
    (dist / "assets" / "app.js").write_text("console.log(1)")
    (dist / "favicon.svg").write_text("<svg/>")
    (tmp_path / "secret.txt").write_text("ne pas servir")
    api = FastAPI()

    @api.get("/sante")
    def sante():
        return {"statut": "ok"}

    return TestClient(creer_serveur(dist, api))


def test_api_et_front(tmp_path):
    c = _serveur(tmp_path)
    assert c.get("/api/sante").json() == {"statut": "ok"}
    assert "Lexia" in c.get("/").text
    assert c.get("/assets/app.js").text == "console.log(1)"
    assert c.get("/favicon.svg").text == "<svg/>"
    assert "Lexia" in c.get("/assistant").text          # ecran de l'application
    assert c.get("/api/inconnu").status_code == 404      # une route API absente ne renvoie pas le front
    assert "ne pas servir" not in c.get("/../secret.txt").text
