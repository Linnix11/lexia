// Cartes mentales enregistrees : par compte, sans doublon, limite, retrait, effacement du compte.
import { beforeEach, describe, expect, it } from 'vitest'
import type { CarteMentale } from './api'
import { effacerCartesMentales, enregistrerCarteMentale, filtrerCartes, lireCartesMentales, MAX_CARTES, retirerCarteMentale } from './cartesEnregistrees'

const carte = (titre: string): CarteMentale => ({
  titre, branches: [{ libelle: 'Fondement', enfants: [], articles: [] }],
  partiel: true, message: '', restants: 3, avertissement: 'a',
})

beforeEach(() => localStorage.clear())

describe('Cartes mentales enregistrées', () => {
  it('enregistre une fois par compte, sans le quota du jour', () => {
    expect(enregistrerCarteMentale(carte('Usufruit'), 'lea@exemple.fr')).toBe('ok')
    expect(enregistrerCarteMentale(carte('Usufruit'), 'lea@exemple.fr')).toBe('deja')
    const [c] = lireCartesMentales('lea@exemple.fr')
    expect(c.titre).toBe('Usufruit')
    expect(c.carte.restants).toBe(0)
    expect(c.carte.partiel).toBe(false)
    expect(lireCartesMentales('hugo@exemple.fr')).toEqual([])
    expect(Object.keys(localStorage).join()).not.toContain('lea@exemple.fr')
  })

  it('refuse au-delà de la limite, retire et efface', () => {
    for (let i = 0; i < MAX_CARTES; i++) expect(enregistrerCarteMentale(carte(`Carte ${i}`), 'lea@exemple.fr')).toBe('ok')
    expect(enregistrerCarteMentale(carte('De trop'), 'lea@exemple.fr')).toBe('limite')
    const id = lireCartesMentales('lea@exemple.fr')[0].id
    expect(retirerCarteMentale(id, 'lea@exemple.fr')).toHaveLength(MAX_CARTES - 1)
    effacerCartesMentales('lea@exemple.fr')
    expect(lireCartesMentales('lea@exemple.fr')).toEqual([])
  })

  it('recherche par titre, sous-idée ou article, sans accents (D138)', () => {
    enregistrerCarteMentale(carte('Usufruit'), 'lea@exemple.fr')
    enregistrerCarteMentale({ ...carte('Fait des choses'), branches: [{ libelle: 'Garde', articles: [], enfants: [
      { libelle: 'Pouvoirs d’usage', enfants: [], articles: [{ texte: 'article 1242 du Code civil', lien: null }] }] }] }, 'lea@exemple.fr')
    const cartes = lireCartesMentales('lea@exemple.fr')
    const titres = (r: string) => filtrerCartes(cartes, r).map((c) => c.titre)
    expect(titres('')).toEqual(['Fait des choses', 'Usufruit'])
    expect(titres('1242')).toEqual(['Fait des choses'])
    expect(titres('pouvoirs USAGE')).toEqual(['Fait des choses'])
    expect(titres('usufruít')).toEqual(['Usufruit'])
    expect(titres('garde usufruit')).toEqual([])
  })

  it('sans compte, rien n’est enregistré', () => {
    expect(enregistrerCarteMentale(carte('X'), '')).toBe('erreur')
    expect(localStorage.length).toBe(0)
  })
})
