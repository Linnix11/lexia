import type { ReactNode } from 'react'
import { Lien } from '../lib/router'
import { libelleSemestre, niveauDe, SEMESTRES, type Semestre } from '../lib/semestres'
import { useApp, type Vue } from '../state/contexte'
import { useSession } from '../state/session'

const VUES: { id: Vue; label: string; ico: string }[] = [
  { id: 'espace', label: 'Mon espace', ico: '⌂' },
  { id: 'assistant', label: 'Assistant IA', ico: '✳' },
  { id: 'matieres', label: 'Mes matières', ico: '▤' },
  { id: 'fiches', label: 'Fiches & révisions', ico: '▧' },
  { id: 'bibliotheque', label: 'Bibliothèque', ico: '▥' },
]

const ANNEES = ['L1', 'L2', 'L3'] as const

export function Sidebar() {
  const { vue, setVue, matieres, semestre, niveau } = useApp()
  return (
    <aside
      className="fixed inset-x-0 bottom-0 z-30 h-[60px] border-t border-line bg-paper px-3 py-[5px]
                 tab:sticky tab:top-0 tab:z-auto tab:flex tab:h-screen tab:flex-col tab:items-center tab:gap-[30px] tab:border-t-0 tab:border-r tab:bg-side tab:px-[9px] tab:py-[22px]
                 desk:items-stretch desk:px-[17px] desk:py-[26px]"
    >
      <div className="hidden items-center gap-2.5 tab:flex desk:px-2">
        <div className="grid size-[31px] place-items-center rounded-[9px] bg-forest font-display text-[19px] text-white">L</div>
        <div className="hidden desk:block">
          <div className="font-display text-[21px] tracking-[-.4px]">lexia</div>
          <div className="mt-0.5 text-[10px] text-muted">L’espace d’étude juridique</div>
        </div>
      </div>

      <nav aria-label="Navigation principale" className="h-full tab:h-auto tab:w-full">
        <div className="mb-2 hidden px-2.5 text-[10px] tracking-[1.25px] text-[#8c928c] uppercase desk:block">Espace étudiant</div>
        <ul className="flex h-full items-center justify-around tab:grid tab:h-auto tab:gap-1">
          {VUES.map((v) => {
            const actif = vue === v.id
            return (
              <li key={v.id}>
                <button
                  type="button"
                  onClick={() => setVue(v.id)}
                  aria-current={actif ? 'page' : undefined}
                  title={v.label}
                  className={`flex min-w-[42px] items-center justify-center gap-[11px] rounded-lg px-3 py-2 text-[#565f59]
                              tab:w-full tab:px-0 tab:py-3 desk:justify-start desk:px-2.5 desk:py-[11px] desk:text-left
                              ${actif ? 'bg-sage font-semibold text-[#254a3a]' : 'hover:bg-[#e8e9e2]'}`}
                >
                  <span aria-hidden className="text-[18px] tab:text-[16px] desk:w-[18px] desk:text-center">{v.ico}</span>
                  <span className="sr-only desk:not-sr-only">{v.label}</span>
                </button>
              </li>
            )
          })}
        </ul>
      </nav>

      <div className="mt-auto hidden desk:block">
        <div className="mb-2 px-2.5 text-[10px] tracking-[1.25px] text-[#8c928c] uppercase">Mon semestre</div>
        <div className="rounded-[10px] border border-[#dfdfd5] bg-chip p-3">
          <small className="text-[11px] text-muted">Semestre {semestre} · {niveau}</small>
          <strong className="my-1.5 block text-[13px]">Parcours droit général</strong>
          <small className="text-[11px] text-muted">{matieres.length || 3} matières suivies</small>
        </div>
      </div>
    </aside>
  )
}

export function Topbar() {
  const { vue, semestre, setSemestre } = useApp()
  const { profil } = useSession()
  const initiales = (profil?.email ?? 'ét').slice(0, 2).toUpperCase()
  const restant = profil ? Math.max(0, profil.formule.questions_par_jour - profil.usage.questions) : null
  const libelle = VUES.find((v) => v.id === vue)?.label
  return (
    <header className="flex h-14 items-center justify-between border-b border-line bg-surface/65 px-4 tab:h-[68px] tab:px-[22px] desk:px-[38px]">
      <div className="text-[12px] text-muted">
        <span className="hidden tab:inline">Espace étudiant <span aria-hidden> / </span> </span>
        <b className="font-semibold text-ink">{libelle}</b>
      </div>
      <div className="flex items-center gap-2.5 tab:gap-[17px]">
        <label className="sr-only" htmlFor="niveau">Choisir le semestre</label>
        <select
          id="niveau"
          value={semestre}
          onChange={(e) => setSemestre(Number(e.target.value) as Semestre)}
          className="rounded-[7px] border border-line bg-surface px-2 py-[7px] text-[12px] text-[#505b54] tab:px-[11px] tab:py-2"
        >
          {ANNEES.map((annee) => (
            <optgroup key={annee} label={annee}>
              {SEMESTRES.filter((s) => niveauDe(s) === annee).map((s) => (
                <option key={s} value={s}>{libelleSemestre(s)}</option>
              ))}
            </optgroup>
          ))}
        </select>
        {profil?.admin && (
          <Lien href="/admin" className="hidden rounded-full border border-line px-2.5 py-1 text-[11px] text-forest hover:bg-sage tab:inline">Admin</Lien>
        )}
        {profil && (
          <Lien href="/compte" title="Mon compte" className="hidden items-center gap-1 rounded-full bg-mint px-2.5 py-1 text-[11px] text-forest hover:bg-sage tab:flex">
            <span className="font-semibold">{restant}</span> question{(restant ?? 0) > 1 ? 's' : ''} restante{(restant ?? 0) > 1 ? 's' : ''} · {profil.formule.nom}
          </Lien>
        )}
        <Lien href="/compte" aria-label="Mon compte" title={profil?.email}
          className="grid size-[31px] place-items-center rounded-full bg-[#e9dfd0] text-[11px] font-bold text-[#694b31] hover:ring-2 hover:ring-[#d6c6ad]">
          {initiales}
        </Lien>
      </div>
    </header>
  )
}

export function Toast() {
  const { toast } = useApp()
  return (
    <div
      role="status"
      aria-live="polite"
      className={`pointer-events-none fixed bottom-[78px] left-1/2 z-50 -translate-x-1/2 rounded-lg bg-[#263c31] px-4 py-[11px] text-[12px] text-white shadow-[0_8px_28px_#17241d33] transition tab:bottom-[22px]
                  ${toast ? 'translate-y-0 opacity-100' : 'translate-y-5 opacity-0'}`}
    >
      {toast}
    </div>
  )
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-xl border border-line bg-surface ${className}`}>{children}</section>
}

export function CardHead({ titre, sousTitre, droite }: { titre: string; sousTitre?: string; droite?: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div>
        <h2 className="text-[14px] font-[650]">{titre}</h2>
        {sousTitre && <div className="mt-1 text-[11px] text-muted">{sousTitre}</div>}
      </div>
      {droite}
    </div>
  )
}
