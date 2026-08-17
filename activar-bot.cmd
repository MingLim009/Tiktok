@echo off
chcp 65001 >nul
title BOT ACTIVO - Ragnar Capital
call "%~dp0_entorno.cmd" || exit /b 1

cls
echo.
echo ==================================================================
echo   ACTIVAR EL BOT - ENVIO REAL
echo ==================================================================
echo.
echo   ATENCION: esto SI le responde a tus clientes de verdad.
echo.
echo   Antes de seguir, asegurate de que:
echo     - Ya revisaste las respuestas con  revisar-bandeja.cmd
echo     - Estas de acuerdo con el tono y las cotizaciones
echo.
echo   Mientras esto este abierto, el bot revisa tu bandeja cada 45
echo   segundos y responde solo.
echo.
echo   Para detenerlo: cierra esta ventana, o presiona Ctrl + C.
echo.
echo   IMPORTANTE: el bot solo funciona mientras esta ventana este
echo   abierta y la computadora encendida. Si la apagas o se suspende,
echo   deja de responder hasta que la vuelvas a abrir.
echo.
echo ==================================================================
echo.
set /p RESPUESTA="   Escribe  SI  para activarlo (o cierra la ventana): "

if /i not "%RESPUESTA%"=="SI" (
    echo.
    echo   Cancelado. No se activo nada.
    echo.
    pause
    exit /b 0
)

set LOG_LEVEL=INFO
set DRY_RUN=false

cls
echo.
echo   BOT ACTIVO - respondiendo tu bandeja
echo   Para detenerlo: Ctrl + C, o cierra esta ventana.
echo.

python -m ragnar_agent.cli.run_dm --enviar

echo.
echo   El bot se detuvo.
echo.
pause
