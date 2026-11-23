"""Resumes vocaux : texte d'un resume audio d'une reponse, d'un cours depose ou d'un cours recupere (D106).

Le serveur ne produit que le texte ; le navigateur le lit (Web Speech API), sans cout serveur. Texte redige par
le modele en place (Gemini, Groq en secours, via Lexia.generer), avec un plafond de jetons plus bas que les
reponses, puis controle comme les reponses : un paragraphe qui cite un article, une decision ou un pourvoi absent
du document est retire. Reserve aux comptes, limite par jour (table a part, decomptee comme les questions :
remboursee si le modele n'a pas repondu). Plan et choix : docs/resumes-vocaux.md.
"""

from __future__ import annotations

import re
import sqlite3
import threading
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from api import prompts
from api.auth import verifier_origine
from api.citations import Controle, verifier_texte
from api.comptes import _jour
from api.journal import Journal

AVERTISSEMENT = ("Résumé généré automatiquement : il peut contenir des erreurs. "
                 "Vérifiez avec les textes et les sources citées.")
# Gemini compte la reflexion dans maxOutputTokens : 650 mots (~1 000 jetons) et une reflexion « low » tiennent
# sous ce plafond, plus bas que celui des reponses (4 096).
MAX_JETONS_RESUME = 3072
MAX_CARACTERES_DOCUMENT = 24_000   # au-dela, seul le debut est resume (le site le dit)
MAX_CARACTERES_REPONSE = 12_000    # texte d'une reponse envoye par le site
MAX_SOURCES_REPONSE = 12
TAILLE_MORCEAU = 3_000             # le secours ne recoit que les premiers morceaux (rag.pour_secours)
MAX_MOTS = 800                     # environ 5 min 20 a 150 mots par minute
MIN_MOTS = 40
MOTS_PAR_MINUTE = 150
CONSERVATION_JOURS = 31            # compteurs par jour effaces apres un mois

_REPERES = re.compile(r"\s*[\[(]\s*S\d+(?:\s*[,;]\s*S\d+)*\s*[\])]", re.IGNORECASE)


class DemandeResume(BaseModel):
    type: Literal["reponse", "cours", "cours_recupere"]
    id: str | None = Field(default=None, max_length=100)            # cours depose ou cours recupere
    titre: str = Field(default="", max_length=300)                  # reponse
    texte: str = Field(default="", max_length=MAX_CARACTERES_REPONSE)  # reponse
    sources: list[str] = Field(default_factory=list, max_length=MAX_SOURCES_REPONSE)  # reponse : extraits cites


class QuotaResumes:
    """Resumes du jour par compte, dans la base des comptes (table a part : rien a changer dans `usage`)."""

    def __init__(self, chemin: Path | str, par_jour: int, table: str = "resumes_vocaux"):
        # table : nom fixe dans le code (« cartes_mentales » pour les cartes, D112), jamais venu d'une requete
        if not table.isidentifier():
            raise ValueError(table)
        self.par_jour = par_jour
        self._t = table
        self._con = sqlite3.connect(str(chemin), check_same_thread=False)
        self._con.execute("PRAGMA foreign_keys = ON")
        self._con.execute(f"CREATE TABLE IF NOT EXISTS {table} (utilisateur INTEGER NOT NULL "
                          "REFERENCES utilisateurs(id) ON DELETE CASCADE, jour TEXT NOT NULL, "
                          "nombre INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (utilisateur, jour))")
        self._con.commit()
        self._lock = threading.Lock()

    def utilises(self, uid: int) -> int:
        with self._lock:
            row = self._con.execute(f"SELECT nombre FROM {self._t} WHERE utilisateur = ? AND jour = ?",
                                    (uid, _jour())).fetchone()
        return row[0] if row else 0

    def reserver(self, uid: int) -> str | None:
        """Compte un resume (ou une carte) si la limite du jour le permet ; renvoie le jour decompte, a rendre a
        rembourser, ou None si la limite est atteinte."""
        jour = _jour()
        ancien = (date.fromisoformat(jour) - timedelta(days=CONSERVATION_JOURS)).isoformat()
        with self._lock, self._con:
            self._con.execute(f"DELETE FROM {self._t} WHERE jour < ?", (ancien,))
            self._con.execute(f"INSERT OR IGNORE INTO {self._t} (utilisateur, jour) VALUES (?, ?)", (uid, jour))
            cur = self._con.execute(f"UPDATE {self._t} SET nombre = nombre + 1 WHERE utilisateur = ? "
                                    "AND jour = ? AND nombre < ?", (uid, jour, self.par_jour))
            return jour if cur.rowcount == 1 else None

    def rembourser(self, uid: int, jour: str | None = None) -> None:
        """jour : celui de la reservation. Reserve a 23 h 59 et rate apres minuit, le resume etait rendu sur le
        lendemain (audit du 23/11, A5 ; meme defaut que SRV-13 pour les questions)."""
        with self._lock, self._con:
            self._con.execute(f"UPDATE {self._t} SET nombre = MAX(nombre - 1, 0) WHERE utilisateur = ? "
                              "AND jour = ?", (uid, jour or _jour()))


class DocumentIntrouvable(LookupError):
    pass


def decouper(texte: str, entete: str, taille: int = TAILLE_MORCEAU) -> list[dict]:
    """Morceaux de `taille` caracteres au plus, coupes a un saut de ligne ou une espace quand c'est possible."""
    morceaux: list[dict] = []
    texte = texte.strip()
    while texte:
        if len(texte) <= taille:
            bout, texte = texte, ""
        else:
            coupe = max(texte.rfind("\n", 0, taille), texte.rfind(" ", 0, taille))
            coupe = coupe if coupe > taille // 2 else taille
            bout, texte = texte[:coupe].strip(), texte[coupe:].strip()
        if bout:
            morceaux.append(_morceau(bout, entete, len(morceaux)))
    return morceaux


def _morceau(texte: str, entete: str, rang: int, source_id: str = "document") -> dict:
    # Forme d'un passage : lu par rag.pour_secours (source_id, type) et par references (texte, entete).
    return {"id": f"{source_id}:{rang}", "source_id": source_id, "type": "cours", "entete": entete,
            "texte": texte}


def borner(morceaux: list[dict], maximum: int = MAX_CARACTERES_DOCUMENT) -> tuple[list[dict], bool]:
    """Premiers morceaux jusqu'a `maximum` caracteres ; partiel = du texte a ete laisse de cote."""
    garde, total = [], 0
    for m in morceaux:
        if total + len(m["texte"]) > maximum:
            reste = maximum - total
            if reste > 200:
                garde.append({**m, "texte": m["texte"][:reste]})
            return garde, True
        garde.append(m)
        total += len(m["texte"])
    return garde, False


def document_partiel(morceaux: list[dict], envoyes: list[dict]) -> bool:
    """Du texte du document lui-meme n'a pas ete envoye au modele. Les extraits cites d'une reponse ou les passages
    d'une matiere laisses au modele principal quand le secours prend le relais (4 morceaux, rag.pour_secours) n'en
    sont pas : une reponse de quelques paragraphes etait dite « trop longue » (recette du 23/11, R-4)."""
    ids = {m["id"] for m in envoyes}
    return any(m.get("source_id") == "document" and m["id"] not in ids for m in morceaux)


def nettoyer(brut: dict, document: list[dict], controle: Controle) -> list[str]:
    """Paragraphes verifies, sans repere S1, coupes a MAX_MOTS a la fin d'un paragraphe (ou d'une phrase)."""
    gardes: list[str] = []
    mots = 0
    for p in brut.get("paragraphes") or []:
        texte = _REPERES.sub("", str(p or "")).strip()
        if not texte:
            continue
        if not verifier_texte(texte, document, controle):
            controle.elements_retires += 1
            continue
        n = len(texte.split())
        if mots + n > MAX_MOTS:
            if not gardes:  # premier paragraphe trop long a lui seul : coupe a la derniere phrase qui tient
                phrases = re.split(r"(?<=[.!?…])\s+", texte)
                retenu = []
                for ph in phrases:
                    if mots + len(ph.split()) > MAX_MOTS:
                        break
                    retenu.append(ph)
                    mots += len(ph.split())
                if retenu:
                    gardes.append(" ".join(retenu))
            break
        gardes.append(texte)
        mots += n
    return gardes


class ResumesVocaux:
    def __init__(self, lexia, retriever, journal: Journal | None = None, cours=None, catalogue=None):
        self.lexia = lexia          # Lexia dont les modeles ont le plafond MAX_JETONS_RESUME
        self.retriever = retriever
        self.journal = journal or Journal(None)
        self.cours = cours          # api.cours.Cours (lecture seule, base des comptes)
        self.catalogue = catalogue  # api.cours_recuperes.Catalogue

    # -- documents --

    def document(self, d: DemandeResume, uid: int) -> tuple[str, list[dict]]:
        """(titre, morceaux) du document a resumer ; DocumentIntrouvable s'il n'existe pas pour ce compte."""
        if d.type == "cours":
            return self._cours_depose(d.id, uid)
        if d.type == "cours_recupere":
            c = self.catalogue.lire(d.id or "") if self.catalogue is not None else None
            if c is None:
                raise DocumentIntrouvable("Cours introuvable.")
            texte = "\n\n".join(f"{s['titre']}\n{s['texte']}".strip() for s in c["sections"])
            return c["titre"], decouper(texte, f"{c['titre']} ({c['source']})")
        texte = d.texte.strip()
        if not texte:
            raise DocumentIntrouvable("Réponse vide.")
        morceaux = decouper(texte, "Réponse de Lexia")
        for i, pid in enumerate(dict.fromkeys(d.sources)):
            p = (self.cours.passage(uid, pid) if self.cours is not None else None) if pid.startswith("cours:") \
                else self.retriever.get(pid)
            if p is not None:  # extrait inconnu ou cours d'un autre compte : ignore
                morceaux.append({**_morceau(p["texte"][:TAILLE_MORCEAU], p.get("entete") or pid, i, "extrait"),
                                 "numero": p.get("numero"), "meta": p.get("meta") or {}})
        return d.titre.strip(), morceaux

    def _cours_depose(self, cid: str | None, uid: int) -> tuple[str, list[dict]]:
        if self.cours is None or not (cid or "").isdigit():
            raise DocumentIntrouvable("Cours introuvable.")
        # Lecture seule par la connexion du module des cours, pour son seul proprietaire.
        rows = self.cours._q("SELECT c.titre, p.texte FROM cours_passages p JOIN cours c ON c.id = p.cours "
                             "WHERE c.id = ? AND c.utilisateur = ? ORDER BY p.rang", (int(cid), uid))
        if not rows:
            raise DocumentIntrouvable("Cours introuvable.")
        titre = rows[0][0]
        morceaux: list[dict] = []
        for _, texte in rows:
            for m in decouper(texte, titre):
                morceaux.append({**m, "id": f"document:{len(morceaux)}"})
        return titre, morceaux

    # -- resume --

    def resumer(self, d: DemandeResume, titre: str, morceaux: list[dict]) -> dict:
        """titre et morceaux : rendus par document()."""
        debut = time.monotonic()
        morceaux, partiel = borner(morceaux)
        brut, modele, envoyes = self.lexia.generer(
            system=prompts.SYSTEME_RESUME_VOCAL,
            construire=lambda ms: prompts.prompt_resume_vocal(d.type, titre, ms, partiel),
            passages=morceaux, schema=prompts.SCHEMA_RESUME_VOCAL, temperature=0.3)
        controle = Controle()
        # Verifie contre ce que le modele a recu (le secours n'a que les premiers morceaux)
        paragraphes = nettoyer(brut, envoyes, controle)
        mots = sum(len(p.split()) for p in paragraphes)
        valide = mots >= MIN_MOTS
        titre_resume = str(brut.get("titre") or "").strip()[:200]
        if not verifier_texte(titre_resume, envoyes, controle):
            titre_resume = ""
        partiel = partiel or document_partiel(morceaux, envoyes)
        self.journal.ecrire("requetes", route="resume_vocal", type=d.type, modele=modele, mots=mots,
                            partiel=partiel, controle=controle.as_dict(),
                            duree_ms=int((time.monotonic() - debut) * 1000))
        return {
            "titre": titre_resume or titre,
            "paragraphes": paragraphes if valide else [],
            "mots": mots if valide else 0,
            "duree_estimee_s": round(mots * 60 / MOTS_PAR_MINUTE) if valide else 0,
            "partiel": partiel,
            "message": "" if valide else "Impossible de produire un résumé vérifiable de ce document.",
            "avertissement": AVERTISSEMENT,
            "controle": {**controle.as_dict(), "modele_appele": True},
        }


def creer_routes_resumes_vocaux(service: ResumesVocaux, quota: QuotaResumes, utilisateur_requis, limite,
                                place_libre) -> APIRouter:
    """limite : limite de debit par minute (comme /chat) ; place_libre(action) : place parmi les appels au modele."""
    routes = APIRouter()

    @routes.post("/resume-vocal", dependencies=[Depends(limite), Depends(verifier_origine)])
    def resumer(d: DemandeResume, request: Request):
        u = utilisateur_requis(request)
        if not u.email_verifie:
            raise HTTPException(403, "Confirmez votre adresse e-mail pour écouter un résumé : "
                                     "le lien vous a été envoyé à l'inscription.")
        # Document lu avant de decompter : un cours absent ne coute rien.
        try:
            titre, morceaux = service.document(d, u.id)
        except DocumentIntrouvable as e:
            raise HTTPException(404, str(e)) from None
        jour = quota.reserver(u.id)
        if jour is None:
            raise HTTPException(402, f"Limite du jour atteinte : {quota.par_jour} résumés vocaux par jour. "
                                     "Elle se renouvelle à minuit.")
        try:
            res = place_libre(lambda: service.resumer(d, titre, morceaux))
        except Exception:
            quota.rembourser(u.id, jour)  # le modele n'a pas repondu (ou plus de place) : pas decompte
            raise
        if not res["paragraphes"]:
            quota.rembourser(u.id, jour)
        return {**res, "restants": max(0, quota.par_jour - quota.utilises(u.id))}

    @routes.get("/resume-vocal/quota")
    def restants(request: Request):
        u = utilisateur_requis(request)
        return {"par_jour": quota.par_jour, "restants": max(0, quota.par_jour - quota.utilises(u.id))}

    return routes
