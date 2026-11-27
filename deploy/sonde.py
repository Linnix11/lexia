#!/usr/bin/env python3
"""Sonde du serveur : verifie Lexia chaque minute et previent l'editeur quand un element tombe ou revient (D144).

Lancee par /etc/cron.d/lexia en tant que lexia (jamais root), avec le Python du systeme et la bibliotheque standard
seulement : elle doit tourner meme quand le .venv ou une dependance est casse. Avant elle, une panne de nuit
n'etait vue que par la surveillance GitHub (toutes les 2 h) ou par la veille du Mac (seulement s'il est allume).

Verifie : service lexia, lecteur de fichiers, /api/sante en local, site public (nginx + Cloudflare), Gemini
(disjoncteur ouvert = questions sur le modele de secours), disque, memoire, fraicheur du corpus, certificat du
serveur. Alertes :
  - une notification sur le telephone (ntfy, https://docs.ntfy.sh/publish/) et un e-mail aux ADMIN_EMAILS
    (python -m ingest.fraicheur) quand un element tombe, puis quand il revient ; jamais une par minute ;
  - pendant une publication (verrou /run/lexia-publication) ou la mise a jour nocturne (verrou flock), le service
    redemarre : seuil de 10 minutes au lieu de 3, pour ne pas alerter sur les 2 minutes de chargement de l'index ;
  - un resume chaque matin a 8 h (heure de Paris), sans son : s'il n'arrive pas, la sonde ou le serveur est mort.

Reglages : /etc/lexia-sonde.conf (root:lexia, 640), lignes CLE=valeur : NTFY_SUJET (nom du canal ntfy, a garder
secret : sans compte, connaitre le nom suffit pour lire les messages), DOMAINE, NTFY_SERVEUR (https://ntfy.sh par
defaut). Etat : /opt/lexia/logs/sonde.json. Journal (changements seulement) : /opt/lexia/logs/sonde.log.

    python3 deploy/sonde.py            # un passage (cron)
    python3 deploy/sonde.py --essai    # envoie une notification d'essai et l'e-mail
"""

from __future__ import annotations

import fcntl
import json
import os
import shutil
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

APP = Path(os.environ.get("LEXIA_APP", "/opt/lexia"))
CONF = Path(os.environ.get("LEXIA_SONDE_CONF", "/etc/lexia-sonde.conf"))
ETAT = APP / "logs" / "sonde.json"
VERROU_PUBLICATION = Path(os.environ.get("LEXIA_VERROU", "/run/lexia-publication"))
VERROU_MAJ = Path(os.environ.get("LEXIA_VERROU_MAJ", "/run/lexia-mise-a-jour.lock"))
SANTE = "http://127.0.0.1:8000/api/sante"
PARIS = ZoneInfo("Europe/Paris")

# Minutes d'echec consecutives avant de declarer une panne. Les redemarrages durent environ 2 minutes (veille du
# Mac : 15 coupures de 121 a 141 s du 18 au 27 novembre, toutes a une publication ou a la mise a jour de la nuit).
SEUIL = 3
SEUIL_REDEMARRAGE = 10          # publication ou mise a jour en cours
SEUILS = {"gemini": 10, "disque": 5, "memoire": 5, "corpus": 1, "certificat": 1}
VERROU_PERIME = 45 * 60         # un verrou de publication plus vieux ne retarde plus les alertes
DISQUE_MIN = 15.0               # % libre sur /
MEMOIRE_MIN = 10.0              # % disponible
CERTIFICAT_JOURS = 14
HEURE_RESUME = 8
GARDE_ENVOI = 24 * 3600         # un message non parti est abandonne apres 24 h
GARDE_JOURNAL = 7 * 24 * 3600

NOMS = {"service": "Service lexia", "lecteur": "Lecteur de fichiers", "api": "API (local)",
        "site": "Site public", "gemini": "Gemini", "disque": "Disque", "memoire": "Mémoire",
        "corpus": "Mise à jour du corpus", "certificat": "Certificat du serveur"}


def maintenant() -> float:
    return time.time()


def lire_conf(chemin: Path = CONF) -> dict:
    conf = {"NTFY_SERVEUR": "https://ntfy.sh"}
    try:
        for ligne in chemin.read_text().splitlines():
            cle, egal, valeur = ligne.strip().partition("=")
            if egal and cle and not cle.startswith("#"):
                conf[cle.strip()] = valeur.strip()
    except OSError:
        pass
    return conf


# ---------------------------------------------------------------- mesures
# Chaque mesure rend (ok, detail) : ok vaut True, False, ou None quand on ne peut pas savoir (alors l'etat ne
# change pas, par exemple le disjoncteur quand l'API ne repond pas : la panne de l'API suffit).

def _http(url: str, delai: float) -> tuple[int | None, str, float]:
    debut = time.monotonic()
    requete = urllib.request.Request(url, headers={"User-Agent": "lexia-sonde"})
    try:
        with urllib.request.urlopen(requete, timeout=delai) as r:
            return r.status, r.read(200_000).decode("utf-8", "replace"), (time.monotonic() - debut) * 1000
    except urllib.error.HTTPError as e:
        return e.code, "", (time.monotonic() - debut) * 1000
    except (urllib.error.URLError, OSError, ValueError) as e:
        return None, str(getattr(e, "reason", e))[:120], (time.monotonic() - debut) * 1000


def lire_sante(code: int | None, texte: str) -> dict:
    """Resultats tires de /api/sante en local : API, Gemini (disjoncteur) et fraicheur du corpus."""
    if code != 200:
        return {"api": (False, f"HTTP {code}" if code else (texte or "injoignable")), "gemini": (None, ""),
                "corpus": (None, "")}
    try:
        sante = json.loads(texte)
    except ValueError:
        return {"api": (False, "réponse illisible"), "gemini": (None, ""), "corpus": (None, "")}
    if sante.get("statut") != "ok":
        return {"api": (False, f"statut {sante.get('statut')!r}"), "gemini": (None, ""), "corpus": (None, "")}
    disjoncteur = sante.get("disjoncteur")
    frais = sante.get("corpus_a_jour")
    return {"api": (True, ""),
            "gemini": (None, "") if disjoncteur is None else
            (disjoncteur != "ouvert", "indisponible, questions sur le modèle de secours" if disjoncteur == "ouvert" else ""),
            "corpus": (None, "") if frais is None else
            (bool(frais), "" if frais else "pas de mise à jour réussie depuis plus de 36 h (/var/log/lexia-mise-a-jour.log)")}


def _systemd(unite: str) -> tuple[bool | None, str]:
    try:
        r = subprocess.run(["systemctl", "is-active", unite], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None, ""
    etat = r.stdout.strip()
    return etat == "active", "" if etat == "active" else f"systemd : {etat or 'inconnu'}"


def _memoire_disponible() -> float | None:
    try:
        valeurs = dict(l.split(":", 1) for l in Path("/proc/meminfo").read_text().splitlines() if ":" in l)
        return 100 * int(valeurs["MemAvailable"].split()[0]) / int(valeurs["MemTotal"].split()[0])
    except (OSError, KeyError, ValueError, ZeroDivisionError):
        return None


def _certificat(domaine: str) -> tuple[bool | None, str]:
    """Certificat presente par nginx (celui que Cloudflare verifie), lu en local avec le nom du site."""
    contexte = ssl.create_default_context()
    try:
        with socket.create_connection(("127.0.0.1", 443), timeout=10) as brut:
            with contexte.wrap_socket(brut, server_hostname=domaine) as tls:
                fin = ssl.cert_time_to_seconds(tls.getpeercert()["notAfter"])
    except ssl.SSLCertVerificationError as e:
        return False, f"certificat refusé : {e.verify_message}"
    except (OSError, KeyError, ValueError):
        return None, ""          # nginx arrete : le site public le signale deja
    jours = (fin - maintenant()) / 86400
    return jours >= CERTIFICAT_JOURS, "" if jours >= CERTIFICAT_JOURS else f"expire dans {jours:.0f} jours"


def mesurer(conf: dict) -> tuple[dict, float | None]:
    """Resultats de tous les controles, et duree de /api/sante en local (ms) quand elle a repondu."""
    resultats = {"service": _systemd("lexia"), "lecteur": _systemd("lexia-lecteur.socket")}
    code, texte, duree = _http(SANTE, 10)
    resultats |= lire_sante(code, texte)
    domaine = conf.get("DOMAINE", "")
    if domaine:
        code_public, detail, _ = _http(f"https://{domaine}/", 20)
        resultats["site"] = (code_public == 200, "" if code_public == 200 else
                             f"HTTP {code_public}" if code_public else detail or "injoignable")
        resultats["certificat"] = _certificat(domaine)
    disque = shutil.disk_usage("/")
    libre = 100 * disque.free / disque.total
    resultats["disque"] = (libre >= DISQUE_MIN, "" if libre >= DISQUE_MIN else f"{libre:.0f} % libre")
    memoire = _memoire_disponible()
    resultats["memoire"] = (None, "") if memoire is None else (
        memoire >= MEMOIRE_MIN, "" if memoire >= MEMOIRE_MIN else f"{memoire:.0f} % disponible")
    return resultats, (duree if code == 200 else None)


def redemarrage_en_cours(instant: float) -> bool:
    """Publication (verrou de publier.sh, s'il n'est pas perime) ou mise a jour nocturne (flock tenu)."""
    try:
        if instant - VERROU_PUBLICATION.stat().st_mtime < VERROU_PERIME:
            return True
    except OSError:
        pass
    try:
        with open(VERROU_MAJ) as f:
            try:
                fcntl.flock(f, fcntl.LOCK_SH | fcntl.LOCK_NB)
            except BlockingIOError:
                return True
    except OSError:
        pass
    return False


# ---------------------------------------------------------------- etat et evenements

def evaluer(etat: dict, resultats: dict, instant: float, redemarrage: bool) -> list[dict]:
    """Met a jour l'etat et rend les changements : {"nom", "panne": bool, "detail", "duree"}."""
    cibles = etat.setdefault("cibles", {})
    evenements = []
    for nom, (ok, detail) in resultats.items():
        c = cibles.setdefault(nom, {"echecs": 0, "panne_depuis": None, "premier_echec": None, "detail": ""})
        if ok is None:
            continue
        if ok:
            if c["panne_depuis"] is not None:
                evenements.append({"nom": nom, "panne": False, "detail": c["detail"],
                                   "duree": instant - c["premier_echec"]})
                etat.setdefault("journal", []).append([c["premier_echec"], instant, nom])
            c.update(echecs=0, panne_depuis=None, premier_echec=None, detail="")
            continue
        c["echecs"] += 1
        c["detail"] = detail
        c["premier_echec"] = c["premier_echec"] or instant
        seuil = SEUILS.get(nom, SEUIL_REDEMARRAGE if redemarrage else SEUIL)
        if c["panne_depuis"] is None and c["echecs"] >= seuil:
            c["panne_depuis"] = instant
            evenements.append({"nom": nom, "panne": True, "detail": detail, "duree": instant - c["premier_echec"]})
    etat["journal"] = [j for j in etat.get("journal", []) if j[1] > instant - GARDE_JOURNAL]
    return evenements


def _minutes(secondes: float) -> str:
    m = max(1, round(secondes / 60))
    return f"{m} min" if m < 120 else f"{m // 60} h {m % 60:02d}"


def message_evenements(evenements: list[dict], domaine: str) -> dict:
    pannes = [e for e in evenements if e["panne"]]
    retours = [e for e in evenements if not e["panne"]]
    lignes = [f"EN PANNE : {NOMS.get(e['nom'], e['nom'])} ({e['detail']}), depuis {_minutes(e['duree'])}"
              for e in pannes]
    lignes += [f"Rétabli : {NOMS.get(e['nom'], e['nom'])}, après {_minutes(e['duree'])}" for e in retours]
    if pannes:
        titre = "Lexia : " + ", ".join(NOMS.get(e["nom"], e["nom"]) for e in pannes) + " en panne"
    else:
        titre = "Lexia : tout est rétabli" if len(retours) > 1 else f"Lexia : {NOMS.get(retours[0]['nom'], retours[0]['nom'])} rétabli"
    return {"titre": titre, "texte": "\n".join(lignes), "priorite": 5 if pannes else 3,
            "etiquettes": ["rotating_light"] if pannes else ["white_check_mark"], "courriel": True,
            "lien": f"https://{domaine}/" if domaine else None}


def resume_du_jour(etat: dict, instant: float, domaine: str) -> dict | None:
    """Une fois par jour, a partir de 8 h (Paris) : bilan des 24 dernieres heures."""
    local = datetime.fromtimestamp(instant, PARIS)
    jour = local.date().isoformat()
    if local.hour < HEURE_RESUME or etat.get("dernier_resume") == jour:
        return None
    etat["dernier_resume"] = jour
    en_cours = [f"{NOMS.get(n, n)} ({c['detail']}), depuis {_minutes(instant - c['premier_echec'])}"
                for n, c in etat.get("cibles", {}).items() if c.get("panne_depuis")]
    incidents = [j for j in etat.get("journal", []) if j[1] > instant - 86400]
    durees = sorted(d for t, d in etat.get("durees_api", []) if t > instant - 86400)
    lignes = (["EN PANNE : " + " ; ".join(en_cours)] if en_cours else ["Tout fonctionne."])
    if incidents:
        lignes.append(f"{len(incidents)} incident(s) en 24 h, {_minutes(sum(f - d for d, f, _ in incidents))} au total : "
                      + ", ".join(sorted({NOMS.get(n, n) for _, _, n in incidents})))
    else:
        lignes.append("Aucun incident en 24 h.")
    if durees:
        lignes.append(f"/api/sante en local : {durees[len(durees) // 2]:.0f} ms en médiane, {durees[-1]:.0f} ms au pire.")
    return {"titre": "Lexia : " + ("panne en cours" if en_cours else "bilan du matin"), "texte": "\n".join(lignes),
            "priorite": 4 if en_cours else 2, "etiquettes": ["warning"] if en_cours else ["sunrise"],
            "courriel": bool(en_cours), "lien": f"https://{domaine}/" if domaine else None}


# ---------------------------------------------------------------- envoi

def envoyer_ntfy(conf: dict, message: dict) -> bool:
    sujet = conf.get("NTFY_SUJET", "")
    if not sujet:
        return True              # pas de canal configure : rien a retenter
    corps = {"topic": sujet, "title": message["titre"], "message": message["texte"],
             "priority": message["priorite"], "tags": message["etiquettes"]}
    if message.get("lien"):
        corps["click"] = message["lien"]
    requete = urllib.request.Request(conf["NTFY_SERVEUR"].rstrip("/"), data=json.dumps(corps).encode(),
                                     headers={"Content-Type": "application/json", "User-Agent": "lexia-sonde"})
    try:
        with urllib.request.urlopen(requete, timeout=15) as r:
            return 200 <= r.status < 300
    except (urllib.error.URLError, OSError, ValueError):
        return False


def envoyer_courriel(message: dict) -> bool:
    """Par le module d'alerte deja utilise par la sauvegarde et la mise a jour (Resend, ADMIN_EMAILS)."""
    try:
        r = subprocess.run([str(APP / ".venv" / "bin" / "python"), "-m", "ingest.fraicheur",
                            "--sujet", message["titre"], "--alerte", message["texte"]],
                           cwd=APP, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0


def distribuer(etat: dict, conf: dict, instant: float, ntfy=envoyer_ntfy, courriel=envoyer_courriel) -> None:
    """Envoie les messages en attente ; un envoi rate est retente au passage suivant, pendant 24 h au plus."""
    restants = []
    for m in etat.get("en_attente", []):
        if instant - m["cree"] > GARDE_ENVOI:
            print(f"{_horodatage(instant)} abandon apres 24 h : {m['titre']}")
            continue
        if not m.get("ntfy_parti"):
            m["ntfy_parti"] = ntfy(conf, m)
        if m.get("courriel") and not m.get("courriel_parti"):
            m["courriel_parti"] = courriel(m)
        if not m["ntfy_parti"] or (m.get("courriel") and not m["courriel_parti"]):
            restants.append(m)
    etat["en_attente"] = restants


# ---------------------------------------------------------------- passage

def _horodatage(instant: float) -> str:
    return datetime.fromtimestamp(instant, PARIS).isoformat(timespec="seconds")


def charger_etat() -> dict:
    try:
        return json.loads(ETAT.read_text())
    except (OSError, ValueError):
        return {}


def enregistrer_etat(etat: dict) -> None:
    provisoire = ETAT.with_suffix(".tmp")
    provisoire.write_text(json.dumps(etat))
    os.replace(provisoire, ETAT)


def passage(conf: dict, etat: dict, instant: float, resultats: dict, duree_api: float | None,
            redemarrage: bool) -> list[dict]:
    """Un passage sans entree ni sortie (teste) : rend les messages ajoutes a la file d'envoi."""
    domaine = conf.get("DOMAINE", "")
    if duree_api is not None:
        etat["durees_api"] = [x for x in etat.get("durees_api", []) if x[0] > instant - 86400] + [[instant, round(duree_api)]]
    nouveaux = []
    if evenements := evaluer(etat, resultats, instant, redemarrage):
        nouveaux.append(message_evenements(evenements, domaine))
    if resume := resume_du_jour(etat, instant, domaine):
        nouveaux.append(resume)
    for m in nouveaux:
        m["cree"] = instant
        print(f"{_horodatage(instant)} {m['titre']} | {m['texte']}".replace("\n", " | "))
    etat.setdefault("en_attente", []).extend(nouveaux)
    return nouveaux


def main(argv: list[str]) -> int:
    conf = lire_conf()
    if "--essai" in argv:
        essai = {"titre": "Lexia : essai de la sonde", "texte": "Si tu lis ceci, les alertes du serveur arrivent.",
                 "priorite": 3, "etiquettes": ["test_tube"], "courriel": True, "lien": None}
        ok_ntfy, ok_courriel = envoyer_ntfy(conf, essai), envoyer_courriel(essai)
        print(f"ntfy : {'envoye' if ok_ntfy and conf.get('NTFY_SUJET') else 'pas de NTFY_SUJET' if ok_ntfy else 'ECHEC'} ; "
              f"e-mail : {'envoye' if ok_courriel else 'ECHEC'}")
        return 0 if ok_ntfy and ok_courriel else 1
    # Un seul passage a la fois : un passage lent (delais reseau) ne se superpose pas au suivant.
    with open(APP / "logs" / "sonde.lock", "w") as verrou:
        try:
            fcntl.flock(verrou, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        instant = maintenant()
        etat = charger_etat()
        resultats, duree = mesurer(conf)
        passage(conf, etat, instant, resultats, duree, redemarrage_en_cours(instant))
        distribuer(etat, conf, instant)
        enregistrer_etat(etat)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
