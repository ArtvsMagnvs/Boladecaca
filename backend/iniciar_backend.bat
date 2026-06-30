@echo off
title Aithera Backend
cd /d "%~dp0"
echo Iniciando Aithera Backend...
call venv\Scripts\activate.bat
echo.
echo Abriendo navegador en http://localhost:8000/docs ...
start http://localhost:8000/docs
echo.
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
