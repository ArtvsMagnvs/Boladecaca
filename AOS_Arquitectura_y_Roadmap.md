# Aithera V2 — Plan Maestro de Evolución
## Sistema Operativo Personal de IA

> **Este documento es la fuente de verdad del proyecto.**
> Construido a partir del estado real del código existente y los principios definidos por el usuario.
> Todo aquí tiene una justificación. Nada está inventado.
> Última revisión: junio 2026 — sustituye a la versión anterior del Plan AOS.

---

## 1. Punto de partida: qué existe y funciona

Aithera V0.2.0 es una aplicación de escritorio funcional (Electron + React + FastAPI + SQLite).

| Módulo | Estado real | Decisión V2 |
|--------|------------|-------------|
| Chat con streaming SSE | ✅ Funcional | Mantener, conectar al Orchestrator en Fase 7 |
| Proyectos (CRUD) | ✅ Funcional | Mantener sin cambios |
| Tareas (CRUD) | ✅ Funcional | Mantener sin cambios |
| Calendario (CRUD) | ✅ Funcional (fix V0.2) | Evolucionar: disponibilidad + Google Calendar |
| Settings / Proveedores IA | ✅ Funcional | Mantener, añadir config de Execution Engine |
| 8 proveedores IA (ai_manager) | ✅ Funcional | Mantener, refactorizar interfaz BaseAIProvider |
| Agentes (CRUD básico) | ⚠️ Base existe, incompleta | Evolucionar con AgentManager + Tools |
| Email Assistant | ⚠️ Esqueleto backend | Evolucionar (nunca reemplazar) |
| Voice (ElevenLabs + eSpeak) | ⚠️ Backend OK, UI esqueleto | Evolucionar UI cuando sea prioritario |
| Hub (AI Core 3D) | ⚠️ Centro OK, paneles vacíos | Completar paneles con datos reales (Fase 1) |
| SQLite | ✅ Funcional | Migrar a PostgreSQL en Fase 1b |

**Conclusión**: hay una base sólida. El trabajo es evolución, no construcción desde cero.

---

## 2. Principios que rigen cada decisión

**1. Nunca romper lo que funciona.** La app debe estar en estado usable en cada fase. No existe un periodo donde "todo esté roto". Cada commit deja un producto funcional. **Aclaración (2026-07-13, revisión crítica de principios)**: esto protege comportamiento CORRECTO y contratos públicos ya acordados (rutas, schemas, comportamiento esperado por el usuario) — nunca protege un bug, una vulnerabilidad o una configuración insegura solo porque nadie se había quejado todavía. Restringir un CORS abierto a `*` o cifrar una API key que estaba en texto plano NO es "romper lo que funciona": es corregir lo que nunca debió funcionar así. La pregunta correcta no es "¿esto cambia algo?" sino "¿esto le quita al usuario algo que dependía intencionadamente tener?".

**2. Evolución, no reescritura.** Antes de reemplazar un módulo, la pregunta es: ¿puede evolucionar con cambios menores? Si la respuesta es sí, se evoluciona. Solo se reemplaza cuando el módulo existente impide el avance de forma demostrable.

**3. Un único backend, múltiples clientes.** FastAPI es el único lugar con lógica de negocio. Electron, web, Telegram y PWA son interfaces — envían peticiones y muestran resultados. Nunca se duplica lógica entre clientes.

**4. La IA razona, Aithera decide.** Ningún proveedor de IA contiene lógica de negocio. La IA recibe un prompt y devuelve texto o JSON. Aithera interpreta ese resultado y decide qué herramienta usar, qué agente ejecutar, qué dato guardar.

**5. Ejecución controlada, nunca arbitraria.** El Execution Engine solo ejecuta herramientas de una whitelist registrada. La IA nunca puede generar un comando y ejecutarlo directamente. Toda acción con efectos externos pasa por una herramienta validada.

**6. Optimizar para un usuario, no para cientos.** No hay multi-tenancy, no hay balanceo de carga. La arquitectura es la mínima necesaria para que un usuario avanzado trabaje de forma potente y fluida. **Aclaración (2026-07-13)**: esto gobierna infraestructura de escala (multi-tenancy, balanceo, sharding) — nunca seguridad, y no contradice `PLAN_MAESTRO_2026/16` principio 17 ("diseñar a cinco años"): ese principio habla de la calidad de las fronteras del código, no de construir para mil usuarios. Un solo usuario también necesita credenciales cifradas y una red que no esté abierta por defecto.

**7. Cada fase deja el producto usable.** Las fases duran días, no semanas. Si una fase crece demasiado, se parte en dos.

**8. Sin sobreingeniería.** Si hay dos soluciones y la simple funciona, se usa la simple. Sin Celery (asyncio.Queue suficiente), sin GraphQL (REST ya funciona), sin frameworks de agentes (custom en ~200 líneas).

---

## 3. Arquitectura objetivo (V2)

```
CLIENTES (interfaces puras, sin lógica de negocio)
├── Electron App (Windows desktop) ← ya existe
├── Web App     (mismo React, servido por FastAPI) ← Fase 5
├── Telegram Bot (python-telegram-bot v21) ← Fase 5
└── PWA         (manifest + service worker) ← Fase 5

          │ HTTP / SSE
          ▼

BACKEND FastAPI (único, puerto 8000)
│
├── ORCHESTRATOR (Fase 7)
│   ├── Intent Analyzer  ← usa AIManager para clasificar intención
│   ├── Task Planner     ← usa AIManager para planificar pasos
│   └── Response Builder ← sintetiza resultados en lenguaje natural
│
├── AGENT MANAGER (Fase 2)
│   ├── AgentExecutor    ← lanza y gestiona tareas de agentes
│   └── ClaudeCodeAgent  ← agente externo para tareas de código
│
├── EXECUTION ENGINE (Fase 2)
│   ├── FilesystemTool   ← leer/escribir archivos (rutas permitidas)
│   ├── ShellTool        ← whitelist: python, git, npm, uvicorn
│   ├── GitTool          ← status, log, diff, commit
│   └── PowerShellTool   ← scripts específicos aprobados
│
├── TOOL MANAGER (Fase 2)
│   ├── EmailTool        ← Gmail REST API (Fase 4)
│   ├── CalendarTool     ← Google Calendar (Fase 4)
│   └── MemoryTool       ← búsqueda en ChromaDB (Fase 3)
│
├── AI MANAGER (ya existe — mantener, refactorizar interfaz)
│   └── MiniMax, Ollama, Anthropic, OpenAI, Gemini, DeepSeek, OpenRouter, Grok
│
├── MEMORY MANAGER (Fase 3)
│   └── ChromaDB local: conversaciones, contexto usuario, documentos
│
└── AUTOMATION ENGINE (Fase 6)
    └── APScheduler: reglas cron/interval, sistema de aprobaciones

          │
          ▼

PERSISTENCIA
├── PostgreSQL (Fase 1b — migrar desde SQLite)
│   └── projects, tasks, calendar_events, agents, agent_executions,
│       automation_rules, conversations, chat_messages, config, ai_provider_configs
└── ChromaDB (Fase 3 — directorio local %APPDATA%/Aithera/chroma/)
    └── memoria semántica vectorial
```

---

## 4. Decisiones técnicas clave

### SQLite → PostgreSQL (Fase 1b)

**Por qué migrar**: SQLite es suficiente ahora, pero PostgreSQL ofrece búsqueda full-text nativa, mejor soporte para JSON complejo (configs de automatizaciones, tool configs), y es el estándar para cualquier crecimiento futuro. La migración es la mejor inversión técnica del proyecto: se hace una vez y habilita todo lo que viene.

**Cómo**: script Python one-shot que lee todas las tablas de SQLite y las inserta en PostgreSQL. Los modelos SQLAlchemy no cambian, solo el engine. Se inicializa Alembic para gestionar migraciones futuras. SQLite se mantiene como backup durante una fase.

**Riesgo**: bajo. El código de la app no se toca.

### Execution Engine (Fase 2)

No es `subprocess` directo. Es una clase que: (1) valida que la herramienta está en el registro, (2) valida los parámetros (sin path traversal, sin comandos dinámicos), (3) ejecuta con timeout, (4) registra la ejecución en la BD, (5) devuelve resultado estructurado. La IA nunca ve el comando ejecutado, solo el resultado.

### Agentes: arquitectura mínima escalable (Fase 2)

No se construyen decenas de agentes. Se define una interfaz `BaseAgent` con 3 implementaciones iniciales:
- `GenericAgent`: usa el proveedor IA activo
- `ProviderAgent`: fuerza un proveedor específico (MiniMax, Ollama)
- `ClaudeCodeAgent`: delega a Claude Code CLI para tareas de código

Cada agente tiene `allowed_tools`: lista de herramientas que puede usar. El AgentManager gestiona el ciclo de vida (lanzar, cancelar, consultar estado).

### Frontend: evolución del React existente

No se reconstruye. Se añaden componentes progresivamente. El stack (React 18 + Vite + Zustand + Tailwind + Three.js) se mantiene exactamente igual.

### Clientes adicionales: cero cambios en el backend (Fase 5)

El web client es el mismo build de React servido como `StaticFiles` por FastAPI. Telegram es un cliente Python que llama directamente a los servicios internos. Ningún cliente contiene lógica de negocio.

---

## 5. Roadmap por fases

### Tabla resumen

| Fase | Versión | Objetivo principal | Doc de implementación |
|------|---------|-------------------|----------------------|
| 1 | V0.3 | Bugs conocidos + Hub completo con datos reales | `Fase_1_Estabilizacion_Hub_V03.md` |
| 1b | V0.4 | Migración SQLite → PostgreSQL + Alembic | `Fase_1b_PostgreSQL_Migration_V04.md` |
| 2 | V0.5 | AgentManager + Execution Engine + ToolManager | `Fase_2_AgentManager_ExecutionEngine_V05.md` |
| 3 | V0.6 | Memory System (ChromaDB) + contexto en chat | `Fase_3_Memory_ChromaDB_V06.md` |
| 4 | V0.7 | Email + Calendar evolucionados (Google OAuth) | `Fase_4_Email_Calendar_V07.md` |
| 5 | V0.8 | Clientes: Telegram + Web App (mismo backend) | `Fase_5_Clients_Telegram_Web_V08.md` |
| 6 | V0.9 | Automation Engine (reglas + APScheduler) | `Fase_6_Automation_V09.md` |
| 7 | V1.0 | Orchestrator + Claude Code Agent | `Fase_7_Orchestrator_V10.md` |

### Fase 1 — V0.3: Estabilización + Hub completo

Cierra los 6 bugs documentados en `CLAUDE.md` sección 19 (AgentResponse incompleto, voice status anidado, .gitignore, aithera.db en git, modelo MiniMax, versión inconsistente). Completa el Hub Layout con datos reales de la API (proyectos, tareas, agentes, calendario, barra de estado). La app pasa de V0.2 a V0.3 estable.

### Fase 1b — V0.4: Migración PostgreSQL

Script de migración SQLite → PostgreSQL, configuración de Alembic para migraciones futuras, actualización del engine en database.py. Los modelos SQLAlchemy no cambian. El frontend no se toca. Al terminar, la app funciona exactamente igual pero sobre PostgreSQL.

### Fase 2 — V0.5: AgentManager + Execution Engine + ToolManager

Sistema de agentes real. Rediseño del modelo Agent (añadir allowed_tools, max_execution_time). Nueva tabla AgentExecution. BaseTool + FilesystemTool + ShellTool + GitTool + PowerShellTool. ToolManager (registro centralizado). ExecutionEngine (validación + ejecución controlada). AgentManager (ciclo de vida). UI de Agentes completa. Endpoints nuevos.

### Fase 3 — V0.6: Memory System

ChromaDB local + sentence-transformers. MemoryManager con 3 colecciones (conversations, user_context, documents). Integración en chat.py: contexto automático en cada mensaje. Endpoints /api/memory/*. Sección en Settings. La primera vez descarga el modelo de embeddings (~80MB, 1-2 min).

### Fase 4 — V0.7: Email + Calendar (Google OAuth)

Completar el flujo OAuth de Google (backend ya existe en email_assistant.py). EmailTool real con Gmail REST API: list_inbox, get_email, search_emails, create_draft, send_email (siempre con confirmación), classify_email (IA). CalendarTool: list_events, create_event (con confirmación), find_free_slots. UI de Email funcional (evolucionar el esqueleto existente). Configuración de disponibilidad por tipo de actividad.

### Fase 5 — V0.8: Clientes adicionales (Telegram + Web)

Telegram bot con python-telegram-bot v21 en modo polling. Autenticación por chat_id. Comandos: /proyectos, /tareas, /estado + chat natural. Web client: build de React servido por FastAPI en /app. Sistema de PIN para acceso desde la red local. Manifest PWA + service worker básico. El backend no cambia.

### Fase 6 — V0.9: Automation Engine

Modelos AutomationRule y AutomationExecution en PostgreSQL. APScheduler integrado en el lifespan de FastAPI. Tipos de acción: telegram_message, email_summary, agent_task, chat_query. Sistema de aprobaciones para acciones sensibles. UI de automatizaciones. Reglas de ejemplo predefinidas (desactivadas).

### Fase 7 — V1.0: Orchestrator

Orchestrator que analiza intención (query/create/execute/automate/conversational), planifica pasos, ejecuta usando ToolManager y AgentManager, sintetiza respuesta. ClaudeCodeAgent para tareas de programación (llama a Claude Code CLI si está disponible). Integración en el chat: el Orchestrator decide si la tarea necesita herramientas o es conversación directa. UI de aprobación de planes.

---

## 6. Qué NO se hace (decisiones de scope)

| Elemento | Decisión | Razón |
|----------|----------|-------|
| Reescritura del frontend | ❌ No | El React existente se evoluciona |
| Autenticación de usuarios | ❌ No | App personal, un solo usuario |
| Multi-tenancy | ❌ No | Fuera del objetivo |
| Despliegue en cloud | ❌ No | Offline-first, datos personales locales |
| LangChain / AutoGen | ❌ No | Sobreingeniería; AutoGen en maintenance mode 2026 |
| Celery / Redis | ❌ No | asyncio.Queue suficiente para un usuario |
| GraphQL | ❌ No | REST funciona, no hay razón para migrar |
| Tests automáticos (ahora) | ❌ Deuda aceptada | Prioridad: funcionalidad. Tests en V1.1 |
| Aplicación móvil nativa | ❌ No (ahora) | La PWA cubre el caso de uso |

---

## 7. Gestión de riesgos

| Riesgo | Probabilidad | Mitigación |
|--------|-------------|-----------|
| Migración PostgreSQL rompe algo | Baja | Mantener SQLite como backup durante una fase |
| ChromaDB + PyTorch pesa ~1.5GB | Media | Documentar, descarga automática primer arranque |
| Claude Code CLI no disponible | Media | ClaudeCodeAgent falla con mensaje claro, no bloquea nada |
| MiniMax cambia su API de nuevo | Media | minimax_provider.py aislado, fácil de actualizar |
| Una fase se vuelve demasiado grande | Alta | Cortar cuando supere 2 sesiones de Claude Code estimadas |
| Deuda técnica acumulada | Media | Reservar inicio de cada fase para resolver deuda del anterior |

---

## 8. Protocolo de trabajo con Claude Code

Este documento es la entrada para cada sesión de Claude Code. El flujo es:

1. Entregar a Claude Code el documento de la fase actual (ej. `Fase_1b_PostgreSQL_Migration_V04.md`)
2. Claude Code debe leer `CLAUDE.md` antes de empezar (contexto del proyecto)
3. Claude Code implementa tarea por tarea del documento
4. Al terminar cada tarea, verificar los criterios de aceptación del documento
5. Si todo pasa, pasar a la siguiente fase

**Regla de oro**: si en algún momento la app deja de arrancar, revertir y reducir el scope antes de continuar.

**IMPORTANTE**: Claude Code NO debe modificar la base de datos de producción directamente. Todos los cambios de esquema van a través de migraciones Alembic (a partir de Fase 1b).

---

## 9. Responsabilidades

| Responsable | Qué hace |
|-------------|----------|
| Aithera (el sistema) | Orquesta. Decide qué usar, cuándo y cómo. |
| MiniMax / IA activa | Razona. Clasifica intenciones, planifica pasos, genera texto. |
| Claude Code | Implementa. Escribe el código de cada fase bajo instrucciones explícitas. |
| Claude Cowork | Documenta. Crea y actualiza los documentos del proyecto. |
| El usuario | Configura, aprueba acciones sensibles, y define prioridades. |

---

*Un solo usuario. Máximo potencial. Mínima complejidad.*
*Diseñado para ejecutarse íntegramente con IA en cada fase.*
