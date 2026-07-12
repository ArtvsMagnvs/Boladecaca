# Sub-Agents — Aislamiento y concurrencia

## Resumen

**Sub-agents** son agents ejecutados en paralelo o secuencialmente desde un parent. Aithera V1.0 usará para tareas complejas multi-paso.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Tipos

### 1. Secuencial

```python
results = []
for sub_task in sub_tasks:
    sub_agent = get_sub_agent(sub_task.type)
    result = await sub_agent.run(sub_task.input)
    results.append(result)
```

### 2. Paralelo

```python
tasks = [sub_agent.run(st.input) for st in sub_tasks]
results = await asyncio.gather(*tasks)
```

### 3. Background (fire-and-forget)

```python
async def run_background(sub_task):
    asyncio.create_task(sub_agent.run(sub_task.input))

# El parent sigue sin esperar
```

## Aislamiento

Cada sub-agent tiene:
- ✅ **Propio context window** (independiente).
- ✅ **Propios tools** (whitelist per sub-agent).
- ✅ **Propio execution timeout**.
- ✅ **Propio audit log** (`agent_executions` per sub-agent).

## Compartir state

```python
# Shared state via DB
context = await db.get_context("research_X")

# Sub-agents read same context
result_a = await researcher.run(f"Use context: {context}")
result_b = await analyzer.run(f"Use context: {context}")
```

## Concurrencia

```python
import asyncio

async def parallel_subagents(tasks):
    """Run N sub-agents in parallel."""
    coros = [sub_agent.run(t.input) for t in tasks]
    return await asyncio.gather(*coros, return_exceptions=True)
```

⚠️ **Cuidado con rate limits**: si N=10 sub-agents cada uno llama LLM 5 veces = 50 LLM calls simultáneos. Usar semaphore:

```python
semaphore = asyncio.Semaphore(3)  # max 3 concurrent

async def throttled_run(sub_task):
    async with semaphore:
        return await sub_agent.run(sub_task.input)
```

## Aithera V1.0+ plan

- ✅ V1.0: parallel tool calls per sub-agent.
- ✅ V1.0: orchestrator coordina N sub-agents.
- ⏳ V1.5+: sub-agents con state shared (DB o in-memory).

## Referencias cruzadas

- [JWIKI-114 multi-agent-hierarchical.md](./multi-agent-hierarchical.md)
- [JWIKI-117 agent-loops.md](./agent-loops.md)

## Fuentes

1. https://docs.python.org/3/library/asyncio-task.html
2. Aithera V0.5+ AgentManager

## Nivel de confianza

**90%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified