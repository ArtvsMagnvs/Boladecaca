@echo off
REM ============================================================================
REM Aithera - Arranque completo (V0.3)
REM Lanza el backend Y el frontend Electron+React en ventanas separadas.
REM Espera unos segundos entre ambos para que el backend este listo.
REM ============================================================================
title Aithera Launcher (V0.3)
setlocal

cd /d "%~dp0"

echo.
echo ============================================================
echo           A I T H E R A   -   L A U N C H E R
echo                       Version 0.8.5
echo ============================================================
echo.
echo Iniciando backend y frontend Electron...
echo Cierra esta ventana para detener ambos procesos.
echo.

REM --- Backend en ventana separada ------------------------------------------
echo [1/2] Iniciando Aithera Backend...
start "Aithera Backend (V0.3)" cmd /c "iniciar_backend.bat"

REM --- Espera para que el backend este listo -------------------------------
echo Esperando 5 segundos para que el backend este listo...
timeout /t 5 /nobreak > nul

REM --- Frontend Electron+React en otra ventana ----------------------------
echo [2/2] Iniciando frontend Electron...
cd ..
if exist "iniciar_frontend_react.bat" (
    start "Aithera Frontend (Electron)" cmd /c "iniciar_frontend_react.bat"
) else (
    echo [ERROR] No se encontro iniciar_frontend_react.bat en %CD%
)

echo.
echo Backend y frontend lanzados en ventanas separadas.
echo Puedes cerrar las ventanas individualmente cuando termines.
echo.
pause

endlocal
