// Texte brut d'une page legale rendue (CGU, politique de confidentialite) : une seule source, la page de
// Legal.tsx, dont les tests tirent une copie texte versionnee (D111, D115). Utilise seulement par les tests.

/** Valeurs de l'editeur laissees en repères, remplaces par le serveur (api/cgu_texte.py) ou lus tels quels. */
export const REPERES = {
  editeur: '{{editeur}}', adresse: '{{adresse}}', telephone: '{{telephone}}', tva: '{{tva}}', mediateur: '{{mediateur}}',
  siren: '{{siren}}', statut: '{{statut}}', directeur: '{{directeur}}', hebergeur_telephone: '{{hebergeur_telephone}}',
}

/** Nom du fichier d'une version : « 20 novembre 2026 » -> 20-novembre-2026.json */
export const fichierVersion = (version: string) => `${version.normalize('NFD').replace(/[̀-ͯ]/g, '')
  .toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')}.json`

const ligne = (t: string) => t.replace(/[ \t ]+/g, ' ').split('\n').map((l) => l.trim()).join('\n').trim()

/** Texte lisible d'une page : titres, paragraphes et listes ; adresse des liens ajoutee a leur texte. */
export function enTexte(racine: Element): string {
  const enLigne = (n: Node): string => {
    if (n.nodeType === Node.TEXT_NODE) return n.textContent ?? ''
    if (!(n instanceof Element)) return ''
    if (n.tagName === 'BR') return '\n'
    let t = [...n.childNodes].map(enLigne).join('')
    if (n.tagName === 'A') {
      const href = n.getAttribute('href') ?? ''
      const cible = href.startsWith('mailto:') ? decodeURIComponent(href.slice(7).split('?')[0])
        : href.startsWith('/') ? `{{url}}${href}` : href
      if (cible && !t.includes(cible)) t += ` (${cible})`
    }
    return t
  }
  const blocs: string[] = []
  const parcourir = (el: Element) => {
    for (const c of el.children) {
      if (/^H[1-6]$/.test(c.tagName)) blocs.push(ligne(enLigne(c)).toUpperCase())
      else if (c.tagName === 'P') blocs.push(ligne(enLigne(c)))
      else if (c.tagName === 'UL' || c.tagName === 'OL') blocs.push([...c.children].map((li) => `- ${ligne(enLigne(li))}`).join('\n'))
      else parcourir(c)
    }
  }
  parcourir(racine)
  return blocs.filter(Boolean).join('\n\n') + '\n'
}
