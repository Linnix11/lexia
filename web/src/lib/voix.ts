// Lecture a voix haute par le navigateur (Web Speech API) : aucun son produit par le serveur (D106).
import type { DemandeResume, ResumeVocal } from './api'
import { empreinte } from './favoris'
import { ecrireSeance, lireSeance } from './seance'

// Resumes deja prepares, gardes dans l'onglet pour le compte (sessionStorage, efface a la deconnexion) avec la
// phrase ou l'etudiant s'est arrete : rouvrir un resume ne coute plus un des 5 du jour et la lecture reprend la
// ou elle s'etait arretee, apres un changement de page ou un rechargement (D141).
const SEANCE_RESUMES = 'resumes-vocaux'
const MAX_RESUMES_GARDES = 10
export interface ResumeGarde { cle: string; resume: ResumeVocal; position: number }

export const cleResume = (d: DemandeResume) =>
  d.type === 'reponse' ? `reponse:${empreinte(`${d.titre}\n${d.texte}`)}` : `${d.type}:${d.id}`

export function lireResumeGarde(compte: string, cle: string): ResumeGarde | null {
  if (!compte) return null
  const liste = lireSeance<ResumeGarde[]>(SEANCE_RESUMES, compte)
  return (Array.isArray(liste) && liste.find((g) => g.cle === cle && Array.isArray(g.resume?.paragraphes))) || null
}

export function garderResume(compte: string, garde: ResumeGarde) {
  if (!compte || !garde.resume.paragraphes.length) return
  const liste = lireSeance<ResumeGarde[]>(SEANCE_RESUMES, compte)
  const autres = (Array.isArray(liste) ? liste : []).filter((g) => g.cle !== garde.cle)
  ecrireSeance(SEANCE_RESUMES, compte, [garde, ...autres].slice(0, MAX_RESUMES_GARDES))
}

/** Phrases a lire une par une : surlignage de la phrase lue, et Chrome coupe les enonces trop longs. */
export function decouperPhrases(paragraphes: string[]): string[][] {
  // Coupe seulement sur une espace apres la ponctuation : « pourvoi 12-34.567 » reste entier.
  return paragraphes.map((p) =>
    p.split(/(?<=[.!?…][»”")]?)\s+/)
      .map((phrase) => phrase.trim())
      .filter(Boolean))
}

// Voix fantaisie de macOS (Eloquence et voix « novelty ») : proposees en francais de France et du Canada, elles
// remplissaient la liste (recette du 2026-11-23, R-6). Safari les reconnait a leur voiceURI, Chrome a leur nom.
const FANTAISIE = new Set(['eddy', 'flo', 'grandma', 'grandpa', 'reed', 'rocko', 'sandy', 'shelley', 'albert',
  'bad news', 'bahh', 'bells', 'boing', 'bubbles', 'cellos', 'fred', 'good news', 'jester', 'junior', 'kathy',
  'organ', 'ralph', 'superstar', 'trinoids', 'whisper', 'wobble', 'zarvox'])

function fantaisie(v: SpeechSynthesisVoice): boolean {
  const uri = (v.voiceURI || '').toLowerCase()
  const nom = v.name.toLowerCase().replace(/\s*\(.*$/, '').trim()
  return uri.includes('eloquence') || uri.includes('speech.synthesis.voice') || FANTAISIE.has(nom)
}

/** Voix francaises, fr-FR d'abord, sans les voix fantaisie de macOS. Une voix en ligne (voix Google de Chrome...)
 * envoie le texte lu a l'editeur du navigateur : seules les voix de l'appareil sont proposees quand il y en a
 * (recette du 2026-11-20, D-11). */
export function voixFrancaises(voix: SpeechSynthesisVoice[]): SpeechSynthesisVoice[] {
  const toutes = voix.filter((v) => v.lang.toLowerCase().startsWith('fr'))
  const serieuses = toutes.filter((v) => !fantaisie(v))
  const francaises = serieuses.length ? serieuses : toutes
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

/** Intertitre affiche d'une partie : celui du modele, sinon Introduction, Partie n ou A retenir (D141). */
export function intertitre(paragraphes: string[], intertitres: string[] | undefined, i: number): string {
  const donne = intertitres?.length === paragraphes.length ? intertitres[i]?.trim() : ''
  if (donne) return donne
  if (/^À retenir/i.test(paragraphes[i] ?? '')) return 'À retenir'
  return i === 0 && paragraphes.length > 2 ? 'Introduction' : `Partie ${i + 1}`
}

/** Mots par minute a vitesse 1, comme l'estimation du serveur (api/resumes_vocaux.py). */
export const MOTS_PAR_MINUTE = 150
export const compterMots = (texte: string) => texte.split(/\s+/).filter(Boolean).length

/** Transcription a telecharger (lecture hors ligne, dans le metro) : titre, intertitres, avertissement. */
export function transcription(titre: string, paragraphes: string[], intertitres: string[] | undefined,
  avertissement: string): string {
  const parties = paragraphes.map((p, i) => `${intertitre(paragraphes, intertitres, i)}\n\n${p}`)
  return `${titre}\n\n${parties.join('\n\n')}\n\n${avertissement}\n\nRésumé vocal Lexia, ${new Date().toLocaleDateString('fr-FR')}.\n`
}

export function nomDeFichier(titre: string): string {
  const base = titre.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
    .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60)
  return `resume-${base || 'lexia'}.txt`
}

// Vitesse et voix choisies : gardees dans ce navigateur (ni le texte ni le compte). Stockage indisponible
// (navigation privee) : valeurs par defaut.
const CLE_REGLAGES = 'lexia.voix.v1'
export interface Reglages { vitesse: number; voix: string }

export function lireReglages(): Reglages {
  try {
    const r = JSON.parse(localStorage.getItem(CLE_REGLAGES) ?? '{}') as Partial<Reglages>
    return { vitesse: typeof r.vitesse === 'number' && r.vitesse >= 0.5 && r.vitesse <= 2 ? r.vitesse : 1,
      voix: typeof r.voix === 'string' ? r.voix : '' }
  } catch {
    return { vitesse: 1, voix: '' }
  }
}

export function ecrireReglages(r: Reglages) {
  try {
    localStorage.setItem(CLE_REGLAGES, JSON.stringify(r))
  } catch {
    // stockage indisponible : reglages gardes pour la page seulement
  }
}

/** Ecran garde allume pendant la lecture (Screen Wake Lock) : sur telephone, la mise en veille peut interrompre la
 * synthese vocale du navigateur. Sans l'API ou en cas de refus : rien. Renvoie de quoi relacher le verrou. */
export async function garderEcranAllume(): Promise<(() => void) | null> {
  const wl = (navigator as Navigator & { wakeLock?: { request: (t: 'screen') => Promise<{ release: () => Promise<void> }> } }).wakeLock
  if (!wl) return null
  try {
    const verrou = await wl.request('screen')
    return () => { verrou.release().catch(() => {}) }
  } catch {
    return null
  }
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
