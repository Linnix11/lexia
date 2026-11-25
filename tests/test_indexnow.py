"""IndexNow prepare mais pas active (D134) : fichier de cle publie avec le front, script a blanc par defaut, envoi
seulement sur demande. Aucun test n'ouvre de connexion : l'ouverture d'adresse est remplacee."""

import importlib.util
import io
import json
import re
import urllib.error
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("indexnow", RACINE / "deploy" / "indexnow.py")
indexnow = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(indexnow)

SITEMAP = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://lexia-axionstudio.cloud/</loc></url>
  <url><loc>https://lexia-axionstudio.cloud/tarifs</loc></url>
  <url><loc>https://lexia-axionstudio.cloud/guides/methode-fiche-arret</loc><lastmod>2026-11-23</lastmod></url>
</urlset>
"""


class _Reponse(io.BytesIO):
    def __init__(self, corps=b"", status=200):
        super().__init__(corps)
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _interdit(*_a, **_k):
    raise AssertionError("aucune connexion ne doit partir")


@pytest.fixture
def sitemap(tmp_path):
    f = tmp_path / "sitemap.xml"
    f.write_text(SITEMAP)
    return f


def test_fichier_de_cle_publie_avec_le_front():
    """Vite copie web/public a la racine de dist/, servi par api/serveur.py : https://<site>/<cle>.txt."""
    assert re.fullmatch(r"[0-9a-f]{32}", indexnow.CLE)
    fichier = RACINE / "web" / "public" / f"{indexnow.CLE}.txt"
    assert fichier.read_text(encoding="utf-8").strip() == indexnow.CLE
    robots = (RACINE / "web" / "public" / "robots.txt").read_text()
    assert not any(f"/{indexnow.CLE}".startswith(r) for r in re.findall(r"^Disallow: (\S+)", robots, re.M))


def test_adresses_du_sitemap_et_charge(sitemap):
    urls = indexnow.adresses(sitemap.read_text())
    assert urls == ["https://lexia-axionstudio.cloud/", "https://lexia-axionstudio.cloud/tarifs",
                    "https://lexia-axionstudio.cloud/guides/methode-fiche-arret"]
    donnees = indexnow.charge(urls)
    assert donnees == {"host": "lexia-axionstudio.cloud", "key": indexnow.CLE,
                       "keyLocation": f"https://lexia-axionstudio.cloud/{indexnow.CLE}.txt", "urlList": urls}


def test_adresse_hors_du_site_refusee():
    with pytest.raises(ValueError, match="hors du site"):
        indexnow.adresses(SITEMAP.replace("https://lexia-axionstudio.cloud/tarifs", "https://autre.example/tarifs"))
    with pytest.raises(ValueError, match="vide"):
        indexnow.adresses('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>')


def test_par_defaut_rien_ne_part(sitemap, capsys, monkeypatch):
    monkeypatch.setattr(indexnow.urllib.request, "urlopen", _interdit)
    assert indexnow.main(["--sitemap", str(sitemap)]) == 0
    sortie = capsys.readouterr().out
    assert "essai a blanc" in sortie and "Rien n'est parti" in sortie
    assert "https://lexia-axionstudio.cloud/tarifs" in sortie


def test_envoi_refuse_si_la_cle_n_est_pas_en_ligne(sitemap, capsys):
    appels = []

    def ouvrir(requete, timeout):
        appels.append(requete.full_url)
        if requete.full_url.endswith(".txt"):
            raise urllib.error.HTTPError(requete.full_url, 404, "Not Found", {}, None)
        raise AssertionError("pas d'envoi a IndexNow sans cle en ligne")

    assert indexnow.main(["--sitemap", str(sitemap), "--envoyer"], ouvrir=ouvrir) == 1
    assert appels == [f"https://lexia-axionstudio.cloud/{indexnow.CLE}.txt"]
    assert "fichier de cle" in capsys.readouterr().err


@pytest.mark.parametrize("statut, attendu", [(200, 0), (202, 0), (403, 1), (422, 1)])
def test_envoi_quand_la_cle_est_en_ligne(sitemap, statut, attendu):
    requetes = []

    def ouvrir(requete, timeout):
        requetes.append(requete)
        if requete.full_url.endswith(".txt"):
            return _Reponse(indexnow.CLE.encode() + b"\n")
        if statut >= 400:
            raise urllib.error.HTTPError(requete.full_url, statut, "refus", {}, None)
        return _Reponse(status=statut)

    assert indexnow.main(["--sitemap", str(sitemap), "--envoyer"], ouvrir=ouvrir) == attendu
    envoi = requetes[-1]
    assert envoi.full_url == "https://api.indexnow.org/indexnow" and envoi.get_method() == "POST"
    assert envoi.get_header("Content-type") == "application/json; charset=utf-8"
    assert json.loads(envoi.data)["urlList"][1] == "https://lexia-axionstudio.cloud/tarifs"


def test_publier_n_appelle_indexnow_que_sur_demande():
    publier = (RACINE / "deploy" / "publier.sh").read_text()
    code = re.sub(r"#.*", "", publier)
    appels = [i for i, ligne in enumerate(code.splitlines()) if "indexnow.py" in ligne]
    assert len(appels) == 1
    lignes = code.splitlines()
    assert lignes[appels[0] - 1].strip() == 'if [ "${LEXIA_INDEXNOW:-}" = 1 ]; then'
    assert "--envoyer ||" in lignes[appels[0]]   # un echec d'IndexNow n'annule pas la publication
