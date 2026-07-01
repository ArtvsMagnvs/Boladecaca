# CLAUDE.md — Memoria persistente y guía de desarrollo de Aithera

> **Fuente de verdad del proyecto.** Construido exclusivamente a partir del estado
> real del código, los modelos de BD, los routers activos y los docs de fase
> existentes. Nada está inventado. Las secciones marcadas con `[pendiente]`
> indican cosas que aún no se han implementado o no se han documentado.

---

## 1. Estado actual del proyecto

**Versión real**: `0.7.1` (consistente en `backend/app/main.py`,
`backend/app/core/config.py` y `frontend/package.json`).

**Fases completadas**: V0.2 (base) → V0.3 (Hub) → V0.4 (PostgreSQL + Alembic) →
V0.5 (AgentManager + ToolManager) → V0.6 (Memory ChromaDB) → V0.7 (Email + Calendar) →
V0.7.1 (Fase 4b — Email Assistant refactor: captura de emails urgentes sin regla,
toast contextual, detección de reuniones en dos etapas patrón AMD GAIA,
`detect_calendar_conflicts` con cross-check de Google Calendar y tests unitarios).

**Fases pendientes (documentadas, no implementadas)**:
- **V0.8** — Clientes Telegram + Web App (FastAPI serving React build) + PWA
- **V0.9** — Automation Engine (APScheduler + reglas + sistema de aprobaciones)
- **V1.0** — Orchestrator (intent analyzer + planner + Claude Code Agent)

**Estado del git**: branch `master` con todo el código staged (`A`/`AM`) pero
**sin ningún commit todavía**. El staging area contiene la totalidad del
repositorio; el primer commit está pendiente. El roadmap está en
`AOS_Arquitectura_y_Roadmap.md` (249 líneas, sustituye al antiguo Plan AOS).

---

## 2. Stack tecnológico real

### Frontend
- **React 18** + **TypeScript 5.3** + **Vite 5**
- **Electron 29** (desktop wrapper)
- **React Router DOM 6** con **HashRouter** (necesario para `file://`)
- **Zustand 4** (estado global, en `frontend/src/store/`)
- **@react-three/fiber + drei** + **three.js 0.160** (AI Core 3D, AICore.tsx con shaders custom)
- **Framer Motion 11** (transiciones)
- **Tailwind CSS 3.4** + PostCSS + Autoprefixer

### Backend
- **FastAPI** con `lifespan` (startup/shutdown async)
- **SQLAlchemy 2.0** (`from sqlalchemy.orm import declarative_base` — NO usar `sqlalchemy.ext.declarative`)
- **Pydantic v2** (`from_attributes = True` — NO usar `orm_mode`)
- **PostgreSQL** (con fallback automático a SQLite si no hay `DATABASE_URL`)
- **Alembic 1.13** para migraciones (`backend/alembic/`)
- **ChromaDB** + **sentence-transformers** (memoria semántica, ~80MB descarga inicial)
- **python-dotenv**, **httpx**, **uvicorn**
- **psycopg2-binary 2.9.9** (driver PostgreSQL)
- 8 proveedores IA vía `httpx` y SDKs nativos (Anthropic, Gemini)

### Empaquetado
- **electron-builder 24** con `appId: com.aithera.desktop`, target NSIS para Windows

---

## 3. Estructura real del repositorio

```
Aithera/
├── frontend/                       # Electron + React 18 + TypeScript + Vite
│   ├── electron/
│   │   └── main.cjs                # Proceso principal Electron (carga UI; NO arranca backend)
│   ├── src/
│   │   ├── pages/                  # 9 páginas (Hub, Chat, Projects, Tasks, Calendar,
│   │   │                           #   Agents, EmailAssistant, VoiceCenter, Settings)
│   │   ├── components/
│   │   │   ├── hub/                # AICore.tsx (3D), HubPanel.tsx
│   │   │   └── layout/             # AppLayout, Sidebar
│   │   ├── hooks/
│   │   ├── lib/api.ts              # Cliente HTTP del backend
│   │   ├── services/
│   │   ├── store/ + stores/        # Zustand stores
│   │   ├── styles/
│   │   └── types/
│   ├── package.json                # v0.7.0
│   └── tailwind.config.js
│
├── backend/                        # FastAPI + SQLAlchemy + PostgreSQL/SQLite
│   ├── app/
│   │   ├── main.py                 # FastAPI app (v0.7.0), lifespan, exception handler
│   │   ├── core/
│   │   │   ├── config.py           # Settings (VERSION=0.7.0, DATABASE_URL dinámico)
│   │   │   └── logging_config.py
│   │   ├── db/
│   │   │   ├── database.py         # 12 modelos SQLAlchemy + engine dinámico
│   │   │   ├── models.py           # Re-exports
│   │   │   └── schemas.py          # Pydantic v2
│   │   ├── api/endpoints/          # 11 routers (ver §6)
│   │   ├── ai/                     # ai_manager, catalog, 9 providers
│   │   ├── agents/                 # AgentManager (15KB) + ArchitectAgent
│   │   ├── memory/                 # ChromaDB MemoryManager
│   │   ├── tools/                  # ToolManager + 8 herramientas (ver §8)
│   │   ├── voice/                  # ElevenLabs + eSpeak
│   │   ├── integrations/           # google_auth.py (OAuth Google)
│   │   └── services/               # [vacío, creado por预留]
│   ├── modules/
│   │   └── email_assistant/        # Módulo paralelo legacy (ver §10)
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/               # 8 migraciones aplicadas
│   ├── scripts/                    # migrate_sqlite_to_postgres.py y otros
│   ├── alembic.ini
│   └── requirements.txt
│
├── AOS_Arquitectura_y_Roadmap.md   # Roadmap oficial (V0.3 → V1.0)
├── Fase_1_Estabilizacion_Hub_V03.md
├── Fase_1b_PostgreSQL_Migration_V04.md
├── Fase_2_AgentManager_ExecutionEngine_V05.md
├── Fase_2_AgentManager_ToolSystem_V04.md     # versión temprana duplicada
├── Fase_3_Memory_ChromaDB_V05.md
├── Fase_4_Email_Calendar_V06.md
├── Fase_5_Clients_Telegram_Web_V08.md
├── Fase_5_Telegram_V07.md                    # versión temprana
├── Fase_6_Automation_V08.md
├── Fase_7_WebApp_PWA_V09.md
├── Fase_8_Orchestrator_V10.md
├── Actualizacion_V0.2.txt + .docx
├── Aithera_V1_Auditoria_y_Roadmap.docx       # auditoría previa
├── GUIA-OAUTH-GOOGLE.md
├── PLAN_HUB_VISUAL_Y_VOZ.md                  # decisión migración CustomTkinter → Electron
├── Systems Schema.md                         # catálogo de endpoints y modelos
├── "ideas guays"/ideas guays.docx            # ideas sueltas del usuario
├── iniciar_frontend_react.bat
├── .claude/settings.local.json               # config de Claude Code
├── .trae/skills/aithera-context/SKILL.md     # skill de Trae IDE
└── CLAUDE.md                                 # este archivo
```

---

## 4. Fases completadas — qué hay y qué no

### ✅ V0.2 — Estabilización base
Cambios ya aplicados (ver `Actualizacion_V0.2.txt` sección 3):
- Fix closure del streaming de chat (`useRef` para acumular chunks)
- Alineación `ChatResponse` ↔ modelo BD (`model_used`/`tokens_used` vs `model`/`tokens`)
- Schemas Pydantic v2 (`from_attributes=True`) en `schemas.py`
- Calendarios: `start_date`, `end_date`, `all_day`, `color`
- `SQLAlchemy 2.0`: `from sqlalchemy.orm import declarative_base`
- Settings: formulario modal para API keys
- `.env.example` con todos los proveedores
- MiniMax hardcode key + modelo por defecto `MiniMax-M2.7-highspeed` (re-aplicar P5 si fue revertido)

### ✅ V0.3 — Hub completo
- `frontend/src/pages/Hub.tsx` (29.5KB) con layout grid 3-columnas
- Paneles izquierdo (proyectos + tareas + agentes) y derecho (calendario + chat reciente + email)
- Barra de estado inferior con polling cada 30s
- AICore 3D preservado sin tocar
- Cierre de los 6 bugs P1–P6 documentados en `Fase_1_Estabilizacion_Hub_V03.md`

### ✅ V0.4 — PostgreSQL + Alembic
- Migración SQLite → PostgreSQL completada (ver `Fase_1b_PostgreSQL_Migration_V04.md`)
- `DATABASE_URL` dinámico en `config.py` con fallback automático a SQLite
- **8 migraciones Alembic aplicadas**:
  - `4ab2071f433f_initial_schema_snapshot_from_sqlite_migration.py` (V0.4)
  - `24b8353ad754_add_agent_fields_and_execution_table.py` (V0.5)
  - `25c926be5811_force_cascade_delete_on_agent_execut...py` (V0.5 fix)
  - `f94e0572d70d_v07_email_calendar_auto_reply_and_.py` (V0.7)
  - `33074ebc50b0_v07_add_google_event_id_to_calendar_.py` (V0.7)
  - `0840fe70d5ce_v07_meeting_proposals.py` (V0.7)
  - `48b15869c4e3_v07_extra_redesign_auto_reply_rules.py` (V0.7)
  - `bff7a3fd8d7d_v07_extra_email_activity_log_and_.py` (V0.7)
- `psycopg2-binary==2.9.9` y `alembic==1.13.1` añadidos a `requirements.txt`
- Backup SQLite conservado en `%APPDATA%/Aithera/aithera.db` como fallback

### ✅ V0.5 — AgentManager + ExecutionEngine + ToolManager
- `backend/app/agents/agent_manager.py` (15KB): CRUD + ciclo de vida de agentes + ejecuciones asíncronas
- `backend/app/agents/architect.py`: tipo de agente específico
- `backend/app/tools/` (9 archivos): `tool_manager.py` + `base.py` + 7 herramientas
- Tablas nuevas: `agents` (con `allowed_tools`, `max_execution_time`, `is_active`),
  `agent_executions` (status, tool_calls, result, error_message)
- Placeholder de decisión IA: cuando un agente tiene tools, ejecuta `list_dir` /
  `list_scripts` / `git status` como demo end-to-end. La decisión real vendrá
  del LLM en fase de Orchestrator (V1.0).
- Validación de `allowed_tools` contra catálogo del ToolManager al crear/actualizar agente

### ✅ V0.6 — Memory System (ChromaDB)
- `backend/app/memory/memory_manager.py` (15KB): 3 colecciones (`conversations`,
  `user_context`, `documents`)
- Sentence-transformers para embeddings (descarga inicial ~80MB, 1-2 min)
- Degradación graceful: si ChromaDB/sentence-transformers fallan, el chat sigue
  funcionando sin memoria
- Endpoints `/api/memory/*` montados en `main.py`
- Stats en startup log: conversaciones, contextos, documentos indexados

### ✅ V0.7 — Email + Calendar evolucionados
- `backend/app/api/endpoints/email_assistant.py` (**1889 líneas, god-endpoint**)
- `backend/app/tools/email_tool.py` (44KB) — lógica Gmail real
- `backend/app/tools/calendar_tool.py` (29KB) — Google Calendar
- `backend/app/integrations/google_auth.py` (9KB) — OAuth flow
- Modelos nuevos: `EmailAutoReplyRule`, `CalendarAvailability`, `MeetingProposal`, `EmailActivityLog`
- Endpoints implementados (ver header del archivo):
  - Auth: `/status`, `/auth/credentials`, `/auth/start`, `/auth` (DELETE)
  - Inbox: `/inbox`, `/{id}`, `/search`, `/draft`, `/send` (requiere confirmación), `/summary`
  - Auto-reply: `/auto-reply/rules` (CRUD), `/auto-reply/test`, `/auto-reply/send`
- Detección de propuestas de reunión, respuestas de confirmación y reagendado
- Frontend: `EmailAssistant.tsx` (51KB) completamente funcional

---

## 5. Fases pendientes — roadmap

### ⏳ V0.8 — Clientes adicionales (Telegram + Web + PWA)
Doc: `Fase_5_Clients_Telegram_Web_V08.md` + `Fase_5_Telegram_V07.md`
- **Telegram bot**: `python-telegram-bot v21` en polling, autenticación por
  `chat_id`, comandos `/proyectos`, `/tareas`, `/estado` + chat natural
- **Web client**: build de React servido por FastAPI en `/app` (mismo build
  que Electron, sin lógica de negocio propia)
- **PWA**: manifest + service worker básico
- Sistema de PIN para acceso desde la red local
- **Estado**: solo documentado, sin implementar

### ⏳ V0.9 — Automation Engine
Doc: `Fase_6_Automation_V08.md`
- Modelos `AutomationRule` y `AutomationExecution`
- **APScheduler** integrado en el `lifespan` de FastAPI
- Tipos de acción: `telegram_message`, `email_summary`, `agent_task`, `chat_query`
- Sistema de aprobaciones para acciones sensibles
- UI de automatizaciones
- Reglas de ejemplo predefinidas (desactivadas por defecto)
- **Estado**: solo documentado, sin implementar

### ⏳ V1.0 — Orchestrator
Doc: `Fase_8_Orchestrator_V10.md`
- **Intent Analyzer**: clasifica intención (query / create / execute / automate / conversational)
- **Task Planner**: planifica pasos usando el AI Manager
- **Response Builder**: sintetiza resultados en lenguaje natural
- **Claude Code Agent**: delega tareas de código a Claude Code CLI si está disponible
- Integración en chat: el Orchestrator decide si necesita tools o es conversación
- UI de aprobación de planes
- **Estado**: solo documentado, sin implementar

---

## 6. Backend — routers y endpoints activos

11 routers montados en `main.py` (orden de registro):

| Prefijo | Router | Tamaño | Descripción |
|---------|--------|--------|-------------|
| `/api/config` | `config.py` | 1.4KB | Configuración key-value |
| `/api/projects` | `projects.py` | 2.2KB | CRUD proyectos |
| `/api/tasks` | `tasks.py` | 2.0KB | CRUD tareas |
| `/api/calendar` | `calendar.py` | 10KB | CRUD eventos |
| `/api/ai` | `ai.py` | 5.9KB | Status, catálogo, configured, test, activate, ollama models |
| `/api/chat` | `chat.py` | 5.7KB | POST /stream (SSE), GET /history, DELETE /history |
| `/api/agents` | `agents.py` | 7.0KB | CRUD agentes + ejecuciones |
| `/api/email` | `email_assistant.py` | **75KB / 1889 líneas** | God-endpoint: auth + inbox + draft + send + auto-reply + meetings |
| `/api/voice` | `voice.py` | 8.6KB | ElevenLabs + eSpeak |
| `/api/tools` | `tools.py` | 2.3KB | Catálogo de herramientas + ejecución |
| `/api/memory` | `memory.py` | 5.6KB | Búsqueda y stats de memoria semántica |

Health checks: `GET /` (versión), `GET /health` (status simple).
Exception handler global en `main.py:113` que captura y loguea todo.

---

## 7. Frontend — páginas y componentes

### Páginas (`frontend/src/pages/`)

| Página | Tamaño | Estado |
|--------|--------|--------|
| `Hub.tsx` | 29.5KB | ✅ Completo con datos reales (V0.3) |
| `EmailAssistant.tsx` | 51KB | ✅ Funcional avanzado (V0.7) |
| `Settings.tsx` | 32KB | ✅ Formularios completos de API keys |
| `Agents.tsx` | 22KB | ✅ CRUD + ejecución de agentes (V0.5) |
| `Calendar.tsx` | 20KB | ✅ CRUD eventos (V0.2 + fix schemas) |
| `VoiceCenter.tsx` | 11KB | ✅ ElevenLabs + eSpeak |
| `Chat.tsx` | 4.4KB | ✅ Streaming SSE con fix closure |
| `Projects.tsx` | 3.9KB | ✅ CRUD básico |
| `Tasks.tsx` | 4.0KB | ✅ CRUD básico |

### Componentes
- `components/hub/AICore.tsx` (5.3KB) — esfera 3D con shaders custom, no tocar
- `components/hub/HubPanel.tsx` (1KB) — paneles laterales
- `components/layout/` — `AppLayout`, `Sidebar`

---

## 8. ToolManager — 8 herramientas registradas

El paquete `app.tools` se importa en `main.py:15` como efecto secundario
para auto-registrar las herramientas en el `ToolManager`. Sin este import,
`GET /api/tools/` devuelve `[]` y el AgentManager no puede ejecutar nada.

| Tool | Archivo | Tamaño | Capacidades |
|------|---------|--------|-------------|
| `filesystem` | `filesystem_tool.py` | 11KB | list_dir, read_file, write_file (con whitelist de rutas) |
| `shell` | `shell_tool.py` | 7.6KB | ejecutar comandos con whitelist (python, git, npm, uvicorn) |
| `git` | `git_tool.py` | 9.2KB | status, log, diff, commit |
| `powershell` | `powershell_tool.py` | 7.9KB | scripts específicos aprobados |
| `email` | `email_tool.py` | **44KB** | Gmail REST + auto-reply + meeting detection |
| `calendar` | `calendar_tool.py` | **29KB** | Google Calendar + availability + proposals |
| `base` | `base.py` | 2.3KB | Interfaz `BaseTool` para todas las herramientas |
| `tool_manager` | `tool_manager.py` | 11.7KB | Registro centralizado + validación |

**Validaciones del ExecutionEngine** (en `tool_manager.py`):
1. La tool debe estar en el registro
2. Los parámetros se validan contra el schema de la tool (no path traversal, no comandos dinámicos)
3. Ejecución con timeout configurable por agente (`max_execution_time`, max 3600s)
4. Registro de la ejecución en `agent_executions` con `tool_calls` JSON
5. Resultado estructurado: `{ success, output, error, duration_ms }`

---

## 9. Modelos de base de datos (12 reales)

Definidos en `backend/app/db/database.py`:

| Modelo | Tabla | Propósito | Añadido en |
|--------|-------|-----------|------------|
| `Config` | `config` | Key-value settings | V0.2 |
| `Project` | `projects` | Proyectos del usuario | V0.2 |
| `Task` | `tasks` | Tareas | V0.2 |
| `CalendarEvent` | `calendar_events` | Eventos (con `google_event_id`) | V0.2 + V0.7 |
| `Conversation` | `conversations` | Sesiones de chat | V0.2 |
| `ChatMessage` | `chat_messages` | Mensajes con `model_used`/`tokens_used` | V0.2 |
| `Agent` | `agents` | Agentes con `allowed_tools`, `max_execution_time` | V0.5 |
| `AgentExecution` | `agent_executions` | Log de ejecuciones async | V0.5 |
| `EmailAutoReplyRule` | `email_auto_reply_rules` | Reglas de auto-respuesta | V0.7 |
| `CalendarAvailability` | `calendar_availability` | Disponibilidad por tipo de actividad | V0.7 |
| `MeetingProposal` | `meeting_proposals` | Propuestas detectadas en emails | V0.7 |
| `EmailActivityLog` | `email_activity_log` | Auditoría de acciones email | V0.7 |
| `AIProviderConfig` | `ai_provider_configs` | Config de cada proveedor IA | V0.2 |

**Migración de esquema**: ahora con Alembic. NO usar `_ensure_columns()` —
eso era de V0.2. Alembic es la fuente de verdad desde V0.4.

---

## 10. Sistema de IA multi-proveedor

8 proveedores en `backend/app/ai/providers/`:

| Proveedor | Clase | Endpoint | Default | Notas |
|-----------|-------|----------|---------|-------|
| Ollama | `OllamaProvider` | `localhost:11434` | `llama3` | Local, sin API key |
| OpenAI | `OpenAIProvider` | OpenAI API | `gpt-5.1` | |
| Anthropic | `AnthropicProvider` | Anthropic API | `claude-sonnet-4-6` | SDK propio |
| Gemini | `GeminiProvider` | Google AI | `gemini-3.1-pro-preview` | SDK propio |
| MiniMax | `MinimaxProvider` | `api.minimax.io/v1/chat/completions` | `MiniMax-M2.7-highspeed` | `max_completion_tokens` max 2048 |
| DeepSeek | `DeepSeekProvider` | DeepSeek API | `deepseek-v4-flash` | Compatible OpenAI |
| OpenRouter | `OpenRouterProvider` | OpenRouter API | `""` (libre) | Compatible OpenAI |
| Grok (xAI) | `GrokProvider` | xAI API | `grok-4.3` | Compatible OpenAI |

`backend/app/ai/providers/openai_compatible.py` es la base para los que usan
formato OpenAI (DeepSeek, OpenRouter, Grok, y MiniMax lo reutiliza parcialmente).

`AIManager` (singleton en `ai_manager.py`):
- Lee `AIProviderConfig` de la BD en `__init__`
- Bootstrap desde `.env` solo si la DB está vacía
- Proveedor activo: el marcado `is_active=True`
- Health check con caché de 30 segundos
- Fallback no-streaming si `generate_stream` no produce chunks

Configuración del proveedor por prioridad: env var (`MINIMAX_API_KEY`) →
constante hardcoded en el provider → UI de Configuración (Settings).

---

## 11. Memory System — ChromaDB

`backend/app/memory/memory_manager.py` con 3 colecciones:

- **`conversations`** — embeddings de mensajes de chat para RAG
- **`user_context`** — contexto personal persistente (preferencias, datos del usuario)
- **`documents`** — documentos indexados subidos por el usuario

Pipeline:
1. Al arrancar el backend, `memory_manager.is_healthy()` comprueba ChromaDB
2. Si no está, el constructor degrada gracefully (log warning, chat sigue)
3. Si está, la primera vez descarga `sentence-transformers` (~80MB, 1-2 min)
4. Stats en log: `Memory system listo — N conv, M ctx, K docs`

---

## 12. Voice System

- **ElevenLabs** (`voice/elevenlabs_voice.py`): TTS en la nube
- **eSpeak NG** (`voice/espeak_voice.py`): fallback offline
- Backend decide automáticamente qué motor usar según disponibilidad
- Endpoint: `POST /api/voice/synthesize`
- `VoiceCenter.tsx` (11KB) funcional en frontend

---

## 13. Integraciones externas

### Google OAuth 2.0
- `backend/app/integrations/google_auth.py` (9KB)
- Flujo: Authorization Code + PKCE para desktop
- Scopes: Gmail read/send + Calendar read/write
- Documentación en `GUIA-OAUTH-GOOGLE.md`
- Credenciales se guardan en BD vía `POST /api/email/auth/credentials`

### Telegram (V0.8, pendiente)
- Solo documentado. No hay código todavía.

---

## 14. Convenciones de código

### Backend (Python)
- Un archivo por router: `app/api/endpoints/<nombre>.py`
- Schemas Pydantic en `app/db/schemas.py`, modelos en `app/db/database.py`
- **Siempre** `model.model_dump()` (Pydantic v2), nunca `.dict()`
- **Siempre** `from_attributes = True` en `class Config` de schemas de respuesta
- `from sqlalchemy.orm import declarative_base, sessionmaker` — NO `sqlalchemy.ext.declarative`
- Singletons: `agent_manager`, `tool_manager`, `ai_manager`, `memory_manager`
- Imports con efecto secundario solo donde está documentado (ej. `import app.tools`)
- Logs: `from app.core.logging_config import get_system_logger, log_error, log_info`

### Frontend (TypeScript/React)
- Hooks de React: `useState`, `useEffect`, `useRef` — sin librerías externas
- Estado global: **Zustand** (`store/` + `stores/`)
- **Patrón obligatorio para acumular streaming**: `useRef` para chunks, no `useState`
- **HashRouter** siempre (Electron usa `file://`)
- Estilos: Tailwind + CSS variables (`text-ink`, `bg-base-950`, `text-accent`)
- Cliente API: `src/lib/api.ts`, nunca `fetch` directo en componentes

### Nomenclatura
- Proveedores IA: lowercase (`"minimax"`, `"openai"`)
- Modelos: respetar mayúsculas del proveedor (`"MiniMax-M2.7-highspeed"`)
- Endpoints URL: kebab-case; funciones Python: snake_case; componentes React: PascalCase

---

## 15. Pipeline de desarrollo

### Arrancar entorno
```bash
# Terminal 1 — Backend (puerto 8000)
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend (Vite dev server, puerto 5173)
cd frontend
npm install
npm run dev

# Terminal 3 — Electron (opcional)
cd frontend
npm run electron:dev
```

### Migraciones Alembic
```bash
cd backend
alembic revision --autogenerate -m "descripcion"
alembic upgrade head
alembic current   # ver versión aplicada
```

### Build de producción
```bash
cd frontend
npm run build
npm run electron:build  # genera release/*.exe con electron-builder
```

### Configurar MiniMax
1. Settings → Proveedores IA → MiniMax → Configurar
2. Pegar API key (en `Actualizacion_V0.2.txt` sección 1 está la key)
3. Modelo: `MiniMax-M2.7-highspeed`
4. "Probar conexión" → "Guardar" → "Activar"

---

## 16. Restricciones y deuda técnica conocida

### Restricciones actuales
1. **Backend arrancado manualmente** — no hay auto-start desde Electron
2. **Windows-first** — paths tipo `%APPDATA%/Aithera/`, scripts `.bat`
3. **SQLite fallback** — si no hay `DATABASE_URL`, cae a SQLite en `%APPDATA%`
4. **API keys en BD local** — texto plano en `ai_provider_configs` y BD
5. **CORS abierto (`*`)** — aceptable en localhost, no en producción
6. **Sin autenticación** — app personal, un solo usuario

### Deuda técnica crítica

1. **⚠️ God-endpoint `email_assistant.py` (1889 líneas)** — viola la regla
   "un archivo por router". Múltiples routers viven en uno. Acopla auth +
   inbox + drafts + send + auto-reply + meetings. La Fase 4 lo creó así por
   urgencia; el refactor pendiente es dividirlo en:
   - `email_auth.py` (OAuth + credenciales)
   - `email_inbox.py` (lectura)
   - `email_compose.py` (drafts + send)
   - `email_auto_reply.py` (reglas)
   - `email_meetings.py` (proposals + reschedule)

2. **⚠️ Módulos paralelos `app/tools/email_tool.py` vs `modules/email_assistant/`**
   — Hay lógica de email en dos sitios. `modules/email_assistant/` parece
   legacy y `app/tools/email_tool.py` la implementación activa. Hay que
   auditar qué hay en `modules/` y unificar.

3. **⚠️ `backend/app/services/` está vacío** — directorio预留 sin uso real.
   Decidir si se rellena o se elimina.

4. **⚠️ Dos versiones de algunos docs de fase**:
   - `Fase_2_AgentManager_ToolSystem_V04.md` (V04, temprana)
   - `Fase_2_AgentManager_ExecutionEngine_V05.md` (V05, real)
   - `Fase_5_Clients_Telegram_Web_V08.md` (V08)
   - `Fase_5_Telegram_V07.md` (V07, temprana)
   Conservar la versión final (V05, V08) y archivar las tempranas.

5. **⚠️ Backend NO arranca backend desde Electron** — el usuario lo arranca
   manualmente. Solución de producción pendiente (servicio Windows / script
   de inicio automático).

6. **ChatMessage `model_used`/`tokens_used` vs ChatResponse `model`/`tokens`** —
   sigue habiendo inconsistencia detectada en V0.2. Bajo impacto porque
   el endpoint de chat no persiste aún en `ChatMessage`.

7. **Alembic y modelo ORM** — el modelo ORM en `database.py` y la migración
   inicial `initial_schema_snapshot_from_sqlite_migration` pueden divergir
   si se modifica el modelo sin generar nueva migración. Regla: cualquier
   cambio de modelo ⇒ nueva migración Alembic obligatoriamente.

---

## 17. Riesgos técnicos

| Riesgo | Probabilidad | Mitigación |
|--------|--------------|------------|
| Refactor del god-endpoint email_assistant rompa OAuth | Media | Hacer pruebas con cuenta secundaria antes |
| ChromaDB + sentence-transformers ~1.5GB | Media | Documentar peso, descarga solo primer arranque |
| MiniMax cambia su API | Media | `minimax_provider.py` aislado, fácil de actualizar |
| Tres versiones de docs de fase descolocadas | Alta | Limpiar al cerrar V0.8 |
| Git sin commits en master | Alta | Hacer commit inicial con todo el código staged |
| Auto-start backend en producción | Media | Definir mecanismo antes de release |

---

## 18. Decisiones de diseño que guían el proyecto

Estas decisiones son **inviolables** salvo acuerdo explícito del usuario:

1. **No romper lo que funciona** — cada commit deja producto usable
2. **Evolución, no reescritura** — refactor solo cuando un módulo impide avanzar
3. **Un backend, múltiples clientes** — Electron/Telegram/Web/PWA son interfaces puras
4. **La IA razona, Aithera decide** — el LLM nunca tiene acceso directo a herramientas
5. **Ejecución controlada** — ExecutionEngine valida whitelist antes de ejecutar
6. **Optimizar para un usuario** — no multi-tenancy, no balanceo
7. **Cada fase deja producto usable** — duración de días, no semanas
8. **Sin sobreingeniería** — Celery no, GraphQL no, LangChain no, AutoGen no

---

## 19. Cómo actualizar este archivo

Este archivo debe evolucionar a la par del proyecto. Reglas:

1. **Tras cada commit** que toque arquitectura, modelos o endpoints: actualizar
   la sección correspondiente.
2. **Tras cada bump de versión** (V0.x → V0.y): actualizar §1, §4, §5 y §15.
3. **Tras cada refactor mayor** (ej. dividir god-endpoint): actualizar §3, §6, §16.
4. **Nunca** inventar secciones ni asumir comportamientos no presentes en el
   código. Si algo no está implementado, marcar como `[pendiente]`.
5. Si una sección queda obsoleta, moverla a `archive/` (no creado aún) o
   eliminarla explícitamente.

---

*Última actualización: julio 2026 — V0.7.1*
*Construido desde el estado real del repositorio (código + Alembic + docs de fase).*
*Sustituye a la versión V0.2 anterior, que declaraba un estado obsoleto.*