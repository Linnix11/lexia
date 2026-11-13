// Favoris enregistres dans le navigateur uniquement (aucune donnee envoyee au serveur en V1).
import type { Mode, ReponseChat } from './api'

export interface Favori {
  id: string
  question: string
  mode: Mode
  enregistre_le: string
  reponse: ReponseChat
}

const ANCIENNE_CLE = 'lexia.favoris.v1'
// Une cle par compte : sur un ordinateur partage (BU, salle de cours), l'etudiant suivant ne voit pas
// les fiches du precedent, meme si celui-ci a ferme l'onglet sans se deconnecter.
const cle = (compte: string) => `${ANCIENNE_CLE}.${compte.toLowerCase()}`

export function lireFavoris(compte: string): Favori[] {
  try {
    // Fiches enregistrees avant la separation par compte : reprises une fois par le premier compte qui se connecte.
    const ancienne = localStorage.getItem(ANCIENNE_CLE)
    if (ancienne !== null) {
      if (localStorage.getItem(cle(compte)) === null) localStorage.setItem(cle(compte), ancienne)
      localStorage.removeItem(ANCIENNE_CLE)
    }
    const brut = localStorage.getItem(cle(compte))
    const liste = brut ? (JSON.parse(brut) as Favori[]) : []
    return Array.isArray(liste) ? liste : []
  } catch {
    return []
  }
}

export function ecrireFavoris(liste: Favori[], compte: string): boolean {
  try {
    localStorage.setItem(cle(compte), JSON.stringify(liste.slice(0, 100)))
    return true
  } catch {
    return false // stockage indisponible (navigation privee, quota) : on n'interrompt rien
  }
}
