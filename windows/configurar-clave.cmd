@echo off
chcp 65001 >nul
title Configurar la clave de Claude - Ragnar Capital
call "%~dp0_entorno.cmd" || exit /b 1

python -m ragnar_agent.cli.configurar

echo.
pause
