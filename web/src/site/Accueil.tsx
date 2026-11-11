import { Lien } from '../lib/router'
import { useSession } from '../state/session'
import { Formules } from './Tarifs'
import { PublicLayout, Section, Surtitre, bouton, boutonSecondaire } from './Public'

const PILIERS = [
  { titre: 'Des sources officielles', texte: 'Constitution, Code civil, décisions du Conseil constitutionnel et arrêts publiés de la Cour de cassation, issus des données ouvertes de l’État.' },
  { titre: 'Chaque affirmation est citée', texte: 'Les règles de droit renvoient à l’article ou à la décision qui les fonde. Une référence introuvable est retirée avant de vous être montrée.' },
  { titre: 'La bonne version du texte', texte: 'Les articles sont datés. Un clic suffit pour vérifier qu’une version est toujours en vigueur.' },
]

const ETAPES = [
  ['Posez votre question', 'Une notion de cours, un article, une décision, ou une méthode : cas pratique, commentaire d’arrêt, dissertation.'],
  ['Lexia cherche dans les sources', 'Textes officiels d’abord, puis jurisprudence. Si rien ne permet de répondre, Lexia le dit au lieu d’inventer.'],
  ['Vous vérifiez et révisez', 'Ouvrez chaque source, enregistrez la réponse en fiche, entraînez-vous avec des questionnaires corrigés.'],
]

export function Accueil() {
  const { profil } = useSession()
  const cible = profil ? '/app' : '/inscription'
  return (
    <PublicLayout>
      <Section className="grid items-center gap-10 py-14 desk:grid-cols-[1.1fr_.9fr] desk:py-20">
        <div>
          <Surtitre>Droit français · Licence</Surtitre>
          <h1 className="mt-3 font-display text-[36px] leading-[1.08] font-normal tracking-[-.8px] tab:text-[48px]">
            Comprendre le droit,<br />sources à l’appui.
          </h1>
          <p className="mt-4 max-w-[520px] text-[15px] leading-[1.6] text-muted">
            Lexia est un assistant d’étude pour les étudiants en droit : des explications claires, des fiches et des
            questionnaires, toujours appuyés sur les textes et les décisions que vous pouvez ouvrir et vérifier.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Lien href={cible} className={bouton}>{profil ? 'Ouvrir mon espace' : 'Créer un compte gratuit'}</Lien>
            <Lien href="/tarifs" className={boutonSecondaire}>Voir les formules</Lien>
          </div>
          <p className="mt-3 text-[12px] text-muted">Gratuit : 10 questions et 2 questionnaires par jour, sans carte bancaire.</p>
        </div>

        <figure aria-label="Exemple de réponse" className="rounded-xl border border-line bg-surface p-5 shadow-[0_12px_40px_#17241d10]">
          <div className="ml-auto max-w-[85%] rounded-[10px] bg-[#edf1eb] px-3.5 py-2.5 text-[12px]">Quelles sont les conditions de la responsabilité pour faute ?</div>
          <div className="mt-3 rounded-[10px] bg-[#f6f4ee] px-4 py-3.5 text-[12.5px] leading-[1.6]">
            <div className="font-display text-[17px]">La responsabilité pour faute</div>
            <div className="mt-2.5 text-[10px] font-bold tracking-[1.4px] text-forest uppercase">Droit positif</div>
            <p>Tout fait de l’homme qui cause à autrui un dommage oblige celui par la faute duquel il est arrivé à le réparer. <span className="font-semibold text-forest">[S1]</span></p>
            <p className="mt-1">La négligence et l’imprudence engagent aussi la responsabilité. <span className="font-semibold text-forest">[S2]</span></p>
            <div className="mt-2.5 text-[10px] font-bold tracking-[1.4px] text-muted uppercase">Explication</div>
            <p>Trois conditions : un fait fautif, un dommage, un lien de causalité. <span className="font-semibold text-forest">[S1]</span></p>
            <div className="mt-3 border-t border-line-soft pt-2 text-[11px] text-muted">
              <span className="text-forest">[S1]</span> Code civil, article 1240 · en vigueur depuis le 1er octobre 2016<br />
              <span className="text-forest">[S2]</span> Code civil, article 1241 · en vigueur depuis le 1er octobre 2016
            </div>
          </div>
          <figcaption className="mt-2 text-[11px] text-muted">Exemple de présentation d’une réponse.</figcaption>
        </figure>
      </Section>

      <Section className="grid gap-4 pb-14 tab:grid-cols-3">
        {PILIERS.map((p) => (
          <div key={p.titre} className="rounded-xl border border-line bg-surface p-5">
            <h2 className="text-[15px] font-semibold">{p.titre}</h2>
            <p className="mt-2 text-[13px] leading-[1.6] text-muted">{p.texte}</p>
          </div>
        ))}
      </Section>

      <Section className="pb-16">
        <Surtitre>Comment ça marche</Surtitre>
        <h2 className="mt-2 font-display text-[28px] font-normal">Trois étapes, aucune réponse sans source.</h2>
        <ol className="mt-6 grid gap-4 tab:grid-cols-3">
          {ETAPES.map(([titre, texte], i) => (
            <li key={titre} className="rounded-xl border border-line bg-surface p-5">
              <span className="grid size-8 place-items-center rounded-full bg-mint font-display text-[15px] text-forest">{i + 1}</span>
              <h3 className="mt-3 text-[14px] font-semibold">{titre}</h3>
              <p className="mt-1.5 text-[13px] leading-[1.6] text-muted">{texte}</p>
            </li>
          ))}
        </ol>
      </Section>

      <Section className="pb-16">
        <Surtitre>Formules</Surtitre>
        <h2 className="mt-2 mb-6 font-display text-[28px] font-normal">Commencez gratuitement.</h2>
        <Formules />
      </Section>

      <Section className="pb-16">
        <div className="rounded-xl border-l-2 border-[#c8a16d] bg-cream px-5 py-4 text-[13px] leading-[1.6] text-[#746347]">
          Lexia est un outil d’étude. Il ne donne pas de conseil sur une situation personnelle et ne remplace ni vos
          cours ni un professionnel du droit. Vérifiez toujours les sources citées.
        </div>
      </Section>
    </PublicLayout>
  )
}
