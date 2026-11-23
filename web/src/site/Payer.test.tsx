import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Site from '../Site'
import { VERSION_CGU } from '../lib/cgu'
import { empreinte } from '../lib/favoris'

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
let profil: Record<string, unknown> = PROFIL
let etats: unknown[] = []
let fetchMock: ReturnType<typeof vi.fn>
const assign = vi.fn()

beforeEach(() => {
  connecte = true
  profil = PROFIL
  etats = [{ dernier: null, retractable: false, retractables: [] }]
  assign.mockReset()
  fetchMock = vi.fn((url: string) => {
    if (url.endsWith('/auth/session')) return json(connecte ? profil : null)
    if (url.endsWith('/config')) return json({ comptes: true, contact_email: 'contact@exemple.fr', paiement: true })
    if (url.endsWith('/formules')) return json(FORMULES)
    if (url.endsWith('/paiement/session')) return json({ url: 'https://checkout.stripe.com/c/pay/cs_test_1' })
    if (url.endsWith('/paiement/etat')) return json(etats.length > 1 ? etats.shift() : etats[0])
    if (url.endsWith('/paiement/retractation')) return json({ retractes: 1 })
    if (url.endsWith('/auth/supprimer')) return Promise.resolve(new Response(null, { status: 204 }))
    return json({}, 404)
  })
  vi.stubGlobal('fetch', fetchMock)
  vi.stubGlobal('location', { ...window.location, assign })
})
afterEach(() => vi.unstubAllGlobals())

describe('Paiement en ligne', () => {
  it('exige l’accès immédiat et l’acceptation des conditions, puis ouvre la page Stripe', async () => {
    window.history.pushState({}, '', '/tarifs')
    render(<Site />)
    const boutons = await screen.findAllByRole('button', { name: 'Payer par carte' })
    expect(boutons[0]).toBeDisabled()
    fireEvent.change(screen.getAllByLabelText('Durée')[0], { target: { value: '3' } })
    expect(screen.getByText('14,97 €')).toBeInTheDocument()
    fireEvent.click(screen.getAllByRole('checkbox')[0])
    expect(boutons[0]).toBeDisabled()   // conditions pas encore acceptees
    fireEvent.click(screen.getAllByRole('checkbox')[1])
    expect(boutons[0]).toBeEnabled()
    fireEvent.click(boutons[0])
    await waitFor(() => expect(assign).toHaveBeenCalledWith('https://checkout.stripe.com/c/pay/cs_test_1'))
    const appel = fetchMock.mock.calls.find(([u]) => String(u).endsWith('/paiement/session'))!
    expect(JSON.parse(appel[1].body)).toEqual({ formule: 'etudiant', mois: 3, execution_immediate: true, cgu_version: VERSION_CGU })
  })

  it('sans compte, invite à en créer un', async () => {
    connecte = false
    window.history.pushState({}, '', '/tarifs')
    render(<Site />)
    expect((await screen.findAllByRole('link', { name: 'Créer un compte pour souscrire' }))[0]).toHaveAttribute('href', '/inscription')
  })

  it('les CGU donnent leur version et le formulaire type de rétractation', async () => {
    // location est remplace par une copie dans beforeEach : on y met le chemin de la page
    vi.stubGlobal('location', { ...window.location, pathname: '/cgu', assign })
    render(<Site />)
    await screen.findByRole('heading', { name: 'Conditions générales d’utilisation et de vente' })
    await screen.findByText(new RegExp(`Dernière mise à jour : ${VERSION_CGU}`))
    expect(await screen.findByLabelText('Modèle de formulaire de rétractation')).toHaveTextContent('Rayez la mention inutile')
  })

  it('reconnaît la perte du droit de rétractation une fois la formule entièrement exécutée (A10)', async () => {
    window.history.pushState({}, '', '/tarifs')
    render(<Site />)
    expect((await screen.findAllByText(/perdre mon droit de rétractation si la formule est entièrement exécutée/))[0]).toBeInTheDocument()
  })

  it('adresse non confirmée : pas de paiement possible (A3)', async () => {
    profil = { ...PROFIL, email_verifie: false }
    window.history.pushState({}, '', '/tarifs')
    render(<Site />)
    expect((await screen.findAllByText(/Confirmez d’abord votre adresse e-mail/))[0]).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Payer par carte' })).toBeNull()
  })

  it('retour arrière depuis Stripe : le bouton redevient utilisable (A3)', async () => {
    window.history.pushState({}, '', '/tarifs')
    render(<Site />)
    const boutons = await screen.findAllByRole('button', { name: 'Payer par carte' })
    fireEvent.click(screen.getAllByRole('checkbox')[0])
    fireEvent.click(screen.getAllByRole('checkbox')[1])
    fireEvent.click(boutons[0])
    await screen.findByRole('button', { name: 'Ouverture du paiement…' })
    fireEvent(window, new Event('pageshow'))
    await waitFor(() => expect(screen.getAllByRole('button', { name: 'Payer par carte' })).toHaveLength(2))
  })
})

describe('Mon compte et paiement', () => {
  const page = (chemin: string, search = '') => vi.stubGlobal('location', { ...window.location, pathname: chemin, search, assign })

  it('retour de Stripe : activation en cours, puis formule active (A3)', async () => {
    etats = [{ dernier: { statut: 'ouvert', formule: 'etudiant', mois: 1, paye_le: null }, retractable: false, retractables: [] },
      { dernier: { statut: 'paye', formule: 'etudiant', mois: 1, paye_le: '2026-11-18T10:00:00+00:00' }, retractable: false, retractables: [] }]
    page('/compte', '?paiement=ok')
    render(<Site />)
    expect(await screen.findByText(/activation de votre formule en cours/)).toBeInTheDocument()
    expect(await screen.findByText(/votre formule est active/, {}, { timeout: 4000 })).toBeInTheDocument()
  })

  it('rétractation en ligne depuis Mon compte : nom, contrat, adresse de l’accusé (A4, D. 221-5)', async () => {
    const achat = { session: 'cs_test_1', formule: 'etudiant', mois: 1, montant_centimes: 499, paye_le: '2026-11-18T10:00:00+00:00' }
    etats = [{ dernier: { statut: 'paye', formule: 'etudiant', mois: 1, paye_le: achat.paye_le }, retractable: true, retractables: [achat] }]
    page('/compte')
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: 'Renoncer au contrat ici' }))
    // Le bouton disparait : le focus va au premier champ, pas sur <body> (recette du 2026-11-20, D-4).
    expect(screen.getByLabelText('Nom et prénom')).toHaveFocus()
    fireEvent.click(screen.getByRole('button', { name: 'Annuler' }))
    expect(screen.getByRole('button', { name: 'Renoncer au contrat ici' })).toHaveFocus()
    fireEvent.click(screen.getByRole('button', { name: 'Renoncer au contrat ici' }))
    expect(screen.getByLabelText(/Formule Étudiant, 1 mois, 4,99 €/)).toBeChecked()
    expect(screen.getByText(/etu@exemple\.fr/, { selector: 'p' })).toBeInTheDocument()
    const confirmer = screen.getByRole('button', { name: 'Confirmer la rétractation' })
    expect(confirmer).toBeDisabled()   // nom et prenom pas encore saisis
    fireEvent.change(screen.getByLabelText('Nom et prénom'), { target: { value: 'Camille Martin' } })
    etats = [{ dernier: { statut: 'a_rembourser', formule: 'etudiant', mois: 1, paye_le: null }, retractable: false, retractables: [] }]
    fireEvent.click(confirmer)
    expect(await screen.findByText(/Rétractation enregistrée/)).toBeInTheDocument()
    const appel = fetchMock.mock.calls.find(([u]) => String(u).endsWith('/paiement/retractation'))!
    expect(appel[1].method).toBe('POST')
    expect(JSON.parse(appel[1].body)).toEqual({ nom: 'Camille Martin', sessions: ['cs_test_1'] })
  })

  it('suppression du compte : fiches du navigateur effacées, paiements gardés dix ans annoncés (A11)', async () => {
    const cle = `lexia.favoris.v2.${empreinte('etu@exemple.fr')}`
    localStorage.setItem(cle, '[]')
    page('/compte')
    render(<Site />)
    expect(await screen.findByText(/conservée dix ans/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Supprimer mon compte…' }))
    fireEvent.change(screen.getByLabelText('Mot de passe pour confirmer'), { target: { value: 'motdepasse' } })
    fireEvent.click(screen.getByRole('button', { name: 'Supprimer définitivement le compte etu@exemple.fr' }))
    await waitFor(() => expect(localStorage.getItem(cle)).toBeNull())
  })
})

