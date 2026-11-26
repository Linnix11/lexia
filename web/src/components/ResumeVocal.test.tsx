// Resume vocal (D106) : texte demande au serveur, lu par la synthese vocale du navigateur (simulee ici).
import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { decouperPhrases, dureeLisible, intertitre, nomDeFichier, transcription, voixFrancaises } from '../lib/voix'
import { ResumeVocal } from './ResumeVocal'

// Compte connecte simule : les resumes deja prepares sont gardes par compte dans l'onglet (D141).
const session = vi.hoisted(() => ({ email: '' }))
vi.mock('../state/session', () => ({
  useSessionFacultative: () => (session.email ? { profil: { email: session.email } } : null),
}))

const RESUME = {
  titre: 'La responsabilité du fait personnel',
  paragraphes: ['Voici le sujet. L’article 1240 du Code civil pose la règle.', 'À retenir : faute, dommage, lien de causalité.'],
  mots: 200, duree_estimee_s: 80, partiel: false, message: '', restants: 4,
  avertissement: 'Résumé généré automatiquement : il peut contenir des erreurs. Vérifiez avec les textes et les sources citées.',
}

class Enonce {
  text: string
  lang = ''
  rate = 1
  voice: unknown = null
  onend: (() => void) | null = null
  onerror: (() => void) | null = null
  constructor(texte: string) { this.text = texte }
}

const voix = (name: string, lang: string, localService = true) => ({ name, lang, localService, default: false, voiceURI: name }) as SpeechSynthesisVoice
let dits: Enonce[]
let synth: { speak: ReturnType<typeof vi.fn>; cancel: ReturnType<typeof vi.fn>; getVoices: () => SpeechSynthesisVoice[];
  addEventListener: () => void; removeEventListener: () => void }
let reponse: () => Promise<Response>
const json = (corps: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(corps), { status, headers: { 'Content-Type': 'application/json' } }))

beforeEach(() => {
  dits = []
  synth = {
    speak: vi.fn((u: Enonce) => { dits.push(u) }), cancel: vi.fn(),
    getVoices: () => [voix('Amélie', 'fr-CA'), voix('English', 'en-US'), voix('Thomas', 'fr-FR')],
    addEventListener: () => {}, removeEventListener: () => {},
  }
  Object.defineProperty(window, 'speechSynthesis', { value: synth, configurable: true })
  vi.stubGlobal('SpeechSynthesisUtterance', Enonce)
  reponse = () => json(RESUME)
  vi.stubGlobal('fetch', vi.fn(() => reponse()))
})
afterEach(() => {
  session.email = ''
  sessionStorage.clear()
  localStorage.clear()
  vi.unstubAllGlobals()
  delete (window as { speechSynthesis?: unknown }).speechSynthesis
})

const demande = () => ({ type: 'cours' as const, id: '7' })

describe('Résumé vocal', () => {
  it('garde le focus : titre de la section à l’ouverture, bouton à la fermeture (audit du 2026-11-23, D4)', async () => {
    render(<ResumeVocal demande={demande} />)
    fireEvent.click(screen.getByRole('button', { name: 'Écouter un résumé' }))
    expect(screen.getByRole('heading', { name: 'Résumé vocal' })).toHaveFocus()
    await screen.findByText(RESUME.titre)
    fireEvent.click(screen.getByRole('button', { name: 'Fermer' }))
    expect(screen.getByRole('button', { name: 'Reprendre le résumé' })).toHaveFocus()
  })

  it('demande le résumé au clic, l’affiche avec l’avertissement et le lit phrase par phrase', async () => {
    render(<ResumeVocal demande={demande} />)
    expect(fetch).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Écouter un résumé' }))
    expect(await screen.findByText(RESUME.titre)).toBeInTheDocument()
    const [url, init] = vi.mocked(fetch).mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toMatch(/\/resume-vocal$/)
    expect(JSON.parse(init.body as string)).toEqual({ type: 'cours', id: '7' })
    expect(screen.getByText(/erreurs\. Vérifiez avec les textes/)).toBeInTheDocument()
    expect(screen.getByText(/Environ 1 min 20/)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Écouter' }))
    expect(dits[0].text).toBe('Voici le sujet.')
    expect(dits[0].lang).toBe('fr-FR')
    expect((dits[0].voice as SpeechSynthesisVoice).name).toBe('Thomas') // fr-FR avant fr-CA, pas de voix anglaise
    expect(screen.getByText('Voici le sujet.')).toHaveAttribute('aria-current', 'true')

    act(() => dits[0].onend!())
    expect(dits[1].text).toBe('L’article 1240 du Code civil pose la règle.')
    expect(screen.getByText('L’article 1240 du Code civil pose la règle.')).toHaveAttribute('aria-current', 'true')

    fireEvent.click(screen.getByRole('button', { name: 'Pause' }))
    expect(synth.cancel).toHaveBeenCalled()
    act(() => dits[1].onend!()) // fin de l'enonce annule : ignoree
    expect(dits).toHaveLength(2)
    fireEvent.click(screen.getByRole('button', { name: 'Reprendre' }))
    expect(dits[2].text).toBe(dits[1].text)

    fireEvent.change(screen.getByRole('combobox', { name: 'Vitesse' }), { target: { value: '1.5' } })
    expect(dits[3].rate).toBe(1.5)
    expect(screen.getByRole('combobox', { name: 'Voix' })).toBeInTheDocument()

    fireEvent.click(screen.getByText('À retenir : faute, dommage, lien de causalité.')) // saut a une phrase
    expect(dits[4].text).toBe('À retenir : faute, dommage, lien de causalité.')
    act(() => dits[4].onend!())
    expect(screen.getByRole('button', { name: 'Écouter' })).toBeInTheDocument() // fin du resume
  })

  it('affiche le message de l’API quand la limite du jour est atteinte', async () => {
    reponse = () => json({ detail: 'Limite du jour atteinte : 5 résumés vocaux par jour.' }, 402)
    render(<ResumeVocal demande={demande} />)
    fireEvent.click(screen.getByRole('button', { name: 'Écouter un résumé' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Limite du jour atteinte')
  })

  it('donne le texte à lire quand le navigateur ne sait pas lire à voix haute', async () => {
    delete (window as { speechSynthesis?: unknown }).speechSynthesis
    render(<ResumeVocal demande={demande} />)
    fireEvent.click(screen.getByRole('button', { name: 'Écouter un résumé' }))
    expect(await screen.findByText(/n’est pas disponible dans ce navigateur/)).toBeInTheDocument()
    expect(screen.getByText('Voici le sujet.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Écouter' })).not.toBeInTheDocument()
  })
})

const EN_PARTIES = {
  ...RESUME,
  paragraphes: ['Nous verrons d’abord la faute, puis le dommage.', 'La faute est un manquement. Elle s’apprécie in abstracto.',
    'Le dommage doit être certain.', 'À retenir : faute et dommage.'],
  intertitres: ['Introduction', 'La faute', '', 'À retenir'],
}

describe('Résumé vocal en parties (D141)', () => {
  it('affiche le plan, saute à une partie, passe à la suivante ou à la précédente et donne le temps restant', async () => {
    reponse = () => json(EN_PARTIES)
    render(<ResumeVocal demande={demande} />)
    fireEvent.click(screen.getByRole('button', { name: 'Écouter un résumé' }))
    const plan = await screen.findByRole('navigation', { name: 'Plan du résumé' })
    // Intertitre vide : la partie est numerotee
    expect([...plan.querySelectorAll('button')].map((b) => b.textContent)).toEqual([
      expect.stringMatching(/^1\.Introduction0 s$/), expect.stringMatching(/^2\.La faute/),
      expect.stringMatching(/^3\.Partie 3/), expect.stringMatching(/^4\.À retenir/)])
    expect(screen.getByRole('heading', { name: 'La faute', level: 5 })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Partie précédente' })).toBeDisabled()

    fireEvent.click(screen.getByRole('button', { name: /^2\.La faute/ }))
    expect(dits[0].text).toBe('La faute est un manquement.')
    expect(screen.getByRole('button', { name: /^2\.La faute/ })).toHaveAttribute('aria-current', 'step')
    expect(screen.getByText(/Partie 2 sur 4 : La faute · encore environ/)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Partie suivante' }))
    expect(dits[1].text).toBe('Le dommage doit être certain.')
    fireEvent.click(screen.getByRole('button', { name: 'Partie précédente' }))
    expect(dits[2].text).toBe('La faute est un manquement.')

    fireEvent.click(screen.getByRole('button', { name: 'Pause' }))
    fireEvent.click(screen.getByRole('button', { name: 'Partie suivante' })) // en pause : deplace sans lire
    expect(dits).toHaveLength(3)
    fireEvent.click(screen.getByRole('button', { name: 'Reprendre' }))
    expect(dits[3].text).toBe('Le dommage doit être certain.')
  })

  it('garde le résumé dans l’onglet : rouvert, il reprend à la phrase atteinte sans nouvelle demande au serveur', async () => {
    session.email = 'etudiant@exemple.fr'
    reponse = () => json(EN_PARTIES)
    const { unmount } = render(<ResumeVocal demande={demande} />)
    fireEvent.click(screen.getByRole('button', { name: 'Écouter un résumé' }))
    fireEvent.click(await screen.findByRole('button', { name: /^3\.Partie 3/ }))
    expect(dits[0].text).toBe('Le dommage doit être certain.')
    unmount() // changement de page
    expect(JSON.stringify(sessionStorage)).not.toContain('etudiant@exemple.fr') // cle par empreinte du compte

    render(<ResumeVocal demande={demande} />)
    fireEvent.click(screen.getByRole('button', { name: 'Reprendre le résumé' }))
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(screen.getByText(/Déjà préparé : il ne compte pas une seconde fois/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Reprendre' }))
    expect(dits.at(-1)!.text).toBe('Le dommage doit être certain.')

    // Autre document ou autre compte : rien de repris
    session.email = 'autre@exemple.fr'
    render(<ResumeVocal demande={demande} />)
    expect(screen.getByRole('button', { name: 'Écouter un résumé' })).toBeInTheDocument()
  })

  it('retient la vitesse choisie pour les résumés suivants', async () => {
    const { unmount } = render(<ResumeVocal demande={demande} />)
    fireEvent.click(screen.getByRole('button', { name: 'Écouter un résumé' }))
    fireEvent.change(await screen.findByRole('combobox', { name: 'Vitesse' }), { target: { value: '1.25' } })
    unmount()
    render(<ResumeVocal demande={demande} />)
    fireEvent.click(screen.getByRole('button', { name: 'Écouter un résumé' }))
    expect(await screen.findByRole('combobox', { name: 'Vitesse' })).toHaveValue('1.25')
    fireEvent.click(screen.getByRole('button', { name: 'Écouter' }))
    expect(dits[0].rate).toBe(1.25)
  })

  it('télécharge la transcription avec les intertitres et l’avertissement', async () => {
    const blobs: Blob[] = []
    vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: (b: Blob) => { blobs.push(b); return 'blob:x' }, revokeObjectURL: () => {} }))
    const clic = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    reponse = () => json(EN_PARTIES)
    render(<ResumeVocal demande={demande} />)
    fireEvent.click(screen.getByRole('button', { name: 'Écouter un résumé' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Télécharger le texte' }))
    expect(clic).toHaveBeenCalled()
    const texte = await blobs[0].text()
    expect(texte).toContain('La faute\n\nLa faute est un manquement.')
    expect(texte).toContain('Partie 3\n\nLe dommage')
    expect(texte).toContain('il peut contenir des erreurs')
    clic.mockRestore()
  })

  it('met en pause au retour sur l’onglet quand le système a coupé la lecture (écran verrouillé)', async () => {
    render(<ResumeVocal demande={demande} />)
    fireEvent.click(screen.getByRole('button', { name: 'Écouter un résumé' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Écouter' }))
    act(() => dits[0].onend!())
    Object.assign(synth, { speaking: false, pending: false, paused: false })
    act(() => { document.dispatchEvent(new Event('visibilitychange')) })
    fireEvent.click(screen.getByRole('button', { name: 'Reprendre' }))
    expect(dits.at(-1)!.text).toBe('L’article 1240 du Code civil pose la règle.')
  })
})

describe('lib/voix', () => {
  it('nomme les parties et prépare la transcription', () => {
    const ps = ['Annonce.', 'Corps.', 'À retenir : tout.']
    expect(ps.map((_, i) => intertitre(ps, undefined, i))).toEqual(['Introduction', 'Partie 2', 'À retenir'])
    expect(intertitre(ps, ['Un', 'Deux'], 1)).toBe('Partie 2') // intertitres mal alignes : ignores
    expect(transcription('T', ps, ['A', 'B', 'C'], 'Attention.')).toMatch(/^T\n\nA\n\nAnnonce\.\n\nB\n\nCorps\./)
    expect(nomDeFichier('Le dol : vice du consentement')).toBe('resume-le-dol-vice-du-consentement.txt')
  })

  it('découpe en phrases sans couper un numéro de pourvoi', () => {
    expect(decouperPhrases(['Le pourvoi 12-34.567 est rejeté. La Cour de cassation casse ! Fin'])).toEqual([
      ['Le pourvoi 12-34.567 est rejeté.', 'La Cour de cassation casse !', 'Fin'],
    ])
  })

  it('garde les voix françaises, fr-FR d’abord', () => {
    const v = voixFrancaises([voix('A', 'fr-CA'), voix('B', 'en-GB'), voix('C', 'fr-FR'), voix('D', 'fr_FR')])
    expect(v.map((x) => x.name)).toEqual(['C', 'D', 'A'])
  })

  it('voix de l’appareil seulement quand il y en a : une voix en ligne envoie le texte à l’éditeur du navigateur (recette du 2026-11-20, D-11)', () => {
    const v = voixFrancaises([voix('Google français', 'fr-FR', false), voix('Thomas', 'fr-FR'), voix('Amélie', 'fr-CA')])
    expect(v.map((x) => x.name)).toEqual(['Thomas', 'Amélie'])
    // Sans voix locale, les voix en ligne restent proposees (sinon aucune lecture possible).
    expect(voixFrancaises([voix('Google français', 'fr-FR', false)]).map((x) => x.name)).toEqual(['Google français'])
  })

  it('écarte les voix fantaisie de macOS, en double France et Canada (recette du 2026-11-23, R-6)', () => {
    const fantaisie = (name: string, lang: string) =>
      ({ ...voix(`${name} (français (${lang === 'fr-FR' ? 'France' : 'Canada'}))`, lang),
        voiceURI: `com.apple.eloquence.${lang}.${name}` }) as SpeechSynthesisVoice
    // Chrome donne le nom pour voiceURI : le nom suffit a reconnaitre une voix fantaisie
    const v = voixFrancaises([fantaisie('Grandma', 'fr-FR'), fantaisie('Grandpa', 'fr-CA'), fantaisie('Rocko', 'fr-FR'),
      fantaisie('Shelley', 'fr-CA'), voix('Shelley', 'fr-FR'), voix('Thomas', 'fr-FR'), voix('Amélie', 'fr-CA'),
      ({ ...voix('Albert', 'fr-FR'), voiceURI: 'com.apple.speech.synthesis.voice.Albert' }) as SpeechSynthesisVoice])
    expect(v.map((x) => x.name)).toEqual(['Thomas', 'Amélie'])
    // Rien que des voix fantaisie : elles restent (sinon aucune voix française à choisir)
    expect(voixFrancaises([fantaisie('Grandma', 'fr-FR')]).length).toBe(1)
  })

  it('prévient quand la voix choisie est une voix en ligne', async () => {
    synth.getVoices = () => [voix('Google français', 'fr-FR', false)]
    render(<ResumeVocal demande={demande} />)
    fireEvent.click(screen.getByRole('button', { name: 'Écouter un résumé' }))
    expect(await screen.findByText(/voix en ligne de votre navigateur : le texte du résumé est envoyé à son éditeur/)).toBeInTheDocument()
  })

  it('écrit une durée lisible', () => {
    expect(dureeLisible(80)).toBe('1 min 20')
    expect(dureeLisible(180)).toBe('3 min')
    expect(dureeLisible(45)).toBe('45 s')
  })
})
