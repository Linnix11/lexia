// Routeur minimal (History API) : suffisant pour une dizaine de pages, sans dependance.
import { createContext, useCallback, useContext, useEffect, useState, type AnchorHTMLAttributes, type MouseEvent, type ReactNode } from 'react'

interface Routeur {
  chemin: string
  naviguer: (chemin: string, options?: { remplacer?: boolean }) => void
}

const Ctx = createContext<Routeur>({ chemin: '/', naviguer: () => undefined })

export function RouteurProvider({ children }: { children: ReactNode }) {
  const [chemin, setChemin] = useState(() => window.location.pathname)

  useEffect(() => {
    const surRetour = () => setChemin(window.location.pathname)
    window.addEventListener('popstate', surRetour)
    return () => window.removeEventListener('popstate', surRetour)
  }, [])

  const naviguer = useCallback((cible: string, options?: { remplacer?: boolean }) => {
    if (cible === window.location.pathname + window.location.search) return
    if (options?.remplacer) window.history.replaceState(null, '', cible)
    else window.history.pushState(null, '', cible)
    setChemin(new URL(cible, window.location.origin).pathname)
    window.scrollTo(0, 0)
  }, [])

  return <Ctx.Provider value={{ chemin, naviguer }}>{children}</Ctx.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useRouteur() {
  return useContext(Ctx)
}

/** Lien interne : navigation sans recharger la page (clic du milieu / Ctrl+clic et target="_blank" conserves). */
export function Lien({ href, children, ...reste }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) {
  const { naviguer } = useRouteur()
  const surClic = (e: MouseEvent<HTMLAnchorElement>) => {
    reste.onClick?.(e)
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return
    if (href.startsWith('#') || /^https?:|^mailto:/.test(href) || (reste.target && reste.target !== '_self')) return
    e.preventDefault()
    naviguer(href)
  }
  return (
    <a href={href} {...reste} onClick={surClic}>
      {children}
    </a>
  )
}

/** Jeton d'un lien recu par e-mail. Il suit « # » pour ne jamais etre envoye au serveur, donc jamais ecrit dans
 *  ses journaux (audit du 2026-11-18, D2). L'ancien format ?jeton= reste lu pour les e-mails deja envoyes : ces
 *  liens expirent en 24 heures au plus, la lecture peut etre retiree apres le 2026-11-25. */
// eslint-disable-next-line react-refresh/only-export-components
export function jetonDuLien(): string {
  return new URLSearchParams(window.location.hash.slice(1)).get('jeton')
    ?? new URLSearchParams(window.location.search).get('jeton') ?? ''
}

/** Adresse de retour apres connexion (`?suite=`) : chemin interne seulement, jamais « //autre-site », « /\\ »
 *  ni « https: » (audit du 2026-11-19, WEB-11). */
// eslint-disable-next-line react-refresh/only-export-components
export function suiteSure(suite: string | null): string {
  return suite && suite.startsWith('/') && !suite.startsWith('//') && !suite.startsWith('/\\') ? suite : '/app'
}

/** Adresse de la connexion qui ramene ensuite a la page courante. */
// eslint-disable-next-line react-refresh/only-export-components
export function connexionPuisRetour(extra = ''): string {
  const ici = window.location.pathname + window.location.search
  const suite = ici.startsWith('/connexion') || ici === '/' ? '' : `suite=${encodeURIComponent(ici)}`
  const q = [extra, suite].filter(Boolean).join('&')
  return q ? `/connexion?${q}` : '/connexion'
}
