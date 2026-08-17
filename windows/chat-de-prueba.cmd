@echo off
chcp 65001 >nul
title Chat de prueba - Ragnar Capital
call "%~dp0_entorno.cmd" || exit /b 1
set LOG_LEVEL=INFO

python -m ragnar_agent.cli.servir --puerto 8080

echo.
pause
