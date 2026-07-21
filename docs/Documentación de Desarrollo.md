# Documentación de Desarrollo - Aithera

## Tabla de Contenidos
1. [Historia del Proyecto](#historia-del-proyecto)
2. [Fases de Desarrollo](#fases-de-desarrollo)
3. [Decisiones Técnicas](#decisiones-técnicas)
4. [Problemas Conocidos](#problemas-conocidos)
5. [Configuración Actual](#configuración-actual)
6. [Cómo Continuar](#cómo-continuar)

---

## Historia del Proyecto

### Inicio (Fecha de creación: 2024)
Aithera nació como un proyecto para crear un **Sistema Operativo de IA** que combinara:
- Un backend robusto con FastAPI
- Una aplicación de escritorio intuitiva
- Integración con múltiples proveedores de IA
- Gestión de proyectos y tareas

### Visión Original
Crear una aplicación que funcione como un asistente de IA completo, capaz de:
- Gestionar proyectos de desarrollo
- Organizar tareas y calendario
- Mantener conversaciones contextuales
- Proporcionar asistencia especializada mediante agentes

---

## Fases de Desarrollo

### Fase 1: Fundamentos del Backend ✅
**Estado**: Completado

**Objetivos logrados**:
- Creación de la estructura FastAPI
- Configuración de CORS para permitir conexiones
- Sistema de lifespan para inicialización/limpieza
- Endpoints básicos de salud del sistema

**Archivos creados**:
- `backend/app/main.py` - Aplicación principal FastAPI
- `backend/app/core/config.py` - Configuración centralizada

**Lecciones aprendidas**:
- Importancia del lifespan management para recursos
- CORS debe permitir conexiones del desktop app

### Fase 2: Base de Datos ✅
**Estado**: Completado

**Modelos implementados**:
- Config (clave-valor)
- Project (proyectos)
- Task (tareas)
- CalendarEvent (eventos)
- Conversation (conversaciones)
- Agent (agentes)

**Tecnología**: SQLite con SQLAlchemy ORM

**Decisiones**:
- SQLite para simplicidad y portabilidad
- SQLAlchemy para abstracción de base de datos
- Modelos separados en `models.py`, schemas en `schemas.py`

### Fase 3: API Endpoints ✅
**Estado**: Completado

**Endpoints creados**:
1. `/api/config` - Configuración del sistema
2. `/api/projects` - CRUD de proyectos
3. `/api/tasks` - CRUD de tareas
4. `/api/calendar` - Sistema de eventos
5. `/api/chat` - Historial de chat
6. `/api/ai` - Gestión de IA
7. `/api/agents` - Sistema de agentes

**Patrón utilizado**: Router con prefijo `/api`

### Fase 4: Sistema de IA ✅
**Estado**: Completado

**Componentes**:
- AI Manager centralizado
- Provider base abstracto
- Implementaciones específicas:
  - Ollama (local)
  - OpenAI
  - Anthropic

**Arquitectura**:
- Pattern: Provider Strategy
- Permite cambiar proveedor sin modificar código cliente
- Health checks para cada proveedor

**Proveedor por defecto**: Ollama con modelo llama3

### Fase 5: Agentes de IA ✅
**Estado**: Parcialmente completado

**Agente implementado**:
- **Architect Agent**
  - Especialidad: Arquitectura de software
  - Sistema de prompts especializado
  - Capacidades de revisión de código

**Arquitectura planeada**:
- Base Agent class
- Specialized agents (Architect, Coder, Tester, etc.)
- Tool integration para cada agente

### Fase 6: Aplicación de Escritorio ✅
**Estado**: Completado con mejoras pendientes

**Framework**: CustomTkinter (Tkinter modernizado)

**Funcionalidades implementadas**:
- UI con sidebar de navegación
- Conexión con backend API
- Asistente de voz (TTS + STT)
- Secciones:
  - Dashboard
  - Chat
  - Proyectos
  - Tareas
  - Calendario

**Problemas resueltos**:
- Thread safety con cola de mensajes
- Fallback cuando voz no está disponible
- Verificación de estado del backend

### Fase 7: Sistema de Logs ✅
**Estado**: Implementado

**Módulo**: `backend/app/core/logging_config.py`

**Archivos de log**:
- `backend/logs/system.log` - Eventos generales
- `backend/logs/errors.log` - Solo errores

**Funcionalidades**:
- Rotación automática (5MB máx, 3 backups)
- Exception handler global en FastAPI
- Funciones helper: log_info, log_error, etc.
- Integración en startup/shutdown

### Fase 8: Email Executive Assistant ✅
**Estado**: Implementado

**Fecha de implementación**: 2024

**Visión**: Asistente de correo electrónico inteligente con Gmail y Calendar integration

**Componentes implementados**:

1. **OAuth Authentication** (`modules/email_assistant/auth_manager.py`)
   - Flujo OAuth 2.0 con Google
   - Renovación automática de tokens
   - Almacenamiento seguro en `data/google/token.json`

2. **Gmail Tool** (`modules/email_assistant/gmail_tool.py`)
   - CRUD completo de emails
   - Búsqueda avanzada
   - Envío con confirmación obligatoria
   - Clasificación automática por prioridad

3. **Calendar Tool** (`modules/email_assistant/calendar_tool.py`)
   - Integración con Google Calendar
   - Creación de eventos
   - Búsqueda de disponibilidad
   - Detección de conflictos

4. **Email Intelligence Engine** (`modules/email_assistant/email_intelligence.py`)
   - Clasificación: CRÍTICO, IMPORTANTE, ACCIÓN REQUERIDA, etc.
   - Extracción de fechas y eventos
   - Detección de acciones requeridas
   - Generación de resúmenes con Ollama
   - Redacción de respuestas con IA

5. **Conversation Engine** (`modules/email_assistant/conversation_engine.py`)
   - Mantenimiento de contexto
   - Referencias: "el primero", "el último", etc.
   - Estados de conversación
   - Flujo de aprobación

6. **Email Memory** (`modules/email_assistant/memory.py`)
   - Registro de remitentes frecuentes
   - Historial de interacciones
   - Preferencias de usuario
   - Aprendizaje de estilos

7. **UI Integration** (`app/email_ui.py`)
   - Nueva sección en Desktop App
   - Lista de emails importantes
   - Panel de detalle
   - Integración con voz

8. **API Endpoints** (`app/api/endpoints/email_assistant.py`)
   - Endpoints REST completos
   - Procesamiento de comandos de voz
   - Gestión de contexto

**Credenciales OAuth**:
- Ubicación: `backend/config/google_oauth.json`
- Credenciales del usuario ya configuradas

**Dependencias agregadas**:
- google-api-python-client
- google-auth-oauthlib
- google-auth-httplib2
- google-auth

**Decisiones técnicas**:
- OAuth Desktop App flow para evitar servidor web
- Tokens offline para acceso sin interacción constante
- Confirmación obligatoria para todas las acciones sensibles
- Fallback a análisis básico si Ollama no disponible

**Problemas resueltos durante implementación**:
- Flujo OAuth compatible con desktop apps
- Manejo de timeouts en APIs de Google
- Sincronización de estado entre componentes

---

## Decisiones Técnicas

### 1. FastAPI sobre Flask
**Razón**: Mejor rendimiento async, validación automática con Pydantic, documentación Swagger automática

### 2. SQLite sobre PostgreSQL/MySQL
**Razón**: Portabilidad, zero-config, suficiente para uso local

### 3. CustomTkinter sobre PyQt/PySide
**Razón**: Simplicidad, mejor integración con Tkinter existente, theme dark moderno

### 4. Ollama como default
**Razón**: Privacidad, no requiere API keys, funciona offline

### 5. Provider Strategy para IA
**Razón**: Flexibilidad para cambiar entre proveedores, fácil adición de nuevos

---

## Problemas Conocidos

### 1. Fallback de Voz
**Descripción**: Cuando pyttsx3 o speech_recognition fallan, el sistema continúa sin voz
**Impacto**: Bajo - funcionalidad degradada gracefully
**Solución temporal**: Flag VOICE_AVAILABLE

### 2. CORS permissive
**Descripción**: CORS permite todos los orígenes (`*`)
**Impacto**: Seguridad en desarrollo
**Recomendación**: Restringir en producción

### 3. Sin autenticación
**Descripción**: No hay sistema de usuarios/login
**Impacto**: Limitado a uso local 单 usuario
**Pendiente**: Implementar auth system

### 4. Sin tests automatizados
**Descripción**: No hay suite de tests
**Impacto**: Dificulta refactoring
**Pendiente**: Agregar pytest

---

## Configuración Actual

### Variables de Entorno (Backend)
```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-3-opus-20240229
AI_PROVIDER=ollama
```

### URLs de Conexión
```bash
Backend: http://localhost:8000
API: http://localhost:8000/api
```

### Puertos
- Backend FastAPI: 8000
- Ollama (local): 11434

---

## Cómo Continuar

### Prioridad Alta: Testing y Debugging

1. **Sistema de Logs**
   - Completar implementación en backend
   - Agregar logs en desktop app
   - Configurar rotación de logs

2. **Testing**
   - Crear tests unitarios con pytest
   - Tests de integración para API
   - Tests de UI para desktop

### Prioridad Media: Mejoras de UX

1. **Desktop App**
   - Mejor manejo de errores en UI
   - Indicadores de carga más claros
   - Notificaciones del sistema

2. **API**
   - Documentación Swagger más completa
   - Rate limiting
   - Validación más estricta

### Prioridad Baja: Nuevas Features

1. **Sistema de autenticación**
   - Login/registro
   - Sesiones
   - Permisos

2. **Más agentes**
   - Coder Agent
   - Tester Agent
   - DevOps Agent

3. **Integraciones**
   - Git integration
   - Docker integration
   - Cloud storage

---

## Comandos de Ejecución

### Iniciar Backend
```bash
cd backend
.\iniciar_backend.bat
# O manualmente:
cd backend
call venv\Scripts\activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Iniciar Desktop
```bash
cd backend
python app\desktop.py
# O usar el launcher:
.\iniciar_app.bat
```

### Iniciar Todo
```bash
.\iniciar_todo.bat
```

---

## Recursos y Referencias

### Documentación
- [FastAPI](https://fastapi.tiangolo.com/)
- [SQLAlchemy](https://docs.sqlalchemy.org/)
- [CustomTkinter](https://customtkinter.tomschimansky.com/)
- [Ollama](https://ollama.ai/)

### Modelos Recomendados para Ollama
- llama3 (general)
- codellama (código)
- mistral (rápido)
- llama3:70b (mejor calidad, más lento)

---

## Notas para Agentes IA

### Al trabajar en este proyecto:

1. **Revisar siempre primero**:
   - `Systems Schema.md` - Para entender funcionalidades existentes
   - `Documentación de Desarrollo.md` - Para entender el contexto
   - `backend/logs/system.log` - Para ver errores recientes

2. ** Antes de hacer cambios**:
   - Verificar que no se duplique funcionalidad existente
   - Revisar problemas conocidos
   - Agregar logs apropiados

3. ** Después de cambios**:
   - Actualizar esta documentación
   - Verificar que logs se generen correctamente
   - Documentar nuevos problemas encontrados

4. **Para debugging**:
   - Revisar logs en `backend/logs/`
   - Usar health check: `GET /health`
   - Probar endpoints con Swagger: `http://localhost:8000/docs`

---

*Última actualización: 2024*
*Versión del proyecto: 0.1.0*
