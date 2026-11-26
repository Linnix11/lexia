import { fireEvent, render, screen } from '@testing-library/react'
import { useEffect, useState } from 'react'
import { describe, expect, it } from 'vitest'
import { reviser, type Carte } from '../lib/cartes'
import { Ctx, type AppState } from '../state/contexte'
import { CarteRevisions, SeanceRevision } from './Revision'

const hier = new Date(Date.now() - 86_400_000).toISOString()
const demain = new Date(Date.now() + 2 * 86_400_000).toISOString()
const carte = (id: string, recto: string, verso: string, prochaine = hier): Carte =>
  ({ id, origine: 'quiz', recto, verso, sources: [{ id: 's1', entete: 'Code civil, article 1240', url: '' }], niveau: 1, prochaine, creee_le: hier })

let dernieres: Carte[] = []

function Banc({ depart }: { depart: Carte[] }) {
  const [cartes, setCartes] = useState(depart)
  const [seance, setSeance] = useState<{ matiere: string | null } | null>(null)
  useEffect(() => {
    dernieres = cartes
  })
  const valeur = {
    cartes, favoris: [], ajouterCartes: () => {}, ouvrirSource: () => {},
    matieres: [{ id: 'droit_civil', libelle: 'Droit civil' }, { id: 'droit_penal', libelle: 'Droit pénal' }],
    noterCarte: (id: string, sue: boolean) => setCartes((l) => l.map((c) => (c.id === id ? reviser(c, sue) : c))),
    retirerCarte: (id: string) => setCartes((l) => l.filter((c) => c.id !== id)),
  } as unknown as AppState
  return (
    <Ctx.Provider value={valeur}>
      {seance ? <SeanceRevision matiere={seance.matiere} onFin={() => setSeance(null)} />
        : <CarteRevisions onReviser={(matiere) => setSeance({ matiere })} />}
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

    // la carte ratee revient en fin de seance (D140), sans changer sa prochaine date
    expect(screen.getByText('Rattrapage · 1 restante · questionnaire')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Voir la réponse' }))
    fireEvent.click(screen.getByRole('button', { name: 'Je savais' }))

    expect(screen.getByText('Séance terminée.')).toBeInTheDocument()
    expect(screen.getByText(/1 carte sue, 1 à revoir demain\. 1 carte ratée puis retrouvée en fin de séance\./)).toBeInTheDocument()
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

  it('clavier : Espace retourne, 1 « a revoir », 2 « je savais » ; le rattrapage ne fait pas monter la carte (D140)', () => {
    render(<Banc depart={[carte('a', 'Conditions de 1240 ?', 'Faute, dommage, lien'), carte('b', 'Vrai ou faux : X', 'Faux')]} />)
    fireEvent.click(screen.getByRole('button', { name: 'Réviser (2)' }))
    fireEvent.keyDown(document.body, { key: ' ' })
    expect(screen.getByText('Faute, dommage, lien')).toBeInTheDocument()
    fireEvent.keyDown(document.body, { key: '2' })
    expect(screen.getByText('Vrai ou faux : X')).toBeInTheDocument()
    fireEvent.keyDown(document.body, { key: '2' }) // pas encore retournee : sans effet
    expect(screen.queryByRole('region', { name: 'Réponse' })).not.toBeInTheDocument()
    fireEvent.keyDown(document.body, { key: 'Enter' })
    fireEvent.keyDown(document.body, { key: '1' })
    expect(screen.getByText('Rattrapage · 1 restante · questionnaire')).toBeInTheDocument()
    fireEvent.keyDown(document.body, { key: ' ' })
    fireEvent.keyDown(document.body, { key: '2' })
    expect(screen.getByText('Séance terminée.')).toBeInTheDocument()
    expect(dernieres.find((c) => c.id === 'a')?.niveau).toBe(2)
    expect(dernieres.find((c) => c.id === 'b')?.niveau).toBe(1) // ratee puis retrouvee : revient demain quand meme
  })

  it('progres par niveau et seance limitee a une matiere (D140)', () => {
    render(<Banc depart={[{ ...carte('a', 'Civil 1', 'v'), matiere: 'droit_civil', niveau: 4 },
      { ...carte('b', 'Civil 2', 'v', demain), matiere: 'droit_civil', niveau: 2 },
      { ...carte('c', 'Pénal 1', 'v'), matiere: 'droit_penal' }, carte('d', 'Fiche', 'v')]} />)
    expect(screen.getByText(/1 acquise \(niveau 4 ou 5\) · 1 en cours · 2 nouvelles ou ratées/)).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Droit civil (1 à revoir sur 2)' })).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Matière'), { target: { value: 'droit_penal' } })
    fireEvent.click(screen.getByRole('button', { name: 'Réviser (1)' }))
    expect(screen.getByText('Pénal 1')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Voir la réponse' }))
    fireEvent.click(screen.getByRole('button', { name: 'Je savais' }))
    expect(screen.getByText('Séance terminée.')).toBeInTheDocument()
  })

  it('sans carte : invitation a en ajouter', () => {
    render(<Banc depart={[]} />)
    expect(screen.getByText(/Aucune carte pour l’instant/)).toBeInTheDocument()
  })
})
