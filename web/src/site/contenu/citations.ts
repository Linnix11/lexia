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

/** Version courte : « en vigueur depuis le 1er octobre 2016 », sans la mention de l'archive DILA. */
export const versionCourte = (c: Citation) =>
  c.version.replace(/\s*\(archive DILA.*\)$/, '').replace(/^Version /, 'version ')
