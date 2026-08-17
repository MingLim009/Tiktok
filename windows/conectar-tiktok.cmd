@echo off
chcp 65001 >nul
title Conectar TikTok - Ragnar Capital
call "%~dp0_entorno.cmd" || exit /b 1
set LOG_LEVEL=INFO

python -m ragnar_agent.cli.login
if errorlevel 1 (
    echo.
    echo   [X] No se pudo guardar la sesion. Vuelve a intentarlo, y si sigue
    echo       igual mandame una captura de esta ventana completa.
)
echo.
pause
