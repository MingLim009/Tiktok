#!/usr/bin/env bash
cd "$(dirname "$0")" || exit 1
# shellcheck disable=SC1091
source ./_entorno.sh || exit 1

clear
echo
echo "=================================================================="
echo "  REVISAR LA BANDEJA - MODO PRUEBA"
echo "=================================================================="
echo
echo "  Lee tus mensajes reales y muestra que RESPONDERIA a cada uno."
echo
echo "  NO se envia nada. Tus clientes no reciben ningun mensaje."
echo
echo "=================================================================="
echo

python -m ragnar_agent.cli.run_dm --una-vez --informe
codigo=$?

echo
case "$codigo" in
  0)
    echo "  Mandame el archivo  revision-bandeja.txt  que quedo en esta"
    echo "  misma carpeta, y te digo si esta listo para activarlo."
    ;;
  4)
    echo "  Ya quedo generado el archivo con el diagnostico. Mandamelo y yo"
    echo "  lo corrijo. No hace falta que hagas nada mas."
    ;;
  3)
    echo "  Parece que ya hay otra ventana del bot abierta. Cierrala y"
    echo "  vuelve a intentarlo."
    ;;
  2)
    echo "  Revisa el aviso de arriba: falta un dato de configuracion."
    echo "  Suele ser la clave de Claude en el archivo .env (paso 2)."
    ;;
  *)
    echo "  [X] Algo fallo. Mandame una captura de esta ventana completa."
    ;;
esac

echo
read -r -p "  Presiona ENTER para cerrar... "
