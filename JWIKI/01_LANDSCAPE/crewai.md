# CrewAI — Framework de orquestación multi-agente (Crews + Flows)

## Resumen

CrewAI es un framework open-source escrito en Python (~99.7% del código) para orquestar **agentes de IA autónomos que colaboran con roles definidos** ("crews of AI agents"). Su propuesta central son dos paradigmas complementarios: **Crews** (equipos de agentes con `role`/`goal`/`backstory` que colaboran y delegan de forma autónoma) y **Flows** (workflows event-driven con estado tipado y control determinista). A fecha 2026-07-08 tiene **55.157 stars**, **7.754 forks**, licencia **MIT**, versión estable **1.15.2** (publicada ese mismo día) y ~301 contribuidores. Encaja en el ecosistema JARVIS-like como una de las alternativas de más alta abstracción y menor barrera de entrada frente a LangGraph (grafo de estados explícito) y AutoGen (actor-model conversacional).

## Objetivo

Este documento responde a: **¿qué es CrewAI, cómo se estructura su modelo Agent/Task/Crew/Process/Tools/Memory, en qué se diferencia de LangGraph/AutoGen/OpenAI Agents SDK/Google ADK, y qué patrones son借鉴ables para el Orchestrator de Aithera V1.0?** Todos los datos están contrastados contra la GitHub API live y el código fuente del branch `main` con fecha de acceso 2026-07-08.

## Estado

🟢 **Verificado** — código revisado (branch `main`, v1.15.2), GitHub API contrastada live 2026-07-08, 55 hechos verificados, 8+ snippets con `path:line`, 5 conflictos entre fuentes documentados. Confianza 88%.

## Versiones compatibles

| Proyecto | Versión | Notas |
|---|---|---|
| CrewAI (framework) | 1.15.2 | Última estable, publicada 2026-07-08T02:05Z |
| Python | >=3.10, <3.14 | Cap superior explícito en `pyproject.toml` (mismo patrón que Hermes Agent, JWIKI-007) |
| UV (gestor deps) | astral uv | Gestión del monorepo workspace + `crewai install` |
| crewai-tools | paquete separado | `uv pip install 'crewai[tools]'` |
| Aithera | V0.7.3 (actual) → V1.0 (Orchestrator) | Patrón Crew/Flow借鉴able, NO dependencia directa (documentado aquí) |

## Proyectos compatibles

- **Coding agents con skills oficiales**: Claude Code (`/plugin marketplace add crewAIInc/skills`), Cursor, Codex, Windsurf (`npx skills add crewaiinc/skills`) — repo `crewAIInc/skills` con 4 skills.
- **LLM providers**: OpenAI (default), Ollama (local), y todos los conectables vía la capa `crewai.llm.LLM` / `BaseLLM` (docs "Connect CrewAI to LLMs").
- **Protocolos de interoperabilidad**: MCP (Model Context Protocol) nativo, A2A (Agent-to-Agent) nativo.
- **Tools**: `crewai-tools` (SerperDevTool, etc.) + tools custom vía `BaseTool`.
- **Enterprise**: CrewAI AMP Suite / Crew Control Plane (deployment, observabilidad, gobernanza) — comercial, `app.crewai.com`.

## Dependencias

- [01_LANDSCAPE/agent-frameworks.md](agent-frameworks.md) — comparativa de 9 frameworks (JWIKI-010), CrewAI incluido.
- [01_LANDSCAPE/langgraph.md](langgraph.md) — LangGraph (JWIKI-011), alternativa de grafo de estados.
- [01_LANDSCAPE/autogen.md](autogen.md) — AutoGen (JWIKI-013), alternativa actor-model.
- Externas: `pydantic` (BaseModel para Agent/Task/Crew), `lancedb` (Memory, lazy), `crewai.rag.embeddings` (embeddings), UV.

## Arquitectura

CrewAI v1.x es un **monorepo workspace** (gestionado con UV) con seis paquetes en `lib/`: `cli`, `crewai-core`, `crewai-files`, `crewai-tools`, `crewai` (el framework), `devtools`. El core (`lib/crewai/src/crewai/`) organiza sus primitivas así:

```
crewai/
├── agent/        # class Agent(BaseAgent) — role/goal/backstory/tools/llm
├── agents/       # agent_builder, base_agent
├── a2a/          # protocolo Agent-to-Agent
├── crew.py       # class Crew(FlowTrackable, BaseModel) — orquestador
├── task.py       # class Task(BaseModel) — unidad de trabajo
├── process.py    # Enum: sequential | hierarchical
├── flow/         # Flow[State], @start/@listen/@router, or_/and_
├── memory/       # Unified Memory (v1.x): scopes + importance + RAG
├── knowledge/    # knowledge sources (RAG de documentos)
├── mcp/          # cliente MCP nativo (client/config/filters/transports)
├── llm.py, llms/ # capa de conexión LLM (LLM, BaseLLM)
├── tools/        # BaseTool, integración crewai-tools
├── rag/          # embeddings factory, retrieval
├── state/        # CheckpointConfig, persistencia
├── skills/, hooks/, events/, telemetry/, security/, project/
└── __init__.py   # exports públicos + __version__ = "1.15.2"
```

**Dos paradigmas complementarios** (el diseño clave):

```
┌─────────────────────────────────────────────────────────┐
│  CREWS  (autonomía)          │   FLOWS  (control)         │
│  ─────────────────           │   ────────────────         │
│  Agents con roles            │   @start / @listen         │
│  Colaboración + delegación   │   @router (branching)      │
│  Process.sequential          │   Flow[State] tipado       │
│  Process.hierarchical        │   or_ / and_ condiciones   │
│  (manager auto)              │   estado Pydantic          │
└──────────────┬───────────────┴───────────────┬────────────┘
               └────────► se combinan ◄─────────┘
        Crew.kickoff() invocado como paso dentro de un @listen
```

Los Crews optimizan autonomía e inteligencia colaborativa; los Flows aportan control event-driven, estado y branching. Un Flow puede invocar `crew.kickoff()` como un paso más de su grafo.

## Descripción técnica

### Agent

`class Agent(BaseAgent)` (`lib/crewai/src/crewai/agent/core.py:170`) modela un trabajador especializado. Sus campos clave: `role` (quién es), `goal` (qué persigue), `backstory` (contexto/personalidad que condiciona el prompt), `llm` (modelo), `tools` (herramientas disponibles), `allow_delegation` (si puede delegar en otros agentes), `max_iter` (tope de iteraciones), `knowledge_sources` (RAG), y novedades v1.x: `multimodal: bool` (core.py:250) y `reasoning: bool` (core.py:276). El trío `role/goal/backstory` es la firma de CrewAI: en lugar de escribir prompts a mano, describes *quién* es el agente y el framework construye el system prompt.

### Task

`class Task(BaseModel)` (`task.py:114`) es la unidad de trabajo. `description` (task.py:146) y `expected_output` (147) son obligatorios y admiten interpolación `{variable}`. Campos avanzados: `context: list[Task]` (161) permite encadenar el output de otras tasks como entrada (DAG de dependencias sin Flow); `output_json`/`output_pydantic` (169/179) fuerzan salida estructurada validada; `guardrail` (246) valida y reintenta la salida (auto-corrección); `human_input` (227) pausa para revisión humana; `async_execution` (165) ejecuta en paralelo; `output_file` (199) persiste el resultado.

### Crew

`class Crew(FlowTrackable, BaseModel)` (`crew.py:159`) orquesta agentes y tasks. Campos: `agents`, `tasks`, `process` (default `Process.sequential`, crew.py:225), `memory`, `cache` (default True), `planning` (318), `manager_llm`/`manager_agent` (249/254, para hierarchical), `embedder` (241), `knowledge_sources` (340). Métodos de ejecución: `kickoff()` (966), `kickoff_async()` (1096), `kickoff_for_each()` (1060, batch sobre lista de inputs), `train()` (914), `replay(task_id)` (1904, re-ejecución determinista desde una task), `test()` (2100).

### Process (Sequential vs Hierarchical)

`Process` es un `str, Enum` con **solo dos valores activos** (`process.py:4-11`): `sequential` (tasks en orden, output → contexto siguiente) y `hierarchical` (CrewAI asigna un **manager agent automático** que planifica, delega y valida resultados; requiere `manager_llm` o `manager_agent`). Un tercer valor `consensual` está comentado como `# TODO` — no implementado.

### Memory (Unified Memory v1.x — cambio arquitectónico)

⚠️ **Hallazgo importante (Conflicto #2)**: el modelo mental clásico de CrewAI 0.x era "short-term + long-term + entity memory". En **v1.x el core usa Unified Memory**: "single intelligent memory with LLM analysis and pluggable storage" (`memory/unified_memory.py:1`). Cada `MemoryRecord` (`memory/types.py:20`) tiene `scope` (path jerárquico `/company/team/user`), `importance` (0.0-1.0, afecta ranking de recall), `categories`, `metadata`, `source` (provenance), `private` (visibilidad por origen), y `embedding` (excluido de serialización). El subsistema es un RAG completo con event bus (`MemoryQuery/Save Started/Completed/Failed`), `ThreadPoolExecutor` y `build_embedder`. `Memory` se importa lazy (`__init__.py` `_LAZY_IMPORTS`) para no cargar `lancedb` hasta el primer uso.

### Tools, MCP y A2A

Las tools custom heredan de `BaseTool` (`crewai/tools/`). El paquete `crewai-tools` (separado, `crewai[tools]`) trae herramientas listas como `SerperDevTool`. CrewAI tiene **MCP nativo** en el core (`crewai/mcp/` con `client.py`, `config.py`, `filters.py`, `tool_resolver.py`, `transports/`) y **A2A nativo** (`crewai/a2a/`) — esto refuta el claim del doc AutoGen (JWIKI-013) de que CrewAI "solo soporta MCP vía adaptadores" (Conflicto #3).

## Flujo interno

Flujo típico de un Crew sequential:

```
1. crewai create crew <name>       # scaffolding CLI
2. Editar config/agents.yaml       # role/goal/backstory por agente
3. Editar config/tasks.yaml        # description/expected_output/agent
4. crew.py: @CrewBase + @agent/@task/@crew decoradores
5. main.py: LatestAiDevelopmentCrew().crew().kickoff(inputs={...})
   └─► Crew.kickoff()
        └─► Process.sequential:
             ├─ Task 1 → Agent asignado → LLM + tools → output
             ├─ Task 2 (context=[Task1]) → Agent → output
             └─ ... → CrewOutput agregado
        └─► (si hierarchical: manager_agent planifica y delega)
6. output_file (report.md) escrito
```

Flujo de un Flow event-driven:

```
Flow[MarketState].kickoff()
  └─ @start()  fetch_market_data()          # inicializa state
      └─ @listen(fetch_market_data) analyze_with_crew()  # invoca Crew.kickoff()
          └─ @router(analyze_with_crew) determine_next_steps()  # devuelve label
              ├─ @listen("high_confidence") execute_strategy()
              └─ @listen(or_("medium","low")) request_additional_analysis()
```

## Call Stack / API

```
Crew(agents, tasks, process=Process.sequential).kickoff(inputs)
  → Crew.kickoff()                       # crew.py:966
    → resolve process (sequential|hierarchical)  # process.py
      → per Task: Agent.execute_task()   # agent/core.py
        → LLM.call() + tool invocation   # llm.py + tools/
          → Task guardrail validation    # task.py:246
            → output_pydantic/output_json coercion  # task.py:169/179
              → Memory.save() (si memory=True)   # memory/unified_memory.py
                → CrewOutput agregado    # crews/crew_output.py
```

## Diagramas

```
        ┌──────────── Crew ────────────┐
        │  process = sequential | hier  │
        │                               │
   ┌────▼────┐   ┌─────────┐   ┌────────▼───┐
   │ Agent A │   │ Agent B │   │  manager   │ (solo hierarchical)
   │ role/   │   │ role/   │   │  auto      │
   │ goal    │   │ goal    │   └─────┬──────┘
   └────┬────┘   └────┬────┘         │ delega/valida
        │             │              │
     Task 1 ──────► Task 2 ──────► Task N
   (expected_    (context=      (output_file)
    output)       [Task1])
        │
        └─► Tools (BaseTool / crewai-tools / MCP / A2A)
        └─► Memory (Unified: scope + importance + RAG)
        └─► Knowledge (knowledge_sources)
```

## Código relacionado

- `https://github.com/crewAIInc/crewAI/blob/main/lib/crewai/src/crewai/process.py` (L4-11 — Process enum)
- `https://github.com/crewAIInc/crewAI/blob/main/lib/crewai/src/crewai/agent/core.py` (L170 — class Agent)
- `https://github.com/crewAIInc/crewAI/blob/main/lib/crewai/src/crewai/task.py` (L114 — class Task)
- `https://github.com/crewAIInc/crewAI/blob/main/lib/crewai/src/crewai/crew.py` (L159 — class Crew)
- `https://github.com/crewAIInc/crewAI/blob/main/lib/crewai/src/crewai/memory/unified_memory.py` (L1 — Unified Memory)
- `https://github.com/crewAIInc/crewAI/blob/main/lib/crewai/src/crewai/memory/types.py` (L20 — MemoryRecord)
- `https://github.com/crewAIInc/crewAI/blob/main/lib/crewai/src/crewai/__init__.py` (exports + __version__)

## Ejemplos

**1. Agent con role/goal/backstory (YAML declarativo)** — `config/agents.yaml`:

```yaml
researcher:
  role: >
    {topic} Senior Data Researcher
  goal: >
    Uncover cutting-edge developments in {topic}
  backstory: >
    You're a seasoned researcher with a knack for uncovering the latest
    developments in {topic}. Known for your ability to find the most relevant
    information and present it in a clear and concise manner.
```

**2. Task con description/expected_output** — `config/tasks.yaml`:

```yaml
research_task:
  description: >
    Conduct a thorough research about {topic}
  expected_output: >
    A list with 10 bullet points of the most relevant information about {topic}
  agent: researcher
```

**3. Crew con decoradores + Process.sequential** — `crew.py`:

```python
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool

@CrewBase
class LatestAiDevelopmentCrew():
    @agent
    def researcher(self) -> Agent:
        return Agent(config=self.agents_config['researcher'],
                     verbose=True, tools=[SerperDevTool()])

    @task
    def research_task(self) -> Task:
        return Task(config=self.tasks_config['research_task'])

    @crew
    def crew(self) -> Crew:
        return Crew(agents=self.agents, tasks=self.tasks,
                    process=Process.sequential, verbose=True)
```

**4. Crew programático con Process.sequential (sin YAML)**:

```python
from crewai import Agent, Task, Crew, Process

analyst = Agent(role="Senior Market Analyst",
                goal="Conduct deep market analysis with expert insight",
                backstory="You're a veteran analyst known for identifying subtle patterns")
analysis_task = Task(description="Analyze {sector} sector data",
                     expected_output="Detailed market analysis with confidence score",
                     agent=analyst)
crew = Crew(agents=[analyst], tasks=[analysis_task],
            process=Process.sequential, verbose=True)
result = crew.kickoff(inputs={"sector": "tech"})
```

**5. Process.hierarchical (manager automático)**:

```python
crew = Crew(
    agents=[researcher, writer, reviewer],
    tasks=[research, draft, review],
    process=Process.hierarchical,   # CrewAI crea un manager que delega y valida
    manager_llm="gpt-4o",           # o manager_agent=custom_manager
    verbose=True,
)
crew.kickoff()
```

**6. Flow event-driven con estado tipado y routing**:

```python
from crewai.flow.flow import Flow, listen, start, router, or_
from pydantic import BaseModel

class MarketState(BaseModel):
    sentiment: str = "neutral"
    confidence: float = 0.0

class AdvancedAnalysisFlow(Flow[MarketState]):
    @start()
    def fetch_market_data(self):
        self.state.sentiment = "analyzing"
        return {"sector": "tech", "timeframe": "1W"}

    @listen(fetch_market_data)
    def analyze_with_crew(self, data):
        return analysis_crew.kickoff(inputs=data)

    @router(analyze_with_crew)
    def determine_next_steps(self):
        return "high_confidence" if self.state.confidence > 0.8 else "low_confidence"

    @listen(or_("medium_confidence", "low_confidence"))
    def request_additional_analysis(self):
        return "Additional analysis required"
```

**7. Task con structured output (Pydantic)**:

```python
from pydantic import BaseModel
from crewai import Task

class Report(BaseModel):
    title: str
    bullets: list[str]

task = Task(
    description="Summarize the findings",
    expected_output="A structured report",
    output_pydantic=Report,   # task.py:179 — salida validada
    agent=analyst,
)
```

**8. CLI de scaffolding**:

```shell
uv pip install crewai
crewai create crew latest-ai-development
cd latest_ai_development
crewai install
crewai run
```

## Comparativa detallada con LangGraph, AutoGen, OpenAI Agents SDK y Google ADK

| Criterio | CrewAI | LangGraph | AutoGen | OpenAI Agents SDK | Google ADK |
|---|---|---|---|---|---|
| Paradigma | Crews (roles) + Flows (event-driven) | Grafo de estados (StateGraph) | Actor-model conversacional | Handoffs entre agents | Vertex-native, code-first |
| Multi-agente nativo | ✅ Crew de roles + delegación | ✅ nodos/subgrafos | ✅ Teams (RoundRobin, Selector, Swarm) | ✅ handoffs | ✅ sub-agents |
| Nivel de abstracción | Alta (role/goal/backstory) + baja (Flows) | Baja (grafo explícito) | Media (conversación) | Media | Media-alta |
| Config declarativa | ✅ YAML-first | ❌ (todo código) | ❌ | ❌ | parcial |
| MCP | ✅ nativo (`crewai/mcp`) | ✅ nativo (1.0) | ✅ mejor soporte (elicitation) | Parcial | ✅ |
| A2A | ✅ nativo (`crewai/a2a`) | vía LangChain | GraphFlow | ❌ | ✅ (protocolo A2A Google) |
| Estado estructurado | Flows (`Flow[State]` Pydantic) | ✅ core (channels/reducers) | via runtime | via context | via session |
| Delegación / handoffs | hierarchical manager + allow_delegation | aristas condicionales | selector/swarm | handoffs first-class | sub-agents |
| Streaming | ✅ | ✅ (nativo, granular) | ✅ | ✅ | ✅ |
| Human-in-the-loop | ✅ `human_input` en Task | ✅ interrupts/checkpoints | ✅ | parcial | parcial |
| Checkpointing | ✅ (`state/CheckpointConfig`) | ✅ (core, muy fuerte) | via runtime | ❌ | via session |
| Lenguaje | Python (~99.7%) | Python (+ langgraphjs) | Python + .NET | Python | Python |
| License | MIT | MIT | MIT | MIT | Apache-2.0 |
| Stars (2026-07-08) | **55.157** | ver JWIKI-011 | ver JWIKI-013 | — | — |

**Análisis por diferenciador**:

- **vs LangGraph**: LangGraph expone un grafo de estados de bajo nivel (nodos, aristas, `channels`/reducers, supersteps con `Send` para paralelismo). Da control máximo pero exige modelar todo explícitamente. CrewAI ofrece la abstracción role/goal/backstory (mucho más legible) y cubre el hueco de control con Flows. Regla práctica: LangGraph gana en workflows con topología compleja y estado compartido granular; CrewAI gana en velocidad de prototipado de equipos de agentes.
- **vs AutoGen**: AutoGen (Microsoft) usa un actor-model conversacional con cinco patrones de Team (RoundRobinGroupChat, SelectorGroupChat, Swarm, MagenticOneGroupChat, GraphFlow) y soporta agentes Python **y .NET** en el mismo sistema vía gRPC. CrewAI es mono-Python pero con configuración declarativa YAML y una curva de entrada más suave. AutoGen tiene el mejor soporte MCP (elicitation/sampling/roots); CrewAI lo tiene nativo pero menos avanzado.
- **vs OpenAI Agents SDK**: el SDK de OpenAI centra su modelo en *handoffs* explícitos entre agentes (un agente pasa el control a otro). CrewAI cubre esto con `allow_delegation` y el manager de `Process.hierarchical`. El SDK está más acoplado al ecosistema OpenAI; CrewAI es LLM-agnóstico vía `crewai.llm.LLM`.
- **vs Google ADK**: ADK es code-first y nativo de Vertex AI (Google Cloud), con protocolo A2A propio y despliegue gestionado. CrewAI es cloud-agnóstico (aunque ofrece AMP Suite comercial). Ambos soportan A2A. ADK es Apache-2.0 (única licencia no-MIT del grupo).

## Cuándo elegir CrewAI sobre las alternativas

**Elige CrewAI cuando**:
- Necesitas coordinar varios agentes con **roles claros** y quieres que colaboren/deleguen de forma autónoma sin cablear cada transición.
- Valoras la **legibilidad**: describir `role`/`goal`/`backstory` en YAML es más accesible para equipos no expertos que modelar un grafo de estados.
- Quieres **prototipar rápido** y luego endurecer a producción sin cambiar de framework (añadiendo Flows, guardrails, checkpointing, structured output progresivamente).
- Tu stack es **Python puro** y no necesitas interoperar con .NET.
- Quieres **YAML-first** para separar la configuración de prompts de la lógica de negocio.

**Evita CrewAI (o combina con otro) cuando**:
- Necesitas **control de topología muy fino** con estado compartido granular y paralelismo determinista → LangGraph.
- Requieres **agentes cross-language** (Python + .NET en el mismo runtime) → AutoGen.
- Estás **anclado a Vertex AI** y quieres despliegue nativo gestionado → Google ADK.
- Tu caso es un **único agente con handoffs simples** dentro del ecosistema OpenAI → OpenAI Agents SDK puede ser más ligero.

**Casos de uso ideales de CrewAI** (documentados en README y ejemplos oficiales): generación de landing pages, planificación de viajes (Trip Planner), análisis bursátil (Stock Analysis), redacción de descripciones de empleo, y pipelines de research→reporting (el ejemplo canónico researcher + reporting_analyst). El patrón repetido es "equipo de especialistas que se pasan contexto secuencialmente".

## Ecosistema y adopción

CrewAI es una **empresa** (CrewAI Inc., fundada por Joao Moura / `joaomdmoura`) con oferta comercial además del OSS: **CrewAI AMP Suite** (control plane enterprise: deployment gestionado, observabilidad, gobernanza, seguridad, soporte 24/7, on-prem o cloud) y el **Crew Control Plane** con trial gratuito en `app.crewai.com`. Esta dualidad OSS+comercial es similar al modelo de LangChain/LangGraph (LangSmith) — el framework abierto atrae adopción, el control plane monetiza el uso en producción.

Señales de tracción: **55.157 stars**, **7.754 forks**, ~**301 contribuidores**, y un claim de marketing de "over 100,000 developers certified" a través de cursos comunitarios en `learn.crewai.com` y los short courses de DeepLearning.AI (*Multi AI Agent Systems with CrewAI* y *Practical Multi AI Agents and Advanced Use Cases*). **Caveat (P6)**: los 100k son *certificados de curso*, no una métrica de usuarios activos del framework — se cita con su naturaleza. La cadencia de releases (varias por semana con alphas) y el toolchain estricto (ruff+mypy+bandit+pip-audit, `ban-relative-imports`) indican un proyecto con ingeniería madura, no un experimento.

## Buenas prácticas

- ✅ Usar **YAML-first** (`agents.yaml`/`tasks.yaml`) para separar configuración de lógica — facilita iterar prompts sin tocar código.
- ✅ Empezar con `Process.sequential`; pasar a `hierarchical` solo cuando necesites coordinación dinámica con delegación.
- ✅ Forzar `output_pydantic`/`output_json` cuando el output alimenta código downstream — evita parseo frágil de texto libre.
- ✅ Usar `guardrail` en tasks críticas para auto-validación y reintentos.
- ✅ Combinar **Flows para el control** (branching, estado) y **Crews para la autonomía** (colaboración de roles) — es el patrón que los autores recomiendan.
- ✅ Instalar los skills oficiales (`crewAIInc/skills`) si trabajas con un coding agent — enseñan los patrones correctos.

## Errores comunes

- ❌ Asumir que Memory sigue el modelo "short/long/entity" de 0.x — en v1.x es **Unified Memory** con scopes jerárquicos e importance. Leer `unified_memory.py`.
- ❌ Usar `Process.hierarchical` sin definir `manager_llm` ni `manager_agent` — el manager no puede instanciarse.
- ❌ Olvidar `SERPER_API_KEY`/`OPENAI_API_KEY` en `.env` antes de `crewai run`.
- ❌ Esperar cross-language (Python+.NET) como AutoGen — CrewAI es **mono-Python** (~99.7%).
- ❌ Confiar en el conteo "~30k stars" de fuentes con 7+ días — el valor real 2026-07-08 es 55.157 (P2).
- ❌ Instalar `crewai` sin el extra `[tools]` y esperar `SerperDevTool` u otras tools disponibles.

## Breaking Changes

| Versión | Cambio | Impacto |
|---|---|---|
| 0.x → 1.0 | Reestructuración a **monorepo workspace** (`lib/` con 6 paquetes, UV) | Imports internos cambian; `crewai_core.version` como path estable |
| 0.x → 1.x | **Unified Memory** reemplaza short/long/entity clásico | Código que instanciaba memorias específicas debe migrar a `Memory` unificada |
| 1.x | MCP y A2A promovidos a **nativos** en el core | Ya no requiere adaptadores externos para MCP |
| Python | `requires-python >=3.10,<3.14` | Bloquea 3.9 y 3.14+ (wheels de deps) |
| Agent v1.x | `multimodal` y `reasoning` como campos | Nuevas capacidades opt-in |

## Cambios entre versiones

Cadencia de releases muy rápida (varias por semana con sufijos alpha `aN`): 1.15.2 (2026-07-08) ← 1.15.2a2 (07-01) ← 1.15.2a1 (06-30) ← 1.15.1 (06-27) ← 1.15.0 (06-25) ← 1.14.8a5 (06-25). El salto histórico v0.119.0 → v1.0.0-alpha marca el rediseño monorepo + Unified Memory + MCP/A2A nativos. Ver `https://api.github.com/repos/crewAIInc/crewAI/releases`.

## Impacto sobre otros sistemas

- **JWIKI-013 autogen.md — DEBE ACTUALIZARSE**: la afirmación "CrewAI que solo [soporta MCP] vía adaptadores" es FALSA en v1.x. El core tiene `crewai/mcp/` nativo (client + transports). Corregir en el próximo tick que toque JWIKI-013.
- **JWIKI-011 langgraph.md**: tiene un placeholder "[comparativa CrewAI (pendiente)]" en Dependencias y Referencias cruzadas — este doc lo resuelve; enlazar bidireccionalmente cuando se re-toque.
- **JWIKI-010 agent-frameworks.md**: la fila CrewAI debería actualizar stars a 55.157 y MCP a "nativo".
- **Aithera V1.0 Orchestrator**: el patrón Crew (manager hierarchical + delegación) y Flow[State] (estado Pydantic + `@router`) son directamente借鉴ables para el planner + Automation Engine, sin adoptar CrewAI como dependencia.

## Referencias cruzadas

- [01_LANDSCAPE/agent-frameworks.md](agent-frameworks.md) — comparativa 9 frameworks (JWIKI-010).
- [01_LANDSCAPE/langgraph.md](langgraph.md) — LangGraph, grafo de estados (JWIKI-011).
- [01_LANDSCAPE/autogen.md](autogen.md) — AutoGen, actor-model (JWIKI-013).
- [01_LANDSCAPE/hermes-agent.md](hermes-agent.md) — Hermes Agent (JWIKI-007); comparte el patrón `requires-python <3.14` y sistema de skills.
- [01_LANDSCAPE/superpowers.md](superpowers.md) — Superpowers (JWIKI-009); ambos usan skills instalables para coding agents.
- [01_LANDSCAPE/jarvisagent.md](jarvisagent.md) — JarvisAgent (JWIKI-006); comparativa de sub-agent delegation.

## Fuentes

1. https://api.github.com/repos/crewAIInc/crewAI — acceso 2026-07-08 (stars 55.157, forks 7.754, MIT, pushed 2026-07-08)
2. https://api.github.com/repos/crewAIInc/crewAI/languages — 2026-07-08 (Python 99.7%)
3. https://api.github.com/repos/crewAIInc/crewAI/releases — 2026-07-08 (1.15.2)
4. https://raw.githubusercontent.com/crewAIInc/crewAI/main/README.md — 2026-07-08
5. https://raw.githubusercontent.com/crewAIInc/crewAI/main/pyproject.toml — 2026-07-08
6. https://raw.githubusercontent.com/crewAIInc/crewAI/main/lib/crewai/src/crewai/__init__.py — 2026-07-08
7. https://raw.githubusercontent.com/crewAIInc/crewAI/main/lib/crewai/src/crewai/process.py — 2026-07-08
8. https://raw.githubusercontent.com/crewAIInc/crewAI/main/lib/crewai/src/crewai/agent/core.py — 2026-07-08
9. https://raw.githubusercontent.com/crewAIInc/crewAI/main/lib/crewai/src/crewai/task.py — 2026-07-08
10. https://raw.githubusercontent.com/crewAIInc/crewAI/main/lib/crewai/src/crewai/crew.py — 2026-07-08
11. https://raw.githubusercontent.com/crewAIInc/crewAI/main/lib/crewai/src/crewai/memory/unified_memory.py — 2026-07-08
12. https://raw.githubusercontent.com/crewAIInc/crewAI/main/lib/crewai/src/crewai/memory/types.py — 2026-07-08
13. https://docs.crewai.com/ (HTTP 200) — 2026-07-08
14. https://crewai.com (HTTP 200) — 2026-07-08
15. https://github.com/crewAIInc/skills — 2026-07-08
16. Material crudo: `JWIKI/material/JWIKI-012-raw.md` (55 hechos F1-F55) — 2026-07-08

## Nivel de confianza

**88%**. Código fuente revisado directamente (branch `main`, v1.15.2), GitHub API contrastada live, docs oficiales confirmadas (HTTP 200). Descuento del 12% por: (a) rate limit impidió leer `knowledge/` y `tools/` completos, (b) el modelo exacto de `MemoryScope`/`MemorySlice` no se leyó línea a línea, (c) stars de LangGraph/AutoGen live no re-verificados en este tick (se referencian sus docs JWIKI).

## Pendientes

- [ ] Leer `memory/memory_scope.py` completo para documentar `MemoryScope`/`MemorySlice` (visto como PrivateAttr en `crew.py:206`).
- [ ] Verificar stars live de LangGraph/AutoGen para completar la fila numérica de la tabla comparativa.
- [ ] Confirmar el propósito de `crewai-files` (I/O vs knowledge).
- [ ] Documentar el subsistema `knowledge/` (knowledge_sources) con lectura de código (bloqueado por rate limit este tick).
- [ ] Verificar comportamiento de `Process` cuando se combina con Flows anidados.

---

## Changelog

### 2026-07-08 — v1.0 (creación desde cero)
- Autor: orquestador JWIKI single-team (tick A-20260708-2020)
- Cambio: documento creado desde cero (P1: raw+doc no existían). 55 hechos verificados contra GitHub API live + código fuente `main`, 8 snippets con path:line, tabla comparativa de 5 frameworks, 5 conflictos documentados. Hallazgos clave: 55.157 stars (task_queue decía ~30k, +84% stale), Unified Memory reemplaza modelo clásico short/long/entity, MCP+A2A nativos (refuta claim de JWIKI-013).
- Validador: GitHub API live 2026-07-08 + raw.githubusercontent.com cross-check + docs.crewai.com HTTP 200.
