@echo off
REM ============================================================================
REM Aithera Frontend (React + Electron) - Arranque robusto (V0.7)
REM - Detecta automaticamente el backend en puerto 8000
REM - LIBERA AUTOMATICAMENTE el puerto 5173 si esta ocupado (Vite)
REM - Instala dependencias si es la primera vez
REM - Lanza Electron + Vite dev server (npm run electron:dev)
REM
REM FIX V0.7.1 (definitivo): reescrito sin bloques "if ( ... )" porque cmd.exe
REM expande %var% al CARGAR el bloque y se confunde con caracteres especiales.
REM Usamos GOTOs (forma clasica y robusta de batch) en su lugar.
REM ============================================================================
title Aithera Frontend (V0.8)

cd /d "%~dp0"

echo.
echo ============================================================
echo        A I T H E R A   F R O N T E N D
echo                 Version 0.8.7
echo ------------------------------------------------------------
echo   Hub Visual 3D  .  Chat con voz (STT/TTS)
echo   Proyectos . Tareas . Calendario . Agentes
echo   Email Assistant  .  Centro de Voz  .  Memoria
echo   Electron + React + Vite + Three.js
echo ============================================================
echo.

REM --- Verificar que el backend esta corriendo ----------------------------
echo [1/4] Verificando backend en http://localhost:8000 ...
powershell -NoProfile -Command "try { (Invoke-WebRequest -Uri 'http://localhost:8000/' -UseBasicParsing -TimeoutSec 3).StatusCode } catch { exit 1 }" >nul 2>&1
if errorlevel 1 goto :BACKEND_DOWN
echo [OK] Backend respondiendo en puerto 8000.
goto :BACKEND_DONE

:BACKEND_DOWN
echo [WARN] El backend NO parece estar corriendo en puerto 8000.
echo         Es recomendable iniciarlo primero con:
echo             backend\iniciar_backend.bat
echo         Aun asi, intentaremos arrancar el frontend...

:BACKEND_DONE

REM --- Liberar puerto 5173 si esta ocupado (Vite) -------------------------
REM FIX V0.7.1: PowerShell directo sin $_ (cmd.exe rompe $_).
echo.
echo [2/4] Comprobando puerto 5173 (Vite)...
set "PORT_PIDS="
for /f "usebackq" %%p in (`powershell -NoProfile -Command "(Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue).OwningProcess -join ' '"`) do (
    set "PORT_PIDS=%%p"
)

if "%PORT_PIDS%"=="" goto :PORT_FREE_5173

echo [WARN] Puerto 5173 ocupado por PID: %PORT_PIDS%
echo [INFO] Liberando puerto automaticamente...
for %%p in (%PORT_PIDS%) do taskkill /F /PID %%p
timeout /t 2 /nobreak >nul
echo [OK] Puerto 5173 liberado.
goto :PORT_DONE_5173

:PORT_FREE_5173
echo [OK] Puerto 5173 libre.

:PORT_DONE_5173

REM --- Verificar Node y dependencias --------------------------------------
echo.
echo [3/4] Verificando Node.js y dependencias npm...
where node >nul 2>&1
if errorlevel 1 goto :NO_NODE
for /f "tokens=1" %%v in ('node --version') do echo [OK] Node %%v

cd frontend

if not exist "node_modules" goto :NO_NODE_MODULES
echo [OK] node_modules existe.
goto :CHECK_CONCURRENTLY

:NO_NODE_MODULES
echo.
echo Instalando dependencias npm ^(primera vez, puede tardar 1-2 min^)...
call npm install
if errorlevel 1 goto :NPM_FAIL

:CHECK_CONCURRENTLY
call npx --no-install concurrently --version >nul 2>&1
if errorlevel 1 goto :INSTALL_CONCURRENTLY
echo [OK] concurrently + wait-on disponibles.
goto :START_FRONTEND

:INSTALL_CONCURRENTLY
echo [WARN] concurrently no encontrado - instalando...
call npm install --save-dev concurrently wait-on electron electron-builder
if errorlevel 1 goto :NPM_FAIL
echo [OK] concurrently + wait-on disponibles.

REM --- Arranque del frontend ----------------------------------------------
:START_FRONTEND
echo.
echo [4/4] Iniciando Electron + Vite dev server...
echo       - Vite: http://localhost:5173
echo       - Backend API: http://localhost:8000
echo       (Pulsa Ctrl+C para detener)
echo.

call npm run electron:dev

if errorlevel 1 goto :FRONTEND_FAIL
goto :END

:NO_NODE
echo [ERROR] Node.js no encontrado en PATH.
echo         Descargalo de https://nodejs.org/ ^(v18 o superior^)
goto :PAUSE_END

:NPM_FAIL
echo [ERROR] Fallo la instalacion de dependencias. Revisa tu conexion.
goto :PAUSE_END

:FRONTEND_FAIL
echo.
echo [ERROR] El frontend finalizo con codigo de error.
goto :PAUSE_END

:PAUSE_END
pause

:END