# 12 — Auditoría técnica y plan de optimización

> **Origen**: `FABLE5_PROMPTS/PROMPT_07_AUDIT_OPTIMIZATION.md`.
> **Filosofía**: "funciona bien" no basta. Click → abre. Escribes → responde.
> La optimización no es una fase: es una dimensión de calidad presente en cada RFC
> (07-11 incluyen ya sus presupuestos). Este doc consolida hallazgos VERIFICADOS
> contra el código real (2026-07-09) y el plan priorizado.

---

## 1. Hallazgos verificados — Backend

| # | Hallazgo | Evidencia | Impacto | Fix |
|---|---|---|---|---|
| A1 | **ChromaDB + sentence-transformers se inicializan en el `__init__` del singleton, en el import de `main.py`** — bloquean el arranque 3-5 s | `memory_manager.py:36-51` (import chromadb + SentenceTransformerEmbeddingFunction síncronos en constructor) | arranque lento SIEMPRE | init lazy en background: `asyncio.create_task(memory_manager.initialize_async())` en lifespan; `is_healthy()` devuelve False hasta terminar (la degradación graceful ya existe — solo hay que mover el momento) |
| A2 | **httpx sin conexiones persistentes**: cada request de chat abre `AsyncClient` nuevo (TLS handshake en el critical path del primer chunk) | `openai_compatible.py:63,89,134` (`async with httpx.AsyncClient(...)` por llamada) | +100-300 ms por respuesta | un `AsyncClient` por provider (creado lazy, cerrado en shutdown), timeout por request |
| A3 | **Solo 3 `index=True` en toda la BD** — faltan índices en columnas de filtro frecuente | `grep -c index=True database.py` = 3 | queries lentas al crecer | migración solo-índices: `email_activity_log(action_type, read, timestamp)`, `email_triage(created_at)`, `agent_executions(status)`, `tasks(status)`, `calendar_events(start_date)`, `chat_messages(created_at)` |
| A4 | **`chat_message_handler` (gateway) duplica lógica de `/api/chat`** | `gateway.py` vs `chat.py` (mismo pipeline memoria+ai+strip) | doble mantenimiento, ya divergen (persistencia ChatMessage solo en endpoint) | consolidar en `app/services/chat_service.py` (programado: doc 07 sprint M4) |
| A5 | **`email_processing.py` 1017 líneas** (deuda registrada §16 CLAUDE.md) | wc -l | mantenibilidad | dividir junto al trabajo MOS de ingesta (V0.85 M2) o V0.9 A2 — cuando se toque, no antes |
| A6 | **`PROFESSIONAL_VOICES` hardcodeado con IDs probados incorrectos** + mapa espeak↔ElevenLabs hardcodeado | `elevenlabs_voice.py:16,263-281` | bugs de voz, código muerto | eliminar la constante; usar SIEMPRE `/voices/account` (ya existe); mapeo configurable en Settings (V0.83 remate) |
| A7 | Digest/briefing actuales solo leen BD local (OK), pero `summary` y triaje llaman a Gmail/LLM en caliente | por diseño V0.7 | aceptable hasta V0.85 | la ingesta del MOS los convierte en lecturas de índice (doc 07) |
| A8 | Polling de Telegram: PTB usa long-polling (eficiente); sin rate-limit en el Gateway | diseño V0.8 | riesgo de loop de mensajes | cooldown por `user_ref` en `Gateway.dispatch` (1 línea de diseño, implementar en V0.9 A2 con las CooldownCondition) |

## 2. Hallazgos verificados — Frontend

| # | Hallazgo | Evidencia | Fix |
|---|---|---|---|
| F1 | **Three.js/AICore en el bundle principal** — sin `React.lazy`/`Suspense` en Hub.tsx | grep lazy/Suspense en Hub.tsx = 0 | `const AICore = React.lazy(() => import(...))` + `<Suspense fallback={<HubCorePlaceholder/>}>`; revisar que Vite genere chunk separado (three ≈ 600KB min) |
| F2 | Sin `React.lazy` por página (todas las rutas en el bundle inicial) | HashRouter con imports estáticos | code-splitting por ruta con `Suspense` en AppLayout |
| F3 | **Streaming: un render por chunk SSE** (20+/s con modelos rápidos) | patrón actual `setStreamingText` por chunk | batch con `requestAnimationFrame`: acumular en `accumulatedRef` (ya existe) y volcar ≤1 vez por frame |
| F4 | Selectores Zustand no granulares en todas las páginas | revisión por página pendiente | migrar a `useStore(s => s.campo)`; regla de lint mental para código nuevo |
| F5 | Polling del Hub cada 30 s re-setea estados aunque no cambien | `Hub.tsx` efectos | comparar antes de `setState` (o `Object.is` sobre JSON corto); los paneles no deben re-render si su dato no cambió |

## 3. Plan priorizado (sesiones Opus 4.8)

| Prioridad | Ítems | Cuándo | Coste |
|---|---|---|---|
| **P1 — antes/durante V0.85** | A1 (init background) + A3 (índices) — van DENTRO del sprint M5 de doc 07; F1+F2 (lazy Three/rutas) — sprint corto independiente "perf-front" | V0.85 | 1 sesión front + incluido en M5 |
| **P2 — durante V0.85/V0.9** | A2 (httpx persistente), A4 (chat_service, M4), F3 (batch streaming), F5 (polling sin re-render), A6 (voces) | V0.85-V0.9 | ~1.5 sesiones |
| **P3 — antes de V1.0 (bloqueantes de beta)** | **B6: auto-start del backend desde Electron** (spawn del proceso uvicorn desde `electron/main.cjs` + health-wait + kill on quit; instalador NSIS lo empaqueta) · A5 (split processing) · F4 (selectores) · deuda `model_used/tokens` de ChatMessage | V1.0 sprint O5 | ~2 sesiones |

**B6 es requisito duro del MVP beta**: un usuario beta no puede arrancar uvicorn a
mano. Diseño: `main.cjs` lanza `backend/venv/python -m uvicorn...` (o el exe
empaquetado), espera `/health` con timeout 20 s, muestra splash, mata el proceso al
salir; si el puerto ya está en uso, se conecta sin lanzar (modo desarrollador).

## 4. Estándares de rendimiento (vinculantes para los RFCs 07-11)

| Sistema | Operación | Target | Máximo |
|---|---|---|---|
| Backend | arranque hasta aceptar peticiones | < 2 s | 4 s |
| Chat | primer chunk (Ollama / cloud) | < 500 ms / 1.5 s | 1 s / 3 s |
| MOS | `add` / `search` top-10 / `context()` | 50 / 150 / 300 ms | 200 / 500 / 800 ms |
| MOS | jobs ingesta/LLL | invisible | ≤ 5% / 3% CPU |
| AE | trigger / condiciones / inicio acción / gate notif | 10 / 20 / 50 / 500 ms | 50/100/200/2000 ms |
| Orchestrator | intent / enrich / plan / 1er feedback | 500 ms / 300 ms / 3 s / 1 s | 1.5/0.8/8/3 s |
| LSL | `execute()` overhead | < 100 ms | 300 ms |
| Front | bundle inicial / primera pantalla | < 2 MB gz / < 1 s | — |

Optimizaciones de diseño ya incorporadas en los RFCs: pre-fetch + caché 60 s de
contexto (11 B.2), triggers reactivos sin polling propio (11 A.1), planes de 2-3
steps por defecto (11 B.1), skills cacheadas en RAM (09 §1.3), presupuesto/timeout
en `context()` (07 §8), compactación para que la búsqueda no degrade (08 RFC-007).

## 5. Código a eliminar/consolidar

1. `PROFESSIONAL_VOICES` + `espeak_voice_map` hardcodeados (A6) — eliminar.
2. Duplicación gateway/chat (A4) — consolidar en `chat_service`.
3. Verificado: no quedan imports de `backend/modules/` (eliminado V0.7.2). ✅
4. Scripts de debug en `backend/` raíz (`_test_*.py`, `_debug_*.py`, `*_out.txt`,
   `extract_docx.py`) — mover a `backend/scripts/dev/` o borrar (están en git).

## 6. Tests que faltan (cobertura mínima V1.0)

| Test | Tipo | Cuándo |
|---|---|---|
| `test_startup_time.py` (arranque < 2 s, import de main sin ChromaDB bloqueante) | perf | V0.85 M5 |
| `test_memory_contracts.py` / `_ingestion` / `_context` / `_briefing` | contrato/unit | V0.85 M1-M4 |
| `test_chromadb_search_perf.py` (10k items < 200 ms) | perf | V0.85 M5 |
| `test_streaming_latency.py` (1er chunk, con provider fake) | perf | V0.9 |
| `test_automation_isolation.py` + `test_approval_gate.py` (persistencia/reanudación) | unit | V0.9 A1-A2 |
| `test_orchestrator_contracts.py` + `test_orchestrator_perf.py` | contrato/perf | V1.0 O4 |
| render-count del streaming (≤1 render/50 ms) | UI (manual/devtools) | V1.0 O5 |

## 7. Verificación de coherencia de los RFCs (filtro de rendimiento)

Revisados 07-11 contra la sección 4: ningún diseño coloca búsquedas sin presupuesto
en el critical path; todos los jobs son background con micro-batch; toda llamada
LLM interna tiene fallback determinista y `strip_reasoning`; el único punto de
riesgo señalado es el **Context Enricher en cada query** (V1.0) — mitigado con el
camino corto conversational + pre-fetch + caché (11 B.2). Sin contradicciones
detectadas entre PROMPT_01-07; la única corrección aplicada es la de PROMPT_05
(capas 3/4 locales), ya integrada en 08 y 09.

---
*Auditoría 2026-07-09 (Fable 5) sobre el código real en `master` (v0.8.0).*
