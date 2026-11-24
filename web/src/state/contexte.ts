import { createContext, useContext } from 'react'
import type { Correction, CoursDepose, FormatQuiz, Matiere, Mode, Niveau, OptionsCours, Quiz, ReponseChat } from '../lib/api'
import type { Carte } from '../lib/cartes'
import type { Favori } from '../lib/favoris'
import type { Semestre } from '../lib/semestres'

export type Vue = 'espace' | 'assistant' | 'matieres' | 'fiches' | 'cartes' | 'bibliotheque'

/** Vues de l'espace etudiant, chacune a son adresse (recette du 2026-11-23, D125) : recharger, partager ou
 * revenir en arriere garde la vue. /app reste l'accueil de l'espace. court : libelle sous l'icone dans la barre
 * du bas du mobile (audit du 2026-11-18, D7), contenu dans le libelle complet qui reste le nom accessible. */
export const VUES: { id: Vue; chemin: string; label: string; court: string; ico: string }[] = [
  { id: 'espace', chemin: '/app', label: 'Mon espace', court: 'Espace', ico: '⌂' },
  { id: 'assistant', chemin: '/app/assistant', label: 'Assistant IA', court: 'Assistant', ico: '✳' },
  { id: 'matieres', chemin: '/app/matieres', label: 'Mes matières', court: 'Matières', ico: '▤' },
  { id: 'fiches', chemin: '/app/fiches', label: 'Fiches & révisions', court: 'Fiches', ico: '▧' },
  { id: 'cartes', chemin: '/app/cartes', label: 'Mes cartes mentales', court: 'Cartes', ico: '✣' },
  { id: 'bibliotheque', chemin: '/app/bibliotheque', label: 'Bibliothèque', court: 'Biblio', ico: '▥' },
]

/** Vue d'une adresse de l'espace (barre finale ignoree), null hors de l'espace ou pour une adresse inconnue. */
export function vueDeChemin(chemin: string): Vue | null {
  const route = chemin.replace(/\/+$/, '') || '/'
  return VUES.find((v) => v.chemin === route)?.id ?? null
}

export interface Message {
  id: string
  question: string
  mode: Mode
  etat: 'en_cours' | 'ok' | 'erreur'
  reponse?: ReponseChat
  erreur?: string
  statut?: number
}

export type ValeurQuiz = number | boolean | string | null

export interface ParametresQuiz {
  theme: string
  nombre: number
  format: FormatQuiz
  matiere: string | null
}

/** Dernier questionnaire : garde hors de la fenetre, pour la rouvrir (et finir une generation) sans rien perdre. */
export interface EtatQuiz {
  parametres: ParametresQuiz | null
  quiz: Quiz | null
  reponses: Record<number, ValeurQuiz>
  correction: Correction | null
  etat: 'libre' | 'generation' | 'correction'
  erreur: string | null
  /** Code HTTP de l'erreur (402 : limite du jour, lien vers les formules) */
  statut?: number
}

export interface AppState {
  vue: Vue
  setVue: (v: Vue) => void
  niveau: Niveau // deduit du semestre
  semestre: Semestre
  setSemestre: (s: Semestre) => void
  matiere: string | null
  setMatiere: (m: string | null) => void
  mode: Mode // mode choisi dans l'assistant
  setMode: (m: Mode) => void
  mesCours: CoursDepose[] // cours deposes par l'etudiant
  coursMax: number // nombre maximal de cours pour sa formule
  rafraichirCours: () => void
  coursChoisis: number[] // cours utilises par l'assistant et les questionnaires (vide : textes officiels seuls)
  setCoursChoisis: (ids: number[]) => void
  avecOfficiel: boolean // false : « Mon cours uniquement »
  setAvecOfficiel: (v: boolean) => void
  optionsCours: OptionsCours | undefined
  matieres: Matiere[]
  messages: Message[]
  envoyer: (question: string, mode?: Mode) => void
  effacer: () => void
  occupe: boolean
  favoris: Favori[]
  basculerFavori: (m: Message) => void
  estFavori: (reponseId: string) => boolean
  cartes: Carte[] // cartes a retourner, gardees dans ce navigateur (lib/cartes.ts)
  ajouterCartes: (nouvelles: Carte[]) => void
  noterCarte: (id: string, sue: boolean) => void
  retirerCarte: (id: string) => void
  sourceOuverte: string | null
  ouvrirSource: (id: string | null) => void
  quizOuvert: { theme?: string; id: number } | null
  ouvrirQuiz: (theme?: string) => void
  fermerQuiz: () => void
  dernierQuiz: EtatQuiz
  genererQuiz: (p: ParametresQuiz) => void
  repondreQuiz: (index: number, valeur: ValeurQuiz) => void
  corrigerQuiz: () => void
  signalerErreurQuiz: (erreur: string | null) => void
  toast: string | null
  notifier: (msg: string) => void
}

export const Ctx = createContext<AppState | null>(null)

/** Etat de l'espace etudiant s'il entoure le composant (null sur une page publique ou dans un test isole). */
export function useAppFacultatif(): AppState | null {
  return useContext(Ctx)
}

export function useApp(): AppState {
  const v = useContext(Ctx)
  if (!v) throw new Error('useApp doit etre utilise dans <AppProvider>')
  return v
}
