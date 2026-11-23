// Resume vocal d'une reponse, d'une fiche, d'un cours depose ou recupere (D106, docs/resumes-vocaux.md).
// Le serveur redige le texte ; le navigateur le lit (Web Speech API), phrase par phrase, sans cout serveur.
import { useEffect, useMemo, useRef, useState } from 'react'
import { api, ApiError, type DemandeResume, type ResumeVocal as Resume } from '../lib/api'
import { decouperPhrases, dureeLisible, prendreLaMain, rendreLaMain, synthese, voixFrancaises } from '../lib/voix'

const VITESSES = [0.75, 1, 1.25, 1.5]
const AVERTISSEMENT = 'Résumé généré automatiquement : il peut contenir des erreurs. Vérifiez avec les textes et les sources citées.'


/** demande : construite au clic (texte de la reponse, identifiant du cours). */
export function ResumeVocal({ demande, libelle = 'Écouter un résumé' }: { demande: () => DemandeResume; libelle?: string }) {
  const [ouvert, setOuvert] = useState(false)
  const [resume, setResume] = useState<Resume | null>(null)
  const [chargement, setChargement] = useState(false)
  const [erreur, setErreur] = useState<string | null>(null)
  const [lecture, setLecture] = useState<'arret' | 'lecture' | 'pause'>('arret')
  const [position, setPosition] = useState(0)
  const [vitesse, setVitesse] = useState(1)
  const [voix, setVoix] = useState<SpeechSynthesisVoice[]>([])
  const [nomVoix, setNomVoix] = useState('')
  const jeton = useRef(0) // chaque enonce lance porte un numero : la fin d'un enonce annule est ignoree
  const enLecture = useRef(false)
  const moi = useRef({})
  const s = synthese()

  const paragraphes = useMemo(() => decouperPhrases(resume?.paragraphes ?? []), [resume])
  const phrases = useMemo(() => paragraphes.flat(), [paragraphes])
  const voixChoisie = voix.find((v) => v.name === nomVoix) ?? voix[0] ?? null

  // Voix chargees de facon asynchrone par certains navigateurs (Chrome) : evenement voiceschanged.
  useEffect(() => {
    if (!s) return
    const lire = () => setVoix(voixFrancaises(s.getVoices()))
    lire()
    s.addEventListener?.('voiceschanged', lire)
    return () => s.removeEventListener?.('voiceschanged', lire)
  }, [s])

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
    u.onerror = () => { if (jeton.current === n) { enLecture.current = false; setLecture('arret') } }
    enLecture.current = true
    setPosition(i)
    setLecture('lecture')
    s.speak(u)
  }

  const charger = async () => {
    setOuvert(true)
    if (resume || chargement) return
    setChargement(true)
    setErreur(null)
    try {
      setResume(await api.resumeVocal(demande()))
    } catch (e) {
      setErreur(e instanceof ApiError ? e.message : 'Le résumé n’a pas pu être préparé.')
    } finally {
      setChargement(false)
    }
  }

  const fermer = () => { suspendre(); setLecture('arret'); setOuvert(false) }

  if (!ouvert)
    return (
      <button type="button" onClick={charger}
        className="min-h-6 rounded-full border border-line px-2.5 text-[11px] text-forest hover:border-[#9eafa3]">
        {libelle}
      </button>
    )

  const bouton = 'min-h-7 rounded-[7px] border border-line px-2.5 text-[11px] text-forest hover:border-[#9eafa3] disabled:opacity-50'
  return (
    <section aria-label="Résumé vocal" className="mt-2 w-full rounded-[10px] border border-[#cfd9d1] bg-[#f6f8f3] p-3 text-[12px]">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="text-[10px] font-bold tracking-[1.4px] text-forest uppercase">Résumé vocal</h4>
        <button type="button" onClick={fermer} className="text-[11px] text-muted hover:text-forest">Fermer</button>
      </div>
      {chargement && <p role="status" className="mt-2 text-muted">Préparation du résumé… (jusqu’à une minute)</p>}
      {erreur && <p role="alert" className="mt-2 text-[#8c4a36]">{erreur}</p>}
      {resume && !resume.paragraphes.length && <p role="alert" className="mt-2 text-[#8c4a36]">{resume.message}</p>}
      {resume && resume.paragraphes.length > 0 && (
        <>
          <p className="mt-1 text-[12.5px] font-semibold">{resume.titre}</p>
          <p className="text-[10px] text-muted">
            Environ {dureeLisible(resume.duree_estimee_s)} à vitesse normale
            {resume.partiel && ' · Résumé du début du document, trop long pour être résumé en entier'}
            {` · ${resume.restants} résumé(s) restant(s) aujourd’hui`}
          </p>
          {s ? (
            <div className="mt-2 flex flex-wrap items-center gap-2">
              {lecture === 'lecture' ? (
                <button type="button" onClick={pause} className={bouton}>Pause</button>
              ) : (
                <button type="button" onClick={() => parler(position)} className={bouton}>
                  {lecture === 'pause' ? 'Reprendre' : 'Écouter'}
                </button>
              )}
              <button type="button" onClick={() => { suspendre(); setLecture('arret'); setPosition(0) }}
                disabled={lecture === 'arret' && position === 0} className={bouton}>Arrêter</button>
              <label className="flex items-center gap-1 text-[11px] text-muted">
                Vitesse
                <select value={vitesse} className="rounded-[6px] border border-line bg-white px-1 py-0.5 text-ink"
                  onChange={(e) => {
                    const v = Number(e.target.value)
                    setVitesse(v)
                    if (lecture === 'lecture') parler(position, v)
                  }}>
                  {VITESSES.map((v) => <option key={v} value={v}>{String(v).replace('.', ',')}×</option>)}
                </select>
              </label>
              {voix.length > 1 && (
                <label className="flex items-center gap-1 text-[11px] text-muted">
                  Voix
                  <select value={voixChoisie?.name ?? ''} className="max-w-[160px] rounded-[6px] border border-line bg-white px-1 py-0.5 text-ink"
                    onChange={(e) => {
                      setNomVoix(e.target.value)
                      const v = voix.find((x) => x.name === e.target.value) ?? null
                      if (lecture === 'lecture') parler(position, vitesse, v)
                    }}>
                    {voix.map((v) => <option key={v.name} value={v.name}>{v.name}</option>)}
                  </select>
                </label>
              )}
            </div>
          ) : (
            <p className="mt-2 text-[11px] text-muted">La lecture à voix haute n’est pas disponible dans ce navigateur : voici le résumé à lire.</p>
          )}
          {s && voixChoisie && !voixChoisie.localService && (
            <p className="mt-1 text-[10px] text-muted">
              Lecture par une voix en ligne de votre navigateur : le texte du résumé est envoyé à son éditeur (par
              exemple Google pour Chrome) : aucune voix française n’est installée sur cet appareil.
            </p>
          )}
          {s && voix.length === 0 && (
            <p className="mt-1 text-[10px] text-muted">Aucune voix française sur cet appareil : la voix par défaut lit le texte.</p>
          )}
          <div className="mt-2 grid max-w-[75ch] gap-1.5 leading-[1.6]">
            {paragraphes.map((ps, p) => {
              const debut = paragraphes.slice(0, p).reduce((n, x) => n + x.length, 0)
              return (
                <p key={p}>
                  {ps.map((phrase, j) => {
                    const i = debut + j
                    const lue = lecture !== 'arret' && i === position
                    return (
                      <span key={j} aria-current={lue ? 'true' : undefined}
                        onClick={s ? () => parler(i) : undefined}
                        className={`${lue ? 'rounded bg-mint' : ''} ${s ? 'cursor-pointer' : ''}`}>
                        {phrase}{' '}
                      </span>
                    )
                  })}
                </p>
              )
            })}
          </div>
          <p className="mt-2 text-[10px] leading-[1.4] text-[#746347]">{resume.avertissement || AVERTISSEMENT}</p>
        </>
      )}
    </section>
  )
}
