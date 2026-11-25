"""Serveur de production : API sous /api, front compile sur /, retour a index.html pour les ecrans connus, 404
pour les autres adresses (D134)."""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.serveur import creer_serveur


# Comme dist/chemins-application.json ecrit par le prerendu (web/scripts/prerendu.mjs) : routes du routeur du front
CHEMINS = ["/", "/tarifs", "/matieres", "/connexion", "/inscription", "/invitation", "/admin", "/compte",
           "/app", "/app/assistant", "/app/matieres", "/app/fiches", "/app/cartes", "/app/bibliotheque"]


def _serveur(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>Lexia</html>")
    (dist / "introuvable.html").write_text("<html>Page introuvable</html>")
    (dist / "chemins-application.json").write_text(json.dumps(CHEMINS))
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
    assert "Lexia" in c.get("/connexion").text          # ecran de l'application
    assert c.get("/api/inconnu").status_code == 404      # une route API absente ne renvoie pas le front
    assert "ne pas servir" not in c.get("/../secret.txt").text


def test_vues_de_l_espace_servent_l_application(tmp_path):
    """/app/matieres, /app/fiches... (D125) : la coquille de l'application, jamais la page publique prerendue
    de meme nom (/matieres) ni une erreur ; le rechargement d'une vue de l'espace l'affiche donc."""
    c = _serveur(tmp_path)
    publique = tmp_path / "dist" / "pages" / "matieres"
    publique.mkdir(parents=True)
    (publique / "index.html").write_text("<html>Matieres publiques</html>")
    assert c.get("/matieres").text == "<html>Matieres publiques</html>"
    for chemin in ("/app", "/app/", "/app/assistant", "/app/matieres", "/app/fiches", "/app/cartes", "/app/bibliotheque"):
        r = c.get(chemin)
        assert r.status_code == 200, chemin
        assert r.text == "<html>Lexia</html>", chemin
        assert r.headers["cache-control"] == "no-cache", chemin


def test_adresse_inconnue_repond_404_avec_la_page_introuvable(tmp_path):
    """Audit SEO du 24/11 : /a-propos, /Tarifs, /index.html... repondaient 200 avec la coquille, sans noindex (D134)."""
    c = _serveur(tmp_path)
    for chemin in ("/a-propos", "/contact", "/Tarifs", "/index.html", "/introuvable.html", "/page-inexistante-xyz",
                   "/matieres/inexistante", "/guides/zzz", "/assistant", "/app/inconnue", "/appli"):
        r = c.get(chemin)
        assert r.status_code == 404, chemin
        assert r.text == "<html>Page introuvable</html>", chemin
        assert r.headers["x-robots-tag"] == "noindex", chemin
        assert r.headers["cache-control"] == "no-cache", chemin
        assert c.head(chemin).status_code == 404, chemin


def test_ecrans_de_l_application_en_200_mais_noindex(tmp_path):
    """Coquille vide (connexion, inscription, espace) : servie, mais jamais indexee (D134)."""
    c = _serveur(tmp_path)
    for chemin in ("/connexion", "/inscription", "/invitation", "/app", "/app/", "/app/fiches/", "/compte", "/admin"):
        r = c.get(chemin)
        assert r.status_code == 200, chemin
        assert r.text == "<html>Lexia</html>", chemin
        assert r.headers["x-robots-tag"] == "noindex", chemin
    assert "x-robots-tag" not in c.get("/favicon.svg").headers


def test_page_prerendue_indexable(tmp_path):
    c = _serveur(tmp_path)
    publique = tmp_path / "dist" / "pages" / "tarifs"
    publique.mkdir(parents=True)
    (publique / "index.html").write_text("<html>Tarifs</html>")
    r = c.get("/tarifs")
    assert r.status_code == 200 and r.text == "<html>Tarifs</html>"
    assert "x-robots-tag" not in r.headers
    # Le routeur du front distingue la casse : /Tarifs n'est pas une page, meme sur un disque insensible a la casse
    assert c.get("/Tarifs").status_code == 404
    assert c.get("/TARIFS/").status_code == 404


@pytest.mark.parametrize("absent", ["introuvable.html", "chemins-application.json"])
def test_front_incomplet_refuse_au_demarrage(tmp_path, absent):
    """Sans la liste des routes, le serveur repondrait 404 a l'espace etudiant : refus de demarrer."""
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>Lexia</html>")
    (dist / "introuvable.html").write_text("<html>Page introuvable</html>")
    (dist / "chemins-application.json").write_text(json.dumps(CHEMINS))
    (dist / absent).unlink()
    with pytest.raises(RuntimeError, match=absent):
        creer_serveur(dist, FastAPI())
