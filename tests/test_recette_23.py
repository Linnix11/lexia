"""Recette du 23/11 : drapeau « partiel » des resumes vocaux et cartes mentales (R-4), anciens numeros et articles
hors sujet dans les cartes mentales (R-5)."""

from api import cartes_mentales as cm
from api import resumes_vocaux as rv
from api.citations import Controle
from api.rag import pour_secours

REPONSE = ("Droit positif : la victime d'un dommage peut agir sur le fondement de l'article 1240 du Code civil "
           "(ancien article 1382). Le gardien de la chose répond du dommage (ancien article 1384).")


def extrait(i: int, numero: str | None, texte: str, source_id: str = "extrait") -> dict:
    entete = f"Code civil, article {numero}" if numero else f"Cour de cassation, décision {i}"
    return {**rv._morceau(texte, entete, i, source_id), "numero": numero, "meta": {}}


EXTRAITS = [extrait(0, "1240", "Tout fait quelconque de l'homme, qui cause à autrui un dommage, oblige..."),
            extrait(1, "1241", "Chacun est responsable du dommage qu'il a causé non seulement par son fait..."),
            extrait(2, "1242", "On est responsable non seulement du dommage que l'on cause par son propre fait..."),
            extrait(3, None, "Attendu que la cour d'appel a fait application des articles 1733 et 1734 du code "
                             "civil relatifs à l'incendie dans les lieux loués..."),
            extrait(4, None, "Attendu que le gardien de la chose..."),
            extrait(5, None, "Attendu que la faute de la victime...")]


class LexiaSecours:
    """Gemini sature : le secours ne recoit que les premiers morceaux (rag.pour_secours), comme pendant la recette."""

    def __init__(self, brut: dict):
        self.brut = brut

    def generer(self, *, system, construire, passages, schema, temperature):
        envoyes = pour_secours(passages)
        construire(envoyes)
        return self.brut, "groq", envoyes


RESUME = {"titre": "Responsabilité", "paragraphes": [
    "La victime agit sur le fondement de l'article 1240 du Code civil : faute, dommage et lien de causalité. " * 3]}


def test_r4_reponse_courte_avec_le_secours_pas_partielle():
    morceaux = rv.decouper(REPONSE, "Réponse de Lexia") + EXTRAITS
    d = rv.DemandeResume(type="reponse", titre="Responsabilité", texte=REPONSE, sources=["x"])
    res = rv.ResumesVocaux(LexiaSecours(RESUME), None).resumer(d, "Responsabilité", morceaux)
    assert res["paragraphes"] and res["partiel"] is False


def test_r4_document_long_avec_le_secours_partiel():
    morceaux = rv.decouper("Une phrase du cours sur la responsabilité civile. " * 400, "Cours")
    assert len(morceaux) > 4
    d = rv.DemandeResume(type="cours", id="1")
    assert rv.ResumesVocaux(LexiaSecours(RESUME), None).resumer(d, "Cours", morceaux)["partiel"] is True
    assert rv.document_partiel(morceaux, morceaux[:4]) and not rv.document_partiel(morceaux, morceaux)


def test_r4_carte_d_une_reponse_avec_le_secours_pas_partielle():
    brut = {"titre": "Responsabilité", "branches": [
        {"libelle": "Fait personnel", "articles": ["Article 1240 du Code civil"], "enfants": []},
        {"libelle": "Fait des choses", "articles": ["Article 1242 du Code civil"], "enfants": []}]}
    morceaux = rv.decouper(REPONSE, "Réponse de Lexia") + EXTRAITS

    class Index:
        def versions(self, code, numero):
            return []

    carte = cm.CartesMentales(LexiaSecours(brut), Index(), None).carte(cm.DemandeCarte(type="reponse"),
                                                                       ("Responsabilité", morceaux))
    assert carte["branches"] and carte["partiel"] is False


def test_r5_ancien_numero_signale_et_article_cite_par_un_arret_seulement_retire():
    envoyes = rv.decouper(REPONSE, "Réponse de Lexia") + EXTRAITS
    brut = {"branches": [{"libelle": "Responsabilité du fait personnel", "enfants": [],
                          "articles": ["Article 1382", "Article 1240 du Code civil", "Articles 1733 et 1734"]},
                         {"libelle": "Fait des choses", "enfants": [], "articles": ["Article 1384"]}]}
    controle = Controle()
    branches = cm.nettoyer(brut, envoyes, controle)
    feuilles = [a["texte"] for b in branches for a in b["articles"]]
    assert feuilles == ["Article 1382 (ancien numéro, aujourd'hui article 1240)", "Article 1240 du Code civil",
                        "Article 1384 (ancien numéro, aujourd'hui article 1242)"]
    assert controle.citations_retirees == 1
    # le lien d'une feuille a l'ancien numero mene a l'article actuel
    assert branches[0]["articles"][0]["actuel"] == "article 1240 du Code civil"


def test_r5_article_actuel_du_meme_numero_pas_signale():
    """Article 1382 actuel (presomptions, preuve) fourni en extrait : ce n'est pas l'ancien numero."""
    envoyes = [extrait(0, "1382", "Les présomptions qui ne sont pas établies par la loi...")]
    envoyes[0]["meta"] = {"en_vigueur": True}
    brut = {"branches": [{"libelle": "Présomptions", "enfants": [], "articles": ["Article 1382"]}]}
    branches = cm.nettoyer(brut, envoyes, Controle())
    assert branches[0]["articles"] == [{"texte": "Article 1382"}]
