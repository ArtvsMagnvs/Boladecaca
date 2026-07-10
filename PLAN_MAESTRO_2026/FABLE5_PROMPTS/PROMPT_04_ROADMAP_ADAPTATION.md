# PROMPT DEFINITIVO PARA FABLE5 — ADAPTACIÓN DEL ROADMAP V0.9/V1.0/V1.1 AL NUEVO MOS

> **Propósito**: Fable5 debe reescribir completamente las especificaciones de V0.9
> (Automation Engine), V1.0 (Orchestrator) y V1.1 (Hermes Runtime) para que encajen
> con el nuevo modelo de memoria (MOS) diseñado en PROMPT_01, PROMPT_02 y PROMPT_03.
>
> Este documento identifica qué cambia en cada fase, qué integración con el MOS se
> requiere, y cómo deben actualizarse las especificaciones técnicas existentes.
>
> **Qué debe entregar Fable5**: versiones reescritas de las secciones V0.9, V1.0 y
> V1.1 del roadmap, con el nivel de detalle de las secciones V0.7.2-3 y V0.8 actuales.
> También debe entregar el nuevo `03_ROADMAP_ACTUALIZADO.md` completo.

---

## 1. CONTEXTO — LO QUE HAY QUE ADAPTAR

El roadmap actual (`PLAN_MAESTRO_2026/03_ROADMAP_ACTUALIZADO.md`) fue escrito antes
de definir el MOS. Las secciones V0.9, V1.0 y V1.1 asumen una memoria "informal" —
básicamente ChromaDB sin contratos formales. Con el MOS diseñado en los otros
prompts, esas secciones quedan incompletas o directamente incorrectas.

Lo que cambia fundamentalmente:
- **V0.9** asumía acceso ad-hoc a la memoria. Ahora debe usar `Memory API` y `Context API`.
- **V1.0** asumía que el Orchestrator inyecta contexto "de alguna forma". Ahora ese
  "de alguna forma" tiene nombre: `IMemoryStore.context()` + `Decision API`.
- **V1.1** asumía que Hermes "tendrá su propia memoria sincronizada". Ahora está claro
  que Hermes NO tiene memoria propia — usa `AitheraMemoryProvider`.

---

## 2. ADAPTACIÓN DE V0.9 — AUTOMATION ENGINE

### 2.1 Especificación actual (qué hay en el roadmap hoy)

```
V0.9 — Automation Engine + Approval Gates
- APScheduler + AutomationRule + AutomationExecution
- Acciones: telegram_message, email_summary, agent_task, chat_query
- Sistema de aprobaciones + UI
- Reglas predefinidas: daily_briefing, system_monitor, email_summary
- Checkpointing: agent_executions.checkpoint_data
```

### 2.2 Qué cambia con el MOS

**El briefing matinal**: en el roadmap actual se describe como "digest de email (V0.7.3)
+ agenda + tareas del día". Con el MOS de V0.85, el briefing no llama a Gmail en
caliente — recupera información ya indexada en `Private Memory` vía `Context API`.

**Fable5 debe redefinir la regla `daily_briefing`** de la siguiente forma:

```python
# ANTES (sin MOS):
async def daily_briefing():
    emails = await gmail_api.get_recent()  # llamada a red en caliente
    events = await calendar_api.get_today()  # llamada a red en caliente
    return summarize(emails + events)

# DESPUÉS (con MOS V0.85):
async def daily_briefing():
    # La memoria ya tiene los datos indexados del job de ingesta de V0.85
    context = await memory_api.context(
        query="emails importantes y eventos de hoy",
        max_tokens=2000,
        sources=["mem_conversational", "mem_personal"]
    )
    summary = await ai_manager.generate(prompt=BRIEFING_TEMPLATE, context=context)
    return summary
```

**Automation Memory**: cada automatización ejecutada, con su resultado y su contexto,
debe almacenarse en `Automation Memory` (nivel interno del MOS). Esto permite que el
CIE detecte en el futuro qué automatizaciones son más efectivas.

**Approval Gates + Decision API**: cuando el usuario aprueba o rechaza una propuesta
del Automation Engine, esa decisión debe almacenarse en `Decision API`. Esto construye
la "memoria de automatizaciones": el sistema recuerda qué tipos de automatizaciones
el usuario suele aprobar y puede aprender a proponer automáticamente las correctas.

```python
# Al aprobar una automatización:
await decision_api.storeDecision(
    decision=f"Aprobar automatización: {automation.name}",
    reason=user_approval_note,
    alternatives=[],
    project=None
)
```

### 2.3 Nuevas integraciones de V0.9 con el MOS

| Punto de integración | API del MOS usada | Propósito |
|---------------------|-------------------|-----------|
| Briefing matinal | `Context API.buildContext()` | Obtener contexto sin llamadas en caliente |
| Resultado de automatización | `Memory API.add(type=AUTOMATION)` | Construir historial de automatizaciones |
| Aprobación de usuario | `Decision API.storeDecision()` | Aprender preferencias del usuario |
| Error en automatización | `Memory API.add(type=ERROR)` | Construir base de errores |
| Patrón detectado | `Skill API.create()` | Convertir patrón en skill reutilizable |

### 2.4 Lo que NO cambia en V0.9

- APScheduler sigue siendo el scheduler (llega en V0.9, no en V0.85)
- Los approval gates funcionan igual
- El checkpointing en `agent_executions` no cambia
- Las 4 acciones básicas (telegram_message, email_summary, agent_task, chat_query)
  no cambian — solo la fuente de datos del briefing
- Los modelos Alembic `AutomationRule` y `AutomationExecution` no cambian

### 2.5 Misión de Fable5 para V0.9

Reescribir la sección V0.9 del roadmap incluyendo:
1. Cómo las reglas predefinidas usan el MOS en lugar de llamadas en caliente
2. El nuevo flujo de `daily_briefing` con `Context API`
3. La integración con `Decision API` para el aprendizaje de preferencias
4. Los tests de integración MOS ↔ Automation Engine

---

## 3. ADAPTACIÓN DE V1.0 — ORCHESTRATOR

### 3.1 Especificación actual

```
V1.0 — Orchestrator
- Intent Analyzer (modelo barato siempre)
- Task Planner (modelo potente si se necesita)
- Response Builder
- Claude Code Agent
- Tabla orchestrator_traces
- Routing por complejidad
- Sin LangChain/LangGraph/CrewAI
```

### 3.2 Qué cambia con el MOS

**Inyección de contexto**: el Orchestrator debe enriquecer cada query del usuario con
contexto del MOS antes de pasarla al Intent Analyzer. En el roadmap actual esto no
está especificado. Con el MOS:

```
Usuario: "¿Qué debo hacer con el email de Miguel sobre el presupuesto?"
    ↓
Context API.buildContext("email Miguel presupuesto", max_tokens=800)
    ↓ (retorna: historial de conversaciones sobre Miguel, emails recientes, proyectos relacionados)
Intent Analyzer recibe: query + contexto enriquecido
    ↓
...
```

**Decision API en el Orchestrator**: cada decisión de planificación debe quedar
registrada. Esto construye la base de datos de decisiones de Aithera:

```python
# Al seleccionar plan:
await decision_api.storeDecision(
    decision=f"Plan seleccionado: {plan.name} para intent {intent.type}",
    reason=f"Score: {plan.score}, alternativas evaluadas: {len(plans)}",
    alternatives=[p.name for p in plans if p != plan],
    project=current_project
)
```

**`orchestrator_traces` → se amplía**: la tabla de trazas existente debe incluir
los IDs de las queries a `Context API` y `Decision API`, para poder reconstruir
qué información de la memoria influyó en cada decisión del Orchestrator.

**AgentRuntime desde V1.0**: aunque Hermes no llega hasta V1.1, la interfaz
`AgentRuntime` (ver PROMPT_02) debe definirse en V1.0. El Orchestrator usará
`NullRuntime` (que solo ejecuta el flujo de chat actual) hasta V1.1.

```python
# V1.0: Orchestrator usa AgentRuntime pero con NullRuntime
class NullRuntime(AgentRuntime):
    """Runtime de compatibilidad. Delega en el chat handler actual."""
    capabilities = {"chat", "tool_use_basic"}
    
    async def execute_task(self, task, memory, tools, approval_gate):
        # Usa el flujo actual de chat + tool execution
        return await current_chat_flow(task.query, memory, tools)
```

### 3.3 El Orchestrator como cliente del MOS — flujo completo

```
Query del usuario
    ↓
[1] Context API.buildContext(query) → contexto enriquecido
    ↓
[2] Intent Analyzer (modelo barato + contexto) → intent
    ↓
[3] if intent.needs_planning:
        Task Planner (modelo potente) → plan
        Decision API.storeDecision(plan) → decision_id
    ↓
[4] Para cada paso del plan:
        a. Memory API.search(step.query) → memoria relevante
        b. AgentRuntime.execute_task(step, memory, tools) → resultado
        c. Memory API.add(result, type=CONVERSATIONAL) → indexar resultado
    ↓
[5] Response Builder → respuesta al usuario
    ↓
[6] orchestrator_traces: loguear con context_query_id + decision_id
```

### 3.4 Nuevas integraciones de V1.0 con el MOS

| Punto de integración | API del MOS usada | Propósito |
|---------------------|-------------------|-----------|
| Enriquecimiento de query | `Context API.buildContext()` | El Orchestrator tiene contexto antes de decidir |
| Decisión de planificación | `Decision API.storeDecision()` | Historia de decisiones del Orchestrator |
| Resultado de ejecución | `Memory API.add(type=CONVERSATIONAL)` | Indexar qué hizo el Orchestrator |
| Error de ejecución | `Memory API.add(type=ERROR)` | Aprender de fallos |
| Skill detectada | `Skill API.create()` | Extraer skills de tareas exitosas |

### 3.5 Lo que NO cambia en V1.0

- Intent Analyzer usa siempre el modelo más barato (Ollama > MiniMax > resto)
- Task Planner solo para intents complejos
- Sin LangChain ni frameworks externos
- `orchestrator_traces` como tabla (se amplía, no se reemplaza)
- Claude Code Agent como caso especial de AgentRuntime

### 3.6 Misión de Fable5 para V1.0

Reescribir la sección V1.0 incluyendo:
1. El flujo completo del Orchestrator con el MOS (sección 3.3)
2. La definición formal de `AgentRuntime` e `NullRuntime`
3. Las ampliaciones a `orchestrator_traces` (nuevas columnas)
4. Los tests de integración MOS ↔ Orchestrator
5. La especificación de cuándo el Orchestrator decide usar memoria vs. llamada directa

---

## 4. ADAPTACIÓN DE V1.1 — HERMES RUNTIME

### 4.1 Especificación actual

```
V1.1 — Hermes como sistema de agentes principal
- Hermes (Nous Research) bajo el Orchestrator
- El Orchestrator delega en Hermes
- Skills/memoria de Hermes ↔ memoria de Aithera (sin definir)
- Estado: "pendiente de diseño"
```

### 4.2 Qué cambia con el MOS (ahora totalmente definido)

La sección "Skills/memoria de Hermes ↔ memoria de Aithera (sin definir)" ya está
definida en PROMPT_02 y PROMPT_03. Fable5 debe incorporarla:

**Los 4 adapters son el corazón de V1.1**:
```
HermesRuntime
├── AitheraMemoryProvider    → IMemoryStore → ChromaDB/Qdrant
├── AitheraSkillProvider     → ISkillStore → Skill Engine
├── AitheraToolProvider      → ToolManager (con whitelist + approval gates)
└── AitheraContextProvider   → Context API
```

**Hermes Desktop como herramienta de ingeniería**: queda explicitado que Hermes
Desktop sigue siendo útil para el desarrollador (para entender cómo Hermes procesa
tasks internamente y depurar los adapters). No es la interfaz del usuario.

**Skill Memory se activa completamente**: en V0.85 y V1.0, la Skill Memory es básica
(ChromaDB, sin Skill Engine completo). En V1.1, el `AitheraSkillProvider` activa el
Skill Engine completo: detección automática de skills por Hermes, versionado, ciclo
de vida completo (DETECTED → DRAFT → VALIDATED → LOCAL).

**Working Memory (Letta) se incorpora**: en V1.1, cada instancia de `HermesRuntime`
tiene su propia Working Memory (estado de sesión) implementada sobre Letta. Letta
es transparente para el Orchestrator — es un detalle interno del `HermesRuntime`.

### 4.3 El flujo completo Orchestrator → Hermes → MOS

```
Orchestrator recibe intent complejo (planning + tool_use + reflection)
    ↓
Orchestrator.execute(task, runtime=HermesRuntime)
    ↓
HermesRuntime.execute_task(task, memory=IMemoryStore, tools=ToolManager)
    ↓
Hermes (internamente):
    [1] AitheraContextProvider.get_context(task.query)
        → recupera contexto del MOS (Private Memory + Project Memory)
    [2] Razonamiento + planificación interna de Hermes
    [3] AitheraSkillProvider.list_skills()
        → Hermes ve las skills de Aithera como suyas
    [4] AitheraToolProvider.execute_tool(tool, params)
        → pasa por whitelist + approval_gate de Aithera
    [5] Reflexión interna de Hermes
    [6] AitheraMemoryProvider.save(resultado, metadata)
        → el aprendizaje de Hermes va al MOS, no a sus propios archivos
    ↓
HermesRuntime devuelve AgentResult al Orchestrator
    ↓
Orchestrator indexa el resultado en Memory API
    ↓
Response Builder → usuario
```

### 4.4 Nuevas integraciones de V1.1 con el MOS

| Punto de integración | Mecanismo | API del MOS |
|---------------------|-----------|-------------|
| Hermes lee contexto | AitheraContextProvider | `Context API.get_context()` |
| Hermes ve skills | AitheraSkillProvider | `Skill API.list()`, `Skill API.execute()` |
| Hermes usa tools | AitheraToolProvider | `ToolManager + ApprovalGate` |
| Hermes guarda aprendizaje | AitheraMemoryProvider | `Memory API.add()` |
| Hermes crea skill nueva | AitheraSkillProvider | `Skill API.create()` |
| Hermes mejora skill | AitheraSkillProvider | `Skill API.improve()` |

### 4.5 Lo que NO cambia en V1.1

- El Orchestrator sigue siendo el cerebro — decide qué va a Hermes y qué no
- Los approval gates siguen funcionando (ahora encapsulados en AitheraToolProvider)
- Hermes nunca tiene acceso directo a la BD, al filesystem ni a las colecciones ChromaDB
- El principio de whitelist sigue vigente para todas las tools

### 4.6 Misión de Fable5 para V1.1

Reescribir la sección V1.1 incluyendo:
1. El flujo completo Orchestrator → Hermes → MOS (sección 4.3)
2. Los 4 adapters con especificación técnica completa
3. La incorporación de Working Memory (Letta) como detalle interno
4. El plan de investigación previa (ver PROMPT_02 sección 7)
5. El plan de contingencia si Hermes no tiene API de providers
6. Los criterios de cierre de V1.1

---

## 5. EL NUEVO ROADMAP COMPLETO

Fable5 debe producir una nueva versión de `03_ROADMAP_ACTUALIZADO.md` que integre
todos los cambios. La estructura del nuevo roadmap:

```
# Roadmap actualizado — V0.85 → V2.0+

## V0.85 — Memory Operating System Skeleton
[Basado en PROMPT_01, opción elegida por el usuario]

## V0.9 — Automation Engine + Approval Gates
[Sección adaptada: usa MOS para briefing, Decision API para aprendizaje]

## V1.0 — Orchestrator
[Sección adaptada: AgentRuntime interface, Context API para enriquecimiento,
 Decision API para trazas, NullRuntime como implementación inicial]

## V1.1 — Hermes Runtime
[Sección reescrita completamente: adapters, flujo completo, Letta, Skill Engine]

## V1.2 — MCP Interoperability
[Sin cambios mayores: AitheraToolProvider ya gestiona MCP]

## V1.4/V1.5 — Hub Visual Avanzado + Project Memory
[Añadir: activación de Project Memory (Capa 2 del MOS)]

## V2.0+ — MOS Completo + GSN + CIE + Guardians
[Nueva sección: basada en PROMPT_03]

## Tabla resumen
[Actualizada con todas las versiones]

## Mapa de evolución del MOS
[Nueva sección: qué capas del MOS están activas en cada versión]
```

### Mapa de evolución del MOS por versión

Fable5 debe incluir esta tabla en el nuevo roadmap:

| Componente MOS | V0.85 | V0.9 | V1.0 | V1.1 | V1.2 | V1.4 | V2.0+ |
|----------------|-------|------|------|------|------|------|-------|
| Conversational Memory | ✅ ChromaDB | ✅ | ✅ | ✅ Qdrant | ✅ | ✅ | ✅ |
| Working Memory | ❌ | ❌ | ❌ | ✅ Letta (en Hermes) | ✅ | ✅ | ✅ |
| Semantic Memory | ✅ básico | ✅ | ✅ | ✅ + Qdrant | ✅ | ✅ | ✅ |
| Episodic Memory | ❌ stub | ❌ | ❌ | ✅ Graphiti | ✅ | ✅ | ✅ |
| Knowledge Engine | ❌ stub | ❌ | ❌ | ❌ | ✅ Cognee | ✅ | ✅ |
| Decision Memory | ✅ PostgreSQL | ✅ | ✅ + KuzuDB | ✅ | ✅ | ✅ | ✅ |
| Error Memory | ✅ básico | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Skill Memory | ✅ básico | ✅ | ✅ | ✅ completo | ✅ | ✅ | ✅ |
| Context Memory | ✅ básico | ✅ | ✅ | ✅ Mem0 | ✅ | ✅ | ✅ |
| **Private Memory** | ✅ local | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Project Memory** | ❌ stub | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Global Skill Network** | ❌ stub | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Collective Intelligence** | ❌ stub | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Guardians** | ❌ stub | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 6. DEPENDENCIAS ENTRE DOCUMENTOS — ORDEN DE LECTURA PARA FABLE5

Los 4 prompts forman un sistema coherente. Fable5 debe leerlos en este orden:

```
PROMPT_01 (MOS V0.85 Skeleton)
    ↓ define los contratos base que todo lo demás usa
PROMPT_03 (MOS Full Architecture)
    ↓ define la visión completa que los contratos deben soportar
PROMPT_02 (Hermes Integration)
    ↓ define cómo Hermes usa el MOS via adapters
PROMPT_04 (Este documento — Roadmap Adaptation)
    ↓ integra todo en versiones concretas del roadmap
```

Y estos son los documentos existentes que también debe leer:

```
CLAUDE.md                           → estado real del código
03_ROADMAP_ACTUALIZADO.md           → roadmap que debe reescribirse
06_GATEWAY_V08_DISENO.md            → referencia de patrón de diseño
backend/app/memory/memory_manager.py → código que hay que extender
backend/app/tools/tool_manager.py   → referencia de cómo funciona la whitelist
backend/app/ai/ai_manager.py        → referencia del patrón multi-proveedor
```

---

## 7. CRITERIOS DE COHERENCIA — LO QUE FABLE5 DEBE VERIFICAR

Antes de entregar los documentos, Fable5 debe verificar:

1. **Contratos consistentes**: la `IMemoryStore` de PROMPT_01 debe ser la misma
   que usa el Orchestrator en V1.0 y los adapters de Hermes en V1.1.

2. **Sin rotura hacia atrás**: los endpoints `/api/memory/*` definidos en V0.85
   no pueden cambiar en V0.9, V1.0 ni V1.1. Solo se añaden endpoints nuevos.

3. **Sin saltos tecnológicos en una misma versión**: si V1.1 introduce Qdrant Y
   Letta Y Graphiti Y Mem0 a la vez, es demasiado. Fable5 debe priorizar y escalonar.

4. **Approval gates preservados**: en todas las versiones, ninguna herramienta
   puede ejecutarse sin pasar por el approval gate correspondiente. Los adapters
   de Hermes en V1.1 no pueden saltarse esta restricción.

5. **Hermes invisible en el Hub**: el usuario nunca ve "Hermes" en la interfaz.
   Ve las capacidades de Aithera. Fable5 debe verificar que ningún texto de la
   UI mencione Hermes directamente.

---

## 8. MISIÓN COMPLETA DE FABLE5 PARA ESTE DOCUMENTO

Entregables esperados:

1. **`03_ROADMAP_ACTUALIZADO.md` reescrito** — versión completa del roadmap
   que integra MOS, V0.85, adaptación de V0.9/V1.0/V1.1 y visión V2.0+.

2. **Sección V0.9 reescrita** — con flujo de briefing usando `Context API`,
   integración con `Decision API` para aprendizaje de preferencias, y tabla
   de integraciones MOS ↔ Automation Engine.

3. **Sección V1.0 reescrita** — con flujo completo del Orchestrator usando MOS,
   definición de `AgentRuntime` e `NullRuntime`, ampliaciones a `orchestrator_traces`.

4. **Sección V1.1 reescrita** — completa, con los 4 adapters, flujo completo
   Orchestrator → Hermes → MOS, Letta como Working Memory, plan de investigación
   previa y criterios de cierre.

5. **Nueva sección V2.0+** — basada en PROMPT_03: GSN, CIE, Guardians.

6. **Mapa de evolución del MOS** — tabla de qué componentes están activos en
   cada versión (sección 5 de este documento).

7. **Detección de conflictos**: si Fable5 detecta alguna contradicción entre
   los 4 prompts, debe documentarla y proponer la resolución, no ignorarla.

---

*Documento creado: 2026-07-09. Leer junto a PROMPT_01, PROMPT_02 y PROMPT_03.
Este es el documento de integración: une el diseño del MOS (03) con los adapters
de Hermes (02) con el skeleton inicial (01) en un roadmap coherente y ejecutable.*
