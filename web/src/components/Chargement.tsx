// Attente d'une action longue (carte mentale, resume vocal, reponse, questionnaire, lecture d'un depot) :
// cercle qui tourne, etape en cours qui avance, secondes ecoulees et barre animee. Sans mouvement si le
// systeme demande moins d'animations (motion-reduce) : le texte et le compteur suffisent.
import { useEffect, useState } from 'react'

/** Duree d'affichage de chaque etape avant de passer a la suivante ; la derniere reste affichee. */
const PAS_ETAPE_MS = 6000

export function Rond({ className = 'h-4 w-4' }: { className?: string }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className={`${className} shrink-0 animate-spin motion-reduce:animate-none`}>
      <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeOpacity="0.2" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}

/** etapes : textes affiches l'un apres l'autre ; duree : ordre de grandeur annonce (« jusqu'à une minute »). */
export function Chargement({ etapes, duree, className = '' }: { etapes: string[]; duree?: string; className?: string }) {
  const [secondes, setSecondes] = useState(0)
  useEffect(() => {
    const debut = Date.now()
    const t = window.setInterval(() => setSecondes(Math.floor((Date.now() - debut) / 1000)), 1000)
    return () => window.clearInterval(t)
  }, [])
  const etape = etapes[Math.min(etapes.length - 1, Math.floor((secondes * 1000) / PAS_ETAPE_MS))]
  return (
    <div className={`rounded-[10px] bg-[#f6f4ee] px-3.5 py-3 text-forest ${className}`}>
      {/* Une seule annonce pour les lecteurs d'ecran : l'etape, pas chaque seconde */}
      <p role="status" className="flex items-center gap-2 text-[12px] font-semibold">
        <Rond />
        <span>{etape}</span>
      </p>
      <div aria-hidden="true" className="mt-2 h-1 overflow-hidden rounded-full bg-[#e3e8e2]">
        <div className="lexia-barre h-full w-1/3 rounded-full bg-forest motion-reduce:w-full motion-reduce:opacity-40" />
      </div>
      <p aria-hidden="true" className="mt-1.5 text-[11px] text-muted">
        {secondes > 0 ? `${secondes} s` : ' '}{duree ? ` · ${duree}` : ''}
      </p>
    </div>
  )
}
