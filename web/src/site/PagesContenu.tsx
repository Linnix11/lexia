// Pages publiques de contenu (D116) : liste des matieres, page de chaque matiere, guides de methode et fiches.
// Chargees a part (lazy) et compilees en HTML a la publication (web/scripts/prerendu.mjs) : lisibles sans
// JavaScript par les moteurs de recherche et les moteurs de reponse.
import { Lien } from '../lib/router'
import { grouperParAnnee } from '../lib/matieres'
import { useSession } from '../state/session'
import { citation, libelleCitation, versionCourte } from './contenu/citations'
import { GUIDES, clesCitations, guideParSlug, type Bloc } from './contenu/guides'
import { MATIERES_PUBLIQUES, matiereParSlug } from './contenu/matieres'
import { PublicLayout, Section, Surtitre, bouton, boutonSecondaire } from './Public'
import { questionsMatiere } from './seo'

const LIBELLES_ANNEES: Record<string, string> = { L1: 'Licence 1', L2: 'Licence 2', L3: 'Licence 3' }
const dateLisible = (iso: string) =>
  new Date(`${iso}T12:00:00Z`).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' })

function FilAriane({ etapes }: { etapes: [string, string?][] }) {
  return (
    <nav aria-label="Fil d’Ariane" className="text-[12px] text-muted">
      <ol className="flex flex-wrap gap-1">
        <li><Lien href="/" className="hover:text-forest">Accueil</Lien></li>
        {etapes.map(([nom, href]) => (
          <li key={nom} className="before:mr-1 before:content-['›']">
            {href ? <Lien href={href} className="hover:text-forest">{nom}</Lien> : <span aria-current="page">{nom}</span>}
          </li>
        ))}
      </ol>
    </nav>
  )
}

/** Article officiel cite : texte (alineas choisis), lien vers Legifrance ou le site du Conseil constitutionnel, version. */
export function CitationOfficielle({ cle, alineas }: { cle: string; alineas?: number[] }) {
  const c = citation(cle)
  const extrait = alineas ? alineas.map((i) => c.alineas[i]).filter(Boolean) : c.alineas
  const partiel = extrait.length < c.alineas.length
  return (
    <figure className="my-4 rounded-[10px] border-l-2 border-forest bg-surface px-4 py-3">
      <blockquote cite={c.url} className="grid gap-1.5 text-[13.5px] leading-[1.6]">
        {extrait.map((a, i) => <p key={i}>{a}</p>)}
      </blockquote>
      <figcaption className="mt-2 text-[12px] text-muted">
        <a href={c.url} className="font-semibold text-forest underline-offset-2 hover:underline" rel="noopener">{libelleCitation(c)}</a>
        {partiel ? ' (extrait)' : ''} · {versionCourte(c)}
      </figcaption>
    </figure>
  )
}

function BlocGuide({ bloc }: { bloc: Bloc }) {
  if ('p' in bloc) return <p className="mt-3 text-[14px] leading-[1.7]">{bloc.p}</p>
  if ('citation' in bloc) return <CitationOfficielle cle={bloc.citation} alineas={bloc.alineas} />
  const Liste = bloc.ordonnee ? 'ol' : 'ul'
  return (
    <Liste className={`mt-3 grid gap-1.5 pl-5 text-[14px] leading-[1.6] ${bloc.ordonnee ? 'list-decimal' : 'list-disc'}`}>
      {bloc.liste.map((x) => <li key={x}>{x}</li>)}
    </Liste>
  )
}

function Faq({ questions }: { questions: { question: string; reponse: string }[] }) {
  return (
    <section aria-labelledby="faq" className="mt-10">
      <h2 id="faq" className="font-display text-[24px] font-normal">Questions fréquentes</h2>
      <dl className="mt-4 grid gap-4">
        {questions.map((q) => (
          <div key={q.question} className="rounded-xl border border-line bg-surface p-4">
            <dt className="text-[14px] font-semibold">{q.question}</dt>
            <dd className="mt-1.5 text-[13.5px] leading-[1.6] text-muted">{q.reponse}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}

function Inscription({ texte }: { texte: string }) {
  const { profil } = useSession()
  return (
    <aside className="mt-10 rounded-xl border border-forest bg-mint px-5 py-5">
      <p className="text-[14px] leading-[1.6] text-ink">{texte}</p>
      <div className="mt-4 flex flex-wrap gap-3">
        <Lien href={profil ? '/app' : '/inscription'} className={bouton}>{profil ? 'Ouvrir mon espace' : 'Créer un compte gratuit'}</Lien>
        <Lien href="/tarifs" className={boutonSecondaire}>Voir les formules</Lien>
      </div>
    </aside>
  )
}

function Avertissement() {
  return (
    <p className="mt-8 text-[12px] leading-[1.6] text-muted">
      Page d’étude, pas un avis juridique. Les articles sont cités dans leur version en vigueur à la date indiquée :
      vérifiez-les sur le site officiel avant de les utiliser.
    </p>
  )
}

export function IndexMatieres() {
  const groupes = grouperParAnnee(MATIERES_PUBLIQUES)
  return (
    <PublicLayout>
      <Section className="py-12">
        <FilAriane etapes={[['Matières']]} />
        <h1 className="mt-4 font-display text-[34px] leading-[1.1] font-normal tracking-[-.6px]">Les {MATIERES_PUBLIQUES.length} matières de la licence de droit</h1>
        <p className="mt-3 max-w-[680px] text-[14px] leading-[1.6] text-muted">
          Lexia couvre les matières les plus enseignées de la L1 à la L3, classées d’après les maquettes de huit facultés
          de droit. Pour chacune : ce qu’elle couvre, une question de cours avec l’article officiel, les sources
          consultées et les questions fréquentes.
        </p>
        {groupes.map((g) => (
          <section key={g.titre} aria-labelledby={`annee-${g.annee ?? 'autres'}`} className="mt-10">
            <h2 id={`annee-${g.annee ?? 'autres'}`} className="font-display text-[24px] font-normal">{g.titre}</h2>
            <ul className="mt-4 grid gap-3 tab:grid-cols-2 desk:grid-cols-3">
              {g.matieres.map((m) => {
                const mp = MATIERES_PUBLIQUES.find((x) => x.id === m.id)!
                return (
                  <li key={m.id}>
                    <Lien href={`/matieres/${mp.slug}`} className="block h-full rounded-xl border border-line bg-surface p-4 hover:border-[#9eafa3]">
                      <span className="text-[15px] font-semibold text-forest">{m.libelle}</span>
                      <span className="mt-1.5 block text-[12.5px] leading-[1.55] text-muted">{mp.presentation.split('. ')[0]}.</span>
                    </Lien>
                  </li>
                )
              })}
            </ul>
          </section>
        ))}
        <Inscription texte="Posez vos questions de cours dans la matière de votre choix : chaque réponse cite l’article ou la décision qui la fonde." />
      </Section>
    </PublicLayout>
  )
}

export function PageMatiere({ slug }: { slug: string }) {
  const m = matiereParSlug(slug)!
  const annee = LIBELLES_ANNEES[m.annee ?? ''] ?? 'Licence'
  const principales = new Set(m.principales ?? [])
  const sources = [...m.sources].sort((a, b) => Number(principales.has(b)) - Number(principales.has(a)))
  const memeAnnee = MATIERES_PUBLIQUES.filter((x) => x.annee === m.annee && x.id !== m.id)
  const guides = GUIDES.filter((g) => m.guides?.includes(g.slug))
  return (
    <PublicLayout>
      <Section className="py-12">
        <article className="max-w-[760px]">
          <FilAriane etapes={[['Matières', '/matieres'], [m.libelle]]} />
          <div className="mt-5"><Surtitre>{annee} · Droit français</Surtitre></div>
          <h1 className="mt-3 font-display text-[34px] leading-[1.1] font-normal tracking-[-.6px]">{m.libelle}</h1>
          <p className="mt-4 text-[15px] leading-[1.7]">{m.presentation}</p>

          {(m.mots?.length ?? 0) > 0 && (
            <section aria-labelledby="notions" className="mt-8">
              <h2 id="notions" className="font-display text-[22px] font-normal">Notions et intitulés de cours</h2>
              <ul className="mt-3 flex flex-wrap gap-2">
                {m.mots!.map((x) => <li key={x} className="rounded-full border border-line bg-chip px-3 py-1 text-[12.5px]">{x}</li>)}
              </ul>
            </section>
          )}

          <section aria-labelledby="question-cours" className="mt-8">
            <h2 id="question-cours" className="font-display text-[22px] font-normal">Question de cours</h2>
            {m.questions.map((q) => (
              <div key={q.question} className="mt-4">
                <h3 className="text-[15px] font-semibold">{q.question}</h3>
                <p className="mt-2 text-[14px] leading-[1.7]">{q.reponse}</p>
                {q.citations.map((c) => <CitationOfficielle key={c.cle} cle={c.cle} alineas={c.alineas} />)}
              </div>
            ))}
          </section>

          <section aria-labelledby="sources" className="mt-8">
            <h2 id="sources" className="font-display text-[22px] font-normal">Sources consultées par Lexia</h2>
            <p className="mt-2 text-[13px] text-muted">Textes et décisions officiels, issus des données ouvertes de l’État et des institutions. Les principales sont en tête.</p>
            <ul className="mt-3 grid gap-1.5 pl-5 text-[14px] list-disc">
              {sources.map((s) => <li key={s}>{m.noms_sources?.[s] ?? s}</li>)}
            </ul>
          </section>

          {guides.length > 0 && (
            <section aria-labelledby="guides" className="mt-8">
              <h2 id="guides" className="font-display text-[22px] font-normal">Guides utiles</h2>
              <ul className="mt-3 grid gap-1.5 pl-5 text-[14px] list-disc">
                {guides.map((g) => <li key={g.slug}><Lien href={`/guides/${g.slug}`} className="text-forest underline-offset-2 hover:underline">{g.titre}</Lien></li>)}
              </ul>
            </section>
          )}

          {/* la question de cours est deja montree plus haut : la liste visible commence apres elle */}
          <Faq questions={questionsMatiere(m).slice(m.questions.length)} />
          <Inscription texte={`Révisez le ${m.libelle.charAt(0).toLowerCase()}${m.libelle.slice(1)} avec Lexia : explications, fiches et questionnaires, avec le texte officiel à un clic.`} />

          {memeAnnee.length > 0 && (
            <nav aria-label={`Autres matières de ${annee}`} className="mt-10">
              <h2 className="text-[13px] font-semibold text-muted">Autres matières de {annee}</h2>
              <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[13px]">
                {memeAnnee.map((x) => <li key={x.id}><Lien href={`/matieres/${x.slug}`} className="text-forest hover:underline">{x.libelle}</Lien></li>)}
              </ul>
            </nav>
          )}
          <Avertissement />
        </article>
      </Section>
    </PublicLayout>
  )
}

export function IndexGuides() {
  return (
    <PublicLayout>
      <Section className="py-12">
        <FilAriane etapes={[['Guides']]} />
        <h1 className="mt-4 font-display text-[34px] leading-[1.1] font-normal tracking-[-.6px]">Guides de méthode et fiches de droit</h1>
        <p className="mt-3 max-w-[680px] text-[14px] leading-[1.6] text-muted">
          Méthodes des exercices de la licence et fiches de révision. Chaque règle renvoie à l’article officiel qui la
          fonde, cité dans sa version en vigueur.
        </p>
        <ul className="mt-8 grid gap-3 tab:grid-cols-2">
          {GUIDES.map((g) => (
            <li key={g.slug}>
              <Lien href={`/guides/${g.slug}`} className="block h-full rounded-xl border border-line bg-surface p-5 hover:border-[#9eafa3]">
                <span className="text-[11px] font-bold tracking-[1.4px] text-muted uppercase">{g.niveau}</span>
                <span className="mt-1 block text-[16px] font-semibold text-forest">{g.titre}</span>
                <span className="mt-1.5 block text-[13px] leading-[1.55] text-muted">{g.description}</span>
              </Lien>
            </li>
          ))}
        </ul>
        <Inscription texte="Entraînez-vous ensuite avec Lexia : modes Cas pratique, Commentaire d’arrêt et Dissertation, sources citées." />
      </Section>
    </PublicLayout>
  )
}

export function PageGuide({ slug }: { slug: string }) {
  const g = guideParSlug(slug)!
  const matieres = MATIERES_PUBLIQUES.filter((m) => g.matieres.includes(m.id))
  return (
    <PublicLayout>
      <Section className="py-12">
        <article className="max-w-[760px]">
          <FilAriane etapes={[['Guides', '/guides'], [g.titre]]} />
          <div className="mt-5"><Surtitre>{g.niveau} · Guide</Surtitre></div>
          <h1 className="mt-3 font-display text-[32px] leading-[1.12] font-normal tracking-[-.5px]">{g.titre}</h1>
          <p className="mt-2 text-[12px] text-muted">
            Publié le <time dateTime={g.publie}>{dateLisible(g.publie)}</time> par Lexia
            {matieres.length > 0 && <> · Matières : {matieres.map((m, i) => (
              <span key={m.id}>{i > 0 && ', '}<Lien href={`/matieres/${m.slug}`} className="text-forest hover:underline">{m.libelle}</Lien></span>
            ))}</>}
          </p>
          <section aria-labelledby="en-bref" className="mt-6 rounded-xl bg-cream px-5 py-4">
            <h2 id="en-bref" className="text-[11px] font-bold tracking-[1.4px] text-forest uppercase">En bref</h2>
            <p className="mt-1.5 text-[14.5px] leading-[1.7]">{g.enBref}</p>
          </section>
          {g.sections.map((s) => (
            <section key={s.titre} className="mt-8">
              <h2 className="font-display text-[23px] font-normal">{s.titre}</h2>
              {s.blocs.map((b, i) => <BlocGuide key={i} bloc={b} />)}
            </section>
          ))}
          {g.faq.length > 0 && <Faq questions={g.faq} />}
          <section aria-labelledby="textes" className="mt-10">
            <h2 id="textes" className="font-display text-[22px] font-normal">Textes cités</h2>
            <ul className="mt-3 grid gap-1 pl-5 text-[13px] list-disc">
              {clesCitations(g).map((k) => {
                const c = citation(k)
                return <li key={k}><a href={c.url} className="text-forest hover:underline" rel="noopener">{libelleCitation(c)}</a> <span className="text-muted">({versionCourte(c)})</span></li>
              })}
            </ul>
          </section>
          <Inscription texte="Appliquez la méthode à vos propres sujets : Lexia vous guide pas à pas et cite les textes officiels." />
          <Avertissement />
        </article>
      </Section>
    </PublicLayout>
  )
}
