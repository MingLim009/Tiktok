#!/usr/bin/env bash
cd "$(dirname "$0")" || exit 1
# shellcheck disable=SC1091
source ./_entorno.sh || exit 1
export LOG_LEVEL=INFO

python -m ragnar_agent.cli.login || echo "
  [X] No se pudo guardar la sesion. Vuelve a intentarlo, y si sigue
      igual mandame una captura de esta ventana completa."

echo
read -r -p "  Presiona ENTER para cerrar... "
