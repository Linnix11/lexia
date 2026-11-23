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
  // 1 a 3 phrases sourcees affichees en tete ; absente des reponses et fiches anterieures, vide en commentaire
  // et en dissertation (audit d'interface du 2026-11-16, point 3)
  reponse_directe?: Element[]
  message: string
  sources: FicheSource[]
  avertissement: string
  controle: Controle
}

/** Reponse de /fraicheur : date jusqu'a laquelle chaque source est a jour (audit B7). */
export interface FraicheurSource {
  nom: string
  date: string // AAAA-MM-JJ
  nature: 'textes' | 'jurisprudence'
  /** D'ou vient la decision la plus recente (« site du Conseil constitutionnel, ... », D113) ; absent sinon. */
  origine?: string
}

export interface Fraicheur {
  textes: string | null
  sources: Record<string, FraicheurSource>
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
  annee?: string // L1, L2 ou L3 : annee ou la matiere est le plus souvent enseignee (D97)
  mots?: string[] // autres intitules des maquettes (recherche)
  principales?: string[] // sources montrees d'abord
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
  /** Prenom (D100) et nom (D102) : demandes a l'inscription, vides pour les comptes anciens ; jamais envoyes au modele. */
  prenom?: string | null
  nom?: string | null
  cree_le: string
  formule: Formule
  formule_fin: string | null
  usage: { jour: string; questions: number; quiz: number }
  admin: boolean
  double_authentification?: boolean
  codes_secours_restants?: number
  email_verifie?: boolean
  // Reponse de l'inscription seulement : faux quand le lien n'est pas parti (plafond d'envois, D119)
  lien_envoye?: boolean
  /** Consentement aux e-mails d'information (case distincte a l'inscription, retirable dans Mon compte) */
  infos_email?: boolean
  /** Compte cree avec un code d'acces de la beta fermee : questionnaire « Donner mon avis » (D121) */
  beta?: boolean
}

/** Reponse facultative a « Comment avez-vous connu Lexia ? » (api/comptes.py, ORIGINES) */
export const ORIGINES = [
  ['reseaux_sociaux', 'Réseaux sociaux'],
  ['association', 'Association étudiante'],
  ['ami', 'Un ami ou une amie'],
  ['enseignant', 'Un enseignant'],
  ['recherche', 'Recherche sur internet'],
  ['autre', 'Autre'],
] as const
export type Origine = (typeof ORIGINES)[number][0]

/** Cases et reponse de l'inscription, enregistrees avec le compte (note de l'editeur du 2026-11-20, point 1) */
export interface ChoixInscription {
  age_atteste: boolean
  cgu_version: string
  infos_email: boolean
  origine: Origine | null
  /** Beta fermee (D121) : code d'acces recu par e-mail, exige quand le serveur l'annonce (config.beta_fermee) */
  code_beta?: string | null
}

/** Reponse de /auth/connexion quand le compte a la double authentification : le code reste a saisir. */
export interface DeuxiemeEtape {
  double_authentification_requise: true
  jeton: string
}

export interface JourStats {
  jour: string
  questions: number
  quiz: number
  actifs: number
  inscriptions: number
}

/** Dernier paiement du compte (retour de la page Stripe) et retractation possible (moins de 14 jours). */
export interface AchatRetractable {
  session: string
  formule: string
  mois: number
  montant_centimes: number
  paye_le: string
  /** Dernier jour du delai (AAAA-MM-JJ), proroge au premier jour ouvrable (C. consom. L. 221-19 3°) */
  fin: string
}

export interface EtatPaiement {
  dernier: { statut: string; formule: string; mois: number; paye_le: string | null } | null
  retractable: boolean
  retractables: AchatRetractable[]
}

/** Paiement qui demande une action de l'editeur (remboursement, verification dans Stripe). */
export interface PaiementATraiter {
  session: string
  email: string
  formule: string
  mois: number
  montant_centimes: number
  statut: string
  motif: string | null
  cree_le: string
  paye_le: string | null
  retractation_le: string | null
  /** null : accuse de retractation pas encore parti (renvoye chaque jour) */
  accuse_envoye_le?: string | null
  paiement_stripe: string | null
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
  /** Fidelite par semaine d'inscription, sans donnee nominative ; null : delai pas encore atteint (D111) */
  fidelite?: { semaine: string; inscrits: number; revenus_7j: number | null; revenus_30j: number | null }[]
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
  courriel?: boolean
}

export interface ConfigPublique {
  comptes: boolean
  contact_email: string | null
  /** Paiement en ligne par Stripe Checkout actif (cles configurees sur le serveur). */
  paiement?: boolean
  /** Beta fermee : inscription avec un code d'acces seulement (BETA_FERMEE=1, D121) */
  beta_fermee?: boolean
  legal?: InfosLegales
}

/** Beta fermee (D121) : code d'acces, sans le code lui-meme (affiche une seule fois, a sa creation). */
export interface CodeBeta {
  id: number
  libelle: string
  plafond: number
  /** Inscriptions faites avec le code (jamais rendues, meme si le compte est supprime) */
  inscriptions: number
  /** Comptes encore existants crees avec le code */
  comptes: number
  actif: boolean
  cree_le: string
  /** Reponse de la creation seulement */
  code?: string
}

export interface AvisBeta {
  note: number
  aide: string
  manque: string
  erreur: string
  lien: string
}

export interface AvisBetaLu extends AvisBeta {
  id: number
  jour: string
}

export interface DureesBeta {
  mesures: number
  mediane_ms: number | null
  p90_ms: number | null
}

/** Suivi d'usage anonyme : agregats seulement, ni texte des questions ni compte (D121) */
export interface UsageBeta {
  jours: number
  par_jour: { jour: string; questions: number; total: number }[]
  fonctions: ({ fonction: string; libelle: string; appels: number; erreurs: number; refus: number; taux_erreur: number | null } & DureesBeta)[]
  etapes: ({ etape: string } & DureesBeta)[]
  appels: number
  taux_erreur: number | null
}

/** Export CSV des avis : simple lien (GET, cookie de session), le navigateur enregistre le fichier. */
export const LIEN_AVIS_CSV = `${BASE}/admin/beta/avis.csv`

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
  422: 'Votre saisie est incomplète ou trop courte : vérifiez-la et réessayez.',
  429: 'Trop de requêtes : patientez une minute avant de réessayer.',
  // Pages de nginx ou Cloudflare, sans detail JSON (audit du 2026-11-18, D9)
  502: 'Le serveur Lexia redémarre ou est surchargé. Réessayez dans un instant.',
  503: 'Le modèle est momentanément indisponible. Réessayez dans quelques instants.',
  504: 'Le serveur Lexia a mis trop de temps à répondre. Réessayez dans un instant.',
  524: 'Le serveur Lexia a mis trop de temps à répondre. Réessayez dans un instant.',
}

// Au-dela, la requete est abandonnee : nginx coupe a 120 s, une page ne doit jamais attendre indefiniment.
// Un depot de fichier, plus long sur une connexion lente, a davantage de temps (audit du 2026-11-18, D9).
const DELAI_MS = 130_000
const DELAI_DEPOT_MS = 600_000

async function requete<T>(chemin: string, init?: RequestInit): Promise<T> {
  let r: Response
  try {
    r = await fetch(`${BASE}${chemin}`, {
      signal: AbortSignal.timeout(init?.body instanceof Blob ? DELAI_DEPOT_MS : DELAI_MS),
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch (e) {
    if (e instanceof DOMException && e.name === 'TimeoutError') throw new ApiError(0, MESSAGES[504])
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

/** Envoi d'un fichier par XMLHttpRequest pour suivre sa progression ; memes messages d'erreur que requete. */
function envoyerAvecProgres<T>(chemin: string, fichier: File, entetes: Record<string, string>,
  progres: (part: number) => void): Promise<T> {
  return new Promise<T>((ok, ko) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${BASE}${chemin}`)
    xhr.timeout = DELAI_DEPOT_MS
    xhr.setRequestHeader('Content-Type', 'application/octet-stream')
    for (const [k, v] of Object.entries(entetes)) xhr.setRequestHeader(k, v)
    xhr.upload.onprogress = (e) => { if (e.lengthComputable && e.total > 0) progres(Math.min(1, e.loaded / e.total)) }
    xhr.upload.onload = () => progres(1)
    xhr.ontimeout = () => ko(new ApiError(0, MESSAGES[504]))
    xhr.onerror = () => ko(new ApiError(0, 'Le serveur Lexia est injoignable. Vérifiez votre connexion.'))
    xhr.onload = () => {
      let corps: unknown = null
      try {
        corps = JSON.parse(xhr.responseText)
      } catch {
        /* corps non JSON (page de nginx ou de Cloudflare) : message par defaut */
      }
      if (xhr.status >= 200 && xhr.status < 300) return ok(corps as T)
      const detail = (corps as { detail?: unknown } | null)?.detail
      if (xhr.status === 401) surSessionExpiree?.()
      ko(new ApiError(xhr.status, typeof detail === 'string' ? detail
        : xhr.status === 413 ? 'Fichier trop volumineux (20 Mo au plus).'
          : MESSAGES[xhr.status] ?? `Erreur inattendue (${xhr.status}).`))
    }
    xhr.send(fichier)
  })
}

export interface ApercuCours extends CoursDepose {
  apercu: { page: number | null; page_fin: number | null; texte: string }[]
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
  avertissement?: string | null // ex. pages sans texte (scan) : leur contenu n'est pas pris en compte
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

/** Cours recupere sur un site tiers sous licence libre (docs/cours-libres.md) : attribution exigee par la licence. */
export interface CoursRecupere {
  id: string
  titre: string
  matiere: string
  libelle_matiere: string
  auteur: string
  source: string
  source_url: string
  url_original: string
  historique_url: string
  licence: string
  licence_libelle: string
  licence_url: string
  mis_a_jour: string
  modifications: string
  sections: number
}

export interface CoursRecupereComplet extends Omit<CoursRecupere, 'sections'> {
  avertissement: string
  sections: { titre: string; texte: string }[]
}

/** Demande de resume vocal (D106, docs/resumes-vocaux.md) : le serveur relit lui-meme cours et extraits. */
export type DemandeResume =
  | { type: 'reponse'; titre: string; texte: string; sources: string[] }
  | { type: 'cours' | 'cours_recupere'; id: string }

export interface ResumeVocal {
  titre: string
  paragraphes: string[]
  mots: number
  duree_estimee_s: number
  partiel: boolean // document trop long : seul son debut est resume
  message: string
  avertissement: string
  restants: number
}

/** Carte mentale (D112, docs/cartes-mentales.md) : documents lus comme pour le resume vocal, ou une matiere. */
export type DemandeCarte = DemandeResume | { type: 'matiere'; matiere: string; notion: string }

export interface FeuilleCarte {
  texte: string // reference presente dans les extraits envoyes au modele
  lien: { url: string; entete: string } | null // texte officiel, quand Lexia le connait
}

export interface NoeudCarte {
  libelle: string
  articles: FeuilleCarte[]
  enfants: NoeudCarte[]
}

export interface CarteMentale {
  titre: string
  branches: NoeudCarte[]
  partiel: boolean
  message: string
  avertissement: string
  restants: number
}

export const api = {
  config: () => requete<ConfigPublique>('/config'),
  formules: () => requete<Formule[]>('/formules'),
  session: () => requete<Profil | null>('/auth/session'),
  /** Donnees du compte (RGPD art. 15 et 20 ; audit du 2026-11-19, JUR-11) */
  exporterDonnees: () => requete<unknown>('/compte/export'),
  inscription: (email: string, mot_de_passe: string, accepte_cgu: boolean, prenom: string, nom: string, choix: ChoixInscription) =>
    post<Profil>('/auth/inscription', { email, mot_de_passe, accepte_cgu, prenom: prenom.trim(), nom: nom.trim(), ...choix }),
  changerInfosEmail: (accepte: boolean) => post<Profil>('/auth/infos-email', { accepte }),
  changerIdentite: (prenom: string, nom: string) => post<Profil>('/auth/identite', { prenom: prenom.trim(), nom: nom.trim() }),
  connexion: (email: string, mot_de_passe: string) => post<Profil | DeuxiemeEtape>('/auth/connexion', { email, mot_de_passe }),
  connexionCode: (jeton: string, code: string) => post<Profil>('/auth/connexion/code', { jeton, code }),
  verifierEmail: (jeton: string) => post<Profil | null>('/auth/email/verifier', { jeton }),
  renvoyerVerification: () => post<{ envoye: boolean }>('/auth/email/renvoyer', {}),
  motDePasseOublie: (email: string) => post<{ envoye: boolean }>('/auth/mot-de-passe/oubli', { email }),
  nouveauMotDePasse: (jeton: string, mot_de_passe: string) =>
    post<{ modifie: boolean }>('/auth/mot-de-passe/nouveau', { jeton, mot_de_passe }),
  deuxFacteurs: {
    preparer: () => post<{ secret: string; uri: string }>('/auth/2fa/preparer', {}),
    activer: (mot_de_passe: string, code: string) => post<{ codes_secours: string[] }>('/auth/2fa/activer', { mot_de_passe, code }),
    desactiver: (mot_de_passe: string, code: string) => post<Profil>('/auth/2fa/desactiver', { mot_de_passe, code }),
  },
  deconnexion: () => post<void>('/auth/deconnexion', {}),
  /** code : celui de l'application quand la double authentification est active (SEC-6), sinon vide */
  supprimerCompte: (mot_de_passe: string, code = '') => post<void>('/auth/supprimer', { mot_de_passe, code }),
  /** Ouvre une session de paiement Stripe Checkout ; renvoie l'adresse de la page de paiement. */
  payer: (formule: string, mois: number, execution_immediate: boolean, cgu_version: string) =>
    post<{ url: string }>('/paiement/session', { formule, mois, execution_immediate, cgu_version }),
  paiementEtat: () => requete<EtatPaiement>('/paiement/etat'),
  /** Declaration de retractation en ligne (art. L. 221-21 et D. 221-5 du Code de la consommation). */
  retracter: (nom: string, sessions: string[]) =>
    post<{ retractes: number; accuse_envoye: boolean; le: string }>('/paiement/retractation', { nom, sessions }),
  admin: {
    stats: () => requete<StatsAdmin>('/admin/stats'),
    paiements: () => requete<PaiementATraiter[]>('/paiement/a-traiter'),
    // recherche dans le corps de la requete, jamais dans l'adresse (journaux, historique ; D111)
    clients: (q = '') => (q.trim() ? post<ClientAdmin[]>('/admin/clients/recherche', { q }) : requete<ClientAdmin[]>('/admin/clients')),
    formule: (id: number, formule: string, jours: number | null) =>
      post<ClientAdmin>(`/admin/clients/${id}/formule`, { formule, jours }),
    role: (id: number, admin: boolean) => post<ClientAdmin>(`/admin/clients/${id}/admin`, { admin }),
    supprimer: (id: number) => post<void>(`/admin/clients/${id}/supprimer`, {}),
    activite: () => requete<ActiviteAdmin>('/admin/activite?limite=150'),
    serveur: () => requete<ServeurAdmin>('/admin/serveur'),
    ajouterAnnale: (a: NouvelleAnnale) => post<Annale>('/admin/annales', a),
    supprimerAnnale: (id: number) => post<void>(`/admin/annales/${id}/supprimer`, {}),
    beta: {
      codes: () => requete<CodeBeta[]>('/admin/beta/codes'),
      creerCode: (libelle: string, plafond: number, code?: string) =>
        post<CodeBeta>('/admin/beta/codes', code ? { libelle, plafond, code } : { libelle, plafond }),
      desactiverCode: (id: number) => post<CodeBeta>(`/admin/beta/codes/${id}/desactiver`, {}),
      avis: () => requete<{ avis: AvisBetaLu[]; note_moyenne: number | null }>('/admin/beta/avis'),
      usage: (jours = 14) => requete<UsageBeta>(`/admin/beta/usage?jours=${jours}`),
    },
  },
  donnerAvis: (avis: AvisBeta) => post<{ enregistre: boolean }>('/beta/avis', avis),
  matieres: () => requete<Matiere[]>('/matieres'),
  fraicheur: () => requete<Fraicheur>('/fraicheur'),
  annales: () => requete<{ niveaux: string[]; annales: Annale[] }>('/annales'),
  coursRecuperes: {
    lister: () => requete<{ avertissement: string; cours: CoursRecupere[] }>('/cours-recuperes'),
    lire: (id: string) => requete<CoursRecupereComplet>(`/cours-recuperes/${encodeURIComponent(id)}`),
    // Mots dans le corps, jamais dans l'adresse (journaux du serveur ; D111, D120)
    rechercher: (q: string) => post<{ cours: string[] }>('/cours-recuperes/recherche', { q }),
  },
  chat: (question: string, mode: Mode, matiere: string | null, niveau: Niveau, semestre: number, cours?: OptionsCours) =>
    post<ReponseChat>('/chat', { question, mode, matiere, niveau, semestre, ...optionsCours(cours) }),
  quiz: (theme: string, format: FormatQuiz, nombre: number, matiere: string | null, niveau: Niveau, semestre: number,
    cours?: OptionsCours) =>
    post<Quiz>('/quiz', { theme, format, nombre, matiere, niveau, semestre, ...optionsCours(cours) }),
  cours: {
    lister: () => requete<{ cours: CoursDepose[]; maximum: number; formats: string[] }>('/cours'),
    deposer: (fichier: File, matiere: string, titre: string) => {
      // Nom du fichier et titre en en-tetes, pas dans l'adresse : l'adresse est ecrite dans les journaux
      // de nginx et de Cloudflare, et le nom contient parfois celui de l'etudiant (« Droit civil Dupont.pdf »).
      return requete<CoursDepose>(`/cours?${new URLSearchParams({ matiere })}`, {
        method: 'POST', body: fichier,
        headers: {
          'Content-Type': 'application/octet-stream',
          'X-Lexia-Fichier': encodeURIComponent(fichier.name),
          'X-Lexia-Titre': encodeURIComponent(titre),
        },
      })
    },
    /** Meme envoi, avec la progression de l'envoi du fichier (fetch ne la donne pas) : 0 a 1, puis la lecture. */
    deposerAvecProgres: (fichier: File, matiere: string, titre: string, progres: (part: number) => void) =>
      envoyerAvecProgres<CoursDepose>(`/cours?${new URLSearchParams({ matiere })}`, fichier, {
        'X-Lexia-Fichier': encodeURIComponent(fichier.name),
        'X-Lexia-Titre': encodeURIComponent(titre),
      }, progres),
    apercu: (id: number) => requete<ApercuCours>(`/cours/${id}/apercu`),
    modifier: (id: number, changement: { titre?: string; matiere?: string }) =>
      post<CoursDepose>(`/cours/${id}/modifier`, changement),
    supprimer: (id: number) => post<void>(`/cours/${id}/supprimer`, {}),
  },
  corriger: (quiz_id: string, reponses: { index: number; valeur: number | boolean | string | null }[]) =>
    post<Correction>('/quiz/correct', { quiz_id, reponses }),
  resumeVocal: (demande: DemandeResume) => post<ResumeVocal>('/resume-vocal', demande),
  carteMentale: (demande: DemandeCarte) => post<CarteMentale>('/carte-mentale', demande),
  source: (id: string) => requete<SourceComplete>(`/sources/${encodeURIComponent(id)}`),
  vigueur: (id: string) => requete<Vigueur>(`/sources/${encodeURIComponent(id)}/vigueur`),
  feedback: (reponse_id: string, utile: boolean, motif?: string) =>
    post<void>('/feedback', { reponse_id, utile, motif: motif ?? null }),
}
