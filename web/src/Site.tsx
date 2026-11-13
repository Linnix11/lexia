import { useEffect, type ReactNode } from 'react'
import App from './App'
import { Admin } from './site/Admin'
import { Lien, RouteurProvider, useRouteur } from './lib/router'
import { Accueil } from './site/Accueil'
import { Connexion, Inscription } from './site/Auth'
import { Compte } from './site/Compte'
import { Cgu, Confidentialite, MentionsLegales } from './site/Legal'
import { PublicLayout, Section, bouton } from './site/Public'
import { Tarifs } from './site/Tarifs'
import { VerifierEmail } from './site/VerifierEmail'
import { SessionProvider, useSession } from './state/session'
import { Signet } from './components/Logo'

const PUBLIQUES: Record<string, () => ReactNode> = {
  '/': () => <Accueil />,
  '/tarifs': () => <Tarifs />,
  '/mentions-legales': () => <MentionsLegales />,
  '/cgu': () => <Cgu />,
  '/confidentialite': () => <Confidentialite />,
  '/verifier-email': () => <VerifierEmail />,
}
const INVITES: Record<string, () => ReactNode> = {
  '/connexion': () => <Connexion />,
  '/inscription': () => <Inscription />,
}
const MEMBRES: Record<string, () => ReactNode> = {
  '/app': () => <App />,
  '/compte': () => <Compte />,
}

function Chargement() {
  return (
    <div className="grid min-h-screen place-items-center" aria-label="Chargement">
      <Signet hauteur={44} className="animate-pulse" />
    </div>
  )
}

function Redirection({ vers }: { vers: string }) {
  const { naviguer } = useRouteur()
  useEffect(() => naviguer(vers, { remplacer: true }), [naviguer, vers])
  return <Chargement />
}

function Introuvable() {
  return (
    <PublicLayout>
      <Section className="py-20 text-center">
        <h1 className="font-display text-[34px] font-normal">Page introuvable</h1>
        <p className="mt-2 text-muted">Cette adresse ne correspond à aucune page de Lexia.</p>
        <Lien href="/" className={`${bouton} mt-6`}>Revenir à l’accueil</Lien>
      </Section>
    </PublicLayout>
  )
}

function Routes() {
  const { chemin } = useRouteur()
  const { profil } = useSession()
  const route = chemin.replace(/\/+$/, '') || '/'

  if (PUBLIQUES[route]) return <>{PUBLIQUES[route]()}</>
  if (INVITES[route]) {
    if (profil === undefined) return <Chargement />
    return profil ? <Redirection vers="/app" /> : <>{INVITES[route]()}</>
  }
  if (route === '/admin') {
    if (profil === undefined) return <Chargement />
    if (!profil) return <Redirection vers="/connexion" />
    return profil.admin ? <Admin /> : <Introuvable />
  }
  if (MEMBRES[route]) {
    if (profil === undefined) return <Chargement />
    return profil ? <>{MEMBRES[route]()}</> : <Redirection vers="/connexion" />
  }
  return <Introuvable />
}

export default function Site() {
  return (
    <RouteurProvider>
      <SessionProvider>
        <Routes />
      </SessionProvider>
    </RouteurProvider>
  )
}
