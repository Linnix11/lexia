import { createContext, useContext } from 'react'
import type { Correction, CoursDepose, FormatQuiz, Matiere, Mode, Niveau, OptionsCours, Quiz, ReponseChat } from '../lib/api'
import type { Favori } from '../lib/favoris'
import type { Semestre } from '../lib/semestres'

export type Vue = 'espace' | 'assistant' | 'matieres' | 'fiches' | 'bibliotheque'

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

export function useApp(): AppState {
  const v = useContext(Ctx)
  if (!v) throw new Error('useApp doit etre utilise dans <AppProvider>')
  return v
}
