import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Site from '../Site'

const json = (corps: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(corps), { status, headers: { 'Content-Type': 'application/json' } }))

let paiement = true

beforeEach(() => {
  paiement = true
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url.endsWith('/auth/session')) return json(null)
    if (url.endsWith('/config')) return json({ comptes: true, contact_email: 'contact@exemple.fr', paiement,
      legal: { editeur: 'Éditeur', adresse: '1 rue du Droit, Paris', gemini_payant: false, groq: false } })
    return json({}, 404)
  }))
})
afterEach(() => vi.unstubAllGlobals())

describe('Conditions générales', () => {
  it('décrivent la rétractation en ligne quand le paiement est actif', async () => {
    window.history.pushState({}, '', '/cgu')
    render(<Site />)
    expect(await screen.findByText(/« Renoncer au contrat ici »/)).toBeInTheDocument()
    expect(screen.getByText(/« Confirmer la rétractation »/)).toBeInTheDocument()
  })

  it('sans paiement en ligne, pas de bouton de rétractation annoncé', async () => {
    paiement = false
    window.history.pushState({}, '', '/cgu')
    render(<Site />)
    await screen.findByText(/Aucun paiement n’est encaissé sur le site/)
    expect(screen.queryByText(/« Renoncer au contrat ici »/)).not.toBeInTheDocument()
  })

  it('donnent un lien de signalement de contenu illicite pré-rempli (DSA, art. 16)', async () => {
    window.history.pushState({}, '', '/cgu')
    render(<Site />)
    const lien = await screen.findByRole('link', { name: 'signaler un contenu illicite' })
    const href = lien.getAttribute('href')!
    expect(href.startsWith('mailto:contact@exemple.fr?subject=Signalement')).toBe(true)
    expect(decodeURIComponent(href)).toContain('de bonne foi')
  })

  it('disent que les passages de cours partent chez Google au niveau gratuit', async () => {
    window.history.pushState({}, '', '/cgu')
    render(<Site />)
    expect(await screen.findByText(/Google peut utiliser ces passages/)).toBeInTheDocument()
  })
})

describe('Politique de confidentialité', () => {
  it('décrit le prénom et le nom, jamais transmis à l IA (D100, D102)', async () => {
    window.history.pushState({}, '', '/confidentialite')
    render(<Site />)
    expect(await screen.findByText(/Le prénom sert à vous saluer dans votre espace ; le nom identifie le titulaire du compte/)).toBeInTheDocument()
    expect(screen.getByText(/Ils ne sont jamais transmis à l’intelligence artificielle/)).toBeInTheDocument()
    expect(screen.getByText(/Prénom et nom : comme le compte, effacés avec lui/)).toBeInTheDocument()
  })
})
