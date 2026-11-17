import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Site from '../Site'

const FORMULES = [
  { id: 'gratuit', nom: 'Gratuit', prix_mensuel_euros: 0, questions_par_jour: 10, quiz_par_jour: 2, description: 'd', avantages: ['a'] },
  { id: 'etudiant', nom: 'Étudiant', prix_mensuel_euros: 4.99, questions_par_jour: 100, quiz_par_jour: 20, description: 'd', avantages: ['b'] },
  { id: 'intensif', nom: 'Intensif', prix_mensuel_euros: 9.99, questions_par_jour: 300, quiz_par_jour: 100, description: 'd', avantages: ['c'] },
]
const PROFIL = { email: 'etu@exemple.fr', cree_le: '2026-11-11T10:00:00+00:00', formule_fin: null, formule: FORMULES[0],
  usage: { jour: '2026-11-11', questions: 0, quiz: 0 }, admin: false }

const json = (corps: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(corps), { status, headers: { 'Content-Type': 'application/json' } }))

let connecte = true
let fetchMock: ReturnType<typeof vi.fn>
const assign = vi.fn()

beforeEach(() => {
  connecte = true
  assign.mockReset()
  fetchMock = vi.fn((url: string) => {
    if (url.endsWith('/auth/session')) return json(connecte ? PROFIL : null)
    if (url.endsWith('/config')) return json({ comptes: true, contact_email: 'contact@exemple.fr', paiement: true })
    if (url.endsWith('/formules')) return json(FORMULES)
    if (url.endsWith('/paiement/session')) return json({ url: 'https://checkout.stripe.com/c/pay/cs_test_1' })
    return json({}, 404)
  })
  vi.stubGlobal('fetch', fetchMock)
  vi.stubGlobal('location', { ...window.location, assign })
})
afterEach(() => vi.unstubAllGlobals())

describe('Paiement en ligne', () => {
  it('exige la demande d’accès immédiat, puis ouvre la page Stripe', async () => {
    window.history.pushState({}, '', '/tarifs')
    render(<Site />)
    const boutons = await screen.findAllByRole('button', { name: 'Payer par carte' })
    expect(boutons[0]).toBeDisabled()
    fireEvent.change(screen.getAllByLabelText('Durée')[0], { target: { value: '3' } })
    expect(screen.getByText('14,97 €')).toBeInTheDocument()
    fireEvent.click(screen.getAllByRole('checkbox')[0])
    expect(boutons[0]).toBeEnabled()
    fireEvent.click(boutons[0])
    await waitFor(() => expect(assign).toHaveBeenCalledWith('https://checkout.stripe.com/c/pay/cs_test_1'))
    const appel = fetchMock.mock.calls.find(([u]) => String(u).endsWith('/paiement/session'))!
    expect(JSON.parse(appel[1].body)).toEqual({ formule: 'etudiant', mois: 3, execution_immediate: true })
  })

  it('sans compte, invite à en créer un', async () => {
    connecte = false
    window.history.pushState({}, '', '/tarifs')
    render(<Site />)
    expect((await screen.findAllByRole('link', { name: 'Créer un compte pour souscrire' }))[0]).toHaveAttribute('href', '/inscription')
  })
})
