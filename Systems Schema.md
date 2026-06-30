# Systems Schema - Aithera

## Descripción General
Aithera es un **Sistema Operativo de IA** que combina un backend FastAPI con una aplicación de escritorio Python, permitiendo gestión de proyectos, tareas, calendarios y chat con múltiples proveedores de IA.

---

## 1. Backend API (FastAPI)

### 1.1 Estructura de la API

#### Endpoint: `/api/config`
- **Propósito**: Gestión de configuración del sistema
- **Operaciones**: GET, PUT
- **Estado**: Implementado

#### Endpoint: `/api/projects`
- **Propósito**: CRUD completo de proyectos
- **Operaciones**:
  - `GET /` - Listar todos los proyectos
  - `POST /` - Crear nuevo proyecto
  - `PUT /{project_id}` - Actualizar proyecto
  - `DELETE /{project_id}` - Eliminar proyecto
- **Campos**: id, name, description, status, progress
- **Estado**: Implementado

#### Endpoint: `/api/tasks`
- **Propósito**: Gestión de tareas asociadas a proyectos
- **Operaciones**:
  - `GET /` - Listar todas las tareas
  - `POST /` - Crear nueva tarea
  - `PUT /{task_id}` - Actualizar tarea
  - `DELETE /{task_id}` - Eliminar tarea
- **Campos**: id, title, description, status, priority, project_id
- **Estado**: Implementado

#### Endpoint: `/api/calendar`
- **Propósito**: Sistema de calendario y eventos
- **Operaciones**:
  - `GET /events` - Listar eventos
  - `POST /events` - Crear evento
  - `GET /events/{event_id}` - Obtener evento específico
  - `PUT /events/{event_id}` - Actualizar evento
  - `DELETE /events/{event_id}` - Eliminar evento
- **Campos**: id, title, description, date, time, type
- **Estado**: Implementado

#### Endpoint: `/api/ai`
- **Propósito**: Gestión de proveedores de IA
- **Operaciones**:
  - `GET /providers` - Listar proveedores disponibles
  - `POST /chat` - Enviar mensaje al chat de IA
  - `GET /health` - Verificar estado del proveedor actual
  - `PUT /provider` - Cambiar proveedor de IA
- **Estado**: Implementado

#### Endpoint: `/api/chat`
- **Propósito**: Historial de conversaciones
- **Operaciones**: GET, POST
- **Estado**: Implementado

#### Endpoint: `/api/agents`
- **Propósito**: Sistema de agentes de IA especializados
- **Operaciones**:
  - `GET /` - Listar agentes
  - `POST /` - Interactuar con agente
  - `GET /{agent_name}` - Obtener agente específico
- **Estado**: Implementado

### 1.2 Modelos de Base de Datos (SQLite)

#### Config
- Almacena configuración global del sistema
- Campos: key, value

#### Project
- Proyectos del usuario
- Campos: id, name, description, status, progress, created_at

#### Task
- Tareas vinculadas a proyectos
- Campos: id, title, description, status, priority, project_id, created_at

#### CalendarEvent
- Eventos del calendario
- Campos: id, title, description, date, time, type, created_at

#### Conversation
- Historial de conversaciones
- Campos: id, message, response, timestamp

#### Agent
- Registro de agentes
- Campos: id, name, system_prompt, created_at

### 1.3 Sistema de IA (AI Manager)

#### Proveedores Soportados

1. **Ollama** (Local)
   - URL: http://localhost:11434
   - Modelo por defecto: llama3
   - Estado: Configurado por defecto

2. **OpenAI**
   - Requiere: OPENAI_API_KEY
   - Modelo por defecto: gpt-4

3. **Anthropic**
   - Requiere: ANTHROPIC_API_KEY
   - Modelo por defecto: claude-3-opus-20240229

#### Funcionalidades del AI Manager
- Cambio dinámico entre proveedores
- Chat asíncrono con system prompts
- Health check de proveedores
- Lista de proveedores disponibles

### 1.4 Sistema de Agentes

#### Architect Agent
- **Especialidad**: Arquitectura de software y diseño de sistemas
- **Capacidades**:
  - Diseño de arquitectura de aplicaciones
  - Patrones de diseño (MVC, microservices, event-driven)
  - Revisión de código y mejores prácticas
  - Planificación técnica de proyectos
- **Estado**: Implementado

---

## 2. Aplicación de Escritorio (CustomTkinter)

### 2.1 Interfaz Principal

#### Sidebar de Navegación
- Dashboard
- Chat
- Proyectos
- Tareas
- Calendario

#### Barra Superior
- Indicador de estado del backend
- Botón de voz
- Selector de proveedor de IA

### 2.2 Funcionalidades de Escritorio

#### 2.2.1 Asistente de Voz
- **TTS (Text-to-Speech)**: pyttsx3
- **STT (Speech-to-Text)**: speech_recognition con Google
- **Idioma**: Español (es-ES)
- **Funciones**:
  - `speak()` - Reproducir texto como voz
  - `listen()` - Escuchar entrada de voz
- **Estado**: Implementado (con fallback si no hay audio)

#### 2.2.2 Conexión con Backend
- URL: http://localhost:8000/api
- Verificación de estado del backend
- Actualización en tiempo real de estado
- Cola de mensajes para thread safety

#### 2.2.3 Dashboard
- Vista general del sistema
- Estado de conexiones
- Accesos rápidos

#### 2.2.4 Sección de Chat
- Interfaz de chat con IA
- Historial de mensajes
- Cambio de proveedor de IA
- Indicadores de carga

#### 2.2.5 Gestión de Proyectos (UI)
- Lista de proyectos
- Crear/editar/eliminar proyectos
- Barra de progreso
- Estados: active, completed, archived

#### 2.2.6 Gestión de Tareas (UI)
- Lista de tareas por proyecto
- Estados: pending, in_progress, completed
- Prioridades: low, medium, high

#### 2.2.7 Calendario (UI)
- Vista de eventos
- Crear/editar/eliminar eventos
- Tipos de evento configurables

### 2.3 Configuración de Apariencia
- Theme: Dark mode
- Color principal: #00d4ff (cyan)
- Frame sidebar: #111111
- CustomTkinter como framework UI

---

## 3. Email Executive Assistant V1

### 3.1 Descripción General
Asistente inteligente de correo electrónico y calendario con integración OAuth de Google, análisis con IA y comandos de voz.

**Ubicación**: `backend/modules/email_assistant/`

### 3.2 Gmail Tool

#### Funcionalidades
- Autenticación OAuth 2.0
- Listar emails (INBOX, con filtros)
- Búsqueda avanzada (Gmail query syntax)
- Leer emails completos
- Enviar emails
- Crear borradores
- Modificar etiquetas
- Archivar/Eliminar emails
- Descargar adjuntos

#### API Endpoints
- `GET /api/email-assistant/auth/status`
- `POST /api/email-assistant/auth/login`
- `POST /api/email-assistant/auth/logout`
- `GET /api/email-assistant/emails`
- `GET /api/email-assistant/emails/{id}`
- `GET /api/email-assistant/emails/search/{query}`
- `POST /api/email-assistant/emails/send`
- `POST /api/email-assistant/emails/{id}/archive`

### 3.3 Calendar Tool

#### Funcionalidades
- Listar eventos de Google Calendar
- Crear eventos
- Modificar eventos
- Eliminar eventos
- Buscar huecos disponibles
- Detectar conflictos
- Recordatorios

#### API Endpoints
- `GET /api/email-assistant/calendar/events`
- `POST /api/email-assistant/calendar/events`
- `GET /api/email-assistant/calendar/slots`

### 3.4 Email Intelligence Engine

#### Clasificación Automática
- **CRÍTICO**: Urgente, requiere atención inmediata
- **IMPORTANTE**: De remitentes importantes
- **ACCIÓN REQUERIDA**: Necesita respuesta
- **INFORMATIVO**: Solo para leer
- **PROMOCIONAL**: Ofertas y promociones
- **SPAM**: Correo no deseado

#### Extracción Automática
- Fechas mencionadas
- Reuniones y citas
- Eventos detectados
- Acciones requeridas
- Remitentes

#### Generación con IA (Ollama)
- Resúmenes naturales
- Respuestas sugeridas
- Análisis contextual

### 3.5 Conversation Engine

#### Gestión de Contexto
- Mantiene email actual seleccionado
- Referencias: "el primero", "el último", "número 3"
- Estados: IDLE, READING, COMPOSING, AWAITING_APPROVAL
- Historial de acciones

#### Flujo de Respuesta
1. Usuario solicita respuesta
2. IA genera borrador
3. Usuario revisa/modifica
4. Usuario aprueba
5. Email enviado

### 3.6 Sistema de Memoria

#### Información Guardada
- Remitentes frecuentes
- Historial de interacciones
- Acciones realizadas
- Preferencias horarias
- Estilos de respuesta

#### Ubicación
- `backend/data/email_memory/senders.json`
- `backend/data/email_memory/preferences.json`
- `backend/data/email_memory/history.json`
- `backend/data/email_memory/actions.json`

### 3.7 UI en Desktop App

#### Nueva Sección: Email Assistant
- Lista de emails importantes
- Panel de detalle
- Botones de acción
- Integración con voz

#### Comandos de Voz Soportados
- "Revisa mis emails"
- "Lee el primero"
- "Responde"
- "Programa reunión"
- "¿Cuántos correos importantes tengo?"

### 3.8 Seguridad

#### OAuth
- Credenciales en: `backend/config/google_oauth.json`
- Tokens en: `backend/data/google/token.json`

#### Confirmación Obligatoria
Nunca se ejecuta automáticamente:
- Envío de emails
- Archivar emails
- Crear eventos
- Eliminar eventos

---

## 4. Sistema de Logs

### 4.1 Propósito
Capturar y registrar errores del sistema para facilitar debugging durante desarrollo y testing.

### 4.2 Ubicación
- Backend: `backend/logs/system.log`
- Desktop: `logs/desktop.log`

### 4.3 Formato de Logs
```
[TIMESTAMP] [LEVEL] [MODULE] Message
- TIMESTAMP: YYYY-MM-DD HH:MM:SS
- LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL
- MODULE: Nombre del módulo que genera el log
- Message: Descripción del evento/error
```

### 4.4 Niveles de Log
- **DEBUG**: Información detallada para desarrollo
- **INFO**: Eventos normales del sistema
- **WARNING**: Situaciones inesperadas pero manejables
- **ERROR**: Errores que afectan funcionalidad
- **CRITICAL**: Fallos graves del sistema

---

## 5. Variables de Entorno

### Backend
```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
OPENAI_API_KEY=<tu_key>
OPENAI_MODEL=gpt-4
ANTHROPIC_API_KEY=<tu_key>
ANTHROPIC_MODEL=claude-3-opus-20240229
AI_PROVIDER=ollama
```

### Desktop
```
API_URL=http://localhost:8000/api
BACKEND_URL=http://localhost:8000
```

---

## 6. Dependencias

### Python (Backend)
- fastapi
- uvicorn
- sqlalchemy
- pydantic
- python-multipart
- httptools
- google-api-python-client
- google-auth-oauthlib

### Python (Desktop)
- customtkinter
- requests
- pyttsx3
- speech-recognition
- Pillow

---

## 7. Estado del Proyecto

### Completado
- Backend FastAPI con todos los endpoints
- Base de datos SQLite con modelos
- AI Manager con múltiples proveedores
- Desktop app con UI completa
- Sistema de logging
- Architect Agent
- Email Executive Assistant V1 (Gmail + Calendar)

### En Desarrollo
- Integración completa de agentes
- Mejoras en UI/UX
- Testing automatizado

### Pendiente
- Sistema de autenticación de usuarios
- Deploy en producción
- Documentación de API (Swagger)
- Tests unitarios

---

## 8. Estructura de Archivos

```
Aithera/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── desktop.py           # App de escritorio
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   └── architect.py     # Agente Architect
│   │   ├── ai/
│   │   │   ├── __init__.py
│   │   │   ├── ai_manager.py   # Gestor de IA
│   │   │   └── providers/
│   │   │       ├── __init__.py
│   │   │       ├── base.py
│   │   │       ├── ollama_provider.py
│   │   │       ├── openai_provider.py
│   │   │       └── anthropic_provider.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── endpoints/
│   │   │       ├── __init__.py
│   │   │       ├── config.py
│   │   │       ├── projects.py
│   │   │       ├── tasks.py
│   │   │       ├── calendar.py
│   │   │       ├── ai.py
│   │   │       ├── chat.py
│   │   │       └── agents.py
│   │   │       └── email_assistant.py  # Email Assistant API
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   └── logging_config.py  # Sistema de logs
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── database.py
│   │   │   ├── models.py
│   │   │   └── schemas.py
│   │   ├── email_ui.py          # UI del Email Assistant
│   ├── modules/
│   │   └── email_assistant/     # Email Executive Assistant
│   │       ├── __init__.py
│   │       ├── auth_manager.py
│   │       ├── gmail_tool.py
│   │       ├── calendar_tool.py
│   │       ├── email_intelligence.py
│   │       ├── conversation_engine.py
│   │       ├── memory.py
│   │       └── requirements.txt
│   ├── config/
│   │   └── google_oauth.json   # Credenciales OAuth
│   ├── data/
│   │   ├── google/             # Tokens OAuth
│   │   └── email_memory/        # Memoria del Email Assistant
│   ├── logs/                    # Sistema de logs
│   │   ├── system.log
│   │   └── errors.log
│   ├── aithera.db              # Base de datos SQLite
│   └── venv/                    # Ambiente virtual
└── Documentación/
    ├── Systems Schema.md
    └── Documentación de Desarrollo.md
```
