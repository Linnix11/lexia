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
})
