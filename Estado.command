#!/usr/bin/env bash
cd "$(dirname "$0")" || exit 1
# shellcheck disable=SC1091
source ./_entorno.sh || exit 1

python -m ragnar_agent.cli.estado

echo
read -r -p "  Presiona ENTER para cerrar... "
