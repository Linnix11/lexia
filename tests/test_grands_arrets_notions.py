"""Grands arrets par notion (D124) : registre, fiches Lexia, ajout aux extraits, note au modele, arrets abandonnes.

Dossier enseignant du 23/11 : aucune des 30 reponses ne citait un grand arret. Jand'heur, Franck et Blanco etaient
absents de l'index (ou jamais remontes), et api/grands_arrets.py ne servait un arret que si la question le nommait.
"""

import json
import re
import sqlite3
from pathlib import Path

import pytest
import yaml

from api import grands_arrets, prompts
from api.config import ROOT
from api.grands_arrets import GRANDS_ARRETS, GRANDS_ARRETS_ADMINISTRATIFS, SOURCE_FICHES
from api.matieres import MATIERES, sources_par_matiere
from api.rag import K_CHAT, K_SECOURS, Lexia, pour_secours
from api.retrieval.base import Hit
from eval.cas import charger, correspond

INDEX_REEL = ROOT / "data" / "index"
reel = pytest.mark.skipif(not (INDEX_REEL / "lexia.sqlite").exists(), reason="index reel absent")
JEU = ROOT / "eval" / "cas_grands_arrets_notions.yaml"
REG = grands_arrets.registre()


# --- registre -----------------------------------------------------------------------------------------------------

def test_registre_complet_et_coherent():
    assert len(REG.arrets) >= 100
    for a in REG.arrets.values():
        assert a.statut in grands_arrets.STATUTS, a.id
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", a.date), a.id
        assert set(a.matieres) <= set(MATIERES), a.id
        assert bool(a.index) != bool(a.fiche), f"{a.id} : une decision de l'index ou une fiche, pas les deux"
        assert a.portee and a.citation, a.id
        if a.fiche:
            assert set(a.fiche) == {"faits", "question", "solution", "apport", "portee"}, a.id
        for texte in (a.citation, a.portee, *(a.fiche or {}).values()):
            assert "—" not in texte and "–" not in texte, a.id          # pas de tiret long (consigne de l'editeur)
            assert not re.search(r"[\U0001F300-\U0001FAFF]", texte), a.id
    citees = {i for n in REG.notions.values() for i in n.arrets}
    assert citees == set(REG.arrets)       # chaque arret est rattache a une notion, chaque notion a des arrets connus


def test_arrets_abandonnes_disent_par_quoi():
    abandonnes = [a for a in REG.arrets.values() if a.statut == "abandonne"]
    assert {"desmares", "canal-de-craponne", "consorts-cruz", "cohn-bendit", "tropic-travaux", "semoules",
            "perruche", "mariage-2007"} == {a.id for a in abandonnes}
    for a in abandonnes:
        assert re.search(r"abandonn|n'est plus le droit positif|remplac", a.portee, re.I), a.id


def test_numeros_identiques_a_ceux_de_D90():
    """Un meme arret ne peut pas avoir deux numeros (api/grands_arrets.py, D90 et B5)."""
    pourvois = {p for _, ps, _ in GRANDS_ARRETS for p in ps}
    jade = {d for _, d, _, _ in GRANDS_ARRETS_ADMINISTRATIFS}
    for a in REG.arrets.values():
        if a.index and a.index.startswith("conseil_etat:"):
            assert a.index.split(":")[1] in jade or a.id in {
                "prince-napoleon", "cadot", "cames", "casanova", "camino", "regnault-desroziers", "lecomte",
                "ingenieurs-conseils", "lutetia", "bianchi", "aprei", "bergoend"}, a.id
        if a.reference and re.fullmatch(r"\d{2}-\d{2}\.\d{3}", a.reference) and a.reference in pourvois:
            assert a.reference in pourvois


def test_source_declaree_au_registre_hors_des_matieres():
    registre = yaml.safe_load((ROOT / "registry" / "sources.yaml").read_text(encoding="utf-8"))
    src = next(s for s in registre["sources"] if s["id"] == SOURCE_FICHES)
    assert src["statut"] == "fiche_lexia" and src["fichier"] == "registry/grands_arrets.yaml"
    assert all(SOURCE_FICHES not in v for v in sources_par_matiere().values())   # jamais dans la recherche


def test_fiche_lexia_jamais_presentee_comme_decision():
    p = grands_arrets.fiche(f"{SOURCE_FICHES}:jand-heur")
    assert p["type"] == "fiche" and p["url"] == "" and p["entete"].startswith("Fiche Lexia (non officielle)")
    assert "à relire par un enseignant" in p["version"]
    assert p["texte"].startswith(grands_arrets.AVERTISSEMENT_FICHE)
    assert "13 février 1930" in p["entete"] and "Portée actuelle" in p["texte"]
    assert grands_arrets.fiche(f"{SOURCE_FICHES}:nicolo") is None       # dans l'index : pas de fiche
    assert grands_arrets.fiche("code_civil:jand-heur") is None
    assert "13 février 1930" in prompts.format_extraits([p]) and "fiche Lexia" in prompts.format_extraits([p])


# --- notions ------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("question, notion, premier", [
    ("Quelles sont les conditions de la responsabilité du fait des choses ?", "fait_des_choses", "jand-heur"),
    ("Qu'est-ce que le recours pour excès de pouvoir ?", "recours_exces_pouvoir", "dame-lamotte"),
    ("Expliquez la primauté du droit de l'Union européenne.", "primaute_droit_union", "costa"),
    ("Qu'est-ce que le bloc de constitutionnalité ?", "bloc_constitutionnalite", "cc-71-44-dc"),
    ("Quels sont les fondements de la responsabilité administrative ?", "responsabilite_administrative", "blanco"),
    ("Le juge peut-il réviser le contrat en cas d'imprévision ?", "imprevision", "canal-de-craponne"),
])
def test_notion_reconnue_et_ses_grands_arrets(question, notion, premier):
    assert notion in grands_arrets.notions_de(question)
    assert grands_arrets.arrets_pour(question)[0].id == premier


@pytest.mark.parametrize("question", [
    "Franck casse la vitre de son voisin avec un ballon. Le voisin peut-il obtenir réparation ?",
    "Mme Mercier a vendu sa maison à M. Costa. La vente est-elle valable ?",
    "Qu'est-ce que l'intérêt à agir en procédure civile ?",
    "Une clause contraire à l'ordre public et à la liberté contractuelle est-elle valable ?",
    "Le salarié peut-il abuser de sa liberté d'expression ?",
])
def test_pas_de_grand_arret_hors_sujet(question):
    """Nom courant sans contexte d'arret (D90), notion voisine (interet a agir du proces civil, ordre public du
    contrat) : aucun grand arret."""
    assert grands_arrets.arrets_pour(question) == []


def test_arret_nomme_en_premier():
    q = "Que décide l'arrêt Franck sur la garde de la chose ?"
    assert [a.id for a in grands_arrets.arrets_pour(q)][:2] == ["franck", "jand-heur"]


# --- ajout aux extraits (retriever factice) ----------------------------------------------------------------------

def article(i):
    return {"id": f"code_civil:A{i}", "source_id": "code_civil", "type": "article", "numero": str(1240 + i),
            "entete": f"Code civil, article {1240 + i}", "texte": "Texte.", "url": "u", "version": "v",
            "meta": {"en_vigueur": True}}


BLIECK = {"id": "judilibre:JURITEXT000007026394:sommaire", "source_id": "judilibre", "type": "sommaire",
          "numero": None, "entete": "Cour de cassation, Assemblée plénière, 29 mars 1991, 89-15.231",
          "texte": "RESPONSABILITE...", "url": "https://www.legifrance.gouv.fr/juri/id/JURITEXT000007026394",
          "version": "v", "meta": {"id_dila": "JURITEXT000007026394", "date": "1991-03-29"}}


class Retriever:
    mode = "test"

    def __init__(self, hits):
        self.hits = hits

    def search(self, question, **kw):
        return [Hit(p, 1.0, {"lexical"}) for p in self.hits]

    def get(self, pid):
        return {BLIECK["id"]: BLIECK}.get(pid) or grands_arrets.fiche(pid)

    def versions(self, s, n):
        return []

    def couverture(self, s):
        return 0.0


def test_grands_arrets_apres_les_extraits_sans_rien_changer_avant():
    base = [article(i) for i in range(K_CHAT)]
    q = "Quelles sont les conditions de la responsabilité du fait des choses ?"
    avant, _ = Lexia(Retriever(base), llm=None, avec_grands_arrets=False).rechercher(q, None, K_CHAT)
    apres, infos = Lexia(Retriever(base), llm=None).rechercher(q, None, K_CHAT)
    assert apres[:len(avant)] == avant
    ajoutes = apres[len(avant):]
    assert [p["id"] for p in ajoutes] == [f"{SOURCE_FICHES}:jand-heur", f"{SOURCE_FICHES}:franck",
                                          f"{SOURCE_FICHES}:teffaine"]      # 3 au plus, ordre de la notion
    assert infos["grands_arrets"] == 3 and all(p["grand_arret"]["ajoute"] for p in ajoutes)
    # secours : les memes K_SECOURS extraits qu'avant, plus le premier grand arret
    assert pour_secours(apres) == pour_secours(avant) + [ajoutes[0]]
    assert len(pour_secours(avant)) == K_SECOURS


def test_decision_deja_presente_signalee_sans_doublon():
    q = "Existe-t-il un principe général de responsabilité du fait d'autrui ?"
    passages, infos = Lexia(Retriever([article(0), BLIECK]), llm=None).rechercher(q, None, K_CHAT)
    ids = [p["id"] for p in passages]
    assert ids.count(BLIECK["id"]) == 1 and ids.index(BLIECK["id"]) == 1
    blieck = passages[1]
    assert blieck["grand_arret"] == {**blieck["grand_arret"], "id": "blieck", "ajoute": False}
    assert "Blieck" in blieck["entete"] and BLIECK["entete"] in blieck["entete"]
    assert "Blieck" not in BLIECK["entete"]           # le passage du retriever n'est pas modifie
    assert infos["grands_arrets"] == 0                  # Bertrand et Costedoat absents de ce faux index


def test_decision_absente_de_l_index_pas_de_fiche_de_remplacement():
    q = "Qu'est-ce que le recours pour excès de pouvoir ?"
    passages, infos = Lexia(Retriever([article(0)]), llm=None).rechercher(q, None, K_CHAT)
    assert [p["id"] for p in passages] == ["code_civil:A0"] and infos["grands_arrets"] == 0


# --- consigne au modele et controle ------------------------------------------------------------------------------

def _marques(*ids):
    out = []
    for i in ids:
        a = REG.arrets[i]
        p = grands_arrets.passage_fiche(a) if a.fiche else {**BLIECK, "id": a.index}
        out.append(grands_arrets.marquer(p, a, ajoute=True))
    return out


def test_note_cite_date_et_statut_abandonne():
    passages = [article(0)] + _marques("jand-heur", "canal-de-craponne")
    prompt = prompts.prompt_chat("Le juge peut-il réviser un contrat ?", "expliquer", passages)
    assert "[S2] Cass., ch. réunies, 13 février 1930, Jand'heur : toujours appliqué" in prompt
    assert "[S3] Cass. civ., 6 mars 1876, Canal de Craponne : ABANDONNÉ" in prompt
    assert "jamais présenté comme le droit positif" in prompt
    assert "grands arrêts" not in prompts.prompt_chat("Que dit l'article 1240 ?", "expliquer", [article(0)])


def test_arret_abandonne_seul_n_est_pas_du_droit_positif():
    passages = [article(0)] + _marques("canal-de-craponne")
    craponne = passages[1]["id"]
    reponse = {"statut": "reponse", "droit_positif": [
        {"texte": "Le juge ne peut pas réviser le contrat.", "sources": [craponne]},
        {"texte": "Le juge peut réviser le contrat (article 1195).", "sources": ["code_civil:A0"]},
        {"texte": "Revirement par l'ordonnance de 2016.", "sources": [craponne, "code_civil:A0"]}],
        "explication": [], "reponse_directe": [{"texte": "Non.", "sources": [craponne]}]}
    assert grands_arrets.ecarter_abandonnes(reponse, passages) == 2
    assert [e["texte"] for e in reponse["droit_positif"]] == [
        "Le juge peut réviser le contrat (article 1195).", "Revirement par l'ordonnance de 2016."]
    assert reponse["explication"] == [{"texte": "Le juge ne peut pas réviser le contrat.", "sources": [craponne]}]
    assert reponse["reponse_directe"] == []


def test_chat_deplace_l_arret_abandonne_et_vigueur_de_la_fiche():
    class LLM:
        def generate_json(self, *, prompt, **kw):
            self.prompt = prompt
            s = re.search(r"\[(S\d+)\] Cass\. civ\., 6 mars 1876", prompt).group(1)
            return {"statut": "reponse", "titre": "Imprévision", "message": "",
                    "droit_positif": [{"texte": "Le juge ne révise jamais le contrat.", "sources": [s]},
                                      {"texte": "Article 1241.", "sources": ["S2"]}],
                    "explication": [], "points_incertains": []}, "fake"
    llm = LLM()
    lexia = Lexia(Retriever([article(0), article(1)]), llm=llm)
    r = lexia.chat("Le juge peut-il réviser un contrat pour imprévision ?", "expliquer", None)
    assert [e["texte"] for e in r["droit_positif"]] == ["Article 1241."]
    assert any("ne révise jamais" in e["texte"] for e in r["explication"])
    fiche = next(s for s in r["sources"] if s["source_id"] == SOURCE_FICHES)
    assert fiche["entete"].startswith("Fiche Lexia (non officielle)") and fiche["url"] == ""
    v = lexia.vigueur(f"{SOURCE_FICHES}:canal-de-craponne")
    assert v["applicable"] is False and "pas le texte de la décision" in v["message"]


# --- index reel ---------------------------------------------------------------------------------------------------

@reel
def test_chaque_decision_du_registre_est_dans_l_index_a_sa_date():
    con = sqlite3.connect(INDEX_REEL / "lexia.sqlite")
    for a in REG.arrets.values():
        if not a.index:
            continue
        row = con.execute("SELECT data FROM passages WHERE id = ?", (a.index,)).fetchone()
        assert row, f"{a.id} : {a.index} absent de l'index"
        p = json.loads(row[0])
        assert p["meta"]["date"] == a.date, a.id
        if a.reference and re.fullmatch(r"\d{2}-\d{2}\.\d{3}", a.reference):
            assert a.reference.replace(".", "") in p["meta"]["numeros_pourvoi"], a.id
        if p["source_id"] == "decisions_conseil_constitutionnel":
            assert f"{p['meta']['numero']} {p['meta']['nature']}" == a.reference, a.id
        if p["source_id"] == "conseil_etat" and a.reference:
            assert p["meta"]["numero"].split()[0] == a.reference, a.id


@reel
def test_retriever_reel_sert_les_fiches():
    from api.retrieval.local import LocalRetriever
    r = LocalRetriever(INDEX_REEL)
    assert r.get(f"{SOURCE_FICHES}:teffaine")["entete"].endswith("16 juin 1896, Teffaine")
    assert r.get(f"{SOURCE_FICHES}:inconnu") is None


@reel
@pytest.mark.parametrize("cas", charger(JEU), ids=lambda c: c.id)
def test_jeu_par_notion_les_grands_arrets_arrivent(cas):
    """Sans Gemini (ni reformulation ni vecteurs) ; sans la correction (avec_grands_arrets=False), 1 cas sur 20
    passe : Jand'heur, Franck, Costa... n'etaient jamais fournis."""
    from api.retrieval.local import LocalRetriever
    r = LocalRetriever(INDEX_REEL)
    passages, _ = Lexia(r, llm=None).rechercher(cas.question, cas.matiere, K_CHAT)
    assert cas.trouve(passages), [p["id"] for p in passages]
    avant, _ = Lexia(r, llm=None, avec_grands_arrets=False).rechercher(cas.question, cas.matiere, K_CHAT)
    # recherche d'avant D124 : seul gan-04 (Dame Lamotte, sommaire trouve par le plein texte) passait
    assert cas.trouve(avant) == (cas.id == "gan-04")


def test_document_de_relecture_a_jour():
    """docs/relecture-enseignant/grands-arrets.md : regenerer par `python -m api.grands_arrets`."""
    texte = grands_arrets.DOCUMENT.read_text(encoding="utf-8")
    assert texte == grands_arrets.document()
    assert texte.count("\n*À relire par un enseignant.*\n") == sum(1 for a in REG.arrets.values() if a.fiche) == 14
    assert "—" not in texte


def test_source_attendue_ga():
    assert correspond("ga:jand-heur", grands_arrets.fiche(f"{SOURCE_FICHES}:jand-heur"))
    assert correspond("ga:blieck", BLIECK)
    assert not correspond("ga:franck", grands_arrets.fiche(f"{SOURCE_FICHES}:jand-heur"))
    assert len(charger(JEU)) == 20 and Path(JEU).exists()
