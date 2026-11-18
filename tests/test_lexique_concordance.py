"""Phase B du plan d'amelioration : lexique local, anciens numeros (reforme 2016), modes methode,
et non-regression de la recherche sur les cas de l'evaluation qui echouaient."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import concordance, lexique
from api.config import Settings
from api.main import create_app
from api.prompts import prompt_chat
from api.rag import Lexia
from api.references import extraire
from api.retrieval.local import LocalRetriever
from tests.test_api import ABSTENTION, FakeLLM, index_dir  # noqa: F401  (fixture partagee)

CC, CONST = "code_civil", "constitution_1958"
INDEX_REEL = Path(__file__).resolve().parent.parent / "data" / "index"


# --- lexique ------------------------------------------------------------------

@pytest.mark.parametrize("question, attendu", [
    ("Pourquoi les juges ne peuvent-ils pas rendre d'arrêts de règlement ?", (CC, "5")),
    ("Le juge est-il lié par ses propres décisions antérieures ?", (CC, "5")),
    ("Propose un plan de dissertation sur la non-rétroactivité de la loi", (CC, "2")),
    ("Quels principes ne peuvent pas faire l'objet d'une révision constitutionnelle ?", (CONST, "89")),
    ("Quelles sont les conditions de la responsabilité pour faute ?", (CC, "1240")),
    ("Explique la méthode du commentaire d'arrêt en droit des contrats", (CC, "1103")),
    ("Quel est le principe de la force obligatoire du contrat ?", (CC, "1103")),
    ("Qu’est-ce que le devoir d’information ?", (CC, "1112-1")),  # apostrophes typographiques
    ("Qu'est-ce que la violence économique ?", (CC, "1143")),
])
def test_lexique_reconnait_les_notions(question, attendu):
    assert attendu in lexique.suggestions(question)


@pytest.mark.parametrize("question, exclu", [
    ("Qu'est-ce que la force majeure en matière contractuelle ?", (CC, "414")),   # « majeure » != majorité
    ("Comment se passe la dissolution du PACS ?", (CONST, "12")),
    ("Que dit l'article précédent ?", (CC, "5")),
])
def test_lexique_sans_faux_positif(question, exclu):
    assert exclu not in lexique.suggestions(question)


@pytest.mark.parametrize("question", [
    "Paul a vendu sa voiture à Marie en lui cachant qu’elle avait été gravement accidentée. Marie peut-elle faire annuler la vente ?",
    "Le vendeur a menti sur le kilométrage du véhicule. L'acheteur peut-il agir ?",
    "Elle a signé le contrat sans qu'on lui dise que le local était insalubre, le bailleur le savait. Que faire ?",
    "Le cédant a dissimulé les dettes de la société lors de la cession des parts.",
    "Il a acheté un terrain que le vendeur savait inconstructible, sans le lui dire.",
    "Le bail est signé ; le propriétaire cache une fuite d'eau au locataire.",
])
def test_lexique_reconnait_la_reticence_racontee(question):
    assert lexique.suggestions(question)[:2] == [(CC, "1137"), (CC, "1112-1")]


@pytest.mark.parametrize("question", [
    "L'acheteur découvre un vice caché sur la machine vendue. Quel recours ?",   # garantie, pas dol
    "Il cache de l'argent volé dans sa cave.",                                     # aucun contrat
    "Le locataire a caché une clé sous le paillasson.",
    "Le vendeur répond-il d'un vice caché à l'acheteur après la vente ?",
])
def test_lexique_reticence_sans_faux_positif(question):
    assert (CC, "1137") not in lexique.suggestions(question)


# Situations racontees (D75) : formulations differentes de celles des jeux d'evaluation.
@pytest.mark.parametrize("question, attendu", [
    ("Mon neveu de huit ans a cassé la fenêtre de la boulangerie. Qui va payer ?", (CC, "1242")),
    ("Un livreur salarié renverse une passante avec son scooter. L'employeur doit-il payer ?", (CC, "1242")),
    ("Le berger allemand du voisin a mordu le facteur.", (CC, "1243")),
    ("Une cheminée mal entretenue s'est effondrée sur la voiture garée en bas.", (CC, "1244")),
    ("Un automobiliste distrait a endommagé ma clôture : peut-il être obligé de la réparer ?", (CC, "1240")),
    ("Il a signé la cession de son fonds sous la menace d'une arme. Que faire ?", (CC, "1140")),
    ("Elle a acheté un vase en pensant qu'il datait de l'époque Ming.", (CC, "1132")),
    ("Le locataire a trois loyers impayés : le bailleur peut-il résilier le bail ?", (CC, "1728")),
    ("Le maçon n'a jamais terminé le mur commandé et payé. Quels recours ?", (CC, "1217")),
    ("Le client ne paie pas ses factures : le prestataire peut-il cesser de livrer ?", (CC, "1219")),
    ("Un garçon de treize ans a acheté seul une console à 600 euros.", (CC, "1146")),
    ("J'ai payé deux fois la même facture au plombier.", (CC, "1302")),
    ("Elle ne verse plus rien pour l'entretien de leur fille depuis la séparation.", (CC, "371-2")),
    ("Il occupe la maison depuis trente-deux ans sans titre. Peut-il devenir propriétaire ?", (CC, "2272")),
    ("Elle frappe l'homme qui l'agressait dans le métro.", ("code_penal", "122-5")),
    ("Un homme se faisait passer pour un agent EDF afin d'entrer chez les gens.", ("code_penal", "313-1")),
    ("La comptable détourne l'argent que l'association lui avait confié.", ("code_penal", "314-1")),
    ("Un salarié est renvoyé parce qu'il porte la barbe.", ("code_travail", "L1232-1")),
    ("Son chef l'humilie devant ses collègues chaque matin.", ("code_travail", "L1152-1")),
    ("Le préfet interdit une réunion publique : peut-on obtenir une suspension en urgence ?",
     ("code_justice_administrative", "L521-2")),
    ("La télévision achetée le mois dernier ne s'allume plus à cause d'une soudure défectueuse.", (CC, "1641")),
    ("Le vendeur savait-il que la charpente de la maison vendue était rongée par les termites ?", (CC, "1641")),
    ("Le père veut que son fils vienne vivre chez lui après le divorce ; la mère refuse.", (CC, "373-2")),
    ("Un agriculteur stocke son fourrage sur le champ du voisin sans lui en parler ni demander son autorisation.", (CC, "544")),
    ("La mairie va démolir mon kiosque demain : puis-je saisir le juge très vite ?", ("code_justice_administrative", "L521-2")),
    ("Le couvreur laisse tomber une tuile sur le capot d'une voiture garée.", (CC, "1242")),
    ("J'ai versé un acompte à un menuisier qui n'a jamais posé les fenêtres.", (CC, "1229")),
    ("Le bailleur refuse de faire les travaux alors que le logement est insalubre.", (CC, "1719")),
    ("La trésorière conserve pour elle les cotisations qu'elle devait reverser au club.", ("code_penal", "314-1")),
    ("Par inattention, une cycliste renverse un enfant qui est blessé.", ("code_penal", "222-19")),
    ("Il fait 50 heures chaque semaine et n'est payé que pour 35.", ("code_travail", "L3121-28")),
    ("Le rectorat a refusé ma mutation sans aucune justification.", ("code_relations_public_administration", "L211-2")),
    ("Mon locataire se plaint d'infiltrations et le propriétaire ne fait rien.", (CC, "1719")),
    ("Mes beaux-parents m'empêchent de voir mon grand-père depuis des mois.", (CC, "371-4")),
    ("Un caissier repart le soir avec du matériel de l'entreprise.", ("code_penal", "311-1")),
    ("Un homme prétend être policier pour se faire remettre les bijoux d'une passante.", ("code_penal", "313-1")),
    ("Le salarié a été licencié en raison de son origine.", ("code_travail", "L1132-1")),
    ("La préfecture a rejeté ma demande sans me donner la moindre explication.", ("code_relations_public_administration", "L211-2")),
])
def test_lexique_reconnait_les_situations(question, attendu):
    assert attendu in lexique.suggestions(question)


@pytest.mark.parametrize("question, exclu", [
    ("Un père divorcé refuse de payer la pension de ses enfants.", (CC, "1219")),      # pas un contrat synallagmatique
    ("Un client glisse un parfum dans son sac sans payer.", (CC, "1242")),             # vol, pas une chute
    ("L'employé vire l'argent des clients sur son compte.", ("code_travail", "L1232-1")),
    ("Quelle est la différence entre la responsabilité contractuelle et délictuelle ?", (CC, "1146")),
    ("Le juge civil peut-il statuer en urgence sur un litige entre voisins ?", ("code_justice_administrative", "L521-2")),
    ("Un enfant de dix ans casse la vitre d'un voisin avec son ballon.", (CC, "1641")),            # pas de vente
    ("Qu'est-ce qu'un vice du consentement dans la vente ?", (CC, "1641")),
    ("J'ai planté un pommier dans mon jardin, quelles distances respecter ?", (CC, "544")),
    ("Le salarié travaille 35 heures par semaine.", ("code_travail", "L3121-28")),
    ("En voulant éviter un chien sur la route, une conductrice blesse un piéton.", (CC, "1243")),
    ("Un client glisse un parfum dans son sac et sort sans payer.", ("code_penal", "314-1")),       # vol simple
    ("Mon voisin m'a expliqué la raison de son refus.", ("code_relations_public_administration", "L211-2")),
])
def test_lexique_situations_sans_faux_positif(question, exclu):
    assert exclu not in lexique.suggestions(question)


def test_lexique_plafonne():
    q = "force obligatoire, bonne foi dans le contrat, vices du consentement, dol, violence, lésion"
    assert len(lexique.suggestions(q)) == lexique.MAX_LEXIQUE


# --- concordance --------------------------------------------------------------

def test_anciens_numeros_seulement_pour_le_code_civil():
    assert concordance.anciens_numeros(extraire("Que dit l'article 1134 du Code civil ?")) == {
        "1134": ("1103", "1193", "1104")}
    assert concordance.anciens_numeros(extraire("article 1382")) == {"1382": ("1240",)}
    assert concordance.anciens_numeros(extraire("article 1134 du code pénal")) == {}
    assert concordance.anciens_numeros(extraire("article 1240 du Code civil")) == {}


def test_note_de_concordance_dans_le_prompt():
    p = prompt_chat("Que dit l'article 1134 ?", "expliquer", [], anciens={"1134": ["1103", "1193", "1104"]})
    assert "1er octobre 2016" in p and "1103, 1193, 1104" in p
    assert "réécrit" in concordance.note({"1101": ["1101"]})
    assert "1134" not in prompt_chat("q", "expliquer", [])


def test_ancien_numero_sert_l_ancien_texte_et_l_article_actuel(index_dir, tmp_path):  # noqa: F811
    llm = FakeLLM()
    llm.reponses.append(ABSTENTION)
    settings = Settings(gemini_models=("fake",), index_dir=index_dir, logs_dir=tmp_path)
    client = TestClient(create_app(settings, retriever=LocalRetriever(index_dir), llm=llm))
    data = client.post("/chat", json={"question": "Que dit l'article 1382 du Code civil ?"}).json()
    prompt = llm.prompts[-1]
    assert "du 21 mars 1804 au 1er octobre 2016" in prompt          # ancienne version de 1382
    assert "Code civil, article 1240" in prompt                       # article actuel
    assert "jusqu'au 1er octobre 2016" in prompt                      # consigne au modele
    assert data["controle"]["concordance"] == {"1382": ["1240"]}

    ancien = "code_civil:LEGIARTI000006438819"
    v = client.get(f"/sources/{ancien}/vigueur").json()
    assert v["en_vigueur"] is False and "1240" in v["message"]
    assert v["version_en_vigueur"]["id"] == "code_civil:LEGIARTI000032041571"


# --- modes methode ------------------------------------------------------------

def test_methode_sans_extrait_appelle_quand_meme_le_modele(index_dir, tmp_path):  # noqa: F811
    llm = FakeLLM()
    llm.reponses.append({"statut": "reponse", "titre": "Méthode", "droit_positif": [],
                         "explication": [{"texte": "1. Définir les termes du sujet.", "sources": []}],
                         "points_incertains": [], "message": ""})
    settings = Settings(gemini_models=("fake",), index_dir=index_dir, logs_dir=tmp_path)
    client = TestClient(create_app(settings, retriever=LocalRetriever(index_dir), llm=llm))
    data = client.post("/chat", json={"question": "zzqqwx yyvvkk", "mode": "dissertation"}).json()
    assert len(llm.prompts) == 1 and data["statut"] == "reponse"
    assert "n'utilise pas le statut 'abstention'" in llm.prompts[0]
    # hors mode methode, toujours aucune sollicitation du modele
    data = client.post("/chat", json={"question": "zzqqwx yyvvkk"}).json()
    assert data["statut"] == "abstention" and len(llm.prompts) == 1


# --- index reel : articles du lexique, concordance et cas de l'evaluation ----------

reel = pytest.mark.skipif(not (INDEX_REEL / "lexia.sqlite").exists(), reason="index reel absent")


@pytest.fixture(scope="module")
def retriever_reel():
    # Copie propre (publication) : pas d'index, les tests qui en dependent sont ignores au lieu d'echouer.
    if not (INDEX_REEL / "lexia.sqlite").exists():
        pytest.skip("index reel absent")
    return LocalRetriever(INDEX_REEL)


def _en_vigueur(r, src, num):
    return [v for v in r.versions(src, num) if (v.get("meta") or {}).get("en_vigueur") or src == CONST]


@reel
def test_articles_du_lexique_existent(retriever_reel):
    # Une source hors DILA ajoutee au registre (traites de l'Union, D98) n'entre dans un index qu'a sa prochaine
    # reconstruction : ses articles sont alors verifies ; avant, seule une telle source peut manquer entierement.
    from ingest import run
    dans_l_index = {s for (s,) in retriever_reel._q("SELECT DISTINCT source_id FROM passages")}
    cites = {s for _, arts in lexique.NOTIONS for s, _ in arts}
    assert all(hasattr(run.SOURCES[s], "fetch") for s in cites - dans_l_index), cites - dans_l_index
    absents = [(s, n) for _, arts in lexique.NOTIONS for s, n in arts
               if s in dans_l_index and not _en_vigueur(retriever_reel, s, n)]
    assert absents == []


@reel
def test_table_de_concordance_verifiee(retriever_reel):
    for ancien, nouveaux in concordance.REFORME_2016.items():
        assert concordance.ancienne_version(retriever_reel.versions(CC, ancien)), ancien
        for n in nouveaux:
            assert _en_vigueur(retriever_reel, CC, n), (ancien, n)


# Cas de eval/cas.yaml dont la source attendue n'etait pas transmise au modele (run 20261111-153059).
# Recherche sans Gemini (ni reformulation ni vecteurs) : le cas le plus defavorable.
CAS_REGRESSION = ["intro-04", "intro-36", "intro-37", "const-32", "civ-32", "civ-40", "piege-29", "piege-30"]


@reel
@pytest.mark.parametrize("cas_id", CAS_REGRESSION)
def test_source_attendue_retrouvee_sans_gemini(retriever_reel, cas_id):
    from eval.cas import charger, correspond
    from api.rag import K_CHAT
    cas = {c.id: c for c in charger()}[cas_id]
    passages, _ = Lexia(retriever_reel, llm=None).rechercher(cas.question, cas.matiere, K_CHAT)
    assert any(correspond(ref, p) for ref in cas.sources for p in passages), \
        [f"{p['source_id']}:{p.get('numero')}" for p in passages]


# --- matieres speciales : l'article 777 (successions) ne doit plus servir pour le dol en matiere de contrats ---

def test_lexique_dol_complet_et_notions_generales_en_dernier():
    assert lexique.suggestions("Quelle est la sanction du dol ?") == [(CC, "1137"), (CC, "1131"), (CC, "1138"), (CC, "1139")]
    # « droit des contrats » ne prend plus la place des articles de la notion precise
    assert lexique.suggestions("Qu'est-ce que le dol en droit des contrats ?")[0] == (CC, "1137")
    assert lexique.suggestions("Le dol peut-il annuler l'option successorale d'un héritier ?")[0] == (CC, "777")


def test_hors_matiere():
    art_777 = {"source_id": CC, "meta": {"plan": ["Livre III", "Titre Ier : Des successions", "Section 1 : Dispositions générales."]}}
    art_1137 = {"source_id": CC, "meta": {"plan": ["Livre III", "Titre III : Des sources d'obligations"]}}
    assert lexique.hors_matiere(art_777, "Quelle est la sanction du dol ?")
    assert not lexique.hors_matiere(art_777, "Le dol de l'héritier dans la succession")
    assert not lexique.hors_matiere(art_1137, "Quelle est la sanction du dol ?")
    regime = {"source_id": CC, "meta": {"plan": ["Titre V : Du contrat de mariage et des régimes matrimoniaux"]}}
    assert lexique.hors_matiere(regime, "dol") and not lexique.hors_matiere(regime, "dol entre époux")


@reel
@pytest.mark.parametrize("question, present, absent", [
    ("Qu'est-ce que le dol et la réticence dolosive ?", "1137", "777"),
    ("Quelle est la sanction du dol ?", "1131", "777"),
    ("Le dol peut-il annuler l'option successorale d'un héritier ?", "777", None),
    ("Que dit l'article 777 du code civil ?", "777", None),          # cite : jamais ecarte
])
def test_article_777_seulement_pour_les_successions(retriever_reel, question, present, absent):
    from api.rag import K_CHAT
    passages, _ = Lexia(retriever_reel, llm=None).rechercher(question, None, K_CHAT)
    numeros = [p.get("numero") for p in passages if p["source_id"] == CC]
    assert present in numeros and (absent is None or absent not in numeros), numeros


@reel
@pytest.mark.parametrize("question", [
    "Qu'est-ce que la réticence dolosive ?",
    "Un contrat signé sous la violence est-il valable ?",
])
def test_vice_du_consentement_suivi_de_ses_regles_communes(retriever_reel, question):
    from api.rag import K_CHAT
    passages, _ = Lexia(retriever_reel, llm=None).rechercher(question, "droit_des_contrats", K_CHAT)
    numeros = [p.get("numero") for p in passages if p["source_id"] == CC]
    assert numeros.count("1130") == 1 and numeros.count("1131") == 1, numeros


def test_regles_communes_apres_le_premier_vice_en_vigueur_sans_doublon():
    art = lambda n, vig=True: {"id": f"cc:{n}:{vig}", "source_id": CC, "numero": n, "meta": {"en_vigueur": vig}}  # noqa: E731

    class Versions:
        def versions(self, s, n):
            return [art(n, False), art(n)]

    lx = Lexia(Versions(), llm=None)
    ordre = lambda ps: [(p["numero"], p["meta"]["en_vigueur"]) for p in ps]  # noqa: E731
    # ancien article 1134 (force obligatoire, abroge en 2016) : numero dans la plage, mais pas en vigueur
    assert ordre(lx._regles_communes_vices([art("1134", False)])) == [("1134", False)]
    # 1131 deja present : seul 1130 est ajoute, juste apres le dol
    ps = lx._regles_communes_vices([art("1641"), art("1137"), art("1131")])
    assert ordre(ps) == [("1641", True), ("1137", True), ("1130", True), ("1131", True)]


# --- droit penal, social, administratif (lexique etendu le 2026-11-12) ---------------------------

@reel
@pytest.mark.parametrize("question, matiere, attendu", [
    ("Qu'est-ce que la légitime défense ?", "droit_penal", ("code_penal", "122-5")),
    ("Qu'est-ce que le trouble psychique en droit pénal ?", "droit_penal", ("code_penal", "122-1")),
    ("Quel est le délai de prescription d'un délit ?", "droit_penal", ("code_procedure_penale", "8")),
    ("Qu'est-ce que la garde à vue ?", "droit_penal", ("code_procedure_penale", "62-2")),
    ("Qu'est-ce qu'un licenciement pour motif économique ?", "droit_social", ("code_travail", "L1233-3")),
    ("Qu'est-ce que la rupture conventionnelle ?", "droit_social", ("code_travail", "L1237-11")),
    ("Qu'est-ce que le recours pour excès de pouvoir ?", "droit_administratif", ("code_justice_administrative", "R421-1")),
    ("Qu'est-ce que le référé-liberté ?", "droit_administratif", ("code_justice_administrative", "L521-2")),
    ("Que se passe-t-il si l'administration garde le silence ?", "droit_administratif",
     ("code_relations_public_administration", "L231-1")),
])
def test_article_de_principe_retrouve(retriever_reel, question, matiere, attendu):
    from api.rag import K_CHAT
    passages, _ = Lexia(retriever_reel, llm=None).rechercher(question, matiere, K_CHAT)
    trouves = [(p["source_id"], p.get("numero")) for p in passages]
    assert attendu in trouves, trouves
