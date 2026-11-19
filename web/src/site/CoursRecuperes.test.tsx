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
    if (url.includes('/cours-recuperes/recherche?q=')) return json({ cours: ['cours-factice'] })
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

  it('montre une matière à la fois par pages de 20, et cherche un titre dans toutes', async () => {
    const fiche = (i: number, matiere: string, libelle: string) =>
      ({ ...FACTICE, id: `f-${matiere}-${i}`, titre: `${libelle} ${String(i).padStart(2, '0')}`, matiere, libelle_matiere: libelle })
    cours = [...Array.from({ length: 25 }, (_, i) => fiche(i, 'droit_civil', 'Civil')),
      fiche(0, 'droit_penal', 'Pénal')]
    render(<Site />)
    expect(await screen.findByText('Civil 00')).toBeInTheDocument()
    expect(screen.getAllByRole('article')).toHaveLength(20)
    expect(screen.queryByText('Pénal 00')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Afficher 5 de plus' }))
    expect(screen.getAllByRole('article')).toHaveLength(25)
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'penal' } })
    expect(screen.getByText('Pénal 00')).toBeInTheDocument()
    expect(screen.getAllByRole('article')).toHaveLength(1)
  })

  it('ajoute après les titres les cours dont le texte répond à la recherche', async () => {
    cours = [FACTICE]
    render(<Site />)
    await screen.findByText('Cours factice de test')
    fireEvent.change(screen.getByRole('searchbox'), { target: { value: 'juge aux affaires' } })
    expect(await screen.findByText('Cours factice de test', {}, { timeout: 2000 })).toBeInTheDocument()
    expect(screen.queryByText(/Aucun cours ne correspond/)).not.toBeInTheDocument()
  })
})
