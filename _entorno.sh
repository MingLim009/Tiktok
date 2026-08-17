#!/usr/bin/env bash
# ---------------------------------------------------------------------
#  Prepara el entorno en Mac / Linux.
#  No se ejecuta solo: lo cargan los demas con  source _entorno.sh
# ---------------------------------------------------------------------

cd "$(dirname "${BASH_SOURCE[0]}")" || exit 1

if [ ! -f ".venv/bin/activate" ]; then
    echo
    echo "  [X] Todavia no esta preparado el programa."
    echo
    echo "      Abre primero:  1-Empezar-aqui.command"
    echo "      Eso lo deja listo. Despues vuelve a abrir este."
    echo
    read -r -p "  Presiona ENTER para cerrar... "
    exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate || {
    echo "  [X] No se pudo preparar el entorno. Vuelve a abrir 1-Empezar-aqui.command"
    read -r -p "  Presiona ENTER para cerrar... "
    exit 1
}

if ! python -c "import ragnar_agent" >/dev/null 2>&1; then
    python -m pip install --quiet -e . --no-deps >/dev/null 2>&1
    if ! python -c "import ragnar_agent" >/dev/null 2>&1; then
        echo "  [X] Falta instalar el programa. Vuelve a abrir 1-Empezar-aqui.command"
        read -r -p "  Presiona ENTER para cerrar... "
        exit 1
    fi
fi

export PYTHONIOENCODING=utf-8
export LOG_LEVEL=WARNING
