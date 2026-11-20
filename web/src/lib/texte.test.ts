import { describe, expect, it } from 'vitest'
import { normaliser } from './texte'

describe('normaliser (WEB-18)', () => {
  it('rapproche ligatures, accents et apostrophes typographiques', () => {
    expect(normaliser('Œuvre')).toBe(normaliser('oeuvre'))
    expect(normaliser('l’acte')).toBe(normaliser("l'acte"))
    expect(normaliser('Pénal')).toBe('penal')
    expect(normaliser('curriculum  vitæ')).toBe('curriculum vitae')
  })
})
