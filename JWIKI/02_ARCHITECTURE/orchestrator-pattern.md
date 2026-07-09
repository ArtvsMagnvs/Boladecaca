# Orchestrator Pattern — Diseño V1.0

## Resumen

**Orchestrator** es el patrón central de Aithera V1.0: recibe mensajes del Gateway, clasifica intent, planifica tareas, delega a skills/tools, y construye respuesta. Inspirado en OpenClaw y Hermes Agent.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Arquitectura del Orchestrator

```
MessageEnvelope (Gateway)
        ↓
Orchestrator.handle(envelope)
        ↓
┌───────────────────────────────────┐
│  1. Intent Analyzer               │
│     (LLM call: classify intent)    │
└─────────┬─────────────────────────┘
          ↓
┌───────────────────────────────────┐
│  2. Task Planner                   │
│     (LLM call: break into tasks)   │
└─────────┬─────────────────────────┘
          ↓
┌───────────────────────────────────┐
│  3. Task Executor                   │
│     (DAG execution, parallel where │
│      possible)                      │
└─────────┬─────────────────────────┘
          ↓
┌───────────────────────────────────┐
│  4. Response Builder                │
│     (Aggregate results, format)     │
└─────────┬─────────────────────────┘
          ↓
OutboundMessage → Gateway → Adapter → Canal
```

## 1. Intent Analyzer

```python
class IntentAnalyzer:
    INTENT_TAXONOMY = [
        "chat",           # conversación general
        "query",          # pregunta factual
        "execute",        # ejecutar tool
        "create",         # generar contenido
        "automate",       # trigger automation
        "conversational", # respuesta conversacional corta
    ]
    
    async def classify(self, message: str) -> Intent:
        prompt = f"""Clasifica el siguiente mensaje en una de estas categorías: {self.INTENT_TAXONOMY}
        Mensaje: {message}
        Responde solo con la categoría."""
        response = await self.llm.complete(prompt)
        return Intent(response.text.strip())
```

## 2. Task Planner

```python
class TaskPlanner:
    async def plan(self, intent: Intent, context: dict) -> Plan:
        prompt = f"""Dado el intent '{intent}' y contexto {context}, devuelve una lista de tasks en JSON:
        [
          {{"tool": "name", "args": {{...}}, "depends_on": []}}
        ]
        """
        response = await self.llm.complete(prompt)
        return Plan.from_json(response.text)
```

## 3. Task Executor (DAG)

```python
class TaskExecutor:
    async def execute(self, plan: Plan) -> list[TaskResult]:
        results = []
        # Topological sort
        for layer in plan.topological_layers():
            # Execute layer in parallel
            layer_results = await asyncio.gather(*[
                self._run_task(task, results) for task in layer
            ])
            results.extend(layer_results)
        return results
    
    async def _run_task(self, task, prior_results):
        # Resolve args from prior results
        args = self._resolve_args(task.args, prior_results)
        tool = self.tool_manager.get(task.tool)
        return await tool.execute(**args)
```

## 4. Response Builder

```python
class ResponseBuilder:
    async def build(self, intent, plan, results, envelope) -> OutboundMessage:
        if intent == Intent.CHAT:
            # conversational response
            response = await self.llm.chat(
                system="Responde al usuario de forma concisa y amigable.",
                user=f"Resultados: {results}"
            )
            return OutboundMessage(channel=envelope.channel, chat_id=envelope.chat_id, text=response)
        elif intent == Intent.EXECUTE:
            return OutboundMessage(channel=envelope.channel, chat_id=envelope.chat_id, text=f"✅ {len(results)} tasks ejecutadas")
        # etc.
```

## Integración con Gateway V0.8

```python
# V0.8 → V1.0
# V0.8: gateway.set_handler(chat_message_handler)
# V1.0: gateway.set_handler(orchestrator)

class Orchestrator:
    async def handle(self, envelope: MessageEnvelope) -> OutboundMessage:
        intent = await self.intent_analyzer.classify(envelope.text)
        plan = await self.task_planner.plan(intent, envelope.metadata)
        results = await self.task_executor.execute(plan)
        return await self.response_builder.build(intent, plan, results, envelope)
```

## Skills y Sub-agents (V1.0)

El Orchestrator puede delegar a **skills** (Superpowers-style):

```python
class SkillOrchestrator:
    SKILLS = ["brainstorming", "tdd", "debugging", ...]
    
    async def handle(self, envelope):
        # Cargar skill aplicable
        skill = self._match_skill(envelope.text)
        if skill:
            return await skill.execute(envelope)
        return await super().handle(envelope)
```

## Inspirations

- **OpenClaw**: channels → gateway → agent runtime → sandbox.
- **Hermes Agent**: closed learning loop + skills (agentskills.io).
- **Superpowers**: TDD enforced + SDD (subagent-driven development).
- **CrewAI**: agents + tasks + process (sequential/hierarchical).
- **LangGraph**: state machines para agents.

## Aithera V0.7.3 → V1.0 migration

V0.7.3 tiene AgentManager (CRUD + ejecución asíncrona). V1.0 Orchestrator es **mucho más sofisticado**:
- Multi-intent (no solo "ejecutar agent").
- Planning con LLM.
- DAG execution.
- Skills integration.

## Pendientes

- [ ] Diseñar `MessageEnvelope` extendido para V1.0 (con attachments, voice, etc.).
- [ ] Implementar `TaskPlanner` con prompts few-shot.
- [ ] Skill discovery desde `aithera-skills/` directorio.
- [ ] State management con checkpoints (resume mid-task).

## Referencias cruzadas

- [JWIKI-053 hexagonal-ports.md](./hexagonal-ports.md)
- [JWIKI-054 clean-architecture.md](./clean-architecture.md)
- [JWIKI-107 patterns-react.md](../06_AGENTS/patterns-react.md)
- [JWIKI-117 agent-loops.md](../06_AGENTS/agent-loops.md)

## Fuentes

1. OpenClaw architecture (inspiration)
2. Superpowers SDD (inspiration)
3. LangGraph state machines (inspiration)
4. CrewAI patterns (inspiration)

## Nivel de confianza

**80%** — Diseño conceptual. Implementación V1.0 pendiente.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified