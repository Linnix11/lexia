#!/bin/sh
# Ouvre projections.xlsx dans Microsoft Excel (Mac), recalcule et enregistre : le fichier garde ensuite les
# valeurs en cache (apercu du Mac, GitHub, messageries). A lancer apres generer_projections.py.
# Usage : sh docs/business/outils/enregistrer_excel.sh [chemin du classeur]
set -e
F="${1:-$(cd "$(dirname "$0")/.." && pwd)/projections.xlsx}"
osascript <<FIN
tell application "Microsoft Excel"
  open (POSIX file "$F")
  calculate full
  save active workbook
  close active workbook saving no
end tell
FIN
echo "$F"
