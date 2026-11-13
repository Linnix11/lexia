// Page ouverte depuis le lien de l'e-mail de confirmation (/verifier-email?jeton=...).
import { useEffect, useRef, useState } from 'react'
import { api, ApiError } from '../lib/api'
import { Lien, useRouteur } from '../lib/router'
import { useSession } from '../state/session'
import { Carte } from './Auth'
import { bouton, boutonSecondaire } from './Public'

export function VerifierEmail() {
  const { majProfil } = useSession()
  const { naviguer } = useRouteur()
  const jeton = new URLSearchParams(window.location.search).get('jeton') ?? ''
  const [etat, setEtat] = useState<'verification' | 'ok' | 'echec'>(jeton ? 'verification' : 'echec')
  const [erreur, setErreur] = useState(jeton ? '' : 'Ce lien est incomplet : ouvrez-le depuis l’e-mail reçu.')
  const lance = useRef(false)

  useEffect(() => {
    if (!jeton || lance.current) return // le jeton ne sert qu'une fois : jamais deux appels
    lance.current = true
    api.verifierEmail(jeton)
      .then((p) => { majProfil(p); setEtat('ok') })
      .catch((e) => {
        setErreur(e instanceof ApiError ? e.message : 'Vérification impossible pour le moment.')
        setEtat('echec')
      })
  }, [jeton, majProfil])

  if (etat === 'verification') {
    return <Carte titre="Vérification en cours…" sousTitre="Nous confirmons votre adresse e-mail."><div /></Carte>
  }
  if (etat === 'ok') {
    return (
      <Carte titre="Adresse confirmée" sousTitre="Votre compte est prêt : vous pouvez poser vos questions de droit.">
        <button type="button" onClick={() => naviguer('/app', { remplacer: true })} className={bouton}>
          Ouvrir mon espace
        </button>
      </Carte>
    )
  }
  return (
    <Carte titre="Lien non valable" sousTitre={erreur}>
      <p className="text-[13px] text-muted">
        Connectez-vous, puis demandez un nouvel e-mail depuis le bandeau affiché en haut de votre espace.
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        <Lien href="/connexion" className={bouton}>Se connecter</Lien>
        <Lien href="/" className={boutonSecondaire}>Accueil</Lien>
      </div>
    </Carte>
  )
}

/** Bandeau affiche tant que l'adresse n'est pas confirmee : sans elle, aucune question n'est possible. */
export function BandeauEmail() {
  const { profil, rafraichir } = useSession()
  const [envoi, setEnvoi] = useState(false)
  const [message, setMessage] = useState('')
  if (!profil || profil.email_verifie !== false) return null

  const renvoyer = async () => {
    setEnvoi(true)
    setMessage('')
    try {
      await api.renvoyerVerification()
      setMessage(`Nouvel e-mail envoyé à ${profil.email}.`)
      await rafraichir()
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : 'Envoi impossible pour le moment.')
    } finally {
      setEnvoi(false)
    }
  }

  return (
    <div role="status" className="border-b border-[#ecd9c4] bg-cream px-4 py-2.5 text-[12px] text-[#5f4f37] tab:px-6">
      <div className="mx-auto flex max-w-[1240px] flex-wrap items-center gap-x-3 gap-y-1.5">
        <span>
          <strong className="font-semibold">Confirmez votre adresse e-mail</strong> pour poser vos questions :
          le lien a été envoyé à {profil.email}.
        </span>
        <button type="button" onClick={renvoyer} disabled={envoi}
          className="rounded-[7px] border border-[#d8c3a4] px-2.5 py-1 text-[12px] text-[#5f4f37] hover:bg-[#f6ece0] disabled:opacity-60">
          {envoi ? 'Envoi…' : 'Renvoyer l’e-mail'}
        </button>
        {message && <span className="text-[#746347]">{message}</span>}
      </div>
    </div>
  )
}
