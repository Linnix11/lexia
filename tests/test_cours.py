"""Cours deposes : extraction, depot, limites, recherche, confidentialite entre comptes."""

import io
import sqlite3
import time
import zipfile

import pytest
from fastapi.testclient import TestClient

from api.comptes import Comptes
from api.config import Settings
from api.cours import ErreurCours, decouper, extraire_texte
from api.extraction import extraire_isole
from api.main import create_app
from tests.test_comptes import Retriever, inscrire

COURS = ("Le dol est une manoeuvre destinée à tromper le cocontractant pour obtenir son consentement.\n\n"
         "La sanction du dol est la nullité relative du contrat, et des dommages et intérêts.\n\n" * 3)
REPONSE = {"statut": "reponse", "titre": "Le dol", "droit_positif": [{"texte": "Le dol vicie le consentement.", "sources": ["S1"]}],
           "explication": [], "points_incertains": [], "message": ""}


class LLM:
    def __init__(self):
        self.prompts = []

    def generate_json(self, *, prompt, **kw):
        self.prompts.append(prompt)
        return REPONSE, "fake"


def pdf_minimal(texte: str) -> bytes:
    """PDF d'une page avec du texte (sans dependance) ; les decalages xref sont calcules."""
    flux = f"BT /F1 12 Tf 50 750 Td ({texte}) Tj ET".encode("latin-1")
    objets = [b"<< /Type /Catalog /Pages 2 0 R >>",
              b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
              b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
              b"<< /Length %d >>\nstream\n" % len(flux) + flux + b"\nendstream",
              b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    sortie, positions = bytearray(b"%PDF-1.4\n"), []
    for i, o in enumerate(objets, start=1):
        positions.append(len(sortie))
        sortie += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(sortie)
    sortie += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objets) + 1)
    sortie += b"".join(b"%010d 00000 n \n" % p for p in positions)
    sortie += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objets) + 1, xref)
    return bytes(sortie)


def docx_minimal(paragraphes: list[str]) -> bytes:
    corps = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphes)
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as z:
        z.writestr("word/document.xml", f'<w:document xmlns:w="x"><w:body>{corps}</w:body></w:document>')
    return tampon.getvalue()


def test_extraction_des_formats():
    texte = "Le dol est une manoeuvre destinee a tromper le cocontractant. " * 5
    pages = extraire_texte("cours.pdf", pdf_minimal(texte))
    assert pages[0][0] == 1 and "manoeuvre" in pages[0][1]
    assert "R &amp; D" not in extraire_texte("c.docx", docx_minimal(["Titre", "R &amp; D"]))[0][1]
    assert extraire_texte("c.txt", "Bonjour".encode())[0][1] == "Bonjour"
    with pytest.raises(ErreurCours, match="Format"):
        extraire_texte("c.exe", b"x")
    with pytest.raises(ErreurCours, match="pas de texte"):
        extraire_texte("scan.pdf", pdf_minimal("x"))
    passages = decouper([(1, "Premier paragraphe.\n\nSecond paragraphe."), (2, "a. " * 2000)])
    assert passages[0] == (1, 1, "Premier paragraphe.\nSecond paragraphe.") and all(len(t) <= 3000 for *_, t in passages)


@pytest.fixture
def env(tmp_path):
    comptes, llm = Comptes(tmp_path / "comptes.db"), LLM()
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0),
                     retriever=Retriever(), llm=llm, comptes=comptes)
    return app, comptes, llm, tmp_path / "comptes.db"


def deposer(client, titre="Le dol", contenu=COURS.encode(), fichier="dol.txt", matiere="droit_civil"):
    """Comme le site : nom et titre en en-tetes encodes, hors de l'adresse (ecrite dans les journaux)."""
    from urllib.parse import quote
    return client.post("/cours", params={"matiere": matiere}, content=contenu,
                       headers={"Content-Type": "application/octet-stream",
                                "X-Lexia-Fichier": quote(fichier), "X-Lexia-Titre": quote(titre)})


def test_nom_et_titre_accentues_lus_dans_les_en_tetes(env):
    app, _, _, _ = env
    client = TestClient(app)
    inscrire(client)
    r = deposer(client, titre="Les sûretés réelles", fichier="Sûretés Dupont.txt")
    assert r.status_code == 201 and r.json()["titre"] == "Les sûretés réelles"
    assert r.json()["fichier"] == "Sûretés Dupont.txt"


def test_depot_liste_limite_et_suppression(env):
    app, comptes, _, base = env
    client = TestClient(app)
    assert deposer(client).status_code == 401                              # compte requis
    inscrire(client)
    r = deposer(client)
    assert r.status_code == 201 and r.json()["statut"] == "pret" and r.json()["passages"] >= 1
    assert deposer(client, matiere="inconnue").status_code == 422
    deposer(client, titre="Deux"), deposer(client, titre="Trois")
    r = deposer(client, titre="Quatre")
    assert r.status_code == 422 and "Limite atteinte : 3 cours" in r.json()["detail"]   # formule gratuite
    liste = client.get("/cours").json()
    assert len(liste["cours"]) == 3 and liste["maximum"] == 3
    cid = liste["cours"][0]["id"]
    assert client.post(f"/cours/{cid}/supprimer").status_code == 204
    assert len(client.get("/cours").json()["cours"]) == 2
    with sqlite3.connect(base) as c:                                        # texte retire de l'index aussi
        assert c.execute("SELECT count(*) FROM cours_fts").fetchone()[0] == \
            c.execute("SELECT count(*) FROM cours_passages").fetchone()[0]


def test_chat_sur_mon_cours_uniquement_puis_avec_les_textes_officiels(env):
    app, _, llm, _ = env
    client = TestClient(app)
    inscrire(client)
    cid = deposer(client).json()["id"]
    r = client.post("/chat", json={"question": "Quelle est la sanction du dol ?", "cours": [cid], "avec_officiel": False}).json()
    assert r["statut"] == "reponse" and r["sources"][0]["source_id"] == "cours_perso"
    assert "Mon cours « Le dol »" in llm.prompts[-1] and "Code civil" not in llm.prompts[-1]
    assert "révise SON cours" in llm.prompts[-1]

    client.post("/chat", json={"question": "Quelle est la sanction du dol ?", "cours": [cid], "avec_officiel": True})
    assert "Mon cours « Le dol »" in llm.prompts[-1] and "Code civil, article 1240" in llm.prompts[-1]
    assert "complète-le avec les sources officielles" in llm.prompts[-1]


def test_un_cours_reste_prive(env):
    app, comptes, llm, base = env
    alice, bob = TestClient(app), TestClient(app)
    inscrire(alice, email="alice@exemple.fr")
    inscrire(bob, email="bob@exemple.fr")
    cid = deposer(alice).json()["id"]
    r = alice.post("/chat", json={"question": "sanction du dol", "cours": [cid], "avec_officiel": False}).json()
    pid = r["sources"][0]["id"]
    assert alice.get(f"/sources/{pid}").json()["texte"].startswith("Le dol")
    assert alice.get(f"/sources/{pid}/vigueur").json()["applicable"] is False
    assert bob.get(f"/sources/{pid}").status_code == 404                   # ni lecture...
    assert bob.post(f"/cours/{cid}/supprimer").status_code == 422          # ...ni suppression par un autre
    nb = len(llm.prompts)
    bob.post("/chat", json={"question": "sanction du dol", "cours": [cid], "avec_officiel": False})
    assert "Mon cours" not in llm.prompts[-1] or len(llm.prompts) == nb    # le cours d'Alice n'est jamais lu

    comptes.supprimer(comptes.par_email("alice@exemple.fr").id)             # suppression du compte
    with sqlite3.connect(base) as c:
        assert c.execute("SELECT count(*) FROM cours").fetchone()[0] == 0
        assert c.execute("SELECT count(*) FROM cours_fts").fetchone()[0] == 0


def test_fichier_word_piege_refuse_sans_tout_decompresser():
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("word/document.xml", "<w:p>" + "a" * 30_000_000 + "</w:p>")   # 30 Mo -> ~30 Ko compresses
    assert len(tampon.getvalue()) < 100_000
    with pytest.raises(ErreurCours, match="anormalement volumineux"):
        extraire_texte("piege.docx", tampon.getvalue())


def test_fichier_word_aux_paragraphes_jamais_fermes_refuse_vite():
    """L'ancienne expression reguliere prenait 2 s pour 40 Ko et des heures pour 10 Mo (tout le site bloque)."""
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("word/document.xml", '<w:document xmlns:w="x">' + "<w:p>" * 2_000_000)   # 10 Mo
    debut = time.monotonic()
    with pytest.raises(ErreurCours, match="illisible"):
        extraire_texte("piege.docx", tampon.getvalue())
    # Seuil large : l'ancienne lecture prenait des heures ; une machine chargee ne doit pas faire echouer le test.
    assert time.monotonic() - debut < 60


def test_fichier_word_texte_paragraphes_et_entites():
    texte = extraire_texte("c.docx", docx_minimal(["Titre", "R &amp; D", "a &lt; b"]))[0][1]
    assert texte.split("\n") == ["Titre", "R & D", "a < b"]


def test_pdf_trop_de_pages(monkeypatch):
    import api.extraction as extraction
    monkeypatch.setattr(extraction, "PAGES_MAX", 0)
    with pytest.raises(ErreurCours, match="Document trop long"):
        extraire_texte("c.pdf", pdf_minimal("Le dol est une manoeuvre destinee a tromper le cocontractant. " * 5))


def test_depots_limites_par_jour(env, monkeypatch):
    import api.cours as cours
    monkeypatch.setattr(cours, "DEPOTS_PAR_JOUR", 2)
    app, _, _, _ = env
    client = TestClient(app)
    inscrire(client)
    for _ in range(2):
        cid = deposer(client).json()["id"]
        assert client.post(f"/cours/{cid}/supprimer").status_code == 204    # deposer / retirer en boucle...
    r = deposer(client)
    assert r.status_code == 422 and "Trop de dépôts" in r.json()["detail"]   # ...est plafonne


def test_un_depot_refuse_ne_consomme_pas_d_essai(tmp_path, monkeypatch):
    """Une suite de refus (limite de la formule atteinte) ne doit pas epuiser le quota du jour."""
    import api.cours as cours_mod
    from api.comptes import Comptes
    from api.cours import Cours, ErreurCours

    monkeypatch.setattr(cours_mod, "DEPOTS_PAR_JOUR", 4)
    chemin = tmp_path / "t.db"
    u = Comptes(chemin).creer("a@b.fr", "motdepasse-solide")
    c = Cours(chemin)
    for i in range(3):
        c.ajouter(u.id, "droit_civil", f"Cours {i}", f"c{i}.txt", b"Le dol est une manoeuvre.", 3)
    for _ in range(5):  # cinq refus : la formule n'autorise que trois cours
        with pytest.raises(ErreurCours, match="Limite atteinte"):
            c.ajouter(u.id, "droit_civil", "Refuse", "x.txt", b"texte", 3)
    c.supprimer(u.id, c.lister(u.id)[0]["id"])
    c.ajouter(u.id, "droit_civil", "Nouveau", "n.txt", b"La bonne foi.", 3)  # 4e depot reussi : accepte


def test_une_lecture_de_fichier_refusee_compte_un_essai(tmp_path, monkeypatch):
    """Un fichier refuse a la lecture coute autant qu'un depot reussi : il se renvoyait sans limite."""
    import api.cours as cours_mod
    from api.cours import Cours

    monkeypatch.setattr(cours_mod, "DEPOTS_PAR_JOUR", 2)
    chemin = tmp_path / "t.db"
    u = Comptes(chemin).creer("a@b.fr", "motdepasse-solide")
    c = Cours(chemin)
    for _ in range(2):
        with pytest.raises(ErreurCours, match="illisible"):
            c.ajouter(u.id, "droit_civil", "Piege", "p.docx", b"pas un zip", 3)
    with pytest.raises(ErreurCours, match="Trop de dépôts"):
        c.ajouter(u.id, "droit_civil", "Vrai", "v.txt", b"Le dol est une manoeuvre.", 3)


def test_un_seul_depot_a_la_fois_par_compte(env, monkeypatch):
    """Deux depots paralleles du meme compte passaient tous deux la limite de cours de la formule."""
    import asyncio
    import threading

    import httpx

    from api.cours import Cours

    app, _, _, _ = env
    client = TestClient(app)
    inscrire(client)
    cookies = dict(client.cookies)
    lent = threading.Event()
    original = Cours.ajouter

    def ajouter_lent(self, *a, **k):
        lent.wait(5)
        return original(self, *a, **k)

    monkeypatch.setattr(Cours, "ajouter", ajouter_lent)

    async def deux_depots():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver",
                                     cookies=cookies) as ac:
            params = {"matiere": "droit_civil"}
            entetes = {"X-Lexia-Fichier": "dol.txt", "X-Lexia-Titre": "Le%20dol"}
            premier = asyncio.create_task(ac.post("/cours", params=params, headers=entetes, content=COURS.encode()))
            await asyncio.sleep(0.3)
            second = await ac.post("/cours", params=params, headers=entetes, content=COURS.encode())
            lent.set()
            return (await premier).status_code, second.status_code

    assert asyncio.run(deux_depots()) == (201, 429)


def _docx_brut(xml: str) -> bytes:
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("word/document.xml", xml)
    return tampon.getvalue()


def test_word_aux_entites_repetees_refuse_sans_rien_developper():
    """1 Ko de Word developpait 98 millions de caracteres (280 Mo) : expat accepte une amplification x100."""
    xml = ('<?xml version="1.0"?><!DOCTYPE d [<!ENTITY a "' + "x" * 290 + '">]>'
           '<w:document xmlns:w="x"><w:p><w:t>' + "&a;" * 340_000 + "</w:t></w:p></w:document>")
    debut = time.monotonic()
    with pytest.raises(ErreurCours, match="illisible"):
        extraire_texte("e.docx", _docx_brut(xml))
    assert time.monotonic() - debut < 30                      # ancienne lecture : 23 s et 1 Go a 10 Mo


def test_word_aux_balises_trop_imbriquees_refuse():
    with pytest.raises(ErreurCours, match="illisible"):
        extraire_texte("p.docx", _docx_brut('<w:document xmlns:w="x">' + "<a>" * 100_000 + "</a>" * 100_000 + "</w:document>"))


def test_word_trop_de_texte_arrete_en_cours_de_lecture(monkeypatch):
    import api.extraction as extraction
    monkeypatch.setattr(extraction, "CARACTERES_MAX", 10)
    with pytest.raises(ErreurCours, match="trop long"):
        extraire_texte("l.docx", docx_minimal(["un texte de plus de dix caracteres"]))


def test_lecture_isolee_dans_un_autre_processus():
    assert extraire_isole("c.docx", docx_minimal(["Titre", "R &amp; D"]))[0][1].split("\n") == ["Titre", "R & D"]
    with pytest.raises(ErreurCours, match="Format"):
        extraire_isole("c.exe", b"x")                       # l'erreur du processus de lecture est relayee


def test_lecture_trop_longue_refusee():
    """Un PDF dont les 1000 pages partagent un meme contenu compresse prenait 4 a 5 h : le processus est tue."""
    with pytest.raises(ErreurCours, match="trop de temps"):
        extraire_isole("c.txt", b"x" * 10, delai=0.001)


# --- lot C de l'audit du 2026-11-18 : qualite de lecture des cours deposes --------------------------------

from pathlib import Path  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "cours"


def pdf_pages(textes: list[str]) -> bytes:
    """PDF de plusieurs pages, une ligne de texte par element de la liste (decoupee sur « \\n »)."""
    objets = [b"<< /Type /Catalog /Pages 2 0 R >>", None,
              b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"]
    kids = []
    for texte in textes:
        lignes = " ".join(f"({ligne}) Tj 0 -14 Td" for ligne in texte.split("\n"))
        flux = f"BT /F1 11 Tf 50 750 Td {lignes} ET".encode("latin-1")
        objets.append(b"<< /Length %d >>\nstream\n" % len(flux) + flux + b"\nendstream")
        objets.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents %d 0 R "
                      b"/Resources << /Font << /F1 3 0 R >> >> >>" % len(objets))
        kids.append(len(objets))
    objets[1] = b"<< /Type /Pages /Kids [%s] /Count %d >>" % (b" ".join(b"%d 0 R" % k for k in kids), len(kids))
    sortie, positions = bytearray(b"%PDF-1.4\n"), []
    for i, o in enumerate(objets, start=1):
        positions.append(len(sortie))
        sortie += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    xref = len(sortie)
    sortie += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objets) + 1)
    sortie += b"".join(b"%010d 00000 n \n" % p for p in positions)
    sortie += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objets) + 1, xref)
    return bytes(sortie)


def _zip(membres: dict[str, str]) -> bytes:
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
        for nom, xml in membres.items():
            z.writestr(nom, xml)
    return tampon.getvalue()


PARAGRAPHE = ("La faute civile est définie comme la violation d'une obligation préexistante, appréciée "
              "in abstracto par référence au comportement d'une personne raisonnable placée dans les mêmes "
              "circonstances. ")


def test_c1_word_numerotation_notes_tabulations_et_tableaux():
    """Cours Word de l'auditeur : plan numerote, note de bas de page, tabulation, traits d'union, tableau."""
    texte = extraire_texte("c2.docx", (FIXTURES / "c2.docx").read_bytes())[0][1]
    lignes = texte.split("\n")
    assert "I. Les conditions communes" in lignes
    assert "A. Le caractère déterminant" in lignes
    assert "1. Le vice doit avoir été déterminant" in lignes
    assert "II. Les vices en particulier" in lignes                      # la numerotation continue
    assert "98-20.817" in texte                                           # note de bas de page lue
    assert "1131Les" not in texte and "Article 1131\tLes vices" in texte  # tabulation
    assert "non-rétroactivité" in texte and "contrepartie" in texte       # trait d'union insecable, cesure
    assert "partie\nsont distincts" in texte                              # saut de ligne
    assert "Dol | 1137 | Nullité relative et dommages-intérêts" in lignes  # une ligne de tableau par ligne


def test_c1_les_definitions_de_tabulation_du_paragraphe_ne_sont_pas_du_texte():
    xml = ('<w:document xmlns:w="x"><w:body><w:p><w:pPr><w:tabs><w:tab w:val="left" w:pos="720"/></w:tabs></w:pPr>'
           '<w:r><w:t>Titre</w:t></w:r></w:p></w:body></w:document>')
    assert extraire_texte("c.docx", _zip({"word/document.xml": xml}))[0][1] == "Titre"


def test_c9_powerpoint_et_opendocument():
    diapo = ('<p:sld xmlns:p="p" xmlns:a="a"><p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>{}</a:t></a:r></a:p>'
             '</p:txBody></p:sp></p:spTree></p:cSld></p:sld>')
    deux_lignes = diapo.format("Le dol</a:t></a:r><a:br/><a:r><a:t>La violence")
    pptx = _zip({"ppt/slides/slide2.xml": diapo.format("Le dol"), "ppt/slides/slide10.xml": diapo.format("La violence"),
                 "ppt/slides/slide1.xml": diapo.format("Les vices du consentement")})
    assert extraire_texte("c.pptx", pptx) == [(1, "Les vices du consentement"), (2, "Le dol"), (10, "La violence")]
    assert extraire_texte("c.pptx", _zip({"ppt/slides/slide1.xml": deux_lignes})) == [(1, "Le dol\nLa violence")]
    contenu = ('<office:document-content xmlns:office="o" xmlns:text="t"><office:body><office:text>'
               '<text:h>I. Le dol</text:h><text:p>Article 1137<text:tab/>Le dol<text:s text:c="2"/>est'
               '<text:note><text:note-citation>1</text:note-citation><text:note-body><text:p>Cass. com., 1994.'
               '</text:p></text:note-body></text:note> un vice.<text:line-break/>Fin.</text:p>'
               '</office:text></office:body></office:document-content>')
    texte = extraire_texte("c.odt", _zip({"content.xml": contenu}))[0][1]
    assert texte == "I. Le dol\nArticle 1137\tLe dol  est un vice.\nFin.\nNote 1 : Cass. com., 1994."


def test_c9_texte_windows_et_bom():
    assert extraire_texte("c.txt", (FIXTURES / "c3_cp1252.txt").read_bytes())[0][1].startswith(
        "Le cœur du contrat : l’article 1128 – consentement, capacité, contenu …")
    assert extraire_texte("c.txt", (FIXTURES / "c4_bom.txt").read_bytes())[0][1] == \
        "Introduction\nLe droit pénal spécial.\n"
    assert extraire_texte("c.txt", "Le dol".encode("utf-16"))[0][1] == "Le dol"


def test_c2_pdf_scanne_en_grande_partie_refuse():
    """19 pages scannees sur 20 (seul un numero de page en texte) : refuse, en disant pourquoi."""
    with pytest.raises(ErreurCours, match="19 pages sur 20 sans texte"):
        extraire_texte("scan.pdf", (FIXTURES / "scan.pdf").read_bytes())


def test_c2_quelques_pages_scannees_signalees(tmp_path):
    from api.cours import Cours

    chemin = tmp_path / "t.db"
    u = Comptes(chemin).creer("a@b.fr", "motdepasse-solide")
    c = Cours(chemin)
    fiche = c.ajouter(u.id, "droit_civil", "Faute", "f.pdf", pdf_pages([PARAGRAPHE * 2, "3", PARAGRAPHE * 2]), 3)
    assert fiche["avertissement"] == "Page 2 sans texte (scan ou image) : son contenu n'est pas pris en compte."
    assert c.lister(u.id)[0]["avertissement"] == fiche["avertissement"]


def test_c3_decoupage_sur_tout_le_texte_avec_le_plan_et_les_pages():
    pages = [(1, "I. Le fait générateur\nA. La faute\n" + PARAGRAPHE * 9 + "La faute de l'enfant est admise depuis"),
             (2, "1984 par l'assemblée plénière.\n" + PARAGRAPHE * 9 + "\nB. Le lien de causalité\n" + PARAGRAPHE * 3)]
    passages = decouper(pages)
    assert passages[0][2].startswith("[I. Le fait générateur]\nA. La faute\n")   # titre seul : pas de passage
    phrase = [p for p in passages if "admise depuis 1984" in " ".join(p[2].split())]
    assert phrase and phrase[0][:2] == (1, 2)                       # phrase coupee par la page : recollee
    assert passages[1][2].startswith("[I. Le fait générateur > A. La faute]\n")   # plan rappele en tete
    b = next(p for p in passages if "B. Le lien de causalité" in p[2])
    assert b[2].startswith("[I. Le fait générateur]\nB. Le lien") and b[:2] == (2, 2)


def test_c3_pages_d_un_passage_affichees_dans_l_entete(tmp_path):
    from api.cours import Cours

    chemin = tmp_path / "t.db"
    u = Comptes(chemin).creer("a@b.fr", "motdepasse-solide")
    c = Cours(chemin)
    c.ajouter(u.id, "droit_civil", "Long", "l.pdf", (FIXTURES / "c5_long.pdf").read_bytes(), 3)
    trouves = c.rechercher(u.id, [c.lister(u.id)[0]["id"]], "violence", 20)
    entetes = {p["entete"] for p in trouves}
    assert any(", pages " in e for e in entetes), entetes


def test_c4_cesures_et_ligatures():
    passages = decouper([(1, "la mise en jeu de la respon-\nsabilité civile, l'eﬃcacité du contrat "
                             "et le principe de non-\nrétroactivité."), (2, "")])
    texte = passages[0][2]
    assert "responsabilité civile" in texte and "efficacité" in texte and "non-rétroactivité" in texte


def test_c4_un_mot_coupe_se_retrouve_par_la_recherche(tmp_path):
    from api.cours import Cours

    chemin = tmp_path / "t.db"
    u = Comptes(chemin).creer("a@b.fr", "motdepasse-solide")
    c = Cours(chemin)
    cid = c.ajouter(u.id, "droit_civil", "Faute", "c1.pdf", (FIXTURES / "c1.pdf").read_bytes(), 3)["id"]
    assert any("responsabilité civile" in p["texte"] for p in c.rechercher(u.id, [cid], "responsabilité civile", 5))


def test_c11_entetes_et_numeros_de_page_retires():
    pages = extraire_texte("c1.pdf", (FIXTURES / "c1.pdf").read_bytes())
    texte = "\n".join(p[2] for p in decouper(pages))
    assert "Pr. Martin" not in texte                              # en-tete repete sur chaque page
    assert not any(ligne.strip() == "2" for ligne in texte.split("\n"))   # numero de page
    assert "Chapitre 2. La responsabilité du fait personnel" in texte


def test_c5_mon_cours_seulement_une_explication_sans_source_est_signalee():
    from api.citations import valider_reponse

    table = {"S1": {"id": "cours:1:1", "texte": "Le dol est une manoeuvre.", "source_id": "cours_perso"}}
    brut = {"statut": "reponse", "titre": "Le dol",
            "droit_positif": [{"texte": "Le dol vicie le consentement.", "sources": ["S1"]}],
            "explication": [{"texte": "La réticence dolosive est aussi un dol.", "sources": []},
                            {"texte": "Le dol suppose une manoeuvre.", "sources": ["S1"]}],
            "points_incertains": []}
    reponse, _ = valider_reponse(brut, table, cours_seul=True)
    assert [e["texte"] for e in reponse["explication"]] == ["Le dol suppose une manoeuvre."]
    assert reponse["points_incertains"][0]["texte"].startswith("Hors de votre cours, à vérifier : La réticence")
    reponse, _ = valider_reponse(brut, table)                      # avec les textes officiels : inchange
    assert len(reponse["explication"]) == 2


def test_c6_ancien_numero_du_cours_signale_dans_la_reponse(env):
    app, _, _, _ = env
    client = TestClient(app)
    inscrire(client)
    cours = ("La responsabilité du fait personnel repose sur l'article 1382 du Code civil : tout fait "
             "quelconque de l'homme qui cause à autrui un dommage oblige à le réparer.\n\n") * 3
    cid = deposer(client, titre="Responsabilité", contenu=cours.encode()).json()["id"]
    r = client.post("/chat", json={"question": "Quel est le fondement de la responsabilité du fait personnel ?",
                                   "cours": [cid], "avec_officiel": False}).json()
    assert r["statut"] == "reponse"
    alerte = [p for p in r["points_incertains"] if "1382" in p["texte"]]
    assert alerte and "1240" in alerte[0]["texte"] and alerte[0]["sources"]


def _octets(chemin) -> bytes:
    return b"".join(Path(f"{chemin}{s}").read_bytes() for s in ("", "-wal") if Path(f"{chemin}{s}").exists())


def test_c7_cours_retire_absent_des_octets_de_la_base_et_de_la_sauvegarde(tmp_path):
    import os
    import subprocess
    import sys

    from api.cours import Cours

    chemin = tmp_path / "donnees" / "lexia.db"
    chemin.parent.mkdir()
    comptes = Comptes(chemin)
    u = comptes.creer("a@b.fr", "motdepasse-solide")
    c = Cours(chemin)
    secret = "Zorglubienne"
    garde = c.ajouter(u.id, "droit_civil", "Garde", "g.txt", b"La bonne foi contractuelle.", 5)
    cid = c.ajouter(u.id, "droit_civil", "Secret", "s.txt",
                    f"La theorie {secret} du consentement {secret}ment eclaire.".encode() * 40, 5)["id"]
    assert secret.encode() in _octets(chemin)
    c.supprimer(u.id, cid)
    assert secret.encode() not in _octets(chemin)                  # ni la base, ni le journal WAL
    assert secret.lower().encode() not in _octets(chemin).lower()  # ni les mots de l'index plein texte
    assert c.fiche(u.id, garde["id"])["titre"] == "Garde"

    racine = Path(__file__).resolve().parent.parent
    sauvegardes = tmp_path / "sauvegardes"
    r = subprocess.run(["bash", str(racine / "deploy" / "sauvegarder_comptes.sh")], capture_output=True, text=True,
                       env={**os.environ, "LEXIA_RACINE": str(racine), "LEXIA_BASE": str(chemin),
                            "LEXIA_SAUVEGARDES": str(sauvegardes), "LEXIA_PYTHON": sys.executable})
    assert r.returncode == 0, r.stderr
    copies = list(sauvegardes.glob("lexia-*.db"))
    assert len(copies) == 1 and secret.lower().encode() not in copies[0].read_bytes().lower()
    with sqlite3.connect(copies[0]) as s:
        assert s.execute("SELECT count(*) FROM cours").fetchone()[0] == 1


def test_c10_vectorisation_en_erreur_relancee_sans_redemarrage(tmp_path, monkeypatch):
    import api.cours as cours_mod
    from api.cours import Cours

    class Embedder:
        panne = True

        def embed_documents(self, textes):
            if self.panne:
                raise RuntimeError("modele indisponible")
            return [[1.0, 0.0] for _ in textes]

    monkeypatch.setattr(cours_mod, "RELANCE_VECTORISATION", 0)
    chemin = tmp_path / "t.db"
    u = Comptes(chemin).creer("a@b.fr", "motdepasse-solide")
    e = Embedder()
    c = Cours(chemin, e)
    cid = c.ajouter(u.id, "droit_civil", "Dol", "d.txt", b"Le dol est une manoeuvre.", 3)["id"]
    c._fil.submit(lambda: None).result()
    assert c.fiche(u.id, cid)["statut"] == "erreur"
    e.panne = False
    assert c.lister(u.id)[0]["statut"] == "traitement"               # relance a la consultation de la liste
    c._fil.submit(lambda: None).result()
    assert c.fiche(u.id, cid)["statut"] == "pret"
