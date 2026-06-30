# Primeros Pasos - Email Executive Assistant

## Instalación Rápida

### 1. Instalar Dependencias de Google API

```powershell
cd c:\Users\Alejandro\Desktop\Aithera\backend

# Activa el entorno virtual
.\venv\Scripts\activate

# Instala las dependencias del Email Assistant
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2 google-auth
```

### 2. Credenciales OAuth

Las credenciales de OAuth ya están configuradas en:
```
backend\config\google_oauth.json
```

**Nota**: Estas credenciales son para tu cuenta de Google Cloud Project. Asegúrate de que los scopes necesarios estén habilitados:
- https://www.googleapis.com/auth/gmail.readonly
- https://www.googleapis.com/auth/gmail.send
- https://www.googleapis.com/auth/gmail.modify
- https://www.googleapis.com/auth/calendar.readonly
- https://www.googleapis.com/auth/calendar.events

### 3. Iniciar el Backend

```powershell
cd c:\Users\Alejandro\Desktop\Aithera\backend
.\iniciar_backend.bat
```

O manualmente:
```powershell
cd c:\Users\Alejandro\Desktop\Aithera\backend
call venv\Scripts\activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Iniciar la Desktop App

```powershell
cd c:\Users\Alejandro\Desktop\Aithera\backend
python app\desktop.py
```

### 5. Autenticarse con Google

1. En la Desktop App, haz clic en **"Email Assistant"** en el menú lateral
2. Verás un mensaje de "No autenticado"
3. Haz clic en el mensaje para iniciar sesión
4. Se abrirá tu navegador web para completar el OAuth
5. Autoriza los permisos solicitados
6. Serás redirigido a localhost (el backend procesará el token automáticamente)

## Uso Básico

### Desde la Desktop App

1. **Ver correos importantes**
   - Ve a "Email Assistant"
   - Automáticamente se muestran correos CRÍTICO, IMPORTANTE y ACCIÓN REQUERIDA

2. **Leer un correo**
   - Haz clic en cualquier correo de la lista
   - Verás el resumen, fechas detectadas y acciones requeridas

3. **Responder un correo**
   - Selecciona un correo
   - Haz clic en "Responder"
   - Revisa el borrador generado
   - Haz clic en "Enviar" para aprobar

4. **Programar desde un correo**
   - Si se detectó una fecha, haz clic en "Programar"
   - El sistema buscará disponibilidad en tu calendario
   - Confirma la creación del evento

### Comandos de Voz

Di los siguientes comandos (asegurándote de que el micrófono esté activo):

- **"Revisa mis emails"** → Lista correos importantes
- **"Lee el primero"** → Muestra el primer correo
- **"Responde"** → Genera un borrador de respuesta
- **"Sí"** → Aprueba y envía
- **"Programa reunión"** → Busca disponibilidad

## Verificación

### Verificar que el backend está corriendo

```powershell
curl http://localhost:8000/health
```

Debería responder:
```json
{"status": "healthy"}
```

### Verificar autenticación

```powershell
curl http://localhost:8000/api/email-assistant/auth/status
```

Debería responder:
```json
{"authenticated": true, "message": "Autenticado con Google"}
```

### Verificar emails

```powershell
curl "http://localhost:8000/api/email-assistant/emails?filter_type=important"
```

## Solución de Problemas

### Error: "Module not found"

```powershell
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2 google-auth
```

### Error: "Token expired"

1. Haz logout y login de nuevo desde la app
2. O elimina `backend/data/google/token.json` y autentícate de nuevo

### Error: "Scopes not enabled"

Ve a Google Cloud Console > APIs y servicios > Biblioteca
Busca "Gmail API" y "Calendar API" y habilítalos

### Desktop App no muestra Email Assistant

Asegúrate de estar ejecutando la versión más reciente del desktop.py

## Archivos de Datos

| Archivo | Ubicación | Descripción |
|---------|-----------|-------------|
| Credenciales | `backend/config/google_oauth.json` | Client ID, Secret |
| Tokens | `backend/data/google/token.json` | Access/Refresh tokens |
| Memoria | `backend/data/email_memory/` | Historial, preferencias |
| Logs | `backend/logs/` | system.log, errors.log |

## Próximos Pasos

Una vez configurado, puedes:

1. Configurar preferencias de horarios de reunión
2. Entrenar al asistente con tus preferencias
3. Añadir etiquetas a contactos frecuentes
4. Personalizar el estilo de respuestas

---

**¿Necesitas ayuda?** Revisa `modules/email_assistant/README.md` para documentación completa.
