// Histogramme d'une serie par jour (SVG, sans dependance).
// Specs : barres <= 24 px, extremite arrondie 4 px, base carree, ecart de 2 px, grille hairline,
// infobulle au survol (zone de survol = toute la colonne), tableau des valeurs en complement.
import { useEffect, useRef, useState } from 'react'
import type { JourStats } from '../lib/api'

const COULEUR = '#2b8a5e' // vert de la marque, valide (luminosite, chroma, contraste) sur la surface claire
const HAUTEUR = 190
const MARGE = { haut: 12, droite: 8, bas: 24, gauche: 34 }

function maxPropre(v: number): number {
  if (v <= 4) return 4
  const pas = 10 ** Math.floor(Math.log10(v))
  for (const m of [1, 2, 2.5, 5, 10]) if (m * pas >= v) return m * pas
  return 10 * pas
}

const jourCourt = (iso: string) => new Date(iso + 'T12:00:00').toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })
const jourLong = (iso: string) => new Date(iso + 'T12:00:00').toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' })

export function Histogramme({ serie, titre }: { serie: JourStats[]; titre: string }) {
  const boite = useRef<HTMLDivElement>(null)
  const [largeur, setLargeur] = useState(600)
  const [survol, setSurvol] = useState<number | null>(null)

  useEffect(() => {
    const el = boite.current
    if (!el) return
    const ro = new ResizeObserver(([e]) => setLargeur(Math.max(260, e.contentRect.width)))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const max = maxPropre(Math.max(...serie.map((d) => d.questions), 0))
  const largeurUtile = largeur - MARGE.gauche - MARGE.droite
  const hauteurUtile = HAUTEUR - MARGE.haut - MARGE.bas
  const colonne = largeurUtile / serie.length
  const barre = Math.max(2, Math.min(24, colonne - 2))
  const y = (v: number) => MARGE.haut + hauteurUtile - (v / max) * hauteurUtile
  const graduations = [0, max / 2, max]
  const pasEtiquette = colonne < 18 ? 7 : colonne < 30 ? 5 : 2

  const barrePath = (x: number, v: number) => {
    const h = (v / max) * hauteurUtile
    if (h <= 0) return ''
    const r = Math.min(4, h, barre / 2)
    const haut = MARGE.haut + hauteurUtile - h
    const bas = MARGE.haut + hauteurUtile
    return `M${x},${bas} V${haut + r} Q${x},${haut} ${x + r},${haut} H${x + barre - r} Q${x + barre},${haut} ${x + barre},${haut + r} V${bas} Z`
  }

  const d = survol !== null ? serie[survol] : null
  const xInfo = survol !== null ? MARGE.gauche + survol * colonne + colonne / 2 : 0

  return (
    <figure className="m-0">
      <figcaption className="mb-2 text-[13px] font-semibold">{titre}</figcaption>
      <div ref={boite} className="relative" onMouseLeave={() => setSurvol(null)}>
        <svg width={largeur} height={HAUTEUR} role="img" aria-label={`${titre}. Valeurs détaillées dans le tableau ci-dessous.`}>
          {graduations.map((g) => (
            <g key={g}>
              <line x1={MARGE.gauche} x2={largeur - MARGE.droite} y1={y(g)} y2={y(g)} stroke="#e6e4dc" strokeWidth={1} />
              <text x={MARGE.gauche - 6} y={y(g)} textAnchor="end" dominantBaseline="middle" className="fill-[#8a9089] text-[10px]">
                {g.toLocaleString('fr-FR')}
              </text>
            </g>
          ))}
          {serie.map((p, i) => {
            const x0 = MARGE.gauche + i * colonne
            const xb = x0 + (colonne - barre) / 2
            return (
              <g key={p.jour}>
                <path d={barrePath(xb, p.questions)} fill={COULEUR} opacity={survol === null || survol === i ? 1 : 0.45} />
                {(i % pasEtiquette === 0 || i === serie.length - 1) && (
                  <text x={x0 + colonne / 2} y={HAUTEUR - 6} textAnchor="middle" className="fill-[#8a9089] text-[10px]">{jourCourt(p.jour)}</text>
                )}
                {/* zone de survol : toute la colonne, plus grande que la barre */}
                <rect x={x0} y={MARGE.haut} width={colonne} height={hauteurUtile} fill="transparent" onMouseEnter={() => setSurvol(i)} />
              </g>
            )
          })}
        </svg>
        {d && (
          <div className="pointer-events-none absolute top-0 z-10 w-[190px] rounded-lg border border-line bg-surface px-3 py-2 text-[12px] shadow-[0_8px_24px_#17241d1f]"
            style={{ left: Math.min(Math.max(xInfo - 95, 0), largeur - 190) }}>
            <div className="mb-1 font-semibold capitalize">{jourLong(d.jour)}</div>
            <div className="flex justify-between"><span className="flex items-center gap-1.5"><span className="inline-block size-2 rounded-sm" style={{ background: COULEUR }} />Questions</span><b>{d.questions}</b></div>
            <div className="flex justify-between text-muted"><span>Questionnaires</span><span>{d.quiz}</span></div>
            <div className="flex justify-between text-muted"><span>Comptes actifs</span><span>{d.actifs}</span></div>
            <div className="flex justify-between text-muted"><span>Inscriptions</span><span>{d.inscriptions}</span></div>
          </div>
        )}
      </div>
      <details className="mt-2 text-[12px]">
        <summary className="cursor-pointer text-forest">Voir les données</summary>
        <div className="mt-2 max-h-56 overflow-auto">
          <table className="w-full text-left">
            <thead className="sticky top-0 bg-surface text-muted">
              <tr><th className="py-1 font-normal">Jour</th><th className="font-normal">Questions</th><th className="font-normal">Questionnaires</th><th className="font-normal">Actifs</th><th className="font-normal">Inscriptions</th></tr>
            </thead>
            <tbody>
              {[...serie].reverse().map((p) => (
                <tr key={p.jour} className="border-t border-line-soft"><td className="py-1">{jourCourt(p.jour)}</td><td>{p.questions}</td><td>{p.quiz}</td><td>{p.actifs}</td><td>{p.inscriptions}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  )
}
