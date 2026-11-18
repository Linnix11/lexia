"""Lecture du texte d'un cours depose (PDF, Word, OpenDocument, PowerPoint, texte), dans un processus a part.

Un fichier piege pouvait bloquer ou faire tomber tout le serveur (audit de securite du 2026-11-16) :
- un PDF de 150 Ko dont les 1000 pages partagent un meme contenu compresse : 4 a 5 h de calcul ;
- un Word aux entites XML repetees ou aux balises imbriquees : 1 Go de memoire pour 10 Ko envoyes.
Le service n'a qu'un processus : un calcul ou une memoire sans fin le bloquaient pour tous. La lecture se
fait donc dans un processus Python separe (extraire_isole), limite en duree et en memoire, que l'on tue
au-dela. Ce module n'importe que la bibliotheque standard et pypdf : le processus demarre vite.

    python -m api.extraction <nom du fichier>  < contenu   ->  {"pages": [[page, texte], ...]} ou {"erreur": ...}
"""

from __future__ import annotations

import codecs
import io
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.parsers import expat

CARACTERES_MAX = 1_000_000          # texte extrait au plus
PAGES_MAX = 1000                    # pages d'un PDF
XML_WORD_MAX = 10 * 1024 * 1024     # un fichier XML decompresse (word/document.xml...) : au-dela, archive piegee
XML_TOTAL_MAX = 3 * XML_WORD_MAX    # tous les fichiers XML lus d'une archive (diapositives, notes...)
PART_SCANNEE_MAX = 0.5              # PDF refuse au-dela de cette part de pages sans texte (scan, photo)
PROFONDEUR_MAX = 200                # balises imbriquees dans un document Word (Word en fait moins de 20)
DELAI_LECTURE = 60                  # secondes pour lire un fichier, au-dela il est refuse
MEMOIRE_LECTURE = 768 * 1024 * 1024  # memoire du processus de lecture
FORMATS = {".pdf": "PDF", ".docx": "Word", ".odt": "OpenDocument", ".pptx": "PowerPoint", ".txt": "texte",
           ".md": "texte"}
RACINE = Path(__file__).resolve().parent.parent


class ErreurCours(ValueError):
    """Erreur presentable a l'etudiant."""


def extraire_isole(nom: str, contenu: bytes, delai: float = DELAI_LECTURE) -> list[tuple[int | None, str]]:
    """extraire_texte dans un processus separe, tue s'il depasse le delai ou la memoire."""
    try:
        r = subprocess.run([sys.executable, "-m", "api.extraction", nom], input=contenu, capture_output=True,
                           timeout=delai, cwd=RACINE)
    except subprocess.TimeoutExpired:
        raise ErreurCours("La lecture de ce fichier prend trop de temps : il est refusé. "
                          "Déposez une version plus simple (texte exporté en PDF ou Word).") from None
    try:
        sortie = json.loads(r.stdout) if r.returncode == 0 else {}
    except ValueError:
        sortie = {}
    if "erreur" in sortie:
        raise ErreurCours(sortie["erreur"])
    if "pages" not in sortie:
        raise ErreurCours("Ce fichier n'a pas pu être lu (trop lourd ou endommagé) : il est refusé.")
    return [(page, texte) for page, texte in sortie["pages"]]


def extraire_texte(nom: str, contenu: bytes) -> list[tuple[int | None, str]]:
    """[(page, texte)] ; page = None quand le format n'a pas de pages. A appeler via extraire_isole."""
    ext = Path(nom).suffix.lower()
    if ext not in FORMATS:
        raise ErreurCours("Format non pris en charge : déposez un PDF, un fichier Word (.docx), OpenDocument (.odt), "
                          "PowerPoint (.pptx) ou un texte (.txt).")
    if ext == ".pdf":
        return _texte_pdf(contenu)
    if ext in (".docx", ".odt", ".pptx"):
        illisible = f"Ce fichier {FORMATS[ext]} est illisible ou endommagé."
        try:
            with zipfile.ZipFile(io.BytesIO(contenu)) as z:
                return _texte_zip(ext, z, illisible)
        except (zipfile.BadZipFile, KeyError, RuntimeError, NotImplementedError):
            # RuntimeError : membre chiffre ; NotImplementedError : compression inconnue
            raise ErreurCours(illisible) from None
    return [(None, _texte_brut(contenu))]


def _texte_brut(contenu: bytes) -> str:
    """Texte UTF-8 (avec ou sans BOM), UTF-16 (Bloc-notes « Unicode ») ou Windows-1252 (ancien Bloc-notes)."""
    if contenu.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return contenu.decode("utf-16", errors="replace")
    try:
        return contenu.decode("utf-8-sig")
    except UnicodeDecodeError:
        return contenu.decode("cp1252", errors="replace")  # latin-1 rendait « œ », « ’ », « – » illisibles


def _texte_pdf(contenu: bytes) -> list[tuple[int | None, str]]:
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
    except (PyPdfError, ValueError, KeyError) as e:  # PyPdfError : aussi les limites internes de pypdf
        if isinstance(e, ErreurCours):
            raise
        raise ErreurCours("Ce PDF est illisible ou endommagé.") from None
    vides = pages_sans_texte(pages)
    # Seuil global seul (200 caracteres), un PDF de 20 pages dont 19 scannees passait sans rien dire (audit C2).
    if sum(len(t.strip()) for _, t in pages) < 200 or len(vides) > len(pages) * PART_SCANNEE_MAX:
        detail = f" ({len(vides)} pages sur {len(pages)} sans texte)" if len(pages) > 1 else ""
        raise ErreurCours(f"Ce PDF ne contient pas de texte{detail} : c'est un scan ou des photos, et la lecture "
                          "des documents scannés n'est pas encore disponible.")
    return pages


def pages_sans_texte(pages: list[tuple[int | None, str]]) -> list[int]:
    """Pages d'un PDF sans texte lisible (scan, photo) : moins de 15 lettres, numero de page compris."""
    return [p for p, t in pages if p is not None and len(re.sub(r"[\W\d_]+", "", t)) < 15]


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
        resultat = {"pages": extraire_texte(sys.argv[1], sys.stdin.buffer.read())}
    except ErreurCours as e:
        resultat = {"erreur": str(e)}
    sys.stdout.write(json.dumps(resultat))
