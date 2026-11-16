"""Faits racontes a la premiere personne : expliques ; seules les demandes de conseil sont refusees (D77)."""

import pytest

from api.conseil import demande_de_conseil
from api.prompts import NOTE_PAS_UN_CONSEIL
from tests.test_api import FakeLLM, env, index_dir  # noqa: F401  (fixtures partagees)


@pytest.mark.parametrize("question", [
    "Mon employeur m'a licencié hier sans motif, est-ce que je vais gagner aux prud'hommes ?",
    "Mon voisin a abîmé ma voiture, combien puis-je lui réclamer ?",
    "J'ai reçu une amende, rédige-moi une contestation à envoyer.",
    "Écrivez-moi la lettre de mise en demeure pour mon garagiste.",
    "Je veux rompre mon PACS demain, quelles démarches dois-je faire pour moi ?",
    "Mon propriétaire refuse de me rendre ma caution, que dois-je faire ?",
    "Mon patron m'a mis à pied sans explication, ai-je des chances aux prud'hommes ?",
    "Combien vais-je toucher d'indemnités après mon licenciement ?",
    "Mon assureur refuse de payer, dois-je porter plainte ?",
])
def test_demandes_de_conseil_reconnues(question):
    assert demande_de_conseil(question)


@pytest.mark.parametrize("question", [
    "Le fils de quinze ans de mes voisins a tagué la façade de mon garage. À qui puis-je réclamer le nettoyage ?",
    "Mon terrain n'a aucun accès à la route. Puis-je passer chez mon voisin pour y accéder ?",
    "J'ai acheté un téléphone qui ne s'allume plus au bout de trois jours. Le vendeur doit-il le reprendre ?",
    "Je me suis fait agresser et j'ai frappé mon agresseur. Est-ce de la légitime défense ?",
    "Combien de temps puis-je contester une décision administrative ?",
    "Combien d'années faut-il pour devenir propriétaire par prescription ?",
    "Comment rédiger une mise en demeure ?",
    "Qu'est-ce que le dol ?",
])
def test_faits_et_questions_de_cours_ne_sont_pas_des_conseils(question):
    assert not demande_de_conseil(question)


REPONSE = {"statut": "reponse", "titre": "Responsabilité pour faute",
           "droit_positif": [{"texte": "Tout fait quelconque de l'homme qui cause un dommage oblige à le réparer.",
                              "sources": ["S1"]}],
           "explication": [], "message": "",
           "points_incertains": [{"texte": "Analyse générale : consultez un professionnel du droit.", "sources": []}]}
REFUS = {"statut": "hors_champ", "titre": "", "droit_positif": [], "explication": [],
         "points_incertains": [], "message": ""}


def test_demande_de_conseil_refusee_sans_appel_au_modele(env):  # noqa: F811
    client, llm, _ = env
    data = client.post("/chat", json={"question": "Mon voisin a abîmé ma voiture, combien puis-je lui réclamer ?"}).json()
    assert data["statut"] == "hors_champ" and "professionnel" in data["message"] and llm.prompts == []


def test_faits_refuses_par_le_modele_sont_relances_une_fois(env):  # noqa: F811
    client, llm, _ = env
    llm.reponses += [REFUS, REPONSE]
    q = "Le fils de mes voisins a tagué mon garage : l'article 1240 du code civil me permet-il de réclamer réparation ?"
    data = client.post("/chat", json={"question": q}).json()
    assert data["statut"] == "reponse" and len(llm.prompts) == 2
    assert NOTE_PAS_UN_CONSEIL not in llm.prompts[0] and llm.prompts[1].endswith(NOTE_PAS_UN_CONSEIL)
    assert "professionnel" in data["points_incertains"][0]["texte"]


def test_second_refus_du_modele_garde(env):  # noqa: F811
    client, llm, _ = env
    llm.reponses += [REFUS, REFUS]
    q = "Mon voisin a abîmé ma voiture : que dit l'article 1240 du code civil ?"
    data = client.post("/chat", json={"question": q}).json()
    assert data["statut"] == "hors_champ" and len(llm.prompts) == 2
