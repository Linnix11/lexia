"""Administration des comptes en ligne de commande (sans interface web : rien a exposer sur Internet).

Sur le serveur :
    cd /opt/lexia && sudo -u lexia .venv/bin/python -m api.admin liste
    sudo -u lexia .venv/bin/python -m api.admin formule etudiant@exemple.fr etudiant --jours 31
    sudo -u lexia .venv/bin/python -m api.admin formule etudiant@exemple.fr gratuit
    sudo -u lexia .venv/bin/python -m api.admin infos etudiant@exemple.fr
    sudo -u lexia .venv/bin/python -m api.admin admin moi@exemple.fr        (--retirer pour l'enlever)
    sudo -u lexia .venv/bin/python -m api.admin supprimer etudiant@exemple.fr
    sudo -u lexia .venv/bin/python -m api.admin motdepasse etudiant@exemple.fr   (saisie masquee ; ssh -t)
    sudo -u lexia .venv/bin/python -m api.admin desactiver2fa etudiant@exemple.fr (telephone et codes de secours perdus)

Formules : gratuit, etudiant, intensif (voir api/plans.py). --jours : duree d'une formule payante ;
a l'echeance, le compte repasse automatiquement en gratuit.
"""

from __future__ import annotations

import argparse
import getpass
import sys

from api.comptes import Comptes, ErreurCompte
from api.config import get_settings
from api.plans import FORMULES


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sous = parser.add_subparsers(dest="commande", required=True)
    sous.add_parser("liste", help="Lister les comptes")
    p = sous.add_parser("formule", help="Changer la formule d'un compte")
    p.add_argument("email")
    p.add_argument("formule", choices=sorted(FORMULES))
    p.add_argument("--jours", type=int, help="Duree en jours (formule payante), sinon sans fin")
    p = sous.add_parser("infos", help="Formule et consommation du jour d'un compte")
    p.add_argument("email")
    p = sous.add_parser("admin", help="Donner ou retirer le role administrateur")
    p.add_argument("email")
    p.add_argument("--retirer", action="store_true", help="Retirer le role au lieu de le donner")
    p = sous.add_parser("supprimer", help="Supprimer definitivement un compte")
    p.add_argument("email")
    p.add_argument("--oui", action="store_true", help="Ne pas demander de confirmation")
    p = sous.add_parser("desactiver2fa", help="Desactiver la double authentification (telephone perdu)")
    p.add_argument("email")
    p = sous.add_parser("motdepasse", help="Definir un nouveau mot de passe (saisie masquee) et fermer les sessions")
    p.add_argument("email")
    args = parser.parse_args(argv)

    settings = get_settings()
    comptes = Comptes(settings.app_db, admins=settings.admin_emails)
    try:
        if args.commande == "liste":
            utilisateurs = comptes.lister()
            for u in utilisateurs:
                fin = f" jusqu'au {u.formule_fin}" if u.formule_fin else ""
                role = " [admin]" if u.admin else ""
                print(f"{u.email:40s} {u.formule_id:9s}{fin:20s} cree le {u.cree_le[:10]}{role}")
            print(f"{len(utilisateurs)} compte(s)")
        elif args.commande == "formule":
            u = comptes.changer_formule(args.email, args.formule, args.jours)
            fin = f" jusqu'au {u.formule_fin}" if u.formule_fin else " (sans fin)"
            print(f"{u.email} : formule {u.formule_id}{fin}")
        elif args.commande == "admin":
            u = comptes.definir_admin(args.email, not args.retirer)
            print(f"{u.email} : {'administrateur' if u.admin else 'utilisateur'}")
        elif args.commande == "infos":
            u = comptes.par_email(args.email)
            if u is None:
                raise ErreurCompte(f"Aucun compte pour {args.email}")
            us = comptes.usage(u.id)
            f = u.formule
            print(f"{u.email} - formule active : {f.nom} (enregistree : {u.formule_id}, fin : {u.formule_fin or '-'})")
            print(f"Aujourd'hui : {us['questions']}/{f.questions_par_jour} questions, {us['quiz']}/{f.quiz_par_jour} quiz")
        elif args.commande == "supprimer":
            u = comptes.par_email(args.email)
            if u is None:
                raise ErreurCompte(f"Aucun compte pour {args.email}")
            if not args.oui and input(f"Supprimer definitivement {u.email} ? (oui/non) ").strip().lower() != "oui":
                print("Annule.")
                return 1
            comptes.supprimer(u.id)
            print(f"{u.email} supprime.")
        elif args.commande == "desactiver2fa":
            u = comptes.par_email(args.email)
            if u is None:
                raise ErreurCompte(f"Aucun compte pour {args.email}")
            comptes.desactiver_2fa(u.id)
            print(f"{u.email} : double authentification desactivee, sessions fermees.")
        elif args.commande == "motdepasse":
            mdp = getpass.getpass("Nouveau mot de passe : ")
            if getpass.getpass("Confirmer : ") != mdp:
                raise ErreurCompte("Les deux saisies ne correspondent pas.")
            u = comptes.changer_mdp(args.email, mdp)
            print(f"{u.email} : mot de passe change, sessions fermees.")
    except ErreurCompte as e:
        print(f"Erreur : {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
