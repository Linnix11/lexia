// Carte mentale d'une reponse, d'une fiche, d'un cours depose ou recupere, ou d'une matiere (D112,
// docs/cartes-mentales.md). Le serveur rend un plan verifie ; le navigateur le dessine en SVG maison.
// Accessibilite : la meme carte en listes imbriquees, toujours presente (visible au clavier, ou en « Vue en liste »).
import { useMemo, useRef, useState } from 'react'
import { useFocusSection } from '../lib/focusSection'
import { api, ApiError, type CarteMentale as Carte, type DemandeCarte, type FeuilleCarte, type NoeudCarte } from '../lib/api'
import { COULEURS, disposer, exporterPng, nomFichier, type Boite } from '../lib/carteMentale'
import { Chargement } from './Chargement'
import { enregistrerCarteMentale, MESSAGE_LIMITE_CARTES } from '../lib/cartesEnregistrees'
import { useSessionFacultative } from '../state/session'
import { useAppFacultatif } from '../state/contexte'

const AVERTISSEMENT = 'Carte générée automatiquement : vérifiez avec les textes.'
const ZOOMS = [0.5, 0.75, 1, 1.25, 1.5, 2]
const POLICE = 'system-ui, -apple-system, Segoe UI, Roboto, sans-serif'

const etroit = () => typeof window !== 'undefined' && !!window.matchMedia?.('(max-width: 639px)').matches

function Feuilles({ articles, couleur }: { articles: FeuilleCarte[]; couleur: string }) {
  if (!articles.length) return null
  return (
    <ul aria-label="Articles cités" className="mt-1 flex flex-wrap gap-1.5">
      {articles.map((a) => (
        <li key={a.texte} className="rounded-full border bg-cream px-2 py-0.5 text-[11px]" style={{ borderColor: couleur, color: couleur }}>
          {a.lien ? (
            <a href={a.lien.url} target="_blank" rel="noopener noreferrer" className="underline" title={a.lien.entete}>
              {a.texte}<span className="sr-only"> (texte officiel, nouvel onglet)</span>
            </a>
          ) : a.texte}
        </li>
      ))}
    </ul>
  )
}

/** Version en liste : branches repliables, references en liens. */
function Liste({ carte, replies, basculer }: { carte: Carte; replies: ReadonlySet<number>; basculer: (b: number) => void }) {
  return (
    <div>
      <p className="font-semibold text-[13px]">{carte.titre}</p>
      <ul className="mt-1.5 grid gap-2">
        {carte.branches.map((br: NoeudCarte, b) => {
          const couleur = COULEURS[b % COULEURS.length]
          const ouvert = !replies.has(b)
          const contenu = br.enfants.length > 0 || br.articles.length > 0
          return (
            <li key={b} className="border-l-[3px] pl-2.5" style={{ borderColor: couleur }}>
              {contenu ? (
                <button type="button" onClick={() => basculer(b)} aria-expanded={ouvert}
                  className="text-left text-[12.5px] font-semibold hover:underline" style={{ color: couleur }}>
                  <span aria-hidden>{ouvert ? '▾ ' : '▸ '}</span>{br.libelle}
                </button>
              ) : (
                <span className="text-[12.5px] font-semibold" style={{ color: couleur }}>{br.libelle}</span>
              )}
              {ouvert && (
                <>
                  <Feuilles articles={br.articles} couleur={couleur} />
                  {br.enfants.length > 0 && (
                    <ul className="mt-1 grid gap-1 pl-3">
                      {br.enfants.map((e, j) => (
                        <li key={j} className="text-[12px] leading-[1.45]">
                          {e.libelle}
                          <Feuilles articles={e.articles} couleur={couleur} />
                        </li>
                      ))}
                    </ul>
                  )}
                </>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function Dessin({ boites, basculer }: { boites: Boite[]; basculer: (b: number) => void }) {
  return (
    <>
      {boites.map((b) => {
        const centre = b.genre === 'centre'
        const plein = centre || b.genre === 'branche'
        const texte = plein ? '#ffffff' : b.genre === 'feuille' ? b.couleur : '#202724'
        const forme = (
          <g key={b.cle} onClick={b.genre === 'branche' ? () => basculer(b.branche) : undefined}
            style={b.genre === 'branche' ? { cursor: 'pointer' } : undefined} data-genre={b.genre}>
            <rect x={b.x} y={b.y} width={b.l} height={b.h} rx={b.genre === 'feuille' ? 10 : 8}
              fill={plein ? b.couleur : b.genre === 'feuille' ? '#fbf7ef' : '#ffffff'}
              stroke={b.couleur} strokeWidth={b.genre === 'enfant' ? 1.5 : 1} />
            <text x={b.x + 10} y={b.y + 10} fill={texte} fontFamily={POLICE}
              fontSize={centre ? 13 : b.genre === 'branche' ? 12.5 : 11.5} fontWeight={plein ? 600 : 400}
              textDecoration={b.lien ? 'underline' : undefined}>
              {b.lignes.map((l, i) => <tspan key={i} x={b.x + 10} dy={i === 0 ? 13 : 16}>{l}</tspan>)}
            </text>
            {b.replie > 0 && (
              <g>
                <circle cx={b.x + b.l} cy={b.y + b.h / 2} r={10} fill="#ffffff" stroke={b.couleur} />
                <text x={b.x + b.l} y={b.y + b.h / 2 + 4} textAnchor="middle" fontFamily={POLICE} fontSize={10.5}
                  fill={b.couleur} fontWeight={600}>+{b.replie}</text>
              </g>
            )}
          </g>
        )
        return b.lien ? (
          <a key={b.cle} href={b.lien.url} target="_blank" rel="noopener noreferrer" tabIndex={-1}>{forme}</a>
        ) : forme
      })}
    </>
  )
}

const MESSAGES_ENREGISTREMENT = {
  ok: 'Carte enregistrée dans « Mes cartes mentales » (dans ce navigateur uniquement).',
  deja: 'Cette carte est déjà dans « Mes cartes mentales ».',
  limite: MESSAGE_LIMITE_CARTES,
  erreur: 'Le navigateur n’a pas pu enregistrer la carte (navigation privée ou stockage plein).',
} as const

/** demande : construite au clic ; avecNotion : champ « notion » facultatif avant la demande (matiere).
 * enregistree : carte deja gardee (page « Mes cartes mentales ») affichee sans rien demander au serveur. */
export function CarteMentale({ demande, libelle = 'Carte mentale', avecNotion = false, enregistree, onFermer }: {
  demande?: (notion: string) => DemandeCarte; libelle?: string; avecNotion?: boolean
  enregistree?: Carte; onFermer?: () => void
}) {
  const [ouvert, setOuvert] = useState(!!enregistree)
  const { titre, ouvreur } = useFocusSection(ouvert)
  const [carte, setCarte] = useState<Carte | null>(enregistree ?? null)
  const compte = useSessionFacultative()?.profil?.email ?? ''
  const app = useAppFacultatif()
  const [sauvegarde, setSauvegarde] = useState<keyof typeof MESSAGES_ENREGISTREMENT | null>(null)
  const [chargement, setChargement] = useState(false)
  const [erreur, setErreur] = useState<string | null>(null)
  const [notion, setNotion] = useState('')
  const [replies, setReplies] = useState<ReadonlySet<number>>(new Set())
  const [zoom, setZoom] = useState(1)
  const [vue, setVue] = useState<'dessin' | 'liste'>(() => (etroit() ? 'liste' : 'dessin'))
  const [export_, setExport] = useState<string | null>(null)
  const svg = useRef<SVGSVGElement>(null)
  const disposition = useMemo(() => (carte && carte.branches.length ? disposer(carte, replies) : null), [carte, replies])

  const charger = async () => {
    if (chargement || !demande) return
    setChargement(true)
    setErreur(null)
    try {
      const c = await api.carteMentale(demande(notion.trim()))
      setReplies(new Set())
      setCarte(c)
      setSauvegarde(null)
    } catch (e) {
      setErreur(e instanceof ApiError ? e.message : 'La carte mentale n’a pas pu être préparée.')
    } finally {
      setChargement(false)
    }
  }

  const ouvrir = () => {
    setOuvert(true)
    if (!avecNotion && !carte) charger()
  }

  const basculer = (b: number) => setReplies((r) => {
    const n = new Set(r)
    if (n.has(b)) n.delete(b)
    else n.add(b)
    return n
  })

  const exporter = async () => {
    if (!svg.current || !disposition || !carte) return
    setExport(null)
    try {
      await exporterPng(svg.current, disposition.largeur, disposition.hauteur, nomFichier(carte.titre))
    } catch {
      setExport('L’image n’a pas pu être créée dans ce navigateur : utilisez la vue en liste ou une capture d’écran.')
    }
  }

  if (!ouvert)
    return (
      <button ref={ouvreur} type="button" onClick={ouvrir}
        className="min-h-6 rounded-full border border-line px-2.5 text-[11px] text-forest hover:border-[#9eafa3]">
        {libelle}
      </button>
    )

  const bouton = 'min-h-7 rounded-[7px] border border-line px-2.5 text-[11px] text-forest hover:border-[#9eafa3] disabled:opacity-50'
  const iZoom = ZOOMS.indexOf(zoom)
  return (
    <section aria-label="Carte mentale" className="mt-2 w-full rounded-[10px] border border-[#cfd9d1] bg-[#f6f8f3] p-3 text-[12px]">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 ref={titre} tabIndex={-1} className="text-[11px] font-bold tracking-[1.4px] text-forest uppercase">Carte mentale</h4>
        <button type="button" onClick={() => (onFermer ? onFermer() : setOuvert(false))} className="text-[11px] text-muted hover:text-forest">Fermer</button>
      </div>
      {avecNotion && (
        <form className="mt-2 flex flex-wrap items-end gap-2" onSubmit={(e) => { e.preventDefault(); charger() }}>
          <label className="grid min-w-[180px] flex-1 gap-1 text-[11px] text-muted">
            Notion (facultatif)
            <input value={notion} onChange={(e) => setNotion(e.target.value)} maxLength={120}
              placeholder="ex. responsabilité du fait des choses"
              className="rounded-[7px] border border-line bg-white px-2 py-1.5 text-[12px] text-ink" />
          </label>
          <button type="submit" disabled={chargement} className={bouton}>{carte ? 'Refaire la carte' : 'Créer la carte'}</button>
        </form>
      )}
      {chargement && (
        <Chargement className="mt-2" duree="jusqu’à une minute"
          etapes={['Lecture du contenu…', 'Recherche des articles à citer…', 'Construction des branches…', 'Vérification des renvois…', 'Presque prête…']} />
      )}
      {erreur && <p role="alert" className="mt-2 text-[#8c4a36]">{erreur}</p>}
      {carte && !carte.branches.length && <p role="alert" className="mt-2 text-[#8c4a36]">{carte.message}</p>}
      {carte && disposition && (
        <>
          {!enregistree && (
            <p className="mt-1 text-[11px] text-muted">
              {carte.partiel && 'Carte du début du document, trop long pour être pris en entier · '}
              {`${carte.restants} carte(s) restante(s) aujourd’hui`}
            </p>
          )}
          <div className="mt-2 flex flex-wrap items-center gap-2" role="toolbar" aria-label="Affichage de la carte">
            <button type="button" className={bouton} aria-pressed={vue === 'liste'}
              onClick={() => setVue(vue === 'liste' ? 'dessin' : 'liste')}>
              {vue === 'liste' ? 'Vue en carte' : 'Vue en liste'}
            </button>
            {vue === 'dessin' && (
              <>
                <button type="button" className={bouton} aria-label="Dézoomer" disabled={iZoom <= 0}
                  onClick={() => setZoom(ZOOMS[iZoom - 1])}>−</button>
                <span className="min-w-10 text-center text-[11px] text-muted" aria-live="polite">{Math.round(zoom * 100)} %</span>
                <button type="button" className={bouton} aria-label="Zoomer" disabled={iZoom >= ZOOMS.length - 1}
                  onClick={() => setZoom(ZOOMS[iZoom + 1])}>+</button>
              </>
            )}
            <button type="button" className={bouton} onClick={() => setReplies(new Set())} disabled={replies.size === 0}>Tout déplier</button>
            <button type="button" className={bouton} disabled={replies.size === carte.branches.length}
              onClick={() => setReplies(new Set(carte.branches.map((_, i) => i)))}>Tout replier</button>
            {vue === 'dessin' && <button type="button" className={bouton} onClick={exporter}>Image PNG</button>}
            {!enregistree && compte && (
              <button type="button" className={`${bouton} border-forest font-semibold`}
                onClick={() => setSauvegarde(enregistrerCarteMentale(carte, compte))}>
                Enregistrer la carte
              </button>
            )}
          </div>
          {sauvegarde && (
            <p role="status" className={`mt-1 text-[11px] ${sauvegarde === 'ok' || sauvegarde === 'deja' ? 'text-forest' : 'text-[#8c4a36]'}`}>
              {MESSAGES_ENREGISTREMENT[sauvegarde]}
              {(sauvegarde === 'ok' || sauvegarde === 'deja') && app && (
                <> <button type="button" onClick={() => app.setVue('cartes')} className="font-semibold underline">Voir mes cartes</button></>
              )}
            </p>
          )}
          {export_ && <p role="alert" className="mt-1 text-[11px] text-[#8c4a36]">{export_}</p>}
          {vue === 'dessin' && (
            <div className="mt-2 max-h-[70vh] overflow-auto rounded-[8px] border border-line bg-white [-webkit-overflow-scrolling:touch]">
              <svg ref={svg} aria-hidden="true" focusable="false" data-testid="dessin-carte"
                viewBox={`0 0 ${disposition.largeur} ${disposition.hauteur}`}
                width={disposition.largeur * zoom} height={disposition.hauteur * zoom} className="block">
                {disposition.traits.map((t) => (
                  <path key={t.cle} d={t.d} fill="none" stroke={t.couleur} strokeWidth={1.5} strokeOpacity={0.7} />
                ))}
                <Dessin boites={disposition.boites} basculer={basculer} />
              </svg>
            </div>
          )}
          {/* Toujours presente : lue par les lecteurs d'ecran ; affichee si on y entre au clavier ou en vue liste. */}
          <div className={vue === 'liste' ? 'mt-2 rounded-[8px] border border-line bg-white p-3'
            : 'sr-only focus-within:not-sr-only focus-within:mt-2 focus-within:block focus-within:rounded-[8px] focus-within:border focus-within:border-line focus-within:bg-white focus-within:p-3'}>
            <Liste carte={carte} replies={replies} basculer={basculer} />
          </div>
          <p className="mt-2 text-[11px] text-muted">Cliquez sur une branche pour la replier ; les articles soulignés ouvrent le texte officiel.</p>
          <p className="mt-1 text-[11px] leading-[1.4] text-[#746347]">{carte.avertissement || AVERTISSEMENT}</p>
        </>
      )}
    </section>
  )
}
