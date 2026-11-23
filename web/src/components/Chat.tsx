import { useEffect, useLayoutEffect, useRef, useState, type DragEvent, type FormEvent, type KeyboardEvent as ToucheReact } from 'react'
import type { Mode } from '../lib/api'
import { infosMode, MODES } from '../lib/modes'
import { Lien } from '../lib/router'
import { useApp } from '../state/contexte'
import { Reponse } from './Reponse'
import { ChoixCours } from './ChoixCours'
import { ACCEPT, fichiersDeposes } from '../lib/fichiers'
import { DepotRapide } from './MesCours'
import { OptionsMatieres } from './OptionsMatieres'
import { Chargement, Rond } from './Chargement'

const SUGGESTIONS: { label: string; question: string; mode: Mode }[] = [
  { label: 'Hiérarchie des normes', question: 'Explique-moi la hiérarchie des normes', mode: 'expliquer' },
  { label: 'Fiche de révision', question: 'Fais-moi une fiche sur la responsabilité civile', mode: 'fiche' },
  { label: 'Méthode du cas pratique', question: 'Aide-moi à structurer un cas pratique', mode: 'cas_pratique' },
]

function Attente() {
  return (
    <div className="grid gap-2.5">
      <Chargement duree="10 à 30 secondes en général"
        etapes={['Lexia cherche dans les textes et la jurisprudence…', 'Tri des passages les plus utiles…',
          'Rédaction de la réponse…', 'Vérification des sources citées…', 'Encore un instant…']} />
      <div aria-hidden className="grid animate-pulse gap-2 px-1 motion-reduce:animate-none">
        <div className="h-3 w-2/3 rounded bg-[#e7e4da]" />
        <div className="h-3 w-full rounded bg-[#ece9e0]" />
        <div className="h-3 w-5/6 rounded bg-[#ece9e0]" />
      </div>
    </div>
  )
}

export function Chat({ complet = false }: { complet?: boolean }) {
  const { messages, envoyer, occupe, matiere, setMatiere, matieres, effacer, mode: modeChoisi, setMode } = useApp()
  const [texte, setTexte] = useState('')
  // L'assistant complet propose les modes ; la carte de « Mon espace » reste en mode explication.
  const mode = complet ? modeChoisi : 'expliquer'
  const infos = infosMode(mode)
  const fin = useRef<HTMLDivElement>(null)
  // Depot de cours depuis l'assistant : glisser-deposer (fichiers ou dossier), trombone, ou Ctrl/Cmd + Maj + U.
  const choixFichier = useRef<HTMLInputElement>(null)
  const [aDeposer, setADeposer] = useState<File[] | null>(null)
  const [survol, setSurvol] = useState(false)
  useEffect(() => {
    const raccourci = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'u') {
        e.preventDefault()
        choixFichier.current?.click()
      }
    }
    window.addEventListener('keydown', raccourci)
    return () => window.removeEventListener('keydown', raccourci)
  }, [])

  const derniereEtat = messages.at(-1)?.etat
  // Annonce courte pour les lecteurs d'ecran, au lieu de relire toute la conversation (audit du 2026-11-19, WEB-3)
  const dernier = messages.at(-1)
  const annonce = !dernier ? '' : dernier.etat === 'en_cours' ? 'Lexia prépare la réponse.'
    : dernier.etat === 'ok' ? `Réponse prête : ${dernier.reponse?.titre ?? ''}` : `Erreur : ${dernier.erreur ?? ''}`
  // Effacer la conversation en deux temps : rien ne se perd sur un clic involontaire (WEB-20)
  const [confirmerEffacement, setConfirmerEffacement] = useState(false)
  useEffect(() => {
    if (!confirmerEffacement) return
    const t = setTimeout(() => setConfirmerEffacement(false), 5000)
    return () => clearTimeout(t)
  }, [confirmerEffacement])
  useEffect(() => {
    fin.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [messages.length, derniereEtat])

  // Saisie multiligne (audit du 2026-11-16, point 2) : Entree envoie, Maj + Entree passe a la ligne,
  // le champ grandit jusqu'a six lignes environ.
  const champ = useRef<HTMLTextAreaElement>(null)
  useLayoutEffect(() => {
    const el = champ.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }, [texte])
  const auClavier = (e: ToucheReact<HTMLTextAreaElement>) => {
    if (e.key !== 'Enter' || e.shiftKey || e.nativeEvent.isComposing) return
    // Ecran tactile : pas de touche Maj sur le clavier du telephone, Entree va a la ligne et le bouton envoie
    // (audit mobile du 2026-11-18).
    if (window.matchMedia?.('(pointer: coarse)').matches) return
    e.preventDefault()
    e.currentTarget.form?.requestSubmit()
  }

  // Question trop courte : dit au clic, au lieu d'un bouton grise explique par une infobulle (audit WEB-10)
  const [tropCourt, setTropCourt] = useState(false)
  const soumettre = (e: FormEvent) => {
    e.preventDefault()
    if (occupe || !texte.trim()) return
    if (texte.trim().length < 3) return setTropCourt(true)  // l'API exige 3 caracteres (ChatRequest)
    setTropCourt(false)
    envoyer(texte, mode)
    setTexte('')
  }

  const glisser = {
    onDragOver: (e: DragEvent) => {
      if (![...e.dataTransfer.types].includes('Files')) return
      e.preventDefault()
      setSurvol(true)
    },
    onDragLeave: (e: DragEvent) => {
      if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setSurvol(false)
    },
    onDrop: (e: DragEvent) => {
      if (![...e.dataTransfer.types].includes('Files')) return
      e.preventDefault()
      setSurvol(false)
      void fichiersDeposes(e.dataTransfer).then((f) => f.length && setADeposer(f))
    },
  }

  return (
    <div className="relative flex min-h-[340px] min-w-0 flex-1 flex-col" {...glisser}>
      {survol && (
        <div aria-hidden className="pointer-events-none absolute inset-0 z-10 grid place-items-center rounded-[10px] border-2 border-dashed border-forest bg-[#f6f8f3]/90 text-center">
          <p className="font-display text-[19px] text-forest">Déposez votre cours ici<span className="mt-1 block font-sans text-[11px] text-muted">PDF (même scanné), Word, PowerPoint, photo de cours… · un fichier, plusieurs, ou un dossier</span></p>
        </div>
      )}
      {complet && (
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <div role="radiogroup" aria-label="Type d’aide" className="flex flex-wrap gap-1.5">
            {MODES.map((m) => (
              <button
                key={m.id}
                type="button"
                role="radio"
                aria-checked={mode === m.id}
                onClick={() => setMode(m.id)}
                className={`rounded-full border px-2.5 py-1.5 text-[11px] ${
                  mode === m.id ? 'border-forest bg-mint font-semibold text-forest' : 'border-line bg-chip text-[#59615b] hover:border-[#9eafa3]'
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>
          <label className="ml-auto flex items-center gap-1.5 text-[11px] text-muted">
            Matière
            <select
              value={matiere ?? ''}
              onChange={(e) => setMatiere(e.target.value || null)}
              className="rounded-[7px] border border-line bg-white px-2 py-1.5 text-[11px] text-ink"
            >
              <option value="">Toutes</option>
              <OptionsMatieres matieres={matieres} />
            </select>
          </label>
          <p className="w-full text-[11px] text-muted" aria-live="polite">{infos.description}</p>
        </div>
      )}

      {/* Cours depose : disponible depuis « Mon espace » comme depuis l'assistant complet. */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <ChoixCours surDepot={() => choixFichier.current?.click()} />
      </div>

      {messages.length === 0 ? (
        <div className="pt-6 pb-5">
          <h2 className="mb-2 font-display text-[24px] font-normal">Qu’aimeriez-vous travailler&nbsp;?</h2>
          <p className="max-w-[520px] text-[12px] leading-[1.55] text-muted">
            Posez une question de cours ou choisissez un exercice. Chaque réponse s’appuie sur des textes officiels et
            des décisions de justice que vous pouvez ouvrir et vérifier.
          </p>
          <div className="mt-[15px] flex flex-wrap gap-[7px]">
            {SUGGESTIONS.map((s) => (
              <button
                key={s.label}
                type="button"
                onClick={() => envoyer(s.question, s.mode)}
                className="rounded-full border border-line bg-chip px-2.5 py-2 text-[11px] text-[#59615b] hover:border-[#9eafa3] hover:text-forest"
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className={`mb-3.5 grid min-w-0 gap-2.5 border-t border-line pt-[15px] ${complet ? '' : 'tab:max-h-[560px] tab:overflow-y-auto tab:pr-1'}`}>
          {messages.map((m) => (
            <div key={m.id} className="grid min-w-0 gap-2.5">
              <div className="ml-auto max-w-[92%] rounded-[10px] bg-[#edf1eb] px-3.5 py-3 text-[12px] leading-[1.55] whitespace-pre-line">
                {m.question}
                {m.mode !== 'expliquer' && (
                  <span className="ml-2 text-[11px] text-muted">· {MODES.find((x) => x.id === m.mode)?.label}</span>
                )}
              </div>
              {m.etat === 'en_cours' && <Attente />}
              {m.etat === 'erreur' && (
                <div role="alert" className="flex flex-wrap items-center justify-between gap-2 rounded-[10px] border border-[#ecd9c4] bg-cream px-3.5 py-3 text-[12px] text-[#746347]">
                  <span>{m.erreur}</span>
                  {m.statut === 402 ? (
                    <Lien href="/tarifs" className="text-[11px] font-semibold text-forest hover:underline">Voir les formules</Lien>
                  ) : (
                    <button type="button" onClick={() => envoyer(m.question, m.mode)} disabled={occupe}
                      className="text-[11px] font-semibold text-forest hover:underline disabled:opacity-50">
                      Réessayer
                    </button>
                  )}
                </div>
              )}
              {m.etat === 'ok' && m.reponse && <Reponse message={m} />}
            </div>
          ))}
          <div ref={fin} />
        </div>
      )}

      {aDeposer && <DepotRapide key={aDeposer.map((f) => f.name).join('|')} fichiers={aDeposer} onFermer={() => setADeposer(null)} />}
      <form
        onSubmit={soumettre}
        // Contour foret au focus sur tout le formulaire : le champ est en outline-none (audit du 2026-11-23, D2, WCAG 2.4.7)
        className="mt-auto flex gap-[9px] rounded-[10px] border border-[#878f88] bg-white p-[7px] focus-within:border-forest focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-forest"
      >
        <button type="button" onClick={() => choixFichier.current?.click()}
              title="Ajouter un cours (PDF, Word, photo…) · Ctrl/Cmd + Maj + U" aria-label="Ajouter un cours"
          className="rounded-[7px] px-2 text-[16px] text-muted hover:bg-chip hover:text-forest">📎</button>
        <input ref={choixFichier} type="file" multiple accept={ACCEPT} hidden data-testid="ajout-cours"
          onChange={(e) => {
            const f = [...(e.target.files ?? [])]
            if (f.length) setADeposer(f)
            e.target.value = ''
          }} />
        <label htmlFor={complet ? 'question-complete' : 'question'} className="sr-only">Votre question</label>
        <textarea
          ref={champ}
          id={complet ? 'question-complete' : 'question'}
          value={texte}
          onChange={(e) => { setTexte(e.target.value); setTropCourt(false) }}
          onKeyDown={auClavier}
          rows={1}
          placeholder={complet ? infos.placeholder : 'Écrivez votre question de droit…'}
          autoComplete="off"
          maxLength={2000}
          aria-describedby={complet ? 'aide-saisie-complete' : 'aide-saisie'}
          className="min-w-0 flex-1 resize-none self-center border-0 bg-transparent px-2 py-[7px] text-[12px] leading-[1.5] text-ink outline-none"
        />
        <button
          type="submit"
          disabled={occupe}
          // bouton desactive pendant une reponse : son libelle « Recherche… » le dit (audit du 2026-11-18, D8)
          title={occupe ? 'Une réponse est en cours de préparation.' : undefined}
          className="inline-flex items-center gap-1.5 rounded-[7px] bg-forest px-3.5 text-[12px] text-white hover:bg-forest-dark disabled:opacity-50"
        >
          {occupe && <Rond className="h-3.5 w-3.5" />}
          {occupe ? 'Recherche…' : 'Envoyer ↗'}
        </button>
      </form>
      {tropCourt && <p role="alert" className="mx-0.5 mt-2 text-[12px] text-[#8c4a36]">Écrivez au moins 3 caractères.</p>}
      <div className="mx-0.5 mt-2.5 flex justify-between gap-2 text-[12px] text-[#5f6762]">
        <span>
          <span id={complet ? 'aide-saisie-complete' : 'aide-saisie'} className="pointer-coarse:hidden">Entrée pour envoyer, Maj + Entrée pour aller à la ligne. </span>
          Réponses générées par une intelligence artificielle · vérifiez toujours la règle applicable et la version des textes.
        </span>
        {messages.length > 0 && !occupe && (
          <button type="button" className={`shrink-0 hover:text-forest ${confirmerEffacement ? 'font-semibold text-[#8c4a36]' : ''}`}
            onClick={() => {
              if (!confirmerEffacement) return setConfirmerEffacement(true)
              setConfirmerEffacement(false)
              effacer()
            }}>
            {confirmerEffacement ? 'Confirmer l’effacement' : 'Effacer la conversation'}
          </button>
        )}
      </div>
      <p role="status" className="sr-only">{annonce}</p>
    </div>
  )
}
