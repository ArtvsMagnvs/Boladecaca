@echo off
REM ============================================================================
REM Aithera - Arranque de la aplicacion completa (V0.3)
REM
REM Antes este .bat lanzaba la version CustomTkinter (Python desktop
GUI)
REM que ya no se mantiene. Ahora lanza el frontend Electron+React
(Vite + React).
REM Asegurate de que el backend ya esta corriendo en otra ventana
(iniciar_backend.bat).
REM ============================================================================
title Aithera App (V0.3 - Electron)
setlocal

cd /d "%~dp0"

echo.
echo ============================================================
echo            A I T H E R A   A P P
echo                  Version 0.3.0
echo ============================================================
echo.

REM --- Verificar backend ----------------------------------------------------
echo Comprobando que el backend este corriendo en http://localhost:8000 ...
powershell -NoProfile -Command "try { (Invoke-WebRequest -Uri 'http://localhost:8000/health' -UseBasicParsing -TimeoutSec 3).StatusCode } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    echo [WARN] El backend no responde en localhost:8000.
    echo         Arranca primero el backend con iniciar_backend.bat
    echo         o iniciar_todo.bat para lanzar ambos a la vez.
    echo.
    pause
)

REM --- Lanzar frontend Electron+React ---------------------------------------
echo Iniciando frontend Electron+React...
cd ..
if exist "iniciar_frontend_react.bat" (
    call "iniciar_frontend_react.bat"
) else (
    echo [ERROR] No se encontro iniciar_frontend_react.bat
    pause
)

endlocal
