import { Fragment, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, ApiError, type ActiviteAdmin, type ClientAdmin, type ServeurAdmin, type StatsAdmin } from '../lib/api'
import { Lien } from '../lib/router'
import { useSession } from '../state/session'
import { Histogramme } from './Graphique'
import { boutonSecondaire } from './Public'

type Onglet = 'apercu' | 'clients' | 'activite' | 'serveur'
const ONGLETS: { id: Onglet; label: string }[] = [
  { id: 'apercu', label: 'Vue d’ensemble' },
  { id: 'clients', label: 'Clients' },
  { id: 'activite', label: 'Activité' },
  { id: 'serveur', label: 'Serveur' },
]
const NOMS_FORMULES: Record<string, string> = { gratuit: 'Gratuit', etudiant: 'Étudiant', intensif: 'Intensif' }

const euros = (v: number) => v.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })
const octets = (v: number | null | undefined) => {
  if (v == null) return '-'
  const u = ['o', 'Ko', 'Mo', 'Go', 'To']
  let i = 0
  let x = v
  while (x >= 1024 && i < u.length - 1) { x /= 1024; i++ }
  return `${x.toLocaleString('fr-FR', { maximumFractionDigits: 1 })} ${u[i]}`
}
const duree = (s: number | null | undefined) => {
  if (s == null) return '-'
  const j = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60)
  return j ? `${j} j ${h} h` : h ? `${h} h ${m} min` : `${m} min`
}
const date = (iso: string | null) => (iso ? new Date(iso.length === 10 ? iso + 'T12:00:00' : iso).toLocaleDateString('fr-FR') : '-')
const heure = (iso: string) => new Date(iso).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })

function Carte({ titre, children, className = '' }: { titre?: string; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-xl border border-line bg-surface p-4 tab:p-5 ${className}`}>
      {titre && <h2 className="mb-3 text-[13px] font-semibold">{titre}</h2>}
      {children}
    </section>
  )
}

function Tuile({ libelle, valeur, detail }: { libelle: string; valeur: ReactNode; detail?: ReactNode }) {
  return (
    <div className="min-w-0 rounded-xl border border-line bg-surface p-4">
      <div className="text-[12px] text-muted">{libelle}</div>
      <div className="mt-1 font-display text-[28px] leading-none">{valeur}</div>
      {detail && <div className="mt-1.5 text-[12px] text-muted">{detail}</div>}
    </div>
  )
}

/** Etat avec icone + libelle (jamais la couleur seule). */
function Etat({ niveau, children }: { niveau: 'ok' | 'attention' | 'neutre'; children: ReactNode }) {
  const s = { ok: ['●', 'bg-mint text-forest'], attention: ['▲', 'bg-[#f6e9e4] text-[#8c4a36]'], neutre: ['○', 'bg-chip text-muted'] }[niveau]
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[12px] ${s[1]}`}><span aria-hidden>{s[0]}</span>{children}</span>
}

function Jauge({ libelle, utilise, total }: { libelle: string; utilise: number; total: number }) {
  const pct = total ? Math.round((utilise / total) * 100) : 0
  return (
    <div>
      <div className="flex justify-between text-[12px]"><span>{libelle}</span><span className="text-muted">{octets(utilise)} / {octets(total)} ({pct} %)</span></div>
      <div className="mt-1 h-2 rounded-full bg-[#e7e4da]"><div className={`h-full rounded-full ${pct > 85 ? 'bg-[#c2765f]' : 'bg-[#2b8a5e]'}`} style={{ width: `${pct}%` }} /></div>
    </div>
  )
}

// --- Vue d'ensemble --------------------------------------------------------------

function Apercu({ s }: { s: StatsAdmin }) {
  const a = s.activite.dernieres_24h
  const retours = s.activite.retours
  const satisfaction = retours.utiles + retours.pas_utiles ? Math.round((100 * retours.utiles) / (retours.utiles + retours.pas_utiles)) : null
  const abstentions = (a.statuts.abstention ?? 0) + (a.statuts.hors_champ ?? 0)
  return (
    <div className="grid gap-4 [&>*]:min-w-0">
      <div className="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-3">
        <Tuile libelle="Comptes" valeur={s.comptes.total} detail={`+${s.comptes.nouveaux_7j} sur 7 jours`} />
        <Tuile libelle="Abonnés payants" valeur={s.comptes.payants_actifs} detail={s.comptes.formules_expirees ? `${s.comptes.formules_expirees} expiré(s)` : 'formules actives'} />
        <Tuile libelle="Revenu mensuel théorique" valeur={euros(s.revenu_mensuel_estime)} detail="aux prix affichés" />
        <Tuile libelle="Questions aujourd’hui" valeur={s.aujourd_hui.questions} detail={`${s.aujourd_hui.actifs} compte(s) actif(s)`} />
        <Tuile libelle="Erreurs du modèle (24 h)" valeur={a.erreurs_modele}
          detail={a.erreurs_modele ? <Etat niveau="attention">à surveiller</Etat> : <Etat niveau="ok">aucune</Etat>} />
        <Tuile libelle="Réponses jugées utiles" valeur={satisfaction === null ? '-' : `${satisfaction} %`} detail={`${retours.utiles + retours.pas_utiles} avis`} />
      </div>

      <Carte>
        <Histogramme serie={s.serie} titre="Questions posées par jour (30 derniers jours)" />
      </Carte>

      <div className="grid gap-4 desk:grid-cols-2 [&>*]:min-w-0">
        <Carte titre="Répartition par formule">
          <ul className="grid gap-3">
            {s.formules.map((f) => {
              const n = s.comptes.par_formule[f.id] ?? 0
              const pct = s.comptes.total ? Math.round((100 * n) / s.comptes.total) : 0
              return (
                <li key={f.id}>
                  <div className="flex justify-between text-[13px]"><span>{f.nom} <span className="text-muted">· {f.prix_mensuel_euros ? euros(f.prix_mensuel_euros) + '/mois' : 'gratuit'}</span></span><span>{n} <span className="text-muted">({pct} %)</span></span></div>
                  <div className="mt-1 h-2 rounded-full bg-[#e7e4da]"><div className="h-full rounded-full bg-[#2b8a5e]" style={{ width: `${pct}%` }} /></div>
                </li>
              )
            })}
          </ul>
        </Carte>
        <Carte titre="Activité des dernières 24 h">
          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-[13px]">
            <dt className="text-muted">Questions</dt><dd>{a.questions}</dd>
            <dt className="text-muted">Questionnaires</dt><dd>{a.quiz}</dd>
            <dt className="text-muted">Réponses sourcées</dt><dd>{a.statuts.reponse ?? 0}</dd>
            <dt className="text-muted">Abstentions et hors champ</dt><dd>{abstentions}</dd>
            <dt className="text-muted">Durée moyenne / 95 %</dt><dd>{a.duree_moyenne_ms ? `${(a.duree_moyenne_ms / 1000).toFixed(1)} s / ${((a.duree_p95_ms ?? 0) / 1000).toFixed(1)} s` : '-'}</dd>
            <dt className="text-muted">Questions sur 7 jours</dt><dd>{s.activite.questions_7j}</dd>
          </dl>
          {s.activite.derniere_erreur && (
            <p className="mt-3 rounded-lg bg-cream px-3 py-2 text-[12px] text-[#746347]">
              Dernière erreur du modèle : {heure(s.activite.derniere_erreur.ts)} · {s.activite.derniere_erreur.detail.slice(0, 140)}
            </p>
          )}
        </Carte>
      </div>
    </div>
  )
}

// --- Clients -----------------------------------------------------------------------

function LigneClient({ c, moi, maj, retirer }: { c: ClientAdmin; moi: string; maj: (c: ClientAdmin) => void; retirer: (id: number) => void }) {
  const [formule, setFormule] = useState(c.formule_enregistree)
  const [jours, setJours] = useState<string>('31')
  const [etat, setEtat] = useState<'libre' | 'envoi' | 'confirmer'>('libre')
  const [erreur, setErreur] = useState<string | null>(null)
  const estMoi = c.email === moi

  const agir = async (action: () => Promise<void>) => {
    setEtat('envoi')
    setErreur(null)
    try { await action() } catch (e) { setErreur(e instanceof ApiError ? e.message : 'Action impossible.') }
    setEtat('libre')
  }
  const appliquer = () => agir(async () => maj(await api.admin.formule(c.id, formule, formule === 'gratuit' || jours === '' ? null : Number(jours))))
  const basculerAdmin = () => agir(async () => maj(await api.admin.role(c.id, !c.admin)))
  const supprimer = () => agir(async () => { await api.admin.supprimer(c.id); retirer(c.id) })
  const champ = 'rounded-md border border-line bg-white px-2 py-1 text-[12px]'

  return (
    <tr className="border-t border-line-soft align-top">
      <td className="py-2.5 pr-3">
        <div className="font-medium break-all">{c.email}</div>
        <div className="mt-0.5 flex flex-wrap gap-1 text-[11px] text-muted">
          inscrit le {date(c.cree_le)}
          {c.admin && <span className="rounded-full bg-mint px-1.5 text-forest">admin</span>}
          {estMoi && <span className="rounded-full bg-chip px-1.5">vous</span>}
        </div>
      </td>
      <td className="py-2.5 pr-3 text-[12px]">
        <div>{NOMS_FORMULES[c.formule]}</div>
        <div className="text-muted">{c.formule_fin ? `jusqu’au ${date(c.formule_fin)}` : c.formule !== 'gratuit' ? 'sans fin' : ''}</div>
      </td>
      <td className="py-2.5 pr-3 text-[12px] whitespace-nowrap">{c.questions_aujourdhui} / {c.limite_questions}<div className="text-muted">{c.questions_30j} sur 30 j</div></td>
      <td className="py-2.5 pr-3 text-[12px] whitespace-nowrap">{date(c.derniere_activite)}</td>
      <td className="py-2.5">
        <div className="flex flex-wrap items-center gap-1.5">
          <label className="sr-only" htmlFor={`f-${c.id}`}>Formule de {c.email}</label>
          <select id={`f-${c.id}`} value={formule} onChange={(e) => setFormule(e.target.value)} className={champ}>
            {Object.entries(NOMS_FORMULES).map(([id, nom]) => <option key={id} value={id}>{nom}</option>)}
          </select>
          {formule !== 'gratuit' && (
            <>
              <label className="sr-only" htmlFor={`j-${c.id}`}>Durée</label>
              <select id={`j-${c.id}`} value={jours} onChange={(e) => setJours(e.target.value)} className={champ}>
                <option value="31">1 mois</option>
                <option value="92">3 mois</option>
                <option value="365">1 an</option>
                <option value="">sans fin</option>
              </select>
            </>
          )}
          <button type="button" onClick={appliquer} disabled={etat === 'envoi'} className="rounded-md bg-forest px-2.5 py-1 text-[12px] text-white disabled:opacity-60">Appliquer</button>
        </div>
        <div className="mt-1.5 flex flex-wrap gap-3 text-[12px]">
          {!estMoi && (
            <button type="button" onClick={basculerAdmin} disabled={etat === 'envoi'} className="text-forest hover:underline">
              {c.admin ? 'Retirer le rôle admin' : 'Rendre admin'}
            </button>
          )}
          {!estMoi && etat !== 'confirmer' && (
            <button type="button" onClick={() => setEtat('confirmer')} className="text-[#8c4a36] hover:underline">Supprimer…</button>
          )}
          {etat === 'confirmer' && (
            <span className="flex flex-wrap items-center gap-2">
              <button type="button" onClick={supprimer} className="rounded-md bg-[#8c4a36] px-2 py-0.5 text-white">Supprimer le compte {c.email}</button>
              <button type="button" onClick={() => setEtat('libre')} className="text-muted">Annuler</button>
            </span>
          )}
        </div>
        {erreur && <p role="alert" className="mt-1 text-[12px] text-[#8c4a36]">{erreur}</p>}
      </td>
    </tr>
  )
}

function Clients({ moi }: { moi: string }) {
  const [q, setQ] = useState('')
  const [clients, setClients] = useState<ClientAdmin[] | null>(null)
  const [formule, setFormule] = useState('')

  useEffect(() => {
    let actif = true
    const t = window.setTimeout(() => {
      api.admin.clients(q).then((c) => actif && setClients(c)).catch(() => actif && setClients([]))
    }, 250)
    return () => { actif = false; window.clearTimeout(t) }
  }, [q])

  const visibles = useMemo(() => (clients ?? []).filter((c) => !formule || c.formule === formule), [clients, formule])
  const maj = (n: ClientAdmin) => setClients((l) => l?.map((c) => (c.id === n.id ? n : c)) ?? l)
  const retirer = (id: number) => setClients((l) => l?.filter((c) => c.id !== id) ?? l)

  return (
    <Carte>
      <div className="mb-3 flex flex-wrap items-end gap-2">
        <label className="grid flex-1 gap-1 text-[12px] text-muted">
          Rechercher un client
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="adresse e-mail" className="min-w-[200px] rounded-lg border border-line bg-white px-3 py-2 text-[13px] text-ink" />
        </label>
        <label className="grid gap-1 text-[12px] text-muted">
          Formule
          <select value={formule} onChange={(e) => setFormule(e.target.value)} className="rounded-lg border border-line bg-white px-3 py-2 text-[13px] text-ink">
            <option value="">Toutes</option>
            {Object.entries(NOMS_FORMULES).map(([id, nom]) => <option key={id} value={id}>{nom}</option>)}
          </select>
        </label>
      </div>
      {clients === null ? (
        <div className="grid animate-pulse gap-2">{[0, 1, 2].map((i) => <div key={i} className="h-10 rounded bg-[#ece9e0]" />)}</div>
      ) : visibles.length === 0 ? (
        <p className="py-6 text-center text-[13px] text-muted">{q || formule ? 'Aucun client ne correspond à ces filtres.' : 'Aucun compte pour l’instant.'}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-[13px]">
            <thead className="text-[12px] text-muted">
              <tr><th className="pb-2 font-normal">Client</th><th className="pb-2 font-normal">Formule</th><th className="pb-2 font-normal">Questions</th><th className="pb-2 font-normal">Dernière activité</th><th className="pb-2 font-normal">Actions</th></tr>
            </thead>
            <tbody>{visibles.map((c) => <LigneClient key={c.id} c={c} moi={moi} maj={maj} retirer={retirer} />)}</tbody>
          </table>
        </div>
      )}
      <p className="mt-3 text-[12px] text-muted">{visibles.length} client(s) affiché(s). Une formule payante expirée repasse automatiquement en gratuit.</p>
    </Carte>
  )
}

// --- Activite ------------------------------------------------------------------------

function Activite({ a }: { a: ActiviteAdmin }) {
  return (
    <div className="grid gap-4 [&>*]:min-w-0">
      <Carte titre="Dernières requêtes">
        <p className="mb-2 text-[12px] text-muted">Le texte des questions n’est jamais enregistré : seuls le type, le résultat et la durée le sont.</p>
        <div className="max-h-[520px] overflow-auto">
          <table className="w-full min-w-[640px] text-left text-[12px]">
            <thead className="sticky top-0 bg-surface text-muted">
              <tr><th className="py-1 font-normal">Date</th><th className="font-normal">Type</th><th className="font-normal">Matière</th><th className="font-normal">Résultat</th><th className="font-normal">Recherche</th><th className="font-normal">Modèle</th><th className="font-normal">Durée</th></tr>
            </thead>
            <tbody>
              {a.requetes.map((r, i) => (
                <tr key={i} className="border-t border-line-soft">
                  <td className="py-1.5 whitespace-nowrap">{heure(r.ts)}</td>
                  <td>{r.route === 'chat' ? `Question · ${r.mode}` : r.route === 'quiz' ? `Quiz · ${r.format} (${r.obtenu})` : r.route}</td>
                  <td>{r.matiere ?? '-'}</td>
                  <td>{r.statut ?? '-'}</td>
                  <td>{r.recherche ?? '-'}</td>
                  <td>{r.modele ?? '-'}</td>
                  <td className="whitespace-nowrap">{r.duree_ms != null ? `${(r.duree_ms / 1000).toFixed(1)} s` : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!a.requetes.length && <p className="py-4 text-center text-[13px] text-muted">Aucune requête enregistrée.</p>}
        </div>
      </Carte>
      <Carte titre="Erreurs du modèle">
        {a.erreurs.length ? (
          <ul className="grid gap-2 text-[12px]">
            {a.erreurs.map((e, i) => (
              <li key={i} className="rounded-lg bg-cream px-3 py-2 text-[#746347]"><b>{heure(e.ts)}</b> · {e.route} · {e.detail}</li>
            ))}
          </ul>
        ) : <p className="text-[13px] text-muted">Aucune erreur enregistrée.</p>}
      </Carte>
    </div>
  )
}

// --- Serveur -------------------------------------------------------------------------

function Serveur({ s }: { s: ServeurAdmin }) {
  const etat = { ok: <Etat niveau="ok">opérationnel</Etat>, degrade: <Etat niveau="attention">erreurs fréquentes</Etat>, inconnu: <Etat niveau="neutre">pas encore d’appel</Etat> }[s.etat_modele]
  const memSys = s.memoire_systeme
  return (
    <div className="grid gap-4 desk:grid-cols-2 [&>*]:min-w-0">
      <Carte titre="Service">
        <dl className="grid grid-cols-[150px_1fr] gap-y-2 text-[13px]">
          <dt className="text-muted">État</dt><dd><Etat niveau="ok">en ligne</Etat></dd>
          <dt className="text-muted">Démarré depuis</dt><dd>{duree(s.uptime_service_s)}</dd>
          <dt className="text-muted">Version</dt><dd>{s.version ?? 'non renseignée'}</dd>
          <dt className="text-muted">Serveur allumé depuis</dt><dd>{duree(s.uptime_systeme_s)}</dd>
          <dt className="text-muted">Système</dt><dd>{s.systeme} · Python {s.python}</dd>
          <dt className="text-muted">Processeurs / charge</dt><dd>{s.processeurs ?? '-'} · {s.charge ? s.charge.map((c) => c.toFixed(2)).join(' / ') : '-'}</dd>
        </dl>
      </Carte>
      <Carte titre="Ressources">
        <div className="grid gap-4">
          {memSys && <Jauge libelle="Mémoire du serveur" utilise={memSys.total - memSys.disponible} total={memSys.total} />}
          <Jauge libelle="Disque" utilise={s.disque.total - s.disque.libre} total={s.disque.total} />
          <p className="text-[12px] text-muted">Mémoire utilisée par Lexia : {octets(s.memoire_service)}</p>
        </div>
      </Carte>
      <Carte titre="Modèle de réponse (Gemini)">
        <div className="mb-3">{etat}</div>
        <dl className="grid grid-cols-[150px_1fr] gap-y-2 text-[13px]">
          {Object.entries(s.modeles).map(([k, v]) => (
            <Fragment key={k}><dt className="text-muted capitalize">{k}</dt><dd className="break-all">{Array.isArray(v) ? v.join(', ') : v ?? '-'}</dd></Fragment>
          ))}
        </dl>
      </Carte>
      <Carte titre="Corpus de recherche">
        <dl className="grid grid-cols-[150px_1fr] gap-y-2 text-[13px]">
          <dt className="text-muted">Moteur</dt><dd>{s.index.moteur}</dd>
          <dt className="text-muted">Passages</dt><dd>{s.index.passages.toLocaleString('fr-FR')}</dd>
          <dt className="text-muted">Embeddings</dt><dd>{s.index.embeddings.toLocaleString('fr-FR')} {s.index.couverture != null && `(${Math.round(s.index.couverture * 100)} %)`}</dd>
        </dl>
      </Carte>
    </div>
  )
}

// --- Page ----------------------------------------------------------------------------

export function Admin() {
  const { profil } = useSession()
  const [onglet, setOnglet] = useState<Onglet>('apercu')
  const [stats, setStats] = useState<StatsAdmin | null>(null)
  const [activite, setActivite] = useState<ActiviteAdmin | null>(null)
  const [serveur, setServeur] = useState<ServeurAdmin | null>(null)
  const [erreur, setErreur] = useState<string | null>(null)
  const [maj, setMaj] = useState<Date | null>(null)

  const charger = useCallback(() => {
    Promise.all([api.admin.stats(), api.admin.activite(), api.admin.serveur()])
      .then(([s, a, v]) => { setStats(s); setActivite(a); setServeur(v); setMaj(new Date()); setErreur(null) })
      .catch((e) => setErreur(e instanceof ApiError ? e.message : 'Chargement impossible.'))
  }, [])

  useEffect(() => {
    charger()
    const t = window.setInterval(charger, 30000)
    return () => window.clearInterval(t)
  }, [charger])

  if (!profil) return null
  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-surface/70">
        <div className="mx-auto flex h-16 max-w-[1240px] items-center justify-between gap-3 px-4 tab:px-6">
          <div className="flex items-center gap-2.5">
            <Lien href="/" aria-label="Accueil" className="grid size-[31px] place-items-center rounded-[9px] bg-forest font-display text-[19px] text-white">L</Lien>
            <span className="font-display text-[18px] tab:text-[20px]">Administration</span>
          </div>
          <div className="flex items-center gap-2">
            <Lien href="/app" className={`${boutonSecondaire} !py-2`}>Panel</Lien>
            <span className="hidden tab:block"><Lien href="/compte" className={`${boutonSecondaire} !py-2`}>Mon compte</Lien></span>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-[1240px] px-4 py-6 tab:px-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <nav aria-label="Sections de l’administration" className="flex flex-wrap gap-1 rounded-lg bg-side p-1">
            {ONGLETS.map((o) => (
              <button key={o.id} type="button" onClick={() => setOnglet(o.id)} aria-current={onglet === o.id ? 'page' : undefined}
                className={`rounded-md px-3 py-1.5 text-[13px] ${onglet === o.id ? 'bg-surface font-semibold text-forest shadow-sm' : 'text-[#565f59] hover:text-forest'}`}>
                {o.label}
              </button>
            ))}
          </nav>
          <div className="flex items-center gap-2 text-[12px] text-muted">
            {maj && <span>Mis à jour à {maj.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>}
            <button type="button" onClick={charger} className="rounded-md border border-line px-2 py-1 hover:text-forest">Actualiser</button>
          </div>
        </div>
        {erreur && <p role="alert" className="mb-4 rounded-lg bg-[#f6e9e4] px-3 py-2 text-[13px] text-[#8c4a36]">{erreur}</p>}
        {onglet === 'clients' ? <Clients moi={profil.email} />
          : !stats || !activite || !serveur ? (
            <div className="grid animate-pulse gap-3 desk:grid-cols-3" aria-label="Chargement">{[0, 1, 2].map((i) => <div key={i} className="h-28 rounded-xl bg-[#ece9e0]" />)}</div>
          ) : onglet === 'apercu' ? <Apercu s={stats} />
            : onglet === 'activite' ? <Activite a={activite} />
              : <Serveur s={serveur} />}
      </main>
    </div>
  )
}
