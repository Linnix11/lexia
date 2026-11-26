// Fiches de revision (D139) : affichage par rubriques, recherche et classement par matiere, impression, revision.
import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Site from '../Site'
import type { ReponseChat } from '../lib/api'
import { lireCartes } from '../lib/cartes'
import { ficheEnHtml, parRubrique } from '../lib/exportFiches'
import { ecrireFavoris, filtrerFiches, lireFavoris, matieresDesFiches, type Favori } from '../lib/favoris'

const SOURCES: ReponseChat['sources'] = [
  { id: 'cc:1103', label: 'S1', source_id: 'code_civil', type: 'article', numero: '1103', entete: 'Code civil, article 1103',
    url: 'https://www.legifrance.gouv.fr/codes/article_lc/A1103', version: 'Version depuis le 1er octobre 2016', en_vigueur: true,
    date: '2016-10-01', extrait: 'Les contrats légalement formés…' },
  { id: 'cass:marechaux', label: 'S2', source_id: 'cass_commerciale', type: 'sommaire', numero: null,
    entete: 'Cour de cassation, chambre commerciale, 10 juillet 2007', url: '', version: '', en_vigueur: null, date: '2007-07-10', extrait: '…' },
]

const FICHE: ReponseChat = {
  reponse_id: 'f-force',
  statut: 'reponse',
  titre: 'La force obligatoire du contrat',
  reponse_directe: [{ texte: 'Le contrat légalement formé tient lieu de loi aux parties.', sources: ['cc:1103'] }],
  droit_positif: [{ texte: 'Les contrats légalement formés tiennent lieu de loi à ceux qui les ont faits.', sources: ['cc:1103'] }],
  explication: [
    { texte: 'La force obligatoire oblige les parties à exécuter le contrat.', sources: ['cc:1103'], rubrique: 'Définition' },
    { texte: 'Le contrat ne se modifie que du consentement mutuel.', sources: ['cc:1103'], rubrique: 'Règles à retenir' },
    { texte: 'Les Maréchaux : la bonne foi ne touche pas à la substance des droits.', sources: ['cass:marechaux'], rubrique: 'Jurisprudence clé' },
    { texte: 'Ne pas confondre imprévision et force majeure.', sources: ['cc:1103'], rubrique: 'Pièges fréquents' },
    { texte: 'Force obligatoire : article 1103', sources: ['cc:1103'], rubrique: 'Mémo' },
    { texte: 'Bonne foi <loyauté> : Les Maréchaux', sources: ['cass:marechaux'], rubrique: 'Mémo' },
  ],
  points_incertains: [{ texte: 'Vérifiez dans votre cours les sanctions de l’inexécution.', sources: [] }],
  message: '',
  sources: SOURCES,
  avertissement: "Lexia est un outil d'étude.",
  controle: { citations_retirees: 0, elements_retires: 0, references_non_verifiees: [], recherche: 'hybride' },
}

const autre = (id: string, titre: string, texte: string): ReponseChat => ({
  ...FICHE, reponse_id: id, titre, reponse_directe: [{ texte, sources: [] }], droit_positif: [], explication: [], points_incertains: [],
  sources: [],
})

const FICHES: Favori[] = [
  { id: 'f-force', question: 'Fiche sur la force obligatoire', mode: 'fiche', enregistre_le: '2026-11-26T10:00:00Z', reponse: FICHE,
    matiere: 'droit_des_contrats' },
  { id: 'f-faute', question: 'Fiche sur la faute', mode: 'fiche', enregistre_le: '2026-11-25T10:00:00Z',
    reponse: autre('f-faute', 'La responsabilité pour faute', 'Article 1240 : faute, dommage, lien de causalité.'), matiere: 'droit_civil' },
  { id: 'f-ancienne', question: 'Le dol', mode: 'expliquer', enregistre_le: '2026-11-20T10:00:00Z',
    reponse: autre('f-ancienne', 'Le dol', 'Manœuvres pour obtenir le consentement.') },
]

const PROFIL = {
  email: 'etu@exemple.fr', cree_le: '2026-11-11T10:00:00+00:00', formule_fin: null, email_verifie: true,
  formule: { id: 'gratuit', nom: 'Gratuit', prix_mensuel_euros: 0, questions_par_jour: 10, quiz_par_jour: 2, description: '', avantages: [] },
  usage: { jour: '2026-11-11', questions: 3, quiz: 0 },
  admin: false,
}
const MATIERES = [
  { id: 'droit_civil', libelle: 'Droit civil', sources: ['code_civil'] },
  { id: 'droit_des_contrats', libelle: 'Droit des contrats', sources: ['code_civil'] },
]

const repondre = (corps: unknown, status = 200) =>
  Promise.resolve(new Response(JSON.stringify(corps), { status, headers: { 'Content-Type': 'application/json' } }))

beforeEach(() => {
  localStorage.clear()
  window.history.pushState({}, '', '/app/fiches')
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url.endsWith('/auth/session') || url.endsWith('/auth/moi')) return repondre(PROFIL)
    if (url.endsWith('/config')) return repondre({ comptes: true, contact_email: null })
    if (url.endsWith('/matieres')) return repondre(MATIERES)
    if (url.endsWith('/chat')) return repondre(FICHE)
    return repondre({}, 404)
  }))
})

afterEach(() => vi.unstubAllGlobals())

async function ouvrirFiches() {
  ecrireFavoris(FICHES, 'etu@exemple.fr')
  render(<Site />)
  await screen.findByText('La force obligatoire du contrat')
  await screen.findByRole('button', { name: /Droit civil \(1\)/ }) // matieres chargees
}

describe('Mes fiches', () => {
  it('une fiche de revision montre ses rubriques sans clic, memo encadre, textes et sources replies', async () => {
    await ouvrirFiches()
    fireEvent.click(screen.getByRole('button', { name: /^La force obligatoire du contrat/ }))
    for (const rubrique of ['Définition', 'Règles à retenir', 'Jurisprudence clé', 'Pièges fréquents', 'Mémo']) {
      const titre = screen.getByRole('heading', { name: rubrique })
      expect(titre.closest('details')).toBeNull()
    }
    const memo = screen.getByRole('region', { name: 'Mémo' })
    expect(within(memo).getByText(/Force obligatoire : article 1103/)).toBeInTheDocument()
    // points_incertains : « Points à vérifier », plus de doublon avec la rubrique « Pièges fréquents »
    expect(screen.getByRole('heading', { name: 'Points à vérifier' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Règles essentielles' }).closest('details')).not.toBeNull()
  })

  it('cherche dans le contenu des fiches, sans accents ni majuscules, et filtre par matiere', async () => {
    await ouvrirFiches()
    const champ = screen.getByRole('searchbox', { name: 'Chercher dans mes fiches' })
    fireEvent.change(champ, { target: { value: 'marechaux' } }) // dans la jurisprudence cle, avec accent
    expect(screen.getByText('1 fiche sur 3.')).toBeInTheDocument()
    expect(screen.queryByText('La responsabilité pour faute')).not.toBeInTheDocument()
    fireEvent.change(champ, { target: { value: 'ARTICLE 1240' } })
    expect(screen.getByText('La responsabilité pour faute')).toBeInTheDocument()
    expect(screen.queryByText('La force obligatoire du contrat')).not.toBeInTheDocument()
    fireEvent.change(champ, { target: { value: 'introuvable' } })
    expect(screen.getByText('Aucune fiche ne correspond.')).toBeInTheDocument()
    fireEvent.change(champ, { target: { value: '' } })

    const groupe = screen.getByRole('group', { name: 'Matière' })
    expect(within(groupe).getAllByRole('button').map((b) => b.textContent))
      .toEqual(['Toutes (3)', 'Droit civil (1)', 'Droit des contrats (1)', 'Sans matière (1)'])
    fireEvent.click(within(groupe).getByRole('button', { name: 'Droit des contrats (1)' }))
    expect(screen.getByText('La force obligatoire du contrat')).toBeInTheDocument()
    expect(screen.queryByText('Le dol')).not.toBeInTheDocument()
    expect(screen.getByText(/Fiche · Droit des contrats · 26\/11\/2026/)).toBeInTheDocument()
    fireEvent.click(within(groupe).getByRole('button', { name: 'Sans matière (1)' }))
    expect(screen.getByText('Le dol')).toBeInTheDocument()
    expect(screen.queryByText('La force obligatoire du contrat')).not.toBeInTheDocument()
  })

  it('« Imprimer ou PDF » imprime la fiche seule, dans un cadre a part', async () => {
    await ouvrirFiches()
    fireEvent.click(screen.getByRole('button', { name: 'Imprimer ou PDF : fiche « La force obligatoire du contrat »' }))
    const cadre = document.querySelector('iframe')!
    expect(cadre.getAttribute('aria-hidden')).toBe('true')
    expect(cadre.srcdoc).toContain('<h1>La force obligatoire du contrat</h1>')
    expect(cadre.srcdoc).toContain('Droit des contrats')
    cadre.remove()
  })

  it('« Réviser cette fiche » ajoute sa seule carte aux revisions, sans toucher aux autres fiches', async () => {
    await ouvrirFiches()
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Réviser cette fiche : « La force obligatoire du contrat »' }))
    })
    expect(lireCartes('etu@exemple.fr').map((c) => c.id)).toEqual(['fiche:f-force'])
    expect(screen.getByText('Dans vos révisions')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /^Réviser cette fiche :/ })).toHaveLength(2)
  })

  it('la matiere choisie a l envoi est gardee avec la fiche', async () => {
    window.history.pushState({}, '', '/app/matieres')
    render(<Site />)
    const carte = (await screen.findByRole('heading', { name: 'Droit des contrats' })).parentElement!
    fireEvent.click(within(carte).getByRole('button', { name: 'Poser une question' }))
    fireEvent.click(await screen.findByRole('radio', { name: 'Fiche' }))
    fireEvent.change(screen.getByLabelText('Votre question'), { target: { value: 'la force obligatoire' } })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Envoyer/ }))
    })
    await screen.findAllByText('La force obligatoire du contrat')
    expect(lireFavoris('etu@exemple.fr').map((f) => [f.id, f.matiere])).toEqual([['f-force', 'droit_des_contrats']])
  })
})

describe('fonctions des fiches', () => {
  it('filtrerFiches et matieresDesFiches', () => {
    expect(filtrerFiches(FICHES, 'imprevision force').map((f) => f.id)).toEqual(['f-force'])
    expect(filtrerFiches(FICHES, '', null).map((f) => f.id)).toEqual(['f-ancienne'])
    expect(filtrerFiches(FICHES, '  ').length).toBe(3)
    expect(matieresDesFiches(FICHES, [{ id: 'droit_civil', libelle: 'Droit civil' }]).map((g) => g.libelle))
      .toEqual(['Droit civil', 'droit_des_contrats', 'Sans matière'])
  })

  it('parRubrique garde l ordre et regroupe les elements sans rubrique', () => {
    expect(parRubrique(FICHE.explication, 'À retenir').map(([r, items]) => [r, items.length]))
      .toEqual([['Définition', 1], ['Règles à retenir', 1], ['Jurisprudence clé', 1], ['Pièges fréquents', 1], ['Mémo', 2]])
    expect(parRubrique([{ texte: 'x', sources: [] }], 'À retenir')).toEqual([['À retenir', [{ texte: 'x', sources: [] }]]])
  })

  it('ficheEnHtml : rubriques dans l ordre, memo encadre, sources numerotees, texte echappe, mention IA', () => {
    const html = ficheEnHtml(FICHES[0], 'Droit des contrats')
    const ordre = ['L’essentiel', 'Définition', 'Règles à retenir', 'Jurisprudence clé', 'Pièges fréquents', 'Mémo', 'Points à vérifier',
      'Règles essentielles', 'Sources'].map((t) => html.indexOf(`<h2>${t}</h2>`))
    expect(ordre.every((pos, i) => pos > 0 && (i === 0 || pos > ordre[i - 1]))).toBe(true)
    expect(html).toContain('<section class="memo"><h2>Mémo</h2>')
    expect(html).toContain('Bonne foi &lt;loyauté&gt; : Les Maréchaux <span class="ref">[2]</span>')
    expect(html).not.toContain('<loyauté>')
    expect(html).toContain('Code civil, article 1103 (Version depuis le 1er octobre 2016) : https://www.legifrance.gouv.fr/codes/article_lc/A1103')
    expect(html).toContain('Fiche générée par une intelligence artificielle (Lexia)')
    expect(html).toContain('@page')
  })
})
