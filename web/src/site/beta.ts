// Beta fermee dans les pages prerendues (D132). Le HTML est compile sur le Mac, sans la configuration du serveur :
// beta-publiee.json donne la valeur du premier affichage (HTML prerendu, lu par les moteurs, puis repris par React).
// Une fois /api/config lue, la configuration du serveur fait foi. deploy/publier.sh refuse de publier si les deux
// different (beta_concorde dans deploy/garde_publication.sh) : a l'ouverture de la beta, passer la valeur a false.
import type { ConfigPublique } from '../lib/api'
import publiee from './beta-publiee.json'

export const BETA_FERMEE_PUBLIEE: boolean = publiee.beta_fermee

/** Beta fermee : configuration du serveur si elle est lue, valeur publiee sinon (prerendu, chargement, echec). */
export function betaFermee(config: ConfigPublique | null): boolean {
  return config ? Boolean(config.beta_fermee) : BETA_FERMEE_PUBLIEE
}
