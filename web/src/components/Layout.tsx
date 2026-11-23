import type { MouseEvent, ReactNode } from 'react'
import { Lien, useRouteur } from '../lib/router'
import { BandeauEmail } from '../site/VerifierEmail'
import { libelleSemestre, niveauDe, SEMESTRES, type Semestre } from '../lib/semestres'
import { useApp, type Vue } from '../state/contexte'
import { useSession } from '../state/session'
import { BoutonAvis } from './AvisBeta'
import { LogoHorizontal, Signet } from './Logo'

// court : libelle visible sous l'icone dans la barre du bas du mobile (audit du 2026-11-18, D7), contenu
// dans le libelle complet qui reste le nom accessible.
const VUES: { id: Vue; label: string; court: string; ico: string }[] = [
  { id: 'espace', label: 'Mon espace', court: 'Espace', ico: '⌂' },
  { id: 'assistant', label: 'Assistant IA', court: 'Assistant', ico: '✳' },
  { id: 'matieres', label: 'Mes matières', court: 'Matières', ico: '▤' },
  { id: 'fiches', label: 'Fiches & révisions', court: 'Fiches', ico: '▧' },
  { id: 'cartes', label: 'Mes cartes mentales', court: 'Cartes', ico: '✣' },
  { id: 'bibliotheque', label: 'Bibliothèque', court: 'Biblio', ico: '▥' },
]

const ANNEES = ['L1', 'L2', 'L3'] as const

/** Cadre de l'espace etudiant (barre laterale et en-tete), partage par /app et /compte : passer par son
 * compte ne fait plus perdre la navigation de l'espace (audit du 2026-11-16, point 14). */
export function CadreEspace({ titre, children }: { titre?: string; children: ReactNode }) {
  return (
    <>
      {/* Lien d'evitement, premier arret du clavier (RGAA 12.7 ; recette du 2026-11-20, D-9) */}
      <a href="#contenu" onClick={allerAuContenu}
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-lg focus:bg-forest focus:px-3 focus:py-2 focus:text-[13px] focus:text-white">
        Aller au contenu
      </a>
      <BandeauEmail />
      <div className="min-h-screen pb-[calc(61px+env(safe-area-inset-bottom))] tab:grid tab:grid-cols-[68px_minmax(0,1fr)] tab:pb-0 desk:grid-cols-[232px_minmax(0,1fr)]">
        <Sidebar horsEspace={titre !== undefined} />
        <main id="contenu" tabIndex={-1} className="min-w-0 outline-none">
          <Topbar titre={titre} />
          <div className="mx-auto max-w-[1300px] px-4 pt-6 pb-6 min-[361px]:px-4 tab:px-[22px] tab:pt-[29px] desk:px-[38px] desk:pt-9 desk:pb-[52px]">
            {children}
            <footer className="pt-5 text-[11px] leading-[1.6] text-[#5f6762] tab:flex tab:justify-between tab:gap-3.5">
              <span className="block">Lexia · étude du droit français</span>
              <span className="mt-1 block tab:mt-0">Les citations ouvrent la source, la date et la version utilisées.</span>
            </footer>
          </div>
        </main>
      </div>
      <Toast />
    </>
  )
}

/** Focus sur le contenu sans toucher a l'adresse : le routeur et le jeton des liens lisent le « # ». */
function allerAuContenu(e: MouseEvent<HTMLAnchorElement>) {
  const cible = document.getElementById('contenu')
  if (!cible) return
  e.preventDefault()
  cible.focus()
  cible.scrollIntoView({ block: 'start' })
}

/** horsEspace : page du cadre hors de /app (Mon compte) ; un clic ramene a la vue choisie de l'espace. */
export function Sidebar({ horsEspace = false }: { horsEspace?: boolean }) {
  const { vue, setVue, matieres, semestre, niveau } = useApp()
  const { naviguer } = useRouteur()
  return (
    // Barre du bas du mobile : hauteur et marge de la barre d'accueil de l'iPhone (env(), viewport-fit=cover),
    // masquee pendant la saisie (index.css, data-barre-bas) ; audit mobile du 2026-11-18.
    <aside
      data-barre-bas
      className="fixed inset-x-0 bottom-0 z-30 h-[calc(60px+env(safe-area-inset-bottom))] border-t border-line bg-paper px-3 pt-[5px] pb-[calc(5px+env(safe-area-inset-bottom))]
                 tab:sticky tab:top-0 tab:z-auto tab:flex tab:h-screen tab:flex-col tab:items-center tab:gap-[30px] tab:border-t-0 tab:border-r tab:bg-side tab:px-[9px] tab:py-[22px]
                 desk:items-stretch desk:px-[17px] desk:py-[26px]"
    >
      <div className="hidden items-center gap-2.5 tab:flex desk:px-2">
        <Signet hauteur={34} className="desk:hidden" />
        <div className="hidden desk:block">
          <LogoHorizontal hauteur={45} />
          <div className="mt-1 text-[11px] text-muted">L’espace d’étude juridique</div>
        </div>
      </div>

      <nav aria-label="Navigation principale" className="h-full tab:h-auto tab:w-full">
        <div className="mb-2 hidden px-2.5 text-[11px] tracking-[1.25px] text-[#5f6762] uppercase desk:block">Espace étudiant</div>
        <ul className="flex h-full items-center justify-around tab:grid tab:h-auto tab:gap-1">
          {VUES.map((v) => {
            const actif = !horsEspace && vue === v.id
            return (
              <li key={v.id}>
                <button
                  type="button"
                  onClick={() => {
                    setVue(v.id)
                    if (horsEspace) naviguer('/app')
                  }}
                  aria-current={actif ? 'page' : undefined}
                  title={v.label}
                  className={`flex min-w-[42px] flex-col items-center justify-center gap-0.5 rounded-lg px-2 py-1.5 text-[#565f59]
                              tab:w-full tab:flex-row tab:gap-[11px] tab:px-0 tab:py-3 desk:justify-start desk:px-2.5 desk:py-[11px] desk:text-left
                              ${actif ? 'bg-sage font-semibold text-[#254a3a]' : 'hover:bg-[#e8e9e2]'}`}
                >
                  <span aria-hidden className="text-[18px] tab:text-[16px] desk:w-[18px] desk:text-center">{v.ico}</span>
                  <span aria-hidden className="text-[11px] leading-none tab:hidden">{v.court}</span>
                  <span className="sr-only desk:not-sr-only">{v.label}</span>
                </button>
              </li>
            )
          })}
        </ul>
      </nav>

      <div className="mt-auto hidden desk:block">
        <div className="mb-2 px-2.5 text-[11px] tracking-[1.25px] text-[#5f6762] uppercase">Mon semestre</div>
        <div className="rounded-[10px] border border-[#dfdfd5] bg-chip p-3">
          <small className="text-[11px] text-muted">Semestre {semestre} · {niveau}</small>
          <strong className="my-1.5 block text-[13px]">Parcours droit général</strong>
          <small className="text-[11px] text-muted">{matieres.length > 1 ? `${matieres.length} matières disponibles` : `${matieres.length} matière disponible`}</small>
        </div>
      </div>
    </aside>
  )
}

export function Topbar({ titre }: { titre?: string }) {
  const { vue, semestre, setSemestre } = useApp()
  const { profil } = useSession()
  const initiales = (profil?.prenom?.trim() || profil?.email || 'ét').slice(0, profil?.prenom?.trim() ? 1 : 2).toUpperCase()
  const restant = profil ? Math.max(0, profil.formule.questions_par_jour - profil.usage.questions) : null
  const libelle = titre ?? VUES.find((v) => v.id === vue)?.label
  return (
    // Mobile : le titre se tronque, les actions et le rond du compte gardent leur taille ; le rond est le seul
    // acces a « Mon compte » sur telephone (recette du 2026-11-20, D-2).
    <header className="flex h-14 items-center justify-end gap-2 border-b tab:justify-between border-line bg-surface/65 px-4 tab:h-[68px] tab:px-[22px] desk:px-[38px]">
      {/* Sur telephone, la page porte son propre titre et la barre du bas marque la vue : le fil d'Ariane reste
          lu par les lecteurs d'ecran, la place va au semestre et au compte. */}
      <div className="sr-only min-w-0 truncate text-[12px] text-muted tab:not-sr-only" title={libelle}>
        <span className="hidden tab:inline">Espace étudiant <span aria-hidden> / </span> </span>
        <b className="font-semibold text-ink">{libelle}</b>
      </div>
      <div className="flex shrink-0 items-center gap-1.5 min-[400px]:gap-2.5 tab:gap-[17px]">
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
          <Lien href={profil.double_authentification ? '/admin' : '/compte?2fa'}
            title={profil.double_authentification ? undefined : 'Activez la double authentification pour accéder à l’administration'}
            className="hidden rounded-full border border-line px-2.5 py-1 text-[11px] text-forest hover:bg-sage tab:inline">
            {profil.double_authentification ? 'Admin' : 'Admin · activer la 2FA'}
          </Lien>
        )}
        <BoutonAvis />
        {profil && (
          <Lien href="/compte" title="Mon compte" className="flex items-center gap-1 whitespace-nowrap rounded-full bg-mint px-2.5 py-1 text-[11px] text-forest hover:bg-sage">
            {/* visible aussi sur mobile, sans le nom de la formule (audit du 2026-11-18, D7) */}
            <span className="font-semibold">{restant}</span>
            {/* sous 361 px, le nombre seul : le mot reste lu par les lecteurs d'ecran */}
            <span className="max-[360px]:sr-only"><span className="hidden tab:inline">question{(restant ?? 0) > 1 ? 's' : ''} </span>restante{(restant ?? 0) > 1 ? 's' : ''}</span>
            <span className="hidden tab:inline">· {profil.formule.nom}</span>
          </Lien>
        )}
        {/* zone de clic de 44 px, pastille de 31 px (WCAG 2.5.5 ; audit du 2026-11-19, WEB-9) */}
        <Lien href="/compte" aria-label="Mon compte" title={profil?.email} className="group grid size-11 shrink-0 place-items-center rounded-full">
          <span className="grid size-[31px] place-items-center rounded-full bg-[#e9dfd0] text-[11px] font-bold text-[#694b31] group-hover:ring-2 group-hover:ring-[#d6c6ad]">
            {initiales}
          </span>
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
      className={`pointer-events-none fixed bottom-[calc(78px+env(safe-area-inset-bottom))] left-1/2 z-50 -translate-x-1/2 rounded-lg bg-[#263c31] px-4 py-[11px] text-[12px] text-white shadow-[0_8px_28px_#17241d33] transition tab:bottom-[22px]
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
