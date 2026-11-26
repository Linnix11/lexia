// Carte mentale d'une reponse, d'une fiche, d'un cours depose ou recupere, ou d'une matiere (D112,
// docs/cartes-mentales.md). Le serveur rend un plan verifie ; le navigateur le dessine en SVG maison.
// Accessibilite : la meme carte en listes imbriquees, toujours presente (visible au clavier, ou en « Vue en liste »).
// D138 : mode « Réviser » (sous-idees et references masquees, revelees une a une), impression ou PDF, plan copie.
import { useMemo, useRef, useState, type Ref } from 'react'
import { flushSync } from 'react-dom'
import { createRoot } from 'react-dom/client'
import { useFocusSection } from '../lib/focusSection'
import { api, ApiError, type CarteMentale as Carte, type DemandeCarte, type FeuilleCarte, type NoeudCarte } from '../lib/api'
import { COULEURS, disposer, exporterPng, nomFichier, pageImpression, planTexte, type Boite, type Disposition } from '../lib/carteMentale'
import { Chargement } from './Chargement'
import { enregistrerCarteMentale, MESSAGE_LIMITE_CARTES } from '../lib/cartesEnregistrees'
import { useSessionFacultative } from '../state/session'
import { useAppFacultatif } from '../state/contexte'

const AVERTISSEMENT = 'Carte générée automatiquement : vérifiez avec les textes.'
const ZOOMS = [0.5, 0.75, 1, 1.25, 1.5, 2]
const POLICE = 'system-ui, -apple-system, Segoe UI, Roboto, sans-serif'
const ROUGE = '#8c4a36' // arret abandonne : bordure en tirets

const etroit = () => typeof window !== 'undefined' && !!window.matchMedia?.('(max-width: 639px)').matches

/** Cles des elements a retrouver en mode revision : les memes que les boites du dessin (lib/carteMentale.ts). */
const cleEnfant = (b: number, j: number) => `b${b}-e${j}`
const cleFeuille = (parent: string, i: number) => `${parent}-a${i}`

function aRetrouver(carte: Carte): string[] {
  return carte.branches.flatMap((br, b) => [
    ...br.articles.map((_, i) => cleFeuille(`b${b}`, i)),
    ...br.enfants.flatMap((e, j) => [cleEnfant(b, j), ...e.articles.map((_, i) => cleFeuille(cleEnfant(b, j), i))]),
  ])
}

interface Revision {
  masque: (cle: string) => boolean
  reveler: (cle: string) => void
}

const BOUTON_MASQUE = 'min-h-7 rounded-full border border-dashed bg-white px-2.5 py-0.5 text-[11px] text-muted hover:text-forest'

function Feuilles({ articles, couleur, parent, libelle, revision }: {
  articles: FeuilleCarte[]; couleur: string; parent: string; libelle: string; revision: Revision
}) {
  if (!articles.length) return null
  return (
    <ul aria-label="Articles cités" className="mt-1 flex flex-wrap gap-1.5">
      {articles.map((a, i) => {
        const cle = cleFeuille(parent, i)
        if (revision.masque(cle))
          return (
            <li key={cle}>
              <button type="button" onClick={() => revision.reveler(cle)} className={BOUTON_MASQUE} style={{ borderColor: couleur }}
                aria-label={`Révéler la référence ${i + 1} de « ${libelle} »`}>? Référence</button>
            </li>
          )
        const abandonne = a.statut === 'abandonne'
        return (
          <li key={cle} className={`rounded-full border bg-cream px-2 py-0.5 text-[11px] ${abandonne ? 'border-dashed' : ''}`}
            style={{ borderColor: abandonne ? ROUGE : couleur, color: couleur }}>
            {a.lien ? (
              <a href={a.lien.url} target="_blank" rel="noopener noreferrer" className="underline" title={a.lien.entete}>
                {a.texte}<span className="sr-only"> (texte officiel, nouvel onglet)</span>
              </a>
            ) : a.texte}
          </li>
        )
      })}
    </ul>
  )
}

/** Version en liste : branches repliables, references en liens ; en revision, boutons « ? » a la place. */
function Liste({ carte, replies, basculer, revision }: {
  carte: Carte; replies: ReadonlySet<number>; basculer: (b: number) => void; revision: Revision
}) {
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
                  <Feuilles articles={br.articles} couleur={couleur} parent={`b${b}`} libelle={br.libelle} revision={revision} />
                  {br.enfants.length > 0 && (
                    <ul className="mt-1 grid gap-1 pl-3">
                      {br.enfants.map((e, j) => {
                        const masque = revision.masque(cleEnfant(b, j))
                        return (
                          <li key={j} className="text-[12px] leading-[1.45]">
                            {masque ? (
                              <button type="button" onClick={() => revision.reveler(cleEnfant(b, j))} className={BOUTON_MASQUE}
                                style={{ borderColor: couleur }} aria-label={`Révéler la sous-idée ${j + 1} de « ${br.libelle} »`}>
                                ? Sous-idée à retrouver
                              </button>
                            ) : e.libelle}
                            <Feuilles articles={e.articles} couleur={couleur} parent={cleEnfant(b, j)}
                              libelle={masque ? `la sous-idée ${j + 1} de ${br.libelle}` : e.libelle} revision={revision} />
                          </li>
                        )
                      })}
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

function Dessin({ boites, basculer, revision }: { boites: Boite[]; basculer: (b: number) => void; revision: Revision }) {
  return (
    <>
      {boites.map((b) => {
        const centre = b.genre === 'centre'
        const plein = centre || b.genre === 'branche'
        const masque = (b.genre === 'enfant' || b.genre === 'feuille') && revision.masque(b.cle)
        const abandonne = b.statut === 'abandonne' && !masque
        const texte = plein ? '#ffffff' : b.genre === 'feuille' ? b.couleur : '#202724'
        const clic = masque ? () => revision.reveler(b.cle) : b.genre === 'branche' ? () => basculer(b.branche) : undefined
        const forme = (
          <g key={b.cle} onClick={clic} style={clic ? { cursor: 'pointer' } : undefined} data-genre={b.genre}
            data-masque={masque || undefined}>
            <rect x={b.x} y={b.y} width={b.l} height={b.h} rx={b.genre === 'feuille' ? 10 : 8}
              fill={masque ? '#f6f8f3' : plein ? b.couleur : b.genre === 'feuille' ? '#fbf7ef' : '#ffffff'}
              stroke={abandonne ? ROUGE : b.couleur} strokeWidth={b.genre === 'enfant' || abandonne ? 1.5 : 1}
              strokeDasharray={masque || abandonne ? '5 3' : undefined} />
            {masque ? (
              <text x={b.x + b.l / 2} y={b.y + b.h / 2 + 5} textAnchor="middle" fill={b.couleur} fontFamily={POLICE}
                fontSize={15} fontWeight={600}>?</text>
            ) : (
              <text x={b.x + 10} y={b.y + 10} fill={texte} fontFamily={POLICE}
                fontSize={centre ? 13 : b.genre === 'branche' ? 12.5 : 11.5} fontWeight={plein ? 600 : 400}
                textDecoration={b.lien ? 'underline' : undefined}>
                {b.lignes.map((l, i) => <tspan key={i} x={b.x + 10} dy={i === 0 ? 13 : 16}>{l}</tspan>)}
              </text>
            )}
            {b.replie > 0 && (
              <g>
                <circle cx={b.x + b.l} cy={b.y + b.h / 2} r={10} fill="#ffffff" stroke={b.couleur} />
                <text x={b.x + b.l} y={b.y + b.h / 2 + 4} textAnchor="middle" fontFamily={POLICE} fontSize={10.5}
                  fill={b.couleur} fontWeight={600}>+{b.replie}</text>
              </g>
            )}
          </g>
        )
        return b.lien && !masque ? (
          <a key={b.cle} href={b.lien.url} target="_blank" rel="noopener noreferrer" tabIndex={-1}>{forme}</a>
        ) : forme
      })}
    </>
  )
}

function Svg({ disposition, zoom = 1, basculer, revision, svgRef }: {
  disposition: Disposition; zoom?: number; basculer: (b: number) => void; revision: Revision; svgRef?: Ref<SVGSVGElement>
}) {
  return (
    <svg ref={svgRef} aria-hidden="true" focusable="false" data-testid="dessin-carte" xmlns="http://www.w3.org/2000/svg"
      viewBox={`0 0 ${disposition.largeur} ${disposition.hauteur}`}
      width={disposition.largeur * zoom} height={disposition.hauteur * zoom} className="block">
      {disposition.traits.map((t) => (
        <path key={t.cle} d={t.d} fill="none" stroke={t.couleur} strokeWidth={1.5} strokeOpacity={0.7} />
      ))}
      <Dessin boites={disposition.boites} basculer={basculer} revision={revision} />
    </svg>
  )
}

const SANS_REVISION: Revision = { masque: () => false, reveler: () => {} }

/** Dessin complet (tout deplie, rien de masque) en texte SVG, pour la page a imprimer. */
function svgComplet(carte: Carte): string {
  const conteneur = document.createElement('div')
  const racine = createRoot(conteneur)
  flushSync(() => racine.render(<Svg disposition={disposer(carte)} basculer={() => {}} revision={SANS_REVISION} />))
  const svg = conteneur.innerHTML.replace(' data-testid="dessin-carte"', '')
  racine.unmount()
  return svg
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
  const [avis, setAvis] = useState<{ texte: string; ok: boolean } | null>(null)
  const [enRevision, setEnRevision] = useState(false)
  const [reveles, setReveles] = useState<ReadonlySet<string>>(new Set())
  const svg = useRef<SVGSVGElement>(null)
  const disposition = useMemo(() => (carte && carte.branches.length ? disposer(carte, replies) : null), [carte, replies])
  const cles = useMemo(() => (carte ? aRetrouver(carte) : []), [carte])
  const revision: Revision = {
    masque: (cle) => enRevision && !reveles.has(cle),
    reveler: (cle) => setReveles((r) => new Set(r).add(cle)),
  }

  const charger = async () => {
    if (chargement || !demande) return
    setChargement(true)
    setErreur(null)
    try {
      const c = await api.carteMentale(demande(notion.trim()))
      setReplies(new Set())
      setReveles(new Set())
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

  const reviser = () => {
    setEnRevision(!enRevision)
    setReveles(new Set())
    setReplies(new Set()) // toutes les branches ouvertes : chaque « ? » est visible
  }

  const exporter = async () => {
    if (!svg.current || !disposition || !carte) return
    setAvis(null)
    try {
      await exporterPng(svg.current, disposition.largeur, disposition.hauteur, nomFichier(carte.titre))
    } catch {
      setAvis({ ok: false, texte: 'L’image n’a pas pu être créée dans ce navigateur : utilisez « Imprimer ou PDF » ou une capture d’écran.' })
    }
  }

  const imprimer = () => {
    if (!carte) return
    setAvis(null)
    const fenetre = window.open('', '_blank')
    if (!fenetre) {
      setAvis({ ok: false, texte: 'Le navigateur a bloqué la fenêtre d’impression : autorisez les fenêtres de Lexia, ou utilisez l’image PNG.' })
      return
    }
    fenetre.document.open()
    fenetre.document.write(pageImpression(carte, svgComplet(carte)))
    fenetre.document.close()
    fenetre.focus()
    // « Enregistrer au format PDF » est propose par la boite d'impression du navigateur
    setTimeout(() => fenetre.print(), 250)
  }

  const copier = async () => {
    if (!carte) return
    try {
      await navigator.clipboard.writeText(planTexte(carte))
      setAvis({ ok: true, texte: 'Plan copié : collez-le dans vos fiches.' })
    } catch {
      setAvis({ ok: false, texte: 'Le navigateur n’a pas permis la copie : utilisez la vue en liste et sélectionnez le texte.' })
    }
  }

  if (!ouvert)
    return (
      <button ref={ouvreur} type="button" onClick={ouvrir}
        className="min-h-6 rounded-full border border-line px-2.5 text-[11px] text-forest hover:border-[#9eafa3]">
        {libelle}
      </button>
    )

  const bouton = 'min-h-8 rounded-[7px] border border-line bg-white/60 px-2.5 text-[11px] text-forest hover:border-[#9eafa3] disabled:opacity-50'
  const iZoom = ZOOMS.indexOf(zoom)
  const toutReplie = !!carte && replies.size === carte.branches.length
  const restants = cles.filter((c) => !reveles.has(c)).length
  return (
    <section aria-label="Carte mentale" className="mt-2 w-full rounded-[10px] border border-[#cfd9d1] bg-[#f6f8f3] p-3 text-[12px]">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 ref={titre} tabIndex={-1} className="text-[11px] font-bold tracking-[1.4px] text-forest uppercase">Carte mentale</h4>
        <button type="button" onClick={() => (onFermer ? onFermer() : setOuvert(false))} className="min-h-8 text-[11px] text-muted hover:text-forest">Fermer</button>
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
          <div className="mt-2 flex flex-wrap items-center gap-1.5" role="toolbar" aria-label="Affichage de la carte">
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
            <button type="button" className={bouton}
              onClick={() => setReplies(toutReplie ? new Set() : new Set(carte.branches.map((_, i) => i)))}>
              {toutReplie ? 'Tout déplier' : 'Tout replier'}
            </button>
          </div>
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5" role="toolbar" aria-label="Réviser et exporter la carte">
            <button type="button" aria-pressed={enRevision} onClick={reviser} disabled={!cles.length}
              className={enRevision
                ? 'min-h-8 rounded-[7px] border border-forest bg-forest px-2.5 text-[11px] font-semibold text-white hover:bg-forest-dark'
                : `${bouton} font-semibold`}>
              {enRevision ? 'Quitter la révision' : 'Réviser'}
            </button>
            {enRevision && restants > 0 && (
              <button type="button" className={bouton} onClick={() => setReveles(new Set(cles))}>Tout révéler</button>
            )}
            <button type="button" className={bouton} onClick={imprimer}>Imprimer ou PDF</button>
            {vue === 'dessin' && <button type="button" className={bouton} onClick={exporter}>Image PNG</button>}
            <button type="button" className={bouton} onClick={copier}>Copier le plan</button>
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
          {avis && <p role={avis.ok ? 'status' : 'alert'} className={`mt-1 text-[11px] ${avis.ok ? 'text-forest' : 'text-[#8c4a36]'}`}>{avis.texte}</p>}
          {enRevision && (
            <p className="mt-2 rounded-[7px] border border-dashed border-[#9eafa3] bg-white px-2.5 py-1.5 text-[11.5px] leading-[1.45] text-ink">
              Retrouvez de mémoire chaque sous-idée et chaque référence, puis touchez « ? » pour vérifier.{' '}
              <span role="status" className="font-semibold text-forest">
                {restants ? `${cles.length - restants} sur ${cles.length} révélé(s).` : 'Tout est révélé.'}
              </span>
            </p>
          )}
          {vue === 'dessin' && (
            <div className="mt-2 max-h-[70vh] overflow-auto rounded-[8px] border border-line bg-white [-webkit-overflow-scrolling:touch]">
              <Svg svgRef={svg} disposition={disposition} zoom={zoom} basculer={basculer} revision={revision} />
            </div>
          )}
          {/* Toujours presente : lue par les lecteurs d'ecran ; affichee si on y entre au clavier ou en vue liste. */}
          <div className={vue === 'liste' ? 'mt-2 rounded-[8px] border border-line bg-white p-3'
            : 'sr-only focus-within:not-sr-only focus-within:mt-2 focus-within:block focus-within:rounded-[8px] focus-within:border focus-within:border-line focus-within:bg-white focus-within:p-3'}>
            <Liste carte={carte} replies={replies} basculer={basculer} revision={revision} />
          </div>
          {!enRevision && (
            <p className="mt-2 text-[11px] text-muted">
              Touchez une branche pour la replier ; les articles soulignés ouvrent le texte officiel. « Réviser » masque
              les sous-idées et les références pour vous interroger.
            </p>
          )}
          <p className="mt-1 text-[11px] leading-[1.4] text-[#746347]">{carte.avertissement || AVERTISSEMENT}</p>
        </>
      )}
    </section>
  )
}
