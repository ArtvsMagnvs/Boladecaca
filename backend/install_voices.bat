@echo off
chcp 65001 >nul
title Aithera - Instalar Voces Profesionales

echo ========================================
echo    INSTALAR VOCES PROFESIONALES
echo ========================================
echo.

echo Instalando voces profesionales de eSpeak NG...
echo.

REM Crear directorio de voces si no existe
if not exist "..\voces" mkdir "..\voces"

echo Descargando eSpeak NG portable...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/espeak-ng/espeak-ng/releases/download/1.51/espeak-ng-x64.zip' -OutFile 'espeak-ng.zip'" 2>nul

if exist "espeak-ng.zip" (
    echo Extrayendo...
    powershell -Command "Expand-Archive -Path 'espeak-ng.zip' -DestinationPath '..\voces\espeak-ng' -Force"
    del "espeak-ng.zip"
    echo.
    echo eSpeak NG instalado en ..\voces\espeak-ng
) else (
    echo Advertencia: No se pudo descargar eSpeak NG
)

echo.
echo ========================================
echo    VOCES DE WINDOWS DISPONIBLES
echo ========================================
echo.
echo Abriendo configuracion de Windows...
echo.

REM Abrir configuracion de Voz de Windows
start ms-settings:time-language

echo.
echo PASOS PARA INSTALAR VOCES EN WINDOWS:
echo.
echo 1. En la ventana de Configuracion que se abre:
echo    - Ve a "Hora e idioma" ^> "Voz"
echo    - Busca "Voces de Speech"
echo    - Haz clic en "Agregar voces"
echo.
echo 2. Idiomas disponibles para instalar:
echo    - Espanol (Espana y Mexico)
echo    - Ingles (US, UK, Australia, India)
echo    - Japones
echo    - Frances
echo    - Aleman
echo    - Italiano
echo    - Portugues
echo    - Chino
echo    - Coreano
echo    - Y muchos mas...
echo.
echo 3. Selecciona las voces que necesites y descargalas.
echo.
echo ========================================
echo    ELEVENLABS (OPCIONAL)
echo ========================================
echo.
echo Para voces IA profesionales ilimitadas:
echo.
echo 1. Ve a https://elevenlabs.io
echo 2. Crea cuenta gratuita (10,000 caracteres/mes gratis)
echo 3. Genera tu API Key en el perfil
echo 4. Crea el archivo .env en esta carpeta:
echo    echo ELEVENLABS_API_KEY=tu_key ^> .env
echo.

pause
