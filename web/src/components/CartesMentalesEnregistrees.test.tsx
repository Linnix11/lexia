// « Enregistrer la carte » puis page « Mes cartes mentales » (ouverture, retrait en deux clics).
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { CarteMentale as Carte } from '../lib/api'
import { enregistrerCarteMentale, lireCartesMentales } from '../lib/cartesEnregistrees'
import { SessionProvider } from '../state/session'
import Site from '../Site'
import { CarteMentale } from './CarteMentale'

const CARTE: Carte = {
  titre: 'Usufruit', partiel: false, message: '', restants: 4, avertissement: 'Carte générée automatiquement : vérifiez avec les textes.',
  branches: [{ libelle: 'Droits de l’usufruitier', enfants: [], articles: [] }, { libelle: 'Extinction', enfants: [], articles: [] }],
}
const GRATUIT = { id: 'gratuit', nom: 'Gratuit', prix_mensuel_euros: 0, questions_par_jour: 10, quiz_par_jour: 2, description: 'd', avantages: ['a'] }
const PROFIL = { email: 'etu@exemple.fr', cree_le: '2026-11-11T10:00:00+00:00', formule_fin: null, formule: GRATUIT,
  usage: { jour: '2026-11-11', questions: 0, quiz: 0 }, admin: false, email_verifie: true }
const json = (corps: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(corps), { status, headers: { 'Content-Type': 'application/json' } }))

beforeEach(() => {
  localStorage.clear()
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url.endsWith('/auth/session')) return json(PROFIL)
    if (url.endsWith('/config')) return json({ comptes: true, contact_email: 'contact@exemple.fr' })
    if (url.endsWith('/carte-mentale')) return json(CARTE)
    if (url.endsWith('/formules')) return json([GRATUIT])
    if (url.endsWith('/matieres')) return json([])
    return json({}, 404)
  }))
})
afterEach(() => vi.unstubAllGlobals())

describe('Cartes mentales enregistrées', () => {
  it('le bouton « Enregistrer la carte » la garde pour ce compte, une seule fois', async () => {
    render(<SessionProvider><CarteMentale demande={() => ({ type: 'cours', id: '7' })} /></SessionProvider>)
    fireEvent.click(screen.getByRole('button', { name: 'Carte mentale' }))
    const enregistrer = await screen.findByRole('button', { name: 'Enregistrer la carte' })
    fireEvent.click(enregistrer)
    expect(screen.getByText(/Carte enregistrée dans « Mes cartes mentales »/)).toBeInTheDocument()
    expect(lireCartesMentales('etu@exemple.fr').map((c) => c.titre)).toEqual(['Usufruit'])
    fireEvent.click(enregistrer)
    expect(screen.getByText(/déjà dans « Mes cartes mentales »/)).toBeInTheDocument()
    expect(lireCartesMentales('etu@exemple.fr')).toHaveLength(1)
  })

  it('la page « Mes cartes mentales » ouvre et retire une carte', async () => {
    enregistrerCarteMentale(CARTE, 'etu@exemple.fr')
    window.history.pushState({}, '', '/app')
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: 'Mes cartes mentales' }))
    fireEvent.click(await screen.findByRole('button', { name: /^Usufruit\s*Enregistrée le/ }))
    expect(await screen.findByRole('region', { name: 'Carte mentale' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Enregistrer la carte' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retirer la carte « Usufruit »' }))
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Confirmer le retrait de « Usufruit »' })) })
    await waitFor(() => expect(screen.getByText('Aucune carte enregistrée pour l’instant.')).toBeInTheDocument())
    expect(lireCartesMentales('etu@exemple.fr')).toEqual([])
  })

  it('cherche parmi les cartes dès qu’il y en a plus de trois (D138)', async () => {
    for (const titre of ['Usufruit', 'Servitudes', 'Possession', 'Fait des choses'])
      enregistrerCarteMentale({ ...CARTE, titre }, 'etu@exemple.fr')
    window.history.pushState({}, '', '/app')
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: 'Mes cartes mentales' }))
    const champ = await screen.findByRole('searchbox', { name: /Rechercher une carte/ })
    fireEvent.change(champ, { target: { value: 'servitude' } })
    expect(screen.getByText('1 carte(s) sur 4')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Servitudes\s*Enregistrée le/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Usufruit\s*Enregistrée le/ })).not.toBeInTheDocument()
    fireEvent.change(champ, { target: { value: 'introuvable' } })
    expect(screen.getByText('Aucune carte ne correspond à « introuvable ».')).toBeInTheDocument()
  })
})
