import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { api, ApiError, ORIGINES, type Origine } from '../lib/api'
import { VERSION_CGU } from '../lib/cgu'
import { NOM_MAX, PRENOM_MAX } from '../lib/personnalisation'
import { Lien, suiteSure, useRouteur } from '../lib/router'
import { useSession } from '../state/session'
import { PublicLayout, bouton } from './Public'

export const champ = 'w-full rounded-[8px] border border-line bg-white px-3 py-2.5 text-[14px] text-ink aria-[invalid=true]:border-[#c2765f]'
export const MDP_MIN = 10

export function Carte({ titre, sousTitre, children }: { titre: string; sousTitre: string; children: ReactNode }) {
  return (
    <PublicLayout>
      <div className="mx-auto max-w-[420px] px-4 py-14">
        <h1 className="font-display text-[30px] font-normal">{titre}</h1>
        <p className="mt-1.5 mb-6 text-[13px] text-muted">{sousTitre}</p>
        <div className="rounded-xl border border-line bg-surface p-6">{children}</div>
      </div>
    </PublicLayout>
  )
}

export function Erreur({ message }: { message: string | null }) {
  if (!message) return null
  return <p role="alert" className="rounded-lg bg-[#f6e9e4] px-3 py-2 text-[13px] text-[#8c4a36]">{message}</p>
}

export function Connexion() {
  const { connexion, terminerConnexion } = useSession()
  const { naviguer } = useRouteur()
  const [email, setEmail] = useState('')
  const [mdp, setMdp] = useState('')
  const [jeton, setJeton] = useState<string | null>(null) // double authentification : code a saisir
  const [code, setCode] = useState('')
  const [erreur, setErreur] = useState<string | null>(null)
  const [envoi, setEnvoi] = useState(false)
  const expiree = new URLSearchParams(window.location.search).has('expiree')
  // Retour a la page demandee avant la connexion (WEB-11)
  const suite = suiteSure(new URLSearchParams(window.location.search).get('suite'))

  const soumettre = async (e: FormEvent) => {
    e.preventDefault()
    // Bouton actif champs vides : la raison est dite au clic (WEB-10 ; audit du 2026-11-23, D8)
    if (!email.trim() || !mdp) return setErreur('Saisissez votre adresse e-mail et votre mot de passe.')
    setErreur(null)
    setEnvoi(true)
    try {
      const r = await connexion(email, mdp)
      if ('jeton' in r) setJeton(r.jeton)
      else naviguer(suite, { remplacer: true })
    } catch (err) {
      setErreur(err instanceof ApiError ? err.message : 'Connexion impossible pour le moment.')
    } finally {
      setEnvoi(false)
    }
  }

  const soumettreCode = async (e: FormEvent) => {
    e.preventDefault()
    if (!jeton) return
    setErreur(null)
    setEnvoi(true)
    try {
      await terminerConnexion(jeton, code)
      naviguer(suite, { remplacer: true })
    } catch (err) {
      setErreur(err instanceof ApiError ? err.message : 'Vérification impossible pour le moment.')
      if (err instanceof ApiError && err.message.includes('reconnectez')) setJeton(null)
    } finally {
      setEnvoi(false)
    }
  }

  if (jeton) {
    return (
      <Carte titre="Code de vérification" sousTitre="Ouvrez votre application d’authentification et saisissez le code à 6 chiffres affiché pour Lexia.">
        <form onSubmit={soumettreCode} className="grid gap-4" noValidate>
          <label className="grid gap-1.5 text-[13px]">
            Code de l’application (ou code de secours)
            <input autoFocus inputMode="numeric" autoComplete="one-time-code" required value={code} maxLength={12}
              onChange={(e) => setCode(e.target.value)} className={`${champ} tracking-[3px]`} />
          </label>
          <Erreur message={erreur} />
          <button type="submit" disabled={envoi || code.trim().length < 6} className={bouton}>{envoi ? 'Vérification…' : 'Valider'}</button>
        </form>
        <button type="button" onClick={() => { setJeton(null); setCode(''); setErreur(null) }}
          className="mt-4 text-[12px] text-muted hover:text-forest">← Revenir à l’e-mail et au mot de passe</button>
      </Carte>
    )
  }

  return (
    <Carte titre="Connexion" sousTitre="Retrouvez votre espace d’étude.">
      {expiree && <p className="mb-4 rounded-lg bg-cream px-3 py-2 text-[13px] text-[#746347]">Votre session a expiré : reconnectez-vous.</p>}
      <form onSubmit={soumettre} className="grid gap-4" noValidate>
        <label className="grid gap-1.5 text-[13px]">
          Adresse e-mail
          <input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={champ} />
        </label>
        <label className="grid gap-1.5 text-[13px]">
          Mot de passe
          <input type="password" autoComplete="current-password" required value={mdp} onChange={(e) => setMdp(e.target.value)} className={champ} />
        </label>
        <Erreur message={erreur} />
        <button type="submit" disabled={envoi} className={bouton}>{envoi ? 'Connexion…' : 'Se connecter'}</button>
      </form>
      <p className="mt-3 text-center text-[12px] text-muted">
        <Lien href="/mot-de-passe-oublie" className="text-forest hover:underline">Mot de passe oublié ?</Lien>
      </p>
      <p className="mt-5 text-center text-[13px] text-muted">
        Pas encore de compte ? <Lien href="/inscription" className="font-semibold text-forest hover:underline">Créer un compte gratuit</Lien>
      </p>
    </Carte>
  )
}

export function Inscription() {
  const { inscription } = useSession()
  const { naviguer } = useRouteur()
  const [email, setEmail] = useState('')
  const [prenom, setPrenom] = useState('') // prenom et nom demandes a l'inscription (D102)
  const [nom, setNom] = useState('')
  const [mdp, setMdp] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [cgu, setCgu] = useState(false)
  const [age, setAge] = useState(false) // CGU, article 3 : compte reserve aux 15 ans et plus
  // Case distincte et non cochee : le consentement aux e-mails d'information ne conditionne pas le compte
  const [infos, setInfos] = useState(false)
  const [origine, setOrigine] = useState<Origine | ''>('') // facultatif
  const [touche, setTouche] = useState<Record<string, boolean>>({})
  const [erreur, setErreur] = useState<string | null>(null)
  const [envoi, setEnvoi] = useState(false)
  // Limites de la formule gratuite lues sur le serveur, jamais ecrites en dur (audit du 2026-11-19, WEB-17)
  const [gratuit, setGratuit] = useState<string>('Formule gratuite, sans carte bancaire.')
  useEffect(() => {
    let actif = true
    api.formules().then((fs) => {
      const g = fs.find((f) => f.prix_mensuel_euros === 0)
      if (actif && g) setGratuit(`Gratuit : ${g.questions_par_jour} questions et ${g.quiz_par_jour} questionnaire${g.quiz_par_jour > 1 ? 's' : ''} par jour.`)
    }).catch(() => undefined)
    return () => { actif = false }
  }, [])

  const erreurs = {
    prenom: prenom.trim() ? null : 'Indiquez votre prénom.',
    nom: nom.trim() ? null : 'Indiquez votre nom.',
    email: /^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(email.trim()) ? null : 'Adresse e-mail invalide.',
    mdp: mdp.length >= MDP_MIN ? null : `Au moins ${MDP_MIN} caractères.`,
    confirmation: confirmation === mdp ? null : 'Les deux mots de passe ne correspondent pas.',
    cases: age && cgu ? null : 'Cochez les deux cases ci-dessus pour créer votre compte.',
  }
  const valide = !erreurs.prenom && !erreurs.nom && !erreurs.email && !erreurs.mdp && !erreurs.confirmation && cgu && age
  const montre = (k: keyof typeof erreurs) => (touche[k] ? erreurs[k] : null)
  const quitter = (k: string) => () => setTouche((t) => ({ ...t, [k]: true }))

  const soumettre = async (e: FormEvent) => {
    e.preventDefault()
    setTouche({ prenom: true, nom: true, email: true, mdp: true, confirmation: true, cases: true })
    if (!valide) {
      // focus sur le premier champ en erreur, une fois les messages affiches
      setTimeout(() => document.querySelector<HTMLElement>('form [aria-invalid="true"]')?.focus(), 0)
      return
    }
    setErreur(null)
    setEnvoi(true)
    try {
      // Case d'age et version des CGU enregistrees avec le compte (note de l'editeur du 2026-11-20, point 1)
      await inscription(email, mdp, cgu, prenom, nom,
        { age_atteste: age, cgu_version: VERSION_CGU, infos_email: infos, origine: origine || null })
      naviguer('/app', { remplacer: true })
    } catch (err) {
      setErreur(err instanceof ApiError ? err.message : 'Inscription impossible pour le moment.')
    } finally {
      setEnvoi(false)
    }
  }

  const aide = (id: string, msg: string | null) => msg && <span id={id} className="text-[12px] text-[#8c4a36]">{msg}</span>

  return (
    <Carte titre="Créer un compte" sousTitre={gratuit}>
      <form onSubmit={soumettre} className="grid gap-4" noValidate>
        <div className="grid gap-4 min-[420px]:grid-cols-2">
          <label className="grid content-start gap-1.5 text-[13px]">
            Prénom
            <input autoComplete="given-name" value={prenom} maxLength={PRENOM_MAX} onChange={(e) => setPrenom(e.target.value)}
              onBlur={quitter('prenom')} aria-invalid={!!montre('prenom')} aria-describedby="err-prenom aide-identite" className={champ} />
            {aide('err-prenom', montre('prenom'))}
          </label>
          <label className="grid content-start gap-1.5 text-[13px]">
            Nom
            <input autoComplete="family-name" value={nom} maxLength={NOM_MAX} onChange={(e) => setNom(e.target.value)}
              onBlur={quitter('nom')} aria-invalid={!!montre('nom')} aria-describedby="err-nom aide-identite" className={champ} />
            {aide('err-nom', montre('nom'))}
          </label>
          <span id="aide-identite" className="-mt-2 text-[12px] text-muted min-[420px]:col-span-2">
            Votre prénom sert à vous saluer dans votre espace. Ni votre prénom ni votre nom ne sont transmis à l’IA.
          </span>
        </div>
        <label className="grid gap-1.5 text-[13px]">
          Adresse e-mail
          <input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} onBlur={quitter('email')}
            aria-invalid={!!montre('email')} aria-describedby="err-email" className={champ} />
          {aide('err-email', montre('email'))}
        </label>
        <label className="grid gap-1.5 text-[13px]">
          Mot de passe <span className="text-[12px] text-muted">{MDP_MIN} caractères minimum</span>
          <input type="password" autoComplete="new-password" value={mdp} onChange={(e) => setMdp(e.target.value)} onBlur={quitter('mdp')}
            aria-invalid={!!montre('mdp')} aria-describedby="err-mdp" className={champ} />
          {aide('err-mdp', montre('mdp'))}
        </label>
        <label className="grid gap-1.5 text-[13px]">
          Confirmez le mot de passe
          <input type="password" autoComplete="new-password" value={confirmation} onChange={(e) => setConfirmation(e.target.value)}
            onBlur={quitter('confirmation')} aria-invalid={!!montre('confirmation')} aria-describedby="err-conf" className={champ} />
          {aide('err-conf', montre('confirmation'))}
        </label>
        <label className="flex items-start gap-2 text-[13px] leading-[1.5]">
          <input type="checkbox" checked={age} onChange={(e) => setAge(e.target.checked)} className="mt-1 accent-forest" />
          <span>J’ai 15 ans ou plus.</span>
        </label>
        <label className="flex items-start gap-2 text-[13px] leading-[1.5]">
          <input type="checkbox" checked={cgu} onChange={(e) => setCgu(e.target.checked)} className="mt-1 accent-forest" />
          <span>
            J’accepte les <Lien href="/cgu" target="_blank" className="text-forest underline">conditions d’utilisation</Lien> et
            j’ai lu la <Lien href="/confidentialite" target="_blank" className="text-forest underline">politique de confidentialité</Lien>.
          </span>
        </label>
        {aide('err-cases', montre('cases'))}
        <label className="flex items-start gap-2 text-[13px] leading-[1.5]">
          <input type="checkbox" checked={infos} onChange={(e) => setInfos(e.target.checked)} className="mt-1 accent-forest" />
          <span>
            J’accepte de recevoir les e-mails d’information de Lexia (nouveautés, quelques fois par an). Facultatif,
            modifiable à tout moment dans « Mon compte ».
          </span>
        </label>
        <label className="grid gap-1.5 text-[13px]">
          Comment avez-vous connu Lexia ? <span className="text-[12px] text-muted">Facultatif</span>
          <select value={origine} onChange={(e) => setOrigine(e.target.value as Origine | '')} className={champ}>
            <option value="">Je préfère ne pas répondre</option>
            {ORIGINES.map(([valeur, libelle]) => <option key={valeur} value={valeur}>{libelle}</option>)}
          </select>
        </label>
        <Erreur message={erreur} />
        {/* Bouton actif : les erreurs s'affichent au clic au lieu d'un bouton grise sans explication (WEB-10) */}
        <button type="submit" disabled={envoi} className={bouton}>{envoi ? 'Création…' : 'Créer mon compte'}</button>
      </form>
      <p className="mt-5 text-center text-[13px] text-muted">
        Déjà inscrit ? <Lien href="/connexion" className="font-semibold text-forest hover:underline">Se connecter</Lien>
      </p>
    </Carte>
  )
}
