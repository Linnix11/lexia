"""Faits racontes a la premiere personne : expliques ; seules les demandes de conseil sont refusees (D77)."""

import pytest

from api.conseil import demande_de_conseil
from api.prompts import NOTE_RELANCE_HORS_CHAMP
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
    # formulations que la detection ratait : la relance « hors champ » faisait alors rediger le document
    # (second audit du 2026-11-16, point 3)
    "Rédigez une mise en demeure pour mon voisin.",
    "Rédige une lettre de résiliation à mon bailleur.",
    "Faut-il que je porte plainte contre mon voisin ?",
    "Est-ce que je devrais signer cette rupture conventionnelle ?",
    "Écris un courrier de réclamation à mon opérateur.",
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
    "Rédige une fiche sur la mise en demeure.",
    "Rédige la réponse au cas pratique suivant : Paul vend sa voiture accidentée à Marie.",
    "Prépare un plan de dissertation sur la responsabilité du fait d'autrui.",
    "Dans quels cas faut-il porter plainte pour obtenir réparation ?",
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
    assert NOTE_RELANCE_HORS_CHAMP not in llm.prompts[0] and llm.prompts[1].endswith(NOTE_RELANCE_HORS_CHAMP)
    assert "professionnel" in data["points_incertains"][0]["texte"]


def test_second_refus_du_modele_garde(env):  # noqa: F811
    client, llm, _ = env
    llm.reponses += [REFUS, REFUS]
    q = "Mon voisin a abîmé ma voiture : que dit l'article 1240 du code civil ?"
    data = client.post("/chat", json={"question": q}).json()
    assert data["statut"] == "hors_champ" and len(llm.prompts) == 2


def test_note_de_relance_neutre():
    """Elle ne doit pas imposer de repondre : une demande de conseil ratee par la detection restait redigee."""
    assert "garde" in NOTE_RELANCE_HORS_CHAMP and "hors_champ" in NOTE_RELANCE_HORS_CHAMP
    assert "Ce n'est pas une demande de conseil" not in NOTE_RELANCE_HORS_CHAMP


def test_pas_de_relance_apres_une_premiere_reponse_lente(env, monkeypatch):  # noqa: F811
    """Une seconde generation apres une premiere lente depassait les 120 s de nginx (point 10)."""
    import api.rag as rag
    monkeypatch.setattr(rag, "DELAI_MAX_RELANCE", -1.0)
    client, llm, _ = env
    llm.reponses += [REFUS, REPONSE]
    q = "Le fils de mes voisins a tagué mon garage : l'article 1240 du code civil me permet-il de réclamer réparation ?"
    data = client.post("/chat", json={"question": q}).json()
    assert data["statut"] == "hors_champ" and len(llm.prompts) == 1


SANS_SOURCE = {"statut": "reponse", "titre": "Méthode", "droit_positif": [], "message": "", "points_incertains": [],
               "explication": [{"texte": "Qualifiez les faits, puis appliquez la règle.", "sources": [],
                                "rubrique": "Majeure"}]}


def test_methode_sans_source_relancee_une_fois(env):  # noqa: F811
    """Le secours rendait une methode sans source alors que les articles etaient dans les extraits."""
    from api.prompts import NOTE_RELANCE_SOURCES
    client, llm, _ = env
    llm.reponses += [SANS_SOURCE, REPONSE]
    data = client.post("/chat", json={"question": "article 1240 : mon voisin a cassé ma vitre", "mode": "cas_pratique"}).json()
    assert len(llm.prompts) == 2 and llm.prompts[1].endswith(NOTE_RELANCE_SOURCES)
    assert data["droit_positif"] and data["droit_positif"][0]["sources"]


def test_une_seule_relance_par_question(env):  # noqa: F811
    client, llm, _ = env
    llm.reponses += [REFUS, SANS_SOURCE, REPONSE]       # hors champ, puis sans source : pas de troisieme appel
    q = "Le fils de mes voisins a tagué mon garage : que dit l'article 1240 du code civil ?"
    client.post("/chat", json={"question": q, "mode": "cas_pratique"})
    assert len(llm.prompts) == 2
