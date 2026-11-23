// Guides publics de methode et fiches (D116). Chaque regle enoncee renvoie a un article cite, dont le texte, le
// lien officiel et la version sont lus dans l'index de recherche (citations.json). Les conseils de methode sont
// ceux enseignes en licence ; ils peuvent varier d'un enseignant a l'autre, ce que les guides signalent.
import { GUIDES_LISTE, type GuideListe } from './guidesListe'

export type Bloc =
  | { p: string }
  | { liste: string[]; ordonnee?: boolean }
  | { citation: string; alineas?: number[] }

interface CorpsGuide {
  /** Reponse directe, en tete de page : ce que les moteurs de reponse citent en premier. */
  enBref: string
  sections: { titre: string; blocs: Bloc[] }[]
  faq: { question: string; reponse: string }[]
}

const CORPS: Record<string, CorpsGuide> = {
  'methode-cas-pratique-droit-des-contrats': {
    enBref: 'Un cas pratique se résout en cinq temps : qualifier les faits, poser le problème de droit, énoncer la règle avec son article (la majeure), l’appliquer aux faits (la mineure), puis conclure. En droit des contrats, les questions portent le plus souvent sur la formation du contrat (consentement, capacité, contenu, article 1128 du Code civil) et sur les sanctions de l’inexécution (article 1217).',
    sections: [
      {
        titre: '1. Lire les faits et les qualifier',
        blocs: [
          { p: 'Relisez l’énoncé en notant les personnes, les dates et les actes. Qualifier, c’est faire entrer chaque fait dans une catégorie juridique : y a-t-il un contrat, et lequel (vente, bail, prestation de service) ? Le point de départ est la définition légale du contrat.' },
          { citation: 'code_civil:1101' },
          { p: 'Une même situation peut poser plusieurs questions : une négociation rompue, un consentement surpris, une prestation mal exécutée. Traitez-les une par une, dans l’ordre chronologique.' },
        ],
      },
      {
        titre: '2. Poser le problème de droit',
        blocs: [
          { p: 'Le problème de droit est une question abstraite, détachée des noms des parties. Par exemple : « Un contrat conclu à la suite d’un mensonge sur une qualité essentielle de la chose peut-il être annulé ? ». Une bonne question annonce déjà la règle que vous allez chercher.' },
        ],
      },
      {
        titre: '3. La majeure : énoncer la règle et son fondement',
        blocs: [
          { p: 'Citez l’article qui pose la règle, puis ses conditions. Pour la validité du contrat, l’article 1128 en pose trois.' },
          { citation: 'code_civil:1128' },
          { p: 'Si le consentement est en cause, vérifiez les vices du consentement : l’erreur, le dol et la violence ne l’affectent que s’ils ont été déterminants.' },
          { citation: 'code_civil:1130' },
          { citation: 'code_civil:1132' },
          { citation: 'code_civil:1137' },
          { citation: 'code_civil:1140' },
          { p: 'Pensez aussi au devoir d’information, qui ne porte pas sur l’estimation de la valeur de la prestation, et à la liberté des négociations, encadrée par la bonne foi.' },
          { citation: 'code_civil:1112-1', alineas: [0, 1, 2] },
          { citation: 'code_civil:1112', alineas: [0] },
          { citation: 'code_civil:1104' },
        ],
      },
      {
        titre: '4. La mineure : appliquer la règle aux faits',
        blocs: [
          { p: 'Reprenez chaque condition de la majeure et confrontez-la aux faits de l’énoncé : la condition est-elle remplie, pourquoi ? Si un fait manque, dites-le et envisagez les deux hypothèses. N’oubliez pas la charge de la preuve.' },
          { citation: 'code_civil:1353' },
        ],
      },
      {
        titre: '5. Conclure, puis envisager les sanctions',
        blocs: [
          { p: 'Répondez clairement au problème posé. Si le contrat n’est pas valable, la sanction est la nullité, qui efface le contrat et oblige aux restitutions.' },
          { citation: 'code_civil:1178' },
          { p: 'Si le contrat est valable mais mal exécuté, l’article 1217 offre plusieurs sanctions, cumulables lorsqu’elles ne sont pas incompatibles. Le contrat légalement formé s’impose aux parties.' },
          { citation: 'code_civil:1103' },
          { citation: 'code_civil:1217' },
          { citation: 'code_civil:1219' },
          { citation: 'code_civil:1231-1' },
        ],
      },
      {
        titre: 'Exemple rédigé',
        blocs: [
          { p: 'Faits : Alice achète à Bruno une voiture d’occasion que Bruno lui présente comme n’ayant jamais été accidentée. Alice apprend ensuite que Bruno savait que le véhicule avait subi un grave accident. Peut-elle remettre en cause la vente ?' },
          { p: 'Problème de droit : un mensonge du vendeur sur l’état du bien vendu permet-il d’obtenir l’annulation de la vente ?' },
          { p: 'Majeure : le dol est le fait pour un contractant d’obtenir le consentement de l’autre par des manœuvres ou des mensonges (article 1137 du Code civil). Il vicie le consentement lorsque, sans lui, la victime n’aurait pas contracté ou aurait contracté à des conditions substantiellement différentes (article 1130). Le contrat est alors nul et la victime peut aussi demander réparation (article 1178).' },
          { p: 'Mineure : Bruno a affirmé que la voiture n’avait jamais été accidentée alors qu’il savait le contraire : c’est un mensonge. Il reste à établir qu’il a été déterminant : un acheteur qui sait qu’un véhicule a subi un grave accident n’achète pas, ou pas au même prix. Alice devra le prouver.' },
          { p: 'Conclusion : Alice peut demander au juge l’annulation de la vente pour dol, avec restitution du prix contre restitution du véhicule, et réparation de son préjudice.' },
        ],
      },
      {
        titre: 'Erreurs fréquentes',
        blocs: [
          {
            liste: [
              'Citer les anciens numéros du Code civil : l’ancien article 1134 correspond aujourd’hui aux articles 1103, 1104 et 1193, l’ancien 1116 aux articles 1137 et 1139.',
              'Réciter le cours sans l’appliquer aux faits : la mineure compte autant que la majeure.',
              'Oublier de conclure sur chaque question.',
              'Ne pas vérifier que l’article cité est en vigueur à la date des faits.',
            ],
          },
        ],
      },
    ],
    faq: [
      { question: 'Quelle différence entre la majeure et la mineure ?', reponse: 'La majeure énonce la règle de droit et son fondement (un article, une jurisprudence). La mineure applique cette règle aux faits de l’énoncé, condition par condition.' },
      { question: 'Faut-il citer de la jurisprudence dans un cas pratique ?', reponse: 'Oui lorsqu’elle précise ou complète la règle légale, mais le texte vient d’abord. Indiquez la juridiction et la date de la décision.' },
      { question: 'Lexia peut-il m’aider à préparer un cas pratique ?', reponse: 'Oui : le mode Cas pratique de Lexia présente la qualification des faits, le problème de droit, la majeure, la mineure et la conclusion, avec les articles cités et le texte officiel à un clic. Il sert à vérifier votre raisonnement, pas à remplacer votre copie.' },
    ],
  },
  'methode-commentaire-arret': {
    enBref: 'Commenter un arrêt, c’est expliquer le sens de la décision, apprécier sa valeur et mesurer sa portée. Le travail commence par la fiche d’arrêt (faits, procédure, prétentions, problème de droit, solution) et se termine par un plan en deux parties tiré de la décision elle-même. Pour un arrêt de la Cour de cassation, gardez en tête qu’elle juge le droit, pas les faits.',
    sections: [
      {
        titre: '1. Savoir ce que juge la Cour de cassation',
        blocs: [
          { p: 'La Cour de cassation ne rejuge pas l’affaire : elle vérifie que la décision attaquée a correctement appliqué le droit. C’est ce qui donne son intérêt au commentaire : l’arrêt tranche une question de droit.' },
          { citation: 'code_organisation_judiciaire:L411-1' },
          { citation: 'code_organisation_judiciaire:L411-2' },
          { citation: 'code_procedure_civile:604' },
          { p: 'Le dispositif dit si la Cour rejette le pourvoi ou casse la décision. Elle peut casser sans renvoyer l’affaire à une autre juridiction.' },
          { citation: 'code_organisation_judiciaire:L411-3', alineas: [0, 1] },
        ],
      },
      {
        titre: '2. Lire l’arrêt dans l’ordre',
        blocs: [
          { p: 'Repérez ses parties : le visa (« Vu l’article… ») dans les arrêts de cassation, l’exposé des faits et de la procédure, les moyens du pourvoi, la réponse de la Cour (les motifs) et le dispositif. Comme tout jugement, l’arrêt expose les prétentions des parties, est motivé et se termine par un dispositif.' },
          { citation: 'code_procedure_civile:455', alineas: [0, 2] },
        ],
      },
      {
        titre: '3. Rédiger la fiche d’arrêt',
        blocs: [
          {
            ordonnee: true,
            liste: [
              'Les faits, qualifiés juridiquement et sans détail inutile.',
              'La procédure : qui a agi, devant quelles juridictions, avec quelles décisions.',
              'Les prétentions et arguments des parties devant la Cour.',
              'Le problème de droit, sous forme de question abstraite.',
              'La solution : rejet ou cassation, et la règle que la Cour affirme.',
            ],
          },
        ],
      },
      {
        titre: '4. Le sens, la valeur et la portée',
        blocs: [
          {
            liste: [
              'Le sens : que dit exactement la Cour ? Expliquez chaque terme de la solution.',
              'La valeur : la solution est-elle conforme au texte, cohérente avec les décisions antérieures, opportune ? Appuyez-vous sur le texte applicable et sur votre cours.',
              'La portée : s’agit-il d’un arrêt de principe ou d’espèce ? Quelles conséquences pour la suite ? La règle a-t-elle été confirmée ou modifiée depuis, par exemple par une réforme du texte ?',
            ],
          },
        ],
      },
      {
        titre: '5. Construire le plan et l’introduction',
        blocs: [
          { p: 'Le plan suit le raisonnement de l’arrêt, en deux parties et deux sous-parties, avec des titres qui parlent de la décision et non de la méthode. Évitez le plan « I. Les faits, II. La solution ». Les attentes précises varient selon les enseignants : suivez celles de votre équipe pédagogique.' },
          { p: 'L’introduction comprend une accroche, la fiche d’arrêt rédigée, l’intérêt de la décision et l’annonce du plan.' },
        ],
      },
    ],
    faq: [
      { question: 'Comment reconnaître un arrêt de rejet et un arrêt de cassation ?', reponse: 'Par le dispositif : « rejette le pourvoi » pour un arrêt de rejet, « casse et annule » pour un arrêt de cassation. Un arrêt de cassation commence en général par un visa du texte appliqué.' },
      { question: 'Le commentaire d’arrêt est-il une dissertation sur le thème de l’arrêt ?', reponse: 'Non. Le cours sert à éclairer la décision ; chaque développement doit partir de l’arrêt et y revenir.' },
      { question: 'Lexia peut-il m’aider pour un commentaire d’arrêt ?', reponse: 'Oui : le mode Commentaire d’arrêt de Lexia propose une fiche d’arrêt, le sens, la valeur et la portée, une problématique et un plan, avec les textes cités. Indiquez la juridiction, la date et le numéro de l’arrêt.' },
    ],
  },
  'fiche-responsabilite-civile-pour-faute': {
    enBref: 'Celui qui cause un dommage à autrui par sa faute doit le réparer (article 1240 du Code civil). Trois conditions sont exigées : une faute, un dommage et un lien de causalité entre les deux. Une simple négligence ou imprudence suffit (article 1241). Ces articles portaient les numéros 1382 et 1383 avant la réforme de 2016.',
    sections: [
      {
        titre: 'Le principe',
        blocs: [
          { citation: 'code_civil:1240' },
          { citation: 'code_civil:1241' },
          { p: 'Il s’agit de responsabilité extracontractuelle : elle joue entre personnes qui ne sont pas liées par un contrat, ou pour un dommage sans rapport avec l’exécution d’un contrat.' },
        ],
      },
      {
        titre: 'Les trois conditions',
        blocs: [
          {
            ordonnee: true,
            liste: [
              'Une faute : un comportement que n’aurait pas eu une personne prudente et diligente. Elle peut être intentionnelle ou non ; l’article 1241 vise la négligence et l’imprudence.',
              'Un dommage : la doctrine et la jurisprudence exigent un préjudice certain, personnel et direct. Il peut être matériel, corporel ou moral.',
              'Un lien de causalité entre la faute et le dommage. Les cours présentent deux grandes théories : l’équivalence des conditions et la causalité adéquate.',
            ],
          },
          { p: 'C’est à la victime de prouver ces trois éléments.' },
        ],
      },
      {
        titre: 'Les autres régimes du même chapitre',
        blocs: [
          { p: 'L’article 1242 étend la responsabilité au fait des choses que l’on a sous sa garde et au fait des personnes dont on doit répondre. Les parents en sont responsables de plein droit pour leurs enfants mineurs. Cet article a été modifié en 2025 : vérifiez la version citée ci-dessous.' },
          { citation: 'code_civil:1242', alineas: [0, 3] },
        ],
      },
      {
        titre: 'Anciens et nouveaux numéros',
        blocs: [
          {
            liste: [
              'Ancien article 1382 : aujourd’hui article 1240.',
              'Ancien article 1383 : aujourd’hui article 1241.',
              'Ancien article 1384 : aujourd’hui article 1242.',
            ],
          },
          { p: 'Les arrêts antérieurs à 2016 citent les anciens numéros : pensez à faire le lien dans vos copies.' },
        ],
      },
    ],
    faq: [
      { question: 'Une simple imprudence suffit-elle à engager la responsabilité ?', reponse: 'Oui. L’article 1241 du Code civil rend chacun responsable du dommage causé par sa négligence ou son imprudence, pas seulement par un acte volontaire.' },
      { question: 'Quelle différence avec la responsabilité contractuelle ?', reponse: 'La responsabilité contractuelle répare le dommage causé par l’inexécution d’un contrat (article 1231-1 du Code civil). Les articles 1240 et 1241 s’appliquent en dehors de tout contrat.' },
    ],
  },
  'fiche-question-prioritaire-de-constitutionnalite': {
    enBref: 'La question prioritaire de constitutionnalité permet de soutenir, au cours d’un procès, qu’une disposition législative porte atteinte aux droits et libertés que la Constitution garantit (article 61-1 de la Constitution). Le juge la transmet au Conseil d’État ou à la Cour de cassation si trois conditions sont réunies ; ceux-ci décident de saisir ou non le Conseil constitutionnel. Une disposition déclarée inconstitutionnelle est abrogée (article 62).',
    sections: [
      {
        titre: 'Deux contrôles de constitutionnalité',
        blocs: [
          { p: 'Avant la promulgation d’une loi, le contrôle a priori est ouvert à des autorités politiques, dont soixante députés ou soixante sénateurs (article 61).' },
          { citation: 'constitution_1958:61', alineas: [1, 2] },
          { p: 'Après son entrée en vigueur, la loi peut être contestée par la QPC, à l’occasion d’une instance en cours devant une juridiction (article 61-1).' },
          { citation: 'constitution_1958:61-1' },
        ],
      },
      {
        titre: 'Les conditions de transmission',
        blocs: [
          { p: 'Elles sont fixées par l’ordonnance n° 58-1067 du 7 novembre 1958 portant loi organique sur le Conseil constitutionnel, en vigueur sur ce point depuis le 1er mars 2010.' },
          { citation: 'ordonnance_58_1067:23-2', alineas: [0, 1, 2, 3] },
          { p: 'La question est « prioritaire » : saisi à la fois d’une contestation de la loi au regard de la Constitution et au regard des engagements internationaux, le juge se prononce d’abord sur la transmission de la QPC.' },
          { citation: 'ordonnance_58_1067:23-2', alineas: [4] },
        ],
      },
      {
        titre: 'Les effets de la décision',
        blocs: [
          { citation: 'constitution_1958:62' },
          { p: 'Le Conseil constitutionnel peut donc reporter l’abrogation dans le temps et en régler les effets. Ses décisions s’imposent à toutes les autorités.' },
        ],
      },
      {
        titre: 'Pour un cas pratique ou une dissertation',
        blocs: [
          {
            liste: [
              'Vérifiez qu’il s’agit d’une disposition législative (pas d’un décret).',
              'Identifiez le droit ou la liberté constitutionnellement garanti en cause.',
              'Reprenez les trois conditions de l’article 23-2 une à une.',
              'Distinguez bien le contrôle de constitutionnalité (Conseil constitutionnel) du contrôle de conventionnalité (juges ordinaires, article 55 de la Constitution).',
            ],
          },
        ],
      },
    ],
    faq: [
      { question: 'Qui peut poser une QPC ?', reponse: 'Une partie à un procès en cours, devant une juridiction relevant du Conseil d’État ou de la Cour de cassation ou devant l’une de ces deux cours, en soutenant qu’une disposition législative porte atteinte aux droits et libertés que la Constitution garantit.' },
      { question: 'Que devient une loi déclarée inconstitutionnelle après une QPC ?', reponse: 'Elle est abrogée à compter de la publication de la décision ou d’une date ultérieure fixée par le Conseil constitutionnel, qui détermine les conditions dans lesquelles les effets passés peuvent être remis en cause (article 62 de la Constitution).' },
    ],
  },
  'methode-cas-pratique-droit-penal': {
    enBref: 'Un cas pratique de droit pénal se résout infraction par infraction : trouver le texte d’incrimination (élément légal), vérifier l’acte (élément matériel) et l’intention ou la faute (élément moral), puis examiner les causes d’irresponsabilité, comme la légitime défense, avant d’indiquer la peine encourue.',
    sections: [
      {
        titre: '1. L’élément légal',
        blocs: [
          { p: 'Pas d’infraction sans texte : chaque qualification doit reposer sur un article qui définit les éléments de l’infraction et la peine. Citez-le précisément, avec sa version en vigueur à la date des faits.' },
          { citation: 'code_penal:111-3' },
        ],
      },
      {
        titre: '2. L’élément matériel et l’auteur',
        blocs: [
          { p: 'Décrivez l’acte (une action, parfois une abstention) et le résultat exigé par le texte. La responsabilité pénale est personnelle : chacun ne répond que de son propre fait, ce qui oblige à examiner séparément chaque protagoniste.' },
          { citation: 'code_penal:121-1' },
        ],
      },
      {
        titre: '3. L’élément moral',
        blocs: [
          { p: 'Les crimes et délits sont en principe intentionnels. Une imprudence ou une mise en danger ne suffit que si la loi le prévoit pour l’infraction en cause.' },
          { citation: 'code_penal:121-3', alineas: [0, 1, 2] },
        ],
      },
      {
        titre: '4. Les causes d’irresponsabilité',
        blocs: [
          { p: 'Une infraction constituée peut ne pas être punissable. La légitime défense des personnes suppose une atteinte injustifiée, une riposte dans le même temps, nécessaire et proportionnée ; la défense des biens exclut l’homicide volontaire et exige un acte strictement nécessaire.' },
          { citation: 'code_penal:122-5' },
        ],
      },
      {
        titre: '5. Structurer la copie',
        blocs: [
          {
            ordonnee: true,
            liste: [
              'Pour chaque personne et chaque fait : la qualification envisagée et son texte.',
              'Les éléments matériel et moral, confrontés aux faits.',
              'Les causes d’irresponsabilité éventuelles.',
              'La conclusion : l’infraction est-elle constituée et punissable, quelle peine est encourue ?',
            ],
          },
          { p: 'Si plusieurs qualifications sont possibles, envisagez-les dans l’ordre de gravité et expliquez votre choix.' },
        ],
      },
    ],
    faq: [
      { question: 'Faut-il toujours citer l’article d’incrimination ?', reponse: 'Oui. Le principe de légalité (article 111-3 du Code pénal) interdit de punir un comportement que la loi, ou le règlement pour une contravention, ne définit pas. La copie doit donc partir du texte.' },
      { question: 'Une infraction non intentionnelle existe-t-elle ?', reponse: 'Oui, mais seulement lorsque la loi le prévoit : mise en danger délibérée de la personne d’autrui, ou faute d’imprudence, de négligence ou de manquement à une obligation de prudence ou de sécurité (article 121-3 du Code pénal).' },
    ],
  },
}

export interface Guide extends GuideListe, CorpsGuide {}

export const GUIDES: Guide[] = GUIDES_LISTE.map((g) => {
  const c = CORPS[g.slug]
  if (!c) throw new Error(`Contenu manquant pour le guide ${g.slug}`)
  return { ...g, ...c }
})

/** Cles des articles cites par un guide, dans l'ordre et sans doublon. */
export const clesCitations = (g: Guide) =>
  [...new Set(g.sections.flatMap((s) => s.blocs.flatMap((b) => ('citation' in b ? [b.citation] : []))))]

export const guideParSlug = (slug: string) => GUIDES.find((g) => g.slug === slug)
