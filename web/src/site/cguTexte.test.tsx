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

const REPERES = {
  editeur: '{{editeur}}', adresse: '{{adresse}}', telephone: '{{telephone}}', tva: '{{tva}}', mediateur: '{{mediateur}}',
  siren: '{{siren}}', statut: '{{statut}}', directeur: '{{directeur}}', hebergeur_telephone: '{{hebergeur_telephone}}',
}

/** Nom du fichier d'une version : « 20 novembre 2026 » -> 20-novembre-2026.json */
const fichierVersion = (version: string) => `${version.normalize('NFD').replace(/[̀-ͯ]/g, '')
  .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')}.json`

const ligne = (t: string) => t.replace(/[ \t ]+/g, ' ').split('\n').map((l) => l.trim()).join('\n').trim()

/** Texte lisible d'une page : titres, paragraphes et listes ; adresse des liens ajoutee a leur texte. */
function enTexte(racine: Element): string {
  const enLigne = (n: Node): string => {
    if (n.nodeType === Node.TEXT_NODE) return n.textContent ?? ''
    if (!(n instanceof Element)) return ''
    if (n.tagName === 'BR') return '\n'
    let t = [...n.childNodes].map(enLigne).join('')
    if (n.tagName === 'A') {
      const href = n.getAttribute('href') ?? ''
      const cible = href.startsWith('mailto:') ? decodeURIComponent(href.slice(7).split('?')[0])
        : href.startsWith('/') ? `{{url}}${href}` : href
      if (cible && !t.includes(cible)) t += ` (${cible})`
    }
    return t
  }
  const blocs: string[] = []
  const parcourir = (el: Element) => {
    for (const c of el.children) {
      if (/^H[1-6]$/.test(c.tagName)) blocs.push(ligne(enLigne(c)).toUpperCase())
      else if (c.tagName === 'P') blocs.push(ligne(enLigne(c)))
      else if (c.tagName === 'UL' || c.tagName === 'OL') blocs.push([...c.children].map((li) => `- ${ligne(enLigne(li))}`).join('\n'))
      else parcourir(c)
    }
  }
  parcourir(racine)
  return blocs.filter(Boolean).join('\n\n') + '\n'
}

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
