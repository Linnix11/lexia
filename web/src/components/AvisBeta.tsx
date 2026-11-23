import { useState, type FormEvent } from 'react'
import { api, ApiError, type AvisBeta as Avis } from '../lib/api'
import { useDialog } from '../lib/useDialog'
import { useSession } from '../state/session'

const VIDE: Avis = { note: 0, aide: '', manque: '', erreur: '', lien: '' }
const NOTES = ['Pas utile', 'Peu utile', 'Assez utile', 'Utile', 'Très utile']
const champ = 'w-full min-w-0 rounded-[7px] border border-line bg-white p-[9px] text-[13px] text-ink'

/** Questionnaire de retour de la beta fermee (D121) : enregistre sur le serveur de Lexia, sans service tiers,
 * sans lien avec le compte (ni adresse, ni numero, ni heure). */
function Formulaire({ fermer }: { fermer: () => void }) {
  const ref = useDialog<HTMLDivElement>(true, fermer)
  const [avis, setAvis] = useState<Avis>(VIDE)
  const [erreur, setErreur] = useState<string | null>(null)
  const [etat, setEtat] = useState<'saisie' | 'envoi' | 'merci'>('saisie')
  const maj = <K extends keyof Avis>(k: K, v: Avis[K]) => setAvis((a) => ({ ...a, [k]: v }))

  const envoyer = async (e: FormEvent) => {
    e.preventDefault()
    if (!avis.note) return setErreur('Choisissez une note de 1 à 5.')
    if (avis.lien.trim() && !/^https?:\/\/\S+$/.test(avis.lien.trim())) return setErreur('Le lien doit commencer par https://')
    setErreur(null)
    setEtat('envoi')
    try {
      await api.donnerAvis({ ...avis, lien: avis.lien.trim() })
      setEtat('merci')
    } catch (err) {
      setErreur(err instanceof ApiError ? err.message : 'Envoi impossible pour le moment.')
      setEtat('saisie')
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-[#17241d70] p-[18px]"
      onMouseDown={(e) => e.target === e.currentTarget && fermer()}>
      <div ref={ref} role="dialog" aria-modal="true" aria-labelledby="avis-titre"
        className="max-h-[90dvh] w-full max-w-[560px] overflow-auto rounded-[14px] border border-line bg-surface p-[22px] shadow-[0_20px_70px_#17241d35]">
        <div className="flex items-start justify-between gap-3">
          <h2 id="avis-titre" className="font-display text-[24px] font-normal">Donner mon avis</h2>
          <button type="button" onClick={fermer} aria-label="Fermer le questionnaire"
            className="grid size-11 shrink-0 place-items-center rounded-[7px] border border-line text-muted hover:text-ink">✕</button>
        </div>
        {etat === 'merci' ? (
          <div className="mt-3 grid gap-4">
            <p role="status" className="text-[14px]">Merci : votre avis est enregistré. Il nous aide à corriger Lexia avant son ouverture.</p>
            <button type="button" onClick={fermer} className="justify-self-start rounded-lg bg-forest px-4 py-2 text-[13px] text-white">Fermer</button>
          </div>
        ) : (
          <form onSubmit={envoyer} className="mt-2 grid gap-4" noValidate>
            <p className="text-[12px] text-muted">
              Votre avis n’est pas rattaché à votre compte : n’y écrivez ni votre nom ni d’information personnelle.
              Il est lu par l’équipe Lexia et gardé 12 mois.
            </p>
            <fieldset className="grid gap-2">
              <legend className="mb-1 text-[13px]">Lexia vous a-t-il été utile ?</legend>
              <div className="flex flex-wrap gap-1.5">
                {NOTES.map((libelle, i) => (
                  <label key={i} className={`cursor-pointer rounded-lg border px-3 py-2 text-[12px] has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-forest ${avis.note === i + 1 ? 'border-forest bg-mint text-forest' : 'border-line'}`}>
                    <input type="radio" name="note" value={i + 1} checked={avis.note === i + 1} onChange={() => maj('note', i + 1)} className="sr-only" />
                    <b>{i + 1}</b> · {libelle}
                  </label>
                ))}
              </div>
            </fieldset>
            <label className="grid gap-1.5 text-[13px]">Ce qui vous a aidé
              <textarea rows={2} maxLength={2000} value={avis.aide} onChange={(e) => maj('aide', e.target.value)} className={champ} />
            </label>
            <label className="grid gap-1.5 text-[13px]">Ce qui vous a manqué
              <textarea rows={2} maxLength={2000} value={avis.manque} onChange={(e) => maj('manque', e.target.value)} className={champ} />
            </label>
            <label className="grid gap-1.5 text-[13px]">Une réponse fausse repérée <span className="text-[12px] text-muted">Facultatif : la question posée et ce qui était faux</span>
              <textarea rows={2} maxLength={2000} value={avis.erreur} onChange={(e) => maj('erreur', e.target.value)} className={champ} />
            </label>
            <label className="grid gap-1.5 text-[13px]">Lien de la source en cause <span className="text-[12px] text-muted">Facultatif, par exemple la page Légifrance citée</span>
              <input type="url" maxLength={500} value={avis.lien} onChange={(e) => maj('lien', e.target.value)} placeholder="https://" className={champ} />
            </label>
            {erreur && <p role="alert" className="rounded-lg bg-[#f6e9e4] px-3 py-2 text-[13px] text-[#8c4a36]">{erreur}</p>}
            <button type="submit" disabled={etat === 'envoi'} className="justify-self-start rounded-lg bg-forest px-4 py-2 text-[13px] text-white hover:bg-forest-dark disabled:opacity-60">
              {etat === 'envoi' ? 'Envoi…' : 'Envoyer mon avis'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}

/** Bouton de l'en-tete, visible des comptes de la beta (et des administrateurs, pour l'essayer). */
export function BoutonAvis() {
  const { profil } = useSession()
  const [ouvert, setOuvert] = useState(false)
  if (!profil || !(profil.beta || profil.admin)) return null
  return (
    <>
      {/* Libelle court sur telephone (barre etroite), nom accessible complet */}
      <button type="button" onClick={() => setOuvert(true)} aria-label="Donner mon avis"
        className="whitespace-nowrap rounded-full border border-line px-2.5 py-1 text-[11px] text-forest hover:bg-sage">
        <span className="tab:hidden">Avis</span><span className="hidden tab:inline">Donner mon avis</span>
      </button>
      {ouvert && <Formulaire fermer={() => setOuvert(false)} />}
    </>
  )
}
