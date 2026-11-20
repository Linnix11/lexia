"""Arrets recents de la Cour de cassation par l'API Judilibre (PISTE), en complement de l'archive DILA CASS.

Pourquoi (docs/jurisprudence-recente.md, D113) : l'archive DILA CASS du 2026-11-08 s'arrete aux arrets du
17 septembre 2026, comme Legifrance ; Judilibre publie les arrets le lendemain de leur prononce.

Desactive tant que la cle manque : JUDILIBRE_KEY_ID (identifiant « KeyId » de l'application PISTE de l'editeur,
dans .env). Sans cle, rien n'est appele et le cache reste vide : l'index est celui de la DILA seule.

Perimetre identique a l'archive CASS (D38) : arrets de la Cour de cassation publies au Bulletin ou au Rapport.
Chaque nuit (ingest/mise_a_jour.py), synchroniser() :
  - premiere fois : arrets rendus depuis FENETRE_JOURS avant l'archive DILA (date de decision) ;
  - ensuite : arrets crees ou modifies depuis la synchronisation precedente (date de mise a jour), et retrait
    des arrets supprimes (/transactionalhistory, propriete to_be_deleted) : les CGU de la Cour demandent une
    base tenue a jour (72 h recommandees).
Une decision par fichier JSON dans data/raw/judilibre/decisions/. cass.collect() lit ce cache apres l'archive
DILA et n'en garde que les arrets absents de l'archive (meme ECLI, ou meme date et meme pourvoi).

Mentions exigees par les CGU (article V) : juridiction, formation et date de chaque decision (titre et en-tete),
source « open data de la Cour de cassation » et date de mise a jour des donnees (champ version).
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterator
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

from ingest.jurisprudence import date_fr, decouper, decouper_sommaire
from ingest.models import Passage

URL_API = "https://api.piste.gouv.fr/cassation/judilibre/v1.0"   # bac a sable : sandbox-api.piste.gouv.fr
URL_DECISION = "https://www.courdecassation.fr/decision/{id}"
VARIABLE_CLE = "JUDILIBRE_KEY_ID"
FENETRE_JOURS = 180     # premiere synchronisation : l'archive DILA a souvent plusieurs semaines de retard
RECOUVREMENT_JOURS = 3  # synchronisations suivantes : on repart un peu avant la precedente
TAILLE_LOT = 1000       # maximum de l'API pour un client authentifie
FILTRES = {"jurisdiction": "cc", "type": "arret", "publication": ["b", "r"]}

# Cles de chambre de Judilibre (taxonomie « chamber ») -> (source Lexia, formation au format de l'archive CASS)
CHAMBRES = {
    "civ1": ("judilibre", "Première chambre civile"),
    "civ2": ("judilibre", "Deuxième chambre civile"),
    "civ3": ("judilibre", "Troisième chambre civile"),
    "pl": ("judilibre", "Assemblée plénière"),
    "mi": ("judilibre", "Chambre mixte"),
    "creun": ("judilibre", "Chambres réunies"),
    "cr": ("cass_criminelle", "Chambre criminelle"),
    "soc": ("cass_sociale", "Chambre sociale"),
    "comm": ("cass_commerciale", "Chambre commerciale"),
}
ZONES_UTILES = ("expose", "moyens", "motivations", "dispositif")   # ni introduction (composition), ni annexes


def cle() -> str | None:
    return os.environ.get(VARIABLE_CLE) or None


def client(cle_api: str) -> httpx.Client:
    return httpx.Client(base_url=os.environ.get("JUDILIBRE_URL", URL_API), timeout=120,
                        headers={"KeyId": cle_api, "accept": "application/json"})


def _ecrire(chemin: Path, contenu: str) -> None:
    tmp = chemin.with_name(chemin.name + ".tmp")
    tmp.write_text(contenu, encoding="utf-8")
    tmp.replace(chemin)


def _exporter(http: httpx.Client, params: dict) -> Iterator[dict]:
    lot = 0
    while True:
        r = http.get("/export", params={**FILTRES, **params, "batch_size": TAILLE_LOT, "batch": lot})
        r.raise_for_status()
        page = r.json()
        yield from page.get("results") or []
        if not page.get("next_batch"):
            return
        lot += 1


def _supprimees(http: httpx.Client, depuis: str) -> set[str]:
    ids: set[str] = set()
    params: dict | None = {"date": depuis}
    while params is not None:
        r = http.get("/transactionalhistory", params=params)
        r.raise_for_status()
        page = r.json()
        ids |= {t["id"] for t in page.get("transactions") or [] if t.get("action") == "deleted"}
        suite = page.get("next_page")
        params = dict(httpx.QueryParams(suite.split("?", 1)[-1])) if suite else None
    return ids


def synchroniser(http: httpx.Client, raw_dir: Path, debut: str, maintenant: datetime | None = None) -> dict:
    """Met le cache a jour. debut : date (AAAA-MM-JJ) a partir de laquelle garder les arrets ; les plus anciens
    sont dans l'archive DILA et sont retires du cache. Renvoie le nombre d'arrets ecrits et retires."""
    maintenant = maintenant or datetime.now(timezone.utc)
    dossier = raw_dir / "decisions"
    dossier.mkdir(parents=True, exist_ok=True)
    etat_f = raw_dir / "etat.json"
    etat = json.loads(etat_f.read_text()) if etat_f.exists() else {}
    if etat.get("synchro"):
        depuis = (date.fromisoformat(etat["synchro"][:10]) - timedelta(days=RECOUVREMENT_JOURS)).isoformat()
        params = {"date_type": "update", "date_start": depuis}
        retirees = _supprimees(http, depuis)
    else:
        params = {"date_type": "creation", "date_start": debut}
        retirees = set()
    ecrites = 0
    for d in _exporter(http, params):
        if d.get("to_be_deleted"):
            retirees.add(d["id"])
        elif d.get("chamber") in CHAMBRES and str(d.get("decision_date", "")) >= debut:
            _ecrire(dossier / f"{d['id']}.json", json.dumps(d, ensure_ascii=False))
            ecrites += 1
    for i in retirees:
        (dossier / f"{i}.json").unlink(missing_ok=True)
    for f in dossier.glob("*.json"):   # arrets entres depuis dans l'archive DILA
        if json.loads(f.read_text(encoding="utf-8")).get("decision_date", "") < debut:
            f.unlink()
    _ecrire(etat_f, json.dumps({"synchro": maintenant.isoformat(timespec="seconds"), "debut": debut}))
    return {"ecrites": ecrites, "retirees": len(retirees)}


def date_synchro(raw_dir: Path) -> str | None:
    try:
        return json.loads((raw_dir / "etat.json").read_text())["synchro"][:10]
    except (OSError, ValueError, KeyError):
        return None


def decisions(raw_dir: Path) -> list[dict]:
    """Arrets du cache, dans l'ordre des identifiants (ordre stable des passages)."""
    return [json.loads(f.read_text(encoding="utf-8")) for f in sorted((raw_dir / "decisions").glob("*.json"))]


def pourvoi(numero: str) -> str:
    """« 17-18.194 » -> « 17-18194 », forme des numeros de l'archive CASS (table pourvois de l'index)."""
    return re.sub(r"[.\s]", "", numero)


def _lignes(texte: str) -> list[str]:
    return [l for l in (re.sub(r"[ \t  ]+", " ", x).strip() for x in texte.splitlines()) if l]


def _corps(d: dict) -> list[str]:
    """Expose du litige, moyens, motifs et dispositif, d'apres le zonage de Judilibre (sans l'introduction, qui
    donne la composition de la formation, ni les moyens annexes). Sans zonage : texte entier, filtre comme
    l'archive CASS."""
    from ingest.sources import cass

    texte = d.get("text") or ""
    zones = d.get("zones") or {}
    morceaux = sorted((z["start"], z["end"]) for nom in ZONES_UTILES for z in zones.get(nom) or [])
    if morceaux:
        return _lignes("\n".join(texte[a:b] for a, b in morceaux))
    return cass.lignes_utiles(_lignes(texte))


def parse_decision(d: dict, *, date_recuperation: str, version: str) -> list[Passage]:
    from ingest.sources import cass

    if d.get("chamber") not in CHAMBRES:
        return []
    source_id, formation = CHAMBRES[d["chamber"]]
    numero = d.get("number") or ""
    titre = (f"Cour de cassation, {formation}, {date_fr(d['decision_date'])}, {numero}, "
             f"{'Publié au bulletin' if 'b' in (d.get('publication') or []) else 'Publié au rapport'}")
    meta = {
        "juridiction": "Cour de cassation",
        "formation": formation,
        "date": d["decision_date"],
        "numeros_pourvoi": [pourvoi(n) for n in (d.get("numbers") or [numero]) if n],
        "solution": (d.get("solution_alt") or d.get("solution") or "").capitalize(),
        "ecli": d.get("ecli") or "",
        "id_source": f"judilibre:{d['id']}",
        "origine": "Judilibre",
    }
    common = dict(source_id=source_id, titre=titre, url=URL_DECISION.format(id=d["id"]), version=version,
                  date_recuperation=date_recuperation, meta=meta, entete=titre)
    passages = []
    sommaire = [" - ".join(d["themes"])] if d.get("themes") else []
    if d.get("summary"):
        sommaire.append(d["summary"].strip())
    for k, bloc in enumerate(decouper_sommaire(sommaire)):
        if len("".join(bloc).strip()) >= cass.SOMMAIRE_MIN:
            passages.append(Passage(id=f"{source_id}:{d['id']}:{'sommaire' if k == 0 else f'sommaire-{k + 1}'}",
                                    type="sommaire", numero=None, alineas=bloc, **common))
    for i, m in enumerate(decouper(_corps(d), cass.est_dispositif, ignorer=cass.est_formule), start=1):
        passages.append(Passage(id=f"{source_id}:{d['id']}:{i}", type=m.type, numero=m.plage or None,
                                alineas=m.alineas, **common))
    return passages


def complements(raw_dir: Path, source_id: str, deja: set[str], *, date_recuperation: str) -> Iterator[Passage]:
    """Passages des arrets du cache rattaches a source_id et absents de l'archive DILA. deja : cles des arrets
    de l'archive (cles())."""
    synchro = date_synchro(raw_dir)
    if synchro is None:
        return
    version = f"Open data de la Cour de cassation (Judilibre), mise à jour du {synchro}"
    for d in decisions(raw_dir):
        if CHAMBRES.get(d.get("chamber"), ("",))[0] != source_id or cles(d) & deja:
            continue
        yield from parse_decision(d, date_recuperation=date_recuperation, version=version)


def cles(d: dict) -> set[str]:
    """ECLI et couples date-pourvoi d'un arret de Judilibre, pour le reconnaitre dans l'archive DILA."""
    out = {f"{d.get('decision_date')}|{pourvoi(n)}" for n in (d.get("numbers") or [d.get("number") or ""]) if n}
    return out | ({d["ecli"]} if d.get("ecli") else set())


def cles_dila(meta: dict) -> set[str]:
    out = {f"{meta.get('date')}|{n}" for n in meta.get("numeros_pourvoi") or []}
    return out | ({meta["ecli"]} if meta.get("ecli") else set())
