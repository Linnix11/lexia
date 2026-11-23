// Fraicheur des sources (audit du 2026-11-18, B7) : jusqu'a quelle date chaque source est a jour.
// La DILA ne publie pour la Cour de cassation et le Conseil constitutionnel que des archives globales espacees :
// l'etudiant doit savoir qu'une decision plus recente peut manquer.
import { useEffect, useState } from 'react'
import { api, type Fraicheur, type FraicheurSource } from './api'

/** Au-dela, une source citee dans une reponse est signalee comme ancienne. */
export const JOURS_ANCIENNE = 30

let chargement: Promise<Fraicheur | null> | null = null

/** Une seule requete par page ; un echec est oublie pour reessayer plus tard. */
export function chargerFraicheur(): Promise<Fraicheur | null> {
  chargement ??= api.fraicheur()
    // reponse inattendue (ancien serveur sans la route) : traitee comme une absence de donnees
    .then((f) => (f && typeof f.sources === 'object' && f.sources ? f : null))
    .catch(() => {
      chargement = null
      return null
    })
  return chargement
}

export function oublierFraicheur() {
  chargement = null
}

export function useFraicheur(): Fraicheur | null {
  const [f, setF] = useState<Fraicheur | null>(null)
  useEffect(() => {
    let actif = true
    void chargerFraicheur().then((v) => actif && setF(v))
    return () => {
      actif = false
    }
  }, [])
  return f
}

export function dateLongue(iso: string): string {
  return new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' })
    .format(new Date(`${iso}T00:00:00Z`))
}

/** « version du 17 novembre 2026 » (textes) ou « décisions jusqu'au 17 septembre 2026 » (jurisprudence). */
export function libelleFraicheur(s: FraicheurSource): string {
  if (s.nature === 'textes') return `version du ${dateLongue(s.date)}`
  // Source et date de mise a jour citees, comme le demandent les CGU open data de la Cour de cassation et les
  // mentions du site du Conseil constitutionnel (D113 ; audit du 2026-11-23, E7)
  return `décisions jusqu’au ${dateLongue(s.date)}${s.origine ? ` (source : ${s.origine})` : ''}`
}

/** Date la plus recente parmi plusieurs sources (ex. les quatre formations de la Cour de cassation). */
export function plusRecente(f: Fraicheur | null, ids: string[]): string | null {
  const dates = ids.map((id) => f?.sources[id]?.date).filter((d): d is string => !!d)
  return dates.length ? dates.sort().at(-1)! : null
}

export function ancienne(date: string, maintenant: Date = new Date()): boolean {
  return maintenant.getTime() - Date.parse(`${date}T00:00:00Z`) > JOURS_ANCIENNE * 86_400_000
}

/** Sources citees dont la date de fraicheur a plus de 30 jours, sans doublon. */
export function sourcesAnciennes(f: Fraicheur | null, ids: string[], maintenant: Date = new Date()): FraicheurSource[] {
  const vues = new Set<string>()
  return ids.flatMap((id) => {
    const s = f?.sources[id]
    if (!s || vues.has(id) || !ancienne(s.date, maintenant)) return []
    vues.add(id)
    return [s]
  })
}
