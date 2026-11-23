/// <reference types="node" />
// Texte de la politique de confidentialite, tire de la page Confidentialite de Legal.tsx comme celui des CGU (D111) :
// la page est la seule source, docs/confidentialite/<version>.json en est la copie lue par le registre des
// traitements et par le juriste. Une variante par etat de la configuration qui change le texte (niveau Gemini,
// secours Groq), e-mails et paiement actifs comme en production. Apres une modification de la politique :
// changer VERSION_CONFIDENTIALITE (lib/cgu.ts), `npm run confidentialite` dans web/, puis committer le fichier.
import { readFileSync, writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import Site from '../Site'
import { VERSION_CONFIDENTIALITE } from '../lib/cgu'
import { enTexte, fichierVersion, REPERES } from './texteLegal'

async function texteConfidentialite(geminiPayant: boolean, groq: boolean): Promise<string> {
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    const corps = url.endsWith('/config')
      ? { comptes: true, paiement: true, contact_email: '{{contact}}', legal: { ...REPERES, gemini_payant: geminiPayant, groq, courriel: true } }
      : url.endsWith('/auth/session') ? null : {}
    return Promise.resolve(new Response(JSON.stringify(corps), { status: 200, headers: { 'Content-Type': 'application/json' } }))
  }))
  window.history.pushState({}, '', '/confidentialite')
  render(<Site />)
  await screen.findByRole('heading', { level: 1, name: /Politique de confidentialité/ })
  await screen.findByText(/Stripe Payments Europe/)   // configuration chargee (paiement actif)
  const texte = enTexte(document.querySelector('main')!)
  cleanup()
  vi.unstubAllGlobals()
  return texte
}

afterEach(() => vi.unstubAllGlobals())

describe('Texte de la politique de confidentialite', () => {
  it('docs/confidentialite contient le texte de la version en vigueur, identique a la page', async () => {
    const variantes: Record<string, string> = {}
    for (const gp of [false, true]) {
      for (const groq of [false, true]) variantes[`gemini_payant=${+gp},groq=${+groq}`] = await texteConfidentialite(gp, groq)
    }
    const attendu = JSON.stringify({ version: VERSION_CONFIDENTIALITE, variantes }, null, 1) + '\n'
    const chemin = resolve(dirname(fileURLToPath(import.meta.url)), '../../../docs/confidentialite', fichierVersion(VERSION_CONFIDENTIALITE))
    if (process.env.ECRIRE_CONFIDENTIALITE) writeFileSync(chemin, attendu)
    let enregistre = ''
    try {
      enregistre = readFileSync(chemin, 'utf8')
    } catch {
      /* fichier absent : l'egalite ci-dessous echoue avec le message utile */
    }
    expect(enregistre, 'Politique modifiee : changez VERSION_CONFIDENTIALITE, lancez `npm run confidentialite` dans web/ et committez docs/confidentialite/').toBe(attendu)
    const t = variantes['gemini_payant=1,groq=1']
    expect(t).toContain(`Dernière mise à jour : ${VERSION_CONFIDENTIALITE}`)
    for (const morceau of ['Résumés vocaux et cartes mentales : nombre', 'LECTURE À VOIX HAUTE DES RÉSUMÉS', 'DÉCISIONS DE JUSTICE REPRODUITES', 'Groq', 'Resend', 'Stripe'])
      expect(t).toContain(morceau)
    expect(t).not.toMatch(/<|>|\{\{(?!editeur|adresse|telephone|tva|mediateur|siren|statut|directeur|hebergeur_telephone|contact|url)/)
  }, 30_000)
})
