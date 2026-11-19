// Cartes a retourner avec repetition espacee, tirees des questionnaires corriges et des fiches.
// Aucun appel au modele ni au serveur : les cartes restent dans ce navigateur, comme les fiches.
import type { Correction, FicheSource, Quiz } from './api'
import { empreinte, type Favori } from './favoris'

export interface SourceCarte {
  id: string
  entete: string
  url: string
}

export interface Carte {
  id: string // « quiz:<quiz_id>:<index> » ou « fiche:<reponse_id> » : un meme contenu n'est ajoute qu'une fois
  origine: 'quiz' | 'fiche'
  recto: string
  verso: string
  sources: SourceCarte[]
  niveau: number // 1 a 5
  prochaine: string // ISO : la carte est a revoir a partir de cette date
  creee_le: string
}

// Systeme de Leitner simplifie : une carte sue au niveau n revient apres INTERVALLES_JOURS[n - 1] jours.
export const INTERVALLES_JOURS = [1, 3, 7, 14, 30]
const NIVEAU_MAX = INTERVALLES_JOURS.length

export const MAX_CARTES = 500
export const MESSAGE_LIMITE_CARTES = `Limite de ${MAX_CARTES} cartes atteinte : retirez des cartes pour en ajouter.`

/** Minuit (heure locale) du jour qui suit `maintenant` de `jours` jours. */
function minuitDans(maintenant: Date, jours: number): string {
  return new Date(maintenant.getFullYear(), maintenant.getMonth(), maintenant.getDate() + jours).toISOString()
}

function sourcesCitees(ids: string[], sources: FicheSource[]): SourceCarte[] {
  const vus = new Set<string>()
  const out: SourceCarte[] = []
  for (const id of ids) {
    const s = sources.find((x) => x.id === id)
    if (s && !vus.has(id)) {
      vus.add(id)
      out.push({ id: s.id, entete: s.entete, url: s.url })
    }
  }
  return out
}

function nouvelleCarte(id: string, origine: Carte['origine'], recto: string, verso: string, sources: SourceCarte[], maintenant: Date): Carte {
  // Due des minuit du jour : une carte ajoutee apres l'ouverture de la vue compte deja parmi celles a revoir.
  return { id, origine, recto, verso, sources, niveau: 1, prochaine: minuitDans(maintenant, 0), creee_le: maintenant.toISOString() }
}

/** Une carte par question corrigee dont la reponse est connue. */
export function cartesDuQuiz(quiz: Quiz, correction: Correction, maintenant = new Date()): Carte[] {
  const sources = [...correction.sources, ...quiz.sources]
  const cartes: Carte[] = []
  for (const q of quiz.questions) {
    const r = correction.resultats.find((x) => x.index === q.index)
    if (!r) continue
    let reponse = ''
    if (typeof r.bonne_reponse === 'number' && q.choix) reponse = q.choix[r.bonne_reponse] ?? ''
    else if (typeof r.bonne_reponse === 'boolean') reponse = r.bonne_reponse ? 'Vrai' : 'Faux'
    else if (r.elements_attendus?.length) reponse = `Éléments attendus : ${r.elements_attendus.join(' ; ')}`
    if (!reponse) continue
    const recto = quiz.format === 'vrai_faux' ? `Vrai ou faux : ${q.affirmation ?? q.question ?? ''}` : (q.question ?? q.affirmation ?? '')
    if (!recto.trim()) continue
    const verso = [reponse, r.explication?.trim()].filter(Boolean).join('\n\n')
    cartes.push(nouvelleCarte(`quiz:${quiz.quiz_id}:${q.index}`, 'quiz', recto, verso, sourcesCitees(r.sources, sources), maintenant))
  }
  return cartes
}

/** Au recto la question posee ; au verso la reponse directe, a defaut les trois premieres regles de droit positif. */
export function carteDeFiche(f: Favori, maintenant = new Date()): Carte | null {
  const r = f.reponse
  const elements = r.reponse_directe?.length ? r.reponse_directe : (r.droit_positif ?? []).slice(0, 3)
  const verso = elements.map((e) => e.texte.trim()).filter(Boolean).join('\n')
  if (!verso || !f.question.trim()) return null
  return nouvelleCarte(`fiche:${f.id}`, 'fiche', f.question, verso, sourcesCitees(elements.flatMap((e) => e.sources), r.sources), maintenant)
}

/** Note une revision : sue, la carte monte d'un niveau ; ratee, elle repart au niveau 1 et revient demain. */
export function reviser(c: Carte, sue: boolean, maintenant = new Date()): Carte {
  if (!sue) return { ...c, niveau: 1, prochaine: minuitDans(maintenant, 1) }
  const niveau = Math.min(Math.max(c.niveau, 1), NIVEAU_MAX)
  return { ...c, niveau: Math.min(niveau + 1, NIVEAU_MAX), prochaine: minuitDans(maintenant, INTERVALLES_JOURS[niveau - 1]) }
}

/** Cartes a revoir maintenant, les plus en retard d'abord. */
export function aReviser(cartes: Carte[], maintenant = new Date()): Carte[] {
  const t = maintenant.getTime()
  return cartes.filter((c) => Date.parse(c.prochaine) <= t).sort((a, b) => Date.parse(a.prochaine) - Date.parse(b.prochaine))
}

/** Ajoute sans doublon (une carte deja presente garde sa progression), dans la limite de MAX_CARTES. */
export function ajouterCartes(existantes: Carte[], nouvelles: Carte[]): { liste: Carte[]; ajoutees: number; refusees: number } {
  const ids = new Set(existantes.map((c) => c.id))
  const liste = [...existantes]
  let ajoutees = 0
  let refusees = 0
  for (const c of nouvelles) {
    if (ids.has(c.id)) continue
    if (liste.length >= MAX_CARTES) {
      refusees++
      continue
    }
    ids.add(c.id)
    liste.push(c)
    ajoutees++
  }
  return { liste, ajoutees, refusees }
}

// Une cle par compte, sans l'adresse en clair (meme regle que les fiches, favoris.ts).
const cle = (compte: string) => `lexia.cartes.v1.${empreinte(compte.toLowerCase())}`

export function lireCartes(compte: string): Carte[] {
  try {
    const brut = localStorage.getItem(cle(compte))
    const liste = brut ? (JSON.parse(brut) as Carte[]) : []
    return Array.isArray(liste) ? liste : []
  } catch {
    return []
  }
}

export function ecrireCartes(liste: Carte[], compte: string): boolean {
  try {
    localStorage.setItem(cle(compte), JSON.stringify(liste))
    return true
  } catch {
    return false // stockage indisponible (navigation privee, quota)
  }
}

/** Suppression du compte : les cartes de ce compte quittent aussi ce navigateur. */
export function effacerCartes(compte: string) {
  try {
    localStorage.removeItem(cle(compte))
  } catch {
    /* stockage indisponible : rien a effacer */
  }
}
