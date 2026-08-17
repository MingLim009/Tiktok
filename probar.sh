#!/usr/bin/env bash
# Agente de TikTok — Ragnar Capital
# Mac / Linux:  doble clic, o desde la terminal:  bash probar.sh
set -u
cd "$(dirname "$0")"

echo
echo "=================================================================="
echo "  AGENTE DE TIKTOK — RAGNAR CAPITAL"
echo "=================================================================="
echo

if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "  [X] No se encontró Python en este equipo."
    echo "      Instálalo desde https://www.python.org/downloads/"
    echo
    read -r -p "  Presiona ENTER para cerrar… "
    exit 1
fi

# Se comprueba el activate, que es lo que realmente se usa: un entorno a
# medias tiene el python pero no funciona, y seguiríamos con el Python del
# sistema, sin las librerías.
if [ ! -f ".venv/bin/activate" ]; then
    if [ -d ".venv" ]; then
        echo "  El entorno quedó incompleto de un intento anterior."
        echo "  Reconstruyéndolo…"
    else
        echo "  Preparando el entorno por primera vez."
        echo "  Esto se demora un par de minutos. Sólo pasa esta vez."
    fi
    echo
    "$PY" -m venv --clear .venv || { echo "  [X] No se pudo crear el entorno."; exit 1; }
fi

# shellcheck disable=SC1091
source .venv/bin/activate || { echo "  [X] No se pudo activar el entorno."; exit 1; }

if ! python -c "import yaml, requests, dotenv, anthropic" >/dev/null 2>&1; then
    echo "  Instalando componentes…"
    python -m pip install --quiet --upgrade pip
    python -m pip install --quiet -r requirements.txt || {
        echo "  [X] Falló la instalación. Suele ser falta de internet."; exit 1; }
    python -c "import yaml, requests, dotenv, anthropic" >/dev/null 2>&1 || {
        echo "  [X] Los componentes no quedaron bien instalados."; exit 1; }
    echo "  Listo."
    echo
fi

export PYTHONPATH=src
export PYTHONIOENCODING=utf-8
export LOG_LEVEL=WARNING

echo "  Consultando tus tasas de hoy…"
echo
python -m ragnar_agent.cli.demo --tasas || {
    echo
    echo "  [X] Algo falló. Mándame una captura de esta ventana completa."
    read -r -p "  Presiona ENTER para cerrar… "
    exit 1
}

echo
echo "=================================================================="
echo "  Si arriba ves las tasas, el motor funciona correctamente."
echo
echo "  Para conversar con el bot escribe:"
echo "      python -m ragnar_agent.cli.demo"
echo "  (necesita la clave de Claude configurada en el archivo .env)"
echo "=================================================================="
echo
exec "${SHELL:-bash}"
