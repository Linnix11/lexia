"""Construit le dossier de relecture a partir de questions.json et reponses.jsonl.

Usage (Python du systeme, avec python-docx et openpyxl) :
    python3 docs/relecture-enseignant/outils/generer.py

Ecrit dans docs/relecture-enseignant/ : dossier.md, dossier.docx, grille.xlsx, lettre.docx (depuis lettre.md).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT  # noqa: F401
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

DOSSIER = Path(__file__).resolve().parent.parent
DATE = "24 novembre 2026"
VERSION = "60f0f03"

PRESENTATION = [
    "Lexia est un assistant d'étude du droit français destiné aux étudiants de licence (L1 à L3), publié par Axion Studio et accessible sur https://lexia-axionstudio.cloud.",
    "Il ne répond pas « de mémoire » : à chaque question, il cherche d'abord dans un index d'environ 926 600 passages (codes et lois issus de Légifrance, Constitution, jurisprudence judiciaire et administrative, cours en libre accès).",
    "Les huit extraits les plus pertinents sont transmis à un modèle de langue (Gemini, de Google, au niveau gratuit ; Groq en secours quand Gemini est indisponible).",
    "Le modèle a pour consigne de n'énoncer aucune règle qui ne figure pas dans ces extraits et de citer, pour chaque affirmation, l'extrait qui la fonde.",
    "Un contrôle automatique retire ensuite toute citation qui ne correspond pas à un extrait fourni et toute phrase qui mentionne un article ou une décision absents des extraits.",
    "Pour chaque article cité, Lexia indique la version et si elle est en vigueur à la date du jour ; une ancienne numérotation du Code civil (avant 2016) est signalée.",
    "Cinq modes de réponse : expliquer une notion, fiche de révision, cas pratique (syllogisme), commentaire d'arrêt, dissertation (problématique et plan).",
    "Quand les extraits ne suffisent pas, Lexia doit le dire (« abstention ») plutôt qu'inventer ; il refuse aussi le conseil personnel (rédiger, chiffrer, prédire un procès).",
    "Chaque réponse porte un avertissement : Lexia est un outil d'étude, pas un avis juridique, et les sources doivent être vérifiées.",
    "La vente d'abonnements est prévue pour janvier 2027 : votre relecture est la première évaluation indépendante de la qualité juridique des réponses.",
]

MODE_EMPLOI = [
    "Le dossier contient 30 questions posées à Lexia le 24 novembre 2026, avec la réponse obtenue telle quelle, sans retouche : 12 questions de cours, 8 cas pratiques, 5 demandes de fiche ou de plan de dissertation, 5 questions pièges.",
    "Les questions pièges (n° 26 à 30) portent sur un texte abrogé, une notion confondue, un droit étranger ou une décision introuvable : elles servent à voir si Lexia admet ses limites. Une abstention y est une bonne réponse.",
    "Pour chaque réponse sont indiqués le modèle qui a répondu (Gemini ou Groq) et les sources citées, avec leur lien. Les repères [S1], [S2]... renvoient à la liste des sources de la réponse.",
    "Notez chaque réponse sur les cinq critères de la grille, de 0 à 3. Un critère sans objet (par exemple la méthode pour une simple définition) peut rester vide.",
    "Les notes se saisissent au choix sur la version imprimée (cases sous chaque réponse) ou dans le classeur grille.xlsx, qui calcule les moyennes.",
    "Un commentaire court suffit ; il est le plus utile quand une réponse est fausse, incomplète ou dangereuse pour un étudiant : dites ce qui manque ou ce qui est inexact.",
    "Le bas de la grille demande votre avis d'ensemble : utiliseriez-vous ou conseilleriez-vous Lexia ?",
    "Durée indicative : deux à trois heures. Vos notes ne seront pas publiées sans votre accord écrit.",
]

CRITERES = [
    ("Exactitude juridique", "Exactitude", "Les règles énoncées sont justes et complètes au regard du programme ; aucune erreur de droit."),
    ("Sources pertinentes et à jour", "Sources", "Les articles et décisions cités fondent bien la réponse ; versions en vigueur ; jurisprudence de référence présente."),
    ("Méthode", "Méthode", "Syllogisme en cas pratique, problématique et plan en dissertation, définition puis conditions en question de cours."),
    ("Clarté pour un étudiant de L1 à L3", "Clarté", "Vocabulaire exact, phrases lisibles, niveau adapté, pas de détour inutile."),
    ("Aveu des limites", "Limites", "Lexia signale ce qu'elle ne sait pas ou ne trouve pas, et ne comble pas les vides par une invention."),
]
ECHELLE = [
    ("0", "Faux, absent ou trompeur"),
    ("1", "Insuffisant : erreurs ou manques importants"),
    ("2", "Correct avec des réserves"),
    ("3", "Satisfaisant, utilisable tel quel par un étudiant"),
]
QUESTION_FINALE = "Utiliseriez-vous Lexia, ou le conseilleriez-vous à vos étudiants ?"
CHOIX_FINAL = ("Oui", "Oui, avec réserves", "Non")

STATUTS = {
    "reponse": "Réponse",
    "abstention": "Abstention (Lexia dit que ses sources ne permettent pas de répondre)",
    "hors_champ": "Hors champ (Lexia refuse de répondre)",
}
MATIERES = {
    "introduction_au_droit": "Introduction au droit", "droit_constitutionnel": "Droit constitutionnel",
    "droit_civil": "Droit civil", "droit_de_la_famille": "Droit de la famille", "droit_des_biens": "Droit des biens",
    "droit_des_contrats": "Droit des contrats", "droit_administratif": "Droit administratif",
    "droit_penal": "Droit pénal", "procedure_civile": "Procédure civile", "procedure_penale": "Procédure pénale",
    None: "Aucune (toutes matières)",
}
MODES = {"expliquer": "Expliquer", "fiche": "Fiche de révision", "cas_pratique": "Cas pratique",
         "commentaire": "Commentaire d'arrêt", "dissertation": "Dissertation"}
RUBRIQUES = (("reponse_directe", "En bref"), ("droit_positif", "Droit positif"),
             ("explication", "Explication"), ("points_incertains", "Points incertains"))


def modele_lisible(m: str | None) -> str:
    if not m:
        return "aucun"
    return f"Gemini ({m})" if m.startswith("gemini") else f"Groq ({m})"


def fournisseur(m: str | None) -> str:
    if not m:
        return "aucun"
    return "Gemini" if m.startswith("gemini") else "Groq"


def charger() -> list[dict]:
    questions = json.loads((DOSSIER / "questions.json").read_text(encoding="utf-8"))
    reponses = {}
    for line in (DOSSIER / "reponses.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            reponses[d["n"]] = d
    for q in questions:
        q["resultat"] = reponses.get(q["n"], {})
    return questions


def labels(r: dict) -> dict[str, str]:
    return {s["id"]: s["label"] or "?" for s in r.get("sources") or []}


def elements(r: dict) -> list[tuple[str, list[tuple[str | None, str]]]]:
    """[(titre de rubrique, [(sous-rubrique, texte avec repères)])]"""
    lab = labels(r)
    out = []
    for cle, titre in RUBRIQUES:
        lignes = []
        for e in r.get(cle) or []:
            reps = sorted({lab.get(pid, "?") for pid in e.get("sources") or []}, key=lambda x: (len(x), x))
            texte = e["texte"].strip() + (f" [{', '.join(reps)}]" if reps else "")
            lignes.append((e.get("rubrique"), texte))
        if lignes:
            out.append((titre, lignes))
    return out


def source_ligne(s: dict) -> str:
    entete = s.get("entete") or s["id"]
    vig = "" if s.get("en_vigueur") is not False else " [version qui n'est plus en vigueur]"
    date = f", {s['date']}" if s.get("date") and s["date"] not in entete else ""
    return f"{s.get('label') or '?'} : {entete}{date}{vig}"


NON_OBTENUE = ("Réponse non obtenue : Gemini était indisponible (erreurs 503 puis quota gratuit épuisé) lors de la "
               "production du dossier. À compléter avant l'envoi à l'enseignant.")


def statut_lisible(res: dict) -> str:
    return STATUTS.get(res.get("statut"), "non obtenue")


def nb_controle(r: dict) -> str:
    c = r.get("controle") or {}
    n1, n2 = c.get("citations_retirees", 0), c.get("elements_retires", 0)
    if not (n1 or n2):
        return ""
    return (f"Contrôle automatique : {n1} citation(s) et {n2} phrase(s) retirée(s) avant affichage "
            "(source inexistante ou référence absente des extraits).")


# --------------------------------------------------------------------------- Markdown

def markdown(questions: list[dict]) -> str:
    md = [f"# Lexia : dossier de relecture par un enseignant en droit", "",
          f"Axion Studio, {DATE}. Réponses produites par le moteur de Lexia (version {VERSION}), sans retouche.", "",
          "Version imprimable avec cases de notation : `dossier.docx`. Saisie des notes : `grille.xlsx`. "
          "Lettre d'accompagnement : `lettre.md`.", "",
          "## 1. Lexia en dix lignes", ""]
    md += [f"{i}. {t}" for i, t in enumerate(PRESENTATION, 1)]
    md += ["", "## 2. Mode d'emploi de la relecture", ""]
    md += [f"- {t}" for t in MODE_EMPLOI]
    md += ["", "## 3. Grille de notation", "", "Échelle commune aux cinq critères :", ""]
    md += [f"- **{n}** : {t}" for n, t in ECHELLE]
    md += ["", "| Critère | Ce qui est évalué | Note (0 à 3) | Commentaire |", "|---|---|---|---|"]
    md += [f"| {c} | {d} | | |" for c, _, d in CRITERES]
    md += ["", f"**Question finale.** {QUESTION_FINALE} ({' / '.join(CHOIX_FINAL)}) Pourquoi ?", "",
           "## 4. Les 30 questions et les réponses de Lexia", "",
           "| N° | Catégorie | Matière | Niveau | Mode | Modèle | Statut |", "|---|---|---|---|---|---|---|"]
    for q in questions:
        res = q["resultat"]
        md.append(f"| {q['n']} | {q['categorie']} | {MATIERES[q['matiere']]} | {q['niveau']} | {MODES[q['mode']]} "
                  f"| {fournisseur(res.get('modele'))} | {res.get('statut') or 'non obtenue'} |")
    for q in questions:
        res = q["resultat"]
        r = res.get("reponse") or {}
        md += ["", "---", "", f"### Question {q['n']} ({q['categorie']})", "",
               f"Matière : {MATIERES[q['matiere']]}. Niveau : {q['niveau']}. Mode : {MODES[q['mode']]}.", "",
               f"> {q['question']}", "",
               f"**Modèle qui a répondu** : {modele_lisible(res.get('modele'))}. "
               f"**Statut** : {statut_lisible(res)}.", ""]
        if not res.get("statut"):
            md += [f"**{NON_OBTENUE}**", ""]
            continue
        if r.get("titre"):
            md += [f"**{r['titre']}**", ""]
        if r.get("message"):
            md += [f"Message de Lexia : {r['message']}", ""]
        for titre, lignes in elements(r):
            md += [f"*{titre}*", ""]
            for sous, texte in lignes:
                md.append(f"- {'**' + sous + '** : ' if sous else ''}{texte}")
            md.append("")
        if nb_controle(r):
            md += [nb_controle(r), ""]
        sources = r.get("sources") or []
        md += ["*Sources citées*", ""]
        md += [f"- {source_ligne(s)} ({s['url']})" for s in sources] or ["- Aucune source citée."]
        md += ["", "Notes : Exactitude __/3 · Sources __/3 · Méthode __/3 · Clarté __/3 · Limites __/3", ""]
    return "\n".join(md) + "\n"


# --------------------------------------------------------------------------- Word

def ombrer(cellule, couleur: str) -> None:
    tc = cellule._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), couleur)
    tc.append(shd)


def largeurs(table, cms: list[float]) -> None:
    """Largeurs fixes ecrites partout (tblW, tblLayout, tblGrid, tcW) et bordures explicites : sans elles,
    certains lecteurs (apercu macOS, Google Docs) ignorent les largeurs et le style « Table Grid »."""
    table.autofit = False
    tbl = table._tbl
    pr = tbl.tblPr
    for tag in ("w:tblW", "w:tblLayout", "w:tblBorders"):
        for e in pr.findall(qn(tag)):
            pr.remove(e)
    tw = OxmlElement("w:tblW")
    tw.set(qn("w:w"), str(int(sum(cms) * 567)))
    tw.set(qn("w:type"), "dxa")
    pr.append(tw)
    bords = OxmlElement("w:tblBorders")
    for cote in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b = OxmlElement(f"w:{cote}")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), "4")
        b.set(qn("w:space"), "0")
        b.set(qn("w:color"), "8A94A6")
        bords.append(b)
    pr.append(bords)
    lay = OxmlElement("w:tblLayout")
    lay.set(qn("w:type"), "fixed")
    pr.append(lay)
    ordre = ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize", "tblStyleColBandSize", "tblW",
             "jc", "tblCellSpacing", "tblInd", "tblBorders", "shd", "tblLayout", "tblCellMar", "tblLook"]
    enfants = sorted(pr, key=lambda e: ordre.index(e.tag.split("}")[1]) if e.tag.split("}")[1] in ordre else 99)
    for e in enfants:  # ordre impose par le schema OOXML (Word refuse parfois un ordre libre)
        pr.remove(e)
        pr.append(e)
    for col, w in zip(tbl.tblGrid.findall(qn("w:gridCol")), cms):
        col.set(qn("w:w"), str(int(w * 567)))
    for row in table.rows:
        for c, w in zip(row.cells, cms):
            c.width = Cm(w)


def cellule(c, texte: str, gras: bool = False, taille: float = 10) -> None:
    c.text = ""
    p = c.paragraphs[0]
    run = p.add_run(texte)
    run.bold = gras
    run.font.size = Pt(taille)


def styles(doc: Document) -> None:
    st = doc.styles["Normal"]
    st.font.name = "Arial"
    st.font.size = Pt(11)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
    st.paragraph_format.space_after = Pt(4)
    for nom, taille in (("Title", 22), ("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 11.5)):
        s = doc.styles[nom]
        s.font.name = "Arial"
        s.font.size = Pt(taille)
        s.font.bold = True
        s.font.color.rgb = RGBColor(0x1F, 0x2A, 0x44)
        s.element.rPr.rFonts.set(qn("w:asciiTheme"), "")
        s.paragraph_format.space_before = Pt(12 if nom != "Title" else 0)
        s.paragraph_format.space_after = Pt(6)
        s.paragraph_format.keep_with_next = True
    sec = doc.sections[0]
    sec.page_height, sec.page_width = Cm(29.7), Cm(21)
    for m in ("left_margin", "right_margin"):
        setattr(sec, m, Cm(2.2))
    sec.top_margin = sec.bottom_margin = Cm(2)
    pied = sec.footer.paragraphs[0]
    pied.text = f"Lexia, dossier de relecture, {DATE}. Document confidentiel, non destiné à la diffusion."
    pied.runs[0].font.size = Pt(8)


def saut(doc: Document) -> None:
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def grille_page(doc: Document) -> None:
    doc.add_heading("Grille de notation", level=1)
    doc.add_paragraph("Avis d'ensemble sur les 30 réponses (la notation question par question figure sous chaque "
                      "réponse et dans grille.xlsx). Cochez une case de 0 à 3 par critère.")
    t = doc.add_table(rows=1 + len(ECHELLE), cols=2)
    t.style = "Table Grid"
    cellule(t.cell(0, 0), "Note", True)
    cellule(t.cell(0, 1), "Signification", True)
    ombrer(t.cell(0, 0), "DCE3EE")
    ombrer(t.cell(0, 1), "DCE3EE")
    for i, (n, s) in enumerate(ECHELLE, 1):
        cellule(t.cell(i, 0), n, True)
        cellule(t.cell(i, 1), s)
    largeurs(t, [2, 14.6])
    doc.add_paragraph()
    t = doc.add_table(rows=1 + len(CRITERES), cols=7)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, h in enumerate(("Critère", "Ce qui est évalué", "0", "1", "2", "3", "Commentaire")):
        cellule(t.cell(0, j), h, True, 9.5)
        ombrer(t.cell(0, j), "DCE3EE")
    for i, (c, _, d) in enumerate(CRITERES, 1):
        cellule(t.cell(i, 0), c, True, 9.5)
        cellule(t.cell(i, 1), d, False, 8.5)
        for j in range(2, 6):
            cellule(t.cell(i, j), "", False, 9)
        cellule(t.cell(i, 6), "")
        t.rows[i].height = Cm(2.3)
    largeurs(t, [3, 4.8, 1.1, 1.1, 1.1, 1.1, 4.4])
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.add_run("Question finale. ").bold = True
    p.add_run(QUESTION_FINALE)
    doc.add_paragraph("    ".join(f"[  ] {c}" for c in CHOIX_FINAL))
    for _ in range(3):
        doc.add_paragraph("." * 95 if _ else "Pourquoi ? " + "." * 80)
    doc.add_paragraph("Nom, fonction et établissement (facultatif) : " + "." * 50)
    doc.add_paragraph("Date : " + "." * 30)


def notes_question(doc: Document) -> None:
    t = doc.add_table(rows=3, cols=5)
    t.style = "Table Grid"
    for j, (_, court, _) in enumerate(CRITERES):
        cellule(t.cell(0, j), court, True, 9)
        ombrer(t.cell(0, j), "EEF1F6")
        cellule(t.cell(1, j), "      / 3", False, 9)
    largeurs(t, [3.32] * 5)
    fusion = t.cell(2, 0).merge(t.cell(2, 4))
    cellule(fusion, "Commentaire :", False, 9)
    t.rows[2].height = Cm(1.8)


def word(questions: list[dict]) -> Document:
    doc = Document()
    styles(doc)
    doc.add_paragraph("Lexia", style="Title")
    p = doc.add_paragraph()
    r = p.add_run("Dossier de relecture par un enseignant en droit")
    r.font.size = Pt(15)
    r.bold = True
    doc.add_paragraph(f"Axion Studio, {DATE}. 30 questions posées à Lexia (version {VERSION}) et ses réponses, "
                      "reproduites sans retouche.")
    doc.add_heading("Lexia en dix lignes", level=1)
    for i, t in enumerate(PRESENTATION, 1):
        doc.add_paragraph(f"{i}. {t}")
    doc.add_heading("Mode d'emploi de la relecture", level=1)
    for t in MODE_EMPLOI:
        doc.add_paragraph(t, style="List Bullet")
    saut(doc)
    grille_page(doc)
    saut(doc)
    doc.add_heading("Liste des 30 questions", level=1)
    t = doc.add_table(rows=1 + len(questions), cols=6)
    t.style = "Table Grid"
    for j, h in enumerate(("N°", "Catégorie", "Matière", "Niv.", "Modèle", "Statut")):
        cellule(t.cell(0, j), h, True, 9)
        ombrer(t.cell(0, j), "DCE3EE")
    for i, q in enumerate(questions, 1):
        res = q["resultat"]
        vals = (str(q["n"]), q["categorie"], MATIERES[q["matiere"]], q["niveau"], fournisseur(res.get("modele")),
                res.get("statut") or "non obtenue")
        for j, v in enumerate(vals):
            cellule(t.cell(i, j), v, False, 8.5)
    largeurs(t, [1, 5.2, 4.2, 1.2, 2.2, 2.8])
    for q in questions:
        saut(doc)
        res = q["resultat"]
        r = res.get("reponse") or {}
        doc.add_heading(f"Question {q['n']} : {q['categorie']}", level=2)
        doc.add_paragraph(f"{MATIERES[q['matiere']]}, {q['niveau']}, mode {MODES[q['mode']].lower()}.").runs[0].italic = True
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.6)
        p.add_run(q["question"]).bold = True
        p = doc.add_paragraph()
        p.add_run("Modèle : ").bold = True
        p.add_run(modele_lisible(res.get("modele")) + ".  ")
        p.add_run("Statut : ").bold = True
        p.add_run(statut_lisible(res) + ".")
        if not res.get("statut"):
            doc.add_paragraph().add_run(NON_OBTENUE).bold = True
            continue
        if r.get("titre"):
            doc.add_heading(r["titre"], level=3)
        if r.get("message"):
            doc.add_paragraph(f"Message de Lexia : {r['message']}")
        for titre, lignes in elements(r):
            pt = doc.add_paragraph()
            pt.add_run(titre).bold = True
            pt.paragraph_format.keep_with_next = True
            for sous, texte in lignes:
                pl = doc.add_paragraph(style="List Bullet")
                if sous:
                    pl.add_run(sous + " : ").bold = True
                pl.add_run(texte)
        if nb_controle(r):
            doc.add_paragraph(nb_controle(r)).runs[0].italic = True
        pt = doc.add_paragraph()
        pt.add_run("Sources citées").bold = True
        pt.paragraph_format.keep_with_next = True
        for s in r.get("sources") or []:
            pl = doc.add_paragraph(style="List Bullet")
            run = pl.add_run(source_ligne(s))
            run.font.size = Pt(9.5)
            u = pl.add_run(f" {s['url']}")
            u.font.size = Pt(8)
            u.font.color.rgb = RGBColor(0x44, 0x55, 0x77)
        if not r.get("sources"):
            doc.add_paragraph("Aucune source citée.", style="List Bullet")
        doc.add_paragraph().paragraph_format.space_after = Pt(2)
        notes_question(doc)
    return doc


# --------------------------------------------------------------------------- Excel

def excel(questions: list[dict]):
    wb = Workbook()
    fin = Side(style="thin", color="A6B0C3")
    bord = Border(left=fin, right=fin, top=fin, bottom=fin)
    entete = PatternFill("solid", fgColor="DCE3EE")
    saisie = PatternFill("solid", fgColor="FFF6CC")
    police = Font(name="Arial", size=10)
    gras = Font(name="Arial", size=10, bold=True)

    # Feuille 1 : mode d'emploi
    me = wb.active
    me.title = "Mode d'emploi"
    lignes = [
        ("Lexia : grille de notation de la relecture", True),
        (f"Axion Studio, {DATE}. 30 réponses de Lexia (version {VERSION}), détaillées dans dossier.md ou dossier.docx.", False),
        ("", False),
        ("Cellules à remplir : uniquement les cellules sur fond jaune.", True),
        ("Feuille « Notes » : une note de 0 à 3 par critère et par question (colonnes H à L), et un commentaire (colonne N). Un critère sans objet peut rester vide.", False),
        ("Feuille « Synthèse » : la question finale (cellule B12) et son explication (B13). Les moyennes se calculent seules.", False),
        ("", False),
        ("Échelle commune aux cinq critères", True),
        *[(f"{n} : {t}", False) for n, t in ECHELLE],
        ("", False),
        ("Les cinq critères", True),
        *[(f"{c} : {d}", False) for c, _, d in CRITERES],
        ("", False),
        ("Exemple de saisie (fictif, ne pas recopier)", True),
        ("Question 4 : Exactitude 3, Sources 2, Méthode 3, Clarté 3, Limites 2. Commentaire : « Juste, mais l'arrêt Derguini sur la faute de l'infans manque. »", False),
    ]
    for i, (t, g) in enumerate(lignes, 1):
        c = me.cell(row=i, column=1, value=t)
        c.font = Font(name="Arial", size=12 if i == 1 else 10, bold=g)
        c.alignment = Alignment(wrap_text=True, vertical="top")
    me.column_dimensions["A"].width = 120

    # Feuille 2 : notes
    ws = wb.create_sheet("Notes")
    cols = ["N°", "Catégorie", "Matière", "Niveau", "Mode", "Question", "Modèle",
            *[c[1] + " (0-3)" for c in CRITERES], "Total (sur 15)", "Commentaire"]
    for j, h in enumerate(cols, 1):
        c = ws.cell(row=1, column=j, value=h)
        c.font, c.fill, c.border = gras, entete, bord
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    dv = DataValidation(type="whole", operator="between", formula1="0", formula2="3", allow_blank=True,
                        showErrorMessage=True, errorTitle="Note invalide", error="Saisir un entier de 0 à 3.")
    ws.add_data_validation(dv)
    for i, q in enumerate(questions, 2):
        vals = [q["n"], q["categorie"], MATIERES[q["matiere"]], q["niveau"], MODES[q["mode"]], q["question"],
                fournisseur(q["resultat"].get("modele"))]
        for j, v in enumerate(vals, 1):
            c = ws.cell(row=i, column=j, value=v)
            c.font, c.border = police, bord
            c.alignment = Alignment(wrap_text=True, vertical="top")
        for j in range(8, 13):
            c = ws.cell(row=i, column=j)
            c.fill, c.border, c.font = saisie, bord, police
            c.alignment = Alignment(horizontal="center", vertical="top")
        dv.add(f"H{i}:L{i}")
        t = ws.cell(row=i, column=13, value=f'=IF(COUNT(H{i}:L{i})=0,"",SUM(H{i}:L{i}))')
        t.font, t.border = gras, bord
        t.alignment = Alignment(horizontal="center", vertical="top")
        c = ws.cell(row=i, column=14)
        c.fill, c.border, c.font = saisie, bord, police
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[i].height = 48
    for col, w in zip("ABCDEFGHIJKLMN", (5, 22, 18, 7, 13, 60, 9, 11, 11, 11, 11, 11, 10, 50)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "H2"
    dernier = len(questions) + 1

    # Feuille 3 : synthese
    sy = wb.create_sheet("Synthèse")
    sy["A1"] = "Synthèse (calculée à partir de la feuille Notes)"
    sy["A1"].font = Font(name="Arial", size=12, bold=True)
    sy["A3"], sy["B3"], sy["C3"] = "Critère", "Moyenne (sur 3)", "Réponses notées"
    for c in ("A3", "B3", "C3"):
        sy[c].font, sy[c].fill, sy[c].border = gras, entete, bord
    for k, (nom, _, _) in enumerate(CRITERES):
        r = 4 + k
        col = "HIJKL"[k]
        sy.cell(row=r, column=1, value=nom)
        sy.cell(row=r, column=2, value=f'=IFERROR(AVERAGE(Notes!{col}2:{col}{dernier}),"")').number_format = "0.00"
        sy.cell(row=r, column=3, value=f"=COUNT(Notes!{col}2:{col}{dernier})")
        for j in (1, 2, 3):
            sy.cell(row=r, column=j).font = police
            sy.cell(row=r, column=j).border = bord
    sy["A9"] = "Total moyen (sur 15)"
    sy["B9"] = f'=IFERROR(AVERAGE(Notes!M2:M{dernier}),"")'
    sy["B9"].number_format = "0.00"
    for c in ("A9", "B9"):
        sy[c].font, sy[c].border = gras, bord
    sy["A11"] = "Question finale"
    sy["A11"].font = gras
    sy["A12"] = QUESTION_FINALE
    sy["A13"] = "Pourquoi ?"
    for c in ("A12", "A13"):
        sy[c].font = police
        sy[c].alignment = Alignment(wrap_text=True, vertical="top")
    for c in ("B12", "B13"):
        sy[c].fill, sy[c].border, sy[c].font = saisie, bord, police
        sy[c].alignment = Alignment(wrap_text=True, vertical="top")
    choix = DataValidation(type="list", formula1='"' + ",".join(CHOIX_FINAL) + '"', allow_blank=True)
    sy.add_data_validation(choix)
    choix.add("B12")
    sy.row_dimensions[12].height = 30
    sy.row_dimensions[13].height = 90
    sy["A15"] = "Moyenne par catégorie de questions (total sur 15)"
    sy["A15"].font = gras
    cats = list(dict.fromkeys(q["categorie"].split(" (")[0] for q in questions))
    for k, cat in enumerate(cats):
        r = 16 + k
        sy.cell(row=r, column=1, value=cat).font = police
        c = sy.cell(row=r, column=2, value=f'=IFERROR(AVERAGEIF(Notes!B2:B{dernier},"{cat}*",Notes!M2:M{dernier}),"")')
        c.number_format, c.font = "0.00", police
    sy.column_dimensions["A"].width = 55
    sy.column_dimensions["B"].width = 45
    sy.column_dimensions["C"].width = 16
    wb.move_sheet("Synthèse", offset=-1)
    wb.active = 0
    return wb


# --------------------------------------------------------------------------- lettre

def lettre_docx() -> Document:
    doc = Document()
    styles(doc)
    doc.sections[0].footer.paragraphs[0].text = ""
    for bloc in (DOSSIER / "lettre.md").read_text(encoding="utf-8").split("\n\n"):
        bloc = bloc.strip()
        if not bloc or bloc.startswith("<!--"):
            continue
        if bloc.startswith("# "):
            continue
        p = doc.add_paragraph()
        for k, ligne in enumerate(bloc.splitlines()):
            if k:
                p.add_run().add_break()
            morceaux = re.split(r"(\*\*[^*]+\*\*)", ligne.rstrip("\\ ").strip())
            for m in morceaux:
                if m.startswith("**"):
                    p.add_run(m.strip("*")).bold = True
                elif m:
                    p.add_run(m)
    return doc


def main() -> None:
    questions = charger()
    (DOSSIER / "dossier.md").write_text(markdown(questions), encoding="utf-8")
    word(questions).save(DOSSIER / "dossier.docx")
    excel(questions).save(DOSSIER / "grille.xlsx")
    if (DOSSIER / "lettre.md").exists():
        lettre_docx().save(DOSSIER / "lettre.docx")
    print("ecrit :", ", ".join(p.name for p in sorted(DOSSIER.glob("*.*"))))


if __name__ == "__main__":
    main()
