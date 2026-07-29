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

## 0. Lectura obligatoria antes de cualquier tarea

**Antes de planificar o desarrollar CUALQUIER COSA en Aithera, lee primero
[`PRINCIPIOS_KARPATHY.md`](PRINCIPIOS_KARPATHY.md).** Son principios base de
comportamiento (pensar antes de programar, simplicidad primero, cambios
quirúrgicos, ejecución orientada a objetivos) — una capa distinta y anterior
a los principios de arquitectura/producto de este mismo archivo (§18) y de
`PLAN_MAESTRO_2026/16_...md` §1: esos dicen QUÉ construye Aithera,
`PRINCIPIOS_KARPATHY.md` dice CÓMO debe comportarse Claude al construirlo, en
cualquier fase, en cualquier tarea. Se aplican con criterio (tareas triviales
no necesitan el rigor completo — ver la propia nota de trade-off del
documento), pero se leen siempre primero.

Cuando una tarea encaje claramente en un dominio especializado (frontend,
backend, base de datos, seguridad, IA/TIE, testing...), consulta
[`AGENTES_ESPECIALIZADOS.md`](AGENTES_ESPECIALIZADOS.md) y delega en el
subagente curado correspondiente en vez de resolverlo todo de forma
genérica.

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

**V1.0 — MEL v1 (Model Execution Layer, bloque CERRADO sobre `master`; plan de
sesiones `PLAN_MAESTRO_2026/22_MEL_PLAN_SESIONES.md`, sprints E1·E1b·E2·E2b;
diseño maestro doc 19).** La capa universal de ejecución de modelos: el resto del
sistema pide CAPACIDADES (chat/classify/reason/…), el MEL decide QUÉ MODELO. Sin
bump de versión (sigue `0.9.2`): MEL v1 es un bloque de la senda a `1.0.0`, que
cierra con integración Orchestrator + MVP-beta.
- ✅ **E1 — Núcleo** (`app/mel/`, módulo nuevo): contratos CONGELADOS
  (`contracts.py`: `Capability` [8 activas + research/vision/agentic reservadas,
  append-only], `ExecutionRequest`/`ExecutionResult`, `ModelRef`, `PolicyName`,
  `DecisionTrace`). `registry.py` (ENVUELVE `ai_manager` — **único módulo del MEL
  que lo importa**, frontera dura doc 16; `resolve_model_name` fuzzy). `catalog.py`
  (scores curados por (proveedor,modelo)×capacidad — dato, no benchmark).
  `policies.py` (compilador Economy/Quality/Offline + `PolicyStore`). `decision.py`
  (Rule Engine determinista <1ms, ring buffer de 500 trazas, precedencia
  override>pin>política escrita e inactiva hasta E2b). `fallback.py` (clasificación
  de fallos + circuit breakers). `executor.py` (`complete`/`stream` + fallback
  multi-salto + registro async `mel_executions` + `strip_reasoning` B21 aplicado
  aquí para TODOS los callers). Migración 20.ª (`mel_executions`+`mel_policies`).
- ✅ **E1b — Catálogo Auto-Investigado** (`research.py`): al conectar/cambiar un
  modelo (evento nuevo `provider.model_configured`, emitido por `ai.py`), otro
  modelo lo investiga (capacidad RESEARCH activada) y puntúa sus 8 capacidades con
  su propio nivel de **confianza** (informe "bajo" NUNCA mueve el catálogo curado
  — honestidad, doc 19 §5.4.3); persiste `mel_capability_reports` (migración 21.ª).
  `effective_score` = catálogo 50/50 con el informe reciente (salvo confianza
  baja); las políticas compilan con el score EFECTIVO. Refresco cada
  `MEL_RESEARCH_REFRESH_DAYS` (14) por APScheduler. `GET /api/mel/capability-report`.
- ✅ **E2 — Migración de call-sites + EL SWITCH + pantalla Inteligencia**: TODO el
  sistema deja de llamar a `ai_manager` directo y pide CAPACIDADES al MEL
  (grep-cero de `ai_manager.chat(` fuera de `registry.py`, blindado por test).
  ~15 call-sites migrados: `tie/router.py` (el shim que el TIE anunciaba desde T2),
  `chat_service.answer` (CHAT), `NullRuntime.stream_task`+`chat.py` legacy
  (`mel.stream`), email triaje (CLASSIFY)/ai_reply (DRAFT)/inbox summary+summarizer
  (SUMMARIZE, `policy_override=economy` en el job nocturno), las 6 de `email_tool`,
  architect (REASON/CODE). **Recalibración honesta del catálogo** (`catalog.py`
  "ollama"): local bueno-suficiente en tareas estructuradas (classify/summarize/
  extract ≥ umbral Economy → local gratis) pero más flojo en generación abierta
  (chat/draft/reason/code/analyze < umbral → cloud bajo Economy) — sin degradar el
  chat del usuario. Frontend: Ajustes → **Inteligencia** (3 tarjetas + selector de
  política activa 1-clic + cadena capacidad→modelos). Endpoints `/api/mel/policies`
  (+`/active`).
- ✅ **E2b — Personalización de políticas + override explícito** (petición directa
  del usuario intercalada + doc 19 §7b): **(A, petición del usuario)** política
  "Personalizado" (4ª política, lienzo editable = Calidad de partida) + editar el
  modelo PRIMARIO por capacidad en Economía/Calidad/Personalizado (los respaldos se
  conservan solos) + botón **Restaurar** por política (`set_primary`/`restore` en
  `PolicyStore`; endpoints `/mel/models`, PATCH `/mel/policies/{name}/primary`, POST
  `/restore`; UI en Inteligencia). **(B, override explícito, doc 19 §7b)**
  `overrides.py` + `mel_overrides` (migración 22.ª): pin PERSISTENTE de modelo por
  proyecto. Precedencia real en el executor: override de TAREA (`model_override`,
  inmediato, fallo duro si no está) > pin de PROYECTO (persistente, degradación
  suave si su modelo ya no está) > política. `Intent.explicit_model {name,scope}`
  (append-only) + el clasificador lo detecta; pipeline: scope=task → llega a
  `ExecutionRequest.model_override` por camino corto Y complejo; unspecified →
  pregunta el alcance sin ejecutar; project → `set_project_override` + rastro en
  Decision API; nombre no resuelto → responde con las opciones reales, nunca
  inventa. `project_id` fluye misión→`AgentTask`→`answer`→`context_tags` para que
  el pin de proyecto se lea en ejecución. UI: lista de pines borrables en
  Inteligencia. **Bug encontrado en la verificación en vivo del reparto por tipo y
  arreglado**: `policy_override` recompilaba la política en vez de leer las
  ediciones persistidas del usuario (`chain_for_named`, test de regresión). Suite:
  **508 passed**. Verificado en vivo contra Postgres + proveedores reales: TIE→MEL
  respondiendo, reparto por tipo (chat→minimax, code→ollama con Personalizado),
  override de tarea, pin de proyecto leído por el executor. **Nota de diseño
  observada** (no bug): con los 2 modelos actuales el auto-catálogo (E1b) puntúa el
  llama3 real como capaz (confianza "media"), así que Economy→todo local y
  Quality→todo cloud (uniforme); el reparto por tipo DENTRO de una política aparece
  con modelos de fuerzas distintas por capacidad (p.ej. Ornith code-especialista) o
  a mano con Personalizado. **Pendiente como planes APARTE** (no MEL v1): integración
  Orchestrator (AE `AgentTaskAction`→`tie.submit_mission`) y MVP-beta.
- **V1.0 — Capacitación de tools (bloque CERRADO sobre `master`, 2026-07-18)**:
petición directa del usuario ANTES de la integración del Orchestrator — "revisa
si las tools existentes realmente funcionan en testeos en vivo o si están
puestas pero no son funcionales" + añadir las que faltaban de una lista concreta.
Sin bump (sigue `0.9.2`).
- **Auditoría en vivo de las 6 existentes** (contra sistemas REALES, no mocks):
  filesystem/shell/powershell/git → **22/22 OK**, incluidas las defensas
  (path traversal, binario fuera de whitelist, encadenamiento de comandos, repo
  fuera de HOME). email/calendar → lectura real OK; la escritura
  (create_draft/send_email/create_event) se verificó con el cliente de Google
  MOCKEADO a propósito: enviar un email o crear un evento real en la cuenta del
  usuario no se hace sin permiso explícito. **Hallazgo real (config externa, no
  bug)**: la Google Calendar API NO está habilitada en el proyecto de Google
  Cloud (403 real) → `list_events`/`get_event`/`create_event`/`sync_to_aithera`
  fallan hasta habilitarla a mano en Google Cloud Console; `find_free_slots`
  degrada bien porque ya tenía fail-soft alrededor de la llamada a Google.
- **Adjuntos en el Email Assistant**: `create_draft`/`send_email` ganan
  `attachments: list[str]` dentro del MISMO `email_tool.py` (no un sistema
  aparte) — `MIMEMultipart` + reuso literal de la validación de paths de
  `FilesystemTool` (solo dentro de HOME, límite 15MB). Verificado: adjunto real
  embebido en el MIME, `Content-Disposition` correcto, path fuera de HOME
  rechazado, caso sin adjuntos idéntico a antes.
- **8 tools nuevas** (ver §8 para el detalle): `process`, `secrets`, `memory`,
  `model`, `download`, `search` (Brave+SerpAPI con fallback, configurables en
  Ajustes → Búsqueda web), `browser` (Playwright/Chromium real) y `desktop`
  (ratón/teclado + OCR nativo de Windows). Total: **14 tools, 91 acciones**.
- **Permisos**: `browser.use`/`computer.use` pasan de `available=False`
  ("próximamente") a `True` — cambio de UN flag, exactamente como el diseño de
  A3b anticipaba; el frontend no necesitó tocarse (ya leía el flag).
- **Rendimiento**: `desktop_tool` importaba pyautogui+winocr a nivel de módulo
  (+0.44 s en el import de `app.main`, medido, porque el ToolManager registra
  todas las tools al arrancar) → corregido a import LAZY, mismo patrón que
  Playwright. Arranque de ~1.93 s → ~1.73 s.
- Tests: `test_new_tools.py` (31) + 2 de `test_permissions.py` actualizados.
  Suite: **539 passed**. `tsc`/`vite build` limpios.
- **Pendiente REAL que esto destapa** (el siguiente bloque): `agent_manager.
  _run_execution()` sigue siendo el **placeholder de V0.5** — ignora la tarea
  del usuario y ejecuta acciones fijas de demo (`list_dir`/`list_scripts`/
  `git status`) según qué tools tenga el agente. Las 14 tools existen y son
  asignables, pero **ningún agente decide todavía cuál usar**: eso es
  exactamente lo que resuelve la integración del Orchestrator.

**V1.1** — Hermes (Nous Research) como sistema de agentes bajo el TIE + Learner

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
├── PRINCIPIOS_KARPATHY.md          # lectura obligatoria (§0)
├── AGENTES_ESPECIALIZADOS.md
├── PLAN_MAESTRO_2026/              # docs de diseño vigentes (01-31)
├── docs/                           # [2026-07-21] guías y docs sueltos reubicados
│   ├── GUIA-OAUTH-GOOGLE.md
│   ├── PLAN_HUB_VISUAL_Y_VOZ.md    # decisión migración CustomTkinter → Electron
│   ├── Systems Schema.md           # catálogo de endpoints y modelos
│   └── IDEA.md · Documentación de Desarrollo.md
├── archive/                        # histórico
│   ├── fases/                      # [2026-07-21] TODOS los Fase_*.md/docx viejos
│   └── crewai-ajeno/               # restos de CrewAI (gitignored, borrable)
├── test-lab/                       # [doc 31] misiones de prueba (gitignored)
├── scratch/ + backend/scratch/     # depuración suelta (gitignored)
├── "ideas guays"/ideas guays.docx  # ideas sueltas del usuario
├── iniciar_frontend_react.bat
├── .claude/settings.local.json     # config de Claude Code
├── .trae/skills/aithera-context/SKILL.md     # skill de Trae IDE
└── CLAUDE.md                       # este archivo
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
- Cierre de los 6 bugs P1–P6 documentados en `archive/fases/Fase_1_Estabilizacion_Hub_V03.md`

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

### ✅ V1.0 — MEL v1 (Model Execution Layer, bloque CERRADO) — Orchestrator/MVP-beta pendientes
Docs: `PLAN_MAESTRO_2026/19` (diseño maestro) + `22` (plan de sesiones E1-E2b).
La capa universal de ejecución de modelos: el resto pide CAPACIDADES, el MEL
decide QUÉ MODELO. Sin bump (sigue `0.9.2`) — MEL v1 es un bloque de la senda a
`1.0.0`.
- Módulo `app/mel/`: contratos congelados + `registry` (envuelve `ai_manager`,
  frontera dura) + `catalog` (scores curados) + `policies` (Economy/Quality/
  Offline/**Custom**) + `decision` (Rule Engine determinista) + `fallback`
  (breakers) + `executor` (complete/stream + registro) + `research` (auto-catálogo
  E1b) + `overrides` (pin por proyecto E2b).
- **EL SWITCH**: todo el sistema pide capacidades al MEL (grep-cero de
  `ai_manager.chat(` fuera de `registry.py`). El TIE, el chat, el email, el
  summarizer, architect — todos por `mel.complete`/`mel.stream`.
- **Control del usuario** (Ajustes → Inteligencia): política activa 1-clic +
  personalizar el modelo por capacidad en Economía/Calidad/Personalizado +
  Restaurar + override explícito ("usa DeepSeek para esto" / "todo el proyecto con
  Claude") + pines de proyecto borrables.
- **Estado**: **E1-E2b HECHOS, bloque CERRADO** (núcleo + auto-catálogo + migración
  de call-sites + pantalla Inteligencia + personalización + override explícito;
  ver §1 para el detalle por sprint). 3 migraciones (20-22) aplicadas al Postgres
  real. Suite backend: **508 passed**. Verificado en vivo (TIE→MEL, reparto por
  tipo, override de tarea, pin de proyecto). **Pendiente como planes APARTE**:
  integración Orchestrator (AE→`tie.submit_mission`) + MVP-beta → cierran V1.0 en
  `1.0.0`. **Deuda menor anotada**: el `lifespan` no llama `ensure_ready()` (las
  políticas compilan en el primer uso, default Economy — funciona, pero no hay
  políticas hasta la primera petición); el auto-catálogo puede puntuar generoso un
  local capaz (confianza "media" mueve el catálogo) — revisable si se quiere
  Economy más agresiva hacia cloud en generación abierta.

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
| `/api/search` | `search_config.py` | ~95 líneas | V1.0 (Tools): status + configure/deconfigure de los proveedores de búsqueda (Brave/SerpAPI), keys cifradas DPAPI — mismo patrón que Telegram |
| `/api/tie` | `tie.py` | — | V1.0 TIE: misiones (list/get/cancel/approve-plan/delete) |
| `/api/mel` | `mel.py` | — | V1.0 MEL: capability-report (E1b) + policies/active + models/primary/restore + overrides (E2/E2b) |

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

## 8. ToolManager — 15 herramientas registradas (96 acciones)

El paquete `app.tools` se importa en `main.py:15` como efecto secundario
para auto-registrar las herramientas en el `ToolManager`. Sin este import,
`GET /api/tools/` devuelve `[]` y el AgentManager no puede ejecutar nada.
El catálogo lo consume la UI de agentes (`allowed_tools`) de forma DINÁMICA:
registrar una tool nueva la hace asignable sin tocar el frontend.

| Tool | Archivo | Capacidades | Añadida |
|------|---------|-------------|---------|
| `filesystem` | `filesystem_tool.py` | list_dir, read_file, write_file, create_dir, delete_file, file_exists (whitelist: solo dentro de HOME) | V0.4 |
| `shell` | `shell_tool.py` | ejecutar comandos con whitelist estricta (python, pip, git, npm, node, npx, uvicorn) | V0.4 |
| `git` | `git_tool.py` | status, log, diff, branch_list, show_file, add, commit | V0.4 |
| `powershell` | `powershell_tool.py` | run_script (solo .ps1 predefinidos en `~/AitheraScripts`), list_scripts | V0.5 |
| `email` | `email_tool.py` | Gmail REST + auto-reply + meeting detection + **adjuntos** (V1.0) | V0.7 |
| `calendar` | `calendar_tool.py` | Google Calendar + availability + free slots + proposals | V0.7 |
| `process` | `process_tool.py` | list_processes, cpu_status, ram_status, open_program (whitelist), close_program (protege el sistema y el propio backend) | V1.0 |
| `secrets` | `secrets_tool.py` | get/set/list(enmascarado)/delete — cifrado DPAPI en tabla `Config` (namespace `secret:`) | V1.0 |
| `memory` | `memory_tool.py` | search/save/update/delete sobre el MOS (vía `memory_router`, nunca ChromaDB directo) | V1.0 |
| `model` | `model_tool.py` | list/load/pull/delete modelos de Ollama + gpu_ram_status (psutil + nvidia-smi) | V1.0 |
| `download` | `download_tool.py` | download_url (tarea de fondo, no bloquea el timeout del manager), get_download_status, cancel_download | V1.0 |
| `search` | `search_tool.py` | search_web/news/images/videos — Brave Search API primero, SerpAPI como respaldo (Ajustes → Búsqueda web) | V1.0 |
| `browser` | `browser_tool.py` | Playwright/Chromium real: open_url, new_tab, close_tab, google_search, click, type, scroll, wait_for_element, download_file, upload_file, screenshot, get_html, get_text | V1.0 |
| `desktop` | `desktop_tool.py` | click, double_click, type, hotkey, move_mouse (SIEMPRE confirmación) + screenshot, ocr, find_text_on_screen (OCR nativo de Windows vía winocr) | V1.0 |
| `document` | `document_tool.py` | read_pdf (texto, rango de páginas), read_docx, read_xlsx (lectura, sin confirmación) + write_docx (bloques: heading/paragraph/table), write_xlsx (filas/hojas) (escritura, confirmación → `filesystem.write`). pypdf/python-docx/openpyxl lazy. Solo dentro de HOME. #218 | V1.0 |
| — | `base.py` | Interfaz `BaseTool` que implementan todas | V0.4 |
| — | `tool_manager.py` | Registro centralizado + whitelist por agente + timeout duro + log de auditoría | V0.4 |

**Dependencias de las tools de V1.0**: `psutil` (process/model), `playwright`
(browser — requiere además `playwright install chromium` UNA vez, ~300MB fuera
de pip), `pyautogui` + `winocr` (desktop), `pypdf`+`python-docx`+`openpyxl`
(document, #218 — Python puro, sin binarios ni modelos que descargar).
Playwright, pyautogui/winocr y las 3 de document se importan de forma **LAZY**
a propósito: importarlos a nivel de módulo añadía coste al arranque de `app.main`
(medido ~0.44 s solo con pyautogui) porque el ToolManager registra todas las
tools al importar, aunque nadie use nunca esas tools. Verificado con document:
`import app.tools` NO carga pypdf/docx/openpyxl.

**Elección de OCR (V1.0)**: `winocr` (motor nativo de Windows) en vez de
`pytesseract` (exige instalar el binario Tesseract aparte, un instalador de
Windows no automatizable) o `easyocr` (arrastra su propia versión de PyTorch,
con riesgo real de romper la que ya usan sentence-transformers/ChromaDB —
confirmado al intentar instalarlo: quiso bajar torch 2.13.0 sobre el 2.12.1+cpu
existente).

**[2026-07-23] Chrome REAL + perfil persistente + cookies definitivas**
(petición del usuario): `browser_tool` ya NO usa el Chromium "de test" con
perfil de usar-y-tirar. Ahora lanza el Google **Chrome instalado**
(`BROWSER_CHANNEL="chrome"`, respaldo a Chromium bundled) sobre un **perfil
PERSISTENTE propio de Aithera** (`%APPDATA%/Aithera/chrome-profile`, override
`BROWSER_PROFILE_DIR`): el usuario inicia sesión en Google UNA vez y queda; las
cookies/consentimientos sobreviven a misiones y reinicios. No es el perfil de
uso diario del usuario a propósito (Chrome ≥136 bloquea la automatización sobre
el user-data-dir por defecto, y su Chrome abierto lo tiene bloqueado) — perfil
propio persistente = mismo efecto práctico sin pelea. Con perfil persistente
las misiones COMPARTEN el contexto (sesión de Google compartida es el objetivo)
y solo se aíslan las pestañas; `close_session` cierra las pestañas de la misión
pero NO el contexto compartido. **Muro de cookies — arreglo DEFINITIVO** (`_dismiss_consent` v2, 3 capas):
(1) lo APRENDIDO para ese dominio (persiste en `consent_learned.json` del
perfil — "que aprenda de forma definitiva"), (2) catálogo de 15 CMPs
mayoritarios por CSS (página + iframes), (3) botón/enlace por TEXTO de
aceptación en 5 idiomas (ES/EN/FR/DE/PT, atraviesa shadow DOM) para los CMPs
caseros. Todo éxito se aprende; sumado al perfil persistente, un muro solo
cuesta tiempo UNA vez por sitio en la vida del perfil. Se reintenta ANTES de
cada `click`/`type` (YouTube lo reinyecta). Tests sin red:
`test_browser_consent_v2.py` (11) + `test_audit_s3_browser.py` (fixture al modo
efímero). Verificado en vivo con Chrome real: YouTube y El Mundo cargan
contenido real, cero cookies visibles.

**Limitaciones reales conocidas** (verificadas en vivo, no supuestas):
`browser.google_search` funciona a nivel de código pero Google bloquea el
tráfico headless como sospechoso → para buscar de verdad se usa `search`
(Brave/SerpAPI), no el navegador. En la máquina del usuario, `desktop.hotkey`
con `Ctrl+A`/`Ctrl+C` se comporta de forma anómala — reproducido igual con 3
mecanismos de inyección independientes (pyautogui, librería `keyboard`,
SendInput con scancodes físicos), lo que descarta un fallo de la tool; otras
combinaciones (`Ctrl+Z`, teclas sueltas) funcionan bien.

**[2026-07-23] `document_tool` — documentos de oficina reales (#218)**: cerraba
un hueco de capacidad básico (Aithera no podía leer un PDF ni entregar un
XLSX/DOCX de verdad). 15.ª tool, 5 acciones: `read_pdf` (texto, rango de
páginas opcional), `read_docx`, `read_xlsx` (lectura, sin confirmación) +
`write_docx` (bloques heading/paragraph/table o `content` plano) y `write_xlsx`
(filas simples o varias hojas) (escritura → confirmación, mapeada a
`filesystem.write` en el catálogo de permisos). Alcance HONESTO: PDF solo
LECTURA (generar PDF es reportlab/weasyprint, mucho más pesado y menos
necesario, fuera de alcance); un PDF escaneado no tiene texto que extraer → el
resultado lo avisa y sugiere OCR (`desktop_tool`/winocr). Librerías `pypdf` +
`python-docx` + `openpyxl` (Python PURO, sin binarios ni modelos que descargar —
misma disciplina que se evitó con pytesseract/easyocr), importadas de forma
LAZY (verificado: `import app.tools` no las carga). Reusa EXACTAMENTE la
validación de paths de `filesystem_tool` (solo HOME, sin traversal). Con límites
(25MB por archivo, 200 páginas, 500k chars, 5000 filas/hoja) para no volcar un
libro entero al contexto del LLM. Frase curada en `capabilities_map` (el chat
sabe presentarla). Tests: `test_document_tool.py` (16 — ciclos completos
escribir→leer de XLSX y DOCX, extracción de texto de un PDF hecho a mano,
aviso honesto sin texto, seguridad de paths, confirmación por acción,
helper de rango de páginas). Suite: **886 passed**. Verificado en vivo contra
las librerías reales (round-trips) y leyendo un PDF real del usuario.

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
| Claude Code | `ClaudeCodeProvider` | CLI local (`claude -p`) | `sonnet` | **Sin API key** — usa la sesión Pro/Max del CLI. No apto para chat/classify/agentic (MEL) |
| Codex (OpenAI) | `CodexProvider` | CLI local (`codex exec`) | `""` (modelo de la cuenta) | **Sin API key** — usa la sesión de ChatGPT (`codex login`) o `--with-api-key`. Repo oficial `openai/codex` (Apache-2.0). No apto para chat/classify/agentic (MEL) |

(Más proveedores por API: Kimi/GLM/Qwen. La tabla histórica listaba 8; hoy hay
13 en `PROVIDER_CLASSES`.)

**Proveedores por CLI (Claude Code, Codex)** — `claude_code_provider.py` /
`codex_provider.py`: NO hablan HTTP con una API; ejecutan el binario que el
usuario ya tiene instalado y logueado (`claude` / `codex`) en modo NO
interactivo. En `NO_KEY_PROVIDERS` (sin API key). Botón "Activar" de 1 clic en
Ajustes → Proveedores (comprueba el CLI y lo deja enrutando). `is_local=False`
en el MEL (servicio de pago con sesión en la nube, jamás cuenta como local) y
`UNFIT_CAPABILITIES` = {chat, classify, agentic} (arrancan un proceso por
llamada, lentos, sin streaming; aptos para programar/razonar/redactar/analizar
en segundo plano). **Disponibilidad de Codex por plan** (página de precios
oficial de OpenAI, 2026-07-24): incluido en Free/Go/Plus/Pro/Business/Edu/
Enterprise; el README del repo lista un conjunto más estrecho (sin Free/Go), así
que la UI dice "incluido en tu plan de ChatGPT" y ofrece la API key como
alternativa si el login con ChatGPT no funcionara.

**Instalar + login asistidos (2026-07-24, `app/api/endpoints/codex_setup.py` +
`components/settings/CodexSetup.tsx`)**: para que CUALQUIER usuario lo active sin
terminal — botón **"Instalar Codex"** → `npm install -g @openai/codex` (paquete
OFICIAL del registro npm, en un hilo con progreso; MISMO patrón que la
instalación de Kokoro/Ollama; NO se usa el instalador `curl … | sh` — ejecutar un
script remoto es justo lo que se evita) + botón **"Iniciar sesión"** → lanza
`codex login`, que abre el NAVEGADOR del usuario para que inicie sesión con su
cuenta de ChatGPT (Aithera NUNCA teclea las credenciales — auto-rellenar la
contraseña no es posible ni permitido; es el mismo modelo del OAuth de Google que
ya existe). Éxito detectado por `~/.codex/auth.json`; si el navegador no se abre,
la UI muestra la URL para abrirla a mano. Guía rápida (comandos exactos) SIEMPRE
visible como respaldo. Endpoints: `GET/POST /api/codex/{status,install,login}`.
**Verificado en vivo con codex-cli 0.145.0**: `npm install` real OK (~7 min, el
worker da 30), `codex --version` OK, `/status` reflejando installed/authenticated,
y el `codex exec` real sin sesión → 401 detectado con la pista `codex login`
(hallazgos en vivo aplicados: `stdin=DEVNULL` para que "Reading additional input
from stdin…" no cuelgue; el error y la pista se muestran por la COLA del stderr,
no el banner).

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
- Documentación en `docs/GUIA-OAUTH-GOOGLE.md`
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
7. **Ejecución de tools solo por whitelist, sin aislamiento de proceso** —
   `shell_tool`/`powershell_tool`/`desktop_tool`/`browser_tool` validan contra
   una whitelist de comandos, pero corren en el proceso del backend, sin
   contenedor/sandbox. La comparativa competitiva (2026-07-24, doc 32 Anexo)
   confirmó que 2 de 3 sistemas OSS punteros (OpenClaw: Docker; Hermes:
   Docker/SSH/Singularity/Modal/Daytona/OpenShell; OpenJarvis: WASM+Docker) lo
   tratan como imprescindible. **Programado: sandboxing Docker opcional en V1.4**
   (doc 27 §8 S1, degradación graciosa a whitelist si no hay Docker). No urge
   (sin incidentes; app monousuario), pero es la brecha de seguridad más
   consistente frente a la competencia.

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
   Electron (ver `docs/PLAN_HUB_VISUAL_Y_VOZ.md`) pero este código muerto sobrevivió.
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

> Estas son decisiones de **arquitectura/producto** (QUÉ construye Aithera).
> Para principios de **comportamiento** (CÓMO debe trabajar Claude en
> cualquier tarea — pensar antes de programar, simplicidad, cambios
> quirúrgicos, objetivos verificables), ver
> [`PRINCIPIOS_KARPATHY.md`](PRINCIPIOS_KARPATHY.md) (§0, lectura obligatoria
> antes de empezar cualquier tarea).

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

## 21. Bloque ORQUESTRATOR (V1.0, cerrado en `0.9.5`)

Plan de sesiones: `PLAN_MAESTRO_2026/23_ORQUESTRATOR_PLAN_SESIONES.md` (R1-R7).
**La capa POR ENCIMA del TIE**, no un renombrado: decide QUÉ MISIONES hay;
el TIE decide los pasos DENTRO de una misión; el MEL decide el modelo.

**El problema que resuelve** (doc 23 §0): antes, «revisa mis emails **y además**
apunta esta idea» acababa en UNA misión con pasos secuenciales — el planner
colapsaba encargos heterogéneos y el segundo se perdía o esperaba al primero.

| Sprint | Qué añadió |
|---|---|
| **R1** | `tie/toolloop.py` — el bucle elegir→ejecutar→observar. **Δ2**: el TIE NUNCA había ejecutado una tool (el nodo solo llevaba una whitelist y nadie escribía `metadata.tool_call`): decía haber listado archivos y se los inventaba. Era un fallo de honestidad, no de funcionalidad |
| **R2** | `app/orchestrator/` — `decomposer` (1 mensaje → N objetivos con dependencias), `conductor` (concurrencia + semáforo + aislamiento + anidamiento), `consolidator`, `store`. Migración 24 (`orchestration_runs`) |
| **R3** | `tools/aithera_tool.py` — Aithera se opera a sí misma (proyectos/tareas/agentes/reglas/cron). **Adaptadores**, nunca reimplementan lógica de negocio. `internal=True`: no es asignable a un agente, es del Orquestador |
| **R4** | `tie/authority.py` — frontera de autoridad por misión. `agent_manager._run_execution` deja de ser el placeholder de V0.5 y delega en el TIE con la whitelist del agente; `AgentTaskAction` del AE también |
| **R5** | Checkpoints verificables (reusando el ApprovalGate) + `core/notify.py` (aviso por el canal preferido) + cron desde el chat que sobrevive al reinicio |
| **R6** | `tie/capabilities_map.py` — el chat sabe qué puede hacer Aithera, generado DESDE el código (no una lista a mano que envejece). Navegación fluida: `search` → `browser` |
| **R6.5a** | `ExecutionRequest.messages` + los 12 proveedores (OpenAI-compat / Anthropic / Gemini / Ollama / Claude Code, 4 formatos incompatibles). Solo la tubería: el chat responde igual que antes |
| **R6.5b** | Continuidad real: `chat_messages.session_id` (migración 25) + ventana de turnos con presupuesto + la consulta al MOS deja de ser el mensaje suelto |
| **R6.5c** | `memory/profile.py` — hechos estables del usuario destilados en el job nocturno, visibles y borrables en Ajustes |
| **R7** | Cierre: E2E con la cadena real, rendimiento medido, auditoría, bump `0.9.5` |

**Números de R7** (medidos, no prometidos):
- **Overhead del Orquestador en el camino de 1 objetivo: 0,0017 ms** (presupuesto
  50 ms). La regla de no-regresión de doc 23 §0 —el ~80% de los mensajes no paga
  ni una llamada extra al LLM ni latencia— era una promesa escrita; ahora está
  medida y con test que la vigila.
- Concurrencia real verificada contra Postgres: pico de 2 misiones simultáneas,
  `ORCH_MAX_CONCURRENT` respetado, dependencias sin paralelizar.

**Limpieza de R7** (deuda del propio bloque, saldada): se retiró el subárbol
muerto de `tie/router.py` (`fast`/`smart`/`choose`/`active_model` + los settings
`TIE_FAST_MODEL`/`TIE_SMART_MODEL`) — desde E2 la elección de modelo la hace el
MEL y aquello era un segundo mando desconectado; 5 imports sin usar; 3 cabeceras
que describían un pasado ya sustituido. Los jobs del MOS (`ingestion`,
`summarizer`, `lifecycle`, `profile`) pasan a exponerse en el barrel de
`app.memory` de forma PEREZOSA (PEP 562) y quedan vigilados por
`test_module_boundaries.py`: eran 12 imports cruzando la frontera del módulo sin
que nadie lo notara, y hacerlos eager habría roto el presupuesto de arranque.

---

## 22. Bloque CORRECCIÓN POST-AUDITORÍA (pre-1.0, en curso)

Auditoría de comité (doc 24) sobre 4 fallos reales de producción → plan de
corrección en 4 sesiones (doc 25). **S1 EJECUTADA (2026-07-20, Fable 5)**:
- **A-1** `tie/toolloop.py`: grounding — `ok=True` exige ≥1 tool ejecutada con
  éxito; answer sin tools se rechaza con feedback o se acepta como FALLO
  honesto (nunca éxito inventado).
- **A-2** `automation/approval.py` + toolloop: `ApprovalGate.expire()` nuevo —
  el timeout de espera EXPIRA la aprobación (claim atómico, evento
  `approval.expired`); cero aprobaciones cadáver en la UI.
- **D-1** `automation/permissions.py`: catálogo 9→11 permisos
  (`tie.plan_approval` high, `tie.checkpoint` low, grupo "Misiones") +
  `_GATE_KIND_PERMISSION` + `is_kind_pre_authorized()` — el perfil Autónomo
  ya cubre los gates del TIE. Frontend sin tocar (grupos dinámicos).
- **#9** `app/desktop.py` → tombstone (borrado final: `git rm`).
- **#10** `core/events.py`: set `_inflight` retiene tasks de handlers (GC).
- Tests: `test_audit_s1_fixes.py` (10 nuevos) + 4 existentes actualizados a
  los contratos nuevos + `test_permissions.py` (9→11).
- **Pendiente S1**: correr suite completa en Windows + verificación en vivo.
**S2 EJECUTADA (2026-07-20, Fable 5)**:
- **C-1** fidelidad del goal: `Intent.raw_text` (append-only, estampado por
  `classify()` tras el parseo — el LLM no puede pisarlo); `_complex_path`
  planifica sobre el texto ORIGINAL, el goal reescrito queda solo para UI;
  prompts del clasificador ("resumen fiel, no añadas") y del planner (REGLA
  DE ORO de fidelidad + OBJETIVO "única fuente del plan" + contexto "SOLO
  REFERENCIA") reescritos; `submit_mission(intent=…)` opcional. El conductor
  sigue clasificando por objetivo A PROPÓSITO (intent per-objetivo más
  preciso; el daño era solo la reescritura, que raw_text elimina — doc 25).
- **B-1** capacidad honesta: `_tools_catalog_text()` (el planner ve acciones
  reales, no solo nombres); **`PlanRejection`** — `{"cannot": …}` del modelo →
  respuesta honesta al usuario sin ejecutar nada (≠ None que degrada);
  `_MAX_REASONABLE_NODES` 6→8; `TIE_TOOL_MAX_ITERS_WRITE=12` +
  `runtime._iters_for()` (presupuesto ampliado para nodos de construcción).
- Tests: `test_audit_s2_fixes.py` (14: 10 de C-1/B-1 + 4 de C-1b). Cero rotos.
**S2-extra EJECUTADA (2026-07-20, Fable 5)** — petición del usuario (trabaja en
varios proyectos, la memoria de uno no puede colarse en otro):
- **C-1b** aislamiento determinista de proyecto: `context()` (interfaces/router/
  local_store) gana `project_id` (append-only) — items con `project_id` distinto
  se excluyen, los sin etiqueta (general) entran; filtro en Python, no Chroma.
  Lectura: enricher (con project_id en caché) ← executor/`mission.project_id`,
  `_context_for`, `chat_service`. Escritura: el toolloop etiqueta con
  `authority.project_id` toda `memory.save_memory` en misión de proyecto.
- **Fix entorno**: `pyproject.toml` raíz era de CrewAI (resto ajeno) y sus
  addopts rompían `pytest` — era EL error del usuario; sustituido por config
  mínima de Aithera.
- **Verificado en el sandbox contra el CÓDIGO REAL** (deps ligeras instaladas,
  pesadas evitadas por imports lazy): A-1 grounding (toolloop.run real), A-2
  (ApprovalGate real+SQLite), C-1b (LocalMemoryStore.context real), D-1
  (permissions real), C-1/B-1/#10 (contracts/planner/events reales) + 17/17
  lógica pura. **Pendiente en Windows**: suite completa + verificación en vivo.
**S3 EJECUTADA (2026-07-20, Fable 5)**:
- **A-3** `tools/browser_tool.py`: `_dismiss_consent()` (10 selectores de CMPs
  mayoritarios, best-effort, 1.2s×3 máx) se ejecuta tras cada `goto` ANTES de
  reportar éxito — llegar al muro de cookies no es llegar a la página;
  `_page_state()` devuelve `{tab_id,url,title,text_excerpt,consent_dismissed}`
  en `open_url`/`new_tab`/`google_search` (el modelo sabe dónde aterrizó sin
  otra llamada).
- **F-1** sesión de navegador POR MISIÓN: el estado global
  `_pages`/`_current_tab` (condición de carrera real con `ORCH_MAX_CONCURRENT=3`)
  se sustituye por `_sessions: {mission_id: _Session}` con BrowserContext
  propio; `AgentTask.mission_id` (append-only) → `toolloop.run(session_key=…)`
  inyecta `params["_session"]` solo para `browser` (lo pone el código, no el
  modelo); `close_session()` + `executor._release_mission_resources()` liberan
  el contexto al terminar la misión (`_CLEANUP_TASKS` retiene las tasks).
- Tests: `test_audit_s3_browser.py` (10, sin red, dobles de Page/Context);
  fixture de `test_new_tools.py` actualizada al modelo de sesiones.
- Verificado contra el código real (browser_tool + toolloop reales). **Vivo con
  Chromium pendiente**: "abre youtube.com" → title/text_excerpt del contenido.
**S4 EJECUTADA (2026-07-20, Fable 5)** — `tests/test_product_contracts.py`
NUEVO (13 tests): la capa que faltaba, la que valida COMPORTAMIENTO en las
costuras entre módulos (los 4 fallos de producción pasaron los 751 tests de
módulo). UN solo fake (frontera del LLM); ToolManager escribiendo en disco
real, ApprovalGate y permisos reales, sin red, limpieza total por test. Los 8
contratos: "si digo que lo he hecho, lo he hecho" · "lo que pido es lo que se
planifica" · "si te doy permiso de antemano, no me preguntas" · "una aprobación
inútil no se queda ahí" · "si te pido un archivo, el archivo existe" · "si solo
hice parte, te digo qué parte" · "si te digo que pares, paras" · "nunca te
quedas sin respuesta". **Hallazgo descubierto al escribirlos**: sin el permiso
`filesystem.write` concedido una misión de archivos NO escribe nada (correcto,
pero no estaba cubierto ni documentado — explica en parte el fallo B). **Regla
de mantenimiento**: todo bug de producción entra aquí como test que falla ANTES
de arreglarse. Verificado contra código real (contratos 1/4/5/7; el kill-switch
cortó un nodo de 30s en 0,04s sin escribir nada).
**BLOQUE DE CORRECCIÓN COMPLETO** — los 8 hallazgos bloqueantes tratados.
Pendiente en Windows: suite completa + verificación en vivo de los 3 escenarios
de aceptación (doc 24 §5) + decisión Playwright/Chromium en el instalador.

---

## 23. Bloque OPTIMIZACIÓN (pre-1.0, en curso) — doc 26

Plan maestro de optimización en `PLAN_MAESTRO_2026/26_PLAN_OPTIMIZACION_V095.md`.
Primer sprint (O1-O3) EJECUTADO (2026-07-20, Fable 5):
- **O1 — Latencia de voz** (conversación fluida tipo GPT/Alexa): STT modo `fast`
  (`whisper_stt.py`: modelo `base` + `beam_size=1` + VAD 250ms +
  `condition_on_previous_text=False`; endpoint `/transcribe?fast=true`; el chat
  de voz lo usa). TTS **streaming por frases** (`Chat.tsx::speak` +
  `splitIntoSpeechChunks`: sintetiza la 1.ª frase y empieza a sonar en ~0.5s,
  prefetch de 1). Turn-taking 1200ms→**700ms**. Palanca futura V1.1: streaming
  LLM→TTS + barge-in.
- **O2 — Settings como modal** (`components/Modal.tsx` NEW + `Settings.tsx`):
  de página-scroll a pantalla completa → modal centrado (`max-w-5xl`,
  `max-h-88vh`) con tab-rail de 6 pestañas (IA y Modelos · Permisos · Voz ·
  Conexiones · Memoria · Sistema). Esc/clic-fuera cierran, scroll de fondo
  bloqueado, animación suave. **Cero funciones perdidas**. `tsc` limpio.
- **O3 — Rendimiento/deuda**: polling visibility-aware (`hooks/usePolling.ts`
  NEW + Hub/Missions/Automation: no sondean con la ventana oculta) + **lazy
  routes** (`App.tsx`: `React.lazy`+`Suspense`, solo el Hub eager — arranque más
  ligero) + banner `iniciar_app.bat` 0.3.0→0.9.5 + `AitheraApp` legacy confirmado
  solo en el tombstone `desktop.py`.
Segunda tanda (V1-V3, 2026-07-20, Fable 5) — investigada contra la **JWIKI
`08_VOICE/`** (presupuesto TTFB < 2s, Whisper no es streaming):
- **V1 — Voz natural**: `voice/text_clean.py` gana **`clean_for_speech()`**
  (markdown, tablas, enlaces, código y emojis fuera del TTS) — antes la voz
  decía "asterisco asterisco" y leía guiones de lista. **Barge-in completo**:
  `stopSpeaking()` + `watchForBargeIn()` (escucha con `echoCancellation`
  mientras habla; 250ms de voz sostenida corta la locución) + el botón del
  micro también interrumpe; se registra lo REALMENTE dicho y el turno siguiente
  lleva contexto OCULTO al modelo ("te interrumpieron, solo oyó X, no repitas")
  vía `sendMessage(text, {prefix})`.
- **V2 — Personalidades** (`app/ai/personalities.py` NEW): la personalidad
  **compone sobre** el prompt base, NUNCA lo sustituye (una personalidad no
  puede desactivar el texto plano ni la honestidad — reglas nacidas de la
  auditoría). "Aithera" por defecto derivada de la filosofía real del proyecto
  + 4 estándar (Profesional/Cercana/Concisa/Didáctica) + **la propia**: el
  usuario la describe en bruto y `improve_prompt()` (MEL, REASON) la convierte
  en un bloque de tono bien formado, con salvaguarda anti-mentira. Endpoints
  `/api/voice/personalities`; UI `components/voice/PersonalityPicker.tsx`.
- **V3 — Voz por defecto garantizada**: `GET /api/voice/defaults` resuelve
  SIEMPRE una voz (la del usuario o la mejor del idioma; EdgeTTS por ser el
  único gratis sin key) **y la persiste**. Cierra el bug de que Aithera
  respondiera muda hasta ir al Centro de Voz a elegir a mano.
Tercera tanda (VZ1/VZ5 + P1/P2/P3 + D-#10/#11 + U1, 2026-07-20, Fable 5):
- **VZ1 — streaming LLM→TTS** (`Chat.tsx`): `beginSpeechStream()` — la voz
  arranca mientras el modelo AÚN escribe; cada token alimenta una cola que
  extrae frases y sintetiza al vuelo. Verificado: la 1.ª frase suena al ~37%
  del texto en respuestas largas. El barge-in vive en la misma cola.
- **VZ5 — profiling**: cada turno de voz imprime `[voz-perfil] stt/llm_1er_token/
  voz_suena` en consola del navegador + STT en el log del backend. Herramienta
  para medir qué etapa domina en la máquina del usuario (antes se optimizaba a
  ciegas). **Siguiente**: hacer turnos reales y decidir VZ2/VZ3/VZ4 con datos.
- **P1** `hooks/usePolling.ts` aplicado a TODAS las páginas (Chat/Settings/
  Sidebar además de Hub/Missions/Automation): ningún poll corre con la ventana
  oculta. **P3** `ChatBubble` memoizado (no re-parsea markdown de mensajes
  viejos en cada token del streaming).
- **D-#10** `CalendarEvent` sale del autouse de limpieza de email (cross-domain,
  graphify §16.10); fixture dedicada `_clean_calendar_events`. **D-#11**
  verificado: los edges EmailTool→Payloads eran falsos positivos de graphify.
- **U1** `components/ConfirmDialog.tsx` (`useConfirm`): reemplaza `window.confirm()`
  nativo por diálogo con la estética de la app; aplicado a Missions y Agents,
  resto pendiente (mismo patrón por sitio).
- **Pendiente de voz (doc 26 §VZ)**: VZ2 modelo `tiny`/GPU, VZ3 Silero VAD, VZ4
  Realtime API — decidir con los datos del profiling. VZ1/VZ5 ya hechos.
- **Pendiente (doc 26 §⏳)**: P4 arranque backend, U1 confirm() restantes
  (Settings/EmailAssistant), U2/U3 (empty-states, focus-trap). P1/P2/P3 hechos.
  P3 re-renders de Chat, P4 arranque backend, D-#9/#10/#11 (hygiene de tests),
  U1-3 (Modal en otros diálogos, focus-trap), V1-2 (streaming LLM→TTS, barge-in).
  Verificado por `tsc --noEmit` (exit 0) en todos los cambios de frontend +
  `py_compile` en los de backend. **Pendiente en Windows**: suite completa +
  vivo (medir fluidez de voz real, vistazo al modal de Settings).

---

## 24. Bloque LATENCIA DEL RUNTIME + AUTÓNOMO 100% (pre-1.0, 2026-07-20)

Petición directa del usuario: las misiones (incluso mecánicas como "abre
YouTube y pon X") tardaban muchísimo, y el modo Autónomo seguía pidiendo
permiso para el navegador. Rastreado, diagnosticado y arreglado:

**Diagnóstico de latencia** (rastreo del flujo Orchestrator→TIE→MEL→toolloop):
una misión mecánica hacía ~8-9 llamadas al LLM secuenciales, **7 de ellas al
modelo de razonamiento MÁS LENTO** — porque (a) el planner usa REASON, y
(b) `Capability.AGENTIC` (el bucle de tool-use, **una llamada por cada acción**)
heredaba de `reason`. Con MiniMax/DeepSeek (razonadores con `<think>`) eso son
25-50s. Ese era el arranque lento Y la lentitud entre acciones.

**Fixes** (sin tocar ningún timeout → no rompe misiones):
- **AGENTIC → CLASSIFY** (`mel/catalog.py`): elegir la siguiente herramienta de
  un catálogo es una tarea estructurada rápida, no razonamiento profundo. Ahora
  cada acción usa el modelo rápido. Es el mayor recorte (aplica a TODO toolloop,
  directo y complejo).
- **Camino de ACCIÓN DIRECTA** (`tie/pipeline.py` + `Intent.is_direct_action`):
  una tarea mecánica de un solo encargo (sin `requires_planning`, no
  multi-objetivo) salta el planner y su grafo multi-nodo; un ÚNICO bucle de
  tool-use la resuelve de corrido. "Abre YouTube y pon la canción" pasa de ~8-9
  llamadas (7 lentas) a **3 rápidas, 0 al planner**. Verificado contra el
  pipeline real.
- **Clasificador afinado** (`tie/intents.py`): distingue "secuencia mecánica de
  acciones" (requires_planning=false → directa/rápida) de "plan estructurado con
  dependencias/entregables" (true → planner). Ante la duda mecánica, false.
- **Profiling** (`toolloop.py` + `pipeline.py`): cada paso loguea
  `[tie-perfil] toolloop paso N: modelo Xms` — para medir en la máquina real qué
  domina.

**Modo AUTÓNOMO 100% — fix definitivo** (`automation/permissions.py`): el bug
era que el perfil `full` ENUMERABA permisos individuales; si el usuario lo
activó antes de que existieran `tie.plan_approval`/`browser.use` (añadidos en
S1), su config persistida no los tenía y el gate del plan (que incluye el
navegador) seguía preguntando. Ahora `autonomy_is_full()` lee el PERFIL activo,
y `is_pre_authorized`/`is_kind_pre_authorized` auto-aprueban CUALQUIER gate o
permiso —presente o futuro— cuando el perfil es `full`. A prueba de kinds que
aún no existen. La regla de oro A3b intacta: auto-aprobado deja rastro en
`approvals` (no es silencioso). `manual` sigue fail-closed. Verificado contra el
ApprovalGate real.

Tests: `test_runtime_latency_autonomy.py` (8: autónomo total auto-aprueba
cualquier gate incl. futuros, manual sigue preguntando, gate real sin pending,
mecánicas→directa, complejas→planner, AGENTIC=CLASSIFY en los 12 proveedores).
Verificado end-to-end: "abre YouTube y pon X" = 3 llamadas AGENTIC, 0 al planner.

**2ª pasada de latencia (2026-07-21, con logs REALES del usuario)** — el
profiling `[tie-perfil]` reveló la causa raíz que el análisis estático no vio:
- **Cada paso del toolloop = 13-18s en `claude_code/opus`.** El cambio
  AGENTIC→CLASSIFY no bastaba: la política activa del usuario ("custom") elige
  el modelo de MÁXIMA CALIDAD por capacidad, que seguía siendo opus. Fix:
  `TIE_TOOL_POLICY` (default **"economy"**, local-primero) — el toolloop se
  enruta SIEMPRE por una política rápida, no la de calidad del usuario. Cada
  paso baja de ~15s a ~1-3s. Escape hatch `TIE_TOOL_MODEL` (ej.
  `claude_code:haiku`) si el modelo local resulta flojo para el navegador.
- **El auto-catálogo del MEL (`mel.research`) competía DURANTE la misión**:
  investigaba opus/sonnet/haiku/fable con el modelo de calidad, serializando el
  proveedor. Fix: investiga con `policy_override="economy"` (barato) + su job de
  arranque se retrasa de 90s a 900s (fuera de la ventana de primer uso).
- **El muro de cookies REAPARECÍA al clicar** (YouTube lo reinyecta): `_click`/
  `_type` ejecutan `_dismiss_consent` ANTES de interactuar; y `_dismiss_consent`
  ahora escanea también los IFRAMES (Google/YouTube meten el consentimiento en
  `consent.youtube.com` dentro de un iframe que `page.locator` no veía).
- Tests: +1 (`test_toolloop_fuerza_politica_rapida_no_la_de_calidad`).
**Pendiente en Windows**: relanzar backend, medir `[tie-perfil]` (debe bajar de
15s/paso a 1-3s) + verificar YouTube en vivo (canción sin pausarse).

---

## 25. Bloque UX + MEL-UI + OBSERVABILIDAD (2026-07-21, Fable 5)

Tres sesiones largas de peticiones directas del usuario. Sin bump (sigue `0.9.5`).

**UX/tema (tanda 1 + 2 correcciones)**:
- **Tema claro/oscuro**: colores como variables CSS por tema (`styles/index.css`
  `:root,.dark` / `.light`; `tailwind.config.js` los consume con
  `rgb(var(--x) / <alpha>)`) + `store/useThemeStore.ts` (persistido) + toggle en
  Ajustes. 2ª pasada tras feedback: **NADA blanco en claro** — escala completa
  de grises (lienzo 224, tarjetas 238, nunca 255) + borde neutro + sombra suave
  (`--panel-shadow`); `Modal.tsx` usa `.modal-panel` temado.
- **REGLA DE ORO (2 correcciones furiosas del usuario): el AVCS es la IDENTIDAD
  de Aithera — NUNCA se adapta al tema.** Se probó una paleta "tinta" y se
  revirtió al 100%. El "velo blanco" en claro era el fondo de la página
  transparentándose tras el canvas (partículas aditivas sobre claro = lavadas):
  arreglado con un ESCENARIO oscuro fijo `#0a0a0f` en el contenedor de
  `AitheraPresence` cuando la ruta es el Hub — pixel-idéntico en ambos temas,
  engine intacto. La etiqueta central del Hub usa tinta clara FIJA.
- **Electron**: `show:false` + `maximize()` al abrir; F11 fullscreen total; Esc sale.
- **Scanner de hardware** (`core/hardware.py` + `GET /api/local-models/hardware`):
  CPU (nombre vía registro de Windows)/RAM/GPU-VRAM → recomienda modelo Ollama
  (óptimo + inferior + superior-solo-si-sobra; umbrales GPU 0.80/0.65 vs RAM
  0.55/0.40) y tier AVCS (Q1-Q4). Panel informativo en Ajustes → Sistema.
- **Doc 30**: plan de las features mayores (onboarding+auto-config, i18n
  ES/EN/FR/PT, OAuth fácil, Kokoro/Docker, AVCS-detrás-de-Workspace).

**Ajustes reorganizado**: pestañas ia·permisos·voz·**hub (HUB Visual:
Apariencia + Presencia visual)**·conexiones·memoria·sistema; **Voz absorbe TODO
el Centro de Voz** (`components/voice/VoicePanel.tsx`; `pages/VoiceCenter.tsx` =
tombstone re-export, ítem del sidebar retirado, `/voice` redirige); modal de
TAMAÑO FIJO (`fixedHeight`); fila TTS fija (texto a 2 líneas, botones quietos);
Kokoro: el endpoint de instalación pip existía a ciegas — ahora hilo con salida
capturada + estados idle/installing/done/failed visibles + botón "Instalar
Kokoro" con sondeo; voces EdgeTTS FR/PT + "Crear Voz"→ElevenLabs.

**Modelos locales**: familias PLEGADAS con chevron SVG 22px; sección "Modelos
locales — descarga e instalación" (la activación vive en Proveedores); botón
"Eliminar" real (borra en Ollama, libera GB); **fix self-heal `/enable`** (bug
real qwen3:14b: la fila `local_models` solo la creaba el instalador propio — si
el modelo llegó a Ollama por otra vía, 404 "no instalado"; ahora el DISCO es la
fuente de verdad y se da de alta al vuelo); familia **Llama** añadida al
catálogo (llama3.2:3b / llama3 / llama3.3:70b).

**Proveedores de IA**: dos grupos ENMARCADOS — "En tu equipo" (un card por
modelo local INSTALADO con toggle → `LocalModel.enabled`, lo que el MEL lee; sin
API key) y "En la nube" (ordenada: activados > conectados > sin conectar).
**Claude Code CLI**: renombrado, descripción "Plan Pro/Max: sin API key…",
botón **Activar** 1-clic (test CLI → persiste config+interruptor en BD entre
sesiones, verificado con AIManager nuevo), sin selector de modelos (los 4 se
asignan en Inteligencia). **Catálogo jul-2026 verificado con búsqueda web**:
GPT-5.6 Sol/Terra/Luna + 5.5/5.4/5.4-mini (ids del changelog oficial), Claude
fable-5/opus-4-8/sonnet-5/haiku-4-5, Gemini 3.5 Flash, MiniMax M3/M3-highspeed,
DeepSeek v4, Grok 4.5/Build 0.1, Kimi K3, GLM-5.2, Qwen3.7-Max. `model_labels`
+ `description` por proveedor — **FIX: el schema Pydantic
`AIProviderConfigResponse` RECORTABA los campos nuevos** (response_model filtra;
añadidos al schema).

**MEL-UI vinculado de verdad** (el bug reportado: Sidebar/Estado decían
"minimax" con la política Personalizado en Claude): `useAppStore.chatPrimary` =
primario de CHAT **EFECTIVO** de la política activa (salta no-aptos) →
Sidebar, Hub (etiqueta central + barra) y "Estado del Sistema de IA" muestran
LO MISMO; el punto rojo ya no viene del health legacy sino del breaker del chat
primario. Badges de tarea por card desde la política ACTIVA (fuera el "Chat"
legacy). **Fallos visibles**: `CircuitBreaker.last_reason` + `open_reason()` →
`health_summary().down_detail` → panel "⚠ Modelos con problemas" + modelos en
rojo en cadenas y selects. **Inteligencia**: título "(MEL: Model Execution
Layer)", 4 POSICIONES editables por capacidad (`PolicyStore.set_slot`, PATCH
`/mel/policies/{name}/slot`; la 4ª SOLO locales — rechazado en backend),
nombres cortos compartidos (`lib/modelNames.ts`: "Claude CLI · Opus 4.8",
"MiniMax · M3-highspeed"), hint destacado en recuadro. **Banner naranja
"trabajando solo en local"** (`GET /api/mel/health-summary`: local_only cuando
TODA la nube configurada tiene breaker abierto y hay local; AppLayout con (?)
y deep-link a Ajustes→IA vía `location.state.tab`). Fable 5 = el más capaz en
el catálogo MEL (corregido; Quality lo elige primero).

**Gating de capacidades UNFIT** (fallo real de producción, "caso Melendi": el
chat por Claude CLI respondió con su identidad de terminal y latencias de
minutos): `mel/catalog.py::UNFIT_CAPABILITIES` — `claude_code` ∉
{chat, classify, agentic} en 3 capas: compilador excluye, **filtro RETROACTIVO
en ejecución** (`active_chain`/`chain_for_named` sanean políticas ya editadas
sin tocarlas), UI excluye/⛔ + aviso en la tarjeta. Verificado en vivo.

**Telemetría de misiones punta a punta** (doc 31): `app/telemetry/`
(disciplina modular) + tabla `mission_events` (**migración 26.ª
`a7c8d9e0f1a2`, PENDIENTE de `alembic upgrade head` en el Postgres real**).
Hooks quirúrgicos best-effort: `tie/tracer.py` (record_start fija contextvar +
mission_start/intent/plan/mission_end con duración), `mel/executor._record_async`
(CADA llamada LLM: capacidad/modelo/latencia/fallbacks), `tie/toolloop.py`
(cada tool con duración y error), `tie/executor.py` (contexto al reanudar +
node_end). API `GET /api/telemetry/missions/{id}` (timeline+resumen) y
`/api/telemetry/report?hours=` (agregado). Purga diaria 04:35 (retención =
TIE_MISSION_RETENTION_DAYS). **Test-lab**: `test-lab/` (gitignored) +
`backend/scripts/mission_lab.py` (batería HTTP real: files/code/web/browser/
memory/multi — desktop excluido) + `mission_report.py` (timeline legible +
`--aggregate`). Ciclo de mejora en doc 31 §5.

**Orden del repo (2026-07-21)**: raíz y backend/ SOLO esenciales. Movidos:
`Fase_*` → `archive/fases/`; guías → `docs/`; restos CrewAI → 
`archive/crewai-ajeno/` (gitignored, borrable); `_test_*.py`/logs de backend →
`backend/scratch/` (gitignored). Gitignored además: `TripoSR/`, `otsaas/`
(proyectos AJENOS dentro de la carpeta — recolocar fuera), `backend/Aithera/`
(datos ChromaDB), `graphify-out/`. **Si algo de esto estaba trackeado, hace
falta `git rm -r --cached`** — ver INSTRUCCIONES_CLAUDE_CODE.md.

**Pendiente en Windows** (delegado a Claude Code vía
`INSTRUCCIONES_CLAUDE_CODE.md`): `alembic upgrade head` (migración 26.ª),
suite completa pytest, batería `mission_lab.py` + baseline, commit de todo.

---

## 26. Auditoría global del runtime — campañas de test en vivo + S1 (2026-07-27)

Doc `PLAN_MAESTRO_2026/34_AUDITORIA_GLOBAL_RUNTIME.md` — auditoría global pedida
por el usuario tras una sesión real con 5 fallos (catálogo de tools divergente,
narración sin anclar, coste sin medir, auto-catálogo del MEL compitiendo con el
usuario, camino caliente lento). Propuesta P1-P5 sin capas nuevas, plan de
sesiones S1-S5 (luego S1-S9 tras la campaña 01), y protocolo de campañas de
test en vivo para MiniMax M3 (doc 34 §11, regla de oro: **nunca toca código**).

- **Campaña 00** (`test-lab/campanya-00-baseline/`, MiniMax M3): 18 tests. Su
  RESUMEN.md tuvo 3 falsos positivos (verificados y refutados por Claude
  contrastando contra la evidencia CRUDA que el propio MiniMax archivó —
  `timing.txt`/`log.txt`/`execution-final.json`: el "cuelgue" era timeout de
  cliente de 30s + falta de deadline arriba de los 180s del provider (→NEW-2);
  la "mentira" del approval era verdadera esa vez, pero reveló que la
  narración del chat no se deriva del estado (refuerza P2); los "89
  tool_calls" eran `len()` sobre un string JSON de 89 caracteres, la llamada
  real fue 1). Minado el log completo (nadie lo había revisado entero):
  **LOG-1** — dos tests de `test_tie_planner.py` (`test_enricher_presupuesto_
  agotado_devuelve_vacio`, `test_enricher_error_del_mos_no_rompe`) llevaban
  desde S2-extra probando un `TypeError` de binding en vez de lo que decían
  probar (`context()` ganó `project_id` y solo se actualizó UNO de los tres
  fakes) — el presupuesto de latencia del enricher, protección central del
  camino caliente, sin cobertura real. **LOG-2**: la suite de tests escribe en
  `logs/system.log` de producción (127 líneas de fakes mezcladas con actividad
  real). **LOG-3**: fallo real nocturno del dedup del MOS + un pin de proyecto
  huérfano a un modelo no configurado. §11.7 (reglas R1-R8) nace de los 3
  falsos positivos, para que no se repitan en campañas futuras.
- **Campaña 01** (`test-lab/campanya-01-cobertura/`): Bloque R completo (9/9,
  con `VEREDICTO.md`+`telemetry.json` en todos). Bloques N/X no alcanzados —
  el propio Bloque R encontró algo más grave: **fabricación de resultados de
  tool en el CAMINO CORTO** (confirmado 3 veces en 20 min — fuentes web con
  cita nunca visitadas, estructura de `backend/app` inventada al 0% de
  coincidencia con el disco, resumen de documento sin leerlo — pasa cuando
  `classify` falla su JSON con `llama3`, ~40% de las veces en la máquina del
  usuario, y el camino corto no tiene el guardarraíl de A-1/S1 porque nunca se
  diseñó con tools). Nace **P6/S6**. Otros hallazgos: el panel de Misiones NO
  ofrece el gate de permiso de tool (solo existe en el Chat) → **S7**, junto
  con permisos individuales inertes bajo el perfil Autónomo sin aviso en la
  UI y un mensaje de log que atribuye la causa equivocada; `GET /api/tie/
  missions/{mission_id}` 404 con el id real, 200 con `trace_id` (reabre la
  tarea #208) → **S8**; fuga de sesión de navegador entre misiones
  concurrentes reproducida en vivo pese al fix de F-1/S3 → **S9** (reabre).
  El aislamiento de `mem_personal` por proyecto, pendiente desde la campaña
  00, esta vez sí se probó bien: **sin fuga observada** (aunque sin barrera
  estructural — el chat nunca manda `project_id`, deuda anotada, no bug).
- **S1 EJECUTADA (2026-07-27, Sonnet)**: **P1** — `tool_manager.tie_catalog()`
  (accesor único con `include_internal=True`) usado por los 4 sitios que antes
  llamaban por separado (`graph.py` tenía el bug: le faltaba el flag, así que
  el planner ofrecía `aithera` y el validador la rechazaba — 8 reproducciones
  confirmadas). Test de invariante nuevo (el catálogo que el planner OFRECE es
  la MISMA llamada que el que el validador ACEPTA — no pueden divergir).
  **P4** — `mel/research.py` excluye proveedores por CLI del auto-catálogo
  (`claude_code`/`codex`, fallaban siempre y costaban minutos); nace
  `nightly_refresh()` (como mucho `MEL_RESEARCH_MAX_PER_NIGHT`=1 modelo,
  `force=False`); el job pasa de dispararse a los 900s del ARRANQUE del
  backend a un cron nocturno (04:40, junto a los del MOS). Decisión explícita
  documentada sobre el resto de fallos JSON del research (no CLI): se deja
  best-effort a propósito — tras las dos correcciones de alcance, el peor caso
  ya es "como mucho una llamada perdida cada 14 días de madrugada", no "45
  minutos compitiendo con el usuario". **NEW-3**: resuelta SIN código — la
  campaña 01 verificó en vivo que la hipótesis del mismatch de `mission_id`
  no se reproduce; el problema real (el gate de permiso de tool no tiene UI en
  Misiones) es distinto y se movió a S7. **Hallazgo real de la verificación**:
  2 test-doubles de `ToolManager` (patrón LOG-1 — un doble de un contrato que
  evoluciona debe evolucionar con él) no implementaban `tie_catalog()`,
  corregidos. Verificado en el sandbox: ~370 tests relevantes en verde;
  `test_product_contracts.py` 8/13 en aislamiento (los 5 restantes tienen un
  `approval_wait_s=120` real por diseño, ajeno a P1/P4, no ejecutable en el
  presupuesto de este sandbox). **Pendiente en Windows**: suite completa +
  verificación en vivo repitiendo los 8 encargos del 25-jul. El plan de
  sesiones completo (S1-S9) vive en doc 34 §10; siguiente sesión: **S6**
  (grounding en el camino corto, Opus) — la más urgente de las que quedan.
- **S10 EJECUTADA (2026-07-27, Sonnet)** — no era parte del plan S1-S9, la
  encontró el usuario probando P1 en vivo: creó un agente en el proyecto
  "Cordyceps" con `filesystem`+`browser`, le pidió leer el GDD del proyecto y
  escribir un documento de investigación — el agente escribió
  `Cordyceps_Wiki.docx` **fuera** de la carpeta del proyecto, en
  `C:\Users\Alejandro\`. Causa raíz: `app/tie/authority.py::_PATH_PARAMS` (lo
  que `Authority._check_path_scope()` usa para saber qué parámetros de qué
  tools tienen que quedarse dentro de `Authority.repo_path`, R4 doc 23) solo
  cubría `filesystem`/`git` — `document` (#218, lectura/escritura de
  `.docx`/`.xlsx`/`.pdf`) y `download` escriben a disco igual que
  `filesystem.write_file` pero nunca pasaban por la frontera de proyecto.
  **Arreglo**: `_PATH_PARAMS` gana `document`/`download`/`browser` — esta
  última SOLO para sus 2 acciones con parámetro `path`
  (`download_file`/`upload_file`); navegar/buscar/hacer clic en la web sigue
  sin restricción a propósito (petición explícita del usuario: "aunque hagan
  búsquedas web fuera de la carpeta" — internet es externo, el disco local
  no). El resto del mecanismo (`_check_path_scope`, `commonpath` contra `..`)
  no cambió. **Caveat**: solo se activa si el proyecto tiene `repo_path`
  configurado (📁 en `ProjectPopup.tsx`, opcional desde V0.87 W2e) — sin
  carpeta asignada no hay frontera que imponer, por diseño ya documentado.
  Tests nuevos en `test_agent_execution.py` (3, mismo estilo que los de
  `filesystem` ya existentes): repro exacta del bug, descargas, y que
  `browser` solo restringe la descarga (no la navegación). Verificado en el
  sandbox: los 3 nuevos + los 16 del archivo en verde. Documentado en doc 34
  §10 (nueva sesión S10). No se creó ningún documento "Cordyceps Wiki" real —
  era solo el caso de prueba del usuario, no un encargo. **Pendiente en
  Windows**: repetir el escenario exacto (agente con `document` asignado,
  proyecto con carpeta) y confirmar que el archivo aterriza dentro.
- **Doc 34 reestructurado (2026-07-28, Fable 5)**, petición del usuario: cada
  sesión pendiente lleva un **«Diseño ejecutable»** contrastado contra el
  código (archivo, función, cambio exacto, tests) para que el modelo que la
  ejecute implemente y verifique, no diseñe. Dos **fusiones**: **S2·S6** (el
  mismo grounding aplicado a las 3 capas que redactan prosa) y **S7·S8** (el
  panel de Misiones y su API; el fix de S7 necesita el id único de S8). Al
  diseñar se encontraron **dos causas raíz** que estaban como "hay que
  investigar": **S5** — `executor._execute_node` construye el contexto de un
  nodo SOLO con memoria del MOS; el resultado de los nodos de los que depende
  (`node.depends_on`) no se le pasa por ningún camino, así que "lee X y haz Y"
  solo funciona si ambas cosas caen en el mismo nodo (no hay tubería, y esa es
  la causa real de "el contenido no llegó a la sesión"); **S9** —
  `browser_tool._ensure_browser()` no tiene lock, así que dos misiones
  concurrentes lanzan dos navegadores sobre el mismo perfil persistente, Chrome
  bloquea el segundo y los globals se pisan → `TargetClosedError` en AMBAS.
  El **§11 (protocolo de campañas)** pasa de MiniMax a **Claude** y gana 4
  bloques nuevos: **REG** (regresión de cada sesión cerrada, abre toda
  campaña), **F** (entradas variadas: erratas, idioma mezclado, mensajes
  kilométricos, contradicción, referencia al turno anterior, ambigüedad…),
  **N** (las 10 áreas nunca probadas) y **X** (adversarial: inyección desde
  web/archivo, traversal, doble aprobación en carrera).
- ✅ **S2·S6 EJECUTADA (2026-07-28, Fable 5) — narración anclada en las TRES
  capas** (P2 de la campaña 00 + P6 de la campaña 01, fusionadas). Los dos
  fallos que cierra: (a) el email del 25-jul que SE ENVIÓ y el chat dijo
  "necesito tu confirmación" sin que existiera ninguna aprobación donde
  confirmarlo; (b) las 3 fabricaciones del camino corto de la campaña 01
  (fuentes web con cita nunca visitadas, estructura de `backend/app` inventada
  al 0% de coincidencia, resumen de un documento sin leerlo).
  **`app/core/grounding.py` NUEVO** (funciones puras, 0 LLM, ES+EN):
  `claims_completed_action` · `claims_pending_approval` ·
  `claims_future_action` · `with_honesty_note`. **Desviación deliberada del
  diseño** (que lo situaba en `app/tie/`): lo usan tres módulos —
  `tie/responder`, `orchestrator/consolidator` y `services/chat_service`— y los
  internos del TIE no se importan desde fuera (doc 16); `app/core/` es la capa
  compartida, como `strings.py`/`events.py`. **Capa 1 — consolidator SIN LLM en
  ningún caso**: fuera `_SYSTEM_PROMPT`, `_detalle()` y la llamada a
  `mel_complete`; los `outcome` que el responder ya redactó se concatenan de
  forma determinista (el cap por outcome sube 400→1200 chars: lo que era una
  plantilla de respaldo es ahora LA respuesta). El propio código YA reconocía
  que esa pasada no aportaba con 1 objetivo — se extiende a N. **Capa 2 —
  `responder._is_grounded()`**: si el texto dice que falta el visto bueno y
  NINGÚN nodo está en `WAITING_APPROVAL` (fuente: el grafo, que el executor
  persiste en cada transición), se descarta y sale la plantilla determinista.
  **Capa 3 — camino corto**: `chat_service.answer()` y
  `NullRuntime.stream_task()` añaden la coletilla honesta; en streaming se
  acumulan los chunks y se juzga la respuesta ENTERA al terminar (una
  afirmación puede repartirse entre chunks). **El riesgo atendido es el
  ruido**: los patrones NUNCA marcan verbos cognitivos ("he pensado", "he
  entendido") ni acciones sobre la propia conversación ("he leído tu
  mensaje"), y una promesa seguida de su cumplimiento ("voy a leer… lo he
  leído y dice X") tampoco se marca — 14 de los 34 tests son negativos por
  esto. **Simplificación sobre el diseño**: la 2.ª comprobación del responder
  ("afirma acción sin ningún paso hecho") se retiró por código muerto —
  `build()` ya desvía a `_template_failure` sin nodos DONE. **Limpieza
  propia**: quitar `_detalle()` dejó huérfanas 5 claves i18n × 4 idiomas
  (`orchestrator.state_*`), retiradas; su test se actualizó al contrato nuevo
  en vez de borrarse (patrón LOG-1). Tests: `test_audit_s2s6_grounding.py`
  NUEVO (34) + 191 de las áreas tocadas en verde. **Comprobación de
  mutación**: desactivando el grounding del runtime, el test del streaming
  falla — ejercita el código real. **Pendiente en Windows**: suite completa +
  criterio de cierre en vivo (los 3 casos de T05 y el caso del email).
- ✅ **S3 EJECUTADA (2026-07-28, Sonnet) — presupuesto de llamadas LLM por
  camino, MEDIDO** (P3, doc 34 §10): hasta ahora "va lento" no tenía número —
  había que reconstruir del log a mano qué camino tomó un turno. `tie/
  pipeline.py` gana `_record_path()` (best-effort, `telemetry.record("path",
  name=...)`), llamado en las CUATRO funciones reales que deciden el camino de
  un turno: `_short_path`/`_short_path_stream` (+ el precheck/quick_answer) →
  "chat", `_direct_action_path` → "direct", `_complex_path` → "planned"
  (cubre a la vez el chat complejo, la degradación a corto tras un plan
  inválido, y `submit_mission` — los tres pasan por la misma función).
  `orchestrator/__init__.py` gana `_record_multi_path()` en los 3 sitios donde
  un mensaje se confirma multi-objetivo (`_orchestrate`, `_orchestrate_stream`,
  `submit`), registrado bajo el id del propio run (no hay "mission" para la
  orquestación en sí, cada objetivo tiene la suya). **4 presupuestos nuevos**
  en `config.py` (env-overridables): `BUDGET_LLM_CHAT=0` (el camino corto
  nunca crea mission_id, techo teórico) · `BUDGET_LLM_DIRECT=6` ·
  `BUDGET_LLM_PLANNED=12` · `BUDGET_LLM_MULTI_PER_OBJECTIVE=8`.
  `telemetry.mission_timeline()` extendida de forma ADITIVA (el `summary` que
  ya devolvía gana `llm_calls`/`path`/`budget`/`within_budget`/
  `slowest_llm_ms`; sin evento "path" queda "desconocido" sin presupuesto —
  nunca se marca en rojo por falta de dato). `scripts/mission_lab.py` gana
  `_budget_check()` (import directo de `app.telemetry`, mismo patrón que
  `mission_report.py`: comparten entorno/BD) con PASS/FAIL impreso por
  escenario y `sys.exit(1)` si alguno se pasa, más `--baseline <json>` que
  compara contra la pasada anterior (llamadas y duración) y deja el archivo
  actualizado — convierte "va lento" en un número comparable entre campañas.
  **Hallazgo real durante la implementación**: `_short_path()` (la variante
  NO-streaming que usa `handle()`, distinta de `_short_path_stream` del chat
  de Electron) se había quedado sin instrumentar en la primera pasada — el
  test `test_camino_corto_registra_path_chat` lo cazó de inmediato. **Segundo
  hallazgo, higiene de tests (patrón LOG-1)**: `mission_events` es una tabla
  GLOBAL que otros archivos de test también escriben sin conocer la fixture de
  éste; limpiar solo al SALIR dejaba que el residuo de un archivo anterior
  (p.ej. un test de orquestador multi-objetivo) se colara en el primer test de
  éste cuando corrían juntos en la misma sesión de pytest — arreglado limpiando
  también al ENTRAR. Tests: `test_telemetry_budget.py` NUEVO (9 — las 4
  bifurcaciones reales con el pipeline real y fakes solo en la frontera del
  LLM/planner, `mission_timeline()` con eventos sintéticos en ambos sentidos
  de `within_budget`, "desconocido" sin romper, contrato aditivo congelado,
  presupuesto "multi" usa el setting per-objective). **Comprobación de
  mutación**: desactivando `_telemetry.record("path", ...)` los 4 tests de
  bifurcación fallan — ejercitan código real. Suite: 9/9 nuevos + 180/180 del
  subconjunto orchestrator/tie/telemetry en verde (un fallo puntual de OTRO
  test por una tarea de fondo en vuelo, no reproducido en repeticiones — mismo
  tipo de flake fire-and-forget ya conocido en el proyecto, no una regresión).
  **Pendiente en Windows**: `mission_lab.py --baseline` contra el backend real
  (aquí solo se probó con eventos sintéticos en SQLite, sin backend HTTP en
  marcha en el sandbox).
- ✅ **S4 EJECUTADA (2026-07-28) — camino caliente rápido + DEADLINES**
  (P5 + NEW-2, doc 34 §10). **El contexto de NEW-2**: no había ni un `timeout`
  ni un `wait_for` en `mel/executor.py`, `tie/intents.py` ni `tie/router.py` —
  el único límite del camino caliente eran los 180 s del provider de Ollama y,
  con cadena de fallback, 180 s **por salto**; sin plazo, el chat podía pasar
  minutos en "analizando" sin escribir una línea (lo que la campaña 00 leyó
  como "cuelgue": no lo era, el event loop seguía vivo — era falta de plazo).
  **(1) Clasificador con modelo/política propios**: `TIE_CLASSIFY_MODEL`
  (default `""`) + `TIE_CLASSIFY_POLICY` (default `"speed"`);
  `router.complete()` gana `model_override`/`policy_override` opcionales
  (default None → request idéntico al de antes para planner/responder, con
  test de no-regresión) e `intents.classify()` los resuelve con el MISMO
  patrón que `toolloop.run` ya usaba (modelo fijo manda; si no, la política
  rápida). El clasificador deja de heredar la política de CALIDAD del usuario
  — corría en el camino caliente de CADA mensaje no trivial. **(2) Ventana
  deslizante del transcript** (`toolloop._prompt_from`, función pura): el
  prompt se acota a la cabecera (objetivo + contexto + catálogo, SIEMPRE — sin
  ellos el modelo pierde qué hace y con qué) + las últimas
  `TIE_TOOL_TRANSCRIPT_WINDOW` (8) interacciones, declarando en una línea
  cuántas se omitieron; el transcript completo sigue íntegro en memoria para
  telemetría. Antes crecía sin límite y se reenviaba entero (4000 chars × 12
  vueltas ≈ 50k). **(3) Deadlines por capa**: `MEL_REQUEST_DEADLINE_S` (120)
  en `_try_one` con razón PROPIA `"timeout"` (no la genérica `"transient"`:
  agotar el plazo es un diagnóstico distinto de un fallo de red) añadida a
  `_BREAKER_REASONS`, así un proveedor colgado se salta durante `OPEN_S` en
  vez de costar el plazo en cada mensaje; `MEL_STREAM_FIRST_CHUNK_S` (60) vía
  `_with_first_chunk_deadline()` — plazo SOLO al primer chunk (cortar una
  respuesta que ya avanza sería peor) y **reusando el `except` que ya
  existía** para registrar/abrir breaker/emitir el error, sin un segundo
  camino de degradación; `TIE_CLASSIFY_DEADLINE_S` (60) degradando por el
  MISMO camino que ya existía para su error. **(4) Latido del stream**
  (`pipeline._heartbeat_until`, `TIE_HEARTBEAT_S`=15, clave i18n
  `status.still_working` ×4 idiomas) en los tres puntos donde un turno podía
  quedarse mudo (classify, acción directa, camino complejo) — observa pero no
  consume: el caller sigue haciendo `await task`, así que una excepción del
  trabajo llega intacta. **NO se tocó el punto 2 del diseño (thrash de
  Ollama)**: el propio diseño lo marcaba "VERIFICAR antes de tocar" y su
  verificación exige `ollama ps` contra el backend real — cambiar una política
  del MEL por una corazonada no es un arreglo. **Hallazgo real (patrón LOG-1,
  tercera vez en este bloque)**: añadir dos kwargs a `router.complete` rompió
  test-doubles de 4 archivos que fijaban la firma vieja; solo UNO reventó su
  test y de forma engañosa (el `TypeError` lo tragaba el fail-safe de
  `classify` y el intent degradaba a charla — parecía "el clasificador no
  detecta el modelo", no "el doble está roto"). Los 6 dobles corregidos con
  `**kw`. Tests: `test_audit_s4_hotpath.py` (NUEVO, 18). **Comprobación de
  mutación**: sin el `wait_for` del MEL el test cuelga y falla; sin la
  propagación de overrides fallan los dos de classify. Regresión: **420
  passed** (subconjunto tie/mel/telemetry/audit/orchestrator). **Pendiente en
  Windows**: el thrash de Ollama (`ollama ps` × 3 mensajes) y el objetivo
  medible contra el `summary` de S3 (classify < 3 s p95, paso de toolloop
  < 4 s p95, ningún turno > 60 s sin evento).
- ✅ **S5 EJECUTADA (2026-07-28) — el resultado de una tool llega ENTERO al
  paso siguiente** (NEW-1, doc 34 §10). **El fallo que cierra** (campaña 00,
  T13): el agente leyó el GDD con `read_docx` → `"ok": true` — y acto seguido
  respondió *"el paso que debía redactar el resumen falló porque el contenido
  completo no llegó a cargarse en la sesión"*. Era LITERALMENTE cierto: **no
  había tubería**. `executor._execute_node` construía el contexto del nodo SOLO
  con memoria del MOS; el `output` de los nodos de los que depende
  (`node.depends_on`) no llegaba por ningún camino. "Lee X y haz Y con ello"
  —el caso de uso central de un asistente— solo funcionaba si ambas cosas caían
  en el MISMO nodo (el toolloop sí ve sus propias observaciones); en cuanto el
  planner las separaba, el segundo trabajaba a ciegas y, como la honestidad SÍ
  funciona, el fallo quedaba invisible detrás de una disculpa educada.
  **(1) La tubería** (`executor._handoff_from_deps`, NEW): los `output` de las
  dependencias en DONE se anteponen al contexto de memoria (el trabajo de ESTA
  misión pesa más que un recuerdo); solo lo que salió BIEN (el resultado de un
  paso fallido no es material de trabajo); recorte por dependencia con
  `TIE_NODE_HANDOFF_CHARS` (12000) y marca `[TRUNCADO: X de Y caracteres]` —
  honestidad deliberada: el paso siguiente debe SABER que le falta contenido
  para pedirlo, en vez de suponer que el documento era así de corto.
  **(2) Observación con cabeza, no con tijera** (`toolloop._observation`, NEW):
  las acciones cuyo VALOR es el contenido (`document.read_*`,
  `filesystem.read_file`, `browser.get_text/get_html`) entregan el campo `text`
  en PLANO con presupuesto propio (`TIE_OBSERVATION_CHARS_CONTENT`, 24000) más
  una línea de metadatos; el resto sigue igual (JSON a 4000). Esto explica el
  "a veces lee más, a veces menos, sin patrón visible": el recorte actuaba
  sobre el JSON YA SERIALIZADO, así que cuánto contenido real sobrevivía
  dependía de la proporción ruido-de-estructura/contenido de cada documento —
  no era aleatorio. **(3) `read_docx` honesto** (`document_tool`): extrae
  además cabeceras y pies (try/except, para que una sección rara no tumbe la
  lectura del cuerpo) y añade `note`+`truncated`, mismo patrón que el `note` de
  `read_pdf`. Antes los omitía EN SILENCIO: en un GDD con portada el título
  vive justo ahí, y bastaba para un "leyó solo una parte" sin que interviniera
  ningún límite de tamaño. **Hallazgo de la comprobación de mutación (y test
  nacido de él)**: al desactivar `_observation` en su punto de llamada, los
  tests de la función pura seguían pasando — la lógica podía ser correcta y
  estar DESCONECTADA; se añadió un test que ejecuta `toolloop.run` REAL sobre
  un archivo REAL de ~20k y mira el prompt de la 2.ª vuelta. Tests:
  `test_audit_s5_handoff.py` (NUEVO, 13). Regresión: **433 passed**
  (420 de S4 + 13). **Pendiente en Windows**: repetir el caso real (agente con
  `document` en un proyecto con carpeta, "lee el GDD y hazme un resumen") y
  confirmar que el paso 2 trabaja sobre el contenido del paso 1.
- 📋 **Verificación en vivo del usuario (2026-07-28) — 3 hallazgos NUEVOS**
  (doc 34 §12.4, ninguno tocado todavía). Confirmados como CORRECTOS: el email
  de S2·S6 (enviado de verdad, contado con su `message_id`, **sin** decir
  "necesito tu confirmación" — el fallo del 25-jul, cerrado), los dos casos de
  fabricación del camino corto (honestos y sin coletilla sobrante — el riesgo
  de ruido del fix no se materializó), el DOCX de S10 dentro de la carpeta del
  proyecto, y el catálogo de S1. De la MISMA misión salen tres cosas nuevas:
  **NEW-4** — un nodo puede quedar "Hecha" contradiciendo su propio texto
  ("No puedo completar este objetivo…" con check verde): `_validate_result`
  pregunta "¿corrió alguna tool con éxito?", no "¿logró el objetivo?", así que
  una prosa de rendición fundamentada por un `list_dir` cuela como resultado
  válido → sesión propia (candidata: reusar `core/grounding.py` para detectar
  la rendición y degradar a FAILED, determinista y sin LLM). **NEW-5** — un
  agente con `browser`/`search` asignadas y el nodo recibió solo
  `document`+`filesystem`; dos causas posibles (el planner no las asignó, o
  `Authority`/el recorte del toolloop las quitó) → medir el `plan` persistido
  antes de tocar; relacionado con S11 pero NO es lo mismo (allí la tool no
  está; aquí sí está y no llega). **NEW-6** — cabecera "Completada" con cuerpo
  "estoy esperando tu confirmación para un paso": el grounding no aplica (ese
  texto lo escribe `_execute_and_respond`, no un LLM); misma familia que la
  ventana de desfase de T5 pero sin autocorregirse → S7·S8.
- ✅ **S7·S8 EJECUTADA (2026-07-28) — gate de permiso de tool visible en
  Misiones + identificador único de misión** (fusión de la antigua S7 +
  S8, doc 34 §10). **1 · `resolve_trace_id`** (`tie/tracer.py`, nuevo): PK
  primero, si no hay fila cae a buscar por `mission_id` (la más reciente).
  Los 4 endpoints de `/api/tie/missions/*` (`get`/`delete`/`cancel`/
  `approve-plan`) lo llaman al entrar — cualquiera de los dos ids funciona
  en cualquiera de los cuatro (antes solo el `trace_id` PK, y el chat
  anuncia el `mission_id`: el mismatch real detrás de lo que NEW-3
  hipotetizaba de otra forma). **2 · `mission_id` en el gate de tool**:
  `toolloop._ask_permission` gana el parámetro (viene de `session_key`,
  que ya era `mission.id`) y lo añade al `action_payload` — aditivo, cero
  regresión. **3 · el panel en Misiones — desviación necesaria sobre el
  diseño**: el diseño original asumía que `GET /api/automation/approvals`
  exponía `action_payload` para filtrar por él en el frontend, pero
  `_approval_out()` lo oculta a propósito desde A1 ("puede llevar detalles
  internos"). Arreglo: `_approval_out()` gana un campo `mission_id` PROPIO
  (la única excepción nombrada del payload crudo, nunca el resto).
  `Missions.tsx` gana una tercera variante de panel de gate (mismo patrón
  visual que el del plan/nodo), resuelta con el `api.resolveApproval`
  genérico de A1 — sin backend nuevo, sin websockets, mismo sondeo de 2s
  ya existente. **4 · el log dice la causa real**: `_ask_permission`
  distingue `permission_service.autonomy_is_full()` ("auto-aprobado por el
  perfil Autónomo, los toggles no aplican") del toggle individual; en
  Ajustes → Permisos, un aviso ÚNICO (no uno por toggle,
  `settings.permisos.togglesInertNote`) cuando el perfil activo es `full`.
  Tests: `test_audit_s7s8_missions.py` (NUEVO, 14 — resolución de id por
  PK/mission_id/inexistente, los 4 endpoints con ambos ids incl.
  no-regresión del `trace_id` real y 404 con id inventado, `approve_plan`
  aislando `resolve_plan` con un fake para probar solo la resolución del
  id, el gate con `mission_id` real y con `None` sin `session_key`, el
  endpoint de aprobaciones exponiendo `mission_id` y sin exponer el resto
  del payload, el log distinguiendo perfil Autónomo de toggle vía
  `caplog`). **Comprobación de mutación** (4 mutaciones independientes,
  restauradas y verificadas byte a byte): neutralizar `resolve_trace_id`
  tumba las 5 pruebas de resolución (incluida `delete_mission`, que cae a
  su `"not_found"` de siempre — la regresión exacta que evita); quitar
  `mission_id` del payload del gate tumba 2; quitar el campo de
  `_approval_out` tumba 2 (`KeyError`); revertir el mensaje del log tumba
  1. Regresión: **479 passed, 6 skipped** (subconjunto tie/mel/telemetry/
  audit/action_intent/orchestrator/automation) + `test_module_boundaries`
  10/10 + `tsc --noEmit` limpio. **NEW-6 (doc 34 §12.4) NO queda cerrado
  por esta sesión** pese a vivir en su bucket: su causa es el desfase
  `state`/`outcome` de `_execute_and_respond` (misma familia que la
  ventana de T5), ajena a la resolución de ids y a la visibilidad del
  gate — sigue pendiente, sesión propia. **Pendiente en Windows**:
  aprobar/rechazar un gate de permiso de tool desde `/missions` sin volver
  al Chat; el aviso de "Autónomo" visible en Ajustes → Permisos.

---

- ✅ **S9 EJECUTADA (2026-07-28) — lock en el lanzamiento del navegador +
  autocuración de pestañas muertas** (reabre F-1, doc 24 §22): causa raíz ya
  localizada por lectura de código en el diseño de esta sesión —
  `_ensure_browser()` no tenía ningún lock, así que dos misiones lanzadas
  con segundos de diferencia (reproducido en vivo en la campaña 01,
  T06-R-D5-browser-concurrente) pasaban AMBAS el guard "¿ya está lanzado?" y
  arrancaban DOS `launch_persistent_context()` sobre el MISMO perfil —
  Chrome bloquea el segundo proceso, y las dos misiones se quedan con una
  referencia rota (`TargetClosedError`). **`tools/browser_tool.py`**: lock
  de módulo `_launch_lock = asyncio.Lock()`, con **double-checked locking**
  en `_ensure_browser()` (guard rápido SIN lock si ya está lanzado — cero
  coste en el camino caliente — y, si no, entra al lock con el MISMO guard
  REPETIDO dentro, para que una corrutina que esperó no relance nada) y en
  `_get_session()` (misma protección para la creación de un `BrowserContext`
  en modo respaldo — un único lock cubre las dos carreras, porque no
  compiten entre sí). **Pestaña muerta se autocura**: `_get_page()` ahora
  comprueba `page.is_closed()` (o trata una EXCEPCIÓN de esa llamada como
  "muerta" también — un `TargetClosedError` residual cuenta igual que el
  caso limpio); si está muerta, se descarta de `sess.pages` y se crea una
  pestaña nueva en vez de devolver un handle que reventaría en la siguiente
  llamada real de Playwright. **Hallazgo real de la regresión (LOG-1, otra
  vez)**: el `_FakePage` de `test_audit_s3_browser.py` (S3) no tenía
  `is_closed()` — con el cambio, CUALQUIER llamada a esa página fake lanzaba
  `AttributeError`, mi propio `except Exception: dead = True` la trataba
  como "siempre muerta", y `_get_page` recreaba una pestaña en CADA llamada,
  rompiendo `test_f1_la_misma_mision_reutiliza_su_pestana`. Arreglado
  añadiendo `is_closed()` al doble (Playwright real siempre lo tiene) — el
  fallo era del doble, no de la lógica nueva. **Nota de entorno de test, no
  de producción**: un `asyncio.Lock()` de módulo se vincula al event loop en
  el que se usa por primera vez; pytest-anyio crea un loop nuevo por test,
  así que el fixture de los tests nuevos RECREA `_launch_lock` en cada test
  (en producción es irrelevante — un único loop de por vida del proceso).
  Tests: `test_audit_s9_browser_lock.py` NUEVO (7 — la regresión exacta del
  hallazgo con 5 corrutinas concurrentes acabando en 1 solo lanzamiento,
  no-regresión de llamada ya-lanzada, la misma carrera en pequeño para
  `_get_session` con el mismo sid, no-regresión de sids distintos con
  contextos propios —F-1 intacto—, pestaña muerta se recrea, pestaña viva se
  reutiliza sin cambios, `is_closed()` que LANZA se trata como muerta).
  **Comprobación de mutación** (3 mutaciones independientes, restauradas y
  verificadas byte a byte): quitar el lock de `_ensure_browser` tumba el
  test de concurrencia; quitar el de `_get_session` tumba el suyo; quitar el
  chequeo de página muerta tumba los 2 de `_get_page`. Regresión:
  `test_audit_s3_browser.py`+`test_audit_s9_browser_lock.py` 17/17,
  **458 passed, 6 skipped** en el subconjunto browser/tie/mel/audit/
  orchestrator/automation (los fallos de `test_new_tools.py::test_desktop_*`
  son del sandbox, sin `pyautogui`/display, ajenos a este cambio).
  `test_module_boundaries` 10/10. **Pendiente en Windows**: repetir el
  experimento exacto de la campaña 01 — dos misiones con `browser` lanzadas
  con <20s de diferencia por la UI — y confirmar que ninguna colisiona (no
  reproducible contra Chrome/Chromium real en este sandbox, sin navegador
  instalado).

- ✅ **NEW-7 CERRADO (2026-07-28) — fabricación SIN verbo delator en el camino
  corto** (doc 34 §12.5, hallazgo de la verificación en vivo del usuario): el
  chat respondió a "Lista los archivos de la carpeta Aithera, dime cuántos .py
  hay en backend/app/tie, y léeme las primeras líneas de pipeline.py" con un
  listado inventado, un recuento falso ("Total de archivos .py: 7") y un bloque
  de código con imports que NO existen en el archivo real — sin ninguna nota de
  honestidad. **Dos causas independientes, dos capas.** (1) **La raíz**
  (`tie/action_intent.py` + `tie/intents.py`): `action_intent()` (25-jul)
  rescataba del fail-safe `conversational` las órdenes sobre la PROPIA Aithera,
  pero una petición de leer archivos/web/correo seguía degradando a charla — y
  el camino corto NO tiene herramientas, así que ahí el modelo solo puede
  inventar (con `llama3` el JSON del clasificador falla ~40% de las veces,
  medido en la campaña 01). Nace `world_intent()`, su hermano: detector
  determinista (0 LLM) de "esto pide leer el mundo", con los verbos en **dos
  niveles** para no arrastrar charla al bucle de tools — un verbo FUERTE ("lee",
  "lista", "abre", "navega") basta con un objeto del mundo; uno DÉBIL y genérico
  ("dime", "muestra", "cuántos") exige además una RUTA o EXTENSIÓN concreta.
  Esa distinción separa "dime cuántos .py hay en backend/app/tie" (sí) de "dime
  qué archivos suele tener un proyecto FastAPI" (no) — el falso positivo real
  que motivó los dos niveles. Se consulta en los CUATRO puntos donde el intent
  podía degradar a charla: los 3 fallos del clasificador (error, sin JSON,
  excepción) y —nuevo— el **suelo de confianza** (existe para no actuar sobre
  una corazonada, pero "charla sin herramientas" tampoco es un default seguro
  cuando el usuario ha nombrado un archivo concreto). `action_intent()` mantiene
  la prioridad: una orden sobre Aithera es más específica. (2) **El respaldo**
  (`core/grounding.py`): S2·S6 anclaba VERBOS ("he leído"), y este texto no usa
  ninguno — presenta los datos y ya está. `presents_unverifiable_evidence()` no
  mira verbos sino la FORMA: contenido de un archivo concreto (bloque de código
  + ruta/nombre real), listado de directorio (3+ líneas con extensión),
  recuento de ficheros, o bibliografía web (2+ enlaces citados). Cuando dispara,
  la nota deja de ser la coletilla suave y pasa a un **aviso fuerte**
  (`grounding.fabricated_note`, 4 idiomas). Nace `note_for()` como punto ÚNICO
  de decisión, para que la variante con streaming (`runtime.stream_task`, que
  solo puede añadir al final) y la que no (`with_honesty_note`) no diverjan.
  **El riesgo atendido es el ruido**: 14 de los 41 tests son negativos — un
  ejemplo de código pedido no dispara, ni una mención suelta a `main.py`, ni un
  enlace único, ni la negativa honesta que el propio usuario vio funcionar bien
  en la misma pasada. **Hallazgo de la regresión**:
  `test_classify_json_basura_fallback` falló porque usaba "resúmeme el informe
  del proyecto Aithera" para probar el fail-safe — ese input ahora se rescata a
  un intent CON herramientas, que es lo correcto (resumir un informe nunca leído
  ERA el bug); el test afirmaba el contrato viejo y se actualizó a un mensaje
  que de verdad es charla, en vez de debilitar el código. Tests:
  `test_audit_new7_fabricacion.py` NUEVO (41). **Comprobación de mutación** (2
  mutaciones, restauradas y verificadas byte a byte): desactivar el rescate del
  intent tumba los 2 tests de clasificación; desactivar el detector de evidencia
  tumba los 2 de la nota. Regresión: **402 passed, 4 skipped** en el subconjunto
  tie/audit/intent/grounding/orchestrator/chat/module_boundaries. **Pendiente en
  Windows**: repetir el mensaje EXACTO y confirmar que el log ya no dice
  "fallback conversational" y que la respuesta trae el listado REAL o falla
  honestamente, nunca uno inventado.

- ✅ **S9b EJECUTADA (2026-07-28) — un navegador MUERTO se relanza** (hallazgo
  de la verificación en vivo de S9 por el usuario): tras S9, tres misiones
  seguidas con navegador seguían muriendo con `TargetClosedError` ("El
  navegador (BrowserContext) está cerrado en esta sesión"). S9 arregló la
  CARRERA entre misiones concurrentes; debajo quedaba algo peor y que ni
  siquiera necesita concurrencia: **`_ensure_browser()` comprobaba `is not
  None`, no si el navegador seguía VIVO**. En cuanto `_persistent_context`
  moría por una causa externa (el usuario cierra esa ventana de Chrome, el
  proceso se cae), la global apuntaba al cadáver PARA SIEMPRE — el guard decía
  "ya está lanzado", no se relanzaba nunca, y ninguna misión posterior podía
  navegar hasta reiniciar el backend entero. **Dos mecanismos, porque uno solo
  no basta**: (1) chequeo barato ANTES (`_alive()` + `_browser_ready()`, que
  sustituye al `is not None` del guard) descarta el cadáver evidente sin coste,
  con `_reset_browser_globals()` limpiando también `_sessions` (sus contextos
  apuntan al muerto) y `_get_session` descartando una sesión que ya no apunta
  al contexto vigente; (2) reintento en el PUNTO DE USO (`_get_page`), porque
  el estado real de un proceso externo solo se conoce al usarlo — entre el
  chequeo y la llamada puede morir. UN solo reintento: si el navegador nuevo
  también falla, el error sube y la misión falla honestamente, nunca un bucle.
  `_looks_closed()` decide por TEXTO y no por tipo (Playwright lanza
  `TargetClosedError` pero también `Error` a secas con el mismo mensaje), y
  distingue un fallo de red de un navegador muerto — confundirlos relanzaría
  Chrome cerrando las pestañas del usuario por un timeout cualquiera.
  `browser_tool.py` gana además su `logger` (no tenía ninguno). **Dos hallazgos
  del propio proceso**: (a) la primera versión del test de reintento NO lo
  ejercitaba — el chequeo previo ya curaba el caso antes de llegar ahí, y la
  mutación lo destapó (el doble ahora MIENTE: `is_connected()` dice True y
  `new_page()` revienta, que es el caso real que ningún chequeo previo puede
  cubrir); (b) LOG-1 por tercera vez en este bloque: el `_FakeContext` de
  `test_audit_s9_browser_lock.py` no tenía `pages` ni `is_connected` (Playwright
  real SIEMPRE los tiene), así que `_alive()` lo daba por muerto y
  `_ensure_browser` relanzaba en cada llamada — el doble estaba incompleto, no
  la lógica nueva. Tests: `test_audit_s9b_browser_muerto.py` NUEVO (14 — los dos
  detectores con sus casos negativos, el guard que fallaba, relanzar tras morir,
  no relanzar estando vivo, sesiones viejas descartadas, el reintento real, sin
  bucle si el relanzamiento también falla, y que un error de red NO dispara
  relanzamiento). **Comprobación de mutación** (2, restauradas y verificadas
  byte a byte): volver el guard a `is not None` tumba 3; quitar el reintento
  tumba 1. Regresión: **436 passed, 6 skipped** en el subconjunto browser/tie/
  mel/audit/intent/grounding/orchestrator/automation. **Pendiente en Windows**:
  repetir las 3 misiones de navegador que fallaron y confirmar que ahora
  navegan; y cerrar a mano la ventana de Chrome de Aithera a mitad de sesión
  para ver que la siguiente misión la relanza sola.

- ✅ **S9c EJECUTADA (2026-07-28) — bucle estéril + texto externo sucio** (las
  dos cosas que quedaron observadas al cerrar S9b; ninguna es del navegador).
  **(1) Repetición estéril** (`tie/toolloop.py`): con el navegador roto, el
  bucle gastó sus 12 vueltas pidiendo `browser.open_url` una y otra vez con
  EXACTAMENTE el mismo error — 12 llamadas al LLM para una conclusión que ya
  estaba clara en la segunda. Contador por **firma de fallo** `(tool_id, action,
  error normalizado y recortado a 120 chars)`, de modo que dos
  `TargetClosedError` con distinta URL son el MISMO problema (y dos timeouts con
  distinto número de ms, también). **Dos escalones**: al 2.º fallo idéntico se
  AVISA al modelo en el transcript ("no lo repitas: otra vía, u explica el
  límite"), al 3.º se abandona devolviendo el error REAL como causa. No se corta
  a la primera a propósito — un reintento tras un fallo transitorio es legítimo
  y tiene su test de no-regresión. El mismo contador cubre las DENEGACIONES
  repetidas (insistir en una tool inexistente), que era la otra forma
  documentada de girar en vacío (#209). Ambos dejan evento de telemetría
  (`repeated_failure`/`repeated_denial`). **(2) Texto externo sucio**
  (`app/core/sanitize.py` NUEVO + `tools/search_tool.py`): una búsqueda de
  vídeos trajo resultados REALES pero con los enlaces rotos —
  `…iy35dCK0iaI￼Ritmos`—; ese `￼` (U+FFFC) es invisible en el JSON y en el log,
  y el modelo lo pega dentro del enlace markdown. Viene de los `description` del
  proveedor. Funciones puras en la capa compartida (el problema no es de la
  búsqueda: es de cualquier texto externo — web, documento, email):
  `strip_invisible()` quita invisibles conocidos + categorías `Cc`/`Cf`
  conservando `\n\r\t`; **`clean_url()` CORTA por el invisible en vez de
  quitarlo** — dentro de una URL no es ruido, es la FRONTERA (limpiar produce
  `…iaIRitmos`, un enlace igual de roto pero más difícil de ver; me equivoqué en
  la primera versión y lo cazó el test); `clean_external()` recorre dicts/listas
  respetando números/booleanos/None. Aplicado en los DOS normalizadores de
  `search_tool` (Brave y SerpAPI), en la frontera, una vez. **El riesgo atendido
  es pasarse**: 4 de los 21 tests comprueban que acentos, emojis, CJK y saltos
  de línea salen intactos. Tests: `test_audit_s9c_bucle_y_texto.py` NUEVO (21).
  **Comprobación de mutación** (3): quitar el corte por fallo repetido tumba su
  test; hacer que `clean_url` limpie en vez de cortar tumba 2; la tercera
  —`search_tool` deja de sanear— **NO se detectó al primer intento** (los tests
  probaban la función pura pero nadie comprobaba que la tool la USARA: lógica
  correcta y desconectada, mismo hallazgo que en S9b), así que se añadió un test
  que ejercita `_search_brave` REAL contra una respuesta HTTP sucia. Regresión:
  **500 passed, 7 skipped** (el único fallo, `test_document_tool::
  test_path_fuera_de_home_rechazado`, es del sandbox — ruta `C:\Windows` sobre
  Linux — ajeno a estos cambios). **Pendiente en Windows**: repetir una búsqueda
  de vídeos y comprobar que los enlaces del chat abren de verdad.

- ✅ **NEW-7b EJECUTADA (2026-07-28) — el verbo de guardar en el mismo mensaje
  ya no se pierde** (verificación en vivo, hallazgo distinto de NEW-7 §12.5
  aunque de la misma familia): *"Investiga qué es FastAPI y guárdame un
  resumen de tres líneas"* investigó bien (`world_intent()` de NEW-7 detectó
  la lectura) pero al llegar al paso de guardar respondió que no tenía
  herramienta de escritura disponible — la orden de guardar iba en el MISMO
  mensaje y se perdía porque `world_intent()` solo reconoce verbos de LECTURA
  ("lee", "lista", "busca"), nunca de ESCRITURA ("guarda", "anota"): la tool
  ni siquiera se pedía. **`app/tie/action_intent.py::_wants_to_persist(text)`**
  (determinista, sin LLM): exige un verbo de guardar Y descarta los modismos
  que no hablan de persistir un dato ("guarda silencio", "guarda las
  distancias", "guarda la calma/compostura/cama"). `ensure_persistence_tool
  (intent, text)` añade `filesystem` a `requires_tools` cuando el intent YA
  implica hacer algo y el mensaje pide guardar, sin pisar lo que ya hubiera.
  **Aplicado universalmente**: `app/tie/intents.py::classify()` se parte en un
  wrapper delgado que llama al cuerpo original (renombrado `_classify_core()`)
  y pasa CUALQUIER resultado por `ensure_persistence_tool()` — cubre los tres
  caminos que producen un intent (LLM con éxito, rescate determinista, fallback
  conversational) con un solo punto de aplicación, porque el LLM también puede
  olvidar `filesystem` en un intent por lo demás correcto. Tests:
  `test_audit_new7b_persistencia.py` NUEVO (25 — detector puro en positivo/
  negativo, integración con `Intent` sin duplicar ni tocar conversational, y 3
  end-to-end contra `classify()` real: el mensaje EXACTO del fallo, un LLM que
  acierta pero olvida `filesystem` mockeando `app.mel.complete`, y la
  no-regresión de que lectura pura no gana `filesystem` porque sí).
  **Comprobación de mutación** (3, restauradas y verificadas byte a byte):
  desactivar la llamada del wrapper tumba el end-to-end del mensaje real;
  forzar el guardia de modismos a `True` tumba los 5 negativos; forzar la
  detección de verbo a `False` tumba los 7 positivos + el de integración.
  Regresión: **117 tests en verde** (`test_audit_new7_fabricacion.py` 41,
  `test_tie_contracts.py` 17, `test_tie_handle.py` 25, `test_tie_planner.py`+
  `test_audit_new7b_persistencia.py` 34), sin ningún roto por el split
  `classify()`/`_classify_core()`. **Pendiente en Windows**: repetir el
  mensaje exacto y confirmar que Aithera guarda el resumen (o pregunta la
  ruta) en vez de decir que no tiene herramienta disponible.

- ✅ **NEW-4 EJECUTADA (2026-07-28) — un nodo con rendición explícita ya no
  queda "Hecha"** (verificación en vivo, doc 34 §12.4/§12.9): un paso de una
  misión real respondió literalmente *"No puedo completar este objetivo: las
  herramientas disponibles en este paso NO incluyen ninguna de búsqueda web ni
  navegador"* y la UI lo mostró con el check verde. Causa: `_validate_result`
  (T3, `tie/executor.py`) pregunta "¿corrió una tool con éxito y hay salida
  con forma?", nunca "¿el nodo consiguió su objetivo?" — un `list_dir` real le
  dio forma a la salida, así que su prosa de rendición coló como resultado
  válido. **`core/grounding.py` gana `is_surrender(text)`**: detecta una
  rendición EXPLÍCITA y DECLARATIVA ("no puedo completar este objetivo", "no
  dispongo de las herramientas necesarias", "unable to complete this"…) solo
  en los primeros 200 caracteres — mirar solo la cabecera es lo que evita
  marcar un resultado PARCIAL honesto ("hice X, no pude con Y, pero el resto
  está completo") como si fuera rendición total. `_validate_result` gana un
  tercer chequeo, tan determinista y barato como los dos que ya tenía: si
  `is_surrender(result.output)`, el nodo se degrada a FAILED con
  `method="grounding"` en vez de DONE — el recovery de T3 (dependientes
  transitivos → SKIPPED) hace el resto sin tocar nada más. Tests:
  `test_audit_new4_rendicion.py` NUEVO (18 — 8 rendiciones positivas ES/EN
  incluido el mensaje real, 5 negativos con resultados honestos/parciales, 1
  caso de rendición mencionada al final de un texto largo que NO dispara, y 3
  de integración con el executor real vía runtime fake). **Comprobación de
  mutación** (2, restauradas y verificadas byte a byte): quitar el chequeo de
  `_validate_result` tumba el test de integración; forzar `is_surrender` a
  `False` tumba los 8 positivos + el de integración. Regresión: **128 tests en
  verde** (`test_audit_new4_rendicion` 18, `test_tie_executor` 16,
  `test_audit_s2s6_grounding` 34, `test_module_boundaries`+
  `test_audit_new7_fabricacion`+`test_tie_planner` 60), sin roturas por el
  nuevo import de `app.core.grounding` en `tie/executor.py` (mismo patrón que
  `tie/responder.py`). **Pendiente en Windows**: repetir el escenario —una
  misión con un paso al que le falten herramientas necesarias, forzando una
  respuesta de rendición— y confirmar que el nodo queda en rojo (FAILED), no
  en verde.

- ✅ **NEW-6 EJECUTADA (2026-07-28) — "Completada" con texto de espera de
  aprobación** (verificación en vivo, doc 34 §12.4/§12.10): una misión
  mostraba cabecera "Completada" con el cuerpo *"He empezado y estoy
  esperando tu confirmación para un paso"* — la plantilla `pipeline.
  waiting_confirmation`. Causa: `_finalize()` (T3) solo escribe `mission.
  state` en la traza, NUNCA `outcome`. Cuando un nodo abre su propio gate,
  `pipeline._execute_and_respond` escribe el placeholder de espera; al
  resolverse el gate, la reanudación es EVENT-DRIVEN y vive en `executor.py`
  (`_apply_gate_verdict`/`_apply_checkpoint_verdict`) y volvía a llamar
  `run()` SIN pasar por `pipeline._execute_and_respond` — nadie volvía a
  sintetizar el `outcome`: el estado avanzaba a "done" pero el cuerpo se
  quedaba con el placeholder para siempre. **`executor.finish_and_record
  (graph, mission, trace_id)`** (NUEVO): punto ÚNICO que decide el outcome
  final tras CUALQUIER `run()` — si `mission.state == "waiting"` escribe el
  placeholder, si no llama a `responder.build()` y emite el evento
  `mission.*` correspondiente. Los TRES callers pasan a compartir la MISMA
  función: `_apply_gate_verdict`/`_apply_checkpoint_verdict` (antes ninguno
  sintetizaba nada) la ganan tras su `run()`; `pipeline._execute_and_respond`
  se reescribe para DELEGAR en ella en vez de llevar su propia copia — la
  duplicación era la grieta por la que se coló el bug. Dirección de
  dependencia respetada (`pipeline.py` → `executor.py`, nunca al revés — el
  helper vive en `executor.py` para evitar un ciclo). Tests:
  `test_audit_new6_outcome_fresco.py` NUEVO (6 — las 2 ramas puras de
  `finish_and_record`, la regresión EXACTA con gate de nodo aprobado y
  rechazado, el mismo caso con un CHECKPOINT, no-regresión sin gates); se
  mockea `app.mel.complete` porque sin mock `router.complete()` tarda ~1.7s
  en agotar la cadena de proveedores en el sandbox. **Comprobación de
  mutación** (3, restauradas y verificadas byte a byte): quitar la llamada en
  `_apply_gate_verdict` tumba 2 tests; quitarla en `_apply_checkpoint_verdict`
  tumba 1; vaciar `finish_and_record()` por dentro tumba 3. Regresión: **84
  tests en verde** (`test_audit_new6_outcome_fresco` 6 + `test_tie_executor`
  16 + `test_audit_new4_rendicion` 18 + `test_tie_handle`+`test_tie_e2e` 28 +
  `test_module_boundaries`+`test_tie_perf` 16). **Pendiente en Windows**:
  forzar una misión con un plan de 2+ pasos donde el segundo pida permiso,
  aprobarlo desde `/missions`, y confirmar que la cabecera pasa a
  "Completada" CON un resumen real — nunca con el texto de espera.

- 🔎 **NEW-5 DIAGNOSTICADA, NO CERRADA (2026-07-29) — tools del agente que no
  llegan al nodo** (doc 34 §12.4): a diferencia de las demás sesiones de este
  bloque, el propio doc 34 exige medir contra la BD real ANTES de tocar
  código ("Hay que medirlo antes de tocar"), y este entorno no tiene acceso al
  Postgres real del usuario — así que esta sesión es solo trazado de código +
  una herramienta de medición, sin fix todavía. **Trazado completo**:
  `agent.allowed_tools` (BD) → `agent_manager._delegate_to_tie()` (pasa la
  lista intacta) → `Authority.allowed_tools` → `planner._generate_graph()`,
  que filtra en DOS puntos — el catálogo OFRECIDO al LLM ya viene recortado a
  `permitidas`, y tras el JSON del LLM un recorte determinista
  `n.tools = [t for t in n.tools if t in permitidas]` que SOLO puede QUITAR
  una tool no permitida, nunca una que sí lo esté — y `graph.validate()`
  (chequeo "tools ⊆ catálogo") tampoco trunca nada, RECHAZA el plan entero si
  un nodo referencia una tool fuera de catálogo. **No se encontró ningún
  camino de código que quite en silencio una tool que SÍ estuviera en
  `allowed_tools`** — esto debilita la hipótesis (b) del doc ("Authority/el
  recorte del toolloop las quitó") y refuerza la (a) ("el planner no se las
  asignó al nodo pese a tenerlas en el catálogo" — calidad de planificación,
  no bug de seguridad), salvo que el propio agente no tuviera esas tools en
  BD en el momento real de la prueba (discrepancia de datos, no de código).
  **`backend/scripts/diagnose_new5.py`** (NUEVO, read-only, no toca nada):
  para las últimas N misiones con `browser`/`search` en `authority.
  allowed_tools`, imprime por nodo lo PERMITIDO vs lo ASIGNADO por el planner
  (`node.tools`, persistido en `orchestrator_traces.plan`) vs lo REALMENTE
  LLAMADO (`node.tool_calls`) — la medición exacta que doc 34 pide, sin
  necesitar tocar el backend en marcha. Verificado en el sandbox contra una
  BD SQLite de prueba construida a mano con el patrón exacto reportado:
  reproduce el aviso `⚠ SIN browser/search asignadas` cuando
  `authority.allowed_tools` las tenía pero el nodo no. **Pendiente en
  Windows**: correr `cd backend && python scripts/diagnose_new5.py` (o con
  `--limit 40` si la misión de la prueba quedó más atrás) y, con el resultado
  real, decidir si el fix es de prompting del planner (más tools por defecto
  para pasos de "recolectar información", o instrucción más explícita) o si
  aparece el patrón (c) no contemplado en el doc original (el nodo SÍ tenía
  las tools asignadas pero el toolloop nunca las llamó — un problema
  distinto, de juicio del modelo en ejecución, no de planificación).

- ✅ **S11 EJECUTADA (2026-07-29) — gate de concesión de tool ausente +
  advertencia de incompletitud** (doc 34 §S11, último punto del plan S1-S11):
  el caso Cordyceps/NEW-5 desde el otro lado — cuando el modelo pide una tool
  REAL que no está en la whitelist del nodo (pero el agente SÍ la tiene
  permitida vía `Authority.allowed_tools`), el bucle ya no la deniega en
  silencio: abre un gate de CONCESIÓN (`tool.grant.<id>`, una sola vez por
  tool y por ejecución del bucle, `asked_grants`) preguntando "¿te la doy, o
  sigues sin ella?" — el mismo tipo de pausa que ya existía para acciones
  sensibles, extendido a capacidades ausentes. **`toolloop._ask_grant`**
  (NUEVO) + **`_wait_gate`** (extraído de `_ask_permission`, que pasa a
  delegar en él — un solo ciclo de sondeo/expiración para los dos tipos de
  gate). Concedida → se añade a `allowed_tools`, se recalculan `catalog`/
  `by_pair`, y el bucle CONTINÚA (conceder no ejecuta nada por su cuenta: el
  modelo re-pide la misma tool en la vuelta siguiente, ya disponible).
  Rechazada → `ToolLoopResult.limitations` (campo nuevo, append-only) →
  `AgentResult.limitations` → `node.result["limitations"]` (executor) →
  `responder._with_limitations_note()` (NUEVO: advertencia determinista final,
  nunca la escribe el LLM, aplicada una sola vez en `build()` tras
  `_synthesize()` — cubre tanto la síntesis real como su propio respaldo
  `_template_success`). Clave i18n `responder.limitations_note` en los 4
  idiomas. **Desviación de seguridad necesaria, no estaba en el diseño
  original**: el gate SOLO se ofrece si la tool está dentro de `Authority.
  allowed_tools` (lo que el AGENTE tiene permitido, R4) — no basta con que
  exista en el ToolManager; sin este límite, un "sí" del usuario habría
  abierto una vía para saltarse la frontera de autoridad de la misión.
  **Hallazgo real de la regresión** (no del diseño): un test YA EXISTENTE sin
  `authority` ni `approval_gate` empezó a fallar — sin canal de aprobación
  disponible el código abría igualmente un gate "fantasma" que nadie podía
  resolver; corregido exigiendo `approval_gate is not None` en `grantable`
  (mismo comportamiento que antes de S11 cuando no hay a quién preguntar).
  Tests: `tests/test_audit_s11_grant.py` (NUEVO, 8 — gate se abre con una tool
  real fuera de whitelist, se pregunta UNA sola vez pese a 3 reintentos,
  aprobado ejecuta con éxito, rechazado deja `limitations` + advertencia en la
  respuesta final, tool inventada NO abre gate, acción inválida de una tool
  YA permitida tampoco abre gate, **fuera de `Authority.allowed_tools` NO es
  concedible** —la frontera de seguridad añadida—, perfil Autónomo auto-concede
  con rastro real en `approvals`). **Comprobación de mutación** (4,
  restauradas y verificadas byte a byte): quitar el bound de `Authority`
  tumba el test de frontera; quitar `asked_grants` tumba el de "una sola
  vez"; quitar `approval_gate is not None` tumba la regresión real de
  `test_tie_toolloop.py`; desactivar `_with_limitations_note` tumba el test
  del responder. Regresión: ~370 tests en verde en el sandbox (toolloop,
  executor, mel, automation, orchestrator, module_boundaries, product_
  contracts 9/13 en aislamiento — los 4 restantes exigen un
  `approval_wait_s=120` real, límite ya documentado desde S1), sin roturas
  nuevas salvo la ya corregida. **Con esto se cierra el plan S1-S11 completo
  salvo NEW-5** (pendiente de medición contra la BD real). **Pendiente en
  Windows**: repetir el caso EXACTO de Cordyceps (agente con `document` NO
  asignado a un paso, proyecto con carpeta, pedirle que lea un archivo local
  real) y confirmar que Aithera PARA a preguntar en vez de seguir en
  silencio; si se rechaza, que la respuesta final lleve la advertencia de
  incompletitud.

---

*Última actualización: 2026-07-29 — **S11 ejecutada (§26)**: gate de
concesión cuando una tool real permitida al agente no llegó al nodo — el
bucle pregunta "¿te la doy, o sigues sin ella?" en vez de denegar en
silencio; rechazada, la respuesta final avisa siempre de la limitación
(`responder._with_limitations_note`, i18n). Acotado por `Authority.
allowed_tools` para no abrir un agujero de seguridad. 8 tests nuevos + 4
mutaciones confirmadas + ~370 de regresión en verde (sandbox). **Cierra el
plan S1-S11 completo salvo NEW-5**, que sigue pendiente de medir contra la
BD real.*

*Anterior: 2026-07-29 — **NEW-5 diagnosticada, NO cerrada (§26)**:
trazado estático completo de la cadena `agent.allowed_tools`→`Authority`→
`planner`→`graph.validate()` sin encontrar ningún camino de código que quite
en silencio una tool permitida — debilita la hipótesis "recorte de
seguridad" y refuerza "el planner no la asignó pese a tenerla disponible".
Sin acceso a la BD Postgres real desde este entorno (el propio doc 34 exige
medir antes de tocar), se creó `backend/scripts/diagnose_new5.py` (read-only,
verificado contra SQLite de prueba) para que el usuario mida la misión real
y decida el fix. Ningún cambio de comportamiento todavía — la única sesión
de este bloque que se detiene antes del fix por falta de evidencia.*

*Anterior: 2026-07-28 — **NEW-6 ejecutada (§26)**: la reanudación
de un gate de nodo o checkpoint ya sintetiza un outcome fresco en vez de
dejar el placeholder de espera para siempre — `executor.finish_and_record()`,
punto único compartido por los 3 callers que antes tenían lógica duplicada (o
ninguna). 6 tests nuevos + 84 de regresión en verde (sandbox), 3 mutaciones
confirmadas. **Con esto quedan cerrados 7 de los 8 hallazgos de la
verificación en vivo del 28-jul salvo NEW-5**, que sigue pendiente de medir
contra la BD real.*

*Anterior: 2026-07-28 — **NEW-4 ejecutada (§26)**: un nodo con
rendición explícita en su propia respuesta ya no queda "Hecha" —
`core/grounding.is_surrender()` (cabecera del texto, conservador ante
resultados parciales honestos) + tercer chequeo en `_validate_result`. 18
tests nuevos + 128 de regresión en verde (sandbox), 2 mutaciones confirmadas.*

*Anterior: 2026-07-28 — **NEW-7b ejecutada (§26)**: el verbo de
guardar/anotar en el mismo mensaje que pedía investigar ya no se pierde —
`ensure_persistence_tool()` aplicado universalmente en `classify()`. 25 tests
nuevos + 117 de regresión en verde (sandbox), 3 mutaciones confirmadas.*

*Anterior: 2026-07-28 — **S9c ejecutada (§26)**: el toolloop deja
de insistir en lo que ya falló idéntico (contador por firma de fallo, aviso al
2.º y abandono al 3.º, también para denegaciones repetidas) y el texto que
entra de fuera se sanea en la frontera (`app/core/sanitize.py`, con URLs que se
CORTAN por el invisible en vez de limpiarse). 21 tests nuevos + 500 de
regresión en verde (sandbox), 3 mutaciones confirmadas.*

*Anterior: 2026-07-28 — **S9b ejecutada (§26)**: un navegador
muerto se relanza en vez de envenenar el proceso — el guard comprobaba
`is not None` en vez de vivacidad, así que un Chrome cerrado por fuera
condenaba TODAS las misiones posteriores hasta reiniciar el backend. Chequeo
de vivacidad + reintento en el punto de uso. 14 tests nuevos + 436 de
regresión en verde (sandbox), 2 mutaciones confirmadas.*

*Anterior: 2026-07-28 — **NEW-7 cerrado (§26)**: la fabricación
del camino corto SIN verbo delator (listados, contenido de archivos, cifras)
— dos capas: `world_intent()` evita que una petición de leer el mundo degrade
a charla sin herramientas cuando el clasificador falla, y
`presents_unverifiable_evidence()` marca con un aviso fuerte lo que aun así
se cuele. 41 tests nuevos + 402 de regresión en verde (sandbox), 2 mutaciones
confirmadas. Pendiente en Windows: repetir el mensaje exacto del fallo.*

*Anterior: 2026-07-28 — **S9 ejecutada (§26)**: lock de
lanzamiento del navegador (`_launch_lock`, double-checked locking en
`_ensure_browser`/`_get_session`) + autocuración de pestañas muertas en
`_get_page` — cierra la fuga de sesión entre misiones concurrentes que la
campaña 01 reprodujo en vivo (F-1 reabierto, doc 24 §22). 7 tests nuevos +
458 de regresión en verde (sandbox), 3 mutaciones confirmadas. Pendiente en
Windows: repetir el experimento con dos misiones reales de navegador.*

*Anterior: 2026-07-28 — **S7·S8 ejecutada (§26)**: gate de
permiso de tool visible en Misiones + identificador único de misión.
`tracer.resolve_trace_id` hace que cualquiera de los dos ids (trace_id PK o
mission_id, lo que anuncia el chat) funcione en los 4 endpoints de
`/api/tie/missions/*`; el gate de tool (`tie_tool_permission`) lleva
`mission_id` en su payload y `Missions.tsx` gana un tercer panel para
resolverlo sin volver al Chat (con una desviación necesaria: `_approval_out`
solo expone ESE campo del payload crudo, nunca el resto, porque A1 lo oculta
a propósito); el log de una auto-aprobación ya distingue "perfil Autónomo"
de un toggle individual, con aviso a juego en Ajustes → Permisos. 14 tests
nuevos + 479 de regresión en verde (sandbox), 4 mutaciones confirmadas.
NEW-6 (el desfase estado/texto de una misión) vivía en el bucket de esta
sesión pero tiene causa distinta — sigue pendiente, sesión propia. Siguiente:
**S9** (fuga de sesión de navegador entre misiones concurrentes).*

*Anterior: 2026-07-28 — **S5 ejecutada (§26)**: la TUBERÍA entre
pasos. El resultado de un nodo llega íntegro al siguiente (`_handoff_from_deps`,
con recorte honesto que declara cuánto falta); la observación de una lectura se
entrega en texto plano con presupuesto propio en vez de JSON descabezado a 4000
(eso explicaba el "a veces lee más, a veces menos"); y `read_docx` extrae
cabeceras/pies y avisa de lo que NO lee. 13 tests nuevos + 433 de regresión en
verde (sandbox). **Además, verificación en vivo del usuario**: S2·S6, S10 y S1
confirmados contra su backend real — y de esa misma pasada salen 3 hallazgos
nuevos sin tocar (NEW-4/5/6, doc 34 §12.4).*

*Anterior: 2026-07-28 — **S4 ejecutada (§26)**: camino caliente +
DEADLINES. El clasificador deja de heredar la política de calidad del usuario
(`TIE_CLASSIFY_MODEL/POLICY`, `router.complete` con overrides opcionales); el
transcript del toolloop deja de reenviarse entero (ventana deslizante que
conserva SIEMPRE objetivo y catálogo); y las tres capas del camino caliente
ganan plazo (petición del MEL con razón propia `timeout` que abre el breaker,
primer chunk de streaming, clasificador) más un latido cada 15 s para que
ningún turno se quede mudo. 18 tests nuevos + 420 de regresión en verde
(sandbox). NO se tocó el thrash de Ollama: su propio diseño exige verificarlo
en vivo antes.*

*Anterior: 2026-07-28 — **S3 ejecutada (§26)**: presupuesto de
llamadas LLM por camino, medido — `telemetry.record("path", ...)` en las 4
bifurcaciones reales del pipeline/orquestador (chat/direct/planned/multi),
`mission_timeline()` extendida de forma aditiva (`llm_calls`/`path`/`budget`/
`within_budget`/`slowest_llm_ms`), `mission_lab.py --baseline` para comparar
campañas con números. 9 tests nuevos + 180 de regresión en verde (sandbox).*

*Anterior: 2026-07-28 — **doc 34 reestructurado + S2·S6 ejecutada
(§26)**: cada sesión pendiente con diseño ejecutable contrastado contra el
código, fusiones S2·S6 y S7·S8, dos causas raíz localizadas (la tubería de
resultados entre nodos que no existe; el lanzamiento del navegador sin lock),
protocolo de campañas migrado a Claude con 4 bloques nuevos (REG·F·N·X). En
código: **narración anclada en las 3 capas** — `app/core/grounding.py` nuevo,
consolidator sin LLM, responder que descarta un "falta tu confirmación" falso,
y coletilla honesta en el camino corto. 34 tests nuevos + 191 de regresión en
verde (sandbox).*

*Anterior: 2026-07-27 — **S1 + S10 del bloque de auditoría del
runtime ejecutadas (§26)**: P1 (catálogo único) + P4 (auto-catálogo MEL
nocturno, sin CLI) + S10 (frontera de proyecto para `document`/`download`/
`browser`-descarga, bug reportado en vivo por el usuario) cerrados en código,
NEW-3 resuelto sin código. Plan de sesiones ampliado a S1-S10 tras la
campaña 01 de test en vivo. Suite backend (subset relevante, sandbox): ~370
tests verdes + 3 nuevos de S10.*

*Última actualización anterior: 2026-07-21 — **bloque UX + MEL-UI + OBSERVABILIDAD (§25)**; antes: 2026-07-20 — **V1.0 bloque ORQUESTRATOR (R1-R7) CERRADO,
bump `0.9.2` → `0.9.5`, tag `v0.9.5`** (ver §21) + **bloque CORRECCIÓN S1
ejecutada** (ver §22). Suite backend: **751 passed** (pre-S1; re-verificar).
Bloques cerrados: V0.2 → V0.7.3 → V0.8 → V0.85 (MOS) → V0.87 (WPMS) → V0.9
(Automation Engine) → V1.0 TIE v1 (T1-T5) → V1.0 MEL v1 (E1-E2b) → V1.0 Tools →
**V1.0 Orquestrator (R1-R7)**. Siguiente y último para `1.0.0`: **MVP-beta**
(instalador NSIS, auto-start del backend, onboarding).*
*Construido desde el estado real del repositorio (código + Alembic + docs de fase).*
*Sustituye a la versión V0.2 anterior, que declaraba un estado obsoleto.*

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
