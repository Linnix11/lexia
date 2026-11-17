// Affichage des sources citees (audit du 2026-11-16, points 3 et 4).
import type { FicheSource } from './api'

/** Numero d'affichage continu (1, 2, 3...) dans l'ordre de la liste des sources de la reponse :
 * le serveur numerote S1, S2, S4 quand un passage est ecarte, ce qui laissait des trous. */
export function numeroSource(sources: FicheSource[], id: string): number {
  return sources.findIndex((s) => s.id === id) + 1
}

/** « Code civil, Livre III : ..., Titre III : ..., article 1231-1 » devient « Code civil · article 1231-1 ».
 * Les autres intitules (decisions, preambules) restent entiers. */
export function titreCourt(entete: string): string {
  const parties = entete.split(', ')
  const fin = parties.at(-1) ?? ''
  if (parties.length < 3 || !/^article\s/i.test(fin)) return entete
  return `${parties[0]} · ${fin}`
}
