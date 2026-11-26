// Carte mentale (D112) : plan demande au serveur, dessin SVG, repli, zoom, version en liste accessible.
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { CarteMentale as Carte } from '../lib/api'
import { couperLignes, disposer, nomFichier, pageImpression, planTexte } from '../lib/carteMentale'
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
  it('affiche une carte enregistrée sans rien demander au serveur ni le quota du jour', () => {
    const fermer = vi.fn()
    render(<CarteMentale enregistree={{ ...CARTE, restants: 0 }} onFermer={fermer} />)
    expect(screen.getByText('Fondement', { selector: 'tspan, text' })).toBeInTheDocument()
    expect(screen.queryByText(/restante\(s\) aujourd’hui/)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Enregistrer la carte' })).not.toBeInTheDocument()
    expect(fetch).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Fermer' }))
    expect(fermer).toHaveBeenCalled()
  })

  it('montre l’animation de chargement pendant la préparation', async () => {
    let finir: (r: Response) => void = () => {}
    reponse = () => new Promise<Response>((r) => { finir = r })
    render(<CarteMentale demande={demande} />)
    fireEvent.click(screen.getByRole('button', { name: 'Carte mentale' }))
    expect(await screen.findByRole('status')).toHaveTextContent('Lecture du contenu…')
    finir(new Response(JSON.stringify(CARTE), { status: 200, headers: { 'Content-Type': 'application/json' } }))
    await waitFor(() => expect(screen.queryByText('Lecture du contenu…')).not.toBeInTheDocument())
  })

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

describe('Carte mentale : réviser, imprimer, copier (D138)', () => {
  const ouvrir = async () => {
    render(<CarteMentale demande={demande} />)
    fireEvent.click(screen.getByRole('button', { name: 'Carte mentale' }))
    await screen.findByTestId('dessin-carte')
  }

  it('« Réviser » masque sous-idées et références, les révèle une à une, puis toutes', async () => {
    await ouvrir()
    fireEvent.click(screen.getByRole('button', { name: 'Tout replier' }))
    const reviser = screen.getByRole('button', { name: 'Réviser' })
    fireEvent.click(reviser)
    expect(reviser).toHaveAttribute('aria-pressed', 'true')
    // branches depliees, visibles ; sous-idees et references cachees dans le dessin et dans la liste
    expect(libellesDessin()).toEqual(expect.arrayContaining(['Fondement', 'Conditions']))
    expect(libellesDessin()).not.toContain('Faute prouvée')
    expect(libellesDessin()).not.toContain('article 1240 du Code civil')
    // 3 sous-idees et 2 references (1240 sous la branche, 1241 sous « Dommage »)
    expect(dessin().querySelectorAll('[data-masque]')).toHaveLength(5)
    expect(screen.queryByRole('link', { name: /article 1240/ })).not.toBeInTheDocument()
    expect(screen.getByText('0 sur 5 révélé(s).')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Révéler la sous-idée 1 de « Conditions »' }))
    expect(libellesDessin()).toContain('Dommage')
    expect(screen.getByText('1 sur 5 révélé(s).')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Révéler la référence 1 de « Dommage »' })).toBeInTheDocument()
    fireEvent.click(dessin().querySelector('[data-masque]')!) // clic sur un « ? » du dessin
    expect(screen.getByText('2 sur 5 révélé(s).')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Tout révéler' }))
    expect(screen.getByText('Tout est révélé.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /article 1240/ })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Quitter la révision' }))
    expect(dessin().querySelectorAll('[data-masque]')).toHaveLength(0)
  })

  it('« Imprimer ou PDF » ouvre la carte entière et son plan, avec la mention IA', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    const ecrit: string[] = []
    const fenetre = { document: { open: vi.fn(), write: (h: string) => ecrit.push(h), close: vi.fn() }, focus: vi.fn(), print: vi.fn() }
    vi.stubGlobal('open', vi.fn(() => fenetre))
    await ouvrir()
    fireEvent.click(screen.getByRole('button', { name: 'Tout replier' })) // repliee a l'ecran : imprimee entiere
    fireEvent.click(screen.getByRole('button', { name: 'Imprimer ou PDF' }))
    const page = ecrit.join('')
    expect(page).toContain('<title>Carte mentale · Responsabilité du fait personnel</title>')
    expect(page).toMatch(/<svg[^>]*viewBox/)
    expect(page).toContain('Faute prouvée')                                         // dessin et plan entiers
    expect(page).toContain('<a href="https://www.legifrance.gouv.fr/a1240">article 1240 du Code civil</a>')
    expect(page).toContain('Carte générée par une intelligence artificielle (Lexia)')
    expect(page).not.toContain('data-testid')
    vi.advanceTimersByTime(300)
    expect(fenetre.print).toHaveBeenCalled()
    vi.useRealTimers()
  })

  it('prévient quand la fenêtre d’impression est bloquée', async () => {
    vi.stubGlobal('open', vi.fn(() => null))
    await ouvrir()
    fireEvent.click(screen.getByRole('button', { name: 'Imprimer ou PDF' }))
    expect(screen.getByRole('alert')).toHaveTextContent('bloqué la fenêtre d’impression')
  })

  it('« Copier le plan » copie un plan numéroté avec les références', async () => {
    const ecrire = vi.fn(() => Promise.resolve())
    vi.stubGlobal('navigator', { ...navigator, clipboard: { writeText: ecrire } })
    await ouvrir()
    fireEvent.click(screen.getByRole('button', { name: 'Copier le plan' }))
    expect(await screen.findByRole('status')).toHaveTextContent('Plan copié')
    expect(ecrire).toHaveBeenCalledWith(planTexte(CARTE))
  })

  it('signale un arrêt abandonné par une bordure en tirets', () => {
    const carte: Carte = { ...CARTE, branches: [{ libelle: 'Faute de la victime', enfants: [], articles: [
      { texte: 'Cass. civ. 2e, 21 juillet 1982, Desmares (arrêt abandonné : n’est plus le droit positif)', lien: null, statut: 'abandonne' }] },
    CARTE.branches[1]] }
    render(<CarteMentale enregistree={carte} />)
    expect(dessin().querySelector('[data-genre="feuille"] rect')).toHaveAttribute('stroke-dasharray', '5 3')
    const pastille = screen.getAllByText(/Desmares/).find((e) => e.tagName === 'LI')!
    expect(pastille).toHaveClass('border-dashed')
  })
})

describe('lib/carteMentale : plan et impression', () => {
  it('plan en texte : branches numérotées, sous-idées en tirets, mention IA', () => {
    expect(planTexte(CARTE).split('\n')).toEqual([
      'Responsabilité du fait personnel', '',
      '1. Fondement (article 1240 du Code civil)', '   - Faute prouvée',
      '2. Conditions', '   - Dommage (article 1241)', '   - Lien de causalité',
      '3. Exonération', '',
      'Carte générée par une intelligence artificielle (Lexia) : vérifiez les sources citées.'])
  })

  it('page à imprimer : texte échappé', () => {
    const page = pageImpression({ ...CARTE, titre: 'A <b>&</b> "B"' }, '<svg></svg>', new Date('2026-11-26T12:00:00Z'))
    expect(page).toContain('A &lt;b&gt;&amp;&lt;/b&gt; &quot;B&quot;')
    expect(page).not.toContain('<b>')
    expect(page).toContain('Imprimée le 26/11/2026')
  })
})

describe('lib/carteMentale', () => {
  it('coupe les libellés en lignes sans dépasser la largeur', () => {
    expect(couperLignes('Responsabilité du fait personnel', 20)).toEqual(['Responsabilité du', 'fait personnel'])
    const long = couperLignes('mot '.repeat(60), 10)
    expect(long).toHaveLength(6)
    expect(long[5].endsWith('…')).toBe(true)
    // une feuille annotee de 98 caracteres n'est plus coupee (4 lignes la tronquaient, D138)
    const feuille = 'article 1384 du Code civil (ancien numéro, aujourd’hui article 1242) et article 1242 du Code civil'
    expect(couperLignes(feuille, 25).join(' ')).toBe(feuille)
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
