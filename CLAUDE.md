# CLAUDE.md — Memoria persistente y guía de desarrollo de Aithera

<!-- SKILL: graphify (`.claude/skills/graphify/SKILL.md`) - knowledge graph del codebase. Trigger: `/graphify`
When the user types `/graphify`, invoke the Skill tool with skill: "graphify" before doing anything else.
Actualizar tras cada sesión: `graphify . --update` en terminal dentro de la carpeta Aithera.
Auto-update por commit (instalar una vez): `graphify hook install` en terminal dentro de Aithera. -->

> **Fuente de verdad del proyecto.** Construido exclusivamente a partir del estado
> real del código, los modelos de BD, los routers activos y los docs de fase
> existentes. Nada está inventado. Las secciones marcadas con `[pendiente]`
> indican cosas que aún no se han implementado o no se han documentado.

---

## 1. Estado actual del proyecto

**Versión real**: `0.9.2` (consistente en `backend/app/main.py`,
`backend/app/core/config.py` y `frontend/package.json`; tag de git `v0.9.2`).
Bump 0.9.0 → 0.9.2 (2026-07-17) al **cerrar el bloque TIE v1 completo (V1.0
T1-T5)** — decisión de versión del usuario (2026-07-16): V1.0 se desarrolla por
bloques, el TIE cierra en `0.9.2`; MEL → integración Orchestrator → MVP-beta
vendrán después y cerrarán la fase completa en `1.0.0` — ver más abajo.
Bump 0.8.7 → 0.9.0 (2026-07-16) al **cerrar V0.9 completa (Automation Engine +
ApprovalGate, sprints A1 → A2a → A2b → A3 → A3b → A4)** — ver más abajo.
Bump 0.7.3 → 0.8.0 (2026-07-09) al cerrar el grueso de V0.8: Gateway +
Telegram + hardening (CORS/DPAPI) + voz (STT Whisper, TTS multi-proveedor
EdgeTTS/ElevenLabs/Kokoro/eSpeak, conversación continua) + Hub responsivo.
Bump 0.8.0 → 0.8.5 (2026-07-13) al **cerrar V0.85 completa (MOS Skeleton,
sprints M1-M5)**. Bump 0.8.5 → 0.8.7 (2026-07-15) al **cerrar V0.87 completa
(WPMS Workspace & Project Management, sprints W1 → W2a-W2e → W3b → W4)** —
ver más abajo. Banners de los `.bat` de arranque actualizados a 0.9.2
(`iniciar_backend.bat`, `iniciar_todo.bat`, `iniciar_frontend_react.bat`;
`backend/iniciar_app.bat` sigue con un banner `0.3.0` heredado y
desactualizado — deuda menor, no tocado).

**Fases completadas**: V0.2 (base) → V0.3 (Hub) → V0.4 (PostgreSQL + Alembic) →
V0.5 (AgentManager + ToolManager) → V0.6 (Memory ChromaDB) → V0.7 (Email + Calendar) →
V0.7.1 (Fase 4b — Email Assistant refactor: captura de emails urgentes sin regla,
toast contextual, detección de reuniones en dos etapas patrón AMD GAIA,
`detect_calendar_conflicts` con cross-check de Google Calendar y tests unitarios)
→ **V0.7.2** (Sprint 2 PLAN_MAESTRO_2026: split del god-endpoint email en 7
routers + `app/services/email_service.py`, rutas públicas intactas por contrato;
FIX del bug latente `json`/`log_activity` que impedía persistir el activity log)
→ **V0.7.3** (Sprints 3-4 PLAN_MAESTRO_2026 — **Email Assistant TERMINADO**:
triaje del inbox en 7 categorías con clasificador de 2 etapas heurística→LLM;
autonomía gradual por regla patrón Inbox Zero — toda regla nace en 'propose'
(borradores), el feedback del usuario (✓/✎/✗) alimenta contadores y con saldo
≥5 se ofrece subirla a 'auto'; digest diario `GET /api/email/digest` + tarjeta
en el Hub; docs de fase duplicados archivados en `archive/`; **remate 4b**:
autonomía elegible directamente al crear la regla (para remitentes poco
frecuentes) y `ai_prompt` por regla — respuesta redactada por el proveedor IA
activo con instrucción de estilo del usuario, plantilla como fallback).

**Trabajo V0.8 en curso (post-0.7.3, sobre `master`; versión en código aún `0.7.3`)**:
- **B21 — filtro de razonamiento** (`app/ai/reasoning_filter.py`): separa la
  cadena de pensamiento `<think>…</think>` de los modelos razonadores (MiniMax
  M2.7, DeepSeek R) de la respuesta real. `strip_reasoning()` (completas) +
  `StreamingReasoningFilter` (SSE chunk a chunk, tolera el tag partido entre
  chunks). Aplicado en `chat.py`; `email_tool.strip_reasoning` delega aquí.
- **Gateway + MessageEnvelope (esqueleto V0.8, patrón OpenClaw)** (`app/gateway/`):
  núcleo channel-agnostic. `MessageEnvelope`/`OutboundMessage`/`Attachment`,
  `ChannelAdapter` (ABC), `Gateway` (registro + `dispatch` fail-soft) y
  `chat_message_handler` (equivalente channel-agnostic de `/api/chat`, con B21).
  Diseño en `PLAN_MAESTRO_2026/06_GATEWAY_V08_DISENO.md`. En V1.0 el handler se
  cambia por el Orchestrator con `gateway.set_handler()` — un solo punto.
- **Canal Telegram** (`app/gateway/adapters/telegram_adapter.py`): primer adapter
  real sobre el Gateway (python-telegram-bot 21.10, polling). Chat natural →
  `gateway.dispatch`; comandos `/start` `/proyectos` `/tareas` `/estado`;
  whitelist de `chat_id`. Configurable desde Ajustes (sección Telegram en
  `Settings.tsx`) vía router `/api/telegram` (status/configure). Registrado en el
  `lifespan` solo si hay token; degradación graceful si falta la lib o el token.
- **Cifrado de secretos en reposo (DPAPI)** (`app/core/secrets.py`): `encrypt`/
  `decrypt`/`mask` con DPAPI de Windows (fallback marcado en no-Windows, y
  compatibilidad con valores legado en texto plano). Usado por el token de
  Telegram y por las API keys de los proveedores IA.
- **Security Hardening (V0.8)**: CORS restringido a orígenes conocidos en
  `main.py` (localhost + `null` de Electron + `Settings.CORS_ALLOWED_ORIGINS`;
  ya NO `allow_origins=['*']`). API keys de los proveedores cifradas en reposo:
  el `AIManager` cifra al persistir (`_enc`) y descifra al instanciar (`_dec`);
  migración Alembic `d4e5f6a7b8c9_v08_encrypt_api_keys` re-cifra las existentes
  (idempotente). Falta solo el PIN/token de red (irá con el cliente Web, post-V1.0).

**V0.85 — MOS Skeleton (en curso, sobre `master`)**: Memory Operating System,
Opción B (arquitectura definitiva, implementación mínima). Diseño completo en
`PLAN_MAESTRO_2026/07_MOS_V085_DISENO.md` (+ 08 arquitectura). Sprints M1-M5.
- ✅ **M1 — Contratos + esqueleto** (`app/memory/`): contratos CONGELADOS en
  `interfaces.py` (`IMemoryStore` 6 métodos async, `ISkillStore`, `MemoryType`
  —5 activos + 6 reservados, append-only—, `MemoryItem`, `MemoryQuery`,
  `LocalSkill` con linaje `derived_from`/`superseded_by` [Δ doc 14], `SkillStatus`).
  `LocalMemoryStore` (ChromaDB, reusa el cliente del `memory_manager` legacy vía
  accesor compartido — una sola carga de sentence-transformers; 1 colección por
  MemoryType, `CONVERSATIONAL` aliasa la legacy `conversations`; metadata
  saneada; async vía `to_thread`; dedup idempotente por `dedup_key`).
  `MemoryRouter` (singleton `memory_router`, `{MemoryType→IMemoryStore}`, todo a
  Local en V0.85 — el punto de intercambio tecnológico, 08 RFC-006). Stubs:
  `distributed_store.py` (V2.0+), `stores/skill_store.py` (singleton `skill_store`).
  `app/services/decision_service.py` (tabla `decisions` fuente de verdad + espejo
  `mem_decision`, best-effort). Migración Alembic 12.ª `e5f6a7b8c9d0_v085_mos_skeleton`
  (`memory_job_runs`, `decisions` con `mission_id` [Δ]). Disciplina modular
  [Δ doc 16]: API pública en `app/memory/__init__.py`, vigilada por
  `test_module_boundaries.py`. Tests `test_memory_contracts.py` (contratos + e2e
  ChromaDB + dedup + skills + decision_service). `AITHERA_CHROMA_PATH` aísla la
  BD vectorial en tests. `/api/memory/*` intacto por contrato.
- ✅ **M2 — Ingesta proactiva** (`app/memory/ingestion.py`): job email (cada
  `Settings.MEMORY_INGEST_INTERVAL_MIN`, default 20 min) indexa
  `list_inbox_preview` (subject+snippet+sender) en `mem_personal` vía
  `email_service`/`EmailTool` —nunca Gmail directo—, cruza `EmailTriage` ya
  calculada (no llama al LLM), `dedup_key=email_id`. Job calendario (cada
  `MEMORY_INGEST_CALENDAR_INTERVAL_MIN`, default 60 min): `CalendarEvent`
  locales (−7d/+14d, sin límite) + Google `list_events` (solo futuro, fail-soft
  —la API no soporta ventana pasada—), `dedup_key=f"cal:{local:id|google:id}"`.
  Arranque en el `lifespan` de `main.py` (mismo patrón que el Gateway:
  `create_task` + try/except total, jitter inicial); si Google no está
  conectado, pasada "ok, 0 items" sin ruido. Cada pasada escribe un
  `MemoryJobRun` (`ingestion.last_run(job_name)`).
  **[Δ doc 17] nace `app/core/events.py`** (pub/sub in-process, ≤80 líneas:
  `Event` frozen + `subscribe`/`unsubscribe`/`emit`, aislamiento total de
  handlers rotos, comodín `"*"`): la ingesta emite `memory.ingested` (al
  terminar una pasada con items) y `email.triaged` (por email ya categorizado).
  Endpoints aditivos `GET /api/memory/ingest/status` (última pasada + próximo
  run estimado por job) y `POST /api/memory/ingest/run?job=email|calendar|all`
  (fuerza una pasada sin esperar). Tests: `test_events.py` (bus completo),
  `test_memory_ingestion.py` (e2e con `EmailTool` fake — sin credenciales
  Google en CI—, calendario con datos reales de BD, idempotencia de 2ª pasada,
  entrega del evento a un handler de prueba, endpoints). Suite completa: 209
  passed (sin tareas asíncronas colgadas en el teardown del `lifespan`).
- ✅ **M3 — Resumen nocturno + Briefing + tarjeta Hub** (`app/memory/summarizer.py`):
  job diario **03:30 hora LOCAL** (`datetime.now()`, no UTC — a propósito,
  doc 07 §7) que junta `EmailTriage` del día + agenda ya ingestada (M2) +
  turnos de chat, y escribe un item `mem_personal` (`kind=daily_summary`,
  `dedup_key=day:{date}` → re-ejecutar el mismo día sobreescribe). Modelo:
  **Ollama si está sano (coste 0) → proveedor activo → plantilla determinista**
  (nunca se salta el día); salida por `strip_reasoning()` (B21).
  `GET /api/memory/briefing?date=`: resumen (cache si existe, si no
  determinista al vuelo — cero LLM en el critical path del GET) + urgentes
  pendientes (`EmailTriage.category='urgente'` sin ninguna `EmailActivityLog`
  todavía — no acotado por día, "pendiente" es un estado, no un evento del
  día) + agenda del día + top remitentes. `GET /api/memory/stats` extendido
  (aditivo) con `mos_collections` (items por `MemoryType` activo) y
  `mos_days_covered`. Tarjeta **"Memoria"** en el Hub (`Hub.tsx`): resumen de
  hoy en 2 líneas + última ingesta + nº de urgentes, cargada junto al resto de
  paneles (patrón `Promise.all` + `safeSet`, mismo estilo que el digest de
  Email). **Regresión encontrada y arreglada**: ChromaDB 1.5.x NO admite
  `$gte`/`$lte` sobre strings (solo números) — afectaba también a
  `LocalMemoryStore.summarize()` de M1 (nunca se había ejercitado con datos
  reales); se resolvió con `$in` sobre fechas enumeradas (rangos cortos,
  acotado a 1 año) o filtro en Python cuando el campo no es un `date` uniforme
  (`event_start` mezcla fecha y datetime; `timestamp` de conversaciones sí es
  uniforme pero de todos modos se filtra en Python por simplicidad). Test de
  regresión en `test_memory_contracts.py`. **Cierre de fase verificado**:
  `test_criterio_de_cierre_briefing_sin_google` (Gmail desconectado, briefing
  real) + verificación manual contra el backend real del usuario (28
  urgentes pendientes reales, resumen coherente, tarjeta del Hub renderizando
  con datos en vivo). Suite completa: 220 passed.
- ✅ **M4 — Contexto con fuentes + consolidación `chat_service.py`**
  (`app/services/chat_service.py`): pipeline ÚNICO de chat (system prompt +
  memoria + IA + `strip_reasoning`), usado por `POST /api/chat` (`chat.py`) Y
  por el Gateway (`gateway.py::chat_message_handler`) — antes duplicaban esta
  lógica casi entera (doc 12 A4). `build_system_prompt()` combina: prompt base
  + preferencias (colección legacy `user_context`, fuera del MOS a propósito —
  doc 07 no la migra en V0.85) + **memoria del MOS con atribución de fuente**
  vía `memory_router.context()` (conversacional + personal + proyecto + skill
  + decision). **Presupuesto de latencia duro de 300 ms** (`asyncio.wait_for`)
  sobre la llamada al MOS — si excede, contexto vacío, el chat nunca espera
  (doc 07 §8). `answer()` preserva el orden de persistencia pre-existente
  (mensaje del usuario indexado ANTES de llamar a la IA, para no perderlo si
  la IA falla) y el flag `persist_chat_message` (el Gateway sigue sin escribir
  en `ChatMessage`, igual que antes). `/api/chat/stream` (el camino real que
  usa `Chat.tsx`) comparte `build_system_prompt()` pero mantiene su propio
  generador — no puede delegar en `answer()` sin streaming. Import diferido de
  `ai_manager` dentro de `answer()` (patrón ya usado en `email_service.py`,
  necesario para que los tests puedan sustituirlo con `monkeypatch`).
  **Verificado en vivo contra el backend real** (no solo tests): el modelo citó
  correctamente preferencias reales guardadas del usuario ("reuniones por la
  tarde después de las 15:00", "color favorito verde") tanto en `/api/chat`
  como en `/api/chat/stream`, y ambos turnos quedaron en `ChatMessage`. Tests:
  `test_memory_context.py` (presupuesto de latencia forzando un `context()`
  lento, orden de persistencia con IA que lanza excepción, `persist_chat_message`,
  y que `/api/chat` y el Gateway invocan literalmente la misma función).
  Suite completa: 228 passed.
- ✅ **M5 — Hardening, rendimiento y cierre** (doc 07 §10 M5, doc 12 A1/A3):
  **A1 — init async de ChromaDB en background**: `MemoryManager.__init__()`
  pasa a ser INSTANTÁNEO (ya no hace I/O); la carga real de chromadb +
  sentence-transformers vive en `_do_init()`, invocada por
  `initialize_async()` (`asyncio.to_thread`, arrancada como
  `asyncio.create_task` en el `lifespan` — background, no bloqueante) o
  `initialize_sync()` (bloqueante; la usa `tests/conftest.py` a nivel de
  módulo, ANTES de que pytest coleccione ningún test — necesario porque varios
  `pytestmark = pytest.mark.skipif(not memory_router.healthy, ...)` se evalúan
  en collection time, antes de que corra cualquier fixture; sin este fix
  hubiera saltado ~40 tests en silencio). El log "Memory system listo" ahora
  se emite desde dentro de la propia tarea de fondo, cuando de verdad termina.
  **Verificado en vivo contra el backend real**: "Application startup
  complete" a las 10:51:14, pero "Memory system listo" no llegó hasta las
  10:51:23 — **9 s en los que el backend ya aceptaba peticiones** en vez de
  estar bloqueado (antes de M5, esos 9 s bloqueaban el arranque siempre).
  **A3 — índices de rendimiento** (migración 14.ª `f6a7b8c9d0e1_v085_m5_indices`,
  idempotente): 8 columnas de filtro frecuente indexadas —
  `email_activity_log(action_type, read, timestamp)`, `email_triage(created_at)`,
  `agent_executions(status)`, `tasks(status)`, `calendar_events(start_date)`,
  `chat_messages(created_at)` (antes solo 3 `index=True` en toda la BD).
  Tests de rendimiento (doc 12 §6): `test_startup_time.py` (constructor de
  `MemoryManager` <0.1 s + `import app.main` aislado en subproceso <2 s, sin
  disparar la carga de memoria) y `test_chromadb_search_perf.py` (búsqueda
  <200 ms con 10k items — corpus con embeddings sintéticos para que preparar
  el test sea rápido, query con el embedding function real). **Bump de
  versión** 0.8.0 → 0.8.5 en las 3 ubicaciones sincronizadas + banners `.bat`.
  Suite completa: **232 passed, 0 skipped**. **V0.85 (MOS Skeleton) CERRADA.**
  Alcance NO incluido en M5 (no está en la fila M5 de doc 07 §10 — ver deuda
  técnica): compactación/`lifecycle.py` (RFC-007) y `httpx` con conexiones
  persistentes (doc 12 A2) quedan para V0.9.

**V0.87 — WPMS (Workspace & Project Management, doc 18) — CERRADA sobre `master`**:
la capa operativa (estado en SQL) que organiza proyectos/milestones/tareas
vara-Linear; el conocimiento permanente sigue en el MOS (`mem_project`). Sprints
W1 → W2a-W2e (W2 dividida por decisión de producto: drag&drop core + ratón y
teclado a la par, luego pulido/edición completa de agentes/esqueleto GitHub-
orquestador) → W3b (Kanban) → W4 (integración MOS/eventos/briefing/Hub).
**Bloque completo, suite backend 260 passed.**
- ✅ **W1 — Modelo + progreso + endpoints** (`app/workspace/`): extensión ADITIVA
  del modelo real `Project`/`Task` (no reescritura) + entidad nueva `Milestone`
  (el eje de versión). `Project +=` `repo_path·current_version·target_version·
  start_date·tags·docs·archived_at`; `Task +=` `milestone_id(ix)·checklist·
  depends_on·estimate·order_index·closed_at·links` (JSON donde aplica; `order` es
  palabra reservada → `order_index`). Referencias cross-módulo
  (`Task.milestone_id`, `Milestone.project_id`) como Integer plano indexado —NO
  ForeignKey— porque `init_db()` corre `create_all` al importar, antes de que
  workspace registre `Milestone` (mismo criterio laxo que `Conversation.agent_id`;
  la integridad la lleva el endpoint). Migración Alembic 15.ª
  `a7b8c9d0e1f2_v087_wpms_model` **aditiva e idempotente** (verificada en los dos
  caminos reales: no-op sobre BD ya creada por `create_all`, y ADD real sobre BD
  vieja con datos intactos). **Progreso automático** (`workspace/progress.py`,
  función pura testeable): `done/total` por conteo, ratio 0-1 (el frontend pinta
  `progress*100`); `DONE_STATUSES={done,completed}` (coincide con el filtro real
  del `telegram_adapter`); lo escribe `workspace/service.py` por evento
  (crear/editar/borrar tarea → recalcula `Project.progress`), NUNCA el usuario.
  **Versionado**: completar un milestone propaga `current_version`←version y
  activa el siguiente `planned` (`service.complete_milestone`); el destilado a
  `mem_project` + eventos son hooks vacíos hasta W3. `endpoints/workspace.py`
  **absorbe `/api/projects` y `/api/tasks` con contrato idéntico** (patrón split
  email; `projects.py`/`tasks.py` eliminados) + `/api/milestones` (CRUD +
  `/complete`) + `/api/workspace/progress`. Disciplina modular (doc 16): API
  pública en `app/workspace/__init__.py` (`Milestone`, `workspace_service`,
  `compute_progress`), fronteras vigiladas por `test_module_boundaries.py`
  extendido (`app.workspace.models/.service/.progress` internos). Tests:
  `test_workspace_model.py` (13: progreso puro, contrato rutas viejas, campos
  nuevos, Milestone CRUD, progreso automático, `closed_at`, versionado, borrado
  → backlog). Suite completa: **254 passed**.
- ✅ **W2a — Vista Proyecto + popup Task (UI ratón-primero)** (`frontend/src/pages/Workspace/`):
  vista de una columna (panel de proyectos + detalle: cabecera versión/estado,
  barra de progreso del milestone activo, enlaces repo/docs, lista de milestones
  con progreso, lista de tareas, actividad reciente). `Modal.tsx` (shell: Esc +
  clic-fuera + Guardar visible) + `TaskPopup`/`ProjectPopup`/`MilestonePopup`
  (todo editable por ratón; checklist con checkboxes; links commit/pr/mission/
  decision; Completar milestone → versionado). Progreso se recalcula en vivo al
  marcar una tarea (verificado e2e contra el backend real). Routing: `/workspace`
  nuevo, `/projects`+`/tasks` → `Navigate` a `/workspace`, `Sidebar` unifica en un
  ítem "Workspace", `Hub` repunta sus `navigate()`; `Projects.tsx`/`Tasks.tsx`
  eliminados. `lib/api.ts` extendido (tipos + métodos milestones/progress).
  `tsc --noEmit` 0 errores, `vite build` OK. El board Kanban + drag&drop es W2b.
- ✅ **W2b — Lienzo espacial: tarjetas arrastrables/redimensionables + estantería**
  (`frontend/src/pages/Workspace/`): el panel de proyectos pasa de lista fija a
  tarjetas-ventana. `useWindowCard.ts` — mecánica con Pointer Events nativos
  (sin librería nueva): mutación directa del DOM durante el gesto (60fps),
  estado confirmado solo en `pointerup`; resize acotado a 3 asas (derecha=ancho,
  abajo=alto, esquina=ambos) para no acoplar mover posición con redimensionar.
  Persistencia en `localStorage` (`aithera.workspace.cardLayouts`), nunca SQL ni
  `mem_project` — es preferencia de pantalla, no conocimiento (doc 18 regla
  rectora). Fondo ambiental: reusa `AICore.tsx` tal cual (sin modificarlo),
  atenuado — **no** es el AVCS completo de doc 13 (V0.82/V0.83, sin construir).
  `Shelf.tsx` (estantería, lista todos los proyectos para que uno abierto nunca
  se pierda detrás de otro) + `ProjectCard.tsx` (header arrastrable, doble clic
  expande al área del Workspace, contenido adaptativo por alto disponible,
  carga perezosa de milestones/tareas por tarjeta) + `WorkspaceCanvas.tsx`.
  **Bug real encontrado y arreglado en verificación en vivo** (no solo
  tsc/build): dos proyectos abiertos por primera vez caían en la misma
  posición por defecto, superpuestos — el fallback de `setLayout()` usaba
  índice 0 en vez del real; corregido derivando el stagger de `project_id`
  (estable) en vez de un índice de array. Verificado en vivo contra el dev
  server real con `PointerEvent`s nativos (la herramienta de drag automatizado
  no está disponible en este entorno): arrastre con delta exacto, 3 asas
  independientes, expandir/restaurar preserva el rect libre, minimizar, y
  soltar sobre la estantería la minimiza automáticamente.
- ✅ **Fix W2b (15-jul)**: 3 asas → **8 asas** (4 bordes + 4 esquinas);
  `resolveResize()` reescrito — los bordes norte/oeste clampan tamaño primero
  y derivan la posición de cuánto se movió REALMENTE el borde (evita que la
  tarjeta "salte" al tocar el mínimo). `Shelf.tsx` gana arrastrar-para-sacar
  (fantasma que sigue al cursor; la tarjeta real no existe hasta soltar,
  patrón estándar cuando el objetivo del arrastre no está montado).
- ✅ **W2c — Tarjetas de agente reordenables** (`frontend/src/pages/Workspace/`):
  cada tarjeta de proyecto muestra sus agentes reales. Migración 16.ª
  (aditiva): `Agent += project_id·skills·icon`. **Bug real encontrado en
  pruebas de la migración**: `project_id` se intentó como ForeignKey real
  primero (mismo archivo que `Project`, sin problema de orden) pero SQLite no
  soporta añadir una columna con constraint FK vía `ALTER TABLE ADD COLUMN`
  fuera de "batch mode" — confirmado con una migración de prueba que falló a
  mitad camino; corregido a Integer suelto, mismo criterio que
  `Milestone`/`Task.milestone_id` de W1, por un motivo distinto pero igual de
  real. `AgentChip.tsx` (marco de estado gris/rojo/azul-animado vía
  conic-gradient enmascarado, CSS puro) + `AgentsSection.tsx` (reorden 1D por
  arrastre — busca el chip más cercano al puntero, persistido en
  `localStorage`) + `AgentCreatePopup.tsx`/`AgentDetailPopup.tsx`. Hueco
  "Automatizaciones" (stub V0.9). `tsc`/`vite build` limpios; suite backend
  **254 passed**; migración verificada en los dos caminos reales (no-op +
  ADD con datos).
- ✅ **Fixes post-W2c (15-jul, reportados por el usuario)**: (1) **crear agente
  no funcionaba** — causa raíz confirmada: la migración 16.ª nunca se aplicó
  al Postgres real (mismo patrón que el incidente de W1: probada solo contra
  SQLite de usar-y-tirar). `alembic upgrade head` aplicado contra el Postgres
  real, datos intactos. (2) **errores de guardado silenciosos en los 4 popups**
  del Workspace — `request()` descartaba el `detail` real de FastAPI y los
  popups no tenían `catch`, así que cualquier fallo se veía como "no pasa
  nada". Arreglado en la raíz (`request()` parsea el detail; `ErrorBanner`
  compartido en los 4 popups). (3) **reorganización EN VIVO al redimensionar**
  — `useDragResize` gana `onLiveResize` (dispara en cada `pointermove` de un
  resize, desacoplado de `onCommit`); `AgentsSection` pasa a montarse siempre
  y ocultarse por CSS (evita refetch en cada cruce de umbral durante el
  gesto). (4) **catálogo de skills con filtro por categoría**
  (`SkillPickerPopup.tsx`, `frontend/src/data/skillsCatalog.json`, generado
  de `msitarzewski/agency-agents` — 254 entradas/17 categorías, catálogo
  estático sin backend). Verificado en vivo contra el backend real: crear
  agente completo, filtro de skills (Marketing → 36 resultados), y el
  contenido de la tarjeta cambiando ANTES de soltar el ratón al redimensionar.
- ✅ **W2d — Agente en pantalla completa + panel de proceso** (`AgentFullscreen.tsx`):
  doble clic en un icono de agente lo abre ocupando el área del Workspace
  (vive en `WorkspaceCanvas`, no en la `ProjectCard` chica que lo abrió, con
  z-index por encima de cualquier tarjeta). **Alcance honesto** (auditado
  `agent_manager.py` antes de diseñar, no después): la ejecución hoy es un
  placeholder de V0.5 (demo fija, sin razonamiento real) — el panel muestra
  tarea → estado real (sondeo cada 1.8s) → resultado real + `tool_calls`,
  nunca streaming inventado; nota visible explicándolo. Icono (emoji) +
  `is_active` editables vía `api.updateAgent`. Sincronización entre el chip
  pequeño y la pantalla completa (dos instancias con datos propios) vía un
  `refreshTick` que sube por `WorkspaceCanvas → ProjectCard → AgentsSection`.
  Verificado en vivo end-to-end: crear agente → pantalla completa → lanzar
  tarea real → sondeo detecta "Completada" con resultado real → cambiar
  icono/estado → cerrar → el chip refleja los cambios sin recargar.
- ✅ **W2e — Esqueleto GitHub/orquestador + edición completa de agentes + pulido**
  (peticiones directas del usuario, 15-jul): migración 17.ª
  `c9d0e1f2a3b4_v087_wpms_w2e_project_agent_skeleton` (aditiva, aplicada al
  Postgres real de inmediato — ya van 3 incidentes de "migración nunca
  aplicada", esta vez se verificó en el mismo paso): `Project.github_url`
  (solo el enlace — **sin integración real de GitHub**, eso es V1.2 MCP;
  `ProjectPopup.tsx` gana el campo + botón stub "Crear repositorio" con nota
  explicativa, nunca llama a ninguna API) y `Agent.role` (reservado para
  `"orchestrator"`, sin UI ni lógica — esqueleto puro documentado en
  `PLAN_MAESTRO_2026/14_TIE_COGNITIVE_RUNTIME_DISENO.md` §4.3c: el TIE v1
  (V1.0) creará el orquestador por proyecto con autoridad limitada a los
  agentes de su mismo `project_id` y a las carpetas de ese proyecto — cross-
  referenciado en `03_ROADMAP_ACTUALIZADO.md` §5). **Carpeta local real**:
  primer uso real de IPC de Electron (`preload.cjs` estaba vacío a propósito
  como punto de extensión) — `dialog:pick-folder` en `main.cjs` +
  `window.aithera.pickFolder()` expuesto vía `contextBridge`, botón 📁 en
  `ProjectPopup.tsx` que degrada con gracia (se oculta) fuera de Electron.
  **"Modelo IA" dinámico**: `useModeloIAOptions.ts` — "Flexible según
  necesidad" (antes "Generic") + solo los proveedores con
  `AIProviderEntry.is_configured` (vía `api.getConfiguredProviders()`); se
  eliminó `"custom"` (no usable) y la lista fija hardcodeada; usado en
  `AgentCreatePopup.tsx` y en el nuevo modo edición de `AgentFullscreen.tsx`
  — si el usuario conecta/desconecta un proveedor en Ajustes, la lista se
  actualiza sola. **Edición completa de agentes**: `AgentFullscreen.tsx` gana
  un modo "Editar" (nombre/descripción/Modelo IA/skills/herramientas
  permitidas/timeout, con `SkillPickerPopup` reutilizado) — antes solo
  icono/`is_active` eran editables. **Un solo clic abre pantalla completa**:
  se retiró `AgentDetailPopup.tsx` (popup de solo lectura redundante);
  `AgentChip.tsx` pierde `onOpenFullscreen`/doble-clic, `onOpen` ahora siempre
  abre `AgentFullscreen`. **Indicador "trabajando…"** estilo WhatsApp: punto
  verde pulsante en la esquina del icono (tamaño "icon") + texto
  "escribiendo…" en verde (tamaños "compact"/"full") cuando el agente tiene
  una `AgentExecution` en `pending`/`running`; `AgentsSection.load()` pasa a
  pedir ejecuciones de TODOS los agentes en todos los tamaños (antes solo en
  "full" o para inactivos) — pocos agentes por proyecto, coste bajo (doc 18
  regla 6). **Pulido CSS**: `.glass-surface` gana un borde azul eléctrico fino
  (`rgba(94,168,255,0.35)`, antes casi invisible en `rgba(255,255,255,0.06)`)
  — afecta a TODAS las tarjetas y popups del Workspace de una sola vez;
  `.agent-ring-glow` gana un `::after` — un punto de 6px que sobresale del
  grosor del anillo (2px), fijo en el punto más brillante del "cometa" y que
  rota CON él al ser hijo del mismo elemento animado. Suite backend
  **254 passed** (sin regresión). Verificado en vivo contra el backend y
  frontend reales: dropdown "Modelo IA" mostrando solo Ollama/MiniMax
  (los dos conectados, sin `custom` ni `claude_code` desconectado), crear
  agente funcionando de nuevo, clic simple abriendo pantalla completa,
  edición completa guardando y reflejándose en el chip al cerrar, borde
  azul confirmado por `getComputedStyle`, punto del anillo confirmado
  (6×6px, con `box-shadow` de brillo).
- ✅ **W3b — Board Kanban + drag&drop de tareas + atajos + panel `(?)`**
  (`TaskBoard.tsx`, nuevo): 3 columnas (Pendiente/En progreso/Hecha, los
  mismos 3 valores que ya usaba `TaskPopup`) solo cuando la `ProjectCard` está
  **expandida** (ancho completo del lienzo) — con la tarjeta compacta el
  `TaskList` plano de W2b sigue siendo la vista, 3 columnas no caben con
  sentido en poco ancho. **Arrastre**: mismo patrón nativo de Pointer Events
  ya usado en `AgentsSection.tsx` (sin librería, doc 16 principio 5),
  extendido de 1 a 3 columnas — `colsRef` espeja el estado en un ref para que
  `endDrag` lea siempre el valor más reciente sin closures obsoletas (mismo
  motivo que `orderRef` en W2c). Al soltar, solo se renumera `order_index` de
  la columna de DESTINO (quitar un elemento no rompe el orden relativo de los
  que quedan); el `status` de la tarea arrastrada cambia solo si cruzó de
  columna. Persistencia no-optimista: `ProjectCard.reorderTasks()` hace los
  `PATCH` y siempre recarga desde el backend después (mismo patrón que el
  resto del Workspace). **Alta rápida por columna**: botón "+" en cada
  columna + `TaskPopup` gana `defaultStatus` (la tarea nace ya en esa
  columna). **Atajos de teclado** (mouse+teclado a la par, doc 18 decisión
  W2a/W2b — el mismo criterio se extiende aquí): `N` nueva tarea en la
  columna seleccionada, `Enter` abre la tarea seleccionada, `↑/↓` mueve
  dentro de la columna, `←/→` cambia de columna, `1/2/3` mueve la tarea
  seleccionada de columna sin arrastrar (accesibilidad), `?` abre/cierra el
  panel de ayuda con la lista completa. El `<div tabIndex={0}>` del board
  recibe foco al montar/cuando no hay un popup abierto encima (prop
  `disabled`, evita que los atajos compitan con lo que se escribe en
  `TaskPopup`/`MilestonePopup`); deliberadamente **sin atajo de borrar**
  (una tecla que elimina sin confirmación es un riesgo, doc de seguridad del
  proyecto — borrar sigue siendo solo el botón explícito del popup). Suite
  backend **254 passed** (sin cambios de backend — `order_index`/`status`
  ya existían desde W1, solo estaban sin usar). Verificado en vivo contra el
  backend y frontend reales: crear tareas en las 3 columnas, arrastre entre
  columnas confirmado por API (`status`/`order_index`/`closed_at`
  persistidos), navegación con flechas, `1/2/3` moviendo de columna
  (confirmado por API), `Enter` abriendo la tarea seleccionada, `N` con
  `defaultStatus` correcto, panel `?` mostrando los 7 atajos.
- ✅ **Fixes post-W3b (15-jul, reportados por el usuario)**: (1) **etiquetas de
  "+"** — el "+" de Milestones y el de cada columna del Kanban no decían qué
  creaban; ahora "+ Milestone" y "+ Tarea". (2) **panel de ayuda (?) invisible**
  — vivía escondido dentro del Kanban (solo con la tarjeta expandida, y ni
  siquiera coloreado); se retira de ahí y nace `HelpPanel.tsx` (`HelpButton` +
  `windowShortcuts()` compartidos): botón redondo AMARILLO (`signal.warn`,
  `#E8B95E`) SIEMPRE visible en la cabecera de toda tarjeta-ventana (proyecto
  Y agente), un único panel por tarjeta que combina los gestos de ventana
  (arrastrar/redimensionar/expandir) con los atajos del Kanban cuando aplica;
  la tecla `?` del board delega en el mismo estado del botón (`onToggleHelp`)
  en vez de duplicar un panel propio. (3) **tarjetas de agente = tarjetas de
  proyecto** — pedido explícito: abrir un agente ya NO es siempre pantalla
  completa. `AgentFullscreen.tsx` (W2d/W2e) se retira; nace
  `AgentWindowCard.tsx`, que reusa EXACTAMENTE la misma mecánica de
  `useWindowCard.ts` (arrastre/8 asas de resize/expandir/"estantería") sobre
  su PROPIA instancia de `useWorkspaceLayouts` (clave de localStorage
  `aithera.workspace.agentCardLayouts` — los espacios de id de `Agent` y
  `Project` son independientes, no pueden compartir clave). `useWorkspaceLayouts`
  gana un `storageKey` parametrizable + `openIds` (deriva qué tarjetas no
  están "guardadas" directamente del store persistido — los agentes no tienen
  una estantería visual global, así que `WorkspaceCanvas` no tiene de otro
  modo cómo saber cuáles reabrir al recargar la página). Ventanas de agente
  flotan con un offset de z-index fijo (+100000) por encima de las tarjetas de
  proyecto — dos instancias independientes del hook, dos contadores de zIndex
  independientes, el offset evita ambigüedad de apilado sin compartir estado.
  Contenido adaptativo por alto disponible (mismo patrón que `ProjectCard`):
  solo cabecera si muy pequeña, +info (skills/tools/timeout o el formulario de
  edición) a partir de 140px, +chat/proceso a partir de 320px o expandida
  (ahí recupera el layout de dos columnas original). "Cerrar" un agente
  equivale a `sendToShelf` (misma función que minimizar un proyecto) — no hay
  estantería visual para agentes, pero el chip en `AgentsSection` sigue siendo
  la forma de reabrirlo. Verificado en vivo con Pointer Events nativos
  (herramienta de arrastre automatizado no disponible en este entorno): abrir
  un agente nace en ventana 360×280 (no pantalla completa), redimensionar con
  el asa SE (360×280 → 480×380 exacto), doble clic expande a `inset-0` con
  layout de dos columnas, cerrar vuelve al chip, reabrir preserva el último
  tamaño/posición (persistencia confirmada). `tsc`/`vite build` limpios.
- ✅ **W4 — Integración MOS/eventos/briefing + Hub** (doc 18 §5, §7, §10):
  cierra el bloque completo de WPMS. **Eventos** (`app/workspace/service.py`,
  `app/core/events.py`): los 5 del diseño —`task.created`, `task.status_changed`
  (`{task_id, from, to}`), `task.closed`, `milestone.completed`,
  `project.progress_changed`— emitidos en los puntos reales (crear/editar/
  borrar tarea, completar milestone). **Nota de concurrencia real**: `events.emit`
  exige un event loop corriendo en el hilo (`asyncio.get_running_loop()`); los
  endpoints de `workspace.py` que tocan eventos/MOS (`create_task`,
  `update_task`, `delete_task`, `complete_milestone`, el nuevo
  `archive_project`) pasan a `async def` para ejecutarse sobre el loop en vez
  de en el threadpool de FastAPI —si se quedan `def` sync, `emit()` calla en
  silencio (best-effort por diseño, doc 17, pero silenciosamente mudo no es
  lo mismo que funcionando—. **Destilado a `mem_project`** (SOLO hechos
  permanentes, nunca estado operativo, doc 18 §5.1 primera línea):
  `_on_milestone_completed` (resumen del milestone, `dedup_key=milestone:{id}`),
  nuevo **archivado de proyecto** (`POST /api/projects/{id}/archive` — sella
  `archived_at`, idempotente, resumen final a mem_project
  `dedup_key=project_archived:{id}`; antes `archived_at` era una columna sin
  ninguna acción de usuario que la tocara desde W1 — cabo suelto real,
  cerrado aquí con botón "Archivar" en `ProjectPopup.tsx` + badge "Archivado"
  en `Shelf.tsx`). **Decision API**: `on_task_closed` — si la tarea trae
  `links.decision`, registra el hecho en `decisions` vía `decision_service`
  (fuente SQL + espejo `mem_decision`); sin decision, no escribe nada al MOS
  (estado operativo puro). **Briefing** (`workspace_service.briefing_snapshot`,
  vive en `app/workspace/` por disciplina modular, doc 16 — `summarizer.py`
  solo la llama y mezcla el resultado): milestone activo + progreso por
  proyecto no archivado, deadlines próximos (7 días), tareas de alta
  prioridad abiertas, bloqueos (`depends_on` con alguna dependencia sin
  cerrar), actividad reciente — exactamente lo pedido en doc 18 §7, sin
  Gmail/LLM en caliente. `GET /api/memory/briefing` gana la clave `workspace`
  (aditivo). **Hub**: tarjeta "Memoria" (M3) extendida con deadlines
  próximos/tareas bloqueadas cuando hay alguno (sin llamada extra, mismo
  briefing); "Proyectos activos" corregido para excluir archivados (archivar
  es independiente de `status`, un proyecto archivado con `status="active"`
  seguía apareciendo como activo — bug real encontrado en esta misma pasada
  de auditoría). **Auditoría de cabos sueltos** (pedida explícitamente): (1)
  `Project.github_url` (W2e) cross-referenciado en
  `PLAN_MAESTRO_2026/03_ROADMAP_ACTUALIZADO.md` §7 (V1.2) con la conexión real
  al MCP de GitHub. (2) doc 18 §7 prometía `WorkspaceAction` para el
  Automation Engine — no existía en
  `PLAN_MAESTRO_2026/11_AUTOMATION_ORCHESTRATOR_RFC.md`; añadido junto con los
  5 nombres de evento concretos en la sección de `EventTrigger`. (3) doc 18
  §7 prometía que el Learner (doc 15) consumiría estimado-vs-real/bloqueos del
  WPMS — `15_LEARNING_SYSTEM_DISENO.md` no lo mencionaba; añadida la fila con
  los campos reales (`Task.estimate`, `depends_on`, los 3 eventos de tarea).
  (4) doc 11 §A.3 (`daily_briefing`) actualizado para reflejar que el briefing
  ya trae `workspace` desde V0.87, no solo email/calendario. Tests nuevos en
  `test_workspace_model.py` (Parte 7, 6 tests): milestone completado distila a
  mem_project, tarea cerrada con/sin decision, eventos
  task.created/status_changed/closed/project.progress_changed (via
  monkeypatch de `emit`), archivar es idempotente y distila, briefing_snapshot
  con datos reales. Suite completa: **260 passed** (234 previos + 6 nuevos de
  W4, 20 acumulados de W2c-W3b). Verificado en vivo contra el backend y
  frontend reales: crear/archivar un proyecto real, `GET /api/memory/briefing`
  devolviendo `workspace` con el milestone activo real del usuario
  ("Niide y El Círculo Dárico" 1/2) y actividad reciente real, Hub sin errores
  de consola. **V0.87 WPMS — BLOQUE CERRADO.**

**V0.9 — Automation Engine + ApprovalGate (en curso sobre `master`; plan de
sesiones detallado en `PLAN_MAESTRO_2026/20_V09_PLAN_SESIONES.md`, sprints
A1·A2a·A2b·A3·A4).**
- ✅ **A1 — ApprovalGate (el primitivo genérico) + esquema v0.9 + migración del
  email-confirm** (`app/automation/`, módulo nuevo): el ApprovalGate es EL
  cimiento que reusan V0.9 (acciones), V1.0 (steps del Orchestrator con
  `approval_required`) y V1.1 (Hermes/skills). Migración Alembic 18.ª
  `d0e1f2a3b4c5_v09_automation_schema` (esquema-primero, patrón M1/W1, aplicada
  al Postgres real de inmediato y verificada — datos intactos 7/6/9): crea las 3
  tablas de V0.9 por adelantado (`approvals`, `automation_rules`,
  `automation_executions` —estas dos últimas se USAN en A2b, aquí solo se crean—)
  + columna aditiva `agent_executions.checkpoint_data` (para que en V1.0 los
  planes multi-paso reanuden con el MISMO gate sin migración nueva). Modelos en
  `app/automation/models.py` (disciplina modular doc 16: API pública en
  `__init__.py`, fronteras en `test_module_boundaries.py`). **`ApprovalGate`**
  (`approval.py`, singleton `approval_gate`): `request_approval` (persiste
  `Approval(status=pending)`, notifica por el canal de origen best-effort, emite
  `approval.requested`) · `resolve` (**idempotente por claim atómico** —un
  `UPDATE ... WHERE status=pending` reclama la transición, solo el primer resolver
  ejecuta; reconstruye la acción desde `(action_type, action_payload)` vía el
  **registro de ejecutores** inyectable —para que A3 enchufe acciones reales sin
  que el gate importe `actions.py`, evita ciclo—; escribe en la **Decision API**;
  emite `approval.resolved`) · `list_pending` · `get`. **Reanudable tras
  reinicio**: todo el estado vive en la fila `approvals`, así que un gate nuevo
  resuelve una aprobación creada antes (probado). **Δ8 `gateway.notify(channel,
  target, OutboundMessage)`**: push saliente sin envelope entrante (envelope
  sintético → `adapter.deliver`, cero cambios en adapters; el Hub no es canal del
  Gateway → sondea `GET /api/automation/approvals`). Endpoints `automation.py`
  (`/api/automation`): `GET /approvals`, `GET /approvals/{id}`, `POST
  /approvals/{id}/resolve`. **Migración del email-confirm**: `/api/email/send`
  con `confirmed:true` sigue INTACTO (contrato congelado por
  `test_email_contracts`); se registra en el `lifespan` el ejecutor `email_send`
  para que agentes/automatizaciones pidan aprobación de un envío (A3 conectará el
  resto de acciones). Tests: `test_approval_gate.py` (10: pending, aprobado
  ejecuta + escribe decision, rechazado no ejecuta, **reanudación tras reinicio**,
  **idempotencia doble-resolve**, sin-ejecutor no rompe, eventos, endpoints,
  ejecutor email_send registrado) + `test_module_boundaries` extendido.
  **Verificado en vivo contra el Postgres real** (no solo SQLite de tests):
  crear→pending→resolver ejecuta con el payload correcto, doble-resolve
  idempotente, decisión escrita y enlazada, limpieza sin ensuciar la BD. Suite:
  **279 passed** (269 previos + 10 de A1), 1 fallo **pre-existente y ajeno**
  (`test_summarize_filtra_por_rango_de_fechas`, ChromaDB del MOS V0.85 — reproduce
  sin los cambios de A1, trazado como tarea aparte).
- ✅ **A2a — Infraestructura de jobs: APScheduler + lifecycle.py + httpx persistente**
  (doc 20 §4·A2a; A2 se dividió A2a/A2b por carga, igual que W2→W2a-e):
  **APScheduler** (`app/automation/scheduler.py`, singleton `scheduler_service`,
  `AsyncIOScheduler` con `coalesce`/`max_instances=1`/`misfire_grace`) entra como
  el planificador ÚNICO — los jobs asyncio de V0.85 (ingesta M2, resumen nocturno
  M3) dejan de ser `asyncio.create_task(_loop())` y pasan a `add_interval_job`/
  `add_cron_job`; el wiring vive en el `lifespan` de `main.py` (composition root,
  para que el scheduler NO dependa de `app.memory`); `run_summarizer`/
  `ingest_email`/`ingest_calendar` siguen siendo las funciones de trabajo (las
  llama el scheduler y el endpoint `/api/memory/ingest/run`); se retiraron los
  `_loop`/`start_background_jobs`/`start_summarizer_job` (código muerto).
  **`app/memory/lifecycle.py`** (`MemoryLifecycleManager`, singleton
  `lifecycle_manager`, doc 08 RFC-007 — NUNCA se construyó en V0.85, [Δ] doc 11):
  job nocturno (04:00 local, tras el summarizer) que **destila** la memoria —
  (1) **dedup** semántico (coseno >0.97 mismo tipo → fusiona, conserva el de
  metadata más rica, numpy), (2/3) **prune** de items crudos viejos (fuera de la
  ventana HOT 30d) **cuyo día YA tiene resumen** (el summarizer lo garantiza) —
  con salvaguardas DURAS (nunca borra `pinned`, `category=urgente`,
  `kind=daily_summary`, ni `mem_decision`/`mem_skill`; `mem_error`/`mem_automation`
  detalle 90d), (4) **archive** al vault Markdown antes de podar
  (`vault.append_archive_entries`); **presupuesto** `MEMORY_BUDGET_MB` (512): si
  la BD vectorial lo supera, aprieta la ventana HOT (30→21→14→7). Micro-batch
  ≤500/noche, escribe `MemoryJobRun`, emite `memory.compacted {pruned,merged,tier}`.
  **httpx persistente** (doc 12 A2): un `AsyncClient` por proveedor IA (lazy en
  `BaseAIProvider._get_client`, cerrado en shutdown vía `ai_manager.aclose()`),
  timeout POR REQUEST — antes se abría un `async with httpx.AsyncClient()` por
  llamada (+100-300ms de handshake TLS en el primer chunk); tocados los 5
  providers + `list_ollama_models`. **Cooldown del Gateway** (doc 12 A8):
  `Gateway.dispatch` gana un guard anti-flood por `(canal, user_ref)` con reloj
  monotónico (`GATEWAY_COOLDOWN_S`, default 1s, 0=off) — corta loops de mensajes
  sin molestar al chat humano. Settings nuevos: `MEMORY_BUDGET_MB`,
  `MEMORY_LIFECYCLE_HOUR`, `AUTOMATION_ENABLED`, `GATEWAY_COOLDOWN_S`.
  `requirements.txt +APScheduler==3.11.0`. Tests: `test_lifecycle.py` (8: dedup
  fusiona/respeta distintos, prune borra-con-resumen pero respeta pinned/urgente/
  resumen, prune NO borra sin resumen, `mem_decision` intacta, presupuesto aprieta
  ventana, `MemoryJobRun`, evento `memory.compacted`). Suite: **278 passed**
  (el pre-existente `test_summarize_filtra…` era un flake de ChromaDB frío;
  además la tarea de fondo lo arregló con reloj local en `store()` — commit aparte).
- ✅ **A2b — Motor de reglas + Triggers + Conditions** (doc 20 §4·A2b): el
  corazón del AE. `app/automation/triggers.py`: `Trigger(ABC)` congelado
  (`evaluate(ctx)`+`arm(engine,rule_id)`+`disarm()`) — trigger nuevo =
  implementar la interfaz, cero cambios en `engine.py` (P06 §4, probado
  literalmente en un test). **`ScheduleTrigger`** (cron/interval, arma un job
  real en `scheduler_service` de A2a — el propio disparo del cron ES el hecho,
  `evaluate()` siempre da `TriggerEvent`). **`EventTrigger`** (se suscribe a
  `app/core/events.py` por nombre exacto + `payload_filter` opcional;
  `event_key_field` deriva el `event_key` de idempotencia del payload) —
  **consume sin cambios los eventos que el WPMS (V0.87) ya emite**
  (`task.created/status_changed/closed`, `milestone.completed`,
  `project.progress_changed`, Δ1 doc 20 §1) además de los del MOS
  (`memory.ingested`, `email.triaged`). Stubs con interfaz: `ConditionTrigger`,
  `PatternTrigger` (V1.2, LLL), `MemoryTrigger` (V1.2), `WebhookTrigger` (V1.x).
  `app/automation/conditions.py`: `Condition(ABC)` + `And`/`Or`/`Not`
  composables; `CooldownCondition` (lee `automation_executions`, sin estado en
  memoria — sobrevive a un reinicio) y `TimeWindowCondition` (franja horaria
  LOCAL, soporta cruzar medianoche). Stub `UserStateCondition` (V1.x).
  `app/automation/engine.py`: `AutomationEngine` — `load_rules()` arma todas
  las `enabled=True` (arrancado en el `lifespan` TRAS APScheduler y TRAS los
  adapters del Gateway, como pide el doc); `handle_trigger(rule_id, ctx)` es el
  punto de entrada único de CUALQUIER trigger armado, con **aislamiento total**
  (una regla rota jamás mata al motor ni afecta a otras — ni siquiera propaga al
  handler de `events.py`/job de APScheduler que la invocó) e **idempotencia**
  real (`(rule_id, event_key)` con un `ok` previo nunca se re-ejecuta). El
  registro `action_type→executor` es inyectable (A3 lo rellena; en A2b vacío →
  se audita como `skipped` con motivo, nunca rompe). La emisión de
  `automation.rule_fired` queda para A4 a propósito (doc 17 §4, su turno). Barrel
  `app/automation/__init__.py` ampliado con la API completa de A2a/A2b (incluye
  `scheduler_service`, antes importado directo — ya no, fronteras coherentes);
  `test_module_boundaries` extendido (`scheduler`/`engine`/`triggers`/
  `conditions` internos). Tests: `test_automation_isolation.py` (10: trigger
  nuevo sin tocar el engine, idempotencia, aislamiento ante excepción propia,
  aislamiento ante trigger roto, sin-ejecutor→skipped, condición no
  cumplida→skipped, And/Or/Not, TimeWindow con reloj fijado por monkeypatch,
  Cooldown con BD real) + `test_event_trigger.py` (6: dispara al emitir,
  **dispara con un evento real del WPMS** (`milestone.completed`), filtra por
  payload, disarm dejar de escuchar, ScheduleTrigger arma/desarma un job real y
  dispara a mano, `ScheduleTrigger()` sin cron/interval lanza). **Verificado en
  vivo contra el Postgres real** (primera vez que el motor lee/escribe de
  verdad `automation_rules`/`automation_executions`, creadas en A1 pero nunca
  ejercitadas contra Postgres): crea regla real → arma → emite evento real →
  ejecuta con el payload correcto → escribe la ejecución → reemitir el mismo
  hecho NO duplica (idempotencia confirmada en Postgres, no solo SQLite de
  tests) → limpieza sin ensuciar la BD. Suite: **294 passed** (278 previos + 16
  de A2b).
- ✅ **A3 — Acciones + reglas predefinidas + UI** (doc 20 §4·A3): que el AE por
  fin haga cosas. `app/automation/actions.py`: `Action(ABC)` congelado + 5
  acciones reales, todas cableando sobre APIs YA EXISTENTES (el AE nunca
  reimplementa lógica de negocio): **`TelegramMessageAction`** (`gateway.notify`
  de A1; `config.text` literal o `config.source` ∈ `daily_briefing`/
  `system_monitor`/`urgent_email` para construir el texto en el momento —
  `daily_briefing` reusa `gather_day_data`+`get_cached_summary` de `summarizer.py`
  con el bloque `workspace` ya incluido, `system_monitor` usa
  `ai_manager.health_check()`, `urgent_email` resuelve remitente/asunto contra
  `EmailTriage` porque el evento solo trae `email_id`); **`EmailSummaryAction`**
  (reusa literalmente `GET /api/email/digest`, V0.7.3 B7 — cero lógica
  duplicada); **`ChatQueryAction`** (reusa `chat_service.answer()`, V0.85 M4);
  **`AgentTaskAction`** (`agent_manager.create_execution()` — el ÚNICO punto que
  V1.0 reconecta al Orchestrator, doc 11 §B.4, deliberadamente sin lógica extra
  alrededor); **`WorkspaceAction`** (Δ2 — `create_task`/`close_task`/
  `move_task`/`update_task`, reusando EXACTAMENTE los side effects del endpoint
  HTTP: `apply_task_status_side_effects`+`recompute_project_progress`+
  `emit_task_created`/`emit_task_status_changed`+`on_task_closed`; el AE nunca
  recalcula progreso a mano). 4 stubs registrados a propósito (para que fallen
  CLARO con `NotImplementedError("V1.1"/"V1.x")` si una regla mal configurada
  los usa, no con el genérico "sin ejecutor"): `SkillExecutionAction`,
  `CalendarBlockAction`, `ChainedRuleAction`, `MemoryUpdateAction`.
  `app/automation/rules_builtin.py`: 5 reglas predefinidas sembradas de forma
  idempotente en el arranque (por `name`, nunca duplica ni pisa una regla que
  el usuario ya haya creado con ese nombre) — TODAS `enabled=False` (HITL):
  `daily_briefing` (08:00), `system_monitor` (cada 30min, cooldown 5min,
  estilo Mark-XLVII), `urgent_email_alert` (evento `email.triaged` +
  `category=urgente`), `email_summary` (18:00), `agent_task` (plantilla
  genérica con `agent_id=None` — inofensiva incluso si alguien la activa sin
  configurarla). **Endpoints** (`automation.py`): `GET /rules` (+filtro
  `project_id`, Δ10), `PATCH /rules/{id}` (activa/desactiva **EN CALIENTE** —
  arma/desarma el trigger en el motor sin reiniciar el backend), `GET
  /executions` (historial). **Frontend**: `pages/Automation.tsx` (nueva página
  `/automation` + ítem de Sidebar) — aprobaciones pendientes con ✓/✗, lista de
  reglas con toggle simple (el interruptor deslizante azul + selector de
  autonomía es A3b, deliberadamente no adelantado aquí), historial con
  filtro por regla. `AutomationSection.tsx` rellena el stub de
  `ProjectCard.tsx` (Δ10) con las reglas filtradas por `project_id` — hoy
  casi siempre vacío (las 5 predefinidas nacen globales, sin UI de creación
  de reglas por proyecto todavía). **Bug real encontrado en la verificación en
  vivo**: `engine.py` solo miraba si el ejecutor lanzaba una excepción, nunca
  si el propio `ActionResult` devuelto reportaba `ok=False` (fallo de negocio
  controlado, p.ej. "sin chat_id configurado") — una regla que fallaba
  silenciosamente se auditaba como `status=ok`. Corregido con
  `_interpret_result()` (duck-typing sobre `.ok`/`.detail`, sin importar
  `actions.py` desde `engine.py` — evita el ciclo): ahora un `ok=False` se
  registra como `status=failed` con el `detail` como error. Tests: 33 nuevos
  (`test_automation_actions.py` 19 + `test_rules_builtin.py` 14, incluye
  endpoints HTTP) + 2 de regresión del bug de `ActionResult.ok`. **Verificado
  en vivo contra el Postgres real**: activar `daily_briefing` de verdad
  (arranque real, siembra idempotente confirmada), disparar a mano, confirmar
  que el fallo de negocio (sin canal Telegram registrado en el script de
  verificación) se audita como `failed` con motivo claro tras el fix; una
  `WorkspaceAction.close_task` sobre una tarea real recalculó el progreso del
  proyecto a 1.0 correctamente. Suite: **324 passed** (294 previos + 30 de A3).
- ✅ **A3b — Permisos & Autonomía** (doc 20 §A3b, petición directa del usuario
  intercalada durante A2a): la capa de POLÍTICA sobre el `ApprovalGate` —
  el gate sigue siendo el primitivo genérico y sigue existiendo siempre; lo
  nuevo es que ahora puede auto-resolverse cuando el usuario ya dio permiso
  de antemano para ese tipo de acción, en vez de preguntar cada vez.
  `app/automation/permissions.py` (NEW): `PermissionDef` (catálogo congelado,
  9 entradas — `email.send`, `telegram.send`, `agent.execute`,
  `workspace.write`, `calendar.write`, `automation.rules`, `memory.write`,
  y 2 marcadas `available=False` a propósito como reservas de futuro,
  `browser.use`/`computer.use`, pedidas explícitamente por el usuario para
  cuando existan esas tools), `PROFILES` (`manual`=nada activo,
  `balanced`=solo riesgo bajo, `full`=todo lo disponible — el equivalente a
  "omitir permisos" de Claude Code, pedido explícitamente como selector
  rápido arriba del panel). Estado persistido en la tabla `Config` existente
  (`permission.<id>`="on"/"off", `autonomy_profile`), mismo patrón
  `_get`/`_set` que ya usaba `telegram.py` — sin migración nueva.
  **Fail-CLOSED por diseño**: `is_pre_authorized(kind)` devuelve `False` para
  cualquier id desconocido y para cualquier permiso con `available=False` —
  el default seguro es siempre preguntar. **Regla de oro** (comentada en el
  código): "pre-autorizado NUNCA significa silencioso" — `ApprovalGate.
  request_approval()` (`approval.py`, MODIFICADO) persiste SIEMPRE la fila
  `Approval` primero: si el permiso está pre-autorizado, se auto-resuelve
  llamando internamente a `resolve()` con `note="auto (permiso
  pre-autorizado)"` — reusa el mismo claim atómico/ejecución/Decision
  API/evento que una resolución manual del usuario, nunca duplica esa lógica.
  Hay rastro de auditoría en `approvals` incluso en modo autónomo total.
  **Endpoints** (`automation.py`): `GET /permissions` (catálogo + estado +
  perfil activo, una sola llamada), `POST /permissions` (toggle individual),
  `POST /permissions/profile` (aplica un perfil de golpe). **Frontend**:
  `components/Toggle.tsx` (NEW) — interruptor deslizante genérico, sin texto
  ON/OFF (petición explícita: solo la bolita se desliza y el fondo pasa a
  azul-accent), reutilizable por cualquier ajuste booleano futuro de la app,
  no solo Permisos. Sección **"Permisos"** nueva en `Settings.tsx` — selector
  rápido de perfil (manual/balanced/full) arriba, lista de los 9 permisos con
  su Toggle debajo (los 2 `available=False` se muestran atenuados con
  "próximamente"), agrupados por `group`. Tests: `test_permissions.py` (NEW,
  21 — catálogo, fail-closed por defecto, persistencia del toggle, los 3
  perfiles, invariante `PROFILES⊆CATALOG`, y los 4 tests críticos de
  integración con el gate: OFF sigue preguntando, ON auto-resuelve CON
  `resolution_note` verificado, un permiso no afecta a un `kind` distinto,
  revertir a OFF vuelve a preguntar). Suite completa: **345 passed** (324
  previos + 21 de A3b). **Verificado en vivo contra el Postgres real**
  (script directo, `DATABASE_URL` real): permiso OFF → `request_approval`
  deja la fila en `pending`; activar el permiso → la siguiente petición del
  mismo `kind` se auto-resuelve al instante con el `resolution_note` correcto
  y la acción registrada se ejecuta; desactivarlo de nuevo vuelve a preguntar.
  `tsc --noEmit` y `npm run build` limpios. **Nota de transparencia**: no se
  pudo completar el click-through visual en navegador para este sprint — el
  puerto 8000 ya estaba ocupado por un proceso Python ajeno a esta sesión
  (backend arrancado manualmente por el usuario, sirviendo código viejo sin
  `/api/automation/permissions`); no se reinició ese proceso para no
  interferir con él. La verificación de A3b se apoya en el script contra
  Postgres real + la suite completa (que ejercita el HTTP real vía
  `TestClient`) + build limpio; pendiente un vistazo visual rápido del panel
  de Ajustes en la próxima sesión con el backend real relanzado.
- ✅ **A4 — Integración MOS + Learner stub + cierre (tag v0.9.0)** (doc 20 §A4):
  el AE deja rastro consultable, para que el Learner de V1.1/V1.2 nazca con
  datos reales en vez de arrancar en blanco. **Memoria de automatización/error**
  (doc 11 §A.3): `engine.py` gana `_remember()`, invocado tras CUALQUIER
  ejecución REAL (el executor llegó a correr — ok o failed; nunca "skipped":
  condiciones no cumplidas, sin ejecutor, o idempotencia ya cubierta antes no
  cuentan como "disparo"). Éxito → `memory_router.store(MemoryType.AUTOMATION)`;
  fallo (excepción real O `ActionResult.ok=False`, mismo camino, doc 20 §A3) →
  `memory_router.store(MemoryType.ERROR)`. Best-effort a propósito: la ejecución
  YA quedó auditada en `automation_executions` antes de llegar a `_remember()`,
  así que un fallo de memoria/evento ahí nunca debe hacer parecer que la regla
  falló. **Evento `automation.rule_fired`** (doc 17 §4, `{rule_id, trigger, ok,
  duration_ms}`) emitido en el mismo punto — completa los 4 eventos del AE
  (`approval.requested/resolved` de A1, `memory.compacted` de A2a).
  **Decision API completa (Δ9)**: `decision_service.history(project=,
  mission_id=, status=, limit=)` — listado cronológico exacto sobre la tabla
  `decisions` (fuente SQL), a diferencia de `search_decisions()` (semántica,
  sobre el espejo `mem_decision`); la pieza que RFC-002 listaba y faltaba desde
  V0.85 M1. Cada aprobación/rechazo ya escribía en `decisions` desde A1 — aquí
  se verifica que ese saldo alimenta a `history()` sin cambios en `approval.py`.
  **`AutomationLearner` stub** (`app/automation/learner.py`, NEW, singleton
  `automation_learner`): `record_feedback`/`suggest_new_rule`/
  `suggest_rule_improvement` → `NotImplementedError("V1.2")`. Interfaz
  congelada documentando de qué datos YA acumulados en V0.9 se alimentará cada
  método (docstring por método, no solo "TODO V1.2") — el feedback real ya se
  captura vía Decision API + MOS desde V0.9, este módulo es el punto de
  enganche, no el cerebro. Registrado en el barrel + `test_module_boundaries.py`
  (mismo patrón que `permission_service` en A3b). **Auditoría de cabos sueltos**
  (pedida explícitamente, doc 20 §A4): docs 11/14/15 revisados contra el código
  real — los 3 ya apuntaban correctamente al AE (doc 14 §4.2 TIE↔AE, doc 15 §8/9
  "AutomationLearner del doc 11 A.1 ES este módulo", doc 11 líneas 16-19/61-65
  con la interfaz exacta que se implementó) — **nada que corregir**, Fable 5 los
  había dejado bien planificados de antemano. **Bug real encontrado en tests
  (no en producción)**: al ejercitar la suite completa (no solo
  `test_automation_mos.py` aislado), un test de A2b/A3 anterior (que dispara
  reglas reales contra `engine.py` sin conocer el MOS) dejaba residuos en
  `mem_automation` que colaban en el primer test de A4 — SQLite reutiliza el id
  1 en cuanto la tabla `automation_rules` queda vacía, así que un `rule_id=1`
  de OTRO archivo de test coincidía con el de éste. Corregido limpiando
  `mem_automation`/`mem_error` tanto al ENTRAR como al SALIR de cada test (antes
  solo al salir) — ningún archivo de test previo necesitó tocarse, la limpieza
  extra en `test_automation_mos.py` basta. **Bump de versión** 0.8.7 → 0.9.0 en
  las 3 ubicaciones sincronizadas + los 3 `.bat` (`iniciar_backend.bat`,
  `iniciar_todo.bat`, `iniciar_frontend_react.bat`; `backend/iniciar_app.bat`
  sigue con su banner `0.3.0` heredado, deuda menor ya documentada). Tests:
  `test_automation_mos.py` (6 — regla ok escribe `mem_automation`, acción
  fallida con `ActionResult.ok=False` Y con excepción real escriben
  `mem_error` por el mismo camino, "skipped" NUNCA deja rastro, el evento
  `automation.rule_fired` se emite con el payload correcto, una aprobación
  resuelta aparece en `decision_service.history()` incluyendo el filtro por
  `status`). Suite completa: **351 passed** (345 previos + 6 de A4).
  **Verificado en vivo contra el Postgres real** (script directo,
  `DATABASE_URL` real, limpieza final confirmada — 0 filas residuales): regla
  OK escribe en `mem_automation` con metadata correcta, acción fallida escribe
  en `mem_error`, regla `skipped` no deja rastro en ningún lado, el evento
  `automation.rule_fired` llega con `ok=True`, una aprobación resuelta aparece
  en `decision_service.history()` y en el filtro `status="active"`. `tsc
  --noEmit` limpio (sin cambios de frontend en A4 más allá del bump de
  versión). **V0.9 (Automation Engine + ApprovalGate) — BLOQUE CERRADO. Tag
  `v0.9.0`.**

**V1.0 — TIE v1 (Task Intelligence Engine, en curso sobre `master`; plan de
sesiones detallado en `PLAN_MAESTRO_2026/21_V10_TIE_PLAN_SESIONES.md`, sprints
T1-T5; artefacto visual acompañante).** El motor cognitivo: entender →
planificar → ejecutar el grafo → responder. **Alcance del plan doc 21: SOLO el
TIE** — el MEL (doc 19, E1-E2), el HermesRuntime (V1.1), el Learner/LLL (V1.1) y
el empaquetado MVP-beta (O5) son planes aparte. Decisión de versión (usuario
2026-07-16): el desarrollo de V1.0 se hace por bloques — el cierre del TIE queda
en **`0.9.2`** (T5), luego MEL → Orchestrator/integración → MVP-beta, que cierra
la fase en `1.0.0`. Durante T1-T4 la versión se mantiene en `0.9.0`.
- ✅ **T1 — Esqueleto + contratos congelados + runtime + intent + camino corto**
  (`app/tie/`, módulo nuevo): el TIE existe con sus contratos CONGELADOS y el
  camino corto funcionando de punta a punta, **sin enganchar todavía al Gateway**
  (el switch `gateway.set_handler(tie.handle)` es T4). **Auditoría del código real
  antes de empezar** (doc 21 §1, corrige supuestos de los docs): la tabla
  `orchestrator_traces` **NO existía** pese a que el doc 11-B la daba por "ya
  prevista" → se crea aquí (migración 19.ª `e1f2a3b4c5d6_v10_tie_traces`, aplicada
  al Postgres real en el mismo paso y verificada — la lección dura del proyecto);
  no había settings `fast/smart` (los añade T2); `gateway.set_handler()` SÍ existe
  ya (V0.8) con firma `MessageHandler = envelope → str|OutboundMessage`.
  **`contracts.py` CONGELADO**: `NodeState` (9 estados), `TaskNode`/`TaskGraph`
  (grafo-como-datos serializable, `to_dict`/`from_dict`), `Mission` (implícita en
  V1.0), y **`Intent` ENRIQUECIDO** (petición del usuario): responde ya las 7
  preguntas — `type`+`goal` (qué quiere), `requires_tools` (qué herramientas),
  `requires_planning` (si planner), `requires_browser`+`requires_computer` (si
  browser/PC — mapean a los permisos `browser.use`/`computer.use` reservados en
  A3b), `requires_automation` (si debe volverse regla del AE), `model_capability`
  ∈ `MEL_CAPABILITIES` (qué pedir al MEL — hint congelado alineado con la
  taxonomía del doc 19, sin acoplar el TIE a nombres de modelo), y
  `requires_memory`+`memory_types`+`context_query` (qué pedir al MOS). Propiedad
  derivada `is_short_path` (conversational siempre; query simple sin planning/
  browser/computer/automation). **`runtime.py`** (doc 10, la interfaz que usará
  el Orchestrator y que HermesRuntime V1.1 implementará sin tocar el executor):
  `AgentRuntime(ABC)` (`execute_task`/`stream_task`/`health_check`/`capabilities`)
  + contratos `AgentTask`/`AgentResult`/`AgentChunk`/`RuntimeHealth` + `NullRuntime`
  (capabilities `{chat,tool_use_basic}`; delega el chat en `chat_service.answer()`
  —el pipeline único de V0.85 M4, reusa memoria del MOS— y puede ejecutar una tool
  simple por el `ToolManager` inyectado con whitelist) + registro `{name:runtime}`
  (el "Agent Factory" = un dict, doc 14 §3.1). **`intents.py`**: `classify()` con
  modelo barato (en T1 proveedor activo; T2 → `router.fast()`; E1 →
  `mel.complete(capability="classify")`) → `Intent` completo validado; umbral
  `<0.55` → fuerza conversational (fail-safe); extracción robusta de JSON
  (bloques markdown), fallback conversational ante CUALQUIER fallo (nunca romper).
  **`tracer.py`** (base): escribe/actualiza `orchestrator_traces` (best-effort,
  nunca rompe el pipeline); `record_start`/`record_intent`/`record_end`, con
  `record_plan`/`update_graph` listos para T2/T3. **`pipeline.py`**: `handle`
  (entrada channel-agnostic con la firma exacta de `MessageHandler`) +
  `submit_mission` (entrada programática del AE/WPMS que salta el intent) — en T1
  resuelven el camino corto (vía `AgentRuntime`, no `chat_service` directo, para
  ejercitar ya la interfaz) y **degradan honestamente** la rama compleja
  (planner/executor son T2-T4). **`missions.py`** (`new_mission`, misión
  implícita). Disciplina modular (doc 16): API pública en `app/tie/__init__.py`
  (`handle`, `submit_mission`, `classify`, contratos, runtime, `tracer`),
  fronteras vigiladas por `test_module_boundaries.py` extendido (`app.tie.*`
  internos). `config.py` += `TIE_ENABLED` (kill-switch; con False el Gateway
  sigue en el `chat_message_handler` legacy). Tests: `test_tie_contracts.py`
  (18 — round-trip de contratos, las 7 preguntas del Intent, `is_short_path`,
  clasificador con `ai_manager` fake incl. umbral/JSON-basura/error/markdown,
  NullRuntime, registro, `handle`/`submit_mission` dejando traza). Suite completa:
  **369 passed** (351 previos + 18 de T1). **Verificado en vivo contra el backend
  real** (MiniMax activo + Postgres real): el clasificador respondió las 7
  preguntas correctamente en mensajes reales (incl. `requires_browser=True` en
  "busca en internet", `model_capability='extract'`, `memory_types=['mem_project']`),
  el camino corto respondió de verdad ("Soy Aithera…"), la traza quedó en
  `orchestrator_traces`, `submit_mission` funcionó, limpieza sin ensuciar la BD.
- ✅ **T2 — Enricher + Router (mínimo) + Planner + Graph (validación DAG)**
  (doc 21 §3·T2): dado un intent complejo, el TIE construye contexto, elige
  modelo potente, y el Planner emite un **TaskGraph validado por schema** que
  `graph.py` valida como DAG antes de que nada se ejecute (planificar jamás
  ejecuta side effects, regla 11-B). **`enricher.py`**: `enrich(query,
  memory_types)` → `memory_router.context()` con **presupuesto de latencia DURO**
  (`asyncio.wait_for(TIE_CONTEXT_BUDGET_MS)`, 300ms — si excede, contexto vacío,
  el TIE nunca espera; mismo patrón que chat_service M4) + caché 60s por
  (query, tipos); mapea los strings del Intent (`mem_project`…) a `MemoryType`,
  ignorando desconocidos. **`router.py`** (Model Router mínimo, doc 14 §3.5):
  fachada honesta — `fast()`/`smart()` devuelven hints de Settings o el modelo
  activo; **`complete(prompt, capability)` es el punto ÚNICO de llamada al LLM
  del TIE** (intents/planner pasan por aquí). En T2 delega en `ai_manager.chat()`
  (el AIManager no permite override de modelo per-call, así que fast/smart son
  hints; el reparto real por modelo llega con el MEL); **shim diseñado para que
  E1 lo convierta en `mel.complete(capability=...)` con un cambio de una línea**
  sin tocar el resto del TIE. `intents.py` refactorizado para usar
  `router.complete(capability="classify")` en vez de `ai_manager` directo
  (centraliza el LLM call). **`planner.py`**: `plan(goal, intent, context,
  mission_id, trace_id)` con modelo potente (capability `reason`); prompt que
  pide grafo de 2-3 nodos con la lista real de tools disponibles (para que no
  invente herramientas); salida del LLM **validada contra el schema + las
  invariantes DAG**; grafo inválido → **1 reintento con el error como feedback**
  → si vuelve a fallar, devuelve `None` (el caller degrada a camino corto, nunca
  rompe); registra el plan en la **Decision API** (`store_decision` con
  `mission_id`, best-effort) + `tracer.record_plan`. **`graph.py`** (el motor
  propio, doc 14 §1.5/§3.4.1, sin NetworkX): `build()` + `validate()` —
  **Kahn/topological** para ciclos (~30 líneas, dict + in-degree), `depends_on`
  solo a ids existentes (sin autodependencias), `tools` de cada nodo ⊆ catálogo
  del `ToolManager` — + `ready_set()` (nodos PENDING con `depends_on` en DONE,
  orden determinista prioridad desc/id asc — lo consumirá el executor en T3).
  `config.py` += `TIE_FAST_MODEL`/`TIE_SMART_MODEL`/`TIE_CONTEXT_BUDGET_MS`/
  `TIE_MAX_PARALLEL`. Disciplina modular: `app.tie.router/graph/enricher/planner`
  internos (fronteras vigiladas). Tests: `test_tie_graph.py` (13 — DAG lineal/
  ramas/ciclos de 2 y 3/autodep/id inexistente/tool fuera de catálogo/ready_set/
  orden) + `test_tie_planner.py` (9 — plan válido 2-3 nodos, registra decisión,
  reintento ante inválido, degrada a None tras 2 fallos, JSON basura, escribe en
  la traza, y el enricher: presupuesto agotado→vacío, caché, error del MOS no
  rompe). Suite completa: **391 passed** (369 previos + 22 de T2). **Verificado
  en vivo contra el backend real** (MiniMax + Postgres): el enricher trajo 1761
  chars de contexto real; un goal complejo real ("revisa mis emails urgentes y
  prepárame un borrador…") produjo un **grafo válido de 3 nodos** con
  dependencias n1→n2→n3, tools `email`/`calendar`, y `approval_required` marcado
  en el paso sensible (ejecutar la acción → gate); el reintento se disparó (1ª
  respuesta no era JSON válido) y el plan quedó persistido con `decision_id`
  enlazado; limpieza sin ensuciar la BD. Nada se ejecuta todavía (el executor es
  T3).
- ✅ **T3 — Graph Execution Engine: executor + checkpoint + gates + recovery +
  kill-switch** (doc 21 §3·T3): el corazón. `app/tie/executor.py` ejecuta un
  TaskGraph ya validado (T2) con las 6 garantías del doc 14 §3.4. **Loop de
  olas**: `run(graph, mission, trace_id)` consume `graph.ready_set()` y ejecuta
  UNO por iteración (V1.0 ola=1, orden determinista prioridad desc/id asc);
  estructurado para que V1.2 lance toda la ola con `asyncio.gather`+semáforo sin
  cambiar el algoritmo. **Ejecución de nodo**: `get_runtime(node.runtime)` →
  `runtime.execute_task(AgentTask, memory=memory_router, tools=tool_manager,
  approval_gate=approval_gate)` — memoria/tools/gate SIEMPRE por inyección (doc
  10); contexto por nodo vía `enricher.enrich(node.context_query)` (presupuesto
  duro de T2). **Checkpoint por transición**: `_transition()` persiste el grafo
  entero en `orchestrator_traces.plan` en CADA cambio de estado — todo el estado
  vive en disco, nada crítico en RAM. **Gates (HITL como estado de primera
  clase)**: nodo `approval_required` → `WAITING_APPROVAL` + `approval_gate.
  request_approval(kind="tie.node", action_type="tie_resume", action_payload=
  {trace_id,node_id,mission_id})` y `run()` RETORNA (`state="waiting"`) — el nodo
  puede esperar días. **Reanudación EVENT-DRIVEN** (decisión de diseño): el
  veredicto se aplica desde el handler de `approval.resolved` (bus, doc 17) y NO
  dentro del ejecutor registrado del gate — porque `resolve()` vive en el camino
  de un request HTTP y el resto del grafo puede tardar minutos; `emit` despacha
  con `create_task`, así que el POST responde al instante. El ejecutor
  `tie_resume` se registra igualmente (devuelve un marcador) para honrar el
  contrato del registro del gate: sin él, `resolve()` reportaría "sin ejecutor" y
  ensuciaría la auditoría. Aprobado y rechazado van por el MISMO camino
  (`_apply_gate_verdict`), idempotente. **Regalo de A3b heredado gratis**: si el
  usuario pre-autorizó ese `kind`, el gate se auto-resuelve al instante (con
  rastro) y el evento reanuda — el TIE no hace nada especial. **Recovery V1.0**
  (degradar): nodo FAILED → dependientes **transitivos** SKIPPED + `mem_error`
  (best-effort, no bloqueante) + el grafo sigue con lo que sí puede; misión
  `done` si algo útil salió, `failed` solo si NADA salió bien. **Kill-switch**:
  `cancel(mission_id)` marca la misión y **cancela cooperativamente la task del
  nodo en vuelo** (`asyncio.Task.cancel()` → el runtime recibe `CancelledError`,
  el nodo queda CANCELLED) — no se espera a que termine su LLM/tool (verificado:
  <2s frente a un nodo de 30s). **Validación por nodo** (§3.4.7): determinista y
  barata (¿éxito? ¿hay salida con forma?) → `node.validation`; un runtime que
  dice `success=True` sin producir nada NO cuela (test dedicado) — jamás teatro.
  **`resume_pending()`** (§3.4.3): recarga las trazas `running|waiting` al
  arrancar y recomputa el ready-set; **caso feo cubierto**: si el usuario aprueba
  mientras el backend está caído, el evento se pierde (el bus es in-process y sin
  persistencia, doc 17) → se recupera consultando el veredicto en disco vía el
  nuevo `TaskNode.gate_id` (extensión append-only del contrato congelado, campo
  con default — permitido por la regla de evolución). `tracer` += `load_graph`/
  `get_meta`/`set_state`/`pending_trace_ids`. Tests: `test_tie_executor.py` (16 —
  orden lineal, ramas independientes por ready-set, checkpoint en disco,
  validación (incl. el runtime que no produce nada), FAILED→SKIPPED transitivo,
  misión sin nada útil=failed, gate pausa sin ejecutar, gate aprobado reanuda,
  gate rechazado degrada, gates de OTROS módulos no se ven afectados,
  kill-switch antes de empezar y **en vuelo**, `resume_pending` continúa/respeta
  gate pendiente/aplica gate resuelto offline). Los tests usan un **runtime FAKE
  registrado en el registro real** — de paso prueban que un runtime nuevo funciona
  sin tocar el executor (el contrato que usará HermesRuntime en V1.1). Suite
  completa: **407 passed** (391 previos + 16 de T3). **Verificado en vivo contra
  el Postgres real**: grafo de 3 nodos → pausa en el gate (`waiting`, n2 sin
  ejecutar, checkpoint `n1=done/n2=waiting_approval` confirmado en Postgres) →
  aprobar → reanuda en background → `n2=done, n3=done`; kill-switch cancelando;
  limpieza sin ensuciar la BD.
- ✅ **T4a — Responder + pipeline completo + gate del plan + EL SWITCH + eventos
  `mission.*` + endpoints** (doc 21 §3·T4; **T4 se dividió en T4a/T4b por carga**,
  mismo criterio que W2→W2a-e y A2→A2a/A2b: T4a es el backend —el TIE piensa y
  ejecuta de verdad, verificable por API—, T4b será el frontend —vista de misión,
  aprobación de plan y streaming de estado—). **`responder.py`**: `build(mission,
  graph)` sintetiza el outcome desde los nodos DONE con `router.complete(capability
  ="summarize")`; **degradación graciosa** (entrega lo conseguido Y explica lo que
  no, jamás finge éxito total) + **plantilla determinista si el LLM falla** (mismo
  patrón que el summarizer de V0.85 M3: nunca dejar al usuario sin respuesta).
  `plan_summary(graph)` para la UI/gate. **`pipeline.py` COMPLETO** (doc 14 §3.3):
  `handle` = clasificar ∥ pre-fetch de contexto **en paralelo** (`asyncio.gather`,
  doc 11 B.2) → camino corto (~80%, sin planner ni grafo) **o** planner → gate del
  plan → `executor.run` → `responder`. Si el planner no logra grafo válido ni tras
  el reintento → degrada al camino corto (regla 11-B: el usuario siempre recibe
  algo). `submit_mission` (entrada del AE/WPMS) **nunca va por el camino corto**:
  una misión explícita no es charla, siempre planifica. **Gate del PLAN** (nuevo,
  `action_type="tie_plan"`, distinto del gate de nodo de T3): si el plan toca algo
  sensible se aprueba ENTERO antes de ejecutar nada (transparencia estilo
  plan-mode; nada se ha ejecutado aún — planificar no tiene side effects).
  **Decisión de diseño clave**: aprobar el plan **autoriza sus pasos sensibles** —
  el usuario ya vio la lista completa, así que no se le vuelve a preguntar nodo por
  nodo; se implementa marcando `node.gate_id = <gate del plan>` (la condición del
  executor para abrir gate es `gate_id is None`, T3), lo que además deja **rastro
  de auditoría**: cada nodo apunta a la aprobación que lo autorizó. `TIE_PLAN_
  APPROVAL` (default true) permite desactivarlo y volver a los gates por nodo.
  Reanudación event-driven (mismo criterio que T3: nunca dentro del `resolve()`
  del gate, que vive en un request HTTP). **EL SWITCH** (`main.py` lifespan):
  `gateway.set_handler(tie.handle)` + `tie.register_handlers()` (gates de nodo +
  del plan) + `executor.resume_pending()` — va DESPUÉS de los adapters y del AE
  (el AE delega en el TIE, no al revés); con `TIE_ENABLED=false` queda el
  `chat_message_handler` legacy (kill-switch real), y si el TIE no arranca el chat
  sigue con el handler legacy (degradación graciosa). **Eventos `mission.*`**
  (doc 17 §4): `started`/`completed`/`failed`/`cancelled` — metadatos, nunca
  contenido; el Learner (V1.1) se suscribirá. **Endpoints** `/api/tie`:
  `GET /missions` (las que esperan aprobación primero), `GET /missions/{id}`
  (+grafo con el estado de cada paso), `POST /missions/{id}/cancel` (kill-switch),
  `POST /missions/{id}/approve-plan`. **Dos hallazgos reales de los tests** (no de
  producción): (1) el test de fronteras cazó que `endpoints/tie.py` importaba
  `app.tie.pipeline` directamente — corregido moviendo la lógica al TIE
  (`tie.resolve_plan()`, fachada) en vez de silenciar el test; (2) un test de T1
  asumía que `submit_mission` iba por el camino corto — quedó obsoleto por el
  cambio de diseño de T4a y se actualizó para reflejar el contrato real. Tests:
  `test_tie_handle.py` (13 — el camino corto responde idéntico y **no invoca el
  planner**, `handle` nunca lanza, query compleja planifica/ejecuta/responde,
  sin plan válido degrada, plan sensible pide aprobación **sin ejecutar nada**,
  plan aprobado ejecuta sin re-preguntar con rastro del gate, plan rechazado no
  ejecuta nada, `submit_mission` siempre planifica, eventos, 4 de endpoints).
  Suite completa: **420 passed** (407 previos + 13). **Verificado en vivo contra
  el backend real** (MiniMax + Postgres): camino corto real respondiendo ("Soy
  Aithera…"), **el planner REAL generó un grafo coherente de 2 nodos**
  ("Recuperar los 3 últimos emails" → "Guardar nota con resumen") que se ejecutó
  y el **responder REAL** sintetizó en lenguaje natural; el gate del plan pausó
  con **nada ejecutado**, al aprobar ejecutó los 2 pasos, `n2.gate_id` = el gate
  del plan y **no se abrió un segundo gate**; limpieza sin ensuciar la BD.
- ✅ **T4b — Frontend: vista de misión + aprobación de plan + streaming de estado**
  (doc 21 §3·T4, segunda mitad): el TIE por fin se VE. **Streaming de estado**
  (doc 11 B.5, primer feedback ≤1s): `/api/chat/stream` (el camino real de
  `Chat.tsx`) pasa por el TIE vía `tie.handle_stream()` — el camino corto (~80%)
  sigue streameando **tokens de verdad** (`NullRuntime.stream_task` reescrito:
  usa el mismo `build_system_prompt` + `chat_stream` + filtro incremental B21 que
  el endpoint legacy), y el complejo emite estados ("analizando" →
  "planificando") + la respuesta del responder. **Hallazgo real y arreglado**:
  `api.streamChat` ignoraba las líneas `event:` pero SÍ procesaba su `data:` como
  texto — con eventos tipados eso habría metido "analizando" dentro de la
  respuesta del chat; el parser se reescribió a SSE de verdad (acumula el bloque
  hasta la línea en blanco y despacha por `event:`), con callbacks
  `onStatus`/`onMission`. Con `TIE_ENABLED=false` el endpoint conserva su camino
  legacy intacto. **`pages/Missions.tsx`** (NEW): lista (las que esperan
  respuesta van primero) + detalle con el **grafo paso a paso** (punto de color
  por `NodeState`, dependencias, duración, error, salida), **aprobación de plan**
  (Aprobar y ejecutar / Descartar) y **kill-switch** ("Parar"); sondeo cada 2s
  SOLO si hay algo vivo (el estado real vive en disco por el checkpoint de T3, así
  que preguntar es barato y siempre da la verdad — sin websockets). Ítem
  "Misiones" en el Sidebar + ruta `/missions`. **`Chat.tsx`**: el placeholder
  mudo "Pensando..." pasa a mostrar lo que el TIE está haciendo de verdad, y una
  respuesta que vino de una misión muestra "Ver el plan y sus pasos →".
  `lib/api.ts` += tipos `Mission`/`MissionDetail`/`TaskGraph`/`TaskNode`/
  `NodeState` + `getMissions`/`getMission`/`cancelMission`/`approvePlan`. Tests:
  3 nuevos de streaming en `test_tie_handle.py` (el camino corto emite status +
  tokens y NO crea misión; el complejo emite `mission` + respuesta;
  `handle_stream` nunca lanza). Suite: **423 passed**; `tsc` y `vite build`
  limpios. **Verificado EN VIVO en el navegador contra el backend real**
  (arrancado con el código nuevo; el log confirmó `TIE v1 activo (Gateway →
  tie.handle)`): el chat mostró "analizando…" y respondió limpio ("Soy Aithera,
  tu sistema operativo personal de IA") **sin que el estado se colara en el
  texto**; una petición real ("revisa mis emails urgentes… y envíalo") hizo que
  el **planner real** generase un plan de 2 pasos, marcase el envío como
  sensible y **pidiese visto bueno sin ejecutar nada**; la vista de Misiones
  mostró la misión "Esperando tu respuesta" la primera, su plan, el paso "pide
  permiso", y **Descartar** dejó todo en `Cancelada` con "No he ejecutado nada".
  Se probó el rechazo y NO la aprobación a propósito: ese plan enviaba un email
  real del usuario — no se disparan acciones reales para validar la UI. Limpieza
  de las trazas/gates/decisiones de prueba confirmada.
- ✅ **Fixes post-T4b (2026-07-17, reportados por el usuario)**: dos bugs reales
  de la primera pasada de T4b, ambos con reproducción exacta del usuario.
  **(1) La conversación se perdía al navegar** — `Chat.tsx` guardaba los
  mensajes en `useState` local; React Router desmonta la página al navegar (p.
  ej. a "Misiones" para ver un plan), así que volver al chat lo reiniciaba
  desde el saludo. Peor aún: si una respuesta seguía en camino (streaming o
  misión compleja) cuando el usuario navegaba fuera, su `setMessages` apuntaba
  a un componente YA desmontado — React descarta esa actualización en
  silencio y la respuesta se perdía **aunque el backend la hubiera generado
  bien**. Arreglado con `store/useChatStore.ts` (NEW, Zustand): mensajes,
  `streaming`/`tieStatus`/`missionId`/`sending` viven en el store singleton
  (mismo patrón ya usado por `presenceMode` en `useAppStore` — "vive en el
  store para que persista por página"). `sendMessage` en `Chat.tsx` pasa a
  leer/escribir SIEMPRE vía `useChatStore.getState()` (nunca el hook de
  selección) dentro de los callbacks async, así que sobrevive a que el
  componente se desmonte a media petición. Efecto colateral bueno: el viejo
  `accumulatedRef`/FIX-V0.2 (un workaround para el closure obsoleto de
  `streamingText`) deja de hacer falta — `getState().streamingText` nunca
  puede quedar obsoleto porque no es un closure de render. **(2) En "Misiones"
  no había botones para aprobar/rechazar** — `Missions.tsx` solo detectaba el
  gate del PLAN (`graph.state === "draft"`, T4a), pero el TIE tiene DOS
  mecanismos de gate independientes: el del plan y el gate de NODO (T3, se
  abre en mitad de la ejecución si `TIE_PLAN_APPROVAL=false` o en casos
  límite) — un nodo en `waiting_approval` con su propio `gate_id` no tocaba
  `graph.state`, así que `awaitingPlan` daba `false` y la UI no ofrecía NINGÚN
  botón aunque la misión estuviera realmente esperando al usuario. Arreglado
  añadiendo `awaitingNode = nodes.find(n => n.state==="waiting_approval" &&
  n.gate_id)` + un panel "Este paso necesita tu permiso" que resuelve
  directamente `api.resolveApproval(node.gate_id, ...)` — el mismo endpoint
  genérico de A1 que ya usa `Automation.tsx`, sin backend nuevo. **Verificado
  en vivo contra el backend real del usuario** (su propio proceso, sin
  reiniciarlo): navegar Chat→Misiones→Chat conservó la conversación completa;
  navegar a otra página **milisegundos después de enviar** (antes de que
  llegara ningún token) y volver mostró la respuesta completa igualmente — la
  condición de carrera exacta queda cerrada. El fix del gate de nodo se
  verificó por revisión de código + reutilización de un endpoint ya cubierto
  por los 10 tests de A1 (no se forzó el escenario en vivo porque habría
  exigido reiniciar el backend del usuario con `TIE_PLAN_APPROVAL=false`, sin
  permiso para tocar su proceso). `tsc`/`vite build` limpios. Suite backend
  sin cambios (fix 100% frontend); un test de perf preexistente
  (`test_import_app_main_no_bloquea_en_memoria`) parpadeó por carga del
  sistema (backend+frontend del usuario corriendo en paralelo) — no
  relacionado con este fix.
- ✅ **Fixes/features post-T4b, tanda 2 (2026-07-17, reportados por el
  usuario)**: cuatro peticiones sobre la vista de Misiones y el Chat.
  **(1) Markdown roto** (causa RAÍZ, no solo síntoma): `DEFAULT_SYSTEM_PROMPT`
  (`chat_service.py` — lo usan el chat Y cada nodo del TIE vía `NullRuntime`)
  no decía nada sobre formato, así que el modelo generaba libremente
  `**negrita**`, tablas `| — |` y encabezados `#` que la UI (texto plano)
  mostraba rotos. Añadida instrucción explícita "texto plano, sin markdown,
  sin tablas" (mismo criterio que `responder._SYSTEM_PROMPT`, que ya lo
  pedía). **Verificado con una llamada REAL al modelo** (pregunta
  tabla-trampa "compárame Git vs SVN"): antes habría salido tabla/negrita,
  ahora salió en lista de guiones limpia — `**` y `|` ausentes de la
  respuesta. **Defensa en profundidad** (un LLM no seguirá la instrucción al
  100%): `lib/miniMarkdown.tsx` (NEW, sin dependencia nueva) — negrita,
  código, listas y tablas GFM reales (`<table>` con `overflow-x-auto`) en vez
  de pipes/guiones sueltos; usado en `Chat.tsx` y `Missions.tsx`. **Verificado
  en vivo contra una misión REAL y antigua del usuario** (de antes del fix,
  con encabezados/tabla/arte ASCII generados por el modelo): la tabla real
  (`| Aspecto | Características |`) renderiza como **30 `<table>` reales**
  con `<th>`/`<strong>` correctos (confirmado inspeccionando el DOM), no como
  texto roto. **(2) Texto de cada paso truncado sin poder expandir**:
  `line-clamp-3` sin ninguna forma de ver el resto. Añadido `expandedNodes`
  (Set por misión, se resetea al cambiar de misión) + botón "ver más"/"ver
  menos" por nodo — solo aparece si el texto es largo de verdad (>220 chars o
  >3 líneas). Verificado en vivo: el toggle cambia de "ver más" a "ver menos"
  y los demás nodos de la misma misión quedan intactos (independientes).
  **(3) Borrar misiones + limpieza automática**: `tracer.delete_trace`
  (solo misiones TERMINADAS — `done`/`failed`/`cancelled`; 409 si sigue viva,
  hay que cancelarla primero) + `tracer.purge_old(retention_days)` (mismo
  espíritu que `lifecycle.py` del MOS pero para el TIE — nunca toca una
  misión viva, sin importar antigüedad). `DELETE /api/tie/missions/{id}` +
  job APScheduler diario 04:30 local (`TIE_MISSION_RETENTION_DAYS`, default
  30; `0` lo desactiva). Botón "×" por misión en la lista (con `confirm()` —
  mismo patrón que `handleDeleteContext` en Settings.tsx), oculto en misiones
  vivas. Tests: 6 nuevos (terminada borra, viva rechaza con 409, inexistente
  404, `purge_old` borra solo terminadas+viejas y NUNCA una viva aunque sea
  vieja). **Verificado con script contra el Postgres real** (proceso aparte,
  sin tocar el backend del usuario): los 3 casos confirmados letra por letra.
  **(4) Pestañas de sesión en el Chat**: `useChatStore.ts` rediseñado a
  `sessions[]` + `activeSessionId` — cada sesión con su propio
  `messages`/`sending`/`streamingText`/`tieStatus`/`missionId` (dos pestañas
  pueden tener un envío en curso A LA VEZ, cada una independiente).
  Persistidas en `localStorage` (primera vez que el proyecto usa el
  middleware `persist` de zustand; clave `aithera.chat.sessions`, mismo
  formato dotted que `aithera.workspace.cardLayouts`) — sobreviven a cerrar y
  reabrir la app, no solo a navegar. Lo transitorio (`sending`,
  `streamingText`) se excluye del `partialize` a propósito: si la app se
  cierra a media respuesta, no debe quedar una pestaña fantasma "enviando"
  para siempre. Título de cada pestaña autogenerado del primer mensaje del
  usuario (trunca a 32 caracteres), fijo desde entonces. `sendMessage` captura
  el `sessionId` UNA vez al principio y lo usa en toda la función — si el
  usuario cambia de pestaña a mitad de una respuesta, esa respuesta sigue
  escribiendo en su sesión de origen, nunca en la que esté activa en pantalla
  (mismo principio que ya protegía las misiones de T4b, aplicado ahora
  también entre pestañas). **Verificado en vivo con dos pestañas reales**:
  mensaje en pestaña 1 → abrir pestaña 2 → mensaje distinto en pestaña 2 →
  volver a pestaña 1 confirma su conversación intacta y ajena a la 2 (y
  viceversa) → recarga completa de página (`F5`) confirma que AMBAS pestañas
  con sus DOS conversaciones sobreviven mediante `localStorage`. Suite
  backend: **429 passed** (sin el flake del turno anterior — confirma que
  era carga puntual del sistema, no una regresión). `tsc`/`vite build`
  limpios. Verificación 100% sin tocar el backend/frontend que el usuario
  tenía corriendo (scripts aparte para lo de Postgres; Vite HMR aplicó los
  cambios de frontend solo).
- ✅ **T5 — Tests de contrato + perf + verificación en vivo + cierre del bloque
  TIE (doc 21 §3·T5)**: blindaje final antes de cerrar. **`test_tie_perf.py`**
  (NEW, 6 tests) mide los 5 presupuestos de latencia del diseño (doc 14 §6) con
  runtimes fake deterministas (sin red, para CI): `graph.validate()` < 10 ms,
  checkpoint por transición < 20 ms, overhead del executor por nodo < 50 ms
  (runtime instantáneo — todo el tiempo medido es del engine, no de un LLM),
  `resume_pending()` con 5 misiones a medias < 500 ms, kill-switch < 2 s con un
  nodo de 5 s en vuelo, y que el camino corto JAMÁS invoca al planner (ni en
  llamadas ni en tiempo — < 100 ms). **`test_tie_e2e.py`** (NEW, 3 tests): a
  diferencia de T1-T4 (que mockean intents/planner/responder directamente para
  aislar cada pieza), aquí se ejercita la CADENA REAL completa —
  `intents.classify` real (JSON→Intent), `planner.plan` real (JSON→TaskGraph
  validado por `graph.py` de verdad, con su reintento real ante JSON basura),
  `executor.run` real (estado+checkpoint+gate), `responder.build` real— con
  UN SOLO punto fake: la frontera del LLM (`ai_manager.chat` para
  intents/planner/responder + `chat_service.answer` para la ejecución de nodo
  vía `NullRuntime`), determinista y sin red. Casos: misión compleja que
  planifica con un paso sensible → pide permiso → aprueba → ejecuta → responde
  (con el gate del plan pre-autorizando el nodo sensible, sin segundo gate);
  el planner reintenta una vez ante JSON basura y, si vuelve a fallar,
  degrada al camino corto (nada mockeado salvo el LLM); un plan sin pasos
  sensibles ejecuta directo sin gate. **`test_module_boundaries.py`** ganó
  `test_tie_handle_respeta_la_firma_de_messagehandler` (inspecciona la firma
  de `tie.handle` — coroutine de 1 argumento — y la instala de verdad en un
  `Gateway()` nuevo para confirmar que queda como el handler activo; blindaje
  estático+dinámico de Δ3 del doc 21) + el conjunto esperado del barrel
  ampliado con `handle_stream`/`resolve_plan` (T4b, antes solo cubiertos por
  `issubset`, ahora exigidos explícitamente). Suite completa: **439 passed**
  (429 previos + 10 de T5), sin regresión — el único fallo visto durante la
  sesión (`test_import_app_main_no_bloquea_en_memoria`, presupuesto de 2 s en
  el import de `app.main`) es un flake de entorno **ajeno al TIE** (perfilado
  con `-X importtime`: el peso es fastapi/sqlalchemy/elevenlabs/ai_manager —
  nada de `app.tie` aparece en el top de costes — y reproduce igual sin
  ninguno de los cambios de T5), documentado como deuda de arranque ya
  conocida, no una regresión de este cierre. **Verificación EN VIVO contra el
  Postgres + backend reales** (script aparte, nunca el proceso del usuario,
  limpieza posterior confirmada — 0 filas residuales, y las 10 trazas
  preexistentes de sesiones anteriores del usuario quedaron intactas): (a)
  camino corto — con MiniMax caído en este entorno (`getaddrinfo failed`, sin
  salida a internet), el `AIManager` hizo fallback automático a Ollama y el
  camino corto respondió igual de bien — la degradación graciosa del proveedor
  activo, verificada de carambola; (b) misión compleja real — un goal real
  ("redacta un email de agradecimiento y envíalo") produjo un plan REAL de 2
  nodos con el paso de envío marcado sensible, pidió permiso sin ejecutar
  nada, y al aprobar ejecutó ambos pasos y el responder sintetizó la
  respuesta final; (c) kill-switch — `cancel()` marca y limpia sin errores
  contra datos reales (el mecanismo de cancelación cooperativa en pleno vuelo
  ya está probado en detalle por `test_tie_executor.py`/`test_tie_perf.py` con
  un runtime fake lento — no es reproducible de forma determinista contra un
  LLM real); (d) reanudación tras reinicio simulado — un nodo pausado en gate
  se aprobó con el handler del evento desuscrito a propósito (backend
  "caído"), quedó esperando, y `resume_pending()` lo recuperó leyendo el
  veredicto en disco y completó la misión, exactamente como diseñado en T3.
  **Hallazgo real de la verificación en vivo** (no un bug de datos ni de
  seguridad, documentado con transparencia): hay una ventana de varios
  segundos donde `orchestrator_traces.state` ya vale `done` (lo escribe
  `executor._finalize()` en cuanto el grafo termina) pero `outcome` todavía
  tiene el texto del gate del plan (lo escribe `pipeline._execute_and_respond()`
  DESPUÉS, cuando `responder.build()` termina su propia llamada al LLM) —
  confirmado con un script dedicado: `state=done` a los 10.5 s, `outcome` real
  no llegó hasta los 15 s. Los estados por nodo (lo que pinta `Missions.tsx`
  para los checks verdes) son correctos todo el tiempo; solo el texto-resumen
  superior puede quedarse momentáneamente desfasado. No bloquea el cierre de
  T5 (autocorrige solo en segundos, nada se ejecuta de más ni se pierde) — se
  dejó anotado como tarea de fondo aparte para una futura sesión de pulido.
  **Cierre de versión**: bump `0.9.0` → `0.9.2` (decisión de versión del
  usuario, 2026-07-16) en las 3 ubicaciones sincronizadas
  (`backend/app/core/config.py`, `backend/app/main.py` ×2 —
  `FastAPI(version=...)` y `GET /`—, `frontend/package.json`) + los 3 `.bat`
  (`iniciar_backend.bat`, `iniciar_todo.bat`, `iniciar_frontend_react.bat`;
  `backend/iniciar_app.bat` sigue con su banner `0.3.0` heredado, deuda menor
  ya documentada desde V0.8.7). **V1.0 — bloque TIE v1 (T1-T5) CERRADO. Tag
  `v0.9.2`.** El siguiente plan (aparte) es el MEL (doc 19, E1-E2) o el cierre
  MVP-beta (doc 03 §5 O5) — a decisión del usuario; el cierre de V1.0 COMPLETO
  (MEL + integración Orchestrator + MVP-beta) es el que sube a `1.0.0`.
- **V1.1** — Hermes (Nous Research) como sistema de agentes bajo el TIE + Learner

**Estado del git**: branch `master` con historia activa. V0.7.1 commiteado
(commit `abf4493`, tag `v0.7.1`). Trabajo V0.8 sobre `master`: B21
(`153f93b`) + Gateway (`a382b99`) + fix del test truncado (`8a961dc`)
commiteados; canal Telegram + DPAPI pendientes de commit local (ver mensaje de
sesión). Regla: un commit por paso terminado. Roadmap en
`AOS_Arquitectura_y_Roadmap.md` + `PLAN_MAESTRO_2026/03_ROADMAP_ACTUALIZADO.md`.

**Tests**: `backend/tests/` pytest — smoke de arranque (`test_smoke.py`),
contratos del API de email (`test_email_contracts.py`, ~30 rutas congeladas +
regresión bug json/log_activity), triaje (`test_email_triage.py`), autonomía +
digest (`test_email_autonomy_digest.py`), meeting detection
(`test_email_assistant.py`). **V0.8**: `test_reasoning_filter.py` (12, B21),
`test_gateway.py` (17), `test_telegram_adapter.py` (10), `test_secrets.py` (6).
Ejecutar: `cd backend && python -m pytest tests/ -v`.

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
- **psycopg2-binary 2.9.10** (driver PostgreSQL; 2.9.10 trae wheels para Python 3.13, la 2.9.9 no compilaba)
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
│   │   │   ├── config.py           # Settings (VERSION=0.7.3, DATABASE_URL dinámico)
│   │   │   ├── secrets.py          # V0.8: cifrado DPAPI de secretos (token TG)
│   │   │   └── logging_config.py
│   │   ├── db/
│   │   │   ├── database.py         # 16 modelos SQLAlchemy + engine dinámico
│   │   │   ├── models.py           # Re-exports
│   │   │   └── schemas.py          # Pydantic v2
│   │   ├── api/endpoints/          # 18 routers: core + 7 email + telegram (ver §6)
│   │   ├── ai/                     # ai_manager, catalog, 9 providers + reasoning_filter (B21)
│   │   ├── agents/                 # AgentManager (15KB) + ArchitectAgent
│   │   ├── gateway/                # V0.8: Gateway channel-agnostic + adapters/telegram (§20)
│   │   ├── memory/                 # ChromaDB MemoryManager
│   │   ├── tools/                  # ToolManager + 8 herramientas (ver §8)
│   │   ├── voice/                  # ElevenLabs + eSpeak
│   │   ├── integrations/           # google_auth.py (OAuth Google)
│   │   └── services/               # email_service.py (helpers email, V0.7.2)
│   ├── tests/                      # pytest: smoke + contratos email + meeting detection
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
- **11 migraciones Alembic** (9ª `a1f2e3d4c5b6_v073_email_triage`; 10ª `b2c3d4e5f6a7_v073_rule_autonomy`; 11ª `c3d4e5f6a7b8_v073b_rule_ai_prompt`):
  - `4ab2071f433f_initial_schema_snapshot_from_sqlite_migration.py` (V0.4)
  - `24b8353ad754_add_agent_fields_and_execution_table.py` (V0.5)
  - `25c926be5811_force_cascade_delete_on_agent_execut...py` (V0.5 fix)
  - `f94e0572d70d_v07_email_calendar_auto_reply_and_.py` (V0.7)
  - `33074ebc50b0_v07_add_google_event_id_to_calendar_.py` (V0.7)
  - `0840fe70d5ce_v07_meeting_proposals.py` (V0.7)
  - `48b15869c4e3_v07_extra_redesign_auto_reply_rules.py` (V0.7)
  - `bff7a3fd8d7d_v07_extra_email_activity_log_and_.py` (V0.7)
- `psycopg2-binary==2.9.10` y `alembic==1.13.1` añadidos a `requirements.txt`
  (bump de 2.9.9 → 2.9.10 en 2026-07: la 2.9.9 no tiene wheel cp313 y compilar
  fallaba en Python 3.13; la 2.9.10 instala precompilada)
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

> **Orden de roadmap acordado (2026-07-04)**: tras el hardening, primero pulido
> de producto (Hub Visual + Voz), luego un salto de memoria (V0.85) ANTES del
> Automation Engine, y finalmente Orchestrator y Hermes. El cliente Web + PWA se
> aplaza a DESPUÉS de V1.0 (no bloquea el resto).

### 🔨 V0.8 — Gateway + Telegram + Security Hardening
Doc: `Fase_5_Clients_Telegram_Web_V08.md` + `PLAN_MAESTRO_2026/06_GATEWAY_V08_DISENO.md`
- ✅ **Gateway + MessageEnvelope** (`app/gateway/`): núcleo channel-agnostic
  (patrón OpenClaw). Ver §20.
- ✅ **Telegram bot**: adapter sobre el Gateway (polling), whitelist por `chat_id`,
  comandos + chat natural, configurable desde Ajustes, token cifrado (DPAPI).
- ✅ **Security Hardening**: CORS restringido a orígenes conocidos (localhost +
  `null` de Electron + extras por `CORS_ALLOWED_ORIGINS`, ya NO `*`); API keys de
  los proveedores IA cifradas en reposo (DPAPI, reusando `app/core/secrets.py`) —
  cifrado al escribir / descifrado al instanciar en el `AIManager`, con migración
  Alembic `d4e5f6a7b8c9_v08_encrypt_api_keys` que re-cifra las existentes.
- ⏳ **Pendiente menor**: PIN/token de red se implementa junto al cliente Web
  (post-V1.0, cuando haga falta exponer a la red).

### ⏳ V0.82 — Hub Visual (pulido de UI) — *etiqueta indicativa*
- Animación de conversación en el Hub (chat con vida).
- Modo pantalla completa con botones para desplegar/plegar las barras laterales
  (tareas, proyectos, funcionalidades, etc.).
- **Estado**: planificado, sin implementar.

### ⏳ V0.83 — Voz completa — *etiqueta indicativa*
- Terminar de configurar las voces principales de ElevenLabs.
- **STT** (speech-to-text) con reconocimiento de voz.
- **Estado**: base existente (`app/voice/`), falta rematar; sin implementar.

### ✅ V0.85 — MOS Skeleton (CERRADA, tag `v0.8.5`)
Salto de memoria de verdad, previo a la automatización y al TIE. Diseño completo:
`PLAN_MAESTRO_2026/07` (implementación) + `08` (arquitectura/RFCs):
- Contratos `IMemoryStore`/`MemoryRouter` + 5 tipos de memoria + tabla `decisions`.
- Ingesta email/calendario en background, resumen nocturno, briefing, contexto
  con atribución de fuente en el chat.
- **[Δ 2026-07-12]** 4 deltas del Cognitive Runtime (docs 14 §4.1 y 16): stub de
  skills con linaje, `decisions.mission_id`, `app/core/events.py` (la ingesta
  emite eventos; spec canónica del bus: `PLAN_MAESTRO_2026/17`), disciplina
  modular (API pública por `__init__.py` + `test_module_boundaries.py`).
- **Estado**: **M1-M5 HECHOS, fase CERRADA** (contratos congelados +
  `LocalMemoryStore`/`MemoryRouter` + stubs + `decisions`/`memory_job_runs` +
  `decision_service` + disciplina modular + ingesta email/calendario +
  `app/core/events.py` + resumen nocturno + `GET /api/memory/briefing` +
  tarjeta Memoria en el Hub + `chat_service.py` (pipeline único de chat,
  contexto del MOS con atribución de fuente y presupuesto de 300 ms) +
  hardening (init async de ChromaDB, 8 índices nuevos, tests de rendimiento);
  ver §1 para el detalle completo por sprint). **Criterio de cierre de fase
  verificado dos veces** (test automatizado con Gmail desconectado +
  verificación manual contra el backend real). Suite: 232 passed, 0 skipped.
  **Deuda diferida a propósito a V0.9** (no estaba en el alcance literal de
  M5): compactación/`lifecycle.py` (RFC-007), `httpx` con conexiones
  persistentes (doc 12 A2).

### ✅ V0.9 — Automation Engine + ApprovalGate (CERRADA, tag `v0.9.0`)
Doc: `PLAN_MAESTRO_2026/11` parte A (sustituye a `Fase_6_Automation_V08.md`) +
plan de sesiones detallado `PLAN_MAESTRO_2026/20_V09_PLAN_SESIONES.md`.
- 4 capas (Triggers/Conditions/Actions/Learner-stub); **APScheduler** en el
  `lifespan` (absorbe los jobs asyncio de V0.85).
- **ApprovalGate genérico** persistente/reanudable — el primitivo que reusan TIE,
  Hermes y skills. `EventTrigger` reactivo sobre los eventos de la ingesta.
- **Permisos & Autonomía (A3b)**: capa de política sobre el gate — permisos
  pre-autorizados auto-resuelven sin preguntar, siempre con rastro de
  auditoría; panel en Ajustes con perfiles rápidos (manual/balanced/full).
- El AE deja rastro en el MOS (`mem_automation`/`mem_error`) y en la Decision
  API (A4) para que el Learner de V1.1/V1.2 nazca con datos reales.
- El AE NO contiene inteligencia: desde V1.0 `AgentTaskAction` delega en el TIE.
- **Estado**: **A1-A4 HECHOS, fase CERRADA** (ApprovalGate + APScheduler +
  lifecycle.py + httpx persistente + motor de reglas/triggers/conditions +
  5 acciones reales + 5 reglas predefinidas + UI de Automatizaciones + Permisos
  & Autonomía + rastro en MOS/Decision API + `AutomationLearner` stub; ver §1
  para el detalle completo por sprint). Suite completa: 351 passed.

### ✅ V1.0 T1-T5 — TIE v1 (bloque CERRADO, tag `v0.9.2`) — MEL/Orchestrator/MVP-beta pendientes
Docs: `PLAN_MAESTRO_2026/14` (TIE/Cognitive Runtime) + `11` parte B (perfil v1) +
`10` (AgentRuntime) + `21` (plan de sesiones T1-T5). Sustituyen a
`Fase_8_Orchestrator_V10.md`. **Decisión de versión (usuario, 2026-07-16)**:
V1.0 se desarrolla por bloques — el TIE cierra en `0.9.2`; MEL (doc 19, E1-E2),
integración Orchestrator y MVP-beta (doc 03 §5 O5) son planes aparte y cierran
la fase COMPLETA en `1.0.0`.
- Módulo `app/tie/`: Intent → Context Enricher → Planner → **TaskGraph**
  (plan-como-grafo serializable) → Graph Execution Engine (lineal en V1.0, con
  checkpoints, gates y kill-switch) → Response Builder → Tracer.
- Camino corto conversational (sin planner) para ~80% de queries. LLL básico
  (detección de tareas repetidas → skills DRAFT con cuarentena, docs 09/15) —
  diferido a V1.1, no en el alcance de T1-T5.
- Enganche clave: `gateway.set_handler(tie.handle)` — un solo punto, sin tocar
  adapters. UI de aprobación de planes. Cierre: MVP beta distribuible.
- **Estado**: **T1-T5 HECHOS, bloque CERRADO** (esqueleto+contratos congelados+
  intent+camino corto, enricher+planner+graph DAG, executor con
  checkpoint/gates/kill-switch/recovery/reanudación, responder+el SWITCH+
  streaming+frontend de Misiones, tests de perf+e2e+cierre de versión; ver §1
  para el detalle completo por sprint, incluidos los 4 fixes/features post-T4b
  pedidos por el usuario). Suite backend: **439 passed**. Pendiente como planes
  APARTE (no son parte de este bloque): **MEL** (doc 19, qué modelo pedir por
  capacidad — hoy `router.py` es un shim de ~30 líneas listo para que E1 lo
  convierta con un cambio de una línea), **integración Orchestrator** (el AE
  migrando `AgentTaskAction` a `tie.submit_mission`, anotado en doc 21 §5 para
  no perderlo), y **MVP-beta** (instalador, auto-start, onboarding).

### ⏳ V1.1 — Hermes Runtime + Learning System
Docs: `PLAN_MAESTRO_2026/10` (Hermes/AgentRuntime) + `15` (Learning System) + `09`.
- Hermes como `AgentRuntime` intercambiable POR DEBAJO del TIE (sprint H0 de
  investigación GO/NO-GO primero; contingencia definida si NO-GO).
- LSL completa + LLL completo + **Mission Learning** (reflexión post-misión) +
  panel "lo que Aithera ha aprendido" con undo.
- **Estado**: diseñado (docs 10/15), sin implementar.

### ⏳ Post-V1.0 — Cliente Web + PWA (aplazado)
- Build de React servido por FastAPI en `/app` (mismo build que Electron, sin
  lógica propia) + PIN/token de red + PWA (manifest + service worker).
- **Aplazado a propósito**: no bloquea Hub Visual, Voz, Memory, Automation ni
  Orchestrator. Se retoma tras V1.0.
- **Estado**: documentado (`Fase_7_WebApp_PWA_V09.md`), sin implementar.

---

## 6. Backend — routers y endpoints activos

18 routers montados en `main.py` (orden de registro):

| Prefijo | Router | Tamaño | Descripción |
|---------|--------|--------|-------------|
| `/api/config` | `config.py` | 1.4KB | Configuración key-value |
| `/api/projects` | `workspace.py` | — | CRUD proyectos (V0.87: absorbido en `workspace.py`, contrato idéntico) + `/{id}/archive` (W4) |
| `/api/tasks` | `workspace.py` | — | CRUD tareas + progreso automático por evento (V0.87) |
| `/api/milestones` | `workspace.py` | ~10KB | V0.87 (WPMS W1): CRUD milestones + `/{id}/complete` (versionado) |
| `/api/workspace` | `workspace.py` | (mismo) | V0.87: `/progress?project_id=` (overall + por milestone) |
| `/api/calendar` | `calendar.py` | 10KB | CRUD eventos |
| `/api/ai` | `ai.py` | 5.9KB | Status, catálogo, configured, test, activate, ollama models |
| `/api/chat` | `chat.py` | 5.7KB | POST /stream (SSE), GET /history, DELETE /history — B21: filtra `<think>` (stream + no-stream) |
| `/api/agents` | `agents.py` | 7.0KB | CRUD agentes + ejecuciones |
| `/api/email` | `email_auth.py` | 113 líneas | OAuth + credenciales + status |
| `/api/email` | `email_inbox.py` | 231 líneas | Inbox, preview (con categoría), búsqueda, summary, triage/run (V0.7.3) |
| `/api/email` | `email_compose.py` | 84 líneas | Draft + send (con confirmación) |
| `/api/email` | `email_auto_reply.py` | ~250 líneas | Reglas auto-reply (CRUD + test + send + feedback de autonomía) |
| `/api/email` | `email_processing.py` | 1017 líneas | process-inbox + process-test (⚠️ dividir en Sprint 3 con el triaje) |
| `/api/email` | `email_meetings.py` | 419 líneas | process-meetings, check-confirmations, proposals |
| `/api/email` | `email_activity.py` | ~260 líneas | Activity log (dashboard) + digest diario |
| `/api/voice` | `voice.py` | 8.6KB | ElevenLabs + eSpeak |
| `/api/tools` | `tools.py` | 2.3KB | Catálogo de herramientas + ejecución |
| `/api/memory` | `memory.py` | 5.6KB | Búsqueda y stats de memoria semántica + V0.85 M2: `ingest/status`, `ingest/run` + M3: `briefing`, `stats` extendido |
| `/api/telegram` | `telegram.py` | ~110 líneas | V0.8: status + configure (token cifrado DPAPI) del canal Telegram |

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
| `Workspace/` | ~5 archivos | ✅ V0.87 W2a: Vista Proyecto + popups (Task/Project/Milestone) ratón-primero. Absorbe Projects+Tasks (eliminados). Board+drag&drop en W2b |

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

## 9. Modelos de base de datos (16 reales)

Definidos en `backend/app/db/database.py`:

| Modelo | Tabla | Propósito | Añadido en |
|--------|-------|-----------|------------|
| `Config` | `config` | Key-value settings | V0.2 |
| `Project` | `projects` | Proyectos (V0.87 WPMS: +`repo_path`,`current_version`,`target_version`,`start_date`,`tags`,`docs`,`archived_at`; `progress` ahora auto por evento) | V0.2 + V0.87 |
| `Task` | `tasks` | Tareas (V0.87 WPMS: +`milestone_id`,`checklist`,`depends_on`,`estimate`,`order_index`,`closed_at`,`links`) | V0.2 + V0.87 |
| `Milestone` | `milestones` | V0.87 (WPMS W1): eje de versión (planned/active/done); progreso calculado, no columna. Definido en `app/workspace/models.py` | V0.87 |
| `CalendarEvent` | `calendar_events` | Eventos (con `google_event_id`) | V0.2 + V0.7 |
| `Conversation` | `conversations` | Sesiones de chat | V0.2 |
| `ChatMessage` | `chat_messages` | Mensajes con `model_used`/`tokens_used` | V0.2 |
| `Agent` | `agents` | Agentes con `allowed_tools`, `max_execution_time` (V0.87 WPMS W2c: +`project_id`,`skills`,`icon`) | V0.5 + V0.87 |
| `AgentExecution` | `agent_executions` | Log de ejecuciones async | V0.5 |
| `EmailAutoReplyRule` | `email_auto_reply_rules` | Reglas de auto-respuesta | V0.7 |
| `CalendarAvailability` | `calendar_availability` | Disponibilidad por tipo de actividad | V0.7 |
| `MeetingProposal` | `meeting_proposals` | Propuestas detectadas en emails | V0.7 |
| `EmailActivityLog` | `email_activity_log` | Auditoría de acciones email | V0.7 |
| `EmailTriage` | `email_triage` | Categoría de triaje por email (7 categorías, 2 etapas) | V0.7.3 |
| `MemoryJobRun` | `memory_job_runs` | Tracking de jobs de memoria (ingesta/summarizer/lifecycle) + checkpoint | V0.85 (MOS M1) |
| `Decision` | `decisions` | Decision Memory (UUID, `mission_id` [Δ]); fuente de verdad + espejo `mem_decision` | V0.85 (MOS M1) |
| `AIProviderConfig` | `ai_provider_configs` | Config de cada proveedor IA | V0.2 |

(17 modelos. `Milestone` vive en `app/workspace/models.py` —disciplina modular
doc 16—, el resto en `database.py`. La memoria semántica del MOS —colecciones
ChromaDB `mem_*`— NO son tablas SQL: viven en ChromaDB vía
`LocalMemoryStore`/`MemoryRouter`, §1.)

**Migración de esquema**: ahora con Alembic (12 migraciones; la 12.ª es
`e5f6a7b8c9d0_v085_mos_skeleton`). NO usar `_ensure_columns()` — eso era de V0.2.
Alembic es la fuente de verdad desde V0.4.

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

### Telegram (V0.8, implementado)
- Adapter sobre el Gateway: `app/gateway/adapters/telegram_adapter.py`
  (`python-telegram-bot 21.10`, polling). Chat natural → `gateway.dispatch`;
  comandos `/start` `/proyectos` `/tareas` `/estado`; whitelist por `chat_id`.
- Configuración desde Ajustes (router `/api/telegram`): token + `chat_id` en la
  tabla `Config`. El token se guarda **cifrado con DPAPI** (`app/core/secrets.py`).
- Registrado en el `lifespan` de `main.py` solo si hay token; si falta la lib o
  el token, se omite y el backend sigue (degradación graceful).
- Config keys: `telegram_bot_token` (cifrado), `telegram_chat_id` (CSV).

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
4. ~~**API keys en BD local — texto plano**~~ — ✅ **SALDADA (V0.8 hardening,
   2026-07-04)**: cifradas en reposo con DPAPI (`app/core/secrets.py`) vía
   `AIManager._enc/_dec` + migración `d4e5f6a7b8c9`. Tolera valores legado en
   plano (decrypt los devuelve tal cual) hasta que la migración los re-cifra.
5. ~~**CORS abierto (`*`)**~~ — ✅ **SALDADA (V0.8 hardening)**: restringido a
   localhost + `null` (Electron) + `CORS_ALLOWED_ORIGINS`. Ver `main.py`.
6. **Sin autenticación de red** — app personal monousuario. El PIN/token para
   exponer a la red local se implementará junto al cliente Web (post-V1.0).

### Deuda técnica crítica

1. ~~**God-endpoint `email_assistant.py` (2038 líneas)**~~ — ✅ **SALDADA
   (Sprint 2, 2026-07-02)**: dividido en 7 routers (auth, inbox, compose,
   auto_reply, processing, meetings, activity — 2 más que los 5 previstos
   porque activity y el pipeline process-* no existían al escribir el plan)
   + `app/services/email_service.py`. Rutas públicas idénticas, verificado
   por tests de contrato. Pendiente menor: `email_processing.py` (1017
   líneas) se descompone en Sprint 3 al construir el triaje.
   De paso se arregló el bug latente `import json as _json` vs `json.`:
   `log_activity` fallaba en silencio y **el activity log nunca había
   persistido nada**. Test de regresión incluido.

2. ~~**Módulos paralelos `app/tools/email_tool.py` vs `modules/email_assistant/`**~~
   — ✅ **SALDADA (Sprint 1, 2026-07-02)**: `backend/modules/` auditado y
   eliminado (código muerto, cero referencias). Veredicto por archivo en
   `PLAN_MAESTRO_2026/05_AUDITORIA_MODULO_LEGACY.md`. Recuperable con
   `git show v0.7.1 -- backend/modules/`.

3. ~~**`backend/app/services/` está vacío**~~ — ✅ **SALDADA (Sprint 2)**:
   primer inquilino real, `email_service.py` (helpers compartidos del dominio
   email: `_email_tool`, `detect_calendar_conflicts`, `_gcal_events_for_date`,
   `log_activity`, `_calendar_find_free_slots`).

4. ~~**Dos versiones de algunos docs de fase**~~ — ✅ **SALDADA (Sprint 4)**:
   `Fase_2_AgentManager_ToolSystem_V04.md` y `Fase_5_Telegram_V07.md`
   archivadas en `archive/`. Quedan las versiones finales (V05, V08).

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

8. **[Graphify audit 2026-07-15] `AitheraApp` (god-object Tkinter legacy)** — el
   grafo de conocimiento detectó que existe un nodo `AitheraApp` con referencias
   a casi todos los módulos del backend. El proyecto migró de CustomTkinter a
   Electron (ver `PLAN_HUB_VISUAL_Y_VOZ.md`) pero este código muerto sobrevivió.
   **Localizar y eliminar antes de V1.0**. Buscar con: `grep -r "AitheraApp" backend/`.

9. **[Graphify audit 2026-07-15] Tests de Telegram cruzan módulos** —
   `test_format_proyectos_lista()` en los tests del adaptador Telegram importa
   el modelo SQL `Project` directamente. Viola la disciplina modular (doc 16).
   **Arreglar en V0.9** (antes del Automation Engine que añadirá más tests).

10. **[Graphify audit 2026-07-15] Test fixture de email toca CalendarEvent** —
    `_clean_email_tables()` borra filas de `CalendarEvent` (cross-domain). Puede
    causar tests de calendario flaky si corren después de tests de email.
    **Arreglar en V0.9** junto con la limpieza general de test isolation.

11. **[Graphify audit 2026-07-15] EmailTool edges inferidos sin verificar** —
    graphify infirió 10 edges desde `EmailTool` hacia `CredentialsPayload` y
    `AutoReplyRulePayload` que no encontró como imports explícitos (posible duck
    typing o acceso dinámico). **Auditar antes de V0.9** cuando el Automation
    Engine empiece a interactuar con el email tool. Verificar con:
    `grep -n "CredentialsPayload\|AutoReplyRulePayload" backend/app/tools/email_tool.py`.

---

## 17. Riesgos técnicos

| Riesgo | Probabilidad | Mitigación |
|--------|--------------|------------|
| Refactor del god-endpoint email_assistant rompa OAuth | Media | Hacer pruebas con cuenta secundaria antes |
| ChromaDB + sentence-transformers ~1.5GB | Media | Documentar peso, descarga solo primer arranque |
| MiniMax cambia su API | Media | `minimax_provider.py` aislado, fácil de actualizar |
| ~~Tres versiones de docs de fase descolocadas~~ | ✅ Resuelto | Sprint 4: archivadas en `archive/` |
| ~~Git sin commits en master~~ | ✅ Resuelto | Sprint 1 (2026-07-02): tag `v0.7.1`, un commit por paso |
| Auto-start backend en producción | Media | Definir mecanismo antes de release |

---

## 18. Decisiones de diseño que guían el proyecto

Estas decisiones son **inviolables** salvo acuerdo explícito del usuario:

1. **No romper lo que funciona** — cada commit deja producto usable. Protege comportamiento CORRECTO y contratos públicos, nunca bugs ni vulnerabilidades: cifrar una key que estaba en plano o cerrar un CORS abierto no es "romper", es corregir (aclaración 2026-07-13, ver AOS §2 principio 1)
2. **Evolución, no reescritura** — refactor solo cuando un módulo impide avanzar
3. **Un backend, múltiples clientes** — Electron/Telegram/Web/PWA son interfaces puras
4. **La IA razona, Aithera decide** — el LLM nunca tiene acceso directo a herramientas
5. **Ejecución controlada** — ExecutionEngine valida whitelist antes de ejecutar
6. **Optimizar para un usuario** — no multi-tenancy, no balanceo. Gobierna infraestructura de escala, no seguridad; no contradice diseñar código que aguante 5 años (doc 16 principio 17 — ver aclaración en AOS §2 principio 6)
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

## 20. Gateway multi-canal (V0.8)

Núcleo channel-agnostic que desacopla los clientes de la lógica de negocio
(patrón OpenClaw). Diseño completo y guía para escribir adapters:
`PLAN_MAESTRO_2026/06_GATEWAY_V08_DISENO.md`.

Piezas en `app/gateway/`:
- `envelope.py` — `MessageEnvelope` (entrante), `OutboundMessage` (saliente),
  `Attachment`. Es EL contrato entre canales y negocio.
- `base.py` — `ChannelAdapter` (ABC): `to_envelope`/`deliver` obligatorios +
  hooks `authorize`/`start`/`stop`.
- `gateway.py` — `Gateway` (registro + `dispatch` con fail-soft) +
  `chat_message_handler` (equivalente channel-agnostic de `/api/chat`, con B21)
  + singleton `gateway`.
- `adapters/telegram_adapter.py` — primer adapter real (ver §13).

Flujo: `canal → adapter.to_envelope() → gateway.dispatch() → handler →
OutboundMessage → adapter.deliver() → canal`. Garantías del `dispatch`: canal
desconocido → `GatewayError`; `authorize()` False → el handler NI se llama;
excepción del handler → fail-soft (mensaje amable al usuario, detalle al log).

Regla de oro (principio 3): la lógica de negocio NUNCA sabe de qué canal vino un
mensaje. Añadir un canal = escribir un adapter fino, cero cambios en el resto.
En V1.0, `gateway.set_handler(orchestrator)` sustituye el chat directo por el
Orchestrator sin tocar ningún adapter.

Registro/arranque en el `lifespan` de `main.py` (`gateway.register(...)` +
`gateway.start_all()` en startup, `gateway.stop_all()` en shutdown).

---

*Última actualización: 2026-07-17 — V1.0 T1-T5 (bloque TIE completo: esqueleto+
contratos, planner+grafo DAG, executor+checkpoint+gates+kill-switch, el SWITCH+
frontend de Misiones, tests de perf+e2e+verificación en vivo+cierre). Tag
`v0.9.2`. Bloques cerrados hasta ahora: V0.2 → V0.7.3 → V0.8 → V0.85 (MOS) →
V0.87 (WPMS) → V0.9 (Automation Engine) → V1.0 TIE v1 (T1-T5). Siguiente (planes
aparte): MEL (doc 19) → integración Orchestrator → MVP-beta (→ cierre `1.0.0`).*
*Construido desde el estado real del repositorio (código + Alembic + docs de fase).*
*Sustituye a la versión V0.2 anterior, que declaraba un estado obsoleto.*

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
