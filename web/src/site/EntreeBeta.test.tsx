import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
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

// Testeur connecte (formule gratuite), pour les tarifs et « Mon compte » (D135)
const PROFIL = { email: 'etu@exemple.fr', cree_le: '2026-11-11T10:00:00+00:00', formule_fin: null, formule: FORMULES[0],
  usage: { jour: '2026-11-11', questions: 0, quiz: 0 }, admin: false }

let config: Record<string, unknown>
let profil: unknown

beforeEach(() => {
  config = { comptes: true, contact_email: 'contact@exemple.fr', beta_fermee: true, paiement: false }
  profil = null
  localStorage.clear()
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url.endsWith('/auth/session') || url.endsWith('/auth/moi')) return json(profil)
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

  it.each(PAGES)('%s : pas de « Créer un compte », « Demander une invitation » à la place', async (chemin) => {
    await ouvrir(chemin)
    await screen.findByRole('heading', { level: 1 })
    // Seul lien vers l'inscription : celui du testeur qui a deja un code (D135)
    for (const a of liens('/inscription')) expect(a).toHaveTextContent(/^J’ai un code/)
    expect(screen.queryByText(/Créer un compte/)).not.toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /Demander une invitation|Invitation/ }).length).toBeGreaterThan(0)
  })

  it('l’accueil dit que l’accès se fait sur invitation, sous le bouton principal', async () => {
    await ouvrir('/')
    expect(screen.getByText(/Bêta fermée : accès sur invitation/)).toBeInTheDocument()
  })

  // Audit du 2026-11-25, G-1 (D135) : le testeur qui a recu un code ne passe plus par « Demander une invitation »
  it('l’accueil et l’en-tête mènent qui a un code droit au formulaire d’inscription', async () => {
    await ouvrir('/')
    expect(screen.getByRole('link', { name: 'J’ai un code d’accès' })).toHaveAttribute('href', '/inscription')
    const entete = screen.getByRole('navigation', { name: 'Navigation du site' })
    expect(within(entete).getByRole('link', { name: 'J’ai un code' })).toHaveAttribute('href', '/inscription')
  })

  it.each([['?code=', '/inscription?code=ABCDE-FGHJK'], ['#code=', '/inscription#code=ABCDE-FGHJK']])(
    'lien %s : code prérempli, modifiable, retiré de l’adresse', async (_, adresse) => {
      window.history.pushState({}, '', adresse)
      render(<Site />)
      const champ = await screen.findByLabelText('Code d’accès à la bêta')
      expect(champ).toHaveValue('ABCDE-FGHJK')
      expect(window.location.pathname).toBe('/inscription')
      expect(window.location.search + window.location.hash).toBe('')
      fireEvent.change(champ, { target: { value: 'AUTRE-CODE' } })
      expect(champ).toHaveValue('AUTRE-CODE')
    })

  it('inscription sans code dans l’adresse : champ vide', async () => {
    window.history.pushState({}, '', '/inscription')
    render(<Site />)
    expect(await screen.findByLabelText('Code d’accès à la bêta')).toHaveValue('')
  })

  // Audit du 2026-11-25, J2 (D135) : rien n'est vendu pendant la beta, pas plus a un compte qu'a un visiteur
  it.each([[false, false], [true, false], [true, true]])(
    'tarifs, compte connecté (%s), paiement en ligne (%s) : ni demande de formule ni paiement', async (connecte, paiement) => {
      profil = connecte ? PROFIL : null
      config = { ...config, paiement }
      window.history.pushState({}, '', '/tarifs')
      render(<Site />)
      await screen.findByRole('heading', { name: 'Étudiant' })
      await waitFor(() => expect(screen.getAllByText(/Pendant la bêta fermée, Lexia est gratuit/).length).toBe(1))
      if (connecte) {
        await screen.findByText('Non proposée pendant la bêta')
        expect(screen.getByRole('link', { name: 'Votre formule actuelle' })).toHaveAttribute('href', '/app')
      }
      expect(screen.queryByText(/Demander cette formule/)).not.toBeInTheDocument()
      expect(screen.queryByText(/activée à la main/)).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /Payer|Choisir/ })).not.toBeInTheDocument()
      expect(screen.queryAllByRole('link').some((a) => a.getAttribute('href')?.startsWith('mailto:'))).toBe(false)
      expect(screen.queryByText(/arrive bientôt/)).not.toBeInTheDocument()
    })

  it('Mon compte : « Voir les formules » plutôt que « Changer de formule », vers la page qui dit la gratuité', async () => {
    profil = PROFIL
    window.history.pushState({}, '', '/compte')
    render(<Site />)
    await screen.findByRole('heading', { name: 'etu@exemple.fr' })
    await waitFor(() => expect(screen.getByRole('link', { name: 'Voir les formules' })).toHaveAttribute('href', '/tarifs'))
    expect(screen.queryByRole('link', { name: 'Changer de formule' })).not.toBeInTheDocument()
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
    expect(screen.getByRole('link', { name: /J’ai un code : créer mon compte/ })).toHaveAttribute('href', '/inscription')
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
    expect(screen.queryByText(/J’ai un code/)).not.toBeInTheDocument()
  })

  it('tarifs : un compte voit toujours « Demander cette formule » et l’activation à la main', async () => {
    config = { comptes: true, contact_email: 'contact@exemple.fr', beta_fermee: false, paiement: false }
    profil = PROFIL
    window.history.pushState({}, '', '/tarifs')
    render(<Site />)
    const lien = (await screen.findAllByRole('link', { name: 'Demander cette formule' }))[0]
    expect(lien.getAttribute('href')).toMatch(/^mailto:contact@exemple\.fr/)
    expect(lien.nextElementSibling).toHaveTextContent('activée à la main')
    expect(screen.queryByText(/Pendant la bêta fermée/)).not.toBeInTheDocument()
    expect(screen.queryByText('Non proposée pendant la bêta')).not.toBeInTheDocument()
    expect(screen.getByText(/Le paiement en ligne arrive bientôt/)).toBeInTheDocument()
  })

  it('Mon compte garde « Changer de formule »', async () => {
    config = { comptes: true, contact_email: 'contact@exemple.fr', beta_fermee: false, paiement: false }
    profil = PROFIL
    window.history.pushState({}, '', '/compte')
    render(<Site />)
    await screen.findByRole('heading', { name: 'etu@exemple.fr' })
    await waitFor(() => expect(screen.getByRole('link', { name: 'Changer de formule' })).toHaveAttribute('href', '/tarifs'))
  })
})
