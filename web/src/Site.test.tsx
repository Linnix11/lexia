import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Site from './Site'

const FORMULES = [
  { id: 'gratuit', nom: 'Gratuit', prix_mensuel_euros: 0, questions_par_jour: 10, quiz_par_jour: 2, description: 'd', avantages: ['10 questions par jour'] },
  { id: 'etudiant', nom: 'Étudiant', prix_mensuel_euros: 4.99, questions_par_jour: 100, quiz_par_jour: 20, description: 'd', avantages: ['100 questions par jour'] },
  { id: 'intensif', nom: 'Intensif', prix_mensuel_euros: 9.99, questions_par_jour: 300, quiz_par_jour: 100, description: 'd', avantages: ['300 questions par jour'] },
]
const PROFIL = { email: 'etu@exemple.fr', cree_le: '2026-11-11T10:00:00+00:00', formule_fin: null, formule: FORMULES[0],
  usage: { jour: '2026-11-11', questions: 10, quiz: 0 }, admin: false }

const json = (corps: unknown, status = 200) =>
  Promise.resolve(new Response(status === 204 ? null : JSON.stringify(corps), { status, headers: { 'Content-Type': 'application/json' } }))

const STATS = {
  comptes: { total: 3, par_formule: { gratuit: 2, etudiant: 1, intensif: 0 }, payants_actifs: 1, formules_expirees: 0, nouveaux_7j: 2, nouveaux_30j: 3 },
  revenu_mensuel_estime: 4.99,
  aujourd_hui: { jour: '2026-11-11', questions: 7, quiz: 1, actifs: 2, inscriptions: 1 },
  serie: Array.from({ length: 30 }, (_, i) => ({ jour: `2026-10-${String(13 + (i % 18)).padStart(2, '0')}`, questions: i, quiz: 0, actifs: 1, inscriptions: 0 })),
  formules: FORMULES,
  activite: { dernieres_24h: { questions: 7, quiz: 1, statuts: { reponse: 6, abstention: 1 }, duree_moyenne_ms: 9000, duree_p95_ms: 14000, erreurs_modele: 0, recherche_hybride: 7 },
    questions_7j: 20, derniere_erreur: null, retours: { utiles: 3, pas_utiles: 1, motifs: {} } },
}
const CLIENTS = [{ id: 2, email: 'etu@exemple.fr', admin: false, formule: 'etudiant', formule_enregistree: 'etudiant', formule_fin: '2026-12-12',
  cree_le: '2026-11-10T10:00:00+00:00', questions_aujourdhui: 4, quiz_aujourdhui: 0, questions_30j: 40, derniere_activite: '2026-11-11', limite_questions: 100 }]
const SERVEUR = { version: 'abc1234', demarre_le: '2026-11-11T10:00:00+00:00', uptime_service_s: 3600, uptime_systeme_s: 86400, charge: [0.1, 0.2, 0.3],
  processeurs: 2, memoire_service: 2e9, memoire_systeme: { total: 8e9, disponible: 6e9 }, disque: { total: 1e11, libre: 9e10 }, python: '3.12.3',
  systeme: 'Linux 6.8', index: { moteur: 'local', passages: 45277, embeddings: 41779, couverture: 1 }, modeles: { generation: ['gemini'] }, etat_modele: 'ok' }

let admin = false
let deuxFacteurs = true
let connecte = false
let fetchMock: ReturnType<typeof vi.fn>

beforeEach(() => {
  connecte = false
  admin = false
  deuxFacteurs = true
  localStorage.clear()
  fetchMock = vi.fn((url: string) => {
    if (url.endsWith('/auth/session') || url.endsWith('/auth/moi')) return connecte ? json({ ...PROFIL, admin, double_authentification: admin && deuxFacteurs }) : json(null)
    if (url.includes('/admin/stats')) return json(STATS)
    if (url.includes('/admin/clients')) return json(CLIENTS)
    if (url.includes('/admin/activite')) return json({ requetes: [], erreurs: [] })
    if (url.includes('/admin/serveur')) return json(SERVEUR)
    if (url.endsWith('/auth/inscription')) {
      connecte = true
      return json(PROFIL, 201)
    }
    if (url.endsWith('/auth/connexion')) return json({ double_authentification_requise: true, jeton: 'j1' })
    // Le lien confirme l'adresse sans ouvrir de session : profil seulement si deja connecte.
    if (url.endsWith('/auth/email/verifier')) return json(connecte ? { ...PROFIL, email_verifie: true } : null)
    if (url.endsWith('/auth/email/renvoyer')) return json({ envoye: true }, 202)
    if (url.endsWith('/auth/mot-de-passe/oubli')) return json({ envoye: true }, 202)
    if (url.endsWith('/auth/mot-de-passe/nouveau')) return json({ modifie: true })
    if (url.endsWith('/auth/connexion/code')) {
      connecte = true
      return json({ ...PROFIL, double_authentification: true })
    }
    if (url.endsWith('/config')) return json({ comptes: true, contact_email: 'contact@exemple.fr' })
    if (url.endsWith('/formules')) return json(FORMULES)
    if (url.endsWith('/matieres')) return json([])
    if (url.endsWith('/chat')) return json({ detail: 'Limite du jour atteinte : 10 questions avec la formule Gratuit.' }, 402)
    return json({}, 404)
  })
  vi.stubGlobal('fetch', fetchMock)
})
afterEach(() => vi.unstubAllGlobals())

const aller = (chemin: string) => window.history.pushState({}, '', chemin)

describe('Site', () => {
  it('redirige vers la connexion si on ouvre le panel sans compte', async () => {
    aller('/app')
    render(<Site />)
    expect(await screen.findByRole('heading', { name: 'Connexion' })).toBeInTheDocument()
    expect(window.location.pathname).toBe('/connexion')
  })

  it('affiche les trois formules et la demande par e-mail', async () => {
    aller('/tarifs')
    render(<Site />)
    expect(await screen.findByRole('heading', { name: 'Étudiant' })).toBeInTheDocument()
    expect(screen.getByText('4,99 €')).toBeInTheDocument()
    const lien = screen.getAllByRole('link', { name: 'Demander cette formule' })[0]
    expect(lien.getAttribute('href')).toMatch(/^mailto:contact@exemple\.fr/)
  })

  it('tarifs : l introduction cite les cours deposes et l activation manuelle est dite sous le bouton (point 15)', async () => {
    aller('/tarifs')
    render(<Site />)
    await screen.findByRole('heading', { name: 'Étudiant' })
    expect(screen.getByText(/nombre de cours que vous pouvez déposer/)).toBeInTheDocument()
    expect(screen.queryByText(/seule la quantité/)).not.toBeInTheDocument()
    const lien = screen.getAllByRole('link', { name: 'Demander cette formule' })[0]
    expect(lien.nextElementSibling).toHaveTextContent('activée à la main')
  })

  it('inscription : validation puis acces au panel, prenom et nom demandes (D102)', async () => {
    aller('/inscription')
    render(<Site />)
    const email = await screen.findByLabelText('Adresse e-mail')
    fireEvent.change(email, { target: { value: 'etu@exemple.fr' } })
    fireEvent.change(screen.getByLabelText(/^Mot de passe/), { target: { value: 'court' } })
    fireEvent.blur(screen.getByLabelText(/^Mot de passe/))
    expect(screen.getByText('Au moins 10 caractères.')).toBeInTheDocument()
    const creer = screen.getByRole('button', { name: 'Créer mon compte' })
    expect(creer).toBeDisabled()
    fireEvent.change(screen.getByLabelText(/^Mot de passe/), { target: { value: 'motdepasse-solide' } })
    fireEvent.change(screen.getByLabelText('Confirmez le mot de passe'), { target: { value: 'motdepasse-solide' } })
    fireEvent.click(screen.getByRole('checkbox', { name: /J’accepte les conditions/ }))
    fireEvent.click(screen.getByRole('checkbox', { name: 'J’ai 15 ans ou plus.' }))
    expect(creer).toBeDisabled() // prenom et nom pas encore saisis
    fireEvent.blur(screen.getByLabelText('Prénom'))
    expect(screen.getByText('Indiquez votre prénom.')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText(/^Prénom/), { target: { value: ' Léa ' } })
    expect(creer).toBeDisabled() // nom manquant
    fireEvent.change(screen.getByLabelText(/^Nom/), { target: { value: 'Martin' } })
    await act(async () => {
      fireEvent.click(creer)
    })
    await waitFor(() => expect(window.location.pathname).toBe('/app'))
    const appel = fetchMock.mock.calls.find(([u]) => String(u).endsWith('/auth/inscription'))!
    expect(JSON.parse(String(appel[1].body))).toEqual({ email: 'etu@exemple.fr', mot_de_passe: 'motdepasse-solide', accepte_cgu: true,
      prenom: 'Léa', nom: 'Martin' })
  })

  it('connexion avec double authentification : code demande apres le mot de passe', async () => {
    aller('/connexion')
    render(<Site />)
    fireEvent.change(await screen.findByLabelText('Adresse e-mail'), { target: { value: 'etu@exemple.fr' } })
    fireEvent.change(screen.getByLabelText('Mot de passe'), { target: { value: 'motdepasse-solide' } })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Se connecter' }))
    })
    const champ = await screen.findByLabelText(/Code de l’application/)
    expect(window.location.pathname).toBe('/connexion')
    fireEvent.change(champ, { target: { value: '123456' } })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Valider' }))
    })
    await waitFor(() => expect(window.location.pathname).toBe('/app'))
    const appel = fetchMock.mock.calls.find(([u]) => String(u).endsWith('/auth/connexion/code'))!
    expect(JSON.parse(String(appel[1].body))).toEqual({ jeton: 'j1', code: '123456' })
  })

  it('limite atteinte : message et lien vers les formules', async () => {
    connecte = true
    aller('/app')
    render(<Site />)
    expect(await screen.findByTitle('Mon compte')).toHaveTextContent(/0\s*question restante/)
    fireEvent.change(await screen.findByLabelText('Votre question'), { target: { value: 'article 1240' } })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Envoyer/ }))
    })
    expect(await screen.findByRole('alert')).toHaveTextContent('Limite du jour atteinte')
    expect(screen.getByRole('link', { name: 'Voir les formules' })).toHaveAttribute('href', '/tarifs')
  })

  it('administration reservee aux admins', async () => {
    connecte = true
    aller('/admin')
    render(<Site />)
    expect(await screen.findByRole('heading', { name: 'Page introuvable' })).toBeInTheDocument()
  })

  it('tableau de bord admin : indicateurs et clients', async () => {
    connecte = true
    admin = true
    aller('/admin')
    render(<Site />)
    expect(await screen.findByText('Revenu mensuel théorique')).toBeInTheDocument()
    expect(screen.getAllByText(/^4,99\s€$/).length).toBeGreaterThan(0)
    expect(screen.getByRole('img', { name: /Questions posées par jour/ })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Clients' }))
    expect(await screen.findByText('etu@exemple.fr')).toBeInTheDocument()
    expect(screen.getByLabelText('Formule de etu@exemple.fr')).toHaveValue('etudiant')
  })

  it('admin sans double authentification : bouton d’activation, aucune requete admin', async () => {
    connecte = true
    admin = true
    deuxFacteurs = false
    aller('/admin')
    render(<Site />)
    const lien = await screen.findByRole('link', { name: 'Activer la double authentification' })
    expect(lien.getAttribute('href')).toBe('/compte?2fa')
    expect(fetchMock.mock.calls.some(([u]) => String(u).includes('/admin/'))).toBe(false)
  })

  it('le lien de l’e-mail confirme l’adresse', async () => {
    aller('/verifier-email#jeton=j-abc')
    render(<Site />)
    expect(await screen.findByRole('heading', { name: 'Adresse confirmée' })).toBeInTheDocument()
    const appel = fetchMock.mock.calls.find(([u]) => String(u).endsWith('/auth/email/verifier'))!
    expect(JSON.parse(String(appel[1].body))).toEqual({ jeton: 'j-abc' })
    // Pas connecte sur ce navigateur : le lien ne connecte pas, il invite a se connecter.
    expect(screen.getByRole('link', { name: 'Se connecter' })).toBeInTheDocument()
  })

  it('mot de passe oublie : lien depuis la connexion, puis meme message pour toute adresse', async () => {
    aller('/connexion')
    render(<Site />)
    fireEvent.click(await screen.findByRole('link', { name: 'Mot de passe oublié ?' }))
    fireEvent.change(await screen.findByLabelText('Adresse e-mail du compte'), { target: { value: 'etu@exemple.fr' } })
    fireEvent.click(screen.getByRole('button', { name: 'Recevoir le lien' }))
    expect(await screen.findByRole('heading', { name: 'Vérifiez vos e-mails' })).toBeInTheDocument()
    const appel = fetchMock.mock.calls.find(([u]) => String(u).endsWith('/auth/mot-de-passe/oubli'))!
    expect(JSON.parse(String(appel[1].body))).toEqual({ email: 'etu@exemple.fr' })
  })

  it('nouveau mot de passe depuis le lien de l e-mail', async () => {
    aller('/nouveau-mot-de-passe#jeton=j-xyz')
    render(<Site />)
    fireEvent.change(await screen.findByLabelText(/Nouveau mot de passe/), { target: { value: 'nouveau-mot-de-passe' } })
    fireEvent.change(screen.getByLabelText('Confirmez le mot de passe'), { target: { value: 'nouveau-mot-de-passe' } })
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
    expect(await screen.findByRole('heading', { name: 'Mot de passe modifié' })).toBeInTheDocument()
    const appel = fetchMock.mock.calls.find(([u]) => String(u).endsWith('/auth/mot-de-passe/nouveau'))!
    expect(JSON.parse(String(appel[1].body))).toEqual({ jeton: 'j-xyz', mot_de_passe: 'nouveau-mot-de-passe' })
  })

  it('ancien format ?jeton= encore lu (e-mails envoyes avant le 2026-11-18)', async () => {
    aller('/nouveau-mot-de-passe?jeton=j-ancien')
    render(<Site />)
    fireEvent.change(await screen.findByLabelText(/Nouveau mot de passe/), { target: { value: 'nouveau-mot-de-passe' } })
    fireEvent.change(screen.getByLabelText('Confirmez le mot de passe'), { target: { value: 'nouveau-mot-de-passe' } })
    fireEvent.click(screen.getByRole('button', { name: 'Enregistrer' }))
    expect(await screen.findByRole('heading', { name: 'Mot de passe modifié' })).toBeInTheDocument()
    const appel = fetchMock.mock.calls.find(([u]) => String(u).endsWith('/auth/mot-de-passe/nouveau'))!
    expect(JSON.parse(String(appel[1].body)).jeton).toBe('j-ancien')
  })

  it('lien sans jeton : message et aucun appel', async () => {
    aller('/verifier-email')
    render(<Site />)
    expect(await screen.findByRole('heading', { name: 'Lien non valable' })).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([u]) => String(u).includes('/auth/email/'))).toBe(false)
  })

  it('page inconnue', async () => {
    aller('/nimporte-quoi')
    render(<Site />)
    expect(await screen.findByRole('heading', { name: 'Page introuvable' })).toBeInTheDocument()
  })
})

describe('Accueil (audit du 18 novembre 2026, D12)', () => {
  it('la demonstration suit la presentation actuelle et les limites gratuites viennent du serveur', async () => {
    aller('/')
    render(<Site />)
    const demo = await screen.findByRole('figure', { name: 'Exemple de réponse' })
    expect(demo).not.toHaveTextContent(/\[S\d\]/)
    expect(demo).toHaveTextContent('[1]')
    expect(demo.textContent!.indexOf('L’essentiel')).toBeLessThan(demo.textContent!.indexOf('Développements et sources'))
    expect(demo).not.toHaveTextContent('Droit positif')
    expect(await screen.findByText(/Gratuit : 10 questions et 2 questionnaires par jour/)).toBeInTheDocument()
    FORMULES[0].quiz_par_jour = 3
    try {
      cleanup()
      render(<Site />)
      expect(await screen.findByText(/Gratuit : 10 questions et 3 questionnaires par jour/)).toBeInTheDocument()
    } finally {
      FORMULES[0].quiz_par_jour = 2
    }
  })
})
