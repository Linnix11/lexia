// Referencement des pages publiques (D116) : titre, description, adresse canonique et donnees structurees
// (schema.org en JSON-LD). Lu par le site (titre de l'onglet) et par le prerendu (web/scripts/prerendu.mjs),
// qui ecrit ces balises dans le HTML de chaque page, le sitemap et llms.txt.
import donnees from './donnees-publiques.json'
import { citation, libelleCitation } from './contenu/citations'
import { GUIDES, clesCitations, type Guide } from './contenu/guides'
import { MATIERES_PUBLIQUES, type MatierePublique } from './contenu/matieres'
import { TITRES_PUBLICS } from './routesPubliques'

/** Adresse du site en ligne. A changer ici seulement si le domaine change. */
export const ORIGINE = 'https://lexia-axionstudio.cloud'
export const NOM = 'Lexia'
export const EDITEUR = 'Axion Studio'
export const IMAGE_PARTAGE = '/og-lexia.png'

export interface PageSeo {
  chemin: string
  /** Titre court (onglet : « titre · Lexia », sauf l'accueil). */
  titre: string
  description: string
  /** true : contenu rendu en HTML a la publication ; false : seules les balises de tete sont ecrites. */
  prerendu: boolean
  sitemap: boolean
  type: 'website' | 'article'
  jsonld: () => object[]
}

const LIBELLES_ANNEES: Record<string, string> = { L1: 'Licence 1', L2: 'Licence 2', L3: 'Licence 3' }

export const titreComplet = (p: Pick<PageSeo, 'chemin' | 'titre'>) => (p.chemin === '/' ? p.titre : `${p.titre} · ${NOM}`)
const url = (chemin: string) => ORIGINE + (chemin === '/' ? '/' : chemin)

/** Noeud de l'editeur : ajoute a chaque graphe par balisesTete (publication.ts), car un « @id » ne relie pas une
 *  page a une autre (audit du 2026-11-23, D6). */
export const editeur = { '@type': 'Organization', '@id': `${ORIGINE}/#editeur`, name: EDITEUR, url: ORIGINE }

const fil = (...etapes: [string, string][]) => ({
  '@type': 'BreadcrumbList',
  itemListElement: [['Accueil', '/'] as [string, string], ...etapes].map(([nom, chemin], i) => ({
    '@type': 'ListItem', position: i + 1, name: nom, item: url(chemin),
  })),
})

const application = () => ({
  '@type': 'WebApplication',
  '@id': `${ORIGINE}/#application`,
  name: NOM,
  url: ORIGINE,
  applicationCategory: 'EducationalApplication',
  operatingSystem: 'Navigateur web',
  inLanguage: 'fr-FR',
  description: 'Assistant d’étude du droit français pour les étudiants en licence : explications, fiches, questionnaires et méthodes (cas pratique, commentaire d’arrêt, dissertation), appuyés sur les textes officiels cités.',
  audience: { '@type': 'EducationalAudience', educationalRole: 'student', audienceType: 'Étudiants en licence de droit' },
  publisher: { '@id': `${ORIGINE}/#editeur` },
  offers: donnees.formules.map((f) => ({
    '@type': 'Offer', name: f.nom, price: f.prix_mensuel_euros.toFixed(2), priceCurrency: 'EUR', description: f.description,
    url: url('/tarifs'),
  })),
})

const faq = (questions: { question: string; reponse: string }[]) => ({
  '@type': 'FAQPage',
  mainEntity: questions.map((q) => ({ '@type': 'Question', name: q.question, acceptedAnswer: { '@type': 'Answer', text: q.reponse } })),
})

/** Questions frequentes d'une matiere : la question de cours, puis deux reponses tirees des donnees du depot. La
 *  question promotionnelle commune aux 20 pages est retiree (audit du 2026-11-23, D7). */
export function questionsMatiere(m: MatierePublique): { question: string; reponse: string }[] {
  const sources = m.sources.map((s) => m.noms_sources?.[s] ?? s)
  return [
    ...m.questions.map((q) => ({ question: q.question, reponse: q.reponse })),
    {
      question: `En quelle année de licence étudie-t-on le ${m.libelle.charAt(0).toLowerCase()}${m.libelle.slice(1)} ?`,
      reponse: `Le plus souvent en ${LIBELLES_ANNEES[m.annee ?? ''] ?? 'licence'}, d’après les maquettes de huit facultés de droit relevées par Lexia en novembre 2026. L’année et l’intitulé exact varient selon les universités.`,
    },
    {
      question: `Sur quelles sources Lexia s’appuie-t-il en ${m.libelle.charAt(0).toLowerCase()}${m.libelle.slice(1)} ?`,
      reponse: `Sur les textes et décisions officiels suivants : ${sources.join(', ')}. Chaque réponse cite l’article ou la décision qui la fonde, avec un lien vers le texte officiel.`,
    },
  ]
}

const DESCRIPTION_ACCUEIL = 'Lexia, assistant d’étude du droit pour les étudiants en licence : explications, fiches, questionnaires et méthodes, appuyés sur un corpus de plus de 900 000 passages officiels.'

const euros = (e: number) => `${e.toFixed(2).replace('.', ',')} €`

/** Description de /tarifs tiree des formules du depot (api/plans.py), comme llms.txt : jamais de prix en dur (D13). */
export function descriptionTarifs(): string {
  const [gratuit, ...payantes] = donnees.formules
  return `Formules de Lexia : gratuite avec un compte (${gratuit.questions_par_jour} questions et ${gratuit.quiz_par_jour} questionnaires par jour), `
    + `${payantes.map((f) => `${f.nom} à ${euros(f.prix_mensuel_euros)}`).join(' et ')} par mois, sans engagement.`
}

function pagesFixes(): PageSeo[] {
  return [
    {
      chemin: '/', titre: TITRES_PUBLICS['/'], description: DESCRIPTION_ACCUEIL,
      prerendu: true, sitemap: true, type: 'website',
      jsonld: () => [
        editeur,
        { '@type': 'WebSite', '@id': `${ORIGINE}/#site`, name: NOM, url: ORIGINE, inLanguage: 'fr-FR', description: DESCRIPTION_ACCUEIL, publisher: { '@id': `${ORIGINE}/#editeur` } },
        application(),
      ],
    },
    {
      chemin: '/tarifs', titre: TITRES_PUBLICS['/tarifs'],
      description: descriptionTarifs(),
      prerendu: true, sitemap: true, type: 'website',
      jsonld: () => [application(), fil(['Tarifs', '/tarifs'])],
    },
    {
      chemin: '/matieres', titre: TITRES_PUBLICS['/matieres'],
      description: 'Les 20 matières de droit couvertes par Lexia, de la L1 à la L3 : présentation, question de cours avec l’article officiel, sources consultées et questions fréquentes.',
      prerendu: true, sitemap: true, type: 'website',
      jsonld: () => [
        {
          '@type': 'CollectionPage', name: 'Les matières de la licence de droit', url: url('/matieres'), inLanguage: 'fr-FR',
          mainEntity: {
            '@type': 'ItemList',
            itemListElement: MATIERES_PUBLIQUES.map((m, i) => ({ '@type': 'ListItem', position: i + 1, name: m.libelle, url: url(`/matieres/${m.slug}`) })),
          },
        },
        fil(['Matières', '/matieres']),
      ],
    },
    {
      chemin: '/guides', titre: TITRES_PUBLICS['/guides'],
      description: 'Guides gratuits pour les étudiants en droit : méthode du cas pratique, du commentaire d’arrêt, fiches de révision, avec les articles officiels cités et datés.',
      prerendu: true, sitemap: true, type: 'website',
      jsonld: () => [
        {
          '@type': 'CollectionPage', name: 'Guides de méthode et fiches de droit', url: url('/guides'), inLanguage: 'fr-FR',
          mainEntity: { '@type': 'ItemList', itemListElement: GUIDES.map((g, i) => ({ '@type': 'ListItem', position: i + 1, name: g.titre, url: url(`/guides/${g.slug}`) })) },
        },
        fil(['Guides', '/guides']),
      ],
    },
    // Pages legales : leurs mentions (editeur, SIRET, hebergeur) viennent de la configuration du serveur, absente a
    // la compilation. Seule la tete est ecrite ; le contenu reste affiche par le navigateur.
    { chemin: '/mentions-legales', titre: TITRES_PUBLICS['/mentions-legales'], description: 'Mentions légales de Lexia : éditeur, directeur de la publication, hébergeur et contact.', prerendu: false, sitemap: true, type: 'website', jsonld: () => [] },
    { chemin: '/cgu', titre: TITRES_PUBLICS['/cgu'], description: 'Conditions générales d’utilisation et de vente de Lexia, assistant d’étude du droit.', prerendu: false, sitemap: true, type: 'website', jsonld: () => [] },
    { chemin: '/confidentialite', titre: TITRES_PUBLICS['/confidentialite'], description: 'Données personnelles traitées par Lexia, finalités, durées de conservation, sous-traitants et droits des utilisateurs.', prerendu: false, sitemap: true, type: 'website', jsonld: () => [] },
  ]
}

const pageMatiere = (m: MatierePublique): PageSeo => {
  const chemin = `/matieres/${m.slug}`
  const annee = m.annee ?? ''
  return {
    chemin,
    titre: TITRES_PUBLICS[chemin],
    description: `${m.libelle} en ${LIBELLES_ANNEES[annee] ?? 'licence'} : ce que couvre la matière, une question de cours avec l’article officiel, les sources consultées par Lexia et les questions fréquentes.`.slice(0, 200),
    prerendu: true, sitemap: true, type: 'website',
    jsonld: () => [
      {
        '@type': 'LearningResource', name: m.libelle, url: url(chemin), inLanguage: 'fr-FR', description: m.presentation,
        educationalLevel: LIBELLES_ANNEES[annee] ?? 'Licence', learningResourceType: 'Fiche de présentation',
        about: [m.libelle, ...(m.mots ?? [])], isAccessibleForFree: true, publisher: { '@id': `${ORIGINE}/#editeur` },
      },
      faq(m.questions.map((q) => ({ question: q.question, reponse: q.reponse }))),
      fil(['Matières', '/matieres'], [m.libelle, chemin]),
    ],
  }
}

const pageGuide = (g: Guide): PageSeo => {
  const chemin = `/guides/${g.slug}`
  return {
    chemin, titre: TITRES_PUBLICS[chemin], description: g.description, prerendu: true, sitemap: true, type: 'article',
    jsonld: () => [
      {
        '@type': 'Article', headline: g.titre, description: g.description, url: url(chemin), inLanguage: 'fr-FR',
        datePublished: g.publie, dateModified: g.publie, educationalLevel: g.niveau, isAccessibleForFree: true,
        author: { '@id': `${ORIGINE}/#editeur` }, publisher: { '@id': `${ORIGINE}/#editeur` },
        image: url(IMAGE_PARTAGE),
        citation: clesCitations(g).map((k) => citation(k)).map((c) => ({ '@type': 'Legislation', name: libelleCitation(c), url: c.url })),
      },
      ...(g.faq.length ? [faq(g.faq)] : []),
      fil(['Guides', '/guides'], [g.titre, chemin]),
    ],
  }
}

/** Toutes les pages publiques referencees, dans l'ordre du sitemap. */
export function pagesSeo(): PageSeo[] {
  return [...pagesFixes(), ...MATIERES_PUBLIQUES.map(pageMatiere), ...GUIDES.map(pageGuide)]
}
