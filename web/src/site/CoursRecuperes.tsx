import { useEffect, useMemo, useState } from 'react'
import { api, type CoursRecupere, type CoursRecupereComplet } from '../lib/api'
import { CadreEspace } from '../components/Layout'
import { useApp } from '../state/contexte'
import { Surtitre } from './Public'

// Meme texte que l'API (api/cours_recuperes.py) : affiche avant meme la reponse du serveur.
export const AVERTISSEMENT = 'Cours récupérés sur des sites tiers sous licence libre. Ils ne sont pas rédigés par Lexia et '
  + 'peuvent contenir des erreurs ou être dépassés. Vérifiez toujours avec les textes officiels.'
const RAPPEL = 'Cours récupéré, non rédigé par Lexia : il peut contenir des erreurs ou être dépassé.'

const lien = 'text-forest underline-offset-2 hover:underline'
const PAR_PAGE = 20
const normaliser = (t: string) => t.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
const dateLongue = (iso: string) =>
  new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' }).format(new Date(`${iso}T12:00:00`))

/** Attribution exigee par les licences : auteur, source, licence, date de mise a jour, lien vers l'original. */
function Attribution({ c }: { c: Omit<CoursRecupere, 'sections'> }) {
  const ligne = 'grid grid-cols-[110px_minmax(0,1fr)] gap-2'
  return (
    <dl className="mt-3 grid gap-1 text-[11px]">
      <div className={ligne}><dt className="text-muted">Auteur</dt><dd>
        {c.auteur}{c.historique_url && <> (<a className={lien} href={c.historique_url} target="_blank" rel="noreferrer">liste des contributeurs ↗</a>)</>}
      </dd></div>
      <div className={ligne}><dt className="text-muted">Source</dt><dd>
        <a className={lien} href={c.source_url} target="_blank" rel="noreferrer">{c.source} ↗</a>
      </dd></div>
      <div className={ligne}><dt className="text-muted">Licence</dt><dd>
        <a className={lien} href={c.licence_url} target="_blank" rel="noreferrer">{c.licence_libelle} ↗</a>
      </dd></div>
      <div className={ligne}><dt className="text-muted">Mise à jour</dt><dd>{dateLongue(c.mis_a_jour)}</dd></div>
      <div className={ligne}><dt className="text-muted">Original</dt><dd className="break-words">
        <a className={lien} href={c.url_original} target="_blank" rel="noreferrer">{c.url_original} ↗</a>
      </dd></div>
      {c.modifications && <div className={ligne}><dt className="text-muted">Modifications</dt><dd>{c.modifications}</dd></div>}
    </dl>
  )
}

function CarteCours({ c }: { c: CoursRecupere }) {
  const [complet, setComplet] = useState<CoursRecupereComplet | null>(null)
  const [ouvert, setOuvert] = useState(false)
  const [erreur, setErreur] = useState(false)

  const basculer = () => {
    setOuvert((o) => !o)
    if (!complet) {
      setErreur(false)
      api.coursRecuperes.lire(c.id).then(setComplet).catch(() => setErreur(true))
    }
  }

  return (
    <article className="rounded-xl border border-line bg-surface p-4 tab:p-[19px]">
      <h3 className="font-display text-[19px] leading-snug font-normal">{c.titre}</h3>
      <p className="mt-2 rounded-[7px] border-l-2 border-[#c8a16d] bg-cream px-2.5 py-1.5 text-[11px] leading-[1.45] text-[#746347]">
        {RAPPEL}
      </p>
      <Attribution c={c} />
      <button type="button" onClick={basculer} aria-expanded={ouvert}
        className="mt-3 rounded-[7px] border border-line px-3 py-1.5 text-[12px] text-forest hover:border-[#9eafa3]">
        {ouvert ? 'Fermer le cours' : 'Lire le cours'}
      </button>
      {ouvert && (
        <div className="mt-4 border-t border-line-soft pt-4">
          {erreur ? (
            <p role="alert" className="text-[12px] text-[#8c4a36]">Le cours n’a pas pu être chargé. Réessayez plus tard.</p>
          ) : !complet ? (
            <div className="grid animate-pulse gap-2">{[0, 1, 2].map((i) => <div key={i} className="h-4 rounded bg-[#ece9e0]" />)}</div>
          ) : (
            <>
              <p className="mb-4 text-[11px] text-muted">{complet.avertissement}</p>
              {complet.sections.map((s, i) => (
                <section key={i} className="mt-4 first:mt-0">
                  {s.titre && <h4 className="text-[13px] font-[650]">{s.titre}</h4>}
                  <p className="mt-1.5 text-[13px] leading-[1.6] whitespace-pre-line">{s.texte}</p>
                </section>
              ))}
            </>
          )}
        </div>
      )}
    </article>
  )
}

/** Page a part des reponses fondees sur les textes officiels : cours de sites tiers sous licence libre, par matiere. */
export function CoursRecuperes() {
  const [cours, setCours] = useState<CoursRecupere[] | null>(null)
  const [avertissement, setAvertissement] = useState(AVERTISSEMENT)
  const [erreur, setErreur] = useState(false)
  const { matiere: matiereEspace } = useApp()
  const [matiere, setMatiere] = useState('')
  const [recherche, setRecherche] = useState('')
  const [nombre, setNombre] = useState(PAR_PAGE)
  // Recherche dans le texte des fiches (index plein texte, cote serveur), apres une courte pause de saisie.
  const [dansLeTexte, setDansLeTexte] = useState<{ q: string; ids: string[] }>({ q: '', ids: [] })
  useEffect(() => {
    const q = recherche.trim()
    if (q.length < 3) return
    let actif = true
    const minuterie = window.setTimeout(() => {
      api.coursRecuperes.rechercher(q).then((r) => actif && setDansLeTexte({ q, ids: r.cours })).catch(() => {})
    }, 300)
    return () => { actif = false; window.clearTimeout(minuterie) }
  }, [recherche])

  useEffect(() => {
    let actif = true
    api.coursRecuperes.lister()
      .then((r) => { if (actif) { setCours(r.cours); setAvertissement(r.avertissement || AVERTISSEMENT) } })
      .catch(() => { if (actif) { setErreur(true); setCours([]) } })
    return () => { actif = false }
  }, [])

  // L'API renvoie les cours tries par matiere puis par titre.
  const groupes = useMemo(() => {
    const g = new Map<string, { libelle: string; cours: CoursRecupere[] }>()
    for (const c of cours ?? []) {
      if (!g.has(c.matiere)) g.set(c.matiere, { libelle: c.libelle_matiere, cours: [] })
      g.get(c.matiere)!.cours.push(c)
    }
    return [...g.entries()]
  }, [cours])
  // Une matiere a la fois (plusieurs centaines de cours) : celle choisie, sinon celle de l'espace, sinon la premiere.
  const ids = groupes.map(([id]) => id)
  const choisie = ids.includes(matiere) ? matiere : ids.includes(matiereEspace ?? '') ? matiereEspace! : ids[0] ?? ''
  const mots = normaliser(recherche.trim())
  // Une recherche porte sur toutes les matieres : titres d'abord, puis fiches dont le texte repond.
  const parTitre = (cours ?? []).filter((c) => mots ? normaliser(c.titre).includes(mots) : c.matiere === choisie)
  const parId = new Map((cours ?? []).map((c) => [c.id, c]))
  const dejaVus = new Set(parTitre.map((c) => c.id))
  const parTexte = mots && dansLeTexte.q === recherche.trim()
    ? dansLeTexte.ids.filter((id) => !dejaVus.has(id)).map((id) => parId.get(id)).filter((c): c is CoursRecupere => !!c)
    : []
  const trouves = [...parTitre, ...parTexte]
  const visibles = trouves.slice(0, nombre)
  const parMatiere = groupes
    .map(([id, g]) => [id, g.libelle, visibles.filter((c) => c.matiere === id)] as const)
    .filter(([, , liste]) => liste.length > 0)

  return (
    <CadreEspace titre="Cours récupérés">
      <div className="mx-auto max-w-[860px]">
        <Surtitre>Cours récupérés</Surtitre>
        <h1 className="mt-2 font-display text-[32px] font-normal">Cours de sources libres</h1>
        <div role="note" aria-label="Avertissement"
          className="mt-4 rounded-xl border border-[#c8a16d] bg-cream px-4 py-3 text-[13px] leading-[1.5] text-[#5e4f36]">
          <strong className="block text-[14px]">À lire avant d’utiliser ces cours</strong>
          <span className="mt-1 block">{avertissement}</span>
          <span className="mt-1 block text-[12px]">
            Ils sont présentés à part : les réponses de l’assistant reposent sur les textes et décisions officiels.
          </span>
        </div>

        {groupes.length > 0 && (
          <div className="mt-5 grid gap-3 tab:grid-cols-2">
            <label className="grid gap-1 text-[11px] text-muted">
              Matière
              <select value={choisie} disabled={!!mots} onChange={(e) => { setMatiere(e.target.value); setNombre(PAR_PAGE) }}
                className="rounded-[7px] border border-line bg-white px-2 py-1.5 text-[12px] text-ink disabled:opacity-60">
                {groupes.map(([id, g]) => <option key={id} value={id}>{g.libelle} ({g.cours.length})</option>)}
              </select>
            </label>
            <label className="grid gap-1 text-[11px] text-muted">
              Rechercher dans les titres et les textes, toutes matières
              <input type="search" value={recherche} onChange={(e) => { setRecherche(e.target.value); setNombre(PAR_PAGE) }}
                placeholder="Divorce, bail, licenciement…"
                className="rounded-[7px] border border-line bg-white px-2 py-1.5 text-[12px] text-ink" />
            </label>
          </div>
        )}

        {cours === null ? (
          <div className="mt-6 grid animate-pulse gap-3">{[0, 1].map((i) => <div key={i} className="h-28 rounded-xl bg-[#ece9e0]" />)}</div>
        ) : erreur ? (
          <p role="alert" className="mt-6 text-[13px] text-[#8c4a36]">Les cours n’ont pas pu être chargés. Réessayez plus tard.</p>
        ) : cours.length === 0 ? (
          <p className="mt-6 text-[13px] text-muted">
            Aucun cours récupéré pour l’instant : les sources libres sont en cours de vérification.
          </p>
        ) : trouves.length === 0 ? (
          <p className="mt-6 text-[13px] text-muted">Aucun cours ne correspond à « {recherche.trim()} ».</p>
        ) : (
          <>
            {parMatiere.map(([id, libelle, liste]) => (
              <section key={id} className="mt-7">
                <h2 className="mb-3 text-[15px] font-[650]">{libelle}</h2>
                <div className="grid gap-3">{liste.map((c) => <CarteCours key={c.id} c={c} />)}</div>
              </section>
            ))}
            <p className="mt-4 text-[11px] text-muted">{visibles.length} sur {trouves.length}</p>
            {trouves.length > visibles.length && (
              <button type="button" onClick={() => setNombre((n) => n + PAR_PAGE)}
                className="mt-2 rounded-[7px] border border-line px-3 py-1.5 text-[12px] text-forest hover:border-[#9eafa3]">
                Afficher {Math.min(PAR_PAGE, trouves.length - visibles.length)} de plus
              </button>
            )}
          </>
        )}
      </div>
    </CadreEspace>
  )
}
