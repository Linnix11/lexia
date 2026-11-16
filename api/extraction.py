"""Lecture du texte d'un cours depose (PDF, Word, texte), dans un processus a part.

Un fichier piege pouvait bloquer ou faire tomber tout le serveur (audit de securite du 2026-11-16) :
- un PDF de 150 Ko dont les 1000 pages partagent un meme contenu compresse : 4 a 5 h de calcul ;
- un Word aux entites XML repetees ou aux balises imbriquees : 1 Go de memoire pour 10 Ko envoyes.
Le service n'a qu'un processus : un calcul ou une memoire sans fin le bloquaient pour tous. La lecture se
fait donc dans un processus Python separe (extraire_isole), limite en duree et en memoire, que l'on tue
au-dela. Ce module n'importe que la bibliotheque standard et pypdf : le processus demarre vite.

    python -m api.extraction <nom du fichier>  < contenu   ->  {"pages": [[page, texte], ...]} ou {"erreur": ...}
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.parsers import expat

CARACTERES_MAX = 1_000_000          # texte extrait au plus
PAGES_MAX = 1000                    # pages d'un PDF
XML_WORD_MAX = 10 * 1024 * 1024     # word/document.xml decompresse : au-dela, archive piegee (« zip bomb »)
PROFONDEUR_MAX = 200                # balises imbriquees dans un document Word (Word en fait moins de 20)
DELAI_LECTURE = 60                  # secondes pour lire un fichier, au-dela il est refuse
MEMOIRE_LECTURE = 768 * 1024 * 1024  # memoire du processus de lecture
FORMATS = {".pdf": "PDF", ".docx": "Word", ".txt": "texte", ".md": "texte"}
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
        raise ErreurCours("Format non pris en charge : déposez un PDF, un fichier Word (.docx) ou un texte (.txt).")
    if ext == ".pdf":
        return _texte_pdf(contenu)
    if ext == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(contenu)) as z, z.open("word/document.xml") as f:
                brut = f.read(XML_WORD_MAX + 1)  # lecture bornee : jamais plus que la limite en memoire
            if len(brut) > XML_WORD_MAX:
                raise ErreurCours("Ce fichier Word est anormalement volumineux une fois décompressé : il est refusé.")
        except (zipfile.BadZipFile, KeyError, RuntimeError, NotImplementedError):
            # RuntimeError : membre chiffre ; NotImplementedError : compression inconnue
            raise ErreurCours("Ce fichier Word est illisible ou endommagé.") from None
        return [(None, _texte_word(brut))]
    try:
        return [(None, contenu.decode("utf-8"))]
    except UnicodeDecodeError:
        return [(None, contenu.decode("latin-1"))]


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
    if sum(len(t.strip()) for _, t in pages) < 200:
        raise ErreurCours("Ce PDF ne contient pas de texte (scan ou photo) : la lecture des documents "
                          "scannés n'est pas encore disponible.")
    return pages


def _texte_word(xml: bytes) -> str:
    """Paragraphes (w:p) et leurs morceaux de texte (w:t), lus au fil de l'eau sans construire d'arbre.

    Refuse toute declaration DOCTYPE ou ENTITY (Word n'en produit jamais) : expat accepte une
    amplification d'entites jusqu'a x100, soit 1 Go pour 10 Mo de document. Refuse aussi les
    imbrications profondes et s'arrete des que le texte depasse CARACTERES_MAX.
    """
    illisible = "Ce fichier Word est illisible ou endommagé."
    paragraphes: list[str] = []
    courant: list[str] = []
    etat = {"profondeur": 0, "dans_t": 0, "total": 0}

    def refuser(*_):
        raise ErreurCours(illisible)

    def debut(nom, _attributs):
        etat["profondeur"] += 1
        if etat["profondeur"] > PROFONDEUR_MAX:
            raise ErreurCours(illisible)
        if nom.rsplit("}", 1)[-1] == "t":
            etat["dans_t"] += 1

    def fin(nom):
        etat["profondeur"] -= 1
        local = nom.rsplit("}", 1)[-1]
        if local == "t":
            etat["dans_t"] -= 1
        elif local == "p":
            paragraphes.append("".join(courant))
            courant.clear()

    def texte(donnees):
        if etat["dans_t"]:
            etat["total"] += len(donnees)
            if etat["total"] > CARACTERES_MAX:
                raise ErreurCours("Document trop long : découpez-le en plusieurs cours.")
            courant.append(donnees)

    lecteur = expat.ParserCreate(namespace_separator="}")
    lecteur.StartDoctypeDeclHandler = refuser
    lecteur.EntityDeclHandler = refuser
    lecteur.StartElementHandler = debut
    lecteur.EndElementHandler = fin
    lecteur.CharacterDataHandler = texte
    try:
        lecteur.Parse(xml, True)
    except expat.ExpatError:
        raise ErreurCours(illisible) from None
    return "\n".join(paragraphes)


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
