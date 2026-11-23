// Carte mentale (D112) : plan demande au serveur, dessin SVG, repli, zoom, version en liste accessible.
import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { CarteMentale as Carte } from '../lib/api'
import { couperLignes, disposer, nomFichier } from '../lib/carteMentale'
import { CarteMentale } from './CarteMentale'

const CARTE: Carte = {
  titre: 'Responsabilité du fait personnel',
  branches: [
    { libelle: 'Fondement', enfants: [{ libelle: 'Faute prouvée', articles: [], enfants: [] }],
      articles: [{ texte: 'article 1240 du Code civil', lien: { url: 'https://www.legifrance.gouv.fr/a1240', entete: 'Code civil, article 1240' } }] },
    { libelle: 'Conditions', articles: [], enfants: [
      { libelle: 'Dommage', enfants: [], articles: [{ texte: 'article 1241', lien: null }] },
      { libelle: 'Lien de causalité', articles: [], enfants: [] }] },
    { libelle: 'Exonération', articles: [], enfants: [] },
  ],
  partiel: false, message: '', restants: 4,
  avertissement: 'Carte générée automatiquement : vérifiez avec les textes.',
}

let reponse: () => Promise<Response>
const json = (corps: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(corps), { status, headers: { 'Content-Type': 'application/json' } }))

beforeEach(() => {
  reponse = () => json(CARTE)
  vi.stubGlobal('fetch', vi.fn(() => reponse()))
})
afterEach(() => { vi.unstubAllGlobals() })

const demande = () => ({ type: 'cours' as const, id: '7' })
const dessin = () => screen.getByTestId('dessin-carte')
const libellesDessin = () => Array.from(dessin().querySelectorAll('text')).map((t) => {
  const lignes = Array.from(t.querySelectorAll('tspan')).map((l) => l.textContent)
  return lignes.length ? lignes.join(' ') : t.textContent
})

describe('Carte mentale', () => {
  it('garde le focus : titre de la section à l’ouverture, bouton à la fermeture (audit du 2026-11-23, D4)', async () => {
    render(<CarteMentale demande={demande} />)
    fireEvent.click(screen.getByRole('button', { name: /carte mentale/i }))
    expect(screen.getByRole('heading', { name: 'Carte mentale' })).toHaveFocus()
    fireEvent.click(screen.getByRole('button', { name: 'Fermer' }))
    expect(screen.getByRole('button', { name: /carte mentale/i })).toHaveFocus()
  })

  it('demande la carte au clic, la dessine et donne la version en liste et l’avertissement', async () => {
    render(<CarteMentale demande={demande} />)
    expect(fetch).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Carte mentale' }))
    await screen.findByTestId('dessin-carte')
    const [url, init] = vi.mocked(fetch).mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toMatch(/\/carte-mentale$/)
    expect(JSON.parse(init.body as string)).toEqual({ type: 'cours', id: '7' })
    // dessin cache aux lecteurs d'ecran ; la liste porte le contenu, avec les liens vers le texte officiel
    expect(dessin()).toHaveAttribute('aria-hidden', 'true')
    expect(libellesDessin()).toEqual(expect.arrayContaining(['Fondement', 'Faute prouvée', 'article 1240 du Code civil']))
    const lien = screen.getByRole('link', { name: /article 1240 du Code civil/ })
    expect(lien).toHaveAttribute('href', 'https://www.legifrance.gouv.fr/a1240')
    expect(lien).toHaveAttribute('target', '_blank')
    expect(screen.getAllByText('article 1241').every((e) => e.closest('a') === null)).toBe(true) // sans lien connu
    expect(screen.getByText(/vérifiez avec les textes/)).toBeInTheDocument()
    expect(screen.getByText(/4 carte\(s\) restante\(s\)/)).toBeInTheDocument()
  })

  it('replie une branche dans le dessin et dans la liste, zoome et passe en vue liste', async () => {
    render(<CarteMentale demande={demande} />)
    fireEvent.click(screen.getByRole('button', { name: 'Carte mentale' }))
    await screen.findByTestId('dessin-carte')
    const branche = screen.getByRole('button', { name: /Fondement/ })
    expect(branche).toHaveAttribute('aria-expanded', 'true')
    fireEvent.click(branche)
    expect(branche).toHaveAttribute('aria-expanded', 'false')
    expect(libellesDessin()).not.toContain('Faute prouvée')
    expect(libellesDessin()).toContain('+2') // sous-branche et article caches
    fireEvent.click(dessin().querySelector('[data-genre="branche"]')!) // clic sur la branche dessinee
    expect(libellesDessin()).toContain('Faute prouvée')
    fireEvent.click(screen.getByRole('button', { name: 'Tout replier' }))
    expect(screen.getAllByRole('button', { expanded: false })).toHaveLength(2) // branche sans contenu : pas de bouton

    const largeur = Number(dessin().getAttribute('width'))
    fireEvent.click(screen.getByRole('button', { name: 'Zoomer' }))
    expect(Number(dessin().getAttribute('width'))).toBeCloseTo(largeur * 1.25)
    expect(screen.getByText('125 %')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Vue en liste' }))
    expect(screen.queryByTestId('dessin-carte')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Image PNG' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Vue en carte' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('demande une notion pour une matière avant de créer la carte', async () => {
    render(<CarteMentale avecNotion demande={(notion) => ({ type: 'matiere', matiere: 'droit_civil', notion })} />)
    fireEvent.click(screen.getByRole('button', { name: 'Carte mentale' }))
    expect(fetch).not.toHaveBeenCalled()
    fireEvent.change(screen.getByLabelText(/Notion/), { target: { value: '  usufruit ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Créer la carte' }))
    await screen.findByTestId('dessin-carte')
    const [, init] = vi.mocked(fetch).mock.calls[0] as unknown as [string, RequestInit]
    expect(JSON.parse(init.body as string)).toEqual({ type: 'matiere', matiere: 'droit_civil', notion: 'usufruit' })
  })

  it('affiche le message de l’API (limite du jour, carte non vérifiable)', async () => {
    reponse = () => json({ detail: 'Limite du jour atteinte : 5 cartes mentales par jour.' }, 402)
    const { unmount } = render(<CarteMentale demande={demande} />)
    fireEvent.click(screen.getByRole('button', { name: 'Carte mentale' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Limite du jour atteinte')
    unmount()
    reponse = () => json({ ...CARTE, branches: [], message: 'Impossible de produire une carte vérifiable de ce document.' })
    render(<CarteMentale demande={demande} />)
    fireEvent.click(screen.getByRole('button', { name: 'Carte mentale' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Impossible de produire une carte vérifiable')
    expect(screen.queryByTestId('dessin-carte')).not.toBeInTheDocument()
  })

  it('commence par la liste sur un écran étroit', async () => {
    vi.stubGlobal('matchMedia', (q: string) => ({ matches: q.includes('max-width'), media: q }))
    render(<CarteMentale demande={demande} />)
    fireEvent.click(screen.getByRole('button', { name: 'Carte mentale' }))
    const liste = await screen.findByRole('button', { name: 'Vue en carte' })
    expect(liste).toBeInTheDocument()
    expect(screen.queryByTestId('dessin-carte')).not.toBeInTheDocument()
    expect(within(screen.getByRole('region', { name: 'Carte mentale' })).getByText('Faute prouvée')).toBeVisible()
  })
})

describe('lib/carteMentale', () => {
  it('coupe les libellés en lignes sans dépasser la largeur', () => {
    expect(couperLignes('Responsabilité du fait personnel', 20)).toEqual(['Responsabilité du', 'fait personnel'])
    const long = couperLignes('mot '.repeat(60), 10)
    expect(long).toHaveLength(4)
    expect(long[3].endsWith('…')).toBe(true)
    expect(couperLignes('anticonstitutionnellement', 10).every((l) => l.length <= 10)).toBe(true)
  })

  it('dispose un arbre sans chevauchement, chaque parent à gauche de ses enfants', () => {
    const d = disposer(CARTE)
    const centre = d.boites.find((b) => b.genre === 'centre')!
    expect(d.boites).toHaveLength(1 + 3 + 3 + 2) // centre, branches, sous-branches, feuilles
    expect(d.traits).toHaveLength(d.boites.length - 1)
    for (const b of d.boites.filter((x) => x.genre === 'branche')) expect(b.x).toBeGreaterThan(centre.x + centre.l)
    // aucune boite ne chevauche une autre de la meme colonne
    const colonnes = new Map<number, typeof d.boites>()
    for (const b of d.boites) colonnes.set(b.x, [...(colonnes.get(b.x) ?? []), b])
    for (const boites of colonnes.values()) {
      const tri = [...boites].sort((a, b) => a.y - b.y)
      tri.slice(1).forEach((b, i) => expect(b.y).toBeGreaterThanOrEqual(tri[i].y + tri[i].h))
    }
    expect(Math.max(...d.boites.map((b) => b.y + b.h))).toBeLessThanOrEqual(d.hauteur)
    // branche repliee : ses enfants disparaissent, le nombre cache est garde
    const repliee = disposer(CARTE, new Set([0]))
    expect(repliee.boites.find((b) => b.cle === 'b0')!.replie).toBe(2)
    expect(repliee.boites).toHaveLength(d.boites.length - 2)
  })

  it('nomme l’image exportée sans accents ni espaces', () => {
    expect(nomFichier('Responsabilité du fait personnel')).toBe('carte-mentale-responsabilite-du-fait-personnel.png')
    expect(nomFichier('')).toBe('carte-mentale.png')
  })
})
