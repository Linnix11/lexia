// Titres et descriptions des guides publics (D116) : module leger, lu par le routeur du site sans charger
// le contenu des guides (guides.ts).

export interface GuideListe {
  slug: string
  titre: string
  /** Meta description (150 a 160 signes environ). */
  description: string
  niveau: string
  /** Matieres concernees (identifiants de api/matieres.py). */
  matieres: string[]
  publie: string
}

export const GUIDES_LISTE: GuideListe[] = [
  {
    slug: 'methode-cas-pratique-droit-des-contrats',
    titre: 'Méthode du cas pratique en droit des contrats',
    description: 'Résoudre un cas pratique en droit des contrats : qualification, problème de droit, majeure, mineure, conclusion, avec les articles du Code civil en vigueur.',
    niveau: 'L2',
    matieres: ['droit_des_contrats', 'droit_civil'],
    publie: '2026-11-23',
  },
  {
    slug: 'methode-commentaire-arret',
    titre: 'Méthode du commentaire d’arrêt',
    description: 'Commenter un arrêt de la Cour de cassation : lire l’arrêt, rédiger la fiche d’arrêt, dégager le sens, la valeur et la portée, construire le plan.',
    niveau: 'L1 et L2',
    matieres: ['introduction_au_droit', 'droit_civil', 'droit_des_contrats', 'procedure_civile'],
    publie: '2026-11-23',
  },
  {
    slug: 'fiche-responsabilite-civile-pour-faute',
    titre: 'Fiche : la responsabilité civile pour faute (articles 1240 et 1241 du Code civil)',
    description: 'Fiche de révision sur la responsabilité civile pour faute : faute, dommage, lien de causalité, articles 1240 à 1242 du Code civil et anciens numéros.',
    niveau: 'L1 et L2',
    matieres: ['droit_civil', 'droit_des_contrats'],
    publie: '2026-11-23',
  },
  {
    slug: 'fiche-question-prioritaire-de-constitutionnalite',
    titre: 'Fiche : la question prioritaire de constitutionnalité (QPC)',
    description: 'Fiche de révision sur la QPC : article 61-1 de la Constitution, conditions de transmission, filtre du Conseil d’État et de la Cour de cassation, effets de la décision.',
    niveau: 'L1',
    matieres: ['droit_constitutionnel', 'libertes_fondamentales'],
    publie: '2026-11-23',
  },
  {
    slug: 'methode-cas-pratique-droit-penal',
    titre: 'Méthode du cas pratique en droit pénal',
    description: 'Résoudre un cas pratique en droit pénal : élément légal, élément matériel, élément moral, causes d’irresponsabilité comme la légitime défense, avec les articles du Code pénal.',
    niveau: 'L2',
    matieres: ['droit_penal', 'procedure_penale'],
    publie: '2026-11-23',
  },
]
