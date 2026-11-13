import type { ReactNode } from 'react'
import { Lien } from '../lib/router'
import { useSession } from '../state/session'
import { Signet } from '../components/Logo'

export const bouton = 'inline-flex items-center justify-center rounded-[8px] bg-forest px-4 py-2.5 text-[13px] font-medium text-white hover:bg-forest-dark disabled:opacity-60'
export const boutonSecondaire = 'inline-flex items-center justify-center rounded-[8px] border border-line bg-surface px-4 py-2.5 text-[13px] text-forest hover:border-[#9eafa3]'

function Logo() {
  return (
    <Lien href="/" className="flex items-center gap-2.5" aria-label="Lexia, accueil">
      <Signet hauteur={34} />
      <span className="hidden font-display text-[21px] tracking-[-.4px] min-[400px]:inline">lexia</span>
    </Lien>
  )
}

export function PublicLayout({ children }: { children: ReactNode }) {
  const { profil } = useSession()
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-line bg-surface/70">
        <div className="mx-auto flex h-16 max-w-[1100px] items-center justify-between gap-2 px-4 tab:px-6">
          <Logo />
          <nav aria-label="Navigation du site" className="flex items-center gap-1 tab:gap-3">
            <Lien href="/tarifs" className="rounded-md px-1.5 py-1.5 text-[13px] whitespace-nowrap text-[#505b54] hover:text-forest tab:px-2">Tarifs</Lien>
            {profil ? (
              <Lien href="/app" className={`${bouton} whitespace-nowrap`}>
                <span className="tab:hidden">Mon espace</span><span className="hidden tab:inline">Ouvrir mon espace</span>
              </Lien>
            ) : (
              <>
                <Lien href="/connexion" className="rounded-md px-1.5 py-1.5 text-[13px] whitespace-nowrap text-[#505b54] hover:text-forest tab:px-2">Connexion</Lien>
                <Lien href="/inscription" className={`${bouton} whitespace-nowrap`}>
                  <span className="tab:hidden">S’inscrire</span><span className="hidden tab:inline">Créer un compte</span>
                </Lien>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="flex-1">{children}</main>
      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-[1100px] flex-col gap-3 px-4 py-6 text-[12px] text-muted tab:flex-row tab:items-center tab:justify-between tab:px-6">
          <span>Lexia · outil d’étude du droit français, pas un avis juridique.</span>
          <nav aria-label="Informations légales" className="flex flex-wrap gap-x-4 gap-y-1">
            <Lien href="/mentions-legales" className="hover:text-forest">Mentions légales</Lien>
            <Lien href="/cgu" className="hover:text-forest">Conditions d’utilisation</Lien>
            <Lien href="/confidentialite" className="hover:text-forest">Confidentialité</Lien>
          </nav>
        </div>
      </footer>
    </div>
  )
}

export function Section({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`mx-auto max-w-[1100px] px-4 tab:px-6 ${className}`}>{children}</section>
}

export function Surtitre({ children }: { children: ReactNode }) {
  return <div className="text-[11px] font-bold tracking-[1.6px] text-forest uppercase">{children}</div>
}
