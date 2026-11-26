/** Version des conditions generales (date de leur derniere modification). Affichee en tete des CGU et envoyee
 *  avec chaque demande de paiement ; le serveur refuse une version qui n'est pas la sienne (api/paiement.py,
 *  VERSION_CGU) : les deux sont a changer ensemble, a chaque modification des conditions. */
export const VERSION_CGU = '20 novembre 2026'

/** Date de la derniere modification de la politique de confidentialite : affichee en tete de la page et nom du
 *  fichier de son texte (docs/confidentialite/, `npm run confidentialite` dans web/). */
export const VERSION_CONFIDENTIALITE = '26 novembre 2026'
