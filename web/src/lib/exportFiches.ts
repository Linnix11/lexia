// Export des fiches en Markdown : elles ne vivent que dans ce navigateur, l'etudiant doit pouvoir les garder
// ailleurs (audit du 2026-11-16, point 5).
import type { Element, FicheSource } from './api'
import type { Favori } from './favoris'
import { infosMode } from './modes'

/** Numero d'affichage continu (1, 2, 3...) dans l'ordre de la liste des sources de la reponse. */
export function numeroSource(sources: FicheSource[], id: string): number {
  return sources.findIndex((s) => s.id === id) + 1
}

function bloc(titre: string, items: Element[], sources: FicheSource[]): string[] {
  if (!items.length) return []
  const lignes = [`## ${titre}`, '']
  items.forEach((it, i) => {
    if (it.rubrique && it.rubrique !== items[i - 1]?.rubrique) lignes.push(...(i > 0 ? [''] : []), `### ${it.rubrique}`, '')
    const refs = it.sources.map((id) => numeroSource(sources, id)).filter((n) => n > 0).map((n) => `[${n}]`).join(' ')
    lignes.push(`- ${it.texte}${refs ? ` ${refs}` : ''}`)
  })
  lignes.push('')
  return lignes
}

export function ficheEnMarkdown(f: Favori): string {
  const r = f.reponse
  const [b1, b2, b3] = infosMode(f.mode).blocs
  const date = new Date(f.enregistre_le).toLocaleDateString('fr-FR')
  const lignes = [
    `# ${r.titre || f.question}`,
    '',
    `Question : ${f.question}  `,
    `${infosMode(f.mode).label} · enregistrée le ${date} · Lexia`,
    '',
    ...bloc(b1, r.droit_positif, r.sources),
    ...bloc(b2, r.explication, r.sources),
    ...bloc(b3, r.points_incertains, r.sources),
  ]
  if (r.sources.length) {
    lignes.push('## Sources', '')
    r.sources.forEach((s, i) => lignes.push(`${i + 1}. ${s.entete}${s.version ? ` (${s.version})` : ''}${s.url ? ` : ${s.url}` : ''}`))
    lignes.push('')
  }
  if (r.avertissement) lignes.push(`_${r.avertissement}_`, '')
  return lignes.join('\n')
}

export function fichesEnMarkdown(liste: Favori[]): string {
  return liste.map(ficheEnMarkdown).join('\n---\n\n')
}

/** Fait telecharger un texte Markdown par le navigateur. */
export function telecharger(nom: string, contenu: string): void {
  const url = URL.createObjectURL(new Blob([contenu], { type: 'text/markdown;charset=utf-8' }))
  const lien = document.createElement('a')
  lien.href = url
  lien.download = nom
  document.body.appendChild(lien)
  lien.click()
  lien.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export function nomFichier(texte: string): string {
  const base = texte.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60)
  return `${base || 'fiche'}.md`
}
