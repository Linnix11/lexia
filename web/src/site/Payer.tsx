// Souscription en ligne (D86) : choix du nombre de mois, demande expresse d'acces immediat (droit de
// retractation, article L. 221-25 du Code de la consommation), puis page de paiement Stripe Checkout.
// Le numero de carte est saisi chez Stripe : il ne passe jamais par Lexia.
import { useState } from 'react'
import { api, ApiError, type Formule } from '../lib/api'
import { VERSION_CGU } from '../lib/cgu'
import { Lien } from '../lib/router'
import { useSession } from '../state/session'
import { bouton, boutonSecondaire } from './Public'

const DUREES = [1, 2, 3, 6, 12]
const euros = (n: number) => `${n.toFixed(2).replace('.', ',')} €`

export function Payer({ formule, principal }: { formule: Formule; principal: boolean }) {
  const { profil } = useSession()
  const [mois, setMois] = useState(1)
  const [accord, setAccord] = useState(false)
  const [cgu, setCgu] = useState(false)
  const [envoi, setEnvoi] = useState(false)
  const [erreur, setErreur] = useState<string | null>(null)
  const style = principal ? bouton : boutonSecondaire

  if (!profil) return <Lien href="/inscription" className={style}>Créer un compte pour souscrire</Lien>

  const payer = async () => {
    setEnvoi(true)
    setErreur(null)
    try {
      const { url } = await api.payer(formule.id, mois, accord, VERSION_CGU)
      window.location.assign(url)
    } catch (e) {
      setErreur(e instanceof ApiError ? e.message : 'Le paiement est momentanément indisponible.')
      setEnvoi(false)
    }
  }

  const id = `acces-immediat-${formule.id}`
  return (
    <div className="grid gap-2">
      <label className="flex items-center justify-between gap-2 text-[13px]">
        Durée
        <select value={mois} onChange={(e) => setMois(Number(e.target.value))}
          className="rounded-[6px] border border-line bg-surface px-2 py-1 text-[13px]">
          {DUREES.map((m) => <option key={m} value={m}>{m} mois</option>)}
        </select>
      </label>
      <p className="text-[13px]">
        Total : <strong>{euros(formule.prix_mensuel_euros * mois)}</strong>, payé en une fois, sans reconduction.
      </p>
      <label htmlFor={id} className="flex gap-2 text-[12px] leading-[1.5] text-muted">
        <input id={id} type="checkbox" checked={accord} onChange={(e) => setAccord(e.target.checked)}
          className="mt-[3px] accent-forest" />
        <span>
          Je demande l’accès immédiat à la formule. Si je me rétracte dans les 14 jours, je paierai la part de la
          période déjà écoulée.
        </span>
      </label>
      <label htmlFor={`cgu-${formule.id}`} className="flex gap-2 text-[12px] leading-[1.5] text-muted">
        <input id={`cgu-${formule.id}`} type="checkbox" checked={cgu} onChange={(e) => setCgu(e.target.checked)}
          className="mt-[3px] accent-forest" />
        <span>
          J’ai lu et j’accepte les{' '}
          <Lien href="/cgu" target="_blank" className="underline">conditions générales d’utilisation et de vente</Lien> du{' '}
          {VERSION_CGU}, y compris le droit de rétractation et son formulaire.
        </span>
      </label>
      <button type="button" disabled={!accord || !cgu || envoi} onClick={payer} className={style}>
        {envoi ? 'Ouverture du paiement…' : 'Payer par carte'}
      </button>
      {erreur && <p role="alert" className="text-[12px] text-[#8c4a36]">{erreur}</p>}
    </div>
  )
}
