@echo off
REM Aithera - aplicar migraciones de base de datos (Alembic)
REM Doble clic y listo. Creado en Sprint 4b (PLAN_MAESTRO_2026).
cd /d "%~dp0"
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)
python -m alembic.config upgrade head
echo.
echo ============================================
echo  Migraciones aplicadas. Version actual:
python -m alembic.config current
echo ============================================
pause
