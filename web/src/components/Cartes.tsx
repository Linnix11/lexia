import { useApp } from '../state/contexte'
import { Card, CardHead } from './Layout'

const OFFICIELLES = [
  { sym: '§', nom: 'Légifrance', desc: '25 codes et lois en vigueur (archives DILA)', url: 'https://www.legifrance.gouv.fr/Droit-francais' },
  { sym: '⚖', nom: 'Cour de cassation', desc: 'Arrêts publiés depuis 2000, toutes chambres',
    url: 'https://www.courdecassation.fr/acces-rapide-judilibre/donnees-ouvertes-open-data-et-api' },
  { sym: '⚖', nom: 'Conseil d’État', desc: 'Recueil Lebon et Tribunal des conflits', url: 'https://www.conseil-etat.fr/' },
  { sym: '◈', nom: 'Conseil constitutionnel', desc: 'Constitution, décisions DC et QPC', url: 'https://www.conseil-constitutionnel.fr/les-decisions' },
]

const fleche = 'text-[14px] text-[#9aa19a] hover:text-forest'

export function CarteSources() {
  return (
    <Card className="p-4 tab:p-[19px]">
      <CardHead titre="Sources de confiance" sousTitre="Textes et jurisprudence consultables"
        droite={<a className={fleche} href="https://www.legifrance.gouv.fr/Droit-francais" target="_blank" rel="noreferrer" aria-label="Ouvrir Légifrance">↗</a>} />
      <ul className="mt-2.5">
        {OFFICIELLES.map((s) => (
          <li key={s.nom} className="flex items-start gap-[11px] border-t border-line-soft py-3">
            <span aria-hidden className="grid size-[30px] shrink-0 place-items-center rounded-lg bg-[#eef1eb] text-[14px] text-forest">{s.sym}</span>
            <span className="min-w-0 flex-1">
              <strong className="block text-[11px] leading-[1.3] font-semibold">{s.nom}</strong>
              <small className="mt-1 block text-[10px] text-muted">{s.desc}</small>
            </span>
            <a className={fleche} href={s.url} target="_blank" rel="noreferrer" aria-label={`Ouvrir ${s.nom}`}>↗</a>
          </li>
        ))}
      </ul>
    </Card>
  )
}

const OUVRAGES = [
  { couv: 'C°', classe: 'bg-[#d9e2d9] text-forest', titre: 'Manuels de droit constitutionnel', note: 'Repères bibliographiques · à confirmer selon votre cours' },
  { couv: 'D°', classe: 'bg-[#e7dfd1] text-[#795932]', titre: 'Introduction générale au droit', note: 'Références sélectionnées par les bibliothèques' },
  { couv: 'O°', classe: 'bg-[#e4e1ed] text-[#5b5777]', titre: 'Droit des obligations', note: 'Contrats et responsabilité civile' },
]

export function CarteBibliotheque({ complete = false }: { complete?: boolean }) {
  const liste = complete ? OUVRAGES : OUVRAGES.slice(0, 2)
  return (
    <Card className="p-4 tab:p-[19px]">
      <CardHead titre="Bibliothèque universitaire" sousTitre="Références recommandées à explorer"
        droite={<a className={fleche} href="https://www.sudoc.abes.fr/" target="_blank" rel="noreferrer" aria-label="Ouvrir le catalogue Sudoc">↗</a>} />
      {liste.map((o) => (
        <div key={o.titre} className="mt-3 flex gap-[11px] border-t border-line-soft pt-3">
          <div aria-hidden className={`grid h-11 w-[34px] shrink-0 place-items-center rounded font-display text-[15px] ${o.classe}`}>{o.couv}</div>
          <div className="min-w-0">
            <strong className="block text-[11px] leading-[1.35]">{o.titre}</strong>
            <small className="mt-1 block text-[10px] leading-[1.35] text-muted">{o.note}</small>
            <a href="https://www.sudoc.abes.fr/" target="_blank" rel="noreferrer" className="mt-[5px] inline-block text-[10px] text-forest hover:underline">
              Rechercher au catalogue universitaire ↗
            </a>
          </div>
        </div>
      ))}
      <p className="mt-3.5 border-l-2 border-[#c8a16d] bg-cream px-2.5 py-[9px] text-[10px] leading-[1.45] text-[#746347]">
        Les manuels commerciaux sont protégés. Lexia référence les ouvrages et leurs catalogues ; leur texte intégral
        nécessite un accès bibliothèque ou une licence.
      </p>
    </Card>
  )
}

export function CarteOutils() {
  const { envoyer, ouvrirQuiz, setVue } = useApp()
  const outils = [
    { ico: '◉', titre: 'Questionnaire', desc: 'Créer un quiz personnalisé', action: () => ouvrirQuiz() },
    { ico: '▤', titre: 'Fiche de révision', desc: 'Synthétiser un cours',
      action: () => envoyer('Prépare une fiche de révision sur les sources du droit', 'fiche') },
    { ico: '⌕', titre: 'Méthodologie', desc: 'Suivre les étapes clés',
      action: () => envoyer('Explique la méthode du commentaire d’arrêt en étapes', 'commentaire') },
    { ico: '✎', titre: 'Cas pratique', desc: 'Raisonner avec méthode',
      action: () => { setVue('assistant'); envoyer('Aide-moi à résoudre un cas pratique de responsabilité civile, étape par étape', 'cas_pratique') } },
  ]
  return (
    <Card className="p-4 tab:px-[19px] tab:py-[18px]">
      <CardHead titre="Boîte à outils" sousTitre="Des formats pour apprendre activement" />
      <div className="mt-3.5 grid grid-cols-2 gap-[9px] desk:grid-cols-4">
        {outils.map((o) => (
          <button key={o.titre} type="button" onClick={o.action}
            className="min-h-[82px] rounded-[9px] border border-line bg-[#faf9f5] px-2.5 py-[11px] text-left text-ink hover:border-[#9fb0a2] hover:bg-[#f6f8f3] tab:min-h-[91px]">
            <div aria-hidden className="mb-[7px] text-[18px]">{o.ico}</div>
            <strong className="block text-[11px] font-semibold">{o.titre}</strong>
            <span className="mt-1 block text-[10px] leading-[1.3] text-muted">{o.desc}</span>
          </button>
        ))}
      </div>
    </Card>
  )
}
