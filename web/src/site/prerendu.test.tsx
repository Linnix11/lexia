// Pages prerendues (D116) sans configuration du serveur, comme a la publication : aucun texte provisoire
// (audit du 2026-11-23, D1 et T15). Meme fonction de rendu que web/scripts/prerendu.mjs.
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { rendre } from '../entree-serveur'
import Site from '../Site'
import { CHEMINS_GUIDES, CHEMINS_MATIERES } from './routesPubliques'
import { BETA_FERMEE_PUBLIEE, betaFermee } from './beta'
import { llmsTxt } from './publication'

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
    expect(html).toContain(BETA_FERMEE_PUBLIEE ? 'href="/invitation"' : 'href="/inscription"')
    if (chemin === '/tarifs') expect(html).toContain('Sans engagement.')
  })

  // Beta fermee dans le HTML prerendu (D132) : la configuration du serveur n'existe pas a la compilation, la valeur
  // publiee (beta-publiee.json) decide du premier affichage et de ce que lisent les moteurs.
  it.each(['/', '/tarifs', '/matieres', CHEMINS_MATIERES[0], CHEMINS_GUIDES[0]])(
    '%s : boutons d’entree selon la bêta publiée, sans lien vers l’inscription si elle est fermée', async (chemin) => {
      window.history.replaceState(null, '', chemin)
      const html = await rendre()
      expect(html.includes('href="/inscription"')).toBe(!BETA_FERMEE_PUBLIEE)
      expect(html.includes('href="/invitation"')).toBe(BETA_FERMEE_PUBLIEE)
      expect(html.includes('Créer un compte')).toBe(!BETA_FERMEE_PUBLIEE)
      if (chemin === '/') expect(html.includes('Bêta fermée : accès sur invitation.')).toBe(BETA_FERMEE_PUBLIEE)
    })

  it('premier rendu du navigateur, configuration pas encore lue : mêmes boutons que le prérendu (hydratation)', async () => {
    window.history.replaceState(null, '', '/')
    const html = await rendre()
    render(<Site />)
    const principal = screen.getAllByRole('link').filter((a) => a.getAttribute('href') === (BETA_FERMEE_PUBLIEE ? '/invitation' : '/inscription'))
    expect(principal.length).toBeGreaterThan(0)
    for (const a of principal) expect(html).toContain(`href="${a.getAttribute('href')}"`)
  })

  it('la bêta publiée est fermée tant que le serveur l’est (D121), llms.txt le dit', () => {
    expect(BETA_FERMEE_PUBLIEE).toBe(true)
    expect(llmsTxt()).toContain('bêta fermée')
    expect(llmsTxt()).toContain('https://lexia-axionstudio.cloud/invitation')
  })

  it('la configuration du serveur, une fois lue, l’emporte sur la valeur publiée', () => {
    expect(betaFermee(null)).toBe(BETA_FERMEE_PUBLIEE)
    expect(betaFermee({ comptes: true, contact_email: null, beta_fermee: false })).toBe(false)
    expect(betaFermee({ comptes: true, contact_email: null })).toBe(false)
    expect(betaFermee({ comptes: true, contact_email: null, beta_fermee: true })).toBe(true)
  })

  it('accueil apres suppression du compte : premier rendu identique au prerendu, message ensuite (audit du 2026-11-23, D12)', async () => {
    window.history.replaceState(null, '', '/?compte-supprime=1')
    expect(await rendre()).not.toContain('supprimés définitivement')
    render(<Site />)
    expect(await screen.findByText(/Votre compte et ses données ont été supprimés définitivement/)).toBeInTheDocument()
  })
})
