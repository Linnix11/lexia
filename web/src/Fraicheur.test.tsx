// Fraicheur des sources affichee dans le site (audit du 2026-11-18, B7).
import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { CarteSources } from './components/Cartes'
import type { Fraicheur } from './lib/api'
import { ancienne, libelleFraicheur, oublierFraicheur, plusRecente, sourcesAnciennes } from './lib/fraicheur'

const FRAICHEUR: Fraicheur = {
  textes: '2026-11-17',
  sources: {
    code_civil: { nom: 'Code civil', date: '2026-11-17', nature: 'textes' },
    judilibre: { nom: 'Cour de cassation : chambres civiles', date: '2026-09-17', nature: 'jurisprudence' },
    cass_criminelle: { nom: 'Cour de cassation : chambre criminelle', date: '2026-09-16', nature: 'jurisprudence' },
    conseil_etat: { nom: 'Conseil d’État', date: '2026-11-10', nature: 'jurisprudence' },
  },
}
const LE_18_NOVEMBRE = new Date('2026-11-18T10:00:00Z')

describe('fraicheur des sources', () => {
  beforeEach(() => {
    oublierFraicheur()
    vi.stubGlobal('fetch', vi.fn((url: string) => Promise.resolve(url.endsWith('/fraicheur')
      ? new Response(JSON.stringify(FRAICHEUR), { status: 200, headers: { 'Content-Type': 'application/json' } })
      : new Response('{}', { status: 404 }))))
  })
  afterEach(() => vi.unstubAllGlobals())

  it('libelles et date la plus recente', () => {
    expect(libelleFraicheur(FRAICHEUR.sources.code_civil)).toBe('version du 17 novembre 2026')
    expect(libelleFraicheur(FRAICHEUR.sources.judilibre)).toBe('décisions jusqu’au 17 septembre 2026')
    expect(plusRecente(FRAICHEUR, ['judilibre', 'cass_criminelle', 'inconnue'])).toBe('2026-09-17')
    expect(plusRecente(null, ['judilibre'])).toBeNull()
  })

  it('une source a jour depuis plus de 30 jours est signalee, une seule fois', () => {
    expect(ancienne('2026-09-17', LE_18_NOVEMBRE)).toBe(true)
    expect(ancienne('2026-11-10', LE_18_NOVEMBRE)).toBe(false)
    const ids = ['judilibre', 'code_civil', 'judilibre', 'conseil_etat', 'cours']
    expect(sourcesAnciennes(FRAICHEUR, ids, LE_18_NOVEMBRE).map((s) => s.nom)).toEqual(['Cour de cassation : chambres civiles'])
    expect(sourcesAnciennes(null, ids, LE_18_NOVEMBRE)).toEqual([])
  })

  it('la carte des sources donne la date de chaque source', async () => {
    render(<CarteSources />)
    expect(await screen.findByText('Version du 17 novembre 2026')).toBeInTheDocument()
    expect(screen.getByText('Décisions jusqu’au 17 septembre 2026')).toBeInTheDocument()
    expect(screen.getByText('Décisions jusqu’au 10 novembre 2026')).toBeInTheDocument()
  })

  it('sans reponse du serveur, la carte reste affichee sans date', async () => {
    oublierFraicheur()
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(new Response('{}', { status: 500 }))))
    render(<CarteSources />)
    expect(await screen.findByText('Cour de cassation')).toBeInTheDocument()
    expect(screen.queryByText(/Décisions jusqu’au/)).toBeNull()
  })
})
