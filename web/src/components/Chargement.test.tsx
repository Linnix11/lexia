// Attente des actions longues : etape qui avance, secondes ecoulees, une seule annonce accessible.
import { act, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { Chargement } from './Chargement'

beforeEach(() => vi.useFakeTimers())
afterEach(() => vi.useRealTimers())

describe('Chargement', () => {
  it('fait avancer les étapes et compte les secondes, puis reste sur la dernière', () => {
    render(<Chargement etapes={['Lecture…', 'Rédaction…', 'Presque prêt…']} duree="jusqu’à une minute" />)
    expect(screen.getByRole('status')).toHaveTextContent('Lecture…')
    act(() => { vi.advanceTimersByTime(7000) })
    expect(screen.getByRole('status')).toHaveTextContent('Rédaction…')
    expect(screen.getByText(/7 s · jusqu’à une minute/)).toBeInTheDocument()
    act(() => { vi.advanceTimersByTime(60000) })
    expect(screen.getByRole('status')).toHaveTextContent('Presque prêt…')
  })

  it('annonce un texte rassurant a la place de la duree passe le seuil (audit du 2026-11-25, G-5)', () => {
    render(<Chargement etapes={['Lecture…']} duree="10 à 45 secondes en général"
      longue={{ apres: 30, texte: 'Plus long que d’habitude, la réponse arrive.' }} />)
    act(() => { vi.advanceTimersByTime(29000) })
    expect(screen.getByText(/10 à 45 secondes en général/)).toBeInTheDocument()
    expect(screen.queryByText('Plus long que d’habitude, la réponse arrive.')).not.toBeInTheDocument()
    act(() => { vi.advanceTimersByTime(2000) })
    expect(screen.queryByText(/10 à 45 secondes/)).not.toBeInTheDocument()
    expect(screen.getAllByRole('status').at(-1)).toHaveTextContent('Plus long que d’habitude, la réponse arrive.')
  })
})
