@echo off
chcp 65001 >nul
title Diagnostico de la bandeja - Ragnar Capital
call "%~dp0_entorno.cmd" || exit /b 1
set LOG_LEVEL=INFO

cls
echo.
echo   Revisando como se ve tu bandeja...
echo.

python -m ragnar_agent.cli.run_dm --diagnostico

echo.
echo ==================================================================
echo   Mandame el archivo  diagnostico_bandeja.txt  que quedo en esta
echo   misma carpeta. Con eso ubico que hay que corregir.
echo ==================================================================
echo.
pause
