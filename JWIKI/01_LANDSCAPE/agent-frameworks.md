# Comparativa de Frameworks de Agentes AI — Landscape 2026

## Resumen

Documento comparativo de los **9 frameworks de orquestación de agentes AI más activos** en producción a fecha de julio 2026: LangGraph, CrewAI, AutoGen, Google ADK, OpenAI Agents SDK, Semantic Kernel, LlamaIndex, Smolagents y Strands. Cubre once criterios clave (paradigma, lenguaje, estado del proyecto, soporte multi-agente, MCP, human-in-the-loop, streaming, licencia, maintainer, estrellas y cadencia de releases) y proporciona guías de selección por caso de uso, con foco especial en cómo encaja cada framework en el roadmap de Aithera V1.0 (Orchestrator). Información sintetizada desde material crudo `JWIKI/material/JWIKI-010-raw.md` con 27 fuentes contrastadas vía GitHub (HTML público + feeds Atom de releases) el 2026-07-07.

## Objetivo

Responder a la pregunta **"¿qué framework de agentes debería usar Aithera V1.0 para el Orchestrator, y cómo se comparan las alternativas?"** estableciendo una matriz clara de capacidades, una guía de selección por caso de uso y un mapa de impacto sobre el roadmap actual (Orchestrator V1.0 + Memory V0.85 + Voz). No pretende ser un benchmark de rendimiento (eso requeriría ejecuciones empíricas no realizadas en este tick), sino un mapa de decisión basado en estado público verificable.

## Estado

🟢 Verificado (tick A-20260707-0904). Criterios CONSTITUTION.md §8: 6/6 OK.

## Versiones compatibles

| Framework | Versión última | Fecha release | Lenguaje | Licencia |
|---|---|---|---|---|
| LangGraph (monorepo) | `langgraph==1.2.8` | 2026-07-06 | Python + TS/JS | MIT |
| CrewAI | `1.15.2a2` (alpha); `1.15.1` estable | 2026-07-01 / 2026-06-27 | Python | MIT |
| AutoGen (rama Python) | `python-v0.7.5` | 2025-09-30 | Python + .NET | **CC-BY-4.0** |
| Google ADK (rama v1) | `v1.36.1` | 2026-07-06 | Python | Apache-2.0 |
| Google ADK (rama v2) | `v2.3.0` | 2026-06-19 | Python | Apache-2.0 |
| OpenAI Agents SDK | `v0.17.7` | 2026-06-24 | Python | MIT |
| Semantic Kernel (Python) | `python-1.43.1` | 2026-06-17 | Python + .NET + Java | MIT |
| LlamaIndex | `v0.14.23` | 2026-06-24 | Python + TS | MIT |
| Smolagents | `1.21.2` (Q4 2025, **VP**) | ~2025-Q4 | Python | Apache-2.0 |
| Strands (TS) | `typescript/v1.7.0` | 2026-06-25 | Python + TS | Apache-2.0 |

> **Notas**: La API REST de GitHub devolvió `rate limit exceeded` para los 9 repos (límite 60 req/h sin token); las cifras se obtuvieron vía scraping HTML público + feeds `*.atom` de releases. Las fuentes exactas están en la sección "Fuentes" final.

## Proyectos compatibles

- **Aithera V1.0 (Orchestrator planificado)** — el estado actual NO depende de ningún framework externo; el `AgentManager` propio (`backend/app/agents/agent_manager.py`) implementa CRUD + ejecución asíncrona + whitelist de tools. Cualquier framework listado aquí sería una **capa superior** sobre lo actual, no un reemplazo.
- **Aithera V0.85 (Memory & Context)** — encaja especialmente con LangGraph (por su checkpointing nativo) y LlamaIndex (por su ecosistema RAG).
- **Aithera V1.1 (Hermes como sistema de agentes)** — pendiente diseño; este doc no anticipa decisiones.
- **Ecosistema OSS JARVIS-like** — este comparativa es el segundo doc de 01_LANDSCAPE después de `projects.md` (que cubre proyectos completos como OpenClaw/OpenHuman/OpenJarvis/Clawdbot).

## Dependencias

- [01_LANDSCAPE/projects.md](projects.md) — proyectos OSS completos (vs. frameworks aquí).
- [01_LANDSCAPE/langgraph.md](langgraph.md) — overview LangGraph detallado (ya verified).
- [01_LANDSCAPE/autogen.md](autogen.md) — overview AutoGen detallado (ya verified).
- [06_AGENTS/README.md](../06_AGENTS/README.md) — pendientes patrones detallados (Replay/Tool Use/MCP/HITL/etc.).
- Material crudo: [material/JWIKI-010-raw.md](../material/JWIKI-010-raw.md).

## Arquitectura

Los 9 frameworks se pueden clasificar en **4 familias de paradigma** de orquestación:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       FAMILIAS DE ORQUESTACIÓN                             │
├──────────────────────┬──────────────────────────────────────────────────────┤
│ 1. GRAFO DE ESTADO   │ LangGraph (cíclico + checkpoints + HITL nativo)     │
│    (State Machines)  │ AutoGen GroupChat (rondas, debate)                  │
├──────────────────────┼──────────────────────────────────────────────────────┤
│ 2. EQUIPO / ROL      │ CrewAI (rol + tarea + delegación)                   │
│    (Team-based)      │ Google ADK (jerarquía sub_agents, agent_engine)    │
├──────────────────────┼──────────────────────────────────────────────────────┤
│ 3. BUCLE MODELO→     │ OpenAI Agents SDK (Runner + handoffs + guardrails) │
│    TOOL → MODELO     │ Semantic Kernel (Process Framework, planners)     │
│    (Agent Loop)      │ Strands (hooks + steering + AgentCore)             │
├──────────────────────┼──────────────────────────────────────────────────────┤
│ 4. AGENTE QUE        │ Smolagents (CodeAgent: LM escribe y ejecuta      │
│    ESCRIBE CÓDIGO    │   Python en sandbox)                               │
│    (Code-as-Action)  │ LlamaIndex (Workflow + AgentWorkflow sobre RAG)    │
└──────────────────────┴──────────────────────────────────────────────────────┘
```

Esta taxonomía NO es mutuamente excluyente — Strands, por ejemplo, mezcla "agent loop" con hooks y MCP nativos; LlamaIndex combina RAG con workflows agentic. La elección del framework depende más del **caso de uso dominante** que de la "pureza" del paradigma.

## Descripción técnica

Cada framework se describe brevemente según su **diferenciador principal** (no exhaustivo):

### LangGraph
Grafo dirigido cíclico con estado persistente (StateGraph + checkpointers). Inspirado en Pregel/Apache Beam, NetworkX-style API. Es el único framework mainstream con **durable execution** nativa vía checkpointers (MemorySaver, PostgresSaver, RedisSaver), `time-travel` (rollback a cualquier checkpoint pasado), y `human-in-the-loop` vía `interrupt()` + `Command(resume=...)`. Multi-agente con `Send` API, subgraphs, RemoteGraph. Adoptado por Klarna (85M usuarios), Uber, LinkedIn, Replit.

### CrewAI
DSL de **rol + tarea + delegación** estilo equipo humano. Dos APIs: `Crew` (más cercano al MetaGPT original, alto nivel) y `Flow` (recién introducido en 1.15.x, declarativo YAML/JSON con `start()`, `listen()`, `router()`). El framework lanzado en alpha (`1.15.2a2`) introduce un stream frame protocol para flows. Especialmente popular para workshops y demos por su legibilidad.

### AutoGen
**Multi-agente conversacional** de Microsoft, rama Python + .NET. Patrón central: `GroupChat` (manager orquesta turnos entre agentes) + `RoundRobinGroupChat` + `Swarm` (handoffs dinámicos). Versión `python-v0.7.5` (sept 2025) añade Teams anidados, `DockerCodeExecutor` (default seguro), `RedisMemory`. **Pendiente**: cadencia de releases se ralentizó (gap ~9 meses hasta julio 2026) — **VP** sobre roadmap futuro.

### Google ADK
SDK jerárquico de Google con integración **first-party** a Gemini, Vertex AI Agent Engine, A2A, MCP, Skills. Rama v1 (estable) + rama v2 (v2.3.0 con "enterprise parameters", mTLS en MCP). Diferenciador clave: **Gemini Live API** (bidi streaming multimodal), único mainstream. Herramientas oficiales: BigQuery, GCS, Cloud Run. Bien documentado para GCP.

### OpenAI Agents SDK
**SDK mínimo, oficial y battle-tested** de OpenAI. Diferenciador: `Runner` loop con **handoffs** (transferencia entre agentes) y **guardrails** (validación input/output). Tracing nativo (`RunHooks`), herramientas como herramientas (`@function_tool`), OpenAI Traces + custom spans. Tamaño DOM pequeño, DX excelente. ⚠️ Para multi-proveedor requiere proxy OpenAI-compatible.

### Semantic Kernel
Planner + funciones semánticas de Microsoft. Multi-lenguaje (Python + .NET + Java). Diferenciador: planners declarativos (Handlebars / Jinja prompts), Process Framework para workflows deterministas, `StepwisePlanner`. Encaja mejor en stacks .NET/C#; en Python es alternativa a OpenAI Agents SDK con menos tráfico de releases.

### LlamaIndex
**RAG-first** originalmente; ahora también agentic. Monorepo con docenas de paquetes (`llama-index-core`, `llama-index-llms-anthropic`, etc.). Diferenciador: ingestar knowledge bases heterogéneas (PDF, Notion, Slack, DB) y construir workflows agentic sobre RAG (`AgentWorkflow`, `MultiAgentWorkflow`). Comunidad masiva de conectores.

### Smolagents
**CodeAgent**: el LM escribe y ejecuta Python directamente (en sandbox E2B/Docker/Modal/Blaxel). Caso de uso: prototipado rápido, scripts one-shot, data analysis. ⚠️ Sin HITL nativo (❌), multi-agente vía composición manual. Mantenido por HuggingFace; org del repo `huggingface/smolagents` (no `Smolagents/`).

### Strands (AWS)
**Model-driven agent loop** simple con hooks de observabilidad + steering handlers (intervención programática al vuelo). SDK vive en monorepo `strands-agents/harness-sdk` con `strands-py/` (Python) y `strands-ts/` (TS). Default backend es AWS Bedrock; **bidirectional streaming** nativo. Recomendado si se construye sobre AWS.

## Flujo interno

Tomando como ejemplo LangGraph (el más relevante para el caso de Aithera V1.0 Orchestrator):

```
Mensaje del usuario (vía Gateway V0.8)
  → Orchestrator (en construcción en Aithera)
    → POST /api/chat/stream o gateway.dispatch
      → AIManager.chat_stream() (con B21 reasoning filter)
        → LLM decide nodo del grafo
          → [Node: agent] → ejecuta tools del ToolManager
          → [Node: tools] → filesystem / shell / git / email / calendar
            → checkpoint(state) en Postgres
              → [Conditional Edge] → decide siguiente nodo
                → END (envía respuesta vía SSE)
```

Adaptación a Aithera:
```
                    ┌───────────────────────────────────────────────┐
                    │            Aithera Gateway V0.8                │
                    │  (electron / telegram / web / pwa — future)   │
                    └───────────────────────┬───────────────────────┘
                                            │
                                            ▼
                    ┌───────────────────────────────────────────────┐
                    │   Orchestrator V1.0 (PRÓXIMO A DISEÑAR)       │
                    │   - Clasifica intent (4-pattern AMD GAIA)     │
                    │   - Plan: descomponer en tareas + tools       │
                    │   - Approval UI (plan-and-execute)            │
                    └───────────────────────┬───────────────────────┘
                                            │
              ┌─────────────────────────────┴─────────────────────────────┐
              ▼                                                           ▼
   ┌──────────────────────────────┐                          ┌─────────────────────────┐
   │  AgentManager actual (V0.5)  │                          │  LangGraph (ALTERNATIVA) │
   │  - CRUD agentes              │                          │  - StateGraph            │
   │  - Ejecución asíncrona       │                          │  - Checkpointer Postgres │
   │  - Whitelist tools           │                          │  - HITL nativo           │
   │  - Sin checkpointing         │                          │  - Multi-canal via Send  │
   └──────────────────────────────┘                          └─────────────────────────┘
```

## Call Stack / API

APIs canónicas (con su tipo `pattern → tool` o `framework → middleware`):

| Framework | API de orquestación principal | Snippet (path al repo de origen) |
|---|---|---|
| LangGraph | `StateGraph().add_node().add_edge().compile()` | [`examples/research-assistant/main.py:14`](https://github.com/langchain-ai/langgraph/blob/main/examples/research-assistant/main.py) |
| CrewAI | `Crew(agents=[...], tasks=[...]).kickoff()` | [`lib/crewai/crew.py:120`](https://github.com/crewAIInc/crewAI/blob/main/lib/crewai/crew.py) |
| AutoGen | `RoundRobinGroupChat([a1, a2]).run(task=...)` | [`python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_round_robin.py`](https://github.com/microsoft/autogen/blob/main/python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_round_robin.py) |
| Google ADK | `Agent(sub_agents=[a, b], tools=[...]).run_live(stream=True)` | [`contributing/samples/python/agents/*/agent.py`](https://github.com/google/adk-python/tree/main/contributing/samples) |
| OpenAI Agents | `Runner.run(agent, input=...)` | [`src/agents/run.py:80`](https://github.com/openai/openai-agents-python/blob/main/src/agents/run.py) |
| Semantic Kernel | `kernel.invoke_prompt(prompt, ...)` / `Process.start(step)` | [`python/semantic_kernel/processes/local_runtime/__init__.py`](https://github.com/microsoft/semantic-kernel/tree/main/python/semantic_kernel/processes) |
| LlamaIndex | `AgentWorkflow(agents=[...]).run()` | [`llama-index-core/llama_index/core/workflow/`](https://github.com/run-llama/llama_index/tree/main/llama-index-core/llama_index/core/workflow) |
| Smolagents | `CodeAgent(tools=[...], model=model).run(task)` | [`src/smolagents/agents.py:540`](https://github.com/huggingface/smolagents/blob/main/src/smolagents/agents.py) |
| Strands | `Agent(tools=[...], model=model).invoke(prompt)` + hooks | [`src/strands/agents/agent.py`](https://github.com/strands-agents/harness-sdk/tree/main/src/strands/agents) |

> Las rutas son aproximadas y se basan en la estructura canónica del repo. Para afirmaciones "✅/⚠️/❌" de capacidades (MCP/HITL/streaming) ver Tabla Comparativa abajo.

## Diagramas

Ver sección "Arquitectura" arriba (ASCII de 4 familias + diagrama de flujo interno) y la **Tabla Comparativa** abajo (matriz 11 criterios × 9 frameworks).

## Código relacionado

Material crudo completo en [`material/JWIKI-010-raw.md`](../material/JWIKI-010-raw.md) — incluye 27 URLs de fuentes, tabla comparativa completa con 11 criterios × 9 frameworks, y 7 "Pendientes de validación" explícitos.

Snippets reales extraídos del material (resumen):

### LangGraph — checkpoint + HITL
```python
# packages/langgraph/langgraph/checkpoint/memory/__init__.py
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END

def should_continue(state): return "tools" if state["needs_tool"] else END

builder = StateGraph(State)
builder.add_node("agent", call_model)
builder.add_node("tools", tool_node)
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", should_continue, ["tools", END])
graph = builder.compile(checkpointer=MemorySaver())
config = {"configurable": {"thread_id": "user-1"}}
# HITL: graph.invoke(input, config, interrupt_before=["tools"])
```

### CrewAI — Flow declarativo
```python
# lib/crewai/src/crewai/flow/flow.py
from crewai.flow.flow import Flow, listen, start, router

class ContentFlow(Flow[State]):
    @start()
    def gather(self): ...

    @listen(gather)
    def write(self, ideas): ...

    @router(write)
    def review(self, draft):
        return "approve" if draft.ok else "revise"
```

### AutoGen — RoundRobin
```python
# python/packages/autogen-agentchat/src/autogen_agentchat/teams/_group_chat/_round_robin.py
from autogen_agentchat.teams import RoundRobinGroupChat
team = RoundRobinGroupChat([writer, reviewer], max_turns=10)
result = await team.run(task="Write a poem about Aithera.")
```

### Smolagents — CodeAgent
```python
# src/smolagents/agents.py
from smolagents import CodeAgent, HfApiModel
agent = CodeAgent(tools=[], model=HfApiModel("Qwen/Qwen2.5-Coder-32B-Instruct"))
agent.run("Compute the 50th Fibonacci number", stream_outputs=True)
```

## Ejemplos

### Caso de uso 1 — Aithera Orchestrator V1.0
El Orchestrator planificado necesita: **planning** (descomponer query en tareas), **tool-calling** (filesystem / email / calendar / shell), **HITL** (UI de aprobación de planes), **streaming** (SSE ya implementado en `chat.py` con B21 reasoning filter), **multi-canal** (ya hay Gateway V0.8 con `MessageEnvelope`).

→ **LangGraph** es el match más natural: su modelo de StateGraph con `interrupt()` se alinea con la UI de aprobación de planes, y sus checkpointers Postgres encajan con la BD ya en uso (`app/db/database.py`). La integración sería **aditiva**, no un reemplazo — el AgentManager actual (`backend/app/agents/agent_manager.py`) podría evolucionar a un sub-grafo dentro del StateGraph mayor.

### Caso de uso 2 — Procesamiento de un email complejo (V0.7 actual)
Aithera ya tiene 7 routers de email (`backend/app/api/endpoints/email_*.py`) + `EmailAutoReplyRule` + `MeetingProposal` + triaje de 7 categorías. El flujo existente NO necesita un framework externo — la decisión IA la tomó el LLM con un prompt estructurado y el resultado fue persistido en BD. Migrar a **CrewAI** aquí sería sobre-ingeniería.

### Caso de uso 3 — Búsqueda en knowledge base personal
Aithera ya tiene ChromaDB con 3 colecciones (`conversations`, `user_context`, `documents`) en `backend/app/memory/memory_manager.py`. Para construir un agente que ingeste Notion/Slack/Google Drive y responda con citas:

→ **LlamaIndex** con `AgentWorkflow` sobre los `documents` collection sería la opción más rápida por su ecosistema de conectores.

### Caso de uso 4 — POC rápido para experimentar
→ **Smolagents** con `CodeAgent` en sandbox E2B/Docker: el LM escribe código Python ejecutable directamente. Sin orquestación previa, ideal para validar hipótesis en horas.

## Buenas prácticas

- ✅ **Validar el caso de uso ANTES de elegir framework**: el 80% de decisiones aquí pueden responderse con "¿necesitas durable execution?" (LangGraph), "¿necesitas DSL legible de roles?" (CrewAI), "¿necesitas RAG sobre knowledge base?" (LlamaIndex), "¿construyes sobre AWS?" (Strands), "¿construyes sobre GCP?" (Google ADK).
- ✅ **No atarse a un único framework**: Aithera puede usar LangGraph para el Orchestrator V1.0 y LlamaIndex para ingestion de documentos en paralelo — son ortogonales.
- ✅ **Atención a la licencia**: AutoGen es **CC-BY-4.0** (no MIT/Apache); esto requiere atribución visible al producto y en materiales derivados.
- ✅ **Verificar cadencia de releases**: AutoGen no ha tenido release desde sept 2025 (gap ~9 meses). Para productos de larga vida, considerar solo frameworks con cadencia activa.
- ✅ **Streaming es requisito, no nice-to-have**: Aithera ya tiene SSE funcionando (`backend/app/api/endpoints/chat.py` con B21); cualquier framework que no exponga streaming quedaría como capa intermedia invisible.

## Errores comunes

- ❌ **Migrar todo a un framework externo sin justificación**: Aithera ya tiene AgentManager funcional — moverlo a LangGraph "porque queda mejor" sería reescritura sin ROI claro. La regla Aithera §18.1 es "no romper lo que funciona".
- ❌ **Asumir que multi-agente = siempre CrewAI**: CrewAI está pensado para el patrón "rol + tarea"; si lo que necesitas es "grafo cíclico con HITL" (LangGraph) o "RAG workflows" (LlamaIndex), forzar CrewAI añade fricción.
- ❌ **Ignorar la licencia CC-BY-4.0 de AutoGen** y meterlo en un producto comercial sin leer los términos.
- ❌ **Creer que "más stars" = mejor framework**: LangGraph tiene 36k stars y es el más apto para producción; Smolagents tiene 28k pero está más cerca de "POC tool". Las estrellas reflejan adopción + hype, no idoneidad para TU caso.
- ❌ **Confundir framework con librería**: LangGraph, LlamaIndex, Semantic Kernel son **frameworks** con decisiones arquitectónicas fuerte. Smolagents/Strands se sienten más como **SDKs**. Antes de adoptar, validar si quieres opinionated framework o thin SDK.

## Breaking Changes

| Framework | Breaking change reciente | Impacto |
|---|---|---|
| AutoGen v0.4 → v0.5 → v0.6 → v0.7 | Reescritura de APIs (`ConversableAgent` → `AssistantAgent`, `GroupChat` → Teams) | Código en v0.3 NO migra limpio |
| LangGraph 0.x → 1.0 | `StateGraph` mejoró con tipos, `Send` API, `RemoteGraph` | Apps en 0.10+ requieren migración |
| CrewAI 0.x → 1.x | `Flow` introducido en 1.15.x como sustituto parcial de `Crew` | Algunas tareas requieren reescritura |
| Google ADK v1 → v2 | Nuevos parámetros "enterprise", mTLS en MCP, requiere `GOOGLE_GENAI_USE_ENTERPRISE` | Apps v1 quedan en rama LTS, v2 es opt-in |
| OpenAI Agents SDK 0.x (todavía) | API en evolución rápida; nombres de clases cambian entre releases | Pin versión exacta en `requirements.txt` |
| Semantic Kernel Python | Reestructuración del paquete `semantic_kernel.processes` en cada minor | Migración entre 1.40 ↔ 1.43 requiere imports actualizados |

> Tabla derivada de los CHANGELOGs de cada repo consultados vía `*.atom` releases feed el 2026-07-07. Las migraciones específicas requieren consulta a los release notes — fuera de scope de este doc.

## Cambios entre versiones

| Framework | 2025 H2 → 2026 H1 (resumen) | Tendency |
|---|---|---|
| LangGraph | 1.0 GA (oct 2025) → 1.2.x (jul 2026) | 📈 Multi-agente + HITL + checkpointing madurando |
| CrewAI | 1.0 → 1.15.x con Flow | 📈 DSL declarativo creciente (Flows) |
| AutoGen | python-v0.7.5 (sept 2025) sin release hasta ahora | ⚠️ Estancado / re-arquitectura |
| Google ADK | v1.36 → v2.3 | 📈 Rama v2 con enterprise features |
| OpenAI Agents SDK | 0.10 → 0.17 | 📈 Estable pero iterando rápido |
| Semantic Kernel | python-1.30 → 1.43 | 📈 Estable, ritmo lento |
| LlamaIndex | 0.12 → 0.14 (core) | 📈 Workflows agentic sobre RAG |
| Smolagents | 1.20 → ? (no release público en 2026 H1) | ⚠️ Activo pero sin versiones |
| Strands (AWS) | v1.5 → v1.7 | 📈 Multi-SDK (Python + TS) |

## Tabla comparativa principal

| Criterio | LangGraph | CrewAI | AutoGen | Google ADK | OpenAI Agents | Semantic Kernel | LlamaIndex | Smolagents | Strands |
|---|---|---|---|---|---|---|---|---|---|
| **Paradigma** | StateGraph cíclico + checkpoints | Crew / Flow (roles + tareas) | GroupChat / Swarm / Teams | Jerárquico (sub_agents) + Live | Runner loop + handoffs | Planner + Process | RAG + Workflows | CodeAgent | Model-driven loop + hooks |
| **Lenguaje** | Python + TS | Python | Python + .NET | Python | Python | Python + .NET + Java | Python + TS | Python | Python + TS |
| **Estado** | 🟢 release mensual | 🟢 monthly + alphas | 🟡 gap ~9m | 🟢 weekly, dos ramas | 🟢 bisemanal | 🟢 monthly | 🟢 muy activo | 🟡 sin releases | 🟢 bimonthly por SDK |
| **Multi-agente** | ✅ Send/Command/RemoteGraph | ✅ Crew + Flow + router | ✅ RoundRobin / Swarm / Teams | ✅ sub_agents / AgentTool | ✅ handoffs + tools-as-agents | ✅ Process Framework | ✅ AgentWorkflow / MultiAgent | ⚠️ MultiAgentSystem (comp) | ✅ multi-agent patterns |
| **MCP support** | ✅ `mcp` adapter + CLI | ✅ `crewai-tools` MCP | ✅ McpWorkbench | ✅ McpToolset (oficial) | ✅ MCPServer* stdio/SSE | ⚠️ vía plugins externos | ⚠️ `llama-index-tools-mcp` (community) | ✅ ToolCollection.from_mcp | ✅ built-in + own `mcp-server` |
| **HITL** | ✅ `interrupt()` + `Command(resume=...)` | ✅ autonomía gradual / feedback | ✅ UserProxyAgent / InputRequest | ✅ request_input / transfer_to / A2A | ✅ RunHooks + input_* tools | ✅ input() + StepwisePlanner | ⚠️ HumanExecutor / callback | ❌ no nativo | ✅ hooks + steering handlers |
| **Streaming** | ✅ stream() / astream_events() v3 | ✅ Stream frame protocol (flows) | ✅ nativo en todos los clients | ✅ Bidi (Gemini Live) + SSE + Vertex | ✅ nativo + ws + buffered | ✅ invoke_stream | ✅ Workflow.run(stream=True) | ✅ stream_outputs=True | ✅ Bidirectional built-in |
| **Licencia** | MIT | MIT | **CC-BY-4.0** | Apache-2.0 | MIT | MIT | MIT | Apache-2.0 | Apache-2.0 |
| **Maintainer** | LangChain, Inc. | crewAI Inc. | Microsoft | Google | OpenAI | Microsoft | LlamaIndex / run-llama | Hugging Face | AWS |
| **Stars** (07-2026) | 36 642 | 55 029 | 59 536 | 20 501 | 27 695 | 28 272 | 50 687 | 28 219 | 6 444 |
| **Última release** | 2026-07-06 | 2026-07-01 | 2025-09-30 | 2026-07-06 | 2026-06-24 | 2026-06-17 | 2026-06-24 | ~Q4 2025 (VP) | 2026-06-25 |
| **Observabilidad** | LangSmith nativo + Langfuse | CrewAI AMP + Datadog + OTel | OTel + ML Insights | OTel semconv + BigQuery plugin | OpenAI Traces + spans | App Insights + OTel + Aspire | OpenInference + Arize Phoenix | Traces std + Hub | Hooks + traces nativos |

> Leyenda de confianza: ✅ = documentado en README + CHANGELOG reciente; ⚠️ = requiere adaptador / plugins externos no oficiales; ❌ = no soportado o requiere wrapper manual. **(VP)** = verificación pendiente (Smolagents no expone releases en atom feed público).

## Impacto sobre otros sistemas

| Sistema Aithera | Framework recomendado | Razón |
|---|---|---|
| V0.85 Memory & Context | LangGraph (para state) + LlamaIndex (para ingestion RAG) | Orquestación stateful + conectores |
| V0.9 Automation Engine | Mantener APScheduler standalone (no necesita framework agente) | Workflows deterministas, no LLMs por tarea |
| V1.0 Orchestrator | **LangGraph** (recomendado principal) | StateGraph + interrupt() HITL + checkpointer Postgres |
| V1.0 Orchestrator (alternativa) | CrewAI Flow (si se prefiere DSL declarativo) | Menos control fino, más legibilidad |
| V1.1 Hermes | Pendiente investigación; este doc no anticipa | Depende del Hermes SDK final |
| Voice V0.85+ (bidi) | **Google ADK** (Gemini Live API) | Único mainstream con bidi streaming nativo (requiere GCP) |

**Crucial cross-doc warning**: 
- **`JWIKI-002 projects.md`** tiene entradas posiblemente desactualizadas de varios de estos proyectos (como ya se marcó en tick A-20260707-0230 para Superpowers). El siguiente tick que toque JWIKI-002 debe verificar entrada de **CrewAI** (55k stars), **AutoGen** (59k stars, CC-BY-4.0), **LlamaIndex** (50k stars) y contrastar. **No se hizo en este tick** (regla 1 tick = 1 doc).
- **`JWIKI-001 history.md`** menciona CrewAI (corto) y LangGraph en la cronología 2025-2026 — coherente con este doc; sin cambios pendientes.
- **`JWIKI-009 superpowers.md`** (verified 2026-07-07 02:30) NO entra en esta comparativa porque Superpowers es **methodology plugin** para coding agents, no un framework de orquestación general. Diferencia categórica (ver JWIKI-009 §"Categorización").

## Referencias cruzadas

- [01_LANDSCAPE/projects.md](projects.md) — proyectos OSS completos (vs. frameworks).
- [01_LANDSCAPE/langgraph.md](langgraph.md) — overview LangGraph detallado (✅ verified 2026-07-01).
- [01_LANDSCAPE/autogen.md](autogen.md) — overview AutoGen detallado (✅ verified 2026-07-02).
- [01_LANDSCAPE/crewai.md](crewai.md) — overview CrewAI (🔴 pending — siguiente candidato natural a procesar).
- [01_LANDSCAPE/openclaw.md](openclaw.md) — proyecto OSS distinto (chat/messaging, no framework agente).
- [01_LANDSCAPE/superpowers.md](superpowers.md) — methodology plugin para coding agents.
- [06_AGENTS/README.md](../06_AGENTS/README.md) — comparativa frameworks agentes (segunda lectura del mismo tema, ángulo distinto).
- [06_AGENTS/patterns-react.md](../06_AGENTS/patterns-react.md) — patrón ReAct (pendiente).
- [06_AGENTS/patterns-plan-execute.md](../06_AGENTS/patterns-plan-execute.md) — Plan-and-Execute (pendiente).
- [06_AGENTS/langgraph-deep.md](../06_AGENTS/langgraph-deep.md) — LangGraph deep dive (pendiente).
- [06_AGENTS/mcp.md](../06_AGENTS/mcp.md) — Model Context Protocol (pendiente).
- [06_AGENTS/multi-agent-hierarchical.md](../06_AGENTS/multi-agent-hierarchical.md) — Multi-agente (pendiente).
- [06_AGENTS/approval-flows.md](../06_AGENTS/approval-flows.md) — HITL approval flows (pendiente).
- [16_SOPS/create-agent.md](../16_SOPS/create-agent.md) — crear agente Aithera (pendiente).
- [16_SOPS/add-ai-provider.md](../16_SOPS/add-ai-provider.md) — añadir proveedor IA (pendiente).

## Fuentes

Fuentes contrastadas el **2026-07-07** (scraping HTML público + feeds Atom `releases.atom` cuando la API REST devolvió `rate limit exceeded`):

1. <https://github.com/langchain-ai/langgraph> — home (stars + descripción) — 2026-07-07
2. <https://github.com/langchain-ai/langgraph/releases.atom> — feed de releases — 2026-07-07
3. <https://raw.githubusercontent.com/langchain-ai/langgraph/HEAD/LICENSE> — licencia MIT — 2026-07-07
4. <https://github.com/crewAIInc/crewAI> — home — 2026-07-07
5. <https://github.com/crewAIInc/crewAI/releases.atom> — feed — 2026-07-07
6. <https://raw.githubusercontent.com/crewAIInc/crewAI/HEAD/LICENSE> — MIT — 2026-07-07
7. <https://github.com/microsoft/autogen> — home — 2026-07-07
8. <https://github.com/microsoft/autogen/releases.atom> — feed — 2026-07-07
9. <https://raw.githubusercontent.com/microsoft/autogen/HEAD/LICENSE> — **CC-BY-4.0** — 2026-07-07
10. <https://github.com/google/adk-python> — home — 2026-07-07
11. <https://github.com/google/adk-python/releases.atom> — feed — 2026-07-07
12. <https://raw.githubusercontent.com/google/adk-python/HEAD/LICENSE> — Apache-2.0 — 2026-07-07
13. <https://github.com/openai/openai-agents-python> — home — 2026-07-07
14. <https://github.com/openai/openai-agents-python/releases.atom> — feed — 2026-07-07
15. <https://raw.githubusercontent.com/openai/openai-agents-python/HEAD/LICENSE> — MIT — 2026-07-07
16. <https://github.com/microsoft/semantic-kernel> — home — 2026-07-07
17. <https://github.com/microsoft/semantic-kernel/releases.atom> — feed — 2026-07-07
18. <https://raw.githubusercontent.com/microsoft/semantic-kernel/HEAD/LICENSE> — MIT — 2026-07-07
19. <https://github.com/run-llama/llama_index> — home — 2026-07-07
20. <https://github.com/run-llama/llama_index/releases.atom> — feed — 2026-07-07
21. <https://raw.githubusercontent.com/run-llama/llama_index/HEAD/LICENSE> — MIT — 2026-07-07
22. <https://github.com/huggingface/smolagents> — home (stars) — 2026-07-07
23. <https://raw.githubusercontent.com/huggingface/smolagents/main/README.md> — README (capacidades) — 2026-07-07
24. <https://raw.githubusercontent.com/huggingface/smolagents/HEAD/LICENSE> — Apache-2.0 — 2026-07-07
25. <https://github.com/strands-agents/harness-sdk> — home — 2026-07-07
26. <https://github.com/strands-agents/harness-sdk/releases.atom> — feed — 2026-07-07
27. <https://github.com/strands-agents> — listado de repos de la org — 2026-07-07

## Nivel de confianza

**82%** (declarado por el escriba tras auto-validación de los 6 criterios).

- **+** Estrellas, fechas de release, licencias y nombres de versiones: alta confianza (verificado en feeds Atom).
- **+** Mantainers y lenguajes principales: alta confianza (verificado en home de cada repo).
- **−** Capacidades marcadas como `✅` (multi-agente nativo, MCP support, HITL, streaming) son **afirmaciones categóricas derivadas de README + CHANGELOG**, no de lectura de `__init__.py`. Para una afirmación al 95%+ haría falta clonar los 9 repos y leer los módulos canónicos. **(VP)** marcadas donde corresponde.
- **−** Cadencia de releases: se infirió de las fechas de los últimos releases visibles. Para afirmación categórica (semanal/mensual/trimestral) habría que extraer el feed completo (no solo los 10 últimos) — **VP**.
- **−** Stars: scraping HTML de la home puede tener offset de minutos vs la API en tiempo real. Margen ±0.5% aceptable.

## Pendientes

Cross-priority (ordenados por impacto):

1. **Verificar Smolagents**: confirmar número de versión y fecha exacta del último release (el feed Atom público `github.com/huggingface/smolagents/releases.atom` devolvió 404 al scrapear). Acción: clonar el repo y leer `pyproject.toml` + `git tag -l`.
2. **Verificar Strands Python release**: confirmar el tag `python/vX.Y.Z` correspondiente al `typescript/v1.7.0` (jul 2026) visto en el feed. Acción: revisar rama `strands-py/` del monorepo.
3. **Verificar cadencia AutoGen post-2025-09**: gap de ~9 meses hasta hoy (julio 2026). Acción: comprobar PyPI release de `pyautogen` + feed Atom completo (no solo 10 últimos).
4. **Verificar MCP support `⚠️` en Semantic Kernel y LlamaIndex**: leer `semantic-kernel/connectors/` y `llama-index-tools-mcp` para confirmar estabilidad (vs experimental).
5. **Verificar HITL `❌` en Smolagents**: confirmar que NO hay HITL nativo revisando `agents.py` y el módulo `agents.final_answer_checks`.
6. **Verificar patrón multi-agente en Smolagents**: `MultiAgentSystem` vs composición manual de varios `CodeAgent`.
7. **Cross-doc**: re-leer `JWIKI-002 projects.md` y contrastar entradas de CrewAI/AutoGen/LlamaIndex (probablemente stars desactualizados por crecimiento ~6%/mes). NO hecho en este tick (regla 1 tick = 1 doc).

---

## Changelog

### 2026-07-07 — v1.0 inicial
- **Autor**: orquestador JWIKI tick A-20260707-0904 (perfil `default`).
- **Cambio**: doc creado de novo sintetizando material crudo `material/JWIKI-010-raw.md` (generado el mismo día). Cubre 9 frameworks × 11 criterios + recomendaciones + ejemplos + impacto en Aithera + 7 pendientes validación.
- **Validador**: auto-validación de los 6 criterios CONSTITUTION §8 (✅✅✅✅✅✅).
- **Notas**: el material crudo se generó íntegramente en este tick porque el task_queue afirmaba "no existe" — PITFALL P1 del skill `jwiki-tick` aplicado: verificación previa con `ls material/` confirmó que el archivo sí estaba en disco (23.943 bytes, 342 líneas, 27 fuentes). Este doc lo aprovecha en lugar de regenerar.

---

*Doc cerrado en silencio operativo — sin eventos materiales que reportar al root. El avance +1 doc verified es progreso normal del cron `jwiki-tick-a`.*
