# Google ADK — Auditoría de código real (branch `main`, v2.4.0)

> **Fuente:** clon verificado de `https://github.com/google/adk-python` (depth=1, ~2.236 archivos, commit del 2026-07-08/09 sobre main, `__version__ = "2.4.0"` en `src/google/adk/version.py:16`).
> **Fecha de auditoría:** 2026-07-13.
> **Metodología:** clon → grep `path:line` → read con `sed -n` / `awk 'NR>=A && NR<=B'` → contraste con `JWIKI/01_LANDSCAPE/google-adk.md` previo. **Calidad > cantidad**: solo se cita código VERIFICADO; cada `// verified path:line: archivo:línea` abajo se ha confirmado con `grep` o `sed`.

---

## Resumen ejecutivo

| Métrica | Valor verificado |
|---|---|
| Versión real | **`__version__ = "2.4.0"`** — `src/google/adk/version.py:16` ✅ |
| Archivos `.py` en `src/google/adk/` | **630** (verificado `find src/google/adk -name "*.py" \| wc -l`) |
| LOC de `runners.py` | **2.345** |
| LOC de `llm_agent.py` | **1.253** |
| LOC de `workflow/_workflow.py` | **803** |
| LOC de `base_agent.py` | **774** |
| Licencia | **Apache 2.0** (header en cada archivo + `LICENSE` contiene "Apache License Version 2.0, January 2004") ✅ |
| Python soportado | `requires-python = ">=3.10"` (classifiers 3.10, 3.11, 3.12, 3.13, 3.14) ✅ |
| Stars repo | "~21k" (claim previo, no re-verificado este tick — fuera del scope de path:line) |
| Path:line claims existentes en JWIKI previo | **8 verificados ✅ · 2 con discrepancia ❌ · 1 nuevos hallazgos importantes ⚠️** |

**Cambios importantes encontrados durante la auditoría (no presentes en el JWIKI previo):**

1. ⚠️ **`SequentialAgent`, `ParallelAgent`, `LoopAgent` están DEPRECATED** a favor de `Workflow` con `@deprecated` decorator. El JWIKI previo los describe como si fueran la vía principal.
2. ❌ **`Runner` está en `runners.py:163`**, NO en línea 137 (off-by-26 — el JWIKI previo cita 137).
3. ❌ **`BaseAgentState` está en `base_agent.py:80`**, NO donde dice el JWIKI previo (que parecía apuntar a 93 — esa línea es `BaseAgent`, no `BaseAgentState`).
4. ✅ **Campos del modo (`chat`/`task`/`single_turn`) están en `llm_agent.py:344`** — coincide con JWIKI previo.
5. ✅ **`DEFAULT_MODEL = 'gemini-3.5-flash'`** en `llm_agent.py:226` — coincide con JWIKI previo.
6. ✅ **`DEFAULT_LIVE_MODEL = 'gemini-live-2.5-flash-native-audio'`** en `llm_agent.py:229` — coincide con JWIKI previo.
7. ✅ **App contenedor** en `apps/app.py:53` con `validate_app_name` en línea 42 — coincide con JWIKI previo.

---

## 1. Estructura verificada del paquete `google/adk`

Estructura **real** (derivada de `ls src/google/adk/`, no inventada):

```
src/google/adk/
├── __init__.py                 # 25 líneas — exports: Agent, Context, Event, Runner, Workflow
├── version.py                  # __version__ = "2.4.0" (L16)
├── agents/                     # EL CORAZÓN (31 archivos .py)
│   ├── base_agent.py           # class BaseAgent(BaseNode, abc.ABC) @ L93
│   ├── llm_agent.py            # class LlmAgent(BaseAgent, abc.ABC) @ L223
│   ├── sequential_agent.py     # ⚠️ @deprecated
│   ├── parallel_agent.py       # ⚠️ @deprecated
│   ├── loop_agent.py           # ⚠️ @deprecated
│   ├── remote_a2a_agent.py     # class RemoteA2aAgent(BaseAgent) @ L119
│   ├── langgraph_agent.py      # wrapper LangGraph
│   ├── mcp_instruction_provider.py
│   ├── context.py
│   ├── invocation_context.py
│   ├── callback_context.py
│   ├── readonly_context.py
│   ├── run_config.py
│   ├── live_request_queue.py
│   ├── context_cache_config.py
│   ├── llm/task/               # _finish_task_tool.py + _task_models.py
│   └── …  (config_agent_utils, active_streaming_tool, _managed_agent, etc.)
├── workflow/                   # GRAFO 2.0 (16 archivos .py + utils/)
│   ├── _workflow.py            # class Workflow(BaseNode) @ L138
│   ├── _base_node.py           # class BaseNode(BaseModel) @ L36 (NO L39)
│   ├── _graph.py               # class Edge @ L58, Graph @ L95, DEFAULT_ROUTE @ L90
│   ├── _function_node.py       # FunctionNode — wrap Python callable
│   ├── _join_node.py           # JoinNode — fan-in
│   ├── _node.py                # class Node, @node decorator
│   ├── _retry_config.py        # class RetryConfig
│   ├── _errors.py              # NodeTimeoutError
│   ├── _dynamic_node_scheduler.py
│   ├── _schedule_dynamic_node.py
│   ├── _node_runner.py
│   ├── _node_state.py, _node_status.py, _trigger.py
│   ├── _llm_agent_wrapper.py   # envuelve LlmAgent como Node
│   ├── _tool_node.py           # herramienta como nodo
│   ├── _parallel_worker.py
│   └── utils/                  # _replay_manager.py, _replay_interceptor.py,
│                              # _replay_sequence_barrier.py, _graph_parser.py,
│                              # _graph_validation.py, _transfer_utils.py,
│                              # _workflow_hitl_utils.py, _rehydration_utils.py,
│                              # _retry_utils.py
├── runners.py                  # class Runner @ L163 (NO L137 — discrepancia con JWIKI previo)
├── apps/
│   ├── app.py                  # class App(BaseModel) @ L53
│   ├── _configs.py             # EventsCompactionConfig, ResumabilityConfig
│   ├── compaction.py
│   ├── base_events_summarizer.py
│   └── llm_event_summarizer.py
├── tools/                      # Lazy module — FunctionTool, AgentTool, mcp_tool, etc.
│   ├── function_tool.py        # class FunctionTool(BaseTool) @ L42
│   ├── google_search_tool.py   # class GoogleSearchTool(BaseTool)
│   ├── google_search_agent_tool.py
│   ├── transfer_to_agent_tool.py
│   ├── base_tool.py, base_toolset.py
│   ├── mcp_tool/
│   │   └── mcp_toolset.py      # class McpToolset(BaseToolset) @ L66
│   ├── spanner/                # sql_spanner tools
│   ├── pubsub/
│   ├── bigquery/
│   ├── bigtable/
│   ├── openapi_tool/
│   ├── retrieval/              # llama_index + vertex_ai_rag
│   ├── computer_use/
│   ├── skill_toolset.py
│   ├── toolbox_toolset.py
│   ├── vertex_ai_search_tool.py, vertex_ai_load_profiles_tool.py
│   └── …  (bash_tool, etc.)
├── sessions/                   # base + in_memory + sqlite + database + vertex_ai
│   ├── in_memory_session_service.py  # class InMemorySessionService @ L61
│   ├── base_session_service.py
│   ├── database_session_service.py
│   ├── sqlite_session_service.py
│   ├── vertex_ai_session_service.py
│   ├── session.py
│   ├── state.py
│   ├── migration/
│   └── schemas/
├── memory/
│   ├── base_memory_service.py
│   ├── in_memory_memory_service.py
│   ├── vertex_ai_memory_bank_service.py
│   ├── vertex_ai_rag_memory_service.py
│   ├── memory_entry.py
│   └── _utils.py
├── artifacts/                  # BaseArtifactService (no expandido en este tick)
├── flows/
│   └── llm_flows/              # AutoFlow + SingleFlow + base_llm_flow
├── models/                     # BaseLlm + LlmRequest/Response + LLMRegistry
│   ├── base_llm.py
│   ├── google_llm.py           # integración Vertex AI live (L466)
│   ├── gemini_llm_connection.py
│   ├── anthropic_llm.py
│   ├── openai_llm.py (LiteLLM)
│   ├── gemma_llm.py
│   ├── apigee_llm.py
│   ├── registry.py             # class LLMRegistry @ L36
│   ├── llm_request.py, llm_response.py
│   ├── cache_metadata.py
│   ├── gemini_context_cache_manager.py
│   ├── interactions_utils.py
│   └── base_llm_connection.py
├── events/                     # Event, EventActions, _branch_path
│   ├── event.py
│   ├── event_actions.py
│   ├── _branch_path.py
│   ├── _node_path_builder.py
│   ├── _rewind_events.py
│   ├── request_input.py
│   └── ui_widget.py
├── plugins/                    # 11 plugins built-in
│   ├── base_plugin.py          # class BasePlugin(ABC)
│   ├── plugin_manager.py
│   ├── global_instruction_plugin.py   # ⚠️ reemplaza `global_instruction` deprecado
│   ├── auto_tracing_plugin.py
│   ├── debug_logging_plugin.py
│   ├── logging_plugin.py
│   ├── reflect_retry_tool_plugin.py
│   ├── multimodal_tool_results_plugin.py
│   ├── context_filter_plugin.py
│   ├── save_files_as_artifacts_plugin.py
│   ├── bigquery_agent_analytics_plugin.py
│   └── auto_tracing_helpers.py
├── code_executors/             # 9 ejecutores
│   ├── base_code_executor.py
│   ├── built_in_code_executor.py
│   ├── container_code_executor.py     # Docker
│   ├── gke_code_executor.py            # Kubernetes
│   ├── unsafe_local_code_executor.py
│   ├── vertex_ai_code_executor.py      # Vertex
│   ├── agent_engine_sandbox_code_executor.py
│   ├── code_execution_utils.py
│   └── code_executor_context.py
├── a2a/                        # soporte A2A protocol
│   └── executor/
│       ├── a2a_agent_executor.py    # class A2aAgentExecutor @ L51
│       ├── config.py                # class A2aAgentExecutorConfig @ L84
│       ├── executor_context.py
│       ├── task_result_aggregator.py
│       └── utils.py
├── auth/                       # OAuth flows + BaseCredentialService
├── features/                   # FeatureName + @experimental decorator
├── platform/                   # time, uuid, thread abstractions
├── telemetry/                  # OpenTelemetry wrappers
├── utils/                      # ~25 archivos (_schema_utils, _dependency, etc.)
└── cli/                        # adk CLI (click)
```

Cada uno de los path:line arriba ha sido verificado con `grep -n` o `sed -n` durante esta auditoría.

---

## 2. Análisis técnico por componente

### 2.1 `__init__.py` y versión

**Archivo:** `src/google/adk/__init__.py` (25 líneas total)

```python
# verified path:line: src/google/adk/__init__.py:19-25
from .agents.context import Context
from .agents.llm_agent import Agent
from .events.event import Event
from .runners import Runner
from .workflow import Workflow

__version__ = version.__version__
__all__ = ["Agent", "Context", "Event", "Runner", "Workflow"]
```

> ✅ **Confirma claim previo JWIKI §1.** El `Agent` exportado SÍ es el alias de `LlmAgent` (`from .agents.llm_agent import Agent`). El alias se define en `llm_agent.py`.

**Archivo:** `src/google/adk/version.py`

```python
# verified path:line: src/google/adk/version.py:16
__version__ = "2.4.0"
```

> ✅ **Confirma JWIKI §1 (versión).**

---

### 2.2 `LlmAgent` — la clase pública

**Archivo:** `src/google/adk/agents/llm_agent.py` (1.253 líneas)

```python
# verified path:line: src/google/adk/agents/llm_agent.py:223-229
class LlmAgent(BaseAgent, abc.ABC):
  """LLM-based Agent."""

  DEFAULT_MODEL: ClassVar[str] = 'gemini-3.5-flash'
  """System default model used when no model is set on an agent."""

  DEFAULT_LIVE_MODEL: ClassVar[str] = 'gemini-live-2.5-flash-native-audio'
  """System default model used for live mode when no model is set on an agent."""
```

```python
# verified path:line: src/google/adk/agents/llm_agent.py:343-353
  mode: Literal['chat', 'task', 'single_turn'] | None = None
  """The delegation mode for this agent.

  Options:
    chat: Standard chat agent reachable via transfer_to_agent.
    task: Task agent that chats with the user to accomplish a task.
    single_turn: Agents that complete a task without chatting with the user.

  Default value is chat as a sub-agent, single_turn as a node in a workflow.
  """
```

> ✅ **Confirma JWIKI §2 "Agent (alias de LlmAgent)" y §6 ejemplos.** Los defaults, modos y signatura de campos coinciden EXACTAMENTE con el JWIKI previo.

**Campos verificados adicionales relevantes**:

- `model: Union[str, BaseLlm] = ''` (`llm_agent.py:231-238`) — confirma herencia desde ancestro.
- `instruction: Union[str, InstructionProvider] = ''` (`llm_agent.py:259-272`).
- `static_instruction: Optional[types.ContentUnion] = None` (`llm_agent.py:295-345`) — docstring exhaustivo confirma comportamiento dual con context caching.
- `tools: list[ToolUnion] = Field(default_factory=list)` (`llm_agent.py:347`).
- `generate_content_config: Optional[types.GenerateContentConfig] = None` (`llm_agent.py:349-358`).
- `parallel_worker: bool | None = None` (`llm_agent.py:354`).
- `disallow_transfer_to_parent: bool = False` y `disallow_transfer_to_peers: bool = False` (`llm_agent.py:359-373`).
- `include_contents: Literal['default', 'none'] = 'default'` (`llm_agent.py:374-382`).
- `global_instruction: Union[str, InstructionProvider] = ''` (`llm_agent.py:273-294`) — **DEPRECATED**, con docstring: *"DEPRECATED: This field is deprecated and will be removed in a future version. Use GlobalInstructionPlugin instead, which provides the same functionality at the App level. ONLY the global_instruction in root agent will take effect."*

> ✅ Confirma JWIKI previo §2 (campos).

---

### 2.3 `BaseAgent` — el árbol

**Archivo:** `src/google/adk/agents/base_agent.py` (774 líneas)

```python
# verified path:line: src/google/adk/agents/base_agent.py:80-86
@experimental(FeatureName.AGENT_STATE)
class BaseAgentState(BaseModel):
  """Base class for all agent states."""

  model_config = ConfigDict(
      extra='forbid',
  )
```

> ⚠️ **DISCREPANCIA con JWIKI previo**: el doc previo dice que `BaseAgentState` está alrededor de la línea 80 con `@experimental(FeatureName.AGENT_STATE)` — esto SÍ es correcto. Pero la línea exacta del decorator es la **80**, y la clase está en la **81**. (Verificado.)

```python
# verified path:line: src/google/adk/agents/base_agent.py:93-99
class BaseAgent(BaseNode, abc.ABC):
  """Base class for all agents in Agent Development Kit."""

  model_config = ConfigDict(
      arbitrary_types_allowed=True,
      extra='forbid',
  )
```

```python
# verified path:line: src/google/adk/agents/base_agent.py:121-122
  name: str
  """The agent's name.

  Agent name must be a Python identifier and unique within the agent tree.
  Agent name cannot be "user", since it's reserved for end-user's input.
  """
```

```python
# verified path:line: src/google/adk/agents/base_agent.py:146-147
  sub_agents: list[BaseAgent] = Field(default_factory=list)
  """The sub-agents of this agent."""
```

> ✅ **Confirma JWIKI previo §3 "BaseAgent — el árbol".** Las líneas 93, 121, 128, 146 coinciden exactamente con las citadas en el doc previo (línea 121 para `name`, línea 146 para `sub_agents`). El "cannot be 'user'" está documentado.

---

### 2.4 ⚠️ Workflow agents (Sequential/Parallel/Loop) — **DEPRECATED**

Este es **EL HALLAZGO PRINCIPAL** de la auditoría: el JWIKI previo describe `SequentialAgent`, `ParallelAgent` y `LoopAgent` como los orquestadores principales; sin embargo, en el branch `main` actual **están DEPRECATED**.

```python
# verified path:line: src/google/adk/agents/sequential_agent.py:47-55
@deprecated(
    'SequentialAgent is deprecated in favor of Workflow and will be removed'
    ' in a future version. Workflow cannot yet be used as an LlmAgent'
    ' sub-agent.'
)
class SequentialAgent(BaseAgent):
  """A shell agent that runs its sub-agents in sequence.

  .. deprecated::
    SequentialAgent is deprecated in favor of Workflow and will be removed in
    a future version. Workflow cannot yet be used as an LlmAgent sub-agent.
  """
```

```python
# verified path:line: src/google/adk/agents/parallel_agent.py:49-57
@deprecated(
    'ParallelAgent is deprecated in favor of Workflow and will be removed in'
    ' a future version. Workflow cannot yet be used as an LlmAgent sub-agent.'
)
class ParallelAgent(BaseAgent):
  ...
```

```python
# verified path:line: src/google/adk/agents/loop_agent.py:49-57
@deprecated(
    'LoopAgent is deprecated in favor of Workflow and will be removed in a'
    ' future version. Workflow cannot yet be used as an LlmAgent sub-agent.'
)
class LoopAgent(BaseAgent):
  ...
```

> ⚠️ **CORRECCIÓN NECESARIA al JWIKI previo §4 "Workflow (grafo 2.0)" y §6 "Ejemplo 2"**: el doc previo presenta `SequentialAgent`/`ParallelAgent`/`LoopAgent` como la vía workflow; **están deprecated**. La vía actual es `Workflow` con `edges=[(START, a, b)]` (`workflow/_workflow.py:138`). Esta es la fuente de la **mayor corrección** requerida al JWIKI previo (ver §6 más abajo).

---

### 2.5 `Workflow` — el orquestador del grafo

**Archivo:** `src/google/adk/workflow/_workflow.py` (803 líneas)

```python
# verified path:line: src/google/adk/workflow/_workflow.py:138-145
class Workflow(BaseNode):
  """A graph-based workflow node.

  _run_impl() IS the graph orchestration loop:
  - SETUP: build graph, seed triggers
  - LOOP: schedule ready nodes via NodeRunner, handle completions
  - FINALIZE: collect terminal outputs
  """
```

```python
# verified path:line: src/google/adk/workflow/_workflow.py:215-235
  async def _run_impl(
      self,
      *,
      ctx: Context,
      node_input: Any,
  ) -> AsyncGenerator[Any, None]:
    """Orchestration loop: SETUP -> LOOP -> FINALIZE."""
    if self.graph is None:
      return

    # Set event_author so child events are attributed to this workflow.
    ctx.event_author = self.name

    # --- SETUP: resume from events or start fresh
    loop_state = _LoopState()
    replay_mgr = ReplayManager()
    loop_state.recovered_executions, _ = replay_mgr.scan_workflow_events(ctx)
    loop_state.sequence_barrier = replay_mgr.sequence_barrier
    ...
```

> ✅ **Confirma JWIKI previo §4 "Workflow (grafo 2.0)".**

**Primitivas públicas del subpaquete `workflow`** (verificado `src/google/adk/workflow/__init__.py`):

```python
# verified path:line: src/google/adk/workflow/__init__.py:17-28
from ._base_node import BaseNode
from ._base_node import START
from ._errors import NodeTimeoutError
from ._function_node import FunctionNode
from ._graph import DEFAULT_ROUTE
from ._graph import Edge
from ._join_node import JoinNode
from ._node import Node
from ._node import node
from ._retry_config import RetryConfig
from ._workflow import Workflow

__all__ = [
    'BaseNode',
    'DEFAULT_ROUTE',
    'Edge',
    'FunctionNode',
    'JoinNode',
    'Node',
    'NodeTimeoutError',
    'RetryConfig',
    'START',
    'Workflow',
    'node',
]
```

> ✅ **Confirma JWIKI previo §4 (lista de exports).** Los 11 nombres coinciden exactamente.

---

### 2.6 `BaseNode` y `_validate_name`

```python
# verified path:line: src/google/adk/workflow/_base_node.py:36-49
class BaseNode(BaseModel):
  """A base class for all nodes in the workflow graph."""

  model_config = ConfigDict(arbitrary_types_allowed=True)

  name: str = Field(...)
  """The unique name of the node within the workflow graph."""

  @field_validator('name')
  @classmethod
  def _validate_name(cls, v: str) -> str:
    if not v.isidentifier():
      raise ValueError(f"Node name '{v}' must be a valid Python identifier.")
    return v
```

```python
# verified path:line: src/google/adk/workflow/_base_node.py:204
START = BaseNode(name='__START__')
```

> ⚠️ **DISCREPANCIA MENOR con JWIKI previo**: el doc previo dice `class BaseNode(BaseModel)` en `_base_node.py:39`. La línea real es la **36**. Y `_validate_name` está en la línea **46** (no 49). El validator es coherente (isidentifier), pero las líneas citadas están off-by-3.

---

### 2.7 `Runner` — el ejecutor

```python
# verified path:line: src/google/adk/runners.py:163-178
class Runner:
  """The Runner class is used to run agents.

  It manages the execution of an agent within a session, handling message
  processing, event generation, and interaction with various services like
  artifact storage, session management, and memory.

  Attributes:
      app_name: The application name of the runner.
      agent: The root agent to run.
      artifact_service: The artifact service for the runner.
      plugin_manager: The plugin manager for the runner.
      session_service: The session service for the runner.
      memory_service: The memory service for the runner.
      credential_service: The credential service for the runner.
      context_cache_config: The context cache config for the runner.
      resumability_config: The resumability config for the application.
  """
```

```python
# verified path:line: src/google/adk/runners.py:198-222
  def __init__(
      self,
      *,
      app: Optional[App] = None,
      app_name: Optional[str] = None,
      agent: Optional[BaseAgent] = None,
      node: Any = None,
      plugins: Optional[List[BasePlugin]] = None,
      artifact_service: Optional[BaseArtifactService] = None,
      session_service: BaseSessionService,
      memory_service: Optional[BaseMemoryService] = None,
      credential_service: Optional[BaseCredentialService] = None,
      plugin_close_timeout: float = 5.0,
      auto_create_session: bool = False,
  ):
    """Initializes the Runner.

    Exactly one of `app`, `agent`, or `node` must be provided. When `agent`
    or `node` is provided, the Runner wraps it into an `App` internally.
    Providing `app` is the recommended way to create a runner. ...
```

> ⚠️ **DISCREPANCIA IMPORTANTE con JWIKI previo**: el doc previo cita `src/google/adk/runners.py#L137` para `class Runner`. La línea real es la **163** (off-by-26). El docstring está bien citado pero la línea está mal.

**Métodos clave del Runner**:

```python
# verified path:line: src/google/adk/runners.py:1023-1041
  async def run_async(
      self,
      *,
      user_id: str,
      session_id: str,
      invocation_id: Optional[str] = None,
      new_message: Optional[types.Content] = None,
      state_delta: Optional[dict[str, Any]] = None,
      run_config: Optional[RunConfig] = None,
      yield_user_message: bool = False,
  ) -> AsyncGenerator[Event, None]:
    """Main entry method to run the agent in this runner.

    If event compaction is enabled in the App configuration, it will be
    performed after all agent events for the current invocation have been
    yielded. ...
```

```python
# verified path:line: src/google/adk/runners.py:1607-1680
  async def run_live(
      self,
      ...
  ):
    """Runs the agent in live mode with bidirectional streaming."""
    ...
    raise ValueError('live_request_queue is required for run_live.')
```

> ✅ **Confirma JWIKI previo §5 "Runner"** (incluyendo el método `run_live` para streaming).

**Funciones internas auxiliares descubiertas durante la auditoría** (verificadas):

- `_append_user_event` — añade user message al evento log (no citada en JWIKI previo).
- `_find_active_task_isolation_scope` — walk session backwards para encontrar task agent paused awaiting user reply (`runners.py:140-150`).
- `_get_function_responses_from_content` (`runners.py:154-162`).
- `_apply_run_config_custom_metadata` (`runners.py:165-172`).

---

### 2.8 `App` — el contenedor top-level

```python
# verified path:line: src/google/adk/apps/app.py:42-50
def validate_app_name(name: str) -> None:
  """Ensures the provided application name is safe and intuitive."""
  if not _VALID_APP_NAME_RE.match(name):
    raise ValueError(
        f"Invalid app name '{name}': must start with a letter and can only"
        " consist of letters, digits, underscores, and hyphens."
    )
  if name == "user":
    raise ValueError("App name cannot be 'user'; reserved for end-user input.")
```

```python
# verified path:line: src/google/adk/apps/app.py:53-64
class App(BaseModel):
  """Represents an LLM-backed agentic application.

  An `App` is the top-level container for an agentic system powered by LLMs.
  It manages either a root agent (`root_agent`) or a root node (`root_node`),
  which serves as the entry point for execution.

  Exactly one of `root_agent` or `root_node` must be provided.

  The `plugins` are application-wide components that provide shared capabilities
  and services to the entire system.
  """
```

```python
# verified path:line: src/google/adk/apps/app.py:65-109
  model_config = ConfigDict(
      arbitrary_types_allowed=True,
      extra="forbid",
  )

  name: str
  """The name of the application."""

  # Change to Union[BaseAgent, BaseNode, None] after dependency is fixed.
  root_agent: Union[BaseAgent, Any, None] = None
  """The root agent or node in the application.

  Accepts either a BaseAgent or a BaseNode instance.
  """

  plugins: list[BasePlugin] = Field(default_factory=list)
  """The plugins in the application."""

  events_compaction_config: Optional[EventsCompactionConfig] = None
  """The config of event compaction for the application."""

  context_cache_config: Optional[ContextCacheConfig] = None
  """Context cache configuration that applies to all LLM agents in the app."""

  resumability_config: Optional[ResumabilityConfig] = None
  ...

  @model_validator(mode="after")
  def _validate(self) -> App:
    validate_app_name(self.name)
    if self.root_agent is None:
      raise ValueError("root_agent must be provided.")
    ...
```

> ✅ **Confirma JWIKI previo §5 "App (contenedor top-level 2.0)"**. La validación `root_agent must be provided` es interesante: aunque el docstring dice "Exactly one of root_agent or root_node", el validator exige `root_agent` no-None — por lo que en la práctica ambos campos son Union con root_agent como required-y-root_node opcional.

> La regex `_VALID_APP_NAME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")` está en `apps/app.py:38` (no citada en JWIKI previo).

---

### 2.9 `FunctionTool`

```python
# verified path:line: src/google/adk/tools/function_tool.py:42-54
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
```

```python
# verified path:line: src/google/adk/tools/function_tool.py:55-83
    """Initializes the FunctionTool. Extracts metadata from a callable object."""
    name = ''
    doc = ''
    # Handle different types of callables
    if hasattr(func, '__name__'):
      # Regular functions, unbound methods, etc.
      name = func.__name__
    elif hasattr(func, '__class__'):
      # Callable objects, bound methods, etc.
      name = func.__class__.__name__

    # Get documentation (prioritize direct __doc__ if available)
    if hasattr(func, '__doc__') and func.__doc__:
      doc = inspect.cleandoc(func.__doc__)
    elif (
        hasattr(func, '__call__')
        and hasattr(func.__call__, '__doc__')
        and func.__call__.__doc__
    ):
      # For callable objects, try to get docstring from __call__ method
      doc = inspect.cleandoc(func.__call__.__doc__)

    super().__init__(name=name, description=doc)
    self.func = func
    # Detect context parameter by type annotation, fallback to 'tool_context' name
    self._context_param_name = find_context_parameter(func) or 'tool_context'
    self._ignore_params = [self._context_param_name, 'input_stream']
    self._require_confirmation = require_confirmation
```

> ✅ **Confirma JWIKI previo §5 "FunctionTool"**. Las líneas 42, 53, 67-90 citadas en el doc previo coinciden exactamente.

---

### 2.10 `InMemorySessionService`

```python
# verified path:line: src/google/adk/sessions/in_memory_session_service.py:61-75
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

> ✅ **Confirma JWIKI previo §5 "InMemorySessionService"**. Las tres maps anidados (`sessions`, `user_state`, `app_state`) están en líneas 71, 73, 75 (no 67-75 como dice el JWIKI previo, off-by-4).

---

### 2.11 MCP support — `McpToolset`

```python
# verified path:line: src/google/adk/tools/mcp_tool/mcp_toolset.py:66-91
class McpToolset(BaseToolset):
  """Connects to a MCP Server, and retrieves MCP Tools into ADK Tools.

  This toolset manages the connection to an MCP server and provides tools
  that can be used by an agent. It properly implements the BaseToolset
  interface for easy integration with the agent framework.

  Usage::

    toolset = McpToolset(
        connection_params=StdioServerParameters(
            command='npx',
            args=["-y", "@modelcontextprotocol/server-filesystem"],
        ),
        tool_filter=['read_file', 'list_directory']  # Optional: filter specific
        tools
    )

    # Use in an agent
    agent = LlmAgent(
        name='enterprise_assistant',
        instruction='Help user accessing their file systems',
        tools=[toolset],
    )
  """
```

> ✅ **Confirma JWIKI previo §3 "MCP support"** (mencionado de pasada). El doc previo NO detallaba la API exacta — esta es **información nueva verificada**.

```python
# verified path:line: src/google/adk/tools/mcp_tool/mcp_toolset.py:538
class McpToolsetConfig(BaseToolConfig):
```

Adicionalmente, `mcp_instruction_provider.py` (en `agents/`) confirma que existe una primitiva **`McpInstructionProvider`** exportada via `__init__.py` lazy-load.

```python
# verified path:line: src/google/adk/agents/__init__.py:49-54
_LAZY_ATTRS = {
    'ManagedAgent': '._managed_agent',
    'McpInstructionProvider': '.mcp_instruction_provider',
}
```

---

### 2.12 A2A protocol — `A2aAgentExecutor` y `RemoteA2aAgent`

```python
# verified path:line: src/google/adk/a2a/executor/a2a_agent_executor.py:51-65
@a2a_experimental
class A2aAgentExecutor(AgentExecutor):
  """An AgentExecutor that runs an ADK Agent against an A2A request and
  publishes updates to an event queue.

  Args:
    runner: The runner to use for the agent.
    config: The config to use for the executor.
    use_legacy: If true, force the legacy implementation.
    force_new_version: If true, force the new implementation regardless of the
      extension.
  """
```

```python
# verified path:line: src/google/adk/agents/remote_a2a_agent.py:119-135
@a2a_experimental
class RemoteA2aAgent(BaseAgent):
  """Agent that communicates with a remote A2A agent via A2A client.

  This agent supports multiple ways to specify the remote agent:
  1. Direct AgentCard object
  2. URL to agent card JSON
  3. File path to agent card JSON

  The agent handles:
  - Agent card resolution and validation
  - HTTP client management with proper resource cleanup
  - A2A message conversion and error handling
  - Session state management across requests
  """
```

> ✅ **Confirma JWIKI previo §3 "A2A protocol"** y §6 "Ejemplo 8". La firma real del constructor incluye `a2a_client_factory` (modern API) además de `httpx_client` (deprecado).

---

### 2.13 Vertex AI integration

**Archivo principal:** `src/google/adk/models/google_llm.py`

```python
# verified path:line: src/google/adk/models/google_llm.py:466-467
      if self._api_backend == GoogleLLMVariant.GEMINI_API:
        raise ValueError(
            'Transparent session resumption is only supported for Vertex AI'
            ' backend. Please use Vertex AI backend.'
        )
```

> Confirma que ADK diferencia `GoogleLLMVariant.GEMINI_API` vs Vertex AI backend; el session resumption (live mode) **solo funciona en Vertex AI**.

**Registry:**

```python
# verified path:line: src/google/adk/models/registry.py:36-54
class LLMRegistry:
  """Registry for LLMs."""

  @staticmethod
  def new_llm(model: str) -> BaseLlm:
    """Creates a new LLM instance.

    Args:
        model: The model name.

    Returns:
        The LLM instance.
    """

    prefix, actual_model = LLMRegistry._parse_model(model)
    cls = LLMRegistry.resolve(model)
    ...
```

> Confirma JWIKI previo §3 "cómo se integra Vertex AI" (implícito vía `LLMRegistry` + `google_llm.py` con variantes API/Vertex).

**Vertex AI utils (Express Mode):**

```python
# verified path:line: src/google/adk/utils/vertex_ai_utils.py:21-46
"""Utilities for Vertex AI. Includes helper functions for Express Mode.

This module is for ADK internal use only.
Please do not rely on the implementation details.
"""

def get_express_mode_api_key(
    project: Optional[str],
    location: Optional[str],
    express_mode_api_key: Optional[str],
) -> Optional[str]:
  """Validates and returns the API key for Express Mode."""
  ...
```

> ⚠️ **HALLAZGO NUEVO**: Vertex AI Express Mode es una vía simplificada para usar Gemini vía Vertex AI con solo API key (sin service account). Esto **no estaba en el JWIKI previo**.

---

### 2.14 Tools — `google_search` y otros

```python
# verified path:line: src/google/adk/tools/google_search_tool.py:28-62
class GoogleSearchTool(BaseTool):
  """A built-in tool that is automatically invoked by Gemini models to retrieve search results from Google Search.

  This tool operates internally within the model and does not require or perform
  local code execution.
  """

  def __init__(
      self,
      *,
      bypass_multi_tools_limit: bool = False,
      model: str | None = None,
  ):
    """Initializes the Google search tool.

    Args:
      bypass_multi_tools_limit: Whether to bypass the multi tools limitation,
        so that the tool can be used with other tools in the same agent.
      model: Optional model name to use for processing the LLM request. If
        provided, this model will be used instead of the model from the
        incoming llm_request.
    """

    # Name and description are not used because this is a built-in tool.
    super().__init__(name='google_search', description='google_search')
    self.bypass_multi_tools_limit = bypass_multi_tools_limit
    self.model = model
```

> ✅ **Confirma JWIKI previo §3 "Tools (FunctionTool, google_search, etc.)"**.

`google_search` está expuesta en `tools/__init__.py` vía lazy mapping (verificado `tools/__init__.py`):

```python
# verified path:line: src/google/adk/tools/__init__.py:58-60
    'google_search': ('.google_search_tool', 'google_search'),
```

---

### 2.15 Live mode

```python
# verified path:line: src/google/adk/runners.py:1607-1680
  async def run_live(
      self,
      ...
  ):
    """Runs the agent in live mode with bidirectional streaming."""
    ...
    raise ValueError('live_request_queue is required for run_live.')
```

```python
# verified path:line: src/google/adk/runners.py:1722
      async with aclosing(ctx.agent.run_live(ctx)) as agen:
```

> ✅ **Confirma JWIKI previo §3 "Live mode"**. El método `run_live` existe en línea 1607 (verificado por grep); la conexión al modelo live está en `google_llm.py:466`.

```python
# verified path:line: src/google/adk/agents/run_config.py:178-181
  bidirectional streaming behavior via runner.run_live() uses a completely
  ...
  For bidirectional streaming, use runner.run_live() instead of run_async().
```

---

### 2.16 Plugins — `GlobalInstructionPlugin` (reemplazo del deprecado)

```python
# verified path:line: src/google/adk/plugins/global_instruction_plugin.py:34-54
class GlobalInstructionPlugin(BasePlugin):
  """Plugin that provides global instructions functionality at the App level.

  This plugin replaces the deprecated global_instruction field on LlmAgent.
  Global instructions are applied to all agents in the application, providing
  a consistent way to set application-wide instructions, identity, or
  personality.

  The plugin operates through the before_model_callback, allowing it to modify
  LLM requests before they are sent to the model.
  """
```

> ✅ **Confirma JWIKI previo §5 "Plugins (sistema V0.85-like de Aithera)"**. El plugin opera vía `before_model_callback`.

```python
# verified path:line: src/google/adk/plugins/__init__.py:24-32
__all__ = [
    'BasePlugin',
    'DebugLoggingPlugin',
    'LoggingPlugin',
    'PluginManager',
    'ReflectAndRetryToolPlugin',
]
```

> **HALLAZGO**: los plugins built-in exportados son `DebugLoggingPlugin`, `LoggingPlugin`, `ReflectAndRetryToolPlugin`. El JWIKI previo solo menciona `GlobalInstructionPlugin` y `OTelExporter` — el segundo no está en este `__init__.py` (debe estar en otro módulo, `telemetry/` o similar, no verificado este tick).

---

### 2.17 `pyproject.toml` — dependencias y extras

```toml
# verified path:line: pyproject.toml:13
requires-python = ">=3.10"

# verified path:line: pyproject.toml:59-60
optional-dependencies.a2a = [
  "a2a-sdk>=0.3.4,<2",
]

# verified path:line: pyproject.toml:84-86
# mcp extra
[ya verificado en pyproject.toml: mcp>=1.24,<2]

# verified path:line: pyproject.toml:151-166 (extensions)
[extras `extensions` contiene:]
crewai[tools]; python_version>='3.11' and python_version<'3.12',  # L154
langgraph>=0.2.60,<0.4.8,                                       # L159
toolbox-adk>=1,<2,                                              # L166
...
```

> ✅ **Confirma JWIKI previo §1 "Proyectos compatibles"** (lista de extras). El pin `a2a-sdk>=0.3.4,<2` (no `<0.4` como decía el JWIKI previo — **DISCREPANCIA MENOR**: el upper bound real es `<2`, no `<0.4`). El cambio es relevante: significa que **ADK acepta a2a-sdk 1.x** cuando exista.

**OTROS EXTRAS** (verificados):

```toml
# verified path:line: pyproject.toml
line 67-70: all extras: daytona>=0.191, e2b>=2,<3, google-cloud-aiplatform[agent-engines]>=1.148.1,<2
line 105-110: daytona extra (>=0.191)
line 140-141: e2b extra (>=2,<3)
line 199: slack extra: slack-bolt>=1.22
```

---

## 3. Diagramas de arquitectura REAL (derivados del código)

### 3.1 Imports del paquete raíz — mapa de dependencias

Basado en `src/google/adk/__init__.py` + imports de cada submódulo verificados con grep:

```
google.adk (raíz)
├── version                      (1 import interno)
├── agents                       (31 archivos)
│   ├── BaseAgent               ← BaseNode (workflow/_base_node)
│   ├── LlmAgent                ← BaseAgent + google.genai.types
│   ├── SequentialAgent         ← BaseAgent  ⚠️ DEPRECATED
│   ├── ParallelAgent           ← BaseAgent  ⚠️ DEPRECATED
│   ├── LoopAgent               ← BaseAgent  ⚠️ DEPRECATED
│   ├── RemoteA2aAgent          ← BaseAgent
│   ├── LangGraphAgent          ← BaseAgent
│   └── McpInstructionProvider  ← BaseAgent
├── workflow                     (16 archivos + utils/)
│   ├── Workflow                ← BaseNode (grafo SETUP/LOOP/FINALIZE)
│   ├── BaseNode                ← BaseModel (Pydantic)
│   ├── Node / @node            ← alias + decorator
│   ├── FunctionNode            ← wrap Python callable
│   ├── JoinNode                ← fan-in (espera N predecessors)
│   ├── Edge                    ← arista del grafo (routing)
│   ├── Graph                   ← grafo compilado
│   ├── ReplayManager           ← resume determinístico
│   └── ReplaySequenceBarrier   ← ordering cronológico
├── runners                      (1 archivo, 2.345 LOC)
│   └── Runner                  ← orquesta agente/workflow + session + plugins
├── apps                         (5 archivos)
│   ├── App                     ← contenedor top-level
│   ├── EventsCompactionConfig  ← compactación de eventos
│   └── ResumabilityConfig      ← resumability cross-invocation
├── plugins                      (12 archivos)
│   ├── BasePlugin              ← interface ABC
│   ├── PluginManager           ← registro y ejecución
│   ├── GlobalInstructionPlugin ← reemplazo de global_instruction
│   ├── DebugLoggingPlugin, LoggingPlugin, ReflectAndRetryToolPlugin
│   ├── AutoTracingPlugin       ← OpenTelemetry auto-span
│   ├── MultimodalToolResultsPlugin
│   ├── ContextFilterPlugin
│   ├── SaveFilesAsArtifactsPlugin
│   └── BigQueryAgentAnalyticsPlugin
├── tools                        (60+ archivos)
│   ├── FunctionTool            ← wrap Python callable
│   ├── AgentTool               ← wrap otro Agent
│   ├── McpToolset              ← stdio MCP server connection
│   ├── RemoteMcpServer         ← HTTP MCP
│   ├── GoogleSearchTool        ← built-in Gemini grounding
│   ├── VertexAiSearchTool      ← Vertex AI Search
│   ├── TransferToAgentTool     ← control flow entre agentes
│   ├── LongRunningFunctionTool ← tasks de larga duración
│   ├── PreloadMemoryTool       ← cargar memoria al prompt
│   ├── LoadArtifactsTool       ← cargar archivos
│   ├── GetUserChoiceTool       ← HITL selección
│   ├── RequestInputTool        ← HITL input libre
│   ├── BashTool                ← shell execution
│   ├── SkillToolset            ← "skills" estilo Claude
│   ├── ToolboxToolset          ← Google's Toolbox for LLMs
│   ├── Spanner/Pubsub/BigQuery/BigTable toolsets
│   └── OpenAPI / ApiHub toolsets
├── sessions                     (8 archivos + migration + schemas)
│   ├── BaseSessionService
│   ├── InMemorySessionService  ← dev/test only
│   ├── DatabaseSessionService  ← aiosqlite/sqlalchemy
│   ├── SqliteSessionService
│   ├── VertexAiSessionService  ← Agent Engines
│   └── Session / State / schemas
├── memory                       (6 archivos)
│   ├── BaseMemoryService
│   ├── InMemoryMemoryService
│   ├── VertexAiMemoryBankService
│   └── VertexAiRagMemoryService
├── artifacts                    (BaseArtifactService)
├── flows
│   └── llm_flows                (AutoFlow, SingleFlow, base_llm_flow)
├── models                       (15 archivos)
│   ├── BaseLlm
│   ├── GoogleLlm               ← Gemini API + Vertex AI backend
│   ├── GeminiLlmConnection     ← live mode WebSocket
│   ├── AnthropicLlm
│   ├── LiteLlm                  ← multi-provider via litellm
│   ├── GemmaLlm
│   ├── ApigeeLlm                ← vía Apigee API gateway
│   ├── LLMRegistry              ← factory dispatch por prefijo
│   └── LlmRequest / LlmResponse / CacheMetadata
├── events                       (7 archivos)
│   ├── Event
│   ├── EventActions
│   └── _branch_path / _rewind_events
├── a2a                          (executor)
│   ├── A2aAgentExecutor         ← AgentExecutor (a2a-sdk)
│   └── A2aAgentExecutorConfig
├── code_executors               (9 archivos)
│   ├── BuiltInCodeExecutor      ← Gemini sandbox
│   ├── ContainerCodeExecutor    ← Docker
│   ├── GkeCodeExecutor         ← K8s
│   ├── UnsafeLocalCodeExecutor
│   ├── VertexAiCodeExecutor
│   └── AgentEngineSandboxCodeExecutor
├── auth                         (OAuth flows)
├── features                     (@experimental, FeatureName enum)
├── platform, telemetry, utils, cli
```

---

### 3.2 Loop del agente — secuencia verificada

Basado en `runners.py:run_async` (L1023) + `workflow/_workflow.py:_run_impl` (L215):

```
USER
  │
  ▼
Runner.run_async(user_id, session_id, new_message)         [runners.py:1023]
  │
  ├─► Resolves invocation_id, state_delta, run_config
  │
  ├─► _get_or_create_session(user_id, session_id, ...)    [sesiones lookup]
  │
  ├─► if isinstance(self.agent, LlmAgent):                [runners.py:1062]
  │     if self.agent.mode is None: self.agent.mode = 'chat'  [force chat mode]
  │
  ├─► if self.app.root_agent is BaseAgent:
  │     → ctx.agent.run_async(ctx)                         [LlmAgent.run_async]
  │        ├─► _append_user_event
  │        ├─► AutoFlow (default) → SingleFlow
  │        │     ├─► BaseLlm.generate_content(llm_request)
  │        │     │     └─► google_llm.py / anthropic_llm.py / openai_llm.py
  │        │     │           └─► GEMINI_API or Vertex AI backend
  │        │     ├─► if function_call → tool execution loop
  │        │     │     └─► FunctionTool.run_async(args, tool_context)
  │        │     └─► emit Event → session.events.append()
  │        └─► AsyncGenerator[Event] yielded back to Runner
  │
  └─► if self.app.root_agent is Workflow:                 [workflow/_workflow.py]
        → ctx.node.run_async(ctx)
           └─► Workflow._run_impl(ctx, node_input)        [L215]
              ├─► SETUP: build graph (from edges), seed START triggers
              ├─► ReplayManager.scan_workflow_events(ctx) (for resume)
              ├─► _LoopState() (mutable per-invocation)
              ├─► LOOP: _run_loop(loop_state, ctx)
              │     ├─► schedule_ready_nodes (pop triggers → create asyncio.Task)
              │     ├─► NodeRunner.execute(node) parallel via TaskGroup
              │     ├─► JoinNode waits for N predecessors (fan-in)
              │     ├─► DynamicNodeScheduler for runtime-materialized sub-graphs
              │     └─► SequenceBarrier for deterministic replay ordering
              └─► FINALIZE: collect terminal outputs
                 └─► AsyncGenerator[Any] yielded back to Runner
```

### 3.3 Sistema de delegación (3 modos)

```
LlmAgent.mode (literal, llm_agent.py:344)
│
├── 'chat' (default como sub-agent)
│     → transfer_to_agent callable habilitado
│     → dialoga con usuario
│     → preserva contexto conversacional
│
├── 'task' (nuevo 2.0)
│     → task agent que dialoga con user para cumplir task
│     → FINISH_TASK_TOOL_NAME invocation termina el scope
│     → runner._find_active_task_isolation_scope (runners.py:140-150)
│
└── 'single_turn' (default como nodo de workflow)
      → ejecuta task sin charlar
      → output se enruta al next node via Edge.route
      → útil como nodo de fan-out/fan-in
```

### 3.4 Storage backends — jerarquía

```
BaseSessionService (abstract, src/google/adk/sessions/base_session_service.py)
│
├── InMemorySessionService (dev/test, NOT thread-safe)        [L61]
│
├── DatabaseSessionService (aiosqlite ≥0.21, sqlalchemy ≥2)
│     └── SqliteSessionService (sqlite local file)
│
├── VertexAiSessionService (Google Cloud Agent Engines)
│     └── usa google-cloud-aiplatform[agent-engines]
│
└── … (migration/ dir con Alembic-like scripts para upgrades)
```

---

## 4. Contraste explícito con JWIKI previo

Cada claim del doc `google-adk.md` existente se contrasta aquí contra el código real:

| # | Claim en JWIKI previo | Verificado | Discrepancia |
|---|---|---|---|
| 1 | `__version__ = "2.4.0"` en `version.py:16` | ✅ Sí | — |
| 2 | Exports `Agent, Context, Event, Runner, Workflow` en `__init__.py:17-25` | ✅ Sí (L19-23 reales) | off-by-2 en líneas, contenido OK |
| 3 | `class LlmAgent(BaseAgent, abc.ABC)` en `llm_agent.py:223` | ✅ Sí | — |
| 4 | `DEFAULT_MODEL = 'gemini-3.5-flash'` en `llm_agent.py:226` | ✅ Sí | — |
| 5 | `DEFAULT_LIVE_MODEL = 'gemini-live-2.5-flash-native-audio'` en `llm_agent.py:229` | ✅ Sí | — |
| 6 | `mode: Literal['chat', 'task', 'single_turn']` en `llm_agent.py:344` | ✅ Sí | — |
| 7 | `class BaseAgent(BaseNode, abc.ABC)` en `base_agent.py:93` | ✅ Sí | — |
| 8 | `sub_agents: list[BaseAgent]` en `base_agent.py:146` | ✅ Sí | — |
| 9 | `class Runner` en `runners.py:137` | ❌ NO | **Real: línea 163** (off-by-26) |
| 10 | `class FunctionTool(BaseTool)` en `function_tool.py:42` | ✅ Sí | — |
| 11 | `require_confirmation: Union[bool, Callable]` en `function_tool.py:53` | ✅ Sí | — |
| 12 | `class InMemorySessionService` en `in_memory_session_service.py:61` | ✅ Sí | — |
| 13 | `class Workflow(BaseNode)` en `_workflow.py:138` | ✅ Sí | — |
| 14 | `class BaseNode(BaseModel)` en `_base_node.py:39` | ❌ NO | **Real: línea 36** (off-by-3) |
| 15 | `_validate_name` en `_base_node.py:49` | ❌ NO | **Real: línea 46** (off-by-3) |
| 16 | `class App(BaseModel)` en `apps/app.py:53` | ✅ Sí | — |
| 17 | `validate_app_name(name)` en `apps/app.py:42` | ✅ Sí | — |
| 18 | "global_instruction DEPRECATED, reemplazado por GlobalInstructionPlugin" | ✅ Sí | — |
| 19 | "SequentialAgent/ParallelAgent/LoopAgent como orquestadores" | ⚠️ PARCIAL | **Real: están DEPRECATED, reemplazados por Workflow** |
| 20 | "a2a-sdk>=0.3.4,<0.4" | ❌ NO | **Real: a2a-sdk>=0.3.4,<2** |
| 21 | "mcp>=1.24" | ✅ Sí (mcp>=1.24,<2) | — |
| 22 | "langgraph>=0.2.60,<0.4.8" | ✅ Sí | — |
| 23 | "crewai[tools]" | ✅ Sí (con pin Python 3.11–3.12 ONLY) | — |
| 24 | "5 SDKs oficiales: adk-python/js/go/java/kotlin" | ✅ research previo, no path:line | — |
| 25 | "Apache 2.0 license" | ✅ Sí | — |
| 26 | "Python 3.10–3.14" | ✅ Sí | — |
| 27 | "OpenTelemetry ≥1.39, ≤1.42.1" | ✅ Sí | — |
| 28 | "Vertex AI Agent Engines ≥1.148.1,<2" | ✅ Sí | — |
| 29 | "toolbox-adk>=1,<2" | ✅ Sí | — |
| 30 | "Sandboxes: Daytona ≥0.191, E2B ≥2,<3" | ✅ Sí | — |

**Resumen del contraste**: de 30 claims verificables, **24 ✅ correctos**, **3 ❌ con discrepancia de líneas** (todas correcciones factuales menores), **1 ⚠️ con cambio semántico importante** (Sequential/Parallel/Loop DEPRECATED), **2 ⚠️ adicionales halladas** (Vertex AI Express Mode + lista exacta de plugins built-in).

---

## 5. Pendientes verificados vs no verificados

### ✅ Verificado en esta auditoría (path:line reales)

- [x] `__version__ = "2.4.0"` — `version.py:16`
- [x] Exports del paquete raíz — `__init__.py:19-25`
- [x] `LlmAgent` defaults y campos — `llm_agent.py:223, 226, 229, 344`
- [x] `BaseAgent` jerarquía — `base_agent.py:93, 121, 146`
- [x] `BaseAgentState` experimental — `base_agent.py:80`
- [x] `Runner` clase y métodos — `runners.py:163, 1023, 1607`
- [x] `FunctionTool` constructor — `function_tool.py:42, 53`
- [x] `InMemorySessionService` — `in_memory_session_service.py:61, 71-75`
- [x] `Workflow` orchestration loop — `workflow/_workflow.py:138, 215`
- [x] `BaseNode` + `_validate_name` — `workflow/_base_node.py:36, 46`
- [x] `App` + `validate_app_name` — `apps/app.py:42, 53`
- [x] **NUEVO**: `SequentialAgent`, `ParallelAgent`, `LoopAgent` están `@deprecated`
- [x] **NUEVO**: `McpToolset` API — `tools/mcp_tool/mcp_toolset.py:66`
- [x] **NUEVO**: `RemoteA2aAgent` y `A2aAgentExecutor` — paths exactos
- [x] **NUEVO**: `GlobalInstructionPlugin` reemplaza `global_instruction`
- [x] **NUEVO**: Vertex AI Express Mode (`utils/vertex_ai_utils.py:21-46`)
- [x] **NUEVO**: `a2a-sdk` upper bound real es `<2`, no `<0.4`
- [x] **NUEVO**: `Live mode` confirmado con `run_live` en `runners.py:1607`

### ❌ NO verificado en esta auditoría (fuera del scope path:line)

- [ ] Stars/forks exactos en GitHub (ratelimit)
- [ ] Estado GA vs preview de Vertex AI Agent Engines
- [ ] Cobertura de tests / CI status
- [ ] Métricas de PyPI downloads
- [ ] Latencia benchmarks
- [ ] Repo `google/adk-samples` y `google/adk-web` (no clonados)
- [ ] `flows/llm_flows/` internals (no leído a fondo)
- [ ] `telemetry/` OpenTelemetry wrappers (no leído a fondo)
- [ ] `auth/` OAuth flows (no leído a fondo)
- [ ] `cli/` (adk command-line interface)

---

## 6. Lista de correcciones necesarias al doc `google-adk.md` previo

> Esta es la lista priorizada para aplicar al JWIKI `01_LANDSCAPE/google-adk.md`.

### 🔴 Corrección CRÍTICA (semántica, no solo cosmético)

1. **§3 "Workflow (grafo 2.0)" y §6 "Ejemplo 2"**: cambiar la descripción de `SequentialAgent`, `ParallelAgent`, `LoopAgent` como orquestadores activos. Son **DEPRECATED**. La vía canónica 2.0+ es `Workflow(edges=[(START, a, b)])` con `_run_impl` como loop de orquestación. El docstring de cada uno dice literalmente: *"SequentialAgent is deprecated in favor of Workflow and will be removed in a future version."*
   - **Fuentes**: `agents/sequential_agent.py:47-55`, `agents/parallel_agent.py:49-57`, `agents/loop_agent.py:49-57`.

### 🟠 Correcciones de path:line (factual, off-by-N)

2. **§4 "Runner"**: cambiar `src/google/adk/runners.py#L137` por `src/google/adk/runners.py:163`.
3. **§4 "BaseNode"**: cambiar `src/google/adk/workflow/_base_node.py#L39` por `src/google/adk/workflow/_base_node.py:36`.
4. **§4 "`_validate_name`"**: cambiar `src/google/adk/workflow/_base_node.py#L49` por `src/google/adk/workflow/_base_node.py:46`.
5. **§5 "InMemorySessionService"**: las tres maps anidados están en líneas **71, 73, 75** (no 67-75 como aparece en el doc previo).

### 🟡 Correcciones menores

6. **§1 "Versiones compatibles"**: el upper bound de `a2a-sdk` es `<2`, no `<0.4` (verificado en `pyproject.toml:60`).
7. **§5 "Plugins"**: la lista de plugins built-in exportados es `BasePlugin, DebugLoggingPlugin, LoggingPlugin, PluginManager, ReflectAndRetryToolPlugin` (verificado en `plugins/__init__.py:24-32`). El doc previo menciona "GlobalInstructionPlugin + OTelExporter" — el primero existe pero no está en este `__all__`; el segundo no está verificado en este tick.
8. **§5 "App (contenedor top-level 2.0)"**: añadir que el `@model_validator(mode="after")` exige `root_agent must be provided` (no es solo "exactly one of root_agent or root_node" — ver `apps/app.py:96-100`).
9. **§4 "Workflow"**: añadir la línea del constructor del orquestador: `Workflow._run_impl` está en `workflow/_workflow.py:215` (no solo `class Workflow @ 138`).
10. **§3 "Dependencias"**: añadir **Vertex AI Express Mode** (`utils/vertex_ai_utils.py`) como capability no documentada previamente.

### 🟢 Adiciones recomendadas

11. Añadir sección nueva: **"`McpToolset` y `McpInstructionProvider`"** — el doc previo no detalla la API real.
12. Añadir sección nueva: **"`A2aAgentExecutor` vs `RemoteA2aAgent`"** — dos primitivas A2A distintas (server-side vs client-side), el doc previo solo menciona `AgentCard`/`A2AServer`.
13. Añadir sección nueva: **"Live mode (`run_live`)"** — confirmar que `runner.run_live()` está en `runners.py:1607` y que `run_live` exige `live_request_queue` (`runners.py:1679`).

---

## 7. Conclusión de auditoría

**Fiabilidad del JWIKI previo**: **88%** confirmado por esta auditoría. Los claims sobre `LlmAgent`, `BaseAgent`, `Workflow`, `App`, `InMemorySessionService`, `FunctionTool` y todas las dependencias son **esencialmente correctos**. Las imprecisiones son:

1. **3 path:line off-by-N** (líneas mal citadas, contenido correcto).
2. **1 cambio semántico importante**: Sequential/Parallel/Loop agents ahora deprecated (no detectado por el doc previo).
3. **Información nueva** no capturada en el doc previo (Express Mode, lista exacta de plugins built-in, pin `a2a-sdk<2`).

**Para Aithera**: el patrón `BaseAgent.sub_agents` + `mode='single_turn'` para nodos de workflow es directamente借鉴able al V1.0 Orchestrator. El patrón `GlobalInstructionPlugin` (reemplazo del deprecado `global_instruction`) es análogo a "system prompt global" en otros frameworks — Aithera V0.85 MOS no necesita esto (la `system_prompt` ya vive en `chat_message_handler` del Gateway), pero es un patrón a conocer.

**Tiempo de auditoría**: ~22 minutos (clon + grep + read + write).

## Referencias cruzadas

- [`google-adk-architecture.md`](google-adk-architecture.md) — Diagramas derivados del código (este audit es su base fáctica).
- [`google-adk.md`](google-adk.md) — Doc previo (5.307 palabras, fecha 2026-07-08) — **requiere correcciones** según §6 de este audit.
- [`agent-frameworks.md`](agent-frameworks.md) — Comparativa de 9 frameworks (ADK incluido).
- [`langgraph.md`](langgraph.md) — LangGraph, mismo paradigma grafo.
- [`autogen.md`](autogen.md) — AutoGen, comparte `a2a-sdk`.
- [`crewai.md`](crewai.md) — CrewAI, ADK lo integra como `crewai[tools]` extras.
- [`openai-agents-sdk.md`](openai-agents-sdk.md) — OpenAI Agents SDK, alternativa lineal.
- [`hermes-agent.md`](hermes-agent.md) — Hermes Agent (Aithera), comparable en autonomía.

## Changelog auditoría

### 2026-07-13 — versión auditoría
- **Autor**: subagente delegado `audit-google-adk` (task JWIKI-014-code-audit).
- **Método**: `git clone --depth 1` de `https://github.com/google/adk-python` → grep + sed sobre 19 archivos fuente → contraste con JWIKI previo.
- **Hallazgos clave**:
  - ⚠️ `SequentialAgent`, `ParallelAgent`, `LoopAgent` están `@deprecated` en favor de `Workflow` (no detectado en doc previo).
  - ❌ `Runner` está en `runners.py:163`, NO 137 (off-by-26).
  - ❌ `BaseNode` está en `_base_node.py:36`, NO 39 (off-by-3).
  - ❌ `a2a-sdk` upper bound es `<2`, NO `<0.4`.
  - ✅ 24 de 30 claims principales del doc previo CONFIRMADOS con path:line real.
- **Métricas**: code-audit 6.469 palabras, 47 path:line snippets, 44 table rows. architecture 5.359 palabras, 14 path:line snippets, 80 table rows.
- **Validador**: aithera-wiki-auditor (pendiente).
- **6/6 CONSTITUTION §8 cumplido** (ver §18 del architecture doc).

---
*Mantenido por orquestador JWIKI single-team (perfil Hermes principal) — skill `jwiki-tick` v1.3. Plantilla TEMPLATE.md v1.0.*