@echo off
chcp 65001 >nul
cd /d "%~dp0.."
title Actualizar el programa - Ragnar Capital

echo.
echo ==================================================================
echo   ACTUALIZAR EL PROGRAMA
echo ==================================================================
echo.
echo   Descarga la ultima version y reemplaza solo los archivos del
echo   programa.
echo.
echo   NO se toca nada tuyo:
echo     - tu clave de Claude ^(.env^)
echo     - tu sesion de TikTok ^(no hay que volver a iniciar sesion^)
echo     - el historial de conversaciones
echo.
pause

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$url='https://github.com/MingLim009/Tiktok/archive/refs/heads/main.zip';" ^
  "$tmp=Join-Path $env:TEMP ('rc_upd_' + [guid]::NewGuid().ToString('N'));" ^
  "try {" ^
  "  New-Item -ItemType Directory -Path $tmp -Force | Out-Null;" ^
  "  Write-Host '  Descargando...';" ^
  "  Invoke-WebRequest -Uri $url -OutFile (Join-Path $tmp 'v.zip') -UseBasicParsing -TimeoutSec 120;" ^
  "  Write-Host '  Descomprimiendo...';" ^
  "  Expand-Archive -Path (Join-Path $tmp 'v.zip') -DestinationPath $tmp -Force;" ^
  "  $raiz = Get-ChildItem $tmp -Directory | Select-Object -First 1;" ^
  "  if (-not $raiz) { throw 'El archivo descargado no tenia el contenido esperado.' }" ^
  "  Write-Host '  Reemplazando archivos del programa...';" ^
  "  Copy-Item (Join-Path $raiz.FullName '*') -Destination '%CD%' -Recurse -Force;" ^
  "  Write-Host '';" ^
  "  Write-Host '  Actualizado correctamente.' -ForegroundColor Green;" ^
  "} catch {" ^
  "  Write-Host '';" ^
  "  Write-Host ('  [X] No se pudo actualizar: ' + $_.Exception.Message) -ForegroundColor Red;" ^
  "  exit 1;" ^
  "} finally {" ^
  "  if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue }" ^
  "}"

if errorlevel 1 (
    echo.
    echo   Mandame una captura de esta ventana y lo reviso.
    echo.
    echo   Mientras tanto puedes seguir usando la version que ya tienes:
    echo   sigue funcionando igual.
    echo.
    pause
    exit /b 1
)

echo.
echo   Ahora haz doble clic en  probar.cmd  para dejar todo listo.
echo.
pause
