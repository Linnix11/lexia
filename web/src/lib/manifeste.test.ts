// Site ajoute a l'ecran d'accueil d'un telephone : icone, nom et couleur (audit mobile du 2026-11-18).
import { describe, expect, it } from 'vitest'
import html from '../../index.html?raw'
import manifeste from '../../public/manifest.json'

const icones = Object.keys(import.meta.glob('../../public/*.png')).map((c) => c.replace('../../public', ''))

describe('PWA et icones', () => {
  it('index.html declare viewport-fit=cover, le manifeste, l icone Apple et la couleur', () => {
    expect(html).toMatch(/name="viewport" content="[^"]*viewport-fit=cover/)
    expect(html).toContain('<link rel="manifest" href="/manifest.json" />')
    expect(html).toContain('<link rel="apple-touch-icon" href="/apple-touch-icon.png" />')
    expect(html).toMatch(/name="theme-color"/)
    expect(icones).toContain('/apple-touch-icon.png')
  })

  it('le manifeste pointe vers des icones presentes', () => {
    expect(manifeste).toMatchObject({ short_name: 'Lexia', display: 'standalone', start_url: '/app', lang: 'fr' })
    // Kit de marque (brand/icones, D118) : icones ordinaires et masquables (zone sure d'Android)
    expect(manifeste.icons.map((i) => `${i.sizes} ${i.purpose}`)).toEqual(['192x192 any', '512x512 any', '192x192 maskable', '512x512 maskable'])
    for (const i of manifeste.icons) expect(icones).toContain(i.src)
  })

  it('favicon.ico present et declare : /favicon.ico ne doit pas repondre la page HTML (audit du 2026-11-23, D15)', () => {
    expect(html).toContain('<link rel="icon" href="/favicon.ico" sizes="48x48" />')
    expect(Object.keys(import.meta.glob('../../public/favicon.ico'))).toHaveLength(1)
    expect(Object.keys(import.meta.glob('../../public/favicon.svg'))).toHaveLength(1)
  })
})
