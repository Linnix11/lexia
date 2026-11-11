import type { FicheSource, Mode } from './api'

export const MODES: { id: Mode; label: string }[] = [
  { id: 'expliquer', label: 'Expliquer' },
  { id: 'fiche', label: 'Fiche' },
  { id: 'cas_pratique', label: 'Cas pratique' },
  { id: 'commentaire', label: 'Commentaire d’arrêt' },
  { id: 'dissertation', label: 'Dissertation' },
]

const SYMBOLES: Record<string, string> = {
  constitution_1958: '◈',
  code_civil: '§',
  decisions_conseil_constitutionnel: '◈',
  judilibre: '⚖',
}

export function symbole(s: FicheSource) {
  return SYMBOLES[s.source_id] ?? '§'
}
