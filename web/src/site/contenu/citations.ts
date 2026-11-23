// Articles cites par les pages publiques (matieres, guides). Texte, lien officiel et version lus dans l'index de
// recherche par `python -m api.donnees_publiques` (D116) : rien n'est recopie a la main.
import donnees from './citations.json'

export interface Citation {
  texte: string
  numero: string
  alineas: string[]
  url: string
  version: string
}

export const CITATIONS: Record<string, Citation> = donnees

/** « L411-1 » devient « L. 411-1 », comme dans les codes imprimes. */
export const numeroLisible = (n: string) => n.replace(/^([LRDA])(\d)/, '$1. $2')

/** « Code civil, art. 1101 ». */
export const libelleCitation = (c: Citation) => `${c.texte}, art. ${numeroLisible(c.numero)}`

export function citation(cle: string): Citation {
  const c = CITATIONS[cle]
  if (!c) throw new Error(`Citation inconnue : ${cle}`)
  return c
}

const MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
const dateLisible = (iso: string) => {
  const [a, m, j] = iso.split('-').map(Number)
  return `${j === 1 ? '1er' : j} ${MOIS[m - 1]} ${a}`
}

/** Version courte : « version depuis le 1er octobre 2016, article en vigueur (DILA, mise à jour du 16 novembre
 *  2026) ». La date de derniere mise a jour reste : la Licence Ouverte 2.0 la demande (audit du 2026-11-23, E8). */
export const versionCourte = (c: Citation) =>
  c.version
    .replace(/\s*\(archive DILA [^,()]*, mise à jour du (\d{4}-\d{2}-\d{2})\)$/, (_, d: string) => ` (DILA, mise à jour du ${dateLisible(d)})`)
    .replace(/\s*\(archive DILA[^()]*\)$/, ' (DILA)')
    .replace(/^Version /, 'version ')
