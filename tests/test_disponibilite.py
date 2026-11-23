"""Modeles, disponibilite et quotas (audit du 23/11, lot A ; tests T1, T2, T4, T5, T6)."""

import threading
import time

import pytest
from fastapi.testclient import TestClient

from api import rerank
from api.cartes_mentales import CartesMentales, DemandeCarte
from api.comptes import Comptes
from api.config import Settings
from api.llm.base import LLMError
from api.main import create_app
from api.matieres import MATIERES
from api.quiz import QuizService
from api.rag import Disjoncteur, Lexia
from api.resumes_vocaux import QuotaResumes
from api.retrieval.base import Hit
from tests.test_secours import LLM, Retriever


class Horloge:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def _lexia(principal, secours, horloge, seuil=1):
    return Lexia(Retriever(), principal, secours=secours,
                 disjoncteur=Disjoncteur(seuil=seuil, pause=300, horloge=horloge))


def _panne_puis_retour(principal, lexia, horloge, appel):
    """Gemini en panne (disjoncteur ouvert), puis revenu ; la pause finie, `appel()` doit le rappeler."""
    principal.echec = True
    appel()
    assert lexia.disjoncteur.en_pause()
    principal.echec = False
    principal.prompts.clear()
    for i in range(3):                          # questions espacees de 400 s : la pause est finie a chaque fois
        horloge.t += 400
        appel()
    return len(principal.prompts)


# --- A1 / T1 : apres une panne, Gemini est rappele a la fin de la pause -------------------------------------

def test_t1_chat_rappelle_le_principal_apres_la_pause():
    horloge, principal, secours = Horloge(), LLM(echec=False), LLM(echec=False)
    lexia = _lexia(principal, secours, horloge)
    n = _panne_puis_retour(principal, lexia, horloge, lambda: lexia.chat(f"responsabilité {time.time()}", "expliquer", None))
    assert n == 3                               # avant : 0 (la recherche prenait l'essai, Groq repondait)
    assert not lexia.disjoncteur.en_pause()


def test_t1_quiz_rappelle_le_principal_apres_la_pause():
    horloge, principal, secours = Horloge(), LLM(echec=False), LLM(echec=False)
    lexia = _lexia(principal, secours, horloge)
    quiz = QuizService(lexia, principal)
    assert _panne_puis_retour(principal, lexia, horloge,
                              lambda: quiz.generer("responsabilité", "qcm", 3, None)) == 3


def test_t1_carte_d_une_matiere_rappelle_le_principal_apres_la_pause():
    horloge, principal, secours = Horloge(), LLM(echec=False), LLM(echec=False)
    lexia = _lexia(principal, secours, horloge)
    # Comme dans api/main.py : la carte a ses propres modeles mais le disjoncteur des questions
    lexia_carte = Lexia(Retriever(), principal, secours=secours, disjoncteur=lexia.disjoncteur)
    cartes = CartesMentales(lexia_carte, Retriever(), documents=None, chercheur=lexia)
    demande = DemandeCarte(type="matiere", matiere=next(iter(MATIERES)))
    assert _panne_puis_retour(principal, lexia, horloge, lambda: cartes.carte(demande, None)) == 3


def test_t1_sante_ne_prend_pas_l_essai():
    """/sante (verifications de publier.sh) lisait ouvert() et prenait l'essai de fin de pause."""
    horloge = Horloge()
    d = Disjoncteur(seuil=1, pause=300, horloge=horloge)
    d.echec()
    assert d.en_pause()
    horloge.t = 301
    assert not d.en_pause() and not d.en_pause()  # sans effet : l'essai reste a prendre
    assert not d.ouvert()                         # la premiere question le prend


# --- A2 / T2 : les appels a budget reduit n'ouvrent pas le disjoncteur des questions ----------------------

def test_t2_trois_cartes_ratees_n_ouvrent_pas_le_disjoncteur():
    horloge, principal, secours = Horloge(), LLM(echec=True), LLM(echec=False)
    lexia = _lexia(principal, secours, horloge, seuil=3)
    lexia_carte = Lexia(Retriever(), principal, secours=secours, disjoncteur=lexia.disjoncteur,
                        compter_echecs=False)
    for _ in range(3):
        lexia_carte.generer(system="s", construire=lambda ps: "p", passages=[], schema={})
    assert not lexia.disjoncteur.en_pause()
    principal.echec = False
    lexia.chat("responsabilité", "expliquer", None)
    assert len(principal.prompts) == 4          # la question essaie toujours Gemini


def test_t2_carte_ratee_a_la_fin_de_la_pause_rend_l_essai():
    horloge, principal, secours = Horloge(), LLM(echec=True), LLM(echec=False)
    lexia = _lexia(principal, secours, horloge)
    lexia_carte = Lexia(Retriever(), principal, secours=secours, disjoncteur=lexia.disjoncteur,
                        compter_echecs=False)
    lexia.generer(system="s", construire=lambda ps: "p", passages=[], schema={})
    horloge.t = 301
    lexia_carte.generer(system="s", construire=lambda ps: "p", passages=[], schema={})  # prend l'essai, echoue
    assert not lexia.disjoncteur.ouvert()       # une question peut faire l'essai tout de suite


def test_t2_cartes_ratees_par_la_route_n_ouvrent_pas_le_disjoncteur(tmp_path):
    from tests.test_comptes import Retriever as RetrieverComptes, inscrire
    principal, secours = LLM(echec=True), LLM(echec=False)
    comptes = Comptes(tmp_path / "c.db")
    app = create_app(Settings(gemini_models=("fake",), logs_dir=None, rate_limit_per_minute=0,
                              disjoncteur_seuil=2, cartes_mentales_par_jour=10, resumes_vocaux_par_jour=10),
                     retriever=RetrieverComptes(), llm=principal, secours=secours, comptes=comptes, journal=None)
    client = TestClient(app)
    assert inscrire(client).status_code == 201
    comptes.confirmer_email(comptes.par_email("etu@exemple.fr").id)
    for _ in range(3):
        assert client.post("/carte-mentale", json={"type": "matiere", "matiere": next(iter(MATIERES))}).status_code == 200
        assert client.post("/resume-vocal", json={"type": "reponse", "texte": "L'article 1240 du Code civil."}
                           ).status_code == 200
    assert len(principal.prompts) == 6                                  # Gemini essaye a chaque fois
    assert TestClient(app, client=("127.0.0.1", 50000)).get("/sante").json()["disjoncteur"] == "ferme"


# --- A3 / T4 : attente du reclassement bornee ----------------------------------------------------------------

class _CrossEncoder:
    def predict(self, paires, **kw):
        return [float(i) for i in range(len(paires))]


def _reclasseur():
    r = rerank.CrossEncoderReclasseur.__new__(rerank.CrossEncoderReclasseur)
    r.model, r._ce = "factice", _CrossEncoder()
    return r


def test_t4_semaphore_plein_la_question_n_attend_pas_plus_que_le_delai(monkeypatch):
    monkeypatch.setattr(rerank, "ATTENTE_MAX", 0.2)
    hits = [Hit({"id": str(i), "entete": "", "texte": "t"}, 1.0 - i / 10, {"lexical"}) for i in range(3)]
    for _ in range(rerank.RECLASSEMENTS_SIMULTANES):
        assert rerank._PLACES.acquire(timeout=1)
    try:
        debut = time.monotonic()
        res = _reclasseur().reordonner("q", hits)
        assert time.monotonic() - debut < 1.0
        assert [h.passage["id"] for h in res] == ["0", "1", "2"]     # ordre de la fusion garde
    finally:
        for _ in range(rerank.RECLASSEMENTS_SIMULTANES):
            rerank._PLACES.release()
    res = _reclasseur().reordonner("q", hits)                         # place libre : reclasse
    assert [h.passage["id"] for h in res] == ["2", "1", "0"] and "reclasse" in res[0].via


def test_t4_place_rendue_si_le_modele_leve():
    class Casse:
        def predict(self, *a, **kw):
            raise RuntimeError("modele")
    r = _reclasseur()
    r._ce = Casse()
    hits = [Hit({"id": "0", "entete": "", "texte": "t"}, 1.0, set())]
    for _ in range(rerank.RECLASSEMENTS_SIMULTANES + 1):
        with pytest.raises(RuntimeError):
            r.reordonner("q", hits)
    assert rerank._PLACES.acquire(timeout=0.1)
    rerank._PLACES.release()


# --- A4 / T5 : reponse du cache non decomptee -----------------------------------------------------------------

def test_t5_reponse_du_cache_non_decomptee(tmp_path):
    from tests.test_comptes import Retriever as RetrieverComptes, inscrire
    from tests.test_secours import REPONSE

    class Modele:
        def __init__(self):
            self.appels = 0

        def generate_json(self, **kw):
            self.appels += 1
            return REPONSE, "fake"

    comptes = Comptes(tmp_path / "c.db")
    modele = Modele()
    client = TestClient(create_app(Settings(gemini_models=("fake",), logs_dir=None, rate_limit_per_minute=0),
                                   retriever=RetrieverComptes(), llm=modele, comptes=comptes, journal=None))
    assert inscrire(client).status_code == 201
    comptes.confirmer_email(comptes.par_email("etu@exemple.fr").id)
    q = {"question": "Quelle est la responsabilité du fait personnel ?"}
    assert client.post("/chat", json=q).status_code == 200
    r = client.post("/chat", json=q).json()
    assert r["controle"]["cache"] is True and modele.appels == 1
    assert client.get("/auth/moi").json()["usage"]["questions"] == 1   # avant : 2


# --- A5 / T6 : quotas des resumes et cartes ---------------------------------------------------------------------

def test_t6_remboursement_apres_minuit_sur_le_jour_de_la_reservation(tmp_path, monkeypatch):
    from api import resumes_vocaux
    comptes = Comptes(tmp_path / "c.db")
    uid = comptes.creer("a@example.com", "motdepasse-long-1").id
    quota = QuotaResumes(comptes.chemin, 2)
    monkeypatch.setattr(resumes_vocaux, "_jour", lambda: "2026-11-23")
    jour = quota.reserver(uid)
    assert jour == "2026-11-23"
    monkeypatch.setattr(resumes_vocaux, "_jour", lambda: "2026-11-24")
    quota.rembourser(uid, jour)
    monkeypatch.setattr(resumes_vocaux, "_jour", lambda: "2026-11-23")
    assert quota.utilises(uid) == 0             # avant : 1 (rendu sur le 24)


def test_t6_vingt_reservations_simultanees_pour_une_limite_de_cinq(tmp_path):
    comptes = Comptes(tmp_path / "c.db")
    uid = comptes.creer("a@example.com", "motdepasse-long-1").id
    quota = QuotaResumes(comptes.chemin, 5, table="cartes_mentales")
    depart, resultats = threading.Barrier(20), []

    def reserver():
        depart.wait()
        resultats.append(quota.reserver(uid))
    fils = [threading.Thread(target=reserver) for _ in range(20)]
    for f in fils:
        f.start()
    for f in fils:
        f.join()
    assert sum(1 for r in resultats if r) == 5 and quota.utilises(uid) == 5


# --- A6 : /feedback a sa propre limite par minute -----------------------------------------------------------------

def test_a6_avis_ne_consomment_pas_la_limite_des_questions():
    principal = LLM(echec=False)
    client = TestClient(create_app(Settings(gemini_models=("fake",), logs_dir=None, rate_limit_per_minute=3),
                                   retriever=Retriever(), llm=principal, secours=None, journal=None))
    for _ in range(3):
        assert client.post("/feedback", json={"reponse_id": "reponse-1", "utile": True}).status_code == 204
    assert client.post("/feedback", json={"reponse_id": "reponse-1", "utile": True}).status_code == 429
    assert client.post("/chat", json={"question": "responsabilité"}).status_code == 200   # avant : 429
