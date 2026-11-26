// D140 : correction expliquee choix par choix, erreurs en cartes, questions ratees a refaire.
import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { Correction, Quiz } from '../lib/api'
import type { Carte } from '../lib/cartes'
import { Ctx, type AppState, type EtatQuiz } from '../state/contexte'
import { QuizModal } from './QuizModal'

const QUIZ: Quiz = { quiz_id: 'qz-1', format: 'qcm', theme: 'la faute', demande: 2, obtenu: 2, message: '', avertissement: '',
  sources: [], questions: [
    { index: 0, question: 'Paul blesse Marie par imprudence : quel fondement ?', choix: ['Le contrat', 'La faute prouvée', 'Le fait des choses'] },
    { index: 1, question: 'Quel article pose le principe ?', choix: ['1240', '1103', '1231-1'] },
  ] }
const CORRECTION: Correction = { quiz_id: 'qz-1', score: 1, total: 2, sources: [], resultats: [
  { index: 0, statut: 'incorrect', explication: 'La faute oblige à réparer.', sources: [], bonne_reponse: 1,
    justifications: ['Faux : aucun contrat entre eux.', 'Juste : imprudence et dommage.', 'Faux : aucune chose en cause.'] },
  { index: 1, statut: 'correct', explication: 'Article 1240.', sources: [], bonne_reponse: 0 },
] }

function ouvrir(ajouterCartes = vi.fn()) {
  const dernierQuiz: EtatQuiz = { parametres: { theme: 'la faute', nombre: 5, format: 'qcm', matiere: 'droit_civil' }, quiz: QUIZ,
    reponses: { 0: 0, 1: 0 }, correction: CORRECTION, etat: 'libre', erreur: null }
  const valeur = { quizOuvert: { id: 1 }, matiere: null, matieres: [], dernierQuiz, ajouterCartes, fermerQuiz: () => {},
    ouvrirSource: () => {}, genererQuiz: () => {}, repondreQuiz: () => {}, corrigerQuiz: () => {}, signalerErreurQuiz: () => {},
    mesCours: [], coursChoisis: [] } as unknown as AppState
  render(<Ctx.Provider value={valeur}><QuizModal /></Ctx.Provider>)
  return ajouterCartes
}

describe('questionnaire corrige (D140)', () => {
  it('chaque choix dit s il est juste ou faux, et pourquoi', () => {
    ouvrir()
    const q1 = screen.getAllByRole('group')[0]
    expect(within(q1).getByText('✗ Votre réponse.').parentElement).toHaveTextContent('Faux : aucun contrat entre eux.')
    expect(within(q1).getByText('✓ Bonne réponse.').parentElement).toHaveTextContent('Juste : imprudence et dommage.')
    expect(within(q1).getByText('Faux : aucune chose en cause.')).toBeInTheDocument()
    expect(within(screen.getAllByRole('group')[1]).getByText('✓ Bonne réponse, votre réponse.')).toBeInTheDocument()
  })

  it('les erreurs seulement en cartes, avec la matiere du questionnaire', () => {
    const ajouter = ouvrir()
    fireEvent.click(screen.getByRole('button', { name: 'Ajouter mes erreurs aux cartes (1)' }))
    const cartes = ajouter.mock.calls[0][0] as Carte[]
    expect(cartes.map((c) => c.id)).toEqual(['quiz:qz-1:0'])
    expect(cartes[0].verso).toContain('Votre réponse : Le contrat. Faux : aucun contrat entre eux.')
    expect(cartes[0].matiere).toBe('droit_civil')
    fireEvent.click(screen.getByRole('button', { name: 'Ajouter toutes les questions' }))
    expect(ajouter.mock.calls[1][0]).toHaveLength(2)
  })

  it('refaire les questions ratees, verifier sur place, revenir a la correction', () => {
    ouvrir()
    fireEvent.click(screen.getByRole('button', { name: 'Refaire les questions ratées (1)' }))
    expect(screen.getByRole('heading', { name: 'Questions ratées, à refaire' })).toHaveFocus()
    const reprise = screen.getByRole('group')
    expect(within(reprise).queryByText('Quel article pose le principe ?')).not.toBeInTheDocument()
    expect(within(reprise).getByRole('radio', { name: 'La faute prouvée' })).not.toBeChecked()
    fireEvent.click(within(reprise).getByRole('radio', { name: 'La faute prouvée' }))
    fireEvent.click(screen.getByRole('button', { name: 'Vérifier' }))
    expect(screen.getByRole('status')).toHaveTextContent('Reprise : 1 / 1')
    expect(within(reprise).getByText('✓ Bonne réponse, votre réponse.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Revenir à la correction' }))
    expect(screen.getByText('Score : 1 / 2')).toBeInTheDocument()
  })
})
