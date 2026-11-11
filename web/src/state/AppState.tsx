import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { api, ApiError, type Matiere, type Mode, type Niveau } from '../lib/api'
import { ecrireFavoris, lireFavoris, type Favori } from '../lib/favoris'
import { Ctx, type AppState, type Message, type Vue } from './contexte'
import { useSession } from './session'

let compteur = 0
const nouvelId = () => `m${Date.now()}-${compteur++}`

export function AppProvider({ children }: { children: ReactNode }) {
  const [vue, setVue] = useState<Vue>('espace')
  const [niveau, setNiveau] = useState<Niveau>('L1')
  const [matiere, setMatiere] = useState<string | null>(null)
  const [matieres, setMatieres] = useState<Matiere[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [favoris, setFavoris] = useState<Favori[]>(() => lireFavoris())
  const [sourceOuverte, setSourceOuverte] = useState<string | null>(null)
  const [quizOuvert, setQuizOuvert] = useState<{ theme?: string; id: number } | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const minuteur = useRef<number | undefined>(undefined)
  const { rafraichir } = useSession()

  const notifier = useCallback((msg: string) => {
    setToast(msg)
    window.clearTimeout(minuteur.current)
    minuteur.current = window.setTimeout(() => setToast(null), 2600)
  }, [])

  useEffect(() => {
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
  }, [])

  const occupe = messages.some((m) => m.etat === 'en_cours')

  const envoyer = useCallback(
    (question: string, mode: Mode = 'expliquer') => {
      const q = question.trim()
      if (!q || occupe) return
      const id = nouvelId()
      setMessages((ms) => [...ms, { id, question: q, mode, etat: 'en_cours' }])
      api
        .chat(q, mode, matiere, niveau)
        .then((reponse) => setMessages((ms) => ms.map((m) => (m.id === id ? { ...m, etat: 'ok', reponse } : m))))
        .catch((e: unknown) => {
          const erreur = e instanceof ApiError ? e.message : 'Une erreur est survenue.'
          const statut = e instanceof ApiError ? e.status : undefined
          setMessages((ms) => ms.map((m) => (m.id === id ? { ...m, etat: 'erreur', erreur, statut } : m)))
        })
        .finally(() => void rafraichir())
    },
    [matiere, niveau, occupe, rafraichir],
  )

  const basculerFavori = useCallback(
    (m: Message) => {
      if (!m.reponse) return
      const rid = m.reponse.reponse_id
      setFavoris((liste) => {
        const existe = liste.some((f) => f.id === rid)
        const suivante = existe
          ? liste.filter((f) => f.id !== rid)
          : [{ id: rid, question: m.question, mode: m.mode, enregistre_le: new Date().toISOString(), reponse: m.reponse! }, ...liste]
        if (!ecrireFavoris(suivante)) notifier("Le navigateur n'a pas pu enregistrer ce favori.")
        else notifier(existe ? 'Retiré des fiches' : 'Ajouté à « Fiches & révisions »')
        return suivante
      })
    },
    [notifier],
  )

  const valeur = useMemo<AppState>(
    () => ({
      vue,
      setVue,
      niveau,
      setNiveau,
      matiere,
      setMatiere,
      matieres,
      messages,
      envoyer,
      effacer: () => setMessages([]),
      occupe,
      favoris,
      basculerFavori,
      estFavori: (rid) => favoris.some((f) => f.id === rid),
      sourceOuverte,
      ouvrirSource: setSourceOuverte,
      quizOuvert,
      ouvrirQuiz: (theme) => setQuizOuvert({ theme, id: Date.now() }),
      fermerQuiz: () => setQuizOuvert(null),
      toast,
      notifier,
    }),
    [vue, niveau, matiere, matieres, messages, envoyer, occupe, favoris, basculerFavori, sourceOuverte, quizOuvert, toast, notifier],
  )

  return <Ctx.Provider value={valeur}>{children}</Ctx.Provider>
}
