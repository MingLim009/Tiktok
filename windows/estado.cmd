@echo off
chcp 65001 >nul
title Estado del agente - Ragnar Capital
call "%~dp0_entorno.cmd" || exit /b 1

python -m ragnar_agent.cli.estado
echo.
pause
