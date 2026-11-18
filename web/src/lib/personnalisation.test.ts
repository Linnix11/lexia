import { beforeEach, describe, expect, it } from 'vitest'
import { ecrireDerniereMatiere, effacerDerniereMatiere, lireDerniereMatiere, phraseQuestionsRestantes, salutation, tronquer } from './personnalisation'

describe('personnalisation', () => {
  beforeEach(() => localStorage.clear())

  it('salue selon l heure, avec le prenom seulement s il existe', () => {
    expect(salutation('Léa', 9)).toBe('Bonjour, Léa.')
    expect(salutation('Léa', 19)).toBe('Bonsoir, Léa.')
    expect(salutation(null, 4)).toBe('Bonsoir.')
    expect(salutation('  ', 12)).toBe('Bonjour.')
  })

  it('dit simplement les questions restantes', () => {
    expect(phraseQuestionsRestantes(7, 10)).toBe('Il vous reste 7 questions aujourd’hui.')
    expect(phraseQuestionsRestantes(1, 10)).toBe('Il vous reste 1 question aujourd’hui.')
    expect(phraseQuestionsRestantes(0, 10)).toMatch(/vos 10 questions du jour : le compteur repart à minuit/)
  })

  it('garde la derniere matiere par compte, sans l adresse dans la cle', () => {
    ecrireDerniereMatiere('etu@exemple.fr', 'contrats')
    expect(lireDerniereMatiere('ETU@exemple.fr')).toBe('contrats')
    expect(lireDerniereMatiere('autre@exemple.fr')).toBeNull()
    expect(Object.keys(localStorage).join()).not.toContain('etu@')
    effacerDerniereMatiere('etu@exemple.fr')
    expect(lireDerniereMatiere('etu@exemple.fr')).toBeNull()
  })

  it('tronque une question longue', () => {
    expect(tronquer('court')).toBe('court')
    expect(tronquer('x'.repeat(100), 10)).toHaveLength(10)
  })
})
