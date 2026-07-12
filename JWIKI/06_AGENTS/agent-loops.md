# Agent Loops — Single vs Multi

## Resumen

**Agent loops** son los ciclos de ejecución: single-agent loop (1 agent, multiple iterations) vs multi-agent loop (N agents, coordination).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Single-agent loop

```
Agent
  ↓ iterate
  LLM call → if tool_calls → execute → continue
       ↓
       if no tool_calls → done
```

```python
async def single_loop(query, llm, tools, max_iters=10):
    messages = [{"role": "user", "content": query}]
    for i in range(max_iters):
        response = await llm.chat(messages, tools=tools)
        if not response.tool_calls:
            return response.content
        for tc in response.tool_calls:
            result = await execute(tc)
            messages.append({"role": "tool", ...})
    return "Max iters"
```

## Multi-agent loop

```
Orchestrator
  ↓ classify intent
  ↓
  Sub-agent A ──┐
  Sub-agent B ──┼── parallel/sequential
  Sub-agent C ──┘
       ↓
  Orchestrator synthesize
```

```python
async def multi_loop(task, orchestrator, sub_agents):
    # 1. Classify intent
    intent = await orchestrator.classify(task)
    
    # 2. Run sub-agents
    if intent.parallel:
        results = await asyncio.gather(*[
            sub_agents[name].run(intent.sub_tasks[name])
            for name in intent.sub_agents
        ])
    else:
        results = []
        for name in intent.sub_agents:
            results.append(await sub_agents[name].run(intent.sub_tasks[name]))
    
    # 3. Synthesize
    return await orchestrator.synthesize(task, results)
```

## Termination conditions

### Single-agent

- ✅ LLM no retorna tool_calls.
- ✅ Max iterations reached.
- ✅ Token limit exceeded.
- ✅ Timeout.
- ✅ Explicit "done" signal.

### Multi-agent

- ✅ All sub-agents completed.
- ✅ Orchestrator decides "done".
- ✅ Vote/agreement (consensus).
- ✅ Error budget exceeded.

## Aithera V0.5+ actual

AgentManager implementa single-agent loop (CLAUDE.md §1):
```python
for iteration in range(10):
    response = await self.ai.chat(messages, tools=...)
    if not response.tool_calls:
        return response.content
    # execute tool calls
```

## Aithera V1.0+

V1.0 Orchestrator implementa multi-agent loop con:
- ✅ Intent classification.
- ✅ Parallel/sequential sub-agents.
- ✅ Synthesizer.
- ✅ State preservation.

## Pros y cons

| Pattern | Pros | Con |
|---|---|---|
| Single loop | simple, debug | 1 task at a time |
| Multi loop | parallelismo | complejo, costoso |

## Referencias cruzadas

- [JWIKI-114 multi-agent-hierarchical.md](./multi-agent-hierarchical.md)
- [JWIKI-116 sub-agents.md](./sub-agents.md)
- [JWIKI-106 aithera-agent-manager.md](./aithera-agent-manager.md)
- CLAUDE.md §1

## Fuentes

1. https://lilianweng.github.io/posts/2023-06-23-agent/

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified