// Depot de cours depuis la page des matieres : plusieurs fichiers, glisser-deposer, progression et refus clairs.
import { useRef, useState, type DragEvent, type FormEvent } from 'react'
import { api, ApiError } from '../lib/api'
import { useApp } from '../state/contexte'
import { ACCEPT, FORMATS_LISIBLES, fichiersDeposes, refusFichier, sansExtension, titresDistincts } from '../lib/fichiers'
import { Card, CardHead } from './Layout'
import { OptionsMatieres } from './OptionsMatieres'
import { Rond } from './Chargement'

type Etat =
  | { etape: 'attente' }
  | { etape: 'envoi'; part: number }
  | { etape: 'lecture' }
  | { etape: 'fait'; message: string }
  | { etape: 'refus'; message: string }

interface Ligne { fichier: File; etat: Etat }

export function DepotCours() {
  const { matieres, mesCours, coursMax, rafraichirCours, notifier } = useApp()
  const [lignes, setLignes] = useState<Ligne[]>([])
  const [matiere, setMatiere] = useState('')
  const [titre, setTitre] = useState('')
  const [envoi, setEnvoi] = useState(false)
  // Bouton actif : la raison d'un refus est dite au clic (audit du 2026-11-19, WEB-10 ; audit du 2026-11-23, D8)
  const [aide, setAide] = useState<string | null>(null)
  const [survol, setSurvol] = useState(false)
  const choix = useRef<HTMLInputElement>(null)
  const place = coursMax > 0 ? Math.max(0, coursMax - mesCours.length) : Infinity
  const plein = place === 0
  const aEnvoyer = lignes.filter((l) => l.etat.etape === 'attente')

  const ajouter = (fichiers: File[]) => {
    if (envoi || fichiers.length === 0) return
    setAide(null)
    const neufs = fichiers.map((f): Ligne => {
      const refus = refusFichier(f)
      return { fichier: f, etat: refus ? { etape: 'refus', message: refus } : { etape: 'attente' } }
    })
    // Les fichiers deja envoyes ou refuses disparaissent : la liste ne montre que le nouveau choix.
    setLignes(neufs)
    setTitre(neufs.length === 1 && neufs[0].etat.etape === 'attente' ? sansExtension(neufs[0].fichier.name) : '')
  }

  const maj = (i: number, etat: Etat) => setLignes((ls) => ls.map((l, j) => (j === i ? { ...l, etat } : l)))

  const deposer = async (e: FormEvent) => {
    e.preventDefault()
    if (aEnvoyer.length === 0) return setAide('Choisissez d’abord un ou plusieurs fichiers.')
    if (!matiere) return setAide('Choisissez la matière du cours.')
    setAide(null)
    setEnvoi(true)
    let deposes = 0
    let restant = place
    const distincts = titresDistincts(aEnvoyer.map((l) => l.fichier.name))
    const titres = new Map(aEnvoyer.map((l, k) => [l, distincts[k]]))
    // Un fichier apres l'autre : le serveur ne lit qu'un depot a la fois par compte.
    for (const [i, l] of lignes.entries()) {
      if (l.etat.etape !== 'attente') continue
      if (restant <= 0) {
        maj(i, { etape: 'refus', message: `limite de ${coursMax} cours atteinte pour votre formule.` })
        continue
      }
      maj(i, { etape: 'envoi', part: 0 })
      try {
        const nom = aEnvoyer.length === 1 ? titre.trim() : titres.get(l) ?? sansExtension(l.fichier.name)
        const depose = await api.cours.deposerAvecProgres(l.fichier, matiere, nom, (part) =>
          maj(i, part >= 1 ? { etape: 'lecture' } : { etape: 'envoi', part }))
        deposes += 1
        restant -= 1
        const detail = `${depose.pages ? `${depose.pages} page${depose.pages > 1 ? 's' : ''}, ` : ''}${depose.passages} passage${depose.passages > 1 ? 's' : ''}`
        maj(i, { etape: 'fait', message: depose.avertissement ? `déposé (${detail}). ${depose.avertissement}` : `déposé (${detail}).` })
      } catch (err) {
        maj(i, { etape: 'refus', message: err instanceof ApiError ? err.message : 'le dépôt a échoué.' })
      }
    }
    setEnvoi(false)
    if (deposes) {
      rafraichirCours()
      notifier(deposes > 1 ? `${deposes} cours déposés : Lexia les prépare pour vos révisions.` : 'Cours déposé : Lexia le prépare pour vos révisions.')
    }
    if (choix.current) choix.current.value = ''
  }

  const deposerFichiers = async (e: DragEvent) => {
    e.preventDefault()
    setSurvol(false)
    ajouter(await fichiersDeposes(e.dataTransfer))
  }

  const champ = 'rounded-[7px] border border-line bg-white p-[9px] text-[12px] text-ink'
  return (
    <Card className="mb-[18px] p-4 tab:p-[19px]">
      <div onDragOver={(e) => { e.preventDefault(); setSurvol(true) }} onDragLeave={() => setSurvol(false)} onDrop={deposerFichiers}
        data-testid="zone-depot" className={survol ? 'rounded-[10px] outline-2 outline-dashed outline-forest outline-offset-4' : ''}>
        <CardHead titre="Déposer des cours"
          sousTitre={`${FORMATS_LISIBLES}, 20 Mo au plus par fichier. Glissez vos fichiers ici. Vos cours restent privés : vous seul pouvez les utiliser.`}
          droite={coursMax > 0 ? <span className="text-[11px] text-muted">{mesCours.length} / {coursMax} cours</span> : undefined} />
        <form onSubmit={deposer} className="mt-3.5 flex flex-wrap items-end gap-2">
          {/* Champ natif masque : son bouton s'affichait en anglais selon le navigateur (« Choose File »). */}
          <div className="grid min-w-[200px] flex-1 gap-1.5 text-[11px] text-muted">
            <span id="depot-fichier-libelle">Fichiers</span>
            <input ref={choix} id="depot-fichier" data-testid="depot-fichier" type="file" multiple accept={ACCEPT}
              className="sr-only" tabIndex={-1} aria-hidden onChange={(e) => ajouter([...(e.target.files ?? [])])} />
            <span className="flex items-center gap-2.5 rounded-[7px] border border-line bg-white px-[5px] py-[4px] text-[12px] text-ink">
              <button type="button" onClick={() => choix.current?.click()} aria-describedby="depot-fichier-nom" disabled={envoi}
                className="shrink-0 rounded-[6px] border border-line bg-chip px-2.5 py-1 text-[12px] text-forest hover:border-[#9eafa3]">
                Choisir des fichiers
              </button>
              <span id="depot-fichier-nom" className="min-w-0 truncate text-muted">
                {lignes.length === 0 ? 'Aucun fichier choisi' : lignes.length === 1 ? lignes[0].fichier.name : `${lignes.length} fichiers`}
              </span>
            </span>
          </div>
          <label className="grid gap-1.5 text-[11px] text-muted">
            Matière
            <select value={matiere} onChange={(e) => { setMatiere(e.target.value); setAide(null) }} className={champ}>
              <option value="">Choisir…</option>
              <OptionsMatieres matieres={matieres} />
            </select>
          </label>
          {aEnvoyer.length <= 1 && (
            <label className="grid min-w-[180px] flex-1 gap-1.5 text-[11px] text-muted">
              Titre (facultatif)
              <input value={titre} onChange={(e) => setTitre(e.target.value)} maxLength={120} placeholder="Ex. Chapitre 3 : les vices du consentement" className={champ} />
            </label>
          )}
          <button type="submit" disabled={envoi || plein} aria-describedby="aide-depot"
            className="inline-flex items-center gap-1.5 rounded-[7px] bg-forest px-3 py-[9px] text-[12px] text-white hover:bg-forest-dark disabled:opacity-50">
            {envoi && <Rond className="h-3.5 w-3.5" />}
            {envoi ? 'Envoi…' : aEnvoyer.length > 1 ? `Déposer ${aEnvoyer.length} cours` : 'Déposer'}
          </button>
          <p id="aide-depot" role="status" className="w-full text-[12px] text-[#8c4a36] empty:hidden">{aide ?? ''}</p>
        </form>
      </div>
      {plein && <p className="mt-2 text-[11px] text-[#8c4a36]">Limite atteinte pour votre formule : retirez un cours ou passez à une formule supérieure.</p>}
      {lignes.length > 0 && (
        <ul aria-label="Fichiers à déposer" className="mt-3 grid gap-1.5 text-[11px]">
          {lignes.map((l, i) => <LigneDepot key={`${i}-${l.fichier.name}`} ligne={l} />)}
        </ul>
      )}
    </Card>
  )
}

function LigneDepot({ ligne: { fichier, etat } }: { ligne: Ligne }) {
  const pourcent = etat.etape === 'envoi' ? Math.round(etat.part * 100) : etat.etape === 'attente' ? 0 : 100
  return (
    <li className="grid gap-1">
      <span className="flex justify-between gap-2">
        <span className="min-w-0 truncate font-semibold text-ink">{fichier.name}</span>
        <span className="inline-flex shrink-0 items-center gap-1 text-muted">
          {(etat.etape === 'envoi' || etat.etape === 'lecture') && <Rond className="h-3 w-3 text-forest" />}
          {etat.etape === 'attente' ? 'prêt à envoyer' : etat.etape === 'envoi' ? `envoi ${pourcent} %`
            : etat.etape === 'lecture' ? 'lecture du fichier (un scan peut prendre une minute)…' : etat.etape === 'fait' ? 'déposé' : 'refusé'}
        </span>
      </span>
      {(etat.etape === 'envoi' || etat.etape === 'lecture') && (
        <span role="progressbar" aria-label={`Dépôt de ${fichier.name}`} aria-valuemin={0} aria-valuemax={100}
          aria-valuenow={etat.etape === 'envoi' ? pourcent : undefined}
          aria-valuetext={etat.etape === 'lecture' ? 'Lecture du fichier' : `${pourcent} %`}
          className="block h-1.5 overflow-hidden rounded-full bg-chip">
          <span className={`block h-full bg-forest ${etat.etape === 'lecture' ? 'animate-pulse' : ''}`} style={{ width: `${pourcent}%` }} />
        </span>
      )}
      {etat.etape === 'fait' && <span role="status" className="text-muted">{etat.message}</span>}
      {etat.etape === 'refus' && <span role="alert" className="text-[#8c4a36]">{etat.message}</span>}
    </li>
  )
}
