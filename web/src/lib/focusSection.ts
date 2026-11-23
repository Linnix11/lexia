// Section ouverte a la place de son bouton (resume vocal, carte mentale) : le bouton qui avait le focus disparait.
// Focus sur le titre de la section a l'ouverture, retour au bouton a la fermeture, jamais sur <body>
// (recette du 2026-11-20, D-4 ; audit du 2026-11-23, D4).
import { useEffect, useRef } from 'react'

export function useFocusSection(ouvert: boolean) {
  const titre = useRef<HTMLHeadingElement>(null)
  const ouvreur = useRef<HTMLButtonElement>(null)
  const dejaOuvert = useRef(false)
  useEffect(() => {
    if (ouvert) {
      dejaOuvert.current = true
      titre.current?.focus()
    } else if (dejaOuvert.current) {
      ouvreur.current?.focus()
    }
  }, [ouvert])
  return { titre, ouvreur }
}
