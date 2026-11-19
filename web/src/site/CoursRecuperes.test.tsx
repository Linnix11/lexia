// Page des cours recuperes sous licence libre : un cours factice, aucun cours reel (docs/cours-libres.md).
import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Site from '../Site'
import { AVERTISSEMENT } from './CoursRecuperes'

const PROFIL = { email: 'etu@exemple.fr', cree_le: '2026-11-11T10:00:00+00:00', formule_fin: null, admin: false,
  formule: { id: 'gratuit', nom: 'Gratuit', prix_mensuel_euros: 0, questions_par_jour: 10, quiz_par_jour: 2, description: 'd', avantages: [] },
  usage: { jour: '2026-11-11', questions: 0, quiz: 0 } }
const FACTICE = {
  id: 'cours-factice', titre: 'Cours factice de test', matiere: 'droit_constitutionnel', libelle_matiere: 'Droit constitutionnel',
  auteur: 'Auteur factice', source: 'Site factice', source_url: 'https://exemple.invalid/',
  url_original: 'https://exemple.invalid/cours-factice', historique_url: '', licence: 'etalab-2.0',
  licence_libelle: 'Licence Ouverte 2.0', licence_url: 'https://github.com/etalab/licence-ouverte/blob/master/LO.md',
  mis_a_jour: '2026-01-15', modifications: 'Découpé en sections', sections: 1,
}

const json = (corps: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(corps), { status, headers: { 'Content-Type': 'application/json' } }))

let cours: unknown[] = []

beforeEach(() => {
  cours = []
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url.endsWith('/auth/session')) return json(PROFIL)
    if (url.endsWith('/cours-recuperes')) return json({ avertissement: AVERTISSEMENT, cours })
    if (url.endsWith('/cours-recuperes/cours-factice'))
      return json({ ...FACTICE, avertissement: AVERTISSEMENT, sections: [{ titre: 'I. Première partie', texte: 'Texte factice.' }] })
    return json({}, 404)
  }))
  window.history.pushState({}, '', '/cours-recuperes')
})
afterEach(() => vi.unstubAllGlobals())

describe('Cours récupérés', () => {
  it('avertit en haut de la page et dit qu’aucun cours n’est encore là', async () => {
    render(<Site />)
    expect(await screen.findByText('Aucun cours récupéré pour l’instant', { exact: false })).toBeInTheDocument()
    expect(within(screen.getByRole('note', { name: 'Avertissement' })).getByText(AVERTISSEMENT)).toBeInTheDocument()
  })

  it('range par matière, rappelle l’avertissement et donne l’attribution de chaque cours', async () => {
    cours = [FACTICE]
    render(<Site />)
    const carte = (await screen.findByText('Cours factice de test')).closest('article')!
    expect(screen.getByRole('heading', { name: 'Droit constitutionnel' })).toBeInTheDocument()
    expect(within(carte).getByText(/non rédigé par Lexia/)).toBeInTheDocument()
    expect(within(carte).getByText('Auteur factice')).toBeInTheDocument()
    expect(within(carte).getByRole('link', { name: /Site factice/ })).toHaveAttribute('href', 'https://exemple.invalid/')
    expect(within(carte).getByRole('link', { name: /Licence Ouverte 2.0/ })).toHaveAttribute('href', FACTICE.licence_url)
    expect(within(carte).getByText('15 janvier 2026')).toBeInTheDocument()
    expect(within(carte).getByRole('link', { name: /exemple.invalid\/cours-factice/ })).toHaveAttribute('href', FACTICE.url_original)
    fireEvent.click(within(carte).getByRole('button', { name: 'Lire le cours' }))
    expect(await within(carte).findByText('Texte factice.')).toBeInTheDocument()
  })
})
