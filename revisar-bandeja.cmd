@echo off
chcp 65001 >nul
title Revisar bandeja (modo prueba) - Ragnar Capital
call "%~dp0_entorno.cmd" || exit /b 1

cls
echo.
echo ==================================================================
echo   REVISAR LA BANDEJA - MODO PRUEBA
echo ==================================================================
echo.
echo   Lee tus mensajes reales y muestra que RESPONDERIA a cada uno.
echo.
echo   NO se envia nada. Tus clientes no reciben ningun mensaje.
echo.
echo ==================================================================
echo.

python -m ragnar_agent.cli.run_dm --una-vez --informe

REM  Los codigos vienen de run_dm: 4 = no se pudo leer la bandeja (ya dejo
REM  el diagnostico hecho), 3 = otro bot abierto, 2 = falta configuracion.
if errorlevel 4 goto sin_bandeja
if errorlevel 3 goto otro_abierto
if errorlevel 2 goto sin_config
if errorlevel 1 goto error

echo   Mandame el archivo  revision-bandeja.txt  que quedo en esta
echo   misma carpeta, y te digo si esta listo para activarlo.
echo.
pause
exit /b 0

:sin_bandeja
echo.
echo   Ya quedo generado el archivo con el diagnostico. Mandamelo y yo
echo   lo corrijo. No hace falta que hagas nada mas.
echo.
pause
exit /b 0

:otro_abierto
echo.
echo   Parece que ya hay otra ventana del bot abierta. Cierrala y vuelve
echo   a intentarlo.
echo.
pause
exit /b 0

:sin_config
echo.
echo   Revisa el aviso de arriba: falta un dato de configuracion.
echo   Suele ser la clave de Claude en el archivo .env ^(paso 2^).
echo.
pause
exit /b 0

:error
echo.
echo   [X] Algo fallo. Mandame una captura de esta ventana completa.
echo.
pause
exit /b 1
echo.
pause
