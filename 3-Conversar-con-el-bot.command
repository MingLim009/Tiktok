#!/usr/bin/env bash
cd "$(dirname "$0")" || exit 1
# shellcheck disable=SC1091
source ./_entorno.sh || exit 1

clear
echo
echo "=================================================================="
echo "  CONVERSAR CON EL BOT"
echo "=================================================================="
echo
echo "  Escribele como si fueras un cliente tuyo. Por ejemplo:"
echo
echo "      a cuanto esta el cambio?"
echo "      quiero cambiar 5000 bolivianos a soles"
echo "      y si son 300 mil?"
echo "      me pueden llamar?"
echo
echo "  Escribe  salir  para terminar."
echo
echo "  (Necesita tu clave de Claude en el archivo .env)"
echo "=================================================================="
echo

python -m ragnar_agent.cli.demo || echo "
  [X] Algo fallo. Mandame una captura de esta ventana completa."

echo
read -r -p "  Presiona ENTER para cerrar... "
