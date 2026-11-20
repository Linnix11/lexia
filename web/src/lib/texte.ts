/** Forme de comparaison pour la recherche : sans accents ni casse, « œ » et « æ » en deux lettres, apostrophes et
 *  guillemets typographiques ramenes a leur forme droite (audit du 2026-11-19, WEB-18 : « oeuvre » trouve
 *  « œuvre », « l'acte » trouve « l’acte »). */
export function normaliser(t: string): string {
  return t
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/œ/gi, 'oe')
    .replace(/æ/gi, 'ae')
    .replace(/[‘’ʼ´`]/g, "'")
    .replace(/[“”«»]/g, '"')
    .replace(/\s+/g, ' ')
    .toLowerCase()
}
