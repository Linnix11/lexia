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
const MAX_LIGNES = 4

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
}

function arbre(carte: CarteMentale, replies: ReadonlySet<number>): Noeud {
  const feuilles = (cle: string, articles: FeuilleCarte[], b: number): Noeud[] =>
    articles.map((a, i) => ({ cle: `${cle}-a${i}`, genre: 'feuille', texte: a.texte, branche: b, lien: a.lien, enfants: [], replie: 0 }))
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
      branche: n.branche, lien: n.lien, replie: n.replie,
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
    const canvas = document.createElement('canvas')
    canvas.width = largeur * echelle
    canvas.height = hauteur * echelle
    const ctx = canvas.getContext('2d')
    if (!ctx) throw new Error('canvas')
    ctx.fillStyle = '#ffffff'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.scale(echelle, echelle)
    ctx.drawImage(image, 0, 0, largeur, hauteur)
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
