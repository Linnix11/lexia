import { beforeEach, describe, expect, it } from 'vitest'
import type { Correction, FicheSource, Quiz, ReponseChat } from './api'
import {
  aReviser, ajouterCartes, carteDeFiche, cartesDuQuiz, effacerCartes, ecrireCartes, INTERVALLES_JOURS, lireCartes,
  MAX_CARTES, reviser, type Carte,
} from './cartes'
import type { Favori } from './favoris'

const source = (id: string, entete: string): FicheSource => ({
  id, label: null, source_id: 'code_civil', type: 'article', numero: null, entete, url: `https://www.legifrance.gouv.fr/${id}`,
  version: '', en_vigueur: true, date: null, extrait: '',
})

const S1 = source('a1240', 'Code civil, article 1240')
const S2 = source('a1241', 'Code civil, article 1241')

function quiz(format: Quiz['format'], questions: Quiz['questions']): Quiz {
  return { quiz_id: 'q-1', format, theme: 'responsabilité', demande: questions.length, obtenu: questions.length, questions,
    message: '', sources: [S1, S2], avertissement: '' }
}

// 19 novembre 2026, 15 h (heure locale)
const MAINTENANT = new Date(2026, 10, 19, 15, 0)

function nouvelle(id = 'c1'): Carte {
  return { id, origine: 'quiz', recto: 'Recto', verso: 'Verso', sources: [], niveau: 1,
    prochaine: MAINTENANT.toISOString(), creee_le: MAINTENANT.toISOString() }
}

describe('cartes tirees d un questionnaire corrige', () => {
  it('QCM : la bonne reponse et l explication au verso, les sources citees seulement', () => {
    const q = quiz('qcm', [{ index: 0, question: 'Quelle condition ?', choix: ['Une faute', 'Un contrat'] }])
    const c: Correction = { quiz_id: 'q-1', score: 1, total: 1, sources: [S1, S2],
      resultats: [{ index: 0, statut: 'correct', explication: 'Article 1240.', sources: ['a1240'], bonne_reponse: 0 }] }
    const [carte] = cartesDuQuiz(q, c, MAINTENANT)
    expect(carte.id).toBe('quiz:q-1:0')
    expect(carte.recto).toBe('Quelle condition ?')
    expect(carte.verso).toBe('Une faute\n\nArticle 1240.')
    expect(carte.sources).toEqual([{ id: 'a1240', entete: 'Code civil, article 1240', url: S1.url }])
    expect(carte.niveau).toBe(1)
    expect(aReviser([carte], MAINTENANT)).toHaveLength(1)
  })

  it('vrai ou faux et questions ouvertes', () => {
    const vf = quiz('vrai_faux', [{ index: 0, affirmation: 'La faute suffit.' }])
    const cvf: Correction = { quiz_id: 'q-1', score: 0, total: 1, sources: [],
      resultats: [{ index: 0, statut: 'incorrect', explication: '', sources: [], bonne_reponse: false }] }
    expect(cartesDuQuiz(vf, cvf, MAINTENANT)[0]).toMatchObject({ recto: 'Vrai ou faux : La faute suffit.', verso: 'Faux' })

    const ouv = quiz('ouvertes', [{ index: 0, question: 'Conditions ?' }])
    const cov: Correction = { quiz_id: 'q-1', score: 0, total: 1, sources: [],
      resultats: [{ index: 0, statut: 'partiel', explication: '', sources: [], elements_attendus: ['faute', 'dommage', 'lien'] }] }
    expect(cartesDuQuiz(ouv, cov, MAINTENANT)[0].verso).toBe('Éléments attendus : faute ; dommage ; lien')
  })

  it('ecarte une question sans reponse connue', () => {
    const q = quiz('ouvertes', [{ index: 0, question: 'Conditions ?' }])
    const c: Correction = { quiz_id: 'q-1', score: 0, total: 1, sources: [],
      resultats: [{ index: 0, statut: 'a_verifier', explication: '', sources: [] }] }
    expect(cartesDuQuiz(q, c, MAINTENANT)).toEqual([])
  })
})

describe('carte tiree d une fiche', () => {
  const reponse = (r: Partial<ReponseChat>): ReponseChat => ({
    reponse_id: 'r-1', statut: 'reponse', titre: 'La faute', droit_positif: [], explication: [], points_incertains: [],
    message: '', sources: [S1, S2], avertissement: '', controle: {} as ReponseChat['controle'], ...r,
  })
  const fiche = (r: Partial<ReponseChat>): Favori => ({ id: 'r-1', question: 'Qu’est-ce que la faute ?', mode: 'fiche',
    enregistre_le: MAINTENANT.toISOString(), reponse: reponse(r) })

  it('reponse directe au verso', () => {
    const carte = carteDeFiche(fiche({ reponse_directe: [{ texte: 'Un manquement.', sources: ['a1240'] }] }), MAINTENANT)
    expect(carte).toMatchObject({ id: 'fiche:r-1', origine: 'fiche', recto: 'Qu’est-ce que la faute ?', verso: 'Un manquement.' })
    expect(carte?.sources.map((s) => s.id)).toEqual(['a1240'])
  })

  it('a defaut, les trois premieres regles de droit positif ; rien sans contenu', () => {
    const dp = ['A.', 'B.', 'C.', 'D.'].map((texte) => ({ texte, sources: ['a1241'] }))
    expect(carteDeFiche(fiche({ droit_positif: dp }), MAINTENANT)?.verso).toBe('A.\nB.\nC.')
    expect(carteDeFiche(fiche({}), MAINTENANT)).toBeNull()
  })
})

describe('repetition espacee', () => {
  it('une carte sue monte d un niveau et revient apres 1, 3, 7, 14 puis 30 jours, a minuit', () => {
    let c = nouvelle()
    const vus: string[] = []
    for (let i = 0; i < 6; i++) {
      c = reviser(c, true, MAINTENANT)
      vus.push(`${c.niveau}:${new Date(c.prochaine).getDate()}`)
    }
    expect(INTERVALLES_JOURS).toEqual([1, 3, 7, 14, 30])
    // 20 nov., 22 nov., 26 nov., 3 dec., 19 dec., puis 19 dec. encore (niveau 5 garde 30 jours)
    expect(vus).toEqual(['2:20', '3:22', '4:26', '5:3', '5:19', '5:19'])
    expect(new Date(c.prochaine).getHours()).toBe(0)
  })

  it('une carte ratee repart au niveau 1, a revoir demain', () => {
    const c = reviser({ ...nouvelle(), niveau: 4 }, false, MAINTENANT)
    expect(c.niveau).toBe(1)
    expect(new Date(c.prochaine)).toEqual(new Date(2026, 10, 20))
    expect(aReviser([c], MAINTENANT)).toEqual([])
    expect(aReviser([c], new Date(2026, 10, 20, 0, 1))).toHaveLength(1)
  })
})

describe('stockage dans le navigateur', () => {
  beforeEach(() => localStorage.clear())

  it('une cle par compte, sans l adresse, effacee avec le compte', () => {
    ecrireCartes([nouvelle()], 'etu@exemple.fr')
    expect(lireCartes('ETU@exemple.fr')).toHaveLength(1)
    expect(lireCartes('autre@exemple.fr')).toEqual([])
    expect(Object.keys(localStorage).join()).not.toContain('etu@')
    effacerCartes('etu@exemple.fr')
    expect(lireCartes('etu@exemple.fr')).toEqual([])
  })

  it('ajout sans doublon (la progression est gardee) et dans la limite', () => {
    const sue = { ...nouvelle('a'), niveau: 3 }
    const r = ajouterCartes([sue], [nouvelle('a'), nouvelle('b')])
    expect(r.ajoutees).toBe(1)
    expect(r.liste.find((c) => c.id === 'a')?.niveau).toBe(3)

    const pleines = Array.from({ length: MAX_CARTES }, (_, i) => nouvelle(`p${i}`))
    const r2 = ajouterCartes(pleines, [nouvelle('x')])
    expect(r2).toMatchObject({ ajoutees: 0, refusees: 1 })
    expect(r2.liste).toHaveLength(MAX_CARTES)
  })
})
