import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
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

beforeEach(() => {
  emailVerifie = true
  localStorage.clear()
  window.history.pushState({}, '', '/app')
  fetchMock = vi.fn((url: string) => {
    if (url.endsWith('/auth/session') || url.endsWith('/auth/moi')) return repondre({ ...PROFIL, email_verifie: emailVerifie })
    if (url.endsWith('/auth/email/renvoyer')) return repondre({ envoye: true }, 202)
    if (url.endsWith('/config')) return repondre({ comptes: true, contact_email: null })
    if (url.endsWith('/matieres')) return repondre([{ id: 'droit_civil', libelle: 'Droit civil', sources: ['code_civil'] }])
    if (url.endsWith('/chat')) return repondre(REPONSE)
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
    expect(screen.getByRole('button', { name: '[S1]' })).toBeInTheDocument()
    expect(screen.getByText(/1 élément\(s\) non vérifiable\(s\) retiré\(s\)/)).toBeInTheDocument()
    const corps = JSON.parse(fetchMock.mock.calls.find(([u]) => String(u).endsWith('/chat'))![1].body)
    expect(corps).toMatchObject({ question: 'Que dit l’article 1240 ?', mode: 'expliquer', niveau: 'L1', semestre: 1 })
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
    fireEvent.click(screen.getByRole('button', { name: '[S1]' }))
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
    expect(lireFavoris().map((f) => f.id)).toEqual(['r-123'])
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
    await waitFor(() => expect(lireFavoris().map((f) => f.id)).toEqual(['r-123']))   // sans clic sur « Enregistrer »
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
    await waitFor(() => expect(lireFavoris()).toHaveLength(1))
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
  it('resiste a un stockage corrompu', () => {
    localStorage.setItem('lexia.favoris.v1', '{pas du json')
    expect(lireFavoris()).toEqual([])
    expect(ecrireFavoris([])).toBe(true)
  })
})
