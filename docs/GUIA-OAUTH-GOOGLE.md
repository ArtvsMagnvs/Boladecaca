# Guía de Autenticación OAuth - Email Assistant

## Cómo Conectar tu Cuenta de Google

### Paso 1: Abre la Desktop App
1. Ejecuta el archivo `iniciar_todo.bat` o:
   ```powershell
   cd c:\Users\Alejandro\Desktop\Aithera\backend
   python app\desktop.py
   ```

### Paso 2: Ve a Email Assistant
1. En el menú lateral izquierdo, haz clic en **"Email Assistant"**

### Paso 3: Haz clic en "Conectar Google"
1. Verás un botón azul **"Conectar Google"** en la parte superior
2. Haz clic en él

### Paso 4: Completa la Autenticación
1. Se abrirá tu navegador web predeterminado
2. Inicia sesión con tu cuenta de Google (si no lo estás)
3. Verás una página de permisos de Google:
   - **Ver tu correo electrónico principal**
   - **Ver y gestionar tu correo**
   - **Ver y gestionar tus eventos del calendario**
4. Haz clic en **"Permitir"**

### Paso 5: Espera la Confirmación
1. El navegador se redirigirá a una página de confirmación
2. La Desktop App mostrará "Conectado con Google" en verde
3. Los correos importantes se cargarán automáticamente

## Solución de Problemas

### El navegador no se abre
1. Verifica que tienes un navegador web instalado
2. Puedes copiar manualmente el URL que aparece en la consola del backend

### Error "Archivo de credenciales no encontrado"
1. Verifica que el archivo existe:
   ```
   c:\Users\Alejandro\Desktop\Aithera\backend\config\google_oauth.json
   ```

### Error de timeout
1. Asegúrate de tener buena conexión a internet
2. Verifica que los servidores de Google están accesibles
3. Intenta de nuevo

### Quiero desconectar mi cuenta
1. En Email Assistant, haz clic en el botón **"Desconectar"**
2. Para eliminar todos los datos, elimina:
   ```
   c:\Users\Alejandro\Desktop\Aithera\backend\data\google\token.json
   ```

## URLs de Consola (para debugging)

Si necesitas ver el estado del OAuth:

```powershell
# Verificar estado
curl http://localhost:8000/api/email-assistant/auth/status

# Iniciar login manualmente
curl -X POST http://localhost:8000/api/email-assistant/auth/login
```

## Permisos Solicitados

El Email Assistant solicita estos permisos de Google:

| Permiso | Descripción |
|---------|-------------|
| gmail.readonly | Ver tus correos |
| gmail.send | Enviar correos en tu nombre |
| gmail.modify | Marcar correos como leídos, archivar |
| calendar.readonly | Ver tu calendario |
| calendar.events | Crear eventos en tu calendario |

## Privacidad

- Las credenciales se almacenan localmente en `config/google_oauth.json`
- Los tokens se almacenan localmente en `data/google/token.json`
- Nunca se envían a servidores externos
- Puedes revocar el acceso en cualquier momento desde tu cuenta de Google

## Configuración de APIs en Google Cloud

Si necesitas configurar tus propias credenciales:

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un proyecto o selecciona uno existente
3. Habilita las APIs:
   - Gmail API
   - Google Calendar API
4. Crea credenciales OAuth 2.0 (Tipo: Aplicación de escritorio)
5. Descarga el archivo JSON y guárdalo como `google_oauth.json`

---

**¿Problemas?** Revisa los logs en `backend/logs/` para más detalles.
