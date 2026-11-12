// Cours deposes par l'etudiant : depot (PDF, Word, texte) et liste par matiere.
import { useState, type FormEvent } from 'react'
import { api, ApiError } from '../lib/api'
import { useApp } from '../state/contexte'
import { formatAccepte, sansExtension } from '../lib/fichiers'
import { Card, CardHead } from './Layout'

const FORMATS = '.pdf,.docx,.txt,.md'
const TAILLE_MAX = 20 * 1024 * 1024

export function DepotCours() {
  const { matieres, mesCours, coursMax, rafraichirCours, notifier } = useApp()
  const [fichier, setFichier] = useState<File | null>(null)
  const [matiere, setMatiere] = useState('')
  const [titre, setTitre] = useState('')
  const [envoi, setEnvoi] = useState(false)
  const [erreur, setErreur] = useState<string | null>(null)
  const plein = coursMax > 0 && mesCours.length >= coursMax

  const deposer = async (e: FormEvent) => {
    e.preventDefault()
    if (!fichier || !matiere) return
    if (fichier.size > TAILLE_MAX) {
      setErreur('Fichier trop volumineux (20 Mo au plus).')
      return
    }
    setEnvoi(true)
    setErreur(null)
    try {
      await api.cours.deposer(fichier, matiere, titre.trim())
      notifier('Cours déposé : Lexia le prépare pour vos révisions.')
      setFichier(null)
      setTitre('')
      ;(e.target as HTMLFormElement).reset()
      rafraichirCours()
    } catch (err) {
      setErreur(err instanceof ApiError ? err.message : 'Le dépôt a échoué.')
    } finally {
      setEnvoi(false)
    }
  }

  const champ = 'rounded-[7px] border border-line bg-white p-[9px] text-[12px] text-ink'
  return (
    <Card className="mb-[18px] p-4 tab:p-[19px]">
      <CardHead titre="Déposer un cours"
        sousTitre="PDF, Word ou texte, 20 Mo au plus. Votre cours reste privé : vous seul pouvez l’utiliser."
        droite={coursMax > 0 ? <span className="text-[11px] text-muted">{mesCours.length} / {coursMax} cours</span> : undefined} />
      <form onSubmit={deposer} className="mt-3.5 flex flex-wrap items-end gap-2">
        <label className="grid min-w-[200px] flex-1 gap-1.5 text-[11px] text-muted">
          Fichier
          <input type="file" accept={FORMATS} onChange={(e) => setFichier(e.target.files?.[0] ?? null)} className={champ} />
        </label>
        <label className="grid gap-1.5 text-[11px] text-muted">
          Matière
          <select value={matiere} onChange={(e) => setMatiere(e.target.value)} className={champ}>
            <option value="">Choisir…</option>
            {matieres.map((m) => <option key={m.id} value={m.id}>{m.libelle}</option>)}
          </select>
        </label>
        <label className="grid min-w-[180px] flex-1 gap-1.5 text-[11px] text-muted">
          Titre (facultatif)
          <input value={titre} onChange={(e) => setTitre(e.target.value)} maxLength={120} placeholder="Ex. Chapitre 3 : les vices du consentement" className={champ} />
        </label>
        <button type="submit" disabled={!fichier || !matiere || envoi || plein}
          className="rounded-[7px] bg-forest px-3 py-[9px] text-[12px] text-white hover:bg-forest-dark disabled:opacity-50">
          {envoi ? 'Envoi…' : 'Déposer'}
        </button>
      </form>
      {plein && <p className="mt-2 text-[11px] text-[#8c4a36]">Limite atteinte pour votre formule : retirez un cours ou passez à une formule supérieure.</p>}
      {erreur && <p role="alert" className="mt-2 text-[11px] text-[#8c4a36]">{erreur}</p>}
    </Card>
  )
}

const STATUTS = { traitement: 'en préparation…', pret: 'prêt', erreur: 'recherche par mots-clés seulement' }

export function ListeCoursMatiere({ matiere }: { matiere: string }) {
  const { mesCours, rafraichirCours, setCoursChoisi, setMatiere, setVue, coursChoisi, notifier } = useApp()
  const liste = mesCours.filter((c) => c.matiere === matiere)
  if (liste.length === 0) return null
  const retirer = (id: number, titre: string) => {
    if (!window.confirm(`Retirer définitivement le cours « ${titre} » ?`)) return
    api.cours.supprimer(id)
      .then(() => {
        if (coursChoisi === id) setCoursChoisi(null)
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
          <li key={c.id} className="flex flex-wrap items-center justify-between gap-2 text-[12px]">
            <span className="min-w-0">
              <span className="font-semibold">{c.titre}</span>
              <span className="block text-[10px] text-muted">
                {c.pages ? `${c.pages} pages · ` : ''}{STATUTS[c.statut]}
              </span>
            </span>
            <span className="flex gap-2">
              <button type="button" onClick={() => { setCoursChoisi(c.id); setMatiere(matiere); setVue('assistant') }}
                className="text-[11px] font-semibold text-forest hover:underline">Réviser</button>
              <button type="button" onClick={() => retirer(c.id, c.titre)} className="text-[11px] text-muted hover:text-[#8c4a36]">Retirer</button>
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}

/** Depot rapide depuis l'assistant : choix de la matiere, envoi, puis le cours devient le cours de travail. */
export function DepotRapide({ fichiers, onFermer }: { fichiers: File[]; onFermer: () => void }) {
  const { matieres, matiere: matiereCourante, mesCours, coursMax, rafraichirCours, setCoursChoisi, notifier } = useApp()
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
    let dernier: number | null = null
    for (const f of acceptes.slice(0, place)) {
      setEnvoi(f.name)
      if (f.size > TAILLE_MAX) {
        echecs.push(`${f.name} : fichier trop volumineux (20 Mo au plus).`)
        continue
      }
      try {
        const titreFichier = acceptes.length === 1 ? titre.trim() : sansExtension(f.name)
        dernier = (await api.cours.deposer(f, matiere, titreFichier)).id
      } catch (err) {
        echecs.push(`${f.name} : ${err instanceof ApiError ? err.message : 'le dépôt a échoué.'}`)
      }
    }
    if (acceptes.length > place) echecs.push(`${acceptes.length - place} fichier(s) non déposé(s) : limite de ${coursMax} cours atteinte.`)
    setEnvoi(null)
    rafraichirCours()
    if (dernier !== null) {
      setCoursChoisi(dernier)
      notifier('Cours ajouté : posez-lui vos questions.')
    }
    if (echecs.length) setErreurs(echecs)
    else onFermer()
  }

  const champ = 'rounded-[7px] border border-line bg-white p-[7px] text-[12px] text-ink'
  return (
    <form onSubmit={deposer} aria-label="Ajouter un cours"
      className="mb-2.5 grid gap-2 rounded-[10px] border border-[#cfd9d1] bg-[#f6f8f3] p-3 text-[12px]">
      <p className="font-semibold">
        {acceptes.length === 0 ? 'Aucun fichier pris en charge (PDF, Word ou texte).'
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
              {matieres.map((m) => <option key={m.id} value={m.id}>{m.libelle}</option>)}
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
