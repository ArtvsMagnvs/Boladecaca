# LangGraph Overview

## Resumen

LangGraph es un framework de orquestación de agentes AI de bajo nivel desarrollado por LangChain Inc, basado en grafos dirigidos cíclicos con estado persistente. A diferencia de LangChain (DAG lineal), LangGraph permite ciclos, checkpointing nativo, human-in-the-loop y time-travel debugging. Con ~36k stars y 34.5M descargas mensuales en PyPI, es el framework de agentes más adoptado en producción, usado por Klarna (85M usuarios), Uber, LinkedIn y Replit.

## Objetivo

Documentar LangGraph como referencia para el ecosistema de asistentes JARVIS-like: arquitectura core (StateGraph), features diferenciadores (checkpointing, HITL, streaming), ecosistema de integraciones, adopción en producción, y comparación contra CrewAI y AutoGen.

## Estado

🟡 En progreso — Documento en fase de síntesis por Aithera Escriba. Pendiente de auditoría.

## Versiones compatibles

| Proyecto | Versión | Notas |
|---|---|---|
| LangGraph (Python) | 1.2.6 (18 jun 2026) | Última estable |
| LangGraph.js (TypeScript) | 0.4.x | Menos madura que Python |
| LangChain core | 1.4.8 | Misma fecha que LangGraph 1.2.6 |
| LangGraph GA 1.0 | 22 octubre 2025 | Lanzamiento conjunto LangChain 1.0 |

## Proyectos compatibles

- LangGraph Platform (anteriormente Cloud) — deployments gestionados, 400+ empresas en beta
- LangGraph Studio — IDE visual para depuración
- LangGraph CLI — herramienta de deployment
- Integraciones: Redis, PostgreSQL, MongoDB, LangSmith, MCP, LangChain LCEL

## Dependencias

- [01_LANDSCAPE/projects.md](projects.md) — contexto de ecosistema OSS
- [06_AGENTS/langgraph-deep.md](06_AGENTS/langgraph-deep.md) — deep dive técnico (pendiente)
- [01_LANDSCAPE/crewai.md](crewai.md) — comparativa CrewAI (pendiente)
- [01_LANDSCAPE/autogen.md](autogen.md) — comparativa AutoGen (pendiente)

## Arquitectura

LangGraph implementa un **StateGraph**: grafo dirigido cíclico donde cada nodo es una función Python que recibe y retorna estado. La inspiración proviene de Pregel (Google) y Apache Beam, con interfaz pública inspirada en NetworkX.

```
┌─────────────────────────────────────────────────────────────┐
│                    StateGraph (TypedDict)                   │
│                                                              │
│  START ──▶ [Node: agent] ──▶ [Conditional Edge] ──▶ END    │
│                │                   │                         │
│                ▼                   ▼                         │
│          [Node: tools]      ┌─────────────────────┐         │
│                │            │ should_continue()   │         │
│                ▼            │ return END|continue│         │
│            [Node: agent]    └─────────────────────┘         │
│                │                                               │
│                └──────────────────────────────────▶ [interrupt()] ──▶ Human approval
│                                                              │
│  ┌────────── Checkpointer ── Persists state per thread_id ──┐ │
│  │ MemorySaver | PostgresSaver | RedisSaver | MongoDBSaver  │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Descripción técnica

### Conceptos core

**StateGraph** es la abstracción central. El estado es un `TypedDict` donde cada nodo recibe el estado actual y retorna una actualización parcial que hace merge (no sobreescribe). Los updates se acumulan mediante un reducer — por ejemplo `Annotated[int, operator.add]` para contadores de retry.

**Nodes** son funciones Python puras: reciben el estado y retornan actualizaciones. No hay magia — cada decisión es un edge explícito.

**Edges** definen transiciones entre nodos:
- `add_edge(START, "agent")` — punto de entrada fijo
- `add_conditional_edges("agent", routing_fn)` — enrutamiento dinámico
- `add_edge("tools", "agent")` — flujo condicional

**Compile()** valida el grafo (detecta nodos desconectados, END inalcanzable, puntos de entrada faltantes) y produce un ejecutor estilo Pregel.

### Superstep execution

El runtime ejecuta **supersteps**: durante un superstep, múltiples ramas pueden ejecutarse en paralelo mediante `Send`, escribiendo a estado compartido. Antes del siguiente rutear, el estado se hace merge — eliminando race conditions en ramas paralelas. Esto difiere fundamentalmente de CrewAI (tasks secuenciales/paralelos sin estado compartido granular).

### Checkpointing / Persistence

Cada ejecución de nodo persiste el estado. Si el servidor cae, `resume` por `thread_id` recupera el último checkpoint. Backends disponibles: MemorySaver, PostgresSaver, AsyncRedisSaver, MongoDBSaver, OracleSaver.

### Human-in-the-loop

`interrupt()` pausa el grafo y espera input externo. Uso típico: approval gates antes de acciones sensibles (refunds >$500, envío de emails, etc.).

### Time-travel debugging

Capacidad de inspeccionar el estado en cualquier checkpoint pasado. Útil para auditing y debugging de workflows complejos.

### Memory Store (cross-thread)

Además del checkpointing (persistencia por thread), LangGraph Store permite memoria de largo plazo con búsqueda semántica cross-thread. Backends: PostgresStore, RedisStore, MongoDBStore.

### LangGraph.js

Versión TypeScript/JavaScript del framework. Funcionalmente equivalente pero menos madura que Python — no recomendada para producción hasta que alcance paridad de features.

## Flujo interno

1. Definir `StateSchema` como `TypedDict`
2. Crear `StateGraph(AgentState)` 
3. Añadir nodos con `add_node("nombre", función)`
4. Definir edges con `add_edge()` y `add_conditional_edges()`
5. Opcional: añadir checkpointer `graph.compile(checkpointer=saver)`
6. Opcional: añadir store `graph.compile(store=memory_store)`
7. Compilar: `app = graph.compile()`
8. Invocar: `app.invoke({"messages": [...]}, config={"configurable": {"thread_id": "user-123"}})`
9. Para streaming: `app.stream({"messages": [...]})`

## Call Stack / API

```
app.invoke(input, config)
  → compile() validó el grafo (ejecutor Pregel)
    → Ejecuta nodo START
      → Ejecuta nodo "agent" (función Python pura)
        → LLM.invoke() (ChatOpenAI/Anthropic/etc)
          → Retorna actualización parcial de estado
      → Merge de estado (reducer pattern)
        → Conditional edge routing
          → ¿Hay tool_calls? → nodo "tools"
          → ¿No hay tool_calls o END? → END
      → ¿interrupt() llamado? → PAUSA, espera external approval
    → Loop hasta END o interrupt
  → Retorna estado final
```

## Diagramas

```mermaid
graph TD
    START([START]) --> AGENT[agent<br/>LLM call]
    AGENT --> CHECK{Has tool_calls?}
    CHECK -->|Yes| TOOLS[tools<br/>Tool execution]
    TOOLS --> AGENT
    CHECK -->|No| APPROVAL{Needs approval?}
    APPROVAL -->|Yes| INTERRUPT[/interrupt()/]
    INTERRUPT --> HUMAN[Human approval]
    HUMAN --> AGENT
    APPROVAL -->|No| END([END])
```

## Código relacionado

- Repo principal: https://github.com/langchain-ai/langgraph
- LangGraph.js: https://github.com/langchain-ai/langgraphjs
- LangGraph Platform: https://langchain.com/ (sección Cloud/LangGraph Platform)
- Redis integration: https://github.com/redis-developer/langgraph-redis
- MCP Server: https://github.com/langchain-ai/langgraph-mcp
- Long-term memory example: https://github.com/Ofekirsh/langgraph-agent-memory

## Ejemplos

### Minimal StateGraph

```python
# langgraph_minimal.py — LangGraph 1.0+
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]  # acumula via reducer

llm = ChatOpenAI(model="gpt-4o-mini")

def call_model(state: AgentState):
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

def should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    return "continue" if last.tool_calls else END

graph = StateGraph(AgentState)
graph.add_node("agent", call_model)
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", should_continue)
graph.add_edge("agent", END)

app = graph.compile()
result = app.invoke({"messages": [("user", "What is LangGraph?")]})
```

### Postgres Checkpointing (producción)

```python
# persistence.py — Production checkpointing
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg_pool import ConnectionPool

DB_URI = "postgresql://user:pass@host:5432/langgraph?sslmode=require"
pool = ConnectionPool(conninfo=DB_URI, max_size=10)

with pool.connection() as conn:
    saver = PostgresSaver(conn)
    saver.setup()

app = graph.compile(checkpointer=saver)

config = {"configurable": {"thread_id": "user-123"}}
result = app.invoke({"messages": [...]}, config=config)
# Resume after crash: same thread_id resumes from last checkpoint
result = app.invoke({"messages": [new_msg]}, config=config)
```

### Human-in-the-loop interrupt

```python
# hitl.py — Approval gates
from langgraph.types import interrupt

def approval_node(state: AgentState) -> AgentState:
    if state["requires_approval"]:
        # Execution pauses here
        approval = interrupt("Awaiting manager approval for refund > $500")
        return {"approved": approval}
    return state
```

### Visual debugging

```python
# debug.py — Mermaid diagram
from IPython.display import Image, display
display(Image(graph.get_graph().draw_mermaid_png()))
```

### Redis middleware (cache + checkpointing compartido)

```python
# redis_middleware.py — Semantic cache
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.middleware.redis import IntegratedRedisMiddleware, SemanticCacheConfig

checkpointer = AsyncRedisSaver(redis_url="redis://localhost:6379")
await checkpointer.asetup()

middleware = IntegratedRedisMiddleware.from_saver(
    checkpointer,
    configs=[SemanticCacheConfig(name="llm_cache")],
)

agent = create_agent(model="gpt-4o-mini", tools=tools,
                     checkpointer=checkpointer,
                     middleware=[middleware])
```

## Buenas prácticas

- ✅ Usar `Annotated[T, reducer]` para acumular estados parciales (ej: `retry_count: Annotated[int, operator.add]`)
- ✅ Definir estado upfront con TypedDict — reduce complejidad en redes de agentes
- ✅ Usar `interrupt()` para cualquier acción que requiera approval humana
- ✅ Compilar el grafo una vez al inicio de la aplicación, no en cada invoke
- ✅ Persistir con PostgresSaver o RedisSaver en producción (MemorySaver solo para desarrollo)
- ✅ Usar `thread_id` para aislar conversaciones — permite resume seguro
- ✅ Generar diagramas Mermaid durante desarrollo para validar que el graph refleja el flujo deseado
- ✅ LangGraph.js: usar solo para prototipado — Python es la implementación de referencia

## Errores comunes

- ❌ Definir estado demasiado complejo al inicio — empezar simple, expandir cuando el patrón esté claro
- ❌ Olvidar `compile()` — el grafo no es ejecutable sin él
- ❌ No validar el grafo con `get_graph().draw_mermaid_png()` antes de production
- ❌ Usar logging `print()` dentro de nodos — el logging en Tasks es problemático
- ❌ Confundir checkpointing (persistencia por thread) con Memory Store (memoria cross-thread)
- ❌ Usar LangGraph para workflows lineales (overkill) — LangChain LCEL es suficiente
- ❌ Depender de `AgentExecutor` (deprecated) — migrar a `create_agent` (LangChain 1.0) o StateGraph directamente
- ❌ Ignorar los CVEs documentados — actualizar a `langgraph>=1.0.10` y checkpointer packages actualizados

## Breaking Changes

| Versión | Cambio | Impacto |
|---|---|---|
| LangGraph 1.0 GA (Oct 2025) | API estable, sin breaking changes desde alpha | Low — compatible con alpha 1.0 |
| AgentExecutor → create_agent | Deprecation del AgentExecutor legacy | Medium — migrar antes de dic 2026 |
| LangGraph.js 0.4.x vs Python 1.2.x | Paridad de features incompleta | Low — TS no es producción-ready aún |

## Cambios entre versiones

| Fecha | Versión | Cambio |
|---|---|---|
| 2 sep 2025 | Alpha 1.0 | Alpha releases Python y JS |
| 22 oct 2025 | GA 1.0 | Lanzamiento conjunto LangChain 1.0 |
| 18 jun 2026 | 1.2.6 | Última versión estable |

## Impacto sobre otros sistemas

- **LangChain**: `create_agent` (LangChain 1.0) corre internamente sobre LangGraph runtime — son complementarios
- **LangSmith**: integración nativa para tracing y evaluación
- **LangGraph Platform**: deployment gestionado que abstrae infraestructura
- **MCP ecosystem**: LangGraph puede actuar como MCP server o cliente

## Referencias cruzadas

- [01_LANDSCAPE/projects.md](projects.md) — ecosistema OSS general
- [06_AGENTS/langgraph-deep.md](06_AGENTS/langgraph-deep.md) — deep dive (pendiente)
- [01_LANDSCAPE/crewai.md](crewai.md) — comparativa CrewAI (pendiente)
- [01_LANDSCAPE/autogen.md](autogen.md) — comparativa AutoGen (pendiente)
- [06_AGENTS/mcp.md](06_AGENTS/mcp.md) — MCP integration (pendiente)
- [07_MEMORY/chromadb.md](07_MEMORY/chromadb.md) — vector store (pendiente)

## Fuentes

1. https://github.com/langchain-ai/langgraph — Repo principal, acceso 2026-07-01
2. https://docs.langchain.com/oss/python/langgraph/overview — Docs oficiales LangGraph, acceso 2026-07-01
3. https://github.com/langchain-ai/langgraph/releases — Releases, acceso 2026-07-01
4. https://www.star-history.com/langchain-ai/langgraph — Star history, acceso 2026-07-01
5. https://agentmarketcap.ai/blog/2026/04/08/langgraph-fortune-500-production-stateful-multi-agent-workflows — Empresas en producción, acceso 2026-07-01
6. https://www.langchain.com/built-with-langgraph — Casos de producción, acceso 2026-07-01
7. https://www.abstractalgorithms.dev/from-langchain-to-langgraph-when-agents-need-state-machines — Arquitectura técnica, acceso 2026-07-01
8. https://dev.to/pockit_tools/langgraph-vs-crewai-vs-autogen-the-complete-multi-agent-ai-orchestration-guide-for-2026-2d63 — Comparativa frameworks, acceso 2026-07-01
9. https://sparkco.ai/blog/mastering-langgraph-checkpointing-best-practices-for-2025 — Checkpointing, acceso 2026-07-01
10. https://redis.io/blog/langgraph-redis-build-smarter-ai-agents-with-memory-persistence/ — Redis integration, acceso 2026-07-01
11. https://labs.cloudsecurityalliance.org/research/csa-research-note-langgraph-rce-chain-20260614-csa-styled/ — CVEs, acceso 2026-07-01
12. https://www.braincuber.com/blog/crewai-vs-autogen-vs-langgraph-multi-agent-framework-comparison — Benchmarks, acceso 2026-07-01
13. https://latenode.com/blog/platform-comparisons-alternatives/automation-platform-comparisons/langgraph-vs-autogen-vs-crewai-complete-ai-agent-framework-comparison-architecture-analysis-2025 — Análisis comparativo, acceso 2026-07-01
14. https://www.linkedin.com/posts/rraryan_langchain-langgraph-autogen-activity-7404395707476062208-UVeV — Cuándo usar cada framework, acceso 2026-07-01
15. https://github.com/redis-developer/langgraph-redis — Redis middleware repo, acceso 2026-07-01
16. https://docs.langchain.com/oss/python/langgraph/add-memory — Memory Store docs, acceso 2026-07-01

## Nivel de confianza

78% — 16 fuentes contrastadas, 5 snippets de código funcionales, 3 tablas comparativas, 8 hechos pendientes de validación independiente (stars exactas, versiones JS, CVEs confirmadas vía changelog, benchmarks).

## Pendientes

- [ ] Verificar estrellas exactas via GitHub API (fuentes reportan 34.1k–36.1k)
- [ ] Confirmar versión exacta de LangGraph.js 0.4.x (release más reciente)
- [ ] Distinguir entre empresas en beta (400+) vs deployments production documentados (20+)
- [ ] Confirmar que CVE-2025-67644, CVE-2026-28277, CVE-2026-27022 están parcheados verificando changelog
- [ ] Verificar metodología de benchmark "94% accuracy" vs "89% accuracy" — fuente braincuber.com
- [ ] Confirmar paridad de features LangGraph 1.0 en términos de API stability
- [ ] Verificar repo exacto del MCP adapter (langchain-mcp-adapters vs langgraph-mcp)
- [ ] Marcar cifras de benchmark (5.76X speed, 20% escalation) como "según fuente braincuber.com"

---

## Changelog

### 2026-07-01 — v1.0
- **Autor**: Aithera Escriba (`aithera-wiki-escriba`)
- **Cambio**: Síntesis del material crudo del investigador (90 hechos, 7 snippets, 3 tablas comparativas)
- **Validador**: Pendiente de auditoría
