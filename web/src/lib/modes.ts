import type { FicheSource, Mode } from './api'

export interface InfosMode {
  id: Mode
  label: string
  description: string
  placeholder: string
  /** Titres des trois blocs de la reponse (droit_positif, explication, points_incertains). */
  blocs: [string, string, string]
}

export const MODES: InfosMode[] = [
  { id: 'expliquer', label: 'Expliquer', description: 'Définition, règle, conditions, exceptions et un exemple simple.',
    placeholder: 'Quelle notion voulez-vous comprendre ?', blocs: ['Droit positif', 'Explication', 'Points d’attention'] },
  { id: 'fiche', label: 'Fiche', description: 'Fiche de révision, enregistrée automatiquement dans « Fiches & révisions ».',
    placeholder: 'Sur quelle notion voulez-vous une fiche ?', blocs: ['Règles essentielles', 'À retenir', 'Pièges fréquents'] },
  { id: 'cas_pratique', label: 'Cas pratique', description: 'Qualification des faits, problème de droit, majeure, mineure, conclusion.',
    placeholder: 'Décrivez les faits du cas pratique…', blocs: ['Règles applicables', 'Raisonnement', 'Points à vérifier'] },
  { id: 'commentaire', label: 'Commentaire d’arrêt', description: 'Fiche d’arrêt, sens, valeur et portée, problématique et plan.',
    placeholder: 'Quel arrêt voulez-vous commenter ? (juridiction, date, numéro)', blocs: ['Règles en cause', 'Analyse et plan', 'Points à vérifier'] },
  { id: 'dissertation', label: 'Dissertation', description: 'Définitions, problématique, plan en deux parties et sources mobilisables.',
    placeholder: 'Quel est le sujet de la dissertation ?', blocs: ['Règles mobilisables', 'Problématique et plan', 'Points à vérifier'] },
]

export const infosMode = (id: Mode): InfosMode => MODES.find((m) => m.id === id) ?? MODES[0]

const SYMBOLES: Record<string, string> = {
  constitution_1958: '◈',
  code_civil: '§',
  decisions_conseil_constitutionnel: '◈',
  judilibre: '⚖',
  cass_criminelle: '⚖',
  cass_sociale: '⚖',
  cass_commerciale: '⚖',
  conseil_etat: '⚖',
}

export function symbole(s: FicheSource) {
  return SYMBOLES[s.source_id] ?? '§'
}
