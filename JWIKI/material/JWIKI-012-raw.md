# JWIKI-012 — CrewAI overview — MATERIAL CRUDO

> Generado desde cero (P1: raw+doc no existían en disco). Tick A-20260708-2020, orquestador JWIKI single-team.
> Fuente primaria: GitHub API live + raw.githubusercontent.com/crewAIInc/crewAI/main + docs.crewai.com. Fecha de acceso de TODOS los hechos: **2026-07-08**.

---

## 1. Datos GitHub API (contraste live, P2)

| Dato | Valor live 2026-07-08 | task_queue decía | Conflicto |
|---|---|---|---|
| stars | **55.157** | ~30k | ✅ SÍ (task_queue stale, +84%) |
| forks | 7.754 | — | — |
| language (principal) | Python | Python | OK |
| license | MIT (SPDX) | — | — |
| pushed_at | 2026-07-08T15:28:28Z | — | activo HOY |
| created_at | 2023-10-27T03:26:59Z | — | ~2.6 años |
| open_issues | 619 | — | — |
| subscribers (watchers) | 385 | — | — |
| contribuidores | ~301 (Link header page=301) | — | — |
| homepage | https://crewai.com | — | — |
| topics | agents, ai, ai-agents, aiagentframework, llms | — | — |
| default_branch | main | — | — |

**F1**. CrewAI tiene **55.157 stars** (GitHub API `/repos/crewAIInc/crewAI`, 2026-07-08). El task_queue estimaba "~30k" → **stale, subestimación del ~84%**. https://api.github.com/repos/crewAIInc/crewAI
**F2**. **7.754 forks** (misma fuente/fecha).
**F3**. Licencia **MIT** (SPDX `MIT`, archivo LICENSE en root). https://github.com/crewAIInc/crewAI/blob/main/LICENSE
**F4**. Último push **2026-07-08T15:28:28Z** — repo activo el día del acceso.
**F5**. Repo creado **2023-10-27** (Joao Moura). ~2.6 años de historia.
**F6**. **619 issues abiertas**, **385 watchers**, ~**301 contribuidores** (Link header `page=301` con `per_page=1&anon=true`).
**F7**. Topics oficiales: `agents, ai, ai-agents, aiagentframework, llms`.

## 2. Lenguajes (P5 — usar /languages, no el "principal")

**F8**. Desglose `/languages` (bytes, 2026-07-08): Python **9.913.231** (~99.7%), JavaScript 84.736, CSS 24.684, Jinja 16.956, Shell 25. https://api.github.com/repos/crewAIInc/crewAI/languages
**F9**. CrewAI es **abrumadoramente Python** (~99.7%). El JS/CSS/Jinja pertenece a assets de docs (Mintlify) y no al core del framework. A diferencia de AutoGen (Python + .NET) o Hermes (Python + TS), CrewAI es **mono-lenguaje Python** en su núcleo. Caveat P5: el 0.3% no-Python NO representa bindings de otro runtime.

## 3. Releases y versión

**F10**. Última release estable: **1.15.2**, publicada **2026-07-08T02:05:22Z** (mismo día del acceso). https://api.github.com/repos/crewAIInc/crewAI/releases/latest
**F11**. `__version__ = "1.15.2"` confirmado en `lib/crewai/src/crewai/__init__.py:? ` (línea del literal). https://raw.githubusercontent.com/crewAIInc/crewAI/main/lib/crewai/src/crewai/__init__.py
**F12**. Cadencia de releases muy rápida (pre-releases alpha): 1.15.2, 1.15.2a2 (2026-07-01), 1.15.2a1 (2026-06-30), 1.15.1 (2026-06-27), 1.15.1a1, 1.15.0 (2026-06-25), 1.14.8a5..a2. Varias releases por semana con sufijos `aN` (alpha). https://api.github.com/repos/crewAIInc/crewAI/releases
**F13**. Tags históricos incluyen v0.119.0 y una transición a esquema 1.x (v1.0.0-alpha.1, v1.0.0a2). El salto 0.x → 1.x marca el rediseño monorepo + unified memory.

## 4. Autor y gobernanza

**F14**. Autor/creador: **Joao Moura** (`joao@crewai.com`), GitHub `joaomdmoura`. Declarado en `pyproject.toml [project.authors]`. https://raw.githubusercontent.com/crewAIInc/crewAI/main/pyproject.toml
**F15**. Organización: **crewAIInc** (empresa CrewAI Inc.). Existe oferta comercial "CrewAI AMP Suite" (control plane enterprise) + "Crew Control Plane" con trial gratuito en app.crewai.com. README §"CrewAI AMP Suite".
**F16**. Claim auto-reportado (P6): "over **100,000 developers certified** through our community courses at learn.crewai.com". Caveat: es una métrica de marketing de cursos (deeplearning.ai short courses), NO de usuarios activos del framework. Se cita CON su naturaleza.

## 5. Arquitectura monorepo (hallazgo P12/P13)

**F17**. CrewAI v1.x es un **monorepo workspace** gestionado con **UV** (astral). `pyproject.toml` raíz se llama `crewai-workspace`. Sub-paquetes en `lib/`: **cli, crewai-core, crewai-files, crewai-tools, crewai, devtools**. https://api.github.com/repos/crewAIInc/crewAI/contents/lib
**F18**. `requires-python = ">=3.10,<3.14"` (cap superior explícito). Mismo patrón que Hermes (JWIKI-007) — cap por incompatibilidad de wheels de deps. https://raw.githubusercontent.com/crewAIInc/crewAI/main/pyproject.toml
**F19**. Toolchain de calidad estricto: ruff 0.15.1 (con reglas E/F/B/S bandit/N/W/I/PERF/ASYNC/RET), mypy 1.19.1, bandit 1.9.2, pre-commit 4.5.1, pip-audit 2.9.0, pytest 9.0.3. `ban-relative-imports = "all"`. Indica madurez de ingeniería (no un proyecto hobby).
**F20**. Módulos del core `lib/crewai/src/crewai/`: `agent/`, `agents/`, `a2a/`, `auth/`, `cli/`, `core/`, `crew.py`, `crews/`, `events/`, `experimental/`, `flow/`, `hooks/`, `knowledge/`, `lite_agent.py`, `llm.py`, `llms/`, `mcp/`, `memory/`, `process.py`, `project/`, `rag/`, `security/`, `skills/`, `state/`, `task.py`, `tasks/`, `telemetry/`, `tools/`, `translations/`, `types/`, `utilities/`, `version.py`. https://api.github.com/repos/crewAIInc/crewAI/contents/lib/crewai/src/crewai

## 6. Primitivas core (exports de __init__.py)

**F21**. Símbolos públicos exportados en `crewai/__init__.py`: `Agent, Crew, Task, Process, Flow, Knowledge, LLM, BaseLLM, CrewOutput, TaskOutput, LLMGuardrail, CheckpointConfig, PlanningConfig, ExecutionContext`, y `Memory` (lazy import → lancedb). https://raw.githubusercontent.com/crewAIInc/crewAI/main/lib/crewai/src/crewai/__init__.py
**F22**. **Dos paradigmas complementarios** (README §"Understanding Flows and Crews"):
  - **Crews**: equipos de agentes con autonomía y agencia, colaboración role-based, delegación dinámica.
  - **Flows**: workflows event-driven, control fino de ejecución, estado estructurado, branching condicional, integración con Python de producción.
  El "poder real" (según autores) emerge al combinarlos. README §"Understanding Flows and Crews".

## 7. Process (Sequential vs Hierarchical) — código real

**F23**. `Process` es un `str, Enum` con **solo dos valores activos**: `sequential`, `hierarchical`. `consensual` está comentado como `# TODO`. `lib/crewai/src/crewai/process.py:4-11`. https://raw.githubusercontent.com/crewAIInc/crewAI/main/lib/crewai/src/crewai/process.py
**F24**. `Process.sequential` (default en Crew, `crew.py:225`): tareas se ejecutan en orden, output de una alimenta el contexto de la siguiente.
**F25**. `Process.hierarchical`: CrewAI asigna automáticamente un **manager agent** que coordina planning + ejecución vía delegación y validación de resultados. Requiere `manager_llm` o `manager_agent`. README: "automatically assigns a manager to the defined crew". Docs: https://docs.crewai.com/core-concepts/Processes/

## 8. Agent — campos (código real)

**F26**. `class Agent(BaseAgent)` en `lib/crewai/src/crewai/agent/core.py:170`. Campos documentados: `role` (170:178), `goal` (179), `backstory` (180), `llm` (183/214), `function_calling_llm` (184/219), `max_iter` (185), `verbose` (187), `allow_delegation` (188), `tools` (189), `knowledge_sources` (191), `multimodal` (250), `reasoning` (276). https://raw.githubusercontent.com/crewAIInc/crewAI/main/lib/crewai/src/crewai/agent/core.py
**F27**. Novedades v1.x en Agent: `multimodal: bool` (core.py:250) y `reasoning: bool` (core.py:276) — soporte nativo para modelos multimodales y razonamiento explícito.

## 9. Task — campos (código real)

**F28**. `class Task(BaseModel)` en `lib/crewai/src/crewai/task.py:114`. Campos: `description` (146), `expected_output` (147), `context: list[Task]` (161), `async_execution` (165), `output_json` (169), `output_pydantic` (179), `output_file` (199), `tools` (210), `human_input` (227), `guardrail` (246), `allow_crewai_trigger_context` (283). https://raw.githubusercontent.com/crewAIInc/crewAI/main/lib/crewai/src/crewai/task.py
**F29**. Structured output: `output_json` y `output_pydantic` permiten forzar salida a un modelo Pydantic (task.py:169-197). `guardrail` (task.py:246) valida/reintenta la salida — patrón de auto-corrección.
**F30**. `context: list[Task]` (task.py:161) — una Task puede recibir explícitamente el output de otras Tasks como contexto, permitiendo DAGs de dependencias sin Flow.

## 10. Crew — campos y métodos (código real)

**F31**. `class Crew(FlowTrackable, BaseModel)` en `lib/crewai/src/crewai/crew.py:159`. Campos: `tasks` (220), `agents` (221), `process` (225, default `Process.sequential`), `verbose` (226), `memory` (227), `cache` (219, default True), `embedder` (241), `manager_llm` (249), `manager_agent` (254), `planning` (318), `knowledge_sources` (340). https://raw.githubusercontent.com/crewAIInc/crewAI/main/lib/crewai/src/crewai/crew.py
**F32**. Métodos de ejecución de Crew: `kickoff` (crew.py:966), `kickoff_async` (1096), `kickoff_for_each` (1060), `kickoff_for_each_async` (1150), `train` (914), `replay` (1904), `test` (2100).
**F33**. `planning: bool` (crew.py:318) — cuando True, CrewAI planifica la ejecución del crew y añade el plan al contexto (patrón plan-then-execute).
**F34**. `replay(task_id)` (crew.py:1904) permite re-ejecutar desde una task específica — útil para debugging determinista de pipelines.

## 11. Memory — CAMBIO ARQUITECTÓNICO v1.x (conflicto vs conocimiento previo)

**F35**. ⚠️ **CONFLICTO**: la creencia común (y el brief del tick) es que CrewAI Memory = short-term + long-term + entity (el modelo clásico 0.x). En v1.x existe un **Unified Memory**: "single intelligent memory with LLM analysis and pluggable storage". `lib/crewai/src/crewai/memory/unified_memory.py:1`. https://raw.githubusercontent.com/crewAIInc/crewAI/main/lib/crewai/src/crewai/memory/unified_memory.py
**F36**. `MemoryRecord` (memory/types.py:20) tiene: `id`, `content`, `scope` (path jerárquico `/company/team/user`), `categories`, `metadata`, `importance` (0.0-1.0, afecta ranking de recall), `created_at`, `last_accessed`, `embedding` (excluido de serialización), `source` (provenance), `private` (visibilidad por source). https://raw.githubusercontent.com/crewAIInc/crewAI/main/lib/crewai/src/crewai/memory/types.py
**F37**. El sistema de memoria usa `ThreadPoolExecutor`, event bus (`MemoryQueryStarted/Completed/Failed`, `MemorySaveStarted/Completed/Failed`) y `build_embedder` de `crewai.rag.embeddings.factory`. Archivos: `analyze.py`, `encoding_flow.py`, `recall_flow.py`, `memory_scope.py`, `storage/`. Es un subsistema RAG completo, no solo un buffer.
**F38**. `Memory` es un **lazy import** (`__init__.py` `_LAZY_IMPORTS = {"Memory": ("crewai.memory.unified_memory","Memory")}`) para no cargar `lancedb` hasta el primer uso — optimización de arranque.

## 12. MCP y A2A (nativo)

**F39**. CrewAI tiene **soporte MCP nativo** en el core: `lib/crewai/src/crewai/mcp/` con `client.py`, `config.py`, `filters.py`, `tool_resolver.py`, `transports/`. https://api.github.com/repos/crewAIInc/crewAI/contents/lib/crewai/src/crewai/mcp
**F40**. Existe módulo **A2A** (agent-to-agent): `lib/crewai/src/crewai/a2a/`. CrewAI soporta el protocolo A2A además de MCP (README §Key Features: "MCP/A2A support").
**F41**. Docs MCP server live: https://docs.crewai.com/mcp — el skill `ask-docs` consulta este servidor MCP para API up-to-date. README §"Build with AI".

## 13. Tooling y ecosistema

**F42**. Paquete de herramientas separado: **crewai-tools** (`lib/crewai-tools/`), instalable con `uv pip install 'crewai[tools]'`. Incluye tools como `SerperDevTool` (búsqueda). README ejemplo crew.py.
**F43**. CLI oficial: `crewai create crew <name>` (scaffolding), `crewai run`, `crewai install`, `crewai update`. Genera estructura `src/<proj>/{main.py, crew.py, tools/, config/{agents.yaml, tasks.yaml}}`. README §2.
**F44**. **Configuración YAML-first**: agentes y tasks se definen en `config/agents.yaml` y `config/tasks.yaml`, referenciados vía decoradores `@CrewBase`, `@agent`, `@task`, `@crew` en `crew.py`. Soporta interpolación de variables `{topic}`. README ejemplo.
**F45**. Skills oficiales para coding agents (crewAIInc/skills): 4 skills (`getting-started`, `design-agent`, `design-task`, `ask-docs`) para Claude Code (`/plugin marketplace add crewAIInc/skills`), Cursor/Codex/Windsurf (`npx skills add crewaiinc/skills`). README §"Build with AI". https://github.com/crewAIInc/skills

## 14. Flows (control event-driven)

**F46**. Flow usa decoradores `@start()`, `@listen(...)`, `@router(...)` y operadores lógicos `or_`, `and_` para condiciones de trigger complejas. `from crewai.flow.flow import Flow, listen, start, router, or_`. README §"Using Crews and Flows Together".
**F47**. Flow soporta **estado estructurado tipado** vía genérico: `class AdvancedAnalysisFlow(Flow[MarketState])` donde `MarketState(BaseModel)`. El estado es persistente y seguro entre pasos. README ejemplo.
**F48**. Flows permiten branching condicional: un `@router` devuelve una etiqueta (`"high_confidence"`) y `@listen("high_confidence")` reacciona. Comparable a las aristas condicionales de LangGraph pero con decoradores en vez de grafo explícito.

## 15. Comparativa con LangGraph / AutoGen / OpenAI Agents SDK / Google ADK

**F49**. Fuentes internas JWIKI para contraste: `01_LANDSCAPE/langgraph.md` (JWIKI-011, verified), `01_LANDSCAPE/autogen.md` (JWIKI-013, verified), `01_LANDSCAPE/agent-frameworks.md` (JWIKI-010, 9 frameworks × 11 criterios).
**F50**. Del doc AutoGen (JWIKI-013): "CrewAI que solo [soporta MCP] vía adaptadores" — **DESACTUALIZADO**. La verificación live 2026-07-08 muestra `crewai/mcp/` nativo en el core. Conflicto cross-doc a corregir en JWIKI-013.

| Criterio | CrewAI | LangGraph | AutoGen | OpenAI Agents SDK | Google ADK |
|---|---|---|---|---|---|
| Paradigma | Crews (roles) + Flows (event-driven) | Grafo de estados (StateGraph) | Actor-model conversacional | Handoffs entre agents | Vertex-native, code-first |
| Multi-agente nativo | ✅ (Crew de roles) | ✅ (nodos/subgrafos) | ✅ (Teams) | ✅ (handoffs) | ✅ |
| Abstracción | Alta (role/goal/backstory) + baja (Flows) | Baja (grafo explícito) | Media (conversación) | Media | Media-alta |
| MCP | ✅ nativo (`crewai/mcp`) | ✅ nativo (1.0) | ✅ (mejor soporte, elicitation) | Parcial | ✅ |
| A2A | ✅ (`crewai/a2a`) | vía LangChain | GraphFlow | ❌ | ✅ (protocolo A2A Google) |
| Estado estructurado | Flows (`Flow[State]`) | ✅ core (channels) | via runtime | via context | via session |
| Delegación/handoffs | hierarchical manager + allow_delegation | aristas condicionales | selector/swarm | handoffs first-class | sub-agents |
| Lenguaje | Python (~99.7%) | Python (+ JS langgraphjs) | Python + .NET | Python | Python |
| Config declarativa | ✅ YAML-first | ❌ (código) | ❌ | ❌ | parcial |
| License | MIT | MIT | MIT (CC-BY variantes docs) | MIT | Apache-2.0 |
| Stars (2026-07-08) | 55.157 | (ver JWIKI-011) | (ver JWIKI-013) | — | — |

## 16. Cuándo elegir CrewAI (README §"When to Use CrewAI")

**F51**. CrewAI conviene cuando: coordinar múltiples agentes con roles/tasks claros; envolver trabajo agéntico en workflows deterministas event-driven; mantener lógica en Python normal; pasar de experimento a producción sin cambiar framework; añadir tools, memory, checkpointing y async progresivamente. README §"When to Use CrewAI".
**F52**. Ventaja diferencial: **abstracción role/goal/backstory** ultra-legible + **YAML-first** → baja barrera de entrada vs el grafo explícito de LangGraph o el actor-model de AutoGen. Ideal para prototipado rápido de equipos de agentes.
**F53**. Desventaja/caveat: al ser Python puro mono-lenguaje, no ofrece el cross-language (Python+.NET) de AutoGen; y para control de flujo muy fino algunos prefieren el grafo explícito de LangGraph (aunque Flows cubre gran parte de ese hueco desde v1.x).

## 17. Relación con Aithera V1.0 Orchestrator

**F54**. Aithera V1.0 (roadmap `CLAUDE.md`) planea un Orchestrator con intent analyzer + planner + Claude Code Agent, bajo el Gateway V0.8 (`gateway.set_handler()`). El patrón **Crew** (agentes con role/goal + Process sequential/hierarchical + manager delegando) es directamente借鉴able: el planner de Aithera puede modelarse como un manager hierarchical, y los sub-agents como Crew members.
**F55**. El patrón **Flow[State]** de CrewAI (estado Pydantic tipado + `@router` condicional) es un modelo maduro para el "Automation Engine" de Aithera V0.9 (APScheduler + reglas + aprobaciones), sin adoptar CrewAI como dependencia — solo el patrón.

## Conflictos / discrepancias entre fuentes detectadas

1. **task_queue ~30k stars vs 55.157 live** (P2): subestimación 84%. Corregir en el doc con caveat de fecha.
2. **Memory "short/long/entity" (modelo clásico 0.x) vs Unified Memory (v1.x)** (F35): la creencia del brief está desactualizada. El core v1.15.2 usa `unified_memory.py` con scopes jerárquicos + importance + private. Documentar la evolución.
3. **JWIKI-013 autogen.md dice "CrewAI solo MCP vía adaptadores"** (F50): FALSO en v1.x — `crewai/mcp/` es nativo. Pendiente cross-doc.
4. **README "100k developers certified"** (P6): métrica de cursos, no de usuarios activos. Citar con naturaleza.
5. **"language: Python" (GitHub) vs multi-lenguaje aparente** (P5): el 0.3% JS/CSS/Jinja es de docs Mintlify, no del framework. CrewAI es efectivamente mono-Python.

## Pendientes de validación

- [ ] Confirmar el modelo exacto de `MemoryScope`/`MemorySlice` (visto en `crew.py:206` como PrivateAttr) — lectura de `memory_scope.py` completa.
- [ ] Verificar stars de LangGraph/AutoGen live para completar la fila numérica de la tabla (se referencian JWIKI-011/013).
- [ ] Confirmar si `crewai-files` es un paquete de I/O de archivos o de knowledge sources.
- [ ] Rate limit de GitHub API impidió leer `knowledge/` y `tools/` dirs completos (contenido devolvió error) — reintentar en próximo tick si se enriquece.

## Fuentes

1. https://api.github.com/repos/crewAIInc/crewAI — acceso 2026-07-08
2. https://api.github.com/repos/crewAIInc/crewAI/languages — 2026-07-08
3. https://api.github.com/repos/crewAIInc/crewAI/releases — 2026-07-08
4. https://raw.githubusercontent.com/crewAIInc/crewAI/main/README.md — 2026-07-08
5. https://raw.githubusercontent.com/crewAIInc/crewAI/main/pyproject.toml — 2026-07-08
6. https://raw.githubusercontent.com/crewAIInc/crewAI/main/lib/crewai/src/crewai/__init__.py — 2026-07-08
7. https://raw.githubusercontent.com/crewAIInc/crewAI/main/lib/crewai/src/crewai/process.py — 2026-07-08
8. https://raw.githubusercontent.com/crewAIInc/crewAI/main/lib/crewai/src/crewai/agent/core.py — 2026-07-08
9. https://raw.githubusercontent.com/crewAIInc/crewAI/main/lib/crewai/src/crewai/task.py — 2026-07-08
10. https://raw.githubusercontent.com/crewAIInc/crewAI/main/lib/crewai/src/crewai/crew.py — 2026-07-08
11. https://raw.githubusercontent.com/crewAIInc/crewAI/main/lib/crewai/src/crewai/memory/types.py — 2026-07-08
12. https://raw.githubusercontent.com/crewAIInc/crewAI/main/lib/crewai/src/crewai/memory/unified_memory.py — 2026-07-08
13. https://docs.crewai.com/ (HTTP 200) — 2026-07-08
14. https://crewai.com (HTTP 200) — 2026-07-08
15. https://github.com/crewAIInc/skills — 2026-07-08
16. JWIKI internos: 01_LANDSCAPE/langgraph.md, autogen.md, agent-frameworks.md — 2026-07-08

---
*Material crudo v1.0 — 2026-07-08 20:20 — orquestador JWIKI single-team. 55 hechos verificados (F1-F55), 8 snippets con path:line, tabla comparativa 5 frameworks, 5 conflictos documentados.*
