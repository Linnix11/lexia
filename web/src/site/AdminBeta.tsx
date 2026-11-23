import { useCallback, useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { api, ApiError, LIEN_AVIS_CSV, type AvisBetaLu, type CodeBeta, type UsageBeta } from '../lib/api'

// Beta fermee (D121) : codes d'acces, avis des etudiants, suivi d'usage anonyme.

const ETAPES: Record<string, string> = {
  recherche: 'Recherche (entière)',
  reformulation: 'Reformulation',
  vectorisation: 'Vectorisation',
  references: 'Références citées',
  lexicale: 'Recherche plein texte',
  vectorielle: 'Recherche vectorielle',
  reclassement: 'Reclassement',
  generation: 'Rédaction par le modèle',
  totale: 'Question entière',
}
const secondes = (ms: number | null) => (ms == null ? '-' : `${(ms / 1000).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} s`)
const pourcent = (t: number | null) => (t == null ? '-' : `${(t * 100).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} %`)
const date = (iso: string) => new Date(iso.length === 10 ? iso + 'T12:00:00' : iso).toLocaleDateString('fr-FR')
const champ = 'min-w-0 rounded-lg border border-line bg-white px-3 py-2 text-[13px] text-ink'
const th = 'py-1 pr-3 font-normal'

function Carte({ titre, children }: { titre: string; children: ReactNode }) {
  return (
    <section className="min-w-0 rounded-xl border border-line bg-surface p-4 tab:p-5">
      <h2 className="mb-3 text-[13px] font-semibold">{titre}</h2>
      {children}
    </section>
  )
}

function Codes() {
  const [codes, setCodes] = useState<CodeBeta[] | null>(null)
  const [libelle, setLibelle] = useState('')
  const [plafond, setPlafond] = useState(20)
  const [nouveau, setNouveau] = useState<CodeBeta | null>(null)
  const [erreur, setErreur] = useState<string | null>(null)
  const charger = useCallback(() => { api.admin.beta.codes().then(setCodes).catch(() => setCodes([])) }, [])
  useEffect(charger, [charger])

  const creer = async (e: FormEvent) => {
    e.preventDefault()
    setErreur(null)
    try {
      setNouveau(await api.admin.beta.creerCode(libelle.trim(), plafond))
      setLibelle('')
      charger()
    } catch (err) {
      setErreur(err instanceof ApiError ? err.message : 'Création impossible.')
    }
  }
  const desactiver = async (id: number) => {
    try {
      const c = await api.admin.beta.desactiverCode(id)
      setCodes((l) => l?.map((x) => (x.id === id ? c : x)) ?? l)
    } catch (err) {
      setErreur(err instanceof ApiError ? err.message : 'Action impossible.')
    }
  }

  return (
    <Carte titre="Codes d’accès">
      <p className="mb-3 text-[12px] text-muted">
        Avec <code>BETA_FERMEE=1</code> dans le .env du serveur, l’inscription demande un de ces codes. Le code
        n’est affiché qu’une fois, à sa création : notez-le. Un compte supprimé ne rend pas sa place.
      </p>
      <form onSubmit={creer} className="mb-3 flex flex-wrap items-end gap-2">
        <label className="grid flex-1 gap-1 text-[12px] text-muted">Nom du groupe
          <input required minLength={2} maxLength={80} value={libelle} onChange={(e) => setLibelle(e.target.value)} placeholder="L1 Assas, TD 3" className={champ} />
        </label>
        <label className="grid w-[110px] gap-1 text-[12px] text-muted">Places
          <input required type="number" min={1} max={500} value={plafond} onChange={(e) => setPlafond(Number(e.target.value))} className={champ} />
        </label>
        <button type="submit" className="rounded-lg bg-forest px-3 py-2 text-[13px] text-white hover:bg-forest-dark">Créer un code</button>
      </form>
      {nouveau?.code && (
        <p role="status" className="mb-3 rounded-lg bg-mint px-3 py-2 text-[13px] text-forest">
          Code pour « {nouveau.libelle} » ({nouveau.plafond} places) : <b className="select-all tracking-[2px]">{nouveau.code}</b>
          <span className="block text-[12px]">Il ne sera plus affiché : copiez-le maintenant.</span>
        </p>
      )}
      {erreur && <p role="alert" className="mb-3 text-[12px] text-[#8c4a36]">{erreur}</p>}
      {codes === null ? <p className="text-[13px] text-muted">Chargement…</p> : codes.length === 0 ? (
        <p className="text-[13px] text-muted">Aucun code pour l’instant.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[520px] text-left text-[12px]">
            <thead className="text-muted"><tr><th scope="col" className={th}>Groupe</th><th scope="col" className={th}>Inscriptions</th><th scope="col" className={th}>Comptes actuels</th><th scope="col" className={th}>Créé le</th><th scope="col" className={th}>État</th></tr></thead>
            <tbody>
              {codes.map((c) => (
                <tr key={c.id} className="border-t border-line">
                  <th scope="row" className="py-1.5 pr-3 font-normal">{c.libelle}</th>
                  <td className="py-1.5 pr-3">{c.inscriptions} / {c.plafond}</td>
                  <td className="py-1.5 pr-3">{c.comptes}</td>
                  <td className="py-1.5 pr-3">{date(c.cree_le)}</td>
                  <td className="py-1.5">
                    {c.actif ? (
                      <button type="button" onClick={() => desactiver(c.id)} className="text-[#8c4a36] hover:underline">Désactiver « {c.libelle} »</button>
                    ) : <span className="text-muted">désactivé</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Carte>
  )
}

function Avis() {
  const [r, setR] = useState<{ avis: AvisBetaLu[]; note_moyenne: number | null } | null>(null)
  useEffect(() => { api.admin.beta.avis().then(setR).catch(() => setR({ avis: [], note_moyenne: null })) }, [])
  return (
    <Carte titre={`Avis des étudiants (${r?.avis.length ?? 0})`}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-[13px]">
        <span>Note d’utilité moyenne : <b>{r?.note_moyenne != null ? `${r.note_moyenne.toLocaleString('fr-FR')} / 5` : '-'}</b></span>
        <a href={LIEN_AVIS_CSV} download className="rounded-md border border-line px-2.5 py-1 text-[12px] text-forest hover:bg-sage">Exporter en CSV</a>
      </div>
      {!r ? <p className="text-[13px] text-muted">Chargement…</p> : r.avis.length === 0 ? (
        <p className="text-[13px] text-muted">Aucun avis pour l’instant.</p>
      ) : (
        <ul className="grid max-h-[520px] gap-2 overflow-auto text-[12px]">
          {r.avis.map((a) => (
            <li key={a.id} className="rounded-lg border border-line-soft p-3">
              <div className="mb-1 text-muted">{date(a.jour)} · note {a.note} / 5</div>
              {a.aide && <p><b>A aidé :</b> {a.aide}</p>}
              {a.manque && <p><b>A manqué :</b> {a.manque}</p>}
              {a.erreur && <p><b>Réponse fausse :</b> {a.erreur}</p>}
              {/* lien saisi par un etudiant : jamais suivi automatiquement, ouvert sans referent */}
              {a.lien && <p className="break-all"><b>Lien :</b> <a href={a.lien} target="_blank" rel="noopener noreferrer nofollow" className="text-forest underline">{a.lien}</a></p>}
            </li>
          ))}
        </ul>
      )}
    </Carte>
  )
}

function Usage() {
  const [u, setU] = useState<UsageBeta | null>(null)
  const [jours, setJours] = useState(14)
  useEffect(() => { api.admin.beta.usage(jours).then(setU).catch(() => setU(null)) }, [jours])
  if (!u) return <Carte titre="Suivi d’usage"><p className="text-[13px] text-muted">Chargement…</p></Carte>
  const actives = u.fonctions.filter((f) => f.appels > 0)
  return (
    <Carte titre="Suivi d’usage anonyme">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <p className="text-[12px] text-muted">
          Nombres agrégés, sans texte des questions ni compte ; les essais des administrateurs ne sont pas comptés.
          Taux d’erreur : réponses en erreur du serveur (5xx) sur tous les appels.
        </p>
        <label className="flex items-center gap-2 text-[12px] text-muted">Période
          <select value={jours} onChange={(e) => setJours(Number(e.target.value))} className={champ}>
            <option value={7}>7 jours</option><option value={14}>14 jours</option><option value={30}>30 jours</option><option value={90}>90 jours</option>
          </select>
        </label>
      </div>
      <p className="mb-3 text-[13px]">{u.appels} appel(s) · taux d’erreur : <b>{pourcent(u.taux_erreur)}</b></p>
      <div className="grid gap-4 desk:grid-cols-2 [&>*]:min-w-0">
        <div className="overflow-x-auto">
          <h3 className="mb-1 text-[12px] font-semibold">Questions par jour</h3>
          <table className="w-full text-left text-[12px]">
            <thead className="text-muted"><tr><th scope="col" className={th}>Jour</th><th scope="col" className={th}>Questions</th><th scope="col" className={th}>Tous appels</th></tr></thead>
            <tbody>
              {u.par_jour.slice().reverse().map((j) => (
                <tr key={j.jour} className="border-t border-line"><th scope="row" className="py-1 pr-3 font-normal">{date(j.jour)}</th><td className="pr-3">{j.questions}</td><td>{j.total}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="grid content-start gap-4">
          <div className="overflow-x-auto">
            <h3 className="mb-1 text-[12px] font-semibold">Répartition par fonction</h3>
            {actives.length === 0 ? <p className="text-[12px] text-muted">Aucun appel sur la période.</p> : (
              <table className="w-full text-left text-[12px]">
                <thead className="text-muted"><tr><th scope="col" className={th}>Fonction</th><th scope="col" className={th}>Appels</th><th scope="col" className={th}>Part</th><th scope="col" className={th}>Médiane / 90 %</th><th scope="col" className={th}>Erreurs</th><th scope="col" className={th}>Refus</th></tr></thead>
                <tbody>
                  {actives.map((f) => (
                    <tr key={f.fonction} className="border-t border-line">
                      <th scope="row" className="py-1 pr-3 font-normal">{f.libelle}</th><td className="pr-3">{f.appels}</td>
                      <td className="pr-3">{pourcent(u.appels ? f.appels / u.appels : null)}</td>
                      <td className="pr-3 whitespace-nowrap">{secondes(f.mediane_ms)} / {secondes(f.p90_ms)}</td>
                      <td className="pr-3">{pourcent(f.taux_erreur)}</td><td>{f.refus}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          <div className="overflow-x-auto">
            <h3 className="mb-1 text-[12px] font-semibold">Durées par étape d’une question</h3>
            <table className="w-full text-left text-[12px]">
              <thead className="text-muted"><tr><th scope="col" className={th}>Étape</th><th scope="col" className={th}>Mesures</th><th scope="col" className={th}>Médiane</th><th scope="col" className={th}>90e centile</th></tr></thead>
              <tbody>
                {u.etapes.map((e) => (
                  <tr key={e.etape} className="border-t border-line">
                    <th scope="row" className="py-1 pr-3 font-normal">{ETAPES[e.etape] ?? e.etape}</th><td className="pr-3">{e.mesures}</td>
                    <td className="pr-3">{secondes(e.mediane_ms)}</td><td>{secondes(e.p90_ms)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Carte>
  )
}

export function AdminBeta() {
  return (
    <div className="grid gap-4 [&>*]:min-w-0">
      <Codes />
      <Usage />
      <Avis />
    </div>
  )
}
