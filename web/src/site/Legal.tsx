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
          Téléphone : <V v={l?.telephone} manque="Numéro de téléphone" /><br />
          Contact : <Contact adresse={contact} /><br />
          Directeur de la publication : <V v={l?.directeur} manque="Nom" />
        </p>
      </section>
      <section>
        <h2>Hébergement</h2>
        <p>
          Le site est hébergé par HOSTINGER INTERNATIONAL LIMITED, société privée à responsabilité limitée de droit
          chypriote, dont le siège social est situé au 61 Lordou Vironos str., 6023 Larnaca, Chypre.
          Téléphone : <V v={l?.hebergeur_telephone} manque="Numéro de téléphone de l’hébergeur" />.
        </p>
      </section>
      <section>
        <h2>Sources juridiques</h2>
        <p>
          Les textes et décisions affichés proviennent des données ouvertes publiées par la Direction de l’information
          légale et administrative (DILA : bases LEGI, CONSTIT, CASS et JADE), réutilisées selon la Licence Ouverte /
          Open Licence d’Etalab, et du site du Conseil constitutionnel pour la Constitution. Chaque source est
          accompagnée de sa date de mise à jour et d’un lien vers sa version officielle. Seule la publication sur
          Légifrance fait foi.
        </p>
        <p>
          Les décisions de justice sont diffusées sous la forme pseudonymisée publiée par la DILA ; toute tentative de
          réidentification des personnes est interdite.
        </p>
      </section>
      <section>
        <h2>Intelligence artificielle</h2>
        <p>
          Les réponses, fiches et questionnaires de Lexia sont générés par une intelligence artificielle (modèles Gemini
          de Google{l?.groq ? <>, ou en secours un modèle ouvert exécuté par Groq</> : null}), à partir des sources citées. Ils peuvent comporter des erreurs et ne constituent pas un avis
          juridique ni une consultation juridique.
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
          <li>Lexia fournit des explications, fiches et questionnaires générés par une intelligence artificielle à partir de sources juridiques officielles.</li>
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
          <strong>Souscription.</strong> Aucun paiement n’est encaissé sur le site. Une formule payante se demande par
          e-mail (<Contact adresse={contact} />). Avant toute souscription, l’éditeur confirme par écrit la formule,
          son prix toutes taxes comprises ({l?.tva ? l.tva : <V manque="Mention TVA" />}), sa durée et le mode de
          paiement. Le contrat est conclu à la réception du paiement ; la formule est alors activée pour la durée
          achetée, indiquée sur la page « Mon compte ».
        </p>
        <p>
          <strong>Durée, sans reconduction.</strong> Une formule payante dure le nombre de mois acheté et n’est jamais
          renouvelée automatiquement : à son échéance, le compte repasse en formule gratuite, sans démarche ni frais.
        </p>
        <p>
          <strong>Droit de rétractation.</strong> Vous disposez de quatorze jours à compter de la souscription pour
          vous rétracter, sans motif, par simple e-mail à <Contact adresse={contact} /> (article L. 221-18 du Code de
          la consommation). Si vous demandez expressément que la formule soit activée avant la fin de ce délai, vous
          payez, en cas de rétractation, un montant proportionnel à la période déjà écoulée (article L. 221-25).
          Le remboursement intervient dans les quatorze jours suivant votre demande, par le moyen de paiement utilisé.
        </p>
      </section>
      <section>
        <h2>5. Cours déposés</h2>
        <p>
          Vous pouvez déposer vos propres cours (PDF, Word, texte) pour réviser avec Lexia. Vous garantissez avoir le
          droit de les utiliser : un cours reçu de votre enseignant ou de votre faculté reste son œuvre, et vous ne le
          déposez que pour votre usage personnel d’étude. Lexia n’acquiert aucun droit sur vos cours, ne les montre
          à personne d’autre et ne les partage pas. Vous pouvez les retirer à tout moment ; ils sont aussi supprimés
          avec votre compte. Le nombre de cours conservés dépend de votre formule (page Tarifs).
        </p>
      </section>
      <section>
        <h2>6. Usage acceptable</h2>
        <p>
          Sont interdits : l’utilisation automatisée massive, le contournement des limites, la revente du service, la
          réidentification des personnes citées dans les décisions de justice et toute utilisation contraire à la loi. L’éditeur peut suspendre un compte en cas de manquement.
        </p>
      </section>
      <section>
        <h2>7. Disponibilité et responsabilité</h2>
        <p>
          Le service est fourni en l’état, sans garantie de disponibilité continue. Il dépend de prestataires tiers,
          notamment le modèle de langage utilisé pour rédiger les réponses. La responsabilité de l’éditeur ne saurait
          être engagée du fait d’une décision prise sur la base d’une réponse du service.
        </p>
      </section>
      <section>
        <h2>8. Droit applicable</h2>
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
          <li><strong>Double authentification</strong> (si vous l’activez) : clé secrète partagée avec votre application d’authentification et empreintes des codes de secours, supprimées à la désactivation ou avec le compte.</li>
          <li><strong>Utilisation</strong> : nombre de questions et de questionnaires du jour, pour appliquer les limites de votre formule.</li>
          <li><strong>Cours déposés</strong> : le texte extrait de vos cours (découpé en passages, avec le numéro de page), leur titre, leur matière et le nom du fichier. Le fichier d’origine n’est pas conservé. Vos cours ne sont visibles que par vous.</li>
          <li><strong>Journaux techniques</strong> : identifiants des sources utilisées, durée de traitement, statut des réponses. Le texte de vos questions n’y est pas enregistré.</li>
          <li><strong>Retours</strong> : avis « utile / pas utile » et motif choisi dans une liste.</li>
          <li><strong>Journaux du serveur web</strong> : adresse IP, date, page demandée et navigateur, conservés 14 jours pour la sécurité du service.</li>
          <li><strong>Réponses déjà calculées</strong> : le texte d’une question et sa réponse sont gardés en mémoire vive 24 heures au plus, pour répondre immédiatement à une question identique ; ils ne sont jamais écrits sur disque et ne sont reliés à aucun compte.</li>
        </ul>
        <p>
          L’adresse e-mail et le mot de passe sont nécessaires pour créer un compte ; sans eux, le service ne peut pas
          être fourni. Vos fiches enregistrées et le semestre choisi restent dans votre navigateur (stockage local) et
          ne sont pas envoyés au serveur.
        </p>
      </section>
      <section>
        <h2>Traitement de vos questions</h2>
        <p>
          Pour produire une réponse, le texte de votre question et les extraits retrouvés (textes officiels et, si vous
          le choisissez, passages de votre cours) sont transmis à
          l’API Gemini de Google, qui peut les traiter hors de l’Union européenne.{' '}
          {l?.gemini_payant ? (
            <>Lexia utilise le niveau payant : selon les conditions de ce niveau, Google n’utilise ni les questions ni
            les réponses pour améliorer ses produits ; il les conserve pendant une durée limitée, uniquement pour
            détecter les abus, assurer la sécurité du service et respecter ses obligations légales.</>
          ) : (
            <>
              Lexia utilise actuellement le niveau gratuit : selon ses conditions, Google peut utiliser les questions
              et les réponses pour améliorer ses produits, et des relecteurs humains peuvent les lire.{' '}
              <A>[Les conditions de Google n’autorisent que le niveau payant pour un service proposé à des
              utilisateurs de l’Espace économique européen : à régulariser avant toute ouverture.]</A>
            </>
          )}{' '}
          {l?.groq && (
            <>
              {l?.courriel ? <>{' '}Votre adresse e-mail est transmise à Resend (États-Unis) pour l’unique envoi
              du message de confirmation d’adresse ; ni votre mot de passe ni vos questions ne lui sont communiqués.</> : null}              {' '}Lorsque Gemini est indisponible, la question et quelques extraits sont transmis à Groq (États-Unis), qui
              exécute un modèle ouvert ; selon ses conditions, Groq ne conserve pas ces données par défaut, sauf journaux
              de sécurité limités à 30 jours.
            </>
          )}{' '}
          N’indiquez pas d’informations personnelles dans vos questions.
        </p>
      </section>
      <section>
        <h2>Destinataires</h2>
        <p>
          Les données ne sont ni vendues ni cédées. Elles sont traitées par l’éditeur et par ses sous-traitants :
          Hostinger (hébergement du site et des données de compte), Google (rédaction des réponses, voir
          ci-dessus){l?.groq ? <>, Groq (rédaction des réponses en secours)</> : null}
          {l?.courriel ? <> et Resend (envoi de l’e-mail de confirmation d’adresse)</> : null}.
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
          <li>Cours déposés : jusqu’à ce que vous les retiriez, ou jusqu’à la suppression du compte ; les sauvegardes (14 jours) peuvent en garder une copie jusqu’à leur effacement.</li>
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
          portabilité, ainsi que le droit de définir des directives sur le sort de vos données après votre décès
          (article 85 de la loi du 6 janvier 1978). Vous pouvez supprimer votre compte vous-même depuis « Mon
          compte », ou écrire à <Contact adresse={contact} />. Vous pouvez aussi saisir la CNIL (www.cnil.fr).
        </p>
      </section>
    </Page>
  )
}
