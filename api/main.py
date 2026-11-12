"""API HTTP de Lexia.

Lancement en developpement :
    uvicorn api.main:app --reload --port 8000
Documentation interactive : http://localhost:8000/docs
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.admin_routes import creer_routes_admin
from api.annales import Annales, creer_routes_annales
from api.auth import creer_routes, routes_formules
from api.comptes import Comptes, Utilisateur
from api.cours import Cours, creer_routes_cours
from api.config import Settings, get_settings
from api.journal import Journal
from api.llm.base import LLM, LLMError
from api.matieres import LIBELLES, sources_par_matiere
from api.textes import NOMS
from api.quiz import QuizService
from api.rag import Lexia, fiche_source
from api.retrieval.base import Retriever
from api.schemas.models import ChatRequest, CorrectionRequest, FeedbackRequest, QuizRequest

log = logging.getLogger("lexia")


class LimiteRequetes:
    """Fenetre glissante d'une minute par adresse IP (memoire du processus)."""

    def __init__(self, par_minute: int):
        self.par_minute = par_minute
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def __call__(self, request: Request) -> None:
        if self.par_minute <= 0:
            return
        ip = request.client.host if request.client else "inconnu"
        now = time.monotonic()
        with self._lock:
            q = self._hits[ip]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= self.par_minute:
                raise HTTPException(429, "Trop de requêtes : réessayez dans une minute.")
            q.append(now)


def _construire_retriever(settings: Settings) -> Retriever:
    from api.retrieval.local import LocalRetriever

    return LocalRetriever(settings.index_dir, embed_model=settings.embed_model or None)


def _construire_embedder(settings: Settings):
    if not settings.embed_provider:
        return None
    from ingest import embedders

    return embedders.creer(settings.embed_provider, settings.embed_model, settings.gemini_api_key)


def releve_jetons(journal: Journal | None, role: str):
    """Jetons consommes par appel, dans logs/modele.jsonl (aucun texte) : base du calcul de cout (eval/cout.py)."""
    if journal is None:
        return None

    def releve(modele: str, usage: dict) -> None:
        journal.ecrire("modele", modele=modele, role=role, entree=usage.get("promptTokenCount", 0),
                       sortie=usage.get("candidatesTokenCount", 0), reflexion=usage.get("thoughtsTokenCount", 0))
    return releve


def _construire_llm(settings: Settings, journal: Journal | None = None) -> LLM:
    from api.llm.gemini import GeminiLLM

    return GeminiLLM(api_key=settings.gemini_api_key, models=settings.gemini_models,
                     thinking_level=settings.gemini_thinking_level, timeout=settings.llm_timeout,
                     releve=releve_jetons(journal, "generation"))


def _construire_secours(settings: Settings):
    if not settings.groq_api_key:
        return None
    from api.llm.groq import GroqLLM

    return GroqLLM(api_key=settings.groq_api_key, model=settings.groq_model, timeout=settings.llm_timeout)


def _construire_expanseur(settings: Settings, journal: Journal | None = None):
    if not settings.expansion_model:
        return None
    from api.expansion import Expanseur
    from api.llm.gemini import GeminiLLM

    # une tentative par modele (principal puis secours) et un delai court par modele :
    # la reformulation ne doit jamais bloquer la reponse
    modeles = (settings.expansion_model, *settings.expansion_fallback_models)
    return Expanseur(GeminiLLM(api_key=settings.gemini_api_key, models=modeles,
                               thinking_level=settings.gemini_thinking_level,
                               timeout=settings.expansion_timeout, tentatives=1,
                               releve=releve_jetons(journal, "reformulation")))


def _construire_reclasseur(settings: Settings):
    if not settings.rerank_model:
        return None
    from api.rerank import CrossEncoderReclasseur

    return CrossEncoderReclasseur(settings.rerank_model)


def create_app(settings: Settings | None = None, *, retriever: Retriever | None = None,
               llm: LLM | None = None, journal: Journal | None = None, embedder=None,
               expanseur=None, reclasseur=None, comptes: Comptes | None = None, secours=None) -> FastAPI:
    settings = settings or get_settings()
    retriever = retriever or _construire_retriever(settings)
    journal = journal if journal is not None else Journal(settings.logs_dir)
    llm = llm or _construire_llm(settings, journal)
    if embedder is None:
        embedder = _construire_embedder(settings)  # charge le modele au demarrage (pas a la 1re question)
    if expanseur is None:
        expanseur = _construire_expanseur(settings, journal)
    if reclasseur is None:
        reclasseur = _construire_reclasseur(settings)
    if secours is None:
        secours = _construire_secours(settings)
    lexia = Lexia(retriever, llm, journal, embedder, expanseur, reclasseur, delai_reformulation=settings.expansion_timeout,
                  secours=secours)
    quiz = QuizService(lexia, llm, journal=journal)
    limite = LimiteRequetes(settings.rate_limit_per_minute)
    # Les routes synchrones partagent 40 threads avec tout le site : quand Gemini est lent, chaque appel
    # en garde un jusqu'a ~100 s. Au-dela de ce plafond, reponse 503 immediate pour garder des threads libres.
    appels_modele = threading.BoundedSemaphore(max(1, settings.appels_modele_simultanes))

    app = FastAPI(title="Lexia API", version="0.2.0",
                  description="Assistant d'étude en droit français : réponses fondées sur des sources officielles citées.")
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    # --- comptes et quotas -------------------------------------------------------
    if settings.comptes_actifs and comptes is None:
        comptes = Comptes(settings.app_db, admins=settings.admin_emails)
    utilisateur_requis = None
    cours = None
    if comptes is not None:
        routes_auth, utilisateur_requis = creer_routes(comptes, settings.inscriptions_par_ip_jour)
        app.include_router(routes_auth, prefix="/auth")
        extras = {"embeddings": getattr(embedder, "model", None), "reclassement": getattr(reclasseur, "model", None)}
        app.include_router(creer_routes_admin(comptes, utilisateur_requis, journal, settings, retriever, extras),
                           prefix="/admin")

        def admin_requis(request: Request) -> Utilisateur:
            u = utilisateur_requis(request)
            if not u.admin:
                raise HTTPException(403, "Accès réservé aux administrateurs.")
            return u

        cours = Cours(comptes.chemin, embedder)
        lexia.cours = cours
        app.include_router(creer_routes_cours(cours, utilisateur_requis))

        annales = Annales(comptes.chemin)
        routes_annales, admin_annales = creer_routes_annales(annales, admin_requis, journal)
        app.include_router(routes_annales)
        app.include_router(admin_annales, prefix="/admin")
    app.include_router(routes_formules())

    def _utilisateur(request: Request) -> Utilisateur | None:
        return utilisateur_requis(request) if utilisateur_requis else None

    def _consommer(u: Utilisateur | None, type_: str) -> None:
        if u is None:
            return
        if not comptes.reserver(u, type_):
            f = u.formule
            limite = f.questions_par_jour if type_ == "questions" else f.quiz_par_jour
            quoi = "questions" if type_ == "questions" else "questionnaires"
            raise HTTPException(402, f"Limite du jour atteinte : {limite} {quoi} avec la formule {f.nom}. "
                                     "Elle se renouvelle à minuit, ou passez à une formule supérieure.")

    def _place_libre(action):
        if not appels_modele.acquire(blocking=False):
            raise HTTPException(503, "Lexia est très sollicité : réessayez dans quelques instants.")
        try:
            return action()
        finally:
            appels_modele.release()

    def _avec_quota(u: Utilisateur | None, type_: str, action):
        """Decompte avant l'appel (limite atomique), rembourse si le modele n'a pas repondu (D32)."""
        _consommer(u, type_)
        try:
            res = action()
        except Exception:
            if u is not None:
                comptes.rembourser(u, type_)  # le modele n'a pas repondu : pas decompte
            raise
        if u is not None and not res["controle"]["modele_appele"]:
            comptes.rembourser(u, type_)  # aucun extrait trouve : le modele n'a pas ete appele
        return res

    @app.exception_handler(LLMError)
    async def _llm_indisponible(request: Request, exc: LLMError):
        log.warning("LLM indisponible : %s", exc)
        journal.ecrire("erreurs", route=request.url.path, type="modele_indisponible", detail=str(exc)[:300])
        return JSONResponse(status_code=503, content={
            "detail": "Le modèle est momentanément indisponible. Réessayez dans quelques instants."})

    def _taille(texte: str) -> None:
        if len(texte) > settings.max_question_chars:
            raise HTTPException(413, f"Texte trop long (maximum {settings.max_question_chars} caractères).")

    def _matiere(m: str | None) -> None:
        if m and m not in sources_par_matiere():
            raise HTTPException(422, f"Matière inconnue : {m}")

    @app.get("/sante")
    def sante():
        return {"statut": "ok", **retriever.stats(), "modeles": list(settings.gemini_models),
                "secours": getattr(secours, "model", None),
                "embeddings_modele": getattr(embedder, "model", None),
                "reformulation_modele": settings.expansion_model or None,
                "reclassement_modele": getattr(reclasseur, "model", None)}

    @app.get("/config")
    def config_publique():
        legal = {k: (v or None) if isinstance(v, str) else v for k, v in settings.legal.items()}
        return {"comptes": comptes is not None, "contact_email": settings.contact_email or None, "legal": legal}

    @app.get("/matieres")
    def matieres():
        return [{"id": m, "libelle": LIBELLES.get(m, m), "sources": list(s),
                 "noms_sources": {i: NOMS.get(i, i) for i in s}} for m, s in sources_par_matiere().items()]

    @app.post("/chat", dependencies=[Depends(limite)])
    def chat(req: ChatRequest, request: Request):
        u = _utilisateur(request)
        _taille(req.question)
        _matiere(req.matiere)
        return _place_libre(lambda: _avec_quota(u, "questions",
                                                lambda: lexia.chat(req.question.strip(), req.mode, req.matiere,
                                                                   req.niveau, req.semestre, req.cours,
                                                                   req.avec_officiel, u.id if u else None)))

    @app.post("/quiz", dependencies=[Depends(limite)])
    def creer_quiz(req: QuizRequest, request: Request):
        u = _utilisateur(request)
        _taille(req.theme)
        _matiere(req.matiere)
        return _place_libre(lambda: _avec_quota(
            u, "quiz", lambda: quiz.generer(req.theme.strip(), req.format, req.nombre, req.matiere,
                                      req.niveau, req.semestre, req.cours, req.avec_officiel,
                                      u.id if u else None)))

    @app.post("/quiz/correct", dependencies=[Depends(limite)])
    def corriger_quiz(req: CorrectionRequest, request: Request):
        _utilisateur(request)
        res = _place_libre(lambda: quiz.corriger(req.quiz_id, [r.model_dump() for r in req.reponses]))
        if res is None:
            raise HTTPException(404, "Questionnaire introuvable ou expiré : générez-en un nouveau.")
        return res

    # /vigueur doit etre declaree avant la route generique (les identifiants contiennent des ':')
    def _passage_de_cours(passage_id: str, request: Request) -> dict:
        """Passage d'un cours depose : visible par son seul proprietaire."""
        u = _utilisateur(request)
        p = cours.passage(u.id, passage_id) if (u is not None and cours is not None) else None
        if p is None:
            raise HTTPException(404, "Source introuvable.")
        return p

    @app.get("/sources/{passage_id:path}/vigueur")
    def vigueur(passage_id: str, request: Request):
        if passage_id.startswith("cours:"):
            p = _passage_de_cours(passage_id, request)
            return {"id": p["id"], "source_id": p["source_id"], "version": p["version"], "url": "",
                    "applicable": False, "en_vigueur": None, "version_en_vigueur": None,
                    "message": "Passage de votre cours : il n'a pas de version officielle. Vérifiez les règles "
                               "qu'il cite dans les textes officiels."}
        res = lexia.vigueur(passage_id)
        if res is None:
            raise HTTPException(404, "Source introuvable.")
        return res

    @app.get("/sources/{passage_id:path}")
    def source(passage_id: str, request: Request):
        p = _passage_de_cours(passage_id, request) if passage_id.startswith("cours:") else retriever.get(passage_id)
        if p is None:
            raise HTTPException(404, "Source introuvable.")
        return {**fiche_source(p), "texte": p["texte"], "titre": p.get("titre"), "meta": p.get("meta") or {}}

    @app.post("/feedback", status_code=204)
    def feedback(req: FeedbackRequest, request: Request):
        _utilisateur(request)  # compte requis : evite qu'un anonyme fausse les statistiques ou remplisse le disque
        journal.ecrire("feedback", reponse_id=req.reponse_id, utile=req.utile, motif=req.motif)

    app.state.retriever = retriever  # utile aux outils d'evaluation
    app.state.comptes = comptes
    return app


def _app_paresseuse():
    """Construit l'application au demarrage d'uvicorn (pas a l'import, pour les tests)."""
    logging.basicConfig(level=logging.INFO)
    return create_app()


def __getattr__(name: str):
    if name == "app":
        global app
        app = _app_paresseuse()
        return app
    raise AttributeError(name)
