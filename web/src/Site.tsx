import { Component, lazy, Suspense, useEffect, useRef, type ErrorInfo, type ReactNode } from 'react'
import { Lien, RouteurProvider, suiteSure, useRouteur } from './lib/router'
import { Accueil } from './site/Accueil'
import { Connexion, Inscription } from './site/Auth'
import { PublicLayout, Section, bouton } from './site/Public'
import { Tarifs } from './site/Tarifs'
import { CHEMINS_GUIDES, CHEMINS_MATIERES, TITRES_PUBLICS } from './site/routesPubliques'
import { VerifierEmail } from './site/VerifierEmail'
import { MotDePasseOublie, NouveauMotDePasse } from './site/MotDePasse'
import { SessionProvider, useSession } from './state/session'
import { AppProvider } from './state/AppState'
import { Signet } from './components/Logo'

// Administration chargee a part : seuls les administrateurs la telechargent (audit du 2026-11-18, D11).
const Admin = lazy(() => import('./site/Admin').then((m) => ({ default: m.Admin })))
// Pages legales et espace etudiant charges a part : l'accueil d'un visiteur est plus leger (audit du 2026-11-19,
// WEB-23). L'echec de chargement d'un module (publication pendant la visite) est rattrape par LimiteErreur.
const App = lazy(() => import('./App'))
const Compte = lazy(() => import('./site/Compte').then((m) => ({ default: m.Compte })))
const CoursRecuperes = lazy(() => import('./site/CoursRecuperes').then((m) => ({ default: m.CoursRecuperes })))
const Cgu = lazy(() => import('./site/Legal').then((m) => ({ default: m.Cgu })))
const Confidentialite = lazy(() => import('./site/Legal').then((m) => ({ default: m.Confidentialite })))
const MentionsLegales = lazy(() => import('./site/Legal').then((m) => ({ default: m.MentionsLegales })))
// Pages de contenu (matieres, guides ; D116) : texte charge a part, routes et titres dans un module leger.
const IndexMatieres = lazy(() => import('./site/PagesContenu').then((m) => ({ default: m.IndexMatieres })))
const PageMatiere = lazy(() => import('./site/PagesContenu').then((m) => ({ default: m.PageMatiere })))
const IndexGuides = lazy(() => import('./site/PagesContenu').then((m) => ({ default: m.IndexGuides })))
const PageGuide = lazy(() => import('./site/PagesContenu').then((m) => ({ default: m.PageGuide })))

const PUBLIQUES: Record<string, () => ReactNode> = {
  '/': () => <Accueil />,
  '/tarifs': () => <Tarifs />,
  '/mentions-legales': () => <MentionsLegales />,
  '/cgu': () => <Cgu />,
  '/confidentialite': () => <Confidentialite />,
  '/verifier-email': () => <VerifierEmail />,
  '/mot-de-passe-oublie': () => <MotDePasseOublie />,
  '/nouveau-mot-de-passe': () => <NouveauMotDePasse />,
  '/matieres': () => <IndexMatieres />,
  '/guides': () => <IndexGuides />,
  ...Object.fromEntries(CHEMINS_MATIERES.map((c) => [c, () => <PageMatiere slug={c.slice('/matieres/'.length)} />])),
  ...Object.fromEntries(CHEMINS_GUIDES.map((c) => [c, () => <PageGuide slug={c.slice('/guides/'.length)} />])),
}
const INVITES: Record<string, () => ReactNode> = {
  '/connexion': () => <Connexion />,
  '/inscription': () => <Inscription />,
}
const MEMBRES: Record<string, () => ReactNode> = {
  '/app': () => <App />,
  '/compte': () => <Compte />,
  '/cours-recuperes': () => <CoursRecuperes />,
}

/** Titre de l'onglet par page (WCAG 2.4.2, audit du 2026-11-19, WEB-5). */
const TITRES: Record<string, string> = {
  '/': 'Lexia, assistant d’étude du droit',
  '/tarifs': 'Tarifs',
  '/mentions-legales': 'Mentions légales',
  '/cgu': 'Conditions d’utilisation',
  '/confidentialite': 'Politique de confidentialité',
  '/verifier-email': 'Confirmation de l’adresse',
  '/mot-de-passe-oublie': 'Mot de passe oublié',
  '/nouveau-mot-de-passe': 'Nouveau mot de passe',
  '/connexion': 'Connexion',
  '/inscription': 'Créer un compte',
  '/app': 'Mon espace',
  '/compte': 'Mon compte',
  '/cours-recuperes': 'Fiches pratiques de l’administration',
  '/admin': 'Administration',
  ...TITRES_PUBLICS, // pages referencees : titres ecrits aussi dans le HTML prerendu (D116)
}

function Chargement() {
  const { indisponible, reessayer } = useSession()
  if (indisponible) {
    return (
      <div className="grid min-h-screen place-items-center px-4">
        <div role="alert" className="max-w-[380px] text-center">
          <Signet hauteur={44} />
          <p className="mt-4 text-[15px] text-ink">Lexia redémarre, réessayez dans un instant.</p>
          <p className="mt-1 text-[13px] text-muted">Vous n’avez pas été déconnecté.</p>
          <button type="button" onClick={reessayer} className={`${bouton} mt-5 min-h-11`}>Réessayer</button>
        </div>
      </div>
    )
  }
  return (
    <div className="grid min-h-screen place-items-center" role="status" aria-label="Chargement">
      <Signet hauteur={44} className="animate-pulse" />
    </div>
  )
}

/** Limite d'erreur : une erreur de rendu ou un module introuvable (onglet ouvert pendant une publication)
 *  affiche « Recharger » au lieu d'une page blanche (audit du 2026-11-19, WEB-2). */
class LimiteErreur extends Component<{ children: ReactNode; cle: string }, { erreur: boolean; cle: string }> {
  state = { erreur: false, cle: this.props.cle }
  static getDerivedStateFromError() {
    return { erreur: true }
  }
  // Changer de page efface l'erreur : la page suivante a sa chance
  static getDerivedStateFromProps(props: { cle: string }, state: { cle: string }) {
    return props.cle !== state.cle ? { erreur: false, cle: props.cle } : null
  }
  componentDidCatch(e: Error, _info: ErrorInfo) {
    // Module de code introuvable apres une publication : un rechargement unique suffit.
    const module = /dynamically imported module|Importing a module script failed/i.test(String(e?.message))
    try {
      if (module && !sessionStorage.getItem('lexia-recharge')) {
        sessionStorage.setItem('lexia-recharge', '1')
        window.location.reload()
      }
    } catch {
      /* stockage indisponible : l'ecran « Recharger » suffit */
    }
  }
  render() {
    if (!this.state.erreur) return this.props.children
    return (
      <div className="grid min-h-screen place-items-center px-4">
        <div role="alert" className="max-w-[380px] text-center">
          <Signet hauteur={44} />
          <h1 className="mt-4 font-display text-[24px] font-normal">Cette page n’a pas pu s’afficher</h1>
          <p className="mt-1 text-[13px] text-muted">Lexia a peut-être été mis à jour pendant votre visite. Rechargez la page.</p>
          <button type="button" onClick={() => window.location.reload()} className={`${bouton} mt-5 min-h-11`}>Recharger</button>
        </div>
      </div>
    )
  }
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

/** Titre de l'onglet, et focus sur le titre de la page apres une navigation interne (WEB-5). */
function useTitreEtFocus(route: string) {
  const premier = useRef(true)
  useEffect(() => {
    document.title = route === '/' ? TITRES['/'] : `${TITRES[route] ?? 'Page introuvable'} · Lexia`
    if (premier.current) {
      premier.current = false
      return
    }
    const minuterie = setTimeout(() => {
      const cible = document.querySelector<HTMLElement>('main h1, h1') ?? document.querySelector<HTMLElement>('main')
      if (!cible) return
      if (!cible.hasAttribute('tabindex')) cible.setAttribute('tabindex', '-1')
      cible.focus({ preventScroll: true })
    }, 0)
    return () => clearTimeout(minuterie)
  }, [route])
}

function Routes() {
  const { chemin } = useRouteur()
  const { profil } = useSession()
  const route = chemin.replace(/\/+$/, '') || '/'
  useTitreEtFocus(route)
  // Page demandee avant la connexion (retour de Stripe sur /compte?paiement=ok, par exemple ; WEB-11)
  const versConnexion = `/connexion?suite=${encodeURIComponent(route + window.location.search)}`

  if (PUBLIQUES[route]) return <>{PUBLIQUES[route]()}</>
  if (INVITES[route]) {
    if (profil === undefined) return <Chargement />
    return profil ? <Redirection vers={suiteSure(new URLSearchParams(window.location.search).get('suite'))} /> : <>{INVITES[route]()}</>
  }
  if (route === '/admin') {
    if (profil === undefined) return <Chargement />
    if (!profil) return <Redirection vers={versConnexion} />
    return profil.admin ? <Suspense fallback={<Chargement />}><Admin /></Suspense> : <Introuvable />
  }
  if (MEMBRES[route]) {
    if (profil === undefined) return <Chargement />
    return profil ? <>{MEMBRES[route]()}</> : <Redirection vers={versConnexion} />
  }
  return <Introuvable />
}

function RoutesProtegees() {
  const { chemin } = useRouteur()
  return (
    <LimiteErreur cle={chemin}>
      <Suspense fallback={<Chargement />}>
        <Routes />
      </Suspense>
    </LimiteErreur>
  )
}

/** Espace etudiant monte au-dessus des pages, une instance par compte : passer par Compte ou Tarifs
 * ne perd ni la conversation, ni le questionnaire, ni la vue ouverte (audit du 2026-11-16, point 16). */
function EspaceEtudiant({ children }: { children: ReactNode }) {
  const { profil } = useSession()
  return <AppProvider key={profil?.email ?? ''}>{children}</AppProvider>
}

export default function Site() {
  return (
    <RouteurProvider>
      <SessionProvider>
        <EspaceEtudiant>
          <RoutesProtegees />
        </EspaceEtudiant>
      </SessionProvider>
    </RouteurProvider>
  )
}
