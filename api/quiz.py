"""Questionnaires : generation a partir du corpus, validation, stockage temporaire et correction.

Les questions sont gardees en memoire et en base (TTL) avec leurs reponses : le client ne recoit jamais
les bonnes reponses avant la correction. En base, 3 heures au plus : le theme saisi, les questions, le numero du
compte qui l'a cree et la correction (sans le texte des reponses de l'etudiant).
"""

from __future__ import annotations

import json
import random
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from api import prompts
from api.citations import _LABELS_DANS_TEXTE, Controle, labels_valides, retirer_reperes, verifier_texte
from api.concordance import annoter, numeros_actuels
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
    # Correction des questions ouvertes deja faite par le modele : renvoyee telle quelle ensuite,
    # pour qu'un meme questionnaire ne declenche qu'un seul appel payant.
    correction: dict | None = None
    # Compte qui l'a cree (None : visiteur) : seul lui peut le faire corriger. La correction renvoie les
    # extraits, y compris d'un cours personnel (audit du 2026-11-16, point 12).
    proprietaire: int | None = None
    # Une correction a la fois par questionnaire : plusieurs /quiz/correct simultanes lancaient chacun un
    # appel au modele, hors quota (second audit du 2026-11-16, point 12). Le second recoit la correction du premier.
    verrou: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)


class QuizStore:
    """Questionnaires en memoire (avec leur verrou), recopies en base si `chemin` est donne : un redemarrage du
    service (publication) ne perd plus les questionnaires en cours (audit du 2026-11-18, D5)."""

    def __init__(self, ttl: int = TTL_SECONDES, maximum: int = MAX_QUIZ, chemin: Path | None = None):
        self._ttl, self._max = ttl, maximum
        self._items: dict[str, Quiz] = {}
        self._lock = threading.Lock()
        self._con = None
        if chemin is not None:
            self._con = sqlite3.connect(str(chemin), check_same_thread=False)
            # Questionnaires purges vraiment effaces du fichier, comme les comptes et les cours (SEC-10)
            self._con.execute("PRAGMA secure_delete = ON")
            self._con.execute("CREATE TABLE IF NOT EXISTS questionnaires "
                              "(id TEXT PRIMARY KEY, cree REAL NOT NULL, donnees TEXT NOT NULL)")
            self._con.commit()

    def ajouter(self, quiz: Quiz) -> None:
        with self._lock:
            self._purger()
            if len(self._items) >= self._max:
                plus_ancien = min(self._items.values(), key=lambda q: q.cree)
                del self._items[plus_ancien.id]
            self._items[quiz.id] = quiz
            self._ecrire(quiz)

    def enregistrer(self, quiz: Quiz) -> None:
        """Recopie en base un questionnaire modifie (correction faite)."""
        with self._lock:
            self._ecrire(quiz)

    def get(self, quiz_id: str) -> Quiz | None:
        with self._lock:
            self._purger()
            quiz = self._items.get(quiz_id)
            if quiz is None and self._con is not None:
                ligne = self._con.execute("SELECT donnees FROM questionnaires WHERE id = ?", (quiz_id,)).fetchone()
                if ligne:
                    quiz = self._items[quiz_id] = Quiz(**json.loads(ligne[0]))
            return quiz

    def _ecrire(self, quiz: Quiz) -> None:
        if self._con is None:
            return
        donnees = {k: getattr(quiz, k) for k in ("id", "format", "theme", "questions", "table", "cree",
                                                  "correction", "proprietaire")}
        self._con.execute("INSERT OR REPLACE INTO questionnaires (id, cree, donnees) VALUES (?, ?, ?)",
                          (quiz.id, quiz.cree, json.dumps(donnees, ensure_ascii=False)))
        self._con.commit()

    def _purger(self) -> None:
        limite = time.time() - self._ttl
        for k in [k for k, q in self._items.items() if q.cree < limite]:
            del self._items[k]
        if self._con is not None:
            self._con.execute("DELETE FROM questionnaires WHERE cree < ?", (limite,))
            self._con.commit()


def _valider_question(q: dict, fmt: str, table: dict[str, dict], controle: Controle) -> dict | None:
    if not isinstance(q, dict):   # forme deja controlee dans api/llm/forme.py ; filet si un appelant l'oublie
        return None
    passages = list(table.values())
    sources = labels_valides(q.get("sources"), table, controle)
    if not sources:
        return None
    def net(t) -> str:
        # Reperes « S8 », « (S1, S2) » ecrits dans le texte : sans sens pour l'etudiant, retires comme dans les
        # reponses (D136, R10) ; le 26/11, des corriges disaient « l'extrait S8 precise... » (D140)
        return retirer_reperes(_LABELS_DANS_TEXTE.sub("", str(t or "").strip()), table)

    explication = net(q.get("explication"))
    if fmt == "qcm":
        enonce = net(q.get("question"))
        choix = [net(c) for c in q.get("choix") or []]
        bonne = q.get("bonne_reponse")
        if not enonce or not 3 <= len(choix) <= 5 or len(set(choix)) != len(choix) or not all(choix):
            return None
        if not isinstance(bonne, int) or isinstance(bonne, bool) or not 0 <= bonne < len(choix):
            return None
        textes = [enonce, explication, *choix]
        item = {"question": enonce, "choix": choix, "bonne_reponse": bonne}
        # Pourquoi chaque choix est juste ou faux (D140) : facultatif, la question reste sans lui (modele de
        # secours, liste de mauvaise longueur, phrase non verifiable)
        justifs = q.get("justifications")
        if isinstance(justifs, list) and len(justifs) == len(choix):
            justifs = [net(j) for j in justifs]
            if all(justifs) and all(verifier_texte(j, passages, Controle()) for j in justifs):
                item["justifications"] = justifs
    elif fmt == "vrai_faux":
        enonce = net(q.get("affirmation"))
        rep = q.get("reponse")
        if not enonce or not isinstance(rep, bool):
            return None
        textes = [enonce, explication]
        item = {"affirmation": enonce, "reponse": rep}
    else:
        enonce = net(q.get("question"))
        attendus = [e for e in (net(x) for x in q.get("elements_attendus") or []) if e]
        if not enonce or not attendus:
            return None
        textes = [enonce, explication, *attendus]
        item = {"question": enonce, "elements_attendus": attendus}
    if not all(verifier_texte(t, passages, controle) for t in textes):
        return None
    return {**item, "explication": explication, "sources": sources}


def _melanger(q: dict, hasard: random.Random, place: int | None = None) -> dict:
    """Choix du QCM dans un ordre tire au hasard, justifications comprises ; la bonne reponse a la `place` donnee
    (modulo le nombre de choix) si elle l'est. Le 26/11, 9 bonnes reponses sur 10 etaient le choix B : l'etudiant
    apprenait la place de la reponse, pas le droit (D140)."""
    if "choix" not in q:
        return q
    ordre = [i for i in range(len(q["choix"])) if i != q["bonne_reponse"]]
    hasard.shuffle(ordre)
    ordre.insert(hasard.randrange(len(q["choix"])) if place is None else place % len(q["choix"]), q["bonne_reponse"])
    out = {**q, "choix": [q["choix"][i] for i in ordre], "bonne_reponse": ordre.index(q["bonne_reponse"])}
    if "justifications" in q:
        out["justifications"] = [q["justifications"][i] for i in ordre]
    return out


_CHAMPS_TEXTE = ("question", "affirmation", "explication")
_CHAMPS_LISTE = ("choix", "justifications", "elements_attendus")


def _signaler_anciens(q: dict, par_id: dict[str, dict]) -> dict:
    """« article 1382 du Code civil » donne pour le droit actuel : ancienne numerotation signalee, comme dans les
    reponses (D136), d'apres les extraits que la question cite. Apres la verification des references : la mention
    ajoute le numero actuel, qui peut manquer aux extraits (D140)."""
    actuels = numeros_actuels([par_id[i] for i in q["sources"] if i in par_id])
    out = dict(q)
    for champ in _CHAMPS_TEXTE:
        if isinstance(out.get(champ), str):
            out[champ] = annoter(out[champ], actuels)
    for champ in _CHAMPS_LISTE:
        if isinstance(out.get(champ), list):
            out[champ] = [annoter(t, actuels) for t in out[champ]]
    return out


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
        self.hasard = random.Random()  # ordre des choix du QCM (les tests en fixent la graine)

    def generer(self, theme: str, fmt: str, nombre: int, matiere: str | None, niveau: str | None = None,
                semestre: int | None = None, cours_ids: list[int] | None = None, avec_officiel: bool = True,
                uid: int | None = None) -> dict:
        debut = time.monotonic()
        avec_cours = bool(cours_ids) and self.lexia.cours is not None and uid is not None
        option_cours = ("avec_officiel" if avec_officiel else "seul") if avec_cours else None
        passages, infos = self.lexia.extraits(theme, matiere, K_QUIZ, cours_ids, avec_officiel, uid)
        recherche = infos["recherche"]
        table = table_extraits(passages)
        controle = Controle()
        questions: list[dict] = []
        modele = None
        if passages:
            brut, modele, passages = self.lexia.generer(
                system=prompts.SYSTEME_QUIZ,
                construire=lambda ps: prompts.prompt_quiz(theme, fmt, nombre, ps, niveau, semestre, option_cours,
                                                          infos.get("concordance")),
                passages=passages,
                schema=prompts.SCHEMAS_QUIZ[fmt],
                temperature=0.5,
            )
            table = table_extraits(passages)
            par_id = {p["id"]: p for p in passages}
            places: list[int] = []   # bonnes reponses reparties entre A, B, C et D, dans un ordre tire au hasard
            for q in brut.get("questions") or []:
                v = _valider_question(q, fmt, table, controle)
                if v is None:
                    controle.elements_retires += 1
                elif len(questions) < nombre:
                    if not places:
                        places = self.hasard.sample(range(4), 4)
                    questions.append(_signaler_anciens(_melanger(v, self.hasard, places.pop()), par_id))
        quiz = Quiz(id=str(uuid.uuid4()), format=fmt, theme=theme, questions=questions, table=table,
                    proprietaire=uid)
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
            "controle": {**controle.as_dict(), "recherche": recherche, "modele_appele": modele is not None},
        }

    def corriger(self, quiz_id: str, reponses: list[dict], uid: int | None = None) -> dict | None:
        quiz = self.store.get(quiz_id)
        if quiz is None or quiz.proprietaire != uid:
            return None
        with quiz.verrou:
            if quiz.correction is not None:
                return quiz.correction
            return self._corriger(quiz, reponses)

    def _corriger(self, quiz: Quiz, reponses: list[dict]) -> dict:
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
                if q.get("justifications"):   # pourquoi chaque choix est juste ou faux (D140)
                    res["justifications"] = q["justifications"]
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

        modele_appele = bool(a_corriger) and self._corriger_ouvertes(quiz, a_corriger, resultats)

        notes = [r for r in resultats if r["statut"] in ("correct", "incorrect", "partiel")]
        score = sum(1 if r["statut"] == "correct" else 0.5 if r["statut"] == "partiel" else 0 for r in notes)
        labels = {p["id"]: lab for lab, p in quiz.table.items()}
        utilises = {pid for q in quiz.questions for pid in q["sources"]}
        self.journal.ecrire("requetes", route="quiz_correct", quiz_id=quiz.id, format=quiz.format,
                            score=score, total=len(quiz.questions))
        res = {
            "quiz_id": quiz.id,
            "score": score,
            "total": len(quiz.questions),
            "resultats": resultats,
            "sources": [fiche_source(p, labels[p["id"]]) for p in quiz.table.values() if p["id"] in utilises],
        }
        if modele_appele:
            quiz.correction = res
            self.store.enregistrer(quiz)
        return res

    def _corriger_ouvertes(self, quiz: Quiz, a_corriger, resultats) -> bool:
        """Corrige par le modele ; renvoie False si le modele n'a pas repondu (nouvel essai permis)."""
        cites = {pid for _, q, _ in a_corriger for pid in q["sources"]}
        passages = [p for p in quiz.table.values() if p["id"] in cites]
        # Extraits cites en tete : le secours n'en recoit que les premiers (pour_secours).
        ordre = passages + [p for p in quiz.table.values() if p["id"] not in cites]

        def construire(ps: list[dict]) -> str:
            labels = {p["id"]: f"S{n}" for n, p in enumerate(ps, start=1)}
            blocs = [
                f"<question index=\"{i}\">\n{q['question']}\nÉléments attendus : {' ; '.join(q['elements_attendus'])}\n"
                f"Extraits : {', '.join(labels[pid] for pid in q['sources'] if pid in labels)}\n"
                f"<reponse_etudiant>\n{texte}\n</reponse_etudiant>\n</question>"
                for i, q, texte in a_corriger
            ]
            return f"<extraits>\n{prompts.format_extraits(ps)}\n</extraits>\n\n" + "\n\n".join(blocs)

        # Par lexia.generer : secours Groq et disjoncteur, comme les autres appels (audit du 2026-11-18, D1).
        try:
            brut, _, _ = self.lexia.generer(system=prompts.SYSTEME_CORRECTION, construire=construire, passages=ordre,
                                            schema=prompts.SCHEMA_CORRECTION, temperature=0.1)
            corrections = {c.get("index"): c for c in brut.get("corrections") or []}
            appele = True
        except LLMError:
            corrections, appele = {}, False
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
        return appele
