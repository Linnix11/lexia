import { useEffect, useRef } from 'react'

const FOCUSABLES = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

/** Fenetre modale accessible : focus initial, Tab piege dans la fenetre, Echap ferme, focus restaure. */
export function useDialog<T extends HTMLElement>(ouvert: boolean, fermer: () => void) {
  const ref = useRef<T>(null)
  const fermerRef = useRef(fermer)
  useEffect(() => {
    fermerRef.current = fermer
  }, [fermer])

  useEffect(() => {
    if (!ouvert) return
    const precedent = document.activeElement as HTMLElement | null
    const racine = ref.current
    // champ marque data-autofocus en priorite, sinon premier element focalisable
    ;(racine?.querySelector<HTMLElement>('[data-autofocus]') ?? racine?.querySelector<HTMLElement>(FOCUSABLES))?.focus()

    const auClavier = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        fermerRef.current()
        return
      }
      if (e.key !== 'Tab' || !racine) return
      const elements = Array.from(racine.querySelectorAll<HTMLElement>(FOCUSABLES)).filter((el) => el.offsetParent !== null)
      if (!elements.length) return
      const premier = elements[0]
      const dernier = elements[elements.length - 1]
      if (e.shiftKey && document.activeElement === premier) {
        e.preventDefault()
        dernier.focus()
      } else if (!e.shiftKey && document.activeElement === dernier) {
        e.preventDefault()
        premier.focus()
      }
    }
    document.addEventListener('keydown', auClavier)
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', auClavier)
      document.body.style.overflow = overflow
      precedent?.focus?.()
    }
  }, [ouvert])

  return ref
}
