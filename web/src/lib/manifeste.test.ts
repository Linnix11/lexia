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
    expect(manifeste.icons.map((i) => i.sizes)).toEqual(['192x192', '512x512'])
    for (const i of manifeste.icons) expect(icones).toContain(i.src)
  })
})
