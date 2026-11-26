// Mise en page d'une carte mentale (D112, docs/cartes-mentales.md) : arbre horizontal dessine en SVG maison,
// sans bibliotheque. Notion centrale a gauche, branches, sous-branches, references en feuilles.
import type { CarteMentale, FeuilleCarte } from './api'

export type Genre = 'centre' | 'branche' | 'enfant' | 'feuille'

export interface Boite {
  cle: string
  genre: Genre
  lignes: string[]
  x: number
  y: number
  l: number
  h: number
  couleur: string
  branche: number // -1 pour la notion centrale
  lien: FeuilleCarte['lien']
  replie: number // enfants caches (branche repliee), 0 sinon
  statut?: FeuilleCarte['statut'] // grand arret abandonne ou nuance (D138)
}

export interface Trait {
  cle: string
  d: string
  couleur: string
}

export interface Disposition {
  boites: Boite[]
  traits: Trait[]
  largeur: number
  hauteur: number
}

// Couleurs des branches : contraste de 4,5:1 au moins sur fond blanc pour le texte des feuilles.
export const COULEURS = ['#315e4b', '#8a4f1f', '#3d5a80', '#7a4a6b', '#55642a', '#9b3d2e', '#26666a']
const ENCRE = '#202724'
const LARGEURS: Record<Genre, number> = { centre: 170, branche: 180, enfant: 176, feuille: 168 }
const CARACTERES: Record<Genre, number> = { centre: 20, branche: 24, enfant: 25, feuille: 25 }
const ECART_COLONNES = 44
const ECART_LIGNES = 10
const INTERLIGNE = 16
const MARGE_INTERNE = 10
const MARGE = 16
// 6 lignes : un libelle de 120 caracteres et la mention « ancien numero » ou « arret abandonne » tiennent sans
// etre coupes (4 lignes coupaient la mention, revue du 26/11, D138).
const MAX_LIGNES = 6

/** Coupe un libelle en lignes de `max` caracteres au plus, aux espaces ; MAX_LIGNES lignes, puis « … ». */
export function couperLignes(texte: string, max: number): string[] {
  const lignes: string[] = []
  let courante = ''
  for (const mot of texte.split(/\s+/).filter(Boolean)) {
    const morceaux = mot.length > max ? mot.match(new RegExp(`.{1,${max}}`, 'g'))! : [mot]
    for (const m of morceaux) {
      if (!courante) courante = m
      else if (courante.length + 1 + m.length <= max) courante += ` ${m}`
      else {
        lignes.push(courante)
        courante = m
      }
    }
  }
  if (courante) lignes.push(courante)
  if (lignes.length > MAX_LIGNES) {
    const fin = lignes[MAX_LIGNES - 1]
    return [...lignes.slice(0, MAX_LIGNES - 1), `${fin.slice(0, Math.max(0, max - 1))}…`]
  }
  return lignes.length ? lignes : ['']
}

interface Noeud {
  cle: string
  genre: Genre
  texte: string
  branche: number
  lien: FeuilleCarte['lien']
  enfants: Noeud[]
  replie: number
  statut?: FeuilleCarte['statut']
}

function arbre(carte: CarteMentale, replies: ReadonlySet<number>): Noeud {
  const feuilles = (cle: string, articles: FeuilleCarte[], b: number): Noeud[] =>
    articles.map((a, i) => ({ cle: `${cle}-a${i}`, genre: 'feuille', texte: a.texte, branche: b, lien: a.lien, enfants: [], replie: 0, statut: a.statut }))
  return {
    cle: 'centre', genre: 'centre', texte: carte.titre, branche: -1, lien: null, replie: 0,
    enfants: carte.branches.map((br, b) => {
      const enfants: Noeud[] = [
        ...br.enfants.map((e, j) => ({
          cle: `b${b}-e${j}`, genre: 'enfant' as const, texte: e.libelle, branche: b, lien: null, replie: 0,
          enfants: feuilles(`b${b}-e${j}`, e.articles, b),
        })),
        ...feuilles(`b${b}`, br.articles, b),
      ]
      const replie = replies.has(b)
      return { cle: `b${b}`, genre: 'branche' as const, texte: br.libelle, branche: b, lien: null,
        enfants: replie ? [] : enfants, replie: replie ? enfants.length : 0 }
    }),
  }
}

const hauteurBoite = (lignes: number) => lignes * INTERLIGNE + 2 * MARGE_INTERNE

/** Position de chaque boite : chaque noeud est centre sur ses enfants, les colonnes vont de gauche a droite. */
export function disposer(carte: CarteMentale, replies: ReadonlySet<number> = new Set()): Disposition {
  const racine = arbre(carte, replies)
  const boites: Boite[] = []
  const traits: Trait[] = []
  const colonnes = [0, 1, 2, 3].map((p) => MARGE + p * (LARGEURS.branche + ECART_COLONNES))

  // Hauteur occupee par un sous-arbre
  const hauteurs = new Map<Noeud, number>()
  const mesurer = (n: Noeud): number => {
    const propre = hauteurBoite(couperLignes(n.texte, CARACTERES[n.genre]).length)
    const enfants = n.enfants.reduce((t, e) => t + mesurer(e), 0) + Math.max(0, n.enfants.length - 1) * ECART_LIGNES
    const h = Math.max(propre, enfants)
    hauteurs.set(n, h)
    return h
  }
  const total = mesurer(racine)

  const placer = (n: Noeud, profondeur: number, haut: number, parent: Boite | null) => {
    const lignes = couperLignes(n.texte, CARACTERES[n.genre])
    const h = hauteurBoite(lignes.length)
    const b: Boite = {
      cle: n.cle, genre: n.genre, lignes, x: colonnes[profondeur], y: haut + (hauteurs.get(n)! - h) / 2,
      l: LARGEURS[n.genre], h, couleur: n.branche < 0 ? ENCRE : COULEURS[n.branche % COULEURS.length],
      branche: n.branche, lien: n.lien, replie: n.replie, statut: n.statut,
    }
    boites.push(b)
    if (parent) {
      const x1 = parent.x + parent.l
      const y1 = parent.y + parent.h / 2
      const x2 = b.x
      const y2 = b.y + b.h / 2
      const m = (x1 + x2) / 2
      traits.push({ cle: `t-${n.cle}`, d: `M${x1},${y1} C${m},${y1} ${m},${y2} ${x2},${y2}`, couleur: b.couleur })
    }
    let y = haut + (hauteurs.get(n)! - (n.enfants.reduce((t, e) => t + hauteurs.get(e)!, 0)
      + Math.max(0, n.enfants.length - 1) * ECART_LIGNES)) / 2
    for (const e of n.enfants) {
      placer(e, profondeur + 1, y, b)
      y += hauteurs.get(e)! + ECART_LIGNES
    }
  }
  placer(racine, 0, MARGE, null)

  const droite = Math.max(...boites.map((b) => b.x + b.l))
  return { boites, traits, largeur: droite + MARGE, hauteur: total + 2 * MARGE }
}

/** Nom de fichier de l'image exportee : « carte-mentale-responsabilite-du-fait-personnel.png ». */
export function nomFichier(titre: string): string {
  const base = titre.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
    .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60)
  return `carte-mentale${base ? `-${base}` : ''}.png`
}

export const MENTION_IA_CARTE = 'Carte générée par une intelligence artificielle (Lexia) : vérifiez les sources citées.'

/** Plan de la carte en texte, a coller dans ses fiches (« Copier le plan », D138) : branches numerotees,
 * sous-idees en tirets, references entre parentheses. */
export function planTexte(carte: CarteMentale): string {
  const refs = (articles: FeuilleCarte[]) => (articles.length ? ` (${articles.map((a) => a.texte).join(' ; ')})` : '')
  const lignes = [carte.titre, '']
  carte.branches.forEach((b, i) => {
    lignes.push(`${i + 1}. ${b.libelle}${refs(b.articles)}`)
    for (const e of b.enfants) lignes.push(`   - ${e.libelle}${refs(e.articles)}`)
  })
  lignes.push('', MENTION_IA_CARTE)
  return lignes.join('\n')
}

const echapper = (t: string) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')

function feuillesHtml(articles: FeuilleCarte[]): string {
  if (!articles.length) return ''
  return ` <span class="refs">(${articles.map((a) => (a.lien
    ? `<a href="${echapper(a.lien.url)}">${echapper(a.texte)}</a>`
    : echapper(a.texte))).join(' ; ')})</span>`
}

/** Page a imprimer ou a enregistrer en PDF (D138) : le dessin entier sur une page en paysage, puis le plan en
 * liste (lisible meme quand le dessin est grand), liens vers le texte officiel gardes dans le PDF, mention IA. */
export function pageImpression(carte: CarteMentale, svg: string, date = new Date()): string {
  const plan = carte.branches.map((b, i) => {
    const couleur = COULEURS[i % COULEURS.length]
    const enfants = b.enfants.map((e) => `<li>${echapper(e.libelle)}${feuillesHtml(e.articles)}</li>`).join('')
    return `<li class="branche" style="border-color:${couleur}"><strong style="color:${couleur}">${echapper(b.libelle)}</strong>`
      + `${feuillesHtml(b.articles)}${enfants ? `<ul>${enfants}</ul>` : ''}</li>`
  }).join('')
  return `<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Carte mentale · ${echapper(carte.titre)}</title>
<style>
@page { size: A4 landscape; margin: 10mm }
body { margin: 0; color: #202724; font: 10.5pt/1.4 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif }
h1 { margin: 0 0 4mm; font: 600 16pt Georgia, "Times New Roman", serif }
h2 { margin: 0 0 3mm; font: 600 12pt Georgia, "Times New Roman", serif }
.dessin svg { display: block; width: 100%; height: auto; max-height: 165mm }
.plan { break-before: page; page-break-before: always }
.plan > ol { margin: 0; padding: 0; list-style: none; columns: 2; column-gap: 10mm }
.branche { break-inside: avoid; margin: 0 0 4mm; padding-left: 3mm; border-left: 3px solid }
.branche ul { margin: 1mm 0 0; padding-left: 5mm }
.refs, .refs a { color: #4f5853 }
.mention { margin-top: 5mm; color: #666e69; font-size: 8.5pt }
@media screen { body { margin: 16px } .plan { margin-top: 24px } }
</style></head><body>
<h1>${echapper(carte.titre)}</h1>
<div class="dessin">${svg}</div>
<section class="plan"><h2>Plan de la carte</h2><ol>${plan}</ol>
<p class="mention">${echapper(carte.avertissement || 'Carte générée automatiquement : vérifiez avec les textes.')} ${echapper(MENTION_IA_CARTE)}
Imprimée le ${date.toLocaleDateString('fr-FR')}.</p></section>
</body></html>`
}

/** Image PNG du dessin (SVG dessine dans un canvas, fond blanc, deux fois plus net), sans bibliotheque. */
export async function exporterPng(svg: SVGSVGElement, largeur: number, hauteur: number, nom: string): Promise<void> {
  const copie = svg.cloneNode(true) as SVGSVGElement
  copie.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  copie.setAttribute('width', String(largeur))
  copie.setAttribute('height', String(hauteur))
  const url = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(copie)], { type: 'image/svg+xml;charset=utf-8' }))
  try {
    const image = new Image()
    await new Promise<void>((ok, ko) => {
      image.onload = () => ok()
      image.onerror = () => ko(new Error('image'))
      image.src = url
    })
    const echelle = 2
    const bandeau = 26 // mention « generee par IA » sous le dessin (reglement (UE) 2024/1689, art. 50 ; audit du 2026-11-23, E11)
    const canvas = document.createElement('canvas')
    canvas.width = largeur * echelle
    canvas.height = (hauteur + bandeau) * echelle
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('canvas')
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.scale(echelle, echelle)
    ctx.drawImage(image, 0, 0, largeur, hauteur)
    ctx.fillStyle = '#666e69'
    ctx.font = '12px Inter, -apple-system, "Segoe UI", sans-serif'
    ctx.fillText(MENTION_IA_CARTE, 12, hauteur + 17, largeur - 24)
    const png = await new Promise<Blob | null>((ok) => canvas.toBlob(ok, 'image/png'))
    if (!png) throw new Error('png')
    const lien = document.createElement('a')
    lien.href = URL.createObjectURL(png)
    lien.download = nom
    lien.click()
    setTimeout(() => URL.revokeObjectURL(lien.href), 1000)
  } finally {
    URL.revokeObjectURL(url)
  }
}
