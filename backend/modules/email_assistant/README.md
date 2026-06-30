# Email Executive Assistant V1 - Aithera

## Descripción

El Email Executive Assistant de Aithera es un asistente inteligente de correo electrónico y calendario que permite gestionar emails, reuniones, eventos y respuestas de forma conversacional.

## Características Principales

### 📧 Gmail Integration
- Autenticación OAuth 2.0 con Google
- Lectura y búsqueda de correos
- Clasificación automática por prioridad
- Generación de resúmenes inteligentes
- Envío de correos con aprobación
- Clasificación: CRÍTICO, IMPORTANTE, ACCIÓN REQUERIDA, INFORMATIVO, PROMOCIONAL, SPAM

### 📅 Calendar Integration
- Lectura de eventos de Google Calendar
- Creación de eventos desde emails
- Búsqueda de disponibilidad
- Detección de conflictos
- Recordatorios automáticos

### 🤖 Email Intelligence Engine
- Análisis de contenido con IA (Ollama)
- Extracción automática de fechas
- Detección de reuniones y eventos
- Identificación de acciones requeridas
- Generación de resúmenes contextuales

### 🗣️ Conversation Engine
- Mantenimiento de contexto conversacional
- Referencias como "el primero", "el último"
- Seguimiento de acciones pendientes
- Flujo de aprobación de respuestas

### 💾 Sistema de Memoria
- Registro de remitentes frecuentes
- Historial de interacciones
- Preferencias de usuario (horarios de reunión)
- Aprendizaje de estilos de respuesta

## Estructura del Módulo

```
modules/email_assistant/
├── __init__.py              # Punto de entrada del módulo
├── auth_manager.py          # Gestión de OAuth con Google
├── gmail_tool.py            # API de Gmail
├── calendar_tool.py         # API de Google Calendar
├── email_intelligence.py    # Motor de análisis con IA
├── conversation_engine.py   # Gestión de contexto conversacional
├── memory.py                # Sistema de memoria persistente
└── requirements.txt         # Dependencias adicionales
```

## Configuración

### 1. Credenciales OAuth

El archivo de configuración debe estar en:
```
backend/config/google_oauth.json
```

Formato:
```json
{
  "installed": {
    "client_id": "TU_CLIENT_ID",
    "project_id": "TU_PROJECT_ID",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "TU_CLIENT_SECRET",
    "redirect_uris": ["http://localhost"]
  }
}
```

### 2. Instalación de Dependencias

```bash
cd backend
pip install -m modules/email_assistant/requirements.txt
```

O manualmente:
```bash
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2 google-auth
```

## API Endpoints

### Autenticación
- `GET /api/email-assistant/auth/status` - Verificar estado de autenticación
- `POST /api/email-assistant/auth/login` - Iniciar sesión OAuth
- `POST /api/email-assistant/auth/logout` - Cerrar sesión

### Emails
- `GET /api/email-assistant/emails` - Listar emails (con filtros)
- `GET /api/email-assistant/emails/{id}` - Detalle de email
- `GET /api/email-assistant/emails/search/{query}` - Buscar emails
- `POST /api/email-assistant/emails/send` - Enviar email
- `POST /api/email-assistant/emails/{id}/mark-read` - Marcar como leído
- `POST /api/email-assistant/emails/{id}/archive` - Archivar

### Respuestas
- `POST /api/email-assistant/emails/response/generate` - Generar borrador
- `POST /api/email-assistant/emails/response/approve` - Aprobar y enviar

### Calendario
- `GET /api/email-assistant/calendar/events` - Listar eventos
- `POST /api/email-assistant/calendar/events` - Crear evento
- `GET /api/email-assistant/calendar/slots` - Buscar huecos disponibles

### Context & Memory
- `GET /api/email-assistant/context` - Estado actual de conversación
- `GET /api/email-assistant/memory/summary` - Resumen de memoria
- `POST /api/email-assistant/memory/preferences/{key}` - Actualizar preferencias

### Comandos de Voz
- `POST /api/email-assistant/voice/command` - Procesar comando de voz

## Uso en Desktop App

### Comandos de Voz Soportados

1. **Revisar emails**
   - "Revisa mis emails"
   - "Muéstrame correos importantes"
   
2. **Seleccionar email**
   - "Lee el primero"
   - "Abre el último"
   - "Busca correos de Amazon"
   
3. **Responder**
   - "Responde"
   - "Sí, envíalo"
   
4. **Calendario**
   - "Busca un hueco"
   - "Programa reunión"

### Flujo de Ejemplo

```
Usuario: "Revisa mis emails"
Aithera: "Tienes 3 correos importantes:
         - Escuela (de Juan)
         - Entrega Amazon (de Amazon)
         - Evento Blockchain (de María)
         ¿Cuál quieres revisar?"

Usuario: "Lee el de la escuela"
Aithera: "De: Juan García
         Asunto: Reunión de padres
         Resumen: La escuela solicita reunión el jueves.
         Acción: Confirmar asistencia.
         ¿Quieres responder?"

Usuario: "Sí"
Aithera: (Genera borrador con IA)
         "Aquí está mi propuesta de respuesta:
          Hola Juan,
          Confirmo mi asistencia a la reunión del jueves.
          ¿A qué hora es?
          Saludos"
         ¿Lo envío?"

Usuario: "Sí"
Aithera: "Correo enviado correctamente"
```

## Seguridad

### Confirmación Obligatoria
Todas las acciones sensibles requieren confirmación explícita:
- ✗ Enviar email (nunca automático)
- ✗ Archivar email
- ✗ Eliminar email
- ✗ Crear evento
- ✗ Modificar evento

### Almacenamiento de Tokens
- Tokens OAuth almacenados en: `backend/data/google/token.json`
- Tokens nunca se exponen en logs

## Comandos para Desarrollo

### Probar API manualmente

```bash
# Verificar autenticación
curl http://localhost:8000/api/email-assistant/auth/status

# Listar emails
curl http://localhost:8000/api/email-assistant/emails?filter_type=important

# Buscar disponibilidad
curl http://localhost:8000/api/email-assistant/calendar/slots?days=7
```

## Integración con Ollama

El Email Intelligence Engine utiliza Ollama para:
1. Generación de resúmenes naturales
2. Redacción de respuestas
3. Análisis contextual

Asegúrate de que Ollama esté ejecutándose:
```bash
ollama serve
```

## Troubleshooting

### Error: "No autenticado con Gmail"
1. Verificar que `config/google_oauth.json` existe
2. Ejecutar login desde la app
3. VerificarScopes de OAuth en Google Cloud Console

### Error: "Token expired"
1. El token se renueva automáticamente
2. Si falla, hacer logout y login de nuevo

### Error: "Ollama not available"
1. Verificar que Ollama está ejecutándose
2. Verificar variable OLLAMA_BASE_URL
3. El sistema funciona sin Ollama (modo básico)

## Próximas Funcionalidades

- [ ] Integración con calendario interno de Aithera
- [ ] Más agentes especializados
- [ ] Historial de conversaciones completo
- [ ] Plantillas de respuesta personalizables
- [ ] Notificaciones push

---

*Versión: 1.0.0*
*Fecha: 2024*
