"""Resumes vocaux : route reservee aux comptes, quota par jour, documents prives, controle des articles (D106)."""

import json

import pytest
from fastapi.testclient import TestClient

from api import resumes_vocaux as rv
from api.citations import Controle
from api.comptes import Comptes
from api.config import Settings
from api.llm.base import LLMError
from api.main import create_app
from tests.test_comptes import PASSAGE, Retriever, inscrire
from tests.test_cours import deposer
from tests.test_cours_recuperes import FACTICE, ecrire

PARAGRAPHE = ("La responsabilité du fait personnel repose sur l'article 1240 du Code civil : celui qui cause un "
              "dommage à autrui par sa faute doit le réparer. Il faut une faute, un dommage et un lien de causalité.")
RESUME = {"titre": "La responsabilité du fait personnel",
          "paragraphes": [PARAGRAPHE, "Selon l'article 9999 du Code civil, tout est permis.",
                          "À retenir : faute, dommage et lien de causalité [S1]."]}


class LLM:
    def __init__(self):
        self.echec = False
        self.reponse = RESUME
        self.appels = []

    def generate_json(self, *, system, prompt, **kw):
        if self.echec:
            raise LLMError("503")
        self.appels.append((system, prompt))
        return self.reponse, "fake"


@pytest.fixture
def env(tmp_path):
    llm = LLM()
    catalogue = tmp_path / "catalogue.json"
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0,
                              cours_recuperes=catalogue, resumes_vocaux_par_jour=2),
                     retriever=Retriever(), llm=llm, comptes=Comptes(tmp_path / "comptes.db"))
    return TestClient(app), llm, catalogue, tmp_path


def demande_reponse(**extra):
    return {"type": "reponse", "titre": "Responsabilité", "texte": "L'article 1240 du Code civil impose de réparer.",
            "sources": [PASSAGE["id"]], **extra}


def test_reserve_aux_comptes(env):
    client, llm, _, _ = env
    assert client.post("/resume-vocal", json=demande_reponse()).status_code == 401
    assert llm.appels == []


def test_resume_d_une_reponse_controle_et_avertissement(env):
    client, llm, _, tmp_path = env
    inscrire(client)
    r = client.post("/resume-vocal", json=demande_reponse())
    assert r.status_code == 200 and r.headers["X-AI-Generated"] == "true"
    res = r.json()
    # article 9999 absent du document : paragraphe retire ; repere [S1] retire du texte
    assert res["paragraphes"] == [PARAGRAPHE, "À retenir : faute, dommage et lien de causalité."]
    assert res["controle"]["elements_retires"] == 1 and "article 9999" in res["controle"]["references_non_verifiees"]
    assert res["avertissement"] == rv.AVERTISSEMENT and "erreurs" in res["avertissement"]
    assert res["mots"] > 40 and res["duree_estimee_s"] == round(res["mots"] * 60 / 150)
    assert res["restants"] == 1 and not res["partiel"]
    system, prompt = llm.appels[0]
    assert system == rv.prompts.SYSTEME_RESUME_VOCAL and "N'écris JAMAIS un numéro d'article" in system
    # l'extrait cite est relu par le serveur et envoye avec la reponse
    assert PASSAGE["texte"] in prompt and "L'article 1240 du Code civil impose" in prompt
    lignes = [json.loads(l) for l in (tmp_path / "logs" / "requetes.jsonl").read_text().splitlines()]
    assert lignes[-1]["route"] == "resume_vocal" and "paragraphes" not in lignes[-1]


def test_limite_du_jour_et_remboursement(env):
    client, llm, _, _ = env
    inscrire(client)
    llm.echec = True
    assert client.post("/resume-vocal", json=demande_reponse()).status_code == 503
    llm.echec = False
    llm.reponse = {"titre": "x", "paragraphes": ["Selon l'article 9999, rien."]}  # rien de verifiable
    r = client.post("/resume-vocal", json=demande_reponse()).json()
    assert r["paragraphes"] == [] and r["message"] and r["restants"] == 2  # rembourse
    llm.reponse = RESUME
    assert client.get("/resume-vocal/quota").json() == {"par_jour": 2, "restants": 2}
    for _ in range(2):
        assert client.post("/resume-vocal", json=demande_reponse()).status_code == 200
    r = client.post("/resume-vocal", json=demande_reponse())
    assert r.status_code == 402 and "2 résumés vocaux par jour" in r.json()["detail"]


def test_cours_depose_prive(env):
    client, llm, _, _ = env
    inscrire(client)
    cid = deposer(client).json()["id"]
    llm.reponse = {"titre": "Le dol", "paragraphes": [
        "Le dol est une manoeuvre destinée à tromper le cocontractant pour obtenir son consentement. "
        "Sa sanction est la nullité relative du contrat, ainsi que des dommages et intérêts. Retenez bien "
        "ces deux éléments : la manoeuvre et la sanction, qui reviennent souvent dans les sujets d'examen."]}
    r = client.post("/resume-vocal", json={"type": "cours", "id": str(cid)})
    assert r.status_code == 200 and r.json()["paragraphes"]
    assert "Le dol est une manoeuvre" in llm.appels[-1][1] and "cours déposé" in llm.appels[-1][1]
    # autre compte : introuvable, rien de decompte ni d'appel au modele
    client.post("/auth/deconnexion")
    inscrire(client, email="autre@exemple.fr")
    n = len(llm.appels)
    assert client.post("/resume-vocal", json={"type": "cours", "id": str(cid)}).status_code == 404
    assert client.post("/resume-vocal", json={"type": "cours", "id": "abc"}).status_code == 404
    assert len(llm.appels) == n and client.get("/resume-vocal/quota").json()["restants"] == 2


def test_cours_recupere(env):
    client, llm, catalogue, _ = env
    ecrire(catalogue, [FACTICE])
    inscrire(client)
    assert client.post("/resume-vocal", json={"type": "cours_recupere", "id": "absent"}).status_code == 404
    r = client.post("/resume-vocal", json={"type": "cours_recupere", "id": "cours-factice"})
    assert r.status_code == 200
    assert "Texte factice." in llm.appels[-1][1] and "sous licence libre" in llm.appels[-1][1]


def test_extrait_d_un_cours_d_un_autre_compte_ignore(env):
    client, llm, _, _ = env
    inscrire(client)
    r = client.post("/resume-vocal", json=demande_reponse(sources=["cours:1:1", "inconnu"]))
    assert r.status_code == 200 and PASSAGE["texte"] not in llm.appels[-1][1]


def test_entrees_bornees(env):
    client, _, _, _ = env
    inscrire(client)
    assert client.post("/resume-vocal", json=demande_reponse(texte="x" * 12_001)).status_code == 422
    assert client.post("/resume-vocal", json=demande_reponse(sources=[f"s{i}" for i in range(13)])).status_code == 422
    assert client.post("/resume-vocal", json={"type": "audio"}).status_code == 422
    assert client.post("/resume-vocal", json=demande_reponse(texte="  ")).status_code == 404


def test_document_long_borne_et_decoupe():
    morceaux = rv.decouper(("mot " * 20_000).strip(), "Cours")
    assert all(len(m["texte"]) <= rv.TAILLE_MORCEAU for m in morceaux)
    gardes, partiel = rv.borner(morceaux)
    assert partiel and sum(len(m["texte"]) for m in gardes) <= rv.MAX_CARACTERES_DOCUMENT
    assert rv.borner(morceaux[:2]) == (morceaux[:2], False)
    assert "seul son début est fourni" in rv.prompts.prompt_resume_vocal("cours", "T", gardes[:1], True)


def test_resume_coupe_a_800_mots():
    long = " ".join(["Une phrase de dix mots pour remplir le résumé ici."] * 100)  # 1 000 mots
    paragraphes = rv.nettoyer({"paragraphes": ["Court paragraphe d'annonce.", long]}, [], Controle())
    assert paragraphes == ["Court paragraphe d'annonce."]
    (seul,) = rv.nettoyer({"paragraphes": [long]}, [], Controle())
    assert len(seul.split()) <= rv.MAX_MOTS and seul.endswith(".")


def test_plafond_de_jetons_transmis_aux_modeles():
    from api.llm.gemini import GeminiLLM
    from api.llm.groq import GroqLLM

    g = GeminiLLM(api_key="k", models=("m",), max_jetons=rv.MAX_JETONS_RESUME)
    assert g._body("s", "p", {}, 0.2)["generationConfig"]["maxOutputTokens"] == rv.MAX_JETONS_RESUME < 4096
    assert GeminiLLM(api_key="k", models=("m",))._body("s", "p", {}, 0.2)["generationConfig"]["maxOutputTokens"] == 4096
    assert GroqLLM(api_key="k", models=("m",), max_jetons=rv.MAX_JETONS_RESUME)._max_jetons == rv.MAX_JETONS_RESUME
