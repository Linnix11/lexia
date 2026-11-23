// Chemins et titres des pages publiques de contenu (D116). Module leger : le routeur (Site.tsx) le lit sans
// charger le texte des matieres et des guides, qui reste dans un fichier a part telecharge a la demande.
import { matieres } from './donnees-publiques.json'
import { GUIDES_LISTE } from './contenu/guidesListe'

/** « droit_des_contrats » devient « droit-des-contrats ». */
export const slugMatiere = (id: string) => id.replace(/_/g, '-')

// Court : 62 caracteres au plus avec « · Lexia », les moteurs coupent vers 60 (audit du 2026-11-23, D13)
export const titreMatiere = (m: { libelle: string; annee?: string }) => `${m.libelle} (${m.annee}) : cours et sources`

export const CHEMINS_MATIERES = matieres.map((m) => `/matieres/${slugMatiere(m.id)}`)
export const CHEMINS_GUIDES = GUIDES_LISTE.map((g) => `/guides/${g.slug}`)

/** Titre court de chaque page publique ; l'onglet affiche « titre · Lexia » (sauf l'accueil). */
export const TITRES_PUBLICS: Record<string, string> = {
  '/': 'Lexia, assistant d’étude du droit pour la licence',
  '/tarifs': 'Tarifs : gratuit, Étudiant et Intensif',
  '/matieres': `Les ${matieres.length} matières de la licence de droit`,
  '/guides': 'Guides de méthode et fiches de droit',
  '/mentions-legales': 'Mentions légales',
  '/cgu': 'Conditions d’utilisation',
  '/confidentialite': 'Politique de confidentialité',
  ...Object.fromEntries(matieres.map((m) => [`/matieres/${slugMatiere(m.id)}`, titreMatiere(m)])),
  ...Object.fromEntries(GUIDES_LISTE.map((g) => [`/guides/${g.slug}`, g.titre])),
}
