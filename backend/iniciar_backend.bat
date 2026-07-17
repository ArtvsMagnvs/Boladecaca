@echo off
REM ============================================================================
REM Aithera Backend - Script de arranque robusto (V0.7)
REM - Detecta automaticamente el venv correcto
REM - LIBERA AUTOMATICAMENTE el puerto 8000 si esta ocupado
REM   (era el bug que daba "[Errno 10048] address already in use")
REM - Activa el venv sin importar donde este (backend\venv o backend\venv311)
REM - Carga variables de entorno desde .env si existe
REM - Lanza uvicorn en http://localhost:8000
REM
REM FIX V0.7.1 (definitivo): reescrito sin bloques "if ( ... )" porque cmd.exe
REM expande %var% al CARGAR el bloque y se confunde con caracteres especiales.
REM Usamos GOTOs (forma clasica y robusta de batch) en su lugar.
REM ============================================================================
title Aithera Backend (V0.8)

cd /d "%~dp0"

echo.
echo ============================================================
echo              A I T H E R A   B A C K E N D
echo                       Version 0.9.2
echo ------------------------------------------------------------
echo   Chat IA multi-proveedor  .  Email + Calendar
echo   Agentes + Herramientas  .  Memoria semantica (ChromaDB)
echo   Voz: STT Whisper + TTS EdgeTTS/ElevenLabs/Kokoro/eSpeak
echo   Gateway multi-canal + Telegram  .  Seguridad DPAPI
echo ============================================================
echo.

REM --- Deteccion del Python del venv ----------------------------------------
set "PYTHON_EXE="
if exist "venv\Scripts\python.exe" set "PYTHON_EXE=%CD%\venv\Scripts\python.exe"
if "%PYTHON_EXE%"=="" if exist "venv311\Scripts\python.exe" set "PYTHON_EXE=%CD%\venv311\Scripts\python.exe"

if "%PYTHON_EXE%"=="" goto :NO_VENV

echo [OK] Python: %PYTHON_EXE%
"%PYTHON_EXE%" --version

REM --- Verificacion de dependencias criticas -------------------------------
echo.
echo Verificando dependencias...
"%PYTHON_EXE%" -c "import fastapi, uvicorn, sqlalchemy, httpx, pydantic" >nul 2>&1
if errorlevel 1 goto :NO_DEPS
echo [OK] Dependencias criticas instaladas.

REM --- Liberar puerto 8000 si esta ocupado (FIX BUG WinError 10048) -------
REM FIX V0.7.1: usamos PowerShell directo sin $_ (cmd.exe rompe $_).
REM "(...).OwningProcess -join ' '" devuelve todos los PIDs en una linea.
echo.
echo Comprobando puerto 8000...
set "PORT_PIDS="
for /f "usebackq" %%p in (`powershell -NoProfile -Command "(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue).OwningProcess -join ' '"`) do (
    set "PORT_PIDS=%%p"
)

if "%PORT_PIDS%"=="" goto :PORT_FREE

REM Hay PIDs que matar
echo [WARN] Puerto 8000 ocupado por PID: %PORT_PIDS%
echo [INFO] Liberando puerto automaticamente...
for %%p in (%PORT_PIDS%) do taskkill /F /PID %%p
REM Esperar a que Windows libere el socket
timeout /t 2 /nobreak >nul
echo [OK] Puerto 8000 liberado.
goto :PORT_DONE

:PORT_FREE
echo [OK] Puerto 8000 libre.
goto :PORT_DONE

:PORT_DONE

REM --- Carga de .env --------------------------------------------------------
if not exist ".env" goto :NO_ENV
echo.
echo Cargando configuracion desde .env...
for /f "usebackq tokens=1,* delims==" %%a in (`findstr /v /b "#" .env`) do (
    if not "%%a"=="" set "%%a=%%b"
)
echo [OK] Variables de entorno cargadas.
goto :ENV_DONE

:NO_ENV
echo [WARN] No existe .env - usando valores por defecto del codigo.
goto :ENV_DONE

:ENV_DONE

REM --- Apertura del navegador (best-effort, no bloqueante) -----------------
echo.
echo Abriendo navegador en http://localhost:8000/docs ...
start "" http://localhost:8000/docs 2>nul

REM --- Arranque de uvicorn --------------------------------------------------
echo.
echo Iniciando Aithera Backend en http://localhost:8000 ...
echo (Pulsa Ctrl+C para detener)
echo.

"%PYTHON_EXE%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000

if errorlevel 1 goto :UVICORN_FAIL
goto :END

:NO_VENV
echo [ERROR] No se encontro un venv valido.
echo         Esperado: %CD%\venv\Scripts\python.exe
echo         Crea el venv con: python -m venv venv
echo         E instala dependencias: venv\Scripts\pip install -r requirements.txt
goto :PAUSE_END

:NO_DEPS
echo [ERROR] Faltan dependencias. Ejecuta:
echo         "%PYTHON_EXE%" -m pip install -r requirements.txt
goto :PAUSE_END

:UVICORN_FAIL
echo.
echo [ERROR] uvicorn finalizo con codigo de error.
echo         Si el puerto sigue ocupado, ejecuta manualmente:
echo         netstat -ano ^| findstr ":8000"
echo         taskkill /F /PID ^<numero^>
goto :PAUSE_END

:PAUSE_END
pause

:END