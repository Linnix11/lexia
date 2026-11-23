// Pages prerendues (D116) sans configuration du serveur, comme a la publication : aucun texte provisoire
// (audit du 2026-11-23, D1 et T15). Meme fonction de rendu que web/scripts/prerendu.mjs.
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { rendre } from '../entree-serveur'
import Site from '../Site'

const PROVISOIRE = [/à compléter/i, /bientôt disponible/i, /arrive bientôt/i, /Demander cette formule/]

describe('pages prerendues', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('fetch pendant le prerendu'))))
  })
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    window.history.replaceState(null, '', '/')
  })

  it.each(['/tarifs', '/'])('%s : ni mention a completer ni formule « bientot disponible »', async (chemin) => {
    window.history.replaceState(null, '', chemin)
    const html = await rendre()
    expect(html).toContain('<h1')
    for (const motif of PROVISOIRE) expect(html, String(motif)).not.toMatch(motif)
    expect(html).toContain('href="/inscription"')
    if (chemin === '/tarifs') expect(html).toContain('Sans engagement.')
  })

  it('accueil apres suppression du compte : premier rendu identique au prerendu, message ensuite (audit du 2026-11-23, D12)', async () => {
    window.history.replaceState(null, '', '/?compte-supprime=1')
    expect(await rendre()).not.toContain('supprimés définitivement')
    render(<Site />)
    expect(await screen.findByText(/Votre compte et ses données ont été supprimés définitivement/)).toBeInTheDocument()
  })
})
