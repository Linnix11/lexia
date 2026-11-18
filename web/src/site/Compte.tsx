import { useEffect, useState, type FormEvent } from 'react'
import { api, ApiError, type EtatPaiement } from '../lib/api'
import { effacerFavoris } from '../lib/favoris'
import { Lien, useRouteur } from '../lib/router'
import { useSession } from '../state/session'
import { DoubleAuthentification } from './DoubleAuthentification'
import { CadreEspace } from '../components/Layout'
import { Surtitre, bouton, boutonSecondaire } from './Public'

function Jauge({ libelle, utilise, limite }: { libelle: string; utilise: number; limite: number }) {
  const pct = Math.min(100, Math.round((utilise / limite) * 100))
  return (
    <div>
      <div className="flex justify-between text-[13px]">
        <span>{libelle}</span>
        <span className="text-muted">{utilise} / {limite}</span>
      </div>
      <div className="mt-1.5 h-2 rounded-full bg-[#e7e4da]" role="progressbar" aria-label={libelle}
        aria-valuenow={utilise} aria-valuemin={0} aria-valuemax={limite}>
        <div className={`h-full rounded-full ${pct >= 100 ? 'bg-[#c2765f]' : 'bg-forest'}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

/** Retour de la page Stripe (/compte?paiement=ok) et retractation en ligne des achats de moins de 14 jours. */
function Paiement() {
  const { config, rafraichir } = useSession()
  const [retour] = useState(() => new URLSearchParams(window.location.search).get('paiement') === 'ok')
  const [etat, setEtat] = useState<EtatPaiement | null>(null)
  const [attente, setAttente] = useState(retour)
  const [confirmer, setConfirmer] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [erreur, setErreur] = useState<string | null>(null)
  const actif = Boolean(config?.paiement)

  // Au retour de Stripe, le signal de paiement arrive en general en quelques secondes : on le guette 20 s.
  useEffect(() => {
    if (!actif) return
    let essais = 0
    let minuteur: number | undefined
    let vivant = true
    const charger = async () => {
      let statut: string | undefined
      try {
        const e = await api.paiementEtat()
        if (!vivant) return
        setEtat(e)
        statut = e.dernier?.statut
        if (retour && statut === 'paye') await rafraichir()
      } catch {
        /* nouvel essai ci-dessous */
      }
      if (!vivant) return
      if (retour && (statut === undefined || statut === 'ouvert' || statut === 'en_attente') && ++essais < 10) {
        minuteur = window.setTimeout(charger, 2000)
      } else {
        setAttente(false)
      }
    }
    charger()
    return () => { vivant = false; window.clearTimeout(minuteur) }
  }, [actif, retour, rafraichir])

  if (!actif) return null
  const statut = etat?.dernier?.statut
  let annonce: string | null = null
  if (retour) {
    if (statut === 'paye') annonce = 'Paiement reçu : votre formule est active. La confirmation du contrat vous a été envoyée par e-mail.'
    else if (statut === 'a_rembourser' || statut === 'ecarte') annonce = 'Paiement reçu, mais la formule n’a pas pu être activée (une autre formule est en cours). Il vous sera remboursé intégralement ; un e-mail vous l’explique.'
    else if (attente) annonce = 'Paiement reçu, activation de votre formule en cours…'
    else annonce = 'Paiement reçu. La confirmation de Stripe tarde : la formule s’activera d’elle-même dans quelques minutes. Rechargez cette page plus tard.'
  }

  const retracter = async () => {
    setErreur(null)
    try {
      await api.retracter()
      setConfirmer(false)
      setEtat(await api.paiementEtat())
      await rafraichir()
      setMessage('Rétractation enregistrée. La formule est retirée et un accusé de réception vous a été envoyé par e-mail ; le remboursement suit dans les 14 jours.')
    } catch (e) {
      setErreur(e instanceof ApiError ? e.message : 'Rétractation impossible pour le moment : écrivez-nous.')
    }
  }

  return (
    <>
      {annonce && <p role="status" className="rounded-xl border border-forest bg-mint px-4 py-3 text-[13px] text-forest">{annonce}</p>}
      {(etat?.retractable || message) && (
        <section className="rounded-xl border border-line bg-surface p-5">
          <h2 className="text-[14px] font-semibold">Rétractation</h2>
          {message ? <p role="status" className="mt-1 text-[12px] leading-[1.6] text-forest">{message}</p> : (
            <>
              <p className="mt-1 text-[12px] leading-[1.6] text-muted">
                Vous avez souscrit il y a moins de 14 jours : vous pouvez vous rétracter sans motif et sans frais. La
                formule est retirée et le paiement vous est remboursé, déduction faite de la part de la période déjà
                écoulée (accès immédiat demandé).
              </p>
              {!confirmer ? (
                <button type="button" onClick={() => setConfirmer(true)} className={`${boutonSecondaire} mt-3`}>Me rétracter…</button>
              ) : (
                <div className="mt-3 flex flex-wrap gap-2">
                  <button type="button" onClick={retracter} className={bouton}>Confirmer ma rétractation</button>
                  <button type="button" onClick={() => setConfirmer(false)} className="px-2 py-2 text-[13px] text-muted">Annuler</button>
                </div>
              )}
            </>
          )}
          {erreur && <p role="alert" className="mt-2 text-[12px] text-[#8c4a36]">{erreur}</p>}
        </section>
      )}
    </>
  )
}

export function Compte() {
  const { profil, deconnexion, supprimer } = useSession()
  const { naviguer } = useRouteur()
  const [suppression, setSuppression] = useState(false)
  const [mdp, setMdp] = useState('')
  const [erreur, setErreur] = useState<string | null>(null)

  if (!profil) return null
  const f = profil.formule

  const sortir = async () => {
    await deconnexion()
    naviguer('/', { remplacer: true })
  }

  const confirmerSuppression = async (e: FormEvent) => {
    e.preventDefault()
    setErreur(null)
    try {
      const email = profil.email
      await supprimer(mdp)
      effacerFavoris(email) // poste partage : les fiches du compte ne restent pas dans le navigateur
      naviguer('/?compte-supprime=1', { remplacer: true })
    } catch (err) {
      setErreur(err instanceof ApiError ? err.message : 'Suppression impossible pour le moment.')
    }
  }

  return (
    <CadreEspace titre="Mon compte">
      <div className="mx-auto max-w-[760px]">
        <Surtitre>Mon compte</Surtitre>
        <h1 className="mt-2 mb-6 font-display text-[32px] font-normal">{profil.email}</h1>

        <div className="grid gap-4">
          <Paiement />
          <section className="rounded-xl border border-line bg-surface p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-[13px] text-muted">Formule</h2>
                <p className="font-display text-[24px]">{f.nom}</p>
                {profil.formule_fin && <p className="text-[12px] text-muted">Active jusqu’au {new Date(profil.formule_fin).toLocaleDateString('fr-FR')}</p>}
              </div>
              <Lien href="/tarifs" className={boutonSecondaire}>{f.id === 'intensif' ? 'Voir les formules' : 'Changer de formule'}</Lien>
            </div>
            <div className="mt-5 grid gap-4">
              <Jauge libelle="Questions aujourd’hui" utilise={profil.usage.questions} limite={f.questions_par_jour} />
              <Jauge libelle="Questionnaires aujourd’hui" utilise={profil.usage.quiz} limite={f.quiz_par_jour} />
            </div>
            <p className="mt-3 text-[12px] text-muted">Les compteurs se remettent à zéro chaque jour à minuit.</p>
          </section>

          <DoubleAuthentification />

          <section className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line bg-surface p-5">
            <div>
              <h2 className="text-[14px] font-semibold">Session</h2>
              <p className="text-[12px] text-muted">Compte créé le {new Date(profil.cree_le).toLocaleDateString('fr-FR')}.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {profil.admin && <Lien href="/admin" className={boutonSecondaire}>Administration</Lien>}
              <Lien href="/app" className={bouton}>Ouvrir mon espace</Lien>
              <button type="button" onClick={sortir} className={boutonSecondaire}>Se déconnecter</button>
            </div>
          </section>

          <section className="rounded-xl border border-[#ecd9c4] bg-cream p-5">
            <h2 className="text-[14px] font-semibold text-[#5f4f37]">Supprimer mon compte</h2>
            <p className="mt-1 text-[12px] leading-[1.6] text-[#746347]">
              Votre adresse e-mail, votre mot de passe, vos cours déposés et vos compteurs d’utilisation sont effacés
              définitivement, ainsi que les fiches enregistrées dans ce navigateur (celles d’un autre appareil y
              restent). Si vous avez payé une formule, la trace du paiement (date, formule, montant, adresse e-mail)
              est conservée dix ans, comme toute pièce comptable.
            </p>
            {!suppression ? (
              <button type="button" onClick={() => setSuppression(true)}
                className="mt-3 rounded-[8px] border border-[#c2765f] px-3 py-2 text-[13px] text-[#8c4a36] hover:bg-[#f6e9e4]">
                Supprimer mon compte…
              </button>
            ) : (
              <form onSubmit={confirmerSuppression} className="mt-3 flex flex-wrap items-end gap-2">
                <label className="grid gap-1 text-[12px] text-[#5f4f37]">
                  Mot de passe pour confirmer
                  <input type="password" autoComplete="current-password" autoFocus value={mdp} onChange={(e) => setMdp(e.target.value)}
                    className="rounded-[8px] border border-line bg-white px-3 py-2 text-[14px]" />
                </label>
                <button type="submit" disabled={!mdp} className="rounded-[8px] bg-[#8c4a36] px-3 py-2 text-[13px] text-white disabled:opacity-60">
                  Supprimer définitivement le compte {profil.email}
                </button>
                <button type="button" onClick={() => { setSuppression(false); setMdp(''); setErreur(null) }} className="px-2 py-2 text-[13px] text-muted">
                  Annuler
                </button>
                {erreur && <p role="alert" className="w-full text-[12px] text-[#8c4a36]">{erreur}</p>}
              </form>
            )}
          </section>
        </div>
      </div>
    </CadreEspace>
  )
}
