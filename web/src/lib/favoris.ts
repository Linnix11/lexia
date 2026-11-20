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
// L'adresse n'apparait plus dans le nom de la cle : sur un poste partage, l'etudiant suivant la lisait
// dans les outils du navigateur (audit du 2026-11-16, point 13). Empreinte FNV-1a : pas un secret,
// seulement une cle stable qui ne montre pas l'adresse.
export function empreinte(texte: string): string {
  let h = 0x811c9dc5
  for (let i = 0; i < texte.length; i++) {
    h ^= texte.charCodeAt(i)
    h = Math.imul(h, 0x01000193) >>> 0
  }
  return h.toString(36)
}
const cle = (compte: string) => `lexia.favoris.v2.${empreinte(compte.toLowerCase())}`

/** Suppression du compte : les fiches de ce compte quittent aussi ce navigateur. */
export function effacerFavoris(compte: string) {
  try {
    localStorage.removeItem(cle(compte))
  } catch {
    /* stockage indisponible : rien a effacer */
  }
}

/** Reprend une fois des fiches rangees sous une ancienne cle, puis efface celle-ci. */
function reprendre(ancienne: string, compte: string) {
  const valeur = localStorage.getItem(ancienne)
  if (valeur === null) return
  if (localStorage.getItem(cle(compte)) === null) localStorage.setItem(cle(compte), valeur)
  localStorage.removeItem(ancienne)
}

export function lireFavoris(compte: string): Favori[] {
  // Pas encore de compte (chargement) : ne rien reprendre sous une cle vide, les fiches d'avant y seraient perdues
  // (audit du 2026-11-19, WEB-12).
  if (!compte) return []
  try {
    // Fiches d'avant la separation par compte (reprises par le premier compte qui se connecte), puis
    // fiches rangees sous l'adresse en clair.
    reprendre(ANCIENNE_CLE, compte)
    reprendre(`${ANCIENNE_CLE}.${compte.toLowerCase()}`, compte)
    const brut = localStorage.getItem(cle(compte))
    const liste = brut ? (JSON.parse(brut) as Favori[]) : []
    return Array.isArray(liste) ? liste : []
  } catch {
    return []
  }
}

// Au-dela, l'ajout est refuse avec un message : la plus ancienne fiche disparaissait sans prevenir au
// rechargement (audit du 2026-11-18, D10).
export const MAX_FICHES = 100
export const MESSAGE_LIMITE_FICHES = `Limite de ${MAX_FICHES} fiches atteinte : exportez puis retirez des fiches pour en ajouter.`

export function ecrireFavoris(liste: Favori[], compte: string): boolean {
  try {
    localStorage.setItem(cle(compte), JSON.stringify(liste))
    return true
  } catch {
    return false // stockage indisponible (navigation privee, quota) : on n'interrompt rien
  }
}
