import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { api, ApiError, type CoursDepose, type Matiere, type Mode, type OptionsCours } from '../lib/api'
import { ajouterCartes as ajouter, ecrireCartes, lireCartes, MESSAGE_LIMITE_CARTES, reviser, type Carte } from '../lib/cartes'
import { ecrireFavoris, lireFavoris, MAX_FICHES, MESSAGE_LIMITE_FICHES, type Favori } from '../lib/favoris'
import { ecrireDerniereMatiere, lireDerniereMatiere } from '../lib/personnalisation'
import { ecrireSeance, lireSeance } from '../lib/seance'
import { ecrireSemestre, lireSemestre, niveauDe, type Semestre } from '../lib/semestres'
import { Ctx, type AppState, type EtatQuiz, type Message, type ParametresQuiz, type ValeurQuiz, type Vue } from './contexte'
import { useSession } from './session'

const AUCUN_COURS: CoursDepose[] = []
let compteur = 0
const nouvelId = () => `m${Date.now()}-${compteur++}`
const MESSAGES_GARDES = 30
const QUIZ_VIDE: EtatQuiz = { parametres: null, quiz: null, reponses: {}, correction: null, etat: 'libre', erreur: null }

/** Conversation reprise de la seance : une reponse attendue au moment du rechargement ne reviendra pas. */
function conversationReprise(compte: string): Message[] {
  const liste = lireSeance<Message[]>('conversation', compte)
  if (!Array.isArray(liste)) return []
  return liste.map((m) => (m.etat === 'en_cours'
    ? { ...m, etat: 'erreur', erreur: 'La page a été rechargée avant la réponse : relancez la question.' }
    : m))
}

function quizRepris(compte: string): EtatQuiz {
  const q = lireSeance<EtatQuiz>('quiz', compte)
  if (!q || typeof q !== 'object') return QUIZ_VIDE
  const interrompu = q.etat === 'generation'
  return { ...QUIZ_VIDE, ...q, etat: 'libre', erreur: interrompu ? 'La page a été rechargée pendant la génération : relancez-la.' : null }
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [vue, setVueEtat] = useState<Vue>('espace')
  // Une autre vue s'ouvre en haut de la page, comme une navigation (recette du 2026-11-20, D-3). Fait avant
  // le rendu : la conversation peut ensuite defiler jusqu'a son dernier message.
  const vueActuelle = useRef(vue)
  const setVue = useCallback((v: Vue) => {
    if (v !== vueActuelle.current) window.scrollTo(0, 0)
    vueActuelle.current = v
    setVueEtat(v)
  }, [])
  const { rafraichir, profil } = useSession()
  const compte = profil?.email ?? ''
  const [semestre, setSemestreEtat] = useState<Semestre>(() => lireSemestre(compte))
  const niveau = niveauDe(semestre)
  const setSemestre = useCallback((s: Semestre) => {
    setSemestreEtat(s)
    ecrireSemestre(s, compte)
  }, [compte])
  // Derniere matiere choisie reprise a la visite suivante (D100), gardee dans ce navigateur seulement.
  const [matiereChoisie, setMatiere] = useState<string | null>(() => lireDerniereMatiere(compte))
  const [mode, setMode] = useState<Mode>('expliquer')
  const [coursCharges, setMesCours] = useState<CoursDepose[]>([])
  const [coursMax, setCoursMax] = useState(0)
  const [coursChoisis, setCoursChoisis] = useState<number[]>([])
  const [avecOfficiel, setAvecOfficiel] = useState(true)
  const [matieres, setMatieres] = useState<Matiere[]>([])
  // Matiere retiree depuis (liste des matieres changee) : on repart de « Toutes ».
  const matiere = matiereChoisie && matieres.length && !matieres.some((m) => m.id === matiereChoisie) ? null : matiereChoisie
  useEffect(() => {
    ecrireDerniereMatiere(compte, matiere)
  }, [compte, matiere])
  // Le fournisseur est monte au-dessus des pages (Site.tsx) avec une cle par compte : la conversation et le
  // questionnaire survivent au passage par Compte ou Tarifs (audit du 2026-11-16, points 12 et 16).
  const [messages, setMessages] = useState<Message[]>(() => conversationReprise(compte))
  const [dernierQuiz, setDernierQuiz] = useState<EtatQuiz>(() => quizRepris(compte))
  const [favoris, setFavoris] = useState<Favori[]>(() => lireFavoris(compte))
  const [cartes, setCartes] = useState<Carte[]>(() => lireCartes(compte))
  const [sourceOuverte, setSourceOuverte] = useState<string | null>(null)
  const [quizOuvert, setQuizOuvert] = useState<{ theme?: string; id: number } | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const minuteur = useRef<number | undefined>(undefined)
  const quizVisible = useRef(false)
  useEffect(() => {
    quizVisible.current = quizOuvert !== null
  }, [quizOuvert])

  useEffect(() => {
    if (compte) ecrireSeance('conversation', compte, messages.length ? messages.slice(-MESSAGES_GARDES) : null)
  }, [messages, compte])
  useEffect(() => {
    if (compte) ecrireSeance('quiz', compte, dernierQuiz.quiz || dernierQuiz.parametres ? dernierQuiz : null)
  }, [dernierQuiz, compte])

  const rafraichirCours = useCallback(() => {
    api.cours.lister()
      .then((r) => {
        const liste = Array.isArray(r?.cours) ? r.cours : []
        setMesCours(liste)
        setCoursMax(r?.maximum ?? 0)
        setCoursChoisis((ids) => ids.filter((id) => liste.some((x) => x.id === id)))
      })
      .catch(() => setMesCours([]))
  }, [])

  const connecte = Boolean(profil)
  useEffect(() => {
    if (connecte) rafraichirCours()
  }, [connecte, rafraichirCours])
  const mesCours = connecte ? coursCharges : AUCUN_COURS // deconnecte : rien n'est affiche

  // Un cours en cours de traitement (calcul des embeddings) : la liste se met a jour toute seule.
  const enTraitement = mesCours.some((c) => c.statut === 'traitement')
  useEffect(() => {
    if (!enTraitement) return
    const t = window.setInterval(rafraichirCours, 4000)
    return () => window.clearInterval(t)
  }, [enTraitement, rafraichirCours])

  // Plusieurs cours interrogeables ensemble (audit C8 : un seul partait jusqu'ici).
  const optionsCours = useMemo<OptionsCours | undefined>(
    () => (coursChoisis.length ? { cours: coursChoisis, avec_officiel: avecOfficiel } : undefined),
    [coursChoisis, avecOfficiel],
  )

  const notifier = useCallback((msg: string) => {
    setToast(msg)
    window.clearTimeout(minuteur.current)
    minuteur.current = window.setTimeout(() => setToast(null), 2600)
  }, [])

  useEffect(() => {
    if (!connecte) return // pages publiques : l'espace etudiant n'est pas affiche
    // L'API peut encore etre en train de demarrer (chargement du modele d'embeddings) : quelques essais.
    let actif = true
    let essai = 0
    let minuterie: number | undefined
    const charger = () => {
      api
        .matieres()
        .then((m) => actif && setMatieres(m))
        .catch(() => {
          if (actif && ++essai < 6) minuterie = window.setTimeout(charger, 3000)
        })
    }
    charger()
    return () => {
      actif = false
      window.clearTimeout(minuterie)
    }
  }, [connecte])

  const occupe = messages.some((m) => m.etat === 'en_cours')

  const enregistrerFiche = useCallback(
    (m: Message) => {
      if (!m.reponse) return
      const f: Favori = { id: m.reponse.reponse_id, question: m.question, mode: m.mode, enregistre_le: new Date().toISOString(), reponse: m.reponse }
      setFavoris((liste) => {
        if (liste.some((x) => x.id === f.id)) return liste
        if (liste.length >= MAX_FICHES) {
          notifier(MESSAGE_LIMITE_FICHES)
          return liste
        }
        const suivante = [f, ...liste]
        notifier(ecrireFavoris(suivante, compte) ? 'Fiche enregistrée dans ce navigateur uniquement (« Fiches & révisions »)' : "Le navigateur n'a pas pu enregistrer cette fiche.")
        return suivante
      })
    },
    [notifier, compte],
  )

  // Changer de matiere deselectionne les cours deposes dans une autre matiere (sinon la question sur le droit
  // penal partirait avec un cours de contrats).
  const choisirMatiere = useCallback(
    (id: string | null) => {
      setMatiere(id)
      if (id) setCoursChoisis((ids) => ids.filter((c) => mesCours.find((x) => x.id === c)?.matiere === id))
    },
    [mesCours],
  )

  const envoyer = useCallback(
    (question: string, modeDemande?: Mode) => {
      const q = question.trim()
      if (!q || occupe) return
      const m = modeDemande ?? mode
      setMode(m) // le choix affiche en haut de l'assistant suit la derniere demande
      const id = nouvelId()
      setMessages((ms) => [...ms, { id, question: q, mode: m, etat: 'en_cours' }])
      api
        .chat(q, m, matiere, niveau, semestre, optionsCours)
        .then((reponse) => {
          setMessages((ms) => ms.map((x) => (x.id === id ? { ...x, etat: 'ok', reponse } : x)))
          // Une fiche de revision est enregistree d'office (sans attendre un clic sur « Enregistrer »).
          if (m === 'fiche' && reponse.statut === 'reponse') enregistrerFiche({ id, question: q, mode: m, etat: 'ok', reponse })
        })
        .catch((e: unknown) => {
          const erreur = e instanceof ApiError ? e.message : 'Une erreur est survenue.'
          const statut = e instanceof ApiError ? e.status : undefined
          setMessages((ms) => ms.map((x) => (x.id === id ? { ...x, etat: 'erreur', erreur, statut } : x)))
        })
        .finally(() => void rafraichir())
    },
    [mode, matiere, niveau, semestre, occupe, rafraichir, enregistrerFiche, optionsCours],
  )

  // La generation continue si la fenetre est fermee (clic hors de la fenetre, Echap, changement de page) :
  // le questionnaire attend a sa reouverture (audit du 2026-11-16, point 9).
  const genererQuiz = useCallback(
    (p: ParametresQuiz) => {
      setDernierQuiz({ ...QUIZ_VIDE, parametres: p, etat: 'generation' })
      api
        .quiz(p.theme, p.format, p.nombre, p.matiere, niveau, semestre, optionsCours)
        .then((quiz) => {
          setDernierQuiz((d) => ({ ...d, quiz, etat: 'libre', erreur: quiz.quiz_id ? null : quiz.message }))
          if (quiz.quiz_id && !quizVisible.current) notifier('Votre questionnaire est prêt : rouvrez-le avec « S’entraîner ».')
        })
        .catch((e: unknown) => {
          setDernierQuiz((d) => ({ ...d, etat: 'libre', erreur: e instanceof ApiError ? e.message : 'La génération a échoué.',
            statut: e instanceof ApiError ? e.status : undefined }))
        })
        .finally(() => void rafraichir())
    },
    [niveau, semestre, optionsCours, notifier, rafraichir],
  )

  const repondreQuiz = useCallback((index: number, valeur: ValeurQuiz) => {
    setDernierQuiz((d) => ({ ...d, reponses: { ...d.reponses, [index]: valeur } }))
  }, [])

  const corrigerQuiz = useCallback(() => {
    const { quiz, reponses } = dernierQuiz
    if (!quiz?.quiz_id) return
    setDernierQuiz((d) => ({ ...d, etat: 'correction', erreur: null }))
    const liste = quiz.questions.map((q) => ({ index: q.index, valeur: reponses[q.index] ?? null }))
    api
      .corriger(quiz.quiz_id, liste)
      .then((correction) => setDernierQuiz((d) => ({ ...d, correction, etat: 'libre' })))
      .catch((e: unknown) => {
        setDernierQuiz((d) => ({ ...d, etat: 'libre', erreur: e instanceof ApiError ? e.message : 'La correction a échoué.',
          statut: e instanceof ApiError ? e.status : undefined }))
      })
  }, [dernierQuiz])

  const signalerErreurQuiz = useCallback((erreur: string | null) => setDernierQuiz((d) => ({ ...d, erreur, statut: undefined })), [])

  const basculerFavori = useCallback(
    (m: Message) => {
      if (!m.reponse) return
      const rid = m.reponse.reponse_id
      setFavoris((liste) => {
        const existe = liste.some((f) => f.id === rid)
        if (!existe && liste.length >= MAX_FICHES) {
          notifier(MESSAGE_LIMITE_FICHES)
          return liste
        }
        const suivante = existe
          ? liste.filter((f) => f.id !== rid)
          : [{ id: rid, question: m.question, mode: m.mode, enregistre_le: new Date().toISOString(), reponse: m.reponse! }, ...liste]
        if (!ecrireFavoris(suivante, compte)) notifier("Le navigateur n'a pas pu enregistrer ce favori.")
        else notifier(existe ? 'Retiré des fiches' : 'Enregistrée dans ce navigateur uniquement (« Fiches & révisions »)')
        return suivante
      })
    },
    [notifier, compte],
  )

  const ajouterCartes = useCallback(
    (nouvelles: Carte[]) => {
      const r = ajouter(cartes, nouvelles)
      if (r.ajoutees === 0) {
        notifier(r.refusees ? MESSAGE_LIMITE_CARTES : nouvelles.length ? 'Ces cartes sont déjà dans vos révisions.' : 'Aucune carte à tirer de ce contenu.')
        return
      }
      setCartes(r.liste)
      if (!ecrireCartes(r.liste, compte)) notifier("Le navigateur n'a pas pu enregistrer ces cartes.")
      else notifier(`${r.ajoutees} carte${r.ajoutees > 1 ? 's' : ''} ajoutée${r.ajoutees > 1 ? 's' : ''} aux révisions (« Fiches & révisions »)`
        + (r.refusees ? ` ; ${MESSAGE_LIMITE_CARTES}` : ''))
    },
    [cartes, notifier, compte],
  )

  const enregistrerCartes = useCallback(
    (suivante: Carte[]) => {
      setCartes(suivante)
      if (!ecrireCartes(suivante, compte)) notifier("Le navigateur n'a pas pu enregistrer vos révisions.")
    },
    [notifier, compte],
  )
  const noterCarte = useCallback(
    (id: string, sue: boolean) => enregistrerCartes(cartes.map((c) => (c.id === id ? reviser(c, sue) : c))),
    [cartes, enregistrerCartes],
  )
  const retirerCarte = useCallback((id: string) => enregistrerCartes(cartes.filter((c) => c.id !== id)), [cartes, enregistrerCartes])

  const valeur = useMemo<AppState>(
    () => ({
      vue,
      setVue,
      niveau,
      semestre,
      setSemestre,
      matiere,
      setMatiere: choisirMatiere,
      mode,
      setMode,
      mesCours,
      coursMax,
      rafraichirCours,
      coursChoisis,
      setCoursChoisis,
      avecOfficiel,
      setAvecOfficiel,
      optionsCours,
      matieres,
      messages,
      envoyer,
      effacer: () => setMessages([]),
      occupe,
      favoris,
      basculerFavori,
      estFavori: (rid) => favoris.some((f) => f.id === rid),
      cartes,
      ajouterCartes,
      noterCarte,
      retirerCarte,
      sourceOuverte,
      ouvrirSource: setSourceOuverte,
      quizOuvert,
      ouvrirQuiz: (theme) => setQuizOuvert({ theme, id: Date.now() }),
      fermerQuiz: () => setQuizOuvert(null),
      dernierQuiz,
      genererQuiz,
      repondreQuiz,
      corrigerQuiz,
      signalerErreurQuiz,
      toast,
      notifier,
    }),
    [vue, setVue, niveau, semestre, setSemestre, choisirMatiere, mode, mesCours, coursMax, rafraichirCours, coursChoisis, avecOfficiel, optionsCours, matiere, matieres, messages, envoyer, occupe, favoris, basculerFavori, cartes, ajouterCartes, noterCarte, retirerCarte, sourceOuverte, quizOuvert, toast, notifier, dernierQuiz, genererQuiz, repondreQuiz, corrigerQuiz, signalerErreurQuiz],
  )

  return <Ctx.Provider value={valeur}>{children}</Ctx.Provider>
}
