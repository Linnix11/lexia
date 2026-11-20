"""Export des donnees du compte (RGPD art. 15 et 20 ; audit du 2026-11-19, JUR-11).

GET /compte/export : un fichier JSON avec le compte (sans mot de passe ni secret), les compteurs d'usage, les cours
deposes avec leur texte et les paiements. Les fiches, le semestre et la conversation restent dans le navigateur :
ils n'ont jamais ete envoyes au serveur, le fichier le rappelle.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from api.comptes import Comptes, Utilisateur

# Colonnes du compte exportees : jamais l'empreinte du mot de passe, les jetons ni les secrets de double
# authentification.
COLONNES_COMPTE = ("email", "prenom", "nom", "formule", "formule_fin", "cree_le", "cgu_le", "cgu_version",
                   "age_atteste", "infos_email_le", "origine", "email_verifie_le", "actif_le", "inactif_avis_le")
COLONNES_PAIEMENT = ("formule", "mois", "montant_centimes", "devise", "statut", "cree_le", "paye_le",
                     "execution_immediate_le", "cgu_version", "retractation_le", "retractation_nom",
                     "accuse_envoye_le", "confirmation_envoyee_le")


def _lignes(comptes: Comptes, table: str, colonnes: tuple[str, ...], condition: str, params: tuple) -> list[dict]:
    """Lignes d'une table, en ne gardant que les colonnes qui existent (tables migrees au fil des versions)."""
    with comptes._lock:
        existe = comptes._con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                                      (table,)).fetchone()
        if not existe:
            return []
        presentes = {r[1] for r in comptes._con.execute(f"PRAGMA table_info({table})")}
        choisies = [c for c in colonnes if c in presentes]
        cur = comptes._con.execute(f"SELECT {', '.join(choisies)} FROM {table} WHERE {condition}", params)
        return [dict(zip(choisies, r)) for r in cur.fetchall()]


def donnees_du_compte(comptes: Comptes, uid: int) -> dict:
    compte = _lignes(comptes, "utilisateurs", COLONNES_COMPTE, "id = ?", (uid,))
    cours = []
    for c in _lignes(comptes, "cours", ("id", "matiere", "titre", "fichier", "pages", "statut", "ajoute_le"),
                     "utilisateur = ? ORDER BY id", (uid,)):
        passages = _lignes(comptes, "cours_passages", ("rang", "page", "page_fin", "texte"),
                           "cours = ? ORDER BY rang", (c.pop("id"),))
        cours.append({**c, "texte": [p["texte"] for p in passages]})
    return {
        "exporte_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "compte": compte[0] if compte else None,
        "usage_par_jour": _lignes(comptes, "usage", ("jour", "questions", "quiz"), "utilisateur = ? ORDER BY jour",
                                  (uid,)),
        "cours_deposes": cours,
        "paiements": _lignes(comptes, "paiements", COLONNES_PAIEMENT, "utilisateur = ? ORDER BY id", (uid,)),
        "dans_votre_navigateur": "Vos fiches, le semestre, la derniere matiere et la conversation en cours sont "
                                 "gardes dans votre navigateur et jamais envoyes au serveur : exportez vos fiches "
                                 "depuis « Fiches & révisions ».",
    }


def creer_route_export(comptes: Comptes, utilisateur_requis) -> APIRouter:
    router = APIRouter()

    @router.get("/compte/export")
    def exporter(u: Utilisateur = Depends(utilisateur_requis)):
        return JSONResponse(donnees_du_compte(comptes, u.id), headers={
            "Content-Disposition": 'attachment; filename="lexia-mes-donnees.json"', "Cache-Control": "no-store"})

    return router
