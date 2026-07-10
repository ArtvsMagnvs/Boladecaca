# PROMPT DEFINITIVO PARA FABLE5 — AUDITORÍA COMPLETA Y PLAN DE OPTIMIZACIÓN

> **Propósito**: Fable5 debe auditar el estado actual del código de Aithera y producir
> un plan de optimización técnica para que el sistema existente funcione a la perfección
> antes de construir encima. Adicionalmente, debe garantizar que TODOS los sistemas
> diseñados en los prompts anteriores (MOS, Automation Engine, Orchestrator, LSL, LLL)
> están diseñados con rendimiento y calidad de producción desde el día uno.
>
> **Filosofía**: "Funciona bien" no es suficiente. Cada interacción debe ser rápida,
> predecible y sin sorpresas. Haces click, abre. Escribes, responde. Hablas, escucha.
> Sin cargas lentas, sin bucles de búsqueda, sin código redundante, sin renders
> innecesarios.

---

## 1. AUDITORÍA DEL BACKEND EXISTENTE

### 1.1 Arranque del backend

**Problema conocido**: el arranque tarda por la inicialización de ChromaDB +
sentence-transformers (~3-5 segundos después del primer import).

Fable5 debe auditar:
- ¿ChromaDB se inicializa de forma lazy o bloquea el arranque?
- ¿sentence-transformers descarga el modelo en cada arranque o cachea?
- ¿El `lifespan` de FastAPI hace operaciones síncronas que bloquean?
- ¿Los singletons (`ai_manager`, `tool_manager`, `memory_manager`) se inicializan
  en paralelo o en serie?

**Target**: backend disponible para recibir peticiones en < 2 segundos.
La inicialización de ChromaDB y sentence-transformers debe ir al background,
no bloquear el arranque.

### 1.2 Endpoint de chat — latencia del streaming

**Problema conocido**: el primer chunk del stream puede tardar si el `AIManager`
inicializa la conexión con el proveedor en caliente.

Fable5 debe auditar:
- ¿El `AIManager` mantiene conexiones HTTP persistentes o las abre en cada request?
- ¿El filtro de razonamiento B21 (`StreamingReasoningFilter`) añade latencia medible?
- ¿El RAG de memoria (inyección de contexto) está en el critical path del primer chunk?
- ¿El endpoint de streaming usa `StreamingResponse` de forma eficiente?

**Target**: primer chunk de respuesta en < 500ms para modelos locales (Ollama),
< 1.5s para modelos en la nube.

### 1.3 Sistema de memoria (ChromaDB)

**Problema conocido**: ChromaDB con sentence-transformers puede ser lento en
búsquedas si las colecciones son grandes o si el modelo de embeddings no está
en caché caliente.

Fable5 debe auditar:
- ¿Las búsquedas en ChromaDB están limitadas a top-k razonable (≤10)?
- ¿Se hace embedding de la query en el critical path o de forma lazy?
- ¿Hay búsquedas innecesarias (llamar a ChromaDB cuando no hay contexto útil)?
- ¿Las colecciones tienen los índices correctos?

**Target**: búsqueda semántica en < 200ms con colecciones de hasta 100,000 items.

### 1.4 Endpoints de email

El Email Assistant tiene 7 routers con lógica compleja. Fable5 debe auditar:
- ¿Hay llamadas a Gmail API en el critical path que podrían cachearse?
- ¿El triaje en 2 etapas (heurística + LLM) es eficiente para el inbox típico?
- ¿Los endpoints de `/digest` y `/briefing` hacen llamadas en caliente a Gmail
  o usan el índice de memoria (si existe)?
- ¿Hay N+1 queries en algún endpoint (una query SQL por email en lugar de un JOIN)?

### 1.5 Base de datos (PostgreSQL / SQLite)

Fable5 debe verificar:
- ¿Todas las tablas tienen índices en las columnas de búsqueda frecuente?
  (`created_at`, `status`, `user_id`, `project_id`, `category`)
- ¿Los modelos Alembic tienen índices definidos o se asume que el ORM los crea?
- ¿Hay queries que hacen `SELECT *` cuando solo se necesitan 2-3 columnas?
- ¿Las relaciones entre tablas tienen `lazy="select"` (N+1) en lugar de `lazy="joined"`?

### 1.6 Gateway y Telegram

Fable5 debe auditar:
- ¿El polling de Telegram consume CPU cuando no hay mensajes?
- ¿El Gateway tiene límites de rate para prevenir loops de mensajes?
- ¿El `chat_message_handler` del Gateway duplica lógica del endpoint `/api/chat`?
  (si es así, consolidar en una sola implementación)

---

## 2. AUDITORÍA DEL FRONTEND EXISTENTE

### 2.1 Bundle size y tiempo de carga inicial

**Target**: bundle inicial < 2MB gzipped. Primera pantalla visible < 1 segundo.

Fable5 debe auditar:
- ¿Three.js (AICore 3D) se carga en la ruta inicial o de forma lazy?
- ¿`@react-three/fiber` y `drei` están en el bundle principal o en un chunk separado?
- ¿Framer Motion está en el bundle principal (añade ~30KB gzipped)?
- ¿Las páginas tienen `React.lazy()` + `Suspense` para code splitting?

**Optimización esperada**: AICore.tsx con Three.js debe estar en un chunk separado
que se carga solo cuando el usuario navega al Hub. Las otras páginas deben cargar
sin esperar a Three.js.

### 2.2 Re-renders innecesarios

**Problema conocido**: el store de Zustand tiene selectores en algunas páginas pero
no en todas. Un cambio en cualquier propiedad del store puede re-renderizar todo.

Fable5 debe auditar:
- ¿Todas las páginas usan selectores granulares (`useAppStore(s => s.foo)` en
  lugar de `useAppStore()` completo)?
- ¿`Hub.tsx` (29.5KB) tiene efectos que se re-ejecutan innecesariamente?
- ¿El AICore 3D re-renderiza en cada tick del `useFrame` o solo cuando cambia `coreState`?
- ¿Las listas de emails, tareas y proyectos se re-renderizan en cada poll de 30s?

### 2.3 Polling y efectos

El Hub hace polling cada 30s para actualizar el estado. Fable5 debe auditar:
- ¿El polling provoca re-renders en toda la UI o solo actualiza los datos que cambiaron?
- ¿Los `useEffect` con dependencias vacías `[]` tienen cleanup correcto?
- ¿Hay efectos que se re-ejecutan en cada render porque tienen objetos/funciones
  como dependencias (problema clásico de React)?
- ¿El `messagesEndRef.current?.scrollIntoView()` en Chat.tsx se ejecuta en
  todos los renders o solo cuando hay mensajes nuevos?

### 2.4 Streaming del chat

Fable5 debe auditar el flujo de streaming SSE:
- ¿El `accumulatedRef` pattern (ya implementado) elimina completamente el closure bug?
- ¿El `setStreamingText()` en cada chunk provoca un render por chunk? (puede ser
  caro con modelos rápidos que envían 20+ chunks/segundo)
- **Optimización posible**: batch de updates de streaming cada 50ms en lugar de
  en cada chunk, usando `requestAnimationFrame` o `setTimeout(0)`.

### 2.5 Electron y permisos

- ¿El `preload.cjs` expone solo lo necesario o tiene surface de seguridad innecesaria?
- ¿El permission handler de micrófono (V0.83) tiene cleanup correcto al cerrar?

---

## 3. DEUDA TÉCNICA IDENTIFICADA

Fable5 debe revisar y confirmar (o ampliar) esta lista de deuda técnica conocida:

| # | Deuda | Impacto | Versión para saldar |
|---|-------|---------|---------------------|
| 1 | Backend NO arranca desde Electron | UX: usuario arranca manual | Pre-V1.0 (o V1.0) |
| 2 | ChatMessage `model_used`/`tokens_used` vs ChatResponse `model`/`tokens` | Inconsistencia datos | Pre-V1.0 |
| 3 | `email_processing.py` (1017 líneas, aún sin dividir) | Mantenibilidad | V0.85 o V0.9 |
| 4 | ChromaDB bloquea arranque | Latencia startup | V0.85 |
| 5 | No hay índices explícitos en tablas de BD | Performance queries | V0.85 o auditoría |
| 6 | Hub.tsx (29.5KB) carga Three.js en route principal | Bundle bloat | V0.82/V0.83 |
| 7 | Streaming: render por chunk | Posible jank en modelos rápidos | V1.0 |
| 8 | Selectores Zustand no granulares en todas las páginas | Re-renders | V1.0 |

---

## 4. PLAN DE OPTIMIZACIÓN — PRIORIDADES

### PRIORIDAD 1 — Hacerlo antes de V0.85

Estas optimizaciones son baratas y tienen alto impacto:

**B1: Lazy loading de Three.js y AICore**
```tsx
// frontend/src/pages/Hub.tsx
const AICore = React.lazy(() => import("@/components/hub/AICore"));

// Solo carga Three.js cuando el Hub se renderiza
<Suspense fallback={<HubCorePlaceholder />}>
  <AICore state={coreState} />
</Suspense>
```

**B2: ChromaDB en background al arrancar**
```python
# backend/app/main.py — lifespan
@asynccontextmanager
async def lifespan(app):
    # Arrancar backend INMEDIATAMENTE (no esperar a ChromaDB)
    asyncio.create_task(memory_manager.initialize_async())  # background
    yield
    await memory_manager.shutdown()
```

**B3: Índices en las tablas más consultadas**
Nueva migración Alembic solo con índices:
```python
# Alembic migration: add_performance_indexes
op.create_index("ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"])
op.create_index("ix_tasks_status", "tasks", ["status"])
op.create_index("ix_email_triage_email_id", "email_triage", ["email_id"])
op.create_index("ix_agent_executions_status", "agent_executions", ["status"])
```

### PRIORIDAD 2 — Durante V0.85

**B4: Streaming batching**
```typescript
// Batch de updates cada 50ms para no render por chunk
const batchTimerRef = useRef<number | null>(null);

const handleChunk = (chunk: string) => {
  accumulatedRef.current += chunk;
  if (!batchTimerRef.current) {
    batchTimerRef.current = requestAnimationFrame(() => {
      setStreamingText(accumulatedRef.current);
      batchTimerRef.current = null;
    });
  }
};
```

**B5: Granularidad de selectores en páginas pendientes**
Páginas que aún hacen `useAppStore()` completo → migrar a selectores granulares.

**B6: Auto-start del backend desde Electron**
El backend debería arrancar automáticamente cuando Electron abre. Opciones:
- Script `.bat` ejecutado desde `electron/main.cjs` al arrancar
- Servicio Windows registrado en la instalación (electron-builder NSIS hook)

### PRIORIDAD 3 — Antes de V1.0

**B7: Dividir `email_processing.py`** en módulos específicos de triaje y pipeline.

**B8: Resolver inconsistencia `model_used`/`tokens_used`** en el modelo `ChatMessage`.

---

## 5. ESTÁNDARES DE RENDIMIENTO PARA LOS NUEVOS SISTEMAS

Todo sistema diseñado en los prompts anteriores (MOS, Automation Engine, Orchestrator,
LSL, LLL) debe cumplir estos estándares. Fable5 debe incorporarlos en cada RFC:

### 5.1 MOS (Memory Operating System)

| Operación | Target | Máximo aceptable |
|-----------|--------|-----------------|
| `Memory API.add()` | < 50ms | 200ms |
| `Memory API.search()` top-10 | < 150ms | 500ms |
| `Context API.buildContext()` | < 300ms | 800ms |
| `Skill API.execute()` (local) | < 100ms | 300ms |
| Job de ingesta de emails | No bloquea event loop | ≤ 5% CPU background |
| Local Learning Loop (ciclo) | Transparente para usuario | ≤ 3% CPU en background |

### 5.2 Automation Engine

| Operación | Target | Máximo aceptable |
|-----------|--------|-----------------|
| Evaluación de trigger | < 10ms | 50ms |
| Evaluación de condiciones | < 20ms | 100ms |
| Inicio de ejecución de regla | < 50ms desde evento | 200ms |
| Notificación de approval gate | < 500ms desde trigger | 2s |

### 5.3 Orchestrator

| Operación | Target | Máximo aceptable |
|-----------|--------|-----------------|
| Intent classification | < 500ms (Ollama local) | 1.5s (cloud) |
| Context enrichment (MOS) | < 300ms | 800ms |
| Task planning (modelo potente) | < 3s | 8s |
| Primer resultado al usuario | < 1s desde query | 3s |
| Ejecución step básico (tool call) | < 2s | 10s |

### 5.4 Local Learning Loop

- Ciclo de análisis cada 6 horas: **transparente** (usuario no lo nota)
- Micro-batch: máximo 50 items por ciclo para no acaparar CPU
- Prioridad de thread: IDLE (solo cuando el sistema está sin actividad)
- Propuesta de skill al usuario: **no bloqueante**, aparece como notificación suave

---

## 6. OPTIMIZACIONES DE DISEÑO EN LOS NUEVOS SISTEMAS

Fable5 debe incorporar estas optimizaciones en el diseño de cada sistema nuevo:

### 6.1 MOS — Evitar hot paths en el critical path

El Context Enricher del Orchestrator llama a `Context API.buildContext()` antes
de cada query. Esto NO puede estar en el critical path de respuesta al usuario.
Fable5 debe diseñar:
- **Pre-fetch de contexto**: el Orchestrator inicia `buildContext()` mientras el
  usuario todavía está escribiendo (usando el texto parcial del input)
- **Caché de contexto**: si la misma query o similar se hizo en los últimos 60s,
  reutilizar el contexto (invalidar si la memoria cambia)

### 6.2 Automation Engine — Diseño sin bloqueo

Los triggers que escuchan eventos (emails, calendario) NO deben usar polling
activo. Deben ser reactivos:
- El EmailAssistant ya tiene un job de triaje → el EventTrigger escucha ese job,
  no hace su propio polling a Gmail
- El CalendarTool ya indexa eventos → el EventTrigger escucha el índice, no
  consulta Google Calendar en cada evaluación

### 6.3 Orchestrator — Plans pequeños por defecto

El Task Planner debe preferir planes de 2-3 steps cuando sea posible. Los planes
largos (5+ steps) solo se generan cuando el usuario explícitamente pide tareas
complejas. Un plan innecesariamente largo:
- Cuesta más en tokens del modelo potente
- Introduce más puntos de fallo
- Requiere más aprobaciones intermedias

Regla de diseño: si el Task Planner genera un plan de >5 steps para una query
simple, es un bug de planificación, no una feature.

### 6.4 LSL — Skills cargadas en memoria en arranque

La Local Skill Library carga todas las skills en estado `LOCAL` y `VALIDATED` en
memoria al arrancar (no ChromaDB lookup en cada ejecución). Las skills son
relativamente pequeñas (<5KB c/u) y cambiarán pocas veces al día. Cache en
memoria con invalidación cuando el usuario añade/modifica una skill.

---

## 7. CÓDIGO A ELIMINAR O CONSOLIDAR

Fable5 debe identificar y proponer eliminación de:

1. **Código muerto confirmado**: `backend/modules/` ya fue eliminado (V0.7.2).
   Verificar que no queden referencias en ningún import.

2. **Lógica duplicada Gateway/Chat**: el `chat_message_handler` en `gateway.py`
   y el endpoint `POST /api/chat` comparten lógica. Fable5 debe verificar si
   se puede consolidar o si hay razones para mantenerlos separados.

3. **Voces predefinidas hardcodeadas en `voice.py`**: el `espeak_voice_map` con
   IDs de ElevenLabs hardcodeados es deuda técnica. Fable5 debe proponer cómo
   hacer este mapeo configurable.

4. **`PROFESSIONAL_VOICES` en `elevenlabs_voice.py`**: lista de voces hardcodeada
   que ya se ha probado incorrecta (IDs no existen en la cuenta real). Debe
   eliminarse completamente — el endpoint `/voices/account` ya hace la llamada
   correcta a la API.

---

## 8. TESTS QUE FALTAN (COBERTURA MÍNIMA PARA V1.0)

Fable5 debe incluir en su plan los tests que hay que añadir antes de V1.0:

| Test | Tipo | Prioridad |
|------|------|-----------|
| `test_startup_time.py` | Performance | Alta — backend debe arrancar en < 2s |
| `test_streaming_latency.py` | Performance | Alta — primer chunk < 500ms (Ollama) |
| `test_memory_contracts.py` | Contrato API | Alta — API del MOS no puede cambiar |
| `test_orchestrator_contracts.py` | Contrato API | Alta — antes de V1.0 |
| `test_automation_isolation.py` | Unit | Media — fallo de acción no bloquea engine |
| `test_chromadb_search_perf.py` | Performance | Media — búsqueda < 200ms con 10k items |
| `test_chat_render_count.tsx` | UI | Baja — renders en streaming no >1 por 50ms |

---

## 9. MISIÓN DE FABLE5

1. **Auditoría del backend**: revisar los archivos listados en la sección 1 y
   confirmar/ampliar los problemas identificados. Proponer soluciones concretas.

2. **Auditoría del frontend**: revisar los archivos listados en la sección 2.
   Proponer optimizaciones de bundle, re-renders y streaming.

3. **Plan de optimización priorizado**: lista ordenada de optimizaciones con
   estimación de esfuerzo (en sesiones con Opus 4.8) y versión objetivo.

4. **Estándares de rendimiento en todos los RFCs**: asegurarse de que cada RFC
   de los prompts anteriores (MOS, AE, Orchestrator) incluye los targets de
   rendimiento de la sección 5 y las optimizaciones de diseño de la sección 6.

5. **Lista de código a eliminar**: confirmar y ampliar la sección 7. Todo código
   muerto eliminado = menos superficie de bugs.

6. **Plan de tests de rendimiento**: integrar los tests de la sección 8 en el
   plan de sprints de V0.85 y V1.0.

7. **Verificación de coherencia**: todo lo diseñado en PROMPT_01–06 debe pasar
   el "filtro de rendimiento" de este documento. Si algo está diseñado de forma
   que inevitable producirá lentitud (e.g., búsqueda síncrona en critical path),
   Fable5 debe señalarlo y proponer alternativa.

---

## 10. DOCUMENTOS DE CONTEXTO QUE FABLE5 DEBE LEER

1. `CLAUDE.md` — stack real, deuda técnica §16, riesgos §17
2. `backend/app/main.py` — lifespan, arranque, exception handler
3. `backend/app/memory/memory_manager.py` — ChromaDB initialization
4. `backend/app/ai/ai_manager.py` — cómo se inicializa el AIManager
5. `frontend/src/pages/Hub.tsx` — componente más pesado (29.5KB)
6. `frontend/src/pages/Chat.tsx` — streaming SSE
7. `frontend/src/components/hub/AICore.tsx` — Three.js, shader custom
8. `backend/alembic/versions/` — estado actual de las migraciones
9. Todos los prompts anteriores (PROMPT_01–06) — para el filtro de rendimiento

---

*Documento creado: 2026-07-09. La optimización no es una fase separada — es una
dimensión de calidad que debe estar presente en cada decisión de diseño e
implementación desde V0.85 hasta V2.0+.*
