// Revision des cartes a retourner (lib/cartes.ts) : resume dans « Fiches & revisions » et seance carte par carte.
import { useEffect, useRef, useState } from 'react'
import { aReviser, carteDeFiche, INTERVALLES_JOURS, progres, type Carte } from '../lib/cartes'
import { tronquer } from '../lib/personnalisation'
import { useApp } from '../state/contexte'
import { Card, CardHead } from './Layout'

const bouton = 'rounded-[7px] border border-line px-3 py-2 text-[12px] text-forest hover:border-[#9eafa3] disabled:opacity-60'
const boutonPlein = 'rounded-[7px] bg-forest px-3 py-2 text-[12px] text-white hover:bg-forest-dark disabled:opacity-60'
const touche = 'rounded border border-line bg-white px-1 font-sans text-[10px] text-ink'

const pluriel = (n: number, mot: string) => `${n} ${mot}${n > 1 ? 's' : ''}`
const jour = (iso: string) => new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' })
const deLaMatiere = (matiere: string | null) => (c: Carte) => !matiere || c.matiere === matiere

/** Resume : cartes a revoir, progres, lancement de la seance (toutes matieres ou une seule), ajout des fiches, liste. */
export function CarteRevisions({ onReviser }: { onReviser: (matiere: string | null) => void }) {
  const { cartes, favoris, matieres, ajouterCartes, retirerCarte } = useApp()
  const [maintenant] = useState(() => new Date()) // heure d'ouverture de la vue
  // Retrait d'une carte en deux temps, comme les fiches (WEB-20 ; audit du 2026-11-23, D14)
  const [aRetirer, setARetirer] = useState<string | null>(null)
  const [matiere, setMatiere] = useState<string | null>(null)
  const libelle = (id: string) => matieres?.find((m) => m.id === id)?.libelle ?? id
  // Matieres des cartes tirees d'un questionnaire (D140) : une seance par matiere avant un partiel
  const parMatiere = [...new Set(cartes.map((c) => c.matiere).filter((m): m is string => !!m))]
    .map((id) => ({ id, total: cartes.filter((c) => c.matiere === id).length,
      dues: aReviser(cartes.filter((c) => c.matiere === id), maintenant).length }))
  const choisie = parMatiere.some((m) => m.id === matiere) ? matiere : null
  const dues = aReviser(cartes.filter(deLaMatiere(choisie)), maintenant).length
  const toutesDues = aReviser(cartes, maintenant).length
  const p = progres(cartes, maintenant)
  const tirees = () => ajouterCartes(favoris.map((f) => carteDeFiche(f)).filter((c): c is Carte => c !== null))
  return (
    <Card className="mb-[18px] p-4 tab:p-[19px]">
      <CardHead titre="Cartes à réviser"
        sousTitre={`Revues après ${INTERVALLES_JOURS.join(', ')} jours tant que vous les savez ; une carte ratée revient en fin de séance, puis le lendemain.`} />
      <p className="mt-3 text-[13px]">
        {cartes.length === 0
          ? 'Aucune carte pour l’instant : ajoutez vos fiches ou, après la correction d’un questionnaire, ses questions ou vos erreurs.'
          : toutesDues > 0
            ? `${pluriel(toutesDues, 'carte')} à revoir aujourd’hui, sur ${cartes.length}.`
            : `Rien à revoir aujourd’hui (${pluriel(cartes.length, 'carte')}).`}
      </p>
      {cartes.length > 0 && (
        <div className="mt-2.5">
          {/* Progres (D140) : la barre est decorative, le texte dit la meme chose */}
          <div aria-hidden className="flex h-2 overflow-hidden rounded-full bg-[#ece9e0]">
            <span className="bg-forest" style={{ width: `${(100 * p.acquises) / cartes.length}%` }} />
            <span className="bg-[#9eafa3]" style={{ width: `${(100 * p.enCours) / cartes.length}%` }} />
          </div>
          <p className="mt-1.5 text-[11px] text-muted">
            {p.acquises} acquise{p.acquises > 1 ? 's' : ''} (niveau 4 ou 5) · {p.enCours} en cours · {p.nouvelles} nouvelle{p.nouvelles > 1 ? 's' : ''} ou ratée{p.nouvelles > 1 ? 's' : ''}
            {p.semaine > 0 && ` · à venir : ${p.demain} demain, ${p.semaine} dans les 7 jours`}
          </p>
        </div>
      )}
      <div className="mt-3 flex flex-wrap items-end gap-2">
        {parMatiere.length > 0 && (
          <label className="grid min-w-0 gap-1 text-[11px] text-muted">
            Matière
            <select value={choisie ?? ''} onChange={(e) => setMatiere(e.target.value || null)}
              className="min-h-[38px] max-w-full min-w-0 rounded-[7px] border border-line bg-white px-2 text-[12px] text-ink">
              <option value="">Toutes ({toutesDues} à revoir)</option>
              {parMatiere.map((m) => (
                <option key={m.id} value={m.id}>{libelle(m.id)} ({m.dues} à revoir sur {m.total})</option>
              ))}
            </select>
          </label>
        )}
        <button type="button" onClick={() => onReviser(choisie)} disabled={dues === 0} className={boutonPlein}
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
                    {c.origine === 'quiz' ? 'Questionnaire' : 'Fiche'}{c.matiere ? ` · ${libelle(c.matiere)}` : ''} · niveau {c.niveau} sur {INTERVALLES_JOURS.length} ·{' '}
                    {Date.parse(c.prochaine) <= maintenant.getTime() ? 'à revoir' : `prochaine révision le ${jour(c.prochaine)}`}
                  </span>
                </span>
                <button type="button"
                  onClick={() => {
                    if (aRetirer !== c.id) return setARetirer(c.id)
                    setARetirer(null)
                    retirerCarte(c.id)
                  }}
                  onBlur={() => setARetirer((x) => (x === c.id ? null : x))}
                  aria-label={aRetirer === c.id ? `Confirmer le retrait de la carte « ${tronquer(c.recto, 40)} »` : `Retirer la carte « ${tronquer(c.recto, 40)} »`}
                  className={`shrink-0 text-[11px] hover:text-[#8c4a36] ${aRetirer === c.id ? 'font-semibold text-[#8c4a36]' : 'text-muted'}`}>
                  {aRetirer === c.id ? 'Confirmer le retrait' : 'Retirer'}
                </button>
              </li>
            ))}
          </ul>
        </details>
      )}
    </Card>
  )
}

interface Passage {
  id: string
  rattrapage: boolean // carte ratee plus tot dans la seance, remontree a la fin (sans changer sa prochaine date)
}

/** La cible du clavier est un champ ou une commande : la touche lui revient (Entree sur un bouton, Espace dans un select). */
const cibleInteractive = (t: EventTarget | null) =>
  t instanceof HTMLElement && (t.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON', 'A', 'SUMMARY'].includes(t.tagName))

/** Seance : les cartes dues au lancement, une par une ; recto, puis verso et sources, puis « su » ou « a revoir ».
 * Une carte ratee revient en fin de seance jusqu'a ce qu'elle soit sue (rattrapage, D140) ; sa date de revision
 * reste celle de la premiere note (demain). Clavier : Espace ou Entree retourne, 1 « A revoir », 2 « Je savais ». */
export function SeanceRevision({ onFin, matiere = null }: { onFin: () => void; matiere?: string | null }) {
  const { cartes, noterCarte, ouvrirSource } = useApp()
  // File figee au lancement : une carte notee ne revient que pour le rattrapage.
  const [debut] = useState(() => new Date())
  const [file, setFile] = useState<Passage[]>(() =>
    aReviser(cartes.filter(deLaMatiere(matiere)), debut).map((c) => ({ id: c.id, rattrapage: false })))
  const [premiers] = useState(file.length)
  const [position, setPosition] = useState(0)
  const [retournee, setRetournee] = useState(false)
  const [bilan, setBilan] = useState({ sues: 0, aRevoir: 0, rattrapees: 0 })
  const passage = file[position]
  const carte = passage && cartes.find((c) => c.id === passage.id)
  // Verso focalise a l'affichage : le lecteur d'ecran le lit avant « Je savais » (audit du 2026-11-23, D5)
  const verso = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (retournee) verso.current?.focus()
  }, [retournee])

  const noter = (sue: boolean) => {
    if (!carte || !passage) return
    if (!passage.rattrapage) noterCarte(carte.id, sue)
    if (!sue) setFile((f) => [...f, { id: carte.id, rattrapage: true }])
    setBilan((b) => passage.rattrapage
      ? (sue ? { ...b, rattrapees: b.rattrapees + 1 } : b)
      : (sue ? { ...b, sues: b.sues + 1 } : { ...b, aRevoir: b.aRevoir + 1 }))
    setRetournee(false)
    setPosition((p) => p + 1)
  }

  // Raccourcis (D140) : sur la page entiere tant que la seance est affichee, sauf dans un champ ou sur une commande
  const action = useRef({ retournee, noter })
  useEffect(() => {
    action.current = { retournee, noter }
  })
  useEffect(() => {
    const surTouche = (e: KeyboardEvent) => {
      if (e.altKey || e.ctrlKey || e.metaKey || e.defaultPrevented) return
      const a = action.current
      if (!a.retournee && (e.key === ' ' || e.key === 'Enter') && !cibleInteractive(e.target)) {
        e.preventDefault()
        setRetournee(true)
      } else if (a.retournee && (e.key === '1' || e.key === '2') && !(e.target instanceof HTMLElement && ['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName))) {
        e.preventDefault()
        a.noter(e.key === '2')
      }
    }
    window.addEventListener('keydown', surTouche)
    return () => window.removeEventListener('keydown', surTouche)
  }, [])

  if (!carte) {
    const prochaines = cartes.filter((c) => Date.parse(c.prochaine) > debut.getTime()).map((c) => c.prochaine).sort()
    return (
      <Card className="mb-[18px] p-6 text-center">
        <p className="font-display text-[21px]">Séance terminée.</p>
        <p className="mt-1.5 text-[13px] text-muted">
          {pluriel(bilan.sues, 'carte')} sue{bilan.sues > 1 ? 's' : ''}, {bilan.aRevoir} à revoir demain.
          {bilan.rattrapees > 0 && ` ${pluriel(bilan.rattrapees, 'carte')} ratée${bilan.rattrapees > 1 ? 's' : ''} puis retrouvée${bilan.rattrapees > 1 ? 's' : ''} en fin de séance.`}
          {prochaines.length > 0 && ` Prochaine révision le ${jour(prochaines[0])}.`}
        </p>
        <button type="button" onClick={onFin} className={`mt-4 ${boutonPlein}`}>Retour aux fiches</button>
      </Card>
    )
  }

  const rang = passage.rattrapage ? `Rattrapage · ${file.length - position} restante${file.length - position > 1 ? 's' : ''}`
    : `Carte ${position + 1} sur ${premiers}`
  return (
    <Card className="mb-[18px] p-4 tab:p-[19px]">
      <div className="flex items-center justify-between gap-3 text-[11px] text-muted">
        <span>{rang} · {carte.origine === 'quiz' ? 'questionnaire' : 'fiche'}</span>
        <button type="button" onClick={onFin} className="text-forest hover:underline">Arrêter</button>
      </div>
      <p className="mt-3 font-display text-[19px] leading-[1.35] whitespace-pre-line">{carte.recto}</p>
      {/* Toujours present : annonce la carte suivante, puis la reponse (un aria-live cree avec son contenu se tait) */}
      <p role="status" className="sr-only">
        {retournee ? `Réponse : ${carte.verso}` : `${rang} : ${carte.recto}`}
      </p>
      {!retournee ? (
        <button type="button" onClick={() => setRetournee(true)} className={`mt-4 ${boutonPlein}`} autoFocus
          aria-keyshortcuts="Space Enter">
          Voir la réponse
        </button>
      ) : (
        <>
          <div ref={verso} tabIndex={-1} aria-label="Réponse" role="region"
            className="mt-4 rounded-lg bg-[#f6f4ee] px-3 py-2.5 text-[13px] leading-[1.55] whitespace-pre-line">
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
            <button type="button" onClick={() => noter(false)} className={`min-h-11 ${bouton}`} aria-keyshortcuts="1">À revoir</button>
            <button type="button" onClick={() => noter(true)} className={`min-h-11 ${boutonPlein}`} aria-keyshortcuts="2">Je savais</button>
          </div>
        </>
      )}
      {/* Rappel des raccourcis, sur grand ecran seulement (pas de clavier sur telephone) */}
      <p className="mt-3 hidden text-[11px] text-muted tab:block">
        Clavier : <kbd className={touche}>Espace</kbd> retourner · <kbd className={touche}>1</kbd> à revoir · <kbd className={touche}>2</kbd> je savais
      </p>
    </Card>
  )
}
