// Cours deposes par l'etudiant : liste par matiere (apercu, modification, retrait) et depot rapide depuis l'assistant.
import { useRef, useState, type FormEvent } from 'react'
import { api, ApiError, type ApercuCours, type CoursDepose } from '../lib/api'
import { useApp } from '../state/contexte'
import { FORMATS_LISIBLES, formatAccepte, refusFichier, sansExtension, STATUTS } from '../lib/fichiers'
import { OptionsMatieres } from './OptionsMatieres'
import { Chargement, Rond } from './Chargement'
import { CarteMentale } from './CarteMentale'
import { ResumeVocal } from './ResumeVocal'

export { DepotCours } from './DepotCours'

export function ListeCoursMatiere({ matiere }: { matiere: string }) {
  const { mesCours, rafraichirCours, setCoursChoisis, setMatiere, setVue, coursChoisis, notifier } = useApp()
  const liste = mesCours.filter((c) => c.matiere === matiere)
  if (liste.length === 0) return null
  // Second clic « Confirmer le retrait », comme les fiches et la revision ; plus de window.confirm (recette du 23/11, R-8)
  const retirer = (id: number) => {
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
      <h3 className="mb-1.5 text-[12px] font-bold tracking-[1.4px] text-forest uppercase">Mes cours</h3>
      <ul className="grid gap-2">
        {liste.map((c) => (
          <CoursLigne key={c.id} cours={c} onReviser={() => { setCoursChoisis([c.id]); setMatiere(matiere); setVue('assistant') }}
            onRetirer={() => retirer(c.id)} />
        ))}
      </ul>
    </div>
  )
}

const pluriel = (n: number, mot: string) => `${n} ${mot}${n > 1 ? 's' : ''}`
const APERCU_PAS = 5 // passages par page de l'apercu, comme APERCU_PASSAGES (api/cours.py)

/** Un cours de la liste : pages et passages, apercu du texte lu, modification du titre et de la matiere. */
function CoursLigne({ cours: c, onReviser, onRetirer }: { cours: CoursDepose; onReviser: () => void; onRetirer: () => void }) {
  const { matieres, rafraichirCours, notifier } = useApp()
  const [apercu, setApercu] = useState<ApercuCours | 'chargement' | null>(null)
  const [edition, setEdition] = useState(false)
  const [titre, setTitre] = useState(c.titre)
  const [matiere, setMatiereCours] = useState(c.matiere)
  const [erreur, setErreur] = useState<string | null>(null)
  const [aRetirer, setARetirer] = useState(false)
  const zone = useRef<HTMLDivElement>(null)
  const ocr = c.pages_ocr ?? []

  // Apercu parcouru 5 passages a la fois, ou ouvert a une page lue par OCR (D141 : avant, seuls les 5 premiers
  // passages etaient visibles et une page scannee plus loin ne pouvait pas etre relue).
  const ouvrirApercu = (ou: { debut?: number; page?: number } = {}) => {
    if (apercu === null) setApercu('chargement')
    api.cours.apercu(c.id, ou).then((a) => {
      setApercu(a)
      zone.current?.scrollTo?.({ top: 0 })
    }).catch((e) => {
      setApercu(null)
      notifier(e instanceof ApiError ? e.message : 'L’aperçu n’a pas pu être chargé.')
    })
  }
  const basculerApercu = () => (apercu ? setApercu(null) : ouvrirApercu())
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
  // G-7 (audit du 25/11) : plus aucun texte sous 12 px ; cibles de 44 px au doigt
  const lien = 'min-h-8 text-[12px] text-muted hover:text-forest pointer-coarse:min-h-11'
  const champ = 'rounded-[7px] border border-line bg-white p-[6px] text-[13px] text-ink'
  // Pages d'un passage lues par OCR : seules elles sont a verifier (un passage peut couvrir plusieurs pages)
  const pagesOcr = (x: { page: number | null; page_fin: number | null }) =>
    x.page === null ? [] : ocr.filter((n) => n >= x.page! && n <= (x.page_fin ?? x.page!))
  const pageOcr = (x: { page: number | null; page_fin: number | null }) => pagesOcr(x).length > 0
  const mentionOcr = (x: { page: number | null; page_fin: number | null }) => {
    const p = pagesOcr(x)
    if (!p.length) return ''
    if ((x.page_fin ?? x.page) === x.page) return ' · lue sur un scan'
    return ` · page${p.length > 1 ? 's' : ''} ${p.join(', ')} lue${p.length > 1 ? 's' : ''} sur un scan`
  }
  return (
    <li className="grid gap-1.5 text-[13px]">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="min-w-0">
          <span className="font-semibold">{c.titre}</span>
          <span className="block text-[12px] text-muted">
            {c.pages ? `${pluriel(c.pages, 'page')} · ` : ''}{pluriel(c.passages, 'passage')} · {STATUTS[c.statut]}
          </span>
          {c.avertissement && <span className="block text-[12px] text-[#8c4a36]">{c.avertissement}</span>}
          {ocr.length > 0 && (
            <button type="button" onClick={() => ouvrirApercu({ page: ocr[0] })}
              className="min-h-8 text-[12px] font-semibold text-forest hover:underline pointer-coarse:min-h-11">
              {ocr.length > 1 ? 'Vérifier les pages scannées' : `Vérifier la page ${ocr[0]}`}
            </button>
          )}
        </span>
        <span className="flex flex-wrap gap-x-3 gap-y-1">
          <button type="button" onClick={onReviser} className="min-h-8 text-[12px] font-semibold text-forest hover:underline pointer-coarse:min-h-11">Réviser</button>
          <button type="button" onClick={basculerApercu} aria-expanded={apercu !== null} className={lien}>Aperçu</button>
          <button type="button" onClick={() => { setEdition(!edition); setTitre(c.titre); setMatiereCours(c.matiere) }}
            aria-expanded={edition} className={lien}>Modifier</button>
          <button type="button"
            onClick={() => {
              if (!aRetirer) return setARetirer(true)
              setARetirer(false)
              onRetirer()
            }}
            onBlur={() => setARetirer(false)}
            aria-label={aRetirer ? `Confirmer le retrait du cours « ${c.titre} »` : `Retirer le cours « ${c.titre} »`}
            className={`min-h-8 text-[12px] hover:text-[#8c4a36] pointer-coarse:min-h-11 ${aRetirer ? 'font-semibold text-[#8c4a36]' : 'text-muted'}`}>
            {aRetirer ? 'Confirmer le retrait' : 'Retirer'}
          </button>
        </span>
      </div>
      <div className="flex flex-wrap items-start gap-2">
        <ResumeVocal demande={() => ({ type: 'cours', id: String(c.id) })} />
        <CarteMentale demande={() => ({ type: 'cours', id: String(c.id) })} />
      </div>
      {edition && (
        <form onSubmit={enregistrer} aria-label={`Modifier « ${c.titre} »`} className="flex flex-wrap items-end gap-2 rounded-[8px] bg-[#f6f8f3] p-2">
          <label className="grid min-w-[150px] flex-1 gap-1 text-[12px] text-muted">
            Titre
            <input value={titre} onChange={(e) => setTitre(e.target.value)} maxLength={120} required className={champ} />
          </label>
          <label className="grid gap-1 text-[12px] text-muted">
            Matière
            <select value={matiere} onChange={(e) => setMatiereCours(e.target.value)} className={champ}>
              <OptionsMatieres matieres={matieres} />
            </select>
          </label>
          <button type="submit" disabled={!titre.trim()} className="min-h-9 rounded-[7px] bg-forest px-3 text-[12px] text-white disabled:opacity-50 pointer-coarse:min-h-11">Enregistrer</button>
          {erreur && <p role="alert" className="w-full text-[12px] text-[#8c4a36]">{erreur}</p>}
        </form>
      )}
      {apercu === 'chargement' && <p role="status" className="text-[12px] text-muted">Chargement de l’aperçu…</p>}
      {apercu && apercu !== 'chargement' && (() => {
        const premier = apercu.debut + 1
        const dernier = apercu.debut + apercu.apercu.length
        const nav = 'min-h-8 rounded-[7px] border border-line bg-white px-2.5 text-[12px] text-forest hover:border-[#9eafa3] disabled:opacity-50 pointer-coarse:min-h-11'
        return (
          <div aria-label={`Aperçu de « ${c.titre} »`} role="region" className="rounded-[8px] border border-line-soft bg-white p-2.5">
            <p className="text-[12px] text-muted" aria-live="polite">
              Texte lu par Lexia : {apercu.passages > 1 ? `passages ${premier} à ${dernier} sur ${apercu.passages}` : 'passage unique'}.
              S’il est incomplet ou illisible, retirez le cours et déposez une version plus nette.
            </p>
            {ocr.length > 0 && (
              <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[12px]">
                <span className="text-[#8c4a36]">Lues sur un scan, à vérifier :</span>
                {ocr.map((n) => (
                  <button key={n} type="button" onClick={() => ouvrirApercu({ page: n })} aria-label={`Aller à la page ${n}`}
                    className="min-h-8 rounded-full border border-[#e3c9a8] bg-[#fbf3e6] px-2.5 text-[12px] text-[#7a4b1e] hover:border-[#c8a16d] pointer-coarse:min-h-11">
                    p. {n}
                  </button>
                ))}
              </div>
            )}
            <div ref={zone} className="mt-2 max-h-72 overflow-y-auto text-[13px] leading-relaxed">
              {apercu.apercu.map((x) => (
                <p key={x.rang} className={`mb-2 whitespace-pre-line ${pageOcr(x) ? 'rounded-[6px] border-l-2 border-[#c8a16d] bg-[#fdf8ef] px-2 py-1' : ''}`}>
                  {x.page ? (
                    <span className="mr-1 text-[12px] text-muted">
                      {x.page_fin && x.page_fin !== x.page ? `p. ${x.page} à ${x.page_fin}` : `p. ${x.page}`}
                      {mentionOcr(x)}
                    </span>
                  ) : null}
                  {x.texte}
                </p>
              ))}
            </div>
            {apercu.passages > apercu.apercu.length && (
              <div className="mt-1 flex flex-wrap gap-2">
                <button type="button" disabled={apercu.debut === 0} className={nav}
                  onClick={() => ouvrirApercu({ debut: Math.max(0, apercu.debut - APERCU_PAS) })}>Passages précédents</button>
                <button type="button" disabled={dernier >= apercu.passages} className={nav}
                  onClick={() => ouvrirApercu({ debut: dernier })}>Passages suivants</button>
              </div>
            )}
          </div>
        )
      })()}
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
  const [aide, setAide] = useState<string | null>(null)
  const matiereRef = useRef<HTMLSelectElement>(null)
  const place = coursMax > 0 ? Math.max(0, coursMax - mesCours.length) : acceptes.length

  const deposer = async (e: FormEvent) => {
    e.preventDefault()
    if (acceptes.length === 0) return
    // Bouton actif, raison dite au clic (audit du 25/11, M-4 : grise sans explication depuis « Toutes »)
    if (!matiere) {
      setAide('Choisissez la matière du cours.')
      matiereRef.current?.focus()
      return
    }
    setAide(null)
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
      const fait = deposes.length > 1 ? 'Cours ajoutés : posez-leur vos questions.' : 'Cours ajouté : posez-lui vos questions.'
      notifier([fait, ...avertissements].join(' '))
    }
    // Un depot reussi ferme le formulaire, meme avec un avertissement (page lue par reconnaissance de caracteres) :
    // reste ouvert, il laissait croire qu'il fallait deposer de nouveau (recette du 2026-11-23, R-7). Seul un echec
    // le garde ouvert, avec ses raisons.
    if (echecs.length) setErreurs([...echecs, ...avertissements])
    else onFermer()
  }

  const champ = 'rounded-[7px] border border-line bg-white p-[7px] text-[13px] text-ink'
  return (
    <form onSubmit={deposer} aria-label="Ajouter un cours"
      className="mb-2.5 grid gap-2 rounded-[10px] border border-[#cfd9d1] bg-[#f6f8f3] p-3 text-[13px]">
      <p className="font-semibold">
        {acceptes.length === 0 ? `Aucun fichier pris en charge (${FORMATS_LISIBLES}).`
          : acceptes.length === 1 ? `Ajouter « ${acceptes[0].name} » à mes cours`
            : `Ajouter ${acceptes.length} fichiers à mes cours`}
        {ignores > 0 && <span className="ml-1 font-normal text-muted">({ignores} fichier(s) d’un autre format ignoré(s))</span>}
      </p>
      {acceptes.length > 0 && (
        <div className="flex flex-wrap items-end gap-2">
          <label className="grid gap-1 text-[12px] text-muted">
            Matière
            <select ref={matiereRef} value={matiere} onChange={(e) => { setMatiere(e.target.value); setAide(null) }}
              aria-invalid={aide ? true : undefined} aria-describedby="aide-depot-rapide" className={champ}>
              <option value="">Choisir…</option>
              <OptionsMatieres matieres={matieres} />
            </select>
          </label>
          {acceptes.length === 1 && (
            <label className="grid min-w-[180px] flex-1 gap-1 text-[12px] text-muted">
              Titre
              <input value={titre} onChange={(e) => setTitre(e.target.value)} maxLength={120} className={champ} />
            </label>
          )}
          <button type="submit" disabled={envoi !== null || place === 0} aria-describedby="aide-depot-rapide"
            className="inline-flex min-h-9 items-center gap-1.5 rounded-[7px] bg-forest px-3 text-[13px] text-white hover:bg-forest-dark disabled:opacity-50 pointer-coarse:min-h-11">
            {envoi && <Rond className="h-3.5 w-3.5" />}
            {envoi ? `Envoi de ${envoi}…` : 'Déposer'}
          </button>
          <p id="aide-depot-rapide" role="status" className="w-full text-[12px] text-[#8c4a36] empty:hidden">{aide ?? ''}</p>
        </div>
      )}
      {envoi && (
        <Chargement duree="jusqu’à une minute pour un scan"
          etapes={['Envoi du fichier…', 'Lecture du fichier…', 'Lecture des pages scannées, s’il y en a…', 'Découpage en passages…']} />
      )}
      {place === 0 && acceptes.length > 0 && <p className="text-[12px] text-[#8c4a36]">Limite de {coursMax} cours atteinte pour votre formule.</p>}
      {erreurs.map((m) => <p key={m} role="alert" className="text-[12px] text-[#8c4a36]">{m}</p>)}
      <button type="button" onClick={onFermer} className="min-h-8 justify-self-start text-[12px] text-muted hover:text-forest pointer-coarse:min-h-11">
        {erreurs.length ? 'Fermer' : 'Annuler'}
      </button>
    </form>
  )
}
