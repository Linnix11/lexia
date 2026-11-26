"""D140 : questionnaires plus justes et moins devinables. Choix du QCM melanges (9 bonnes reponses sur 10 en B le
26/11), une justification par choix rendue a la correction seulement, ancien numero du Code civil signale, notes
des anciens numeros et des grands arrets dans la consigne. Sans appel au modele."""

import random

from fastapi.testclient import TestClient

from api import concordance
from api.citations import Controle
from api.config import Settings
from api.main import create_app
from api.prompts import SCHEMAS_QUIZ, SYSTEME_QUIZ, prompt_quiz
from api.quiz import _melanger, _signaler_anciens, _valider_question
from api.rag import table_extraits
from api.retrieval.local import LocalRetriever
from tests.test_api import FakeLLM, index_dir  # noqa: F401  (fixture partagee)


def article(numero: str, texte: str) -> dict:
    return {"id": f"code_civil:{numero}", "source_id": "code_civil", "type": "article", "numero": numero,
            "entete": f"Code civil, article {numero}", "texte": texte, "url": "",
            "meta": {"en_vigueur": True, "date_debut": "2016-10-01"}}


ARRET_1382 = {"id": "cass:1", "source_id": "cass", "type": "decision", "numero": None,
              "entete": "Cour de cassation, Chambre civile 2, du 7 février 1964", "url": "", "meta": {},
              "texte": "Les juges ne peuvent fonder leur décision que sur les dispositions de l'article 1382 du code "
                       "civil lorsque les parties ne se réclament que de la responsabilité du fait personnel."}
A1240 = article("1240", "Tout fait quelconque de l'homme, qui cause à autrui un dommage, oblige celui par la faute "
                        "duquel il est arrivé à le réparer.")
QCM = {"question": "Paul blesse Marie par imprudence. Sur quel fondement agit-elle ?",
       "choix": ["La faute prouvée", "Le fait des choses", "Le contrat", "La garde d'autrui"], "bonne_reponse": 0,
       "explication": "La faute oblige à réparer.", "sources": ["S1"],
       "justifications": ["Juste : la faute oblige à réparer.", "Faux : aucune chose n'intervient.",
                          "Faux : aucun contrat entre eux.", "Faux : personne n'est gardé."]}


def test_consigne_exige_comprehension_distracteurs_et_justifications():
    assert "cas bref" in SYSTEME_QUIZ and "plausibles" in SYSTEME_QUIZ and "longueur voisine" in SYSTEME_QUIZ
    assert "justifications" in SCHEMAS_QUIZ["qcm"]["properties"]["questions"]["items"]["required"]
    assert "1382" in SYSTEME_QUIZ and "abandonné" in SYSTEME_QUIZ


def test_consigne_porte_les_notes_des_anciens_numeros_et_des_grands_arrets():
    p = prompt_quiz("l'article 1382", "vrai_faux", 5, [A1240], anciens={"1382": ("1240",)})
    assert "aujourd'hui à l'article 1240" in p
    arret = {**ARRET_1382, "grand_arret": {"citation": "Cass., ch. réunies, 13 février 1930, Jand'heur",
                                           "statut": "abandonne", "portee": "Portée."}}
    assert "ABANDONNÉ" in prompt_quiz("la garde", "qcm", 5, [arret])
    assert "Attention" not in prompt_quiz("la faute", "qcm", 5, [A1240])


def test_justifications_gardees_si_verifiables_sinon_question_sans_elles():
    table = table_extraits([A1240])
    v = _valider_question(QCM, "qcm", table, Controle())
    assert v["justifications"] == QCM["justifications"]
    # longueur differente du nombre de choix, ou article absent des extraits : justifications retirees seulement
    for justifs in (QCM["justifications"][:3], [*QCM["justifications"][:3], "Faux : voir l'article 1384."]):
        v = _valider_question({**QCM, "justifications": justifs}, "qcm", table, Controle())
        assert v is not None and "justifications" not in v


def test_choix_melanges_bonne_reponse_et_justifications_suivent():
    hasard = random.Random(3)
    q = {k: v for k, v in QCM.items()}
    places = set()
    for _ in range(40):
        m = _melanger(q, hasard)
        assert m["choix"][m["bonne_reponse"]] == "La faute prouvée"
        assert m["justifications"][m["bonne_reponse"]].startswith("Juste")
        assert sorted(m["choix"]) == sorted(q["choix"])
        places.add(m["bonne_reponse"])
    assert places == {0, 1, 2, 3}
    assert _melanger({"affirmation": "x", "reponse": True}, hasard) == {"affirmation": "x", "reponse": True}


def test_ancien_numero_signale_dans_le_corrige():
    q = {"affirmation": "Les juges peuvent retenir le fait des choses.", "reponse": False,
         "explication": "Ils ne peuvent statuer que sur l'article 1382 du Code civil.", "sources": [ARRET_1382["id"]]}
    out = _signaler_anciens(q, {ARRET_1382["id"]: ARRET_1382})
    assert out["explication"] == ("Ils ne peuvent statuer que sur l'article 1382 du Code civil "
                                  f"({concordance.MENTION}, aujourd'hui article 1240).")
    # le numero actuel deja donne : rien a ajouter
    q2 = {**q, "explication": "L'ancien article 1382, devenu 1240, exige une faute."}
    assert _signaler_anciens(q2, {ARRET_1382["id"]: ARRET_1382})["explication"] == q2["explication"]


def test_reperes_retires_du_texte():
    table = table_extraits([A1240])
    q = {**QCM, "explication": "La faute oblige à réparer (S1).",
         "justifications": ["Juste, l'extrait S1 le dit.", *QCM["justifications"][1:]]}
    v = _valider_question(q, "qcm", table, Controle())
    assert v["explication"] == "La faute oblige à réparer." and v["justifications"][0] == "Juste, l'extrait le dit."


def client_quiz(index_dir, tmp_path):  # noqa: F811
    llm = FakeLLM()
    app = create_app(Settings(gemini_models=("fake",), index_dir=index_dir, logs_dir=tmp_path / "logs",
                              rate_limit_per_minute=100, max_question_chars=500),
                     retriever=LocalRetriever(index_dir), llm=llm)
    return TestClient(app), llm


def test_bonnes_reponses_reparties_sur_les_quatre_places(index_dir, tmp_path):  # noqa: F811
    client, llm = client_quiz(index_dir, tmp_path)
    # le modele met toujours la bonne reponse en B, comme le 26/11
    llm.reponses.append({"questions": [{**QCM, "question": f"Question {n} sur l'article 1240 ?", "bonne_reponse": 1,
                                        "choix": ["Le fait des choses", "La faute prouvée", "Le contrat", f"Autre {n}"],
                                        "justifications": None} for n in range(8)]})
    data = client.post("/quiz", json={"theme": "article 1240 responsabilité", "format": "qcm", "nombre": 8}).json()
    assert data["obtenu"] == 8
    places = [q["choix"].index("La faute prouvée") for q in data["questions"]]
    assert sorted(places) == [0, 0, 1, 1, 2, 2, 3, 3]


def test_api_justifications_rendues_a_la_correction_seulement(index_dir, tmp_path):  # noqa: F811
    client, llm = client_quiz(index_dir, tmp_path)
    llm.reponses.append({"questions": [{**QCM, "explication": "L'article 1240 exige une faute."}]})
    data = client.post("/quiz", json={"theme": "article 1240 responsabilité", "format": "qcm", "nombre": 1}).json()
    assert data["obtenu"] == 1 and "justifications" not in data["questions"][0]
    choix = data["questions"][0]["choix"]
    faux = next(i for i, c in enumerate(choix) if c != "La faute prouvée")
    c = client.post("/quiz/correct", json={"quiz_id": data["quiz_id"], "reponses": [{"index": 0, "valeur": faux}]}).json()
    r = c["resultats"][0]
    assert r["statut"] == "incorrect" and choix[r["bonne_reponse"]] == "La faute prouvée"
    assert r["justifications"][r["bonne_reponse"]].startswith("Juste")
    assert r["justifications"][faux].startswith("Faux")
