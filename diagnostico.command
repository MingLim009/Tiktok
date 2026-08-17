#!/usr/bin/env bash
cd "$(dirname "$0")" || exit 1
# shellcheck disable=SC1091
source ./_entorno.sh || exit 1
export LOG_LEVEL=INFO

clear
echo
echo "  Revisando como se ve tu bandeja..."
echo

python -m ragnar_agent.cli.run_dm --diagnostico

echo
echo "=================================================================="
echo "  Mandame el archivo  diagnostico_bandeja.txt  que quedo en esta"
echo "  misma carpeta. Con eso ubico que hay que corregir."
echo "=================================================================="
echo
read -r -p "  Presiona ENTER para cerrar... "
