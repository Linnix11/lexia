// Revision des cartes a retourner (lib/cartes.ts) : resume dans « Fiches & revisions » et seance carte par carte.
import { useState } from 'react'
import { aReviser, carteDeFiche, INTERVALLES_JOURS, type Carte } from '../lib/cartes'
import { tronquer } from '../lib/personnalisation'
import { useApp } from '../state/contexte'
import { Card, CardHead } from './Layout'

const bouton = 'rounded-[7px] border border-line px-3 py-2 text-[12px] text-forest hover:border-[#9eafa3] disabled:opacity-60'
const boutonPlein = 'rounded-[7px] bg-forest px-3 py-2 text-[12px] text-white hover:bg-forest-dark disabled:opacity-60'

const pluriel = (n: number, mot: string) => `${n} ${mot}${n > 1 ? 's' : ''}`
const jour = (iso: string) => new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' })

/** Resume : cartes a revoir, lancement de la seance, ajout des fiches, liste des cartes. */
export function CarteRevisions({ onReviser }: { onReviser: () => void }) {
  const { cartes, favoris, ajouterCartes, retirerCarte } = useApp()
  const [maintenant] = useState(() => new Date()) // heure d'ouverture de la vue
  const dues = aReviser(cartes, maintenant).length
  const tirees = () => ajouterCartes(favoris.map((f) => carteDeFiche(f)).filter((c): c is Carte => c !== null))
  return (
    <Card className="mb-[18px] p-4 tab:p-[19px]">
      <CardHead titre="Cartes à réviser"
        sousTitre={`Revues après ${INTERVALLES_JOURS.join(', ')} jours tant que vous les savez ; une carte ratée revient le lendemain.`} />
      <p className="mt-3 text-[13px]">
        {cartes.length === 0
          ? 'Aucune carte pour l’instant : ajoutez vos fiches ou, après la correction d’un questionnaire, ses questions.'
          : dues > 0
            ? `${pluriel(dues, 'carte')} à revoir aujourd’hui, sur ${cartes.length}.`
            : `Rien à revoir aujourd’hui (${pluriel(cartes.length, 'carte')}).`}
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        <button type="button" onClick={onReviser} disabled={dues === 0} className={boutonPlein}
          title={dues === 0 ? 'Aucune carte à revoir aujourd’hui.' : undefined}>
          Réviser{dues > 0 ? ` (${dues})` : ''}
        </button>
        {favoris.length > 0 && (
          <button type="button" onClick={tirees} className={bouton}>Ajouter mes fiches aux cartes</button>
        )}
      </div>
      {cartes.length > 0 && (
        <details className="mt-3 text-[12px]">
          <summary className="cursor-pointer text-forest">Voir mes cartes ({cartes.length})</summary>
          <ul className="mt-2">
            {cartes.map((c) => (
              <li key={c.id} className="flex items-start justify-between gap-3 border-t border-line-soft py-2">
                <span className="min-w-0">
                  {tronquer(c.recto, 90)}
                  <span className="block text-[11px] text-muted">
                    {c.origine === 'quiz' ? 'Questionnaire' : 'Fiche'} · niveau {c.niveau} sur {INTERVALLES_JOURS.length} ·{' '}
                    {Date.parse(c.prochaine) <= maintenant.getTime() ? 'à revoir' : `prochaine révision le ${jour(c.prochaine)}`}
                  </span>
                </span>
                <button type="button" onClick={() => retirerCarte(c.id)} aria-label={`Retirer la carte « ${tronquer(c.recto, 40)} »`}
                  className="shrink-0 text-[11px] text-muted hover:text-[#8c4a36]">Retirer</button>
              </li>
            ))}
          </ul>
        </details>
      )}
    </Card>
  )
}

/** Seance : les cartes dues au lancement, une par une ; recto, puis verso et sources, puis « su » ou « a revoir ». */
export function SeanceRevision({ onFin }: { onFin: () => void }) {
  const { cartes, noterCarte, ouvrirSource } = useApp()
  // File figee au lancement : une carte notee ne revient pas dans la meme seance.
  const [debut] = useState(() => new Date())
  const [file] = useState(() => aReviser(cartes, debut).map((c) => c.id))
  const [position, setPosition] = useState(0)
  const [retournee, setRetournee] = useState(false)
  const [bilan, setBilan] = useState({ sues: 0, aRevoir: 0 })
  const carte = cartes.find((c) => c.id === file[position])

  const noter = (sue: boolean) => {
    if (!carte) return
    noterCarte(carte.id, sue)
    setBilan((b) => (sue ? { ...b, sues: b.sues + 1 } : { ...b, aRevoir: b.aRevoir + 1 }))
    setRetournee(false)
    setPosition((p) => p + 1)
  }

  if (!carte) {
    const prochaines = cartes.filter((c) => Date.parse(c.prochaine) > debut.getTime()).map((c) => c.prochaine).sort()
    return (
      <Card className="mb-[18px] p-6 text-center">
        <p className="font-display text-[21px]">Séance terminée.</p>
        <p className="mt-1.5 text-[13px] text-muted">
          {pluriel(bilan.sues, 'carte')} sue{bilan.sues > 1 ? 's' : ''}, {bilan.aRevoir} à revoir demain.
          {prochaines.length > 0 && ` Prochaine révision le ${jour(prochaines[0])}.`}
        </p>
        <button type="button" onClick={onFin} className={`mt-4 ${boutonPlein}`}>Retour aux fiches</button>
      </Card>
    )
  }

  return (
    <Card className="mb-[18px] p-4 tab:p-[19px]">
      <div className="flex items-center justify-between gap-3 text-[11px] text-muted">
        <span>Carte {position + 1} sur {file.length} · {carte.origine === 'quiz' ? 'questionnaire' : 'fiche'}</span>
        <button type="button" onClick={onFin} className="text-forest hover:underline">Arrêter</button>
      </div>
      <p className="mt-3 font-display text-[19px] leading-[1.35] whitespace-pre-line">{carte.recto}</p>
      {!retournee ? (
        <button type="button" onClick={() => setRetournee(true)} className={`mt-4 ${boutonPlein}`} autoFocus>
          Voir la réponse
        </button>
      ) : (
        <>
          <div className="mt-4 rounded-lg bg-[#f6f4ee] px-3 py-2.5 text-[13px] leading-[1.55] whitespace-pre-line" aria-live="polite">
            {carte.verso}
          </div>
          {carte.sources.length > 0 && (
            <span className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
              {carte.sources.map((s, i) => (
                <button key={s.id} type="button" onClick={() => ouvrirSource(s.id)} title={s.entete}
                  className="text-[11px] font-semibold text-forest hover:underline">
                  [{i + 1}] {tronquer(s.entete, 60)}
                </button>
              ))}
            </span>
          )}
          <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" onClick={() => noter(false)} className={bouton}>À revoir</button>
            <button type="button" onClick={() => noter(true)} className={boutonPlein} autoFocus>Je savais</button>
          </div>
        </>
      )}
    </Card>
  )
}
