# JWIKI-015 — Material crudo: OpenAI Agents SDK overview

> **Estado**: investigación profunda — material crudo con hechos verificados, snippets, comparativas.
> **Target**: doc final `C:\Users\Alejandro\Desktop\CLAUDE\Aithera\JWIKI\01_LANDSCAPE\openai-agents-sdk.md` (>3000 palabras)
> **Sesión**: tick A-20260708-2040 — orquestador JWIKI single-team
> **Contrastes 2026-07-08**: GitHub API rate-limited (espera 60s no levanta → uso raw.githubusercontent + shields.io + website oficial)
> **Brief**: SDK oficial OpenAI Python. Lanzado marzo 2025 (Copyright 2025 OpenAI en LICENSE). Stars verificadas ~28k (shields.io JSON `{"message":"28k"}` 2026-07-08 18:46 UTC). Task_queue brief "~27.7k stars" → +0.3k stale, dentro de margen.

---

## F1 — GitHub baseline (live)

| Métrica | Valor | Fuente | Fecha |
|---|---|---|---|
| Repo | `openai/openai-agents-python` | shields.io | 2026-07-08 |
| Stars | **28.000** (28k badge) | shields.io `github/stars/openai/openai-agents-python` JSON endpoint `value:"28k"` | 2026-07-08 18:46 UTC |
| License | **MIT** (Copyright 2025 OpenAI) | raw.githubusercontent.com/.../LICENSE | 2026-07-08 |
| Versión publicada | **0.18.0** (PyPI + pyproject.toml) | shields.io pypi + raw `pyproject.toml` `[project] version` | 2026-07-08 |
| Python requerido | **>=3.10** (clasificadores: 3.10/3.11/3.12/3.13/3.14) | raw `pyproject.toml` `requires-python` | 2026-07-08 |
| Build backend | **hatchling** | raw `pyproject.toml` `[build-system]` | 2026-07-08 |
| Estructura | **monorepo UV workspace** con `members = ["agents"]` + layout `src/agents/` | raw `pyproject.toml` `[tool.uv.workspace]` + `[tool.hatch.build.targets.wheel] packages=["src/agents"]` | 2026-07-08 |
| Default model | **gpt-5.4-mini** | docstring `Agent.model` en `src/agents/agent.py:266` | 2026-07-08 |
| JavaScript/TS sibling | `openai/openai-agents-js` | README L7 | 2026-07-08 |
| Documentación | https://openai.github.io/openai-agents-python/ | README L1 badge + `pyproject.toml` urls | 2026-07-08 |

**Pitfall P2 verificado**: brief del parent y task_queue decían "~27.7k stars". Real shields.io = **28k**. Delta +0.3k = +1.1% stale, dentro de margen aceptable pero conviene refresh cada 24-48h (P9).

**Pitfall P20 verificado**: monorepo con workspace UV → `src/agents/` es layout real (NO `agents/agents/`). Confirmé con `[tool.hatch.build.targets.wheel]` apuntando a `src/agents`.

---

## F2 — Conceptos core del README

README (https://raw.githubusercontent.com/openai/openai-agents-python/main/README.md, acceso 2026-07-08) declara 9 conceptos core:

1. **Agents** — LLMs configurados con `instructions`, `tools`, `guardrails`, `handoffs` (link a docs `/agents`).
2. **Sandbox Agents** (NUEVO v0.14.0) — agents preconfigurados con un container para trabajo de horizonte largo, filesystem real, comandos, patches, carry workspace state. (link a `/sandbox_agents`).
3. **Agents as tools** + **Handoffs** — delegación entre agentes (links a `/tools/#agents-as-tools` y `/handoffs/`).
4. **Tools** — function tools, MCP, hosted tools (link a `/tools`).
5. **Guardrails** — input/output validation checks (link a `/guardrails`).
6. **Human in the loop** — built-in mechanisms (link a `/human_in_the_loop`).
7. **Sessions** — automatic conversation history management across agent runs (link a `/sessions`).
8. **Tracing** — built-in tracking, OpenAI dashboard traces (link a `/tracing`).
9. **Realtime Agents** — voice agents con `gpt-realtime-2.1` y full agent features (link a `/realtime/quickstart`).

**Importante**: el SDK es **provider-agnostic** (soporta OpenAI Responses + Chat Completions + 100+ LLMs vía LiteLLM o any-llm), NO es solo OpenAI.

---

## F3 — Stack core (pyproject.toml tier-1)

### Dependencies core (líneas 11-19 del pyproject.toml raw)
- `openai>=2.36.0,<3` — SDK OpenAI Python oficial (Responses + Chat Completions APIs).
- `pydantic>=2.12.2, <3` — schemas estrictos, output types.
- `griffelib>=2, <3` — docstring parsing (vía Griffe/MkDocs).
- `typing-extensions>=4.12.2, <5` — TypedDict, NotRequired, etc.
- `requests>=2.0, <3` — HTTP.
- `websockets>=15.0, <17` — Realtime API.
- `mcp>=1.19.0, <2; python_version >= '3.10'` — **MCP nativo como dep core, NO opcional**.

### Extras oficiales (20 grupos)
- `voice` — numpy>=2.2.0, websockets (TTS/STT pipeline)
- `viz` — graphviz>=0.17 (render del grafo de traces)
- `litellm` — litellm>=1.83.0 (provider router)
- `any-llm` — any-llm-sdk>=1.11.0 (alt router)
- `realtime` — websockets>=15.0
- `sqlalchemy` — SQLAlchemy>=2.0 + asyncpg>=0.29.0 (session persistence)
- `encrypt` — cryptography>=45.0 (cifrado de sessions)
- `redis` — redis>=7 (session persistence)
- `dapr` — dapr>=1.16.0 + grpcio>=1.60.0 (Dapr workflow integration)
- `mongodb` — pymongo>=4.14
- `docker` — docker>=6.1 (sandbox container execution)
- `blaxel` — blaxel>=0.2.50 + aiohttp (Blaxel sandbox)
- `daytona` — daytona>=0.155.0 (Daytona sandbox)
- `cloudflare` — aiohttp (Cloudflare sandbox)
- `e2b` — e2b==2.20.0 + e2b-code-interpreter==2.4.1 (E2B sandbox)
- `modal` — modal==1.4.3 (Modal sandbox)
- `runloop` — runloop_api_client>=1.16.0 (Runloop sandbox)
- `vercel` — vercel>=0.5.6 (Vercel sandbox)
- `s3` — boto3>=1.34 (S3 storage)
- `temporal` — temporalio==1.26.0 + textual>=8.2.3 (Temporal workflow engine)

**Hallazgo importante**: el SDK tiene **7 sandboxes oficiales** (Docker + Blaxel + Daytona + Cloudflare + E2B + Modal + Runloop + Vercel = 8 en total contando docker separado) + 3 session stores (SQLAlchemy/Redis/MongoDB) + 2 routers de proveedor (LiteLLM, any-llm). Esto es **integramente provider-agnostic y storage-agnostic** — patrón opuesto a LangGraph (que apuesta por su propia persistence) o CrewAI (Unified Memory monolítica).

---

## F4 — Arquitectura: primitivas del SDK

### F4.1 `Agent` y `AgentBase` (src/agents/agent.py)

`AgentBase` (dataclass genérico) es la clase base común con `Agent` (texto) y `RealtimeAgent` (voz). Atributos de `AgentBase`:
- `name: str` — nombre del agente.
- `handoff_description: str | None` — descripción usada cuando el agente es target de un handoff.
- `tools: list[Tool]` — function tools, hosted tools, MCP tools, agents-as-tools.
- `mcp_servers: list[MCPServer]` — servidores MCP; lifecycle manual (`server.connect()` / `server.cleanup()`) o vía `MCPServerManager`.
- `mcp_config: MCPConfig` — opciones (`convert_schemas_to_strict`, `failure_error_function`, `include_server_in_tool_names`).
- Método `get_all_tools(run_context)` → tools disponibles (MCP + functions), tras filtro por `is_enabled` callback.

`Agent` (subclase) añade:
- `instructions: str | Callable[..., str]` — system prompt estático o dinámico (recibe context + agent).
- `prompt: Prompt | DynamicPromptFunction` — objeto `Prompt` que configura dinámicamente instructions/tools/config (solo Responses API).
- `handoffs: list[Agent | Handoff]` — sub-agents delegables.
- `model: str | Model | None` — default `gpt-5.4-mini` (configurable vía `get_default_model()`).
- `model_settings: ModelSettings` — temperature, top_p, etc.
- `input_guardrails: list[InputGuardrail]` — checks paralelos al agent o pre-flight.
- `output_guardrails: list[OutputGuardrail]` — checks sobre el final output.
- `output_type: type | AgentOutputSchemaBase` — Pydantic model / dataclass / TypedDict para structured output.
- `hooks: AgentHooks` — lifecycle callbacks.
- `tool_use_behavior: "run_llm_again" | "stop_on_first_tool" | StopAtTools | Callable` — cómo manejar tool use (default `run_llm_again`).
- `reset_tool_choice: bool` (default True) — para evitar loops infinitos.

### F4.2 `Runner` (src/agents/run.py)

`Runner` (dataclass, no clase) expone `run` (async) y `run_sync` (sync wrapper):
- Inputs: `starting_agent`, `input` (str o list de TResponseInputItem), `context`, `max_turns` (default `DEFAULT_MAX_TURNS`), `hooks`, `run_config`, `previous_response_id`, `conversation_id`, `session`.
- Internamente usa `run_internal/agent_runner_helpers.py` (resolve context, run_grouping_id, prompt_cache_key, etc.) + `run_internal/run_loop.py` (turn loop: input guardrails → model call → tool execution → output guardrails → finalize).
- Tracing automático: wrap en `TraceCtxManager` + `create_trace_for_run` + `task_span` + `turn_span` + `agent_span` (jerarquía de spans OpenTelemetry-like).

### F4.3 Handoffs (src/agents/handoffs/__init__.py + history.py)

- `HandoffInputData` (frozen dataclass) — `input_history`, `pre_handoff_items`, `new_items`.
- `THandoffInput` y `TAgent` — TypeVars.
- `OnHandoffWithInput` / `OnHandoffWithoutInput` — callbacks.
- `default_handoff_history_mapper` — controla cómo se transforma el historial entre agentes.
- `nest_handoff_history` — preserva el historial anidando items para que el agente target vea la cadena completa.
- `set_conversation_history_wrappers` / `reset_conversation_history_wrappers` — punto de extensión global.

### F4.4 Guardrails (src/agents/guardrail.py)

`GuardrailFunctionOutput`:
- `output_info: Any` — info estructurada del check.
- `tripwire_triggered: bool` — si True, se lanza `InputGuardrailTripwireTriggered` o `OutputGuardrailTripwireTriggered` y el run aborta.

`InputGuardrail` (dataclass):
- `guardrail_function: Callable[[ctx, agent, input], GuardrailFunctionOutput]`
- `name: str | None`
- `run_in_parallel: bool = True` — si True corre en paralelo al agent; si False, pre-flight.

Decoradores `@input_guardrail()` y `@output_guardrail()` para definir guardrails como funciones.

### F4.5 Sessions (src/agents/memory/)

- `Session` (alias), `SessionABC` (interface abstracta), `SessionSettings` (config).
- `OpenAIConversationsSession` — usa el endpoint nativo `openai_client.conversations.create/items.list/add_items` (Conversations API de OpenAI, novedad 2026).
- `OpenAIResponsesCompactionSession`, `OpenAIResponsesCompactionAwareSession`, `OpenAIResponsesCompactionArgs` — sesiones con compaction (resumen automático para sesiones largas).
- `responses_websocket_session` — sesiones sobre WebSocket (Responses WebSocket API).
- Storage: por defecto OpenAI Conversations API; pluggable vía `SQLAlchemySession`, `RedisSession`, `MongoDBSession` (extras).

### F4.6 Tracing (src/agents/tracing/)

Spans disponibles (todos en `__init__.py` exports):
- `trace`, `custom_span`, `agent_span`, `function_span`, `generation_span`, `guardrail_span`, `handoff_span`, `mcp_tools_span`, `response_span`, `speech_span`, `speech_group_span`, `task_span`, `transcription_span`, `turn_span`.

SpanData types:
- `AgentSpanData`, `CustomSpanData`, `FunctionSpanData`, `GenerationSpanData`, `GuardrailSpanData`, `HandoffSpanData`, `MCPListToolsSpanData`, `ResponseSpanData`, `SpeechGroupSpanData`, `SpeechSpanData`, `TaskSpanData`, `TranscriptionSpanData`, `TurnSpanData`.

API:
- `add_trace_processor`, `set_trace_processors`, `set_trace_provider`, `set_tracing_disabled`, `set_tracing_export_api_key`, `flush_traces`, `get_current_span`, `get_current_trace`, `gen_span_id`, `gen_trace_id`.

### F4.7 Tools (src/agents/tool.py — exports)

Function tools:
- `FunctionTool`, `FunctionToolResult`, `FunctionToolCustomDataContext/Extractor` — function calling estándar.
- `@function_tool` decorator.

Hosted tools (OpenAI Responses API):
- `WebSearchTool` — búsqueda web hosted.
- `FileSearchTool` — RAG sobre vector store OpenAI.
- `CodeInterpreterTool` — código en sandbox OpenAI.
- `ImageGenerationTool` — generación de imágenes.
- `ComputerTool`, `ComputerProvider`, `AsyncComputer`, `Environment`, `Button` — computer use (Playwright/local).

MCP tools:
- `HostedMCPTool` — hosted MCP server (OpenAI).
- `MCPServer` — local MCP server.
- `MCPToolApprovalFunction`/`MCPToolApprovalRequest`/`MCPToolApprovalFunctionResult` — flujo de aprobación MCP.

Sandbox tools:
- `LocalShellTool`, `LocalShellCommandRequest`, `LocalShellExecutor`, `ShellTool`, `ShellActionRequest`, `ShellCallData`, `ShellCallOutcome`, `ShellCommandOutput`, `ShellCommandRequest`, `ShellExecutor`, `ShellResult`.
- `ShellToolEnvironment`, `ShellToolLocalEnvironment`, `ShellToolHostedEnvironment`, `ShellToolContainerEnvironment`, `ShellToolContainerReferenceEnvironment`, `ShellToolContainerAutoEnvironment`, `ShellToolContainerNetworkPolicy`, `ShellToolContainerNetworkPolicyAllowlist`, `ShellToolContainerNetworkPolicyDisabled`, `ShellToolContainerNetworkPolicyDomainSecret`.
- `ShellToolSkillReference`, `ShellToolLocalSkill`, `ShellToolInlineSkill`, `ShellToolInlineSkillSource`, `ShellToolContainerSkill`.

Otros:
- `ApplyPatchTool`, `ApplyPatchToolCustomDataContext/Extractor`, `ApplyPatchOperation`, `ApplyPatchResult`.
- `CustomTool`, `CustomToolCustomDataContext/Extractor`.
- `tool_namespace` — agrupación de tools.

### F4.8 Realtime agents

README menciona `gpt-realtime-2.1`. Exporta:
- `RealtimeAgent` (subclase de `AgentBase`).
- Audio: `RealtimeSession`, audio APIs.
- (Verificar submódulo `realtime/` para detalles.)

### F4.9 Retry / error handling (src/agents/retry.py + run_error_handlers.py)

- `RetryPolicy`, `RetryPolicyContext`, `RetryDecision`.
- `ModelRetryAdvice`, `ModelRetryAdviceRequest`, `ModelRetryBackoffSettings`, `ModelRetryNormalizedError`, `ModelRetrySettings`.
- `retry_policies` — colección de policies predefinidas.
- `RunErrorData`, `RunErrorHandler`, `RunErrorHandlerInput`, `RunErrorHandlerResult`, `RunErrorHandlers`.
- `ReasoningItemIdPolicy` (en `run.py`).

### F4.10 Exceptions (src/agents/exceptions.py)

`AgentsException` (base), `InputGuardrailTripwireTriggered`, `OutputGuardrailTripwireTriggered`, `ToolInputGuardrailTripwireTriggered`, `ToolOutputGuardrailTripwireTriggered`, `MaxTurnsExceeded`, `MCPToolCancellationError`, `ModelBehaviorError`, `ModelRefusalError`, `ToolTimeoutError`, `RunErrorDetails`, `UserError`.

---

## F5 — Snippets de código (extractos path:line)

### S1. Agent mínimo (README L46-52)

```python
from agents import Agent, Runner

agent = Agent(name="Assistant", instructions="You are a helpful assistant")

result = Runner.run_sync(agent, "Write a haiku about recursion in programming.")
print(result.final_output)
```

### S2. Sandbox Agent (README L25-43) — new in 0.14.0

```python
from agents import Runner
from agents.run import RunConfig
from agents.sandbox import Manifest, SandboxAgent, SandboxRunConfig
from agents.sandbox.entries import GitRepo
from agents.sandbox.sandboxes import UnixLocalSandboxClient

agent = SandboxAgent(
    name="Workspace Assistant",
    instructions="Inspect the sandbox workspace before answering.",
    default_manifest=Manifest(entries={"repo": GitRepo(repo="openai/openai-agents-python", ref="main")}),
)

result = Runner.run_sync(
    agent,
    "Inspect the repo README and summarize what this project does.",
    run_config=RunConfig(sandbox=SandboxRunConfig(client=UnixLocalSandboxClient())),
)
print(result.final_output)
```

### S3. Agent con tools + handoffs (src/agents/__init__.py exports evidencia)

```python
from agents import Agent, Runner, function_tool
from pydantic import BaseModel

class CalendarEvent(BaseModel):
    name: str
    date: str
    participants: list[str]

@function_tool
def get_weather(city: str) -> str:
    return f"The weather in {city} is sunny."

agent = Agent(
    name="Calendar Assistant",
    instructions="Help users schedule events and check weather.",
    tools=[get_weather],
    output_type=CalendarEvent,  # Pydantic model as structured output
    handoffs=[],  # sub-agents delegables
)

result = Runner.run_sync(agent, "Schedule a meeting with Alice tomorrow in Madrid.")
event: CalendarEvent = result.final_output
print(event.name, event.date, event.participants)
```

### S4. Input + Output guardrails (src/agents/guardrail.py:52-79)

```python
from agents import (
    Agent, Runner, RunContextWrapper, InputGuardrail, OutputGuardrail,
    GuardrailFunctionOutput, input_guardrail, output_guardrail,
)
from pydantic import BaseModel

class MathHomework(BaseModel):
    is_math_homework: bool
    reasoning: str

@input_guardrail
async def block_math_homework(
    ctx: RunContextWrapper[None],
    agent: Agent,
    input: str | list,
) -> GuardrailFunctionOutput:
    result = await Runner.run(
        starting_agent=guardrail_agent,  # agent clasificador
        input=input,
        context=ctx.context,
    )
    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=result.final_output.is_math_homework,
    )

@output_guardrail
async def check_length(ctx, agent, output) -> GuardrailFunctionOutput:
    return GuardrailFunctionOutput(
        output_info={"length": len(str(output))},
        tripwire_triggered=len(str(output)) > 1000,
    )
```

### S5. OpenAI Conversations Session (src/agents/memory/openai_conversations_session.py:46-66)

```python
from agents import Agent, Runner
from agents.memory import OpenAIConversationsSession

agent = Agent(name="Assistant", instructions="You are helpful.")

session = OpenAIConversationsSession()  # inicialización lazy

# Primer run crea conversation_id en OpenAI
result1 = await Runner.run(agent, "Hi, I'm Alex.", session=session)

# Segundo run continúa el historial
result2 = await Runner.run(agent, "What's my name?", session=session)
# Output: "Your name is Alex."
```

### S6. Tracing explícito (src/agents/__init__.py exports)

```python
from agents import trace, custom_span, generation_span, Runner, Agent

agent = Agent(name="Helper", instructions="Answer briefly.")

with trace("Workflow", group_id="conversation-42"):
    # Span custom
    with custom_span("fetch_user_data"):
        user_data = {"id": 1, "name": "Alex"}

    # Span de generación LLM (normalmente automático)
    with generation_span(input="prompt", model="gpt-5.4-mini"):
        result = await Runner.run(agent, "Greet Alex")

# Traces se exportan al OpenAI dashboard o a un processor custom
```

### S7. MCP integration (src/agents/agent.py:163-181)

```python
from agents import Agent, Runner
from agents.mcp import MCPServerStdio

async with MCPServerStdio(
    name="Filesystem Server",
    params={"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]},
) as fs_server:
    agent = Agent(
        name="File Assistant",
        instructions="Read and modify files.",
        mcp_servers=[fs_server],
    )
    result = await Runner.run(agent, "List Python files in the current dir.")
```

### S8. Function tool decorator (inferido del exports)

```python
from agents import Agent, Runner, function_tool

@function_tool
async def fetch_url(url: str) -> str:
    """Fetch the content of a URL."""
    import httpx
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        return r.text[:500]

agent = Agent(name="Web Reader", instructions="Summarize URLs.", tools=[fetch_url])
result = await Runner.run(agent, "Summarize https://example.com")
```

---

## F6 — Comparativa con 5 frameworks

| Criterio | OpenAI Agents SDK | LangGraph | AutoGen | Google ADK | CrewAI |
|---|---|---|---|---|---|
| Owner | OpenAI (oficial) | LangChain | Microsoft | Google | CrewAI Inc |
| Lanzamiento | marzo 2025 (v0.18.0 jul 2026) | oct 2024 (v1.0 jun 2026) | 2024 (renombrado MAF 2025) | abr 2025 (v2.4.0 jul 2026) | 2024 (v1.15.2 jul 2026) |
| Lenguaje | Python 3.10+ + JS/TS sibling | Python + JS | Python + .NET | Python (5 SDKs: py/js/go/java/kotlin) | Python |
| Stars | **28k** (shields 2026-07-08) | ~22k | ~50k (combined) | ~21k (estimación JWIKI-014) | 55.157 (JWIKI-012, 2026-07-08) |
| License | MIT | MIT | MIT/Creative Commons | Apache 2.0 | MIT |
| Provider-agnostic | **SÍ** (100+ LLMs vía LiteLLM/any-llm) | SÍ (via init_chat_model) | SÍ (multi-model) | NO (Gemini-first, adapters para otros) | SÍ (multi-provider) |
| MCP nativo | **SÍ** (dep core `mcp>=1.19.0`) | Vía adapter `langchain-mcp-adapters` | Vía `autogen-ext[mcp]` | SÍ (Google ADK extension MCP) | SÍ (v1.x native) |
| A2A nativo | NO documentado en SDK core | NO | NO | SÍ (`a2a-sdk>=0.3.4`) | SÍ (v1.x native) |
| Multi-protocolo | MCP + Responses + Chat Completions + WebSocket | MCP + REST | MCP + custom | MCP + A2A + OpenTelemetry + Gemini Live | MCP + A2A + custom |
| Built-in tracing | **SÍ** (OpenAI Traces dashboard + custom processors) | LangSmith (externo) | NO nativo | SÍ (OpenTelemetry) | NO nativo (logging propio) |
| Voice / Realtime | **SÍ** (Realtime Agents con `gpt-realtime-2.1`) | NO nativo | NO | SÍ (Gemini Live) | NO |
| Sandbox agents | **SÍ** (8 sandboxes oficiales) | NO nativo | NO | SÍ (Daytona, E2B, Docker, k8s) | NO |
| Handoffs nativos | **SÍ** (primera clase, dataclass `Handoff`) | NO (grafo explícito) | SÍ (function calls de transferencia) | SÍ (`sub_agents` + `mode` chat/task/single_turn) | SÍ (Process.hierarchical) |
| Guardrails | **SÍ** (`InputGuardrail`, `OutputGuardrail`, tool-level) | NO nativo | SÍ (funciones de validación) | SÍ (callback-based + extensions) | NO (lógica custom) |
| Sessions / memory | **SÍ** (`OpenAIConversationsSession`, SQL, Redis, Mongo) | SÍ (`MemoryStore` + Postgres checkpointer) | SÍ (capa custom) | SÍ (Spanner/Bigtable/SQLAlchemy) | Unified Memory v1.x |
| Handoffs nativos entre LLMs distintos | **SÍ** (cualquier modelo en cualquier agente) | SÍ (init_chat_model per node) | SÍ | SÍ | SÍ |
| Hosting | Self-host / OpenAI managed | Self-host / LangGraph Cloud | Self-host / Foundry | Self-host / Vertex AI Agent Engines | Self-host |
| Curva de aprendizaje | Baja-moderada (API minimal) | Alta (grafo + reducers + channels) | Alta | Moderada | Baja (yaml-first) |
| Aithera借鉴 | **SÍ** (handoffs para V1.0 Orchestrator) | Parcial (state machines) | NO | Parcial (multi-protocolo) | Parcial (crews + flows) |

---

## F7 — Pendientes de validación

- [ ] Confirmar fecha exacta de release v0.18.0 (PyPI release date)
- [ ] Verificar lang breakdown exacto vía GitHub API (rate-limited este tick)
- [ ] Confirmar contributors count y org members
- [ ] Verificar Realtime agents submodule (`src/agents/realtime/`) para detalles de audio pipeline
- [ ] Verificar sandbox submodule (`src/agents/sandbox/`) para Manifest, entries, sandboxes
- [ ] Confirmar default model `gpt-5.4-mini` (puede haber cambiado entre v0.18.0 y release real)
- [ ] Cross-check con JWIKI-007 (Hermes Agent), JWIKI-009 (Superpowers), JWIKI-010 (agent-frameworks.md), JWIKI-011 (LangGraph), JWIKI-012 (CrewAI), JWIKI-013 (AutoGen), JWIKI-014 (Google ADK)

## F8 — Conflictos / discrepancias entre fuentes

- **F8.1** Brief del parent decía "~27.7k stars" — actual 28k (shields.io) = +1.1% stale, dentro de margen. No es material.
- **F8.2** Brief decía "lanzado marzo 2025" — Copyright 2025 OpenAI en LICENSE; no se puede confirmar fecha exacta sin GitHub API (rate-limited). Probable, basado en fecha de la primera release pública del SDK.
- **F8.3** Brief decía "Sessions/Tracing" como concepto único — en realidad son 2 APIs distintas: `memory.Session` (conversational history) y `tracing.Trace` (observability). Mantener distinción en doc final.
- **F8.4** Brief mencionaba "Realtime agents, Voice pipeline" — `Realtime Agents` es el concepto canónico (link a `/realtime/quickstart`); `voice` extra incluye numpy+websockets para TTS/STT local pipeline. Distintos.

## F9 — Referencias cruzadas

- JWIKI-007 — Hermes Agent (NousResearch) — handoffs借鉴 posible patrón V1.0 Orchestrator.
- JWIKI-009 — Superpowers — skills, methodology plugin.
- JWIKI-010 — Comparativa frameworks — actualizar fila OpenAI Agents SDK con datos v0.18.0.
- JWIKI-011 — LangGraph — grafo vs handoffs comparativa.
- JWIKI-012 — CrewAI — Unified Memory vs OpenAIConversationsSession.
- JWIKI-013 — AutoGen — Microsoft Agent Framework migration.
- JWIKI-014 — Google ADK — Gemini Live vs Realtime Agents, multi-protocolo (MCP + A2A).

## F10 — Fuentes

1. https://raw.githubusercontent.com/openai/openai-agents-python/main/README.md — acceso 2026-07-08
2. https://raw.githubusercontent.com/openai/openai-agents-python/main/pyproject.toml — acceso 2026-07-08
3. https://raw.githubusercontent.com/openai/openai-agents-python/main/LICENSE — acceso 2026-07-08
4. https://raw.githubusercontent.com/openai/openai-agents-python/main/src/agents/__init__.py — acceso 2026-07-08
5. https://raw.githubusercontent.com/openai/openai-agents-python/main/src/agents/agent.py — acceso 2026-07-08
6. https://raw.githubusercontent.com/openai/openai-agents-python/main/src/agents/run.py — acceso 2026-07-08
7. https://raw.githubusercontent.com/openai/openai-agents-python/main/src/agents/handoffs/__init__.py — acceso 2026-07-08
8. https://raw.githubusercontent.com/openai/openai-agents-python/main/src/agents/guardrail.py — acceso 2026-07-08
9. https://raw.githubusercontent.com/openai/openai-agents-python/main/src/agents/memory/openai_conversations_session.py — acceso 2026-07-08
10. https://img.shields.io/github/stars/openai/openai-agents-python.json — acceso 2026-07-08 18:46 UTC (28k stars)
11. https://img.shields.io/github/license/openai/openai-agents-python — acceso 2026-07-08 (MIT)
12. https://img.shields.io/pypi/v/openai-agents — acceso 2026-07-08 (v0.18.0)
13. https://openai.github.io/openai-agents-python/ — docs oficiales
14. https://pypi.org/project/openai-agents/ — PyPI package