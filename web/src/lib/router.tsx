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

/** Lien interne : navigation sans recharger la page (clic du milieu / Ctrl+clic conserves). */
export function Lien({ href, children, ...reste }: AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) {
  const { naviguer } = useRouteur()
  const surClic = (e: MouseEvent<HTMLAnchorElement>) => {
    reste.onClick?.(e)
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return
    if (href.startsWith('#') || /^https?:|^mailto:/.test(href)) return
    e.preventDefault()
    naviguer(href)
  }
  return (
    <a href={href} {...reste} onClick={surClic}>
      {children}
    </a>
  )
}
