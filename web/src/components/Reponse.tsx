import { useState } from 'react'
import { api, type Element, type FicheSource, type ReponseChat } from '../lib/api'
import { infosMode, symbole } from '../lib/modes'
import { numeroSource, titreCourt } from '../lib/sources'
import { useApp, type Message } from '../state/contexte'

function Citations({ ids, sources }: { ids: string[]; sources: FicheSource[] }) {
  const { ouvrirSource } = useApp()
  if (!ids.length) return null
  return (
    <span className="ml-1 inline-flex flex-wrap gap-1 align-baseline">
      {ids.map((id) => {
        const s = sources.find((x) => x.id === id)
        if (!s) return null
        return (
          <button
            key={id}
            type="button"
            onClick={() => ouvrirSource(id)}
            title={s.entete}
            className="rounded border-b border-[#b2c2b7] px-0.5 text-[11px] font-semibold text-forest hover:bg-mint"
          >
            [{numeroSource(sources, id)}]
          </button>
        )
      })}
    </span>
  )
}

// Dans un bloc, chaque source n'est citee qu'a sa premiere mention : le modele la recite a chaque
// paragraphe, et [S1] revenait jusqu'a 6 fois. Chaque bloc garde ses propres pastilles.
function premieresCitations(items: Element[]): string[][] {
  const vues = new Set<string>()
  return items.map((it) => it.sources.filter((id) => !vues.has(id) && !!vues.add(id)))
}

function Bloc({ titre, items, sources, ton, rubriques = true }: {
  titre: string; items: Element[]; sources: FicheSource[]; ton: 'droit' | 'neutre' | 'attention'; rubriques?: boolean
}) {
  if (!items.length) return null
  const citations = premieresCitations(items)
  const couleur = ton === 'droit' ? 'text-forest' : ton === 'attention' ? 'text-[#8a6537]' : 'text-muted'
  return (
    <div className="mt-3.5">
      <h4 className={`mb-1.5 text-[10px] font-bold tracking-[1.4px] uppercase ${couleur}`}>{titre}</h4>
      <ul className="grid max-w-[75ch] gap-1.5">
        {items.map((it, i) => (
          <li key={i} className="text-[12.5px] leading-[1.6]">
            {/* rubrique affichee a son premier element : sous-titres propres a chaque mode */}
            {rubriques && it.rubrique && it.rubrique !== items[i - 1]?.rubrique && (
              <span className="mt-1.5 mb-0.5 block text-[11.5px] font-semibold text-ink">{it.rubrique}</span>
            )}
            {it.texte}
            <Citations ids={citations[i]} sources={sources} />
          </li>
        ))}
      </ul>
    </div>
  )
}

export function ListeSources({ sources }: { sources: FicheSource[] }) {
  const { ouvrirSource } = useApp()
  if (!sources.length) return null
  return (
    <div className="mt-4 border-t border-line-soft pt-3">
      <h4 className="mb-1 text-[10px] font-bold tracking-[1.4px] text-muted uppercase">Sources utilisées</h4>
      <ul className="max-w-[75ch]">
        {sources.map((s, i) => (
          <li key={s.id}>
            <button
              type="button"
              onClick={() => ouvrirSource(s.id)}
              className="flex w-full items-start gap-2.5 rounded-lg py-2 text-left hover:bg-chip"
            >
              <span aria-hidden className="grid size-[26px] shrink-0 place-items-center rounded-md bg-[#eef1eb] text-[13px] text-forest">
                {symbole(s)}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-[11px] leading-[1.35] font-semibold" title={s.entete}>
                  <span className="text-forest">[{i + 1}]</span> {titreCourt(s.entete)}
                </span>
                <span className="mt-0.5 block text-[10px] break-words text-muted">{s.version}</span>
              </span>
              {s.en_vigueur === false && (
                <span className="shrink-0 rounded-full bg-cream px-2 py-0.5 text-[10px] text-[#8a6537]">ancienne version</span>
              )}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

const MOTIFS = [
  ['inexact', 'Contenu inexact'],
  ['source_incorrecte', 'Source incorrecte'],
  ['source_manquante', 'Source manquante'],
  ['incomplet', 'Réponse incomplète'],
  ['hors_sujet', 'Hors sujet'],
  ['autre', 'Autre'],
] as const

function Retours({ reponse }: { reponse: ReponseChat }) {
  const { notifier } = useApp()
  const [etat, setEtat] = useState<'libre' | 'motif' | 'envoye'>('libre')
  const envoyer = (utile: boolean, motif?: string) => {
    api.feedback(reponse.reponse_id, utile, motif).catch(() => undefined)
    setEtat('envoye')
    notifier('Merci pour votre retour')
  }
  if (etat === 'envoye') return <span className="text-[10px] text-muted">Retour envoyé</span>
  if (etat === 'motif')
    return (
      <span className="flex flex-wrap items-center gap-1.5">
        <span className="text-[10px] text-muted">Quel problème ?</span>
        {MOTIFS.map(([id, libelle]) => (
          <button key={id} type="button" onClick={() => envoyer(false, id)}
            className="rounded-full border border-line px-2 py-0.5 text-[10px] text-[#59615b] hover:border-[#9eafa3]">
            {libelle}
          </button>
        ))}
      </span>
    )
  return (
    <span className="flex items-center gap-1.5">
      <span className="text-[10px] text-muted">Cette réponse vous a aidé ?</span>
      <button type="button" onClick={() => envoyer(true)} className="rounded-full border border-line px-2 py-0.5 text-[10px] hover:border-[#9eafa3]">Oui</button>
      <button type="button" onClick={() => setEtat('motif')} className="rounded-full border border-line px-2 py-0.5 text-[10px] hover:border-[#9eafa3]">Non</button>
    </span>
  )
}

const RUBRIQUE_EXEMPLE = 'Exemple' // rubrique du mode « expliquer » (api/prompts.py, RUBRIQUES)

/** Reponse directe d'abord (audit du 2026-11-16, point 3) : l'essentiel, les exemples et les points d'attention
 * (qui portent le rappel « consultez un professionnel ») restent visibles ; droit positif, reste de l'explication
 * et sources sont repliés. Sans reponse directe (commentaire, dissertation, fiches anterieures) : affichage complet. */
function Developpements({ r, blocs }: { r: ReponseChat; blocs: [string, string, string] }) {
  const [titreDroit, titreExplication, titreAttention] = blocs
  const directe = r.reponse_directe ?? []
  if (!directe.length)
    return (
      <>
        <Bloc titre={titreDroit} items={r.droit_positif} sources={r.sources} ton="droit" />
        <Bloc titre={titreExplication} items={r.explication} sources={r.sources} ton="neutre" />
        <Bloc titre={titreAttention} items={r.points_incertains} sources={r.sources} ton="attention" />
        <ListeSources sources={r.sources} />
      </>
    )
  const exemples = r.explication.filter((e) => e.rubrique === RUBRIQUE_EXEMPLE)
  const suite = r.explication.filter((e) => e.rubrique !== RUBRIQUE_EXEMPLE)
  return (
    <>
      <Bloc titre="L’essentiel" items={directe} sources={r.sources} ton="droit" />
      <Bloc titre={exemples.length > 1 ? 'Exemples' : 'Exemple'} items={exemples} sources={r.sources} ton="neutre" rubriques={false} />
      <Bloc titre={titreAttention} items={r.points_incertains} sources={r.sources} ton="attention" />
      <details className="mt-3.5 border-t border-line-soft pt-2.5">
        <summary className="cursor-pointer text-[11px] font-semibold text-forest hover:underline">Développements et sources</summary>
        <Bloc titre={titreDroit} items={r.droit_positif} sources={r.sources} ton="droit" />
        <Bloc titre={titreExplication} items={suite} sources={r.sources} ton="neutre" />
        <ListeSources sources={r.sources} />
      </details>
    </>
  )
}

/** titre=false : la fiche ouverte dans « Fiches & révisions » affiche deja le titre dans sa carte (point 6). */
export function Reponse({ message, actions = true, titre = true }: { message: Message; actions?: boolean; titre?: boolean }) {
  const { basculerFavori, estFavori } = useApp()
  const r = message.reponse!
  const retires = r.controle.elements_retires + r.controle.citations_retirees
  return (
    <article className="min-w-0 rounded-[10px] bg-[#f6f4ee] px-4 py-3.5 break-words">
      {r.statut === 'reponse' ? (
        <>
          {titre && r.titre && <h3 className="font-display text-[18px] leading-tight">{r.titre}</h3>}
          <Developpements r={r} blocs={infosMode(message.mode).blocs} />
        </>
      ) : (
        <div className="border-l-2 border-[#c8a16d] bg-cream px-3 py-2.5 text-[12px] leading-[1.55] text-[#746347]">
          <strong className="mb-1 block text-[#5f4f37]">
            {r.statut === 'hors_champ' ? 'Hors du champ de Lexia' : 'Pas de réponse vérifiable'}
          </strong>
          {r.message}
        </div>
      )}

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-line-soft pt-2.5">
        <p className="text-[10px] leading-[1.45] text-[#5f6762]">
          {r.avertissement}
          {retires > 0 && ` ${retires} élément(s) non vérifiable(s) retiré(s) automatiquement.`}
          {r.controle.recherche === 'lexicale' && ' Recherche par mots-clés.'}
        </p>
        {actions && r.statut === 'reponse' && (
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => basculerFavori(message)}
              aria-pressed={estFavori(r.reponse_id)}
              title="La fiche reste dans ce navigateur uniquement ; elle peut être exportée depuis « Fiches & révisions »."
              className="text-[10px] font-semibold text-forest hover:underline"
            >
              {estFavori(r.reponse_id) ? '★ Enregistrée' : '☆ Enregistrer en fiche'}
            </button>
            <Retours reponse={r} />
          </div>
        )}
      </div>
    </article>
  )
}
