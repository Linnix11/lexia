import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, quandSessionExpiree, type ConfigPublique, type Profil } from '../lib/api'

/** Resultat d'une connexion : session ouverte, ou code de l'application a saisir (jeton de l'etape 2). */
export type ResultatConnexion = { ok: true } | { jeton: string }
import { useRouteur } from '../lib/router'

interface Session {
  /** undefined : chargement ; null : non connecte */
  profil: Profil | null | undefined
  config: ConfigPublique | null
  rafraichir: () => Promise<void>
  connexion: (email: string, mdp: string) => Promise<ResultatConnexion>
  terminerConnexion: (jeton: string, code: string) => Promise<void>
  majProfil: (p: Profil) => void
  inscription: (email: string, mdp: string, cgu: boolean) => Promise<void>
  deconnexion: () => Promise<void>
  supprimer: (mdp: string) => Promise<void>
}

const Ctx = createContext<Session | null>(null)

export function SessionProvider({ children }: { children: ReactNode }) {
  const [profil, setProfil] = useState<Profil | null | undefined>(undefined)
  const [config, setConfig] = useState<ConfigPublique | null>(null)
  const { naviguer } = useRouteur()

  const rafraichir = useCallback(async () => {
    try {
      setProfil(await api.session())
    } catch {
      setProfil(null)
    }
  }, [])

  useEffect(() => {
    api.session().then(setProfil).catch(() => setProfil(null))
    api.config().then(setConfig).catch(() => setConfig(null))
  }, [])

  useEffect(() => {
    quandSessionExpiree(() => {
      setProfil(null)
      naviguer('/connexion?expiree=1')
    })
    return () => quandSessionExpiree(null)
  }, [naviguer])

  const valeur = useMemo<Session>(() => ({
    profil,
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
    inscription: async (email, mdp, cgu) => setProfil(await api.inscription(email, mdp, cgu)),
    deconnexion: async () => {
      await api.deconnexion().catch(() => undefined)
      setProfil(null)
    },
    supprimer: async (mdp) => {
      await api.supprimerCompte(mdp)
      setProfil(null)
    },
  }), [profil, config, rafraichir])

  return <Ctx.Provider value={valeur}>{children}</Ctx.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useSession(): Session {
  const v = useContext(Ctx)
  if (!v) throw new Error('useSession doit etre utilise dans <SessionProvider>')
  return v
}
