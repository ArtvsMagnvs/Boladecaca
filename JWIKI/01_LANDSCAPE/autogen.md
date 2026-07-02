# AutoGen (microsoft/autogen) — Overview del framework multi-agente de Microsoft

## Resumen
AutoGen es el framework open-source de Microsoft para construir aplicaciones multi-agente conversacionales. Nació en noviembre de 2023 (v0.2) como uno de los primeros frameworks prominentes de multi-agent y desde enero de 2025 (v0.4) opera sobre un **actor model** con message passing asíncrono, que reemplazó el antiguo patrón de `register_reply`. La versión actual estable al cierre de este documento (julio 2026) es `autogen-agentchat 0.7.5` (publicada 2025-09-30); el repositorio principal (`github.com/microsoft/autogen`, MIT código + CC-BY-4.0 docs) acumula 59,425 stars, 1.23 M descargas PyPI/mes, y desde 2026 está oficialmente en **maintenance mode** con Microsoft Agent Framework (MAF) como sucesor recomendado.

## Objetivo
Documentar el estado real del framework AutoGen en julio 2026: arquitectura actor-model, los cinco patrones de `Team` (RoundRobinGroupChat, SelectorGroupChat, Swarm, MagenticOneGroupChat, GraphFlow), el sucesor MAF, y una comparativa técnica honesta con LangGraph, CrewAI, OpenAI Agents SDK y Google ADK. Responde a la pregunta "¿debería Aithera construir su core agéntico sobre AutoGen o sobre alternativas más activas?".

## Estado
🟡 En progreso — material crudo validado (159 hechos, 8 snippets, tabla 5-frameworks), pendiente verificación por aithera-backend (12 items) y auditoría de 6 criterios. La sección Pendientes documenta exactamente qué falta verificar.

## Versiones compatibles
| Proyecto | Versión | Notas |
|---|---|---|
| AutoGen (autogen-agentchat) | 0.7.5 (2025-09-30) | Última release tagged en `main`; 9 meses sin nuevos tags en `python-v*` a 2026-07-02 |
| AutoGen (autogen-core) | 0.7.5 | Runtime gRPC actor model; release sincronizada con agentchat |
| AutoGen Studio | variable | Web UI experimental; sin tags `python-v*-autogenstudio-*` frecuentes (ver Pendiente #1) |
| Python | 3.10 - 3.13 | Classifier del repo; cp314 excluido por incompatibilidad numpy 2.2 (no afecta a AutoGen) |
| .NET (Microsoft.AutoGen.*) | 4 NuGet packages | Microsoft.AutoGen.Contracts / Core / Core.Grpc / RuntimeGateway.Grpc (ver Pendiente #3 sobre sync con Python) |
| Microsoft Agent Framework (MAF) | sucesor | Mismo grupo Microsoft; absorberá features de AutoGen en roadmap |
| Aithera | V0.7+ | No usar AutoGen directamente en core; estudiar patrones Team como referencia arquitectónica |

## Proyectos compatibles
AutoGen es compatible con:

- **Model providers** (vía interfaz `ChatCompletionClient`): OpenAI, Azure OpenAI, Anthropic, Google Gemini, AWS Bedrock, Ollama (local), y otros vía adaptadores `autogen-ext`.
- **Protocolos interop**: MCP first-class (`McpWorkbench`, `StdioServerParams`, soporte Elicitation/Sampling/Roots en 0.7.5). A2A limitado (delegado a MAF).
- **Code executors**: `LocalCommandLineCodeExecutor`, `DockerCommandLineCodeExecutor` (default en Magentic-One), `JupyterCodeExecutor`.
- **Observability**: OpenTelemetry GenAI traces built-in (`create_agent`, `invoke_agent`, `execute_tool`); Langfuse, Arize Phoenix, MLflow vía instrumentación externa.
- **Magentic-One**: orquestador multi-agente generalista con agentes especializados (Coder, ComputerTerminal, FileSurfer, WebSurfer) — referencia de agente generalista open source (38% GAIA, 32.8% WebArena, 27.7% AssistantBench).
- **Distributed runtime**: `GrpcWorkerAgentRuntime` para actor model cross-process; cross-language runtime Python ↔ .NET vía gRPC.

## Dependencias
Documentos JWIKI requeridos para contexto completo:

- [01_LANDSCAPE/history.md](./history.md) — cronología del ecosistema; AutoGen aparece en Era 4 (2023-nov) como primer framework prominente multi-agent.
- [01_LANDSCAPE/projects.md](./projects.md) — comparativa OSS 2026; tabla incluye AutoGen y permite ver la distancia con OpenClaw/OpenHuman/Hermes/Superpowers.
- [01_LANDSCAPE/agent-frameworks.md](./agent-frameworks.md) — comparativa LangGraph/CrewAI/AutoGen/OpenAI Agents SDK/Google ADK.
- [01_LANDSCAPE/openjarvis.md](./openjarvis.md) — actor model académico (Stanford) y comparativa 5 primitivas vs AutoGen.
- [01_LANDSCAPE/openclaw.md](./openclaw.md) — TypeScript multi-canal; contraste con actor model Python.
- [01_LANDSCAPE/langgraph.md](./langgraph.md) — JWIKI-011; state machine vs actor model.
- [01_LANDSCAPE/clawdbot.md](./clawdbot.md) — JWIKI-008; lineage de renames.
- [06_AGENTS/](../06_AGENTS/README.md) — patrones de agentes (ReAct, Plan-Execute, Reflexion, etc.).
- [07_MEMORY/](../07_MEMORY/README.md) — memory systems; AutoGen usa `save_state/load_state` estilo custom (no ChromaDB out-of-the-box).
- [11_SECURITY/](../11_SECURITY/README.md) — sandboxing y prompt injection defenses.

Dependencias externas (no JWIKI):
- `api.github.com/repos/microsoft/autogen` (datos de repo: stars, contributors, releases)
- `microsoft.github.io/autogen/stable/` (docs v0.4+; legacy 0.2 en `microsoft.github.io/autogen/0.2/`)
- ArXiv 2308.08155 (paper original AutoGen, 2023)
- ArXiv 2411.04468 (Magentic-One paper, 2024-11)

## Arquitectura

AutoGen v0.4+ se estructura como **capas de runtime sobre un actor model gRPC-based**:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      APLICACIÓN DEL USUARIO                            │
│   (scripts Python, FastAPI service, Jupyter notebook, Aithera core)   │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   CAPA DE ALTO NIVEL (autogen-agentchat)               │
│                                                                        │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────────┐   │
│  │ AssistantAgent   │  │ UserProxyAgent   │  │ CodeExecutorAgent   │   │
│  │ (LLM-backed)     │  │ (human-in-loop)  │  │ (sandboxed code)    │   │
│  └──────────────────┘  └──────────────────┘  └─────────────────────┘   │
│                                                                        │
│  Teams (patrones de orquestación multi-agente):                        │
│  ┌─────────────────────┐ ┌────────────────────┐ ┌─────────────────┐  │
│  │ RoundRobinGroupChat │ │ SelectorGroupChat  │ │ Swarm           │  │
│  │ (turno fijo)        │ │ (selector LLM)     │ │ (handoff msgs)  │  │
│  └─────────────────────┘ └────────────────────┘ └─────────────────┘  │
│  ┌─────────────────────────┐ ┌────────────────────────────────────┐   │
│  │ MagenticOneGroupChat    │ │ GraphFlow                          │   │
│  │ (orquestador SOTA)      │ │ (grafos de flujo)                  │   │
│  └─────────────────────────┘ └────────────────────────────────────┘   │
│                                                                        │
│  Termination: TextMentionTermination | MaxMessageTermination |         │
│               HandoffTermination | TokenUsageTermination |             │
│               FunctionCallTermination | SourceMatchTermination         │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      RUNTIME NUCLEAR (autogen-core)                    │
│                                                                        │
│  ┌──────────────┐    ┌───────────────┐    ┌──────────────────────┐   │
│  │  Actor       │    │  Message      │    │  Topic / Subscription │   │
│  │  (BaseAgent  │───▶│  Passing      │───▶│  (pub/sub typed)     │   │
│  │  subclass)   │    │  (pub/sub)    │    │                      │   │
│  └──────────────┘    └───────────────┘    └──────────────────────┘   │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  SingleProcessAgentRuntime  │  GrpcWorkerAgentRuntime         │    │
│  │  (in-process)               │  (distribuido vía gRPC)          │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  CancellationToken  │  AgentId  │  AgentMetadata  │  Type subs │    │
│  │  (async control)    │  (routing)│  (descr tipo)   │  (genéricos)│   │
│  └──────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         EXTENSIONES (autogen-ext)                      │
│                                                                        │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────┐ ┌──────────────┐    │
│  │  OpenAI      │ │  Anthropic   │ │  Ollama    │ │  Azure       │    │
│  │  ChatClient  │ │  ChatClient  │ │  (local)   │ │  OpenAI      │    │
│  └──────────────┘ └──────────────┘ └────────────┘ └──────────────┘    │
│                                                                        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────────┐   │
│  │  McpWorkbench│ │  MagenticOne │ │  OpenInference /             │   │
│  │  (MCP client)│ │  (Coder,     │ │  OpenTelemetry instrument.  │   │
│  │              │ │   WebSurfer, │ │                              │   │
│  │              │ │   FileSurfer)│ │                              │   │
│  └──────────────┘ └──────────────┘ └──────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

**Punto clave de diseño**: el runtime nuclear (`autogen-core`) es independiente del LLM. Los `ChatCompletionClient` se inyectan a los agentes; cambiar de OpenAI a Ollama a Anthropic no requiere tocar lógica de orquestación ni mensajes. Esto es lo que diferencia a AutoGen de frameworks "OpenAI-native" como OpenAI Agents SDK.

## Descripción técnica

### 1. Repositorio, autoría y origen

- **Repo**: `github.com/microsoft/autogen` — MIT (código) + CC-BY-4.0 (documentación) — **license splitting importante** (ver §Buenas prácticas).
- **Organización**: Microsoft Research (multi-lab: AI Frontiers, Systems & Networking).
- **Commits recientes**: actividad mayoritariamente de bots (`copilot-swe-agent` como co-autor en #7054, #7025, #6889, #7022) — ver Pendiente #7 sobre tasa de aceptación de PRs.
- **Lenguajes del repo** (% bytes, GitHub API): Python ~67%, C# ~27% (NuGet), TypeScript ~14% (overlap por packages múltiples).
- **Release history**: v0.2 (nov 2023, paper ArXiv 2308.08155) → v0.3 (may 2024, registro de agentes) → **v0.4 (ene 2025, rewrite a actor model)** → v0.5/0.6/0.7.x (2025) → v0.7.5 (2025-09-30) → sin nuevos tags python-v* desde entonces.
- **Gap de actividad**: 5 meses (oct 2025 → mar 2026) en `main` — ver Pendiente #8 sobre la causa (mode-switch, freeze holiday, reducción activa).

### 2. Los cinco patrones de `Team` (corazón de AutoGen agentchat)

Cada `Team` es una clase de orquestación con reglas de routing y termination específicas:

| Team | Routing | Caso de uso típico | Termination default |
|---|---|---|---|
| `RoundRobinGroupChat` | Turno fijo, circular | Discusión equitativa entre expertos | `MaxMessageTermination(n)` |
| `SelectorGroupChat` | LLM elige el siguiente speaker | Diálogo abierto, expertise heterogénea | `TextMentionTermination("TERMINATE")` |
| `Swarm` | Handoff via mensajes especiales | Triaje, escalado por especialización | `HandoffTermination` |
| `MagenticOneGroupChat` | Orquestador central (Magentic-One) | Tareas generales web/file/code, benchmarks | `MaxMessageTermination(20)` + `TextMentionTermination` |
| `GraphFlow` | Grafo de flujo explícito (nodos + edges) | Pipelines deterministas, batch processing | Custom por nodo |

`Magentic-One` merece mención aparte porque es **state-of-the-art en benchmarks públicos** (paper ArXiv 2411.04468, noviembre 2024): 38% GAIA, 32.8% WebArena, 27.7% AssistantBench. Es el único Team de AutoGen que implementa el patrón de **orquestador + agentes especializados** (Coder, ComputerTerminal, FileSurfer, WebSurfer). Microsoft lo usa como baseline para MAF.

### 3. Actor model y message passing (fundamento de v0.4+)

La diferencia radical de v0.4 frente a v0.2 es el **actor model**:

- **v0.2 (legacy)**: agentes con `register_reply`; cada agent tenía métodos síncronos tipo `def reply(self, messages)`. El control de flujo era manual y propenso a deadlocks.
- **v0.4+ (actual)**: agentes como actores (`BaseAgent` subclass) que reciben `on_messages()`, retornan `Response`. El runtime nuclear (`autogen-core`) maneja el message passing async vía `RpcAgentRuntime` (in-process) o `GrpcWorkerAgentRuntime` (distributed).

**Implicación clave**: v0.4+ requiere que TODA la lógica de agente sea async (`async def on_messages`). Migrar de v0.2 a v0.4+ es un rewrite completo de la lógica de agente, no un cambio de imports. (Migration Guide: `microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/migration-guide.html`).

### 4. Termination conditions

AutoGen permite componer **múltiples termination conditions** con `|` (OR lógico):

```python
# Fuente: Migration Guide, sección Termination
from autogen_agentchat.conditions import (
    TextMentionTermination,
    MaxMessageTermination,
    TokenUsageTermination,
    FunctionCallTermination,
    SourceMatchTermination,
    HandoffTermination,
    TimeoutTermination,
)

# Componer con OR: cualquiera que se cumpla termina el chat
termination = (
    TextMentionTermination("TERMINATE")
    | MaxMessageTermination(max_messages=25)
    | TokenUsageTermination(max_tokens=8000)
    | FunctionCallTermination(function_name="submit_answer")
)
```

Esto es más rico que la mayoría de frameworks competidores, donde típicamente solo hay "max iterations" o "explicit end signal".

### 5. Persistencia de estado

`autogen-core` provee dos APIs oficiales para serializar/reanudar conversaciones:

```python
# Fuente: Migration Guide, sección "Group Chat with Resume"
# Guardar estado completo de un team
state = await team.save_state()
with open("team_state.json", "w") as f:
    json.dump(state, f)

# Restaurar en otro proceso / sesión
team2 = create_team(model_client)
with open("team_state.json", "r") as f:
    state2 = json.load(f)
await team2.load_state(state2)
# El chat continúa exactamente donde quedó
```

A diferencia de LangGraph (que tiene checkpointer nativo con MemorySaver/PostgresSaver/RedisSaver), AutoGen requiere que el caller serialice a JSON. No hay checkpointer transparente.

### 6. MCP support (first-class en 0.7.5)

```python
# Fuente: docs oficiales + 0.7.5 release notes
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams

# Cargar herramientas desde un servidor MCP externo
mcp_server = StdioServerParams(command="npx", args=["-y", "@playwright/mcp"])
workbench = McpWorkbench(server_params=mcp_server)

# Inyectar en un agente
agent = AssistantAgent(
    name="browser_agent",
    model_client=model_client,
    workbench=workbench,  # tools se exponen automáticamente
)
```

Soporta Elicitation, Sampling y Roots (las tres capacidades MCP avanzadas). A junio 2026 es **el framework con mejor soporte MCP de los 5 comparados** (vs LangGraph 1.0 que también lo tiene nativo, vs CrewAI que solo vía adaptadores).

### 7. Distribuido cross-language

`GrpcWorkerAgentRuntime` permite tener **agentes Python y .NET en el mismo sistema** vía gRPC. Esto es raro en frameworks OSS (LangGraph es single-language; OpenAI Agents SDK es Python-only first-class; CrewAI está expandiendo).

Casos de uso reales:
- Agente Python (LLM) que delega a agente .NET (lógica de negocio legacy en C#).
- Workers Python en pods Kubernetes + un orquestador .NET on-prem.
- Edge device (Rust/.NET) llamando a un orquestador Python central.

### 8. Observability built-in

AutoGen emite **OpenTelemetry GenAI spans** automáticamente para `create_agent`, `invoke_agent`, `execute_tool`. Compatible con:
- **OpenInference** (community, status experimental — ver Pendiente #10).
- **Langfuse** (vía OTel collector).
- **Arize Phoenix** (vía OTel collector).
- **MLflow tracing** (vía `mlflow.autogen.autolog()`).

**Caveat conocido** (ver Pendiente #11): AutoGen NO emite spans para las llamadas individuales al modelo (OpenAI/Anthropic API calls). Solo para runtime/agent. Para tracing completo necesitas un wrapper adicional.

### 9. Lenguajes y stacks adyacentes

- **Python**: lenguaje principal (todo el código en `python/packages/`). Versión soportada: 3.10 - 3.13.
- **.NET**: 4 NuGet packages (`Microsoft.AutoGen.Contracts`, `Core`, `Core.Grpc`, `RuntimeGateway.Grpc`) — generados automáticamente desde los protocolos Protobuf del runtime gRPC.
- **TypeScript**: bindings parciales (vía `autogenstudio` web UI); no es SDK first-class.
- **Magentic-One CLI**: `python/packages/magentic-one-cli/` — para invocar el orquestador desde terminal. Status actual: incierto (ver Pendiente #9).

## Flujo interno

Secuencia típica de un `RoundRobinGroupChat` con dos agentes (asistente + code executor):

```
1. Usuario envía mensaje inicial al team
   └─> team.run_stream(task="Write a Python script...")
       └─> RoundRobinGroupChat.run_stream()
           └─> Para cada participante (round-robin):
               ├─> agent.on_messages(messages, ctx)
               │    └─> ChatCompletionClient.create() (LLM call)
               │    └─> publica Response en el topic
               └─> team verifica termination conditions
                   ├─> TextMentionTermination? → si
                   ├─> MaxMessageTermination? → si
                   └─> Si ninguna → siguiente participante
       └─> stream emite TaskResult con chat_history
2. Cliente consume el stream (SSE, websocket, o async iterator)
```

**Variaciones**:
- `SelectorGroupChat`: en lugar de round-robin, el `Selector` (otro LLM o función) elige el siguiente speaker.
- `Swarm`: cuando un agente publica un mensaje con `HandoffMessage(source, target)`, el control salta al target.
- `MagenticOneGroupChat`: el orquestador Magentic-One decide qué agente especializado invocar en cada paso, basándose en un ledger de progreso y confianza.
- `GraphFlow`: el caller define un `DiGraph` con nodos (callables) y edges (transitions); el runtime ejecuta el grafo.

## Call Stack / API

Para una integración típica Aithera-style con FastAPI + SSE streaming:

```
HTTP POST /api/agents/autogen/stream
  → FastAPI handler
    → autogen_chat_service.stream_chat(task, history, team_config)
      → build_team(config)  # Team factory: round-robin, selector, swarm, etc.
        → AssistantAgent(model_client=OpenAIChatCompletionClient(...))
        → UserProxyAgent()  # si human-in-loop
        → termination = TextMentionTermination("DONE") | MaxMessageTermination(20)
      → team.run_stream(task=user_message)
        → async iterator de eventos:
          ├─> TaskResult(messages=[...], source="user")
          ├─> TextMessage(content="...", source="assistant_agent_1")
          ├─> ToolCallRequestEvent(...)
          ├─> ToolCallExecutionEvent(...)
          └─> TaskResult(messages=[...], source="user_proxy")
      → SSE chunks al cliente
        → onChunk en React/Vue
```

Las **funciones clave** de la API pública (Python):

| Función / clase | Propósito |
|---|---|
| `autogen_agentchat.agents.AssistantAgent` | Agente LLM-backed estándar |
| `autogen_agentchat.agents.UserProxyAgent` | Agente human-in-the-loop (solicita input al usuario) |
| `autogen_agentchat.agents.CodeExecutorAgent` | Agente que ejecuta código (sandboxed) |
| `autogen_agentchat.teams.RoundRobinGroupChat` | Team con turno fijo |
| `autogen_agentchat.teams.SelectorGroupChat` | Team con selector LLM |
| `autogen_agentchat.teams.Swarm` | Team con handoff messages |
| `autogen_agentchat.teams.MagenticOneGroupChat` | Team con orquestador Magentic-One |
| `autogen_agentchat.teams.GraphFlow` | Team con grafo explícito |
| `autogen_agentchat.conditions.*` | 7+ termination conditions componibles |
| `autogen_ext.models.openai.OpenAIChatCompletionClient` | Cliente OpenAI/Azure |
| `autogen_ext.models.anthropic.AnthropicChatCompletionClient` | Cliente Anthropic |
| `autogen_ext.models.ollama.OllamaChatCompletionClient` | Cliente Ollama (local) |
| `autogen_ext.tools.mcp.McpWorkbench` | Integración MCP first-class |
| `autogen_core.*` | Runtime nuclear (advanced) |

## Diagramas

### Diagrama de capas (high-level)

```
┌────────────────────────────────────────────────────────────┐
│  USUARIO                                                    │
└──────────────────┬─────────────────────────────────────────┘
                   ▼
┌────────────────────────────────────────────────────────────┐
│  APLICACIÓN (Python script / FastAPI / Jupyter)             │
└──────────────────┬─────────────────────────────────────────┘
                   ▼
┌────────────────────────────────────────────────────────────┐
│  autogen-agentchat (high-level)                             │
│  - AssistantAgent / UserProxyAgent / CodeExecutorAgent      │
│  - Teams: RR / Selector / Swarm / MagenticOne / GraphFlow  │
│  - Termination: 7+ condiciones componibles                  │
└──────────────────┬─────────────────────────────────────────┘
                   ▼
┌────────────────────────────────────────────────────────────┐
│  autogen-core (runtime nuclear)                             │
│  - Actor model + message passing async                      │
│  - SingleProcess / GrpcWorker runtime                       │
│  - BaseAgent, AgentId, AgentMetadata, Type subscriptions    │
└──────────────────┬─────────────────────────────────────────┘
                   ▼
┌────────────────────────────────────────────────────────────┐
│  autogen-ext (adaptadores)                                  │
│  - OpenAI / Anthropic / Ollama / Azure OpenAI / Bedrock    │
│  - MCP workbench / Magentic-One / OpenTelemetry             │
└────────────────────────────────────────────────────────────┘
```

### Diagrama de un Swarm (handoff entre agentes)

```
[Athena (intent classifier)]
       │
       │ HandoffMessage(target="BillingAgent", reason="user wants refund")
       ▼
[BillingAgent]
       │
       │ HandoffMessage(target="RefundAgent", reason="requires approval")
       ▼
[RefundAgent]
       │
       │ publica RefundCompleted
       ▼
   [END]
```

## Código relacionado

Paths exactos en el repo `microsoft/autogen` (branch `main`, acceso 2026-07-02):

- `python/packages/autogen-core/src/autogen_core/_agent.py` — `BaseAgent` ABC con `on_messages`, `on_reset`, `produced_message_types`.
- `python/packages/autogen-core/src/autogen_core/_runtime.py` — `SingleProcessAgentRuntime`, `GrpcWorkerAgentRuntime`.
- `python/packages/autogen-agentchat/src/autogen_agentchat/agents/_assistant_agent.py` — `AssistantAgent` con `ChatCompletionClient`.
- `python/packages/autogen-agentchat/src/autogen_agentchat/teams/_round_robin_group_chat.py` — `RoundRobinGroupChat`.
- `python/packages/autogen-agentchat/src/autogen_agentchat/teams/_selector_group_chat.py` — `SelectorGroupChat`.
- `python/packages/autogen-agentchat/src/autogen_agentchat/teams/_swarm.py` — `Swarm` con handoff messages.
- `python/packages/autogen-agentchat/src/autogen_agentchat/teams/_magentic_one.py` — `MagenticOneGroupChat`.
- `python/packages/autogen-agentchat/src/autogen_agentchat/teams/_graph.py` — `GraphFlow` con `DiGraph`.
- `python/packages/autogen-ext/src/autogen_ext/tools/mcp/_workbench.py` — `McpWorkbench` con Elicitation/Sampling/Roots.
- `python/packages/autogen-ext/src/autogen_ext/models/openai/_openai_client.py` — `OpenAIChatCompletionClient`.
- `python/packages/autogen-ext/src/autogen_ext/models/anthropic/_anthropic_client.py` — `AnthropicChatCompletionClient`.
- `python/packages/autogen-ext/src/autogen_ext/teams/magentic_one/_magentic_one.py` — Helper class `MagenticOne` para quickstart.

## Ejemplos

### Ejemplo 1: RoundRobinGroupChat básico con termination dual

```python
# Fuente: Migration Guide, sección Termination
# Requiere: pip install "autogen-agentchat" "autogen-ext[openai]"
# AutoGen v0.4+ requiere async en TODA la lógica
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def main() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4o")

    # Dos agentes que se turnan en orden
    planner = AssistantAgent(
        "planner",
        model_client=model_client,
        system_message="Planifica los pasos para resolver la tarea. Llama TERMINATE cuando termines.",
    )
    coder = AssistantAgent(
        "coder",
        model_client=model_client,
        system_message="Implementa el plan en Python. Ejecuta el código si es necesario.",
    )

    # Termination compuesta: OR lógico entre dos condiciones
    termination = TextMentionTermination("TERMINATE") | MaxMessageTermination(10)

    # Team con turno fijo (planner → coder → planner → coder ...)
    team = RoundRobinGroupChat(
        [planner, coder],
        termination_condition=termination,
    )

    # Streaming de eventos a la consola
    stream = team.run_stream(task="Escribe un script Python que ordene una lista de diccionarios por 'edad'.")
    await Console(stream)

    await model_client.close()

asyncio.run(main())
```

### Ejemplo 2: SelectorGroupChat con selector LLM (state-based)

```python
# Fuente: Migration Guide, sección "Group Chat with Custom Selector"
# El selector decide qué agente habla a continuación
import asyncio
from typing import Sequence
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

def create_team(model_client: OpenAIChatCompletionClient) -> SelectorGroupChat:
    # Selector LLM que elige el siguiente speaker
    selector = AssistantAgent(
        "Selector",
        description="Elige qué agente debe hablar basándose en la conversación.",
        model_client=model_client,
        system_message="""Eres un selector. Elige UN agente de [Planner, Researcher, Writer] 
basándote en el último mensaje. Responde SOLO con el nombre del agente.""",
    )

    planner = AssistantAgent(
        "Planner",
        description="Descompone tareas complejas en pasos.",
        model_client=model_client,
    )
    researcher = AssistantAgent(
        "Researcher",
        description="Busca información y resume hallazgos.",
        model_client=model_client,
    )
    writer = AssistantAgent(
        "Writer",
        description="Escribe contenido final basado en investigación.",
        model_client=model_client,
    )

    text_mention = TextMentionTermination("DONE")
    max_messages = MaxMessageTermination(max_messages=20)
    return SelectorGroupChat(
        [planner, researcher, writer],
        model_client=model_client,  # LLM del selector
        termination_condition=text_mention | max_messages,
    )

async def main() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4o")
    team = create_team(model_client)
    stream = team.run_stream(task="Investiga el mercado de AI agents en 2026 y escribe un reporte ejecutivo.")
    await Console(stream)
    await model_client.close()

asyncio.run(main())
```

### Ejemplo 3: Swarm con handoff messages para triaje

```python
# Fuente: Migration Guide, sección Swarm
# Cada agente puede transferir el control via HandoffMessage
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import Swarm
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def main() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4o")

    triage = AssistantAgent(
        "TriageAgent",
        model_client=model_client,
        handoffs=["BillingAgent", "TechSupportAgent"],
        system_message="""Clasifica la consulta del usuario.
- Si es de facturación → transfiere a BillingAgent.
- Si es técnico → transfiere a TechSupportAgent.
- Si no sabes → pide clarificación al usuario.""",
    )
    billing = AssistantAgent(
        "BillingAgent",
        model_client=model_client,
        handoffs=["TriageAgent"],
        system_message="""Resuelve consultas de facturación.
Si no puedes resolver, transfiere de vuelta a TriageAgent.""",
    )
    tech = AssistantAgent(
        "TechSupportAgent",
        model_client=model_client,
        handoffs=["TriageAgent"],
        system_message="""Resuelve problemas técnicos.
Si la consulta es de facturación, transfiere de vuelta a TriageAgent.""",
    )

    # Swarm: el handoff entre agentes es via mensajes especiales
    team = Swarm([triage, billing, tech])
    stream = team.run_stream(task="Mi último cargo es incorrecto, ¿pueden revisarlo?")
    await Console(stream)
    await model_client.close()

asyncio.run(main())
```

### Ejemplo 4: Custom agent heredando BaseChatAgent

```python
# Fuente: Migration Guide, sección "Conversable Agent and Register Reply"
# Para lógica custom que NO encaja en AssistantAgent/UserProxyAgent
from typing import Sequence
from autogen_core import CancellationToken
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.messages import TextMessage, BaseChatMessage
from autogen_agentchat.base import Response

class EchoAgent(BaseChatAgent):
    """Agente que simplemente repite el último mensaje del usuario."""

    def __init__(self, name: str) -> None:
        super().__init__(name, "Un agente que hace eco del último mensaje del usuario.")

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (TextMessage,)

    async def on_messages(
        self,
        messages: Sequence[BaseChatMessage],
        cancellation_token: CancellationToken,
    ) -> Response:
        # Tomar el último mensaje del usuario
        last_user_msg = next(
            (m for m in reversed(messages) if m.source == "user"),
            None,
        )
        if last_user_msg is None:
            content = "(no input)"
        else:
            content = f"Echo: {last_user_msg.content}"

        return Response(
            chat_message=TextMessage(content=content, source=self.name),
        )

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        pass  # No state to reset
```

### Ejemplo 5: Persistencia con `save_state` / `load_state`

```python
# Fuente: Migration Guide, sección "Group Chat with Resume"
import asyncio
import json
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def main() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4o", seed=42, temperature=0)
    writer = AssistantAgent("writer", model_client=model_client, system_message="Eres un escritor.")
    critic = AssistantAgent("critic", model_client=model_client, system_message="Crítico. Responde 'APPROVE' si está bien.")

    team = RoundRobinGroupChat([writer, critic], termination_condition=TextMentionTermination("APPROVE"))

    # Chat 1: generar borrador inicial
    async for event in team.run_stream(task="Escribe un microrrelato sobre un robot que descubre que tiene sentimientos."):
        print(event)

    # Guardar estado completo del team
    state = await team.save_state()
    with open("team_state.json", "w") as f:
        json.dump(state, f)

    # Chat 2 (más tarde o en otro proceso): reanudar
    team2 = RoundRobinGroupChat([writer, critic], termination_condition=TextMentionTermination("APPROVE"))
    with open("team_state.json", "r") as f:
        state2 = json.load(f)
    await team2.load_state(state2)

    # Continúa exactamente donde quedó
    async for event in team2.run_stream(task="Traduce el microrrelato al chino."):
        print(event)

    await model_client.close()

asyncio.run(main())
```

### Ejemplo 6: Magentic-One orquestador (helper class)

```python
# Fuente: Migration Guide, sección magentic-one + release notes
# Requiere: pip install -U "autogen-agentchat" "autogen-ext[openai,magentic-one]"
import asyncio
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.teams.magentic_one import MagenticOne
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_ext.agents.file_surfer import FileSurfer
from autogen_ext.agents.magentic_one import MagenticOneCoderAgent

async def main() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4o")

    # Opción A: helper class simple (quickstart)
    assistant = MagenticOne(client=model_client, max_rounds=20)

    # Opción B: team nativo con agentes especializados
    web_surfer = MultimodalWebSurfer("web_surfer", model_client=model_client)
    file_surfer = FileSurfer("file_surfer", model_client=model_client)
    coder = MagenticOneCoderAgent("coder", model_client=model_client)

    team = MagenticOneGroupChat(
        participants=[web_surfer, file_surfer, coder],
        model_client=model_client,
        max_turns=20,
    )

    async for event in team.run_stream(
        task="Encuentra el PIB de China en 2024 y guárdalo en un CSV."
    ):
        print(event)

    await model_client.close()

asyncio.run(main())
```

### Ejemplo 7: MCP integration first-class

```python
# Fuente: 0.7.5 release notes + MCP docs
# AutoGen 0.7.5+ soporta Elicitation, Sampling y Roots
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def main() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4o")

    # Servidor MCP local via stdio (ejemplo: Playwright MCP)
    mcp_params = StdioServerParams(
        command="npx",
        args=["-y", "@playwright/mcp"],
    )

    # Workbench expone las tools del MCP server
    async with McpWorkbench(server_params=mcp_params) as workbench:
        agent = AssistantAgent(
            name="browser_agent",
            model_client=model_client,
            workbench=workbench,  # tools se exponen automáticamente
        )

        # El agente puede usar las tools MCP via function calling
        result = await agent.run(
            task="Ve a wikipedia.org y dime el título de la página principal."
        )
        print(result.messages[-1].content)

    await model_client.close()

asyncio.run(main())
```

### Ejemplo 8: Agente con Anthropic (Claude) en vez de OpenAI

```python
# Fuente: autogen-ext Anthropic integration docs
# Requiere: pip install "autogen-ext[anthropic]"
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.anthropic import AnthropicChatCompletionClient

async def main() -> None:
    # Cambiar de OpenAI a Anthropic es trivial — la API de Agent es la misma
    model_client = AnthropicChatCompletionClient(model="claude-3-5-sonnet-20241022")

    agent = AssistantAgent(
        name="claude_assistant",
        model_client=model_client,
        system_message="Eres Claude, un asistente AI de Anthropic.",
    )

    result = await agent.run(task="¿Cuál es la diferencia entre un monorepo y un polyrepo?")
    print(result.messages[-1].content)

    await model_client.close()

asyncio.run(main())
```

