// Cartes mentales enregistrees (page « Mes cartes mentales »), dans ce navigateur seulement, comme les fiches
// (favoris.ts) : une cle par compte, sans l'adresse en clair. Rien n'est envoye au serveur.
import type { CarteMentale } from './api'
import { empreinte } from './favoris'

export interface CarteEnregistree {
  id: string
  titre: string
  enregistree_le: string
  carte: CarteMentale
}

export const MAX_CARTES = 50
export const MESSAGE_LIMITE_CARTES = `Limite de ${MAX_CARTES} cartes atteinte : retirez-en une pour en enregistrer une autre.`

const cle = (compte: string) => `lexia.cartes-mentales.v1.${empreinte(compte.toLowerCase())}`

export function lireCartesMentales(compte: string): CarteEnregistree[] {
  if (!compte) return []
  try {
    const brut = localStorage.getItem(cle(compte))
    const liste = brut ? (JSON.parse(brut) as CarteEnregistree[]) : []
    return Array.isArray(liste) ? liste : []
  } catch {
    return []
  }
}

function ecrire(liste: CarteEnregistree[], compte: string): boolean {
  try {
    localStorage.setItem(cle(compte), JSON.stringify(liste))
    return true
  } catch {
    return false // navigation privee, quota : on previent sans rien interrompre
  }
}

/** Meme carte (titre et branches identiques) : enregistree une seule fois. */
export function idCarte(carte: CarteMentale): string {
  return empreinte(JSON.stringify([carte.titre, carte.branches]))
}

export type ResultatEnregistrement = 'ok' | 'deja' | 'limite' | 'erreur'

export function enregistrerCarteMentale(carte: CarteMentale, compte: string): ResultatEnregistrement {
  if (!compte) return 'erreur'
  const liste = lireCartesMentales(compte)
  const id = idCarte(carte)
  if (liste.some((c) => c.id === id)) return 'deja'
  if (liste.length >= MAX_CARTES) return 'limite'
  // Le quota du jour et le drapeau « partiel » ne valent qu'au moment de la creation
  const gardee: CarteMentale = { ...carte, restants: 0, partiel: false }
  const nouvelle: CarteEnregistree = { id, titre: carte.titre, enregistree_le: new Date().toISOString(), carte: gardee }
  return ecrire([nouvelle, ...liste], compte) ? 'ok' : 'erreur'
}

export function retirerCarteMentale(id: string, compte: string): CarteEnregistree[] {
  const liste = lireCartesMentales(compte).filter((c) => c.id !== id)
  ecrire(liste, compte)
  return liste
}

/** Suppression du compte : ses cartes quittent aussi ce navigateur. */
export function effacerCartesMentales(compte: string) {
  try {
    localStorage.removeItem(cle(compte))
  } catch {
    /* stockage indisponible : rien a effacer */
  }
}
