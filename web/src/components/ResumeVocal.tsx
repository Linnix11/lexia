// Resume vocal d'une reponse, d'une fiche, d'un cours depose ou recupere (D106, docs/resumes-vocaux.md).
// Le serveur redige le texte ; le navigateur le lit (Web Speech API), phrase par phrase, sans cout serveur.
// D141 : plan du resume en parties cliquables, partie precedente ou suivante, temps restant, reprise la ou
// l'etudiant s'est arrete (resume garde dans l'onglet), vitesse et voix retenues, ecran garde allume pendant la
// lecture, transcription a telecharger.
import { useEffect, useMemo, useRef, useState } from 'react'
import { api, ApiError, type DemandeResume, type ResumeVocal as Resume } from '../lib/api'
import { useFocusSection } from '../lib/focusSection'
import { useSessionFacultative } from '../state/session'
import { Chargement } from './Chargement'
import {
  cleResume, compterMots, decouperPhrases, dureeLisible, ecrireReglages, garderEcranAllume, garderResume, intertitre,
  lireReglages, lireResumeGarde, MOTS_PAR_MINUTE, nomDeFichier, prendreLaMain, rendreLaMain, synthese, transcription,
  voixFrancaises,
} from '../lib/voix'

const VITESSES = [0.75, 1, 1.25, 1.5]
const AVERTISSEMENT = 'Résumé généré automatiquement : il peut contenir des erreurs. Vérifiez avec les textes et les sources citées.'
const virgule = (v: number) => String(v).replace('.', ',')
const pluriel = (n: number, mot: string) => `${n} ${mot}${n > 1 ? 's' : ''}`

/** demande : construite au clic (texte de la reponse, identifiant du cours). */
export function ResumeVocal({ demande, libelle = 'Écouter un résumé' }: { demande: () => DemandeResume; libelle?: string }) {
  const compte = useSessionFacultative()?.profil?.email ?? ''
  const [cle, setCle] = useState(() => cleResume(demande()))
  const [dejaPret] = useState(() => lireResumeGarde(compte, cle) !== null)
  const [ouvert, setOuvert] = useState(false)
  const [resume, setResume] = useState<Resume | null>(null)
  const [repris, setRepris] = useState(false) // resume garde dans l'onglet : pas decompte une seconde fois
  const [chargement, setChargement] = useState(false)
  const [erreur, setErreur] = useState<string | null>(null)
  const [lecture, setLecture] = useState<'arret' | 'lecture' | 'pause'>('arret')
  const [position, setPosition] = useState(0)
  const [vitesse, setVitesse] = useState(() => lireReglages().vitesse)
  const [voix, setVoix] = useState<SpeechSynthesisVoice[]>([])
  const [nomVoix, setNomVoix] = useState(() => lireReglages().voix)
  const jeton = useRef(0) // chaque enonce lance porte un numero : la fin d'un enonce annule est ignoree
  const enLecture = useRef(false)
  const moi = useRef({})
  const s = synthese()
  const { titre, ouvreur } = useFocusSection(ouvert)

  const paragraphes = useMemo(() => decouperPhrases(resume?.paragraphes ?? []), [resume])
  const phrases = useMemo(() => paragraphes.flat(), [paragraphes])
  // Rang de la premiere phrase de chaque partie ; mots restants a partir de chaque phrase (temps restant)
  const debuts = useMemo(() => {
    const d: number[] = []
    paragraphes.forEach((_, p) => d.push(p ? d[p - 1] + paragraphes[p - 1].length : 0))
    return d
  }, [paragraphes])
  const motsApres = useMemo(() => {
    const n = phrases.map(compterMots)
    return n.map((_, i) => n.slice(i).reduce((a, b) => a + b, 0))
  }, [phrases])
  let partie = 0
  debuts.forEach((d, p) => { if (d <= position) partie = p })
  const voixChoisie = voix.find((v) => v.name === nomVoix) ?? voix[0] ?? null
  const enCours = lecture !== 'arret'

  // Voix chargees de facon asynchrone par certains navigateurs (Chrome) : evenement voiceschanged.
  useEffect(() => {
    if (!s) return
    const lire = () => setVoix(voixFrancaises(s.getVoices()))
    lire()
    s.addEventListener?.('voiceschanged', lire)
    return () => s.removeEventListener?.('voiceschanged', lire)
  }, [s])

  // Position gardee avec le resume : rouvert apres un changement de page, il reprend a cette phrase.
  useEffect(() => {
    if (resume) garderResume(compte, { cle, resume, position })
  }, [compte, cle, resume, position])

  // Telephone : ecran garde allume pendant la lecture ; de retour sur l'onglet, une lecture coupee par le
  // systeme (ecran verrouille, autre application) passe en pause a la phrase ou elle s'est arretee.
  useEffect(() => {
    if (lecture !== 'lecture') return
    let relacher: (() => void) | null = null
    let fini = false
    const prendre = () => { garderEcranAllume().then((r) => { if (fini) r?.(); else relacher = r }) }
    prendre()
    const visible = () => {
      if (document.visibilityState !== 'visible') return
      if (s && (s.paused || (!s.speaking && !s.pending))) pause()
      else prendre()
    }
    document.addEventListener('visibilitychange', visible)
    return () => {
      fini = true
      relacher?.()
      document.removeEventListener('visibilitychange', visible)
    }
  }, [lecture]) // eslint-disable-line react-hooks/exhaustive-deps

  const suspendre = () => {
    jeton.current += 1
    if (enLecture.current) s?.cancel()
    enLecture.current = false
  }
  const pause = () => { suspendre(); setLecture('pause') }
  useEffect(() => () => {
    suspendre()
    rendreLaMain(moi.current)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const parler = (i: number, debit = vitesse, v: SpeechSynthesisVoice | null = voixChoisie) => {
    if (!s) return
    suspendre()
    if (i >= phrases.length) {
      setLecture('arret')
      setPosition(0)
      return
    }
    prendreLaMain(moi.current, pause)
    const n = jeton.current
    const u = new SpeechSynthesisUtterance(phrases[i])
    u.lang = v?.lang ?? 'fr-FR'
    if (v) u.voice = v
    u.rate = debit
    u.onend = () => { if (jeton.current === n) parler(i + 1, debit, v) }
    // Enonce coupe (systeme, autre onglet) : en pause sur cette phrase, « Reprendre » y repart
    u.onerror = () => { if (jeton.current === n) { enLecture.current = false; setLecture('pause') } }
    enLecture.current = true
    setPosition(i)
    setLecture('lecture')
    s.speak(u)
  }

  /** Aller a une phrase : lue tout de suite si la lecture est en cours (ou demandee), sinon prete a reprendre. */
  const aller = (i: number, lire = lecture === 'lecture') => {
    if (lire && s) return parler(i)
    suspendre()
    setPosition(i)
    setLecture(i > 0 ? 'pause' : 'arret')
  }

  const charger = async () => {
    setOuvert(true)
    if (resume || chargement) return
    const d = demande()
    const c = cleResume(d)
    setCle(c)
    const garde = lireResumeGarde(compte, c)
    if (garde) {
      setResume(garde.resume)
      setRepris(true)
      setPosition(Math.max(0, garde.position))
      setLecture(garde.position > 0 ? 'pause' : 'arret')
      return
    }
    setChargement(true)
    setErreur(null)
    try {
      setResume(await api.resumeVocal(d))
    } catch (e) {
      setErreur(e instanceof ApiError ? e.message : 'Le résumé n’a pas pu être préparé.')
    } finally {
      setChargement(false)
    }
  }

  // Fermer met en pause : rouvert, le resume reprend a la meme phrase.
  const fermer = () => { if (lecture === 'lecture') pause(); setOuvert(false) }

  const telecharger = () => {
    if (!resume) return
    const texte = transcription(resume.titre, resume.paragraphes, resume.intertitres, resume.avertissement || AVERTISSEMENT)
    const url = URL.createObjectURL(new Blob([texte], { type: 'text/plain;charset=utf-8' }))
    const a = document.createElement('a')
    a.href = url
    a.download = nomDeFichier(resume.titre)
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  const reglerVitesse = (v: number) => {
    setVitesse(v)
    ecrireReglages({ vitesse: v, voix: nomVoix })
    if (lecture === 'lecture') parler(position, v)
  }
  const reglerVoix = (nom: string) => {
    setNomVoix(nom)
    ecrireReglages({ vitesse, voix: nom })
    if (lecture === 'lecture') parler(position, vitesse, voix.find((x) => x.name === nom) ?? null)
  }

  if (!ouvert)
    return (
      <button ref={ouvreur} type="button" onClick={charger}
        className="min-h-8 rounded-full border border-line px-3 text-[12px] text-forest hover:border-[#9eafa3] pointer-coarse:min-h-11">
        {dejaPret || resume ? 'Reprendre le résumé' : libelle}
      </button>
    )

  const bouton = 'min-h-8 rounded-[7px] border border-line bg-white px-2.5 text-[12px] text-forest hover:border-[#9eafa3] disabled:opacity-50 pointer-coarse:min-h-11'
  const intitules = resume ? resume.paragraphes.map((_, p) => intertitre(resume.paragraphes, resume.intertitres, p)) : []
  const restant = Math.round(((motsApres[position] ?? 0) * 60) / (MOTS_PAR_MINUTE * vitesse))
  return (
    <section aria-label="Résumé vocal" className="mt-2 w-full rounded-[10px] border border-[#cfd9d1] bg-[#f6f8f3] p-3 text-[13px]">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 ref={titre} tabIndex={-1} className="text-[12px] font-bold tracking-[1.4px] text-forest uppercase">Résumé vocal</h4>
        <button type="button" onClick={fermer} className="min-h-8 px-1 text-[12px] text-muted hover:text-forest pointer-coarse:min-h-11">Fermer</button>
      </div>
      {chargement && (
        <Chargement className="mt-2" duree="jusqu’à une minute"
          etapes={['Lecture du contenu…', 'Rédaction du résumé…', 'Mise en forme pour l’écoute…', 'Presque prêt…']} />
      )}
      {erreur && <p role="alert" className="mt-2 text-[#8c4a36]">{erreur}</p>}
      {resume && !resume.paragraphes.length && <p role="alert" className="mt-2 text-[#8c4a36]">{resume.message}</p>}
      {resume && resume.paragraphes.length > 0 && (
        <>
          <p className="mt-1 text-[14px] font-semibold">{resume.titre}</p>
          <p className="text-[12px] text-muted">
            Environ {dureeLisible(resume.duree_estimee_s)} à vitesse normale, en {pluriel(resume.paragraphes.length, 'partie')}
            {resume.partiel && ' · Résumé du début du document, trop long pour être résumé en entier'}
            {repris ? ' · Déjà préparé : il ne compte pas une seconde fois dans votre limite du jour'
              : ` · ${resume.restants} résumé(s) restant(s) aujourd’hui`}
          </p>
          {s ? (
            <>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                {lecture === 'lecture' ? (
                  <button type="button" onClick={pause} className={`${bouton} font-semibold`}>Pause</button>
                ) : (
                  <button type="button" onClick={() => parler(position)} className={`${bouton} font-semibold`}>
                    {lecture === 'pause' ? 'Reprendre' : 'Écouter'}
                  </button>
                )}
                <button type="button" onClick={() => aller(debuts[partie - 1] ?? 0)} disabled={partie === 0}
                  aria-label="Partie précédente" className={bouton}>‹ Précédente</button>
                <button type="button" onClick={() => aller(debuts[partie + 1])} disabled={partie >= debuts.length - 1}
                  aria-label="Partie suivante" className={bouton}>Suivante ›</button>
                <button type="button" onClick={() => { suspendre(); setLecture('arret'); setPosition(0) }}
                  disabled={lecture === 'arret' && position === 0} className={bouton}>Arrêter</button>
                <label className="flex items-center gap-1 text-[12px] text-muted">
                  Vitesse
                  <select value={vitesse} onChange={(e) => reglerVitesse(Number(e.target.value))}
                    className="min-h-8 rounded-[6px] border border-line bg-white px-1 text-ink pointer-coarse:min-h-11">
                    {VITESSES.map((v) => <option key={v} value={v}>{virgule(v)}×</option>)}
                  </select>
                </label>
                {voix.length > 1 && (
                  <label className="flex items-center gap-1 text-[12px] text-muted">
                    Voix
                    <select value={voixChoisie?.name ?? ''} onChange={(e) => reglerVoix(e.target.value)}
                      className="min-h-8 max-w-[160px] rounded-[6px] border border-line bg-white px-1 text-ink pointer-coarse:min-h-11">
                      {voix.map((v) => <option key={v.name} value={v.name}>{v.name}</option>)}
                    </select>
                  </label>
                )}
              </div>
              <p className="mt-1.5 text-[12px] text-muted">
                {enCours || position > 0
                  ? `Partie ${partie + 1} sur ${paragraphes.length} : ${intitules[partie]} · encore environ `
                  : `À la vitesse ${virgule(vitesse)}× : environ `}
                <span className="whitespace-nowrap">{dureeLisible(restant)}</span>
              </p>
            </>
          ) : (
            <p className="mt-2 text-[12px] text-muted">La lecture à voix haute n’est pas disponible dans ce navigateur : voici le résumé à lire.</p>
          )}
          {s && voixChoisie && !voixChoisie.localService && (
            <p className="mt-1 text-[12px] text-muted">
              Lecture par une voix en ligne de votre navigateur : le texte du résumé est envoyé à son éditeur (par
              exemple Google pour Chrome) : aucune voix française n’est installée sur cet appareil.
            </p>
          )}
          {s && voix.length === 0 && (
            <p className="mt-1 text-[12px] text-muted">Aucune voix française sur cet appareil : la voix par défaut lit le texte.</p>
          )}
          <nav aria-label="Plan du résumé" className="mt-2">
            <ol className="grid gap-0.5">
              {intitules.map((t, p) => {
                const actuelle = (enCours || position > 0) && p === partie
                return (
                  <li key={p}>
                    <button type="button" aria-current={actuelle ? 'step' : undefined}
                      onClick={() => (s ? aller(debuts[p], true)
                        : document.getElementById(`${cle}-p${p}`)?.scrollIntoView({ block: 'start' }))}
                      className={`flex min-h-8 w-full items-center gap-2 rounded-[7px] px-2 text-left text-[13px] hover:bg-white pointer-coarse:min-h-11 ${actuelle ? 'bg-mint font-semibold text-forest' : 'text-ink'}`}>
                      <span className="w-5 shrink-0 text-[12px] text-muted">{p + 1}.</span>
                      <span className="min-w-0 flex-1">{t}</span>
                      <span className="shrink-0 text-[12px] text-muted">
                        {dureeLisible(Math.round(((motsApres[0] - (motsApres[debuts[p]] ?? 0)) * 60) / (MOTS_PAR_MINUTE * vitesse)))}
                      </span>
                    </button>
                  </li>
                )
              })}
            </ol>
          </nav>
          <div className="mt-3 grid max-w-[75ch] gap-3 text-[14px] leading-[1.65]">
            {paragraphes.map((ps, p) => (
              <div key={p} id={`${cle}-p${p}`}>
                <h5 className="mb-0.5 text-[12px] font-bold text-forest">{intitules[p]}</h5>
                <p>
                  {ps.map((phrase, j) => {
                    const i = debuts[p] + j
                    const lue = enCours && i === position
                    return (
                      <span key={j} aria-current={lue ? 'true' : undefined}
                        onClick={s ? () => aller(i, true) : undefined}
                        className={`${lue ? 'rounded bg-mint' : ''} ${s ? 'cursor-pointer' : ''}`}>
                        {phrase}{' '}
                      </span>
                    )
                  })}
                </p>
              </div>
            ))}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button type="button" onClick={telecharger} className={bouton}>Télécharger le texte</button>
            <span className="text-[12px] text-muted">pour le relire hors connexion</span>
          </div>
          <p className="mt-2 text-[12px] leading-[1.45] text-[#746347]">{resume.avertissement || AVERTISSEMENT}</p>
        </>
      )}
    </section>
  )
}
