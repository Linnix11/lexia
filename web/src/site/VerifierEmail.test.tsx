import { describe, expect, it } from 'vitest'
import { texteLien } from './VerifierEmail'

describe('bandeau de confirmation de l’adresse', () => {
  it('dit quand le lien d’inscription n’est pas parti (plafond d’envois, D119)', () => {
    expect(texteLien({ email: 'etu@exemple.fr', lien_envoye: false })).toContain('n’a pas pu être envoyé')
    expect(texteLien({ email: 'etu@exemple.fr', lien_envoye: false })).toContain('Renvoyer l’e-mail')
  })
  it('garde le message habituel sinon', () => {
    expect(texteLien({ email: 'etu@exemple.fr', lien_envoye: true })).toBe('le lien a été envoyé à etu@exemple.fr.')
    expect(texteLien({ email: 'etu@exemple.fr' })).toBe('le lien a été envoyé à etu@exemple.fr.')
  })
})
