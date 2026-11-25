import { useEffect, useState } from 'react'
import { api, type Formule } from '../lib/api'
import { Lien } from '../lib/router'
import { useSession } from '../state/session'
import { FORMULES_PUBLIQUES, Formules } from './Tarifs'
import { LienInscription } from './Invitation'
import { betaFermee } from './beta'
import { PublicLayout, Section, Surtitre, bouton, boutonSecondaire } from './Public'

const PILIERS = [
  { titre: 'Des sources officielles', texte: 'Constitution, 36 codes, lois en vigueur, Conseil constitutionnel, Cour de cassation et Conseil d’État, issus des données ouvertes de l’État.' },
  { titre: 'Chaque affirmation est citée', texte: 'Les règles de droit renvoient à l’article ou à la décision qui les fonde. Une référence introuvable est retirée avant de vous être montrée.' },
  { titre: 'La bonne version du texte', texte: 'Les articles sont datés. Un clic suffit pour vérifier qu’une version est toujours en vigueur.' },
]

const ETAPES = [
  ['Posez votre question', 'Une notion de cours, un article, une décision, ou une méthode : cas pratique, commentaire d’arrêt, dissertation.'],
  ['Lexia cherche dans les sources', 'Textes officiels d’abord, puis jurisprudence. Si rien ne permet de répondre, Lexia le dit au lieu d’inventer.'],
  ['Vous vérifiez et révisez', 'Ouvrez chaque source, enregistrez la réponse en fiche, entraînez-vous avec des questionnaires corrigés.'],
]

export function Accueil() {
  const { profil, config } = useSession()
  const beta = betaFermee(config) // valeur publiee dans le HTML prerendu (D132)
  // Arrivee depuis « Mon compte » apres suppression : sans ce message, rien ne confirmait la suppression.
  // Lu apres le premier rendu, identique a la page prerendue (sinon erreur d'hydratation ; audit du 2026-11-23, D12).
  const [supprime, setSupprime] = useState(false)
  useEffect(() => setSupprime(new URLSearchParams(window.location.search).has('compte-supprime')), [])
  // Limites de la formule gratuite lues sur le serveur, pas ecrites en dur (audit du 2026-11-18, D12)
  const [gratuit, setGratuit] = useState<Formule | null>(FORMULES_PUBLIQUES.find((x) => x.id === 'gratuit') ?? null)
  useEffect(() => {
    api.formules().then((f) => setGratuit(f.find((x) => x.id === 'gratuit') ?? null)).catch(() => undefined)
  }, [])
  return (
    <PublicLayout>
      {supprime && (
        <p role="status" className="border-b border-line bg-mint px-4 py-3 text-center text-[13px] text-forest">
          Votre compte et ses données ont été supprimés définitivement. Seule la trace d’un éventuel paiement est
          conservée dix ans, comme toute pièce comptable.
        </p>
      )}
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
            {profil ? <Lien href="/app" className={bouton}>Ouvrir mon espace</Lien> : <LienInscription className={bouton} />}
            <Lien href="/tarifs" className={boutonSecondaire}>Voir les formules</Lien>
          </div>
          {/* Beta fermee dite sous le bouton : l'inscription exige un code (D129) */}
          {beta && !profil && <p className="mt-3 text-[13px] font-semibold text-forest">Bêta fermée : accès sur invitation.</p>}
          <p className="mt-3 text-[12px] text-muted">
            {gratuit
              ? `Gratuit : ${gratuit.questions_par_jour} questions et ${gratuit.quiz_par_jour} questionnaires par jour, sans carte bancaire.`
              : 'Formule gratuite, sans carte bancaire.'}
          </p>
        </div>

        <figure aria-label="Exemple de réponse" className="rounded-xl border border-line bg-surface p-5 shadow-[0_12px_40px_#17241d10]">
          <div className="ml-auto max-w-[85%] rounded-[10px] bg-[#edf1eb] px-3.5 py-2.5 text-[12px]">Quelles sont les conditions de la responsabilité pour faute ?</div>
          <div className="mt-3 rounded-[10px] bg-[#f6f4ee] px-4 py-3.5 text-[12.5px] leading-[1.6]">
            <div className="font-display text-[17px]">La responsabilité pour faute</div>
            {/* meme presentation que l'espace : l'essentiel et l'exemple d'abord, sources numerotees [1], [2] (D12) */}
            <div className="mt-2.5 text-[11px] font-bold tracking-[1.4px] text-forest uppercase">L’essentiel</div>
            <p>Celui qui cause un dommage à autrui par sa faute doit le réparer : il faut une faute, un dommage et un lien de causalité. <span className="font-semibold text-forest">[1]</span></p>
            <p className="mt-1">Une simple négligence ou imprudence suffit. <span className="font-semibold text-forest">[2]</span></p>
            <div className="mt-2.5 text-[11px] font-bold tracking-[1.4px] text-muted uppercase">Exemple</div>
            <p>Un cycliste renverse un piéton par imprudence : il doit réparer le dommage subi. <span className="font-semibold text-forest">[1]</span></p>
            <div className="mt-3 border-t border-line-soft pt-2 text-[11px] text-muted">
              <span className="font-semibold text-forest">▸ Développements et sources</span><br />
              <span className="text-forest">[1]</span> Code civil, article 1240 · en vigueur depuis le 1er octobre 2016<br />
              <span className="text-forest">[2]</span> Code civil, article 1241 · en vigueur depuis le 1er octobre 2016
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
          Lexia est un outil d’étude. Des faits que vous racontez sont traités comme un cas pratique : Lexia expose
          les règles qui s’y appliquent, sans rédiger de courrier, prédire l’issue d’un litige ni décider de vos
          démarches. Cette analyse générale ne remplace ni vos cours ni un professionnel du droit. Vérifiez toujours
          les sources citées.
        </div>
      </Section>
    </PublicLayout>
  )
}
