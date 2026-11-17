/** Version des conditions generales (date de leur derniere modification). Affichee en tete des CGU et envoyee
 *  avec chaque demande de paiement ; le serveur refuse une version qui n'est pas la sienne (api/paiement.py,
 *  VERSION_CGU) : les deux sont a changer ensemble, a chaque modification des conditions. */
export const VERSION_CGU = '17 novembre 2026'
