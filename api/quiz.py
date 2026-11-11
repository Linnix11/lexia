"""Questionnaires : generation a partir du corpus, validation, stockage temporaire et correction.

Les questions sont gardees en memoire (TTL) avec leurs reponses : le client ne recoit jamais
les bonnes reponses avant la correction. Aucune donnee personnelle n'est conservee.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field

from api import prompts
from api.citations import Controle, labels_valides, verifier_texte
from api.journal import Journal
from api.llm.base import LLM, LLMError
from api.rag import AVERTISSEMENT, Lexia, fiche_source, table_extraits

K_QUIZ = 12
TTL_SECONDES = 3 * 3600
MAX_QUIZ = 500


@dataclass
class Quiz:
    id: str
    format: str
    theme: str
    questions: list[dict]
    table: dict[str, dict]
    cree: float = field(default_factory=time.time)


class QuizStore:
    def __init__(self, ttl: int = TTL_SECONDES, maximum: int = MAX_QUIZ):
        self._ttl, self._max = ttl, maximum
        self._items: dict[str, Quiz] = {}
        self._lock = threading.Lock()

    def ajouter(self, quiz: Quiz) -> None:
        with self._lock:
            self._purger()
            if len(self._items) >= self._max:
                plus_ancien = min(self._items.values(), key=lambda q: q.cree)
                del self._items[plus_ancien.id]
            self._items[quiz.id] = quiz

    def get(self, quiz_id: str) -> Quiz | None:
        with self._lock:
            self._purger()
            return self._items.get(quiz_id)

    def _purger(self) -> None:
        limite = time.time() - self._ttl
        for k in [k for k, q in self._items.items() if q.cree < limite]:
            del self._items[k]


def _valider_question(q: dict, fmt: str, table: dict[str, dict], controle: Controle) -> dict | None:
    passages = list(table.values())
    sources = labels_valides(q.get("sources"), table, controle)
    if not sources:
        return None
    explication = str(q.get("explication") or "").strip()
    if fmt == "qcm":
        enonce = str(q.get("question") or "").strip()
        choix = [str(c).strip() for c in q.get("choix") or []]
        bonne = q.get("bonne_reponse")
        if not enonce or not 3 <= len(choix) <= 5 or len(set(choix)) != len(choix) or not all(choix):
            return None
        if not isinstance(bonne, int) or isinstance(bonne, bool) or not 0 <= bonne < len(choix):
            return None
        textes = [enonce, explication, *choix]
        item = {"question": enonce, "choix": choix, "bonne_reponse": bonne}
    elif fmt == "vrai_faux":
        enonce = str(q.get("affirmation") or "").strip()
        rep = q.get("reponse")
        if not enonce or not isinstance(rep, bool):
            return None
        textes = [enonce, explication]
        item = {"affirmation": enonce, "reponse": rep}
    else:
        enonce = str(q.get("question") or "").strip()
        attendus = [str(e).strip() for e in q.get("elements_attendus") or [] if str(e).strip()]
        if not enonce or not attendus:
            return None
        textes = [enonce, explication, *attendus]
        item = {"question": enonce, "elements_attendus": attendus}
    if not all(verifier_texte(t, passages, controle) for t in textes):
        return None
    return {**item, "explication": explication, "sources": sources}


def _version_publique(q: dict, index: int, fmt: str) -> dict:
    if fmt == "qcm":
        return {"index": index, "question": q["question"], "choix": q["choix"]}
    if fmt == "vrai_faux":
        return {"index": index, "affirmation": q["affirmation"]}
    return {"index": index, "question": q["question"]}


class QuizService:
    def __init__(self, lexia: Lexia, llm: LLM, store: QuizStore | None = None, journal: Journal | None = None):
        self.lexia, self.llm = lexia, llm
        self.store = store or QuizStore()
        self.journal = journal or Journal(None)

    def generer(self, theme: str, fmt: str, nombre: int, matiere: str | None) -> dict:
        debut = time.monotonic()
        passages, infos = self.lexia.rechercher(theme, matiere, K_QUIZ)
        recherche = infos["recherche"]
        table = table_extraits(passages)
        controle = Controle()
        questions: list[dict] = []
        modele = None
        if passages:
            brut, modele = self.llm.generate_json(
                system=prompts.SYSTEME_QUIZ,
                prompt=prompts.prompt_quiz(theme, fmt, nombre, passages),
                schema=prompts.SCHEMAS_QUIZ[fmt],
                temperature=0.5,
            )
            for q in brut.get("questions") or []:
                v = _valider_question(q, fmt, table, controle)
                if v is None:
                    controle.elements_retires += 1
                elif len(questions) < nombre:
                    questions.append(v)
        quiz = Quiz(id=str(uuid.uuid4()), format=fmt, theme=theme, questions=questions, table=table)
        if questions:
            self.store.ajouter(quiz)
        utilises = {pid for q in questions for pid in q["sources"]}
        labels = {p["id"]: lab for lab, p in table.items()}
        self.journal.ecrire(
            "requetes", route="quiz", quiz_id=quiz.id, format=fmt, matiere=matiere, demande=nombre,
            obtenu=len(questions), recherche=recherche, modele=modele, passages_cites=sorted(utilises),
            controle=controle.as_dict(), duree_ms=int((time.monotonic() - debut) * 1000),
        )
        return {
            "quiz_id": quiz.id if questions else None,
            "format": fmt,
            "theme": theme,
            "demande": nombre,
            "obtenu": len(questions),
            "questions": [_version_publique(q, i, fmt) for i, q in enumerate(questions)],
            "message": "" if questions else
                "Impossible de créer des questions vérifiables sur ce thème avec les sources disponibles.",
            "sources": [fiche_source(p, labels[p["id"]]) for p in passages if p["id"] in utilises],
            "avertissement": AVERTISSEMENT,
            "controle": {**controle.as_dict(), "recherche": recherche},
        }

    def corriger(self, quiz_id: str, reponses: list[dict]) -> dict | None:
        quiz = self.store.get(quiz_id)
        if quiz is None:
            return None
        donnees = {r["index"]: r.get("valeur") for r in reponses}
        resultats: list[dict] = []
        a_corriger: list[tuple[int, dict, str]] = []
        for i, q in enumerate(quiz.questions):
            valeur = donnees.get(i)
            res = {"index": i, "explication": q["explication"], "sources": q["sources"]}
            if quiz.format == "qcm":
                ok = isinstance(valeur, int) and not isinstance(valeur, bool) and valeur == q["bonne_reponse"]
                res.update(statut="non_repondu" if valeur is None else ("correct" if ok else "incorrect"),
                           bonne_reponse=q["bonne_reponse"])
            elif quiz.format == "vrai_faux":
                res.update(statut="non_repondu" if valeur is None else
                           ("correct" if valeur is q["reponse"] else "incorrect"), bonne_reponse=q["reponse"])
            else:
                res.update(elements_attendus=q["elements_attendus"])
                texte = str(valeur or "").strip()[:3000]
                if not texte:
                    res.update(statut="non_repondu")
                else:
                    a_corriger.append((i, q, texte))
            resultats.append(res)

        if a_corriger:
            self._corriger_ouvertes(quiz, a_corriger, resultats)

        notes = [r for r in resultats if r["statut"] in ("correct", "incorrect", "partiel")]
        score = sum(1 if r["statut"] == "correct" else 0.5 if r["statut"] == "partiel" else 0 for r in notes)
        labels = {p["id"]: lab for lab, p in quiz.table.items()}
        utilises = {pid for q in quiz.questions for pid in q["sources"]}
        self.journal.ecrire("requetes", route="quiz_correct", quiz_id=quiz.id, format=quiz.format,
                            score=score, total=len(quiz.questions))
        return {
            "quiz_id": quiz.id,
            "score": score,
            "total": len(quiz.questions),
            "resultats": resultats,
            "sources": [fiche_source(p, labels[p["id"]]) for p in quiz.table.values() if p["id"] in utilises],
        }

    def _corriger_ouvertes(self, quiz: Quiz, a_corriger, resultats) -> None:
        blocs = []
        for i, q, texte in a_corriger:
            labels = [lab for lab, p in quiz.table.items() if p["id"] in q["sources"]]
            blocs.append(
                f"<question index=\"{i}\">\n{q['question']}\nÉléments attendus : {' ; '.join(q['elements_attendus'])}\n"
                f"Extraits : {', '.join(labels)}\n<reponse_etudiant>\n{texte}\n</reponse_etudiant>\n</question>"
            )
        cites = {pid for _, q, _ in a_corriger for pid in q["sources"]}
        passages = [p for p in quiz.table.values() if p["id"] in cites]
        extraits = prompts.format_extraits(list(quiz.table.values()))
        try:
            brut, _ = self.llm.generate_json(
                system=prompts.SYSTEME_CORRECTION,
                prompt=f"<extraits>\n{extraits}\n</extraits>\n\n" + "\n\n".join(blocs),
                schema=prompts.SCHEMA_CORRECTION,
                temperature=0.1,
            )
            corrections = {c.get("index"): c for c in brut.get("corrections") or []}
        except LLMError:
            corrections = {}
        controle = Controle()
        for i, _, _ in a_corriger:
            c = corrections.get(i)
            res = resultats[i]
            if not c or c.get("evaluation") not in ("correct", "partiel", "incorrect"):
                res.update(statut="a_verifier", commentaire="Correction automatique indisponible : comparez votre "
                           "réponse aux éléments attendus.")
                continue
            commentaire = str(c.get("commentaire") or "").strip()
            if not verifier_texte(commentaire, passages or list(quiz.table.values()), controle):
                commentaire = "Comparez votre réponse aux éléments attendus et aux sources citées."
            res.update(statut=c["evaluation"], commentaire=commentaire,
                       elements_manquants=[str(e) for e in c.get("elements_manquants") or []])
