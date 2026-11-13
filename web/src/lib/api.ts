// Client de l'API Lexia (FastAPI). Les types suivent les reponses de api/rag.py et api/quiz.py.

const BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') ?? '/api'

export type Mode = 'expliquer' | 'fiche' | 'cas_pratique' | 'commentaire' | 'dissertation'
export type FormatQuiz = 'qcm' | 'vrai_faux' | 'ouvertes'
export type Niveau = 'L1' | 'L2' | 'L3'

export interface Element {
  texte: string
  sources: string[] // identifiants de passages
  rubrique?: string // rubrique imposee par le mode (Definition, Probleme de droit...)
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
  noms_sources?: Record<string, string>
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
  cours_max: number
  description: string
  avantages: string[]
}

export interface Profil {
  email: string
  cree_le: string
  formule: Formule
  formule_fin: string | null
  usage: { jour: string; questions: number; quiz: number }
  admin: boolean
}

export interface JourStats {
  jour: string
  questions: number
  quiz: number
  actifs: number
  inscriptions: number
}

export interface StatsAdmin {
  comptes: {
    total: number
    par_formule: Record<string, number>
    payants_actifs: number
    formules_expirees: number
    nouveaux_7j: number
    nouveaux_30j: number
  }
  revenu_mensuel_estime: number
  aujourd_hui: JourStats
  serie: JourStats[]
  formules: Formule[]
  activite: {
    dernieres_24h: {
      questions: number
      quiz: number
      statuts: Record<string, number>
      duree_moyenne_ms: number | null
      duree_p95_ms: number | null
      erreurs_modele: number
      recherche_hybride: number
    }
    questions_7j: number
    derniere_erreur: { ts: string; route: string; detail: string } | null
    retours: { utiles: number; pas_utiles: number; motifs: Record<string, number> }
  }
}

export interface ClientAdmin {
  id: number
  email: string
  admin: boolean
  formule: string
  formule_enregistree: string
  formule_fin: string | null
  cree_le: string
  questions_aujourdhui: number
  quiz_aujourdhui: number
  questions_30j: number
  derniere_activite: string | null
  limite_questions: number
}

export interface ActiviteAdmin {
  requetes: {
    ts: string
    route: string
    mode?: string
    matiere?: string | null
    statut?: string
    recherche?: string
    modele?: string | null
    duree_ms?: number
    format?: string
    obtenu?: number
  }[]
  erreurs: { ts: string; route: string; type: string; detail: string }[]
}

export interface ServeurAdmin {
  version: string | null
  demarre_le: string
  uptime_service_s: number
  uptime_systeme_s: number | null
  charge: [number, number, number] | null
  processeurs: number | null
  memoire_service: number | null
  memoire_systeme: { total: number; disponible: number } | null
  disque: { total: number; libre: number }
  python: string
  systeme: string
  index: { moteur: string; passages: number; embeddings: number; couverture?: number }
  modeles: Record<string, string | string[] | null>
  etat_modele: 'ok' | 'degrade' | 'inconnu'
}

export interface InfosLegales {
  editeur: string | null
  statut: string | null
  adresse: string | null
  siren: string | null
  directeur: string | null
  telephone?: string | null
  hebergeur_telephone?: string | null
  tva?: string | null
  mediateur: string | null
  gemini_payant: boolean
  groq?: boolean
}

export interface ConfigPublique {
  comptes: boolean
  contact_email: string | null
  legal?: InfosLegales
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

export interface CoursDepose {
  id: number
  matiere: string
  libelle_matiere: string
  titre: string
  fichier: string
  pages: number | null
  passages: number
  statut: 'traitement' | 'pret' | 'erreur'
  ajoute_le: string
}

/** Cours a utiliser pour une demande ; avec_officiel = false : « Mon cours uniquement ». */
export interface OptionsCours {
  cours: number[]
  avec_officiel: boolean
}

const optionsCours = (o?: OptionsCours) => ({ cours: o?.cours ?? [], avec_officiel: o?.avec_officiel ?? true })

const post = <T,>(chemin: string, corps: unknown) =>
  requete<T>(chemin, { method: 'POST', body: JSON.stringify(corps) })

/** Appele quand une requete renvoie 401 (session expiree) : le site redirige vers la connexion. */
let surSessionExpiree: (() => void) | null = null
export function quandSessionExpiree(fn: (() => void) | null) {
  surSessionExpiree = fn
}

export interface Annale {
  id: number
  titre: string
  matiere: string
  libelle_matiere: string
  niveau: string
  annee: number
  universite: string
  session: string
  url: string
  corrige: boolean
  ajoute_le: string
}

export type NouvelleAnnale = Omit<Annale, 'id' | 'libelle_matiere' | 'ajoute_le'>

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
  admin: {
    stats: () => requete<StatsAdmin>('/admin/stats'),
    clients: (q = '') => requete<ClientAdmin[]>(`/admin/clients?q=${encodeURIComponent(q)}`),
    formule: (id: number, formule: string, jours: number | null) =>
      post<ClientAdmin>(`/admin/clients/${id}/formule`, { formule, jours }),
    role: (id: number, admin: boolean) => post<ClientAdmin>(`/admin/clients/${id}/admin`, { admin }),
    supprimer: (id: number) => post<void>(`/admin/clients/${id}/supprimer`, {}),
    activite: () => requete<ActiviteAdmin>('/admin/activite?limite=150'),
    serveur: () => requete<ServeurAdmin>('/admin/serveur'),
    ajouterAnnale: (a: NouvelleAnnale) => post<Annale>('/admin/annales', a),
    supprimerAnnale: (id: number) => post<void>(`/admin/annales/${id}/supprimer`, {}),
  },
  matieres: () => requete<Matiere[]>('/matieres'),
  annales: () => requete<{ niveaux: string[]; annales: Annale[] }>('/annales'),
  chat: (question: string, mode: Mode, matiere: string | null, niveau: Niveau, semestre: number, cours?: OptionsCours) =>
    post<ReponseChat>('/chat', { question, mode, matiere, niveau, semestre, ...optionsCours(cours) }),
  quiz: (theme: string, format: FormatQuiz, nombre: number, matiere: string | null, niveau: Niveau, semestre: number,
    cours?: OptionsCours) =>
    post<Quiz>('/quiz', { theme, format, nombre, matiere, niveau, semestre, ...optionsCours(cours) }),
  cours: {
    lister: () => requete<{ cours: CoursDepose[]; maximum: number; formats: string[] }>('/cours'),
    deposer: (fichier: File, matiere: string, titre: string) => {
      const params = new URLSearchParams({ matiere, fichier: fichier.name, titre })
      return requete<CoursDepose>(`/cours?${params}`, {
        method: 'POST', body: fichier, headers: { 'Content-Type': 'application/octet-stream' },
      })
    },
    supprimer: (id: number) => post<void>(`/cours/${id}/supprimer`, {}),
  },
  corriger: (quiz_id: string, reponses: { index: number; valeur: number | boolean | string | null }[]) =>
    post<Correction>('/quiz/correct', { quiz_id, reponses }),
  source: (id: string) => requete<SourceComplete>(`/sources/${encodeURIComponent(id)}`),
  vigueur: (id: string) => requete<Vigueur>(`/sources/${encodeURIComponent(id)}/vigueur`),
  feedback: (reponse_id: string, utile: boolean, motif?: string) =>
    post<void>('/feedback', { reponse_id, utile, motif: motif ?? null }),
}
