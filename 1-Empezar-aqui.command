#!/usr/bin/env bash
# Ragnar Capital - preparar el programa y ver las tasas (Mac)
cd "$(dirname "$0")" || exit 1

echo
echo "=================================================================="
echo "  AGENTE DE TIKTOK - RAGNAR CAPITAL"
echo "=================================================================="
echo

# OJO: no basta con que python3 EXISTA. macOS trae un stub en /usr/bin/python3
# que aparece como instalado pero, si faltan las Command Line Tools, al
# ejecutarlo abre un dialogo y no hace nada. Por eso se comprueba que de
# verdad corra, no que este presente.
PY=""
for candidato in python3 python; do
    if command -v "$candidato" >/dev/null 2>&1; then
        if "$candidato" -c "print('ok')" >/dev/null 2>&1; then
            PY="$candidato"
            break
        fi
    fi
done

if [ -z "$PY" ]; then
    echo "  [X] Falta Python en esta Mac, o esta a medio instalar."
    echo
    echo "  ES NORMAL: muchas Mac no lo traen listo para usar."
    echo
    echo "  Tienes dos opciones. La primera es la mas simple:"
    echo
    echo "  OPCION 1 - Descargarlo (recomendada)"
    echo "     1. Entra a  https://www.python.org/downloads/"
    echo "     2. Pulsa el boton amarillo grande que dice"
    echo "        'Download Python' "
    echo "     3. Abre el archivo descargado y sigue el instalador"
    echo "        dandole a Continuar en todo"
    echo "     4. Cuando termine, vuelve a abrir este mismo archivo"
    echo
    echo "  OPCION 2 - Dejar que macOS lo instale"
    echo "     Se te habra abierto una ventana preguntando si quieres"
    echo "     instalar las herramientas para desarrolladores. Dale a"
    echo "     'Instalar', espera a que termine, y vuelve a abrir este"
    echo "     archivo."
    echo
    echo "  Si te complica, abre  Ayuda.command  y mandame lo que salga:"
    echo "  con eso te digo exactamente que hacer."
    echo
    read -r -p "  Presiona ENTER para cerrar... "
    exit 1
fi

# Se comprueba el activate, que es lo que realmente se usa: un entorno a
# medias tiene el python pero no funciona.
if [ ! -f ".venv/bin/activate" ]; then
    if [ -d ".venv" ]; then
        echo "  El entorno quedo incompleto de un intento anterior."
        echo "  Reconstruyendolo..."
    else
        echo "  Preparando el entorno por primera vez."
        echo "  Esto se demora un par de minutos. Solo pasa esta vez."
    fi
    echo
    "$PY" -m venv --clear .venv || {
        echo "  [X] No se pudo crear el entorno."
        read -r -p "  Presiona ENTER para cerrar... "; exit 1; }
fi

# shellcheck disable=SC1091
source .venv/bin/activate || {
    echo "  [X] No se pudo activar el entorno."
    read -r -p "  Presiona ENTER para cerrar... "; exit 1; }

if ! python -c "import yaml, requests, dotenv, anthropic" >/dev/null 2>&1; then
    echo "  Instalando componentes..."
    python -m pip install --quiet --upgrade pip
    python -m pip install --quiet -r requirements.txt || {
        echo "  [X] Fallo la instalacion. Suele ser falta de internet."
        read -r -p "  Presiona ENTER para cerrar... "; exit 1; }
fi

# Instalar el propio proyecto: sin esto los comandos solo funcionan en
# esta ventana y al abrir otra fallan con "No module named ragnar_agent".
if ! python -c "import ragnar_agent" >/dev/null 2>&1; then
    python -m pip install --quiet -e . --no-deps || {
        echo "  [X] No se pudo instalar el programa."
        read -r -p "  Presiona ENTER para cerrar... "; exit 1; }
fi

# El navegador que usa el bot para la bandeja.
python -m playwright install chromium >/dev/null 2>&1

export PYTHONIOENCODING=utf-8
export LOG_LEVEL=WARNING

# La clave se pide aca mismo, en esta ventana. Hacerle editar un archivo
# oculto no funciona: el Finder no lo muestra.
python -m ragnar_agent.cli.configurar

echo
echo "  Consultando tus tasas de hoy..."
echo
python -m ragnar_agent.cli.demo --tasas || {
    echo
    echo "  [X] Algo fallo. Mandame una captura de esta ventana completa."
    read -r -p "  Presiona ENTER para cerrar... "; exit 1; }

echo
echo "=================================================================="
echo "  Si arriba ves tus tasas, el motor funciona correctamente."
echo "=================================================================="
echo
read -r -p "  Presiona ENTER para cerrar... "
