import { describe, expect, it } from 'vitest'
import { titresDistincts } from './fichiers'

describe('titresDistincts (recette du 2026-11-20, D-10)', () => {
  it('garde le nom sans extension quand il est unique', () => {
    expect(titresDistincts(['chapitre3.pdf', 'scan.pdf'])).toEqual(['chapitre3', 'scan'])
  })

  it('distingue par le format les fichiers de meme nom deposes ensemble', () => {
    expect(titresDistincts(['cours-contrats.pdf', 'cours-contrats.docx', 'Cours-Contrats.rtf', 'autre.pdf']))
      .toEqual(['cours-contrats (PDF)', 'cours-contrats (DOCX)', 'Cours-Contrats (RTF)', 'autre'])
  })

  it('numerote ce qui reste identique, y compris sans extension', () => {
    expect(titresDistincts(['td.pdf', 'td.pdf', 'td.pdf', 'notes', 'notes'])).toEqual(['td (PDF)', 'td (PDF) 2', 'td (PDF) 3', 'notes', 'notes 2'])
  })
})
