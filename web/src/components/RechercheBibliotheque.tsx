import { useEffect, useRef, useState, type ReactNode } from 'react'
import { api, type Annale, type CoursRecupere } from '../lib/api'
import { Lien } from '../lib/router'
import { OFFICIELLES } from './Cartes'

/** Barre de recherche facultative de la Bibliotheque : cours recuperes (titres puis texte), annales, sources
 *  officielles, et un lien vers le catalogue universitaire. Rien n'est charge tant que l'etudiant n'ecrit pas. */
const MAX = 6
const normaliser = (t: string) => t.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

function Groupe({ titre, children }: { titre: string; children: ReactNode }) {
  return (
    <section className="border-t border-line-soft pt-3 first:border-t-0 first:pt-0">
      <h3 className="text-[10px] font-bold tracking-[1.2px] text-forest uppercase">{titre}</h3>
      <ul className="mt-1.5 grid gap-1">{children}</ul>
    </section>
  )
}

export function RechercheBibliotheque() {
  const [texte, setTexte] = useState('')
  const [cours, setCours] = useState<CoursRecupere[] | null>(null)
  const [annales, setAnnales] = useState<Annale[] | null>(null)
  const [dansLeTexte, setDansLeTexte] = useState<{ q: string; ids: string[] }>({ q: '', ids: [] })
  const charge = useRef(false)
  const q = texte.trim()
  const mots = normaliser(q)

  // Catalogues charges une fois, a la premiere saisie.
  useEffect(() => {
    if (!q || charge.current) return
    charge.current = true
    api.coursRecuperes.lister().then((r) => setCours(r.cours)).catch(() => setCours([]))
    api.annales().then((r) => setAnnales(r.annales)).catch(() => setAnnales([]))
  }, [q])

  // Recherche dans le texte des cours recuperes (index plein texte), apres une courte pause de saisie.
  useEffect(() => {
    if (q.length < 3) return
    let actif = true
    const minuterie = window.setTimeout(() => {
      api.coursRecuperes.rechercher(q).then((r) => actif && setDansLeTexte({ q, ids: r.cours })).catch(() => {})
    }, 300)
    return () => { actif = false; window.clearTimeout(minuterie) }
  }, [q])

  const parTitre = mots.length >= 2 ? (cours ?? []).filter((c) => normaliser(c.titre).includes(mots)) : []
  const vus = new Set(parTitre.map((c) => c.id))
  const parId = new Map((cours ?? []).map((c) => [c.id, c]))
  const parTexte = dansLeTexte.q === q
    ? dansLeTexte.ids.filter((id) => !vus.has(id)).map((id) => parId.get(id)).filter((c): c is CoursRecupere => !!c)
    : []
  const coursTrouves = [...parTitre, ...parTexte]
  const annalesTrouvees = mots.length >= 2
    ? (annales ?? []).filter((a) => normaliser(`${a.titre} ${a.libelle_matiere} ${a.universite} ${a.annee}`).includes(mots))
    : []
  const sourcesTrouvees = mots.length >= 2 ? OFFICIELLES.filter((s) => normaliser(`${s.nom} ${s.desc}`).includes(mots)) : []
  const lien = 'flex items-baseline justify-between gap-3 rounded-[7px] px-2 py-1.5 text-[12px] hover:bg-[#eef1eb]'

  return (
    <div className="mb-[18px] rounded-xl border border-line bg-surface p-4 tab:p-[19px]">
      <label className="grid gap-1.5 text-[11px] text-muted">
        Rechercher dans la bibliothèque (facultatif)
        <input type="search" value={texte} onChange={(e) => setTexte(e.target.value)}
          placeholder="Un thème, une matière, une université… ex. divorce, bail, Assas"
          className="rounded-[8px] border border-line bg-white px-3 py-2 text-[13px] text-ink" />
      </label>
      {mots.length >= 2 && (
        <div className="mt-4 grid gap-3" aria-live="polite">
          {coursTrouves.length > 0 && (
            <Groupe titre={`Cours récupérés (${coursTrouves.length}), non rédigés par Lexia`}>
              {coursTrouves.slice(0, MAX).map((c) => (
                <li key={c.id}>
                  <Lien href={`/cours-recuperes?q=${encodeURIComponent(c.titre)}`} className={lien}>
                    <span className="min-w-0">{c.titre}</span>
                    <span className="shrink-0 text-[10px] text-muted">{c.libelle_matiere}</span>
                  </Lien>
                </li>
              ))}
              {coursTrouves.length > MAX && (
                <li>
                  <Lien href={`/cours-recuperes?q=${encodeURIComponent(q)}`} className="px-2 text-[11px] text-forest hover:underline">
                    Voir les {coursTrouves.length} cours récupérés
                  </Lien>
                </li>
              )}
            </Groupe>
          )}
          {annalesTrouvees.length > 0 && (
            <Groupe titre={`Annales (${annalesTrouvees.length})`}>
              {annalesTrouvees.slice(0, MAX).map((a) => (
                <li key={a.id}>
                  <a href={a.url} target="_blank" rel="noopener noreferrer" className={lien}>
                    <span className="min-w-0">{a.titre}</span>
                    <span className="shrink-0 text-[10px] text-muted">{a.universite} · {a.annee} ↗</span>
                  </a>
                </li>
              ))}
            </Groupe>
          )}
          {sourcesTrouvees.length > 0 && (
            <Groupe titre="Sources officielles">
              {sourcesTrouvees.map((s) => (
                <li key={s.nom}>
                  <a href={s.url} target="_blank" rel="noreferrer" className={lien}>
                    <span className="min-w-0">{s.nom}</span>
                    <span className="shrink-0 text-[10px] text-muted">↗</span>
                  </a>
                </li>
              ))}
            </Groupe>
          )}
          {coursTrouves.length + annalesTrouvees.length + sourcesTrouvees.length === 0 && cours !== null && annales !== null && (
            <p className="text-[12px] text-muted">Rien dans la bibliothèque pour « {q} ».</p>
          )}
          <a href={`https://www.sudoc.abes.fr/cbs/xslt//DB=2.1/CMD?ACT=SRCHA&IKT=1016&SRT=RLV&TRM=${encodeURIComponent(q)}`}
            target="_blank" rel="noreferrer" className="text-[11px] text-forest hover:underline">
            Chercher « {q} » dans le catalogue des bibliothèques universitaires (Sudoc) ↗
          </a>
        </div>
      )}
    </div>
  )
}
