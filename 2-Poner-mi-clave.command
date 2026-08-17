#!/usr/bin/env bash
# Poner o cambiar la clave de Claude. Se puede abrir las veces que haga falta.
cd "$(dirname "$0")" || exit 1
# shellcheck disable=SC1091
source ./_entorno.sh || exit 1

python -m ragnar_agent.cli.configurar

echo
read -r -p "  Presiona ENTER para cerrar... "
