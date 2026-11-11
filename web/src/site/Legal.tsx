// Pages legales : modeles a completer par l'editeur (les mentions [A COMPLETER] doivent etre remplacees
// avant l'ouverture au public). A faire relire par un juriste.
import type { ReactNode } from 'react'
import { PublicLayout, Section, Surtitre } from './Public'

const A = ({ children }: { children: ReactNode }) => (
  <mark className="rounded bg-[#fbf0d9] px-1 text-[#7a5a1e]">{children}</mark>
)

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
  return (
    <Page titre="Mentions légales" maj="11 novembre 2026">
      <section>
        <h2>Éditeur du site</h2>
        <p>
          <A>[Nom et prénom ou raison sociale]</A><br />
          <A>[Statut : entreprise individuelle, société… et capital le cas échéant]</A><br />
          <A>[Adresse]</A><br />
          <A>[Numéro SIREN / SIRET et RCS le cas échéant]</A><br />
          Contact : <A>[adresse e-mail de contact]</A><br />
          Directeur de la publication : <A>[Nom]</A>
        </p>
      </section>
      <section>
        <h2>Hébergement</h2>
        <p>
          Le site est hébergé par <A>[Hostinger : raison sociale et adresse exactes, disponibles dans votre espace client]</A>.
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
  return (
    <Page titre="Conditions générales d’utilisation" maj="11 novembre 2026">
      <section>
        <h2>1. Objet</h2>
        <p>
          Les présentes conditions encadrent l’utilisation de Lexia, service en ligne d’aide à l’étude du droit
          français édité par <A>[éditeur]</A>. La création d’un compte vaut acceptation de ces conditions.
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
          jour à minuit (heure de Paris). <A>[Conditions de paiement, de durée, de résiliation et droit de
          rétractation : à compléter avant l’ouverture des formules payantes.]</A>
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
        <p>Les présentes conditions sont soumises au droit français. <A>[Juridiction compétente et médiation de la consommation, le cas échéant.]</A></p>
      </section>
    </Page>
  )
}

export function Confidentialite() {
  return (
    <Page titre="Politique de confidentialité" maj="11 novembre 2026">
      <section>
        <h2>Responsable du traitement</h2>
        <p><A>[Éditeur, adresse et contact]</A></p>
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
          l’API Gemini de Google. <A>[Préciser le niveau de service utilisé et ses conditions de traitement des
          données : avec le niveau gratuit, Google indique pouvoir utiliser ces données pour améliorer ses produits.]</A>
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
          <li>Journaux techniques : <A>[durée, par exemple 12 mois]</A>.</li>
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
          portabilité. Vous pouvez supprimer votre compte vous-même depuis « Mon compte », ou écrire à
          <A>[adresse e-mail de contact]</A>. Vous pouvez aussi saisir la CNIL (www.cnil.fr).
        </p>
      </section>
    </Page>
  )
}
