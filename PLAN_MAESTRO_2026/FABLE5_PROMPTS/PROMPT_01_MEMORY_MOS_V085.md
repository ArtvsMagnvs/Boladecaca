# PROMPT DEFINITIVO PARA FABLE5 — DISEÑO DEL MEMORY OPERATING SYSTEM (MOS) V0.85

> **Propósito de este documento**: Briefing técnico + filosófico completo para que
> Fable5 diseñe el plan de implementación definitivo de V0.85 Memory & Context,
> considerando todo el PLAN_MAESTRO_2026 previo y las decisiones de arquitectura
> tomadas en el "Aithera Master Specification" (Memory System Prompts GPT.docx).
>
> **Qué debe entregar Fable5 tras leer esto**: Un documento de diseño técnico para
> V0.85 que incluya arquitectura detallada, contratos de código, plan de sprints,
> criterios de cierre y cómo encaja con V0.9, V1.0 y V1.1. Debe partir de la
> **Opción elegida** (sección 5) y expandirla en un plan de ingeniería ejecutable.

---

## 1. CONTEXTO TÉCNICO ACTUAL — LO QUE YA EXISTE

El proyecto Aithera está en **V0.8** (estado real del código). Todo lo anterior está
funcionando y commiteado. Lo relevante para el diseño de memoria:

### 1.1 Sistema de memoria existente (V0.6 ChromaDB)

Archivo: `backend/app/memory/memory_manager.py` (~15KB)

Tres colecciones ChromaDB actuales:
- `conversations` — embeddings de mensajes de chat para RAG
- `user_context` — contexto personal persistente (preferencias del usuario)
- `documents` — documentos indexados subidos por el usuario

Tecnología: `ChromaDB 1.5.9` + `sentence-transformers 3.3.1` (modelo
`all-MiniLM-L6-v2`, ~80MB). Embeddings locales, sin cloud.

Degradación graceful: si ChromaDB no arranca, el chat sigue funcionando.
Stats en log al arrancar: `Memory system listo — N conv, M ctx, K docs`.

**El sistema existe pero tiene uso limitado**: el chat apenas usa el RAG
conversacional. No hay ingesta automática, no hay resúmenes, no hay contexto
de proyectos ni de emails.

### 1.2 Infraestructura relevante ya construida

- **Email Assistant (V0.7.3)**: 7 routers de email, triaje en 7 categorías,
  clasificador 2 etapas, digest diario, autonomía gradual. Los emails ya tienen
  categorías de triaje listas para indexar.
- **Google Calendar (V0.7)**: `calendar_tool.py` (29KB), acceso OAuth, eventos
  próximos disponibles.
- **Gateway + Canal Telegram (V0.8)**: mensajes multicanal disponibles para
  entregar briefings.
- **AIManager multi-proveedor**: 8 proveedores IA, incluyendo Ollama local.
  Ollama es clave para los resúmenes batch (coste cero).

### 1.3 Stack técnico inviolable

- Backend: FastAPI + SQLAlchemy 2.0 + PostgreSQL (o SQLite fallback)
- Asincronismo: `asyncio` nativo de FastAPI. NO hay Celery. NO hay Redis.
- Scheduler: NO hay APScheduler en V0.85 (llega en V0.9). Los jobs de background
  se implementan como tareas asyncio en el `lifespan` de FastAPI.
- ORM: modelos nuevos siempre con migración Alembic correspondiente.
- Pydantic v2 (`from_attributes=True`, `model.model_dump()`).

---

## 2. FILOSOFÍA Y VISIÓN — DE DÓNDE VIENEN LAS DECISIONES

Las decisiones de arquitectura de V0.85 vienen de un análisis estratégico a largo
plazo. Fable5 debe conocerlas para entender por qué se pide lo que se pide.

### 2.1 Aithera como OS para IAs

Aithera NO es un chatbot, NO es un agente. Es una **infraestructura cognitiva**
diseñada para sobrevivir a cualquier LLM o runtime concreto. Si mañana aparece un
modelo mejor que Claude, un framework mejor que el actual, o una librería de agentes
mejor que Hermes, Aithera debe poder incorporarlos sin perder ni un byte de memoria,
ni una skill, ni un contexto.

**La memoria nunca pertenece al runtime. Pertenece a Aithera.**

### 2.2 ACI y MOS — los dos conceptos clave

El documento estratégico introduce dos términos que Fable5 debe usar como ancla:

- **ACI (Aithera Cognitive Infrastructure)**: toda la infraestructura cognitiva de
  Aithera. Incluye memoria, skills, herramientas, automatización y orquestación.
- **MOS (Memory Operating System)**: el subsistema de la ACI responsable
  exclusivamente de la memoria. V0.85 construye el esqueleto del MOS.

El MOS tiene capas. En V0.85 solo se implementan las capas locales:

```
MOS (Memory Operating System)
├── [V0.85] Private Memory      ← conversacional, personal, proyectos locales, decisiones
├── [V0.85] Skill Memory        ← skills detectadas y aprendidas
├── [V1.0+] Project Memory      ← contexto distribuido de proyectos (stub en V0.85)
├── [V2.0+] Global Skill Network ← red de skills compartidas (stub en V0.85)
└── [V2.0+] Collective Intelligence Engine ← inteligencia colectiva (stub en V0.85)
```

Las capas V1.0+ y V2.0+ **no se implementan** en V0.85, pero sus **interfaces y
contratos SÍ deben existir desde el principio** (como stubs/noop implementations).
Esto es lo que diferencia un sistema con deuda técnica de uno sin ella.

### 2.3 Regla fundamental de implementación

*Diseñar hoy la arquitectura para todo. Implementar hoy solo lo necesario.*

Cuando existan dos opciones:
- **A**: Más completa, más compleja, más lenta de construir.
- **B**: Más sencilla, arquitectura correcta, preparada para evolucionar.

Elegir siempre **B**, mientras no obligue a romper la arquitectura futura.

### 2.4 Criterio de éxito de V0.85

Un único criterio de cierre que lo resume todo:

> Preguntar "¿qué me ha llegado importante hoy?" debe responder desde memoria
> local sin llamar a Gmail en caliente.

---

## 3. QUÉ DEBE SER CAPAZ DE HACER V0.85

Independientemente de la opción de complejidad elegida (sección 5), V0.85 debe
cumplir estos objetivos funcionales:

| Capacidad | Descripción | Prioridad |
|-----------|-------------|-----------|
| Ingesta de email | Job background que indexa emails triacados en ChromaDB | Obligatoria |
| Ingesta de calendario | Indexar eventos próximos y pasados recientes | Obligatoria |
| Contexto en chat | El endpoint `/api/chat` inyecta memoria relevante en el prompt | Obligatoria |
| Resumen diario | Batch nocturno que genera resúmenes email+agenda del día | Obligatoria |
| Briefing on-demand | `¿Qué me ha llegado hoy?` respondido desde memoria | Obligatoria |
| API de memoria limpia | Endpoints `/api/memory/*` con contrato estable | Obligatoria |
| Vault legible | Espejo Markdown en `%APPDATA%/Aithera/vault/` | Opcional |
| Detección de skills | Identificar patrones de uso y skills del usuario | Opcional |
| Detección de patrones | Análisis de frecuencia de temas/personas en emails | Opcional |

---

## 4. LO QUE NO DEBE TOCAR V0.85

Para que la memoria no se convierta en un cuello de botella:

1. **No usar APScheduler** — llega en V0.9. Los jobs de ingesta van en `asyncio`.
2. **No distribuir nada** — 100% local. Sin servidores adicionales, sin sync cloud.
3. **No romper el sistema de chat existente** — el RAG conversacional que existe
   en ChromaDB debe coexistir con las nuevas colecciones.
4. **No reescribir `memory_manager.py`** — extender, no reemplazar.
5. **No bloquear V0.9** — si V0.85 tarda más de ~6 sesiones con Opus 4.8, hay
   que recortar scope, no posponer V0.9.
6. **No inventar nuevas dependencias pesadas** — ChromaDB + sentence-transformers
   ya están. Nada nuevo salvo lo estrictamente necesario.

---

## 5. LAS TRES OPCIONES DE COMPLEJIDAD — DECISIÓN PENDIENTE

A continuación se presentan tres opciones de implementación para que el usuario
(Alejandro) elija. Fable5 desarrollará el plan detallado de la opción elegida.

---

### OPCIÓN A — MOS Express: "Memoria útil ya, arquitectura después"

**En lenguaje llano**: Cogemos el ChromaDB que ya existe y le añadimos dos cosas
concretas: un robot que indexa emails nuevos cada 20 minutos, y un resumen diario
que se genera por la noche. El chat empieza a usar esos datos para responder mejor.
No tocamos la arquitectura en profundidad; eso lo dejamos para más adelante.

**Tiempo estimado**: 2–3 sesiones con Opus 4.8 (~1 semana de trabajo IA)

**Qué se construye**:
- Job asyncio de ingesta: emails triacados → ChromaDB colección `emails_indexed`
- Job nocturno con Ollama: genera resumen día → ChromaDB colección `daily_summaries`
- Endpoint de chat mejorado: inyecta top-5 documentos relevantes en el prompt
- Endpoint `/api/memory/briefing` para el briefing on-demand
- Stats en el Hub: última ingesta, total indexado, cobertura de días

**Lo que NO incluye**:
- Interfaz `IMemoryStore` formal (se puede añadir después pero hay que tocarlo todo)
- Tipos de memoria diferenciados (skills, decisiones, proyectos)
- Vault legible
- Contratos para que Hermes y el Orchestrator los usen directamente

**Deuda técnica generada**: Cuando llegue V1.0 (Orchestrator) necesitará
una interfaz limpia para consultar la memoria. Con esta opción habrá que
refactorizar `memory_manager.py` para añadirla. No es un drama, pero son
2-3 horas extras en ese momento.

**Elegir esta opción si**: El objetivo es tener memoria funcionando esta semana y
continuar inmediatamente con V0.9 Automation.

---

### OPCIÓN B — MOS Skeleton: "Arquitectura correcta, implementación mínima" ⭐ RECOMENDADA

**En lenguaje llano**: Construimos la "columna vertebral" definitiva de la memoria
de Aithera. Definimos claramente los 5 tipos de memoria que va a tener el sistema
(conversacional, personal, proyectos, skills, decisiones), creamos una "API interna"
limpia para acceder a ellos, y sobre esa base implementamos las funcionalidades de
V0.85. Lo que NO se implementa todavía (memoria distribuida, red de skills, etc.)
queda como una puerta cerrada pero ya construida — cuando llegue el momento, solo
hay que abrir la puerta, no derribar la pared.

**Tiempo estimado**: 4–6 sesiones con Opus 4.8 (~2 semanas de trabajo IA)

**Qué se construye**:

*Núcleo arquitectónico:*
- Interfaz `IMemoryStore` con 5 operaciones core (`store`, `retrieve`, `search`,
  `summarize`, `forget`)
- `LocalMemoryStore` que implementa `IMemoryStore` sobre ChromaDB
- `MemoryRouter` que enruta consultas al store correcto según tipo de memoria
- 5 tipos de memoria con colecciones ChromaDB propias: `mem_conversational`,
  `mem_personal`, `mem_project`, `mem_skill`, `mem_decision`
- Stubs `DistributedMemoryStore` y `GlobalSkillStore` (noop) para que el
  Orchestrator y Hermes tengan contratos sin implementación real aún

*Funcionalidad V0.85:*
- Job asyncio de ingesta: emails + calendario → ChromaDB con metadata rico
  (categoría de triaje, timestamp, sender, priority)
- Job nocturno con Ollama: resumen diario jerarquizado (email → día)
- Inyección de contexto en chat: top-k retrieval con atribución de fuente
  (el chat sabrá "esto viene de un email del martes")
- Endpoint `/api/memory/briefing` + tarjeta en el Hub
- Vault opcional: espejo Markdown en `%APPDATA%/Aithera/vault/`

*Lo que NO se implementa pero SÍ existe como contrato:*
```python
class DistributedMemoryStore(IMemoryStore):
    """V2.0+ — Project Memory distribuida. Sin implementación en V0.85."""
    async def store(self, *args, **kwargs):
        raise NotImplementedError("DistributedMemoryStore llegará en V2.0")

class GlobalSkillStore(ISkillStore):
    """V2.0+ — Global Skill Network. Sin implementación en V0.85."""
    ...
```

**Deuda técnica generada**: Prácticamente ninguna. El Orchestrator (V1.0) podrá
depender directamente de `IMemoryStore`. Hermes (V1.1) recibirá un
`AitheraMemoryProvider` que envuelve `LocalMemoryStore`. Cuando llegue V2.0
se añadirá `DistributedMemoryStore` sin tocar nada de lo que existe.

**Elegir esta opción si**: Quieres hacer V0.85 una sola vez, bien hecha, y que
sirva como base sólida hasta V2.0 sin migraciones ni refactors.

---

### OPCIÓN C — ACI Skeleton: "El sistema definitivo desde el día uno"

**En lenguaje llano**: Construimos el esqueleto completo de toda la infraestructura
cognitiva de Aithera (no solo la memoria, sino también el sistema de skills, el
enrutador de contexto, el motor de patrones). Es como construir todos los cimientos
de un rascacielos cuando de momento solo vamos a vivir en los dos primeros pisos.

**Tiempo estimado**: 8–12 sesiones con Opus 4.8 (~4-6 semanas de trabajo IA)

**Qué se construye** (sobre todo lo de la Opción B, más):
- `ISkillStore`, `IContextBuilder`, `IMemoryRouter` como interfaces formales
- Motor de detección de patrones básico (análisis de frecuencia: personas,
  temas, proyectos recurrentes en emails y conversaciones)
- Summary tree completo: email → hilo → día → semana (4 niveles)
- Vault con sincronización bidireccional (borrar un .md = olvidar en ChromaDB)
- Sistema de prioridades de memoria (qué olvidar cuando el espacio es limitado)
- Panel de memoria en el Hub (visualización de lo que Aithera recuerda)

**Deuda técnica generada**: La más baja de las tres opciones a largo plazo.

**El problema**: Con esta opción, V0.9 Automation Engine se retrasa 1-2 meses.
Y V1.0 Orchestrator, 2-3 meses más. El ritmo de desarrollo se detiene en memoria
cuando el usuario todavía tiene V0.9, V1.0 y V1.1 por delante.

**Elegir esta opción si**: Consideras que la memoria es el componente más
estratégico del proyecto y merece ser la prioridad absoluta durante 1-2 meses,
aceptando que el resto del roadmap se desplaza en consecuencia.

---

### Tabla comparativa

| Criterio | Opción A (Express) | Opción B (Skeleton) ⭐ | Opción C (ACI Full) |
|----------|--------------------|----------------------|---------------------|
| Sesiones Opus 4.8 | 2-3 | 4-6 | 8-12 |
| Tiempo (aprox.) | 1 semana | 2 semanas | 4-6 semanas |
| Memoria funcionando | Sí | Sí | Sí |
| Contratos para Orchestrator | No (refactor luego) | Sí | Sí |
| Contratos para Hermes | No (refactor luego) | Sí | Sí |
| Vault legible | No | Opcional | Sí |
| Detección de patrones | No | No | Sí |
| Deuda técnica | Media (refactor en V1.0) | Muy baja | Muy baja |
| Bloquea V0.9 | No | No | Sí (parcialmente) |
| Recomendada | — | ⭐ | — |

---

## 6. RESTRICCIONES ARQUITECTÓNICAS PARA FABLE5 (INDEPENDIENTES DE LA OPCIÓN)

Estas restricciones aplican a cualquier opción elegida. Fable5 debe respetarlas:

### 6.1 Contratos de interfaz

La API pública de memoria (`/api/memory/*`) que Fable5 diseñe para V0.85 es un
**contrato congelado**. No puede cambiar en V0.9, V1.0 ni V1.1. Si es necesario
extenderla, se añaden endpoints nuevos, nunca se modifican los existentes.

Razón: los tests de contrato (patrón de Aithera desde V0.7.2) congelan los
endpoints públicos. Romperlos rompería los tests.

### 6.2 Separación de responsabilidades

```
Job de ingesta         →  solo escribe en ChromaDB
MemoryManager/Store    →  solo lee/escribe ChromaDB (sin lógica de negocio)
Endpoints /api/memory  →  solo orquestan, no saben de ChromaDB directamente
Chat endpoint          →  consulta memoria a través de la API interna, nunca ChromaDB directo
```

### 6.3 Modelo de fallos

El MOS debe fallar con la misma elegancia que el sistema actual. Si ChromaDB no está:
- El chat responde (sin contexto)
- El Hub muestra "memoria no disponible" con un mensaje claro
- Los endpoints de memoria devuelven 503 con detalle útil
- El backend NO crashea

### 6.4 Aislamiento de los jobs asyncio

Los jobs de ingesta y resumen NO pueden bloquear el event loop de FastAPI.
Deben usar `asyncio.create_task()` en el `lifespan` y manejar sus propias
excepciones. Un fallo en el job de ingesta no puede impedir que el chat responda.

### 6.5 Tests obligatorios

Fable5 debe incluir en su plan al menos:
- `test_memory_contracts.py`: contratos de los endpoints `/api/memory/*`
- `test_memory_ingestion.py`: verifica que la ingesta indexa correctamente
- `test_memory_context.py`: verifica que el contexto se inyecta en el chat
- `test_memory_briefing.py`: verifica el endpoint de briefing on-demand

---

## 7. CÓMO CONECTA V0.85 CON EL RESTO DEL ROADMAP

### Con V0.9 — Automation Engine

El Automation Engine necesita saber "qué ha pasado hoy" para generar el briefing
matinal. En V0.85 se construye el endpoint `/api/memory/briefing`. En V0.9 la
regla `daily_briefing` llama a ese endpoint — es una dependencia directa.

Si se elige Opción A, habrá que refactorizar `memory_manager.py` antes de V0.9.
Con Opciones B y C, el Automation Engine se engancha directamente.

### Con V1.0 — Orchestrator

El Orchestrator necesita consultar memoria para enriquecer el contexto antes de
planificar. Con Opción A: el Orchestrator accede a ChromaDB directamente (acoplado).
Con Opciones B y C: el Orchestrator recibe un `IMemoryStore` por inyección de
dependencias (desacoplado). Cambiar el backend de memoria no requiere tocar el
Orchestrator.

### Con V1.1 — Hermes Runtime

Hermes tiene su propio sistema de memoria (archivos Markdown, SQLite propio).
En V1.1 hay que crear un `AitheraMemoryProvider` que Hermes crea que es su
sistema de memoria, pero que internamente habla con el MOS de Aithera.

Con Opción A: ese adapter tiene que luchar contra `memory_manager.py` sin interfaz
formal → mucho pegamento.
Con Opciones B y C: el adapter envuelve `IMemoryStore` → implementación directa y
limpia. Ver `PROMPT_02_HERMES_INTEGRATION.md` para el diseño completo.

---

## 8. MISIÓN DE FABLE5

Con todo lo anterior, Fable5 debe producir un documento de diseño técnico para
V0.85 que incluya:

1. **Arquitectura detallada** de la opción elegida: diagramas de componentes,
   contratos de código (interfaces Python con docstrings), esquema de colecciones
   ChromaDB con campos de metadata.

2. **Nuevos modelos Alembic** si la opción elegida requiere tablas en PostgreSQL
   (por ejemplo, para tracking de jobs de ingesta o metadata de resúmenes).

3. **Plan de sprints** para la opción elegida, asumiendo sesiones de trabajo con
   Opus 4.8. Máximo granularidad: qué se hace en cada sesión, en qué orden, y
   qué se puede paralelizar.

4. **Criterios de cierre** por sprint: cómo saber que cada sprint está terminado
   (qué test pasa, qué endpoint responde qué, qué se puede demostrar).

5. **Actualización del ROADMAP** (`03_ROADMAP_ACTUALIZADO.md`): la sección V0.85
   debe reescribirse con el nivel de detalle de las secciones V0.7.2-3 y V0.8.

6. **Contrato de handoff a V0.9**: qué deja listo V0.85 que V0.9 puede asumir
   sin comprobaciones.

---

## 9. DOCUMENTOS DE CONTEXTO QUE FABLE5 DEBE LEER ANTES DE DISEÑAR

En orden de prioridad:

1. `CLAUDE.md` — estado real del repositorio, stack, decisiones de diseño §18
2. `PLAN_MAESTRO_2026/03_ROADMAP_ACTUALIZADO.md` — roadmap completo actualizado
3. `PLAN_MAESTRO_2026/06_GATEWAY_V08_DISENO.md` — patrón de diseño de referencia
4. `PLAN_MAESTRO_2026/FABLE5_PROMPTS/PROMPT_02_HERMES_INTEGRATION.md` — para
   entender cómo conectará el MOS con Hermes (V1.1)
5. `backend/app/memory/memory_manager.py` — código actual que hay que extender
6. `backend/app/main.py` — cómo se registran los componentes en el lifespan

---

*Documento creado: 2026-07-09 — Decisión de opción pendiente de confirmación del
usuario. Opción recomendada: B (MOS Skeleton).*
