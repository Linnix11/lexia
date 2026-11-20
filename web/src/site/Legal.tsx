// Pages legales. Les informations sur l'editeur viennent du .env du serveur (LEGAL_*, CONTACT_EMAIL) :
// tant qu'une valeur manque, un encart « a completer » s'affiche. A faire relire par un juriste.
import type { ReactNode } from 'react'
import { VERSION_CGU } from '../lib/cgu'
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
  return { l: config?.legal, contact: config?.contact_email ?? null, paiement: !!config?.paiement }
}

/** Lien de signalement d'un contenu illicite (DSA, art. 16) : e-mail pre-rempli avec les quatre elements
 *  demandes par l'article 16, paragraphe 2. */
function Signalement({ adresse }: { adresse: string | null }) {
  if (!adresse) return <V manque="Adresse e-mail de contact" />
  const corps = [
    'Contenu signalé (titre du cours, adresse de la page, ou tout élément permettant de le retrouver) :',
    '',
    'Raisons pour lesquelles ce contenu est illicite :',
    '',
    'Nom et prénom :',
    '',
    'Je déclare de bonne foi que les informations et allégations de ce signalement sont exactes et complètes.',
  ].join('\n')
  const href = `mailto:${adresse}?subject=${encodeURIComponent('Signalement de contenu illicite')}&body=${encodeURIComponent(corps)}`
  return <a href={href} className="underline">signaler un contenu illicite</a>
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
        <p>
          Les réponses, questionnaires et corrections envoyés par l’API de Lexia portent un marquage lisible par
          machine (en-tête HTTP « X-AI-Generated: true ») qui indique qu’ils sont générés par une intelligence
          artificielle (article 50, paragraphe 2, du règlement (UE) 2024/1689).
        </p>
      </section>
    </Page>
  )
}

export function Cgu() {
  const { l, contact, paiement } = useLegal()
  return (
    <Page titre="Conditions générales d’utilisation et de vente" maj={VERSION_CGU}>
      <section aria-label="En bref" className="rounded-[8px] border border-line px-4 py-3">
        <p className="font-semibold">En bref</p>
        <ul>
          <li>Lexia vous aide à étudier le droit avec une intelligence artificielle qui peut se tromper : vérifiez toujours les sources citées.</li>
          <li>Il faut avoir 15 ans ou plus pour créer un compte. Avant 18 ans, demandez l’accord d’un parent pour payer une formule.</li>
          <li>Une formule payante dure le nombre de mois acheté, sans renouvellement automatique.</li>
          <li>Vous pouvez changer d’avis pendant 14 jours après l’achat, depuis « Mon compte » ou par e-mail : vous êtes remboursé, moins la part déjà utilisée si l’accès a commencé (article 4).</li>
          <li>Vos cours déposés ne sont visibles que par vous. Ne déposez que des documents que vous avez le droit d’utiliser.</li>
          <li>Si nous devons limiter ou fermer votre compte, nous vous disons pourquoi et vous pouvez contester (article 6).</li>
        </ul>
      </section>
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
        <p>
          La création d’un compte est réservée aux personnes âgées de 15 ans ou plus, qui le déclarent à
          l’inscription. Si vous avez moins de 18 ans, la souscription d’une formule payante suppose l’accord
          d’un titulaire de l’autorité parentale (article 1148 du Code civil).
        </p>
      </section>
      <section>
        <h2>4. Formules et limites</h2>
        <p>
          Le service est proposé en formule gratuite et en formules payantes, chacune avec un nombre maximal de
          questions et de questionnaires par jour, indiqué sur la page Tarifs. Les compteurs sont remis à zéro chaque
          jour à minuit (heure de Paris).
        </p>
        {paiement ? (
          <>
            <p>
              <strong>Souscription.</strong> Depuis la page Tarifs, vous choisissez la formule et le nombre de mois ;
              le prix total toutes taxes comprises ({l?.tva ? l.tva : <V manque="Mention TVA" />}) est affiché avant le
              paiement. Le paiement se fait en une fois, par carte, sur la page sécurisée de notre prestataire Stripe :
              l’éditeur ne voit ni ne conserve vos coordonnées bancaires. Le contrat est conclu à la confirmation du
              paiement ; la formule est alors activée pour la durée achetée, indiquée sur la page « Mon compte ». Vous
              recevez ensuite par e-mail la confirmation du contrat : formule, durée, prix, date de fin, version des
              présentes conditions acceptée, date de votre demande d’accès immédiat, date limite de rétractation et
              modèle de formulaire de rétractation (article L. 221-13 du Code de la consommation).
            </p>
            <p>
              Un paiement reçu alors qu’une autre formule est déjà en cours sur votre compte, ou après la suppression
              du compte, n’active aucune formule : il vous est remboursé intégralement et un e-mail vous en informe.
              Si un paiement est remboursé en totalité ou contesté auprès de votre banque, la formule achetée est
              retirée.
            </p>
          </>
        ) : (
          <p>
            <strong>Souscription.</strong> Aucun paiement n’est encaissé sur le site. Une formule payante se demande par
            e-mail (<Contact adresse={contact} />). Avant toute souscription, l’éditeur confirme par écrit la formule,
            son prix toutes taxes comprises ({l?.tva ? l.tva : <V manque="Mention TVA" />}), sa durée et le mode de
            paiement. Le contrat est conclu à la réception du paiement ; la formule est alors activée pour la durée
            achetée, indiquée sur la page « Mon compte ».
          </p>
        )}
        <p>
          <strong>Durée, sans reconduction.</strong> Une formule payante dure le nombre de mois acheté et n’est jamais
          renouvelée automatiquement : à son échéance, le compte repasse en formule gratuite, sans démarche ni frais.
        </p>
        <p>
          <strong>Droit de rétractation.</strong> Vous avez le droit de vous rétracter du contrat sans donner de
          motif dans un délai de quatorze jours. Le délai de rétractation expire quatorze jours après le jour de la
          conclusion du contrat (articles L. 221-18 et suivants du Code de la consommation).
        </p>
        <p>
          Pour exercer ce droit, vous nous notifiez votre décision de rétractation au moyen d’une déclaration dénuée
          d’ambiguïté, par exemple par lettre envoyée par la poste à <V v={l?.editeur} manque="Éditeur" />,{' '}
          <V v={l?.adresse} manque="Adresse" /> ou par courrier électronique à <Contact adresse={contact} />{' '}
          (téléphone : <V v={l?.telephone} manque="Numéro de téléphone" />). Vous pouvez utiliser le modèle de
          formulaire de rétractation ci-dessous, mais ce n’est pas obligatoire.
        </p>
        {paiement && (
          <p>
            <strong>Rétractation en ligne.</strong> Vous pouvez également exercer votre droit de rétractation en
            ligne, sur la page « Mon compte » du site, avec le bouton « Renoncer au contrat ici », affiché pendant
            tout le délai de rétractation. Vous y indiquez votre nom et votre prénom, vous choisissez le ou les achats
            de moins de quatorze jours dont vous vous rétractez, et vous voyez l’adresse e-mail de votre compte, qui
            recevra l’accusé de réception ; vous validez avec le bouton « Confirmer la rétractation ». La formule
            concernée est retirée aussitôt. Nous vous envoyons alors, dans les meilleurs délais, un accusé de
            réception de la rétractation sur un support durable (un e-mail), avec son contenu ainsi que la date et
            l’heure de sa soumission (articles L. 221-21 et D. 221-5 du Code de la consommation).
          </p>
        )}
        <p>
          Pour que le délai de rétractation soit respecté, il suffit que vous transmettiez votre communication
          relative à l’exercice du droit de rétractation avant l’expiration du délai de rétractation.
        </p>
        <p>
          <strong>Effets de la rétractation.</strong> En cas de rétractation de votre part, nous vous rembourserons
          tous les paiements reçus de vous sans retard excessif et, en tout état de cause, au plus tard quatorze jours
          à compter du jour où nous sommes informés de votre décision. Nous procéderons au remboursement en utilisant
          le même moyen de paiement que celui que vous aurez utilisé pour la transaction initiale, sauf si vous
          convenez expressément d’un moyen différent ; en tout état de cause, ce remboursement n’occasionnera pas de
          frais pour vous (article L. 221-24).
        </p>
        <p>
          Si vous avez demandé de commencer la prestation de services pendant le délai de rétractation, vous devrez
          nous payer un montant proportionnel à ce qui vous a été fourni jusqu’au moment où vous nous avez informé de
          votre rétractation, par rapport à l’ensemble des prestations prévues par le contrat (article L. 221-25).
          Lors de cette demande, vous reconnaissez perdre le droit de rétractation une fois le contrat entièrement
          exécuté (article L. 221-28, 1°) ; une formule durant au moins un mois, elle n’est jamais entièrement
          exécutée avant la fin du délai de quatorze jours.
        </p>
        <div className="rounded-[8px] border border-line px-4 py-3 text-[13px]" aria-label="Modèle de formulaire de rétractation">
          <p className="font-semibold">Modèle de formulaire de rétractation (annexe à l’article R. 221-1 du Code de la consommation)</p>
          <p>(Veuillez compléter et renvoyer le présent formulaire uniquement si vous souhaitez vous rétracter du contrat.)</p>
          <p>
            À l’attention de <V v={l?.editeur} manque="Éditeur" />, <V v={l?.adresse} manque="Adresse" />,{' '}
            <Contact adresse={contact} /> :
          </p>
          <p>
            Je/nous (*) vous notifie/notifions (*) par la présente ma/notre (*) rétractation du contrat portant sur la
            prestation de services ci-dessous :<br />
            Commandé le :<br />
            Nom du (des) consommateur(s) :<br />
            Adresse du (des) consommateur(s) :<br />
            Signature du (des) consommateur(s) (uniquement en cas de notification du présent formulaire sur papier) :<br />
            Date :
          </p>
          <p>(*) Rayez la mention inutile.</p>
        </div>
      </section>
      <section>
        <h2>5. Cours déposés</h2>
        <p>
          Vous pouvez déposer vos propres cours (PDF, même scanné, Word, OpenDocument, PowerPoint, RTF, texte ou photo)
          pour réviser avec Lexia. Les scans et les photos sont lus sur le serveur de Lexia par un logiciel libre de
          reconnaissance de caractères (Tesseract), sans service extérieur ; seul le texte lu est conservé, jamais le
          fichier ni l’image. Vous garantissez avoir le
          droit de les utiliser : un cours reçu de votre enseignant ou de votre faculté reste son œuvre, et vous ne le
          déposez que pour votre usage personnel d’étude. Lexia n’acquiert aucun droit sur vos cours, ne les montre
          à aucun autre utilisateur, ne les publie pas et ne les vend pas. Vous pouvez les retirer à tout moment ;
          ils sont aussi supprimés avec votre compte. Le nombre de cours conservés dépend de votre formule (page
          Tarifs).
        </p>
        <p>
          Quand vous interrogez Lexia sur votre cours, les seuls passages retenus pour la réponse sont transmis,
          avec votre question, au modèle de langage qui rédige la réponse : l’API Gemini de Google
          {l?.groq ? <>, ou Groq en secours</> : null}.{' '}
          {l?.gemini_payant ? (
            <>Au niveau payant utilisé par Lexia, Google n’utilise pas ces passages pour améliorer ses produits.</>
          ) : (
            <>
              Au niveau gratuit actuellement utilisé, Google peut utiliser ces passages pour améliorer ses produits
              et des relecteurs humains peuvent les lire.{' '}
              <A>[Passage au niveau payant de Gemini à faire avant toute ouverture.]</A>
            </>
          )}{' '}
          Le détail figure dans la politique de confidentialité.
        </p>
      </section>
      <section>
        <h2>5 bis. Contenus déposés : modération et signalement</h2>
        <p>
          L’éditeur ne surveille pas les cours déposés et n’utilise aucun outil automatique pour les examiner. Il
          n’en prend connaissance qu’à la suite d’un signalement ou de la demande d’une autorité. Les décisions sont
          prises par une personne, jamais par un algorithme. Les mesures possibles sont le retrait d’un cours, puis,
          en cas de manquements répétés ou graves, la suspension ou la fermeture du compte (article 6).
        </p>
        <p>
          Toute personne peut nous <Signalement adresse={contact} /> présent sur le service, par e-mail à{' '}
          <Contact adresse={contact} />. Le signalement indique : les raisons pour lesquelles le contenu est
          illicite ; l’endroit exact où il se trouve (titre du cours, adresse de la page ou autre élément permettant
          de le retrouver) ; votre nom et votre adresse e-mail ; une déclaration selon laquelle vous pensez, de bonne
          foi, que les informations et allégations qu’il contient sont exactes et complètes. Nous accusons réception
          du signalement, puis vous informons de notre décision et des voies de recours (article 16 du règlement
          (UE) 2022/2065 sur les services numériques).
        </p>
        <p>
          <strong>Point de contact.</strong> Pour les utilisateurs comme pour les autorités des États membres, la
          Commission européenne et le comité européen des services numériques, le point de contact unique de Lexia
          est l’adresse <Contact adresse={contact} />, en français ou en anglais (articles 11 et 12 du même
          règlement). Une personne répond à chaque message.
        </p>
      </section>
      <section>
        <h2>6. Usage acceptable et suspension</h2>
        <p>
          Sont interdits : l’utilisation automatisée massive, le contournement des limites, la revente du service, la
          réidentification des personnes citées dans les décisions de justice, le dépôt d’un contenu illicite et
          toute utilisation contraire à la loi.
        </p>
        <p>
          En cas de manquement, l’éditeur vous écrit d’abord à l’adresse de votre compte : il indique le manquement
          reproché et la clause des présentes conditions concernée, et vous laisse huit jours pour répondre ou y
          mettre fin. Il ne peut agir sans ce délai qu’en cas d’urgence : atteinte à la sécurité du service, contenu
          manifestement illicite ou demande d’une autorité.
        </p>
        <p>
          Toute mesure (retrait d’un cours, suspension ou fermeture du compte) vous est notifiée par e-mail, au plus
          tard au moment où elle est prise, avec un exposé des motifs : la mesure et sa durée ; les faits sur
          lesquels elle repose et, le cas échéant, le fait qu’elle fait suite à un signalement ; le texte de loi ou
          la clause des présentes conditions en cause ; vos voies de recours (article 17 du règlement (UE)
          2022/2065). Vous pouvez la contester en répondant à cet e-mail : une personne réexamine la décision. Vous
          pouvez aussi saisir le médiateur de la consommation (article 8) ou le juge.
        </p>
        <p>
          Si votre compte est fermé alors qu’une formule payante est en cours, la part du prix correspondant à la
          période non utilisée vous est remboursée. Une suspension qui se révèle injustifiée prolonge votre formule
          d’autant.
        </p>
      </section>
      <section>
        <h2>7. Conformité, disponibilité et responsabilité</h2>
        <p>
          <strong>Garantie légale de conformité.</strong> L’éditeur fournit un service conforme au contrat et à la
          description de l’article 2 (articles L. 224-25-12 et suivants du Code de la consommation). Pendant toute la
          durée d’une formule, il répond des défauts de conformité qui apparaissent. En cas de défaut, vous avez droit
          à la mise en conformité du service, sans frais ; à défaut, à une réduction du prix ou à la résolution du
          contrat, avec remboursement dans les quatorze jours (articles L. 224-25-17 à L. 224-25-23). Signalez le
          défaut à <Contact adresse={contact} />. Ces droits s’appliquent aussi à la formule gratuite, sauf la
          réduction du prix.
        </p>
        <p>
          <strong>Disponibilité.</strong> L’éditeur s’efforce de garder le service accessible en continu. Il
          dépend de prestataires tiers, notamment du modèle de langage qui rédige les réponses : des interruptions
          (maintenance, panne d’un prestataire) peuvent survenir. Une interruption qui empêche durablement
          d’utiliser une formule payante est traitée comme un défaut de conformité.
        </p>
        <p>
          <strong>Usage des réponses.</strong> Les réponses sont une aide à l’étude, générée par une intelligence
          artificielle qui peut se tromper (article 2). Ne prenez pas de décision personnelle (procès, contrat,
          démarche) sur la seule base d’une réponse : consultez un professionnel du droit.
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
  const { l, contact, paiement } = useLegal()
  return (
    <Page titre="Politique de confidentialité" maj="18 novembre 2026">
      <section>
        <h2>Responsable du traitement</h2>
        <p>
          <V v={l?.editeur} manque="Éditeur" />, <V v={l?.adresse} manque="Adresse" />. Contact : <Contact adresse={contact} />
        </p>
      </section>
      <section>
        <h2>Données collectées</h2>
        <ul>
          <li><strong>Compte</strong> : adresse e-mail, empreinte chiffrée du mot de passe (le mot de passe lui-même n’est jamais conservé), formule, date de création, date de la dernière visite (pour supprimer les comptes inutilisés).</li>
          <li><strong>Prénom et nom</strong> : demandés à l’inscription. Le prénom sert à vous saluer dans votre espace ; le nom identifie le titulaire du compte (il pré-remplit par exemple la déclaration de rétractation). Ils ne sont jamais transmis à l’intelligence artificielle, ni à un autre service, ni utilisés dans les e-mails. Vous pouvez les corriger à tout moment dans « Mon compte ».</li>
          <li><strong>Double authentification</strong> (si vous l’activez) : clé secrète partagée avec votre application d’authentification et empreintes des codes de secours, supprimées à la désactivation ou avec le compte.</li>
          <li><strong>Utilisation</strong> : nombre de questions et de questionnaires du jour, pour appliquer les limites de votre formule.</li>
          <li><strong>Formule payante</strong> (si vous en souscrivez une) : formule choisie, date de fin, et éléments de facturation (adresse e-mail, montant, date et moyen de paiement).</li>
          <li><strong>Cours déposés</strong> : le texte extrait de vos cours (découpé en passages, avec le numéro de page), leur titre, leur matière et le nom du fichier. Le fichier d’origine n’est pas conservé. Vos cours ne sont visibles que par vous.</li>
          <li><strong>Journaux techniques</strong> : identifiants des sources utilisées, durée de traitement, statut des réponses. Le texte de vos questions n’y est pas enregistré.</li>
          <li><strong>Retours</strong> : avis « utile / pas utile » et motif choisi dans une liste.</li>
          <li><strong>Journaux du serveur web</strong> : adresse IP, date, page demandée et navigateur, conservés 14 jours pour la sécurité du service.</li>
          <li><strong>Réponses déjà calculées</strong> : le texte d’une question et sa réponse sont gardés en mémoire vive 24 heures au plus, pour répondre immédiatement à une question identique ; ils ne sont jamais écrits sur disque et ne sont reliés à aucun compte.</li>
        </ul>
        <p>
          L’adresse e-mail et le mot de passe sont nécessaires pour créer un compte ; sans eux, le service ne peut pas
          être fourni.
        </p>
        <p>
          Certaines données restent dans votre navigateur et ne sont pas envoyées au serveur : vos fiches
          enregistrées, vos cartes à réviser avec leur date de prochaine révision, le semestre et la dernière matière choisis (stockage local, jusqu’à ce que vous les
          supprimiez) ; la conversation
          en cours (30 derniers messages) et le dernier questionnaire avec sa correction (stockage de session,
          effacé à la fermeture de l’onglet, à la déconnexion et à la suppression du compte), pour ne pas les perdre
          en changeant de page. Sur un ordinateur partagé, déconnectez-vous à la fin de votre séance.
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
              {' '}Lorsque Gemini est indisponible, la question et quelques extraits sont transmis à Groq (États-Unis), qui
              exécute un modèle ouvert ; l’option de non-conservation des données (« Zero Data Retention ») est activée
              dans notre compte Groq : la question n’est pas conservée après la réponse.
            </>
          )}
          {l?.courriel ? <>{' '}Votre adresse e-mail est transmise à Resend (États-Unis) pour l’envoi des messages de
          confirmation d’adresse et de réinitialisation du mot de passe ; ni votre mot de passe, ni vos prénom et nom,
          ni vos questions ne lui sont communiqués.</> : null}{' '}
          Vos prénom et nom ne font jamais partie de ce qui est transmis.{' '}
          N’indiquez pas d’informations personnelles dans vos questions.
        </p>
        <p>
          Ces transferts hors de l’Union européenne reposent sur le cadre de protection des données UE-États-Unis
          (décision d’adéquation de la Commission européenne du 10 juillet 2023), auquel Google
          {l?.courriel ? <>, Resend</> : null} et Cloudflare sont certifiés.
          {l?.groq ? (
            <>{' '}Groq n’y est pas certifié :{' '}
            <A>[garantie du transfert (clauses contractuelles types de la Commission européenne) à vérifier dans
            l’accord de traitement des données de Groq]</A></>
          ) : null}
        </p>
      </section>
      <section>
        <h2>Destinataires</h2>
        <p>
          Les données ne sont ni vendues ni cédées. Elles sont traitées par l’éditeur et par ses sous-traitants :
          Hostinger (hébergement du site et des données de compte), Cloudflare (acheminement et protection du trafic
          entre votre navigateur et le serveur), Google (rédaction des réponses, voir
          ci-dessus){l?.groq ? <>, Groq (rédaction des réponses en secours)</> : null}
          {l?.courriel ? <>, Resend (envoi des e-mails de confirmation d’adresse et de réinitialisation du mot de passe)</> : null}.
        </p>
        {paiement && (
          <p>
            Si vous payez une formule en ligne, les données saisies sur la page de paiement (carte, nom, adresse
            e-mail) sont traitées par Stripe Payments Europe, Limited (Irlande), qui exécute le paiement. Stripe agit
            aussi comme responsable de traitement pour ses propres obligations (lutte contre la fraude, réglementation
            des paiements) ; Stripe, LLC (États-Unis), à qui ces données peuvent être transférées, est certifiée au
            cadre de protection des données UE-États-Unis. L’éditeur ne reçoit que le résultat du paiement, son montant
            et votre adresse e-mail.
          </p>
        )}
      </section>
      <section>
        <h2>Finalités et base légale</h2>
        <ul>
          <li>Fournir le service : compte, réponses, cours déposés, questionnaires, e-mails de confirmation et de réinitialisation (exécution du contrat).</li>
          <li>Appliquer les limites des formules et gérer les formules payantes (exécution du contrat).</li>
          <li>Identifier le titulaire du compte par ses prénom et nom, et le saluer par son prénom dans son espace (exécution du contrat).</li>
          <li>Tenir la comptabilité des formules payantes (obligation légale).</li>
          <li>Assurer la sécurité du service : journaux du serveur web, limites contre les abus, empreinte gardée après une suppression de compte (intérêt légitime).</li>
          <li>Suivre la qualité et le coût du service : journaux techniques sans le texte des questions, avis « utile / pas utile » (intérêt légitime).</li>
        </ul>
      </section>
      <section>
        <h2>Durées de conservation</h2>
        <ul>
          <li>Compte : jusqu’à sa suppression par vous, ou après deux ans sans aucune visite ; un e-mail vous prévient un mois avant et une simple connexion garde le compte. Un compte avec une formule payante en cours n’est jamais supprimé pour ce motif.</li>
          <li>Prénom et nom : comme le compte, effacés avec lui.</li>
          <li>Compteurs de questions et de questionnaires : 90 jours.</li>
          <li>Cours déposés : jusqu’à ce que vous les retiriez, ou jusqu’à la suppression du compte ; les sauvegardes peuvent en garder une copie jusqu’à leur effacement (voir ci-dessous).</li>
          <li>Session de connexion : 30 jours au plus.</li>
          <li>Journaux techniques : 12 mois, puis suppression automatique.</li>
          <li>Journaux du serveur web : 14 jours.</li>
          <li>Après une suppression de compte depuis le site : une empreinte de l’adresse e-mail (pas l’adresse elle-même), 48 heures au plus.</li>
          <li>Sauvegardes de la base des comptes : 14 jours glissants sur le serveur ; une copie de secours, conservée par l’éditeur hors du serveur, 60 jours glissants.</li>
          <li>Formules payantes : pièces comptables (paiements, justificatifs) pendant 10 ans, durée imposée par les obligations comptables ; elles sont gardées même après la suppression du compte.</li>
          <li>Échanges par e-mail avec l’éditeur (demandes, réclamations, exercice de vos droits) : 3 ans après le dernier échange.</li>
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
