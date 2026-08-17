#!/usr/bin/env bash
# ---------------------------------------------------------------------
#  Recoge informacion del equipo para poder ayudar sin adivinar.
#
#  A proposito NO usa Python ni nada instalado por el programa: tiene que
#  funcionar justamente cuando lo demas falla. Solo comandos que trae
#  cualquier Mac de fabrica.
# ---------------------------------------------------------------------
cd "$(dirname "$0")" || exit 1

INFORME="$(pwd)/AYUDA-mandar-esto.txt"

{
    echo "=================================================================="
    echo "  INFORME DE AYUDA - Agente de TikTok"
    echo "=================================================================="
    echo "  Fecha: $(date '+%d/%m/%Y %H:%M')"
    echo

    echo "--- Sistema ---"
    echo "  macOS: $(sw_vers -productVersion 2>/dev/null || echo 'desconocido')"
    echo "  Procesador: $(uname -m)"
    echo

    echo "--- Python ---"
    for c in python3 python; do
        if command -v "$c" >/dev/null 2>&1; then
            ruta="$(command -v "$c")"
            if "$c" -c "print('ok')" >/dev/null 2>&1; then
                echo "  $c: FUNCIONA  ($("$c" --version 2>&1)) en $ruta"
            else
                echo "  $c: PRESENTE PERO NO FUNCIONA en $ruta"
                echo "      (falta instalar las herramientas de desarrollador)"
            fi
        else
            echo "  $c: no esta"
        fi
    done
    if xcode-select -p >/dev/null 2>&1; then
        echo "  Herramientas de desarrollador: instaladas"
    else
        echo "  Herramientas de desarrollador: NO instaladas"
    fi
    echo

    echo "--- Internet ---"
    if curl -fsS -m 10 -o /dev/null https://pypi.org 2>/dev/null; then
        echo "  pypi.org: se alcanza"
    else
        echo "  pypi.org: NO se alcanza"
    fi
    if curl -fsS -m 10 -o /dev/null https://github.com 2>/dev/null; then
        echo "  github.com: se alcanza"
    else
        echo "  github.com: NO se alcanza"
    fi
    echo

    echo "--- Carpeta del programa ---"
    echo "  Ruta: $(pwd)"
    echo "  Archivos en la raiz:"
    ls -1 | sed 's/^/      /'
    echo
    echo "  Permisos de los programas:"
    ls -l ./*.command 2>/dev/null | awk '{print "      " $1 "  " $NF}' \
        || echo "      no se encontraron archivos .command"
    echo

    echo "--- Estado de la instalacion ---"
    if [ -f ".venv/bin/activate" ]; then
        echo "  Entorno: preparado"
    elif [ -d ".venv" ]; then
        echo "  Entorno: A MEDIAS (hay carpeta pero no esta completo)"
    else
        echo "  Entorno: sin preparar todavia"
    fi
    if [ -f ".env" ]; then
        if grep -q "REEMPLAZAR" ".env" 2>/dev/null; then
            echo "  Clave de Claude: el archivo existe pero sin clave puesta"
        else
            echo "  Clave de Claude: puesta"
        fi
    else
        echo "  Clave de Claude: sin configurar todavia"
    fi
    if [ -d ".session" ]; then
        echo "  Sesion de TikTok: guardada"
    else
        echo "  Sesion de TikTok: sin conectar todavia"
    fi
    echo
    echo "=================================================================="
} > "$INFORME" 2>&1

clear
cat "$INFORME"
echo
echo "  Se guardo este informe en tu carpeta, con el nombre:"
echo
echo "      AYUDA-mandar-esto.txt"
echo
echo "  Mandamelo por chat y con eso te digo exactamente que hacer."
echo
read -r -p "  Presiona ENTER para cerrar... "
