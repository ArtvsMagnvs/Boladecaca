@echo off
cd /d "C:\Users\Alejandro\Desktop\CLAUDE\Aithera"
echo Commiteando el trabajo de voz...
echo.
git add backend/app/voice/whisper_stt.py backend/requirements.txt frontend/src/pages/Chat.tsx backend/tests/test_voice.py CLAUDE.md
git commit -m "feat(voice): STT en CPU + modelo small (mas preciso) + auto-envio; pin faster-whisper + mensaje de error accionable + tests de voz"
echo.
echo ================================================
echo   RESULTADO ARRIBA. Si dice 'master ...' fue OK.
echo ================================================
echo.
echo Puedes cerrar esta ventana. (Este .bat se puede borrar.)
pause
