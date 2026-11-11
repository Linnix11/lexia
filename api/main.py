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

from api.config import Settings, get_settings
from api.journal import Journal
from api.llm.base import LLM, LLMError
from api.matieres import LIBELLES, sources_par_matiere
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
    if settings.retriever == "postgres":
        from api.retrieval.postgres import PostgresRetriever

        return PostgresRetriever(settings.database_url)
    from api.retrieval.local import LocalRetriever

    return LocalRetriever(settings.index_dir, embed_model=settings.embed_model or None)


def _construire_embedder(settings: Settings):
    if not settings.embed_provider:
        return None
    from ingest import embedders

    return embedders.creer(settings.embed_provider, settings.embed_model, settings.gemini_api_key)


def _construire_llm(settings: Settings) -> LLM:
    from api.llm.gemini import GeminiLLM

    return GeminiLLM(api_key=settings.gemini_api_key, models=settings.gemini_models,
                     thinking_level=settings.gemini_thinking_level, timeout=settings.llm_timeout)


def _construire_expanseur(settings: Settings):
    if not settings.expansion_model:
        return None
    from api.expansion import Expanseur
    from api.llm.gemini import GeminiLLM

    # une tentative par modele (principal puis secours) et un delai court par modele :
    # la reformulation ne doit jamais bloquer la reponse
    modeles = (settings.expansion_model, *settings.expansion_fallback_models)
    return Expanseur(GeminiLLM(api_key=settings.gemini_api_key, models=modeles,
                               thinking_level=settings.gemini_thinking_level,
                               timeout=settings.expansion_timeout, tentatives=1))


def _construire_reclasseur(settings: Settings):
    if not settings.rerank_model:
        return None
    from api.rerank import CrossEncoderReclasseur

    return CrossEncoderReclasseur(settings.rerank_model)


def create_app(settings: Settings | None = None, *, retriever: Retriever | None = None,
               llm: LLM | None = None, journal: Journal | None = None, embedder=None,
               expanseur=None, reclasseur=None) -> FastAPI:
    settings = settings or get_settings()
    retriever = retriever or _construire_retriever(settings)
    llm = llm or _construire_llm(settings)
    journal = journal if journal is not None else Journal(settings.logs_dir)
    if embedder is None:
        embedder = _construire_embedder(settings)  # charge le modele au demarrage (pas a la 1re question)
    if expanseur is None:
        expanseur = _construire_expanseur(settings)
    if reclasseur is None:
        reclasseur = _construire_reclasseur(settings)
    lexia = Lexia(retriever, llm, journal, embedder, expanseur, reclasseur)
    quiz = QuizService(lexia, llm, journal=journal)
    limite = LimiteRequetes(settings.rate_limit_per_minute)

    app = FastAPI(title="Lexia API", version="0.2.0",
                  description="Assistant d'étude en droit français : réponses fondées sur des sources officielles citées.")
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    @app.exception_handler(LLMError)
    async def _llm_indisponible(request: Request, exc: LLMError):
        log.warning("LLM indisponible : %s", exc)
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
                "embeddings_modele": getattr(embedder, "model", None),
                "reformulation_modele": settings.expansion_model or None,
                "reclassement_modele": getattr(reclasseur, "model", None)}

    @app.get("/matieres")
    def matieres():
        return [{"id": m, "libelle": LIBELLES.get(m, m), "sources": list(s)} for m, s in sources_par_matiere().items()]

    @app.post("/chat", dependencies=[Depends(limite)])
    def chat(req: ChatRequest):
        _taille(req.question)
        _matiere(req.matiere)
        return lexia.chat(req.question.strip(), req.mode, req.matiere)

    @app.post("/quiz", dependencies=[Depends(limite)])
    def creer_quiz(req: QuizRequest):
        _taille(req.theme)
        _matiere(req.matiere)
        return quiz.generer(req.theme.strip(), req.format, req.nombre, req.matiere)

    @app.post("/quiz/correct", dependencies=[Depends(limite)])
    def corriger_quiz(req: CorrectionRequest):
        res = quiz.corriger(req.quiz_id, [r.model_dump() for r in req.reponses])
        if res is None:
            raise HTTPException(404, "Questionnaire introuvable ou expiré : générez-en un nouveau.")
        return res

    # /vigueur doit etre declaree avant la route generique (les identifiants contiennent des ':')
    @app.get("/sources/{passage_id:path}/vigueur")
    def vigueur(passage_id: str):
        res = lexia.vigueur(passage_id)
        if res is None:
            raise HTTPException(404, "Source introuvable.")
        return res

    @app.get("/sources/{passage_id:path}")
    def source(passage_id: str):
        p = retriever.get(passage_id)
        if p is None:
            raise HTTPException(404, "Source introuvable.")
        return {**fiche_source(p), "texte": p["texte"], "titre": p.get("titre"), "meta": p.get("meta") or {}}

    @app.post("/feedback", status_code=204)
    def feedback(req: FeedbackRequest):
        journal.ecrire("feedback", reponse_id=req.reponse_id, utile=req.utile, motif=req.motif)

    app.state.retriever = retriever  # utile aux outils d'evaluation
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
