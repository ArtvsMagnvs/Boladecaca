# PROMPT DEFINITIVO PARA FABLE5 — AUTOMATION ENGINE Y ORCHESTRATOR (DISEÑO COMPLETO)

> **Propósito**: Diseñar el Automation Engine (V0.9) y el Orchestrator (V1.0) a la
> altura arquitectónica del resto del sistema. El objetivo no es construir el sistema
> más complejo posible en V0.9/V1.0 — es construir el MEJOR DISEÑO POSIBLE con la
> implementación MÍNIMA FUNCIONAL en cada versión.
>
> **Regla fundamental**: V1.0 debe ser un sistema completo y usable. No significa
> "ya tiene todo" ni "todo lo que tiene está al máximo". Significa que Aithera
> funciona al completo en modo básico. De V1.0 a V2.0 se potencia. De V2.0 a V3.0
> se lleva al límite. Entrar en bucles de sobreingeniería antes de V1.0 no tiene sentido.

---

## 1. AUTOMATION ENGINE — VISIÓN COMPLETA

### 1.1 Qué es un buen Automation Engine

El Automation Engine actual en el roadmap es funcional pero básico: APScheduler +
reglas simples + approval gate. Eso está bien para V0.9. Pero el diseño de la
arquitectura debe ser capaz de soportar la visión completa sin reescrituras.

**La visión completa** (no necesariamente para V0.9, pero sí el diseño):

Un buen Automation Engine no es un cron glorificado. Es un **sistema reactivo**
capaz de responder a eventos, condiciones complejas y patrones aprendidos. La
diferencia entre un cron y un Automation Engine real:

```
CRON (lo que tenemos ahora):
"Cada día a las 8am → ejecuta briefing"

AUTOMATION ENGINE REAL:
"Cuando Miguel Fernández envía un email marcado como urgente por el triaje
 Y no hay reunión en el calendario en las próximas 2 horas
 Y el assistant está en modo disponible
 → notificar por Telegram con resumen del email
 → sugerir bloquear 30 minutos en el calendario"
```

### 1.2 Arquitectura completa del Automation Engine

#### Capa 1: Trigger System (de dónde vienen los eventos)

```python
class Trigger(ABC):
    """Un trigger detecta una condición y emite un TriggerEvent."""
    
    @abstractmethod
    async def evaluate(self, context: AutomationContext) -> TriggerEvent | None:
        ...

# Implementaciones:
class ScheduleTrigger(Trigger):     # "cada día a las 8am"
class EventTrigger(Trigger):        # "cuando llega un email urgente"
class ConditionTrigger(Trigger):    # "cuando hay >10 emails sin leer"
class PatternTrigger(Trigger):      # "cuando detecto que el usuario está bloqueado"
class WebhookTrigger(Trigger):      # "cuando llega un evento externo"
class MemoryTrigger(Trigger):       # "cuando el MOS detecta un patrón nuevo"
```

#### Capa 2: Condition Engine (filtros antes de actuar)

```python
class Condition(ABC):
    async def evaluate(self, event: TriggerEvent, context: AutomationContext) -> bool:
        ...

# Condiciones compuestas (AND, OR, NOT):
class AndCondition(Condition):   # todas las subcondiciones deben ser True
class OrCondition(Condition):    # al menos una subcondición debe ser True
class NotCondition(Condition)    # inversión
class TimeWindowCondition(Condition)    # "solo entre las 9am y las 9pm"
class CooldownCondition(Condition)      # "no más de una vez cada 5 minutos"
class UserStateCondition(Condition)     # "solo cuando el usuario está disponible"
```

#### Capa 3: Action System (qué hace la automatización)

```python
class Action(ABC):
    async def execute(self, event: TriggerEvent, context: AutomationContext, 
                      approval_gate: ApprovalGate) -> ActionResult:
        ...

# Acciones básicas (V0.9):
class TelegramMessageAction(Action)     # enviar mensaje por Telegram
class EmailSummaryAction(Action)        # resumen de email
class ChatQueryAction(Action)           # hacer una pregunta al chat
class AgentTaskAction(Action)           # ejecutar un agente

# Acciones avanzadas (V1.x+):
class MemoryUpdateAction(Action)        # actualizar memoria directamente
class SkillExecutionAction(Action)      # ejecutar una skill de la LSL
class CalendarBlockAction(Action)       # bloquear tiempo en calendario
class ChainedRuleAction(Action)         # disparar otra regla como output
```

#### Capa 4: Learning Layer (aprende del feedback del usuario)

```python
class AutomationLearner:
    """
    Aprende de las aprobaciones y rechazos del usuario.
    Ajusta el weight de condiciones y sugiere nuevas reglas.
    """
    
    async def record_feedback(self, rule: AutomationRule, approved: bool, 
                               note: str | None):
        """Cada aprobación/rechazo actualiza el modelo interno."""
        ...
    
    async def suggest_new_rule(self, memory: IMemoryStore) -> RuleProposal | None:
        """Basado en patrones de la memoria, propone una nueva regla."""
        ...
    
    async def suggest_rule_improvement(self, rule: AutomationRule) -> RuleImprovement | None:
        """Detecta si una regla tiene baja tasa de aprobación y propone mejora."""
        ...
```

### 1.3 Lo que se implementa en V0.9 (MVP)

V0.9 implementa el mínimo funcional con la arquitectura correcta:

**Implementado en V0.9**:
- `ScheduleTrigger` y `EventTrigger` (email urgente, calendario)
- `CooldownCondition` y `TimeWindowCondition`
- Las 4 acciones básicas (Telegram, email, chat, agent)
- `ApprovalGate` (ya diseñado)
- Checkpointing en `agent_executions`
- Reglas predefinidas: `daily_briefing`, `system_monitor`, `urgent_email_alert`
- Integración básica con MOS: briefing usa `Context API` (ver PROMPT_04)

**Stubs en V0.9 (interfaz definida, implementación vacía)**:
- `PatternTrigger` → `raise NotImplementedError("V1.2+")`
- `MemoryTrigger` → `raise NotImplementedError("V1.2+")`
- `AutomationLearner` → `raise NotImplementedError("V1.x+")`
- `ChainedRuleAction` → `raise NotImplementedError("V1.x+")`

**No implementado, no definido como stub en V0.9**:
- Rule chaining visual (UI de V1.x)
- Natural language rule creation (V1.x)
- Webhook triggers externos (V1.x)

### 1.4 Tabla de evolución del Automation Engine

| Feature | V0.9 | V1.0 | V1.2 | V2.0+ |
|---------|------|------|------|-------|
| ScheduleTrigger | ✅ | ✅ | ✅ | ✅ |
| EventTrigger (email/calendario) | ✅ | ✅ | ✅ | ✅ |
| ConditionEngine básico | ✅ | ✅ | ✅ | ✅ |
| 4 acciones básicas | ✅ | ✅ | ✅ | ✅ |
| ApprovalGate | ✅ | ✅ | ✅ | ✅ |
| Integración MOS (Context API) | ✅ | ✅ | ✅ | ✅ |
| PatternTrigger (LLL) | ❌ | ❌ | ✅ | ✅ |
| MemoryTrigger | ❌ | ❌ | ✅ | ✅ |
| AutomationLearner | ❌ | ❌ | ✅ | ✅ |
| Rule chaining | ❌ | ❌ | ✅ | ✅ |
| Natural language rules | ❌ | ❌ | ❌ | ✅ |
| Self-optimization | ❌ | ❌ | ❌ | ✅ |

---

## 2. ORCHESTRATOR — VISIÓN COMPLETA

### 2.1 Qué es un buen Orchestrator

El Orchestrator actual en el roadmap (V1.0) es un Intent Analyzer + Task Planner.
Eso está bien como punto de partida. Pero el diseño completo es más rico.

Un buen Orchestrator no es un "if-else glorificado" sobre el tipo de intent. Es un
**sistema de razonamiento distribuido** que descompone tareas complejas en subtareas,
las asigna a los mejores ejecutores disponibles, gestiona el estado de ejecución,
maneja fallos con gracia y aprende de sus propias decisiones.

### 2.2 Arquitectura completa del Orchestrator

#### Componente 1: Intent Classifier

```
Query: "Necesito preparar la reunión del jueves con el equipo de Hermes"
    ↓
Intent Classifier (modelo barato: Ollama > MiniMax)
    ↓
Intent {
    type: "complex_task",         # query | create | execute | automate | conversational
    domain: ["calendar", "email", "memory"],
    requires_planning: True,
    estimated_steps: 4,
    requires_tools: ["calendar_tool", "email_tool"],
    requires_memory: True,
    user_context_needed: True,
    confidence: 0.87
}
```

#### Componente 2: Context Enricher

Antes de planificar, el Orchestrator enriquece el intent con contexto del MOS:

```python
async def enrich(self, intent: Intent, memory: IMemoryStore) -> EnrichedIntent:
    context = await memory.context(
        query=intent.raw_query,
        max_tokens=1500,
        sources=["mem_personal", "mem_project", "mem_conversational"]
    )
    # Ejemplo de contexto recuperado:
    # - "La reunión con Hermes suele durar 2h (historial)"
    # - "El usuario prefiere las reuniones de mañana antes de las 12"
    # - "El equipo de Hermes: Miguel, Sara, Carlos (memoria de contactos)"
    # - "Última reunión con Hermes fue el lunes, se habló de la migración de providers"
    return EnrichedIntent(intent=intent, context=context)
```

#### Componente 3: Task Planner

El Task Planner genera el plan SOLO para intents que lo requieren (confidence del
Intent Classifier sobre el campo `requires_planning`):

```python
Plan {
    steps: [
        PlanStep(
            id="1",
            description="Buscar en memoria quién es el equipo de Hermes",
            tool="memory_search",
            depends_on=[],
            can_parallelize=False,
            approval_required=False,
        ),
        PlanStep(
            id="2",
            description="Consultar disponibilidad del jueves en Google Calendar",
            tool="calendar_tool",
            depends_on=["1"],
            can_parallelize=False,
            approval_required=False,
        ),
        PlanStep(
            id="3",
            description="Buscar emails recientes del equipo de Hermes",
            tool="email_inbox",
            depends_on=[],             # puede en paralelo con step 2
            can_parallelize=True,
            approval_required=False,
        ),
        PlanStep(
            id="4",
            description="Crear evento en calendario y enviar invitaciones",
            tool="calendar_tool",
            depends_on=["1", "2", "3"],
            can_parallelize=False,
            approval_required=True,   # requiere aprobación del usuario
        ),
    ],
    estimated_duration_s=12,
    requires_approval_steps=["4"],
    model_used="claude-sonnet-4-6",   # modelo potente solo para planning
}
```

#### Componente 4: Execution Engine

```python
class ExecutionEngine:
    """
    Ejecuta el plan respetando dependencias y paralelismo.
    Estado persistido en orchestrator_traces.
    """
    
    async def execute(self, plan: Plan, runtime: AgentRuntime,
                       memory: IMemoryStore, approval_gate: ApprovalGate):
        results = {}
        
        for wave in self._dependency_waves(plan):  # ordena por dependencias
            # Ejecuta en paralelo los steps de la misma wave
            wave_results = await asyncio.gather(*[
                self._execute_step(step, results, runtime, memory, approval_gate)
                for step in wave
            ])
            results.update(wave_results)
        
        return results
    
    async def _execute_step(self, step, previous_results, runtime, memory, gate):
        if step.approval_required:
            await gate.request(step.description, step.tool, step.params)
        
        # Registra en orchestrator_traces antes y después
        trace_id = await self._trace_start(step)
        try:
            result = await runtime.execute_task(step, memory, self.tools, gate)
            await self._trace_complete(trace_id, result)
            return result
        except Exception as e:
            await self._trace_error(trace_id, e)
            return self._handle_step_failure(step, e)  # graceful degradation
```

#### Componente 5: Response Builder

Sintetiza los resultados de todos los steps en una respuesta coherente para el usuario.
Usa el modelo apropiado según la complejidad (respuestas simples → modelo barato).

#### Componente 6: Trace & Learn

```python
class OrchestratorTracer:
    """
    Registra todas las decisiones del Orchestrator para:
    1. Debugging: reconstruir qué pasó y por qué
    2. Learning: el LLL analiza trazas para detectar patrones de planificación
    3. Métricas: tiempo, tokens, éxito/fallo por tipo de intent
    """
    
    async def record(self, trace: OrchestratorTrace):
        # Guarda en orchestrator_traces (PostgreSQL)
        # También indexa en Memory API para que el LLL pueda analizarlo
        await self.db.save(trace)
        await self.memory.add(
            content=trace.to_summary(),
            memory_type=MemoryType.DECISION,
            metadata={"trace_id": trace.id, "intent_type": trace.intent.type}
        )
```

### 2.3 Lo que se implementa en V1.0 (MVP)

**Implementado en V1.0**:
- Intent Classifier con 5 tipos de intent
- Context Enricher (consulta `Context API` del MOS)
- Task Planner básico (máximo 5 steps, sin paralelismo real aún)
- Execution Engine secuencial (los steps se ejecutan en orden, sin paralelismo)
- Response Builder
- `NullRuntime` (usa el chat handler actual)
- `orchestrator_traces` completo
- Routing por complejidad (modelo barato para classify, modelo potente para planning)
- Decision API: registra cada plan tomado

**Stubs en V1.0**:
- `HermesRuntime` → llega en V1.1
- Paralelismo real en Execution Engine → V1.2
- Plan backtracking (si un step falla, re-planifica) → V1.2

**No implementado en V1.0**:
- Multi-step parallelism
- Adaptive planning (cambia el plan mid-execution según resultados)
- Predictive pre-loading de contexto

### 2.4 Tabla de evolución del Orchestrator

| Feature | V1.0 | V1.1 | V1.2 | V2.0+ |
|---------|------|------|------|-------|
| Intent Classifier (5 tipos) | ✅ | ✅ | ✅ | ✅ |
| Context Enricher (MOS) | ✅ | ✅ | ✅ | ✅ |
| Task Planner básico (<5 steps) | ✅ | ✅ | ✅ | ✅ |
| Execution Engine secuencial | ✅ | ✅ | ✅ | ✅ |
| NullRuntime | ✅ | ✅ | ✅ | ✅ |
| AgentRuntime interface | ✅ | ✅ | ✅ | ✅ |
| orchestrator_traces | ✅ | ✅ | ✅ | ✅ |
| Decision API integration | ✅ | ✅ | ✅ | ✅ |
| HermesRuntime | ❌ | ✅ | ✅ | ✅ |
| Parallel Execution | ❌ | ❌ | ✅ | ✅ |
| Plan Backtracking | ❌ | ❌ | ✅ | ✅ |
| Multi-Runtime routing | ❌ | ❌ | ✅ | ✅ |
| Self-optimizing planner | ❌ | ❌ | ❌ | ✅ |
| Predictive context loading | ❌ | ❌ | ❌ | ✅ |

---

## 3. INTEGRACIÓN AUTOMATION ENGINE ↔ ORCHESTRATOR

Los dos sistemas se complementan. Fable5 debe diseñar cómo interactúan:

```
Automation Engine detecta evento:
  "Email urgente de Miguel sobre presupuesto"
    ↓
AutomationRule.action = AgentTaskAction
    ↓
AgentTaskAction delega en el Orchestrator
  (no en el chat handler directamente)
    ↓
Orchestrator analiza el intent: "procesar email urgente sobre presupuesto"
    ↓
Context Enricher: recupera contexto de Miguel, proyectos relacionados
    ↓
Task Planner: [step1: leer email] [step2: buscar contexto en memoria] 
              [step3: generar resumen] [step4: notificar por Telegram (con gate)]
    ↓
Execution Engine: ejecuta
    ↓
Resultado: "Miguel pregunta sobre el presupuesto Q3 de Aithera.
            Según tu historial, sueles responderle en el mismo día.
            ¿Quieres que redacte un borrador de respuesta?"
```

**Regla**: después de V1.0, el Automation Engine NO llama directamente al chat handler.
Todo pasa por el Orchestrator. El Orchestrator es el único punto de entrada para
ejecución de tareas no triviales.

---

## 4. CRITERIOS DE CALIDAD TÉCNICA

Fable5 debe verificar que el diseño cumple:

### Para el Automation Engine
1. **Extensibilidad de triggers**: añadir un nuevo tipo de trigger no requiere
   tocar el engine — solo implementar la interfaz `Trigger`.
2. **Composabilidad de condiciones**: las condiciones deben poder combinarse con AND/OR/NOT.
3. **Aislamiento de acciones**: una acción fallida no bloquea las siguientes.
4. **Idempotencia**: ejecutar la misma regla dos veces no produce efectos duplicados.
5. **Auditabilidad**: cada ejecución queda registrada en `automation_executions` con
   el resultado, el tiempo, el trigger que la activó y si requirió aprobación.

### Para el Orchestrator
1. **Intent Classifier usa siempre el modelo más barato**: nunca el modelo potente
   para clasificar, solo para planificar.
2. **Plans son serializables**: un plan en estado `waiting_approval` puede
   persistirse en BD y reanudarse horas después.
3. **Fallos son datos**: si un step falla, el error va a `Error Memory` del MOS
   y el Orchestrator intenta degradar con gracia (devolver lo que pudo hacer).
4. **Traces son completos**: cada decisión del Orchestrator (qué modelo usó, qué
   plan generó, qué steps ejecutó, cuánto tardó) queda en `orchestrator_traces`.
5. **Sin side effects en el planning**: la fase de planning NO ejecuta ninguna
   acción. Solo cuando el plan está aprobado (si requiere aprobación) o completo
   se inicia la ejecución.

---

## 5. LO QUE FABLE5 NO DEBE DISEÑAR TODAVÍA

Estas features se aplazarán explícitamente a V2.0+:

- **Natural language rule creation**: "Dile a Aithera qué regla quieres y la crea
  sola". Requiere un Orchestrator maduro + LLL activo. V2.0+.
- **Self-optimizing Automation Engine**: el engine aprende solo qué reglas activar
  y cuándo, sin que el usuario las defina. V2.0+.
- **Multi-agent parallelism en el Orchestrator**: múltiples instancias de
  `HermesRuntime` trabajando en paralelo en el mismo plan. V2.0+.
- **Plan negotiation**: el Orchestrator propone un plan, el usuario lo modifica en
  lenguaje natural, el Orchestrator re-planifica. V1.2.

---

## 6. MISIÓN DE FABLE5

1. **RFC de Automation Engine**: arquitectura completa con las 4 capas
   (Triggers, Conditions, Actions, Learning). Contratos formales de cada interfaz.
   Plan de implementación V0.9 (MVP) vs V1.x vs V2.0+.

2. **RFC de Orchestrator**: arquitectura completa con los 6 componentes. Contratos
   formales. Plan de implementación V1.0 (MVP funcional) vs V1.x vs V2.0+.

3. **RFC de integración AE ↔ Orchestrator**: cómo el Automation Engine delega en
   el Orchestrator para tareas no triviales. Con diagrama de flujo.

4. **Actualización de V0.9 y V1.0 en el roadmap**: reescribir ambas secciones
   con el nivel de detalle de este documento (no el nivel básico actual).

5. **Detección de mejoras en el plan actual**: si Fable5 identifica aspectos del
   diseño de V0.9 o V1.0 que son arquitectónicamente incorrectos o crearán deuda
   técnica, documentarlos con propuesta de solución.

---

*Documento creado: 2026-07-09. Automation Engine y Orchestrator diseñados con
visión V2.0+ pero implementación escalonada: V0.9 y V1.0 son MVPs funcionales,
no el sistema completo. Cada versión posterior potencia el sistema sin reescribirlo.*
