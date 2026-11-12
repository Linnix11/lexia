// Choix du cours depose sur lequel travaillent l'assistant et les questionnaires,
// et de l'option visible « Mon cours uniquement » / « Mon cours + textes officiels ».
import { useApp } from '../state/contexte'

export function ChoixCours() {
  const { mesCours, coursChoisi, setCoursChoisi, avecOfficiel, setAvecOfficiel, setVue } = useApp()
  const prets = mesCours.filter((c) => c.statut !== 'erreur')
  if (prets.length === 0) {
    return (
      <p className="w-full text-[11px] text-muted">
        Travaillez sur votre propre cours :{' '}
        <button type="button" onClick={() => setVue('matieres')} className="font-semibold text-forest hover:underline">
          déposez-le dans « Mes matières »
        </button>
        .
      </p>
    )
  }
  const matieres = [...new Set(prets.map((c) => c.libelle_matiere))]
  const option = (actif: boolean) =>
    `rounded-full border px-2.5 py-1.5 text-[11px] ${actif ? 'border-forest bg-mint font-semibold text-forest' : 'border-line bg-chip text-[#59615b] hover:border-[#9eafa3]'}`
  return (
    <div className="flex w-full flex-wrap items-center gap-2">
      <label className="flex items-center gap-1.5 text-[11px] text-muted">
        Mon cours
        <select
          value={coursChoisi ?? ''}
          onChange={(e) => setCoursChoisi(e.target.value ? Number(e.target.value) : null)}
          className="max-w-[260px] rounded-[7px] border border-line bg-white px-2 py-1.5 text-[11px] text-ink"
        >
          <option value="">Aucun (textes officiels seuls)</option>
          {matieres.map((m) => (
            <optgroup key={m} label={m}>
              {prets.filter((c) => c.libelle_matiere === m).map((c) => (
                <option key={c.id} value={c.id}>{c.titre}</option>
              ))}
            </optgroup>
          ))}
        </select>
      </label>
      {coursChoisi !== null && (
        <div role="radiogroup" aria-label="Sources utilisées" className="flex flex-wrap gap-1.5">
          <button type="button" role="radio" aria-checked={!avecOfficiel} onClick={() => setAvecOfficiel(false)} className={option(!avecOfficiel)}>
            Mon cours uniquement
          </button>
          <button type="button" role="radio" aria-checked={avecOfficiel} onClick={() => setAvecOfficiel(true)} className={option(avecOfficiel)}>
            Mon cours + textes officiels
          </button>
        </div>
      )}
    </div>
  )
}
