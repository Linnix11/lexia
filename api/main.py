"""API HTTP de Lexia.

Lancement en developpement :
    uvicorn api.main:app --reload --port 8000
Documentation interactive (avec API_DOCS=1 dans .env) : http://localhost:8000/docs
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.admin_routes import creer_routes_admin
from api.annales import Annales, creer_routes_annales
from api.auth import COOKIE, cle_ip, creer_routes, exiger_admin, routes_formules, verifier_origine
from api import coffre
from api.comptes import Comptes, Utilisateur
from api.cours import Cours, creer_routes_cours
from api.cours_recuperes import Catalogue, creer_routes_cours_recuperes
from api.config import Settings, get_settings
from api.journal import Journal
from api.llm.base import LLM, LLMError
from api.matieres import LIBELLES, MATIERES, sources_par_matiere
from api.textes import HORS_LEGI, NOMS, SOURCES_TEXTES
from api.quiz import QuizService, QuizStore
from api.rag import Disjoncteur, Lexia, fiche_source
from api.resumes_vocaux import MAX_JETONS_RESUME, QuotaResumes, ResumesVocaux, creer_routes_resumes_vocaux
from api.retrieval.base import Retriever
from api.schemas.models import ChatRequest, CorrectionRequest, FeedbackRequest, QuizRequest
from ingest import fraicheur

log = logging.getLogger("lexia")


class LimiteRequetes:
    """Fenetre glissante d'une minute par session, ou par adresse IP sans session (memoire du processus).

    Par IP seulement, une salle de TD derriere le wifi de la faculte (une seule adresse) partageait 10 questions
    par minute (audit du 19/11, SRV-6). Un etudiant connecte a sa propre limite ; un faux cookie n'apporte rien,
    la route refuse ensuite toute session inconnue avant d'appeler le modele."""

    def __init__(self, par_minute: int):
        self.par_minute = par_minute
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()
        self._derniere_purge = 0.0

    def __call__(self, request: Request) -> None:
        if self.par_minute <= 0:
            return
        session = request.cookies.get(COOKIE)
        # Empreinte du cookie, jamais le cookie lui-meme ; sinon reseau /64 en IPv6
        ip = "session:" + hashlib.sha256(session.encode()).hexdigest()[:32] if session else cle_ip(request)
        now = time.monotonic()
        with self._lock:
            if now - self._derniere_purge > 60:
                # Adresses vues il y a plus d'une minute oubliees : chaque adresse restait en memoire jusqu'au
                # redemarrage, des adresses tournantes faisaient grossir le processus (second audit, point 8).
                self._derniere_purge = now
                for k in [k for k, q in self._hits.items() if not q or now - q[-1] > 60]:
                    del self._hits[k]
            q = self._hits[ip]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= self.par_minute:
                raise HTTPException(429, "Trop de requêtes : réessayez dans une minute.")
            q.append(now)


def identite_vendeur(settings: Settings) -> str:
    """Bloc d'identite de la confirmation du contrat (C. consom. L. 221-5 et L. 221-13 ; audit JUR-8)."""
    legal = settings.legal
    lignes = [
        ("Vendeur", ", ".join(v for v in (legal.get("editeur"), legal.get("statut")) if v)),
        ("Adresse", legal.get("adresse", "")),
        ("Immatriculation", legal.get("siren", "")),
        ("E-mail", settings.contact_email),
        ("Téléphone", legal.get("telephone", "")),
        ("Médiateur de la consommation (recours gratuit)", legal.get("mediateur", "")),
    ]
    return "\n".join(f"{nom} : {valeur}" for nom, valeur in lignes if valeur)


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


def _construire_llm(settings: Settings, journal: Journal | None = None, **options) -> LLM:
    """options : max_jetons (resumes vocaux, plafond plus bas que les reponses)."""
    from api.llm.gemini import GeminiLLM

    # Groq configure : un seul tour de Gemini, borne dans le temps, puis le secours prend le relais.
    avec_secours = bool(settings.groq_api_key)
    return GeminiLLM(api_key=settings.gemini_api_key, models=settings.gemini_models,
                     thinking_level=settings.gemini_thinking_level, timeout=settings.llm_timeout,
                     releve=releve_jetons(journal, "generation"), tentatives=1 if avec_secours else 2,
                     budget=settings.budget_avant_secours if avec_secours else None, **options)


def _construire_secours(settings: Settings, journal: Journal | None = None, **options):
    if not settings.groq_api_key:
        return None
    from api.llm.groq import GroqLLM

    return GroqLLM(api_key=settings.groq_api_key, models=settings.groq_models, timeout=settings.llm_timeout,
                   releve=releve_jetons(journal, "secours"), **options)


def _construire_expanseur(settings: Settings, journal: Journal | None = None):
    if not settings.expansion_model:
        return None
    from api.expansion import Expanseur
    from api.llm.gemini import GeminiLLM

    # une tentative par modele (principal puis secours), tous dans le meme delai : la recherche n'attend pas
    # davantage, un second modele appele apres coup travaillerait pour rien (audit du 2026-11-18, D6)
    modeles = (settings.expansion_model, *settings.expansion_fallback_models)
    return Expanseur(GeminiLLM(api_key=settings.gemini_api_key, models=modeles,
                               thinking_level=settings.gemini_thinking_level,
                               timeout=settings.expansion_timeout, tentatives=1, budget=settings.expansion_timeout,
                               releve=releve_jetons(journal, "reformulation")))


def _construire_reclasseur(settings: Settings):
    if not settings.rerank_model:
        return None
    from api.rerank import CrossEncoderReclasseur

    return CrossEncoderReclasseur(settings.rerank_model)


def create_app(settings: Settings | None = None, *, retriever: Retriever | None = None,
               llm: LLM | None = None, journal: Journal | None = None, embedder=None,
               expanseur=None, reclasseur=None, comptes: Comptes | None = None, secours=None,
               client_stripe=None) -> FastAPI:
    settings = settings or get_settings()
    retriever = retriever or _construire_retriever(settings)
    journal = journal if journal is not None else Journal(settings.logs_dir)
    llm_fourni = llm is not None  # tests : le meme modele factice sert aussi aux resumes vocaux
    llm = llm or _construire_llm(settings, journal)
    if embedder is None:
        embedder = _construire_embedder(settings)  # charge le modele au demarrage (pas a la 1re question)
    if expanseur is None:
        expanseur = _construire_expanseur(settings, journal)
    if reclasseur is None:
        reclasseur = _construire_reclasseur(settings)
    if secours is None:
        secours = _construire_secours(settings, journal)
    lexia = Lexia(retriever, llm, journal, embedder, expanseur, reclasseur, delai_reformulation=settings.expansion_timeout,
                  secours=secours, disjoncteur=Disjoncteur(settings.disjoncteur_seuil, settings.disjoncteur_pause))
    quiz = QuizService(lexia, llm, journal=journal)
    limite = LimiteRequetes(settings.rate_limit_per_minute)
    # Les routes synchrones partagent 40 threads avec tout le site : quand Gemini est lent, chaque appel
    # en garde un jusqu'a ~100 s. Au-dela de ce plafond, reponse 503 immediate pour garder des threads libres.
    appels_modele = threading.BoundedSemaphore(max(1, settings.appels_modele_simultanes))

    # Documentation interactive (/docs, /openapi.json) : seulement si API_DOCS=1 (developpement). En production,
    # elle donnait a tout visiteur le plan complet des routes, administration comprise.
    docs = {} if settings.api_docs else {"docs_url": None, "redoc_url": None, "openapi_url": None}
    app = FastAPI(title="Lexia API", version="0.2.0", **docs,
                  description="Assistant d'étude en droit français : réponses fondées sur des sources officielles citées.")
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    # AI Act, art. 50.2 (marquage lisible par machine des textes generes ; echeance du 2 decembre 2026 pour un
    # systeme deja en ligne, reglement 2026/1744) : en-tete sur les reponses redigees par le modele. Moyen a
    # confirmer quand le code de bonne pratique de la Commission sera fixe (audit du 2026-11-18, E7).
    routes_generees = {"/chat", "/quiz", "/quiz/correct", "/resume-vocal"}

    @app.middleware("http")
    async def marquer_contenu_genere(request: Request, call_next):
        reponse = await call_next(request)
        route = request.scope.get("route")
        if reponse.status_code == 200 and getattr(route, "path", None) in routes_generees:
            reponse.headers["X-AI-Generated"] = "true"
        # Reponses JSON de l'API (profil, administration, cours) jamais gardees par le navigateur : un poste
        # partage les gardait sur disque (audit du 19/11, SEC-5). Pose ici plutot que dans nginx, ou un
        # add_header de location effacerait les en-tetes de securite du serveur.
        if (reponse.headers.get("content-type", "").startswith("application/json")
                and "cache-control" not in reponse.headers):
            reponse.headers["Cache-Control"] = "no-store"
        return reponse

    # --- comptes et quotas -------------------------------------------------------
    if settings.comptes_actifs and comptes is None:
        if not coffre.cle_configuree():
            log.warning("CLE_SECRETS absente : les secrets de double authentification restent en clair "
                        "dans la base. Ajoutez CLE_SECRETS au fichier .env (python -m api.admin cle).")
        comptes = Comptes(settings.app_db, admins=settings.admin_emails)
    utilisateur_requis = None
    cours = None
    if comptes is not None:
        routes_auth, utilisateur_requis = creer_routes(comptes, settings.inscriptions_par_ip_jour,
                                                       settings.url_publique)
        app.include_router(routes_auth, prefix="/auth")
        extras = {"embeddings": getattr(embedder, "model", None), "reclassement": getattr(reclasseur, "model", None)}
        app.include_router(creer_routes_admin(comptes, utilisateur_requis, journal, settings, retriever, extras),
                           prefix="/admin")

        def admin_requis(request: Request) -> Utilisateur:
            return exiger_admin(utilisateur_requis(request))

        quiz.store = QuizStore(chemin=comptes.chemin)  # questionnaires gardes au redemarrage (audit 2026-11-18, D5)
        cours = Cours(comptes.chemin, embedder)
        lexia.cours = cours
        app.include_router(creer_routes_cours(cours, utilisateur_requis))
        from api.export import creer_route_export

        app.include_router(creer_route_export(comptes, utilisateur_requis))   # RGPD art. 15 et 20 (JUR-11)
        # Cours de sites tiers sous licence libre : page a part, jamais dans les reponses (docs/cours-libres.md)
        catalogue = Catalogue(settings.cours_recuperes)
        app.include_router(creer_routes_cours_recuperes(catalogue, utilisateur_requis,
                                                     retriever))

        # Resumes vocaux (D106, docs/resumes-vocaux.md) : memes modeles et meme disjoncteur que les reponses,
        # plafond de jetons plus bas ; quota par jour a part.
        if llm_fourni:
            llm_resume, secours_resume = llm, secours
        else:
            llm_resume = _construire_llm(settings, journal, max_jetons=MAX_JETONS_RESUME)
            secours_resume = _construire_secours(settings, journal, max_jetons=MAX_JETONS_RESUME)
        lexia_resume = Lexia(retriever, llm_resume, journal, secours=secours_resume, disjoncteur=lexia.disjoncteur)
        app.include_router(creer_routes_resumes_vocaux(
            ResumesVocaux(lexia_resume, retriever, journal, cours, catalogue),
            QuotaResumes(comptes.chemin, settings.resumes_vocaux_par_jour), utilisateur_requis, limite,
            lambda action: _place_libre(action)))

        annales = Annales(comptes.chemin)
        routes_annales, admin_annales = creer_routes_annales(annales, admin_requis, journal)
        app.include_router(routes_annales)
        app.include_router(admin_annales, prefix="/admin")
    paiement_actif = bool(comptes is not None and settings.stripe_secret_key and settings.stripe_webhook_secret
                          and settings.url_publique)
    if paiement_actif:
        from api.paiement import Paiements, creer_routes_paiement

        app.include_router(creer_routes_paiement(
            Paiements(comptes), utilisateur_requis, verifier_origine, cle=settings.stripe_secret_key,
            secret_webhook=settings.stripe_webhook_secret, url_publique=settings.url_publique, journal=journal,
            client=client_stripe, admin_requis=admin_requis,
            vendeur=", ".join(v for v in (settings.legal.get("editeur"), settings.legal.get("adresse"),
                                          settings.contact_email) if v),
            identite=identite_vendeur(settings)), prefix="/paiement")
    app.include_router(routes_formules())

    def _utilisateur(request: Request) -> Utilisateur | None:
        return utilisateur_requis(request) if utilisateur_requis else None

    def _consommer(u: Utilisateur | None, type_: str) -> str | None:
        if u is None:
            return None
        jour = comptes.reserver(u, type_)
        if jour is None:
            f = u.formule
            limite = f.questions_par_jour if type_ == "questions" else f.quiz_par_jour
            quoi = "questions" if type_ == "questions" else "questionnaires"
            raise HTTPException(402, f"Limite du jour atteinte : {limite} {quoi} avec la formule {f.nom}. "
                                     "Elle se renouvelle à minuit, ou passez à une formule supérieure.")
        return jour

    def _place_libre(action):
        if not appels_modele.acquire(blocking=False):
            raise HTTPException(503, "Lexia est très sollicité : réessayez dans quelques instants.")
        try:
            return action()
        finally:
            appels_modele.release()

    def _avec_quota(u: Utilisateur | None, type_: str, action):
        """Decompte avant l'appel (limite atomique), rembourse si le modele n'a pas repondu (D32)."""
        if u is not None and not u.email_verifie:
            # Sans cette barriere, le quota gratuit se contourne en creant des comptes avec des
            # adresses inventees : seul l'envoi d'un e-mail prouve qu'une adresse existe.
            raise HTTPException(403, "Confirmez votre adresse e-mail pour poser des questions : "
                                     "le lien vous a été envoyé à l'inscription.")
        jour = _consommer(u, type_)
        try:
            res = action()
        except Exception:
            if u is not None:
                comptes.rembourser(u, type_, jour)  # le modele n'a pas repondu : pas decompte
            raise
        if u is not None and not res["controle"]["modele_appele"]:
            comptes.rembourser(u, type_, jour)  # aucun extrait trouve : le modele n'a pas ete appele
        elif u is not None and type_ == "quiz" and res.get("obtenu") == 0:
            # Aucune question verifiable : rien a faire pour l'etudiant, pas decompte (audit du 19/11, SRV-12).
            comptes.rembourser(u, type_, jour)
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
    def sante(request: Request):
        # Detail (modeles, etat du disjoncteur, taille de l'index) seulement depuis le serveur lui-meme
        # (publier.sh, verifications) : en public, il disait quels modeles viser et quand le secours etait
        # seul actif (audit du 2026-11-16, point 14). Derriere nginx, request.client est la vraie adresse
        # du visiteur (uvicorn --proxy-headers, --forwarded-allow-ips 127.0.0.1).
        # Fraicheur du corpus (audit B8) : en public, un booleen (derniere mise a jour reussie il y a moins de
        # 36 h ; la surveillance GitHub echoue sur false) ; la date, en local seulement.
        public = {"statut": "ok"}
        if (frais := fraicheur.a_jour(settings.index_dir.parent)) is not None:
            public["corpus_a_jour"] = frais
        if not request.client or request.client.host not in ("127.0.0.1", "::1"):
            return public
        maj = fraicheur.derniere_reussite(settings.index_dir.parent)
        return {**public, **retriever.stats(), "corpus_mis_a_jour_le": maj.isoformat() if maj else None,
                "modeles": list(settings.gemini_models),
                "secours": getattr(secours, "model", None),
                "disjoncteur": "ouvert" if secours is not None and lexia.disjoncteur.ouvert() else "ferme",
                "embeddings_modele": getattr(embedder, "model", None),
                "reformulation_modele": settings.expansion_model or None,
                "reclassement_modele": getattr(reclasseur, "model", None)}

    # Fraicheur des sources, affichee dans le site (audit B7) : date de la derniere archive LEGI lue pour les
    # textes, date de la decision la plus recente pour la jurisprudence. Recalculee au plus une fois par heure.
    fraicheur_cache: dict = {}

    @app.get("/fraicheur")
    def fraicheur_sources():
        if fraicheur_cache.get("expire", 0) < time.monotonic():
            textes = fraicheur.date_textes(settings.index_dir)
            dernieres = getattr(retriever, "dernieres_decisions", dict)()
            sources = {s: {"nom": NOMS.get(s, s), "date": d, "nature": "jurisprudence"} for s, d in dernieres.items()}
            if textes:
                sources |= {s: {"nom": NOMS[s], "date": textes, "nature": "textes"} for s in SOURCES_TEXTES
                            if s not in HORS_LEGI}   # Constitution (Conseil constitutionnel), traites (EUR-Lex)
            # Constitution, recuperee sur le site du Conseil constitutionnel : date de sa derniere lecture (SRC-5).
            constitution = (retriever.get("constitution_1958:preambule") or {}).get("date_recuperation") or ""
            if constitution[:4].isdigit():
                sources["constitution_1958"] = {"nom": NOMS["constitution_1958"], "date": constitution[:10],
                                                "nature": "textes"}
            fraicheur_cache.update(expire=time.monotonic() + 3600, valeur={"textes": textes, "sources": sources})
        return fraicheur_cache["valeur"]

    @app.get("/config")
    def config_publique():
        legal = {k: (v or None) if isinstance(v, str) else v for k, v in settings.legal.items()}
        return {"comptes": comptes is not None, "contact_email": settings.contact_email or None, "legal": legal,
                "paiement": paiement_actif}

    @app.get("/matieres")
    def matieres():
        # Annee, autres intitules et sources principales : classement et recherche du site (D97)
        return [{"id": m, "libelle": LIBELLES.get(m, m), "annee": MATIERES[m].annee, "mots": list(MATIERES[m].mots),
                 "principales": list(MATIERES[m].principales), "sources": list(s),
                 "noms_sources": {i: NOMS.get(i, i) for i in s}} for m, s in sources_par_matiere().items()]

    @app.post("/chat", dependencies=[Depends(verifier_origine), Depends(limite)])
    def chat(req: ChatRequest, request: Request):
        u = _utilisateur(request)
        _taille(req.question)
        _matiere(req.matiere)
        return _place_libre(lambda: _avec_quota(u, "questions",
                                                lambda: lexia.chat(req.question.strip(), req.mode, req.matiere,
                                                                   req.niveau, req.semestre, req.cours,
                                                                   req.avec_officiel, u.id if u else None)))

    @app.post("/quiz", dependencies=[Depends(verifier_origine), Depends(limite)])
    def creer_quiz(req: QuizRequest, request: Request):
        u = _utilisateur(request)
        _taille(req.theme)
        _matiere(req.matiere)
        return _place_libre(lambda: _avec_quota(
            u, "quiz", lambda: quiz.generer(req.theme.strip(), req.format, req.nombre, req.matiere,
                                      req.niveau, req.semestre, req.cours, req.avec_officiel,
                                      u.id if u else None)))

    @app.post("/quiz/correct", dependencies=[Depends(verifier_origine), Depends(limite)])
    def corriger_quiz(req: CorrectionRequest, request: Request):
        u = _utilisateur(request)
        res = _place_libre(lambda: quiz.corriger(req.quiz_id, [r.model_dump() for r in req.reponses],
                                                 u.id if u else None))
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

    @app.post("/feedback", status_code=204, dependencies=[Depends(verifier_origine), Depends(limite)])
    def feedback(req: FeedbackRequest, request: Request):
        # Compte a l'adresse confirmee et limite de debit : un compte jetable ecrivait des milliers de lignes
        # par minute et faussait les statistiques (second audit du 2026-11-16, point 14).
        u = _utilisateur(request)
        if u is not None and not u.email_verifie:
            raise HTTPException(403, "Confirmez votre adresse e-mail pour donner votre avis.")
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
