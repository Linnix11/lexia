// Fichiers ecrits a la publication (D116) : balises de tete de chaque page publique, sitemap.xml et llms.txt.
// Utilise par le prerendu (web/scripts/prerendu.mjs) seulement : rien ici n'est charge par le site.
import donnees from './donnees-publiques.json'
import { GUIDES } from './contenu/guides'
import { MATIERES_PUBLIQUES } from './contenu/matieres'
import { EDITEUR, IMAGE_PARTAGE, NOM, ORIGINE, editeur, pagesSeo, titreComplet, type PageSeo } from './seo'

const attr = (s: string) => s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
const texteHtml = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
// JSON dans <script> : « < » echappe, la balise ne peut pas etre refermee par le contenu
const jsonScript = (o: unknown) => JSON.stringify(o).replace(/</g, '\\u003c')

export const urlPage = (chemin: string) => ORIGINE + chemin

/** <title>, description, adresse canonique, Open Graph, carte Twitter et JSON-LD d'une page. */
export function balisesTete(p: PageSeo): string {
  const titre = titreComplet(p)
  const url = urlPage(p.chemin)
  const image = urlPage(IMAGE_PARTAGE)
  const graphe = p.jsonld()
  // Noeud de l'editeur dans chaque graphe qui le cite (publisher, author) : un « @id » n'est resolu que dans sa page (D6)
  const cite = JSON.stringify(graphe).includes(`"${editeur['@id']}"`)
  const ld = cite && !graphe.some((n) => (n as { '@id'?: string })['@id'] === editeur['@id']) ? [editeur, ...graphe] : graphe
  return [
    `<title>${texteHtml(titre)}</title>`,
    `<meta name="description" content="${attr(p.description)}" />`,
    `<link rel="canonical" href="${url}" />`,
    `<meta property="og:type" content="${p.type}" />`,
    `<meta property="og:site_name" content="${NOM}" />`,
    `<meta property="og:locale" content="fr_FR" />`,
    `<meta property="og:title" content="${attr(titre)}" />`,
    `<meta property="og:description" content="${attr(p.description)}" />`,
    `<meta property="og:url" content="${url}" />`,
    `<meta property="og:image" content="${image}" />`,
    '<meta property="og:image:width" content="1200" />',
    '<meta property="og:image:height" content="630" />',
    `<meta property="og:image:alt" content="${attr(`${NOM}, assistant d’étude du droit`)}" />`,
    '<meta name="twitter:card" content="summary_large_image" />',
    `<meta name="twitter:title" content="${attr(titre)}" />`,
    `<meta name="twitter:description" content="${attr(p.description)}" />`,
    `<meta name="twitter:image" content="${image}" />`,
    ...(ld.length ? [`<script type="application/ld+json">${jsonScript({ '@context': 'https://schema.org', '@graph': ld })}</script>`] : []),
  ].join('\n    ')
}

/** Page complete : le gabarit de Vite (dist/index.html) avec la tete de la page et son HTML prerendu. */
export function pageHtml(gabarit: string, p: PageSeo, corps: string): string {
  if (!/<title>[\s\S]*?<\/title>/.test(gabarit) || !gabarit.includes('<div id="root"></div>')) {
    throw new Error('Gabarit inattendu : <title> ou <div id="root"></div> absent de dist/index.html')
  }
  return gabarit
    .replace(/\s*<meta name="description"[^>]*>/, '')
    .replace(/<title>[\s\S]*?<\/title>/, balisesTete(p))
    .replace('<div id="root"></div>', `<div id="root">${corps}</div>`)
}

/** Fichier de la page dans dist/ : /tarifs devient pages/tarifs/index.html (servi par api/serveur.py). */
export const fichierPage = (chemin: string) => (chemin === '/' ? 'pages/index.html' : `pages${chemin}/index.html`)

export function sitemapXml(pages: PageSeo[] = pagesSeo()): string {
  const dates = new Map(GUIDES.map((g) => [`/guides/${g.slug}`, g.publie]))
  const urls = pages.filter((p) => p.sitemap).map((p) => {
    const date = dates.get(p.chemin)
    return `  <url><loc>${urlPage(p.chemin)}</loc>${date ? `<lastmod>${date}</lastmod>` : ''}</url>`
  })
  return `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.join('\n')}\n</urlset>\n`
}

const prixLisible = (e: number) => (e === 0 ? 'gratuit' : `${e.toFixed(2).replace('.', ',')} € par mois`)

/** llms.txt (format de llmstxt.org) : ce qu'est Lexia, en phrases vérifiables, et les pages a lire. */
export function llmsTxt(): string {
  const f = donnees.formules
  const lignes = [
    `# ${NOM}`,
    '',
    `> ${NOM} est un assistant d’étude du droit français pour les étudiants en licence de droit (L1 à L3), publié par ${EDITEUR}. Il explique les notions de cours, rédige des fiches et des questionnaires et guide les exercices de méthode (cas pratique, commentaire d’arrêt, dissertation), en citant les textes et décisions officiels qui fondent chaque réponse.`,
    '',
    'Points clés :',
    '',
    '- Sources : plus de 900 000 passages officiels, issus des données ouvertes de l’État et des institutions (Constitution, codes, lois, décisions du Conseil constitutionnel, arrêts de la Cour de cassation, décisions du Conseil d’État, traités de l’Union européenne).',
    '- Chaque réponse cite l’article ou la décision qui la fonde, avec un lien vers le texte officiel ; une référence introuvable est retirée avant d’être montrée.',
    `- ${MATIERES_PUBLIQUES.length} matières de la L1 à la L3, classées d’après les maquettes de huit facultés de droit.`,
    `- Formules : ${f.map((x) => `${x.nom} (${prixLisible(x.prix_mensuel_euros)}, ${x.questions_par_jour} questions par jour)`).join(', ')}.`,
    '- Lexia est un outil d’étude : il ne donne pas de conseil juridique personnalisé et ne remplace pas un professionnel du droit.',
    '',
    '## Matières',
    '',
    ...MATIERES_PUBLIQUES.map((m) => `- [${m.libelle}](${urlPage(`/matieres/${m.slug}`)}) : ${m.annee}, ${m.presentation.split('. ')[0]}.`),
    '',
    '## Guides de méthode et fiches',
    '',
    ...GUIDES.map((g) => `- [${g.titre}](${urlPage(`/guides/${g.slug}`)}) : ${g.description}`),
    '',
    '## Informations',
    '',
    `- [Accueil](${urlPage('/')}) : présentation de Lexia.`,
    `- [Tarifs](${urlPage('/tarifs')}) : formules et limites quotidiennes.`,
    `- [Mentions légales](${urlPage('/mentions-legales')}) : éditeur et hébergeur.`,
    `- [Conditions d’utilisation](${urlPage('/cgu')})`,
    `- [Politique de confidentialité](${urlPage('/confidentialite')})`,
    '',
  ]
  return lignes.join('\n')
}
