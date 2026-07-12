# 10 — RFC: Integración de Hermes (V1.1) e interfaz AgentRuntime (V1.0)

> **Origen**: `FABLE5_PROMPTS/PROMPT_02_HERMES_INTEGRATION.md`.
> **Decisión inviolable**: Hermes NO es el núcleo de Aithera. Es un motor
> intercambiable — el mismo patrón que los 8 proveedores IA del AIManager, aplicado
> a runtimes de agentes. Hermes piensa; Aithera recuerda y decide qué se ejecuta.
> **Hermes es invisible para el usuario**: ni un solo texto de UI lo menciona.

---

## 1. La interfaz `AgentRuntime` (se define en V1.0, no en V1.1)

```
Orchestrator → AgentRuntime → [ NullRuntime (V1.0) | HermesRuntime (V1.1) | futuros ]
```

```python
# backend/app/tie/runtime.py (V1.0)
# [Δ 2026-07-12: el módulo se llama app/tie/ — doc 14; "orchestrator" es el
#  nombre histórico del pipeline v1. Nada más de este RFC cambia.]
class AgentRuntime(ABC):
    """El Orchestrator SOLO depende de esta interfaz. Un runtime recibe memoria,
    tools y gate DE AITHERA por inyección — jamás gestiona los suyos propios."""

    @abstractmethod
    async def execute_task(self, task: AgentTask, memory: IMemoryStore,
                           tools: ToolManager, approval_gate: ApprovalGate) -> AgentResult: ...

    @abstractmethod
    async def stream_task(self, task, memory, tools, approval_gate) -> AsyncIterator[AgentChunk]: ...

    @abstractmethod
    async def health_check(self) -> RuntimeHealth: ...

    @property
    @abstractmethod
    def capabilities(self) -> set[str]:
        """p.ej. {"planning","reflection","skill_generation","tool_use"} —
        el Orchestrator enruta tareas según esto."""
```

Contratos acompañantes (formato tentativo; los campos exactos de `AgentTask` se
cierran tras la investigación §4 — **[pendiente de investigación de Hermes API]**):

```python
@dataclass AgentTask:    id, instruction, context (str del Context API), plan_step_id,
                         constraints (timeout_s, max_tool_calls), metadata
@dataclass AgentResult:  task_id, success, output, tool_calls (list), tokens, duration_ms,
                         learned (list[str] — candidatos a memoria/skill), error
@dataclass AgentChunk:   task_id, kind ("text"|"tool_call"|"status"), payload
@dataclass RuntimeHealth: available, detail, latency_estimate_ms, model_loaded
class ApprovalGate:      request(description, tool, params) -> awaitable resolución
                         (implementado en V0.9 — doc 11; el runtime lo RECIBE, no lo crea)
```

`NullRuntime` (V1.0): capabilities `{"chat","tool_use_basic"}`; `execute_task`
delega en el `chat_service` actual + ejecución simple de tools. Es la implementación
que hace V1.0 completo sin Hermes.

## 2. Los 4 adapters (V1.1) — `backend/app/hermes/providers/`

Principio: **no modificar el núcleo de Hermes; sustituir solo sus providers.**
Hermes cree que usa sus sistemas nativos; todo pasa por Aithera.

| Adapter | Implementa (lado Hermes) | Delega en (lado Aithera) | Regla |
|---|---|---|---|
| `AitheraMemoryProvider` | memory provider (`save/retrieve`) | `IMemoryStore` (`store/search`) | Hermes nunca sabe que existe ChromaDB; sus saves llevan `source="hermes"` |
| `AitheraSkillProvider` | skill provider (`save/load/list`) | `LocalSkillLibrary` (doc 09) | las skills que Hermes detecta/genera entran como `DETECTED/DRAFT` en la LSL — pertenecen a Aithera |
| `AitheraToolProvider` | tool provider (`execute_tool`) | `ToolManager` + `ApprovalGate` | whitelist + gates SIEMPRE; Hermes jamás ejecuta directo (principio 5 AOS) |
| `AitheraContextProvider` | context provider (`get_context`) | `Context API` (`context()`) | contexto con atribución de fuente, presupuesto de tokens |

Working Memory (estado de sesión): detalle INTERNO de `HermesRuntime` (Letta como
candidato, 08 RFC-006). El Orchestrator no la ve; se destruye al cerrar la tarea;
lo aprendido persiste solo vía `AitheraMemoryProvider`.

## 3. Flujo completo Orchestrator → Hermes → MOS

```
intent complejo (planning+reflection) → Orchestrator elige HermesRuntime por capabilities
  → HermesRuntime.execute_task(task, memory, tools, gate)
      [1] ContextProvider.get_context(task)      ← MOS
      [2] razonamiento/planificación interna de Hermes
      [3] SkillProvider.list()                   ← LSL (las ve como suyas)
      [4] ToolProvider.execute_tool(...)         ← whitelist + approval gate
      [5] reflexión interna
      [6] MemoryProvider.save(aprendizaje)       → MOS (nunca a archivos propios)
  → AgentResult → Orchestrator indexa resultado + trace → Response Builder → usuario
```

## 4. Investigación previa a V1.1 (sprint H0 — obligatorio antes de codificar)

Preguntas a responder con docs/repo/prueba local de Hermes Desktop:

1. ¿Cómo se instancia? (lib Python / servidor local / API REST) → determina lifespan.
2. ¿Expone API de providers formal o requiere ingeniería inversa?
3. Licencia: ¿permite esta integración? ¿restricciones?
4. ¿Requiere internet / llama a APIs de Nous? → privacidad y disponibilidad.
5. ¿Puede usar el AIManager de Aithera como proveedor de LLM?
6. Huella de RAM/CPU junto a ChromaDB + sentence-transformers en un PC personal.

Entregable de H0: informe + decisión GO/NO-GO + cierre de los campos
`[pendiente de investigación]` de este RFC. Hermes Desktop = herramienta de
ingeniería del desarrollador en V1.0-V1.1; jamás interfaz del usuario final.

## 5. Sprints de V1.1 (si H0 = GO)

| Sprint | Contenido | Cierre |
|---|---|---|
| H0 | investigación (§4) | informe + GO/NO-GO |
| H1 | `HermesRuntime(AgentRuntime)` esqueleto + arranque/parada en lifespan + health | `health_check()` OK; tarea trivial e2e |
| H2 | `AitheraMemoryProvider` + `AitheraContextProvider` + tests de aislamiento | Hermes ejecuta usando memoria de Aithera **sin escribir en ningún archivo propio** (criterio de cierre de fase) |
| H3 | `AitheraToolProvider` (gates) + `AitheraSkillProvider` (LSL) | tool con approval pasa por el gate; skill detectada aparece en LSL como DRAFT |
| H4 | routing por capabilities en el Orchestrator + LSL completa (doc 09) + panel "aprendido" | tareas complejas → Hermes; simples → NullRuntime; 0 menciones a "Hermes" en UI |

## 6. Plan de contingencia (si H0 = NO-GO)

Si Hermes no expone providers, su licencia no lo permite o su huella es inviable:

- **La arquitectura no cambia**: `AgentRuntime` y los contratos quedan.
- Plan B1: **wrapper de proceso** — Hermes como subproceso con I/O interceptado
  (adapters a nivel de filesystem/API en vez de providers). Más pegamento, misma
  garantía: el conocimiento acaba en el MOS.
- Plan B2: **`AitheraNativeRuntime`** — construir en V1.2+ las 4 capacidades clave
  (planner, reflection, skill detection vía LLL, context builder) de forma nativa;
  el LLL (doc 09) ya cubre parte del learning loop.
- Plan B3: otro runtime OSS del landscape (evaluar contra los mismos 6 puntos de §4).

En los tres casos, V1.0 ya es un producto completo con `NullRuntime` — Hermes es
mejora, no dependencia (regla de autosuficiencia).

## 7. Futuro

- V1.2: multi-instancia (`Research/Coding/CalendarHermesRuntime`) — perfiles
  distintos, MISMO MOS; comparten conocimiento, no conversaciones. MCP entra por
  `AitheraToolProvider` (Hermes ve tools MCP como tools de Aithera).
- V1.4/1.5: Hermes 100% invisible; Hermes Desktop deja de usarse.
- Si Aithera supera a Hermes: `AitheraNativeRuntime` se registra, se migra tráfico
  gradualmente, Hermes queda de fallback. No se pierde nada: todo vive en el MOS.

---
*Diseño 2026-07-09 (Fable 5). Depende de: 07/08 (MOS), 09 (LSL), 11 (ApprovalGate,
Orchestrator). Los campos marcados [pendiente] se cierran en el sprint H0.*
