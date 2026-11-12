// Cours deposes par l'etudiant : depot (PDF, Word, texte) et liste par matiere.
import { useState, type FormEvent } from 'react'
import { api, ApiError } from '../lib/api'
import { useApp } from '../state/contexte'
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
