import { useEffect, useState } from 'react'
import { api, ApiError, type SourceComplete, type Vigueur } from '../lib/api'
import { useDialog } from '../lib/useDialog'
import { useApp } from '../state/contexte'

const NATURE: Record<string, string> = {
  article: 'Article',
  preambule: 'Préambule',
  motifs: 'Motifs',
  dispositif: 'Dispositif',
  sommaire: 'Sommaire officiel',
}

/** Panneau lateral : texte integral d'une source citee + verification de la version en vigueur. */
export function SourcePanel() {
  const { sourceOuverte } = useApp()
  if (!sourceOuverte) return null
  return <SourceContenu key={sourceOuverte} sourceOuverte={sourceOuverte} />
}

function SourceContenu({ sourceOuverte }: { sourceOuverte: string }) {
  const { ouvrirSource } = useApp()
  const fermer = () => ouvrirSource(null)
  const ref = useDialog<HTMLDivElement>(true, fermer)
  const [source, setSource] = useState<SourceComplete | null>(null)
  const [erreur, setErreur] = useState<string | null>(null)
  const [vigueur, setVigueur] = useState<Vigueur | null>(null)
  const [verification, setVerification] = useState(false)

  useEffect(() => {
    let actif = true
    api
      .source(sourceOuverte)
      .then((s) => actif && setSource(s))
      .catch((e) => actif && setErreur(e instanceof ApiError ? e.message : 'Source indisponible.'))
    return () => {
      actif = false
    }
  }, [sourceOuverte])

  const verifier = () => {
    setVerification(true)
    api
      .vigueur(sourceOuverte)
      .then(setVigueur)
      .catch(() => setErreur('La vérification a échoué. Réessayez.'))
      .finally(() => setVerification(false))
  }

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-[#17241d70]" onMouseDown={(e) => e.target === e.currentTarget && fermer()}>
      <div
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-labelledby="source-titre"
        className="flex h-full w-full max-w-[520px] flex-col overflow-hidden border-l border-line bg-surface shadow-[0_20px_70px_#17241d35]"
      >
        <div className="flex items-start justify-between gap-3 border-b border-line px-5 py-4">
          <div className="min-w-0">
            <div className="text-[10px] font-bold tracking-[1.6px] text-forest uppercase">
              {source ? NATURE[source.type] ?? 'Source' : 'Source'}
            </div>
            <h2 id="source-titre" className="mt-1 font-display text-[19px] leading-snug">
              {source?.entete ?? 'Chargement…'}
            </h2>
          </div>
          <button type="button" onClick={fermer} aria-label="Fermer la source"
            className="rounded-[7px] border border-line px-2.5 py-1.5 text-muted hover:text-ink">
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {erreur && <p role="alert" className="mb-3 rounded-lg bg-cream px-3 py-2 text-[12px] text-[#746347]">{erreur}</p>}
          {!source && !erreur && (
            <div className="grid animate-pulse gap-2">
              {[0, 1, 2, 3].map((i) => <div key={i} className="h-3 rounded bg-[#ece9e0]" />)}
            </div>
          )}
          {source && (
            <>
              {source.titre && source.titre !== source.entete && (
                <p className="mb-3 text-[11px] leading-[1.45] text-muted">{source.titre}</p>
              )}
              <div className="text-[13px] leading-[1.7] whitespace-pre-line">{source.texte}</div>
              <dl className="mt-5 grid gap-1.5 border-t border-line-soft pt-3 text-[11px]">
                <div className="flex gap-2"><dt className="w-[90px] shrink-0 text-muted">Version</dt><dd>{source.version}</dd></div>
                {source.date && <div className="flex gap-2"><dt className="w-[90px] shrink-0 text-muted">Date</dt><dd>{source.date}</dd></div>}
                {typeof source.meta.ecli === 'string' && (
                  <div className="flex gap-2"><dt className="w-[90px] shrink-0 text-muted">ECLI</dt><dd className="break-all">{source.meta.ecli}</dd></div>
                )}
              </dl>

              {vigueur && (
                <div className={`mt-4 rounded-lg border-l-2 px-3 py-2.5 text-[12px] leading-[1.5] ${
                  vigueur.en_vigueur === false ? 'border-[#c8a16d] bg-cream text-[#746347]' : 'border-forest bg-mint text-[#254a3a]'}`}>
                  {vigueur.message}
                  {vigueur.version_en_vigueur && (
                    <button type="button" onClick={() => ouvrirSource(vigueur.version_en_vigueur!.id)}
                      className="mt-1.5 block font-semibold text-forest hover:underline">
                      Ouvrir la version en vigueur →
                    </button>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {source && (
          <div className="flex flex-wrap items-center gap-2 border-t border-line px-5 py-3">
            <button type="button" onClick={verifier} disabled={verification}
              className="rounded-[7px] bg-forest px-3 py-2 text-[11px] text-white hover:bg-forest-dark disabled:opacity-60">
              {verification ? 'Vérification…' : 'Vérifier la version en vigueur'}
            </button>
            {source.url && (
              <a href={source.url} target="_blank" rel="noreferrer"
                className="rounded-[7px] border border-line px-3 py-2 text-[11px] text-forest hover:border-[#9eafa3]">
                Ouvrir la source officielle ↗
              </a>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
