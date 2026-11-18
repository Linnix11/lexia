import { useState } from 'react'
import { Lien } from '../lib/router'
import type { FormatQuiz, Quiz, ResultatQuestion } from '../lib/api'
import { numeroSource, titreCourt } from '../lib/sources'
import { useDialog } from '../lib/useDialog'
import { useApp } from '../state/contexte'
import { ChoixCours } from './ChoixCours'
import { OptionsMatieres } from './OptionsMatieres'

const FORMATS: { id: FormatQuiz; label: string }[] = [
  { id: 'qcm', label: 'QCM' },
  { id: 'vrai_faux', label: 'Vrai / faux' },
  { id: 'ouvertes', label: 'Questions ouvertes' },
]

const STATUTS: Record<ResultatQuestion['statut'], { texte: string; classe: string }> = {
  correct: { texte: 'Correct', classe: 'bg-mint text-forest' },
  partiel: { texte: 'Partiel', classe: 'bg-cream text-[#8a6537]' },
  incorrect: { texte: 'Incorrect', classe: 'bg-[#f6e9e4] text-[#8c4a36]' },
  non_repondu: { texte: 'Sans réponse', classe: 'bg-chip text-muted' },
  a_verifier: { texte: 'À vérifier', classe: 'bg-chip text-muted' },
}

// Exemple de theme propre a la matiere choisie (audit du 2026-11-16, point 8).
const EXEMPLES: Record<string, string> = {
  introduction_au_droit: 'la hiérarchie des normes',
  droit_constitutionnel: 'la séparation des pouvoirs',
  droit_civil: 'la responsabilité du fait des choses',
  droit_des_contrats: 'les vices du consentement',
  droit_penal: 'l’élément intentionnel de l’infraction',
  procedure_civile: 'la compétence territoriale',
  droit_des_affaires: 'le statut du commerçant',
  droit_social: 'la rupture conventionnelle',
  droit_administratif: 'le recours pour excès de pouvoir',
  libertes_fondamentales: 'le référé-liberté',
  droit_de_la_famille: 'la filiation',
  droit_des_biens: 'la possession',
  droit_fiscal: 'l’impôt sur le revenu',
  finances_publiques: 'le vote de la loi de finances',
}
const exempleTheme = (matiere: string | null) => `Ex. ${matiere && EXEMPLES[matiere] ? EXEMPLES[matiere] : 'les vices du consentement'}`

function bonneReponse(q: Quiz['questions'][number], r: ResultatQuestion): string | null {
  if (typeof r.bonne_reponse === 'number' && q.choix) return q.choix[r.bonne_reponse]
  if (typeof r.bonne_reponse === 'boolean') return r.bonne_reponse ? 'Vrai' : 'Faux'
  return null
}

export function QuizModal() {
  const { quizOuvert, matiere } = useApp()
  if (!quizOuvert) return null
  // une cle par ouverture : le formulaire repart du theme demande ; le dernier questionnaire, lui, est garde
  // dans l'etat de l'application et reapparait a chaque ouverture (audit du 2026-11-16, point 12).
  return <QuizContenu key={quizOuvert.id} themeDemande={quizOuvert.theme} matiereInitiale={matiere} />
}

function QuizContenu({ themeDemande, matiereInitiale }: { themeDemande?: string; matiereInitiale: string | null }) {
  const { fermerQuiz, matieres, ouvrirSource, dernierQuiz, genererQuiz, repondreQuiz, corrigerQuiz, signalerErreurQuiz } = useApp()
  const { parametres, quiz, reponses, correction, etat, erreur, statut } = dernierQuiz
  const ref = useDialog<HTMLDivElement>(true, fermerQuiz)
  const [theme, setTheme] = useState(themeDemande ?? parametres?.theme ?? '')
  const [nombre, setNombre] = useState(parametres?.nombre ?? 5)
  const [format, setFormat] = useState<FormatQuiz>(parametres?.format ?? 'qcm')
  const [mat, setMat] = useState<string | null>(matiereInitiale ?? parametres?.matiere ?? null)
  // Un questionnaire est affiche : le formulaire se replie en une ligne pour laisser la place a l'exercice
  // (audit du 2026-11-16, point 10). Il reste ouvert si l'on arrive avec un nouveau theme a travailler.
  const [reglages, setReglages] = useState(!quiz?.quiz_id || themeDemande !== undefined)

  const generer = () => {
    if (theme.trim().length < 3) {
      signalerErreurQuiz('Indiquez un thème d’au moins 3 caractères.')
      return
    }
    // le questionnaire en cours et ses reponses seraient effaces sans prevenir (audit du 2026-11-18, D9)
    if (quiz?.quiz_id && Object.keys(reponses).length > 0
      && !window.confirm('Remplacer le questionnaire en cours ? Vos réponses et la correction seront effacées.')) return
    genererQuiz({ theme: theme.trim(), nombre, format, matiere: mat })
    setReglages(false)
  }
  const corriger = corrigerQuiz

  const sources = correction?.sources ?? quiz?.sources ?? []
  const champ = 'w-full min-w-0 rounded-[7px] border border-line bg-white p-[9px] text-[12px] text-ink'

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-[#17241d70] p-[18px]"
      onMouseDown={(e) => e.target === e.currentTarget && fermerQuiz()}>
      <div ref={ref} role="dialog" aria-modal="true" aria-labelledby="quiz-titre"
        className="max-h-[90vh] w-full max-w-[640px] overflow-auto rounded-[14px] border border-line bg-surface p-[22px] shadow-[0_20px_70px_#17241d35]">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 id="quiz-titre" className="mb-1.5 font-display text-[25px] font-normal">
              {quiz?.quiz_id ? `Questionnaire · ${quiz.theme}` : 'Créer un questionnaire'}
            </h2>
            <p className="text-[11px] text-muted">Questions générées par une intelligence artificielle à partir des textes et décisions du corpus, chacune reliée à ses sources.</p>
            {!quiz?.quiz_id && <div className="mt-2"><ChoixCours /></div>}
          </div>
          <button type="button" onClick={fermerQuiz} aria-label="Fermer le questionnaire"
            className="rounded-[7px] border border-line px-2.5 py-1.5 text-muted hover:text-ink">✕</button>
        </div>

        {!reglages && quiz?.quiz_id && etat !== 'generation' && (
          <div className="mt-4 mb-3 flex flex-wrap items-center justify-between gap-2 rounded-[9px] bg-[#f6f4ee] px-3 py-2 text-[11px] text-muted">
            <span>
              {quiz.questions.length} question{quiz.questions.length > 1 ? 's' : ''} · {FORMATS.find((f) => f.id === quiz.format)?.label}
              {parametres?.matiere ? ` · ${matieres.find((m) => m.id === parametres.matiere)?.libelle ?? ''}` : ''}
            </span>
            <button type="button" onClick={() => setReglages(true)} className="font-semibold text-forest hover:underline">
              Nouveau questionnaire…
            </button>
          </div>
        )}
        {(reglages || !quiz?.quiz_id || etat === 'generation') && (
        <form className="mt-5 mb-3.5 grid gap-[9px] tab:grid-cols-[1fr_110px_150px]"
          onSubmit={(e) => { e.preventDefault(); generer() }}>
          <label className="grid gap-1.5 text-[11px] text-muted">
            Thème
            <input data-autofocus value={theme} onChange={(e) => setTheme(e.target.value)} placeholder={exempleTheme(mat)} className={champ} />
          </label>
          <label className="grid gap-1.5 text-[11px] text-muted">
            Questions
            <select value={nombre} onChange={(e) => setNombre(Number(e.target.value))} className={champ}>
              {[5, 10, 15].map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
          </label>
          <label className="grid gap-1.5 text-[11px] text-muted">
            Format
            <select value={format} onChange={(e) => setFormat(e.target.value as FormatQuiz)} className={champ}>
              {FORMATS.map((f) => <option key={f.id} value={f.id}>{f.label}</option>)}
            </select>
          </label>
          <label className="grid gap-1.5 text-[11px] text-muted tab:col-span-3">
            Matière
            <select value={mat ?? ''} onChange={(e) => setMat(e.target.value || null)} className={champ}>
              <option value="">Toutes les matières</option>
              <OptionsMatieres matieres={matieres} />
            </select>
          </label>
          <div className="tab:col-span-3">
            <button type="submit" disabled={etat !== 'libre'}
              className="rounded-[7px] bg-forest px-[13px] py-2.5 text-[12px] text-white hover:bg-forest-dark disabled:opacity-60">
              {etat === 'generation' ? 'Génération en cours…' : quiz ? 'Générer un nouveau questionnaire ↗' : 'Générer le questionnaire ↗'}
            </button>
          </div>
        </form>
        )}

        {erreur && (
          <p role="alert" className="mb-3 rounded-lg bg-cream px-3 py-2 text-[12px] text-[#746347]">
            {erreur}
            {statut === 402 && <> <Lien href="/tarifs" className="font-semibold text-forest hover:underline">Voir les formules</Lien></>}
          </p>
        )}

        {etat === 'generation' && (
          <div className="grid animate-pulse gap-3 border-t border-line pt-4" aria-label="Génération du questionnaire">
            {[0, 1, 2].map((i) => <div key={i} className="h-10 rounded bg-[#ece9e0]" />)}
          </div>
        )}

        {quiz?.quiz_id && (
          <div className="border-t border-line">
            {correction && (
              <p className="my-3 text-[13px] font-semibold text-forest">Score : {correction.score} / {correction.total}</p>
            )}
            {quiz.obtenu < quiz.demande && !correction && (
              <p className="mt-3 text-[11px] text-muted">
                {quiz.obtenu} question(s) vérifiable(s) sur {quiz.demande} demandées : les autres ont été écartées faute de source.
              </p>
            )}
            <ol>
              {quiz.questions.map((q) => {
                const r = correction?.resultats.find((x) => x.index === q.index)
                const nom = `q${q.index}`
                return (
                  <li key={q.index} className="border-b border-line-soft py-3.5">
                    <fieldset disabled={!!correction}>
                      <legend className="text-[12.5px] leading-[1.45] font-semibold">
                        {q.index + 1}. {q.question ?? q.affirmation}
                      </legend>
                      <div className="mt-2.5 grid gap-[7px]">
                        {quiz.format === 'qcm' && q.choix?.map((c, j) => (
                          <label key={j} className="flex items-start gap-2 text-[12px] text-[#545d56]">
                            <input type="radio" name={nom} checked={reponses[q.index] === j}
                              onChange={() => repondreQuiz(q.index, j)} className="mt-0.5 accent-forest" />
                            {c}
                          </label>
                        ))}
                        {quiz.format === 'vrai_faux' && [true, false].map((v) => (
                          <label key={String(v)} className="flex items-start gap-2 text-[12px] text-[#545d56]">
                            <input type="radio" name={nom} checked={reponses[q.index] === v}
                              onChange={() => repondreQuiz(q.index, v)} className="mt-0.5 accent-forest" />
                            {v ? 'Vrai' : 'Faux'}
                          </label>
                        ))}
                        {quiz.format === 'ouvertes' && (
                          <textarea rows={3} aria-label={`Votre réponse à la question ${q.index + 1}`}
                            value={(reponses[q.index] as string) ?? ''}
                            onChange={(e) => repondreQuiz(q.index, e.target.value)}
                            className={champ} maxLength={3000} />
                        )}
                      </div>
                    </fieldset>

                    {r && (
                      <div className="mt-3 rounded-lg bg-[#f6f4ee] px-3 py-2.5 text-[12px] leading-[1.55]">
                        <span className={`mr-2 rounded-full px-2 py-0.5 text-[10px] font-semibold ${STATUTS[r.statut].classe}`}>
                          {STATUTS[r.statut].texte}
                        </span>
                        {bonneReponse(q, r) && <span className="text-[11px] text-muted">Bonne réponse : <b className="text-ink">{bonneReponse(q, r)}</b></span>}
                        {r.commentaire && <p className="mt-1.5">{r.commentaire}</p>}
                        {r.elements_attendus && (
                          <p className="mt-1.5 text-[11px] text-muted">Éléments attendus : {r.elements_attendus.join(' ; ')}</p>
                        )}
                        {r.explication && <p className="mt-1.5">{r.explication}</p>}
                        <span className="mt-1 flex flex-wrap gap-1">
                          {r.sources.map((id) => {
                            const s = sources.find((x) => x.id === id)
                            return s ? (
                              <button key={id} type="button" onClick={() => ouvrirSource(id)}
                                className="text-[11px] font-semibold text-forest hover:underline" title={s.entete}>
                                [{numeroSource(sources, id)}] {titreCourt(s.entete).slice(0, 60)}{titreCourt(s.entete).length > 60 ? '…' : ''}
                              </button>
                            ) : null
                          })}
                        </span>
                      </div>
                    )}
                  </li>
                )
              })}
            </ol>
          </div>
        )}

        <div className="mt-4 flex flex-wrap items-center justify-between gap-2.5">
          <small className="text-[10px] text-muted">Outil d’entraînement : vérifiez les corrigés dans les sources citées.</small>
          {quiz?.quiz_id && !correction && (
            <button type="button" onClick={corriger} disabled={etat !== 'libre'}
              className="rounded-[7px] bg-forest px-[13px] py-2.5 text-[12px] text-white hover:bg-forest-dark disabled:opacity-60">
              {etat === 'correction' ? 'Correction…' : 'Corriger mes réponses'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
