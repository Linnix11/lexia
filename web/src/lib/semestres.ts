// Semestres de licence : S1-S2 en L1, S3-S4 en L2, S5-S6 en L3. Le choix est garde dans ce navigateur.
import type { Niveau } from './api'

export type Semestre = 1 | 2 | 3 | 4 | 5 | 6

export const SEMESTRES: Semestre[] = [1, 2, 3, 4, 5, 6]

export const niveauDe = (s: Semestre): Niveau => (s <= 2 ? 'L1' : s <= 4 ? 'L2' : 'L3')

export const libelleSemestre = (s: Semestre) => `${niveauDe(s)} · Semestre ${s}`

const CLE = 'lexia.semestre.v1'

export function lireSemestre(): Semestre {
  try {
    const s = Number(localStorage.getItem(CLE))
    return (SEMESTRES as number[]).includes(s) ? (s as Semestre) : 1
  } catch {
    return 1
  }
}

export function ecrireSemestre(s: Semestre): void {
  try {
    localStorage.setItem(CLE, String(s))
  } catch {
    // stockage indisponible (navigation privee) : le choix vaut pour cette visite
  }
}
