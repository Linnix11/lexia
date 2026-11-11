import { useState, type FormEvent } from 'react'
import { ApiError } from '../lib/api'
import { Lien, useRouteur } from '../lib/router'
import { useSession } from '../state/session'
import { PublicLayout, Section, Surtitre, bouton, boutonSecondaire } from './Public'

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
      await supprimer(mdp)
      naviguer('/?compte-supprime=1', { remplacer: true })
    } catch (err) {
      setErreur(err instanceof ApiError ? err.message : 'Suppression impossible pour le moment.')
    }
  }

  return (
    <PublicLayout>
      <Section className="max-w-[760px] py-12">
        <Surtitre>Mon compte</Surtitre>
        <h1 className="mt-2 mb-6 font-display text-[32px] font-normal">{profil.email}</h1>

        <div className="grid gap-4">
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
              Votre adresse e-mail, votre mot de passe et vos compteurs d’utilisation sont effacés définitivement.
              Les fiches enregistrées restent dans ce navigateur jusqu’à ce que vous les retiriez.
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
      </Section>
    </PublicLayout>
  )
}
