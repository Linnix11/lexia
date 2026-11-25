import type { ReactNode } from 'react'
import { Lien } from '../lib/router'
import { useSession } from '../state/session'
import { LogoHorizontal, Signet } from '../components/Logo'
import { betaFermee } from './beta'

export const bouton = 'inline-flex items-center justify-center rounded-[8px] bg-forest px-4 py-2.5 text-[13px] font-medium text-white hover:bg-forest-dark disabled:opacity-60'
export const boutonSecondaire = 'inline-flex items-center justify-center rounded-[8px] border border-line bg-surface px-4 py-2.5 text-[13px] text-forest hover:border-[#9eafa3]'

function Logo() {
  return (
    <Lien href="/" className="flex min-h-11 min-w-11 items-center gap-2.5" aria-label="Lexia, accueil">
      {/* Symbole seul sur un ecran etroit (375 px : la navigation a besoin de la place), logo complet au-dela */}
      <Signet hauteur={36} className="min-[400px]:hidden" />
      <LogoHorizontal hauteur={45} className="hidden min-[400px]:block" />
    </Lien>
  )
}

export function PublicLayout({ children }: { children: ReactNode }) {
  const { profil, config } = useSession()
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-line bg-surface/70">
        <div className="mx-auto flex h-16 max-w-[1100px] items-center justify-between gap-2 px-4 tab:px-6">
          <Logo />
          <nav aria-label="Navigation du site" className="flex items-center gap-1 tab:gap-3">
            {/* Matieres et guides : en-tete a partir de la tablette, pied de page partout (D116) */}
            <Lien href="/matieres" className="hidden min-h-11 items-center rounded-md px-2 text-[13px] whitespace-nowrap text-[#505b54] hover:text-forest tab:inline-flex">Matières</Lien>
            <Lien href="/guides" className="hidden min-h-11 items-center rounded-md px-2 text-[13px] whitespace-nowrap text-[#505b54] hover:text-forest tab:inline-flex">Guides</Lien>
            <Lien href="/tarifs" className="inline-flex min-h-11 items-center rounded-md px-1.5 text-[13px] whitespace-nowrap text-[#505b54] hover:text-forest tab:px-2">Tarifs</Lien>
            {profil ? (
              <Lien href="/app" className={`${bouton} whitespace-nowrap`}>
                <span className="tab:hidden">Mon espace</span><span className="hidden tab:inline">Ouvrir mon espace</span>
              </Lien>
            ) : (
              <>
                <Lien href="/connexion" className="inline-flex min-h-11 items-center rounded-md px-1.5 text-[13px] whitespace-nowrap text-[#505b54] hover:text-forest tab:px-2">Connexion</Lien>
                {betaFermee(config) ? (
                  // Beta fermee : l'inscription exige un code, l'en-tete mene a la demande d'invitation (D129)
                  <Lien href="/invitation" className={`${bouton} whitespace-nowrap`}>
                    <span className="tab:hidden">Invitation</span><span className="hidden tab:inline">Demander une invitation</span>
                  </Lien>
                ) : (
                  <Lien href="/inscription" className={`${bouton} whitespace-nowrap`}>
                    <span className="tab:hidden">S’inscrire</span><span className="hidden tab:inline">Créer un compte</span>
                  </Lien>
                )}
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="flex-1">{children}</main>
      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-[1100px] flex-col gap-3 px-4 py-6 text-[12px] text-muted tab:flex-row tab:items-center tab:justify-between tab:px-6">
          <span>Lexia · outil d’étude du droit français, pas un avis juridique.</span>
          <nav aria-label="Découvrir Lexia" className="flex flex-wrap gap-x-4 gap-y-1">
            <Lien href="/matieres" className="inline-flex min-h-11 items-center hover:text-forest tab:min-h-0">Matières</Lien>
            <Lien href="/guides" className="inline-flex min-h-11 items-center hover:text-forest tab:min-h-0">Guides de méthode</Lien>
            <Lien href="/tarifs" className="inline-flex min-h-11 items-center hover:text-forest tab:min-h-0">Tarifs</Lien>
          </nav>
          <nav aria-label="Informations légales" className="flex flex-wrap gap-x-4 gap-y-1">
            {/* liens de 44 px de haut sur mobile (WEB-9) */}
            <Lien href="/mentions-legales" className="inline-flex min-h-11 items-center hover:text-forest tab:min-h-0">Mentions légales</Lien>
            <Lien href="/cgu" className="inline-flex min-h-11 items-center hover:text-forest tab:min-h-0">Conditions d’utilisation</Lien>
            <Lien href="/confidentialite" className="inline-flex min-h-11 items-center hover:text-forest tab:min-h-0">Confidentialité</Lien>
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
