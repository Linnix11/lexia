import { useEffect, useRef, useState, type FormEvent } from 'react'
import type { Mode } from '../lib/api'
import { MODES } from '../lib/modes'
import { Lien } from '../lib/router'
import { useApp } from '../state/contexte'
import { Reponse } from './Reponse'

const SUGGESTIONS: { label: string; question: string; mode: Mode }[] = [
  { label: 'Hiérarchie des normes', question: 'Explique-moi la hiérarchie des normes', mode: 'expliquer' },
  { label: 'Fiche de révision', question: 'Fais-moi une fiche sur la responsabilité civile', mode: 'fiche' },
  { label: 'Méthode du cas pratique', question: 'Aide-moi à structurer un cas pratique', mode: 'cas_pratique' },
]

function Attente() {
  return (
    <div className="rounded-[10px] bg-[#f6f4ee] px-4 py-3.5" aria-label="Lexia recherche dans les sources">
      <p className="mb-2.5 text-[11px] text-muted">Lexia cherche dans les textes et la jurisprudence…</p>
      <div className="grid animate-pulse gap-2">
        <div className="h-3 w-2/3 rounded bg-[#e7e4da]" />
        <div className="h-3 w-full rounded bg-[#ece9e0]" />
        <div className="h-3 w-5/6 rounded bg-[#ece9e0]" />
      </div>
    </div>
  )
}

export function Chat({ complet = false }: { complet?: boolean }) {
  const { messages, envoyer, occupe, matiere, setMatiere, matieres, effacer } = useApp()
  const [texte, setTexte] = useState('')
  const [mode, setMode] = useState<Mode>('expliquer')
  const fin = useRef<HTMLDivElement>(null)

  const derniereEtat = messages.at(-1)?.etat
  useEffect(() => {
    fin.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [messages.length, derniereEtat])

  const soumettre = (e: FormEvent) => {
    e.preventDefault()
    if (!texte.trim() || occupe) return
    envoyer(texte, mode)
    setTexte('')
  }

  return (
    <div className="flex min-h-[340px] min-w-0 flex-1 flex-col">
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
              {matieres.map((m) => (
                <option key={m.id} value={m.id}>{m.libelle}</option>
              ))}
            </select>
          </label>
        </div>
      )}

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
        <div aria-live="polite" className={`mb-3.5 grid min-w-0 gap-2.5 border-t border-line pt-[15px] ${complet ? '' : 'max-h-[560px] overflow-y-auto pr-1'}`}>
          {messages.map((m) => (
            <div key={m.id} className="grid min-w-0 gap-2.5">
              <div className="ml-auto max-w-[92%] rounded-[10px] bg-[#edf1eb] px-3.5 py-3 text-[12px] leading-[1.55]">
                {m.question}
                {m.mode !== 'expliquer' && (
                  <span className="ml-2 text-[10px] text-muted">· {MODES.find((x) => x.id === m.mode)?.label}</span>
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

      <form
        onSubmit={soumettre}
        className="mt-auto flex gap-[9px] rounded-[10px] border border-[#d9ddd5] bg-white p-[7px] focus-within:border-[#809b89] focus-within:shadow-[0_0_0_3px_#315e4b13]"
      >
        <label htmlFor={complet ? 'question-complete' : 'question'} className="sr-only">Votre question</label>
        <input
          id={complet ? 'question-complete' : 'question'}
          value={texte}
          onChange={(e) => setTexte(e.target.value)}
          placeholder="Écrivez votre question de droit…"
          autoComplete="off"
          maxLength={2000}
          className="min-w-0 flex-1 border-0 px-2 py-[7px] text-[12px] text-ink outline-none"
        />
        <button
          type="submit"
          disabled={occupe || !texte.trim()}
          className="rounded-[7px] bg-forest px-3.5 text-[12px] text-white hover:bg-forest-dark disabled:opacity-50"
        >
          {occupe ? 'Recherche…' : 'Envoyer ↗'}
        </button>
      </form>
      <div className="mx-0.5 mt-2.5 flex justify-between gap-2 text-[10px] text-[#8a9089]">
        <span>Réponses générées par une intelligence artificielle (modèle Gemini de Google) · vérifiez toujours la règle applicable et la version des textes.</span>
        {messages.length > 0 && !occupe && (
          <button type="button" onClick={effacer} className="shrink-0 hover:text-forest">Effacer la conversation</button>
        )}
      </div>
    </div>
  )
}
