// Matieres classees par annee de licence (d'apres les maquettes des facultes, D97) et recherche par mot.
import type { Matiere } from './api'

export const ANNEES = ['L1', 'L2', 'L3'] as const
export type Annee = (typeof ANNEES)[number]

export const LIBELLES_ANNEES: Record<Annee, string> = { L1: 'Licence 1', L2: 'Licence 2', L3: 'Licence 3' }

// Minuscules, sans accents, apostrophes et tirets en espaces : « Procédure pénale » = « procedure penale ».
export const normaliser = (s: string) =>
  s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[’'-]/g, ' ')

const texteDe = (m: Matiere) =>
  normaliser([m.libelle, ...(m.mots ?? []), ...Object.values(m.noms_sources ?? {}), ...m.sources].join(' '))

// Tous les mots de la recherche doivent se trouver dans l'intitule, les autres intitules ou les sources.
export function filtrerMatieres(matieres: Matiere[], recherche: string): Matiere[] {
  const mots = normaliser(recherche).split(/\s+/).filter((m) => m.length > 1)
  if (mots.length === 0) return matieres
  return matieres.filter((m) => {
    const t = texteDe(m)
    return mots.every((mot) => t.includes(mot))
  })
}

export interface GroupeMatieres {
  annee: Annee | null
  titre: string
  matieres: Matiere[]
}

// Groupes L1, L2, L3 dans cet ordre (vides omis) ; une matiere sans annee connue va dans « Autres matières ».
export function grouperParAnnee(matieres: Matiere[]): GroupeMatieres[] {
  const groupes: GroupeMatieres[] = ANNEES.map((a) => ({
    annee: a, titre: LIBELLES_ANNEES[a], matieres: matieres.filter((m) => m.annee === a),
  }))
  const autres = matieres.filter((m) => !ANNEES.includes(m.annee as Annee))
  groupes.push({ annee: null, titre: 'Autres matières', matieres: autres })
  return groupes.filter((g) => g.matieres.length > 0)
}

// Noms des sources principales de la matiere (les premieres sources si l'API n'en designe pas).
export function sourcesPrincipales(m: Matiere): string[] {
  const ids = m.principales?.length ? m.principales : m.sources.slice(0, 2)
  return ids.map((s) => m.noms_sources?.[s] ?? s)
}
