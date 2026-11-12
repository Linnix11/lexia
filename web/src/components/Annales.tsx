import { useEffect, useMemo, useState } from 'react'
import { api, type Annale } from '../lib/api'
import { Card, CardHead } from './Layout'

/** Catalogue d'annales : liens vers les sujets publies par les facultes ou relayes par des associations (rien n'est copie). */
const PAR_PAGE = 20

export function CarteAnnales() {
  const [annales, setAnnales] = useState<Annale[] | null>(null)
  const [erreur, setErreur] = useState(false)
  const [matiere, setMatiere] = useState('')
  const [niveau, setNiveau] = useState('')
  const [nombre, setNombre] = useState(PAR_PAGE)

  useEffect(() => {
    let actif = true
    api.annales()
      .then((r) => actif && setAnnales(r.annales))
      .catch(() => { if (actif) { setErreur(true); setAnnales([]) } })
    return () => { actif = false }
  }, [])

  const matieres = useMemo(() => {
    const m = new Map<string, string>()
    for (const a of annales ?? []) m.set(a.matiere, a.libelle_matiere)
    return [...m.entries()].sort((a, b) => a[1].localeCompare(b[1], 'fr'))
  }, [annales])
  const niveaux = useMemo(() => [...new Set((annales ?? []).map((a) => a.niveau))].sort(), [annales])
  const visibles = (annales ?? []).filter((a) => (!matiere || a.matiere === matiere) && (!niveau || a.niveau === niveau))

  return (
    <Card className="p-[19px] tab:col-span-2">
      <CardHead titre="Annales d’examens" sousTitre="Sujets publiés par les facultés ou relayés par des associations étudiantes, à ouvrir sur leur site" />
      {annales && annales.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          <label className="grid gap-1 text-[11px] text-muted">
            Matière
            <select value={matiere} onChange={(e) => { setMatiere(e.target.value); setNombre(PAR_PAGE) }} className="rounded-[7px] border border-line bg-white px-2 py-1.5 text-[12px] text-ink">
              <option value="">Toutes</option>
              {matieres.map(([id, lib]) => <option key={id} value={id}>{lib}</option>)}
            </select>
          </label>
          <label className="grid gap-1 text-[11px] text-muted">
            Niveau
            <select value={niveau} onChange={(e) => { setNiveau(e.target.value); setNombre(PAR_PAGE) }} className="rounded-[7px] border border-line bg-white px-2 py-1.5 text-[12px] text-ink">
              <option value="">Tous</option>
              {niveaux.map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>
        </div>
      )}
      {annales === null ? (
        <div className="mt-3 grid animate-pulse gap-2">{[0, 1].map((i) => <div key={i} className="h-9 rounded bg-[#ece9e0]" />)}</div>
      ) : erreur ? (
        <p className="mt-3 text-[12px] text-muted">Le catalogue d’annales est indisponible pour le moment.</p>
      ) : annales.length === 0 ? (
        <p className="mt-3 text-[12px] text-muted">Aucune annale référencée pour l’instant. Les sujets publiés par les facultés seront ajoutés ici au fur et à mesure.</p>
      ) : visibles.length === 0 ? (
        <p className="mt-3 text-[12px] text-muted">Aucune annale pour ces filtres.</p>
      ) : (
        <ul className="mt-3 divide-y divide-line">
          {visibles.slice(0, nombre).map((a) => (
            <li key={a.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5">
              <div className="min-w-0">
                <p className="text-[13px]">{a.titre}</p>
                <p className="text-[11px] text-muted">
                  {a.libelle_matiere} · {a.niveau} · {a.universite} · {a.annee}{a.session ? ` · ${a.session}` : ''}{a.corrige ? ' · avec corrigé' : ''}
                </p>
              </div>
              <a href={a.url} target="_blank" rel="noopener noreferrer"
                className="shrink-0 rounded-[7px] border border-line px-3 py-1.5 text-[11px] text-forest hover:border-[#9eafa3]">
                Ouvrir le sujet<span className="sr-only"> (site d’origine, nouvel onglet)</span> ↗
              </a>
            </li>
          ))}
        </ul>
      )}
      {visibles.length > nombre && (
        <button type="button" onClick={() => setNombre((n) => n + PAR_PAGE)}
          className="mt-2 rounded-[7px] border border-line px-3 py-1.5 text-[11px] text-forest hover:border-[#9eafa3]">
          Afficher plus ({visibles.length - nombre} restantes)
        </button>
      )}
    </Card>
  )
}
