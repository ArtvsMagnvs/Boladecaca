# LangGraph — State machines para agents

## Resumen

**LangGraph** (langchain-ai/langgraph) es el framework de state machines para agents. Ver [JWIKI-011 langgraph.md](../01_LANDSCAPE/langgraph.md) para overview.

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## Hello World

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    messages: list[str]

def node_a(state: State):
    return {"messages": state["messages"] + ["A"]}

def node_b(state: State):
    return {"messages": state["messages"] + ["B"]}

graph = StateGraph(State)
graph.add_node("a", node_a)
graph.add_node("b", node_b)
graph.add_edge(START, "a")
graph.add_edge("a", "b")
graph.add_edge("b", END)

app = graph.compile()
result = app.invoke({"messages": []})
# {'messages': ['A', 'B']}
```

## Conditional edges

```python
def should_continue(state: State) -> str:
    if len(state["messages"]) > 5:
        return "end"
    return "continue"

graph.add_conditional_edges("a", should_continue, {
    "continue": "b",
    "end": END
})
```

## Cycles (true agents)

```python
graph.add_edge("a", "b")
graph.add_conditional_edges("b", should_continue, {
    "continue": "a",  # ← cycle
    "end": END
})
```

## Para Aithera V1.0 Orchestrator

V1.0 podría借鉴 LangGraph para state machines. Ver [JWIKI-055 orchestrator-pattern.md](../02_ARCHITECTURE/orchestrator-pattern.md).

## Referencias cruzadas

- [JWIKI-011 langgraph.md](../01_LANDSCAPE/langgraph.md)
- [JWIKI-055 orchestrator-pattern.md](../02_ARCHITECTURE/orchestrator-pattern.md)

## Fuentes

1. https://langchain-ai.github.io/langgraph/
2. https://github.com/langchain-ai/langgraph

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified