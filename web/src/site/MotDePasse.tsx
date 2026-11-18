// Mot de passe oublie : demande du lien (/mot-de-passe-oublie), puis choix du nouveau mot de passe
// depuis le lien recu par e-mail (/nouveau-mot-de-passe#jeton=...).
import { useState, type FormEvent } from 'react'
import { api, ApiError } from '../lib/api'
import { Lien, jetonDuLien } from '../lib/router'
import { Carte, Erreur, MDP_MIN, champ } from './Auth'
import { bouton } from './Public'

export function MotDePasseOublie() {
  const [email, setEmail] = useState('')
  const [envoye, setEnvoye] = useState(false)
  const [erreur, setErreur] = useState<string | null>(null)
  const [envoi, setEnvoi] = useState(false)

  const soumettre = async (e: FormEvent) => {
    e.preventDefault()
    setErreur(null)
    setEnvoi(true)
    try {
      await api.motDePasseOublie(email.trim())
      setEnvoye(true)
    } catch (err) {
      setErreur(err instanceof ApiError ? err.message : 'Envoi impossible pour le moment.')
    } finally {
      setEnvoi(false)
    }
  }

  if (envoye) {
    return (
      <Carte titre="Vérifiez vos e-mails" sousTitre="Si un compte existe avec cette adresse, un lien vient de lui être envoyé.">
        <p className="text-[13px] text-muted">
          Le lien est valable une heure. Pensez à regarder dans les courriers indésirables.
        </p>
        <p className="mt-5 text-center text-[13px]">
          <Lien href="/connexion" className="font-semibold text-forest hover:underline">Retour à la connexion</Lien>
        </p>
      </Carte>
    )
  }
  return (
    <Carte titre="Mot de passe oublié" sousTitre="Recevez un lien pour choisir un nouveau mot de passe.">
      <form onSubmit={soumettre} className="grid gap-4" noValidate>
        <label className="grid gap-1.5 text-[13px]">
          Adresse e-mail du compte
          <input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} className={champ} />
        </label>
        <Erreur message={erreur} />
        <button type="submit" disabled={envoi || !email.trim()} className={bouton}>{envoi ? 'Envoi…' : 'Recevoir le lien'}</button>
      </form>
      <p className="mt-5 text-center text-[13px] text-muted">
        <Lien href="/connexion" className="text-forest hover:underline">Retour à la connexion</Lien>
      </p>
    </Carte>
  )
}

export function NouveauMotDePasse() {
  const jeton = jetonDuLien()
  const [mdp, setMdp] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [fait, setFait] = useState(false)
  const [erreur, setErreur] = useState<string | null>(jeton ? null : 'Ce lien est incomplet : ouvrez-le depuis l’e-mail reçu.')
  const [envoi, setEnvoi] = useState(false)
  const probleme = mdp.length < MDP_MIN ? `Au moins ${MDP_MIN} caractères.`
    : confirmation !== mdp ? 'Les deux mots de passe ne correspondent pas.' : null

  const soumettre = async (e: FormEvent) => {
    e.preventDefault()
    if (probleme) {
      setErreur(probleme)
      return
    }
    setErreur(null)
    setEnvoi(true)
    try {
      await api.nouveauMotDePasse(jeton, mdp)
      setFait(true)
    } catch (err) {
      setErreur(err instanceof ApiError ? err.message : 'Modification impossible pour le moment.')
    } finally {
      setEnvoi(false)
    }
  }

  if (fait) {
    return (
      <Carte titre="Mot de passe modifié" sousTitre="Connectez-vous avec votre nouveau mot de passe. Vos autres appareils ont été déconnectés.">
        <Lien href="/connexion" className={bouton}>Se connecter</Lien>
      </Carte>
    )
  }
  return (
    <Carte titre="Nouveau mot de passe" sousTitre="Choisissez le mot de passe de votre compte Lexia.">
      <form onSubmit={soumettre} className="grid gap-4" noValidate>
        <label className="grid gap-1.5 text-[13px]">
          Nouveau mot de passe <span className="text-[12px] text-muted">{MDP_MIN} caractères minimum</span>
          <input type="password" autoComplete="new-password" value={mdp} onChange={(e) => setMdp(e.target.value)} className={champ} />
        </label>
        <label className="grid gap-1.5 text-[13px]">
          Confirmez le mot de passe
          <input type="password" autoComplete="new-password" value={confirmation} onChange={(e) => setConfirmation(e.target.value)} className={champ} />
        </label>
        <Erreur message={erreur} />
        <button type="submit" disabled={envoi || !jeton || !mdp} className={bouton}>{envoi ? 'Enregistrement…' : 'Enregistrer'}</button>
      </form>
      <p className="mt-5 text-center text-[13px] text-muted">
        Lien expiré ? <Lien href="/mot-de-passe-oublie" className="text-forest hover:underline">Demandez-en un nouveau</Lien>
      </p>
    </Carte>
  )
}
