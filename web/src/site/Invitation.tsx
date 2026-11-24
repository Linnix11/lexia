// Beta fermee annoncee sur les pages publiques (D129) : tant que le serveur la declare (config.beta_fermee, D121),
// l'inscription exige un code d'acces. Les pages ne proposent donc plus « Creer un compte » mais « Demander une
// invitation », qui mene ici. Beta ouverte : les boutons restent ceux d'avant.
import type { ReactNode } from 'react'
import { Lien } from '../lib/router'
import { useSession } from '../state/session'
import { PublicLayout, Section, Surtitre, bouton, boutonSecondaire } from './Public'

/** Lien d'entree d'un visiteur : vers l'inscription, ou vers la demande d'invitation en beta fermee
 *  (seulement si la configuration lue sur le serveur l'annonce). */
export function LienInscription({ className, children = 'Créer un compte gratuit' }: { className?: string; children?: ReactNode }) {
  return useSession().config?.beta_fermee
    ? <Lien href="/invitation" className={className}>Demander une invitation</Lien>
    : <Lien href="/inscription" className={className}>{children}</Lien>
}

export function Invitation() {
  const { config, profil } = useSession()
  const contact = config?.contact_email
  const sujet = encodeURIComponent('Lexia - demande d’invitation à la bêta')

  if (config && !config.beta_fermee) {
    return (
      <PublicLayout>
        <Section className="max-w-[720px] py-14">
          <Surtitre>Inscription</Surtitre>
          <h1 className="mt-3 font-display text-[34px] leading-[1.1] font-normal">Les inscriptions sont ouvertes</h1>
          <p className="mt-3 text-[14px] leading-[1.6] text-muted">Aucun code n’est nécessaire : créez votre compte directement.</p>
          <div className="mt-6">
            <Lien href={profil ? '/app' : '/inscription'} className={bouton}>{profil ? 'Ouvrir mon espace' : 'Créer un compte gratuit'}</Lien>
          </div>
        </Section>
      </PublicLayout>
    )
  }

  return (
    <PublicLayout>
      <Section className="max-w-[720px] py-14">
        <Surtitre>Inscription</Surtitre>
        <h1 className="mt-3 font-display text-[34px] leading-[1.1] font-normal">Lexia est en bêta fermée</h1>
        <p className="mt-3 text-[14px] leading-[1.6] text-muted">
          Pendant la bêta, les comptes s’ouvrent sur invitation : chaque groupe d’étudiants invité reçoit un code
          d’accès, à saisir au moment de créer son compte. Les pages de matières et les guides de méthode restent
          lisibles sans compte.
        </p>
        <h2 className="mt-8 font-display text-[22px] font-normal">Demander une invitation</h2>
        <p className="mt-2 text-[14px] leading-[1.6]">
          Écrivez à{' '}
          {contact
            ? <a href={`mailto:${contact}?subject=${sujet}`} className="font-semibold text-forest underline">{contact}</a>
            : config
              // Pas d'adresse dans la configuration du serveur : encart pour l'editeur, comme les mentions legales
              ? <mark className="rounded bg-[#fbf0d9] px-1 text-[#7a5a1e]">[Adresse de contact pour les invitations : à compléter]</mark>
              : <>l’adresse de contact indiquée dans les <Lien href="/mentions-legales" className="underline">mentions légales</Lien></>}
          {' '}en précisant votre année de licence (L1, L2 ou L3). Si une place est disponible, vous recevez un code
          d’accès personnel.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Lien href="/inscription" className={bouton}>J’ai un code : créer mon compte</Lien>
          <Lien href="/matieres" className={boutonSecondaire}>Voir les matières</Lien>
        </div>
      </Section>
    </PublicLayout>
  )
}
