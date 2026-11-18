// Options d'une liste de matieres, regroupees par annee de licence (D97).
import type { Matiere } from '../lib/api'
import { grouperParAnnee } from '../lib/matieres'

export function OptionsMatieres({ matieres }: { matieres: Matiere[] }) {
  return (
    <>
      {grouperParAnnee(matieres).map((g) => (
        <optgroup key={g.titre} label={g.titre}>
          {g.matieres.map((m) => <option key={m.id} value={m.id}>{m.libelle}</option>)}
        </optgroup>
      ))}
    </>
  )
}
