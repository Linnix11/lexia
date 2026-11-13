// Choix du cours depose sur lequel travaillent l'assistant et les questionnaires,
// et bascule « Mon cours seulement » (sinon le cours complete les textes officiels).
import { useApp } from '../state/contexte'

export function ChoixCours({ surDepot }: { surDepot?: () => void }) {
  const { mesCours, coursChoisi, setCoursChoisi, avecOfficiel, setAvecOfficiel, setVue } = useApp()
  const prets = mesCours.filter((c) => c.statut !== 'erreur')
  if (prets.length === 0) {
    return (
      <p className="w-full text-[11px] text-muted">
        Travaillez sur votre propre cours :{' '}
        <button type="button" onClick={() => (surDepot ? surDepot() : setVue('matieres'))}
          className="font-semibold text-forest hover:underline">
          {surDepot ? 'déposez-le avec le trombone' : 'déposez-le dans « Mes matières »'}
        </button>
        .
      </p>
    )
  }
  const matieres = [...new Set(prets.map((c) => c.libelle_matiere))]
  const seulement = !avecOfficiel
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
        // Interrupteur : allume, la reponse ne s'appuie que sur le cours depose ; eteint, les textes
        // officiels completent le cours.
        <button type="button" role="switch" aria-checked={seulement} onClick={() => setAvecOfficiel(seulement)}
          className={`flex items-center gap-2 rounded-full border px-2.5 py-1 text-[11px] ${
            seulement ? 'border-forest bg-mint font-semibold text-forest' : 'border-line bg-chip text-[#59615b] hover:border-[#9eafa3]'
          }`}>
          <span aria-hidden className={`relative h-[14px] w-[26px] rounded-full transition-colors ${seulement ? 'bg-forest' : 'bg-[#c9cec7]'}`}>
            <span className={`absolute top-[2px] size-[10px] rounded-full bg-white transition-all ${seulement ? 'left-[14px]' : 'left-[2px]'}`} />
          </span>
          Mon cours seulement
        </button>
      )}
    </div>
  )
}
