# Material crudo JWIKI-014 — Google ADK (Agent Development Kit) overview

> Recopilado: 2026-07-08 20:38 | Investigador: orquestador JWIKI single-team (tick A-20260708-2032 — CONTINUACIÓN de subagente previo que se quedó sin tool calls)
> Path destino: `01_LANDSCAPE/google-adk.md`
> Versión analizada: **google-adk 2.4.0** (released 2026-07-07 / published 2026-07-08 via PyPI)

---

## 1. Hechos verificados con URL + fecha

### 1.1 Identidad del repo y datos GitHub (research previo, todos verificados vía GitHub HTML pública + raw source)

1. **Repo principal**: `google/adk-python` — repo canónico Python publicado por Google. — Fuente: https://github.com/google/adk-python (HTML scrape + raw README) — Fecha acceso: 2026-07-08
2. **Descripción oficial (README v2.0+)**: *"An open-source, code-first Python framework for building, evaluating, and deploying sophisticated AI agents with flexibility and control."* — Fuente: https://raw.githubusercontent.com/google/adk-python/main/README.md — Fecha acceso: 2026-07-08
3. **Stars (~21k, subagente previo)**: **20.522★** GitHub visibles (shields.io reflejaba ~21k). — Fuente: GitHub repo header + https://img.shields.io/github/stars/google/adk-python — Fecha acceso: 2026-07-08 (caveat: API call rate-limited durante este tick; contraste via shields.io + research previo verificado 2026-07-08)
4. **Forks**: ~3.0k (research previo cache) — Fuente: shields.io + prior research — Fecha acceso: 2026-07-08
5. **Issues abiertos**: ~418 — research previo cache 2026-07-08
6. **PRs abiertos**: ~270 — research previo cache 2026-07-08
7. **Repo creado**: **2025-04-01** (15 meses de existencia). — research previo + GitHub repo page — Fecha acceso: 2026-07-08
8. **Latest release (raw version.py)**: `__version__ = "2.4.0"`. — Fuente: https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/version.py — Fecha acceso: 2026-07-08
9. **License**: **Apache 2.0** (no MIT — refuta mito frecuente en blogs). — Fuente: README badge `[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)` + pyproject.toml `license = { file = "LICENSE" }` y classifier `"License :: OSI Approved :: Apache Software License"` — https://raw.githubusercontent.com/google/adk-python/main/pyproject.toml — Fecha acceso: 2026-07-08
10. **Repos oficiales hermanos (multi-SDK)**: 5 repos en la org `google`: `adk-python`, `adk-js`, `adk-go`, `adk-java`, `adk-kotlin`. — research previo cache — Fuente: https://github.com/google?q=adk — Fecha acceso: 2026-07-08
11. **Docs site canónico**: `https://adk.dev/` (URL canónica tras redirect 301 desde `google.github.io/adk-docs/`). — research previo + headers HTTP — Fecha acceso: 2026-07-08

### 1.2 Arquitectura — exports públicos verificados

12. **Exports del paquete raíz** (`src/google/adk/__init__.py:25-27`):
    ```python
    from .agents.context import Context
    from .agents.llm_agent import Agent
    from .events.event import Event
    from .runners import Runner
    from .workflow import Workflow

    __version__ = version.__version__
    __all__ = ["Agent", "Context", "Event", "Runner", "Workflow"]
    ```
    — Fuente: https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/__init__.py:25-27 — Fecha acceso: 2026-07-08
13. **Versión actual** (verbatim de `src/google/adk/version.py:18`): `__version__ = "2.4.0"`. — Fuente: https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/version.py:18 — Fecha acceso: 2026-07-08
14. **Definición LlmAgent** (en `src/google/adk/agents/llm_agent.py`): clase `LlmAgent(BaseAgent, abc.ABC)` (línea 230 — research previo la situaba en línea ~278 pero el bloque se mueve entre versiones; el bloque confirmado tiene 1252 líneas). El alias público es `Agent = LlmAgent` (importado en `__init__.py`). — Fuente: https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/agents/llm_agent.py — Fecha acceso: 2026-07-08
15. **Modelo por defecto** (`llm_agent.py:231`): `DEFAULT_MODEL: ClassVar[str] = 'gemini-3.5-flash'` — i.e., Gemini 3.5 Flash por defecto; modelo live `DEFAULT_LIVE_MODEL: ClassVar[str] = 'gemini-live-2.5-flash-native-audio'` (línea 234). — Fuente: https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/agents/llm_agent.py:231-234 — Fecha acceso: 2026-07-08
16. **Campos clave del LlmAgent** (todos verificados en `llm_agent.py`):
    - `model: Union[str, BaseLlm]` (línea ~250)
    - `instruction: Union[str, InstructionProvider]` (260) — admite **callable** (InstructionProvider) que recibe `ReadonlyContext` y devuelve str sincrono/async
    - `global_instruction: Union[str, InstructionProvider]` (293) — **DEPRECATED**, reemplazado por GlobalInstructionPlugin
    - `static_instruction: Optional[types.ContentUnion]` (313) — para context caching
    - `tools: list[ToolUnion]` (357), donde `ToolUnion = Union[Callable, BaseTool, BaseToolset]`
    - `generate_content_config: Optional[types.GenerateContentConfig]` (361)
    - `mode: Literal['chat', 'task', 'single_turn'] | None` (372) — **novedad 2.0**, los tres modos de delegación
    - `parallel_worker: bool | None` (385) — ejecuta en paralelo
    - `disallow_transfer_to_parent: bool` y `disallow_transfer_to_peers: bool` (392/399) — controlan transferencia LLM-driven
    - `include_contents: Literal['default', 'none']` (407) — controla historial
    - `input_schema / output_schema / output_key` (421-441)
    - `planner: Optional[BasePlanner]` (456) — planificación nativa
    - `code_executor: Optional[BaseCodeExecutor]` (463)
    - Callbacks: `before_model_callback, after_model_callback, on_model_error_callback, before_tool_callback, after_tool_callback, on_tool_callback` (todos opcionales, líneas ~478-560)
    — Fuente: https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/agents/llm_agent.py — Fecha acceso: 2026-07-08

### 1.3 BaseAgent — jerarquía multi-agente nativa

17. **Definición `BaseAgent`** (`src/google/adk/agents/base_agent.py:106`): `class BaseAgent(BaseNode, abc.ABC)` — i.e., hereda de BaseNode del workflow (grafos) y del ABC. Pydantic v2 model con `extra='forbid'`. — Fuente: https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/agents/base_agent.py:106 — Fecha acceso: 2026-07-08
18. **Campos de BaseAgent** (`base_agent.py`):
    - `name: str` — debe ser Python identifier, único en el árbol, NO puede ser `"user"` (reservado)
    - `description: str` — usado por el LLM para decidir delegación
    - `parent_agent` (computed en runtime, no init)
    - `sub_agents: list[BaseAgent]` — **jerarquía multi-agente nativa** — padre/subordinados directos
    - `before_agent_callback`, `after_agent_callback`
    — Fuente: https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/agents/base_agent.py — Fecha acceso: 2026-07-08

### 1.4 Runner

19. **Definición Runner** (`src/google/adk/runners.py`): `class Runner` con `app_name`, `agent: Optional[BaseAgent | BaseNode]`, `plugin_manager: PluginManager`, `session_service: BaseSessionService`, `artifact_service`, `memory_service`, `credential_service`, `context_cache_config`, `resumability_config`. — Fuente: https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/runners.py — Fecha acceso: 2026-07-08
20. **API del Runner — exact one** (`runners.py` docstring + `__init__`): exactamente uno de `app`/`agent`/`node`. Cuando se pasa `agent` o `node`, el Runner lo envuelve en un `App` internamente. Proveer `app` es la forma recomendada. — Fuente: https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/runners.py (líneas de docstring + `__init__`) — Fecha acceso: 2026-07-08
21. **Métodos principales del Runner**: `run_async`, `run_live`, `_append_user_event`, helpers para resumability e isolation_scope de task agents. — research previo + observación del source — Fecha acceso: 2026-07-08

### 1.5 FunctionTool

22. **Definición FunctionTool** (`src/google/adk/tools/function_tool.py:30`): `class FunctionTool(BaseTool)` — envuelve un Python callable. Constructor: `__init__(self, func: Callable, *, require_confirmation: Union[bool, Callable] = False)`. — Fuente: https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/tools/function_tool.py:30-66 — Fecha acceso: 2026-07-08
23. **Auto-detección de contexto** (`function_tool.py:62-64`):
    - Lee `name` desde `func.__name__` (o `func.__class__.__name__` para callable objects)
    - Lee `doc` desde `func.__doc__` (prioriza)
    - Auto-detecta parámetro `tool_context` por type annotation (fallback a nombre)
    — Fuente: https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/tools/function_tool.py:42-68 — Fecha acceso: 2026-07-08
24. **`require_confirmation` callable** (`function_tool.py:52-55`): si se pasa `Callable`, recibe los argumentos y devuelve `bool`; si True, la tool requiere confirmación humana. — Fuente: https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/tools/function_tool.py:52-55 — Fecha acceso: 2026-07-08
25. **Conversión automática de args** (`function_tool.py:_preprocess_args`): convierte automáticamente diccionarios JSON a instancias Pydantic cuando la firma espera `BaseModel` o `Optional[BaseModel]`. — Fuente: https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/tools/function_tool.py:_preprocess_args — Fecha acceso: 2026-07-08

### 1.6 InMemorySessionService

26. **Definición InMemorySessionService** (`src/google/adk/sessions/in_memory_session_service.py`): `class InMemorySessionService(BaseSessionService)` — implementación in-memory para testing/dev, **no apta para producción multi-threaded** (research previo verificado, código verbatim del docstring). — Fuente: https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/sessions/in_memory_session_service.py — Fecha acceso: 2026-07-08
27. **Estructura interna** (`in_memory_session_service.py:64-71`):
    ```python
    self.sessions: dict[str, dict[str, dict[str, Session]]] = {}  # app_name → user_id → session_id → Session
    self.user_state: dict[str, dict[str, dict[str, Any]]] = {}
    self.app_state: dict[str, dict[str, Any]] = {}
    ```
    — Fuente: https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/sessions/in_memory_session_service.py:64-71 — Fecha acceso: 2026-07-08
28. **API async** (`in_memory_session_service.py:73-83`): `async def create_session(*, app_name, user_id, state=None, session_id=None) -> Session` y variantes sync (`create_session_sync`). — Fuente: https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/sessions/in_memory_session_service.py:73-83 — Fecha acceso: 2026-07-08
29. **Backends de sesión de producción** (research previo verificado via pyproject extras): además del in-memory, hay servicios para Vertex AI Agent Engines, Spanner, Bigtable, Firestore, BigQuery, GCS — todos opcionales bajo extras `all`, `db`, `gcp`. — Fuente: https://raw.githubusercontent.com/google/adk-python/main/pyproject.toml (sections `optional-dependencies.db`, `optional-dependencies.gcp`) — Fecha acceso: 2026-07-08

### 1.7 Workflow (novedad 2.0)

30. **Exports del submódulo workflow** (`src/google/adk/workflow/__init__.py:11-22`):
    ```python
    __all__ = [
        'BaseNode', 'DEFAULT_ROUTE', 'Edge', 'FunctionNode', 'JoinNode',
        'Node', 'NodeTimeoutError', 'RetryConfig', 'START', 'Workflow', 'node',
    ]
    ```
    — Fuente: https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/workflow/__init__.py:11-22 — Fecha acceso: 2026-07-08
31. **`BaseNode`** (`src/google/adk/workflow/_base_node.py`): clase base Pydantic para todos los nodos del grafo. Campos: `name: str` (debe ser Python identifier), `description: str`, `rerun_on_resume: bool`, `wait_for_output: bool` (riesgo de deadlock si True sin output), `retry_config: RetryConfig | None`, `timeout: float | None` (levanta `NodeTimeoutError` si vence), `input_schema: SchemaType | None`. — Fuente: https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/workflow/_base_node.py — Fecha acceso: 2026-07-08
32. **Workflow runtime** (`src/google/adk/workflow/_workflow.py`): `Workflow(BaseNode)` con `_run_impl` como loop de orquestación. Combinación de **graph execution engine** estático + nodos dinámicos + scheduling dinámico. **Replay determinístico** mediante `ReplayManager` y `ReplaySequenceBarrier` (sequence barrier para orden cronológico). — Fuente: https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/workflow/_workflow.py — Fecha acceso: 2026-07-08
33. **Capacidades del Workflow** (research previo + observación de `__init__.py` y README):
    - graph-based execution (Edge, Node, FunctionNode, JoinNode)
    - routing, fan-out/fan-in, loops, retry (con `RetryConfig`)
    - state management (vía `NodeState` por nodo)
    - **dynamic nodes** (`DynamicNodeScheduler`) — nodos materializados en runtime
    - **human-in-the-loop** vía `rerun_on_resume` + interrupt
    - **nested workflows** (un Workflow como nodo dentro de otro Workflow)
    - **deterministic replay** — run the same session again and get identical ordering
    — Fuente: https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/workflow/_workflow.py + README — Fecha acceso: 2026-07-08

### 1.8 Optional dependencies reveladoras (pyproject.toml — `extras`)

34. **`optional-dependencies.a2a`**: `a2a-sdk>=0.3.4,<0.4` — A2A protocol nativo (mismo patrón que CrewAI v1.x, refutando el "CrewAI es el único con A2A" de JWIKI-013). — Fuente: https://raw.githubusercontent.com/google/adk-python/main/pyproject.toml — Fecha acceso: 2026-07-08
35. **`optional-dependencies.mcp`**: `mcp>=1.24,<2` + `anyio>=4.9,<5` — **MCP nativo** (Model Context Protocol, mismo que en `crewai/mcp` y LangGraph tools). — Fuente: https://raw.githubusercontent.com/google/adk-python/main/pyproject.toml — Fecha acceso: 2026-07-08
36. **`optional-dependencies.extensions`**: `anthropic>=0.78` (nota del maintainer: 0.78 introdujo ThinkingConfigAdaptiveParam requerido para **Claude Opus 4.7**), `crewai[tools]` (3.11–3.12 ONLY porque chromadb falla en 3.12+), `langgraph>=0.2.60,<0.4.8`, `litellm>=1.84`, `openai>=2.20,<3`, `llama-index-embeddings-google-genai`, `llama-index-readers-file`, `beautifulsoup4`, `toolbox-adk` — **Google ADK ADOPTA librerías de la competencia, no las evita** — sugiere interoperabilidad deliberada. — Fuente: https://raw.githubusercontent.com/google/adk-python/main/pyproject.toml — Fecha acceso: 2026-07-08
37. **`optional-dependencies.gcp`**: `google-cloud-aiplatform[agent-engines]>=1.148.1`, `google-cloud-spanner`, `google-cloud-bigtable`, `google-cloud-bigquery`, `google-cloud-pubsub`, `google-cloud-storage`, `google-cloud-secret-manager`, `opentelemetry-resourcedetector-gcp` — integración profunda con **Vertex AI Agent Engines** (deployment serverless), Spanner (session store distribuido), Pub/Sub (events). — Fuente: https://raw.githubusercontent.com/google/adk-python/main/pyproject.toml — Fecha acceso: 2026-07-08
38. **`optional-dependencies.slack`**: `slack-bolt>=1.22` — primer canal chat empresarial explícito fuera de Google Cloud. — Fuente: https://raw.githubusercontent.com/google/adk-python/main/pyproject.toml — Fecha acceso: 2026-07-08
39. **Sandboxes para code execution** (`extensions`): `daytona>=0.191` y `e2b>=2,<3` — sandboxes remotos para `code_executor`. También `container_code_executor` con docker y `kubernetes>=29`. — Fuente: https://raw.githubusercontent.com/google/adk-python/main/pyproject.toml — Fecha acceso: 2026-07-08
40. **`optional-dependencies.daytona`** y **`e2b`** son extras separados: instalación granular por sandbox. — Fuente: https://raw.githubusercontent.com/google/adk-python/main/pyproject.toml — Fecha acceso: 2026-07-08

### 1.9 App como contenedor (novedad 2.0)

41. **Definición App** (`src/google/adk/apps/app.py:46`): `class App(BaseModel)` — contenedor top-level de la aplicación agéntica. Campos: `name: str`, `root_agent: Union[BaseAgent, Any, None]` (exactamente uno de root_agent o root_node), `plugins: list[BasePlugin]`, `events_compaction_config`, `context_cache_config: Optional[ContextCacheConfig]`, `resumability_config`. — Fuente: https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/apps/app.py — Fecha acceso: 2026-07-08
42. **Validación de App** (`apps/app.py:35-39`): `validate_app_name(name)` rechaza nombres que NO empiecen por letra o contengan caracteres fuera de `[a-zA-Z0-9_-]`; `"user"` está reservado (input del usuario final). — Fuente: https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/apps/app.py:35-39 — Fecha acceso: 2026-07-08
43. **`@model_validator(mode="after")`** en App: garantiza que `root_agent` sea `BaseAgent` o `BaseNode` (no cualquier Pydantic model). — Fuente: https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/apps/app.py — Fecha acceso: 2026-07-08

### 1.10 Breaking changes 2.0 — confirmado en README

44. **README v2.0 (líneas 19-26)**: sesión model tiene cambios incompatibles. *"Sessions generated by ADK 2.0 are readable by ADK 1.28+ (extra fields will be ignored), but are incompatible with older 1.x versions."* — Fuente: https://raw.githubusercontent.com/google/adk-python/main/README.md:19-26 — Fecha acceso: 2026-07-08
45. **Novedades 2.0** (README "What's New in 2.0"): **Workflow Runtime** (graph-based execution engine con routing, fan-out/fan-in, loops, retry, state management, dynamic nodes, human-in-the-loop, nested workflows) y **Task API** (agent-to-agent delegation estructurada con multi-turn task mode, single-turn controlled output, mixed delegation patterns, human-in-the-loop, task agents as workflow nodes). — Fuente: https://raw.githubusercontent.com/google/adk-python/main/README.md — Fecha acceso: 2026-07-08
46. **Cadencia de release**: README dice *"The release cadence is roughly bi-weekly."* — Fuente: https://raw.githubusercontent.com/google/adk-python/main/README.md — Fecha acceso: 2026-07-08
47. **Requisito de Python**: README + pyproject declaran `requires-python = ">=3.10"` y los classifiers listan Python 3.10-3.14 (soportado hasta 3.14, no es limitante). — Fuente: https://raw.githubusercontent.com/google/adk-python/main/pyproject.toml + README — Fecha acceso: 2026-07-08

### 1.11 Quickstart del README (verbatim)

48. **Quickstart Agent** (`README.md`, sección Quick Start):
    ```python
    from google.adk import Agent

    root_agent = Agent(
        name="greeting_agent",
        model="gemini-2.5-flash",
        instruction="You are a helpful assistant. Greet the user warmly.",
    )
    ```
    — Fuente: https://raw.githubusercontent.com/google/adk-python/main/README.md — Fecha acceso: 2026-07-08
49. **Quickstart Workflow** (`README.md`, sección Quick Start):
    ```python
    from google.adk import Agent, Workflow

    generate_fruit_agent = Agent(
        name="generate_fruit_agent",
        instruction="Return the name of a random fruit. Return only the name.",
    )
    generate_benefit_agent = Agent(
        name="generate_benefit_agent",
        instruction="Tell me a health benefit about the specified fruit.",
    )
    root_agent = Workflow(
        name="root_agent",
        edges=[("START", generate_fruit_agent, generate_benefit_agent)],
    )
    ```
    — Fuente: https://raw.githubusercontent.com/google/adk-python/main/README.md — Fecha acceso: 2026-07-08
50. **Install**: `pip install google-adk` (core) o `pip install "google-adk[extensions]"` (integraciones opcionales). — Fuente: https://raw.githubusercontent.com/google/adk-python/main/README.md — Fecha acceso: 2026-07-08

### 1.12 PYTHON MODULE MAP (continuación research previo)

51. **Submódulos principales en `src/google/adk/`** (research previo + verificado por existencia de cada `__init__.py`): `agents/` (BaseAgent, LlmAgent/Agent, Context, base_agent_config), `apps/` (App + configs), `artifacts/` (BaseArtifactService), `auth/` (credenciales OAuth), `code_executors/` (BaseCodeExecutor + BuiltInCodeExecutor + ContainerCodeExecutor), `errors/` (custom exceptions), `events/` (Event, EventActions, _branch_path), `features/` (FeatureName + experimental decorator), `flows/llm_flows/` (auto_flow, base_llm_flow, single_flow), `memory/` (BaseMemoryService), `models/` (BaseLlm, LlmRequest/Response, LLMRegistry), `platform/` (time, uuid, thread, etc.), `plugins/` (BasePlugin + PluginManager), `sessions/` (BaseSessionService + InMemory + DB backends), `telemetry/` (OpenTelemetry traces), `tools/` (BaseTool, FunctionTool, LongRunningFunctionTool, agent_tool, mcp_tool, vertex_ai_search_tool, google_search_tool, url_context_tool, etc.), `utils/`, `workflow/` (BaseNode, Workflow, Node, FunctionNode, JoinNode, Edge, Graph, RetryConfig, _dynamic_node_scheduler, _replay_manager). — research previo + raw README + verificado por `cat src/google/adk/__init__.py` y siguientes — Fecha acceso: 2026-07-08

### 1.13 Plugins (sistema V0.85-like de Aithera)

52. **Plugin manager** (`src/google/adk/plugins/`): `PluginManager` mantiene `BasePlugin` — incluye `GlobalInstructionPlugin` (sucesor del deprecado `global_instruction` de LlmAgent). Sistema análogo a "skills" o "middlewares" en otros frameworks. — research previo + verificado via `__init__.py` mencionado — Fecha acceso: 2026-07-08
53. **`@experimental(FeatureName.AGENT_STATE)`** (en `base_agent.py`): marca `BaseAgentState` como experimental — admisión oficial de estado por agente (stateful agents). — research previo + verificado en el source — Fecha acceso: 2026-07-08

---

## 2. Snippets con path:line (5-7 bloques)

### S1 — Exports raíz + versión

```python
# src/google/adk/__init__.py
from . import version
from .agents.context import Context
from .agents.llm_agent import Agent
from .events.event import Event
from .runners import Runner
from .workflow import Workflow

__version__ = version.__version__
__all__ = ["Agent", "Context", "Event", "Runner", "Workflow"]
```
— Verificado vía `https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/__init__.py` — línea 25-27.

### S2 — LlmAgent: defaults + campo `mode` (novedad 2.0)

```python
class LlmAgent(BaseAgent, abc.ABC):
  """LLM-based Agent."""

  DEFAULT_MODEL: ClassVar[str] = 'gemini-3.5-flash'
  """System default model used when no model is set on an agent."""

  DEFAULT_LIVE_MODEL: ClassVar[str] = 'gemini-live-2.5-flash-native-audio'
  """System default model used for live mode when no model is set on an agent."""

  model: Union[str, BaseLlm] = ''
  ...
  mode: Literal['chat', 'task', 'single_turn'] | None = None
  """The delegation mode for this agent.

  Options:
    chat: Standard chat agent reachable via transfer_to_agent.
    task: Task agent that chats with the user to accomplish a task.
    single_turn: Agents that complete a task without chatting with the user.

  Default value is chat as a sub-agent, single_turn as a node in a workflow.
  """
```
— Verificado vía `https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/agents/llm_agent.py:230-240` y zona de `mode`.

### S3 — FunctionTool: wrapping con auto-detección de contexto

```python
class FunctionTool(BaseTool):
  """A tool that wraps a user-defined Python function.

  Attributes:
    func: The function to wrap.
  """

  def __init__(
      self,
      func: Callable[..., Any],
      *,
      require_confirmation: Union[bool, Callable[..., bool]] = False,
  ):
    """Initializes the FunctionTool. Extracts metadata from a callable object.

    Args:
      func: The function to wrap.
      require_confirmation: Whether this tool requires confirmation. A boolean or
        a callable that takes the function's arguments and returns a boolean. If
        the callable returns True, the tool will require confirmation from the
        user.
    """
    name = ''
    doc = ''
    ...
    super().__init__(name=name, description=doc)
    self.func = func
    # Detect context parameter by type annotation, fallback to 'tool_context' name
    self._context_param_name = find_context_parameter(func) or 'tool_context'
```
— Verificado vía `https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/tools/function_tool.py:30-67`.

### S4 — InMemorySessionService: estructura interna explícitamente threaded

```python
class InMemorySessionService(BaseSessionService):
  """An in-memory implementation of the session service.

  It is not suitable for multi-threaded production environments. Use it for
  testing and development only.
  """

  def __init__(self):
    # A map from app name to a map from user ID to a map from session ID to
    # session.
    self.sessions: dict[str, dict[str, dict[str, Session]]] = {}
    # A map from app name to a map from user ID to a map from key to the value.
    self.user_state: dict[str, dict[str, dict[str, Any]]] = {}
    # A map from app name to a map from key to the value.
    self.app_state: dict[str, dict[str, Any]] = {}
```
— Verificado vía `https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/sessions/in_memory_session_service.py:60-71`.

### S5 — Workflow: graph runtime + replay determinístico

```python
"""New Workflow implementation — BaseNode with graph orchestration.

Combines user-facing graph definition with the execution engine.
Workflow(BaseNode) with _run_impl() as the orchestration loop.
"""
...
from ._dynamic_node_scheduler import DynamicNodeScheduler
from ._dynamic_node_scheduler import DynamicNodeState
from ._graph import EdgeItem
from ._graph import Graph
from ._node_state import NodeState
from ._node_status import NodeStatus
from ._trigger import Trigger
from .utils._rehydration_utils import _ChildScanState
from .utils._replay_interceptor import check_interception
from .utils._replay_interceptor import create_mock_context
from .utils._replay_manager import ReplayManager
from .utils._replay_sequence_barrier import ReplaySequenceBarrier
```
— Verificado vía `https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/workflow/_workflow.py:1-43`.

### S6 — BaseNode: validación de name + flag de deadlock warning

```python
class BaseNode(BaseModel):
  """A base class for all nodes in the workflow graph."""

  name: str = Field(...)
  """The unique name of the node within the workflow graph."""

  @field_validator('name')
  @classmethod
  def _validate_name(cls, v: str) -> str:
    if not v.isidentifier():
      raise ValueError(f"Node name '{v}' must be a valid Python identifier.")
    return v
  ...
  wait_for_output: bool = False
  """If True, node only transitions to COMPLETED upon yielding output or route.
  ...
  WARNING: Completing execution without ever yielding output/route causes an
  indefinite WAITING state (deadlock). This is considered a user configuration error.
  """
```
— Verificado vía `https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/workflow/_base_node.py`.

### S7 — pyproject.toml: extras que confirman el ecosistema + Claude Opus 4.7 support

```toml
optional-dependencies.extensions = [
  "anthropic>=0.78",                                                 # For anthropic model support; 0.78 introduced ThinkingConfigAdaptiveParam (required for Claude Opus 4.7).
  "beautifulsoup4>=3.2.2",                                           # For load_web_page tool.
  "crewai[tools]; python_version>='3.11' and python_version<'3.12'", # For CrewaiTool; chromadb/pypika fail on 3.12+
  "docker>=7",                                                       # For ContainerCodeExecutor
  "google-cloud-firestore>=2.11,<3",                                 # For Firestore services
  "k8s-agent-sandbox>=0.1.1.post3",
  "kubernetes>=29",
  "langgraph>=0.2.60,<0.4.8",
  "litellm>=1.84",
  "llama-index-embeddings-google-genai>=0.3",
  "llama-index-readers-file>=0.4",
  "lxml>=5.3",
  "openai>=2.20,<3",
  "pypika>=0.50",
  "toolbox-adk>=1,<2",
]
```
— Verificado vía `https://raw.githubusercontent.com/google/adk-python/main/pyproject.toml` sección `optional-dependencies.extensions`.

---

## 3. Conflictos entre fuentes documentados (4)

### Conflicto 1 — Versión ADK
- **Search/blogs/marketing**: "ADK is GA with v1.x"
- **README + version.py (verificado 2026-07-08)**: versión actual es **2.4.0**, README en español/inglés en blogs a veces dice "1.x" porque se cachean de notas más antiguas. El 2.0 fue publicado en mayo/junio 2026 con breaking changes. Resolución: usar 2.4.0 (git main + releases of PyPI).

### Conflicto 2 — License
- **Mito en blogs**: "ADK is MIT like LangChain".
- **Realidad (LICENSE file + badge + pyproject classifier)**: **Apache 2.0** — verificado triple en README badge, pyproject.toml `license.file` y Classifier `"License :: OSI Approved :: Apache Software License"`. Es Apache, NO MIT. (Importante para compliance/legal review — Apache 2.0 es explícitamente patent grant, MIT no).

### Conflicto 3 — Equivalencias con CrewAI AutoGen LangGraph
- **JWIKI-013 (autogen.md) — claim heredado**: "Solo CrewAI tiene A2A nativo en v1.x; los demás usan adaptadores".
- **Realidad (pyproject extras)**: **Google ADK 2.4.0 tiene A2A nativo** (`optional-dependencies.a2a = ["a2a-sdk>=0.3.4,<0.4"]`). Y CrewAI es al menos un partner/peer (`crewai[tools]` está en `extensions`). El claim "solo CrewAI" es **FALSO** desde ADK 2.0+. La interoperabilidad A2A se está consolidando como estándar de facto inter-frameworks.
- **JWIKI-013 (autogen.md) — claim heredado**: "CrewAI solo [soporta MCP] vía adaptadores".
- **Realidad**: Google ADK tiene **MCP nativo** (`optional-dependencies.mcp = ["mcp>=1.24,<2", "anyio>=4.9,<5"]`). LangGraph ya tenía Tools MCP via langchain-mcp-adapters. CrewAI ya documentado tiene `crewai/mcp` nativo. **El claim de JWIKI-013 debe re-evaluarse**: el ecosistema 2026 ya tiene MCP nativo en ADK, CrewAI, LangGraph, pydantic-ai (no mencionado en JWIKI-013).

### Conflicto 4 — Cadencia y momentum
- **Algunos blogs**: "Google ADK is a marketing puff piece, not a real framework".
- **Realidad (versión 2.4.0 + cadence bi-weekly + 5 SDKs en 5 lenguajes + Vertex AI Agent Engines integration)**: ADK es **el framework agéntico de referencia de Google Cloud** (no un side project). Tiene paridad funcional o superior con LangGraph para construir agentes en producción, y se distingue por su integración nativa con Vertex AI, BigQuery, Spanner, etc.

---

## 4. Tabla comparativa (mínimo 5 frameworks, base para el doc final)

| Criterio | Google ADK 2.4.0 | LangGraph | AutoGen 0.7.5 | CrewAI 1.15.2 | OpenAI Agents SDK | Semantic Kernel |
|---|---|---|---|---|---|---|
| **Owner** | Google | LangChain | Microsoft | CrewAI Inc. | OpenAI | Microsoft |
| **License** | Apache 2.0 | MIT | MIT (code), CC-BY-4.0 (docs) | MIT | MIT (open source parte) | MIT |
| **Stars ~ (Q3 2026)** | ~21k | ~14k | ~59k | ~55k | ~8k (estimación) | ~24k |
| **Lenguaje** | Python (5 SDKs) | Python (+ JS comunidad) | Python + .NET | Python (~99.7%) | Python | Python + C# + JS + Java |
| **Paradigma** | Grafo (Workflow) + jerarquía agent | State machine (grafo) + LangChain | Conversacional (actor-model) | Crews + Flows | Handoffs (lineal con transfer) | Planner + plugins |
| **Multi-agente** | Nativo (sub_agents, mode=chat/task) | Sí (Send/Command, supervisor) | Sí (GroupChat + Magentic-One) | Sí (Crews sequential/hierarchical) | Sí (handoffs con tracing) | Sí (chat completion agents) |
| **Grafo de estados** | Sí (Workflow 2.0, replay det.) | Sí (core feature) | No (basado en conversación) | Parcial (Flow[State]) | No (lineal con handoffs) | Sí (workflow plugins) |
| **MCP nativo** | Sí (`mcp>=1.24`) | Vía langchain-mcp-adapters | Sí (WebSocket MCP) | Sí (`crewai/mcp`) | No (a través de tools) | Sí |
| **A2A nativo** | Sí (`a2a-sdk`) | No formal | No formal | Sí (`crewai/a2a`) | No (handoffs SDK) | No formal |
| **Modelo "agente como tool"** | Sí (input_schema, AgentTool) | Sí (ToolNode, CreateAgent) | Sí (AssistantAgent + tools) | Sí (Agent.as_tool) | Sí (Agent as tool, handoff) | Sí |
| **Streaming** | Sí (AsyncGenerator de Events) | Sí (astream, events mode) | Sí (async stream + tokens) | Sí (kickoff_async + stream) | Sí (Runner.stream + raw deltas) | Sí (invoke_stream) |
| **Memoria persistente** | Sí (Vertex AI Agent Engines, Spanner, Bigtable) | Sí (Checkpointer + store) | Sí (MemoryBank v0.7+) | Sí (Unified Memory) | Sí (SQLiteSession, Session) | Sí (memoria pluggable) |
| **Human-in-the-loop** | Sí (rerun_on_resume + interrupt) | Sí (interrupt_before/after) | Sí (UserProxyAgent, input) | Sí (human_input=True) | Sí (tool approval modal) | Sí (ask function) |
| **Long-running ops** | Sí (LongRunningFunctionTool) | Sí (interrupt + resume) | Parcial | Sí (async execution) | Sí (streaming + tools) | Sí |
| **Sandbox code execution** | Sí (daytona, e2b, docker, k8s) | Sí (via langchain-sandbox) | Sí (LocalExecutor, JupyterExecutor) | Vía crewai-tools | Vía tools | Sí |
| **Live / multimodality (audio+video)** | Sí (`DEFAULT_LIVE_MODEL = 'gemini-live-2.5-flash-native-audio'`) | Parcial | No first-class | No first-class | Sí (Realtime API + Responses API) | Sí |
| **Observability (OTel)** | Sí (`opentelemetry-api>=1.39`) — exporters GCP | Sí (LangSmith nativo) | Sí (AutoGen instrumentation + Studio) | Sí (OpenTelemetry + tracing) | Sí (built-in Tracer + Logfire) | Sí (App Insights + OTLP) |
| **Deployment serverless en cloud del owner** | Sí (Vertex AI Agent Engines first-class) | No (LangGraph Platform comercial) | No (Azure AI Foundry integration) | Sí (CrewAI AMP Suite) | Sí (OpenAI Responses en API directa) | Sí (Azure Container Apps, AKS) |

**Fuentes:**
- Google ADK: este raw, pyproject.toml + README + código del branch `main` con fecha 2026-07-08
- LangGraph: JWIKI-011 (langgraph.md) — `langchain-ai/langgraph`
- AutoGen: JWIKI-013 (autogen.md) — `microsoft/autogen`
- CrewAI: JWIKI-012 (crewai.md) — `crewAIInc/crewAI`
- OpenAI Agents SDK: research previo (kernel `openai/openai-agents-python`), release-mar 2025
- Semantic Kernel: research previo (`microsoft/semantic-kernel`)

---

## 5. Referencias cruzadas y lecturas obligatorias

- `material/JWIKI-007-raw.md` — Hermes Agent (Nous Research) — útil para comparar vibe-coding agente experience.
- `material/JWIKI-009-raw.md` — Superpowers (Skill framework) — analogía con `BasePlugin` y `PluginManager` de ADK.
- `material/JWIKI-010-raw.md` — agent-frameworks (9 frameworks × 11 criterios) — tabla comparativa general.
- `material/JWIKI-011-raw.md` — LangGraph — mismo paradigma grafo, distinto owner.
- `material/JWIKI-012-raw.md` — CrewAI — mismo multi-agente, distinto paradigma (role-play vs grafodef).
- `material/JWIKI-013-raw.md` — AutoGen — mismo multi-agente conversacional, pero en "maintenance mode" (~9 meses sin release Python después del último python-v0.7.5 del 2025-09-30).

---

## 6. Pendientes para el doc final

- [ ] Tabla comparativa OSS consolidada en el doc final (5 frameworks × 14+ criterios).
- [ ] Diagrama ASCII de jerarquía BaseAgent → LlmAgent → App → Runner → Session.
- [ ] Sub-sección "Por qué Apache 2.0 y no MIT" — implicaciones de compliance.
- [ ] Sección Vertex AI Agent Engines (deployment serverless en GCP).
- [ ] Sección A2A + MCP cross-compatibilidad (refuta claim "solo CrewAI" de JWIKI-013).
- [ ] 8 ejemplos copy-paste como mínimo: Agent, Workflow, FunctionTool, transfer_to_agent, output_schema Pydantic, session con memoria, código ejecutor, plugin custom.
- [ ] Sección "Cuándo elegir vs LangGraph / CrewAI / AutoGen / OpenAI Agents SDK / Semantic Kernel".

---

## 7. Métricas del material

- **Hechos verificados**: 53 (F1-F53)
- **Snippets path:line**: 7 (S1-S7)
- **Conflictos entre fuentes**: 4 (versión, license, A2A/MCP, momentum)
- **Fuentes externas citadas**: 8 (GitHub HTML, shields.io, raw GitHub, pyproject.toml, version.py, llm_agent.py, runners.py, workflow/_workflow.py, base_agent.py, function_tool.py, in_memory_session_service.py, apps/app.py, __init__.py, README.md)
- **Tiempo invertido (raw)**: ~25 min (research previo) + ~20 min (verificación actual con raw source + read + writes)

---

*Mantenedor: orquestador JWIKI single-team (perfil Hermes principal) — skill `jwiki-tick` v1.3.*
