"""Catalogue des cours recuperes sous licence libre (page « Cours recuperes », docs/cours-libres.md).

    python -m ingest.cours_recuperes                 # telecharge si besoin et reecrit le catalogue
    python -m ingest.cours_recuperes --hors-ligne    # reutilise seulement ce qui est deja telecharge

Decision de l'editeur du 2026-11-19 (D103) : phases 1 et 2.
- Phase 2 : fiches pratiques de service-public.gouv.fr (Licence Ouverte, archive XML quotidienne de la DILA),
  choisies par sous-theme et rangees dans les matieres de Lexia. Elles alimentent la page et l'index, a part du
  corpus officiel (source fiches_service_public, api.textes.SOURCES_A_PART).
- Phase 3 non retenue : la liste WIKI (Wikiversite, Wikilivres, CC BY-SA 4.0) reste vide.

Phase 1, vie-publique.fr, n'est pas recuperee : le site refuse les clients automatiques (protection anti-robots) et n'offre
aucun export de ses fiches. Il faut demander un export a la DILA (docs/cours-libres.md).

Le texte est repris sans modification de fond : seuls la mise en forme, les liens et les blocs pratiques
(adresses, services en ligne) ne sont pas repris. Le catalogue est ecrit en une fois (fichier temporaire puis
renommage) et valide par le modele de l'API avant ecriture.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag

from api.config import ROOT
from api.cours_recuperes import CoursRecupere
from api.textes import SOURCES_A_PART
from ingest.models import Passage

RAW = ROOT / "data" / "raw" / "cours_recuperes"
CATALOGUE = ROOT / "data" / "cours_recuperes" / "catalogue.json"
PASSAGES_DIR = ROOT / "data" / "passages"
# Source de l'index (a part du corpus officiel, api.textes.SOURCES_A_PART) de chaque site repris.
SOURCE_INDEX = {"Service Public / DILA": "fiches_service_public", "Vie publique": "fiches_vie_publique"}
TAILLE_PASSAGE = 1500  # caracteres, comme les cours deposes (D57)
# Nom generique : aucune donnee du projet ni de l'editeur n'est envoyee aux sites sources.
USER_AGENT = f"CoursLibresIngest/0.1 httpx/{httpx.__version__}"
# Wikimedia refuse un client sans moyen de contact dans son User-Agent (politique des robots,
# https://wikitech.wikimedia.org/wiki/Robot_policy). Adresse ou URL choisie par l'editeur ; sans elle, les wikis
# ne sont pas recuperes.
WIKIMEDIA_CONTACT = os.environ.get("WIKIMEDIA_CONTACT", "").strip()
PAUSE_WIKI = 2.0  # secondes entre deux requetes a l'API Wikimedia

# ---------------------------------------------------------------------------------------------------------------
# service-public.gouv.fr

SP_ZIP_URL = "https://lecomarquage.service-public.gouv.fr/vdd/3.5/part/zip/vosdroits-latest.zip"
SP_ZIP = RAW / "service_public" / "vosdroits-latest.zip"
SP_MODIFICATIONS = ("Texte repris sans modification ; mise en forme, liens, simulateurs et blocs pratiques "
                    "(adresses, services en ligne) non repris.")
DC = "{http://purl.org/dc/elements/1.1/}"

# (sous-theme, dossier ou None pour tout le sous-theme) -> matiere. Seules les fiches pratiques sont reprises :
# les questions-reponses sont trop courtes pour une page de cours.
SP_MATIERES: dict[tuple[str, str | None], str] = {
    ("Organisation de la justice", None): "introduction_au_droit",
    ("État civil", "Changement d'état civil"): "droit_civil",
    ("État civil", "Actes d'état civil"): "droit_civil",
    ("Réparation du préjudice", "Indemnisation du préjudice"): "droit_civil",
    ("Couple", None): "droit_de_la_famille",
    ("Enfant", "Séparation des parents"): "droit_de_la_famille",
    ("Enfant", "Naissance et filiation"): "droit_de_la_famille",
    ("Enfant", "Autorité parentale"): "droit_de_la_famille",
    ("Enfant", "Adoption"): "droit_de_la_famille",
    ("Enfant", "Placement d'un enfant"): "droit_de_la_famille",
    ("Protection des personnes", None): "droit_de_la_famille",
    ("Succession", None): "droit_de_la_famille",
    ("Copropriété", None): "droit_des_biens",
    ("Achat immobilier", None): "droit_des_biens",
    ("Bail d’habitation", None): "droit_des_contrats",
    ("Consommation", None): "droit_des_contrats",
    ("Crédit et surendettement", None): "droit_des_contrats",
    ("Assurance", None): "droit_des_contrats",
    ("Relations avec l'administration", "Obligations de l'administration vis-à-vis des usagers"): "droit_administratif",
    ("Relations avec l'administration", "Mesures contraignantes de l'administration"): "droit_administratif",
    ("Relations avec l'administration", "Litiges avec l'administration : recours administratif, défenseur des droits"): "droit_administratif",
    ("Relations avec l'administration", "Agir en justice contre l'administration"): "contentieux_administratif",
    ("Expropriation - Préemption", None): "droit_administratif_des_biens",
    ("Infractions", None): "droit_penal",
    ("Sanctions pénales", None): "droit_penal",
    ("Procédures judiciaires", "Affaire pénale"): "procedure_penale",
    ("Justice des mineurs", None): "procedure_penale",
    ("Procédures judiciaires", "Affaire civile"): "procedure_civile",
    ("Procédures judiciaires", "Contestation d'un jugement"): "procedure_civile",
    ("Réparation du préjudice", "Saisies et recouvrements"): "procedure_civile",
    ("Contrats et carrière", None): "droit_social",
    ("Quitter son emploi", None): "droit_social",
    ("Relations individuelles et collectives de travail", None): "droit_social",
    ("Temps de travail", None): "droit_social",
    ("Rémunération", None): "droit_social",
    ("Recrutement", None): "droit_social",
    ("Congés", None): "droit_social",
    ("Santé, sécurité et conditions de travail", None): "droit_social",
    ("Particulier employeur", None): "droit_social",
    ("Sécurité sociale", None): "droit_social",
    ("Impôts, taxes et douane", None): "droit_fiscal",
    ("Citoyenneté", "Élections"): "droit_constitutionnel",
    ("Fichiers et protection de la vie privée", None): "libertes_fondamentales",
}

# Blocs repris tels quels, precedes de leur libelle sur le site.
SP_ENCADRES = {"ANoter": "À noter", "ASavoir": "À savoir", "Attention": "Attention", "Rappel": "Rappel",
               "Exemple": "Exemple"}
# Logique d'affichage ou doublons de titres : ignores.
SP_IGNORES = {"Condition", "TitreRiche", "OuSAdresser", "ServiceEnLigne", "PourEnSavoirPlus", "QuiPeutMAider",
              "VoirAussi", "Definition", "Abreviation", "PivotLocal", "Connexion"}


def _texte(el: ET.Element) -> str:
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def _titre(el: ET.Element) -> str:
    t = el.find("Titre")
    return _texte(t) if t is not None else ""


def _rendre(el: ET.Element, lignes: list[str]) -> None:
    """Texte d'un bloc de fiche, une ligne par paragraphe, puce, rangee de tableau ou titre de cas."""
    tag = el.tag
    if tag in SP_IGNORES or tag == "Titre":
        return
    if tag == "Paragraphe":
        if t := _texte(el):
            lignes.append(t)
    elif tag == "Item":
        sous: list[str] = []
        for enfant in el:
            _rendre(enfant, sous)
        if sous:
            lignes.append("- " + sous[0])
            lignes.extend("  " + s for s in sous[1:])
    elif tag == "Rangée":
        cellules = [_texte(c) for c in el.findall("Cellule")]
        if any(cellules):
            lignes.append(" | ".join(cellules))
    elif tag in ("Chapitre", "SousChapitre", "Cas", "Situation"):
        if t := _titre(el):
            lignes.append(t + (" :" if tag in ("Cas", "Situation") else ""))
        for enfant in el:
            _rendre(enfant, lignes)
    elif tag == "TitreFlottant":
        if t := _texte(el):
            lignes.append(t)
    elif tag in SP_ENCADRES:
        sous = []
        for enfant in el:
            _rendre(enfant, sous)
        titre = _titre(el)
        if sous:
            entete = SP_ENCADRES[tag] + (f" ({titre})" if titre and titre != SP_ENCADRES[tag] else "")
            lignes.append(f"{entete} : {sous[0]}")
            lignes.extend(sous[1:])
    else:  # Texte, Liste, Tableau, BlocCas, Introduction... : conteneurs
        for enfant in el:
            _rendre(enfant, lignes)


def fiche_service_public(xml: bytes) -> dict | None:
    """Entree du catalogue pour une fiche pratique retenue, None sinon."""
    r = ET.fromstring(xml)
    if r.findtext(DC + "type") != "Fiche pratique" or r.get("type") != "Fiche d'information conditionnée":
        return None
    sous_theme = r.findtext("SousThemePere") or ""
    dossier = r.findtext("DossierPere/Titre") or ""
    matiere = SP_MATIERES.get((sous_theme, dossier)) or SP_MATIERES.get((sous_theme, None))
    if not matiere:
        return None
    sections: list[dict] = []
    intro: list[str] = []
    for el in r.findall("Introduction"):
        _rendre(el, intro)
    if intro:
        sections.append({"titre": "", "texte": "\n".join(intro)})
    for texte in r.findall("Texte"):
        hors_chapitre: list[str] = []
        for el in texte:
            if el.tag == "Chapitre":
                lignes: list[str] = []
                for enfant in el:
                    _rendre(enfant, lignes)
                if lignes:
                    sections.append({"titre": _titre(el), "texte": "\n".join(lignes)})
            else:
                _rendre(el, hors_chapitre)
        if hors_chapitre:
            sections.append({"titre": "", "texte": "\n".join(hors_chapitre)})
    references = [f"- {_titre(ref)}" for ref in r.iter("Reference") if ref.get("type") == "Texte de référence" and _titre(ref)]
    if references:
        sections.append({"titre": "Textes de référence", "texte": "\n".join(dict.fromkeys(references))})
    if not sections:
        return None
    date = (r.findtext(DC + "date") or "").replace("modified", "").strip()
    return {
        "id": "sp-" + r.get("ID", "").lower(),
        "titre": r.findtext(DC + "title") or "",
        "matiere": matiere,
        "auteur": r.findtext(DC + "creator") or "Direction de l'information légale et administrative",
        "source": "Service Public / DILA",
        "source_url": "https://www.service-public.gouv.fr/",
        "url_original": r.get("spUrl", ""),
        "licence": "etalab-2.0",
        "mis_a_jour": date,
        "modifications": SP_MODIFICATIONS,
        "sections": sections,
    }


def service_public(client: httpx.Client | None) -> list[dict]:
    if client is not None and (not SP_ZIP.exists() or time.time() - SP_ZIP.stat().st_mtime > 20 * 3600):
        SP_ZIP.parent.mkdir(parents=True, exist_ok=True)
        tmp = SP_ZIP.with_suffix(".tmp")
        with client.stream("GET", SP_ZIP_URL) as r:
            r.raise_for_status()
            with tmp.open("wb") as f:
                for bloc in r.iter_bytes():
                    f.write(bloc)
        tmp.replace(SP_ZIP)
    if not SP_ZIP.exists():
        print("service-public : archive absente (mode hors ligne)", file=sys.stderr)
        return []
    out = []
    with zipfile.ZipFile(SP_ZIP) as z:
        for nom in z.namelist():
            if re.fullmatch(r"F\d+\.xml", nom) and (c := fiche_service_public(z.read(nom))):
                out.append(c)
    return out


# ---------------------------------------------------------------------------------------------------------------
# Wikiversite et Wikilivres


@dataclass(frozen=True)
class PageWiki:
    site: str          # fr.wikiversity.org ou fr.wikibooks.org
    titre: str         # page principale de la lecon ou du livre
    matiere: str
    relecture: str     # pourquoi la page est retenue (relecture du 2026-11-19)


# Choisies une a une apres relecture (docs/cours-libres.md, partie 6) : date, articles et institutions cites
# encore en vigueur. Une page absente ici n'est jamais recuperee.
WIKI: tuple[PageWiki, ...] = ()

NOMS_WIKI = {"fr.wikiversity.org": "Wikiversité", "fr.wikibooks.org": "Wikilivres"}
WIKI_IGNORES = ("mw-editsection", "reference", "references", "navbox", "toc", "noprint", "thumb", "metadata",
                "mw-empty-elt", "bandeau", "infobox", "cadre", "mw-references-wrap", "printfooter", "catlinks")
WIKI_MODIFICATIONS = ("Texte repris des chapitres de la page ; mise en forme, images, modèles de navigation et "
                      "notes non repris.")


def _api(client: httpx.Client | None, site: str, **params) -> dict:
    cache = RAW / "wiki" / site / (re.sub(r"[^\w.-]+", "_", json.dumps(params, sort_keys=True))[:180] + ".json")
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    if client is None:
        raise RuntimeError("absent du cache (mode hors ligne)")
    for _ in range(3):
        time.sleep(PAUSE_WIKI)
        debut = time.monotonic()
        r = client.get(f"https://{site}/w/api.php", params={**params, "format": "json", "formatversion": "2"})
        if time.monotonic() - debut > 1:
            time.sleep(5)  # politique Wikimedia : 5 s apres toute requete de plus d'une seconde
        if r.status_code != 429:
            break
        time.sleep(min(float(r.headers.get("Retry-After") or 60), 600))
    r.raise_for_status()
    donnees = r.json()
    if "error" in donnees:
        raise RuntimeError(f"{site} : {donnees['error'].get('info')}")
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(donnees, ensure_ascii=False), encoding="utf-8")
    return donnees


def _ignorer(el: Tag) -> bool:
    classes = el.get("class") or []
    return (el.name in ("style", "script", "figure", "img", "sup", "math", "gallery")
            or any(c in WIKI_IGNORES or c.startswith("navbox") for c in classes)
            or el.get("role") == "navigation")


def texte_wiki(html: str) -> list[dict]:
    """Sections (titre h2, texte) d'une page rendue ; h3 et plus deviennent des lignes de titre."""
    racine = BeautifulSoup(html, "html.parser")
    sections: list[dict] = [{"titre": "", "lignes": []}]

    def ligne(t: str) -> None:
        t = re.sub(r"\s+", " ", t).strip()
        if t:
            sections[-1]["lignes"].append(t)

    def parcourir(el: Tag) -> None:
        for enfant in el.children:
            if isinstance(enfant, NavigableString) or not isinstance(enfant, Tag) or _ignorer(enfant):
                continue
            nom = enfant.name
            if nom == "h2" or (nom == "div" and "mw-heading2" in (enfant.get("class") or [])):
                sections.append({"titre": re.sub(r"\s+", " ", enfant.get_text(" ")).replace("[modifier | modifier le wikicode]", "").strip(), "lignes": []})
            elif re.fullmatch(r"h[3-6]", nom) or (nom == "div" and any(c.startswith("mw-heading") for c in enfant.get("class") or [])):
                for e in enfant.select(".mw-editsection"):
                    e.decompose()
                ligne(enfant.get_text(" "))
            elif nom in ("p", "dt", "dd", "blockquote", "pre"):
                ligne(enfant.get_text(" "))
            elif nom == "li":
                for sous in enfant.find_all(["ul", "ol"], recursive=False):
                    sous.extract()
                    texte = enfant.get_text(" ")
                    ligne("- " + texte)
                    parcourir(sous)
                    break
                else:
                    ligne("- " + enfant.get_text(" "))
            elif nom == "tr":
                cellules = [re.sub(r"\s+", " ", c.get_text(" ")).strip() for c in enfant.find_all(["td", "th"], recursive=False)]
                if any(cellules):
                    ligne(" | ".join(cellules))
            else:
                parcourir(enfant)

    for e in racine.select("sup.reference, .mw-editsection"):
        e.decompose()
    parcourir(racine)
    return [{"titre": s["titre"], "texte": "\n".join(s["lignes"])} for s in sections if s["lignes"]]


def _chapitres(html: str, page: PageWiki) -> list[str]:
    """Sous-pages liees depuis la page principale, dans l'ordre ou elles y apparaissent."""
    vus: list[str] = []
    for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        titre = a.get("title") or ""
        if titre.startswith(page.titre + "/") and "action=" not in a["href"] and titre not in vus:
            vus.append(titre)
    return vus


def cours_wiki(client: httpx.Client | None, page: PageWiki) -> dict:
    principale = _api(client, page.site, action="parse", page=page.titre, prop="text|revid", redirects="1")["parse"]
    sections = [s for s in texte_wiki(principale["text"]) if s["titre"] or len(s["texte"]) > 200]
    revs = [principale["revid"]]
    for chapitre in _chapitres(principale["text"], page):
        p = _api(client, page.site, action="parse", page=chapitre, prop="text|revid", redirects="1")["parse"]
        revs.append(p["revid"])
        corps = "\n".join((f"{s['titre']}\n" if s["titre"] else "") + s["texte"] for s in texte_wiki(p["text"]))
        if corps.strip():
            sections.append({"titre": chapitre.split("/", 1)[1], "texte": corps})
    infos = _api(client, page.site, action="query", prop="revisions", rvprop="timestamp",
                 revids="|".join(map(str, revs)))
    dates = [r["timestamp"][:10] for p in infos["query"]["pages"] for r in p.get("revisions", [])]
    nom = NOMS_WIKI[page.site]
    base = f"https://{page.site}/wiki/"
    url = base + page.titre.replace(" ", "_")
    return {
        "id": "wiki-" + re.sub(r"[^a-z0-9]+", "-", (nom + " " + page.titre).lower()
                                .translate(str.maketrans("àâäéèêëîïôöùûüçœ’'", "aaaeeeeiioouuuco--"))).strip("-")[:90],
        "titre": page.titre,
        "matiere": page.matiere,
        "auteur": f"Contributeurs de {nom}",
        "source": nom,
        "source_url": base,
        "url_original": url,
        "historique_url": f"https://{page.site}/w/index.php?title={page.titre.replace(' ', '_')}&action=history",
        "licence": "cc-by-sa-4.0",
        "mis_a_jour": max(dates),
        "modifications": WIKI_MODIFICATIONS,
        "sections": sections,
    }


# ---------------------------------------------------------------------------------------------------------------
# Index : passages a part du corpus officiel (D103)


def _morceaux(texte: str, taille: int = TAILLE_PASSAGE) -> list[str]:
    """Coupe aux fins de ligne, en morceaux d'au plus `taille` caracteres (une ligne plus longue reste entiere)."""
    out, courant = [], ""
    for ligne in texte.splitlines():
        if courant and len(courant) + 1 + len(ligne) > taille:
            out.append(courant)
            courant = ligne
        else:
            courant = f"{courant}\n{ligne}" if courant else ligne
    if courant:
        out.append(courant)
    return out


def passages(cours: list[dict], date_recuperation: str) -> dict[str, list[Passage]]:
    """Passages de l'index par source (SOURCE_INDEX), type « doctrine ». Pas de `meta.date` : ces fiches ne
    doivent pas entrer dans la fraicheur des sources officielles (table `fraicheur`, /fraicheur)."""
    out: dict[str, list[Passage]] = {}
    for c in cours:
        source_id = SOURCE_INDEX.get(c["source"])
        if source_id is None:
            continue
        assert source_id in SOURCES_A_PART
        n = 0
        for section in c["sections"]:
            for morceau in _morceaux(section["texte"]):
                n += 1
                out.setdefault(source_id, []).append(Passage(
                    id=f"{source_id}:{c['id']}:{n}",
                    source_id=source_id,
                    type="doctrine",
                    numero=None,
                    titre=c["titre"],
                    alineas=[morceau],
                    url=c["url_original"],
                    version=f"mise à jour du {c['mis_a_jour']}",
                    date_recuperation=date_recuperation,
                    meta={"cours_id": c["id"], "matiere": c["matiere"], "source": c["source"],
                          "licence": c["licence"], "mis_a_jour": c["mis_a_jour"], "section": section["titre"]},
                    entete=" > ".join(t for t in (c["titre"], section["titre"]) if t),
                ))
    return out


def ecrire_passages(par_source: dict[str, list[Passage]], dossier: Path = PASSAGES_DIR) -> None:
    """Une source sans aucune fiche cette fois-ci (telechargement echoue) garde son fichier precedent."""
    dossier.mkdir(parents=True, exist_ok=True)
    for source_id, liste in par_source.items():
        cible = dossier / f"{source_id}.jsonl"
        tmp = cible.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            for p in liste:
                f.write(json.dumps(p.to_dict(), ensure_ascii=False) + "\n")
        tmp.replace(cible)


# ---------------------------------------------------------------------------------------------------------------


def ecrire(cours: list[dict], cible: Path = CATALOGUE) -> list[dict]:
    """Valide chaque entree avec le modele de l'API ; les entrees invalides sont signalees et laissees de cote."""
    valides, vus = [], set()
    for c in cours:
        try:
            CoursRecupere.model_validate(c)
        except ValueError as e:
            print(f"ecarte {c.get('id')} : {e}".splitlines()[0], file=sys.stderr)
            continue
        if c["id"] not in vus:
            vus.add(c["id"])
            valides.append(c)
    cible.parent.mkdir(parents=True, exist_ok=True)
    tmp = cible.with_suffix(".tmp")
    tmp.write_text(json.dumps(valides, ensure_ascii=False), encoding="utf-8")
    tmp.replace(cible)
    return valides


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--hors-ligne", action="store_true", help="aucun telechargement")
    args = ap.parse_args(argv)
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=120, follow_redirects=True) as client:
        cours = service_public(None if args.hors_ligne else client)
    ua_wiki = f"CoursLibresIngest/0.1 ({WIKIMEDIA_CONTACT}) httpx/{httpx.__version__}"
    with httpx.Client(headers={"User-Agent": ua_wiki, "Accept-Encoding": "gzip"}, timeout=60) as client:
        en_ligne = None if args.hors_ligne or not WIKIMEDIA_CONTACT else client
        if WIKI and en_ligne is None and not args.hors_ligne:
            print("wikis : WIKIMEDIA_CONTACT absent, seules les pages deja en cache sont reprises", file=sys.stderr)
        for page in WIKI:
            try:
                cours.append(cours_wiki(en_ligne, page))
            except (httpx.HTTPError, RuntimeError, KeyError) as e:
                print(f"{page.site} {page.titre} : {e}", file=sys.stderr)
    valides = ecrire(cours)
    par_source: dict[str, int] = {}
    for c in valides:
        par_source[c["source"]] = par_source.get(c["source"], 0) + 1
    print(f"{len(valides)} cours dans {CATALOGUE.relative_to(ROOT)} : {par_source}")
    index = passages(valides, time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    ecrire_passages(index)
    print("passages pour l'index : " + ", ".join(f"{s} {len(l)}" for s, l in index.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
