import { useState, type FormEvent, type ReactNode } from 'react'
import { ApiError } from '../lib/api'
import { Lien, useRouteur } from '../lib/router'
import { useSession } from '../state/session'
import { PublicLayout, bouton } from './Public'

const champ = 'w-full rounded-[8px] border border-line bg-white px-3 py-2.5 text-[14px] text-ink aria-[invalid=true]:border-[#c2765f]'
const MDP_MIN = 10

function Carte({ titre, sousTitre, children }: { titre: string; sousTitre: string; children: ReactNode }) {
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

function Erreur({ message }: { message: string | null }) {
  if (!message) return null
  return <p role="alert" className="rounded-lg bg-[#f6e9e4] px-3 py-2 text-[13px] text-[#8c4a36]">{message}</p>
}

export function Connexion() {
  const { connexion } = useSession()
  const { naviguer } = useRouteur()
  const [email, setEmail] = useState('')
  const [mdp, setMdp] = useState('')
  const [erreur, setErreur] = useState<string | null>(null)
  const [envoi, setEnvoi] = useState(false)
  const expiree = new URLSearchParams(window.location.search).has('expiree')

  const soumettre = async (e: FormEvent) => {
    e.preventDefault()
    setErreur(null)
    setEnvoi(true)
    try {
      await connexion(email, mdp)
      naviguer('/app', { remplacer: true })
    } catch (err) {
      setErreur(err instanceof ApiError ? err.message : 'Connexion impossible pour le moment.')
    } finally {
      setEnvoi(false)
    }
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
        <button type="submit" disabled={envoi || !email || !mdp} className={bouton}>{envoi ? 'Connexion…' : 'Se connecter'}</button>
      </form>
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
  const [mdp, setMdp] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [cgu, setCgu] = useState(false)
  const [touche, setTouche] = useState<Record<string, boolean>>({})
  const [erreur, setErreur] = useState<string | null>(null)
  const [envoi, setEnvoi] = useState(false)

  const erreurs = {
    email: /^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(email.trim()) ? null : 'Adresse e-mail invalide.',
    mdp: mdp.length >= MDP_MIN ? null : `Au moins ${MDP_MIN} caractères.`,
    confirmation: confirmation === mdp ? null : 'Les deux mots de passe ne correspondent pas.',
  }
  const valide = !erreurs.email && !erreurs.mdp && !erreurs.confirmation && cgu
  const montre = (k: keyof typeof erreurs) => (touche[k] ? erreurs[k] : null)
  const quitter = (k: string) => () => setTouche((t) => ({ ...t, [k]: true }))

  const soumettre = async (e: FormEvent) => {
    e.preventDefault()
    setTouche({ email: true, mdp: true, confirmation: true })
    if (!valide) return
    setErreur(null)
    setEnvoi(true)
    try {
      await inscription(email, mdp, cgu)
      naviguer('/app', { remplacer: true })
    } catch (err) {
      setErreur(err instanceof ApiError ? err.message : 'Inscription impossible pour le moment.')
    } finally {
      setEnvoi(false)
    }
  }

  const aide = (id: string, msg: string | null) => msg && <span id={id} className="text-[12px] text-[#8c4a36]">{msg}</span>

  return (
    <Carte titre="Créer un compte" sousTitre="Gratuit : 10 questions et 2 questionnaires par jour.">
      <form onSubmit={soumettre} className="grid gap-4" noValidate>
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
          <input type="checkbox" checked={cgu} onChange={(e) => setCgu(e.target.checked)} className="mt-1 accent-forest" />
          <span>
            J’accepte les <Lien href="/cgu" target="_blank" className="text-forest underline">conditions d’utilisation</Lien> et
            j’ai lu la <Lien href="/confidentialite" target="_blank" className="text-forest underline">politique de confidentialité</Lien>.
          </span>
        </label>
        <Erreur message={erreur} />
        <button type="submit" disabled={envoi || !valide} className={bouton}>{envoi ? 'Création…' : 'Créer mon compte'}</button>
      </form>
      <p className="mt-5 text-center text-[13px] text-muted">
        Déjà inscrit ? <Lien href="/connexion" className="font-semibold text-forest hover:underline">Se connecter</Lien>
      </p>
    </Carte>
  )
}
