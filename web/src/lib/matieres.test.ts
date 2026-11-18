import { describe, expect, it } from 'vitest'
import type { Matiere } from './api'
import { filtrerMatieres, grouperParAnnee, sourcesPrincipales } from './matieres'

const M: Matiere[] = [
  { id: 'droit_penal', libelle: 'Droit pénal', annee: 'L2', mots: ['droit pénal général'], sources: ['code_penal', 'code_procedure_penale'],
    principales: ['code_penal'], noms_sources: { code_penal: 'Code pénal', code_procedure_penale: 'Code de procédure pénale' } },
  { id: 'procedure_penale', libelle: 'Procédure pénale', annee: 'L3', mots: ['garde à vue'], sources: ['code_procedure_penale', 'cass_criminelle'],
    principales: ['code_procedure_penale', 'cass_criminelle'],
    noms_sources: { code_procedure_penale: 'Code de procédure pénale', cass_criminelle: 'Cour de cassation : chambre criminelle' } },
  { id: 'droit_de_la_famille', libelle: 'Droit de la famille', annee: 'L1', mots: ['régimes matrimoniaux', 'successions'], sources: ['code_civil'] },
  { id: 'ancienne', libelle: 'Matière sans année', sources: ['lois'] },
]

describe('matieres : recherche et classement par annee (D97)', () => {
  it('cherche sans accents ni casse, dans les intitules, les autres intitules et les sources', () => {
    expect(filtrerMatieres(M, 'PROCEDURE penale').map((m) => m.id)).toEqual(['droit_penal', 'procedure_penale'])
    expect(filtrerMatieres(M, 'régimes matrimoniaux').map((m) => m.id)).toEqual(['droit_de_la_famille'])
    expect(filtrerMatieres(M, 'garde a vue').map((m) => m.id)).toEqual(['procedure_penale'])
    expect(filtrerMatieres(M, 'chambre criminelle').map((m) => m.id)).toEqual(['procedure_penale'])
    expect(filtrerMatieres(M, 'droit international')).toEqual([])
    expect(filtrerMatieres(M, '  ')).toHaveLength(4)
  })

  it('groupe L1, L2, L3 dans l ordre, puis les matieres sans annee', () => {
    expect(grouperParAnnee(M).map((g) => [g.titre, g.matieres.map((m) => m.id)])).toEqual([
      ['Licence 1', ['droit_de_la_famille']], ['Licence 2', ['droit_penal']], ['Licence 3', ['procedure_penale']],
      ['Autres matières', ['ancienne']],
    ])
    expect(grouperParAnnee(filtrerMatieres(M, 'famille')).map((g) => g.titre)).toEqual(['Licence 1'])
  })

  it('sources principales par leur nom, sinon les premieres sources', () => {
    expect(sourcesPrincipales(M[1])).toEqual(['Code de procédure pénale', 'Cour de cassation : chambre criminelle'])
    expect(sourcesPrincipales(M[3])).toEqual(['lois'])
  })
})
