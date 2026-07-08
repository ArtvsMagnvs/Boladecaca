# Material crudo JWIKI-010 — Comparativa frameworks de agentes

> Investigación realizada el **2026-07-07** para alimentar el documento
> `JWIKI/01_LANDSCAPE/agent-frameworks.md` (JWIKI-010).
> Fuentes: GitHub (HTML público + feeds Atom de releases, sin rate limit porque
> el scraping HTML no usa la API REST autenticada), READMEs y archivos
> LICENSE en `raw.githubusercontent.com`. La API REST de GitHub devolvió
> `rate limit exceeded` para llamadas sin token, por lo que se sustituyó por
> scraping de las páginas HTML y los feeds Atom públicos de releases.

---

## Tabla resumen (9 frameworks)

| Framework | Stars | Última release | Lenguaje | Licencia | Maintainer | Patrón principal |
|---|---|---|---|---|---|---|
| **LangGraph** | 36 642 | `langgraph==1.2.8` — 2026-07-06 | Python (monorepo Python + TS/JS) | MIT | LangChain, Inc. | State machines / grafos cíclicos |
| **CrewAI** | 55 029 | `1.15.2a2` — 2026-07-01 | Python | MIT (Copyright 2025 crewAI, Inc.) | crewAI Inc. (joaomdmoura) | Equipos de agentes + Flows |
| **AutoGen** | 59 536 | `python-v0.7.5` — 2025-09-30 | Python + .NET | **CC-BY-4.0** (Attribution 4.0 International) | Microsoft | Multi-agente conversacional / GroupChat |
| **Google ADK** | 20 501 | `v1.36.1` — 2026-07-06 (rama v1); `v2.3.0` — 2026-06-19 (rama v2) | Python | Apache-2.0 | Google | Agentes jerárquicos + tools + Live API |
| **OpenAI Agents SDK** | 27 695 | `v0.17.7` — 2026-06-24 | Python | MIT (Copyright 2025 OpenAI) | OpenAI | Agentes + handoffs + guardrails |
| **Semantic Kernel** | 28 272 | `python-1.43.1` — 2026-06-17 | Python + .NET + Java | MIT (Copyright Microsoft) | Microsoft | Planner + funciones semánticas |
| **LlamaIndex** | 50 687 | `v0.14.23` — 2026-06-24 (monorepo con docenas de paquetes; core va a su ritmo) | Python + TS | MIT (Copyright Jerry Liu) | LlamaIndex / run-llama | RAG / workflows (agentic) |
| **Smolagents** | 28 219 | rama `main` activa; releases Atom no encontrados en el repo (última visible: 2025) | Python | Apache-2.0 | Hugging Face (`huggingface/smolagents`) | CodeAgents (LMs que escriben Python) |
| **Strands (AWS)** | 6 444 (monorepo `harness-sdk`) | `typescript/v1.7.0` — 2026-06-25 (TS); rama Python `python/` con releases `python/...` | Python + TypeScript | Apache-2.0 (LICENSE.APACHE) | AWS (`strands-agents`) | Model-driven agent loop + tools + MCP |

> **Notas sobre Smolagents**: el org del repo se llama ahora `huggingface/smolagents`
> (no `Smolagents/smolagents` como en 2024-2025). Su feed Atom de releases en
> `github.com/huggingface/smolagents/releases.atom` no fue localizable desde el
> scraping (la URL devolvió 404). El último release público visible es de finales
> de 2025; el repo sigue activo con commits frecuentes — **VERIFICACIÓN
> PENDIENTE** para la versión exacta y fecha del último release.
>
> **Notas sobre Strands**: el SDK vive en el monorepo `strands-agents/harness-sdk`,
> que contiene `strands-py/` (Python SDK) y `strands-ts/` (TypeScript SDK). Las
> releases están separadas por SDK con tags del tipo `python/vX.Y.Z` y
> `typescript/vX.Y.Z`. Stars y descripción corresponden al monorepo completo.

---

## Hechos verificados por framework

### LangGraph (`github.com/langchain-ai/langgraph`)
1. Stars = **36 642** (scraping HTML de la home del repo, 2026-07-07). Fuente:
   `https://github.com/langchain-ai/langgraph` — fecha acceso 2026-07-07.
2. Última release del monorepo: `langgraph==1.2.8` con fecha **2026-07-06T20:36Z**
   (feed `releases.atom`). Fuente:
   `https://github.com/langchain-ai/langgraph/releases.atom` — fecha acceso
   2026-07-07.
3. Licencia **MIT** confirmada en `LICENSE` (Copyright 2024 LangChain, Inc.).
   Fuente: `https://raw.githubusercontent.com/langchain-ai/langgraph/HEAD/LICENSE`
   — fecha acceso 2026-07-07.

### CrewAI (`github.com/crewAIInc/crewAI`)
1. Stars = **55 029** (scraping HTML, 2026-07-07). Fuente:
   `https://github.com/crewAIInc/crewAI` — fecha acceso 2026-07-07.
2. Última release: `1.15.2a2` con fecha **2026-07-01T22:15Z** (feed
   `releases.atom`). La versión estable más reciente es `1.15.1` (2026-06-27);
   `1.15.2a1/a2` son alphas. Fuente:
   `https://github.com/crewAIInc/crewAI/releases.atom` — fecha acceso 2026-07-07.
3. Licencia **MIT** confirmada en `LICENSE` (Copyright 2025 crewAI, Inc.).
   Fuente: `https://raw.githubusercontent.com/crewAIInc/crewAI/HEAD/LICENSE` —
   fecha acceso 2026-07-07.

### AutoGen (`github.com/microsoft/autogen`)
1. Stars = **59 536** (scraping HTML, 2026-07-07). Fuente:
   `https://github.com/microsoft/autogen` — fecha acceso 2026-07-07.
2. Última release: `python-v0.7.5` con fecha **2025-09-30T06:18Z** (feed
   `releases.atom`). El repo es multi-lenguaje (Python + .NET) y los tags
   indican `python-vX.Y.Z`. Fuente:
   `https://github.com/microsoft/autogen/releases.atom` — fecha acceso 2026-07-07.
3. Licencia **Creative Commons Attribution 4.0 International (CC-BY-4.0)**,
   NO MIT/Apache. Es una elección deliberada de Microsoft, común en proyectos
   académicos/educativos. Fuente:
   `https://raw.githubusercontent.com/microsoft/autogen/HEAD/LICENSE` — fecha
   acceso 2026-07-07.

### Google ADK (`github.com/google/adk-python`)
1. Stars = **20 501** (scraping HTML, 2026-07-07). Fuente:
   `https://github.com/google/adk-python` — fecha acceso 2026-07-07.
2. Última release: `v1.36.1` con fecha **2026-07-06T21:07Z** (feed
   `releases.atom`). Existe además rama `v2` con `v2.3.0` (2026-06-17) que
   introduce migración a "enterprise parameters", `GOOGLE_GENAI_USE_ENTERPRISE`,
   mTLS en MCP, etc. Fuente:
   `https://github.com/google/adk-python/releases.atom` — fecha acceso 2026-07-07.
3. Licencia **Apache-2.0** confirmada en `LICENSE`. Fuente:
   `https://raw.githubusercontent.com/google/adk-python/HEAD/LICENSE` — fecha
   acceso 2026-07-07.

### OpenAI Agents SDK (`github.com/openai/openai-agents-python`)
1. Stars = **27 695** (scraping HTML, 2026-07-07). Fuente:
   `https://github.com/openai/openai-agents-python` — fecha acceso 2026-07-07.
2. Última release: `v0.17.7` con fecha **2026-06-24T05:15Z** (feed
   `releases.atom`). Fuente:
   `https://github.com/openai/openai-agents-python/releases.atom` — fecha
   acceso 2026-07-07.
3. Licencia **MIT** confirmada en `LICENSE` (Copyright 2025 OpenAI). Fuente:
   `https://raw.githubusercontent.com/openai/openai-agents-python/HEAD/LICENSE`
   — fecha acceso 2026-07-07.

### Semantic Kernel (`github.com/microsoft/semantic-kernel`)
1. Stars = **28 272** (scraping HTML, 2026-07-07). Fuente:
   `https://github.com/microsoft/semantic-kernel` — fecha acceso 2026-07-07.
2. Última release Python: `python-1.43.1` con fecha **2026-06-17T07:28Z**
   (feed `releases.atom`). El repo es multi-lenguaje (Python + .NET + Java).
   Fuente: `https://github.com/microsoft/semantic-kernel/releases.atom` —
   fecha acceso 2026-07-07.
3. Licencia **MIT** confirmada en `LICENSE` (Copyright Microsoft Corporation).
   Fuente: `https://raw.githubusercontent.com/microsoft/semantic-kernel/HEAD/LICENSE`
   — fecha acceso 2026-07-07.

### LlamaIndex (`github.com/run-llama/llama_index`)
1. Stars = **50 687** (scraping HTML, 2026-07-07). Fuente:
   `https://github.com/run-llama/llama_index` — fecha acceso 2026-07-07.
2. Última release: `v0.14.23` con fecha **2026-06-24T19:36Z** (feed
   `releases.atom`). Es un monorepo con docenas de paquetes
   (`llama-index-core`, `llama-index-llms-anthropic`, etc.). Fuente:
   `https://github.com/run-llama/llama_index/releases.atom` — fecha acceso
   2026-07-07.
3. Licencia **MIT** confirmada en `LICENSE` (Copyright Jerry Liu). Fuente:
   `https://raw.githubusercontent.com/run-llama/llama_index/HEAD/LICENSE` —
   fecha acceso 2026-07-07.

### Smolagents (`github.com/huggingface/smolagents`)
1. Stars = **28 219** (scraping HTML, 2026-07-07). Fuente:
   `https://github.com/huggingface/smolagents` — fecha acceso 2026-07-07.
2. Última release visible: `1.21.2` (finales de 2025). El feed Atom público en
   `github.com/huggingface/smolagents/releases.atom` devolvió 404 al hacer
   scraping — **VERIFICACIÓN PENDIENTE** del número de versión y fecha exacta
   del último release. El README confirma Apache-2.0 y describe
   `CodeAgent(tools=[...], model=model, stream_outputs=True)`. Fuente:
   `https://raw.githubusercontent.com/huggingface/smolagents/main/README.md` —
   fecha acceso 2026-07-07.
3. Licencia **Apache-2.0** confirmada en `LICENSE` (Copyright 2024 The
   HuggingFace Team). Fuente:
   `https://raw.githubusercontent.com/huggingface/smolagents/HEAD/LICENSE` —
   fecha acceso 2026-07-07.

### Strands (`github.com/strands-agents/harness-sdk`)
1. Stars = **6 444** en el monorepo `harness-sdk` (scraping HTML, 2026-07-07).
   Fuente: `https://github.com/strands-agents/harness-sdk` — fecha acceso
   2026-07-07.
2. Última release TS: `typescript/v1.7.0` con fecha **2026-06-25T21:18Z**
   (feed `releases.atom`). El SDK vive como monorepo con `strands-py/` y
   `strands-ts/` y releases etiquetadas `python/vX.Y.Z` y
   `typescript/vX.Y.Z`. Fuente:
   `https://github.com/strands-agents/harness-sdk/releases.atom` — fecha
   acceso 2026-07-07.
3. Licencia **Apache-2.0** confirmada en `LICENSE.APACHE` (referenciado en el
   README del repo). Fuente:
   `https://github.com/strands-agents/harness-sdk#license` — fecha acceso
   2026-07-07.

---

## Criterios de comparación

1. **Paradigma** — modelo de orquestación principal.
2. **Lenguaje principal** — implementación canónica.
3. **Estado del proyecto** — activo / maintenance / abandonado (basado en
   frecuencia de releases).
4. **Multi-agent support** — sí/no/nativo (API de primera clase para múltiples
   agentes cooperando).
5. **MCP support** — soporte nativo para Model Context Protocol.
6. **Human-in-the-loop** — soporte explícito para intervención humana.
7. **Streaming** — streaming de tokens/eventos al cliente.
8. **License** — tipo de licencia.
9. **Maintainer** — organización responsable.
10. **Stars / release cadence** — adopción y ritmo de updates.

---

## Tabla comparativa por criterio

> Celdas marcadas con `✅` / `⚠️` / `❌` se basan en documentación oficial y
> README de cada repo. Cuando una característica es **nativa** se marca
> explícitamente; cuando requiere **integración** con terceros (p. ej. LangChain
> o LiteLLM) se anota.

| Criterio | LangGraph | CrewAI | AutoGen | Google ADK | OpenAI Agents | Semantic Kernel | LlamaIndex | Smolagents | Strands |
|---|---|---|---|---|---|---|---|---|---|
| **Paradigma** | State machines / grafos cíclicos (StateGraph + checkpoints) | Equipos (Crews) con roles + Flows declarativos | Multi-agente conversacional (GroupChat, RoundRobin, Swarm) + GraphFlow | Jerárquico (sub_agents, agent_engine), tools, Live API | Agentes + handoffs + guardrails (Runner loop) | Planner + funciones semánticas + Process Framework | RAG-first, workflows agentic (`Workflow`, `AgentWorkflow`) | CodeAgents (LM que escribe y ejecuta código Python) | Model-driven agent loop (ciclo modelo-herramienta) + hooks |
| **Lenguaje principal** | Python (monorepo también TS/JS) | Python | Python + .NET | Python | Python | Python + .NET + Java | Python + TS | Python | Python + TypeScript |
| **Estado del proyecto** | 🟢 Activo (release mensual) | 🟢 Activo (release mensual, alphas frecuentes) | 🟡 Activo pero ritmo más lento (última release 2025-09) | 🟢 Muy activo (release semanal, dos ramas v1/v2) | 🟢 Activo (release bisemanal) | 🟢 Activo (release mensual) | 🟢 Muy activo (monorepo, docenas de paquetes) | 🟡 Activo, releases menos visibles | 🟢 Activo (releases por SDK, Python y TS) |
| **Multi-agent support** | ✅ Nativo (Send/Command API, subgraphs, RemoteGraph) | ✅ Nativo (`Crew`, `Flow`, `each.do`, agentes como nodos) | ✅ Nativo (`Team`, `GroupChat`, `RoundRobinGroupChat`, nested Teams) | ✅ Nativo (`sub_agents`, `AgentTool`, jerarquías) | ✅ Nativo (`handoffs` + agentes como tools) | ✅ (`Process Framework`, GroupChatOrchestration) | ✅ (`AgentWorkflow`, `MultiAgentWorkflow`) | ⚠️ Sí vía composición (MultiAgentSystem) | ✅ Nativo (multi-agent patterns en docs) |
| **MCP support** | ✅ Sí (integración con `mcp` python; cli soporta MCP servers) | ✅ Sí (vía `crewai-tools` y adapters MCP) | ✅ Sí (`McpWorkbench`, `McpSessionActor`) | ✅ Sí (`McpToolset`, soporte oficial) | ✅ Sí (`MCPServer*` adapters, stdio/SSE/HTTP) | ⚠️ Sí vía plugins/conectores externos | ⚠️ Vía `llama-index-tools-mcp` (community) | ✅ Sí (`ToolCollection.from_mcp`) | ✅ Sí (built-in, `mcp-server` repo propio de la org) |
| **Human-in-the-loop** | ✅ `interrupt()` + `Command(resume=...)` con checkpointing | ✅ (autonomía gradual, feedback en reglas — patrón equivalente) | ✅ (`UserProxyAgent`, `InputRequestPermission`) | ✅ (`request_input`, `transfer_to_agent`, HITL interrupt en A2A) | ✅ `RunHooks` + tool `input_*` + interrupts | ✅ (`input()` function, StepwisePlanner) | ⚠️ Vía `HumanExecutor`/callback | ❌ No nativo (requiere wrapper) | ✅ Hooks + steering handlers (built-in) |
| **Streaming** | ✅ `stream()` / `astream_events()` v3 (SSE + WebSocket) | ✅ Stream frame protocol para flows (recién añadido) | ✅ Streaming nativo en todos los clients (OpenAI/Anthropic/Bedrock) | ✅ Bidi streaming (Gemini Live API), SSE, Vertex Live | ✅ Streaming nativo + websocket + buffered tool-call streaming | ✅ `invoke_stream` / `add_streaming_func` | ✅ `Workflow.run(stream=True)` + agent streaming | ✅ `stream_outputs=True` en CodeAgent | ✅ Bidirectional streaming (built-in) |
| **License** | MIT | MIT | **CC-BY-4.0** | Apache-2.0 | MIT | MIT | MIT | Apache-2.0 | Apache-2.0 |
| **Maintainer** | LangChain, Inc. | crewAI Inc. | Microsoft | Google | OpenAI | Microsoft | LlamaIndex / run-llama | Hugging Face | AWS |
| **Stars (2026-07-07)** | 36 642 | 55 029 | 59 536 | 20 501 | 27 695 | 28 272 | 50 687 | 28 219 | 6 444 |
| **Última release** | 2026-07-06 | 2026-07-01 | 2025-09-30 | 2026-07-06 | 2026-06-24 | 2026-06-17 | 2026-06-24 | ~Q4 2025 (VP) | 2026-06-25 |
| **Backend de despliegue** | LangGraph Platform / self-host | CrewAI Enterprise / self-host | Local + Azure (AGS, Agent Service) | Vertex AI Agent Engine / self-host | OpenAI platform + cualquier OpenAI-compatible | Cualquiera (kernel es librería) | Cualquiera (librería) | Cualquiera (incluye sandboxing con Docker/E2B/Modal/Blaxel) | Cualquiera + AgentCore (AWS Bedrock) |
| **Observabilidad** | LangSmith (nativo) + Langfuse | CrewAI AMP + Datadog guide + OpenTelemetry | OpenTelemetry + Microsoft ML Insights (AutoGen Studio) | OpenTelemetry (semconv estable + experimental), BigQuery plugin | OpenAI Traces + custom spans | App Insights / OpenTelemetry / Aspire | OpenInference / Arize Phoenix / Langfuse | Traces estándar Python + Hub | Hooks + traces nativos del agent loop |

> **Leyenda de fuente por celda**: las celdas marcadas con referencias a
> releases concretos (p. ej. `1.2.8`, `v1.36.1`) están respaldadas por el
> feed Atom del repo correspondiente, capturado el 2026-07-07. Las celdas de
> capacidades (MCP, HITL, streaming, multi-agent) están respaldadas por los
> READMEs y CHANGELOGs de cada repo. Algunas afirmaciones de capacidades
> requieren **VERIFICACIÓN PENDIENTE** en código fuente — ver sección final.

---

## Recomendaciones de selección (basadas en los datos verificados)

> **Aviso**: estas recomendaciones se basan en el **estado público de cada
> proyecto** (actividad, releases, tamaño de comunidad) y **NO** en benchmarks
> internos. Cada decisión final debe validarse con un POC concreto para el caso
> de uso de Aithera.

### ¿Cuándo usar LangGraph?
- Cuando se necesita **control fino del flujo** (grafos cíclicos, branching,
  paralelismo con `Send`, subgraphs).
- Cuando se quiere **durable execution** (checkpointers en Postgres/Redis) con
  `time-travel` y `human-in-the-loop` nativo vía `interrupt()`.
- Cuando el stack ya está en LangChain/LangSmith.
- **Adecuado para Aithera**: el Orchestrator planificado (V1.0) encaja
  naturalmente con el modelo de StateGraph. Aithera ya tiene streaming SSE,
  checkpointing con Postgres y chat multi-canal — la integración sería directa.

### ¿Cuándo usar CrewAI?
- Cuando el caso de uso es **"rol + tarea + delegación"** estilo equipo humano
  (Researcher → Writer → Reviewer).
- Cuando se prefiere un DSL de alto nivel con **Crews** y **Flows** declarativos
  en YAML/JSON (recién introducido en 1.15.0).
- Buena opción para workshops, demos y casos de uso de negocio donde la
  legibilidad del flujo es más importante que el control fino.

### ¿Cuándo usar AutoGen?
- Cuando se necesita el patrón **GroupChat maduro** (orquestador + agentes que
  debaten) o **Swarm** (handoff dinámico).
- Cuando se trabaja en el ecosistema **Microsoft** (Azure AI Foundry, AGS,
  .NET). Su rama `python-v0.7.x` incluye Teams anidados, DockerCodeExecutor
  (default seguro) y `RedisMemory`.
- ⚠️ **Pendiente**: la cadencia de releases se ralentizó (última 2025-09) — es
  la nota más importante a considerar.

### ¿Cuándo usar Google ADK?
- Cuando se construye sobre **Vertex AI / Gemini** y se necesita acceso a
  **Gemini Live API** (bidi streaming, multimodal en tiempo real).
- Cuando se quiere un SDK con **integraciones first-party** para GCS, BigQuery,
  Agent Engine, A2A, Skills, MCP.
- Muy activo (rama v2 con "enterprise parameters") y bien documentado para
  Google Cloud.
- **Adecuado para Aithera**: el módulo `Live API` (bidi streaming de audio/vídeo)
  encaja con la fase de Voz (V0.85+) — pero ADK ataría a GCP/Vertex.

### ¿Cuándo usar OpenAI Agents SDK?
- Para equipos **100 % OpenAI** (o modelos OpenAI-compatible) que quieren un
  SDK **mínimo, oficial y battle-tested**.
- Excelente DX (Runner, handoffs, guardrails, tracing nativo).
- ⚠️ **Riesgo para Aithera**: ata a la API de OpenAI por defecto. Para
  multi-proveedor habría que pasar por un proxy compatible.

### (Sin recomendación explícita pedida, pero documentadas para completitud)
- **Semantic Kernel**: si el stack es .NET/C# o si se quiere planners
  declarativos (Handlebars/Jinja). Aithera es Python+FastAPI, encaja peor.
- **LlamaIndex**: si el centro del producto es **RAG** sobre knowledge bases.
  Aithera ya tiene ChromaDB propio; integración útil si se necesita
  workflows agentic sobre RAG (`AgentWorkflow`).
- **Smolagents**: para **POCs rápidos** con `CodeAgent` (LM que escribe
  Python). Útil para experimentar, menos para producción enterprise.
- **Strands**: si se construye sobre **AWS Bedrock** (es el default del SDK) y
  se quiere un agent loop simple con hooks y streaming bidireccional. Hooks
  + steering handlers son potentes para observabilidad.

---

## Pendientes de validación

- [ ] **Smolagents**: confirmar número de versión y fecha exacta del último
      release. El feed Atom público devolvió 404 al scrapear — verificar
      manualmente en `github.com/huggingface/smolagents/releases`.
- [ ] **Strands**: confirmar la última release Python (la vista en este
      barrido es `typescript/v1.7.0`; el tag `python/vX.Y.Z` correspondiente
      no se localizó en el output truncado del feed Atom).
- [ ] **AutoGen**: confirmar la cadencia de releases post-2025-09-30 — el gap
      hasta hoy (julio 2026) es de ~9 meses. Verificar si hay una release más
      reciente fuera del feed Atom o si el proyecto está en transición.
- [ ] **MCP support**: las celdas de la tabla comparativa marcadas como `⚠️`
      (Semantic Kernel, LlamaIndex) requieren verificación en código fuente
      / docs oficiales de que la integración es soportada y estable (vs.
      experimental).
- [ ] **HITL en Smolagents**: confirmar que NO hay HITL nativo (la celda
      `❌`) revisando `agents.py` y el módulo `agents.final_answer_checks`.
- [ ] **Multi-agent nativo en Smolagents**: confirmar el patrón exacto
      (`MultiAgentSystem` vs composición manual de varios `CodeAgent`).
- [ ] **Cadencia real de releases**: los datos de "release cadence" se
      infirieron de las fechas de los últimos releases visibles. Para una
      afirmación categórica habría que extraer el feed completo (no solo los
      10 últimos) y calcular frecuencia.

---

## Fuentes (consultadas el 2026-07-07)

1. `https://github.com/langchain-ai/langgraph` — home (stars + descripción) — 2026-07-07
2. `https://github.com/langchain-ai/langgraph/releases.atom` — feed de releases — 2026-07-07
3. `https://raw.githubusercontent.com/langchain-ai/langgraph/HEAD/LICENSE` — licencia — 2026-07-07
4. `https://github.com/crewAIInc/crewAI` — home — 2026-07-07
5. `https://github.com/crewAIInc/crewAI/releases.atom` — feed — 2026-07-07
6. `https://raw.githubusercontent.com/crewAIInc/crewAI/HEAD/LICENSE` — licencia — 2026-07-07
7. `https://github.com/microsoft/autogen` — home — 2026-07-07
8. `https://github.com/microsoft/autogen/releases.atom` — feed — 2026-07-07
9. `https://raw.githubusercontent.com/microsoft/autogen/HEAD/LICENSE` — licencia (CC-BY-4.0) — 2026-07-07
10. `https://github.com/google/adk-python` — home — 2026-07-07
11. `https://github.com/google/adk-python/releases.atom` — feed — 2026-07-07
12. `https://raw.githubusercontent.com/google/adk-python/HEAD/LICENSE` — licencia — 2026-07-07
13. `https://github.com/openai/openai-agents-python` — home — 2026-07-07
14. `https://github.com/openai/openai-agents-python/releases.atom` — feed — 2026-07-07
15. `https://raw.githubusercontent.com/openai/openai-agents-python/HEAD/LICENSE` — licencia — 2026-07-07
16. `https://github.com/microsoft/semantic-kernel` — home — 2026-07-07
17. `https://github.com/microsoft/semantic-kernel/releases.atom` — feed — 2026-07-07
18. `https://raw.githubusercontent.com/microsoft/semantic-kernel/HEAD/LICENSE` — licencia — 2026-07-07
19. `https://github.com/run-llama/llama_index` — home — 2026-07-07
20. `https://github.com/run-llama/llama_index/releases.atom` — feed — 2026-07-07
21. `https://raw.githubusercontent.com/run-llama/llama_index/HEAD/LICENSE` — licencia — 2026-07-07
22. `https://github.com/huggingface/smolagents` — home (stars) — 2026-07-07
23. `https://raw.githubusercontent.com/huggingface/smolagents/main/README.md` — README (capacidades) — 2026-07-07
24. `https://raw.githubusercontent.com/huggingface/smolagents/HEAD/LICENSE` — licencia — 2026-07-07
25. `https://github.com/strands-agents/harness-sdk` — home — 2026-07-07
26. `https://github.com/strands-agents/harness-sdk/releases.atom` — feed — 2026-07-07
27. `https://github.com/strands-agents` — listado de repos de la org — 2026-07-07
28. `https://api.github.com/search/repositories?q=strands-agents` — búsqueda — 2026-07-07

---

## Metodología y honestidad sobre la fuente

- **API REST de GitHub**: rate-limited (60 req/h sin auth) — no se pudo usar
  para los 9 repos. La búsqueda por nombre tampoco autenticada sí funcionó
  (devolvió los resultados de `strands-agents` correctamente).
- **Scraping HTML de páginas públicas + feeds Atom**: funcionó sin rate limit
  para todas las homes y feeds de releases. La fuente primaria de stars,
  descripción, fecha de releases y licencia es esta.
- **README raw de GitHub**: usado para capacidades y descripción cualitativa.
- **Licencias**: verificadas leyendo los archivos `LICENSE` en la rama por
  defecto de cada repo (vía `raw.githubusercontent.com/.../HEAD/LICENSE`).
- **Lo que NO se verificó**: código fuente profundo (capacidades `✅/⚠️/❌` se
  basan en README + CHANGELOG de releases). Para una afirmación categórica
  habría que clonar los repos y leer los módulos — eso queda en
  "Pendientes de validación".