"""Cartes mentales : route reservee aux comptes, quota par jour, schema, controle des feuilles, liens (D112)."""

import json

import pytest
from fastapi.testclient import TestClient

from api import cartes_mentales as cm
from api.citations import Controle
from api.comptes import Comptes
from api.config import Settings
from api.llm.base import LLMError
from api.llm.forme import conforme
from api.main import create_app
from tests.test_comptes import PASSAGE, Retriever, inscrire
from tests.test_cours import deposer
from tests.test_cours_recuperes import FACTICE, ecrire

CARTE = {"titre": "Responsabilité du fait personnel [S1]",
         "branches": [
             {"libelle": "Fondement", "articles": ["article 1240 du Code civil", "article 9999 du Code civil",
                                                   "une faute"],
              "enfants": [{"libelle": "Faute prouvée", "articles": []},
                          {"libelle": "Selon l'article 8888, tout", "articles": []}]},
             {"libelle": "Conditions", "articles": [], "enfants": [
                 {"libelle": "Dommage", "articles": ["art. 1240 C. civ."]},
                 {"libelle": "Lien de causalité", "articles": []}]},
             {"libelle": "Article 7777 du Code civil", "articles": [], "enfants": []},
         ]}


class LLM:
    def __init__(self):
        self.echec = False
        self.reponse = CARTE
        self.appels = []

    def generate_json(self, *, system, prompt, schema, **kw):
        if self.echec:
            raise LLMError("503")
        self.appels.append((system, prompt, schema))
        return self.reponse, "fake"


@pytest.fixture
def env(tmp_path):
    llm = LLM()
    catalogue = tmp_path / "catalogue.json"
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0,
                              cours_recuperes=catalogue, cartes_mentales_par_jour=2),
                     retriever=Retriever(), llm=llm, comptes=Comptes(tmp_path / "comptes.db"))
    return TestClient(app), llm, catalogue, tmp_path


def demande_reponse(**extra):
    return {"type": "reponse", "titre": "Responsabilité",
            "texte": "L'article 1240 du Code civil impose de réparer le dommage causé par sa faute.",
            "sources": [PASSAGE["id"]], **extra}


def test_reserve_aux_comptes(env):
    client, llm, _, _ = env
    assert client.post("/carte-mentale", json=demande_reponse()).status_code == 401
    assert client.get("/carte-mentale/quota").status_code == 401
    assert llm.appels == []


def test_carte_d_une_reponse_controlee_avec_liens(env):
    client, llm, _, tmp_path = env
    inscrire(client)
    r = client.post("/carte-mentale", json=demande_reponse())
    assert r.status_code == 200 and r.headers["X-AI-Generated"] == "true"
    res = r.json()
    assert res["titre"] == "Responsabilité du fait personnel"   # repere S1 retire
    # branche dont le libelle cite un article absent : retiree ; sous-branche idem
    assert [b["libelle"] for b in res["branches"]] == ["Fondement", "Conditions"]
    fondement, conditions = res["branches"]
    assert [e["libelle"] for e in fondement["enfants"]] == ["Faute prouvée"]
    # feuilles : seulement des references presentes dans les extraits ; « une faute » n'en est pas une
    assert [a["texte"] for a in fondement["articles"]] == ["article 1240 du Code civil"]
    assert fondement["articles"][0]["lien"] == {"url": PASSAGE["url"], "entete": PASSAGE["entete"]}
    assert conditions["enfants"][0]["articles"][0]["lien"]["url"] == PASSAGE["url"]
    assert res["controle"]["elements_retires"] == 2 and res["controle"]["citations_retirees"] == 2
    assert {"article 9999", "article 8888", "article 7777"} <= set(res["controle"]["references_non_verifiees"])
    assert res["avertissement"] == cm.AVERTISSEMENT and "vérifiez avec les textes" in res["avertissement"]
    assert res["restants"] == 1 and not res["partiel"]
    system, prompt, schema = llm.appels[0]
    assert system == cm.prompts.SYSTEME_CARTE_MENTALE and "N'écris JAMAIS une référence absente" in system
    assert schema is cm.prompts.SCHEMA_CARTE_MENTALE
    assert PASSAGE["texte"] in prompt and "L'article 1240 du Code civil impose" in prompt
    lignes = [json.loads(l) for l in (tmp_path / "logs" / "requetes.jsonl").read_text().splitlines()]
    assert lignes[-1]["route"] == "carte_mentale" and lignes[-1]["liens"] == 2 and "branches" in lignes[-1]
    assert not any("Fondement" in json.dumps(l) for l in lignes)   # aucun texte de la carte dans le journal


def test_limite_du_jour_et_remboursement(env):
    client, llm, _, _ = env
    inscrire(client)
    llm.echec = True
    assert client.post("/carte-mentale", json=demande_reponse()).status_code == 503
    llm.echec = False
    llm.reponse = {"titre": "x", "branches": [{"libelle": "Seule branche", "articles": [], "enfants": []}]}
    r = client.post("/carte-mentale", json=demande_reponse()).json()
    assert r["branches"] == [] and r["message"] and r["restants"] == 2   # moins de 2 branches : rembourse
    llm.reponse = CARTE
    assert client.get("/carte-mentale/quota").json() == {"par_jour": 2, "restants": 2}
    for _ in range(2):
        assert client.post("/carte-mentale", json=demande_reponse()).status_code == 200
    r = client.post("/carte-mentale", json=demande_reponse())
    assert r.status_code == 402 and "2 cartes mentales par jour" in r.json()["detail"]
    # quota a part de celui des resumes vocaux
    assert client.get("/resume-vocal/quota").json()["restants"] == 5


def test_cours_depose_prive(env):
    client, llm, _, _ = env
    inscrire(client)
    cid = deposer(client).json()["id"]
    llm.reponse = {"titre": "Le dol", "branches": [
        {"libelle": "Définition", "articles": [], "enfants": [{"libelle": "Manoeuvre", "articles": []}]},
        {"libelle": "Sanction", "articles": [], "enfants": []}]}
    r = client.post("/carte-mentale", json={"type": "cours", "id": str(cid)})
    assert r.status_code == 200 and len(r.json()["branches"]) == 2
    assert "Le dol est une manoeuvre" in llm.appels[-1][1] and "cours déposé" in llm.appels[-1][1]
    client.post("/auth/deconnexion")
    inscrire(client, email="autre@exemple.fr")
    n = len(llm.appels)
    assert client.post("/carte-mentale", json={"type": "cours", "id": str(cid)}).status_code == 404
    assert len(llm.appels) == n and client.get("/carte-mentale/quota").json()["restants"] == 2


def test_fiche_recuperee(env):
    client, llm, catalogue, _ = env
    ecrire(catalogue, [FACTICE])
    inscrire(client)
    assert client.post("/carte-mentale", json={"type": "cours_recupere", "id": "absent"}).status_code == 404
    r = client.post("/carte-mentale", json={"type": "cours_recupere", "id": "cours-factice"})
    assert r.status_code == 200
    assert "Texte factice." in llm.appels[-1][1] and "fiche récupérée" in llm.appels[-1][1]


def test_matiere_et_notion(env):
    client, llm, _, _ = env
    inscrire(client)
    assert client.post("/carte-mentale", json={"type": "matiere", "matiere": "inconnue"}).status_code == 404
    assert llm.appels == [] and client.get("/carte-mentale/quota").json()["restants"] == 2
    r = client.post("/carte-mentale", json={"type": "matiere", "matiere": "droit_civil",
                                            "notion": "responsabilité  civile"})
    assert r.status_code == 200 and r.json()["branches"]
    prompt = llm.appels[-1][1]
    assert "responsabilité civile (Droit civil)" in prompt and "extraits officiels" in prompt
    assert PASSAGE["texte"] in prompt
    assert client.post("/carte-mentale", json={"type": "matiere", "matiere": "droit_civil",
                                               "notion": "x" * 121}).status_code == 422


def test_entrees_bornees(env):
    client, _, _, _ = env
    inscrire(client)
    assert client.post("/carte-mentale", json=demande_reponse(texte="x" * 12_001)).status_code == 422
    assert client.post("/carte-mentale", json=demande_reponse(sources=[f"s{i}" for i in range(13)])).status_code == 422
    assert client.post("/carte-mentale", json={"type": "image"}).status_code == 422
    assert client.post("/carte-mentale", json=demande_reponse(texte="  ")).status_code == 404


def test_bornes_de_la_carte():
    passages = [PASSAGE]
    brut = {"branches": [{"libelle": f"Branche {i}", "articles": ["article 1240 du Code civil"] * 5 + [
        "article 1240", "Code civil, art. 1240", "art. 1240 du Code civil", "article 1240 C. civ."],
        "enfants": [{"libelle": f"Sous {j}", "articles": []} for j in range(9)]} for i in range(10)]}
    branches = cm.nettoyer(brut, passages, Controle())
    assert len(branches) == cm.MAX_BRANCHES
    assert all(len(b["enfants"]) == cm.MAX_ENFANTS for b in branches)
    # le meme article, quelle que soit son ecriture : une seule feuille (D138)
    assert all([a["texte"] for a in b["articles"]] == ["article 1240 du Code civil"] for b in branches)
    plusieurs = [{**PASSAGE, "id": f"code_civil:A{n}", "numero": str(n)} for n in range(1240, 1246)]
    noeud = cm.nettoyer({"branches": [{"libelle": "B", "enfants": [],
                                       "articles": [f"article {n} du Code civil" for n in range(1240, 1246)]}]},
                        plusieurs, Controle())[0]
    assert len(noeud["articles"]) == cm.MAX_ARTICLES                     # coupe a 3
    long = cm._libelle("**Mot** " * 60 + ".")
    assert len(long) <= cm.MAX_LIBELLE + 1 and "*" not in long and long.endswith("…")
    # objets hors forme : ignores sans erreur
    assert cm.nettoyer({"branches": ["texte", {"libelle": "", "articles": []}]}, passages, Controle()) == []


def test_schema_strict_et_forme():
    schema = cm.prompts.SCHEMA_CARTE_MENTALE
    assert conforme(CARTE, schema)
    assert not conforme({"titre": "t", "branches": ["texte"]}, schema)
    assert not conforme({"titre": "t", "branches": [{"libelle": "b", "articles": "art. 1", "enfants": []}]}, schema)
    assert not conforme({"titre": "t", "branches": [{"libelle": "b", "articles": [], "enfants": [["x"]]}]}, schema)


def test_lien_cherche_dans_l_index_par_code_et_numero():
    class Index:
        def __init__(self):
            self.demandes = []

        def versions(self, source, numero):
            self.demandes.append((source, numero))
            if numero == "R*421-1":
                return [{"url": "https://legifrance/ancien", "meta": {"en_vigueur": False}},
                        {"url": "https://legifrance/fini", "meta": {"en_vigueur": True, "date_fin": "2001-01-01"}},
                        {"url": "https://legifrance/r421", "entete": "Code de l'urbanisme, article R*421-1",
                         "meta": {"en_vigueur": True}}]
            return []

    index = Index()
    service = cm.CartesMentales(None, index, None)
    lien = service.lien("article R. 421-1 du code de l'urbanisme", [])
    assert lien["url"] == "https://legifrance/r421"
    assert ("code_urbanisme", "R*421-1") in index.demandes
    # sans code nomme ni extrait : pas de lien, et l'index n'est pas interroge
    index.demandes.clear()
    assert service.lien("article 12", []) is None and index.demandes == []
    # decision du Conseil constitutionnel : extrait fourni qui la porte
    decision = {"url": "https://cc/2023-1075", "entete": "Décision 2023-1075 QPC",
                "meta": {"numero": "2023-1075", "nature": "QPC"}}
    assert service.lien("décision n° 2023-1075 QPC", [decision])["url"] == "https://cc/2023-1075"


def test_bornes_de_jetons_et_de_duree():
    from api.llm.gemini import GeminiLLM
    from api.main import _construire_llm, _construire_secours

    settings = Settings(gemini_api_key="k", gemini_models=("m",), groq_api_key="g", cartes_mentales_delai=25.0)
    g = _construire_llm(settings, max_jetons=cm.MAX_JETONS_CARTE, delai=settings.cartes_mentales_delai)
    assert isinstance(g, GeminiLLM) and g._timeout == 25.0 and g._budget == 25.0
    assert g._body("s", "p", {}, 0.2)["generationConfig"]["maxOutputTokens"] == cm.MAX_JETONS_CARTE < 4096
    s = _construire_secours(settings, max_jetons=cm.MAX_JETONS_CARTE, delai=settings.cartes_mentales_delai)
    assert s._timeout == 25.0 and s._max_jetons == cm.MAX_JETONS_CARTE
    # reponses : inchangees
    assert _construire_llm(settings)._timeout == settings.llm_timeout


# --- Revue du 26/11 (D138) : grands arrets, statut, doublons, caracteres de controle ---------------------------

def _passage_grand_arret(ident: str, **champs) -> dict:
    from api import grands_arrets
    a = grands_arrets.registre().arrets[ident]
    p = grands_arrets.passage_fiche(a) if a.fiche else {
        "id": a.index, "source_id": a.index.split(":")[0], "type": "decision", "numero": None,
        "entete": f"Décision {a.reference}", "texte": "Sommaire.", "url": f"https://officiel/{ident}",
        "meta": {"numeros_pourvoi": [a.reference]}, **champs}
    return grands_arrets.marquer(p, a, ajoute=True)


def test_grand_arret_en_feuille_citation_d_usage_et_statut():
    """Carte reelle « imprevision » (Gemini, 26/11) : les feuilles « Fiche Lexia (non officielle) : Cass. civ.,
    6 mars 1876, Canal de Craponne » et l'en-tete recopie de Gaz de Bordeaux (150 caracteres, nom coupe a 120)
    etaient retirees ; l'arret abandonne n'etait signale nulle part."""
    craponne = _passage_grand_arret("canal-de-craponne")
    gaz = _passage_grand_arret("gaz-de-bordeaux", entete="Conseil d'Etat, du 30 mars 1916, 59928")
    brut = {"branches": [
        {"libelle": "Refus historique de la révision (Canal de Craponne)", "enfants": [], "articles": [
            "Fiche Lexia (non officielle) : Cass. civ., 6 mars 1876, Canal de Craponne"]},
        {"libelle": "Droit administratif", "enfants": [], "articles": [
            "Conseil d'Etat, du 30 mars 1916, 59928, publié au recueil Lebon (grand arrêt : CE, 30 mars 1916, "
            "Compagnie générale d'éclairage de Bordeaux (Gaz de Bordeaux))"]}]}
    controle = Controle()
    refus, admin = cm.nettoyer(brut, [PASSAGE, craponne, gaz], controle)
    assert refus["libelle"] == ("Refus historique de la révision (Canal de Craponne) "
                                "(arrêt abandonné : n'est plus le droit positif)")
    assert refus["articles"] == [{"texte": "Cass. civ., 6 mars 1876, Canal de Craponne (arrêt abandonné : n'est plus "
                                           "le droit positif)", "arret": "canal-de-craponne", "statut": "abandonne"}]
    assert admin["articles"][0]["texte"] == ("CE, 30 mars 1916, Compagnie générale d'éclairage de Bordeaux "
                                             "(Gaz de Bordeaux)")
    assert "statut" not in admin["articles"][0] and controle.citations_retirees == 0
    # liens : decision officielle fournie ; une fiche Lexia n'a pas d'adresse
    service = cm.CartesMentales(None, Retriever(), None)
    assert service.lien_arret("gaz-de-bordeaux", [gaz])["url"] == "https://officiel/gaz-de-bordeaux"
    assert service.lien_arret("canal-de-craponne", [craponne]) is None


def test_arret_abandonne_par_son_pourvoi_et_arret_absent_des_extraits():
    desmares = _passage_grand_arret("desmares")
    brut = {"branches": [
        {"libelle": "Faute de la victime", "enfants": [],
         "articles": ["Cass. civ. 2e, 21 juillet 1982, pourvoi 81-12.850"]},
        {"libelle": "Garde", "enfants": [], "articles": ["arrêt Franck"]}]}   # Franck : pas parmi les extraits
    controle = Controle()
    victime, garde = cm.nettoyer(brut, [PASSAGE, desmares], controle)
    assert victime["articles"][0]["texte"].startswith("Cass. civ. 2e, 21 juillet 1982")
    assert victime["articles"][0]["texte"].endswith("(arrêt abandonné : n'est plus le droit positif)")
    assert victime["articles"][0]["statut"] == "abandonne"
    assert garde["articles"] == [] and controle.citations_retirees == 1
    # arret nomme par le document lui-meme (cours depose) : garde, avec son statut
    cours = {"id": "document:1", "source_id": "document", "texte": "L'arrêt Desmares de 1982 a été abandonné en 1987."}
    feuille = cm.nettoyer({"branches": [{"libelle": "X", "enfants": [], "articles": ["arrêt Desmares"]}]},
                          [cours], Controle())
    assert feuille[0]["articles"][0]["texte"] == ("Cass. civ. 2e, 21 juillet 1982, Desmares "
                                                  "(arrêt abandonné : n'est plus le droit positif)")


def test_reference_de_la_branche_pas_repetee_dessous_et_caracteres_de_controle():
    """Carte reelle « promesse unilaterale » : l'article 1124 sous la branche et sous ses deux sous-idees ;
    carte « fait des choses » : « LOI n\\x00 85-677 »."""
    brut = {"branches": [
        {"libelle": "Régime", "articles": ["Code civil, article 1240"], "enfants": [
            {"libelle": "Option", "articles": ["article 1240 du Code civil"]},
            {"libelle": "Sanc\x00tion", "articles": ["art. 1240 C. civ."]}]},
        {"libelle": "Effets", "articles": [], "enfants": [
            {"libelle": "Lésion", "articles": ["article 1240 du Code civil"]}]}]}
    regime, effets = cm.nettoyer(brut, [PASSAGE], Controle())
    assert [a["texte"] for a in regime["articles"]] == ["Code civil, article 1240"]
    assert [e["articles"] for e in regime["enfants"]] == [[], []]
    assert regime["enfants"][1]["libelle"] == "Sanc tion"
    assert cm._libelle("LOI n\x00 85-677 du 5 juillet 1985, article 1") == "LOI n° 85-677 du 5 juillet 1985, article 1"
    assert effets["enfants"][0]["articles"][0]["texte"] == "article 1240 du Code civil"   # autre branche : garde
