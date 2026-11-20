"""Lot B de l'audit du 2026-11-18 : recherche, sources et corpus."""

from datetime import date, timedelta
from pathlib import Path

from api.textes import en_vigueur_aujourdhui
from ingest.sources import legi

FIX = Path(__file__).parent / "fixtures"
HIER = (date.today() - timedelta(days=1)).isoformat()
DEMAIN = (date.today() + timedelta(days=1)).isoformat()


def _article(etat: str, debut: str, fin: str | None):
    brut = (FIX / "LEGIARTI000032041571.xml").read_text(encoding="utf-8")
    brut = brut.replace("<ETAT>VIGUEUR</ETAT>", f"<ETAT>{etat}</ETAT>")
    brut = brut.replace("<DATE_DEBUT>2016-10-01</DATE_DEBUT>", f"<DATE_DEBUT>{debut}</DATE_DEBUT>")
    brut = brut.replace("<DATE_FIN>2999-01-01</DATE_FIN>", f"<DATE_FIN>{fin}</DATE_FIN>" if fin else "")
    return legi.parse_article(brut.encode(), date_recuperation="d", version_archive="a")


# --- B1 : etats DILA contredits par les dates ------------------------------------------------

def test_b1_abroge_avec_fin_future_est_en_vigueur():
    """LPF L24 : « ABROGE » du 18 aout 1993 au 1er mai 2027, applicable aujourd'hui."""
    p = _article("ABROGE", "1993-08-18", "2027-05-01")
    assert p.meta["en_vigueur"] is True
    assert "(en vigueur, abrogation différée, du 18 août 1993 au 1er mai 2027)" in p.entete
    assert p.meta["etat"] == "ABROGE"   # etat DILA garde tel quel


def test_b1_modifie_avec_fin_future_est_en_vigueur():
    """C. trav. R4451-39 : version « MODIFIE » jusqu'au 1er juillet 2027, la suivante est differee."""
    p = _article("MODIFIE", "2018-07-01", "2027-07-01")
    assert p.meta["en_vigueur"] is True
    assert "(en vigueur, modification différée, du 1er juillet 2018 au 1er juillet 2027)" in p.entete


def test_b1_date_de_fin_non_fixee():
    """CGI 302 J : « ABROGE » jusqu'au 22 fevrier 2222, date DILA d'une abrogation non encore datee."""
    p = _article("ABROGE", "2010-04-01", "2222-02-22")
    assert p.meta["en_vigueur"] is True
    assert "2222" not in p.entete and "depuis le 1er avril 2010" in p.entete


def test_b1_modifie_sans_fin_ou_passe_reste_hors_vigueur():
    assert _article("MODIFIE", "2006-01-01", "2999-01-01").meta["en_vigueur"] is False   # C. com. L622-19
    assert _article("MODIFIE", "2006-01-01", None).meta["en_vigueur"] is False
    assert _article("ABROGE", "2006-01-01", HIER).meta["en_vigueur"] is False
    assert _article("MODIFIE_MORT_NE", "2022-01-01", "2999-01-01").meta["en_vigueur"] is False
    assert _article("ABROGE", DEMAIN, "2030-01-01").meta["en_vigueur"] is False


def test_b1_entree_en_vigueur_non_fixee():
    """Ordonnance 2025-229 art. 68 : « VIGUEUR » depuis le 1er janvier 2999 (date DILA non fixee)."""
    p = _article("VIGUEUR", "2999-01-01", None)
    assert p.meta["en_vigueur"] is False
    assert "2999" not in p.entete and "pas encore en vigueur" in p.entete
    assert "entrée en vigueur non fixée" in p.entete
    assert en_vigueur_aujourdhui(p.meta, "lois") is False


def test_b1_entree_en_vigueur_future_recalculee_a_la_requete():
    """Une version qui entre en vigueur apres l'import l'est a la requete, sans attendre une reconstruction (B8)."""
    p = _article("VIGUEUR_DIFF", "2030-01-01", None)
    assert p.meta["en_vigueur"] is False and p.meta["en_vigueur_le"] == "2030-01-01"
    assert "pas encore en vigueur" in p.entete
    assert en_vigueur_aujourdhui(p.meta, "code_civil") is False
    assert en_vigueur_aujourdhui(dict(p.meta, en_vigueur_le=HIER), "code_civil") is True
    assert en_vigueur_aujourdhui(dict(p.meta, en_vigueur_le=HIER, date_fin=HIER), "code_civil") is False
    # Differee deja echue a l'import (la DILA n'a pas mis l'etat a jour) : pas de date, pas de doublon.
    assert "en_vigueur_le" not in _article("VIGUEUR_DIFF", "2026-09-01", None).meta


# --- B2, B3, B4 : citations bis / R* / LO, pourvois -----------------------------------------

import json  # noqa: E402
import sqlite3  # noqa: E402
import threading  # noqa: E402

import pytest  # noqa: E402

from api.references import extraire, reference_couverte  # noqa: E402
from api.retrieval.local import LocalRetriever  # noqa: E402
from ingest.build_index import build  # noqa: E402
from ingest.sources import cass  # noqa: E402


def _numero(num: str, source_id: str, nom: str, art_id: str):
    brut = (FIX / "LEGIARTI000032041571.xml").read_text(encoding="utf-8")
    brut = brut.replace("<NUM>1240</NUM>", f"<NUM>{num}</NUM>").replace("LEGIARTI000032041571", art_id)
    return legi.parse_article(brut.encode(), date_recuperation="d", version_archive="a", source_id=source_id, nom=nom)


@pytest.fixture(scope="module")
def index_b(tmp_path_factory):
    base = tmp_path_factory.mktemp("lot_b")
    (base / "passages").mkdir()
    rows = [
        _numero("D45-2-1 bis", "code_procedure_penale", "Code de procédure pénale", "LEGIARTI000000000001"),
        _numero("R*421-1", "code_urbanisme", "Code de l'urbanisme", "LEGIARTI000000000002"),
        _numero("LO119", "code_electoral", "Code électoral", "LEGIARTI000000000003"),
        _numero("1240 ter", "code_civil", "Code civil", "LEGIARTI000000000004"),
    ]
    rows = [p.to_dict() for p in rows]
    rows += [p.to_dict() for p in cass.parse_arret((FIX / "cass_moderne.xml").read_bytes(),
                                                   date_recuperation="d", version="v")]
    (base / "passages" / "b.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows))
    build(passages_dir=base / "passages", index_dir=base / "index", cache_dir=base / "vide", model="aucun")
    return base / "index"


@pytest.mark.parametrize("question, attendu", [
    ("Que dit l'article D45-2-1 bis du code de procédure pénale ?", "D45-2-1 bis"),
    ("article D. 45-2-1 bis CPP", "D45-2-1 bis"),
    ("article 1240 ter du code civil", "1240 ter"),
    ("article R. 421-1 du code de l'urbanisme", "R421-1"),
    ("article R*421-1 du code de l'urbanisme", "R421-1"),
    ("article R.* 421-1 du code de l'urbanisme", "R421-1"),
    ("article LO 119 du code électoral", "LO119"),
    ("article L.O. 119 du code électoral", "LO119"),
    ("article LO119 du code électoral", "LO119"),
])
def test_b2_b3_extraction(question, attendu):
    assert attendu in extraire(question).articles


@pytest.mark.parametrize("question, numero", [
    ("Que dit l'article D45-2-1 bis du code de procédure pénale ?", "D45-2-1 bis"),
    ("article 1240 ter du code civil", "1240 ter"),
    ("article R. 421-1 du code de l'urbanisme", "R*421-1"),
    ("article R*421-1 du code de l'urbanisme", "R*421-1"),
    ("article LO 119 du code électoral", "LO119"),
])
def test_b2_b3_article_trouve_par_citation(index_b, question, numero):
    r = LocalRetriever(index_b)
    assert [p["numero"] for p in r._par_reference(question, None)] == [numero]


def test_b3_couverture_ignore_l_asterisque():
    p = [{"numero": "R*421-1", "texte": "", "entete": "Code de l'urbanisme, article R*421-1"}]
    assert reference_couverte("article", extraire("article R. 421-1").articles[0], p)
    assert reference_couverte("article", extraire("article R*421-1").articles[0], p)
    assert reference_couverte("article", "R421-1", [{"numero": "", "entete": "", "texte": "l'article R*421-1"}])
    assert reference_couverte("article", "D45-2-1 bis", [{"numero": "D45-2-1 bis", "texte": "", "entete": ""}])
    assert reference_couverte("article", "LO119", [{"numero": "", "entete": "", "texte": "article L.O. 119"}])
    assert not reference_couverte("article", "R421-2", p)


def test_b4_pourvoi_par_table_dediee(index_b):
    con = sqlite3.connect(index_b / "lexia.sqlite")
    assert con.execute("SELECT count(*) FROM pourvois WHERE numero = '20-18893'").fetchone()[0] >= 1
    con.close()
    r = LocalRetriever(index_b)
    hits = r._par_reference("pourvoi n° 20-18.893", None)
    assert hits and all("20-18893" in p["meta"]["numeros_pourvoi"] for p in hits)


def test_b4_une_connexion_en_lecture_par_fil(index_b):
    r = LocalRetriever(index_b)
    cons = []

    def lire():
        r._q("SELECT 1")
        cons.append(r._con)

    fils = [threading.Thread(target=lire) for _ in range(2)]
    for f in fils:
        f.start()
    for f in fils:
        f.join()
    assert len({id(c) for c in cons}) == 2
    with pytest.raises(sqlite3.OperationalError):
        r._con.execute("CREATE TABLE essai (x)")   # lecture seule


# --- B5, B6 : grands arrets administratifs, nom d'un grand arret dans un cours --------------

from api.grands_arrets import GRANDS_ARRETS_ADMINISTRATIFS, decisions_administratives_citees  # noqa: E402
from api.references import references_non_couvertes  # noqa: E402

BLANCO, NICOLO = "CETATEXT000007605886", "CETATEXT000007742504"


@pytest.mark.parametrize("question, attendu", [
    ("Que retient l'arrêt Blanco ?", (BLANCO,)),
    ("Expliquez la jurisprudence Nicolo", (NICOLO,)),
    ("Arrêt Commune de Morsang-sur-Orge et dignité humaine", ("CETATEXT000007877723",)),
    ("L'arrêt Benjamin du Conseil d'État", ("CETATEXT000007636694",)),
    ("Paul Blanco a été blessé par un camion", ()),          # nom courant sans contexte
    ("Benjamin veut résilier son bail", ()),
])
def test_b5_grands_arrets_administratifs_par_nom(question, attendu):
    assert decisions_administratives_citees(question) == attendu
    assert extraire(question).decisions_admin == attendu


def test_b5_identifiants_uniques():
    ids = [d for _, d, _, _ in GRANDS_ARRETS_ADMINISTRATIFS]
    assert len(ids) == len(set(ids)) and all(d.startswith("CETATEXT") for d in ids)


def test_b5_servi_par_la_recherche(tmp_path):
    con = sqlite3.connect(tmp_path / "lexia.sqlite")
    con.executescript("CREATE TABLE passages (rowid INTEGER PRIMARY KEY, id TEXT, source_id TEXT, type TEXT,"
                      " numero TEXT, doc_id TEXT, en_vigueur INTEGER, empreinte TEXT, data TEXT);"
                      "CREATE VIRTUAL TABLE passages_fts USING fts5(entete, texte, source);")
    p = {"id": "conseil_etat:blanco", "source_id": "conseil_etat", "texte": "Enfant blessé",
         "meta": {"id_dila": BLANCO}}
    con.execute("INSERT INTO passages VALUES (1, 'conseil_etat:blanco', 'conseil_etat', 'sommaire', NULL, ?, NULL,"
                " 'e', ?)", (BLANCO, json.dumps(p)))
    con.commit()
    con.close()
    r = LocalRetriever(tmp_path)
    assert [h["id"] for h in r._par_reference("l'arrêt Blanco", None)] == ["conseil_etat:blanco"]
    assert r._par_reference("l'arrêt Blanco", ("code_civil",)) == []


def test_b5_citation_non_couverte_nommee():
    assert references_non_couvertes("Selon l'arrêt Nicolo, le juge contrôle...", []) == [
        "CE, ass., 20 octobre 1989, Nicolo"]
    assert references_non_couvertes("Selon l'arrêt Nicolo...", [{"meta": {"id_dila": NICOLO}, "texte": ""}]) == []


def test_b6_nom_d_un_grand_arret_dans_un_cours_couvre_la_citation():
    cours = [{"entete": "Mon cours « Responsabilité »", "texte": "Depuis l'arrêt Blieck (1991), la responsabilité "
              "générale du fait d'autrui... Le TC, dans l'arrêt Blanco, ...", "meta": {"cours": 1}}]
    assert references_non_couvertes("L'arrêt Blieck a consacré un principe général de responsabilité.", cours) == []
    assert references_non_couvertes("L'arrêt Blanco fonde l'autonomie du droit administratif.", cours) == []
    # un autre grand arret, absent du cours, reste signale
    assert references_non_couvertes("L'arrêt Chronopost...", cours) == ["pourvoi 93-18.632"]


# --- B8 : derniere mise a jour reussie ----------------------------------------------------

from datetime import datetime, timezone  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from ingest import fraicheur  # noqa: E402


def test_b8_fraicheur(tmp_path):
    assert fraicheur.a_jour(tmp_path) is None                       # rien pour en juger
    (tmp_path / "index").mkdir()
    (tmp_path / "index" / "archives.txt").write_text("LEGI_x\n")      # index construit par la mise a jour
    assert fraicheur.a_jour(tmp_path) is True
    (tmp_path / fraicheur.MARQUEUR).write_text("2026-11-16T04:41:02+01:00\n")
    maintenant = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
    assert fraicheur.a_jour(tmp_path, maintenant) is True
    assert fraicheur.a_jour(tmp_path, datetime(2026, 11, 17, 18, 0, tzinfo=timezone.utc)) is False


def test_b8_sante(tmp_path, index_b):
    from api.config import Settings
    from api.main import create_app

    (tmp_path / "index").symlink_to(index_b)
    app = create_app(Settings(index_dir=tmp_path / "index", logs_dir=tmp_path / "logs"),
                     retriever=LocalRetriever(index_b), llm=object())
    assert TestClient(app).get("/sante").json() == {"statut": "ok"}
    (tmp_path / fraicheur.MARQUEUR).write_text("2020-01-01T04:30:00+01:00\n")
    assert TestClient(app).get("/sante").json() == {"statut": "ok", "corpus_a_jour": False}
    local = TestClient(app, client=("127.0.0.1", 50000)).get("/sante").json()
    assert local["corpus_mis_a_jour_le"] == "2020-01-01T04:30:00+01:00" and local["corpus_a_jour"] is False


def test_b8_alerte_sans_configuration(monkeypatch, capsys):
    monkeypatch.setattr(fraicheur, "ROOT", Path("/inexistant"))
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    assert fraicheur.main(["--alerte", "essai"]) == 1
    assert "essai" in capsys.readouterr().err


# --- B7 : date de la decision la plus recente par source ------------------------------------

def test_b7_fraicheur_par_source(index_b):
    con = sqlite3.connect(index_b / "lexia.sqlite")
    dates = dict(con.execute("SELECT source_id, date FROM fraicheur"))
    con.close()
    assert set(dates) == {"judilibre"} and dates["judilibre"][:4].isdigit()   # articles sans date : absents
    assert LocalRetriever(index_b).stats()["derniere_decision"] == dates


# --- B11 : liens Legifrance -----------------------------------------------------------------

def test_b11_liens_legifrance():
    code = _numero("1", "code_civil", "Code civil", "LEGIARTI000000000010")
    assert code.url == "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000000000010"
    assert _numero("L24", "livre_procedures_fiscales", "LPF", "LEGIARTI1").url.startswith(
        "https://www.legifrance.gouv.fr/codes/")
    for src in ("lois", "ddhc_1789", "preambule_1946"):
        assert _numero("1", src, "Texte", "LEGIARTI2").url == "https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI2"


# --- B10 : bruit du corpus ------------------------------------------------------------------

@pytest.mark.parametrize("texte", ["I. Paragraphe modificateur\n\nII. (Abrogé).", "Alinéa modificateur",
                                   "(texte non reproduit).", "I. - (abrogé).\n\nII. - (paragraphe modificateur)."])
def test_b10_article_sans_contenu_ecarte(texte):
    assert legi.sans_contenu(texte.split("\n\n"))


def test_b10_article_avec_contenu_garde():
    assert not legi.sans_contenu(["L'article 467-1 du même code est abrogé."])
    assert not legi.sans_contenu(["I. Paragraphe modificateur", "II. Le présent article entre en vigueur..."])


def test_b10_version_de_duree_nulle_ecartee():
    assert _article("VIGUEUR", "1976-07-01", "1976-07-01") is None          # C. civ. 214
    assert _article("MODIFIE", "2000-01-01", "1999-01-01") is None
    assert _article("MODIFIE_MORT_NE", "2027-01-01", "2026-07-29") is not None
    assert _article("MODIFIE", "1976-07-01", "1980-01-01") is not None


def test_b10_sommaire_reduit_a_un_titre_ecarte():
    brut = (FIX / "cass_moderne.xml").read_text(encoding="utf-8")
    assert any(p.type == "sommaire" for p in cass.parse_arret(brut.encode(), date_recuperation="d", version="v"))
    debut, fin = brut.index("<SOMMAIRE>"), brut.index("</SOMMAIRE>")
    titre = brut[:debut] + '<SOMMAIRE><SCT ID="1" TYPE="PRINCIPAL">PRET</SCT>' + brut[fin:]
    passages = cass.parse_arret(titre.encode(), date_recuperation="d", version="v")
    assert passages and not any(p.type == "sommaire" for p in passages)


def test_b10_passage_repete_dans_une_decision(tmp_path):
    base = dict(source_id="judilibre", type="motifs", numero=None, url="u", texte="même texte", entete="e",
                meta={"id_dila": "JURITEXT1"}, empreinte="x")
    lignes = [dict(base, id="judilibre:JURITEXT1:1"), dict(base, id="judilibre:JURITEXT1:2"),
              dict(base, id="judilibre:JURITEXT2:1", meta={"id_dila": "JURITEXT2"})]
    (tmp_path / "p").mkdir()
    (tmp_path / "p" / "j.jsonl").write_text("\n".join(json.dumps(l) for l in lignes))
    build(passages_dir=tmp_path / "p", index_dir=tmp_path / "i", cache_dir=tmp_path / "c", model="aucun")
    con = sqlite3.connect(tmp_path / "i" / "lexia.sqlite")
    assert [r[0] for r in con.execute("SELECT id FROM passages ORDER BY rowid")] == [
        "judilibre:JURITEXT1:1", "judilibre:JURITEXT2:1"]


# --- B9 : bloc de constitutionnalite --------------------------------------------------------

from api.textes import codes_cites  # noqa: E402
from ingest.sources import codes as codes_src, constit  # noqa: E402


def _charte():
    p = legi.parse_article((FIX / "charte_environnement_LEGIARTI000006276527.xml").read_bytes(),
                           date_recuperation="d", version_archive="a", source_id="lois", nom=None)
    return codes_src.decouper_charte(p)


def test_b9_charte_decoupee_en_articles():
    ps = _charte()
    assert [p.numero for p in ps] == ["PREAMBULE"] + [str(i) for i in range(1, 11)]
    art5 = next(p for p in ps if p.numero == "5")
    assert art5.source_id == "charte_environnement" and art5.texte.startswith("Lorsque la réalisation d'un dommage")
    assert "principe de précaution" in art5.texte
    assert art5.entete.startswith("Charte de l'environnement, article 5 (en vigueur")
    assert ps[0].texte.startswith("Le peuple français") and "Proclame" in ps[0].texte
    assert len({p.id for p in ps}) == 11 and all(p.meta["en_vigueur"] for p in ps)


@pytest.mark.parametrize("question", ["Que dit l'article 5 de la Charte de l'environnement ?",
                                      "article 5 de la Charte", "Article 1er de la charte de l'environnement"])
def test_b9_charte_reconnue(question):
    assert codes_cites(question) == ("charte_environnement",)


def test_b9_autres_chartes_non_reconnues():
    # depuis D98, la Charte des droits fondamentaux est dans le corpus, sous son propre nom
    assert codes_cites("la Charte des droits fondamentaux de l'Union") == ("charte_droits_fondamentaux_ue",)
    assert codes_cites("la charte sociale européenne") == ()


def test_b9_decisions_l():
    assert extraire("décision n° 91-166 L du 13 juin 1991").decisions_cc == ("91-166 L",)
    assert extraire("loi n° 2005-205 l'article 2").decisions_cc == ()
    assert extraire("loi n° 2005-205 L'article 2").decisions_cc == ()
    assert "L" in constit.NATURES


# --- B7 : fraicheur affichee dans le site ---------------------------------------------------

def test_b7_date_des_textes(tmp_path):
    assert fraicheur.date_textes(tmp_path) is None
    (tmp_path / "archives.txt").write_text("Freemium_legi_global_20261108-140000.tar.gz\nLEGI_20261117-212708.tar.gz\n"
                                           "JADE_20261118-212708.tar.gz\nFreemium_cass_global_20261108-140000.tar.gz\n")
    assert fraicheur.date_textes(tmp_path) == "2026-11-17"


def test_b7_route_publique_en_cache(tmp_path, index_b, monkeypatch):
    from api.config import Settings
    from api.main import create_app

    (tmp_path / "index").symlink_to(index_b)
    r = LocalRetriever(index_b)
    appels = []
    monkeypatch.setattr(r, "dernieres_decisions", lambda: appels.append(1) or {"judilibre": "2026-09-17"})
    monkeypatch.setattr(fraicheur, "date_textes", lambda d: "2026-11-17")
    app = create_app(Settings(index_dir=tmp_path / "index", logs_dir=tmp_path / "logs"), retriever=r, llm=object())
    c = TestClient(app)
    f = c.get("/fraicheur").json()
    assert f["textes"] == "2026-11-17"
    assert f["sources"]["judilibre"] == {"nom": "Cour de cassation : chambres civiles, Assemblée plénière, chambre mixte",
                                         "date": "2026-09-17", "nature": "jurisprudence",
                                         "origine": "v"}   # version de la decision la plus recente (D113)
    assert f["sources"]["code_civil"] == {"nom": "Code civil", "date": "2026-11-17", "nature": "textes"}
    assert "constitution_1958" not in f["sources"]   # absente de cet index
    c.get("/fraicheur")
    assert appels == [1]   # calcule une fois, puis servi depuis le cache


def test_src5_constitution_datee(tmp_path, monkeypatch):
    """Audit du 2026-11-19, SRC-5 : la Constitution n'avait aucune date dans la fraicheur des sources."""
    from api.config import Settings
    from api.main import create_app

    class Index:
        def get(self, pid):
            return {"date_recuperation": "2026-11-11T02:10:30+00:00"} if pid == "constitution_1958:preambule" else None

        def dernieres_decisions(self):
            return {}
    monkeypatch.setattr(fraicheur, "date_textes", lambda d: "2026-11-17")
    c = TestClient(create_app(Settings(index_dir=tmp_path, logs_dir=tmp_path / "logs"), retriever=Index(), llm=object()))
    assert c.get("/fraicheur").json()["sources"]["constitution_1958"] == {
        "nom": "Constitution de 1958", "date": "2026-11-11", "nature": "textes"}


def test_b7_dernieres_decisions_index_sans_table(index_b, tmp_path):
    import shutil
    copie = tmp_path / "ancien"
    shutil.copytree(index_b, copie)
    con = sqlite3.connect(copie / "lexia.sqlite")
    con.execute("DROP TABLE fraicheur")
    con.commit()
    con.close()
    assert LocalRetriever(copie).dernieres_decisions() == LocalRetriever(index_b).dernieres_decisions() != {}
