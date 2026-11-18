// Touches personnelles de l'espace etudiant (D100). Rien de nouveau n'est envoye au serveur : le prenom vient du
// profil, la derniere matiere choisie reste dans ce navigateur (une cle par compte, empreinte et non l'adresse).
import { empreinte } from './favoris'

export const PRENOM_MAX = 30

/** « Bonjour » de 5 h a 18 h, « Bonsoir » ensuite. Jamais l'adresse e-mail : sans prenom, la salutation seule. */
export function salutation(prenom: string | null | undefined, heure = new Date().getHours()): string {
  const mot = heure >= 5 && heure < 18 ? 'Bonjour' : 'Bonsoir'
  const p = prenom?.trim()
  return p ? `${mot}, ${p}.` : `${mot}.`
}

export function phraseQuestionsRestantes(restant: number, limite: number): string {
  if (restant <= 0) return `Vous avez utilisé vos ${limite} questions du jour : le compteur repart à minuit.`
  return restant === 1 ? 'Il vous reste 1 question aujourd’hui.' : `Il vous reste ${restant} questions aujourd’hui.`
}

const cle = (compte: string) => `lexia.matiere.v1.${empreinte(compte.toLowerCase())}`

export function lireDerniereMatiere(compte: string): string | null {
  if (!compte) return null
  try {
    return localStorage.getItem(cle(compte))
  } catch {
    return null
  }
}

export function ecrireDerniereMatiere(compte: string, matiere: string | null): void {
  if (!compte) return
  try {
    if (matiere) localStorage.setItem(cle(compte), matiere)
    else localStorage.removeItem(cle(compte))
  } catch {
    // stockage indisponible (navigation privee) : le choix vaut pour cette visite
  }
}

/** Suppression du compte : la derniere matiere quitte aussi ce navigateur. */
export const effacerDerniereMatiere = (compte: string) => ecrireDerniereMatiere(compte, null)

export const tronquer = (texte: string, max = 70) => (texte.length > max ? `${texte.slice(0, max - 1).trimEnd()}…` : texte)
