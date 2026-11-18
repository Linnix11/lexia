"""Traités européens et internationaux : un passage par article.

Sources officielles (vérifiées le 2026-11-14) :
  - TUE, TFUE et Charte des droits fondamentaux de l'Union : versions consolidées publiées au JOUE C 202
    du 7 juin 2016, servies en XHTML par le dépôt Cellar de l'Office des publications de l'Union.
    (Les pages EUR-Lex exigent un navigateur ; les adresses Cellar ont été trouvées par le point SPARQL
    publications.europa.eu/webapi/rdf/sparql, sur les identifiants CELEX 12016M/TXT, 12016E/TXT, 12016P/TXT.)
  - Convention européenne des droits de l'homme : texte publié par la Cour (PDF), tel qu'amendé par les
    protocoles 11, 14 et 15. Seuls la Convention, le Protocole additionnel et les protocoles 4, 6 et 7 sont
    repris : l'extraction du livret mélange l'ordre des pages des protocoles 13 et 16, et la France n'a pas
    ratifié le protocole 12.
  - Charte des Nations unies : page officielle de l'ONU en français.

Interface attendue par ingest.run : SOURCE_ID, fetch(client) -> texte brut, parse(texte) -> passages.
Si la structure d'une source change, parse() lève une erreur plutôt que de produire un texte incomplet.
"""

from __future__ import annotations

import io
import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup, Tag

from ingest.models import Passage


class ParseError(RuntimeError):
    pass


def _propre(texte: str) -> str:
    return " ".join(texte.replace("\xa0", " ").replace(" ", " ").split())


def _date_fr(iso: str) -> str:
    mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
            "octobre", "novembre", "décembre"]
    a, m, j = (int(x) for x in iso.split("-"))
    return f"{'1er' if j == 1 else j} {mois[m - 1]} {a}"


def _numero(libelle: str) -> str:
    m = re.match(r"^article\s+(premier|\d+)\b", _propre(libelle), re.I)
    if not m:
        raise ParseError(f"Intitulé d'article non reconnu : {libelle!r}")
    return "1" if m.group(1).lower() == "premier" else m.group(1)


class Traite:
    """Un traité : identité, adresse officielle et analyseur du texte brut."""

    def __init__(self, source_id: str, nom: str, url: str, source_brute: str, version: str, depuis: str,
                 min_articles: int):
        self.SOURCE_ID = source_id
        self.nom = nom
        self.url = url                    # lien affiché à l'étudiant
        self.source_brute = source_brute  # fichier téléchargé
        self.version = version
        self.depuis = depuis              # date ISO d'entrée en vigueur du texte (pour la France)
        self.min_articles = min_articles

    def fetch(self, client) -> str:
        resp = client.get(self.source_brute, follow_redirects=True, timeout=120)
        resp.raise_for_status()
        return resp.text

    def _passage(self, numero: str | None, titre: str | None, alineas: list[str], date_recuperation: str,
                 *, partie: str | None = None, meta: dict | None = None) -> Passage:
        """partie : protocole d'un traite (« p1 »...) ; sa date d'entree en vigueur n'est pas indiquee."""
        cle = f"{partie}:art:{numero}" if partie else (f"art:{numero}" if numero else "preambule")
        depuis = None if partie else self.depuis
        if numero is None:
            entete = f"{self.nom}, préambule"
        else:
            entete = f"{self.nom}, " + (f"{partie_lisible(partie)}, " if partie else "") + f"article {numero}"
        if titre:
            entete += f" - {titre}"
        entete += f" (en vigueur, depuis le {_date_fr(depuis)})" if depuis else " (en vigueur)"
        return Passage(
            id=f"{self.SOURCE_ID}:{cle}", source_id=self.SOURCE_ID,
            type="preambule" if numero is None else "article",
            numero=None if numero is None else (f"P{partie_numero(partie)}-{numero}" if partie else numero),
            titre=titre, alineas=alineas, url=self.url, version=self.version,
            date_recuperation=date_recuperation, entete=entete,
            meta={"en_vigueur": True, "date_debut": depuis, "date_fin": None, **(meta or {})},
        )

    def _verifier(self, passages: list[Passage]) -> list[Passage]:
        n = sum(p.type == "article" for p in passages)
        if n < self.min_articles:
            raise ParseError(f"{self.nom} : {n} articles lus, {self.min_articles} attendus au moins")
        vides = [p.id for p in passages if not p.alineas]
        if vides:
            raise ParseError(f"{self.nom} : passages vides {vides[:3]}")
        return passages


def partie_lisible(partie: str | None) -> str:
    return {"p1": "Protocole additionnel"}.get(partie or "", f"Protocole n° {partie_numero(partie)}")


def partie_numero(partie: str | None) -> str:
    return (partie or "").removeprefix("p").upper()


# --- Union européenne : XHTML du Journal officiel ---------------------------------------------------

class TraiteUE(Traite):
    def parse(self, xhtml: str, *, date_recuperation: str | None = None) -> list[Passage]:
        date_recuperation = date_recuperation or datetime.now(timezone.utc).isoformat(timespec="seconds")
        soup = BeautifulSoup(xhtml, "html.parser")
        for note in soup.select('a[href^="#ntr"]'):  # appels de note « (2) »
            note.decompose()
        titres_doc = soup.find_all("p", class_="doc-ti")
        if not titres_doc:
            raise ParseError(f"{self.nom} : titre du document introuvable (p.doc-ti)")
        fin = next((t for t in titres_doc[1:] if _propre(t.get_text()).upper().startswith("PROTOCOLE")), None)

        passages: list[Passage] = []
        plan: list[str] = []
        preambule: list[str] = []
        for el in titres_doc[0].find_all_next(["p", "div"]):
            if el is fin:
                break
            classes = el.get("class") or []
            if "ti-section-1" in classes:
                plan = [_propre(el.get_text())]
            elif "ti-section-2" in classes:
                plan = plan[:1] + [_propre(el.get_text())]
            elif "ti-art" in classes:
                passages.append(self._article(el, plan, date_recuperation))
            elif "normal" in classes and not passages:   # avant le premier article : le preambule
                texte = _propre(el.get_text())
                if texte and not texte.startswith("(") and texte.upper() != "PRÉAMBULE":
                    preambule.append(texte)
        if preambule:
            passages.insert(0, self._passage(None, None, preambule, date_recuperation))
        return self._verifier(passages)

    def _article(self, ti: Tag, plan: list[str], date_recuperation: str) -> Passage:
        numero = _numero(ti.get_text())
        titre = None
        ancien = None
        alineas: list[str] = []
        for frere in ti.find_next_siblings():
            classes = frere.get("class") or []
            if "ti-art" in classes:
                break
            texte = _propre(frere.get_text(" "))
            if not texte:
                continue
            if "sti-art" in classes:
                if texte.startswith("(ex"):
                    ancien = texte.strip("() ")       # « ex-article 81 TCE » : ancienne numérotation
                else:
                    titre = texte                     # Charte : intitulé de l'article
                continue
            alineas.append(texte)
        return self._passage(numero, titre, alineas, date_recuperation,
                             meta={"plan": [p for p in plan if p]} | ({"ancien_numero": ancien} if ancien else {}))


# --- Convention européenne des droits de l'homme : texte du livret PDF de la Cour ---------------------

PROTOCOLES_REPRIS = {"additionnel": "p1", "4": "p4", "6": "p6", "7": "p7"}


class ConventionEDH(Traite):
    def fetch(self, client) -> str:
        from pypdf import PdfReader  # dependance d'ingestion (deja utilisee pour les cours deposes)

        resp = client.get(self.source_brute, follow_redirects=True, timeout=120)
        resp.raise_for_status()
        lecteur = PdfReader(io.BytesIO(resp.content))
        return "\n".join(page.extract_text() or "" for page in lecteur.pages)

    def parse(self, texte: str, *, date_recuperation: str | None = None) -> list[Passage]:
        date_recuperation = date_recuperation or datetime.now(timezone.utc).isoformat(timespec="seconds")
        lignes = [_propre(l) for l in texte.split("\n")]
        debut = next((i for i, l in enumerate(lignes) if l == "ARTICLE 1"), None)
        if debut is None:
            raise ParseError("Convention EDH : article 1 introuvable")

        passages: list[Passage] = []
        partie: str | None = None       # None = la Convention ; "p1", "p4"... = un protocole repris
        ignorer = False                 # protocole non repris, ou formule finale « Fait à ... »
        plan: list[str] = []
        courant: dict | None = None

        def clore() -> None:
            if courant is not None:
                passages.append(self._passage(courant["numero"], courant["titre"], courant["alineas"],
                                              date_recuperation, partie=courant["partie"],
                                              meta={"plan": courant["plan"]}))

        i = debut
        while i < len(lignes):
            l = lignes[i]
            suivante = lignes[i + 1] if i + 1 < len(lignes) else ""
            proto = re.match(r"^Protocole (additionnel|n° ?(\d+))$", l)
            if proto and suivante.startswith("à la Convention"):
                clore()
                courant = None
                cle = "additionnel" if proto.group(1) == "additionnel" else proto.group(2)
                partie = PROTOCOLES_REPRIS.get(cle)
                ignorer = partie is None
                plan = []
                i += 1
                continue
            if ignorer or not l or re.fullmatch(r"\d{1,3}( \d{1,3})?", l):   # numeros de page « 34 35 »
                i += 1
                continue
            if l.startswith("Fait à "):     # formule finale du traité : plus aucun article ensuite
                clore()
                courant = None
                ignorer = True
                i += 1
                continue
            if re.fullmatch(r"TITRE [IVX]+", l):
                plan = [l, suivante] if suivante.isupper() else [l]
                i += 2 if suivante.isupper() else 1
                continue
            art = re.fullmatch(r"ARTICLE (\d+)", l)
            if art:
                clore()
                titre = None
                if suivante and not re.match(r"^\d+\.", suivante) and not suivante.endswith((".", ":", ";")):
                    titre = suivante
                    i += 1
                courant = {"numero": art.group(1), "titre": titre, "alineas": [], "partie": partie, "plan": plan}
                i += 1
                continue
            if courant is not None:
                self._ajouter_ligne(courant["alineas"], l)
            i += 1
        clore()
        return self._verifier(passages)

    @staticmethod
    def _ajouter_ligne(alineas: list[str], ligne: str) -> None:
        """Recolle les lignes coupées par la mise en page : un nouvel alinéa commence par « 1. », « a) »
        ou suit une ligne terminée par un point, deux-points ou point-virgule."""
        ligne = re.sub(r"^((?:\d+\.\s+)?)([A-ZÀ-Ý]) ([a-zà-ÿ])", r"\1\2\3", ligne)  # lettrine « L e droit »
        nouveau = (not alineas or re.match(r"^(\d+\.|[a-z]\))\s", ligne)
                   or (alineas[-1].endswith((".", ":", ";")) and ligne[:1].isupper()))
        if nouveau:
            alineas.append(ligne)
        else:
            alineas[-1] = f"{alineas[-1]} {ligne}"


# --- Charte des Nations unies : page de l'ONU --------------------------------------------------------

class CharteONU(Traite):
    def parse(self, html: str, *, date_recuperation: str | None = None) -> list[Passage]:
        date_recuperation = date_recuperation or datetime.now(timezone.utc).isoformat(timespec="seconds")
        soup = BeautifulSoup(html, "html.parser")
        depart = next((h for h in soup.find_all("h2") if _propre(h.get_text()).lower() == "préambule"), None)
        if depart is None:
            raise ParseError("Charte des Nations unies : préambule introuvable")
        passages: list[Passage] = []
        plan: list[str] = []
        courant: dict | None = {"numero": None, "alineas": []}   # le préambule d'abord

        def clore() -> None:
            if courant is not None and courant["alineas"]:
                passages.append(self._passage(courant["numero"], None, courant["alineas"], date_recuperation,
                                              meta={"plan": courant.get("plan", [])}))

        for el in depart.find_all_next(["h2", "h3", "p", "li"]):
            texte = _propre(el.get_text(" "))
            if not texte:
                continue
            if el.name == "h2":
                if not re.match(r"^chapitre", texte, re.I):
                    if passages or (courant and courant["numero"]):
                        break     # fin de la Charte (contenu de la page après le dernier chapitre)
                    continue
                plan = [texte]
                continue
            if el.name == "h3" and re.match(r"^article\s+\d+$", texte, re.I):
                clore()
                courant = {"numero": _numero(texte), "alineas": [], "plan": plan}
                continue
            if el.name == "p" and el.find_parent("li") is not None:
                continue    # deja lu avec son element de liste
            if courant is not None:
                if el.name == "li" and el.parent is not None and el.parent.name == "ol":
                    rang = el.parent.find_all("li", recursive=False).index(el) + 1
                    lettre = "abcdefghijklmnopqrstuvwxyz"[rang - 1] if "alpha" in " ".join(el.parent.get("class") or []) else None
                    texte = f"{lettre}) {texte}" if lettre else f"{rang}. {texte}"
                courant["alineas"].append(texte)
        clore()
        return self._verifier(passages)


CELLAR = "http://publications.europa.eu/resource/cellar/"
SOURCES = [
    TraiteUE("tue", "Traité sur l'Union européenne",
             "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:12016M/TXT",
             CELLAR + "2021d50a-3468-11e6-969e-01aa75ed71a1.0002.02/DOC_1",
             "Version consolidée publiée au JOUE C 202 du 7 juin 2016 (Office des publications de l'Union)",
             "2009-12-01", min_articles=55),
    TraiteUE("tfue", "Traité sur le fonctionnement de l'Union européenne",
             "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:12016E/TXT",
             CELLAR + "f1bcba61-0d85-4e7f-b41e-a72c42eb5c49.0002.02/DOC_1",
             "Version consolidée publiée au JOUE C 202 du 7 juin 2016 (Office des publications de l'Union)",
             "2009-12-01", min_articles=350),
    TraiteUE("charte_droits_fondamentaux_ue", "Charte des droits fondamentaux de l'Union européenne",
             "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:12016P/TXT",
             CELLAR + "c483a582-2c70-11e6-b497-01aa75ed71a1.0009.03/DOC_1",
             "Version publiée au JOUE C 202 du 7 juin 2016 (Office des publications de l'Union)",
             "2009-12-01", min_articles=54),
    ConventionEDH("cedh", "Convention européenne des droits de l'homme",
                  "https://www.echr.coe.int/documents/d/echr/convention_fra",
                  "https://www.echr.coe.int/documents/d/echr/convention_fra",
                  "Texte publié par la Cour européenne des droits de l'homme, tel qu'amendé par les protocoles "
                  "11, 14 et 15 (en vigueur pour la France depuis le 3 mai 1974)",
                  "1974-05-03", min_articles=59),
    CharteONU("charte_onu", "Charte des Nations unies",
              "https://www.un.org/fr/about-us/un-charter/full-text",
              "https://www.un.org/fr/about-us/un-charter/full-text",
              "Texte publié par l'Organisation des Nations unies, amendements de 1963, 1965 et 1971 compris",
              "1945-10-24", min_articles=111),
]
