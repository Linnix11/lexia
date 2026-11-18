// Choix des cours deposes sur lesquels travaillent l'assistant et les questionnaires (plusieurs a la fois),
// et bascule « Mon cours seulement » (sinon les cours completent les textes officiels).
import { useApp } from '../state/contexte'
import { STATUTS } from '../lib/fichiers'

export function ChoixCours({ surDepot }: { surDepot?: () => void }) {
  const { mesCours, coursChoisis, setCoursChoisis, avecOfficiel, setAvecOfficiel, setVue } = useApp()
  // Un cours « erreur » reste interrogeable par mots-cles (audit C10) : il est propose comme les autres.
  if (mesCours.length === 0) {
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
  const matieres = [...new Set(mesCours.map((c) => c.libelle_matiere))]
  const choisis = mesCours.filter((c) => coursChoisis.includes(c.id))
  const resume = choisis.length === 0 ? 'Aucun (textes officiels seuls)'
    : choisis.length === 1 ? choisis[0].titre : `${choisis.length} cours`
  const basculer = (id: number) =>
    setCoursChoisis(coursChoisis.includes(id) ? coursChoisis.filter((c) => c !== id) : [...coursChoisis, id])
  const seulement = !avecOfficiel
  return (
    <div className="flex w-full flex-wrap items-center gap-2">
      <details className="relative text-[11px]">
        <summary className="flex cursor-pointer list-none items-center gap-1.5 text-muted">
          {choisis.length > 1 ? 'Mes cours' : 'Mon cours'}
          <span className="max-w-[260px] truncate rounded-[7px] border border-line bg-white px-2 py-1.5 text-ink">
            {resume} ▾
          </span>
        </summary>
        <fieldset aria-label="Cours à interroger"
          className="absolute z-10 mt-1 grid max-h-[320px] min-w-[240px] gap-1 overflow-auto rounded-[8px] border border-line bg-white p-2.5 shadow-md">
          {matieres.map((m) => (
            <div key={m} className="grid gap-1">
              <span className="text-[10px] font-bold tracking-[1px] text-forest uppercase">{m}</span>
              {mesCours.filter((c) => c.libelle_matiere === m).map((c) => (
                <label key={c.id} className="flex items-center gap-2 text-ink">
                  <input type="checkbox" checked={coursChoisis.includes(c.id)} onChange={() => basculer(c.id)} />
                  <span>
                    {c.titre}
                    {c.statut !== 'pret' && <>{' '}<span className="text-muted">({STATUTS[c.statut]})</span></>}
                  </span>
                </label>
              ))}
            </div>
          ))}
          {choisis.length > 0 && (
            <button type="button" onClick={() => setCoursChoisis([])} className="justify-self-start text-[11px] text-muted hover:text-forest">
              Aucun (textes officiels seuls)
            </button>
          )}
        </fieldset>
      </details>
      {choisis.length > 0 && (
        // Interrupteur : allume, la reponse ne s'appuie que sur les cours deposes ; eteint, les textes
        // officiels completent les cours.
        <button type="button" role="switch" aria-checked={seulement} onClick={() => setAvecOfficiel(seulement)}
          className={`flex items-center gap-2 rounded-full border px-2.5 py-1 text-[11px] ${
            seulement ? 'border-forest bg-mint font-semibold text-forest' : 'border-line bg-chip text-[#59615b] hover:border-[#9eafa3]'
          }`}>
          <span aria-hidden className={`relative h-[14px] w-[26px] rounded-full transition-colors ${seulement ? 'bg-forest' : 'bg-[#c9cec7]'}`}>
            <span className={`absolute top-[2px] size-[10px] rounded-full bg-white transition-all ${seulement ? 'left-[14px]' : 'left-[2px]'}`} />
          </span>
          {choisis.length > 1 ? 'Mes cours seulement' : 'Mon cours seulement'}
        </button>
      )}
    </div>
  )
}
