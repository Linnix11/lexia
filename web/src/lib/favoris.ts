// Favoris enregistres dans le navigateur uniquement (aucune donnee envoyee au serveur en V1).
import type { Mode, ReponseChat } from './api'

export interface Favori {
  id: string
  question: string
  mode: Mode
  enregistre_le: string
  reponse: ReponseChat
}

const CLE = 'lexia.favoris.v1'

export function lireFavoris(): Favori[] {
  try {
    const brut = localStorage.getItem(CLE)
    const liste = brut ? (JSON.parse(brut) as Favori[]) : []
    return Array.isArray(liste) ? liste : []
  } catch {
    return []
  }
}

export function ecrireFavoris(liste: Favori[]): boolean {
  try {
    localStorage.setItem(CLE, JSON.stringify(liste.slice(0, 100)))
    return true
  } catch {
    return false // stockage indisponible (navigation privee, quota) : on n'interrompt rien
  }
}
