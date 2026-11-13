// « Mon compte » : activer ou desactiver la double authentification par application (codes TOTP).
import QRCode from 'qrcode'
import { useState, type FormEvent } from 'react'
import { api, ApiError } from '../lib/api'
import { useSession } from '../state/session'
import { bouton, boutonSecondaire } from './Public'

const champ = 'w-full rounded-[8px] border border-line bg-white px-3 py-2.5 text-[14px] text-ink'

export function DoubleAuthentification() {
  const { profil, rafraichir, majProfil } = useSession()
  const [etape, setEtape] = useState<'repos' | 'scan' | 'secours' | 'desactivation'>('repos')
  const [secret, setSecret] = useState('')
  const [qr, setQr] = useState('')
  const [code, setCode] = useState('')
  const [mdp, setMdp] = useState('')
  const [secours, setSecours] = useState<string[]>([])
  const [erreur, setErreur] = useState<string | null>(null)
  if (!profil) return null
  const active = Boolean(profil.double_authentification)
  const message = (err: unknown) => setErreur(err instanceof ApiError ? err.message : 'Opération impossible pour le moment.')

  const commencer = async () => {
    setErreur(null)
    try {
      const r = await api.deuxFacteurs.preparer()
      setSecret(r.secret)
      setQr(await QRCode.toDataURL(r.uri, { margin: 1, width: 196 }))
      setCode('')
      setEtape('scan')
    } catch (err) {
      message(err)
    }
  }

  const activer = async (e: FormEvent) => {
    e.preventDefault()
    setErreur(null)
    try {
      setSecours((await api.deuxFacteurs.activer(code)).codes_secours)
      setEtape('secours')
      await rafraichir()
    } catch (err) {
      message(err)
    }
  }

  const desactiver = async (e: FormEvent) => {
    e.preventDefault()
    setErreur(null)
    try {
      majProfil(await api.deuxFacteurs.desactiver(mdp, code))
      setEtape('repos')
      setMdp('')
      setCode('')
    } catch (err) {
      message(err)
    }
  }

  return (
    <section className="rounded-xl border border-line bg-surface p-5" aria-labelledby="titre-2fa">
      <h2 id="titre-2fa" className="text-[15px] font-semibold">Double authentification</h2>
      <p className="mt-1 text-[13px] text-muted">
        {active
          ? `Active : un code de votre application est demandé à chaque connexion. Codes de secours restants : ${profil.codes_secours_restants ?? 0}.`
          : 'Protégez votre compte avec un code à 6 chiffres généré par une application (Google Authenticator, Microsoft Authenticator, 2FAS…). Obligatoire pour l’administration.'}
      </p>

      {etape === 'repos' && (
        <button type="button" onClick={active ? () => { setEtape('desactivation'); setCode('') } : commencer}
          className={`mt-4 ${active ? boutonSecondaire : bouton}`}>
          {active ? 'Désactiver' : 'Activer la double authentification'}
        </button>
      )}

      {etape === 'scan' && (
        <form onSubmit={activer} className="mt-4 grid gap-3">
          <p className="text-[13px]">1. Scannez ce QR code avec votre application d’authentification.</p>
          {qr && <img src={qr} alt="QR code à scanner avec l’application d’authentification" width={196} height={196} className="rounded-lg border border-line" />}
          <p className="text-[12px] text-muted">Impossible de scanner ? Saisissez cette clé dans l’application : <code className="break-all rounded bg-chip px-1.5 py-0.5">{secret}</code></p>
          <label className="grid gap-1.5 text-[13px]">
            2. Saisissez le code à 6 chiffres affiché
            <input inputMode="numeric" autoComplete="one-time-code" value={code} maxLength={6} onChange={(e) => setCode(e.target.value)} className={`${champ} max-w-[200px] tracking-[3px]`} />
          </label>
          {erreur && <p role="alert" className="text-[13px] text-[#8c4a36]">{erreur}</p>}
          <div className="flex gap-2">
            <button type="submit" disabled={code.trim().length !== 6} className={bouton}>Activer</button>
            <button type="button" onClick={() => setEtape('repos')} className={boutonSecondaire}>Annuler</button>
          </div>
        </form>
      )}

      {etape === 'secours' && (
        <div className="mt-4 grid gap-3">
          <p className="text-[13px] font-semibold text-forest">Double authentification activée.</p>
          <p className="text-[13px]">Conservez ces codes de secours en lieu sûr : chacun permet <strong>une</strong> connexion si vous perdez votre téléphone. Ils ne seront plus affichés.</p>
          <ul className="grid grid-cols-2 gap-1.5 font-mono text-[14px]">{secours.map((c) => <li key={c} className="rounded bg-chip px-2 py-1">{c}</li>)}</ul>
          <button type="button" onClick={() => { setSecours([]); setEtape('repos') }} className={`justify-self-start ${bouton}`}>J’ai noté mes codes</button>
        </div>
      )}

      {etape === 'desactivation' && (
        <form onSubmit={desactiver} className="mt-4 grid gap-3">
          <label className="grid gap-1.5 text-[13px]">Mot de passe
            <input type="password" autoComplete="current-password" value={mdp} onChange={(e) => setMdp(e.target.value)} className={champ} />
          </label>
          <label className="grid gap-1.5 text-[13px]">Code de l’application (ou code de secours)
            <input inputMode="numeric" autoComplete="one-time-code" value={code} maxLength={12} onChange={(e) => setCode(e.target.value)} className={`${champ} max-w-[200px]`} />
          </label>
          {erreur && <p role="alert" className="text-[13px] text-[#8c4a36]">{erreur}</p>}
          <div className="flex gap-2">
            <button type="submit" disabled={!mdp || code.trim().length < 6} className={bouton}>Désactiver</button>
            <button type="button" onClick={() => setEtape('repos')} className={boutonSecondaire}>Annuler</button>
          </div>
        </form>
      )}
    </section>
  )
}
