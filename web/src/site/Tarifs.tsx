import { VERSION_CGU } from '../lib/cgu'
import { useEffect, useState } from 'react'
import { api, type Formule } from '../lib/api'
import { Lien } from '../lib/router'
import { useSession } from '../state/session'
import { Payer } from './Payer'
import { formules as formulesDuDepot } from './donnees-publiques.json'
import { PublicLayout, Section, Surtitre, bouton, boutonSecondaire } from './Public'

/** Formules ecrites par `python -m api.donnees_publiques` (api/plans.py) : affichees avant la reponse de l'API. */
export const FORMULES_PUBLIQUES = formulesDuDepot as Formule[]

const prix = (f: Formule) =>
  f.prix_mensuel_euros === 0 ? '0 €' : `${f.prix_mensuel_euros.toFixed(2).replace('.', ',')} €`

export function Formules() {
  const { profil, config } = useSession()
  // Formules du depot d'abord (page prerendue, D116), puis celles du serveur, qui font foi
  const [formules, setFormules] = useState<Formule[] | null>(FORMULES_PUBLIQUES)
  const [erreur, setErreur] = useState(false)

  useEffect(() => {
    api.formules().then(setFormules).catch(() => setErreur(true))
  }, [])

  if (erreur && !formules) return <p className="text-[13px] text-muted">Les formules sont momentanément indisponibles.</p>
  if (!formules) {
    return (
      <div className="grid animate-pulse gap-4 tab:grid-cols-3" aria-label="Chargement des formules">
        {[0, 1, 2].map((i) => <div key={i} className="h-72 rounded-xl bg-[#ece9e0]" />)}
      </div>
    )
  }

  return (
    <div className="grid gap-4 tab:grid-cols-3">
      {formules.map((f) => {
        const actuelle = profil?.formule.id === f.id
        const miseEnAvant = f.id === 'etudiant'
        let action
        if (f.id === 'gratuit') {
          action = profil
            ? <Lien href="/app" className={boutonSecondaire}>{actuelle ? 'Votre formule actuelle' : 'Ouvrir mon espace'}</Lien>
            : <Lien href="/inscription" className={bouton}>Créer un compte</Lien>
        } else if (actuelle) {
          action = <span className={`${boutonSecondaire} cursor-default`}>Votre formule actuelle</span>
        } else if (config?.paiement) {
          action = <Payer formule={f} principal={miseEnAvant} />
        } else if (config?.contact_email) {
          const sujet = encodeURIComponent(`Lexia - formule ${f.nom}`)
          // Demande expresse d'acces immediat dans le corps du mail (C. consom. L. 221-25 ; audit du 2026-11-19, JUR-14) :
          // la formule n'est activee qu'apres reception de cette demande. L'etudiant peut la retirer avant d'envoyer.
          const corps = encodeURIComponent(`Bonjour,\n\nJe souhaite passer à la formule ${f.nom}.\nAdresse de mon compte Lexia : ${profil?.email ?? ''}\n\n`
            + 'Je demande l’accès immédiat à la formule. Si je me rétracte dans les 14 jours, je paierai la part de la période '
            + 'déjà écoulée. Je reconnais perdre mon droit de rétractation si la formule est entièrement exécutée avant la fin '
            + `de ce délai. J’accepte les conditions générales (version du ${VERSION_CGU}).\n`)
          action = (
            <>
              <a href={`mailto:${config.contact_email}?subject=${sujet}&body=${corps}`} className={miseEnAvant ? bouton : boutonSecondaire}>Demander cette formule</a>
              {/* Mention au plus pres du bouton (audit du 2026-11-16, point 15) : il ouvre un e-mail, rien n'est paye. */}
              <p className="mt-2 text-[12px] leading-[1.5] text-muted">Ouvre un e-mail de demande, avec votre demande d’accès immédiat. La formule est activée à la main après réception, sans paiement en ligne pour l’instant.</p>
            </>
          )
        } else {
          action = <span className={`${boutonSecondaire} cursor-default opacity-70`}>Bientôt disponible</span>
        }
        return (
          <article key={f.id}
            className={`flex flex-col rounded-xl border bg-surface p-6 ${miseEnAvant ? 'border-forest shadow-[0_12px_40px_#17241d14]' : 'border-line'}`}>
            <div className="flex items-center justify-between gap-2">
              <h3 className="font-display text-[22px]">{f.nom}</h3>
              {miseEnAvant && <span className="rounded-full bg-mint px-2.5 py-1 text-[11px] font-semibold text-forest">Recommandé</span>}
            </div>
            <p className="mt-1 min-h-[40px] text-[13px] text-muted">{f.description}</p>
            <p className="mt-4"><span className="font-display text-[34px]">{prix(f)}</span>{f.prix_mensuel_euros > 0 && <span className="text-[13px] text-muted"> / mois</span>}</p>
            <ul className="mt-4 mb-6 grid gap-2 text-[13px]">
              {f.avantages.map((a) => (
                <li key={a} className="flex gap-2"><span aria-hidden className="text-forest">✓</span>{a}</li>
              ))}
            </ul>
            <div className="mt-auto">{action}</div>
          </article>
        )
      })}
    </div>
  )
}

export function Tarifs() {
  const { config } = useSession()
  return (
    <PublicLayout>
      <Section className="py-14">
        <Surtitre>Tarifs</Surtitre>
        <h1 className="mt-3 font-display text-[36px] leading-[1.1] font-normal tracking-[-.6px]">Une formule pour chaque rythme de révision.</h1>
        <p className="mt-3 mb-8 max-w-[620px] text-[14px] leading-[1.6] text-muted">
          Toutes les formules donnent accès aux mêmes sources et aux mêmes garde-fous. Elles diffèrent par le nombre de
          questions et de questionnaires par jour, et par le nombre de cours que vous pouvez déposer. Les compteurs
          quotidiens se remettent à zéro chaque jour à minuit.
        </p>
        <Formules />
        <p className="mt-6 text-[12px] text-muted">
          Prix toutes taxes comprises, par mois.{' '}
          {config?.legal?.tva ?? <mark className="rounded bg-[#fbf0d9] px-1 text-[#7a5a1e]">[Mention TVA : à compléter]</mark>}{' '}
          Conditions de vente : <Lien href="/cgu" className="underline">conditions générales</Lien>, section 4.
        </p>
        <p className="mt-2 text-[12px] text-muted">
          {config?.paiement
            ? 'Paiement par carte sur la page sécurisée de Stripe : Lexia ne voit pas vos coordonnées bancaires. La formule s’active dès la confirmation du paiement.'
            : 'Le paiement en ligne arrive bientôt.'}{' '}
          Sans engagement.
        </p>
      </Section>
    </PublicLayout>
  )
}
