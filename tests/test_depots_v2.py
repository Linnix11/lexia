"""Depots de cours, version 2 (D107, docs/depots-v2.md) : OCR des scans et des photos, RTF, apercu, modification,
et securite de la lecture (fichier piege, archive trop decompressee, image geante, processus tues)."""

import io
import os
import stat
import struct
import time
import zipfile
import zlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api import extraction
from api.comptes import Comptes
from api.cours import Cours
from api.extraction import ErreurCours, dimensions_image, extraire_texte, lire, lire_isole, ocr_disponible
from tests.test_comptes import inscrire
from tests.test_cours import deposer, env, pdf_pages  # noqa: F401 - env : fixture

FIXTURES = Path(__file__).parent / "fixtures" / "cours"
PHOTO = FIXTURES / "photo_cours.jpg"
PARAGRAPHE = ("La responsabilité civile délictuelle suppose une faute, un dommage et un lien de causalité. "
              "Chacune de ces conditions est appréciée souverainement par les juges du fond. ")
avec_ocr = pytest.mark.skipif(not ocr_disponible(), reason="tesseract ou pdftoppm absent")


def pdf_avec_images(pages: list[str | bytes]) -> bytes:
    """PDF dont chaque page est soit du texte, soit une photo JPEG pleine page (comme un scan)."""
    objets: list[bytes | None] = [b"<< /Type /Catalog /Pages 2 0 R >>", None,
                                  b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"]
    kids, images = [], {}
    for page in pages:
        if isinstance(page, bytes):
            if page not in images:
                _, larg, haut = dimensions_image(page)
                sof = page.index(b"\xff\xc0")
                couleurs = b"/DeviceGray" if page[sof + 9] == 1 else b"/DeviceRGB"
                objets.append(b"<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace %s "
                              b"/BitsPerComponent 8 /Filter /DCTDecode /Length %d >>\nstream\n"
                              % (larg, haut, couleurs, len(page))
                              + page + b"\nendstream")
                images[page] = len(objets)
            flux = b"q 612 0 0 792 0 0 cm /Im1 Do Q"
            ressources = b"<< /XObject << /Im1 %d 0 R >> >>" % images[page]
        else:
            lignes = " ".join(f"({ligne}) Tj 0 -14 Td" for ligne in page.split("\n"))
            flux = f"BT /F1 11 Tf 50 750 Td {lignes} ET".encode("latin-1")
            ressources = b"<< /Font << /F1 3 0 R >> >>"
        objets.append(b"<< /Length %d >>\nstream\n" % len(flux) + flux + b"\nendstream")
        objets.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents %d 0 R /Resources %s >>"
                      % (len(objets), ressources))
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


def png_entete(largeur: int, hauteur: int) -> bytes:
    """PNG minuscule qui declare des dimensions geantes (image « bombe »)."""
    ihdr = struct.pack(">IIBBBBB", largeur, hauteur, 8, 0, 0, 0, 0)
    morceau = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))  # noqa: E731
    return (b"\x89PNG\r\n\x1a\n" + morceau(b"IHDR", ihdr) + morceau(b"IDAT", zlib.compress(b"\x00" * 1000))
            + morceau(b"IEND", b""))


# --- OCR -------------------------------------------------------------------------------------------------

@avec_ocr
def test_photo_de_cours_lue_par_ocr():
    for nom in ("photo_cours.jpg", "photo_cours.png"):
        lecture = lire_isole(nom, (FIXTURES / nom).read_bytes())
        assert lecture.ocr == [1]
        texte = lecture.pages[0][1]
        assert "Article 1240 du Code civil" in texte and "lien de causalite" in texte


@avec_ocr
def test_pdf_en_partie_scanne_lu_par_ocr_et_signale(tmp_path):
    pdf = pdf_avec_images([PARAGRAPHE * 3, PHOTO.read_bytes()])
    lecture = lire_isole("cours.pdf", pdf)
    assert lecture.ocr == [2] and "Article 1240" in lecture.pages[1][1]
    chemin = tmp_path / "t.db"
    u = Comptes(chemin).creer("a@b.fr", "motdepasse-solide")
    fiche = Cours(chemin).ajouter(u.id, "droit_civil", "Faute", "f.pdf", pdf, 3)
    assert fiche["avertissement"] == ("Page 2 lue par reconnaissance de caractères (scan) : "
                                      "vérifiez le texte dans l'aperçu.")
    assert fiche["pages"] == 2


@avec_ocr
def test_pdf_entierement_scanne_accepte_grace_a_l_ocr():
    lecture = lire_isole("scan.pdf", pdf_avec_images([PHOTO.read_bytes()] * 2))
    assert lecture.ocr == [1, 2]


def test_trop_de_pages_scannees_refuse_avant_tout_ocr(monkeypatch):
    monkeypatch.setattr(extraction, "ocr_disponible", lambda: True)
    monkeypatch.setattr(extraction, "_ocr_pdf", lambda *a: pytest.fail("OCR lance"))
    pdf = pdf_avec_images([PHOTO.read_bytes()] * (extraction.OCR_PAGES_MAX + 1))
    with pytest.raises(ErreurCours, match="21 pages scannées : la lecture des scans est limitée à 20 pages"):
        lire("scan.pdf", pdf)


def test_sans_ocr_scan_et_photo_refuses_clairement(monkeypatch):
    monkeypatch.setenv("LEXIA_OCR", "0")
    with pytest.raises(ErreurCours, match="lecture des photos de cours est momentanément indisponible"):
        lire_isole("photo.jpg", PHOTO.read_bytes())
    with pytest.raises(ErreurCours, match=r"\(2 pages sur 2 sans texte\).*momentanément indisponible"):
        lire_isole("scan.pdf", pdf_avec_images([PHOTO.read_bytes()] * 2))


# --- securite : image geante, faux fichiers, processus tues -------------------------------------------------

def test_image_geante_refusee_sans_etre_decodee(monkeypatch):
    """Un PNG de 1 Ko qui se declare en 100 000 x 100 000 pixels reclamerait 10 Go une fois decode."""
    monkeypatch.setattr(extraction, "_tesseract", lambda *a: pytest.fail("image decodee"))
    with pytest.raises(ErreurCours, match="Photo trop grande \\(100000 x 100000 pixels"):
        lire("bombe.png", png_entete(100_000, 100_000))
    with pytest.raises(ErreurCours, match="Photo trop grande"):
        lire("large.png", png_entete(20_000, 100))          # cote trop long, peu de pixels
    jpeg = PHOTO.read_bytes()
    i = jpeg.index(b"\xff\xc0")
    geant = jpeg[:i + 5] + struct.pack(">HH", 60_000, 60_000) + jpeg[i + 9:]
    assert dimensions_image(geant) == ("jpeg", 60_000, 60_000)
    with pytest.raises(ErreurCours, match="Photo trop grande"):
        lire("bombe.jpg", geant)
    with pytest.raises(ErreurCours, match="Photo trop grande"):
        lire_isole("bombe.png", png_entete(100_000, 100_000))  # aussi par le processus de lecture


def test_faux_fichier_image_refuse():
    """Un executable ou un TIFF renomme en .jpg n'est jamais confie a Tesseract."""
    for contenu in (b"MZ\x90\x00" + b"\x00" * 100, b"II*\x00" + b"\x00" * 100, b"", b"\xff\xd8\xff\xd9"):
        with pytest.raises(ErreurCours, match="pas un JPEG ou un PNG lisible"):
            lire("photo.jpg", contenu)


def _faux_programme(dossier: Path, nom: str, script: str) -> None:
    chemin = dossier / nom
    chemin.write_text("#!/bin/sh\n" + script)
    chemin.chmod(chemin.stat().st_mode | stat.S_IEXEC)


def test_ocr_trop_long_tue_avec_tout_son_groupe(tmp_path, monkeypatch):
    """Au-dela du delai, tesseract (lance par le processus de lecture) est tue lui aussi."""
    pid = tmp_path / "pid"
    _faux_programme(tmp_path, "tesseract", f"echo $$ > {pid}\nexec sleep 30\n")
    _faux_programme(tmp_path, "pdftoppm", "exit 1\n")
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    debut = time.monotonic()
    with pytest.raises(ErreurCours, match="trop de temps"):
        lire_isole("photo.jpg", PHOTO.read_bytes(), delai=3)
    assert time.monotonic() - debut < 10
    numero = int(pid.read_text())
    time.sleep(0.2)
    with pytest.raises(ProcessLookupError):
        os.kill(numero, 0)


def test_ocr_sans_les_cles_du_serveur(tmp_path, monkeypatch):
    """Tesseract, lance par le processus de lecture, ne voit pas les cles du serveur (audit du 19/11, SEC-3)."""
    sortie = tmp_path / "env"
    _faux_programme(tmp_path, "tesseract", f"env > {sortie}\necho Article 1240 du Code civil, la faute et le dommage, "
                    "le lien de causalite entre les deux\n")
    _faux_programme(tmp_path, "pdftoppm", "exit 1\n")
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("GEMINI_API_KEY", "cle-secrete")
    monkeypatch.setenv("CLE_SECRETS", "autre-cle")
    assert lire_isole("photo.jpg", PHOTO.read_bytes()).ocr == [1]
    env = sortie.read_text()
    assert "cle-secrete" not in env and "autre-cle" not in env and "OMP_THREAD_LIMIT=1" in env


def test_ocr_borne_dans_le_processus_de_lecture(tmp_path, monkeypatch):
    """Le processus de lecture arrete lui-meme l'OCR a son echeance, avec un message clair."""
    _faux_programme(tmp_path, "tesseract", "exec sleep 30\n")
    _faux_programme(tmp_path, "pdftoppm", "exit 1\n")
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setattr(extraction, "DELAI_OCR", 1)
    with pytest.raises(ErreurCours, match="La lecture de ce scan prend trop de temps"):
        lire("photo.jpg", PHOTO.read_bytes())


def test_archive_trop_decompressee_refusee():
    """OpenDocument et PowerPoint : 60 Mo de XML compresses en quelques dizaines de Ko."""
    for nom, membre in (("c.odt", "content.xml"), ("c.pptx", "ppt/slides/slide1.xml")):
        tampon = io.BytesIO()
        with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(membre, "<a>" + " " * 60_000_000 + "</a>")
        assert len(tampon.getvalue()) < 200_000
        debut = time.monotonic()
        with pytest.raises(ErreurCours, match="anormalement volumineux"):
            lire_isole(nom, tampon.getvalue())
        assert time.monotonic() - debut < 10


# --- RTF -------------------------------------------------------------------------------------------------

RTF = (rb"{\rtf1\ansi\ansicpg1252\deff0{\fonttbl{\f0 Times New Roman;}}{\colortbl;\red0\green0\blue0;}"
       rb"{\*\generator Word;}{\info{\author Dupont}}"
       rb"\pard I. La responsabilit\'e9 du fait d'autrui\par "
       rb"Article 1242 \endash  alin\'e9a 1er : \ldblquote on est responsable\rdblquote .\par"
       rb"{\pict\pngblip 89504e470d0a1a0a}"
       rb"Le r\u233?gime \u8217?est objectif.\par"
       rb"\trowd Parents\cell Article 1242 al. 4\cell\row"
       rb"{\*\bkmkstart x}Fin\bin5 {{{{}\par}")


def test_rtf_lu_sans_polices_images_ni_metadonnees():
    texte = extraire_texte("c.rtf", RTF)[0][1]
    assert texte.split("\n") == ["I. La responsabilité du fait d'autrui",
                                 "Article 1242 – alinéa 1er : “on est responsable”.",
                                 "Le régime ’est objectif.", "Parents | Article 1242 al. 4 |", "Fin"]
    assert "Dupont" not in texte and "Times" not in texte and "8950" not in texte


def test_rtf_piege_refuse_ou_borne():
    with pytest.raises(ErreurCours, match="RTF est illisible"):
        extraire_texte("c.rtf", b"{\\rtf1" + b"{" * 100_000 + b"}" * 100_000)    # groupes imbriques sans fin
    with pytest.raises(ErreurCours, match="RTF est illisible"):
        extraire_texte("c.rtf", b"MZ pas du tout un rtf")
    assert extraire_texte("c.rtf", b"{\\rtf1 Debut\\bin99999999999 xx}")[0][1] == "Debut"   # \bin plus long que le fichier
    with pytest.raises(ErreurCours, match="trop long"):
        extraire_texte("c.rtf", b"{\\rtf1 " + b"a" * 1_100_000 + b"}")
    debut = time.monotonic()
    extraire_texte("c.rtf", b"{\\rtf1 " + b"\\par " * 200_000 + b"}")          # beaucoup de jetons : rapide
    assert time.monotonic() - debut < 5


# --- routes : apercu, modification -------------------------------------------------------------------------

def test_apercu_et_modification_d_un_cours(env):  # noqa: F811
    app, comptes, _, _ = env
    client = TestClient(app)
    inscrire(client)
    cid = deposer(client).json()["id"]
    r = client.get(f"/cours/{cid}/apercu")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    assert r.json()["passages"] >= 1 and "dol" in r.json()["apercu"][0]["texte"]
    r = client.post(f"/cours/{cid}/modifier", json={"titre": "  Les vices du consentement ", "matiere": "droit_penal"})
    assert r.status_code == 200
    assert (r.json()["titre"], r.json()["matiere"]) == ("Les vices du consentement", "droit_penal")
    assert client.post(f"/cours/{cid}/modifier", json={"matiere": "inconnue"}).status_code == 422
    assert client.post(f"/cours/{cid}/modifier", json={"titre": "   "}).status_code == 422
    assert client.post(f"/cours/{cid}/modifier", json={"titre": "Seul"}).json()["matiere"] == "droit_penal"

    autre = TestClient(app)
    inscrire(autre, "autre@exemple.fr")
    assert autre.get(f"/cours/{cid}/apercu").status_code == 404
    assert autre.post(f"/cours/{cid}/modifier", json={"titre": "Vol"}).status_code == 422
    assert client.get(f"/cours/{cid}/apercu").json()["titre"] == "Seul"


def test_formats_annonces_par_l_api(env):  # noqa: F811
    app, *_ = env
    client = TestClient(app)
    inscrire(client)
    assert {".rtf", ".jpg", ".jpeg", ".png"} <= set(client.get("/cours").json()["formats"])
