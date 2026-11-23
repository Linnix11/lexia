import { useEffect, useRef, useState, type FormEvent } from 'react'
import { api, ApiError, type EtatPaiement } from '../lib/api'
import { effacerCartes } from '../lib/cartes'
import { effacerFavoris } from '../lib/favoris'
import { effacerCartesMentales } from '../lib/cartesEnregistrees'
import { telecharger } from '../lib/exportFiches'
import { effacerSemestre } from '../lib/semestres'
import { effacerDerniereMatiere, NOM_MAX, PRENOM_MAX } from '../lib/personnalisation'
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

const NOMS: Record<string, string> = { etudiant: 'Étudiant', intensif: 'Intensif' }
const prix = (centimes: number) => `${(centimes / 100).toFixed(2).replace('.', ',')} €`

/** Fin du delai la plus lointaine des achats retractables, prorogee par le serveur au premier jour ouvrable. */
function finDelai(achats: { fin?: string }[] | undefined): string {
  const fins = (achats ?? []).map((a) => a.fin).filter((f): f is string => Boolean(f)).sort()
  if (!fins.length) return 'la fin du délai de 14 jours'
  const [a, m, j] = fins[fins.length - 1].split('-').map(Number)
  return new Date(a, m - 1, j).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })
}

/** Retour de la page Stripe (/compte?paiement=ok) et retractation en ligne des achats de moins de 14 jours. */
function Paiement() {
  const { config, profil, rafraichir } = useSession()
  const [retour] = useState(() => new URLSearchParams(window.location.search).get('paiement') === 'ok')
  const [etat, setEtat] = useState<EtatPaiement | null>(null)
  const [attente, setAttente] = useState(retour)
  const [declaration, setDeclaration] = useState(false)
  // pre-rempli avec le prenom et le nom du compte, modifiable (la declaration reste celle de l'etudiant)
  const [nom, setNom] = useState(() => [profil?.prenom, profil?.nom].filter(Boolean).join(' '))
  const [choisis, setChoisis] = useState<string[]>([])
  const [message, setMessage] = useState<string | null>(null)
  const [erreur, setErreur] = useState<string | null>(null)
  const actif = Boolean(config?.paiement)
  // Le bouton « Renoncer » disparait a l'ouverture : focus sur le premier champ, puis retour au bouton si l'on
  // annule, jamais sur <body> (recette du 2026-11-20, D-4).
  const champNom = useRef<HTMLInputElement>(null)
  const boutonRenoncer = useRef<HTMLButtonElement>(null)
  const dejaOuvert = useRef(false)
  useEffect(() => {
    if (declaration) champNom.current?.focus()
    else if (dejaOuvert.current) boutonRenoncer.current?.focus()
    dejaOuvert.current ||= declaration
  }, [declaration])

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

  const ouvrir = () => {
    setChoisis(etat?.retractables.map((a) => a.session) ?? [])
    setDeclaration(true)
  }
  const basculer = (session: string) =>
    setChoisis((c) => (c.includes(session) ? c.filter((s) => s !== session) : [...c, session]))

  const retracter = async (e: FormEvent) => {
    e.preventDefault()
    setErreur(null)
    try {
      const r = await api.retracter(nom, choisis)
      setDeclaration(false)
      // Message exact : l'accuse est parti, ou il sera renvoye (audit du 2026-11-19, JUR-7)
      const le = new Date(r.le)
      const quand = `le ${le.toLocaleDateString('fr-FR', { timeZone: 'Europe/Paris' })} à ${le.toLocaleTimeString('fr-FR', { timeZone: 'Europe/Paris', hour: '2-digit', minute: '2-digit' })}`
      setMessage(r.accuse_envoye
        ? `Rétractation enregistrée ${quand}. La formule est retirée et un accusé de réception vous a été envoyé par e-mail ; le remboursement suit dans les 14 jours.`
        : `Rétractation enregistrée ${quand} : la formule est retirée et le remboursement suit dans les 14 jours. L’accusé de réception n’a pas pu partir pour l’instant ; il vous sera renvoyé automatiquement par e-mail. Votre rétractation est valable dès maintenant.`)
      try {
        setEtat(await api.paiementEtat())
        await rafraichir()
      } catch {
        /* la retractation est faite : l'etat se mettra a jour au prochain chargement */
      }
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
                Vous pouvez vous rétracter sans motif jusqu’au {finDelai(etat?.retractables)} inclus. La formule est
                retirée et le paiement vous est remboursé, déduction faite de la part de la période déjà écoulée,
                puisque vous avez demandé l’accès immédiat ; aucun autre frais.
              </p>
              {!declaration ? (
                <button ref={boutonRenoncer} type="button" onClick={ouvrir} className={`${boutonSecondaire} mt-3`}>Renoncer au contrat ici</button>
              ) : (
                // Declaration de retractation en ligne : nom et prenom, contrat vise, adresse de l'accuse (D. 221-5)
                <form onSubmit={retracter} className="mt-3 grid gap-3 text-[13px]">
                  <label className="grid gap-1 text-[12px]">
                    Nom et prénom
                    <input ref={champNom} value={nom} onChange={(e) => setNom(e.target.value)} autoComplete="name" required
                      className="max-w-[360px] rounded-[8px] border border-line bg-white px-3 py-2 text-[14px]" />
                  </label>
                  <fieldset className="grid gap-1">
                    <legend className="text-[12px]">Contrat dont vous vous rétractez</legend>
                    {etat?.retractables.map((a) => (
                      <label key={a.session} className="flex gap-2">
                        <input type="checkbox" checked={choisis.includes(a.session)} onChange={() => basculer(a.session)}
                          className="accent-forest" />
                        Formule {NOMS[a.formule] ?? a.formule}, {a.mois} mois, {prix(a.montant_centimes)}, payée le{' '}
                        {new Date(a.paye_le).toLocaleDateString('fr-FR', { timeZone: 'Europe/Paris' })}
                      </label>
                    ))}
                  </fieldset>
                  <p className="text-[12px] text-muted">L’accusé de réception sera envoyé par e-mail à {profil?.email}.</p>
                  <div className="flex flex-wrap gap-2">
                    <button type="submit" disabled={nom.trim().length < 2 || choisis.length === 0} className={`${bouton} disabled:opacity-60`}>
                      Confirmer la rétractation
                    </button>
                    <button type="button" onClick={() => setDeclaration(false)} className="px-2 py-2 text-[13px] text-muted">Annuler</button>
                  </div>
                </form>
              )}
            </>
          )}
          {erreur && <p role="alert" className="mt-2 text-[12px] text-[#8c4a36]">{erreur}</p>}
        </section>
      )}
    </>
  )
}

/** Export des donnees du compte au format JSON (RGPD art. 15 et 20 ; audit du 2026-11-19, JUR-11). */
function MesDonnees() {
  const [etat, setEtat] = useState<'libre' | 'envoi' | 'erreur'>('libre')
  const exporter = async () => {
    setEtat('envoi')
    try {
      const donnees = await api.exporterDonnees()
      telecharger('lexia-mes-donnees.json', JSON.stringify(donnees, null, 2), 'application/json;charset=utf-8')
      setEtat('libre')
    } catch {
      setEtat('erreur')
    }
  }
  return (
    <section className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line bg-surface p-5">
      <div className="max-w-[460px]">
        <h2 className="text-[14px] font-semibold">Mes données</h2>
        <p className="mt-1 text-[12px] leading-[1.6] text-muted">
          Un fichier JSON avec votre compte, vos compteurs, le texte de vos cours déposés et vos paiements. Vos fiches
          restent dans ce navigateur : exportez-les depuis « Fiches & révisions ».
        </p>
        {etat === 'erreur' && <p role="alert" className="mt-1 text-[12px] text-[#8c4a36]">Export impossible pour le moment. Réessayez.</p>}
      </div>
      <button type="button" onClick={exporter} disabled={etat === 'envoi'} className={boutonSecondaire}>
        {etat === 'envoi' ? 'Préparation…' : 'Télécharger mes données'}
      </button>
    </section>
  )
}

/** Prenom et nom (D100, D102) : modifiables, jamais vides une fois enregistres. */
function Identite() {
  const { profil, majProfil } = useSession()
  const [prenom, setPrenom] = useState(profil?.prenom ?? '')
  const [nom, setNom] = useState(profil?.nom ?? '')
  const [message, setMessage] = useState<string | null>(null)
  const [erreur, setErreur] = useState<string | null>(null)
  const [envoi, setEnvoi] = useState(false)
  const inchange = prenom.trim() === (profil?.prenom ?? '') && nom.trim() === (profil?.nom ?? '')
  const champ = 'max-w-[260px] rounded-[8px] border border-line bg-white px-3 py-2 text-[14px]'

  const enregistrer = async (e: FormEvent) => {
    e.preventDefault()
    setErreur(null)
    setMessage(null)
    setEnvoi(true)
    try {
      const p = await api.changerIdentite(prenom, nom)
      majProfil(p)
      setPrenom(p.prenom ?? '')
      setNom(p.nom ?? '')
      setMessage('Prénom et nom enregistrés.')
    } catch (err) {
      setErreur(err instanceof ApiError ? err.message : 'Enregistrement impossible pour le moment.')
    } finally {
      setEnvoi(false)
    }
  }

  return (
    <section className="rounded-xl border border-line bg-surface p-5">
      <h2 className="text-[14px] font-semibold">Prénom et nom</h2>
      <p className="mt-1 text-[12px] leading-[1.6] text-muted">
        Votre prénom sert à vous saluer dans votre espace. Ni votre prénom ni votre nom ne sont transmis à l’IA ni
        utilisés dans les e-mails. Le nom indiqué dans une déclaration de rétractation figure dans son accusé de
        réception et reste avec le paiement.
      </p>
      <form onSubmit={enregistrer} className="mt-3 flex flex-wrap items-end gap-2">
        <label className="grid gap-1 text-[12px]">
          Prénom
          <input value={prenom} maxLength={PRENOM_MAX} autoComplete="given-name" onChange={(e) => setPrenom(e.target.value)} className={champ} />
        </label>
        <label className="grid gap-1 text-[12px]">
          Nom
          <input value={nom} maxLength={NOM_MAX} autoComplete="family-name" onChange={(e) => setNom(e.target.value)} className={champ} />
        </label>
        <button type="submit" disabled={envoi || inchange || !prenom.trim() || !nom.trim()} className={`${boutonSecondaire} disabled:opacity-60`}>
          {envoi ? 'Enregistrement…' : 'Enregistrer'}
        </button>
        {message && <p role="status" className="w-full text-[12px] text-forest">{message}</p>}
        {erreur && <p role="alert" className="w-full text-[12px] text-[#8c4a36]">{erreur}</p>}
      </form>
    </section>
  )
}

/** Consentement aux e-mails d'information : aussi simple a retirer qu'a donner (RGPD, article 7.3). */
function InfosEmail() {
  const { profil, majProfil } = useSession()
  const [erreur, setErreur] = useState<string | null>(null)
  const [envoi, setEnvoi] = useState(false)
  if (!profil) return null
  const changer = async (accepte: boolean) => {
    setErreur(null)
    setEnvoi(true)
    try {
      majProfil(await api.changerInfosEmail(accepte))
    } catch (err) {
      setErreur(err instanceof ApiError ? err.message : 'Modification impossible pour le moment.')
    } finally {
      setEnvoi(false)
    }
  }
  return (
    <section className="rounded-xl border border-line bg-surface p-5">
      <h2 className="text-[14px] font-semibold">E-mails d’information</h2>
      <label className="mt-2 flex items-start gap-2 text-[13px] leading-[1.5]">
        <input type="checkbox" checked={!!profil.infos_email} disabled={envoi} onChange={(e) => changer(e.target.checked)}
          className="mt-1 accent-forest" />
        <span>Recevoir les nouveautés de Lexia par e-mail, quelques fois par an. Les e-mails liés à votre compte
          (confirmation d’adresse, mot de passe, paiement) partent dans tous les cas.</span>
      </label>
      {erreur && <p role="alert" className="mt-2 text-[12px] text-[#8c4a36]">{erreur}</p>}
    </section>
  )
}

export function Compte() {
  const { profil, deconnexion, supprimer } = useSession()
  const { naviguer } = useRouteur()
  const [suppression, setSuppression] = useState(false)
  const [mdp, setMdp] = useState('')
  const [code, setCode] = useState('') // exige quand la double authentification est active (SEC-6)
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
      await supprimer(mdp, code)
      effacerFavoris(email) // poste partage : les fiches du compte ne restent pas dans le navigateur
      effacerCartes(email)
      effacerCartesMentales(email)
      effacerSemestre(email)
      effacerDerniereMatiere(email)
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

          <Identite />

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

          <InfosEmail />

          <MesDonnees />

          <section className="rounded-xl border border-[#ecd9c4] bg-cream p-5">
            <h2 className="text-[14px] font-semibold text-[#5f4f37]">Supprimer mon compte</h2>
            <p className="mt-1 text-[12px] leading-[1.6] text-[#746347]">
              Votre adresse e-mail, vos prénom et nom, votre mot de passe, vos cours déposés et vos compteurs d’utilisation
              sont effacés définitivement, ainsi que les fiches et la dernière matière enregistrées dans ce navigateur
              (celles d’un autre appareil y restent). Si vous avez payé une formule, la trace du paiement (date, formule, montant, adresse e-mail,
              et le nom d’une éventuelle déclaration de rétractation) est conservée dix ans, comme toute pièce comptable.
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
                {profil.double_authentification && (
                  <label className="grid gap-1 text-[12px] text-[#5f4f37]">
                    Code de l’application (ou code de secours)
                    <input inputMode="numeric" autoComplete="one-time-code" value={code} onChange={(e) => setCode(e.target.value)}
                      className="w-40 rounded-[8px] border border-line bg-white px-3 py-2 text-[14px]" />
                  </label>
                )}
                <button type="submit" disabled={!mdp || (!!profil.double_authentification && !code.trim())}
                  className="rounded-[8px] bg-[#8c4a36] px-3 py-2 text-[13px] text-white disabled:opacity-60">
                  Supprimer définitivement le compte {profil.email}
                </button>
                <button type="button" onClick={() => { setSuppression(false); setMdp(''); setCode(''); setErreur(null) }} className="px-2 py-2 text-[13px] text-muted">
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
