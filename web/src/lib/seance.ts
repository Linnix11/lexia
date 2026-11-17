// Seance du navigateur : la conversation de l'assistant et le dernier questionnaire survivent aux changements
// de page et au rechargement, tant que l'onglet reste ouvert (sessionStorage). Rien n'est envoye au serveur.
// Une cle par compte (empreinte, pas l'adresse) ; la deconnexion efface tout (poste partage).
import { empreinte } from './favoris'

const PREFIXE = 'lexia.seance.v1.'
const cle = (nom: string, compte: string) => `${PREFIXE}${nom}.${empreinte(compte.toLowerCase())}`

export function lireSeance<T>(nom: string, compte: string): T | null {
  try {
    const brut = sessionStorage.getItem(cle(nom, compte))
    return brut ? (JSON.parse(brut) as T) : null
  } catch {
    return null
  }
}

export function ecrireSeance(nom: string, compte: string, valeur: unknown): void {
  try {
    if (valeur === null) sessionStorage.removeItem(cle(nom, compte))
    else sessionStorage.setItem(cle(nom, compte), JSON.stringify(valeur))
  } catch {
    // stockage plein ou indisponible : la seance reste en memoire tant que la page est ouverte
  }
}

export function oublierSeance(): void {
  try {
    Object.keys(sessionStorage).filter((k) => k.startsWith(PREFIXE)).forEach((k) => sessionStorage.removeItem(k))
  } catch {
    // rien a effacer
  }
}
