@echo off
REM ---------------------------------------------------------------------
REM  Prepara el entorno. No se ejecuta solo: lo llaman los demas .cmd.
REM ---------------------------------------------------------------------
cd /d "%~dp0.."

if not exist ".venv\Scripts\activate.bat" (
    echo.
    echo   [X] Todavia no esta preparado el programa.
    echo.
    echo       Haz doble clic primero en:  probar.cmd
    echo       Eso lo deja listo. Despues vuelve a abrir este.
    echo.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo   [X] No se pudo preparar el entorno. Vuelve a correr probar.cmd
    pause
    exit /b 1
)

python -c "import ragnar_agent" >nul 2>&1
if errorlevel 1 (
    python -m pip install --quiet -e . --no-deps >nul 2>&1
    python -c "import ragnar_agent" >nul 2>&1
    if errorlevel 1 (
        echo   [X] Falta instalar el programa. Vuelve a correr probar.cmd
        pause
        exit /b 1
    )
)

set PYTHONIOENCODING=utf-8
set LOG_LEVEL=WARNING
exit /b 0
