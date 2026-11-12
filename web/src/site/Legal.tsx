// Pages legales. Les informations sur l'editeur viennent du .env du serveur (LEGAL_*, CONTACT_EMAIL) :
// tant qu'une valeur manque, un encart « a completer » s'affiche. A faire relire par un juriste.
import type { ReactNode } from 'react'
import { useSession } from '../state/session'
import { PublicLayout, Section, Surtitre } from './Public'

const A = ({ children }: { children: ReactNode }) => (
  <mark className="rounded bg-[#fbf0d9] px-1 text-[#7a5a1e]">{children}</mark>
)

/** Valeur configuree, ou encart « a completer » tant qu'elle manque. */
function V({ v, manque }: { v?: string | null; manque: string }) {
  return v ? <>{v}</> : <A>[{manque} : à compléter]</A>
}

/** Adresse de contact cliquable, ou encart « a completer ». */
function Contact({ adresse }: { adresse: string | null }) {
  return adresse ? <a href={`mailto:${adresse}`} className="underline">{adresse}</a> : <V manque="Adresse e-mail de contact" />
}

function useLegal() {
  const { config } = useSession()
  return { l: config?.legal, contact: config?.contact_email ?? null }
}

function Page({ titre, maj, children }: { titre: string; maj: string; children: ReactNode }) {
  return (
    <PublicLayout>
      <Section className="max-w-[760px] py-12">
        <Surtitre>Informations légales</Surtitre>
        <h1 className="mt-2 font-display text-[32px] font-normal">{titre}</h1>
        <p className="mt-1 mb-8 text-[12px] text-muted">Dernière mise à jour : {maj}</p>
        <div className="grid gap-6 text-[14px] leading-[1.7] [&_h2]:font-display [&_h2]:text-[20px] [&_li]:ml-5 [&_li]:list-disc">
          {children}
        </div>
      </Section>
    </PublicLayout>
  )
}

export function MentionsLegales() {
  const { l, contact } = useLegal()
  return (
    <Page titre="Mentions légales" maj="12 novembre 2026">
      <section>
        <h2>Éditeur du site</h2>
        <p>
          <V v={l?.editeur} manque="Nom et prénom ou raison sociale" /><br />
          <V v={l?.statut} manque="Statut (entreprise individuelle, société, capital le cas échéant)" /><br />
          <V v={l?.adresse} manque="Adresse" /><br />
          <V v={l?.siren} manque="Numéro SIREN / SIRET et RCS le cas échéant" /><br />
          Contact : <Contact adresse={contact} /><br />
          Directeur de la publication : <V v={l?.directeur} manque="Nom" />
        </p>
      </section>
      <section>
        <h2>Hébergement</h2>
        <p>
          Le site est hébergé par HOSTINGER INTERNATIONAL LIMITED, société privée à responsabilité limitée de droit
          chypriote, dont le siège social est situé au 61 Lordou Vironos str., 6023 Larnaca, Chypre.
        </p>
      </section>
      <section>
        <h2>Sources juridiques</h2>
        <p>
          Les textes et décisions affichés proviennent des données ouvertes publiées par la Direction de l’information
          légale et administrative (DILA) et du site du Conseil constitutionnel. Chaque source est accompagnée de sa
          date de récupération et d’un lien vers sa version officielle.
        </p>
      </section>
      <section>
        <h2>Avertissement</h2>
        <p>
          Lexia est un outil d’étude. Les réponses sont générées automatiquement à partir des sources citées et
          peuvent comporter des erreurs ; elles ne constituent pas un avis juridique.
        </p>
      </section>
    </Page>
  )
}

export function Cgu() {
  const { l, contact } = useLegal()
  return (
    <Page titre="Conditions générales d’utilisation" maj="12 novembre 2026">
      <section>
        <h2>1. Objet</h2>
        <p>
          Les présentes conditions encadrent l’utilisation de Lexia, service en ligne d’aide à l’étude du droit
          français édité par <V v={l?.editeur} manque="Éditeur" />. La création d’un compte vaut acceptation de ces conditions.
        </p>
      </section>
      <section>
        <h2>2. Nature du service</h2>
        <ul>
          <li>Lexia fournit des explications, fiches et questionnaires générés automatiquement à partir de sources juridiques officielles.</li>
          <li>Les réponses peuvent être incomplètes ou erronées : l’utilisateur vérifie les sources citées, notamment la version en vigueur des textes.</li>
          <li>Lexia ne fournit aucun conseil juridique personnalisé et ne remplace ni l’enseignement reçu, ni un professionnel du droit.</li>
        </ul>
      </section>
      <section>
        <h2>3. Compte</h2>
        <p>
          Le compte est personnel. L’utilisateur choisit un mot de passe robuste et le garde confidentiel. Il peut
          supprimer son compte à tout moment depuis la page « Mon compte ».
        </p>
      </section>
      <section>
        <h2>4. Formules et limites</h2>
        <p>
          Le service est proposé en formule gratuite et en formules payantes, chacune avec un nombre maximal de
          questions et de questionnaires par jour, indiqué sur la page Tarifs. Les compteurs sont remis à zéro chaque
          jour à minuit (heure de Paris).
        </p>
        <p>
          Aucun paiement n’est encaissé sur le site. Une formule payante est attribuée par l’éditeur sur demande
          (contact : <Contact adresse={contact} />), après accord sur ses conditions (prix, durée, résiliation),
          communiquées par écrit avant toute souscription. Elle reste active jusqu’à la date de fin indiquée sur la
          page « Mon compte ». <A>[Droit de rétractation et modalités de paiement : à compléter avant d’encaisser un
          premier paiement.]</A>
        </p>
      </section>
      <section>
        <h2>5. Usage acceptable</h2>
        <p>
          Sont interdits : l’utilisation automatisée massive, le contournement des limites, la revente du service et
          toute utilisation contraire à la loi. L’éditeur peut suspendre un compte en cas de manquement.
        </p>
      </section>
      <section>
        <h2>6. Disponibilité et responsabilité</h2>
        <p>
          Le service est fourni en l’état, sans garantie de disponibilité continue. Il dépend de prestataires tiers,
          notamment le modèle de langage utilisé pour rédiger les réponses. La responsabilité de l’éditeur ne saurait
          être engagée du fait d’une décision prise sur la base d’une réponse du service.
        </p>
      </section>
      <section>
        <h2>7. Droit applicable</h2>
        <p>
          Les présentes conditions sont soumises au droit français. En cas de litige, l’utilisateur consommateur
          peut recourir gratuitement à un médiateur de la consommation : <V v={l?.mediateur} manque="Nom et coordonnées du médiateur de la consommation" />.
          À défaut d’accord amiable, les tribunaux français sont compétents.
        </p>
      </section>
    </Page>
  )
}

export function Confidentialite() {
  const { l, contact } = useLegal()
  return (
    <Page titre="Politique de confidentialité" maj="12 novembre 2026">
      <section>
        <h2>Responsable du traitement</h2>
        <p>
          <V v={l?.editeur} manque="Éditeur" />, <V v={l?.adresse} manque="Adresse" />. Contact : <Contact adresse={contact} />
        </p>
      </section>
      <section>
        <h2>Données collectées</h2>
        <ul>
          <li><strong>Compte</strong> : adresse e-mail, empreinte chiffrée du mot de passe (le mot de passe lui-même n’est jamais conservé), formule, date de création.</li>
          <li><strong>Utilisation</strong> : nombre de questions et de questionnaires du jour, pour appliquer les limites de votre formule.</li>
          <li><strong>Journaux techniques</strong> : identifiants des sources utilisées, durée de traitement, statut des réponses. Le texte de vos questions n’y est pas enregistré.</li>
          <li><strong>Retours</strong> : avis « utile / pas utile » et motif choisi dans une liste.</li>
        </ul>
        <p>Vos fiches enregistrées restent dans votre navigateur et ne sont pas envoyées au serveur.</p>
      </section>
      <section>
        <h2>Traitement de vos questions</h2>
        <p>
          Pour produire une réponse, le texte de votre question et les extraits juridiques retrouvés sont transmis à
          l’API Gemini de Google, utilisée en niveau payant.{' '}
          {l?.gemini_payant ? (
            <>Selon les conditions de ce niveau, Google n’utilise ni les questions ni les réponses pour améliorer ses
            produits ; il les conserve pendant une durée limitée, uniquement pour détecter les abus, assurer la
            sécurité du service et respecter ses obligations légales.</>
          ) : (
            <A>[La clé Gemini doit passer au niveau payant avant l’ouverture : les conditions de Google n’autorisent que
            ce niveau pour un service proposé à des utilisateurs de l’Espace économique européen.]</A>
          )}{' '}
          N’indiquez pas d’informations personnelles dans vos questions.
        </p>
      </section>
      <section>
        <h2>Finalités et base légale</h2>
        <p>
          Les données sont traitées pour fournir le service (exécution du contrat), appliquer les limites des
          formules et assurer la sécurité du service (intérêt légitime).
        </p>
      </section>
      <section>
        <h2>Durées de conservation</h2>
        <ul>
          <li>Compte et compteurs : jusqu’à la suppression du compte.</li>
          <li>Session de connexion : 30 jours au plus.</li>
          <li>Journaux techniques : 12 mois, puis suppression automatique.</li>
          <li>Sauvegardes de la base des comptes : 14 jours glissants.</li>
        </ul>
      </section>
      <section>
        <h2>Cookies</h2>
        <p>
          Lexia n’utilise qu’un cookie strictement nécessaire : le cookie de session qui vous garde connecté. Aucun
          cookie publicitaire ni de mesure d’audience.
        </p>
      </section>
      <section>
        <h2>Vos droits</h2>
        <p>
          Vous disposez des droits d’accès, de rectification, d’effacement, de limitation, d’opposition et de
          portabilité. Vous pouvez supprimer votre compte vous-même depuis « Mon compte », ou écrire à{' '}
          <Contact adresse={contact} />. Vous pouvez aussi saisir la CNIL (www.cnil.fr).
        </p>
      </section>
    </Page>
  )
}
