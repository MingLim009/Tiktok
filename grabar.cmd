@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Grabacion de la demo - Ragnar Capital
mode con: cols=100 lines=32

REM ---------------------------------------------------------------
REM  Uso interno (no va en el paquete del cliente).
REM  Lanza la demo con 5 segundos de margen para darle a grabar.
REM ---------------------------------------------------------------

if not exist ".venv\Scripts\activate.bat" (
    echo.
    echo   Falta preparar el entorno ^(o quedo incompleto^).
    echo   Corre primero probar.cmd, que lo arma solo.
    echo.
    pause
    exit /b 1
)
call ".venv\Scripts\activate.bat"

set PYTHONPATH=src
set PYTHONIOENCODING=utf-8
set LOG_LEVEL=WARNING

cls
echo.
echo   TOMA 1 de 2 - Las tasas
echo   ----------------------------------------------------------
echo   Sugerencia: agranda la letra de esta ventana antes de seguir
echo   (Ctrl + rueda del raton).
echo.
pause

python -m ragnar_agent.cli.demo --tasas --esperar 5

echo.
echo   ----------------------------------------------------------
echo   TOMA 2 de 2 - La conversacion
echo.
echo   Mensajes para escribir, uno por uno:
echo      hola, a que hora atienden?
echo      quiero cambiar 5000 bolivianos a soles
echo      y si son 300 mil?
echo      me pueden llamar por telefono?
echo.
echo   Escribe 'salir' para terminar.
echo   ----------------------------------------------------------
pause

python -m ragnar_agent.cli.demo --esperar 5

echo.
echo   Grabacion terminada. Detén la captura.
echo.
pause
