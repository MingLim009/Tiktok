@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Agente TikTok - Ragnar Capital

echo.
echo ==================================================================
echo   AGENTE DE TIKTOK - RAGNAR CAPITAL
echo ==================================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo   [X] No se encontro Python en este equipo.
    echo.
    echo   Instalalo desde https://www.python.org/downloads/
    echo   IMPORTANTE: marca la casilla "Add Python to PATH" al instalar.
    echo.
    pause
    exit /b 1
)

REM  Se comprueba activate.bat, que es lo que realmente se usa mas abajo.
REM  Mirar solo python.exe no basta: un entorno a medias (instalacion
REM  interrumpida, antivirus, disco lleno) lo tiene pero no funciona, y
REM  el programa seguiria con el Python del sistema sin las librerias.
if not exist ".venv\Scripts\activate.bat" (
    if exist ".venv" (
        echo   El entorno quedo incompleto de un intento anterior.
        echo   Reconstruyendolo...
    ) else (
        echo   Preparando el entorno por primera vez.
        echo   Esto se demora un par de minutos. Solo pasa esta vez.
    )
    echo.
    python -m venv --clear .venv
    if errorlevel 1 goto sin_entorno
)

if not exist ".venv\Scripts\activate.bat" goto sin_entorno
call ".venv\Scripts\activate.bat"
if errorlevel 1 goto sin_entorno

REM  Comprobar que de verdad se esta usando el entorno y no el Python global.
for /f "delims=" %%P in ('python -c "import sys; print(sys.prefix)"') do set ENTORNO=%%P
echo %ENTORNO% | find /i "%CD%\.venv" >nul
if errorlevel 1 goto sin_entorno

REM  Instalar las librerias solo si falta alguna.
python -c "import yaml, requests, dotenv, anthropic" >nul 2>&1
if errorlevel 1 (
    echo   Instalando componentes...
    python -m pip install --quiet --upgrade pip
    python -m pip install --quiet -r requirements.txt
    if errorlevel 1 goto sin_librerias
    python -c "import yaml, requests, dotenv, anthropic" >nul 2>&1
    if errorlevel 1 goto sin_librerias
    echo   Listo.
    echo.
)

REM  Instalar el propio proyecto. Sin esto, los comandos solo funcionan
REM  dentro de esta ventana: al abrir otra fallan con "No module named
REM  ragnar_agent", que para el cliente es un error incomprensible.
python -c "import ragnar_agent" >nul 2>&1
if errorlevel 1 (
    python -m pip install --quiet -e . --no-deps
    if errorlevel 1 goto sin_librerias
)

set PYTHONIOENCODING=utf-8
set LOG_LEVEL=WARNING

echo   Consultando tus tasas de hoy...
echo.
python -m ragnar_agent.cli.demo --tasas
if errorlevel 1 goto error

echo.
echo ==================================================================
echo   Si arriba ves las tasas, el motor funciona correctamente.
echo.
echo   Para conversar con el bot escribe:
echo       python -m ragnar_agent.cli.demo
echo   (necesita la clave de Claude configurada en el archivo .env)
echo ==================================================================
echo.
cmd /k
exit /b 0

:sin_entorno
echo.
echo   [X] No se pudo preparar el entorno de Python.
echo.
echo   Prueba esto y mandame una captura de lo que salga:
echo       python -m venv --clear .venv
echo.
pause
exit /b 1

:sin_librerias
echo.
echo   [X] No se pudieron instalar los componentes.
echo       Suele ser falta de internet o el antivirus bloqueando la descarga.
echo.
echo   Mandame una captura de esta ventana completa.
echo.
pause
exit /b 1

:error
echo.
echo   [X] Algo fallo. Mandame una captura de esta ventana completa.
echo.
pause
exit /b 1
