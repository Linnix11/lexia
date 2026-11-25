// Prerendu des pages publiques (D116), lance par `npm run build` apres la compilation du site et de l'entree
// serveur (dist-ssr/). Pour chaque page de web/src/site/seo.ts : HTML complet dans dist/pages/<chemin>/index.html
// (contenu lisible sans JavaScript, titre, description, adresse canonique, Open Graph, JSON-LD), puis
// dist/sitemap.xml, dist/llms.txt, dist/introuvable.html et dist/chemins-application.json (D134). dist/index.html
// reste la coquille vide (noindex) des ecrans non prerendus.
import { mkdir, readFile, rm, writeFile } from 'node:fs/promises'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { JSDOM } from 'jsdom'

const web = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const dist = join(web, 'dist')
const ssr = join(web, 'dist-ssr')

// Document du navigateur simule : les composants lisent window.location (routeur) et le stockage local.
const dom = new JSDOM('<!doctype html><html lang="fr"><body></body></html>', { url: 'https://lexia-axionstudio.cloud/' })
const fenetre = dom.window
for (const nom of ['window', 'document', 'location', 'history', 'localStorage', 'sessionStorage', 'HTMLElement', 'Node', 'navigator']) {
  Object.defineProperty(globalThis, nom, { value: nom === 'window' ? fenetre : fenetre[nom], configurable: true, writable: true })
}
// Aucun appel reseau pendant le prerendu : les effets ne s'executent pas, un appel serait une erreur a corriger.
globalThis.fetch = () => Promise.reject(new Error('fetch pendant le prerendu'))

const { rendre, pagesSeo, pageHtml, pageIntrouvableHtml, fichierPage, sitemapXml, llmsTxt, CHEMINS_APPLICATION, CHEMIN_INTROUVABLE } = await import(pathToFileURL(join(ssr, 'entree-serveur.js')).href)

const gabarit = await readFile(join(dist, 'index.html'), 'utf8')
await rm(join(dist, 'pages'), { recursive: true, force: true })
let prerendues = 0
for (const page of pagesSeo()) {
  fenetre.history.replaceState(null, '', page.chemin)
  const corps = page.prerendu ? await rendre() : ''
  if (page.prerendu && !corps.includes('<h1')) throw new Error(`Prerendu sans titre <h1> : ${page.chemin}`)
  const fichier = join(dist, fichierPage(page.chemin))
  await mkdir(dirname(fichier), { recursive: true })
  await writeFile(fichier, pageHtml(gabarit, page, corps))
  if (page.prerendu) prerendues += 1
}
// Vraies 404 (D134) : page introuvable prerendue et liste des ecrans du front, lues par api/serveur.py
fenetre.history.replaceState(null, '', CHEMIN_INTROUVABLE)
const introuvable = await rendre()
if (!introuvable.includes('Page introuvable</h1>')) throw new Error('Prerendu de la page introuvable sans son titre')
await writeFile(join(dist, 'introuvable.html'), pageIntrouvableHtml(gabarit, introuvable))
await writeFile(join(dist, 'chemins-application.json'), JSON.stringify(CHEMINS_APPLICATION) + '\n')
await writeFile(join(dist, 'sitemap.xml'), sitemapXml())
await writeFile(join(dist, 'llms.txt'), llmsTxt())
await rm(ssr, { recursive: true, force: true })
console.log(`prerendu : ${prerendues} pages en HTML, ${pagesSeo().length - prerendues} pages avec tete seule, sitemap.xml, llms.txt, introuvable.html, ${CHEMINS_APPLICATION.length} ecrans`)
