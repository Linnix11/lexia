"""Formules d'abonnement : un seul endroit pour les limites et les prix."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Formule:
    id: str
    nom: str
    prix_mensuel_euros: float
    questions_par_jour: int
    quiz_par_jour: int
    cours_max: int  # cours deposes conserves dans le compte
    description: str
    avantages: tuple[str, ...]

    def as_dict(self) -> dict:
        d = asdict(self)
        d["avantages"] = list(self.avantages)
        return d


FORMULES: dict[str, Formule] = {
    "gratuit": Formule(
        id="gratuit",
        nom="Gratuit",
        prix_mensuel_euros=0,
        questions_par_jour=10,
        quiz_par_jour=2,
        cours_max=3,
        description="Pour découvrir Lexia : il suffit de créer un compte.",
        avantages=("10 questions par jour", "2 questionnaires par jour", "3 cours déposés", "Tous les modes : explication, fiche, méthode",
                   "Sources officielles citées et vérifiables"),
    ),
    "etudiant": Formule(
        id="etudiant",
        nom="Étudiant",
        prix_mensuel_euros=4.99,
        questions_par_jour=100,
        quiz_par_jour=20,
        cours_max=30,
        description="Pour réviser régulièrement pendant le semestre.",
        avantages=("100 questions par jour", "20 questionnaires par jour", "30 cours déposés", "Tous les modes et toutes les matières"),
    ),
    "intensif": Formule(
        id="intensif",
        nom="Intensif",
        prix_mensuel_euros=9.99,
        questions_par_jour=300,
        quiz_par_jour=100,
        cours_max=100,
        description="Pour les périodes de partiels et de concours.",
        avantages=("300 questions par jour", "Questionnaires en usage intensif (100 par jour)", "100 cours déposés",
                   "Tous les modes et toutes les matières"),
    ),
}

FORMULE_PAR_DEFAUT = "gratuit"


def formule(id_formule: str | None) -> Formule:
    return FORMULES.get(id_formule or FORMULE_PAR_DEFAUT, FORMULES[FORMULE_PAR_DEFAUT])
