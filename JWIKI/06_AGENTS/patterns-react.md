# Patrones de agents — ReAct, Plan-Execute, Reflexion, ToT, CoT

## Resumen

5 patrones principales de agents LLM. Cada uno con trade-offs.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Patrones

### 1. ReAct (Reason + Act)

Intercala reasoning con tool calls:

```
Thought: I need to search for X
Action: web_search(X)
Observation: ...
Thought: Now I need to look up Y
Action: memory_search(Y)
Observation: ...
Thought: I have enough info
Final Answer: ...
```

```python
def react_agent(query, tools, max_iters=5):
    messages = [{"role": "user", "content": query}]
    for _ in range(max_iters):
        response = llm.chat(messages, tools=tools)
        if response.has_tool_calls():
            for tc in response.tool_calls:
                result = execute_tool(tc)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": str(result)})
        else:
            return response.content
    return "Max iters reached"
```

**Pros**: simple, interpretable.
**Cons**: puede "perder el foco" en loops.

### 2. Plan-and-Execute

1. **Plan**: LLM genera plan (lista de steps).
2. **Execute**: cada step ejecutado (puede ser tool o sub-agent).
3. **Replan**: si falla, replan.

```python
def plan_execute(query, tools):
    plan = llm.plan(query)  # ["search X", "lookup Y", "synthesize"]
    results = []
    for step in plan:
        try:
            result = execute_tool(step.tool, step.args)
            results.append(result)
        except Exception as e:
            plan = llm.replan(query, plan, results, str(e))
    return synthesize(query, plan, results)
```

**Pros**: planning upfront, retry on failure.
**Cons**: plan puede ser incorrecto.

### 3. Reflexion

Agent reflexiona sobre sus errores y los usa para mejorar:

```python
def reflexion_agent(query, max_trials=3):
    for trial in range(max_trials):
        result = react_agent(query, tools)
        critique = llm.critique(query, result)
        if "satisfactory" in critique:
            return result
        # usar critique en el próximo trial
        query = f"{query}\n\nPrevious attempt: {result}\n\nCritique: {critique}"
    return result
```

**Pros**: mejora con iteración.
**Cons**: más costoso (múltiples LLM calls).

### 4. Chain-of-Thought (CoT)

Reasoning explícito paso a paso:

```
Q: Roger tiene 5 pelotas. Compra 2 más. Luego pierde 3.
A: Pensemos. Roger empieza con 5. Compra 2 → 7. Pierde 3 → 4. Entonces Roger tiene 4 pelotas.
```

```python
prompt = f"Q: {query}\nA: Pensemos paso a paso."
```

**Pros**: mejora accuracy en tasks complejos.
**Cons**: tokens extra.

### 5. Tree of Thoughts (ToT)

Explora múltiples paths en paralelo (como search tree):

```python
def tree_of_thoughts(query):
    # Genera N paths posibles
    thoughts = [llm.thought(query, branch=i) for i in range(N)]
    # Evalúa cada uno
    scores = [llm.evaluate(query, t) for t in thoughts]
    # Expande el mejor
    best = thoughts[scores.index(max(scores))]
    next_thoughts = llm.expand(best)
    # ... recursive
    return best
```

**Pros**: encuentra soluciones no obvias.
**Cons**: muy costoso.

## Para Aithera V1.0

- **V0.5 AgentManager**: implementa ReAct simple.
- **V1.0 Orchestrator**: añadir Plan-Execute + Reflexion.

## Comparativa

| Patrón | Coste | Reliability | Mejor para |
|---|---|---|---|
| ReAct | medio | ⭐⭐⭐ | tasks simples |
| Plan-Execute | medio-alto | ⭐⭐⭐⭐ | tasks complejos multi-step |
| Reflexion | alto | ⭐⭐⭐⭐⭐ | tasks con auto-corrección |
| CoT | bajo | ⭐⭐⭐ | reasoning tasks |
| ToT | muy alto | ⭐⭐⭐⭐⭐ | research, problemas abiertos |

## Referencias cruzadas

- [JWIKI-106 aithera-agent-manager.md](./aithera-agent-manager.md)
- [JWIKI-117 agent-loops.md](./agent-loops.md)

## Fuentes

1. https://arxiv.org/abs/2210.03629 (ReAct)
2. https://arxiv.org/abs/2305.10601 (Tree of Thoughts)
3. https://arxiv.org/abs/2303.11381 (Reflexion)

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified