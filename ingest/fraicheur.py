"""Fraicheur du corpus : date de la derniere mise a jour nocturne reussie, alerte en cas d'echec (audit B8).

Le 2026-11-17, la mise a jour a echoue (ModuleNotFoundError) sans que personne le sache : l'index restait
celui de la veille. Desormais :
  - deploy/mettre_a_jour_corpus.sh ecrit data/mise_a_jour_reussie (date ISO) apres chaque passage reussi,
    nouvel index mis en service ou rien de nouveau chez la DILA ;
  - /api/sante dit si cette date a moins de 36 h (corpus_a_jour), et la donne en local seulement ;
  - la surveillance GitHub echoue si corpus_a_jour vaut false ;
  - en cas d'echec, le script envoie un e-mail aux ADMIN_EMAILS :
        python -m ingest.fraicheur --alerte "message"

Module volontairement leger (bibliotheque standard et api.courriel) : l'alerte doit partir meme quand
une dependance de l'ingestion manque, ce qui etait la cause de l'echec du 17 novembre.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

MARQUEUR = "mise_a_jour_reussie"
DELAI_MAX = timedelta(hours=36)
ROOT = Path(__file__).resolve().parent.parent


def derniere_reussite(data_dir: Path) -> datetime | None:
    """Date de la derniere mise a jour reussie ; a defaut (avant le premier passage), date de construction
    de l'index en service (archives.txt, ecrit par ingest.mise_a_jour)."""
    marqueur = data_dir / MARQUEUR
    try:
        return datetime.fromisoformat(marqueur.read_text().strip())
    except (OSError, ValueError):
        pass
    archives = data_dir / "index" / "archives.txt"
    if archives.exists():
        return datetime.fromtimestamp(archives.stat().st_mtime, tz=timezone.utc)
    return None


def a_jour(data_dir: Path, maintenant: datetime | None = None) -> bool | None:
    """None : rien ne permet de le dire (developpement, index construit a la main)."""
    d = derniere_reussite(data_dir)
    if d is None:
        return None
    if d.tzinfo is None:
        d = d.astimezone()
    return (maintenant or datetime.now(timezone.utc)) - d <= DELAI_MAX


def alerter(message: str) -> int:
    from api import courriel
    from ingest.env import load_env

    load_env(ROOT / ".env")
    destinataires = [a.strip() for a in os.environ.get("ADMIN_EMAILS", "").split(",") if a.strip()]
    if not courriel.configure() or not destinataires:
        print("alerte non envoyee (RESEND_API_KEY ou ADMIN_EMAILS absent) : " + message, file=sys.stderr)
        return 1
    texte = (f"La mise a jour nocturne du corpus Lexia a echoue.\n\n{message}\n\n"
             "L'index en service reste le precedent. Journal : /var/log/lexia-mise-a-jour.log")
    for a in destinataires:
        courriel.envoyer(a, "Lexia : echec de la mise a jour du corpus", texte,
                         "<pre>" + courriel._echapper(texte) + "</pre>")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--alerte", metavar="MESSAGE", required=True, help="Envoyer l'e-mail d'echec")
    return alerter(parser.parse_args(argv).alerte)


if __name__ == "__main__":
    sys.exit(main())
