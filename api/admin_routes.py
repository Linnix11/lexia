"""Tableau de bord administrateur : statistiques, clients, activite, etat du serveur.

Reserve aux comptes administrateurs (colonne admin ou adresse listee dans ADMIN_EMAILS).
Aucune route n'expose le texte des questions : les journaux n'en contiennent pas.
"""

from __future__ import annotations

import os
import platform
import resource
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone
from statistics import mean

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from api.auth import verifier_origine
from api.comptes import Comptes, ErreurCompte, Utilisateur
from api.config import ROOT, Settings
from api.journal import Journal
from api.plans import FORMULES

DEMARRAGE = time.time()


class ChangementFormule(BaseModel):
    formule: str
    jours: int | None = Field(default=None, ge=1, le=3660)


class ChangementAdmin(BaseModel):
    admin: bool


def _depuis(heures: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=heures)).isoformat(timespec="seconds")


def _p95(valeurs: list[int]) -> int | None:
    if not valeurs:
        return None
    v = sorted(valeurs)
    return v[min(len(v) - 1, int(round(0.95 * (len(v) - 1))))]


def resume_activite(journal: Journal) -> dict:
    requetes = journal.lire("requetes")
    erreurs = journal.lire("erreurs")
    retours = journal.lire("feedback")
    h24, j7 = _depuis(24), _depuis(24 * 7)
    chat24 = [r for r in requetes if r.get("route") == "chat" and r.get("ts", "") >= h24]
    quiz24 = [r for r in requetes if r.get("route") == "quiz" and r.get("ts", "") >= h24]
    durees = [r["duree_ms"] for r in chat24 if isinstance(r.get("duree_ms"), int)]
    statuts: dict[str, int] = {}
    for r in chat24:
        statuts[r.get("statut", "?")] = statuts.get(r.get("statut", "?"), 0) + 1
    err24 = [e for e in erreurs if e.get("ts", "") >= h24]
    motifs: dict[str, int] = {}
    for f in retours:
        if f.get("utile") is False and f.get("motif"):
            motifs[f["motif"]] = motifs.get(f["motif"], 0) + 1
    return {
        "dernieres_24h": {
            "questions": len(chat24),
            "quiz": len(quiz24),
            "statuts": statuts,
            "duree_moyenne_ms": round(mean(durees)) if durees else None,
            "duree_p95_ms": _p95(durees),
            "erreurs_modele": len(err24),
            "recherche_hybride": sum(1 for r in chat24 if r.get("recherche") == "hybride"),
        },
        "questions_7j": sum(1 for r in requetes if r.get("route") == "chat" and r.get("ts", "") >= j7),
        "derniere_erreur": erreurs[-1] if erreurs else None,
        "retours": {
            "utiles": sum(1 for f in retours if f.get("utile") is True),
            "pas_utiles": sum(1 for f in retours if f.get("utile") is False),
            "motifs": motifs,
        },
    }


def _memoire_systeme() -> dict | None:
    try:
        infos = {}
        with open("/proc/meminfo", encoding="utf-8") as f:
            for line in f:
                cle, _, valeur = line.partition(":")
                infos[cle] = int(valeur.split()[0]) * 1024
        return {"total": infos["MemTotal"], "disponible": infos["MemAvailable"]}
    except (OSError, KeyError, ValueError):
        return None  # hors Linux (developpement sur Mac)


def _memoire_processus() -> int | None:
    try:
        with open("/proc/self/status", encoding="utf-8") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) * 1024
    except OSError:
        pass
    pic = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return pic if sys.platform == "darwin" else pic * 1024  # octets sur macOS, Ko sur Linux


def _uptime_systeme() -> float | None:
    try:
        with open("/proc/uptime", encoding="utf-8") as f:
            return float(f.read().split()[0])
    except (OSError, ValueError):
        return None


def etat_serveur(settings: Settings, retriever, journal: Journal, extras: dict) -> dict:
    disque = shutil.disk_usage(ROOT)
    version = (ROOT / "VERSION").read_text().strip() if (ROOT / "VERSION").exists() else None
    activite = resume_activite(journal)["dernieres_24h"]
    if activite["questions"] == 0 and activite["erreurs_modele"] == 0:
        etat_modele = "inconnu"
    elif activite["erreurs_modele"] > max(3, activite["questions"]):
        etat_modele = "degrade"
    else:
        etat_modele = "ok"
    return {
        "version": version,
        "demarre_le": datetime.fromtimestamp(DEMARRAGE, timezone.utc).isoformat(timespec="seconds"),
        "uptime_service_s": round(time.time() - DEMARRAGE),
        "uptime_systeme_s": _uptime_systeme(),
        "charge": os.getloadavg() if hasattr(os, "getloadavg") else None,
        "processeurs": os.cpu_count(),
        "memoire_service": _memoire_processus(),
        "memoire_systeme": _memoire_systeme(),
        "disque": {"total": disque.total, "libre": disque.free},
        "python": platform.python_version(),
        "systeme": f"{platform.system()} {platform.release()}",
        "index": retriever.stats(),
        "modeles": {
            "generation": list(settings.gemini_models),
            "reformulation": settings.expansion_model or None,
            **extras,
        },
        "etat_modele": etat_modele,
    }


def creer_routes_admin(comptes: Comptes, utilisateur_requis, journal: Journal, settings: Settings,
                       retriever, extras: dict) -> APIRouter:
    router = APIRouter()

    def admin_requis(request: Request) -> Utilisateur:
        u = utilisateur_requis(request)
        if not u.admin:
            raise HTTPException(403, "Accès réservé aux administrateurs.")
        return u

    def _client(uid: int) -> Utilisateur:
        u = comptes.par_id(uid)
        if u is None:
            raise HTTPException(404, "Compte introuvable.")
        return u

    @router.get("/stats")
    def stats(_: Utilisateur = Depends(admin_requis)):
        return {**comptes.statistiques(30), "activite": resume_activite(journal),
                "formules": [f.as_dict() for f in FORMULES.values()]}

    @router.get("/clients")
    def clients(q: str = "", _: Utilisateur = Depends(admin_requis)):
        return comptes.clients(q[:100])

    @router.post("/clients/{uid}/formule", dependencies=[Depends(verifier_origine)])
    def formule(uid: int, req: ChangementFormule, moi: Utilisateur = Depends(admin_requis)):
        u = _client(uid)
        try:
            comptes.changer_formule(u.email, req.formule, req.jours)
        except ErreurCompte as e:
            raise HTTPException(422, str(e)) from None
        journal.ecrire("admin", action="formule", par=moi.id, cible=uid, formule=req.formule, jours=req.jours)
        return next(c for c in comptes.clients(u.email) if c["id"] == uid)

    @router.post("/clients/{uid}/admin", dependencies=[Depends(verifier_origine)])
    def role(uid: int, req: ChangementAdmin, moi: Utilisateur = Depends(admin_requis)):
        u = _client(uid)
        if u.id == moi.id and not req.admin:
            raise HTTPException(422, "Vous ne pouvez pas retirer votre propre rôle d'administrateur.")
        comptes.definir_admin(u.email, req.admin)
        journal.ecrire("admin", action="role", par=moi.id, cible=uid, admin=req.admin)
        return next(c for c in comptes.clients(u.email) if c["id"] == uid)

    @router.post("/clients/{uid}/supprimer", status_code=204, dependencies=[Depends(verifier_origine)])
    def supprimer(uid: int, moi: Utilisateur = Depends(admin_requis)):
        u = _client(uid)
        if u.id == moi.id:
            raise HTTPException(422, "Supprimez votre propre compte depuis la page « Mon compte ».")
        comptes.supprimer(u.id)
        journal.ecrire("admin", action="suppression", par=moi.id, cible=uid)

    @router.get("/activite")
    def activite(limite: int = 100, _: Utilisateur = Depends(admin_requis)):
        champs = ("ts", "route", "mode", "matiere", "statut", "recherche", "modele", "duree_ms", "format", "obtenu")
        recentes = [{k: r.get(k) for k in champs if k in r} for r in journal.lire("requetes", max_lignes=max(1, min(limite, 500)))]
        erreurs = journal.lire("erreurs", max_lignes=50)
        return {"requetes": list(reversed(recentes)), "erreurs": list(reversed(erreurs))}

    @router.get("/serveur")
    def serveur(_: Utilisateur = Depends(admin_requis)):
        return etat_serveur(settings, retriever, journal, extras)

    return router
