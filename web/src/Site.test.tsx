import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Site from './Site'

const FORMULES = [
  { id: 'gratuit', nom: 'Gratuit', prix_mensuel_euros: 0, questions_par_jour: 10, quiz_par_jour: 2, description: 'd', avantages: ['10 questions par jour'] },
  { id: 'etudiant', nom: 'Étudiant', prix_mensuel_euros: 4.99, questions_par_jour: 100, quiz_par_jour: 20, description: 'd', avantages: ['100 questions par jour'] },
  { id: 'intensif', nom: 'Intensif', prix_mensuel_euros: 9.99, questions_par_jour: 300, quiz_par_jour: 100, description: 'd', avantages: ['300 questions par jour'] },
]
const PROFIL = { email: 'etu@exemple.fr', cree_le: '2026-11-11T10:00:00+00:00', formule_fin: null, formule: FORMULES[0],
  usage: { jour: '2026-11-11', questions: 10, quiz: 0 } }

const json = (corps: unknown, status = 200) =>
  Promise.resolve(new Response(status === 204 ? null : JSON.stringify(corps), { status, headers: { 'Content-Type': 'application/json' } }))

let connecte = false
let fetchMock: ReturnType<typeof vi.fn>

beforeEach(() => {
  connecte = false
  localStorage.clear()
  fetchMock = vi.fn((url: string) => {
    if (url.endsWith('/auth/session') || url.endsWith('/auth/moi')) return connecte ? json(PROFIL) : json(null)
    if (url.endsWith('/auth/inscription')) {
      connecte = true
      return json(PROFIL, 201)
    }
    if (url.endsWith('/config')) return json({ comptes: true, contact_email: 'contact@exemple.fr' })
    if (url.endsWith('/formules')) return json(FORMULES)
    if (url.endsWith('/matieres')) return json([])
    if (url.endsWith('/chat')) return json({ detail: 'Limite du jour atteinte : 10 questions avec la formule Gratuit.' }, 402)
    return json({}, 404)
  })
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => vi.unstubAllGlobals())

const aller = (chemin: string) => window.history.pushState({}, '', chemin)

describe('Site', () => {
  it('redirige vers la connexion si on ouvre le panel sans compte', async () => {
    aller('/app')
    render(<Site />)
    expect(await screen.findByRole('heading', { name: 'Connexion' })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/connexion')
  })

  it('affiche les trois formules et la demande par e-mail', async () => {
    aller('/tarifs')
    render(<Site />)
    expect(await screen.findByRole('heading', { name: 'Étudiant' })).toBeInTheDocument()
    expect(screen.getByText('4,99 €')).toBeInTheDocument()
    const lien = screen.getAllByRole('link', { name: 'Demander cette formule' })[0]
    expect(lien.getAttribute('href')).toMatch(/^mailto:contact@exemple\.fr/)
  })

  it('inscription : validation puis acces au panel', async () => {
    aller('/inscription')
    render(<Site />)
    const email = await screen.findByLabelText('Adresse e-mail')
    fireEvent.change(email, { target: { value: 'etu@exemple.fr' } })
    fireEvent.change(screen.getByLabelText(/^Mot de passe/), { target: { value: 'court' } })
    fireEvent.blur(screen.getByLabelText(/^Mot de passe/))
    expect(screen.getByText('Au moins 10 caractères.')).toBeInTheDocument()
    const creer = screen.getByRole('button', { name: 'Créer mon compte' })
    expect(creer).toBeDisabled()
    fireEvent.change(screen.getByLabelText(/^Mot de passe/), { target: { value: 'motdepasse-solide' } })
    fireEvent.change(screen.getByLabelText('Confirmez le mot de passe'), { target: { value: 'motdepasse-solide' } })
    fireEvent.click(screen.getByRole('checkbox'))
    await act(async () => {
      fireEvent.click(creer)
    })
    await waitFor(() => expect(window.location.pathname).toBe('/app'))
    const appel = fetchMock.mock.calls.find(([u]) => String(u).endsWith('/auth/inscription'))!
    expect(JSON.parse(String(appel[1].body))).toEqual({ email: 'etu@exemple.fr', mot_de_passe: 'motdepasse-solide', accepte_cgu: true })
  })

  it('limite atteinte : message et lien vers les formules', async () => {
    connecte = true
    aller('/app')
    render(<Site />)
    expect(await screen.findByTitle('Mon compte')).toHaveTextContent(/0\s*question restante/)
    fireEvent.change(await screen.findByLabelText('Votre question'), { target: { value: 'article 1240' } })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Envoyer/ }))
    })
    expect(await screen.findByRole('alert')).toHaveTextContent('Limite du jour atteinte')
    expect(screen.getByRole('link', { name: 'Voir les formules' })).toHaveAttribute('href', '/tarifs')
  })

  it('page inconnue', async () => {
    aller('/nimporte-quoi')
    render(<Site />)
    expect(await screen.findByRole('heading', { name: 'Page introuvable' })).toBeInTheDocument()
  })
})
