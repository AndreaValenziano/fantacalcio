#!/bin/bash
# Doppio clic per avviare il Consigliere di formazione su Mac.
cd "$(dirname "$0")" || exit 1
PY=""
for c in python3 /usr/local/bin/python3 /opt/homebrew/bin/python3 /usr/bin/python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  echo "Non trovo Python 3.11 o successivo. Installalo seguendo GUIDA.md, poi riprova."
  read -n 1 -r -p "Premi un tasto per chiudere."
  exit 1
fi
"$PY" -m consigliere || { echo; read -n 1 -r -p "Si è verificato un errore. Premi un tasto per chiudere."; }
