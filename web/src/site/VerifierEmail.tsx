// Page ouverte depuis le lien de l'e-mail de confirmation (/verifier-email#jeton=...).
import { useEffect, useState } from 'react'
import { api, ApiError } from '../lib/api'
import type { Profil } from '../lib/api'
import { Lien, jetonDuLien, useRouteur } from '../lib/router'
import { useSession } from '../state/session'
import { Carte } from './Auth'
import { bouton, boutonSecondaire } from './Public'

// Un appel par jeton pour toute la vie de la page : l'espace etudiant est remonte quand la session se
// charge (cle du compte), et un useRef repartait a false. Le second appel tombait sur le jeton deja
// consomme et affichait « Lien non valable » alors que l'adresse etait confirmee (recette du 2026-11-20, D-1).
const verifications = new Map<string, Promise<Profil | null>>()

function verifierUneFois(jeton: string): Promise<Profil | null> {
  let p = verifications.get(jeton)
  if (!p) {
    p = api.verifierEmail(jeton)
    verifications.set(jeton, p)
  }
  return p
}

export function VerifierEmail() {
  const { majProfil } = useSession()
  const { naviguer } = useRouteur()
  const jeton = jetonDuLien()
  // 'ok' : ce navigateur est connecte au compte ; 'connexion' : adresse confirmee, mais le lien n'ouvre
  // pas de session (il contournerait le mot de passe et la double authentification).
  const [etat, setEtat] = useState<'verification' | 'ok' | 'connexion' | 'echec'>(jeton ? 'verification' : 'echec')
  const [erreur, setErreur] = useState(jeton ? '' : 'Ce lien est incomplet : ouvrez-le depuis l’e-mail reçu.')

  useEffect(() => {
    if (!jeton) return
    let actif = true
    verifierUneFois(jeton) // le jeton ne sert qu'une fois : jamais deux appels, meme apres un remontage
      .then((p) => {
        if (!actif) return
        if (p) majProfil(p)
        setEtat(p ? 'ok' : 'connexion')
      })
      .catch((e) => {
        if (!actif) return
        setErreur(e instanceof ApiError ? e.message : 'Vérification impossible pour le moment.')
        setEtat('echec')
      })
    return () => { actif = false }
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
  if (etat === 'connexion') {
    return (
      <Carte titre="Adresse confirmée" sousTitre="Connectez-vous pour poser vos questions de droit.">
        <Lien href="/connexion" className={bouton}>Se connecter</Lien>
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

/** Suite du bandeau : a l'inscription, le lien peut ne pas etre parti (plafond d'envois du jour, D119). */
export function texteLien(profil: { email: string; lien_envoye?: boolean }): string {
  return profil.lien_envoye === false
    ? 'le lien n’a pas pu être envoyé pour le moment. Utilisez « Renvoyer l’e-mail », ou réessayez plus tard.'
    : `le lien a été envoyé à ${profil.email}.`
}

/** Renvoi du lien de confirmation, partage par le bandeau et l'encart au-dessus du champ de question. */
function useRenvoi() {
  const { profil, rafraichir } = useSession()
  const [envoi, setEnvoi] = useState(false)
  const [message, setMessage] = useState('')
  const renvoyer = async () => {
    setEnvoi(true)
    setMessage('')
    try {
      await api.renvoyerVerification()
      setMessage(`Nouvel e-mail envoyé à ${profil?.email ?? ''}.`)
      await rafraichir()
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : 'Envoi impossible pour le moment.')
    } finally {
      setEnvoi(false)
    }
  }
  const boutonRenvoi = (
    <button type="button" onClick={renvoyer} disabled={envoi}
      className="rounded-[7px] border border-[#d8c3a4] px-2.5 py-1 text-[12px] text-[#5f4f37] hover:bg-[#f6ece0] disabled:opacity-60">
      {envoi ? 'Envoi…' : 'Renvoyer l’e-mail'}
    </button>
  )
  return { boutonRenvoi, message }
}

/** Bandeau affiche tant que l'adresse n'est pas confirmee : sans elle, aucune question n'est possible. */
export function BandeauEmail() {
  const { profil } = useSession()
  const { boutonRenvoi, message } = useRenvoi()
  if (!profil || profil.email_verifie !== false) return null

  return (
    <div role="status" className="border-b border-[#ecd9c4] bg-cream px-4 py-2.5 text-[12px] text-[#5f4f37] tab:px-6">
      <div className="mx-auto flex max-w-[1240px] flex-wrap items-center gap-x-3 gap-y-1.5">
        <span>
          <strong className="font-semibold">Confirmez votre adresse e-mail</strong> pour poser vos questions :
          {' '}{texteLien(profil)}
        </span>
        {boutonRenvoi}
        {message && <span className="text-[#746347]">{message}</span>}
      </div>
    </div>
  )
}

/** Encart au-dessus du champ de question quand l'adresse n'est pas confirmee (D129) : l'envoi y est bloque
 *  au lieu de partir et d'echouer en 403 avec un « Reessayer » qui echouait aussi. */
export function EnvoiBloque({ id }: { id: string }) {
  const { profil } = useSession()
  const { boutonRenvoi, message } = useRenvoi()
  if (!profil || profil.email_verifie !== false) return null
  return (
    <div id={id} data-testid="envoi-bloque"
      className="mb-2.5 flex flex-wrap items-center gap-x-3 gap-y-1.5 rounded-[10px] border border-[#ecd9c4] bg-cream px-3.5 py-3 text-[12px] leading-[1.5] text-[#5f4f37]">
      <span>
        <strong className="font-semibold">Confirmez votre adresse e-mail pour poser une question</strong> :{' '}
        {texteLien(profil)} Une fois l’adresse confirmée, revenez sur cet onglet : l’envoi se débloque.
      </span>
      {boutonRenvoi}
      {message && <span role="status" className="text-[#746347]">{message}</span>}
    </div>
  )
}
