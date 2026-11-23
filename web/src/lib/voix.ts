// Lecture a voix haute par le navigateur (Web Speech API) : aucun son produit par le serveur (D106).

/** Phrases a lire une par une : surlignage de la phrase lue, et Chrome coupe les enonces trop longs. */
export function decouperPhrases(paragraphes: string[]): string[][] {
  // Coupe seulement sur une espace apres la ponctuation : « pourvoi 12-34.567 » reste entier.
  return paragraphes.map((p) =>
    p.split(/(?<=[.!?…][»”")]?)\s+/)
      .map((phrase) => phrase.trim())
      .filter(Boolean))
}

/** Voix francaises, fr-FR d'abord. Une voix en ligne (voix Google de Chrome...) envoie le texte lu a l'editeur du
 * navigateur : seules les voix de l'appareil sont proposees quand il y en a (recette du 2026-11-20, D-11). */
export function voixFrancaises(voix: SpeechSynthesisVoice[]): SpeechSynthesisVoice[] {
  const francaises = voix.filter((v) => v.lang.toLowerCase().startsWith('fr'))
  const locales = francaises.filter((v) => v.localService)
  const rang = (v: SpeechSynthesisVoice) => (v.lang.replace('_', '-').toLowerCase() === 'fr-fr' ? 0 : 1)
  return (locales.length ? locales : francaises).sort((a, b) => rang(a) - rang(b))
}

export const synthese = (): SpeechSynthesis | null =>
  typeof window !== 'undefined' && 'speechSynthesis' in window && typeof SpeechSynthesisUtterance !== 'undefined'
    ? window.speechSynthesis
    : null

/** « 3 min 20 » */
export function dureeLisible(secondes: number): string {
  const min = Math.floor(secondes / 60)
  const s = Math.round(secondes % 60)
  return min ? `${min} min${s ? ` ${String(s).padStart(2, '0')}` : ''}` : `${s} s`
}

// Un seul resume lu a la fois dans la page : en lancer un met l'autre en pause.
let actif: { id: object; pause: () => void } | null = null

export function prendreLaMain(id: object, pause: () => void) {
  if (actif && actif.id !== id) actif.pause()
  actif = { id, pause }
}

export function rendreLaMain(id: object) {
  if (actif?.id === id) actif = null
}
