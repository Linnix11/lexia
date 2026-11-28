"""Sonde du serveur (deploy/sonde.py, D144) : alertes au changement d'etat, seuils, redemarrages, resume du matin."""

import fcntl
import importlib.util
import json
import os
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

RACINE = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("sonde", RACINE / "deploy" / "sonde.py")
sonde = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sonde)

PARIS = ZoneInfo("Europe/Paris")
CONF = {"NTFY_SERVEUR": "https://ntfy.sh", "NTFY_SUJET": "canal-secret", "DOMAINE": "lexia.exemple.fr"}
# 27/11/2026 a 3 h du matin, heure de Paris : avant le resume du jour
NUIT = datetime(2026, 11, 27, 3, 0, tzinfo=PARIS).timestamp()
TOUT_VA_BIEN = {"service": (True, ""), "api": (True, ""), "site": (True, "")}


def panne_api(detail="HTTP 502"):
    return {**TOUT_VA_BIEN, "api": (False, detail)}


def minutes(etat, resultats, debut, n, redemarrage=False):
    """n passages d'une minute ; rend les messages produits."""
    produits = []
    for i in range(n):
        produits += sonde.passage(CONF, etat, debut + 60 * i, resultats, 120.0, redemarrage)
    return produits


def test_coupure_de_deux_minutes_sans_alerte():
    etat = {}
    assert minutes(etat, panne_api(), NUIT, 2) == []
    assert minutes(etat, TOUT_VA_BIEN, NUIT + 120, 1) == []
    assert etat["cibles"]["api"]["echecs"] == 0


def test_panne_puis_retour_un_message_chacun():
    etat = {}
    messages = minutes(etat, panne_api(), NUIT, 10)
    assert len(messages) == 1
    assert messages[0]["priorite"] == 5 and messages[0]["courriel"]
    assert "API (local)" in messages[0]["titre"] and "HTTP 502" in messages[0]["texte"]
    retour = minutes(etat, TOUT_VA_BIEN, NUIT + 600, 1)
    assert len(retour) == 1 and "rétabli" in retour[0]["titre"]
    assert "après 10 min" in retour[0]["texte"]
    assert etat["journal"] == [[NUIT, NUIT + 600, "api"]]


def test_redemarrage_annonce_seuil_de_dix_minutes():
    etat = {}
    assert minutes(etat, panne_api(), NUIT, 9, redemarrage=True) == []
    assert len(minutes(etat, panne_api(), NUIT + 540, 1, redemarrage=True)) == 1


def test_mesure_inconnue_ne_change_rien():
    etat = {}
    minutes(etat, panne_api(), NUIT, 2)
    minutes(etat, {**TOUT_VA_BIEN, "api": (None, "")}, NUIT + 120, 5)
    assert etat["cibles"]["api"]["echecs"] == 2


def test_gemini_seuil_propre():
    etat = {}
    ouvert = {**TOUT_VA_BIEN, "gemini": (False, "indisponible")}
    assert minutes(etat, ouvert, NUIT, 9) == []
    assert len(minutes(etat, ouvert, NUIT + 540, 1)) == 1


def test_plusieurs_pannes_un_seul_message():
    etat = {}
    tout_tombe = {"service": (False, "systemd : failed"), "api": (False, "injoignable"), "site": (False, "HTTP 502")}
    messages = minutes(etat, tout_tombe, NUIT, 3)
    assert len(messages) == 1
    assert messages[0]["texte"].count("EN PANNE") == 3


def test_lire_sante():
    assert sonde.lire_sante(502, "")["api"] == (False, "HTTP 502")
    assert sonde.lire_sante(None, "connection refused")["api"] == (False, "connection refused")
    r = sonde.lire_sante(200, json.dumps({"statut": "ok", "disjoncteur": "ouvert", "corpus_a_jour": False}))
    assert r["api"] == (True, "") and r["gemini"][0] is False and r["corpus"][0] is False
    r = sonde.lire_sante(200, json.dumps({"statut": "ok", "disjoncteur": "ferme", "corpus_a_jour": True}))
    assert r["gemini"] == (True, "") and r["corpus"] == (True, "")
    # public (sans disjoncteur) : inconnu, pas une panne
    assert sonde.lire_sante(200, '{"statut":"ok"}')["gemini"] == (None, "")


def test_resume_du_matin_une_fois_par_jour():
    etat = {}
    minutes(etat, panne_api(), NUIT, 5)
    minutes(etat, TOUT_VA_BIEN, NUIT + 300, 1)
    matin = datetime(2026, 11, 27, 8, 0, tzinfo=PARIS).timestamp()
    messages = sonde.passage(CONF, etat, matin, TOUT_VA_BIEN, 90.0, False)
    assert len(messages) == 1
    resume = messages[0]
    assert resume["titre"] == "Lexia : bilan du matin" and resume["priorite"] == 2 and not resume["courriel"]
    assert "1 incident(s) en 24 h" in resume["texte"] and "API (local)" in resume["texte"]
    assert "ms en médiane" in resume["texte"]
    assert sonde.passage(CONF, etat, matin + 60, TOUT_VA_BIEN, 90.0, False) == []


def test_pas_de_bilan_le_soir_de_l_installation():
    etat = {}
    soir = datetime(2026, 11, 27, 21, 56, tzinfo=PARIS).timestamp()
    assert sonde.passage(CONF, etat, soir, TOUT_VA_BIEN, 30.0, False) == []
    lendemain = datetime(2026, 11, 28, 8, 0, tzinfo=PARIS).timestamp()
    assert sonde.passage(CONF, etat, lendemain, TOUT_VA_BIEN, 30.0, False)[0]["titre"] == "Lexia : bilan du matin"


def test_resume_signale_une_panne_en_cours():
    etat = {}
    minutes(etat, panne_api(), NUIT, 5)
    matin = datetime(2026, 11, 27, 8, 5, tzinfo=PARIS).timestamp()
    resume = sonde.passage(CONF, etat, matin, panne_api(), None, False)[0]
    assert resume["titre"] == "Lexia : panne en cours" and resume["courriel"] and resume["priorite"] == 4
    assert "EN PANNE : API (local)" in resume["texte"]


def test_envoi_rate_retente_puis_abandonne():
    etat = {}
    minutes(etat, panne_api(), NUIT, 3)
    appels = []
    sonde.distribuer(etat, CONF, NUIT + 180, ntfy=lambda c, m: appels.append("n") or False,
                     courriel=lambda m: appels.append("c") or True)
    assert appels == ["n", "c"] and len(etat["en_attente"]) == 1
    # le courriel parti n'est pas renvoye
    sonde.distribuer(etat, CONF, NUIT + 240, ntfy=lambda c, m: appels.append("n") or True,
                     courriel=lambda m: appels.append("c") or True)
    assert appels == ["n", "c", "n"] and etat["en_attente"] == []
    minutes(etat, TOUT_VA_BIEN, NUIT + 300, 1)
    sonde.distribuer(etat, CONF, NUIT + 300 + 25 * 3600, ntfy=lambda c, m: False, courriel=lambda m: False)
    assert etat["en_attente"] == []


def test_corps_ntfy(monkeypatch):
    envoye = {}

    class Reponse:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def faux_urlopen(requete, timeout):
        envoye["url"], envoye["corps"] = requete.full_url, json.loads(requete.data)
        return Reponse()

    monkeypatch.setattr(sonde.urllib.request, "urlopen", faux_urlopen)
    message = sonde.message_evenements([{"nom": "site", "panne": True, "detail": "HTTP 502", "duree": 180}],
                                       "lexia.exemple.fr")
    assert sonde.envoyer_ntfy(CONF, message)
    assert envoye["url"] == "https://ntfy.sh"
    assert envoye["corps"]["topic"] == "canal-secret" and envoye["corps"]["priority"] == 5
    assert envoye["corps"]["click"] == "https://lexia.exemple.fr/"
    # sans canal : rien n'est envoye, rien a retenter
    envoye.clear()
    assert sonde.envoyer_ntfy({"NTFY_SERVEUR": "https://ntfy.sh"}, message) and envoye == {}


def test_redemarrage_en_cours(tmp_path, monkeypatch):
    publication, maj = tmp_path / "lexia-publication", tmp_path / "maj.lock"
    monkeypatch.setattr(sonde, "VERROU_PUBLICATION", publication)
    monkeypatch.setattr(sonde, "VERROU_MAJ", maj)
    assert not sonde.redemarrage_en_cours(time.time())
    publication.mkdir()
    assert sonde.redemarrage_en_cours(time.time())
    # verrou oublie depuis une heure : plus de seuil allonge
    os.utime(publication, (time.time() - 3600, time.time() - 3600))
    assert not sonde.redemarrage_en_cours(time.time())
    # mise a jour nocturne : flock exclusif tenu par le script
    with open(maj, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        assert sonde.redemarrage_en_cours(time.time())
    assert not sonde.redemarrage_en_cours(time.time())


def test_lire_conf(tmp_path):
    fichier = tmp_path / "sonde.conf"
    fichier.write_text("# canal\nNTFY_SUJET=abc\nDOMAINE = lexia.exemple.fr\n")
    conf = sonde.lire_conf(fichier)
    assert conf == {"NTFY_SERVEUR": "https://ntfy.sh", "NTFY_SUJET": "abc", "DOMAINE": "lexia.exemple.fr"}
    assert sonde.lire_conf(tmp_path / "absent") == {"NTFY_SERVEUR": "https://ntfy.sh"}


def test_cron_en_tant_que_lexia():
    lignes = [l for l in (RACINE / "deploy" / "lexia.cron").read_text().splitlines() if "sonde.py" in l]
    assert len(lignes) == 1
    champs = lignes[0].split()
    assert champs[:5] == ["*"] * 5 and champs[5] == "lexia"
    assert "/usr/bin/python3" in lignes[0]


def test_instance_en_service(tmp_path):
    """D145 : la sonde suit l'instance a qui nginx envoie les requetes (8000 ou 8001)."""
    amont = tmp_path / "lexia-amont.conf"
    assert sonde.instance_en_service(amont) == ("lexia", "http://127.0.0.1:8000/api/sante")   # avant D145
    amont.write_text("# Ecrit par lexia-basculer\nupstream lexia_amont {\n    server 127.0.0.1:8001;\n}\n")
    assert sonde.instance_en_service(amont) == ("lexia@8001", "http://127.0.0.1:8001/api/sante")
