@echo off
title Aithera Desktop
cd /d "%~dp0"
echo Iniciando Aithera Desktop...
call venv\Scripts\activate.bat
python app\desktop.py
