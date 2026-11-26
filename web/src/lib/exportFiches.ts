// Export des fiches en Markdown : elles ne vivent que dans ce navigateur, l'etudiant doit pouvoir les garder
// ailleurs (audit du 2026-11-16, point 5).
import type { Element, FicheSource } from './api'
import type { Favori } from './favoris'
import { infosMode } from './modes'
import { numeroSource } from './sources'

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

export const MENTION_IA_FICHE = '_Fiche générée par une intelligence artificielle (Lexia) : vérifiez les sources citées._'

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
    // Marquage du contenu genere (reglement (UE) 2024/1689, art. 50 ; audit du 2026-11-23, E11)
    MENTION_IA_FICHE,
    '',
    ...bloc('L’essentiel', r.reponse_directe ?? [], r.sources),
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
export function telecharger(nom: string, contenu: string, type = 'text/markdown;charset=utf-8'): void {
  const url = URL.createObjectURL(new Blob([contenu], { type }))
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

// --- Fiche de revision : rubriques, impression et PDF (D139) ---------------------------------------------------

/** Rubriques de la fiche (api/prompts.py, RUBRIQUES["fiche"]) mises en valeur a l'affichage et a l'impression. */
export const RUBRIQUE_MEMO = 'Mémo'
export const RUBRIQUE_PIEGES = 'Pièges fréquents'

/** Elements regroupes par rubrique, dans l'ordre de leur premiere apparition ; sans rubrique (fiches d'avant les
 * rubriques) : sous `defaut`. */
export function parRubrique(items: Element[], defaut: string): [string, Element[]][] {
  const groupes = new Map<string, Element[]>()
  for (const it of items) {
    const nom = it.rubrique || defaut
    groupes.set(nom, [...(groupes.get(nom) ?? []), it])
  }
  return [...groupes]
}

const echapper = (t: string) =>
  t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;')

function sectionHtml(titre: string, items: Element[], sources: FicheSource[], classe = ''): string {
  if (!items.length) return ''
  const lignes = items.map((it) => {
    const refs = it.sources.map((id) => numeroSource(sources, id)).filter((n) => n > 0).map((n) => `[${n}]`).join(' ')
    return `<li>${echapper(it.texte)}${refs ? ` <span class="ref">${refs}</span>` : ''}</li>`
  })
  return `<section${classe ? ` class="${classe}"` : ''}><h2>${echapper(titre)}</h2><ul>${lignes.join('')}</ul></section>`
}

const STYLE_IMPRESSION = `
@page { margin: 16mm 15mm; }
* { box-sizing: border-box; }
body { margin: 0 auto; max-width: 720px; padding: 8px; font: 11pt/1.5 Georgia, 'Times New Roman', serif; color: #1d2320; background: #fff; }
.surtitre { margin: 0; font: 600 8.5pt/1.2 system-ui, sans-serif; letter-spacing: .12em; text-transform: uppercase; color: #315e4b; }
h1 { margin: 4pt 0 2pt; font-size: 19pt; line-height: 1.2; font-weight: normal; }
.meta { margin: 0 0 8pt; font: 8.5pt/1.4 system-ui, sans-serif; color: #555; }
.ia { margin: 0 0 10pt; padding: 4pt 8pt; border: 1px solid #d8d4c6; font: italic 8.5pt/1.4 system-ui, sans-serif; color: #555; }
h2 { margin: 12pt 0 3pt; font: 700 9pt/1.2 system-ui, sans-serif; letter-spacing: .1em; text-transform: uppercase; color: #315e4b; break-after: avoid; }
ul { margin: 0; padding-left: 14pt; }
li { margin: 0 0 3pt; break-inside: avoid; }
.ref { font: 8pt system-ui, sans-serif; color: #315e4b; white-space: nowrap; }
.attention h2 { color: #7a5630; }
.memo { margin-top: 12pt; padding: 2pt 10pt 6pt; border: 1.5pt solid #315e4b; border-radius: 4pt; break-inside: avoid; }
.memo li { font-weight: 600; }
.sources ol { margin: 0; padding-left: 16pt; font: 8.5pt/1.4 system-ui, sans-serif; color: #333; }
.sources li { overflow-wrap: anywhere; }
footer { margin-top: 12pt; padding-top: 6pt; border-top: 1px solid #ddd; font: 8pt/1.4 system-ui, sans-serif; color: #555; }
`

/** Page HTML autonome de la fiche, pour l'imprimer ou l'enregistrer en PDF depuis la fenetre d'impression du
 * navigateur. Une fiche de revision suit ses rubriques, memo encadre ; les autres reponses suivent leurs blocs. */
export function ficheEnHtml(f: Favori, matiere?: string): string {
  const r = f.reponse
  const infos = infosMode(f.mode)
  const [b1, b2, b3] = infos.blocs
  const titre = r.titre || f.question
  const date = new Date(f.enregistre_le).toLocaleDateString('fr-FR')
  const corps: string[] = [sectionHtml('L’essentiel', r.reponse_directe ?? [], r.sources)]
  if (f.mode === 'fiche') {
    for (const [rubrique, items] of parRubrique(r.explication, b2))
      corps.push(sectionHtml(rubrique, items, r.sources, rubrique === RUBRIQUE_MEMO ? 'memo' : rubrique === RUBRIQUE_PIEGES ? 'attention' : ''))
    corps.push(sectionHtml(b3, r.points_incertains, r.sources, 'attention'), sectionHtml(b1, r.droit_positif, r.sources))
  } else {
    corps.push(sectionHtml(b1, r.droit_positif, r.sources))
    for (const [rubrique, items] of parRubrique(r.explication, b2)) corps.push(sectionHtml(rubrique, items, r.sources))
    corps.push(sectionHtml(b3, r.points_incertains, r.sources, 'attention'))
  }
  const sources = r.sources.map((s) =>
    `<li>${echapper(s.entete)}${s.version ? ` (${echapper(s.version)})` : ''}${s.url ? ` : ${echapper(s.url)}` : ''}</li>`).join('')
  return [
    '<!doctype html><html lang="fr"><head><meta charset="utf-8">',
    `<title>${echapper(titre)} · Lexia</title><style>${STYLE_IMPRESSION}</style></head><body>`,
    `<p class="surtitre">${echapper(infos.label === 'Fiche' ? 'Fiche de révision' : infos.label)} · Lexia</p>`,
    `<h1>${echapper(titre)}</h1>`,
    `<p class="meta">${[`Question : ${f.question}`, matiere, `enregistrée le ${date}`].filter(Boolean).map((t) => echapper(t!)).join(' · ')}</p>`,
    `<p class="ia">${echapper(MENTION_IA_FICHE.replace(/_/g, ''))}</p>`,
    ...corps.filter(Boolean),
    sources ? `<section class="sources"><h2>Sources</h2><ol>${sources}</ol></section>` : '',
    r.avertissement ? `<footer>${echapper(r.avertissement)}</footer>` : '',
    '</body></html>',
  ].join('\n')
}

/** Ouvre la fenetre d'impression du navigateur sur la fiche seule (« Enregistrer au format PDF » y est propose),
 * depuis un cadre invisible : ni fenetre surgissante, ni reste de l'interface sur la page imprimee. */
export function imprimerFiche(f: Favori, matiere?: string): void {
  const cadre = document.createElement('iframe')
  cadre.setAttribute('aria-hidden', 'true')
  cadre.tabIndex = -1
  cadre.style.cssText = 'position:fixed;right:0;bottom:0;width:0;height:0;border:0;opacity:0'
  let retire = false
  const retirer = () => { if (!retire) { retire = true; cadre.remove() } }
  cadre.onload = () => {
    const fenetre = cadre.contentWindow
    if (!fenetre) return retirer()
    fenetre.addEventListener('afterprint', () => window.setTimeout(retirer, 0))
    fenetre.focus()
    fenetre.print()
    window.setTimeout(retirer, 10 * 60_000) // filet : afterprint n'est pas emis partout
  }
  cadre.srcdoc = ficheEnHtml(f, matiere)
  document.body.appendChild(cadre)
}
