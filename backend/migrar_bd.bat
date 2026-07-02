@echo off
REM Aithera - aplicar migraciones de base de datos (Alembic)
REM Doble clic y listo. Usa el python del venv DIRECTAMENTE (sin activate,
REM que puede no propagar el PATH segun la config de Windows).
cd /d "%~dp0"

set PY=venv\Scripts\python.exe
if not exist %PY% set PY=venv311\Scripts\python.exe
if not exist %PY% (
    echo [ERROR] No encuentro el venv en venv\ ni venv311\. 
    echo Ejecuta esto manualmente en PowerShell:
    echo    .\venv\Scripts\python.exe -m alembic.config upgrade head
    pause
    exit /b 1
)

echo Usando: %PY%
%PY% -m alembic.config upgrade head
echo.
echo ============================================
echo  Version actual de la base de datos:
%PY% -m alembic.config current
echo ============================================
pause
