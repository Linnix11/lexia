import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Site from './Site'
import { lireSemestre } from './lib/semestres'
import { api, type ReponseChat } from './lib/api'
import { ecrireFavoris, empreinte, lireFavoris } from './lib/favoris'
import { ficheEnMarkdown } from './lib/exportFiches'
import css from './index.css?raw'
import sourceSite from './Site.tsx?raw'
import sourceDeuxFacteurs from './site/DoubleAuthentification.tsx?raw'

const REPONSE: ReponseChat = {
  reponse_id: 'r-123',
  statut: 'reponse',
  titre: 'La responsabilité pour faute',
  droit_positif: [{ texte: 'Tout fait fautif causant un dommage oblige à réparer.', sources: ['code_civil:A1240'] }],
  explication: [{ texte: 'Il faut une faute, un dommage et un lien de causalité.', sources: [], rubrique: 'Conditions' }],
  points_incertains: [],
  message: '',
  sources: [{
    id: 'code_civil:A1240', label: 'S1', source_id: 'code_civil', type: 'article', numero: '1240',
    entete: 'Code civil, article 1240', url: 'https://www.legifrance.gouv.fr/codes/article_lc/A1240',
    version: 'Version depuis le 1er octobre 2016', en_vigueur: true, date: '2016-10-01', extrait: 'Tout fait…',
  }],
  avertissement: "Lexia est un outil d'étude.",
  controle: { citations_retirees: 0, elements_retires: 1, references_non_verifiees: [], recherche: 'hybride' },
}

const PROFIL = {
  email: 'etu@exemple.fr', cree_le: '2026-11-11T10:00:00+00:00', formule_fin: null,
  formule: { id: 'gratuit', nom: 'Gratuit', prix_mensuel_euros: 0, questions_par_jour: 10, quiz_par_jour: 2, description: '', avantages: [] },
  usage: { jour: '2026-11-11', questions: 3, quiz: 0 },
  admin: false,
}

function repondre(corps: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(corps), { status, headers: { 'Content-Type': 'application/json' } }))
}

let fetchMock: ReturnType<typeof vi.fn>

let emailVerifie = true
let reponseChat: ReponseChat = REPONSE

beforeEach(() => {
  emailVerifie = true
  reponseChat = REPONSE
  localStorage.clear()
  window.history.pushState({}, '', '/app')
  fetchMock = vi.fn((url: string) => {
    if (url.endsWith('/auth/session') || url.endsWith('/auth/moi')) return repondre({ ...PROFIL, email_verifie: emailVerifie })
    if (url.endsWith('/auth/email/renvoyer')) return repondre({ envoye: true }, 202)
    if (url.endsWith('/config')) return repondre({ comptes: true, contact_email: null })
    if (url.endsWith('/matieres')) return repondre([{ id: 'droit_civil', libelle: 'Droit civil', sources: ['code_civil'] }])
    if (url.endsWith('/chat')) return repondre(reponseChat)
    if (url.includes('/vigueur')) return repondre({ id: 'code_civil:A1240', applicable: true, en_vigueur: true, version: 'v',
      url: 'u', version_en_vigueur: null, message: 'Cette version est en vigueur.' })
    if (url.includes('/sources/')) return repondre({ ...REPONSE.sources[0], texte: "Tout fait quelconque de l'homme…", titre: null, meta: {} })
    return repondre({}, 404)
  })
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => vi.unstubAllGlobals())

async function poser(question: string) {
  render(<Site />)
  await screen.findByLabelText('Votre question')
  fireEvent.change(screen.getByLabelText('Votre question'), { target: { value: question } })
  await act(async () => {
    fireEvent.click(screen.getByRole('button', { name: /Envoyer/ }))
  })
  await screen.findByText('La responsabilité pour faute')
}

describe('Assistant', () => {
  it('affiche les trois blocs, les citations et le controle', async () => {
    await poser('Que dit l’article 1240 ?')
    expect(screen.getByText('Droit positif')).toBeInTheDocument()
    expect(screen.getByText('Explication')).toBeInTheDocument()
    expect(screen.getByText('Conditions')).toBeInTheDocument()   // rubrique du mode affichee en sous-titre
    expect(screen.getByRole('button', { name: '[1] Code civil, article 1240' })).toBeInTheDocument()
    expect(screen.getByText(/1 élément\(s\) non vérifiable\(s\) retiré\(s\)/)).toBeInTheDocument()
    const corps = JSON.parse(fetchMock.mock.calls.find(([u]) => String(u).endsWith('/chat'))![1].body)
    expect(corps).toMatchObject({ question: 'Que dit l’article 1240 ?', mode: 'expliquer', niveau: 'L1', semestre: 1 })
  })

  it('affiche chaque source une seule fois par bloc, a sa premiere mention', async () => {
    const r = REPONSE.droit_positif[0]
    reponseChat = {
      ...REPONSE,
      droit_positif: [r, { ...r, texte: 'Deuxième règle.' }],
      explication: [{ texte: 'La majeure.', sources: [r.sources[0]], rubrique: 'Majeure' },
        { texte: 'La mineure.', sources: [r.sources[0]], rubrique: 'Mineure' }],
      points_incertains: [{ texte: 'Un doute.', sources: [r.sources[0]] }],
    }
    await poser('Que dit l’article 1240 ?')
    // cinq mentions de S1 (2 droit positif, 2 explication, 1 point incertain) : une pastille par bloc
    expect(screen.getAllByRole('button', { name: '[1] Code civil, article 1240' })).toHaveLength(3)
  })

  it('propose les six semestres et envoie le semestre choisi', async () => {
    render(<Site />)
    const choix = await screen.findByLabelText('Choisir le semestre')
    expect(within(choix).getAllByRole('option').map((o) => o.textContent)).toEqual([
      'L1 · Semestre 1', 'L1 · Semestre 2', 'L2 · Semestre 3', 'L2 · Semestre 4', 'L3 · Semestre 5', 'L3 · Semestre 6'])
    fireEvent.change(choix, { target: { value: '4' } })
    expect(lireSemestre('etu@exemple.fr')).toBe(4)   // une cle par compte (WEB-16)
    expect(lireSemestre('autre@exemple.fr')).toBe(1)
    fireEvent.change(screen.getByLabelText('Votre question'), { target: { value: 'article 1240' } })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Envoyer/ }))
    })
    await screen.findByText('La responsabilité pour faute')
    const corps = JSON.parse(fetchMock.mock.calls.find(([u]) => String(u).endsWith('/chat'))![1].body)
    expect(corps).toMatchObject({ niveau: 'L2', semestre: 4 })
  })

  it('ouvre la source citee et verifie la version en vigueur', async () => {
    await poser('article 1240')
    fireEvent.click(screen.getByRole('button', { name: '[1] Code civil, article 1240' }))
    const panneau = await screen.findByRole('dialog')
    await within(panneau).findByText("Tout fait quelconque de l'homme…")
    fireEvent.click(within(panneau).getByRole('button', { name: 'Vérifier la version en vigueur' }))
    await within(panneau).findByText(/Cette version est en vigueur/)
    fireEvent.keyDown(document, { key: 'Escape' })
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
  })

  it('enregistre une reponse en fiche dans le navigateur', async () => {
    await poser('article 1240')
    fireEvent.click(screen.getByRole('button', { name: /Enregistrer en fiche/ }))
    expect(lireFavoris('etu@exemple.fr').map((f) => f.id)).toEqual(['r-123'])
    fireEvent.click(screen.getByRole('button', { name: /Fiches & révisions/ }))
    expect(await screen.findByText('La responsabilité pour faute')).toBeInTheDocument()
  })

  it('ajoute un cours depuis l assistant (trombone ou glisser-deposer) et le selectionne', async () => {
    const cours = { id: 7, matiere: 'droit_civil', libelle_matiere: 'Droit civil', titre: 'Chapitre 3', fichier: 'chapitre3.pdf',
      pages: 12, passages: 30, statut: 'pret', ajoute_le: '2026-11-12T10:00:00+00:00' }
    let liste: unknown[] = []
    const base = fetchMock.getMockImplementation() as (url: string, init?: RequestInit) => Promise<Response>
    fetchMock.mockImplementation((url: string, init?: RequestInit) => {
      if (url.includes('/cours?') && init?.method === 'POST') {
        liste = [cours]
        return repondre(cours, 201)
      }
      if (url.endsWith('/cours')) return repondre({ cours: liste, maximum: 3, formats: ['.pdf'] })
      return base(url, init)
    })
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: /Assistant IA/ }))
    const pdf = new File(['%PDF'], 'chapitre3.pdf', { type: 'application/pdf' })
    fireEvent.change(screen.getByTestId('ajout-cours'), { target: { files: [pdf] } })
    const panneau = await screen.findByRole('form', { name: 'Ajouter un cours' })
    expect(within(panneau).getByText(/chapitre3\.pdf/)).toBeInTheDocument()
    expect(within(panneau).getByLabelText('Titre')).toHaveValue('chapitre3')
    fireEvent.change(within(panneau).getByLabelText('Matière'), { target: { value: 'droit_civil' } })
    await act(async () => {
      fireEvent.click(within(panneau).getByRole('button', { name: 'Déposer' }))
    })
    const envoi = fetchMock.mock.calls.find(([u, i]) => String(u).includes('/cours?') && i?.method === 'POST')!
    expect(String(envoi[0])).toContain('matiere=droit_civil')
    expect(String(envoi[0])).not.toContain('chapitre3')                     // nom et titre hors de l'adresse
    expect((envoi[1].headers as Record<string, string>)['X-Lexia-Fichier']).toBe('chapitre3.pdf')
    expect(envoi[1].body).toBe(pdf)
    await waitFor(() => expect(screen.getByRole('checkbox', { name: 'Chapitre 3' })).toBeChecked())   // devient le cours de travail
    expect(screen.queryByRole('form', { name: 'Ajouter un cours' })).not.toBeInTheDocument()

    // Glisser-deposer : le meme panneau s'ouvre ; un format non pris en charge est signale
    const zone = screen.getByPlaceholderText(/Quelle notion/).closest('form')!.parentElement!
    const exe = new File(['x'], 'virus.exe')
    await act(async () => {
      fireEvent.drop(zone, { dataTransfer: { types: ['Files'], files: [exe], items: [] } })
    })
    expect(await screen.findByText(/Aucun fichier pris en charge/)).toBeInTheDocument()
  })

  it('interroge plusieurs cours a la fois, y compris un cours en erreur (audit C8 et C10)', async () => {
    const commun = { matiere: 'droit_civil', libelle_matiere: 'Droit civil', fichier: 'c.pdf', pages: 3, passages: 4,
      ajoute_le: '2026-11-12T10:00:00+00:00' }
    const liste = [{ ...commun, id: 7, titre: 'Les contrats', statut: 'pret' },
      { ...commun, id: 8, titre: 'La responsabilité', statut: 'erreur', avertissement: 'Page 2 sans texte (scan ou image).' }]
    const base = fetchMock.getMockImplementation() as (url: string, init?: RequestInit) => Promise<Response>
    fetchMock.mockImplementation((url: string, init?: RequestInit) =>
      url.endsWith('/cours') ? repondre({ cours: liste, maximum: 3, formats: ['.pdf'] }) : base(url, init))
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: /Assistant IA/ }))
    fireEvent.click(await screen.findByRole('checkbox', { name: 'Les contrats' }))
    fireEvent.click(screen.getByRole('checkbox', { name: /La responsabilité \(mots-clés seulement/ }))
    fireEvent.click(screen.getByRole('switch', { name: 'Mes cours seulement' }))
    fireEvent.change(screen.getByLabelText('Votre question'), { target: { value: 'La faute' } })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Envoyer/ }))
    })
    const appel = fetchMock.mock.calls.find(([u]) => String(u).endsWith('/chat'))!
    expect(JSON.parse(appel[1].body as string)).toMatchObject({ cours: [7, 8], avec_officiel: false })
  })

  it('le mode choisi change l invite, les titres de la reponse et enregistre la fiche', async () => {
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: /Assistant IA/ }))
    fireEvent.click(screen.getByRole('radio', { name: 'Fiche' }))
    expect(screen.getByRole('radio', { name: 'Fiche' })).toHaveAttribute('aria-checked', 'true')
    expect(screen.getByText(/enregistrée automatiquement/)).toBeInTheDocument()
    const champ = screen.getByPlaceholderText('Sur quelle notion voulez-vous une fiche ?')
    fireEvent.change(champ, { target: { value: 'le dol' } })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Envoyer/ }))
    })
    expect(await screen.findByText('Règles essentielles')).toBeInTheDocument()
    expect(screen.queryByText('Droit positif')).not.toBeInTheDocument()
    const corps = JSON.parse(fetchMock.mock.calls.find(([u]) => String(u).endsWith('/chat'))![1].body)
    expect(corps.mode).toBe('fiche')
    await waitFor(() => expect(lireFavoris('etu@exemple.fr').map((f) => f.id)).toEqual(['r-123']))   // sans clic sur « Enregistrer »
    expect(screen.getByRole('button', { name: /Enregistrée/ })).toBeInTheDocument()
  })

  it('adresse non confirmee : bandeau et renvoi de l e-mail', async () => {
    emailVerifie = false
    render(<Site />)
    expect(await screen.findByText(/Confirmez votre adresse e-mail/)).toBeInTheDocument()
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Renvoyer/ }))
    })
    expect(await screen.findByText(/Nouvel e-mail envoyé/)).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([u]) => String(u).endsWith('/auth/email/renvoyer'))).toBe(true)
  })

  it('la boite a outils ouvre l assistant dans le bon mode sans envoyer de question', async () => {
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: /Raisonner avec méthode/ }))
    expect(await screen.findByRole('radio', { name: 'Cas pratique' })).toHaveAttribute('aria-checked', 'true')
    expect(fetchMock.mock.calls.some(([u]) => String(u).endsWith('/chat'))).toBe(false)   // rien n'est decompte
  })

  it('creer une fiche depuis Fiches & revisions l enregistre et met l assistant en mode Fiche', async () => {
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: /Fiches & révisions/ }))
    fireEvent.change(screen.getByLabelText(/Nouvelle fiche sur/), { target: { value: 'le dol' } })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Créer la fiche' }))
    })
    await waitFor(() => expect(lireFavoris('etu@exemple.fr')).toHaveLength(1))
    expect(screen.getByRole('radio', { name: 'Fiche' })).toHaveAttribute('aria-checked', 'true')
  })

  it('affiche un message clair si le modele est indisponible', async () => {
    fetchMock.mockImplementation((url: string) =>
      url.endsWith('/chat') ? repondre({ detail: 'Le modèle est momentanément indisponible.' }, 503)
        : url.endsWith('/auth/session') || url.endsWith('/auth/moi') ? repondre(PROFIL) : repondre([]))
    render(<Site />)
    await screen.findByLabelText('Votre question')
    fireEvent.change(screen.getByLabelText('Votre question'), { target: { value: 'article 1240' } })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Envoyer/ }))
    })
    expect(await screen.findByRole('alert')).toHaveTextContent('momentanément indisponible')
    expect(screen.getByRole('button', { name: 'Réessayer' })).toBeInTheDocument()
  })
})

describe('Favoris', () => {
  it('les fiches d un compte ne sont pas visibles depuis un autre compte du meme navigateur', () => {
    const fiche = { id: 'r-a', question: 'le dol', mode: 'fiche' as const, enregistre_le: '2026-11-13', reponse: REPONSE }
    expect(ecrireFavoris([fiche], 'a@exemple.fr')).toBe(true)
    expect(lireFavoris('a@exemple.fr').map((f) => f.id)).toEqual(['r-a'])
    expect(lireFavoris('b@exemple.fr')).toEqual([])
  })

  it('reprend une seule fois les fiches enregistrees avant la separation par compte', () => {
    localStorage.setItem('lexia.favoris.v1', JSON.stringify([{ id: 'ancienne', question: 'q', mode: 'fiche', enregistre_le: 'x', reponse: REPONSE }]))
    expect(lireFavoris('a@exemple.fr').map((f) => f.id)).toEqual(['ancienne'])
    expect(localStorage.getItem('lexia.favoris.v1')).toBeNull()
    expect(lireFavoris('b@exemple.fr')).toEqual([])
  })

  it('l adresse du compte n apparait pas dans le stockage du navigateur', () => {
    localStorage.setItem('lexia.favoris.v1.a@exemple.fr', JSON.stringify([{ id: 'r-a', question: 'q', mode: 'fiche', enregistre_le: 'x', reponse: REPONSE }]))
    expect(lireFavoris('a@exemple.fr').map((f) => f.id)).toEqual(['r-a'])     // reprise de l'ancienne cle
    expect(ecrireFavoris(lireFavoris('a@exemple.fr'), 'a@exemple.fr')).toBe(true)
    const cles = Object.keys(localStorage)
    expect(cles.some((c) => c.includes('exemple.fr'))).toBe(false)
    expect(lireFavoris('b@exemple.fr')).toEqual([])
  })

  it('resiste a un stockage corrompu', () => {
    localStorage.setItem('lexia.favoris.v1', '{pas du json')
    expect(lireFavoris('etu@exemple.fr')).toEqual([])
    expect(ecrireFavoris([], 'etu@exemple.fr')).toBe(true)
  })
})

describe('Audit du 16 novembre 2026', () => {
  it('garde la conversation en passant par Compte, au rechargement, et l oublie a la deconnexion (points 14 et 16)', async () => {
    await poser('article 1240')
    fireEvent.click(screen.getByRole('link', { name: 'Mon compte' }))
    expect(await screen.findByRole('heading', { name: 'etu@exemple.fr' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('link', { name: 'Ouvrir mon espace' }))
    expect(await screen.findByText('La responsabilité pour faute')).toBeInTheDocument()

    // rechargement de l'onglet : la conversation revient
    cleanup()
    render(<Site />)
    expect(await screen.findByText('La responsabilité pour faute')).toBeInTheDocument()
    expect(Object.keys(sessionStorage).some((c) => c.includes('exemple.fr'))).toBe(false)   // pas d'adresse dans les cles

    // deconnexion : plus rien dans l'onglet
    fireEvent.click(screen.getByRole('link', { name: 'Mon compte' }))
    await act(async () => {
      fireEvent.click(await screen.findByRole('button', { name: 'Se déconnecter' }))
    })
    expect(Object.keys(sessionStorage).filter((c) => c.startsWith('lexia.seance'))).toEqual([])
  })

  it('une reponse attendue au rechargement est signalee, pas laissee en attente', async () => {
    fetchMock.mockImplementation((url: string) =>
      url.endsWith('/chat') ? new Promise(() => undefined)
        : url.endsWith('/auth/session') || url.endsWith('/auth/moi') ? repondre(PROFIL) : repondre([]))
    render(<Site />)
    fireEvent.change(await screen.findByLabelText('Votre question'), { target: { value: 'article 1240' } })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Envoyer/ }))
    })
    cleanup()
    render(<Site />)
    expect(await screen.findByRole('alert')).toHaveTextContent('rechargée avant la réponse')
  })

  it('le questionnaire survit a la fermeture, meme pendant la generation (points 9 et 12) ; exemple de theme par matiere (point 8)', async () => {
    let livrer: (r: Response) => void = () => undefined
    const QUIZ = { quiz_id: 'qz-1', format: 'qcm', theme: 'la faute', demande: 1, obtenu: 1, message: '', avertissement: '',
      questions: [{ index: 0, question: 'Quel article fonde la responsabilité pour faute ?', choix: ['1240', '1103'] }], sources: REPONSE.sources }
    const base = fetchMock.getMockImplementation() as (url: string, init?: RequestInit) => Promise<Response>
    fetchMock.mockImplementation((url: string, init?: RequestInit) => {
      if (url.endsWith('/quiz')) return new Promise<Response>((ok) => { livrer = ok })
      if (url.endsWith('/quiz/correct')) return repondre({ quiz_id: 'qz-1', score: 1, total: 1, sources: REPONSE.sources,
        resultats: [{ index: 0, statut: 'correct', explication: 'Article 1240.', sources: [], bonne_reponse: 0 }] })
      return base(url, init)
    })
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: /Mes matières/ }))
    fireEvent.click(await screen.findByRole('button', { name: 'S’entraîner' }))
    const theme = screen.getByLabelText('Thème')
    expect(theme).toHaveAttribute('placeholder', 'Ex. la responsabilité du fait des choses')
    fireEvent.change(theme, { target: { value: 'la faute' } })
    fireEvent.click(screen.getByRole('button', { name: /Générer le questionnaire/ }))
    expect(await screen.findByRole('button', { name: /Génération en cours/ })).toBeInTheDocument()

    // clic hors de la fenetre pendant la generation : elle se ferme (scenario probable du point 9)...
    fireEvent.mouseDown(screen.getByRole('dialog').parentElement!)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await act(async () => {
      livrer(new Response(JSON.stringify(QUIZ), { status: 200, headers: { 'Content-Type': 'application/json' } }))
    })
    // ... mais le questionnaire n'est pas perdu
    expect(await screen.findByText(/Votre questionnaire est prêt/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'S’entraîner' }))
    fireEvent.click(await screen.findByRole('radio', { name: '1240' }))
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Corriger mes réponses' }))
    })
    expect(await screen.findByText('Score : 1 / 1')).toBeInTheDocument()

    // fermer puis rouvrir : la correction est toujours la
    fireEvent.click(screen.getByRole('button', { name: 'Fermer le questionnaire' }))
    fireEvent.click(screen.getByRole('button', { name: 'S’entraîner' }))
    expect(await screen.findByText('Score : 1 / 1')).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: '1240' })).toBeChecked()
  })

  it('fiches : la limite au navigateur est dite a l enregistrement, et elles s exportent en Markdown (point 5)', async () => {
    let exporte: Blob | null = null
    vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: (b: Blob) => { exporte = b; return 'blob:fiche' }, revokeObjectURL: () => undefined }))
    await poser('article 1240')
    fireEvent.click(screen.getByRole('button', { name: /Enregistrer en fiche/ }))
    expect(await screen.findByText(/dans ce navigateur uniquement/)).toHaveAttribute('role', 'status')
    fireEvent.click(screen.getByRole('button', { name: /Fiches & révisions/ }))
    fireEvent.click(await screen.findByRole('button', { name: /Exporter toutes les fiches/ }))
    const texte = await exporte!.text()
    expect(texte).toContain('# La responsabilité pour faute')
    expect(texte).toContain('- Tout fait fautif causant un dommage oblige à réparer. [1]')
    expect(texte).toContain('1. Code civil, article 1240 (Version depuis le 1er octobre 2016) : https://www.legifrance.gouv.fr/codes/article_lc/A1240')
  })

  it('les matieres du catalogue sont dites disponibles, pas suivies (point 1)', async () => {
    render(<Site />)
    expect(await screen.findByText('1 matière disponible')).toBeInTheDocument()
    expect(screen.queryByText(/matières suivies/)).not.toBeInTheDocument()
  })

  it('sources numerotees 1, 2, 3 et intitules courts, dans la reponse comme dans le panneau (points 3 et 4)', async () => {
    const long = (n: string) => `Code civil, Livre III : Des différentes manières, Titre III : Des sources d’obligations, article ${n}`
    const s1 = { ...REPONSE.sources[0], id: 'code_civil:A1240', label: 'S1', entete: long('1240') }
    const s4 = { ...REPONSE.sources[0], id: 'code_civil:A1241', label: 'S4', entete: long('1241') }
    reponseChat = { ...REPONSE, sources: [s1, s4],
      droit_positif: [{ texte: 'Règle 1.', sources: [s1.id] }, { texte: 'Règle 2.', sources: [s4.id] }] }
    const base = fetchMock.getMockImplementation() as (url: string, init?: RequestInit) => Promise<Response>
    fetchMock.mockImplementation((url: string, init?: RequestInit) =>
      url.includes('/sources/') ? repondre({ ...s4, texte: 'Chacun est responsable…', titre: null, meta: {} }) : base(url, init))
    await poser('article 1240')
    expect(screen.getByRole('button', { name: '[2] Code civil · article 1241' })).toBeInTheDocument()
    expect(screen.queryByText(/S4/)).not.toBeInTheDocument()
    expect(screen.getByText('Code civil · article 1241')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '[2] Code civil · article 1241' }))
    const panneau = await screen.findByRole('dialog')
    expect(await within(panneau).findByRole('heading', { name: 'Code civil · article 1241' })).toBeInTheDocument()
    expect(within(panneau).getByText('Classement complet').closest('details')).not.toHaveAttribute('open')
  })

  it('une fiche ouverte n affiche son titre qu une fois (point 6)', async () => {
    await poser('article 1240')
    fireEvent.click(screen.getByRole('button', { name: /Enregistrer en fiche/ }))
    fireEvent.click(screen.getByRole('button', { name: /Fiches & révisions/ }))
    fireEvent.click(await screen.findByRole('button', { name: /^La responsabilité pour faute/ }))
    expect(await screen.findByText('Droit positif')).toBeInTheDocument()
    expect(screen.getAllByText('La responsabilité pour faute')).toHaveLength(1)
  })

  it('saisie multiligne : Maj + Entree passe a la ligne, Entree envoie (point 2)', async () => {
    render(<Site />)
    const champ = await screen.findByLabelText('Votre question')
    expect(champ.tagName).toBe('TEXTAREA')
    fireEvent.change(champ, { target: { value: 'Première ligne\nseconde ligne' } })
    fireEvent.keyDown(champ, { key: 'Enter', shiftKey: true })
    expect(fetchMock.mock.calls.some(([u]) => String(u).endsWith('/chat'))).toBe(false)
    await act(async () => {
      fireEvent.keyDown(champ, { key: 'Enter' })
    })
    await screen.findByText('La responsabilité pour faute')
    const corps = JSON.parse(fetchMock.mock.calls.find(([u]) => String(u).endsWith('/chat'))![1].body)
    expect(corps.question).toBe('Première ligne\nseconde ligne')
  })

  it('matieres : actions avant les textes officiels replies, depot en francais (point 7)', async () => {
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: /Mes matières/ }))
    const textes = await screen.findByText('Textes officiels (1)')
    expect(textes.closest('details')).not.toHaveAttribute('open')
    const carte = textes.closest('section')!
    const ordre = within(carte).getByRole('button', { name: 'Poser une question' }).compareDocumentPosition(textes)
    expect(ordre & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Choisir des fichiers' })).toBeInTheDocument()
    expect(screen.getByText('Aucun fichier choisi')).toBeInTheDocument()
    const pdf = new File(['%PDF'], 'chapitre1.pdf', { type: 'application/pdf' })
    fireEvent.change(document.getElementById('depot-fichier')!, { target: { files: [pdf] } })
    expect(screen.getAllByText('chapitre1.pdf').length).toBeGreaterThan(0)
    expect(screen.getByText('prêt à envoyer')).toBeInTheDocument()
  })

  it('matieres classees par annee, cherchables, avec leurs sources principales (D97)', async () => {
    const MATIERES = [
      { id: 'droit_constitutionnel', libelle: 'Droit constitutionnel', annee: 'L1', mots: ['Ve République'], sources: ['constitution_1958'],
        principales: ['constitution_1958'], noms_sources: { constitution_1958: 'Constitution de 1958' } },
      { id: 'droit_penal', libelle: 'Droit pénal', annee: 'L2', sources: ['code_penal', 'code_procedure_penale'], principales: ['code_penal'],
        noms_sources: { code_penal: 'Code pénal', code_procedure_penale: 'Code de procédure pénale' } },
      { id: 'procedure_penale', libelle: 'Procédure pénale', annee: 'L3', mots: ['garde à vue'],
        sources: ['code_procedure_penale', 'cass_criminelle'], principales: ['code_procedure_penale', 'cass_criminelle'],
        noms_sources: { code_procedure_penale: 'Code de procédure pénale', cass_criminelle: 'Cour de cassation : chambre criminelle' } },
    ]
    const base = fetchMock.getMockImplementation() as (url: string, init?: RequestInit) => Promise<Response>
    fetchMock.mockImplementation((url: string, init?: RequestInit) => url.endsWith('/matieres') ? repondre(MATIERES) : base(url, init))
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: /Mes matières/ }))
    expect(await screen.findByRole('heading', { name: 'Licence 3' })).toBeInTheDocument()
    const carte = screen.getByRole('heading', { name: 'Procédure pénale' }).closest('section')!
    expect(within(carte).getByText('Sources principales : Code de procédure pénale · Cour de cassation : chambre criminelle')).toBeInTheDocument()

    const recherche = screen.getByRole('searchbox', { name: 'Chercher une matière' })
    fireEvent.change(recherche, { target: { value: 'procedure penale' } })
    expect(screen.getByRole('heading', { name: 'Procédure pénale' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Droit pénal' })).toBeInTheDocument()  // par le Code de procédure pénale
    expect(screen.queryByRole('heading', { name: 'Droit constitutionnel' })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'L3' }))
    expect(screen.queryByRole('heading', { name: 'Droit pénal' })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Procédure pénale' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Toutes' }))
    fireEvent.change(recherche, { target: { value: 'histoire du droit' } })
    const vide = screen.getByText(/Aucune matière ne correspond à « histoire du droit »/)
    expect(vide).toHaveTextContent('Lexia couvre le droit français et les traités de l’Union européenne')

    // depuis la carte, l'assistant s'ouvre sur la matiere ; son choix est groupe par annee
    fireEvent.change(recherche, { target: { value: 'garde à vue' } })
    fireEvent.click(screen.getByRole('button', { name: 'Poser une question' }))
    const choix = await screen.findByRole('combobox', { name: 'Matière' })
    expect(choix).toHaveValue('procedure_penale')
    expect([...choix.querySelectorAll('optgroup')].map((g) => g.label)).toEqual(['Licence 1', 'Licence 2', 'Licence 3'])
  })

  it('la page Compte garde la navigation de l espace etudiant (point 14)', async () => {
    window.history.pushState({}, '', '/compte')
    render(<Site />)
    expect(await screen.findByRole('heading', { name: 'etu@exemple.fr' })).toBeInTheDocument()
    const nav = screen.getByRole('navigation', { name: 'Navigation principale' })
    fireEvent.click(within(nav).getByRole('button', { name: /Fiches & révisions/ }))
    expect(await screen.findByRole('heading', { name: 'Vos fiches.' })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/app')
  })

  it('questionnaire lance : le formulaire se replie en une ligne, rouvrable (point 10)', async () => {
    const QUIZ = { quiz_id: 'qz-2', format: 'qcm', theme: 'la faute', demande: 1, obtenu: 1, message: '', avertissement: '',
      questions: [{ index: 0, question: 'Quel article ?', choix: ['1240', '1103'] }], sources: REPONSE.sources }
    const base = fetchMock.getMockImplementation() as (url: string, init?: RequestInit) => Promise<Response>
    fetchMock.mockImplementation((url: string, init?: RequestInit) => (url.endsWith('/quiz') ? repondre(QUIZ) : base(url, init)))
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: /Mes matières/ }))
    fireEvent.click(await screen.findByRole('button', { name: 'S’entraîner' }))
    fireEvent.change(screen.getByLabelText('Thème'), { target: { value: 'la faute' } })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Générer le questionnaire/ }))
    })
    expect(await screen.findByRole('radio', { name: '1240' })).toBeInTheDocument()
    expect(screen.queryByLabelText('Thème')).not.toBeInTheDocument()
    expect(screen.getByText(/1 question · QCM · Droit civil/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Nouveau questionnaire…' }))
    expect(screen.getByLabelText('Thème')).toHaveValue('la faute')
  })

  it('bibliotheque : annales en tete, filtrees sur la matiere en cours (point 13)', async () => {
    const annale = (id: number, matiere: string, libelle: string) => ({ id, titre: `Sujet ${libelle}`, matiere, libelle_matiere: libelle,
      niveau: 'L1', annee: 2025, universite: 'Université test', session: '', url: 'https://exemple.fr/sujet', corrige: false, ajoute_le: '2026-11-01' })
    const base = fetchMock.getMockImplementation() as (url: string, init?: RequestInit) => Promise<Response>
    fetchMock.mockImplementation((url: string, init?: RequestInit) => (url.endsWith('/annales')
      ? repondre({ niveaux: ['L1'], annales: [annale(1, 'droit_civil', 'Droit civil'), annale(2, 'droit_penal', 'Droit pénal')] })
      : base(url, init)))
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: /Mes matières/ }))
    fireEvent.click(await screen.findByRole('button', { name: 'Poser une question' }))   // matiere en cours : droit civil
    fireEvent.click(screen.getByRole('button', { name: /Bibliothèque/ }))
    expect(await screen.findByText('Sujet Droit civil')).toBeInTheDocument()
    expect(screen.queryByText('Sujet Droit pénal')).not.toBeInTheDocument()
    const titres = screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent)
    expect(titres.indexOf('Annales d’examens')).toBeLessThan(titres.indexOf('Sources de confiance'))
  })

  it('bibliotheque : barre de recherche facultative sur les cours recuperes, les annales et les sources', async () => {
    const cours = { id: 'sp-f1', titre: 'Divorce accepté', matiere: 'droit_de_la_famille', libelle_matiere: 'Droit de la famille',
      auteur: 'DILA', source: 'Service Public / DILA', source_url: 'https://exemple.invalid/', url_original: 'https://exemple.invalid/f1',
      historique_url: '', licence: 'etalab-2.0', licence_libelle: 'Licence Ouverte 2.0', licence_url: 'https://exemple.invalid/lo',
      mis_a_jour: '2026-03-01', modifications: '', sections: 3 }
    const dansLeTexte = { ...cours, id: 'sp-f2', titre: 'Prestation compensatoire' }
    const annale = { id: 1, titre: 'Sujet divorce et filiation', matiere: 'droit_de_la_famille', libelle_matiere: 'Droit de la famille',
      niveau: 'L1', annee: 2025, universite: 'Université test', session: '', url: 'https://exemple.fr/sujet', corrige: false, ajoute_le: '2026-11-01' }
    const base = fetchMock.getMockImplementation() as (url: string, init?: RequestInit) => Promise<Response>
    fetchMock.mockImplementation((url: string, init?: RequestInit) => {
      if (url.endsWith('/cours-recuperes')) return repondre({ avertissement: 'a', cours: [cours, dansLeTexte] })
      if (url.endsWith('/cours-recuperes/recherche') && init?.method === 'POST'
          && JSON.parse(String(init.body)).q === 'divorce') return repondre({ cours: ['sp-f1', 'sp-f2'] })
      if (url.endsWith('/annales')) return repondre({ niveaux: ['L1'], annales: [annale] })
      return base(url, init)
    })
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: /Bibliothèque/ }))
    const barre = await screen.findByRole('searchbox', { name: /Rechercher dans la bibliothèque/ })
    expect(screen.queryByText(/Cours récupérés \(/)).not.toBeInTheDocument()   // rien tant qu'on n'ecrit pas
    fireEvent.change(barre, { target: { value: 'divorce' } })
    expect(await screen.findByRole('link', { name: /Divorce accepté/ })).toHaveAttribute('href', '/cours-recuperes?q=Divorce%20accept%C3%A9')
    expect(await screen.findByRole('link', { name: /Prestation compensatoire/ }, { timeout: 2000 })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Sujet divorce et filiation/ })).toHaveAttribute('href', 'https://exemple.fr/sujet')
    expect(screen.getByRole('link', { name: /catalogue des bibliothèques universitaires/ })).toHaveAttribute('href', expect.stringContaining('TRM=divorce'))
    fireEvent.change(barre, { target: { value: 'cassation' } })
    const groupe = (await screen.findByRole('heading', { name: 'Sources officielles' })).closest('section')!
    expect(within(groupe).getByRole('link', { name: /Cour de cassation/ })).toBeInTheDocument()
  })
})

describe('Reponse directe d abord (audit du 16 novembre 2026, point 3)', () => {
  const s2 = { ...REPONSE.sources[0], id: 'code_civil:A1241', label: 'S2', entete: 'Code civil, article 1241' }
  const AVEC_DIRECTE: ReponseChat = {
    ...REPONSE,
    sources: [REPONSE.sources[0], s2],
    reponse_directe: [{ texte: 'On répare le dommage causé par sa faute.', sources: ['code_civil:A1240'] }],
    explication: [
      { texte: 'Il faut une faute, un dommage et un lien de causalité.', sources: [], rubrique: 'Conditions' },
      { texte: 'Un cycliste renverse un piéton par imprudence.', sources: ['code_civil:A1241'], rubrique: 'Exemple' },
    ],
    points_incertains: [{ texte: 'Analyse générale : consultez un professionnel du droit.', sources: [] }],
  }

  it('l essentiel, l exemple et les points d attention d abord ; developpements et sources replies', async () => {
    reponseChat = AVEC_DIRECTE
    await poser('Que dit l’article 1240 ?')
    expect(screen.getByText('L’essentiel')).toBeInTheDocument()
    expect(screen.getByText('On répare le dommage causé par sa faute.')).toBeInTheDocument()
    const exemple = screen.getByText('Un cycliste renverse un piéton par imprudence.')
    expect(exemple.closest('details')).toBeNull()
    expect(screen.getByText(/consultez un professionnel/).closest('details')).toBeNull()
    const repli = screen.getByText('Développements et sources').closest('details')!
    expect(repli).not.toHaveAttribute('open')
    expect(within(repli).getByText('Droit positif')).toBeInTheDocument()
    expect(within(repli).getByText('Conditions')).toBeInTheDocument()
    expect(within(repli).getByText('Sources utilisées')).toBeInTheDocument()
    expect(within(repli).queryByText(/Un cycliste/)).not.toBeInTheDocument()   // l'exemple n'est pas repete
    // numerotation commune : la source de l'exemple garde son numero
    expect(within(exemple.closest('li')!).getByRole('button', { name: '[2] Code civil, article 1241' })).toBeInTheDocument()
  })

  it('sans reponse directe (commentaire, fiche anterieure) : affichage complet, rien de replie', async () => {
    await poser('Que dit l’article 1240 ?')
    expect(screen.queryByText('L’essentiel')).not.toBeInTheDocument()
    expect(screen.queryByText('Développements et sources')).not.toBeInTheDocument()
    expect(screen.getByText('Droit positif').closest('details')).toBeNull()
  })

  it('l export Markdown commence par l essentiel', () => {
    const md = ficheEnMarkdown({ id: 'f1', question: 'Q ?', mode: 'expliquer', enregistre_le: '2026-11-17T10:00:00Z',
      reponse: AVEC_DIRECTE })
    expect(md.indexOf('## L’essentiel')).toBeGreaterThan(0)
    expect(md.indexOf('## L’essentiel')).toBeLessThan(md.indexOf('## Droit positif'))
    expect(md).toContain('- On répare le dommage causé par sa faute. [1]')
    // Contenu genere marque comme tel (audit du 2026-11-23, E11)
    expect(md).toContain('Fiche générée par une intelligence artificielle')
    expect(md.indexOf('intelligence artificielle')).toBeLessThan(md.indexOf('## L’essentiel'))
  })
})

describe('Audit du 18 novembre 2026, lot D', () => {
  it('administration et qrcode charges a la demande, hors du fichier principal (D11)', () => {
    expect(sourceSite).not.toMatch(/^import .*'\.\/site\/Admin'/m)
    expect(sourceSite).toContain("lazy(() => import('./site/Admin')")
    expect(sourceDeuxFacteurs).not.toMatch(/^import .*'qrcode'/m)
    expect(sourceDeuxFacteurs).toContain("await import('qrcode')")
  })

  it('101e fiche : refusee avec un message, la plus ancienne n est pas effacee (D10)', async () => {
    const anciennes = Array.from({ length: 100 }, (_, i) => ({ id: `f${i}`, question: `Q${i}`, mode: 'expliquer' as const,
      enregistre_le: '2026-11-01T10:00:00Z', reponse: { ...REPONSE, reponse_id: `f${i}` } }))
    ecrireFavoris(anciennes, 'etu@exemple.fr')
    await poser('article 1240')
    fireEvent.click(screen.getByRole('button', { name: /Enregistrer en fiche/ }))
    expect(await screen.findByText(/Limite de 100 fiches atteinte/)).toBeInTheDocument()
    expect(lireFavoris('etu@exemple.fr').map((f) => f.id)).toEqual(anciennes.map((f) => f.id))
  })

  it('messages : 502, 504 et 524 traduits, delai d attente cote client (D9)', async () => {
    for (const [status, attendu] of [[502, /redémarre/], [504, /trop de temps/], [524, /trop de temps/]] as const) {
      fetchMock.mockImplementationOnce(() => Promise.resolve(new Response('<html>Bad gateway</html>', { status })))
      await expect(api.matieres()).rejects.toThrow(attendu)
    }
    await api.matieres()
    expect(fetchMock.mock.calls.at(-1)![1].signal).toBeInstanceOf(AbortSignal)
  })

  it('matieres en cours de chargement : pas de faux message d erreur (D9)', async () => {
    const base = fetchMock.getMockImplementation() as (url: string, init?: RequestInit) => Promise<Response>
    fetchMock.mockImplementation((url: string, init?: RequestInit) =>
      url.endsWith('/matieres') ? new Promise<Response>(() => undefined) : base(url, init))
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: /Mes matières/ }))
    expect(await screen.findByText(/Chargement des matières/)).toBeInTheDocument()
    expect(screen.queryByText(/API Lexia est démarrée/)).not.toBeInTheDocument()
  })

  it('questionnaire : limite atteinte avec lien vers les formules, remplacement confirme (D9)', async () => {
    const QUIZ = { quiz_id: 'qz-3', format: 'qcm', theme: 'la faute', demande: 1, obtenu: 1, message: '', avertissement: '',
      questions: [{ index: 0, question: 'Quel article ?', choix: ['1240', '1103'] }], sources: REPONSE.sources }
    let limite = false
    const base = fetchMock.getMockImplementation() as (url: string, init?: RequestInit) => Promise<Response>
    fetchMock.mockImplementation((url: string, init?: RequestInit) => (url.endsWith('/quiz')
      ? (limite ? repondre({ detail: 'Limite du jour atteinte.' }, 402) : repondre(QUIZ)) : base(url, init)))
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: /Mes matières/ }))
    fireEvent.click(await screen.findByRole('button', { name: 'S’entraîner' }))
    fireEvent.change(screen.getByLabelText('Thème'), { target: { value: 'la faute' } })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Générer le questionnaire/ }))
    })
    fireEvent.click(await screen.findByRole('radio', { name: '1240' }))
    fireEvent.click(screen.getByRole('button', { name: 'Nouveau questionnaire…' }))
    const confirmer = vi.spyOn(window, 'confirm').mockReturnValue(false)
    fireEvent.click(screen.getByRole('button', { name: /Générer un nouveau questionnaire/ }))
    expect(confirmer).toHaveBeenCalled()
    expect(screen.getByRole('radio', { name: '1240' })).toBeChecked()       // refus : rien n'est efface
    confirmer.mockReturnValue(true)
    limite = true
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Générer un nouveau questionnaire/ }))
    })
    expect(await screen.findByText('Limite du jour atteinte.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Voir les formules' })).toHaveAttribute('href', '/tarifs')
    confirmer.mockRestore()
  })

  it('accessibilite : citation nommee, Oui/Non de 24 px, avertissement lisible, bouton desactive explique (D8)', async () => {
    render(<Site />)
    const envoyer = await screen.findByRole('button', { name: /Envoyer/ })
    // bouton actif, la raison est dite au clic (WEB-10)
    fireEvent.change(screen.getByLabelText('Votre question'), { target: { value: 'ab' } })
    fireEvent.click(envoyer)
    expect(screen.getByRole('alert')).toHaveTextContent('Écrivez au moins 3 caractères.')
    fireEvent.change(screen.getByLabelText('Votre question'), { target: { value: 'Que dit l’article 1240 ?' } })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Envoyer/ }))
    })
    await screen.findByText('La responsabilité pour faute')
    expect(screen.getByRole('button', { name: '[1] Code civil, article 1240' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Oui' })).toHaveClass('min-h-6')
    expect(screen.getByText(/Lexia est un outil d’étude|Lexia est un outil d'étude/)).toHaveClass('text-[12px]')
  })

  it('mobile : libelles visibles dans la barre du bas, questions restantes affichees, champs a 16 px (D7)', async () => {
    render(<Site />)
    const fiches = await screen.findByRole('button', { name: 'Fiches & révisions' })
    expect([...fiches.querySelectorAll('span')].some((s) => s.textContent === 'Fiches' && !s.className.includes('sr-only'))).toBe(true)
    const compte = await screen.findByTitle('Mon compte')
    expect(compte).toHaveTextContent(/7\s*question/)
    expect(compte.className.split(' ')).not.toContain('hidden')
    expect(css).toMatch(/@media \(pointer: coarse\)[^}]*textarea \{\s*font-size: 16px/)
  })

  it('ecran tactile : Entree va a la ligne, seul le bouton envoie (audit mobile)', async () => {
    const original = window.matchMedia
    window.matchMedia = ((q: string) => ({ matches: q === '(pointer: coarse)', media: q })) as unknown as typeof window.matchMedia
    try {
      render(<Site />)
      const champ = await screen.findByLabelText('Votre question')
      fireEvent.change(champ, { target: { value: 'Première ligne' } })
      const suivi = fireEvent.keyDown(champ, { key: 'Enter' })
      expect(suivi).toBe(true)  // retour a la ligne laisse au navigateur
      expect(fetchMock.mock.calls.some(([u]) => String(u).endsWith('/chat'))).toBe(false)
    } finally {
      window.matchMedia = original
    }
  })

  it('mobile : barre du bas au-dessus de la barre d accueil, masquee pendant la saisie (audit mobile)', async () => {
    render(<Site />)
    const barre = (await screen.findByRole('navigation', { name: 'Navigation principale' })).closest('aside')!
    expect(barre).toHaveAttribute('data-barre-bas')
    expect(barre.className).toContain('env(safe-area-inset-bottom)')
    expect(css).toMatch(/textarea\):focus\) \[data-barre-bas\] \{\s*display: none/)
  })

  it('une erreur passagere du serveur ne deconnecte pas l etudiant (D3)', async () => {
    const normal = fetchMock.getMockImplementation() as (url: string) => Promise<Response>
    let panne = false
    fetchMock.mockImplementation((url: string) =>
      panne && url.endsWith('/auth/session') ? repondre({ detail: 'Bad Gateway' }, 502) : normal(url))
    render(<Site />)
    await screen.findByLabelText('Votre question')
    panne = true
    fireEvent.change(screen.getByLabelText('Votre question'), { target: { value: 'Que dit l’article 1240 ?' } })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Envoyer/ }))
    })
    await screen.findByText('La responsabilité pour faute')
    await waitFor(() => expect(fetchMock.mock.calls.filter(([u]) => String(u).endsWith('/auth/session')).length).toBeGreaterThan(1))
    expect(window.location.pathname).toBe('/app')
    expect(screen.getByLabelText('Votre question')).toBeInTheDocument()
  })
})

describe('Recette du 20 novembre 2026', () => {
  it('changer de vue ramene en haut de la page (D-3)', async () => {
    const defiler = vi.fn()
    vi.stubGlobal('scrollTo', defiler)
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: /Mes matières/ }))
    expect(defiler).toHaveBeenCalledWith(0, 0)
    defiler.mockClear()
    fireEvent.click(screen.getByRole('button', { name: /Mes matières/ }))   // meme vue : on ne bouge pas
    expect(defiler).not.toHaveBeenCalled()
  })

  it('lien d evitement vers le contenu, premier element du clavier (D-9)', async () => {
    render(<Site />)
    const lien = await screen.findByRole('link', { name: 'Aller au contenu' })
    const contenu = document.getElementById('contenu')!
    expect(contenu.tagName).toBe('MAIN')
    expect(contenu).toHaveAttribute('tabindex', '-1')
    // Avant la navigation principale dans l'ordre du document.
    const nav = screen.getByRole('navigation', { name: 'Navigation principale' })
    expect(lien.compareDocumentPosition(nav) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    fireEvent.click(lien)
    expect(document.activeElement).toBe(contenu)
  })

  it('mobile : l en-tete tient dans l ecran, le titre se tronque et le rond du compte ne retrecit pas (D-2)', async () => {
    window.history.pushState({}, '', '/compte')
    render(<Site />)
    const rond = await screen.findByRole('link', { name: 'Mon compte' })
    const entete = rond.closest('header')!
    const [titre, actions] = [...entete.children] as HTMLElement[]
    expect(titre.className.split(' ')).toEqual(expect.arrayContaining(['min-w-0', 'truncate']))
    expect(actions.className.split(' ')).toContain('shrink-0')
    expect(rond.className.split(' ')).toContain('shrink-0')
  })
})

describe('Liens internes (D4)', () => {
  it('un lien target="_blank" s ouvre dans un nouvel onglet, pas dans la page', async () => {
    const { RouteurProvider, Lien } = await import('./lib/router')
    render(<RouteurProvider><Lien href="/cgu" target="_blank">CGU</Lien></RouteurProvider>)
    const suivi = fireEvent.click(screen.getByRole('link', { name: 'CGU' }))
    expect(suivi).toBe(true)                       // navigation du navigateur non empechee
    expect(window.location.pathname).toBe('/app')
  })
})

describe('Personnalisation (D100, D102)', () => {
  const avecProfil = (extra: Record<string, unknown>) => {
    const normal = fetchMock.getMockImplementation() as (url: string) => Promise<Response>
    fetchMock.mockImplementation((url: string, init?: RequestInit) => {
      if (url.endsWith('/auth/session') || url.endsWith('/auth/moi')) return repondre({ ...PROFIL, ...extra })
      if (url.endsWith('/auth/identite')) {
        const { prenom, nom } = JSON.parse(String(init?.body))
        return repondre({ ...PROFIL, ...extra, prenom, nom })
      }
      return normal(url)
    })
  }

  it('salue par le prenom selon l heure et dit les questions restantes', async () => {
    avecProfil({ prenom: 'Léa', nom: 'Martin' })
    render(<Site />)
    expect(await screen.findByRole('heading', { level: 1, name: /^(Bonjour|Bonsoir), Léa\.$/ })).toBeInTheDocument()
    expect(screen.queryByText(/Ajoutez votre prénom et votre nom/)).not.toBeInTheDocument()
    expect(screen.getByText(/Il vous reste 7 questions aujourd’hui\./)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Mon compte' })).toHaveTextContent('L')
  })

  it('compte ancien sans prenom : salutation seule, jamais l adresse, invitation a completer sans blocage', async () => {
    avecProfil({ prenom: null, nom: null })
    render(<Site />)
    const titre = await screen.findByRole('heading', { level: 1, name: /^(Bonjour|Bonsoir)\.$/ })
    expect(titre).not.toHaveTextContent('etu')
    expect(screen.getByText(/Ajoutez votre prénom et votre nom/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Compléter dans Mon compte' })).toHaveAttribute('href', '/compte')
    expect(screen.getByLabelText('Votre question')).toBeEnabled()
  })

  it('un prenom avec du HTML est affiche comme du texte', async () => {
    avecProfil({ prenom: '<img src=x onerror=alert(1)>' })
    render(<Site />)
    const titre = await screen.findByRole('heading', { level: 1, name: /<img src=x/ })
    expect(titre.querySelector('img')).toBeNull()
  })

  it('reprend la derniere matiere et propose de reprendre la derniere fiche', async () => {
    localStorage.setItem(`lexia.matiere.v1.${empreinte('etu@exemple.fr')}`, 'droit_civil')
    ecrireFavoris([{ id: 'r-1', question: 'La responsabilité du fait des choses', mode: 'fiche', enregistre_le: '2026-11-17T10:00:00Z', reponse: REPONSE }], 'etu@exemple.fr')
    render(<Site />)
    expect(await screen.findByText('Droit civil · L1 · Semestre 1')).toBeInTheDocument()
    expect(screen.getByText('Dernière fiche : « La responsabilité du fait des choses »')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Revoir' }))
    expect(await screen.findByRole('heading', { name: 'Vos fiches.' })).toBeInTheDocument()
  })

  it('Mon compte : prenom et nom modifiables, jamais vides', async () => {
    avecProfil({ prenom: null, nom: null })
    window.history.pushState({}, '', '/compte')
    render(<Site />)
    const prenom = await screen.findByLabelText('Prénom')
    const enregistrer = screen.getByRole('button', { name: 'Enregistrer' })
    fireEvent.change(prenom, { target: { value: 'Léa' } })
    expect(enregistrer).toBeDisabled() // nom manquant
    fireEvent.change(screen.getByLabelText('Nom'), { target: { value: 'Martin' } })
    await act(async () => {
      fireEvent.click(enregistrer)
    })
    expect(await screen.findByText('Prénom et nom enregistrés.')).toBeInTheDocument()
    const appel = fetchMock.mock.calls.find(([u]) => String(u).endsWith('/auth/identite'))!
    expect(JSON.parse(String(appel[1].body))).toEqual({ prenom: 'Léa', nom: 'Martin' })
    fireEvent.change(prenom, { target: { value: ' ' } })
    expect(enregistrer).toBeDisabled()
  })
})

describe('Depots de cours, version 2 (D107)', () => {
  const COURS = { id: 7, matiere: 'droit_civil', libelle_matiere: 'Droit civil', titre: 'Chapitre 3', fichier: 'chapitre3.pdf',
    pages: 12, passages: 30, statut: 'pret', ajoute_le: '2026-11-12T10:00:00+00:00' }

  /** XMLHttpRequest simule : progression de l'envoi, puis la reponse donnee. */
  function simulerEnvoi(reponse: (nom: string) => { status: number; corps: unknown }) {
    const envois: { url: string; entetes: Record<string, string>; corps: unknown }[] = []
    class FauxXHR {
      upload: { onprogress?: (e: { lengthComputable: boolean; loaded: number; total: number }) => void; onload?: () => void } = {}
      onload?: () => void
      onerror?: () => void
      ontimeout?: () => void
      timeout = 0
      status = 0
      responseText = ''
      private url = ''
      private entetes: Record<string, string> = {}
      open(_m: string, url: string) { this.url = url }
      setRequestHeader(k: string, v: string) { this.entetes[k] = v }
      send(corps: unknown) {
        envois.push({ url: this.url, entetes: this.entetes, corps })
        const r = reponse(decodeURIComponent(this.entetes['X-Lexia-Fichier']))
        setTimeout(() => {
          this.upload.onprogress?.({ lengthComputable: true, loaded: 50, total: 100 })
          this.upload.onload?.()
          this.status = r.status
          this.responseText = JSON.stringify(r.corps)
          this.onload?.()
        }, 0)
      }
    }
    vi.stubGlobal('XMLHttpRequest', FauxXHR)
    return envois
  }

  it('depose plusieurs fichiers avec progression et refuse clairement format et taille avant l envoi', async () => {
    const envois = simulerEnvoi((nom) => nom === 'scan.pdf'
      ? { status: 422, corps: { detail: 'Ce document scanné est illisible : vérifiez que le scan est net.' } }
      : { status: 201, corps: { ...COURS, avertissement: 'Page 2 lue par reconnaissance de caractères (scan) : vérifiez le texte dans l’aperçu.' } })
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: /Mes matières/ }))
    const fichiers = [
      new File(['%PDF'], 'chapitre3.pdf', { type: 'application/pdf' }),
      new File(['%PDF'], 'scan.pdf', { type: 'application/pdf' }),
      new File(['x'], 'cours.doc'),
      new File([new Uint8Array(21 * 1024 * 1024)], 'enorme.pdf'),
      new File(['x'], 'photo.heic'),
    ]
    fireEvent.change(screen.getByTestId('depot-fichier'), { target: { files: fichiers } })
    const liste = screen.getByRole('list', { name: 'Fichiers à déposer' })
    expect(within(liste).getByText(/ancien format Word \(\.doc\) : ouvrez-le puis enregistrez-le en \.docx/)).toBeInTheDocument()
    expect(within(liste).getByText(/fichier trop volumineux \(21,0 Mo, 20 Mo au plus\)/)).toBeInTheDocument()
    expect(within(liste).getByText(/photo HEIC : enregistrez-la en JPEG/)).toBeInTheDocument()
    expect(screen.queryByLabelText('Titre (facultatif)')).not.toBeInTheDocument()   // plusieurs fichiers : leurs noms
    fireEvent.change(screen.getByLabelText('Matière'), { target: { value: 'droit_civil' } })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Déposer 2 cours' }))
    })
    expect(await within(liste).findByText(/déposé \(12 pages, 30 passages\)\. Page 2 lue par reconnaissance/)).toBeInTheDocument()
    expect(await within(liste).findByText(/Ce document scanné est illisible/)).toBeInTheDocument()
    expect(envois.map((e) => e.entetes['X-Lexia-Titre'])).toEqual(['chapitre3', 'scan'])
  })

  it('plusieurs fichiers de meme nom : titres distingues par le format (recette du 2026-11-20, D-10)', async () => {
    const envois = simulerEnvoi(() => ({ status: 201, corps: COURS }))
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: /Mes matières/ }))
    fireEvent.change(screen.getByTestId('depot-fichier'), { target: { files: [
      new File(['%PDF'], 'cours-contrats.pdf', { type: 'application/pdf' }), new File(['x'], 'cours-contrats.docx'),
      new File(['x'], 'cours-contrats.rtf')] } })
    fireEvent.change(screen.getByLabelText('Matière'), { target: { value: 'droit_civil' } })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Déposer 3 cours' }))
    })
    await waitFor(() => expect(envois).toHaveLength(3))
    expect(envois.map((e) => decodeURIComponent(e.entetes['X-Lexia-Titre'])))
      .toEqual(['cours-contrats (PDF)', 'cours-contrats (DOCX)', 'cours-contrats (RTF)'])
    expect(envois[0].url).toContain('matiere=droit_civil')
    expect(envois[0].url).not.toContain('chapitre3')
  })

  it('depot : bouton actif sans fichier ni matiere, la raison est dite au clic (audit du 2026-11-23, D8)', async () => {
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: /Mes matières/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Déposer' }))
    expect(screen.getByText('Choisissez d’abord un ou plusieurs fichiers.')).toBeInTheDocument()
    fireEvent.change(screen.getByTestId('depot-fichier'), { target: { files: [new File(['x'], 'photo.jpg', { type: 'image/jpeg' })] } })
    fireEvent.click(screen.getByRole('button', { name: 'Déposer' }))
    expect(screen.getByText('Choisissez la matière du cours.')).toBeInTheDocument()
  })

  it('montre la progression de l envoi puis la lecture du fichier', async () => {
    simulerEnvoi(() => ({ status: 201, corps: COURS }))
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: /Mes matières/ }))
    fireEvent.change(screen.getByTestId('depot-fichier'), { target: { files: [new File(['x'], 'photo.jpg', { type: 'image/jpeg' })] } })
    expect(screen.getByLabelText('Titre (facultatif)')).toHaveValue('photo')
    fireEvent.change(screen.getByLabelText('Matière'), { target: { value: 'droit_civil' } })
    fireEvent.click(screen.getByRole('button', { name: 'Déposer' }))
    expect(screen.getByRole('progressbar', { name: 'Dépôt de photo.jpg' })).toHaveAttribute('aria-valuenow', '0')
    expect(await screen.findByText(/déposé \(12 pages, 30 passages\)/)).toBeInTheDocument()
  })

  it('apercu du texte lu, puis renommer et changer de matiere', async () => {
    const base = fetchMock.getMockImplementation() as (url: string, init?: RequestInit) => Promise<Response>
    fetchMock.mockImplementation((url: string, init?: RequestInit) => {
      if (url.endsWith('/cours')) return repondre({ cours: [COURS], maximum: 3, formats: ['.pdf'] })
      if (url.endsWith('/cours/7/apercu')) return repondre({ ...COURS, apercu: [{ page: 1, page_fin: 2, texte: 'Le dol est une manoeuvre.' }] })
      if (url.endsWith('/cours/7/modifier')) return repondre({ ...COURS, titre: 'Les vices' })
      return base(url, init)
    })
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: /Mes matières/ }))
    expect(await screen.findByText(/12 pages · 30 passages · prêt/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Aperçu' }))
    const apercu = await screen.findByRole('region', { name: 'Aperçu de « Chapitre 3 »' })
    expect(within(apercu).getByText('Le dol est une manoeuvre.')).toBeInTheDocument()
    expect(within(apercu).getByText('p. 1 à 2')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Modifier' }))
    const formulaire = screen.getByRole('form', { name: 'Modifier « Chapitre 3 »' })
    fireEvent.change(within(formulaire).getByLabelText('Titre'), { target: { value: ' Les vices ' } })
    await act(async () => {
      fireEvent.click(within(formulaire).getByRole('button', { name: 'Enregistrer' }))
    })
    const appel = fetchMock.mock.calls.find(([u]) => String(u).endsWith('/cours/7/modifier'))!
    expect(JSON.parse(String(appel[1].body))).toEqual({ titre: 'Les vices', matiere: 'droit_civil' })
    await waitFor(() => expect(screen.queryByRole('form', { name: 'Modifier « Chapitre 3 »' })).not.toBeInTheDocument())
  })

  it('depot reussi avec un avertissement (scan lu par OCR) : le formulaire se ferme (recette du 2026-11-23, R-7)', async () => {
    const lu = { ...COURS, avertissement: 'Page 1 lue par reconnaissance de caractères.' }
    let liste: unknown[] = []
    const base = fetchMock.getMockImplementation() as (url: string, init?: RequestInit) => Promise<Response>
    fetchMock.mockImplementation((url: string, init?: RequestInit) => {
      if (url.includes('/cours?') && init?.method === 'POST') {
        liste = [lu]
        return repondre(lu, 201)
      }
      if (url.endsWith('/cours')) return repondre({ cours: liste, maximum: 3, formats: ['.pdf'] })
      return base(url, init)
    })
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: /Assistant IA/ }))
    fireEvent.change(screen.getByTestId('ajout-cours'), { target: { files: [new File(['%PDF'], 'scan.pdf', { type: 'application/pdf' })] } })
    const panneau = await screen.findByRole('form', { name: 'Ajouter un cours' })
    fireEvent.change(within(panneau).getByLabelText('Matière'), { target: { value: 'droit_civil' } })
    await act(async () => {
      fireEvent.click(within(panneau).getByRole('button', { name: 'Déposer' }))
    })
    await waitFor(() => expect(screen.queryByRole('form', { name: 'Ajouter un cours' })).not.toBeInTheDocument())
    expect(await screen.findByText(/Cours ajouté.*Page 1 lue par reconnaissance de caractères/)).toBeInTheDocument()
  })

  it('retirer un cours demande un second clic, sans fenetre du navigateur (recette du 2026-11-23, R-8)', async () => {
    const confirmer = vi.spyOn(window, 'confirm')
    const base = fetchMock.getMockImplementation() as (url: string, init?: RequestInit) => Promise<Response>
    fetchMock.mockImplementation((url: string, init?: RequestInit) => {
      if (url.endsWith('/cours')) return repondre({ cours: [COURS], maximum: 3, formats: ['.pdf'] })
      if (url.endsWith('/cours/7/supprimer')) return repondre(null, 204)
      return base(url, init)
    })
    render(<Site />)
    fireEvent.click(await screen.findByRole('button', { name: /Mes matières/ }))
    await screen.findByText(/12 pages · 30 passages · prêt/)
    fireEvent.click(screen.getByRole('button', { name: 'Retirer le cours « Chapitre 3 »' }))
    expect(confirmer).not.toHaveBeenCalled()
    expect(fetchMock.mock.calls.some(([u]) => String(u).endsWith('/cours/7/supprimer'))).toBe(false)
    const confirmation = screen.getByRole('button', { name: 'Confirmer le retrait du cours « Chapitre 3 »' })
    expect(confirmation).toHaveTextContent('Confirmer le retrait')
    await act(async () => {
      fireEvent.click(confirmation)
    })
    expect(fetchMock.mock.calls.some(([u]) => String(u).endsWith('/cours/7/supprimer'))).toBe(true)
    confirmer.mockRestore()
  })
})
