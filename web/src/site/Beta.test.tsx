import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Site from '../Site'

// Beta fermee (D121) : code d'acces a l'inscription, questionnaire « Donner mon avis », onglet Beta de l'administration.

const GRATUIT = { id: 'gratuit', nom: 'Gratuit', prix_mensuel_euros: 0, questions_par_jour: 10, quiz_par_jour: 2, description: 'd', avantages: ['a'] }
const PROFIL = { email: 'etu@exemple.fr', cree_le: '2026-11-11T10:00:00+00:00', formule_fin: null, formule: GRATUIT,
  usage: { jour: '2026-11-11', questions: 0, quiz: 0 }, admin: false, email_verifie: true }
const USAGE = {
  jours: 14, appels: 4, taux_erreur: 0.25,
  par_jour: [{ jour: '2026-11-23', questions: 3, total: 4 }],
  fonctions: [{ fonction: 'question', libelle: 'Question', appels: 3, erreurs: 0, refus: 0, taux_erreur: 0, mesures: 3, mediane_ms: 8000, p90_ms: 12000 },
    { fonction: 'carte_mentale', libelle: 'Carte mentale', appels: 1, erreurs: 1, refus: 0, taux_erreur: 1, mesures: 0, mediane_ms: null, p90_ms: null }],
  etapes: [{ etape: 'generation', mesures: 3, mediane_ms: 6000, p90_ms: 9000 }],
}

const json = (corps: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(corps), { status, headers: { 'Content-Type': 'application/json' } }))

let profil: Record<string, unknown> | null = null
let fetchMock: ReturnType<typeof vi.fn>

beforeEach(() => {
  profil = null
  localStorage.clear()
  fetchMock = vi.fn((url: string) => {
    if (url.endsWith('/auth/session')) return json(profil)
    if (url.endsWith('/config')) return json({ comptes: true, contact_email: 'contact@exemple.fr', beta_fermee: true })
    if (url.endsWith('/formules')) return json([GRATUIT])
    if (url.endsWith('/matieres')) return json([])
    if (url.endsWith('/auth/inscription')) {
      profil = { ...PROFIL, beta: true }
      return json(profil, 201)
    }
    if (url === '/api/beta/avis') return json({ enregistre: true }, 201)
    if (url.endsWith('/admin/beta/codes') && !url.includes('desactiver')) return json([])
    if (url.includes('/admin/beta/avis')) return json({ avis: [{ id: 1, jour: '2026-11-23', note: 4, aide: 'Les fiches', manque: '', erreur: '', lien: '' }], note_moyenne: 4 })
    if (url.includes('/admin/beta/usage')) return json(USAGE)
    if (url.includes('/admin/')) return json({}, 404)
    return json({}, 404)
  })
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => vi.unstubAllGlobals())

const corps = (fin: string) => JSON.parse(String(fetchMock.mock.calls.find(([u]) => String(u).endsWith(fin))![1].body))

describe('Bêta fermée', () => {
  it('l’inscription exige le code d’accès et l’envoie au serveur', async () => {
    window.history.pushState({}, '', '/inscription')
    render(<Site />)
    const code = await screen.findByLabelText('Code d’accès à la bêta')
    fireEvent.change(screen.getByLabelText(/^Prénom/), { target: { value: 'Léa' } })
    fireEvent.change(screen.getByLabelText(/^Nom/), { target: { value: 'Martin' } })
    fireEvent.change(screen.getByLabelText('Adresse e-mail'), { target: { value: 'etu@exemple.fr' } })
    fireEvent.change(screen.getByLabelText(/^Mot de passe/), { target: { value: 'motdepasse-solide' } })
    fireEvent.change(screen.getByLabelText('Confirmez le mot de passe'), { target: { value: 'motdepasse-solide' } })
    fireEvent.click(screen.getByRole('checkbox', { name: 'J’ai 15 ans ou plus.' }))
    fireEvent.click(screen.getByRole('checkbox', { name: /J’accepte les conditions/ }))
    const creer = screen.getByRole('button', { name: 'Créer mon compte' })
    fireEvent.click(creer)   // code vide : rien n'est envoye
    expect(screen.getByText('Saisissez le code d’accès reçu pour la bêta.')).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([u]) => String(u).endsWith('/auth/inscription'))).toBe(false)
    fireEvent.change(code, { target: { value: ' abcde-fghjk ' } })
    await act(async () => { fireEvent.click(creer) })
    await waitFor(() => expect(window.location.pathname).toBe('/app'))
    expect(corps('/auth/inscription').code_beta).toBe('abcde-fghjk')
  })

  it('un compte bêta donne son avis depuis l’en-tête', async () => {
    profil = { ...PROFIL, beta: true }
    window.history.pushState({}, '', '/app')
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: 'Donner mon avis' }))
    const envoyer = screen.getByRole('button', { name: 'Envoyer mon avis' })
    fireEvent.click(envoyer)   // pas de note : refuse sans appel
    expect(screen.getByRole('alert')).toHaveTextContent('Choisissez une note de 1 à 5.')
    fireEvent.click(screen.getByRole('radio', { name: /4 · Utile/ }))
    fireEvent.change(screen.getByLabelText('Ce qui vous a aidé'), { target: { value: 'Les fiches' } })
    fireEvent.change(screen.getByLabelText(/^Lien de la source/), { target: { value: 'https://www.legifrance.gouv.fr/x' } })
    await act(async () => { fireEvent.click(envoyer) })
    expect(await screen.findByText(/votre avis est enregistré/)).toBeInTheDocument()
    expect(corps('/beta/avis')).toEqual({ note: 4, aide: 'Les fiches', manque: '', erreur: '', lien: 'https://www.legifrance.gouv.fr/x' })
  })

  it('le champ code apparaît quand le serveur l’exige, même si la configuration n’a pas pu se charger', async () => {
    const normal = fetchMock.getMockImplementation() as (url: string, init?: RequestInit) => Promise<Response>
    fetchMock.mockImplementation((url: string, init?: RequestInit) => {
      if (url.endsWith('/config')) return json({}, 503)
      if (url.endsWith('/auth/inscription'))
        return json({ detail: 'Lexia est en bêta fermée : saisissez le code d’accès que vous avez reçu.' }, 403)
      return normal(url, init)
    })
    window.history.pushState({}, '', '/inscription')
    render(<Site />)
    fireEvent.change(await screen.findByLabelText(/^Prénom/), { target: { value: 'Léa' } })
    fireEvent.change(screen.getByLabelText(/^Nom/), { target: { value: 'Martin' } })
    fireEvent.change(screen.getByLabelText('Adresse e-mail'), { target: { value: 'etu@exemple.fr' } })
    fireEvent.change(screen.getByLabelText(/^Mot de passe/), { target: { value: 'motdepasse-solide' } })
    fireEvent.change(screen.getByLabelText('Confirmez le mot de passe'), { target: { value: 'motdepasse-solide' } })
    fireEvent.click(screen.getByRole('checkbox', { name: 'J’ai 15 ans ou plus.' }))
    fireEvent.click(screen.getByRole('checkbox', { name: /J’accepte les conditions/ }))
    expect(screen.queryByLabelText('Code d’accès à la bêta')).not.toBeInTheDocument()
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Créer mon compte' })) })
    expect(await screen.findByLabelText(/^Code d’accès à la bêta/)).toBeInTheDocument()
  })

  it('le bouton n’apparaît pas pour un compte hors bêta', async () => {
    profil = { ...PROFIL, beta: false }
    window.history.pushState({}, '', '/app')
    render(<Site />)
    await screen.findAllByRole('link', { name: 'Mon compte' })
    expect(screen.queryByRole('button', { name: 'Donner mon avis' })).not.toBeInTheDocument()
  })

  it('l’administration crée un code, affiche le suivi d’usage et les avis', async () => {
    profil = { ...PROFIL, email: 'chef@exemple.fr', admin: true, double_authentification: true }
    const normal = fetchMock.getMockImplementation() as (url: string, init?: RequestInit) => Promise<Response>
    fetchMock.mockImplementation((url: string, init?: RequestInit) => {
      if (url.endsWith('/admin/beta/codes') && init?.method === 'POST')
        return json({ id: 1, libelle: 'L1 TD 3', plafond: 15, inscriptions: 0, comptes: 0, actif: true, cree_le: '2026-11-23T10:00:00+00:00', code: 'ABCDE-FGHJK' }, 201)
      return normal(url, init)
    })
    window.history.pushState({}, '', '/admin')
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: 'Bêta' }))
    fireEvent.change(await screen.findByLabelText('Nom du groupe'), { target: { value: 'L1 TD 3' } })
    fireEvent.change(screen.getByLabelText('Places'), { target: { value: '15' } })
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Créer un code' })) })
    expect(await screen.findByText('ABCDE-FGHJK')).toBeInTheDocument()
    const creation = fetchMock.mock.calls.find(([u, i]) => String(u).endsWith('/admin/beta/codes') && i?.method === 'POST')!
    expect(JSON.parse(String(creation[1].body))).toEqual({ libelle: 'L1 TD 3', plafond: 15 })
    // Code personnalise : envoye tel que saisi, en majuscules
    fireEvent.click(screen.getByRole('radio', { name: 'Personnalisé' }))
    fireEvent.change(screen.getByLabelText('Nom du groupe'), { target: { value: 'Assas' } })
    fireEvent.change(screen.getByLabelText(/Code choisi/), { target: { value: 'assas-l1-2026' } })
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Créer un code' })) })
    const perso = fetchMock.mock.calls.filter(([u, i]) => String(u).endsWith('/admin/beta/codes') && i?.method === 'POST').at(-1)!
    expect(JSON.parse(String(perso[1].body))).toEqual({ libelle: 'Assas', plafond: 15, code: 'ASSAS-L1-2026' })
    expect(await screen.findByText('Carte mentale')).toBeInTheDocument()
    expect(screen.getByText('Rédaction par le modèle')).toBeInTheDocument()
    expect(screen.getByText('Les fiches')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Exporter en CSV' })).toHaveAttribute('href', '/api/admin/beta/avis.csv')
  })
})
