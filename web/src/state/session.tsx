import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, ApiError, quandSessionExpiree, type ChoixInscription, type ConfigPublique, type Profil } from '../lib/api'
import { oublierSeance } from '../lib/seance'

/** Resultat d'une connexion : session ouverte, ou code de l'application a saisir (jeton de l'etape 2). */
export type ResultatConnexion = { ok: true } | { jeton: string }
import { connexionPuisRetour, useRouteur } from '../lib/router'

interface Session {
  /** undefined : chargement ; null : non connecte */
  profil: Profil | null | undefined
  /** Premier chargement en echec apres plusieurs essais (502, reseau) : on ne sait pas si l'etudiant est connecte. */
  indisponible: boolean
  /** Relance le premier chargement apres `indisponible`. */
  reessayer: () => void
  config: ConfigPublique | null
  rafraichir: () => Promise<void>
  connexion: (email: string, mdp: string) => Promise<ResultatConnexion>
  terminerConnexion: (jeton: string, code: string) => Promise<void>
  majProfil: (p: Profil) => void
  inscription: (email: string, mdp: string, cgu: boolean, prenom: string, nom: string, choix: ChoixInscription) => Promise<void>
  deconnexion: () => Promise<void>
  supprimer: (mdp: string, code?: string) => Promise<void>
}

const ESSAIS_SESSION = 4
const PAUSE_SESSION_MS = import.meta.env.MODE === 'test' ? 20 : 3000

const Ctx = createContext<Session | null>(null)

export function SessionProvider({ children }: { children: ReactNode }) {
  const [profil, setProfil] = useState<Profil | null | undefined>(undefined)
  const [config, setConfig] = useState<ConfigPublique | null>(null)
  const [indisponible, setIndisponible] = useState(false)
  const [tentative, setTentative] = useState(0)
  const { naviguer } = useRouteur()

  const rafraichir = useCallback(async () => {
    try {
      setProfil(await api.session())
    } catch (e) {
      // Seul un 401 deconnecte : une erreur passagere (502, reseau) garde le profil (audit du 2026-11-18, D3).
      if (e instanceof ApiError && e.status === 401) setProfil(null)
    }
  }, [])

  // Premier chargement : seul un 401 (ou une reponse null) veut dire « non connecte ». Une erreur passagere
  // (redemarrage du serveur, 502, reseau) est reessayee toutes les 3 s, puis un message s'affiche au lieu de
  // renvoyer l'etudiant vers la connexion (audit du 2026-11-19, WEB-1).
  useEffect(() => {
    let annule = false
    let minuterie: ReturnType<typeof setTimeout> | undefined
    let essais = 0
    const charger = () => {
      api.session().then((p) => {
        if (!annule) setProfil(p)
      }).catch((e) => {
        if (annule) return
        if (e instanceof ApiError && e.status === 401) return setProfil(null)
        essais += 1
        if (essais < ESSAIS_SESSION) minuterie = setTimeout(charger, PAUSE_SESSION_MS)
        else setIndisponible(true)
      })
    }
    charger()
    return () => {
      annule = true
      clearTimeout(minuterie)
    }
  }, [tentative])

  useEffect(() => {
    api.config().then(setConfig).catch(() => setConfig(null))
  }, [])

  useEffect(() => {
    quandSessionExpiree(() => {
      setProfil(null)
      naviguer(connexionPuisRetour('expiree=1'))
    })
    return () => quandSessionExpiree(null)
  }, [naviguer])

  const valeur = useMemo<Session>(() => ({
    profil,
    indisponible: profil === undefined && indisponible,
    reessayer: () => {
      setIndisponible(false)
      setTentative((n) => n + 1)
    },
    config,
    rafraichir,
    connexion: async (email, mdp) => {
      const r = await api.connexion(email, mdp)
      if ('double_authentification_requise' in r) return { jeton: r.jeton }
      setProfil(r)
      return { ok: true }
    },
    terminerConnexion: async (jeton, code) => setProfil(await api.connexionCode(jeton, code)),
    majProfil: setProfil,
    inscription: async (email, mdp, cgu, prenom, nom, choix) => setProfil(await api.inscription(email, mdp, cgu, prenom, nom, choix)),
    deconnexion: async () => {
      await api.deconnexion().catch(() => undefined)
      oublierSeance() // poste partage : la conversation et le questionnaire ne restent pas dans l'onglet
      setProfil(null)
    },
    supprimer: async (mdp, code) => {
      await api.supprimerCompte(mdp, code)
      oublierSeance()
      setProfil(null)
    },
  }), [profil, indisponible, config, rafraichir])

  return <Ctx.Provider value={valeur}>{children}</Ctx.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
/** Session si la page en a une (null hors du fournisseur : composant rendu seul dans un test, page publique). */
export function useSessionFacultative(): Session | null {
  return useContext(Ctx)
}

export function useSession(): Session {
  const v = useContext(Ctx)
  if (!v) throw new Error('useSession doit etre utilise dans <SessionProvider>')
  return v
}
