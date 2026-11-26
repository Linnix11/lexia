// Semestres de licence : S1-S2 en L1, S3-S4 en L2, S5-S6 en L3. Le choix est garde dans ce navigateur, une cle
// par compte (empreinte, pas l'adresse) : sur un poste partage, l'etudiant suivant ne recoit pas le semestre du
// precedent (audit du 2026-11-19, WEB-16).
import type { Niveau } from './api'
import { empreinte } from './favoris'

export type Semestre = 1 | 2 | 3 | 4 | 5 | 6

export const SEMESTRES: Semestre[] = [1, 2, 3, 4, 5, 6]

export const niveauDe = (s: Semestre): Niveau => (s <= 2 ? 'L1' : s <= 4 ? 'L2' : 'L3')

export const libelleSemestre = (s: Semestre) => `${niveauDe(s)} · Semestre ${s}`

const ANCIENNE_CLE = 'lexia.semestre.v1'
const cle = (compte: string) => `lexia.semestre.v2.${empreinte(compte.toLowerCase())}`

export function lireSemestre(compte: string): Semestre {
  try {
    if (!compte) return 1
    // Ancienne cle commune : reprise une fois par le premier compte qui se connecte, puis effacee.
    const ancienne = localStorage.getItem(ANCIENNE_CLE)
    if (ancienne !== null) {
      if (localStorage.getItem(cle(compte)) === null) localStorage.setItem(cle(compte), ancienne)
      localStorage.removeItem(ANCIENNE_CLE)
    }
    const s = Number(localStorage.getItem(cle(compte)))
    return (SEMESTRES as number[]).includes(s) ? (s as Semestre) : 1
  } catch {
    return 1
  }
}

/** Vrai quand l'etudiant a deja choisi son semestre dans ce navigateur ; sinon l'espace le lui demande a la
 * premiere ouverture, au lieu de le laisser en L1 sans le dire (audit du 2026-11-25, G-2). A appeler apres
 * lireSemestre, qui reprend l'ancienne cle commune. */
export function semestreEnregistre(compte: string): boolean {
  try {
    return !!compte && (SEMESTRES as number[]).includes(Number(localStorage.getItem(cle(compte))))
  } catch {
    return false
  }
}

export function ecrireSemestre(s: Semestre, compte: string): void {
  if (!compte) return
  try {
    localStorage.setItem(cle(compte), String(s))
  } catch {
    // stockage indisponible (navigation privee) : le choix vaut pour cette visite
  }
}

/** Suppression du compte : le semestre quitte aussi ce navigateur. */
export function effacerSemestre(compte: string): void {
  try {
    localStorage.removeItem(cle(compte))
  } catch {
    /* stockage indisponible : rien a effacer */
  }
}
