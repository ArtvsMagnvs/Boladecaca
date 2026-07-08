@echo off
REM backend\install_deps.bat — instalacion reproducible del venv de Aithera
REM
REM Problema raiz: psycopg2-binary==2.9.9 no tiene wheel precompilado para
REM Python 3.13 en Windows. Si pip revalua el grafo de deps completo (lo que
REM ocurre cuando hay paquetes sin instalar), intenta compilar psycopg2 desde
REM fuente y falla con LNK2001.
REM
REM Solucion: instalacion en tres pasadas.
REM   Pasada 1: --no-deps instala exactamente las versiones pineadas sin
REM             revalidar las transitivas. psycopg2-binary ya esta en el venv
REM             => "already satisfied", se salta sin intentar compilar.
REM   Pasada 2: faster-whisper se instala aparte (no esta pineado en
REM             requirements.txt — ver comentario en ese archivo).
REM   Pasada 3: reinstalacion forzada de pydantic-core por si el binario
REM             del venv esta corrupto (error "pydantic_core._pydantic_core
REM             ImportError" al lanzar pytest).
REM
REM Uso:
REM   cd backend
REM   python -m venv venv          (solo si el venv no existe todavia)
REM   venv\Scripts\activate
REM   install_deps.bat

echo.
echo ================================================
echo  Aithera — Instalacion de dependencias del backend
echo ================================================
echo.

echo [1/3] Instalando paquetes pineados (sin revalidar grafo de deps)...
pip install --no-deps -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR en pasada 1. Revisa requirements.txt y el estado del venv.
    pause
    exit /b 1
)
echo OK.

echo.
echo [2/3] Instalando faster-whisper con sus dependencias transitivas...
pip install faster-whisper==1.2.1
if errorlevel 1 (
    echo.
    echo AVISO: faster-whisper no se pudo instalar.
    echo El backend arranca igualmente; el endpoint /voice/transcribe
    echo devolvera 503 hasta que se instale manualmente.
) else (
    echo OK.
)

echo.
echo [3/3] Forzando reinstalacion de pydantic-core ^(arregla binario corrupto^)...
pip install --force-reinstall --no-cache-dir pydantic-core==2.46.4
if errorlevel 1 (
    echo.
    echo AVISO: reinstalacion de pydantic-core fallo. Puede que pytest
    echo siga fallando con ImportError. El backend en si no se ve afectado.
) else (
    echo OK.
)

echo.
echo ================================================
echo  Instalacion completada.
echo.
echo  Para arrancar el backend:
echo    python -m uvicorn app.main:app --reload --port 8000
echo.
echo  Para correr los tests:
echo    python -m pytest tests/ -v
echo ================================================
echo.
pause
