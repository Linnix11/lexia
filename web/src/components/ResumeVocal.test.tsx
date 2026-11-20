// Resume vocal (D106) : texte demande au serveur, lu par la synthese vocale du navigateur (simulee ici).
import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { decouperPhrases, dureeLisible, voixFrancaises } from '../lib/voix'
import { ResumeVocal } from './ResumeVocal'

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

const voix = (name: string, lang: string) => ({ name, lang, localService: true, default: false, voiceURI: name }) as SpeechSynthesisVoice
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
  vi.unstubAllGlobals()
  delete (window as { speechSynthesis?: unknown }).speechSynthesis
})

const demande = () => ({ type: 'cours' as const, id: '7' })

describe('Résumé vocal', () => {
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

describe('lib/voix', () => {
  it('découpe en phrases sans couper un numéro de pourvoi', () => {
    expect(decouperPhrases(['Le pourvoi 12-34.567 est rejeté. La Cour de cassation casse ! Fin'])).toEqual([
      ['Le pourvoi 12-34.567 est rejeté.', 'La Cour de cassation casse !', 'Fin'],
    ])
  })

  it('garde les voix françaises, fr-FR d’abord', () => {
    const v = voixFrancaises([voix('A', 'fr-CA'), voix('B', 'en-GB'), voix('C', 'fr-FR'), voix('D', 'fr_FR')])
    expect(v.map((x) => x.name)).toEqual(['C', 'D', 'A'])
  })

  it('écrit une durée lisible', () => {
    expect(dureeLisible(80)).toBe('1 min 20')
    expect(dureeLisible(180)).toBe('3 min')
    expect(dureeLisible(45)).toBe('45 s')
  })
})
