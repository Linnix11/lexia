// Pages publiques des 20 matieres (D116). L'annee, les autres intitules et les sources viennent de
// donnees-publiques.json (api/matieres.py et registry/sources.yaml) ; seuls la presentation et la question de
// cours sont ecrites ici. Chaque reponse renvoie a un article cite, dont le texte est lu dans l'index.
import { matieres } from '../donnees-publiques.json'
import noms from './noms-sources.json'
import type { Matiere } from '../../lib/api'
import { slugMatiere } from '../routesPubliques'

export interface QuestionCours {
  question: string
  reponse: string
  /** Cles de citations.json, avec les alineas a montrer (tous par defaut). */
  citations: { cle: string; alineas?: number[] }[]
}

interface TexteMatiere {
  presentation: string
  questions: QuestionCours[]
  /** Guides publics utiles dans la matiere (slug). */
  guides?: string[]
}

export const TEXTES_MATIERES: Record<string, TexteMatiere> = {
  introduction_au_droit: {
    presentation: 'L’introduction au droit présente ce qu’est une règle de droit, d’où elle vient (Constitution, traités, lois, règlements, jurisprudence) et comment les juridictions sont organisées. C’est aussi la matière où l’on découvre la méthodologie : fiche d’arrêt, cas pratique, dissertation.',
    questions: [{
      question: 'Une loi nouvelle s’applique-t-elle aux situations passées ?',
      reponse: 'En principe non : selon l’article 2 du Code civil, la loi ne dispose que pour l’avenir et n’a point d’effet rétroactif. Ce principe et ses limites sont un sujet classique de première année.',
      citations: [{ cle: 'code_civil:2' }],
    }],
    guides: ['methode-commentaire-arret', 'methode-cas-pratique-droit-des-contrats'],
  },
  droit_constitutionnel: {
    presentation: 'Le droit constitutionnel étudie l’État, la séparation des pouvoirs et les institutions de la Ve République : Président de la République, Gouvernement, Parlement et Conseil constitutionnel. En première année, il couvre aussi la théorie générale de l’État et l’histoire constitutionnelle française.',
    questions: [{
      question: 'Qu’est-ce que la question prioritaire de constitutionnalité (QPC) ?',
      reponse: 'C’est la possibilité, au cours d’un procès, de soutenir qu’une disposition législative porte atteinte aux droits et libertés que la Constitution garantit. Le Conseil constitutionnel est alors saisi sur renvoi du Conseil d’État ou de la Cour de cassation (article 61-1 de la Constitution).',
      citations: [{ cle: 'constitution_1958:61-1' }],
    }],
    guides: ['fiche-question-prioritaire-de-constitutionnalite'],
  },
  droit_civil: {
    presentation: 'Le droit civil règle les rapports entre particuliers. En première année, il porte d’abord sur les personnes : personnalité juridique, état civil, capacité et droits de la personnalité. La famille, les biens puis les obligations (contrats et responsabilité civile) suivent au fil de la licence.',
    questions: [{
      question: 'Le droit au respect de la vie privée est-il inscrit dans le Code civil ?',
      reponse: 'Oui. L’article 9 du Code civil dispose que chacun a droit au respect de sa vie privée. Il permet au juge de prescrire des mesures pour empêcher ou faire cesser une atteinte à l’intimité de la vie privée, en référé s’il y a urgence.',
      citations: [{ cle: 'code_civil:9' }],
    }],
    guides: ['fiche-responsabilite-civile-pour-faute'],
  },
  droit_de_la_famille: {
    presentation: 'Le droit de la famille traite du couple (mariage, pacte civil de solidarité, concubinage, divorce), de la filiation et de l’autorité parentale. Le droit patrimonial de la famille (régimes matrimoniaux, successions, libéralités) est souvent enseigné plus tard dans la licence.',
    questions: [{
      question: 'Comment le Code civil définit-il l’autorité parentale ?',
      reponse: 'L’article 371-1 du Code civil la définit comme un ensemble de droits et de devoirs ayant pour finalité l’intérêt de l’enfant. Elle appartient aux parents jusqu’à la majorité ou l’émancipation de l’enfant et s’exerce sans violences physiques ou psychologiques.',
      citations: [{ cle: 'code_civil:371-1' }],
    }],
  },
  droit_des_biens: {
    presentation: 'Le droit des biens distingue les choses et les biens, les meubles et les immeubles, et étudie les droits que l’on peut avoir sur eux : la propriété, ses démembrements (usufruit, servitudes) et la possession.',
    questions: [{
      question: 'Comment le Code civil définit-il la propriété ?',
      reponse: 'Selon l’article 544 du Code civil, la propriété est le droit de jouir et disposer des choses de la manière la plus absolue, pourvu qu’on n’en fasse pas un usage prohibé par les lois ou par les règlements.',
      citations: [{ cle: 'code_civil:544' }],
    }],
  },
  droit_des_contrats: {
    presentation: 'Le droit des contrats, au cœur du droit des obligations, étudie la formation du contrat (négociations, consentement, capacité, contenu), ses effets et les sanctions de son inexécution. Les articles du Code civil sur le contrat ont été réécrits en 2016 : la plupart sont en vigueur depuis le 1er octobre 2016.',
    questions: [{
      question: 'Quelles sont les conditions de validité d’un contrat ?',
      reponse: 'L’article 1128 du Code civil en pose trois : le consentement des parties, leur capacité de contracter et un contenu licite et certain. Un contrat qui ne les remplit pas est nul (article 1178).',
      citations: [{ cle: 'code_civil:1128' }, { cle: 'code_civil:1178', alineas: [0] }],
    }],
    guides: ['methode-cas-pratique-droit-des-contrats'],
  },
  droit_administratif: {
    presentation: 'Le droit administratif régit l’action de l’administration : actes administratifs unilatéraux, contrats administratifs, service public, police administrative et responsabilité de la puissance publique. Il est en grande partie construit par la jurisprudence du Conseil d’État et du Tribunal des conflits.',
    questions: [{
      question: 'Que vaut le silence de l’administration sur une demande ?',
      reponse: 'En principe, le silence gardé pendant deux mois par l’administration sur une demande vaut décision d’acceptation (article L. 231-1 du Code des relations entre le public et l’administration). Le même code prévoit des exceptions, à vérifier pour chaque demande.',
      citations: [{ cle: 'code_relations_public_administration:L231-1' }],
    }],
  },
  droit_europeen: {
    presentation: 'Le droit de l’Union européenne étudie les institutions de l’Union, ses sources (traités, règlements, directives), ses rapports avec le droit national et le marché intérieur. Les traités de l’Union et la Charte des droits fondamentaux sont dans les sources de Lexia ; la jurisprudence de la Cour de justice de l’Union n’y est pas encore.',
    questions: [{
      question: 'Sur quel fondement la France participe-t-elle à l’Union européenne ?',
      reponse: 'L’article 88-1 de la Constitution prévoit que la République participe à l’Union européenne, constituée d’États qui exercent en commun certaines de leurs compétences en vertu du traité sur l’Union européenne et du traité sur le fonctionnement de l’Union européenne.',
      citations: [{ cle: 'constitution_1958:88-1' }],
    }],
  },
  droit_penal: {
    presentation: 'Le droit pénal général étudie l’infraction (élément légal, matériel et moral), la responsabilité pénale et la peine. Le droit pénal spécial étudie les infractions une à une : atteintes aux personnes, aux biens, à la Nation et à la paix publique.',
    questions: [{
      question: 'Que signifie le principe de légalité criminelle ?',
      reponse: 'Nul ne peut être puni pour un crime ou un délit dont les éléments ne sont pas définis par la loi, ni d’une peine que la loi ne prévoit pas ; pour les contraventions, c’est le règlement qui les définit (article 111-3 du Code pénal).',
      citations: [{ cle: 'code_penal:111-3' }],
    }],
    guides: ['methode-cas-pratique-droit-penal'],
  },
  droit_des_affaires: {
    presentation: 'Le droit des affaires, ou droit commercial, porte sur le commerçant, les actes de commerce, le fonds de commerce, les baux commerciaux et la concurrence.',
    questions: [{
      question: 'Qui est commerçant au sens du Code de commerce ?',
      reponse: 'Selon l’article L. 121-1 du Code de commerce, sont commerçants ceux qui exercent des actes de commerce et en font leur profession habituelle.',
      citations: [{ cle: 'code_commerce:L121-1' }],
    }],
  },
  finances_publiques: {
    presentation: 'Les finances publiques étudient les budgets de l’État, des collectivités territoriales et de la sécurité sociale : lois de finances, principes budgétaires, exécution des dépenses et des recettes, contrôle par le Parlement et la Cour des comptes.',
    questions: [{
      question: 'Que se passe-t-il si le Parlement ne se prononce pas à temps sur le projet de loi de finances ?',
      reponse: 'Selon l’article 47 de la Constitution, si le Parlement ne s’est pas prononcé dans un délai de soixante-dix jours, les dispositions du projet peuvent être mises en vigueur par ordonnance.',
      citations: [{ cle: 'constitution_1958:47', alineas: [0, 2] }],
    }],
  },
  procedure_civile: {
    presentation: 'La procédure civile, ou droit judiciaire privé, étudie le procès civil : action en justice, compétence des juridictions, principes directeurs du procès, déroulement de l’instance, jugement et voies de recours.',
    questions: [{
      question: 'Le juge civil est-il lié par la qualification que les parties donnent aux faits ?',
      reponse: 'En principe non. Le juge tranche le litige conformément aux règles de droit et doit donner ou restituer leur exacte qualification aux faits et actes litigieux (article 12 du Code de procédure civile), sauf si les parties l’ont lié par un accord exprès, pour les droits dont elles ont la libre disposition.',
      citations: [{ cle: 'code_procedure_civile:12', alineas: [0, 1, 2] }],
    }],
    guides: ['methode-commentaire-arret'],
  },
  procedure_penale: {
    presentation: 'La procédure pénale règle le déroulement du procès pénal : enquête, garde à vue, action publique, instruction, jugement et voies de recours, avec les droits de la personne poursuivie et ceux de la victime.',
    questions: [{
      question: 'Qu’est-ce que la garde à vue ?',
      reponse: 'C’est une mesure de contrainte décidée par un officier de police judiciaire, sous le contrôle de l’autorité judiciaire, qui maintient à la disposition des enquêteurs une personne soupçonnée d’avoir commis ou tenté de commettre un crime ou un délit puni d’emprisonnement (article 62-2 du Code de procédure pénale). Elle doit être l’unique moyen d’atteindre l’un des objectifs que cet article énumère.',
      citations: [{ cle: 'code_procedure_penale:62-2', alineas: [0, 1] }],
    }],
    guides: ['methode-cas-pratique-droit-penal'],
  },
  droit_social: {
    presentation: 'Le droit social réunit le droit du travail (formation et rupture du contrat de travail, relations individuelles et collectives) et le droit de la protection sociale.',
    questions: [{
      question: 'Quelles règles s’appliquent au contrat de travail ?',
      reponse: 'L’article L. 1221-1 du Code du travail le soumet aux règles du droit commun des contrats et laisse les parties choisir sa forme. Le Code du travail ajoute ensuite ses règles propres.',
      citations: [{ cle: 'code_travail:L1221-1' }],
    }],
  },
  droit_des_societes: {
    presentation: 'Le droit des sociétés étudie la constitution, le fonctionnement et la dissolution des sociétés : société à responsabilité limitée, société par actions simplifiée, société anonyme, sociétés civiles.',
    questions: [{
      question: 'Comment le Code civil définit-il la société ?',
      reponse: 'Selon l’article 1832 du Code civil, la société est instituée par deux ou plusieurs personnes qui conviennent par un contrat d’affecter à une entreprise commune des biens ou leur industrie, pour partager le bénéfice ou profiter de l’économie qui pourra en résulter. Elle peut aussi, dans les cas prévus par la loi, être créée par une seule personne, et les associés s’engagent à contribuer aux pertes.',
      citations: [{ cle: 'code_civil:1832' }],
    }],
  },
  contentieux_administratif: {
    presentation: 'Le contentieux administratif étudie le procès devant le juge administratif : recours pour excès de pouvoir, recours de plein contentieux, délais, référés et exécution des décisions de justice.',
    questions: [
      {
        question: 'Dans quel délai faut-il saisir le juge administratif ?',
        reponse: 'En principe dans les deux mois à partir de la notification ou de la publication de la décision attaquée (article R. 421-1 du Code de justice administrative). Ce délai ne s’applique pas à la contestation des mesures prises pour l’exécution d’un contrat.',
        citations: [{ cle: 'code_justice_administrative:R421-1', alineas: [0, 2] }],
      },
      {
        question: 'Qu’est-ce que le référé-liberté ?',
        reponse: 'En cas d’urgence, le juge des référés peut ordonner toutes mesures nécessaires à la sauvegarde d’une liberté fondamentale à laquelle une personne publique, ou un organisme privé chargé d’un service public, a porté une atteinte grave et manifestement illégale. Il se prononce en quarante-huit heures (article L. 521-2 du Code de justice administrative).',
        citations: [{ cle: 'code_justice_administrative:L521-2' }],
      },
    ],
  },
  droit_administratif_des_biens: {
    presentation: 'Le droit administratif des biens étudie les propriétés des personnes publiques (domaine public et domaine privé), leur protection et leur utilisation, ainsi que l’expropriation pour cause d’utilité publique.',
    questions: [{
      question: 'Qu’est-ce que le domaine public ?',
      reponse: 'Selon l’article L. 2111-1 du Code général de la propriété des personnes publiques, il est constitué, sauf dispositions législatives spéciales, des biens d’une personne publique affectés à l’usage direct du public, ou affectés à un service public s’ils font l’objet d’un aménagement indispensable à l’exécution des missions de ce service.',
      citations: [{ cle: 'code_propriete_personnes_publiques:L2111-1' }],
    }],
  },
  droit_international: {
    presentation: 'Le droit international public régit les rapports entre États et organisations internationales (traités, coutume, responsabilité). Le droit international privé règle les situations entre particuliers qui touchent plusieurs pays : conflits de lois et de juridictions.',
    questions: [{
      question: 'Quelle est la place des traités dans le droit français ?',
      reponse: 'Selon l’article 55 de la Constitution, les traités ou accords régulièrement ratifiés ou approuvés ont, dès leur publication, une autorité supérieure à celle des lois, sous réserve de leur application par l’autre partie.',
      citations: [{ cle: 'constitution_1958:55' }],
    }],
  },
  libertes_fondamentales: {
    presentation: 'Les libertés fondamentales étudient les droits et libertés protégés en France (liberté d’expression, respect de la vie privée, égalité, sûreté), leurs sources (Déclaration de 1789, Préambule de 1946, Constitution, Charte des droits fondamentaux de l’Union) et les juges qui les garantissent.',
    questions: [{
      question: 'Où la liberté d’expression est-elle protégée ?',
      reponse: 'Notamment à l’article 11 de la Déclaration des droits de l’homme et du citoyen de 1789 : tout citoyen peut parler, écrire, imprimer librement, sauf à répondre de l’abus de cette liberté dans les cas déterminés par la loi.',
      citations: [{ cle: 'ddhc_1789:11' }],
    }],
  },
  droit_fiscal: {
    presentation: 'Le droit fiscal étudie les impôts (impôt sur le revenu, impôt sur les sociétés, taxe sur la valeur ajoutée…), leur établissement, leur recouvrement et le contentieux fiscal.',
    questions: [{
      question: 'Quel principe fonde l’impôt en droit français ?',
      reponse: 'L’article 13 de la Déclaration des droits de l’homme et du citoyen de 1789 : une contribution commune est indispensable et doit être également répartie entre tous les citoyens, en raison de leurs facultés.',
      citations: [{ cle: 'ddhc_1789:13' }],
    }],
  },
}

export interface MatierePublique extends Matiere, TexteMatiere {
  slug: string
}

const NOMS: Record<string, string> = noms

export const MATIERES_PUBLIQUES: MatierePublique[] = matieres.map((m) => {
  const t = TEXTES_MATIERES[m.id]
  if (!t) throw new Error(`Texte public manquant pour la matière ${m.id}`)
  const noms = Object.fromEntries(m.sources.map((s) => [s, NOMS[s] ?? s]))
  return { ...(m as Matiere), noms_sources: noms, ...t, slug: slugMatiere(m.id) }
})

export const matiereParSlug = (slug: string) => MATIERES_PUBLIQUES.find((m) => m.slug === slug)
