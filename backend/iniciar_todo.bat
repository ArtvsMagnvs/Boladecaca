@echo off
title Aithera
cd /d "%~dp0"

echo =====================================
echo        AI T H E R A
echo =====================================
echo.

REM Start backend in a new window
start "Aithera Backend" cmd /c "cd /d \"%~dp0\" && venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo Esperando que el backend inicie...
timeout /t 3 /nobreak > nul

REM Start desktop app
start "Aithera Desktop" cmd /c "cd /d \"%~dp0\" && venv\Scripts\activate.bat && python app\desktop.py"
