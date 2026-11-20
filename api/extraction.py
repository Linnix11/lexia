"""Lecture du texte d'un cours depose (PDF, Word, OpenDocument, PowerPoint, RTF, texte, photo), dans un processus
a part.

Un fichier piege pouvait bloquer ou faire tomber tout le serveur (audit de securite du 2026-11-16) :
- un PDF de 150 Ko dont les 1000 pages partagent un meme contenu compresse : 4 a 5 h de calcul ;
- un Word aux entites XML repetees ou aux balises imbriquees : 1 Go de memoire pour 10 Ko envoyes.
Le service n'a qu'un processus : un calcul ou une memoire sans fin le bloquaient pour tous. La lecture se
fait donc dans un processus Python separe (extraire_isole), limite en duree et en memoire, que l'on tue
au-dela. Ce module n'importe que la bibliotheque standard et pypdf : le processus demarre vite.

Pages scannees d'un PDF et photos (JPEG, PNG) : lues par OCR (Tesseract en francais, pdftoppm pour rendre la
page), programmes lances par le processus de lecture lui-meme. Ils heritent de ses limites, et tout le groupe de
processus est tue au-dela du delai (D107, docs/depots-v2.md).

    python -m api.extraction <nom du fichier>  < contenu
        ->  {"pages": [[page, texte], ...], "ocr": [pages lues par OCR]} ou {"erreur": ...}
"""

from __future__ import annotations

import codecs
import io
import json
import os
import re
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import NamedTuple
from xml.parsers import expat

CARACTERES_MAX = 1_000_000          # texte extrait au plus
PAGES_MAX = 1000                    # pages d'un PDF
XML_WORD_MAX = 10 * 1024 * 1024     # un fichier XML decompresse (word/document.xml...) : au-dela, archive piegee
XML_TOTAL_MAX = 3 * XML_WORD_MAX    # tous les fichiers XML lus d'une archive (diapositives, notes...)
PART_SCANNEE_MAX = 0.5              # PDF refuse au-dela de cette part de pages sans texte (scan, photo)
PROFONDEUR_MAX = 200                # balises imbriquees dans un document Word (Word en fait moins de 20)
DELAI_LECTURE = 60                  # secondes pour lire un fichier, au-dela il est refuse
MEMOIRE_LECTURE = 768 * 1024 * 1024  # memoire du processus de lecture
FORMATS = {".pdf": "PDF", ".docx": "Word", ".odt": "OpenDocument", ".pptx": "PowerPoint", ".rtf": "RTF",
           ".txt": "texte", ".md": "texte", ".jpg": "photo", ".jpeg": "photo", ".png": "photo"}
FORMATS_OCR = {".pdf", ".jpg", ".jpeg", ".png"}  # formats qui peuvent passer par l'OCR
OCR_PAGES_MAX = 20                  # pages scannees lues par OCR dans un fichier
DELAI_OCR = 75                      # secondes d'OCR au plus pour un fichier (Cloudflare coupe une requete a 100 s)
DELAI_LECTURE_OCR = 90              # delai du processus de lecture quand le fichier peut passer par l'OCR
RENDU_COTE = 3300                   # cote le plus long d'une page rendue pour l'OCR (A4 a 280 dpi environ)
IMAGE_PIXELS_MAX = 50_000_000       # photo : 50 megapixels au plus (lus dans l'en-tete, avant tout decodage)
IMAGE_COTE_MAX = 12_000             # photo : 12 000 pixels de cote au plus
RTF_GROUPES_MAX = 200               # groupes { } imbriques dans un RTF
RACINE = Path(__file__).resolve().parent.parent
ILLISIBLE_SCAN = ("Ce document scanné est illisible{detail} : vérifiez que le scan ou la photo est net, droit et "
                  "bien éclairé, puis déposez-le de nouveau.")


class ErreurCours(ValueError):
    """Erreur presentable a l'etudiant."""


class Lecture(NamedTuple):
    pages: list[tuple[int | None, str]]   # [(page, texte)] ; page = None quand le format n'a pas de pages
    ocr: list[int]                        # pages lues par OCR (scan, photo)


def ocr_disponible() -> bool:
    """Tesseract et pdftoppm installes (paquets tesseract-ocr, tesseract-ocr-fra, poppler-utils), et OCR non
    coupe par LEXIA_OCR=0."""
    return os.environ.get("LEXIA_OCR", "1") != "0" and bool(shutil.which("tesseract") and shutil.which("pdftoppm"))


def _env_lecteur() -> dict[str, str]:
    """Environnement minimal : le lecteur de fichiers n'herite pas des cles du serveur (Gemini, Groq, Resend,
    CLE_SECRETS), qu'une faille de pypdf, zipfile, expat, pdftoppm ou tesseract lui donnerait sinon (audit du
    19/11, SEC-3). Seuls les dossiers de tesseract et pdftoppm s'ajoutent au PATH (/usr/bin sur le serveur), et
    les reglages de l'OCR (LEXIA_OCR, TESSDATA_PREFIX) et le dossier temporaire (TMPDIR) passent."""
    dossiers = ["/usr/bin", "/bin"]
    for programme in ("tesseract", "pdftoppm"):
        chemin = shutil.which(programme)
        if chemin and str(Path(chemin).parent) not in dossiers:
            dossiers.append(str(Path(chemin).parent))
    env = {"PATH": os.pathsep.join(dossiers), "LANG": "C.UTF-8"}
    env.update({k: os.environ[k] for k in ("LEXIA_OCR", "TESSDATA_PREFIX", "TMPDIR") if k in os.environ})
    return env


def lire_isole(nom: str, contenu: bytes, delai: float | None = None) -> Lecture:
    """lire dans un processus separe, tue avec tout son groupe (tesseract, pdftoppm) au-dela du delai."""
    if delai is None:
        delai = DELAI_LECTURE_OCR if Path(nom).suffix.lower() in FORMATS_OCR and ocr_disponible() else DELAI_LECTURE
    # Groupe de processus a part : subprocess.run(timeout=...) ne tuait que le processus Python, un tesseract
    # lance par lui aurait continue a calculer.
    p = subprocess.Popen([sys.executable, "-m", "api.extraction", nom], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=RACINE, start_new_session=True,
                         env=_env_lecteur())
    try:
        stdout, _ = p.communicate(contenu, timeout=delai)
    except subprocess.TimeoutExpired:
        raise ErreurCours("La lecture de ce fichier prend trop de temps : il est refusé. "
                          "Déposez une version plus simple (texte exporté en PDF ou Word).") from None
    finally:
        try:
            os.killpg(p.pid, signal.SIGKILL)  # restes du groupe (processus fils orphelins), puis le processus
        except (ProcessLookupError, PermissionError):
            pass
        if p.poll() is None:
            p.kill()
        p.communicate()
    try:
        sortie = json.loads(stdout) if p.returncode == 0 else {}
    except ValueError:
        sortie = {}
    if "erreur" in sortie:
        raise ErreurCours(sortie["erreur"])
    if "pages" not in sortie:
        raise ErreurCours("Ce fichier n'a pas pu être lu (trop lourd ou endommagé) : il est refusé.")
    return Lecture([(page, texte) for page, texte in sortie["pages"]], list(sortie.get("ocr", [])))


def extraire_isole(nom: str, contenu: bytes, delai: float | None = None) -> list[tuple[int | None, str]]:
    """Pages lues dans un processus separe (voir lire_isole)."""
    return lire_isole(nom, contenu, delai).pages


def extraire_texte(nom: str, contenu: bytes) -> list[tuple[int | None, str]]:
    """[(page, texte)] ; page = None quand le format n'a pas de pages. A appeler via extraire_isole."""
    return lire(nom, contenu).pages


def lire(nom: str, contenu: bytes) -> Lecture:
    _ECHEANCE_OCR[0] = time.monotonic() + DELAI_OCR
    ext = Path(nom).suffix.lower()
    if ext not in FORMATS:
        raise ErreurCours("Format non pris en charge : déposez un PDF, un fichier Word (.docx), OpenDocument (.odt), "
                          "PowerPoint (.pptx), RTF, un texte (.txt, .md) ou une photo (JPEG, PNG).")
    if ext == ".pdf":
        return _texte_pdf(contenu)
    if ext in (".jpg", ".jpeg", ".png"):
        return _texte_photo(contenu)
    if ext == ".rtf":
        return Lecture([(None, _texte_rtf(contenu))], [])
    if ext in (".docx", ".odt", ".pptx"):
        illisible = f"Ce fichier {FORMATS[ext]} est illisible ou endommagé."
        try:
            with zipfile.ZipFile(io.BytesIO(contenu)) as z:
                return Lecture(_texte_zip(ext, z, illisible), [])
        except (zipfile.BadZipFile, KeyError, RuntimeError, NotImplementedError):
            # RuntimeError : membre chiffre ; NotImplementedError : compression inconnue
            raise ErreurCours(illisible) from None
    return Lecture([(None, _texte_brut(contenu))], [])


def _texte_brut(contenu: bytes) -> str:
    """Texte UTF-8 (avec ou sans BOM), UTF-16 (Bloc-notes « Unicode ») ou Windows-1252 (ancien Bloc-notes)."""
    if contenu.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return contenu.decode("utf-16", errors="replace")
    try:
        return contenu.decode("utf-8-sig")
    except UnicodeDecodeError:
        return contenu.decode("cp1252", errors="replace")  # latin-1 rendait « œ », « ’ », « – » illisibles


def _texte_pdf(contenu: bytes) -> Lecture:
    from pypdf import PdfReader
    from pypdf.errors import PyPdfError

    try:
        lecteur = PdfReader(io.BytesIO(contenu))
        if lecteur.is_encrypted:
            raise ErreurCours("Ce PDF est protégé par un mot de passe : déposez une version sans protection.")
        if len(lecteur.pages) > PAGES_MAX:
            raise ErreurCours(f"Document trop long ({len(lecteur.pages)} pages, {PAGES_MAX} au plus) : "
                              "découpez-le en plusieurs cours.")
        pages, total = [], 0
        for i, p in enumerate(lecteur.pages, start=1):
            texte = p.extract_text() or ""
            total += len(texte)
            if total > CARACTERES_MAX:
                raise ErreurCours("Document trop long : découpez-le en plusieurs cours.")
            pages.append((i, texte))
        vides = pages_sans_texte(pages)
        # Page sans texte ni image (blanche, ou texte dessine en traits) : rien a lire par OCR.
        a_lire = [n for n in vides if len(lecteur.pages[n - 1].images) > 0] if vides and ocr_disponible() else []
    except (PyPdfError, ValueError, KeyError) as e:  # PyPdfError : aussi les limites internes de pypdf
        if isinstance(e, ErreurCours):
            raise
        raise ErreurCours("Ce PDF est illisible ou endommagé.") from None
    ocr: list[int] = []
    if a_lire:
        if len(a_lire) > OCR_PAGES_MAX:
            raise ErreurCours(f"Ce PDF compte {len(a_lire)} pages scannées : la lecture des scans est limitée à "
                              f"{OCR_PAGES_MAX} pages par fichier. Découpez-le en plusieurs cours.")
        lues = _ocr_pdf(contenu, a_lire)
        pages = [(n, lues.get(n, t)) for n, t in pages]
        ocr = sorted(n for n, t in lues.items() if t.strip())
        vides = pages_sans_texte(pages)
    # Seuil global seul (200 caracteres), un PDF de 20 pages dont 19 scannees passait sans rien dire (audit C2).
    if sum(len(t.strip()) for _, t in pages) < 200 or len(vides) > len(pages) * PART_SCANNEE_MAX:
        detail = f" ({len(vides)} pages sur {len(pages)} sans texte)" if len(pages) > 1 else ""
        if a_lire:
            raise ErreurCours(ILLISIBLE_SCAN.format(detail=detail))
        if not ocr_disponible():
            raise ErreurCours(f"Ce PDF ne contient pas de texte{detail} : c'est un scan ou des photos, et la "
                              "lecture des documents scannés est momentanément indisponible.")
        raise ErreurCours(f"Ce PDF ne contient pas de texte lisible{detail}.")
    return Lecture(pages, ocr)


def pages_sans_texte(pages: list[tuple[int | None, str]]) -> list[int]:
    """Pages d'un PDF sans texte lisible (scan, photo) : moins de 15 lettres, numero de page compris."""
    return [p for p, t in pages if p is not None and len(re.sub(r"[\W\d_]+", "", t)) < 15]


# --- OCR : pages scannees et photos -------------------------------------------------------------------------

def _env_ocr() -> dict:
    # Un seul fil de calcul par OCR : deux lectures en meme temps (DEPOTS_SIMULTANES) prennent deux coeurs.
    return {**os.environ, "OMP_THREAD_LIMIT": "1"}


_ECHEANCE_OCR = [0.0]  # instant ou l'OCR du fichier en cours doit etre fini (fixe au debut de lire)


def _reste(message: str) -> float:
    reste = _ECHEANCE_OCR[0] - time.monotonic()
    if reste <= 0:
        raise ErreurCours(message)
    return reste


TROP_LONG_OCR = (f"La lecture de ce scan prend trop de temps ({DELAI_OCR} s au plus) : découpez-le en plusieurs "
                 "cours de quelques pages.")


def _tesseract(image: str) -> str | None:
    """Texte d'une image (chemin) par Tesseract en francais ; None si l'image n'a pas pu etre lue."""
    try:
        r = subprocess.run(["tesseract", image, "stdout", "-l", "fra", "--psm", "3"], capture_output=True,
                           timeout=_reste(TROP_LONG_OCR), env=_env_ocr())
    except subprocess.TimeoutExpired:
        raise ErreurCours(TROP_LONG_OCR) from None
    if r.returncode != 0:
        if b"Failed loading language" in r.stderr:  # paquet tesseract-ocr-fra absent
            raise ErreurCours("La lecture des documents scannés est momentanément indisponible.")
        return None
    return r.stdout.decode("utf-8", errors="replace")


def _ocr_pdf(contenu: bytes, numeros: list[int]) -> dict[int, str]:
    """{page: texte lu par OCR} pour les pages demandees d'un PDF (rendues une a une par pdftoppm)."""
    lues: dict[int, str] = {}
    with tempfile.TemporaryDirectory(prefix="lexia-ocr-") as dossier:
        pdf = Path(dossier) / "cours.pdf"
        pdf.write_bytes(contenu)
        for n in numeros:
            image = Path(dossier) / f"p{n}"
            try:
                # -scale-to : cote le plus long fixe, quelle que soit la taille de page declaree (une page de
                # 5 m de cote a 300 dpi ferait 3,5 milliards de pixels).
                r = subprocess.run(["pdftoppm", "-f", str(n), "-l", str(n), "-singlefile", "-gray", "-png",
                                    "-scale-to", str(RENDU_COTE), str(pdf), str(image)],
                                   capture_output=True, timeout=_reste(TROP_LONG_OCR))
            except subprocess.TimeoutExpired:
                raise ErreurCours(TROP_LONG_OCR) from None
            png = image.with_suffix(".png")
            if r.returncode == 0 and png.exists():
                texte = _tesseract(str(png))
                if texte is not None:
                    lues[n] = texte
                png.unlink()
    return lues


def dimensions_image(contenu: bytes) -> tuple[str, int, int]:
    """(format, largeur, hauteur) lus dans l'en-tete d'un PNG ou d'un JPEG, sans decoder l'image."""
    if contenu.startswith(b"\x89PNG\r\n\x1a\n") and contenu[12:16] == b"IHDR" and len(contenu) >= 24:
        largeur, hauteur = struct.unpack(">II", contenu[16:24])
        return "png", largeur, hauteur
    if contenu.startswith(b"\xff\xd8"):
        i = 2
        while i + 9 <= len(contenu):
            if contenu[i] != 0xFF:
                break
            marqueur = contenu[i + 1]
            if marqueur == 0xFF:      # octet de remplissage
                i += 1
                continue
            if marqueur in (0xD8, 0x01) or 0xD0 <= marqueur <= 0xD7:  # marqueurs sans longueur
                i += 2
                continue
            if marqueur in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                hauteur, largeur = struct.unpack(">HH", contenu[i + 5:i + 9])
                return "jpeg", largeur, hauteur
            if marqueur in (0xD9, 0xDA):  # fin d'image ou debut des donnees sans en-tete de trame
                break
            i += 2 + struct.unpack(">H", contenu[i + 2:i + 4])[0]
    raise ErreurCours("Cette image n'est pas un JPEG ou un PNG lisible : enregistrez la photo en JPEG ou en PNG.")


def _texte_photo(contenu: bytes) -> Lecture:
    fmt, largeur, hauteur = dimensions_image(contenu)
    if not largeur or not hauteur:
        raise ErreurCours("Cette photo est illisible ou endommagée.")
    if largeur > IMAGE_COTE_MAX or hauteur > IMAGE_COTE_MAX or largeur * hauteur > IMAGE_PIXELS_MAX:
        raise ErreurCours(f"Photo trop grande ({largeur} x {hauteur} pixels, {IMAGE_PIXELS_MAX // 1_000_000} "
                          "mégapixels au plus) : réduisez-la ou prenez-la en 12 mégapixels.")
    if not ocr_disponible():
        raise ErreurCours("La lecture des photos de cours est momentanément indisponible : déposez un PDF, "
                          "un Word ou un texte.")
    with tempfile.TemporaryDirectory(prefix="lexia-ocr-") as dossier:
        image = Path(dossier) / f"photo.{'png' if fmt == 'png' else 'jpg'}"
        image.write_bytes(contenu)
        texte = _tesseract(str(image))
    if texte is None:
        raise ErreurCours("Cette photo est illisible ou endommagée.")
    if len(re.sub(r"[\W\d_]+", "", texte)) < 40:
        raise ErreurCours(ILLISIBLE_SCAN.format(detail=" (presque aucun texte reconnu)"))
    if len(texte) > CARACTERES_MAX:
        raise ErreurCours("Document trop long : découpez-le en plusieurs cours.")
    return Lecture([(1, texte)], [1])


# --- RTF -------------------------------------------------------------------------------------------------

# Groupes dont le contenu n'est pas du texte du cours : polices, couleurs, styles, images, objets, metadonnees.
_RTF_IGNORES = {"fonttbl", "colortbl", "stylesheet", "info", "pict", "object", "themedata", "colorschememapping",
                "datastore", "latentstyles", "listtable", "listoverridetable", "rsidtbl", "generator",
                "xmlnstbl", "mmathPr", "fldinst", "header", "headerl", "headerr", "headerf", "footer", "footerl",
                "footerr", "footerf", "filetbl", "revtbl", "pgdsctbl", "shppict", "nonshppict", "bkmkstart",
                "bkmkend", "xe", "tc", "listtext", "pntext", "pntxta", "pntxtb", "falt", "panose", "blipuid"}
_RTF_CARACTERES = {"par": "\n", "line": "\n", "sect": "\n\n", "page": "\n", "tab": "\t", "cell": " | ",
                   "row": "\n", "emdash": "\u2014", "endash": "\u2013", "bullet": "\u2022", "lquote": "\u2018",
                   "rquote": "\u2019", "ldblquote": "\u201c", "rdblquote": "\u201d", "~": "\u00a0", "_": "-",
                   "-": ""}
_RTF_JETON = re.compile(r"\\([a-zA-Z]{1,32})(-?\d{1,10})? ?|\\'([0-9a-fA-F]{2})|\\(.)|([{}])|[\r\n]+|([^\\{}\r\n]+)",
                        re.DOTALL)


def _texte_rtf(contenu: bytes) -> str:
    """Texte d'un RTF, lu au fil des jetons sans arbre : groupes bornes, images et polices sautees."""
    if not contenu.lstrip().startswith(b"{\\rtf"):
        raise ErreurCours("Ce fichier RTF est illisible ou endommagé.")
    brut = contenu.decode("latin-1")   # RTF est en ASCII ; les octets binaires (\bin) restent des caracteres
    page_code = "cp1252"
    morceaux: list[str] = []
    total = 0
    pile: list[tuple[bool, int]] = []  # (groupe ignore, nombre de caracteres de repli apres \uN)
    ignore, uc, a_sauter = False, 1, 0
    octets: list[int] = []             # \'hh consecutifs, decodes ensemble (caracteres sur deux octets)
    position = 0

    def ecrire(texte: str) -> None:
        nonlocal total
        if not ignore and texte:
            total += len(texte)
            if total > CARACTERES_MAX:
                raise ErreurCours("Document trop long : découpez-le en plusieurs cours.")
            morceaux.append(texte)

    def vider_octets() -> None:
        if octets:
            ecrire(bytes(octets).decode(page_code, errors="replace"))
            octets.clear()

    while position < len(brut):
        m = _RTF_JETON.match(brut, position)
        if m is None:
            break
        position = m.end()
        mot, nombre, hexa, symbole, accolade, texte = m.groups()
        if hexa is not None:
            if a_sauter:
                a_sauter -= 1
            else:
                octets.append(int(hexa, 16))
            continue
        vider_octets()
        if a_sauter and (texte or symbole):  # caracteres de repli d'un \uN
            n = len(texte) if texte else 1
            if texte and n > a_sauter:
                texte = texte[a_sauter:]
                a_sauter = 0
            else:
                a_sauter -= n
                continue
        if accolade == "{":
            pile.append((ignore, uc))
            if len(pile) > RTF_GROUPES_MAX:
                raise ErreurCours("Ce fichier RTF est illisible ou endommagé.")
        elif accolade == "}":
            if pile:
                ignore, uc = pile.pop()
        elif mot is not None:
            a_sauter = 0
            if mot == "bin":    # donnees binaires : sautees sans etre lues
                position += max(0, min(int(nombre or 0), len(brut) - position))
            elif mot in _RTF_IGNORES:
                ignore = True
            elif mot == "ansicpg" and nombre and nombre.isdigit():
                try:
                    page_code = codecs.lookup(f"cp{nombre}").name
                except LookupError:
                    pass
            elif mot == "uc" and nombre:
                uc = max(0, min(int(nombre), 10))
            elif mot == "u" and nombre:
                n = int(nombre)
                ecrire(chr(n + 65536 if n < 0 else n) if -32768 <= n <= 1114111 and not 0xD800 <= (n % 65536) <= 0xDFFF
                       else "\ufffd")
                a_sauter = uc
            elif mot in _RTF_CARACTERES:
                ecrire(_RTF_CARACTERES[mot])
        elif symbole is not None:
            if symbole == "*":      # destination facultative inconnue : ignoree
                ignore = True
            elif symbole in _RTF_CARACTERES:
                ecrire(_RTF_CARACTERES[symbole])
            elif symbole in "\\{}":
                ecrire(symbole)
        elif texte is not None:
            ecrire(texte)
    vider_octets()
    return re.sub(r"[ \t]*\n[ \t]*", "\n", "".join(morceaux)).strip()


# --- Word, OpenDocument, PowerPoint : archives zip de fichiers XML ----------------------------------------------

def _membre(z: zipfile.ZipFile, nom: str, budget: list[int], obligatoire: bool = True) -> bytes | None:
    """Fichier XML de l'archive, lu de facon bornee (jamais plus que la limite en memoire)."""
    try:
        f = z.open(nom)
    except KeyError:
        if obligatoire:
            raise
        return None
    with f:
        brut = f.read(min(XML_WORD_MAX, budget[0]) + 1)
    budget[0] -= len(brut)
    if len(brut) > XML_WORD_MAX or budget[0] < 0:
        raise ErreurCours("Ce fichier est anormalement volumineux une fois décompressé : il est refusé.")
    return brut


def _texte_zip(ext: str, z: zipfile.ZipFile, illisible: str) -> list[tuple[int | None, str]]:
    budget, total = [XML_TOTAL_MAX], [0]
    if ext == ".odt":
        lecteur = _Lecteur(odf=True)
        _lire_xml(_membre(z, "content.xml", budget), lecteur, illisible, total)
        return [(None, lecteur.texte())]
    if ext == ".pptx":
        diapos = sorted((int(m.group(1)), n) for n in z.namelist()
                        if (m := re.fullmatch(r"ppt/slides/slide(\d+)\.xml", n)))
        if not diapos:
            raise ErreurCours(illisible)
        if len(diapos) > PAGES_MAX:
            raise ErreurCours(f"Document trop long ({len(diapos)} diapositives, {PAGES_MAX} au plus) : "
                              "découpez-le en plusieurs cours.")
        pages = []
        for numero, nom in diapos:
            lecteur = _Lecteur()
            _lire_xml(_membre(z, nom, budget), lecteur, illisible, total)
            pages.append((numero, lecteur.texte()))
        return pages
    # Word : numerotation automatique (« I. », « A. », « 1. ») et notes de bas de page, dans d'autres fichiers
    numerotation = _numerotation(_membre(z, "word/numbering.xml", budget, False), illisible, total)
    notes = _notes_word(_membre(z, "word/footnotes.xml", budget, False), illisible, total)
    lecteur = _Lecteur(numerotation=numerotation, notes=notes)
    _lire_xml(_membre(z, "word/document.xml", budget), lecteur, illisible, total)
    return [(None, lecteur.texte())]


def _lire_xml(xml: bytes | None, lecteur, illisible: str, total: list[int]) -> None:
    """Lecture au fil de l'eau sans construire d'arbre (expat), en appelant lecteur.debut / fin / donnees.

    Refuse toute declaration DOCTYPE ou ENTITY (Word n'en produit jamais) : expat accepte une
    amplification d'entites jusqu'a x100, soit 1 Go pour 10 Mo de document. Refuse aussi les
    imbrications profondes et s'arrete des que le texte depasse CARACTERES_MAX.
    """
    if xml is None:
        return
    profondeur = [0]

    def refuser(*_):
        raise ErreurCours(illisible)

    def debut(nom, attributs):
        profondeur[0] += 1
        if profondeur[0] > PROFONDEUR_MAX:
            raise ErreurCours(illisible)
        lecteur.debut(nom.rsplit("}", 1)[-1], {k.rsplit("}", 1)[-1]: v for k, v in attributs.items()})

    def fin(nom):
        profondeur[0] -= 1
        lecteur.fin(nom.rsplit("}", 1)[-1])

    def donnees(d):
        if lecteur.capte():
            total[0] += len(d)
            if total[0] > CARACTERES_MAX:
                raise ErreurCours("Document trop long : découpez-le en plusieurs cours.")
            lecteur.ajouter(d)

    p = expat.ParserCreate(namespace_separator="}")
    p.StartDoctypeDeclHandler = refuser
    p.EntityDeclHandler = refuser
    p.StartElementHandler = debut
    p.EndElementHandler = fin
    p.CharacterDataHandler = donnees
    try:
        p.Parse(xml, True)
    except expat.ExpatError:
        raise ErreurCours(illisible) from None


class _Lecteur:
    """Paragraphes, numerotation, notes, tabulations et tableaux d'un document Word, PowerPoint ou OpenDocument.

    Word et PowerPoint (OOXML) : texte dans w:t / a:t, paragraphes w:p / a:p, tableaux tbl / tr / tc.
    OpenDocument : texte directement dans text:p et text:h, tableaux table / table-row / table-cell.
    Une ligne de tableau devient une ligne « cellule | cellule » ; une note devient « Note n : ... »
    juste apres son paragraphe (avant, les notes Word n'etaient jamais lues et le tableau se lisait mot a mot).
    """

    def __init__(self, odf: bool = False, numerotation: dict | None = None, notes: dict | None = None):
        self.odf = odf
        self.numerotation = numerotation or {}   # numId -> {niveau: (format, modele, depart)}
        self.notes = notes or {}                 # id de note Word -> texte
        self.compteurs: dict[str, dict[int, int]] = {}
        self.nb_notes = 0
        self.paragraphes: list[str] = []
        self.pile: list[dict] = []               # paragraphes ouverts (une note OpenDocument en contient un autre)
        self.tableaux: list[dict] = []
        self.dans_t = self.dans_r = self.ignorer = self.dans_note = 0

    def capte(self) -> bool:
        return bool(self.pile) and not self.ignorer and (self.odf or self.dans_t > 0)

    def ajouter(self, morceau: str) -> None:
        if self.pile:
            self.pile[-1]["morceaux"].append(morceau)

    def debut(self, nom: str, attr: dict) -> None:
        if nom == "p" or (self.odf and nom == "h"):
            self.pile.append({"morceaux": [], "num": None, "niveau": 0, "notes": []})
        elif nom in ("tbl", "table"):
            self.tableaux.append({"lignes": [], "cellules": [], "cellule": None})
        elif nom in ("tc", "table-cell") and self.tableaux:
            self.tableaux[-1]["cellule"] = []
        elif self.odf:
            if nom == "tab":
                self.ajouter("\t")
            elif nom == "line-break":
                self.ajouter("\n")
            elif nom == "s":
                self.ajouter(" " * min(int(attr.get("c") or 1) if (attr.get("c") or "1").isdigit() else 1, 100))
            elif nom == "note-citation":
                self.ignorer += 1
            elif nom == "note":
                self.dans_note += 1
        elif nom == "t":
            self.dans_t += 1
        elif nom == "r":
            self.dans_r += 1
        elif nom in ("br", "cr"):  # saut de ligne (dans un « run » Word, entre deux « runs » PowerPoint)
            self.ajouter("\n")
        elif self.dans_r and nom in ("tab", "noBreakHyphen"):  # hors d'un « run » : definition de tabulation
            self.ajouter("\t" if nom == "tab" else "-")
        elif nom == "numId" and self.pile:
            self.pile[-1]["num"] = attr.get("val")
        elif nom == "ilvl" and self.pile and (attr.get("val") or "").isdigit():
            self.pile[-1]["niveau"] = int(attr["val"])
        elif nom == "footnoteReference" and self.pile and attr.get("id") in self.notes:
            self.pile[-1]["notes"].append(self.notes[attr["id"]])

    def fin(self, nom: str) -> None:
        if nom == "p" or (self.odf and nom == "h"):
            if not self.pile:
                return
            p = self.pile.pop()
            texte = "".join(p["morceaux"]).strip()
            if self.odf and self.dans_note and self.pile:  # paragraphe d'une note : rattache a son paragraphe
                self.pile[-1]["notes"].append(texte)
                return
            if texte and p["num"] not in (None, "0"):
                texte = self._numero(p["num"], p["niveau"]) + texte
            self._ecrire([texte] + [self._note(n) for n in p["notes"] if n])
        elif nom in ("tc", "table-cell") and self.tableaux and self.tableaux[-1]["cellule"] is not None:
            t = self.tableaux[-1]
            t["cellules"].append(" ".join(x for x in t["cellule"] if x))
            t["cellule"] = None
        elif nom in ("tr", "table-row") and self.tableaux:
            t = self.tableaux[-1]
            if any(t["cellules"]):
                t["lignes"].append(" | ".join(t["cellules"]))
            t["cellules"] = []
        elif nom in ("tbl", "table") and self.tableaux:
            lignes = self.tableaux.pop()["lignes"]
            self._ecrire([" / ".join(lignes)] if self.tableaux else lignes)  # tableau dans un tableau : une cellule
        elif nom == "t":
            self.dans_t -= 1
        elif nom == "r":
            self.dans_r -= 1
        elif nom == "note-citation":
            self.ignorer -= 1
        elif nom == "note":
            self.dans_note -= 1

    def _ecrire(self, textes: list[str]) -> None:
        cellule = self.tableaux[-1]["cellule"] if self.tableaux else None
        (cellule if cellule is not None else self.paragraphes).extend(t for t in textes if t)

    def _note(self, texte: str) -> str:
        self.nb_notes += 1
        return f"Note {self.nb_notes} : {texte}"

    def _numero(self, num: str, niveau: int) -> str:
        niveaux = self.numerotation.get(num) or {}
        if niveau not in niveaux:
            return ""
        compteurs = self.compteurs.setdefault(num, {})
        compteurs[niveau] = compteurs.get(niveau, niveaux[niveau][2] - 1) + 1
        for n in [n for n in compteurs if n > niveau]:
            del compteurs[n]  # « II. » remet « A. » a zero
        fmt, modele, _ = niveaux[niveau]
        if fmt == "bullet":
            return "- "
        if fmt == "none" or not modele:
            return ""

        def valeur(m):
            n = int(m.group(1)) - 1
            f, _, depart = niveaux.get(n, ("decimal", "", 1))
            return _format_numero(compteurs.get(n, depart), f)

        return re.sub(r"%(\d)", valeur, modele).strip() + " "

    def texte(self) -> str:
        return "\n".join(self.paragraphes)


def _format_numero(n: int, fmt: str) -> str:
    if fmt in ("upperRoman", "lowerRoman"):
        romain, reste = "", n
        for v, s in ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"),
                     (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
            while reste >= v:
                romain, reste = romain + s, reste - v
        return romain if fmt == "upperRoman" else romain.lower()
    if fmt in ("upperLetter", "lowerLetter") and n >= 1:
        lettre = chr(ord("A") + (n - 1) % 26) * ((n - 1) // 26 + 1)
        return lettre if fmt == "upperLetter" else lettre.lower()
    return str(n)


def _numerotation(xml: bytes | None, illisible: str, total: list[int]) -> dict:
    """word/numbering.xml -> {numId: {niveau: (format, modele « %1. », depart)}}."""
    abstraits: dict[str, dict[int, list]] = {}
    liens: dict[str, str] = {}

    class Lecteur:
        abstrait = num = None
        niveau = None

        def capte(self):
            return False

        def debut(self, nom, attr):
            if nom == "abstractNum":
                self.abstrait = abstraits.setdefault(attr.get("abstractNumId", ""), {})
            elif nom == "num":
                self.num = attr.get("numId")
            elif nom == "abstractNumId" and self.num is not None:
                liens[self.num] = attr.get("val", "")
            elif nom == "lvl" and self.abstrait is not None and (attr.get("ilvl") or "").isdigit():
                self.niveau = self.abstrait.setdefault(int(attr["ilvl"]), ["decimal", "", 1])
            elif self.niveau is not None and nom in ("numFmt", "lvlText", "start"):
                v = attr.get("val", "")
                if nom == "start":
                    self.niveau[2] = int(v) if v.isdigit() else 1
                else:
                    self.niveau[0 if nom == "numFmt" else 1] = v

        def fin(self, nom):
            if nom == "abstractNum":
                self.abstrait = None
            elif nom == "num":
                self.num = None
            elif nom == "lvl":
                self.niveau = None

    _lire_xml(xml, Lecteur(), illisible, total)
    return {num: {n: tuple(v) for n, v in abstraits.get(a, {}).items()} for num, a in liens.items()}


def _notes_word(xml: bytes | None, illisible: str, total: list[int]) -> dict[str, str]:
    """word/footnotes.xml -> {id: texte de la note}."""
    lecteur, notes, courante = _Lecteur(), {}, {}

    class Notes:
        capte, ajouter = lecteur.capte, lecteur.ajouter

        def debut(self, nom, attr):
            if nom == "footnote":
                courante.update(id=attr.get("id"), depuis=len(lecteur.paragraphes))
            lecteur.debut(nom, attr)

        def fin(self, nom):
            lecteur.fin(nom)
            if nom == "footnote" and courante:
                texte = " ".join(lecteur.paragraphes[courante["depuis"]:]).strip()
                if texte:
                    notes[courante["id"]] = texte

    _lire_xml(xml, Notes(), illisible, total)
    return notes


if __name__ == "__main__":
    import resource

    # Limites posees par le processus lui-meme (preexec_fn n'est pas sur dans un serveur a plusieurs fils).
    for limite, valeur in ((resource.RLIMIT_AS, MEMOIRE_LECTURE), (resource.RLIMIT_CPU, DELAI_LECTURE)):
        try:
            resource.setrlimit(limite, (valeur, valeur))
        except (ValueError, OSError):
            pass  # macOS ne prend pas en charge RLIMIT_AS : le delai suffit en developpement
    try:
        lecture = lire(sys.argv[1], sys.stdin.buffer.read())
        resultat = {"pages": lecture.pages, "ocr": lecture.ocr}
    except ErreurCours as e:
        resultat = {"erreur": str(e)}
    sys.stdout.write(json.dumps(resultat))
