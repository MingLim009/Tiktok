#!/usr/bin/env bash
cd "$(dirname "$0")" || exit 1
# shellcheck disable=SC1091
source ./_entorno.sh || exit 1

clear
echo
echo "=================================================================="
echo "  ACTIVAR EL BOT - ENVIO REAL"
echo "=================================================================="
echo
echo "  ATENCION: esto SI le responde a tus clientes de verdad."
echo
echo "  Antes de seguir, asegurate de que:"
echo "    - Ya revisaste las respuestas con  5-Revisar-bandeja.command"
echo "    - Estas de acuerdo con el tono y las cotizaciones"
echo
echo "  Mientras esto este abierto, el bot revisa tu bandeja cada 45"
echo "  segundos y responde solo."
echo
echo "  Para detenerlo: cierra esta ventana, o presiona Control + C."
echo
echo "  IMPORTANTE: el bot solo funciona mientras esta ventana este"
echo "  abierta y la Mac encendida. Si la apagas o se suspende, deja de"
echo "  responder hasta que la vuelvas a abrir."
echo
echo "=================================================================="
echo
read -r -p "  Escribe  SI  para activarlo (o cierra la ventana): " RESPUESTA

if [ "$(printf '%s' "$RESPUESTA" | tr '[:lower:]' '[:upper:]')" != "SI" ]; then
    echo
    echo "  Cancelado. No se activo nada."
    echo
    read -r -p "  Presiona ENTER para cerrar... "
    exit 0
fi

export LOG_LEVEL=INFO
export DRY_RUN=false

clear
echo
echo "  BOT ACTIVO - respondiendo tu bandeja"
echo "  Para detenerlo: Control + C, o cierra esta ventana."
echo

python -m ragnar_agent.cli.run_dm --enviar

echo
echo "  El bot se detuvo."
echo
read -r -p "  Presiona ENTER para cerrar... "
