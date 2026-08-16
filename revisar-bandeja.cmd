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

python -m ragnar_agent.cli.run_dm --una-vez
if errorlevel 1 (
    echo.
    echo   [X] Algo fallo.
    echo.
    echo       Si dice que no encuentra las conversaciones, haz doble clic
    echo       en  diagnostico.cmd  y mandame el archivo que genera.
)
echo.
pause
