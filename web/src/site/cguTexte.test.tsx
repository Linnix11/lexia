/// <reference types="node" />
// Texte des CGU joint a la confirmation du contrat (C. consom. L. 221-13 : support durable). Une seule source :
// la page Cgu de Legal.tsx, rendue ici puis convertie en texte, une variante par etat de la configuration qui change
// le texte (niveau Gemini, secours Groq). Les valeurs de l'editeur restent des repères {{editeur}}... remplaces par le
// serveur (api/cgu_texte.py). Apres une modification des CGU : `npm run cgu` dans web/, puis committer api/cgu/.
import { readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { render, screen, cleanup } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import Site from '../Site'
import { VERSION_CGU } from '../lib/cgu'
import { enTexte, fichierVersion, REPERES } from './texteLegal'

async function texteCgu(geminiPayant: boolean, groq: boolean): Promise<string> {
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    const corps = url.endsWith('/config')
      ? { comptes: true, paiement: true, contact_email: '{{contact}}', legal: { ...REPERES, gemini_payant: geminiPayant, groq } }
      : url.endsWith('/auth/session') ? null : {}
    return Promise.resolve(new Response(JSON.stringify(corps), { status: 200, headers: { 'Content-Type': 'application/json' } }))
  }))
  window.history.pushState({}, '', '/cgu')
  render(<Site />)
  await screen.findByRole('heading', { level: 1, name: /Conditions générales/ })
  await screen.findByText(/Rétractation en ligne\./)   // configuration chargee (paiement actif)
  const texte = enTexte(document.querySelector('main')!)
  cleanup()
  vi.unstubAllGlobals()
  return texte
}

afterEach(() => vi.unstubAllGlobals())

describe('Texte des CGU joint a la confirmation du contrat', () => {
  it('api/cgu contient le texte de la version en vigueur, identique a la page', async () => {
    const variantes: Record<string, string> = {}
    for (const gp of [false, true]) {
      for (const groq of [false, true]) variantes[`gemini_payant=${+gp},groq=${+groq}`] = await texteCgu(gp, groq)
    }
    const attendu = JSON.stringify({ version: VERSION_CGU, variantes }, null, 1) + '\n'
    // pas de new URL(..., import.meta.url) : Vite le reecrit en adresse de ressource
    const chemin = resolve(dirname(fileURLToPath(import.meta.url)), '../../../api/cgu', fichierVersion(VERSION_CGU))
    if (process.env.ECRIRE_CGU) writeFileSync(chemin, attendu)
    let enregistre = ''
    try {
      enregistre = readFileSync(chemin, 'utf8')
    } catch {
      /* fichier absent : l'egalite ci-dessous echoue avec le message utile */
    }
    expect(enregistre, 'CGU modifiees : lancez `npm run cgu` dans web/ et committez api/cgu/').toBe(attendu)
    const t = variantes['gemini_payant=1,groq=0']
    expect(t).toContain(`Dernière mise à jour : ${VERSION_CGU}`)
    for (const morceau of ['Droit de rétractation', 'Renoncer au contrat ici', '{{editeur}}', '{{contact}}', 'Rayez la mention inutile'])
      expect(t).toContain(morceau)
    expect(t).not.toMatch(/<|>|\{\{(?!editeur|adresse|telephone|tva|mediateur|siren|statut|directeur|hebergeur_telephone|contact|url)/)
  }, 30_000)
})
