# OpenAI Agents SDK — Correcciones a aplicar a `01_LANDSCAPE/openai-agents-sdk.md`

> **Material crudo generado por tick A-20260713. Invocación siguiente:
> `aithera-jwiki-audit` consume este doc + `openai-agents-sdk-code-audit.md`
> + `openai-agents-sdk-architecture.md` para regenerar el doc preexistente
> con las correcciones aplicadas.**

## Resumen

**44 divergencias detectadas** entre el doc preexistente `01_LANDSCAPE/openai-agents-sdk.md`
(tick A-20260708-2040) y el código real del repo (`openai/openai-agents-python`
clonado 2026-07-13, `version = 0.18.2`).

- **UPDATE**: ~30 (afirmaciones parcialmente correctas o incompletas)
- **CORRECT**: 1 (errores factuales)
- **KEEP**: ~13 (ya correctas)
- **NEUTRAL**: ~2 (verificables pero no en este audit)

## Lista accionable (orden de impacto)

### Alta prioridad — actualiza o contradice

1. **Versión en doc preexistente**: `v0.18.0` → debe ser **`v0.18.2`**.
   Fuente: `pyproject.toml:3` y `src/agents/version.py:5`.

2. **`Runner` NO es dataclass**. Reescribir sección `#### Runner (src/agents/run.py)`:
   ```python
   # Real: src/agents/run.py:198 — clase regular con @classmethod
   class Runner:
       @classmethod
       async def run(cls, ...): ...
       @classmethod
       def run_sync(cls, ...): ...
       @classmethod
       def run_streamed(cls, ...): ...
   ```
   Las tres delegan a `DEFAULT_AGENT_RUNNER` (un singleton `AgentRunner`,
   `src/agents/run.py:128-167`), marcado experimental.

3. **RunConfig.default_models**: enfatizar que el default es `gpt-5.4-mini`
   (correcto en doc preexistente) PERO aclarar que las **variantes
   `gpt-5.4-pro`, `gpt-5.4-nano`, `gpt-5.5`, `gpt-5.6-*` también existen**
   con patterns matching ya en código
   (`models/default_models.py:50-69`).

4. **Tool guardrails son 3-way, no binarios**. Documentar:
   - `allow` → tool ejecuta normal.
   - `reject_content(message)` → tool NO ejecuta, modelo recibe `message`
     y continúa (no raise).
   - `raise_exception` → raise `ToolInputGuardrailTripwireTriggered`
     (halt).
   Fuente: `src/agents/tool_guardrails.py:40-117`.

5. **`needs_approval` interrupt pattern** — NUEVO, no documentado:
   ```python
   @function_tool(needs_approval=True)
   def exec(cmd: str) -> str: ...
   ```
   El run se interrumpe, `result.interruptions` lista pending approvals,
   caller llama `RunState.approve(call_id)` o `RunState.reject(call_id)`
   para continuar. Fuente: `src/agents/tool.py:426-433`.

6. **`MultiProvider` `openai_prefix_mode` y `unknown_prefix_mode`** —
   nuevos knobs, no mencionados:
   - `openai_prefix_mode="alias"` (default) strip `"openai/"`
   - `openai_prefix_mode="model_id"` para endpoints OpenAI-compatible
     (vLLM) que esperan IDs namespaceados.
   - `unknown_prefix_mode="error"` (default) raise UserError.
   - `unknown_prefix_mode="model_id"` para OpenRouter-style.
   Fuente: `src/agents/models/multi_provider.py:75-187`.

7. **13 tipos de SpanData** (no 12). Añadir `MCPListToolsSpanData` a la
   lista. Fuente: `src/agents/tracing/span_data.py:427`.

### Media prioridad — completar

8. **`nest_handoff_history=False` por default** (opt-in beta), enfatizar
   en sección Handoffs. Fuente: `src/agents/run_config.py:236-249`.

9. **`SandboxAgent` extiende `Agent` (no `AgentBase`)** — asimetría
   respecto a `RealtimeAgent`. Documentar.

10. **MCP class hierarchy**: `MCPServerStdio`, `MCPServerSse`,
    `MCPServerStreamableHttp` — los 3 transports. Lazy imports vía
    `mcp/__init__.py:32-42`. Documentar.

11. **`ToolSearchTool`** (no en doc preexistente). Mecanismo tool-search
    del Responses API; combina con `FunctionTool(defer_loading=True)`.
    Fuente: `src/agents/__init__.py:190`.

12. **Realtime NO soporta `input_guardrails`** — explícito en el código
    (`realtime/agent.py:30-39`), no en doc preexistente.

13. **`MCPServerManager`** para evitar connect/cleanup manuales
    (`mcp/manager.py`, 411 LOC). Documentar.

14. **`SandboxRunConfig` agrupa `concurrency_limits` y `archive_limits`**
    con defaults generosos (1 GB input, 4 GB extracted, 100k members).
    Riesgo de seguridad en producción. Fuente:
    `src/agents/run_config.py:33-38` + `:178-208`.

15. **`OpenAIAgentRegistrationConfig` + env `OPENAI_AGENT_HARNESS_ID`** —
    para OpenAI telemetry/cross-team tracking.

16. **`set_default_openai_responses_transport("websocket")`** switch a
    WebSocket transport. `OpenAIResponsesWSModel`. Fuente:
    `src/agents/__init__.py:305-311`.

17. **`OpenAIResponsesCompactionAwareSession`** + TypeGuard
    `is_openai_responses_compaction_aware_session()`. Fuente:
    `src/agents/memory/session.py:131-150`.

18. **Custom data extractor en tools**: `FunctionTool.custom_data_extractor`
    Permite metadata SDK-only en `ToolCallOutputItem.raw_item["custom_data"]`
    sin que el modelo lo vea. Fuente: `src/agents/tool.py:452-456`.

19. **`trace_include_sensitive_data`** run-level config, con env
    `OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA` default `"true"`.
    Permite compliance. Fuente: `src/agents/run_config.py:43-44, 264-270`.

20. **Codex tool name collisions**: `_validate_codex_tool_name_collisions`
    (`agent.py:95-118`) — `codex_tool(name=...)` debe ser único.

### Baja prioridad — anotaciones

21. **3 archivos `SandboxArchiveLimits`/`SandboxConcurrencyLimits`/
    `SandboxRunConfig`** — documentar sub-configs.

22. **17 archivos en `run_internal/`** — más granular que lo que el doc
    preexistente sugiere.

23. **`HandoffInputData` tiene 5 campos** (no 4): añadir
    `input_items: tuple[RunItem,...] | None`. Fuente:
    `handoffs/__init__.py:42-71`.

24. **`Handoff.on_invoke_handoff`** es el callback real invocado por el
    runner; `OnHandoffWithInput` / `OnHandoffWithoutInput` son callable
    types pasados al factory `handoff(...)`. Distinguir.

25. **`MultiProvider` `MultiProviderMap`** permite custom provider
    routing independiente de los prefix built-in.

26. **`@tool_input_guardrail` y `@tool_output_guardrail`** sintaxis dual
    (`@decorator` y `@decorator(...)`) — documentar.

27. **`Handoff.strict_json_schema=True`** forzado por el SDK
    (`handoffs/__init__.py:312-314`).

28. **Lazy imports**: `SQLiteSession` y `MCPServer*` se cargan lazy para
    no penalizar cold start. Fuente:
    `__init__.py:256-267` + `mcp/__init__.py:67-83`.

29. **`FunctionTool.defer_loading`** — option de tool-search.

30. **`FunctionTool._tool_origin`** + `ToolOriginType` enum
    (`ToolOriginType` con 3 valores: function, mcp, agent_as_tool).
    Serializa metadata. Fuente: `src/agents/tool.py:270-322`.

31. **`FunctionTool._tool_namespace` + `tool_namespace(...)`** —
    agrupamiento lógico de tools. Fuente: `__init__.py:196`.

32. **`run_internal/_asyncio_progress.py`** — asyncio progress helpers
    (mencionado en imports `run.py:34-40`).

33. **`ShellToolContainer*` / `ShellToolHostedEnvironment` /
    `ShellToolInlineSkill*` / `ShellToolLocalSkill*`** — familia de
    tipos del shell tool (no en doc preexistente). Fuente:
    `tool.py:99-119` (tipos relacionados en `__init__.py:160-179`).

34. **`ComputerTool` + `ComputerProvider`** (lifecycle create/dispose),
    no ComputerProvider hospedada — local only. Source:
    `tool.py:325-356` + `tool.py:331-345` (create/dispose Protocols).

35. **`OpenAIServerConversationTracker`** en
    `run_internal/oai_conversation.py` (mencionado en `run.py:81`).

36. **`PromptCacheKeyResolver`** en
    `run_internal/prompt_cache_key.py` (mencionado en `run.py:82`).

### Neutrales / no verificables en este audit

37. **Default realtime model `gpt-realtime-2.1`** — el código NO fija
    default explícito; viene presumiblemente de docs externas. Tratar
    como "según docs externas", no como hecho verificado.

38. **8 sandbox backends oficiales vía extras** — los clients viven
    probablemente en `extensions/sandboxes/` (no leído este audit).
    Verificar antes de afirmar el número.

39. **`LiteLLM 100+ LLMs`** — verificable pero `extensions/models/litellm_provider.py`
    no leído este audit.

40. **`any-llm-sdk`** — verificable pero `extensions/models/any_llm_provider.py`
    no leído este audit.

41. **MCP deps exactas** — `mcp>=1.19.0, <2` confirmado en
    `pyproject.toml:18`.

42. **Voice pipeline specific actors** — no leído `src/agents/voice/*.py`.

43. **`extensions/visualization.py` (graphviz)** — no leído.

44. **`ComputerToolEnvironmentButton`** y detalles del computer use
    hierarchy — no leídos.

## Acción recomendada

1. `aithera-jwiki-audit` consume este doc + audit doc + architecture doc.
2. Para cada item **#1-7** (alta prioridad): UPDATE el doc preexistente.
3. Para cada item **#8-30** (media/baja): agregar al doc preexistente.
4. Para items **#37-44** (neutrales): marcar explícitamente "no
   verificado en este audit" en lugar de afirmación.

---

*Material crudo v1.0 — generado en tick A-20260713.*
