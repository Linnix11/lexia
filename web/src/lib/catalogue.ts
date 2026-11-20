// Catalogue des cours recuperes (fiches de service-public.gouv.fr) : plus d'un millier d'entrees, charge une seule
// fois par page et partage entre la page des fiches et la recherche de la Bibliotheque (audit du 2026-11-19, WEB-13).
import { api, type CoursRecupere } from './api'

let chargement: Promise<{ avertissement: string; cours: CoursRecupere[] }> | null = null

/** Un echec n'est pas garde : l'appel suivant reessaie. */
export function chargerCatalogue() {
  chargement ??= api.coursRecuperes.lister().catch((e: unknown) => {
    chargement = null
    throw e
  })
  return chargement
}

export function oublierCatalogue() {
  chargement = null
}
