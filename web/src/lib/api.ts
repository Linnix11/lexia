// Client de l'API Lexia (FastAPI). Les types suivent les reponses de api/rag.py et api/quiz.py.

const BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') ?? '/api'

export type Mode = 'expliquer' | 'fiche' | 'cas_pratique' | 'commentaire' | 'dissertation'
export type FormatQuiz = 'qcm' | 'vrai_faux' | 'ouvertes'
export type Niveau = 'L1' | 'L2' | 'L3'

export interface Element {
  texte: string
  sources: string[] // identifiants de passages
}

export interface FicheSource {
  id: string
  label: string | null
  source_id: string
  type: string
  numero: string | null
  entete: string
  url: string
  version: string
  en_vigueur: boolean | null
  date: string | null
  extrait: string
}

export interface Controle {
  citations_retirees: number
  elements_retires: number
  references_non_verifiees: string[]
  recherche: 'hybride' | 'lexicale'
  passages_consultes?: number
}

export interface ReponseChat {
  reponse_id: string
  statut: 'reponse' | 'abstention' | 'hors_champ'
  titre: string
  droit_positif: Element[]
  explication: Element[]
  points_incertains: Element[]
  message: string
  sources: FicheSource[]
  avertissement: string
  controle: Controle
}

export interface SourceComplete extends FicheSource {
  texte: string
  titre: string | null
  meta: Record<string, unknown>
}

export interface Vigueur {
  id: string
  applicable: boolean
  en_vigueur: boolean | null
  version: string
  url: string
  version_en_vigueur: { id: string; version: string; url: string } | null
  message: string
}

export interface Matiere {
  id: string
  libelle: string
  sources: string[]
}

export interface QuestionQuiz {
  index: number
  question?: string
  affirmation?: string
  choix?: string[]
}

export interface Quiz {
  quiz_id: string | null
  format: FormatQuiz
  theme: string
  demande: number
  obtenu: number
  questions: QuestionQuiz[]
  message: string
  sources: FicheSource[]
  avertissement: string
}

export interface ResultatQuestion {
  index: number
  statut: 'correct' | 'incorrect' | 'partiel' | 'non_repondu' | 'a_verifier'
  explication: string
  sources: string[]
  bonne_reponse?: number | boolean
  elements_attendus?: string[]
  commentaire?: string
  elements_manquants?: string[]
}

export interface Correction {
  quiz_id: string
  score: number
  total: number
  resultats: ResultatQuestion[]
  sources: FicheSource[]
}

export interface Formule {
  id: 'gratuit' | 'etudiant' | 'intensif'
  nom: string
  prix_mensuel_euros: number
  questions_par_jour: number
  quiz_par_jour: number
  description: string
  avantages: string[]
}

export interface Profil {
  email: string
  cree_le: string
  formule: Formule
  formule_fin: string | null
  usage: { jour: string; questions: number; quiz: number }
}

export interface ConfigPublique {
  comptes: boolean
  contact_email: string | null
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

const MESSAGES: Record<number, string> = {
  401: 'Votre session a expiré : reconnectez-vous.',
  402: 'Limite du jour atteinte pour votre formule.',
  404: 'Élément introuvable.',
  413: 'Votre texte est trop long.',
  429: 'Trop de requêtes : patientez une minute avant de réessayer.',
  503: 'Le modèle est momentanément indisponible. Réessayez dans quelques instants.',
}

async function requete<T>(chemin: string, init?: RequestInit): Promise<T> {
  let r: Response
  try {
    r = await fetch(`${BASE}${chemin}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    throw new ApiError(0, 'Le serveur Lexia est injoignable. Vérifiez votre connexion.')
  }
  if (r.status === 204) return undefined as T
  if (!r.ok) {
    let detail = MESSAGES[r.status] ?? `Erreur inattendue (${r.status}).`
    try {
      const corps = await r.json()
      if (typeof corps?.detail === 'string') detail = corps.detail
    } catch {
      /* corps non JSON : message par defaut */
    }
    if (r.status === 401 && !chemin.startsWith('/auth/')) surSessionExpiree?.()
    throw new ApiError(r.status, detail)
  }
  return r.json() as Promise<T>
}

const post = <T,>(chemin: string, corps: unknown) =>
  requete<T>(chemin, { method: 'POST', body: JSON.stringify(corps) })

/** Appele quand une requete renvoie 401 (session expiree) : le site redirige vers la connexion. */
let surSessionExpiree: (() => void) | null = null
export function quandSessionExpiree(fn: (() => void) | null) {
  surSessionExpiree = fn
}

export const api = {
  config: () => requete<ConfigPublique>('/config'),
  formules: () => requete<Formule[]>('/formules'),
  moi: () => requete<Profil>('/auth/moi'),
  session: () => requete<Profil | null>('/auth/session'),
  inscription: (email: string, mot_de_passe: string, accepte_cgu: boolean) =>
    post<Profil>('/auth/inscription', { email, mot_de_passe, accepte_cgu }),
  connexion: (email: string, mot_de_passe: string) => post<Profil>('/auth/connexion', { email, mot_de_passe }),
  deconnexion: () => post<void>('/auth/deconnexion', {}),
  supprimerCompte: (mot_de_passe: string) => post<void>('/auth/supprimer', { mot_de_passe }),
  matieres: () => requete<Matiere[]>('/matieres'),
  chat: (question: string, mode: Mode, matiere: string | null, niveau: Niveau) =>
    post<ReponseChat>('/chat', { question, mode, matiere, niveau }),
  quiz: (theme: string, format: FormatQuiz, nombre: number, matiere: string | null, niveau: Niveau) =>
    post<Quiz>('/quiz', { theme, format, nombre, matiere, niveau }),
  corriger: (quiz_id: string, reponses: { index: number; valeur: number | boolean | string | null }[]) =>
    post<Correction>('/quiz/correct', { quiz_id, reponses }),
  source: (id: string) => requete<SourceComplete>(`/sources/${encodeURIComponent(id)}`),
  vigueur: (id: string) => requete<Vigueur>(`/sources/${encodeURIComponent(id)}/vigueur`),
  feedback: (reponse_id: string, utile: boolean, motif?: string) =>
    post<void>('/feedback', { reponse_id, utile, motif: motif ?? null }),
}
