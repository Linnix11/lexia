// Symbole Lexia : le signet (marque-page vert a lisere dore, L blanc). Meme dessin que public/favicon.svg.
export function Signet({ hauteur = 32, inverse = false, className = '' }: { hauteur?: number; inverse?: boolean; className?: string }) {
  const fond = inverse ? '#fffefa' : '#315e4b'
  const lettre = inverse ? '#315e4b' : '#ffffff'
  return (
    <svg viewBox="12 0 40 64" height={hauteur} width={(hauteur * 40) / 64} aria-hidden="true" className={className}>
      <path d="M16 2 H48 V62 L32 49 L16 62 Z" fill={fond} />
      <rect x="16" y="2" width="32" height="5" fill="#bd8951" />
      <text x="32" y="38" textAnchor="middle" fontFamily="Georgia, 'Times New Roman', serif" fontSize="26" fill={lettre}>L</text>
    </svg>
  )
}
