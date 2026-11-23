import { fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'
import { reviser, type Carte } from '../lib/cartes'
import { Ctx, type AppState } from '../state/contexte'
import { CarteRevisions, SeanceRevision } from './Revision'

const hier = new Date(Date.now() - 86_400_000).toISOString()
const demain = new Date(Date.now() + 2 * 86_400_000).toISOString()
const carte = (id: string, recto: string, verso: string, prochaine = hier): Carte =>
  ({ id, origine: 'quiz', recto, verso, sources: [{ id: 's1', entete: 'Code civil, article 1240', url: '' }], niveau: 1, prochaine, creee_le: hier })

function Banc({ depart }: { depart: Carte[] }) {
  const [cartes, setCartes] = useState(depart)
  const [seance, setSeance] = useState(false)
  const valeur = {
    cartes, favoris: [], ajouterCartes: () => {}, ouvrirSource: () => {},
    noterCarte: (id: string, sue: boolean) => setCartes((l) => l.map((c) => (c.id === id ? reviser(c, sue) : c))),
    retirerCarte: (id: string) => setCartes((l) => l.filter((c) => c.id !== id)),
  } as unknown as AppState
  return (
    <Ctx.Provider value={valeur}>
      {seance ? <SeanceRevision onFin={() => setSeance(false)} /> : <CarteRevisions onReviser={() => setSeance(true)} />}
    </Ctx.Provider>
  )
}

describe('revision des cartes', () => {
  it('seance complete : recto, verso, notation, bilan, puis plus rien a revoir', () => {
    render(<Banc depart={[carte('a', 'Conditions de 1240 ?', 'Faute, dommage, lien'), carte('b', 'Vrai ou faux : X', 'Faux'),
      carte('c', 'Pas encore', '...', demain)]} />)
    expect(screen.getByText('2 cartes à revoir aujourd’hui, sur 3.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Réviser (2)' }))

    expect(screen.getByText('Carte 1 sur 2 · questionnaire')).toBeInTheDocument()
    expect(screen.queryByText('Faute, dommage, lien')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Voir la réponse' }))
    expect(screen.getByText('Faute, dommage, lien')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /\[1\] Code civil, article 1240/ })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Je savais' }))

    expect(screen.getByText('Vrai ou faux : X')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Voir la réponse' }))
    fireEvent.click(screen.getByRole('button', { name: 'À revoir' }))

    expect(screen.getByText('Séance terminée.')).toBeInTheDocument()
    expect(screen.getByText(/1 carte sue, 1 à revoir demain\./)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retour aux fiches' }))
    expect(screen.getByText('Rien à revoir aujourd’hui (3 cartes).')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Réviser' })).toBeDisabled()
  })

  it('annonce la carte puis la reponse et met le focus sur le verso (audit du 2026-11-23, D5)', () => {
    render(<Banc depart={[carte('a', 'Conditions de 1240 ?', 'Faute, dommage, lien'), carte('b', 'Vrai ou faux : X', 'Faux')]} />)
    fireEvent.click(screen.getByRole('button', { name: 'Réviser (2)' }))
    expect(screen.getByRole('status')).toHaveTextContent('Carte 1 sur 2 : Conditions de 1240 ?')
    fireEvent.click(screen.getByRole('button', { name: 'Voir la réponse' }))
    expect(screen.getByRole('status')).toHaveTextContent('Réponse : Faute, dommage, lien')
    expect(screen.getByRole('region', { name: 'Réponse' })).toHaveFocus()
    fireEvent.click(screen.getByRole('button', { name: 'Je savais' }))
    expect(screen.getByRole('status')).toHaveTextContent('Carte 2 sur 2 : Vrai ou faux : X')
  })

  it('retire une carte en deux temps (audit du 2026-11-23, D14)', () => {
    render(<Banc depart={[carte('a', 'Conditions de 1240 ?', 'Faute, dommage, lien')]} />)
    fireEvent.click(screen.getByText('Voir mes cartes (1)'))
    fireEvent.click(screen.getByRole('button', { name: /^Retirer la carte/ }))
    expect(screen.getByText('Voir mes cartes (1)')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /^Confirmer le retrait de la carte/ }))
    expect(screen.queryByText(/Voir mes cartes/)).not.toBeInTheDocument()
  })

  it('sans carte : invitation a en ajouter', () => {
    render(<Banc depart={[]} />)
    expect(screen.getByText(/Aucune carte pour l’instant/)).toBeInTheDocument()
  })
})
