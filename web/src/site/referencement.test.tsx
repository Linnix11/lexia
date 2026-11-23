// Referencement (D116) : pages publiques, balises de tete, sitemap, robots.txt, llms.txt et contenu verifiable.
import { cleanup, render, screen } from '@testing-library/react'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Site from '../Site'
import { CITATIONS, citation, libelleCitation, numeroLisible } from './contenu/citations'
import { GUIDES, clesCitations } from './contenu/guides'
import { GUIDES_LISTE } from './contenu/guidesListe'
import { MATIERES_PUBLIQUES } from './contenu/matieres'
import donnees from './donnees-publiques.json'
import { balisesTete, fichierPage, llmsTxt, pageHtml, sitemapXml } from './publication'
import { CHEMINS_GUIDES, CHEMINS_MATIERES, TITRES_PUBLICS } from './routesPubliques'
import { ORIGINE, pagesSeo, questionsMatiere } from './seo'

const PUBLIC = join(__dirname, '..', '..', 'public')
const pages = pagesSeo()

// Phrases a ne pas ecrire (docs/comparatif-notebooklm.md, partie 4) et regles de redaction du depot.
const INTERDITS = [
  /jurisprudence (à|a) jour chaque nuit/i, /jamais utilis[ée]+s? pour l.entra[iî]nement/i, /entra[iî]ner une IA/i,
  /h[ée]berg[ée]+s? en France/i, /sans erreur/i, /fiable à 100/i, /valid[ée]+s? par des enseignants/i,
  /application mobile/i, /paiement par carte/i, /fiches à retourner/i, /NotebookLM|Gemini Notebook/i, /—/,
  /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u,
]
const toutLeTexte = () => JSON.stringify({ GUIDES, MATIERES_PUBLIQUES, llms: llmsTxt(), pages: pages.map((p) => [p.titre, p.description, p.jsonld()]) })

describe('contenu des pages publiques', () => {
  it('une page par matiere du depot, avec presentation et question de cours', () => {
    expect(MATIERES_PUBLIQUES).toHaveLength(donnees.matieres.length)
    expect(MATIERES_PUBLIQUES.length).toBe(20)
    for (const m of MATIERES_PUBLIQUES) {
      expect(m.presentation.length).toBeGreaterThan(80)
      expect(m.questions.length).toBeGreaterThan(0)
    }
    expect(new Set(CHEMINS_MATIERES).size).toBe(20)
  })

  it('chaque article cite existe dans citations.json, avec les alineas demandes', () => {
    const usages = [
      ...MATIERES_PUBLIQUES.flatMap((m) => m.questions.flatMap((q) => q.citations)),
      ...GUIDES.flatMap((g) => g.sections.flatMap((s) => s.blocs.flatMap((b) => ('citation' in b ? [{ cle: b.citation, alineas: b.alineas }] : [])))),
    ]
    expect(usages.length).toBeGreaterThan(40)
    for (const u of usages) {
      const c = citation(u.cle)
      for (const i of u.alineas ?? []) expect(c.alineas[i], `${u.cle} alinea ${i}`).toBeTruthy()
      expect(c.url).toMatch(/^https:\/\/(www\.legifrance\.gouv\.fr|www\.conseil-constitutionnel\.fr)\//)
    }
    // Pas d'article lu dans l'index et jamais cite : la liste de api/donnees_publiques.py reste a jour
    const citees = new Set(usages.map((u) => u.cle))
    expect(Object.keys(CITATIONS).filter((k) => !citees.has(k))).toEqual([])
  })

  it('cite les articles comme les codes imprimes', () => {
    expect(numeroLisible('L411-1')).toBe('L. 411-1')
    expect(numeroLisible('R421-1')).toBe('R. 421-1')
    expect(numeroLisible('1112-1')).toBe('1112-1')
    expect(libelleCitation(citation('code_civil:1101'))).toBe('Code civil, art. 1101')
    expect(libelleCitation(citation('ordonnance_58_1067:23-2'))).toBe('Ordonnance n° 58-1067 du 7 novembre 1958, art. 23-2')
  })

  it('guides avec une reponse directe, des sections et des articles cites', () => {
    expect(GUIDES.length).toBe(10)
    expect(GUIDES.map((g) => g.slug)).toEqual(GUIDES_LISTE.map((g) => g.slug))
    for (const g of GUIDES) {
      expect(g.enBref.length).toBeGreaterThan(150)
      expect(g.sections.length).toBeGreaterThanOrEqual(3)
      expect(clesCitations(g).length).toBeGreaterThanOrEqual(2)
    }
  })

  it('n’ecrit aucune phrase interdite, ni tiret long, ni emoji', () => {
    const texte = toutLeTexte()
    for (const motif of INTERDITS) expect(texte, String(motif)).not.toMatch(motif)
  })
})

describe('balises de referencement', () => {
  it('chemins, titres et descriptions uniques ; titres du routeur identiques', () => {
    expect(new Set(pages.map((p) => p.chemin)).size).toBe(pages.length)
    expect(new Set(pages.map((p) => p.titre)).size).toBe(pages.length)
    expect(new Set(pages.map((p) => p.description)).size).toBe(pages.length)
    for (const p of pages) {
      expect(p.titre).toBe(TITRES_PUBLICS[p.chemin])
      expect(p.description.length, p.chemin).toBeGreaterThanOrEqual(70)
      expect(p.description.length, p.chemin).toBeLessThanOrEqual(200)
    }
    expect(pages.map((p) => p.chemin)).toEqual(expect.arrayContaining([...CHEMINS_MATIERES, ...CHEMINS_GUIDES, '/', '/tarifs', '/matieres', '/guides']))
  })

  it('tete complete : titre, description, canonique, Open Graph, Twitter et JSON-LD lisible', () => {
    const p = pages.find((x) => x.chemin === '/matieres/droit-des-contrats')!
    const tete = balisesTete(p)
    expect(tete).toContain('<title>Droit des contrats (L2) : cours, questions et sources officielles · Lexia</title>')
    expect(tete).toContain(`<link rel="canonical" href="${ORIGINE}/matieres/droit-des-contrats" />`)
    expect(tete).toContain(`<meta property="og:image" content="${ORIGINE}/og-lexia.png" />`)
    expect(tete).toContain('<meta name="twitter:card" content="summary_large_image" />')
    const ld = JSON.parse(tete.split('<script type="application/ld+json">')[1].split('</script>')[0])
    const types = ld['@graph'].map((x: { '@type': string }) => x['@type'])
    expect(types).toEqual(['LearningResource', 'FAQPage', 'BreadcrumbList'])
    const faq = ld['@graph'][1].mainEntity.map((q: { name: string }) => q.name)
    expect(faq).toEqual(questionsMatiere(MATIERES_PUBLIQUES.find((m) => m.id === 'droit_des_contrats')!).map((q) => q.question))
  })

  it('accueil : Organization, WebSite et application avec les prix du depot', () => {
    const ld = pages[0].jsonld() as { '@type': string; offers?: { price: string }[] }[]
    expect(ld.map((x) => x['@type'])).toEqual(['Organization', 'WebSite', 'WebApplication'])
    expect(ld[2].offers!.map((o) => o.price)).toEqual(donnees.formules.map((f) => f.prix_mensuel_euros.toFixed(2)))
  })

  it('pageHtml remplace le titre et la description du gabarit et remplit la racine', () => {
    const gabarit = readFileSync(join(__dirname, '..', '..', 'index.html'), 'utf8')
    const html = pageHtml(gabarit, pages[1], '<h1>Tarifs</h1>')
    expect(html.match(/<title>/g)).toHaveLength(1)
    expect(html.match(/<meta name="description"/g)).toHaveLength(1)
    expect(html).toContain('<div id="root"><h1>Tarifs</h1></div>')
    expect(() => pageHtml('<html></html>', pages[1], '')).toThrow(/Gabarit inattendu/)
    expect(fichierPage('/')).toBe('pages/index.html')
    expect(fichierPage('/guides/methode-commentaire-arret')).toBe('pages/guides/methode-commentaire-arret/index.html')
  })

  it('sitemap : toutes les pages publiques, aucune adresse exclue par robots.txt', () => {
    const robots = readFileSync(join(PUBLIC, 'robots.txt'), 'utf8')
    expect(robots).toContain(`Sitemap: ${ORIGINE}/sitemap.xml`)
    const exclus = [...robots.matchAll(/^Disallow: (\S+)/gm)].map((m) => m[1])
    expect(exclus).toEqual(expect.arrayContaining(['/app', '/compte', '/admin', '/api/']))
    const urls = [...sitemapXml().matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1].slice(ORIGINE.length))
    expect(urls).toHaveLength(pages.length)
    for (const u of urls) expect(exclus.some((e) => u.startsWith(e)), u).toBe(false)
  })

  it('llms.txt : resume, matieres et guides avec leurs adresses', () => {
    const t = llmsTxt()
    expect(t.startsWith('# Lexia\n\n> ')).toBe(true)
    for (const c of [...CHEMINS_MATIERES, ...CHEMINS_GUIDES]) expect(t).toContain(`(${ORIGINE}${c})`)
    expect(t).toContain('4,99 € par mois')
  })
})

describe('pages dans le site', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(new Response('null', { status: 200, headers: { 'Content-Type': 'application/json' } }))))
  })
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    window.history.replaceState(null, '', '/')
  })

  it('page d’une matiere : titre, article officiel lie et inscription', async () => {
    window.history.replaceState(null, '', '/matieres/droit-penal')
    render(<Site />)
    expect(await screen.findByRole('heading', { level: 1, name: 'Droit pénal' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Code pénal, art. 111-3' })).toHaveAttribute('href', citation('code_penal:111-3').url)
    expect(screen.getByRole('link', { name: 'Créer un compte gratuit' })).toHaveAttribute('href', '/inscription')
    expect(document.title).toBe('Droit pénal (L2) : cours, questions et sources officielles · Lexia')
  })

  it('guide : reponse directe, textes cites et fil d’Ariane', async () => {
    window.history.replaceState(null, '', '/guides/methode-commentaire-arret')
    render(<Site />)
    expect(await screen.findByRole('heading', { level: 1, name: 'Méthode du commentaire d’arrêt' })).toBeInTheDocument()
    expect(screen.getByText('En bref')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Code de procédure civile, art. 604' }).length).toBeGreaterThan(0)
    expect(screen.getByRole('navigation', { name: 'Fil d’Ariane' })).toHaveTextContent('Guides')
  })

  it('matiere inconnue : page introuvable', async () => {
    window.history.replaceState(null, '', '/matieres/astrologie')
    render(<Site />)
    expect(await screen.findByRole('heading', { name: 'Page introuvable' })).toBeInTheDocument()
  })
})
