"""Cartes mentales : plan hierarchique d'une reponse, d'un cours depose, d'une fiche recuperee ou d'une matiere (D112).

Le modele en place (Gemini, Groq en secours, via Lexia.generer) rend un plan JSON impose par un schema
(notion centrale, branches, sous-branches, references en feuilles), borne en jetons et en duree. La forme est
controlee par api/llm/forme.py (hors schema : modele suivant) ; le contenu comme les citations des reponses :
un libelle qui cite une reference absente des extraits envoyes est retire, une feuille n'est gardee que si elle
contient une reference presente dans ces extraits. Chaque feuille renvoie au texte officiel quand Lexia le connait.
Le dessin est fait par le navigateur. Reserve aux comptes, limite par jour. Plan : docs/cartes-mentales.md.
"""

from __future__ import annotations

import re
import time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from api import prompts
from api.auth import verifier_origine
from api.citations import Controle, verifier_texte
from api.journal import Journal
from api.matieres import MATIERES
from api.references import _norm_num, articles_cites, extraire, variantes
from api.resumes_vocaux import (MAX_CARACTERES_REPONSE, MAX_SOURCES_REPONSE, DemandeResume, DocumentIntrouvable,
                                QuotaResumes, ResumesVocaux, borner)
from api.textes import en_vigueur_aujourdhui

AVERTISSEMENT = "Carte générée automatiquement : vérifiez avec les textes."
# Gemini compte la reflexion dans maxOutputTokens : un plan de 7 branches de 5 sous-branches (~1 500 jetons au
# plus) et une reflexion « low » tiennent sous ce plafond.
MAX_JETONS_CARTE = 3072
K_MATIERE = 12           # extraits officiels pour une matiere
MAX_BRANCHES = 7
MIN_BRANCHES = 2         # en dessous, pas de carte (et rien de decompte)
MAX_ENFANTS = 5
MAX_ARTICLES = 3
MAX_LIBELLE = 120        # caracteres

_REPERES = re.compile(r"\s*[\[(]\s*S\d+(?:\s*[,;]\s*S\d+)*\s*[\])]", re.IGNORECASE)
_MARKDOWN = re.compile(r"[*_#`>]+")


class DemandeCarte(BaseModel):
    type: Literal["reponse", "cours", "cours_recupere", "matiere"]
    id: str | None = Field(default=None, max_length=100)                 # cours depose ou fiche recuperee
    titre: str = Field(default="", max_length=300)                       # reponse
    texte: str = Field(default="", max_length=MAX_CARACTERES_REPONSE)    # reponse
    sources: list[str] = Field(default_factory=list, max_length=MAX_SOURCES_REPONSE)  # reponse : extraits cites
    matiere: str | None = Field(default=None, max_length=60)             # matiere
    notion: str = Field(default="", max_length=120)                      # matiere : notion a cartographier


def _libelle(brut) -> str:
    """Libelle sur une ligne, sans repere S1 ni Markdown, sans ponctuation finale, coupe a MAX_LIBELLE."""
    texte = _MARKDOWN.sub("", _REPERES.sub("", str(brut or "")))
    texte = " ".join(texte.split()).strip(" .;:,-")
    if len(texte) > MAX_LIBELLE:
        texte = texte[:MAX_LIBELLE].rsplit(" ", 1)[0] + "…"
    return texte


def _noeud(brut, envoyes: list[dict], controle: Controle) -> dict | None:
    if not isinstance(brut, dict):   # forme deja controlee (api/llm/forme.py) ; filet
        controle.elements_retires += 1
        return None
    libelle = _libelle(brut.get("libelle"))
    if not libelle:
        return None
    if not verifier_texte(libelle, envoyes, controle):
        controle.elements_retires += 1
        return None
    articles: list[dict] = []
    for a in brut.get("articles") or []:
        texte = _libelle(a)
        if not texte or any(x["texte"] == texte for x in articles):
            continue
        # Une feuille est une reference (article, decision, pourvoi) presente dans les extraits envoyes.
        if extraire(texte).vide or not verifier_texte(texte, envoyes, controle):
            controle.citations_retirees += 1
            continue
        articles.append({"texte": texte})
        if len(articles) >= MAX_ARTICLES:
            break
    return {"libelle": libelle, "articles": articles}


def nettoyer(brut: dict, envoyes: list[dict], controle: Controle) -> list[dict]:
    """Branches verifiees et bornees (MAX_BRANCHES, MAX_ENFANTS, MAX_ARTICLES)."""
    branches: list[dict] = []
    for b in brut.get("branches") or []:
        noeud = _noeud(b, envoyes, controle)
        if noeud is None:
            continue
        enfants: list[dict] = []
        for e in (b.get("enfants") or []):
            n = _noeud(e, envoyes, controle)
            if n is not None:
                enfants.append({**n, "enfants": []})
            if len(enfants) >= MAX_ENFANTS:
                break
        branches.append({**noeud, "enfants": enfants})
        if len(branches) >= MAX_BRANCHES:
            break
    return branches


def _lien(p: dict) -> dict:
    return {"url": p["url"], "entete": p.get("entete") or p.get("titre") or ""}


class CartesMentales:
    def __init__(self, lexia, retriever, documents: ResumesVocaux, chercheur=None, journal: Journal | None = None):
        self.lexia = lexia            # Lexia dont les modeles ont MAX_JETONS_CARTE et le delai des cartes
        self.retriever = retriever
        self.documents = documents    # lecture des documents des resumes vocaux (meme regles d'acces)
        self.chercheur = chercheur    # Lexia principale : recherche dans une matiere
        self.journal = journal or Journal(None)

    # -- documents --

    def verifier(self, d: DemandeCarte, uid: int):
        """Document a cartographier (titre, morceaux), ou None pour une matiere (cherchee ensuite).
        DocumentIntrouvable s'il n'existe pas pour ce compte : rien n'est decompte."""
        if d.type == "matiere":
            if d.matiere not in MATIERES or self.chercheur is None:
                raise DocumentIntrouvable("Matière inconnue.")
            return None
        return self.documents.document(DemandeResume(type=d.type, id=d.id, titre=d.titre, texte=d.texte,
                                                     sources=d.sources), uid)

    def _matiere(self, d: DemandeCarte) -> tuple[str, list[dict]]:
        m = MATIERES[d.matiere]
        notion = " ".join(d.notion.split())
        requete = notion or f"{m.libelle} : {', '.join(m.mots)}"
        passages, _ = self.chercheur.rechercher(requete, d.matiere, K_MATIERE)
        return (f"{notion} ({m.libelle})" if notion else m.libelle), passages

    def _officiels(self, d: DemandeCarte) -> list[dict]:
        """Extraits officiels cites par la reponse (avec leur adresse) : premiers liens des feuilles."""
        if d.type != "reponse":
            return []
        out = []
        for pid in dict.fromkeys(d.sources):
            p = None if pid.startswith("cours:") else self.retriever.get(pid)
            if p is not None:
                out.append(p)
        return out

    # -- liens --

    def lien(self, texte: str, candidats: list[dict]) -> dict | None:
        """Texte officiel d'une feuille : extrait fourni qui porte la reference, sinon article cherche dans
        l'index par son code et son numero (version en vigueur) ; None sans code nomme ni extrait."""
        candidats = [p for p in candidats if p.get("url")]
        for num, code in articles_cites(texte):
            for p in candidats:
                if _norm_num(p.get("numero") or "") == num and (not code or p.get("source_id") == code):
                    return _lien(p)
            if code:
                versions = [p for v in variantes(num) for p in (self.retriever.versions(code, v) or [])
                            if p.get("url")]
                etats = [en_vigueur_aujourdhui(p.get("meta") or {}, code) for p in versions]
                # version en vigueur d'abord, sinon une version a l'etat inconnu ; jamais une version finie
                for voulu in (True, None):
                    for p, etat in zip(versions, etats):
                        if etat is voulu:
                            return _lien(p)
        refs = extraire(texte)
        for p in candidats:
            meta = p.get("meta") or {}
            if any(meta.get("numero") == d.split()[0] and meta.get("nature") == d.split()[1]
                   for d in refs.decisions_cc):
                return _lien(p)
            if any(x.replace(".", "") in (meta.get("numeros_pourvoi") or []) for x in refs.pourvois):
                return _lien(p)
            if meta.get("id_dila") and meta.get("id_dila") in refs.decisions_admin:
                return _lien(p)
        return None

    # -- carte --

    def carte(self, d: DemandeCarte, document) -> dict:
        """document : rendu par verifier() (None pour une matiere)."""
        debut = time.monotonic()
        if document is None:
            titre, morceaux = self._matiere(d)
        else:
            titre, morceaux = document
        if not morceaux:
            return self._resultat(titre, [], False, Controle(), appele=False,
                                  message="Aucun extrait officiel trouvé pour cette notion : précisez-la.")
        morceaux, partiel = borner(morceaux)
        brut, modele, envoyes = self.lexia.generer(
            system=prompts.SYSTEME_CARTE_MENTALE,
            construire=lambda ms: prompts.prompt_carte_mentale(d.type, titre, ms, partiel),
            passages=morceaux, schema=prompts.SCHEMA_CARTE_MENTALE, temperature=0.2)
        controle = Controle()
        # Verifie contre ce que le modele a recu (le secours n'a que les premiers morceaux)
        branches = nettoyer(brut, envoyes, controle)
        candidats = self._officiels(d) + envoyes
        liens = 0
        for n in branches:
            for x in [n, *n["enfants"]]:
                for a in x["articles"]:
                    a["lien"] = self.lien(a["texte"], candidats)
                    liens += a["lien"] is not None
        titre_carte = _libelle(brut.get("titre"))
        if not verifier_texte(titre_carte, envoyes, controle):
            titre_carte = ""
        partiel = partiel or len(envoyes) < len(morceaux)
        valide = len(branches) >= MIN_BRANCHES
        self.journal.ecrire("requetes", route="carte_mentale", type=d.type, modele=modele,
                            branches=len(branches), noeuds=sum(1 + len(b["enfants"]) for b in branches),
                            feuilles=sum(len(x["articles"]) for b in branches for x in [b, *b["enfants"]]),
                            liens=liens, partiel=partiel, controle=controle.as_dict(),
                            duree_ms=int((time.monotonic() - debut) * 1000))
        return self._resultat(titre_carte or _libelle(titre), branches if valide else [], partiel, controle,
                              appele=True, message="" if valide else
                              "Impossible de produire une carte vérifiable de ce document.")

    @staticmethod
    def _resultat(titre: str, branches: list[dict], partiel: bool, controle: Controle, *, appele: bool,
                  message: str) -> dict:
        return {"titre": titre, "branches": branches, "partiel": partiel, "message": message,
                "avertissement": AVERTISSEMENT, "controle": {**controle.as_dict(), "modele_appele": appele}}


def creer_routes_cartes_mentales(service: CartesMentales, quota: QuotaResumes, utilisateur_requis, limite,
                                 place_libre) -> APIRouter:
    """limite : limite de debit par minute (comme /chat) ; place_libre(action) : place parmi les appels au modele."""
    routes = APIRouter()

    @routes.post("/carte-mentale", dependencies=[Depends(limite), Depends(verifier_origine)])
    def cartographier(d: DemandeCarte, request: Request):
        u = utilisateur_requis(request)
        if not u.email_verifie:
            raise HTTPException(403, "Confirmez votre adresse e-mail pour obtenir une carte mentale : "
                                     "le lien vous a été envoyé à l'inscription.")
        # Document lu avant de decompter : un cours absent ne coute rien.
        try:
            document = service.verifier(d, u.id)
        except DocumentIntrouvable as e:
            raise HTTPException(404, str(e)) from None
        jour = quota.reserver(u.id)
        if jour is None:
            raise HTTPException(402, f"Limite du jour atteinte : {quota.par_jour} cartes mentales par jour. "
                                     "Elle se renouvelle à minuit.")
        try:
            res = place_libre(lambda: service.carte(d, document))
        except Exception:
            quota.rembourser(u.id, jour)  # le modele n'a pas repondu (ou plus de place) : pas decompte
            raise
        if not res["branches"]:
            quota.rembourser(u.id, jour)  # jour de la reservation, meme apres minuit (A5)
        return {**res, "restants": max(0, quota.par_jour - quota.utilises(u.id))}

    @routes.get("/carte-mentale/quota")
    def restants(request: Request):
        u = utilisateur_requis(request)
        return {"par_jour": quota.par_jour, "restants": max(0, quota.par_jour - quota.utilises(u.id))}

    return routes
