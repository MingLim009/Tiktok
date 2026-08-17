#!/usr/bin/env bash
# Descarga la ultima version sin tocar los datos del cliente.
cd "$(dirname "$0")" || exit 1

echo
echo "=================================================================="
echo "  ACTUALIZAR EL PROGRAMA"
echo "=================================================================="
echo
echo "  Descarga la ultima version y reemplaza solo los archivos del"
echo "  programa."
echo
echo "  NO se toca nada tuyo:"
echo "    - tu clave de Claude (.env)"
echo "    - tu sesion de TikTok (no hay que volver a iniciar sesion)"
echo "    - el historial de conversaciones"
echo
read -r -p "  Presiona ENTER para continuar... "

URL="https://github.com/MingLim009/Tiktok/archive/refs/heads/main.zip"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo
echo "  Descargando..."
if ! curl -fsSL "$URL" -o "$TMP/v.zip"; then
    echo
    echo "  [X] No se pudo descargar. Revisa tu conexion a internet."
    echo "      Mientras tanto puedes seguir usando la version que tienes:"
    echo "      sigue funcionando igual."
    echo
    read -r -p "  Presiona ENTER para cerrar... "
    exit 1
fi

echo "  Descomprimiendo..."
if ! unzip -q -o "$TMP/v.zip" -d "$TMP"; then
    echo "  [X] El archivo descargado no se pudo abrir."
    read -r -p "  Presiona ENTER para cerrar... "
    exit 1
fi

RAIZ="$(find "$TMP" -maxdepth 1 -type d -name 'Tiktok-*' | head -1)"
if [ -z "$RAIZ" ]; then
    echo "  [X] El archivo descargado no tenia el contenido esperado."
    read -r -p "  Presiona ENTER para cerrar... "
    exit 1
fi

echo "  Reemplazando archivos del programa..."
# El punto final copia tambien los archivos que empiezan con punto.
cp -R "$RAIZ"/. .
chmod +x ./*.command ./*.sh 2>/dev/null

echo
echo "  Actualizado correctamente."
echo
echo "  Ahora abre  probar.command  para dejar todo listo."
echo
read -r -p "  Presiona ENTER para cerrar... "
