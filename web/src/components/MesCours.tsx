// Cours deposes par l'etudiant : liste par matiere (apercu, modification, retrait) et depot rapide depuis l'assistant.
import { useState, type FormEvent } from 'react'
import { api, ApiError, type ApercuCours, type CoursDepose } from '../lib/api'
import { useApp } from '../state/contexte'
import { FORMATS_LISIBLES, formatAccepte, refusFichier, sansExtension, STATUTS } from '../lib/fichiers'
import { OptionsMatieres } from './OptionsMatieres'
import { CarteMentale } from './CarteMentale'
import { ResumeVocal } from './ResumeVocal'

export { DepotCours } from './DepotCours'

export function ListeCoursMatiere({ matiere }: { matiere: string }) {
  const { mesCours, rafraichirCours, setCoursChoisis, setMatiere, setVue, coursChoisis, notifier } = useApp()
  const liste = mesCours.filter((c) => c.matiere === matiere)
  if (liste.length === 0) return null
  const retirer = (id: number, titre: string) => {
    if (!window.confirm(`Retirer définitivement le cours « ${titre} » ?`)) return
    api.cours.supprimer(id)
      .then(() => {
        setCoursChoisis(coursChoisis.filter((c) => c !== id))
        notifier('Cours retiré')
        rafraichirCours()
      })
      .catch((e) => notifier(e instanceof ApiError ? e.message : 'Le retrait a échoué.'))
  }
  return (
    <div className="mb-4 border-t border-line-soft pt-3">
      <h3 className="mb-1.5 text-[10px] font-bold tracking-[1.4px] text-forest uppercase">Mes cours</h3>
      <ul className="grid gap-2">
        {liste.map((c) => (
          <CoursLigne key={c.id} cours={c} onReviser={() => { setCoursChoisis([c.id]); setMatiere(matiere); setVue('assistant') }}
            onRetirer={() => retirer(c.id, c.titre)} />
        ))}
      </ul>
    </div>
  )
}

const pluriel = (n: number, mot: string) => `${n} ${mot}${n > 1 ? 's' : ''}`

/** Un cours de la liste : pages et passages, apercu du texte lu, modification du titre et de la matiere. */
function CoursLigne({ cours: c, onReviser, onRetirer }: { cours: CoursDepose; onReviser: () => void; onRetirer: () => void }) {
  const { matieres, rafraichirCours, notifier } = useApp()
  const [apercu, setApercu] = useState<ApercuCours | 'chargement' | null>(null)
  const [edition, setEdition] = useState(false)
  const [titre, setTitre] = useState(c.titre)
  const [matiere, setMatiereCours] = useState(c.matiere)
  const [erreur, setErreur] = useState<string | null>(null)

  const basculerApercu = () => {
    if (apercu) return setApercu(null)
    setApercu('chargement')
    api.cours.apercu(c.id).then(setApercu).catch((e) => {
      setApercu(null)
      notifier(e instanceof ApiError ? e.message : 'L’aperçu n’a pas pu être chargé.')
    })
  }
  const enregistrer = (e: FormEvent) => {
    e.preventDefault()
    setErreur(null)
    api.cours.modifier(c.id, { titre: titre.trim(), matiere })
      .then(() => {
        setEdition(false)
        notifier(matiere !== c.matiere ? 'Cours déplacé' : 'Cours renommé')
        rafraichirCours()
      })
      .catch((err) => setErreur(err instanceof ApiError ? err.message : 'La modification a échoué.'))
  }
  const lien = 'text-[11px] text-muted hover:text-forest'
  const champ = 'rounded-[7px] border border-line bg-white p-[6px] text-[12px] text-ink'
  return (
    <li className="grid gap-1.5 text-[12px]">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="min-w-0">
          <span className="font-semibold">{c.titre}</span>
          <span className="block text-[10px] text-muted">
            {c.pages ? `${pluriel(c.pages, 'page')} · ` : ''}{pluriel(c.passages, 'passage')} · {STATUTS[c.statut]}
          </span>
          {c.avertissement && <span className="block text-[10px] text-[#8c4a36]">{c.avertissement}</span>}
        </span>
        <span className="flex flex-wrap gap-2">
          <button type="button" onClick={onReviser} className="text-[11px] font-semibold text-forest hover:underline">Réviser</button>
          <button type="button" onClick={basculerApercu} aria-expanded={apercu !== null} className={lien}>Aperçu</button>
          <button type="button" onClick={() => { setEdition(!edition); setTitre(c.titre); setMatiereCours(c.matiere) }}
            aria-expanded={edition} className={lien}>Modifier</button>
          <button type="button" onClick={onRetirer} className="text-[11px] text-muted hover:text-[#8c4a36]">Retirer</button>
        </span>
      </div>
      <div className="flex flex-wrap items-start gap-2">
        <ResumeVocal demande={() => ({ type: 'cours', id: String(c.id) })} />
        <CarteMentale demande={() => ({ type: 'cours', id: String(c.id) })} />
      </div>
      {edition && (
        <form onSubmit={enregistrer} aria-label={`Modifier « ${c.titre} »`} className="flex flex-wrap items-end gap-2 rounded-[8px] bg-[#f6f8f3] p-2">
          <label className="grid min-w-[150px] flex-1 gap-1 text-[10px] text-muted">
            Titre
            <input value={titre} onChange={(e) => setTitre(e.target.value)} maxLength={120} required className={champ} />
          </label>
          <label className="grid gap-1 text-[10px] text-muted">
            Matière
            <select value={matiere} onChange={(e) => setMatiereCours(e.target.value)} className={champ}>
              <OptionsMatieres matieres={matieres} />
            </select>
          </label>
          <button type="submit" disabled={!titre.trim()} className="rounded-[7px] bg-forest px-2.5 py-[6px] text-[11px] text-white disabled:opacity-50">Enregistrer</button>
          {erreur && <p role="alert" className="w-full text-[10px] text-[#8c4a36]">{erreur}</p>}
        </form>
      )}
      {apercu === 'chargement' && <p role="status" className="text-[10px] text-muted">Chargement de l’aperçu…</p>}
      {apercu && apercu !== 'chargement' && (
        <div aria-label={`Aperçu de « ${c.titre} »`} role="region" className="max-h-64 overflow-y-auto rounded-[8px] border border-line-soft bg-white p-2.5 text-[11px] leading-relaxed">
          <p className="mb-1.5 text-[10px] text-muted">
            Texte lu par Lexia ({apercu.apercu.length} premier{apercu.apercu.length > 1 ? 's' : ''} passage{apercu.apercu.length > 1 ? 's' : ''} sur {apercu.passages}).
            S’il est incomplet ou illisible, retirez le cours et déposez une version plus nette.
          </p>
          {apercu.apercu.map((x, i) => (
            <p key={i} className="mb-2 whitespace-pre-line">
              {x.page ? <span className="mr-1 text-[10px] text-muted">{x.page_fin && x.page_fin !== x.page ? `p. ${x.page} à ${x.page_fin}` : `p. ${x.page}`}</span> : null}
              {x.texte}
            </p>
          ))}
        </div>
      )}
    </li>
  )
}

/** Depot rapide depuis l'assistant : choix de la matiere, envoi, puis le cours devient le cours de travail. */
export function DepotRapide({ fichiers, onFermer }: { fichiers: File[]; onFermer: () => void }) {
  const { matieres, matiere: matiereCourante, mesCours, coursMax, rafraichirCours, setCoursChoisis, notifier } = useApp()
  const acceptes = fichiers.filter(formatAccepte)
  const ignores = fichiers.length - acceptes.length
  const [matiere, setMatiere] = useState(matiereCourante ?? '')
  const [titre, setTitre] = useState(acceptes.length === 1 ? sansExtension(acceptes[0].name) : '')
  const [envoi, setEnvoi] = useState<string | null>(null)
  const [erreurs, setErreurs] = useState<string[]>([])
  const place = coursMax > 0 ? Math.max(0, coursMax - mesCours.length) : acceptes.length

  const deposer = async (e: FormEvent) => {
    e.preventDefault()
    if (!matiere || acceptes.length === 0) return
    const echecs: string[] = []
    const deposes: number[] = []
    const avertissements: string[] = []
    for (const f of acceptes.slice(0, place)) {
      setEnvoi(f.name)
      const refus = refusFichier(f)
      if (refus) {
        echecs.push(`${f.name} : ${refus}`)
        continue
      }
      try {
        const titreFichier = acceptes.length === 1 ? titre.trim() : sansExtension(f.name)
        const depose = await api.cours.deposer(f, matiere, titreFichier)
        deposes.push(depose.id)
        if (depose.avertissement) avertissements.push(`${f.name} : ${depose.avertissement}`)
      } catch (err) {
        echecs.push(`${f.name} : ${err instanceof ApiError ? err.message : 'le dépôt a échoué.'}`)
      }
    }
    if (acceptes.length > place) echecs.push(`${acceptes.length - place} fichier(s) non déposé(s) : limite de ${coursMax} cours atteinte.`)
    setEnvoi(null)
    rafraichirCours()
    if (deposes.length) {
      setCoursChoisis(deposes) // tous les cours deposes deviennent les cours de travail
      notifier(deposes.length > 1 ? 'Cours ajoutés : posez-leur vos questions.' : 'Cours ajouté : posez-lui vos questions.')
    }
    if (echecs.length || avertissements.length) setErreurs([...echecs, ...avertissements])
    else onFermer()
  }

  const champ = 'rounded-[7px] border border-line bg-white p-[7px] text-[12px] text-ink'
  return (
    <form onSubmit={deposer} aria-label="Ajouter un cours"
      className="mb-2.5 grid gap-2 rounded-[10px] border border-[#cfd9d1] bg-[#f6f8f3] p-3 text-[12px]">
      <p className="font-semibold">
        {acceptes.length === 0 ? `Aucun fichier pris en charge (${FORMATS_LISIBLES}).`
          : acceptes.length === 1 ? `Ajouter « ${acceptes[0].name} » à mes cours`
            : `Ajouter ${acceptes.length} fichiers à mes cours`}
        {ignores > 0 && <span className="ml-1 font-normal text-muted">({ignores} fichier(s) d’un autre format ignoré(s))</span>}
      </p>
      {acceptes.length > 0 && (
        <div className="flex flex-wrap items-end gap-2">
          <label className="grid gap-1 text-[11px] text-muted">
            Matière
            <select value={matiere} onChange={(e) => setMatiere(e.target.value)} className={champ} required>
              <option value="">Choisir…</option>
              <OptionsMatieres matieres={matieres} />
            </select>
          </label>
          {acceptes.length === 1 && (
            <label className="grid min-w-[180px] flex-1 gap-1 text-[11px] text-muted">
              Titre
              <input value={titre} onChange={(e) => setTitre(e.target.value)} maxLength={120} className={champ} />
            </label>
          )}
          <button type="submit" disabled={!matiere || envoi !== null || place === 0}
            className="rounded-[7px] bg-forest px-3 py-[8px] text-[12px] text-white hover:bg-forest-dark disabled:opacity-50">
            {envoi ? `Envoi de ${envoi}…` : 'Déposer'}
          </button>
        </div>
      )}
      {place === 0 && acceptes.length > 0 && <p className="text-[11px] text-[#8c4a36]">Limite de {coursMax} cours atteinte pour votre formule.</p>}
      {erreurs.map((m) => <p key={m} role="alert" className="text-[11px] text-[#8c4a36]">{m}</p>)}
      <button type="button" onClick={onFermer} className="justify-self-start text-[11px] text-muted hover:text-forest">
        {erreurs.length ? 'Fermer' : 'Annuler'}
      </button>
    </form>
  )
}
