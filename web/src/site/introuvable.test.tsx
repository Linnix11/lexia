// Vraies 404 et noindex (D134, audit SEO du 24/11) : page introuvable prerendue avec des liens utiles, liste des
// ecrans du front lue par le serveur (api/serveur.py), coquille non indexee, pages prerendues indexables.
import { cleanup, render, screen, within } from '@testing-library/react'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Site, { CHEMINS_APPLICATION } from '../Site'
import { CHEMIN_INTROUVABLE, rendre } from '../entree-serveur'
import { VUES } from '../state/contexte'
import { pageHtml, pageIntrouvableHtml } from './publication'
import { pagesSeo } from './seo'

const GABARIT = readFileSync(join(__dirname, '..', '..', 'index.html'), 'utf8')
const NOINDEX = '<meta name="robots" content="noindex" />'

describe('vraies 404 et noindex (D134)', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('pas de reseau'))))
  })
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    window.history.replaceState(null, '', '/')
  })

  it('page introuvable : liens vers l’accueil, les matières et les guides', async () => {
    window.history.replaceState(null, '', '/a-propos')
    render(<Site />)
    expect(await screen.findByRole('heading', { name: 'Page introuvable' })).toBeInTheDocument()
    const corps = within(screen.getByRole('main'))
    expect(corps.getByRole('link', { name: 'Revenir à l’accueil' })).toHaveAttribute('href', '/')
    expect(corps.getByRole('link', { name: /matières de la licence/ })).toHaveAttribute('href', '/matieres')
    expect(corps.getByRole('link', { name: /Guides de méthode/ })).toHaveAttribute('href', '/guides')
  })

  it('page introuvable prérendue : même contenu sans JavaScript, sans adresse propre dans le routeur', async () => {
    expect(CHEMINS_APPLICATION).not.toContain(CHEMIN_INTROUVABLE)
    window.history.replaceState(null, '', CHEMIN_INTROUVABLE)
    const html = await rendre()
    expect(html).toContain('Page introuvable</h1>')
    for (const href of ['/', '/matieres', '/guides']) expect(html).toContain(`href="${href}"`)
    const page = pageIntrouvableHtml(GABARIT, html)
    expect(page).toContain(NOINDEX)
    expect(page).toContain('<title>Page introuvable · Lexia</title>')
    expect(page).not.toContain('rel="canonical"')
    expect(page).not.toContain('name="description"')
    expect(page).toContain(`<div id="root">${html}</div>`)
  })

  it('liste des écrans lue par le serveur : espace, connexion, invitation, pages publiques', () => {
    for (const chemin of [
      ...VUES.map((v) => v.chemin), ...pagesSeo().map((p) => p.chemin),
      '/connexion', '/inscription', '/invitation', '/compte', '/cours-recuperes', '/admin',
      '/verifier-email', '/mot-de-passe-oublie', '/nouveau-mot-de-passe',
    ]) expect(CHEMINS_APPLICATION, chemin).toContain(chemin)
    for (const chemin of CHEMINS_APPLICATION) expect(chemin === '/' || !chemin.endsWith('/'), chemin).toBe(true)
  })

  it('coquille non indexée, pages prérendues indexables', () => {
    expect(GABARIT).toContain(NOINDEX)
    const tarifs = pagesSeo().find((p) => p.chemin === '/tarifs')!
    const html = pageHtml(GABARIT, tarifs, '<h1>Tarifs</h1>')
    expect(html).not.toContain('name="robots"')
    expect(html).toContain('rel="canonical"')
  })
})
