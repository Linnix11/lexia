"""Cours deposes : extraction, depot, limites, recherche, confidentialite entre comptes."""

import io
import sqlite3
import zipfile

import pytest
from fastapi.testclient import TestClient

from api.comptes import Comptes
from api.config import Settings
from api.cours import ErreurCours, decouper, extraire_texte
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
    assert passages[0] == (1, "Premier paragraphe.\nSecond paragraphe.") and all(len(t) <= 3000 for _, t in passages)


@pytest.fixture
def env(tmp_path):
    comptes, llm = Comptes(tmp_path / "comptes.db"), LLM()
    app = create_app(Settings(gemini_models=("fake",), logs_dir=tmp_path / "logs", rate_limit_per_minute=0),
                     retriever=Retriever(), llm=llm, comptes=comptes)
    return app, comptes, llm, tmp_path / "comptes.db"


def deposer(client, titre="Le dol", contenu=COURS.encode(), fichier="dol.txt", matiere="droit_civil"):
    return client.post("/cours", params={"matiere": matiere, "fichier": fichier, "titre": titre}, content=contenu,
                       headers={"Content-Type": "application/octet-stream"})


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


def test_pdf_trop_de_pages(monkeypatch):
    import api.cours as cours
    monkeypatch.setattr(cours, "PAGES_MAX", 0)
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
