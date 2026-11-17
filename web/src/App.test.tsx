import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Site from './Site'
import type { ReponseChat } from './lib/api'
import { ecrireFavoris, lireFavoris } from './lib/favoris'

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
    expect(screen.getByRole('button', { name: '[1]' })).toBeInTheDocument()
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
    expect(screen.getAllByRole('button', { name: '[1]' })).toHaveLength(3)
  })

  it('propose les six semestres et envoie le semestre choisi', async () => {
    render(<Site />)
    const choix = await screen.findByLabelText('Choisir le semestre')
    expect(within(choix).getAllByRole('option').map((o) => o.textContent)).toEqual([
      'L1 · Semestre 1', 'L1 · Semestre 2', 'L2 · Semestre 3', 'L2 · Semestre 4', 'L3 · Semestre 5', 'L3 · Semestre 6'])
    fireEvent.change(choix, { target: { value: '4' } })
    expect(localStorage.getItem('lexia.semestre.v1')).toBe('4')
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
    fireEvent.click(screen.getByRole('button', { name: '[1]' }))
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
    await waitFor(() => expect(screen.getByLabelText('Mon cours')).toHaveValue('7'))   // devient le cours de travail
    expect(screen.queryByRole('form', { name: 'Ajouter un cours' })).not.toBeInTheDocument()

    // Glisser-deposer : le meme panneau s'ouvre ; un format non pris en charge est signale
    const zone = screen.getByPlaceholderText(/Quelle notion/).closest('form')!.parentElement!
    const exe = new File(['x'], 'virus.exe')
    await act(async () => {
      fireEvent.drop(zone, { dataTransfer: { types: ['Files'], files: [exe], items: [] } })
    })
    expect(await screen.findByText(/Aucun fichier pris en charge/)).toBeInTheDocument()
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
    expect(await screen.findByRole('status')).toHaveTextContent('dans ce navigateur uniquement')
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
    expect(screen.getByRole('button', { name: '[2]' })).toBeInTheDocument()
    expect(screen.queryByText(/S4/)).not.toBeInTheDocument()
    expect(screen.getByText('Code civil · article 1241')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '[2]' }))
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
    expect(screen.getByRole('button', { name: 'Choisir un fichier' })).toBeInTheDocument()
    expect(screen.getByText('Aucun fichier choisi')).toBeInTheDocument()
    const pdf = new File(['%PDF'], 'chapitre1.pdf', { type: 'application/pdf' })
    fireEvent.change(document.getElementById('depot-fichier')!, { target: { files: [pdf] } })
    expect(screen.getByText('chapitre1.pdf')).toBeInTheDocument()
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
})
