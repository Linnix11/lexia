import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Site from '../Site'
import { CHEMINS_GUIDES, CHEMINS_MATIERES } from './routesPubliques'

// Beta fermee annoncee sur les pages publiques (D129) : tant que /api/config renvoie beta_fermee, aucune page ne
// propose de creer un compte (l'inscription exige un code) ; « Demander une invitation » mene a /invitation.

const FORMULES = [
  { id: 'gratuit', nom: 'Gratuit', prix_mensuel_euros: 0, questions_par_jour: 10, quiz_par_jour: 2, description: 'd', avantages: ['a'] },
  { id: 'etudiant', nom: 'Étudiant', prix_mensuel_euros: 4.99, questions_par_jour: 100, quiz_par_jour: 20, description: 'd', avantages: ['b'] },
]

const json = (corps: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(corps), { status, headers: { 'Content-Type': 'application/json' } }))

let config: Record<string, unknown>

beforeEach(() => {
  config = { comptes: true, contact_email: 'contact@exemple.fr', beta_fermee: true, paiement: false }
  localStorage.clear()
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url.endsWith('/auth/session')) return json(null)
    if (url.endsWith('/config')) return json(config)
    if (url.endsWith('/formules')) return json(FORMULES)
    return json({}, 404)
  }))
})
afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

const liens = (href: string) => screen.queryAllByRole('link').filter((a) => a.getAttribute('href') === href)

async function ouvrir(chemin: string) {
  window.history.pushState({}, '', chemin)
  render(<Site />)
  // La configuration est lue apres le premier rendu : on attend qu'elle soit appliquee (lien d'invitation affiche)
  await waitFor(() => expect(liens('/invitation').length).toBeGreaterThan(0))
}

describe('bêta fermée annoncée sur les pages publiques', () => {
  const PAGES = ['/', '/tarifs', '/matieres', CHEMINS_MATIERES[0], CHEMINS_GUIDES[0], '/connexion']

  it.each(PAGES)('%s : aucun lien vers l’inscription, « Demander une invitation » à la place', async (chemin) => {
    await ouvrir(chemin)
    await screen.findByRole('heading', { level: 1 })
    expect(liens('/inscription')).toEqual([])
    expect(screen.queryByText(/Créer un compte/)).not.toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /Demander une invitation|Invitation/ }).length).toBeGreaterThan(0)
  })

  it('l’accueil dit que l’accès se fait sur invitation, sous le bouton principal', async () => {
    await ouvrir('/')
    expect(screen.getByText(/Bêta fermée : accès sur invitation/)).toBeInTheDocument()
  })

  it('l’inscription propose de demander une invitation à qui n’a pas de code', async () => {
    window.history.pushState({}, '', '/inscription')
    render(<Site />)
    await screen.findByLabelText('Code d’accès à la bêta')
    expect(screen.getByRole('link', { name: /Demandez une invitation/ })).toHaveAttribute('href', '/invitation')
  })

  it('la page d’invitation explique comment l’obtenir et donne l’adresse de contact', async () => {
    window.history.pushState({}, '', '/invitation')
    render(<Site />)
    expect(await screen.findByRole('heading', { level: 1, name: /bêta fermée/i })).toBeInTheDocument()
    const contact = await screen.findByRole('link', { name: 'contact@exemple.fr' })
    expect(contact.getAttribute('href')).toMatch(/^mailto:contact@exemple\.fr\?subject=/)
    // Qui a deja un code peut creer son compte
    expect(screen.getByRole('link', { name: /J’ai un code/ })).toHaveAttribute('href', '/inscription')
    expect(document.title).toBe('Demander une invitation · Lexia')
  })

  it('sans adresse de contact configurée, un encart « à compléter » pour l’éditeur', async () => {
    config = { ...config, contact_email: null }
    window.history.pushState({}, '', '/invitation')
    render(<Site />)
    expect(await screen.findByText(/Adresse de contact pour les invitations : à compléter/)).toBeInTheDocument()
    expect(screen.queryAllByRole('link').some((a) => a.getAttribute('href')?.startsWith('mailto:'))).toBe(false)
  })
})

describe('bêta ouverte : rien ne change', () => {
  it.each(['/', '/tarifs', CHEMINS_MATIERES[0]])('%s garde « Créer un compte »', async (chemin) => {
    config = { comptes: true, contact_email: 'contact@exemple.fr', beta_fermee: false, paiement: false }
    window.history.pushState({}, '', chemin)
    render(<Site />)
    await waitFor(() => expect(liens('/inscription').length).toBeGreaterThan(1))
    expect(liens('/invitation')).toEqual([])
    expect(screen.queryByText(/Bêta fermée/)).not.toBeInTheDocument()
    const entete = screen.getByRole('navigation', { name: 'Navigation du site' })
    expect(within(entete).getByRole('link', { name: /Créer un compte|S’inscrire/ })).toHaveAttribute('href', '/inscription')
  })
})
