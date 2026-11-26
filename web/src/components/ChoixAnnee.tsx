// Premiere ouverture de l'espace : l'annee et le semestre sont demandes au lieu de partir en L1 sans le dire.
// Les reponses, les manuels et les annales en dependent (D130). La carte disparait des que le semestre est choisi,
// ici ou dans le menu de l'en-tete (audit du 2026-11-25, G-2 ; D142).
import { useState } from 'react'
import { ANNEES, LIBELLES_ANNEES, type Annee } from '../lib/matieres'
import { libelleSemestre, niveauDe, SEMESTRES } from '../lib/semestres'
import { useApp } from '../state/contexte'

const bouton = 'min-h-11 rounded-full border px-4 text-[14px]'
const choisi = 'border-forest bg-forest font-semibold text-white'
const libre = 'border-[#9eafa3] bg-surface text-forest hover:bg-sage'

export function ChoixAnnee({ className = '' }: { className?: string }) {
  const { semestreChoisi, setSemestre, notifier } = useApp()
  const [annee, setAnnee] = useState<Annee | null>(null)
  if (semestreChoisi) return null
  return (
    <section aria-labelledby="choix-annee" className={`rounded-xl border border-[#c5d3c9] bg-mint px-4 py-4 tab:px-[22px] ${className}`}>
      <h2 id="choix-annee" className="text-[17px] font-[650] text-ink">En quelle année êtes-vous&nbsp;?</h2>
      <p className="mt-1 max-w-[60ch] text-[13px] leading-[1.5] text-[#4f5a53]">
        Lexia adapte ses réponses, les manuels et les annales à votre année. Vous pourrez la changer en haut de la page.
      </p>
      <div role="group" aria-label="Année de licence" className="mt-3 flex flex-wrap gap-2">
        {ANNEES.map((a) => (
          <button key={a} type="button" aria-pressed={annee === a} onClick={() => setAnnee(a)}
            title={LIBELLES_ANNEES[a]} className={`${bouton} ${annee === a ? choisi : libre}`}>
            {a}
          </button>
        ))}
      </div>
      {annee && (
        <>
          <p className="mt-3 text-[13px] font-semibold text-ink">Et le semestre ?</p>
          <div role="group" aria-label="Semestre" className="mt-2 flex flex-wrap gap-2">
            {SEMESTRES.filter((s) => niveauDe(s) === annee).map((s) => (
              <button key={s} type="button" className={`${bouton} ${libre}`}
                onClick={() => { setSemestre(s); notifier(`Année enregistrée : ${libelleSemestre(s)}`) }}>
                Semestre {s}
              </button>
            ))}
          </div>
        </>
      )}
    </section>
  )
}
