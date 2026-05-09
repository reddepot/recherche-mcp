#!/usr/bin/env bash
# Reload à chaud de la matrice dispatch YAML après édition.
# Évite le rebuild Docker / restart serveur.

set -euo pipefail

PIDS=$(pgrep -f "recherche-mcp" || true)

if [[ -z "$PIDS" ]]; then
    echo "Aucun processus recherche-mcp détecté."
    exit 1
fi

echo "Envoi SIGHUP aux processus :"
for pid in $PIDS; do
    echo "  PID $pid"
    kill -HUP "$pid"
done

echo "✓ Matrice dispatch rechargée."
