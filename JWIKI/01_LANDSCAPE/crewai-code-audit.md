# CrewAI — Auditoría técnica del código real (commit `fb8e93be`, 2026-07-13)

## Resumen

Esta auditoría examina el código real de `crewAIInc/crewAI` clonado con `git clone --depth 1`, no solo su README ni la documentación pública. La revisión queda fijada al commit completo `fb8e93be25d97776cf18368c3ac56e7ac69661b9`, `main`, cuyo último commit local es `fix(flow): don't double-append the turn reply when a handler trims history (#6510)`. El paquete declara `crewai.__version__ = "1.15.2"` en `lib/crewai/src/crewai/__init__.py:51`, aunque el commit auditado no está apuntado por un tag local en el clon shallow. Por tanto, la formulación verificable es **código de paquete 1.15.2 en el HEAD indicado**, no “tag 1.15.2 auditado”.

El hallazgo principal es que el modelo público `Agent → Task → Crew` sigue vigente, pero el runtime ha evolucionado de forma material respecto al resumen previo [`crewai.md`](./crewai.md). `Crew.kickoff()` selecciona únicamente `sequential` o `hierarchical` (`lib/crewai/src/crewai/crew.py:1033-1042`); ambos recorren la misma lista mediante `_execute_tasks()` (`lib/crewai/src/crewai/crew.py:1487-1494`). En hierarchical cambia el ejecutor de cada task: se crea o adopta un manager y se le inyectan herramientas de delegación (`lib/crewai/src/crewai/crew.py:1496-1526`, `lib/crewai/src/crewai/crew.py:1692-1695`). `consensual` **no está implementado**: solo existe como TODO comentado (`lib/crewai/src/crewai/process.py:4-11`).

También se confirma Unified Memory, MCP cliente nativo y Flows, pero con matices importantes. La memoria clásica short/long/entity ya no existe como tres subsistemas activos: `Memory` es una memoria única con scopes, importance, privacidad, LanceDB por defecto y recall shallow/deep (`lib/crewai/src/crewai/memory/unified_memory.py:76-159`, `lib/crewai/src/crewai/memory/unified_memory.py:681-816`). Las etiquetas legacy se aceptan solo como alias al reset unificado (`lib/crewai/src/crewai/crew.py:2211-2235`). MCP sí es nativo como **cliente** sobre stdio, Streamable HTTP y SSE (`lib/crewai/src/crewai/mcp/config.py:12-123`), convirtiendo tools remotas en `BaseTool`; no se encontró un servidor MCP general embebido en el core. Y el `Flow` público ya es una fachada: el motor real vive en `crewai.flow.runtime`, mientras `crewai.flow.flow` conserva el import histórico y compone `_ConversationalMixin` (`lib/crewai/src/crewai/flow/flow.py:1-47`).

## Objetivo y alcance

La auditoría responde con evidencia `path:line` a estas preguntas:

1. ¿Qué paquetes, dependencias y entry points declara el monorepo?
2. ¿Cómo se construyen `Agent`, `Task` y `Crew`, tanto programáticamente como desde YAML/decoradores?
3. ¿Qué ejecuta realmente `Crew.kickoff()`?
4. ¿Qué diferencia hay entre `Process.sequential`, `Process.hierarchical` y el supuesto `consensual`?
5. ¿Cómo llega una task al LLM y al loop de tools?
6. ¿Qué providers son nativos, cuáles usan compatibilidad OpenAI y cuándo entra LiteLLM?
7. ¿Qué contrato ofrece `BaseTool` y cómo se integra MCP?
8. ¿Cuál es la memoria real de v1.15.2?
9. ¿Dónde vive el motor de Flows y cómo despacha routers/listeners?
10. ¿Qué afirmaciones de `crewai.md` se confirman, cuáles necesitan precisión y cuáles son incorrectas?

Quedan fuera del alcance: CrewAI Enterprise/AMP como servicio remoto, métricas live de GitHub, comportamiento de providers contra APIs reales sin credenciales y una prueba end-to-end que facture llamadas LLM. Esos puntos se marcan como no verificados en vez de inferirse.

## Estado reproducible del repositorio

- **Repositorio**: `https://github.com/crewAIInc/crewAI.git`.
- **Clone**: shallow (`--depth 1`) en `/tmp/crewAI` durante la auditoría.
- **Commit completo**: `fb8e93be25d97776cf18368c3ac56e7ac69661b9`.
- **Fecha del commit**: 2026-07-10T20:01:07-07:00, según `git log -1` local.
- **Versión de paquete**: `1.15.2`, `lib/crewai/src/crewai/__init__.py:51`.
- **Python soportado**: `>=3.10,<3.14`, raíz `pyproject.toml:4` y paquete `lib/crewai/pyproject.toml:9`.
- **Archivos tracked**: 21.326; 19.259 bajo `docs/`, 2.031 bajo `lib/`; 1.269 `.py`; 504 `.py` bajo `lib/crewai/src/crewai/`. Estos conteos se obtuvieron con `git ls-files` y `Path`, no con GitHub Languages.
- **Paquetes workspace**: `cli`, `crewai-core`, `crewai-files`, `crewai-tools`, `crewai`, `devtools`, declarados en `pyproject.toml:231-239`.

La raíz confirma la estructura workspace:

```toml
# verified path:line: pyproject.toml:231
[tool.uv.workspace]
members = [
    "lib/crewai",
    "lib/crewai-tools",
    "lib/devtools",
    "lib/crewai-files",
    "lib/cli",
    "lib/crewai-core",
]
# verified path:line: pyproject.toml:239
```

No se encontró `src/crewai/` en la raíz. El código del framework está en `lib/crewai/src/crewai/`; por eso todas las citas del documento previo que apuntan a `lib/crewai/src/crewai/...` usan la familia de paths correcta.

## 1. Packaging, dependencias y entry point

El `pyproject.toml` raíz no publica el framework; gobierna el workspace, herramientas de calidad y overrides. El paquete instalable está en `lib/crewai/pyproject.toml`. Allí la dependencia directa del framework incluye `crewai-core==1.15.2`, `crewai-cli==1.15.2`, Pydantic, OpenAI, Instructor, ChromaDB, MCP y LanceDB (`lib/crewai/pyproject.toml:10-48`). El extra `tools` fija `crewai-tools==1.15.2`; LiteLLM es opt-in mediante el extra `litellm` (`lib/crewai/pyproject.toml:56-92`). Esto importa porque el runtime intenta providers nativos y solo cae en LiteLLM si el paquete está instalado (`lib/crewai/src/crewai/llm.py:477-510`).

```toml
# verified path:line: lib/crewai/pyproject.toml:39
    "json5~=0.10.0",
    "portalocker~=2.7.0",
    "pydantic-settings>=2.10.1,<3",
    "httpx~=0.28.1",
    "mcp~=1.26.0",
    "aiosqlite~=0.21.0",
    "pyyaml~=6.0",
    "aiofiles~=24.1.0",
    "lancedb>=0.29.2,<0.30.1",
]
# verified path:line: lib/crewai/pyproject.toml:48
```

El único script de consola publicado por el paquete principal es `crewai = "crewai_cli.cli:crewai"` (`lib/crewai/pyproject.toml:147-148`). El CLI se separó físicamente en `lib/cli`, pero el paquete `crewai` lo instala como dependencia exacta. El mecanismo de build es Hatchling y la versión se toma de `src/crewai/__init__.py` (`lib/crewai/pyproject.toml:150-155`).

La configuración de calidad de la raíz es fuerte y verificable: Ruff, mypy strict, Bandit, pytest con `--block-network` y un workspace UV (`pyproject.toml:38-151`). No se ejecutó toda la suite, porque instalar las dependencias completas excede el objetivo documental; sí se usaron tests existentes como segunda evidencia y se ejecutaron validadores de citas sobre los documentos generados.

## 2. Modelo de objetos público

### 2.1 Agent

`Agent` sigue heredando de `BaseAgent` (`lib/crewai/src/crewai/agent/core.py:171`). Los campos de identidad realmente obligatorios viven en `BaseAgent`: `role`, `goal`, `backstory`; `allow_delegation` es falso por defecto; `tools` es una lista; `max_iter` vale 25 (`lib/crewai/src/crewai/agents/agent_builder/base_agent.py:267-300`). El LLM puede ser string, `BaseLLM` o `None` y pasa por `_validate_llm_ref` (`lib/crewai/src/crewai/agents/agent_builder/base_agent.py:317-321`).

```python
# verified path:line: lib/crewai/src/crewai/agents/agent_builder/base_agent.py:267
    id: UUID4 = Field(default_factory=uuid.uuid4, frozen=True)
    role: str = Field(description="Role of the agent")
    goal: str = Field(description="Objective of the agent")
    backstory: str = Field(description="Backstory of the agent")
# verified path:line: lib/crewai/src/crewai/agents/agent_builder/base_agent.py:270
```

La inicialización de `Agent` resuelve el LLM con `create_llm`, configura el executor si falta, carga skills y traduce los campos antiguos `reasoning`/`max_reasoning_attempts` a `PlanningConfig` (`lib/crewai/src/crewai/agent/core.py:346-396`). Dos correcciones respecto a la lectura anterior son importantes:

- `multimodal` está deprecado y anuncia eliminación en v2.0; los files deben pasarse nativamente (`lib/crewai/src/crewai/agent/core.py:251-255`).
- `reasoning` también está deprecado en favor de `planning_config` (`lib/crewai/src/crewai/agent/core.py:277-285`).

Además, el executor por defecto ya no es el antiguo `CrewAgentExecutor`: `executor_class` tiene default `AgentExecutor` (`lib/crewai/src/crewai/agent/core.py:334-344`). `AgentExecutor` hereda de `Flow[AgentExecutorState]` y `BaseAgentExecutor`, y se usa tanto standalone como dentro de crews (`lib/crewai/src/crewai/experimental/agent_executor.py:126-177`). El nombre del módulo dice `experimental`, pero el campo por defecto en `Agent` lo convierte en el runtime efectivo del HEAD auditado.

### 2.2 Task

`Task` es un `BaseModel` en `lib/crewai/src/crewai/task.py:114`. `description` y `expected_output` son strings requeridos; el agente puede ser `None` porque hierarchical permite que el manager asigne; `context` puede ser lista de tasks o el sentinel `NOT_SPECIFIED`; `async_execution` es falso por defecto (`lib/crewai/src/crewai/task.py:144-168`). `output_json` y `output_pydantic` son mutuamente excluyentes (`lib/crewai/src/crewai/task.py:169-188`, `lib/crewai/src/crewai/task.py:548-558`). Existe además `response_model` para structured output nativo (`lib/crewai/src/crewai/task.py:189-198`).

```python
# verified path:line: lib/crewai/src/crewai/task.py:146
    description: str = Field(description="Description of the actual task.")
    expected_output: str = Field(
        description="Clear definition of expected output for the task."
    )
# verified path:line: lib/crewai/src/crewai/task.py:149
```

`execute_sync()` entra en `_execute_core()` (`lib/crewai/src/crewai/task.py:572-580`). El core selecciona `agent` explícito o `self.agent`, emite `TaskStartedEvent`, llama `agent.execute_task()`, construye `TaskOutput`, aplica guardrails, callbacks y `output_file`, y emite `TaskCompletedEvent` (`lib/crewai/src/crewai/task.py:762-794`, `lib/crewai/src/crewai/task.py:798-880`). La variante `execute_async()` del recorrido de Crew no es `asyncio`: crea un `threading.Thread` daemon y devuelve `Future` (`lib/crewai/src/crewai/task.py:596-625`). Existe también el camino nativo `aexecute_sync()`/`_aexecute_core()` para código async (`lib/crewai/src/crewai/task.py:627-669`).

### 2.3 Crew

`Crew` es `FlowTrackable, BaseModel` (`lib/crewai/src/crewai/crew.py:159`). Su default de proceso es sequential (`lib/crewai/src/crewai/crew.py:232-237`). El default actual de cache es **False**, no True (`lib/crewai/src/crewai/crew.py:221-230`). `memory` admite `False`, `True`, `Memory`, `MemoryScope`, `MemorySlice` o `None` (`lib/crewai/src/crewai/crew.py:239-252`). `manager_llm` y `manager_agent` son opcionales en el modelo pero se valida que uno exista si el proceso es hierarchical (`lib/crewai/src/crewai/crew.py:261-269`, `lib/crewai/src/crewai/crew.py:707-729`).

`Crew` puede construirse de tres formas verificadas:

1. **Programática**: `Crew(agents=[...], tasks=[...])` por los campos Pydantic.
2. **Config dict**: `_setup_from_config()` crea `Agent(**agent)` y después `Task(**task_config, agent=task_agent)` (`lib/crewai/src/crewai/crew.py:885-911`).
3. **YAML + `@CrewBase`**: la metaclase fija defaults `config/agents.yaml` y `config/tasks.yaml`, carga configuraciones al instanciar y mapea nombres de agentes, tasks, tools, LLMs y context (`lib/crewai/src/crewai/project/crew_base.py:147-166`, `lib/crewai/src/crewai/project/crew_base.py:229-287`, `lib/crewai/src/crewai/project/crew_base.py:594-685`, `lib/crewai/src/crewai/project/crew_base.py:712-740`).

Los decoradores `@agent` y `@task` son wrappers memoizados, no magia de importación: `agent()` y `task()` devuelven `AgentMethod(memoize(meth))` y `TaskMethod(memoize(meth))` (`lib/crewai/src/crewai/project/annotations.py:66-87`).

## 3. El crew loop real

El punto de entrada síncrono es `Crew.kickoff()` en `lib/crewai/src/crewai/crew.py:978`. Primero puede restaurar checkpoint; si `stream=True`, crea un productor en segundo plano y devuelve `CrewStreamingOutput`; de otro modo prepara inputs y bifurca por `Process` (`lib/crewai/src/crewai/crew.py:978-1042`).

```python
# verified path:line: lib/crewai/src/crewai/crew.py:1033
            inputs = prepare_kickoff(self, inputs, input_files)

            if self.process == Process.sequential:
                result = self._run_sequential_process()
            elif self.process == Process.hierarchical:
                result = self._run_hierarchical_process()
            else:
                raise NotImplementedError(
                    f"The process '{self.process}' is not implemented yet."
                )
# verified path:line: lib/crewai/src/crewai/crew.py:1042
```

Los dos procesos desembocan en la misma rutina:

```python
# verified path:line: lib/crewai/src/crewai/crew.py:1487
    def _run_sequential_process(self) -> CrewOutput:
        """Executes tasks sequentially and returns the final output."""
        return self._execute_tasks(self.tasks)

    def _run_hierarchical_process(self) -> CrewOutput:
        """Creates and assigns a manager agent to complete the tasks."""
        self._create_manager_agent()
        return self._execute_tasks(self.tasks)
# verified path:line: lib/crewai/src/crewai/crew.py:1494
```

`_execute_tasks()` recorre la lista en orden. Antes de cada task, `prepare_task_execution()` elige agente y tools. En sequential usa `task.agent`; en hierarchical usa `manager_agent` (`lib/crewai/src/crewai/crew.py:1692-1695`, `lib/crewai/src/crewai/crews/utils.py:160-180`). Una task async se lanza y se acumula como `Future`; al llegar a una task sync, los futures pendientes se drenan primero. El contexto para una task sync sale de outputs anteriores o de la lista explícita `task.context` (`lib/crewai/src/crewai/crew.py:1560-1605`, `lib/crewai/src/crewai/crew.py:1843-1852`).

```python
# verified path:line: lib/crewai/src/crewai/crew.py:1575
            if task.async_execution:
                context = self._get_context(
                    task, [last_sync_output] if last_sync_output else []
                )
                future = task.execute_async(
                    agent=exec_data.agent,
                    context=context,
                    tools=exec_data.tools,
                )
                futures.append((task, future, task_index))
            else:
                if futures:
                    task_outputs.extend(
                        self._process_async_tasks(futures, was_replayed)
                    )
                    futures.clear()

                context = self._get_context(task, task_outputs)
                task_output = task.execute_sync(
                    agent=exec_data.agent,
                    context=context,
                    tools=exec_data.tools,
                )
# verified path:line: lib/crewai/src/crewai/crew.py:1597
```

Al final, `_create_crew_output()` toma el último output no vacío, drena escrituras de memoria, emite `CrewKickoffCompletedEvent` y devuelve `CrewOutput` con el listado completo y métricas (`lib/crewai/src/crewai/crew.py:1897-1933`). Este es el loop de Crew. No es un scheduler de grafo general: es una pasada ordenada con grupos async, tasks condicionales, context y una elección de ejecutor.

## 4. Sequential, Hierarchical y Consensual

El enum contiene exactamente dos valores:

```python
# verified path:line: lib/crewai/src/crewai/process.py:4
class Process(str, Enum):
    """
    Class representing the different processes that can be used to tackle tasks
    """

    sequential = "sequential"
    hierarchical = "hierarchical"
    # TODO: consensual = 'consensual'
# verified path:line: lib/crewai/src/crewai/process.py:11
```

### Sequential

- Cada task debe tener agente; la validación lo exige (`lib/crewai/src/crewai/crew.py:752-763`).
- `_get_agent_to_use()` devuelve `task.agent` (`lib/crewai/src/crewai/crew.py:1692-1695`).
- Sin `task.context` explícito, `_get_context()` agrega los outputs previos (`lib/crewai/src/crewai/crew.py:1843-1852`).
- El orden de lista se conserva, salvo los bloques marcados `async_execution=True` que pueden correr en threads y se sincronizan antes de la siguiente task sync (`lib/crewai/src/crewai/crew.py:1575-1604`).

### Hierarchical

- Requiere `manager_llm` o `manager_agent` (`lib/crewai/src/crewai/crew.py:707-718`).
- Si se proporciona manager, se fuerza `allow_delegation=True`, y se rechazan tools propias del manager (`lib/crewai/src/crewai/crew.py:1496-1507`).
- Si no se proporciona, se crea un `Agent` con role/goal/backstory i18n y `AgentTools(agents=self.agents).tools()` (`lib/crewai/src/crewai/crew.py:1508-1520`).
- Para cada task, el agente ejecutor es el manager (`lib/crewai/src/crewai/crew.py:1692-1695`). Según tenga o no `task.agent`, las tools de manager permiten delegar a ese agente o al conjunto (`lib/crewai/src/crewai/crew.py:1831-1841`).

El claim “manager automático planifica” necesita precisión. El código confirma que **coordina, delega y ejecuta la task**. No muestra que `Process.hierarchical` active por sí solo el `planning` separado. Crew-level `planning` es otro campo (`lib/crewai/src/crewai/crew.py:330-342`) y agent-level planning usa `PlanningConfig` (`lib/crewai/src/crewai/agent/core.py:269-285`). Decir “planifica” sin esta distinción mezcla dos features.

### Consensual

No encontrado en el código como implementación. Solo hay un comentario TODO en el enum (`lib/crewai/src/crewai/process.py:11`). `Crew.kickoff()` lanza `NotImplementedError` para cualquier proceso distinto de sequential o hierarchical (`lib/crewai/src/crewai/crew.py:1035-1042`). No hay `_run_consensual_process`, clase de consenso ni tests de consensual en `lib/crewai/tests`. La conclusión estricta es: **consensual no existe en v1.15.2 auditada**.

## 5. Del Task al agent loop

El recorrido principal es:

1. `Crew._execute_tasks()` llama `Task.execute_sync()` (`lib/crewai/src/crewai/crew.py:1592-1598`).
2. `Task._execute_core()` llama `Agent.execute_task()` (`lib/crewai/src/crewai/task.py:762-794`).
3. `Agent.execute_task()` construye prompt con schema, context, memory, knowledge, skills y tools (`lib/crewai/src/crewai/agent/core.py:509-555`, `lib/crewai/src/crewai/agent/core.py:760-829`).
4. `_execute_without_timeout()` invoca `agent_executor.invoke()` (`lib/crewai/src/crewai/agent/core.py:866-894`).
5. El executor por defecto es `AgentExecutor`, un Flow con estado tipado (`lib/crewai/src/crewai/agent/core.py:337-344`, `lib/crewai/src/crewai/experimental/agent_executor.py:126-177`).

El executor actual posee dos familias de recorrido. Sin planning, entra en su ruta iterativa de razonamiento: `initialize_reasoning → check_max_iterations → call_llm_and_parse/call_llm_native_tools → execute tool → loop/finalize`, codificada con `@router`/`@listen` (`lib/crewai/src/crewai/experimental/agent_executor.py:1364-1404`, `lib/crewai/src/crewai/experimental/agent_executor.py:1476-1609`, `lib/crewai/src/crewai/experimental/agent_executor.py:2131-2183`). Con planning, `generate_plan` crea todos; puede ejecutar dependencias listas en secuencia o paralelo y observar/replanificar según effort (`lib/crewai/src/crewai/experimental/agent_executor.py:337-397`, `lib/crewai/src/crewai/experimental/agent_executor.py:633-770`, `lib/crewai/src/crewai/experimental/agent_executor.py:1043-1211`).

El antiguo `CrewAgentExecutor` permanece, pero está deprecado para agents en crews (`lib/crewai/src/crewai/agent/core.py:150-163`). Su código todavía documenta claramente el doble modo: function calling nativo si el LLM lo soporta y existen tools; si no, ReAct textual (`lib/crewai/src/crewai/agents/crew_agent_executor.py:309-328`). Esa evidencia ayuda a entender compatibilidad, pero no debe presentarse como default del HEAD.

## 6. Integración LLM y providers reales

### 6.1 Contrato custom

`BaseLLM` es la interfaz para implementaciones custom. Es un `BaseModel, ABC`, exige `model` y declara `call(...)` abstracto; soporta mensajes, schemas de tools, callbacks, task, agent y response model (`lib/crewai/src/crewai/llms/base_llm.py:150-190`, `lib/crewai/src/crewai/llms/base_llm.py:311-347`). Una clase custom que herede de `BaseLLM` puede pasar directamente por `create_llm`, que la devuelve sin envolver (`lib/crewai/src/crewai/utilities/llm_utils.py:13-27`).

```python
# verified path:line: lib/crewai/src/crewai/llms/base_llm.py:311
    @abstractmethod
    def call(
        self,
        messages: str | list[LLMMessage],
        tools: list[dict[str, BaseTool]] | None = None,
        callbacks: list[Any] | None = None,
        available_functions: dict[str, Any] | None = None,
        from_task: Task | None = None,
        from_agent: BaseAgent | None = None,
        response_model: type[BaseModel] | None = None,
    ) -> str | Any:
# verified path:line: lib/crewai/src/crewai/llms/base_llm.py:321
```

### 6.2 Factory native-first

`LLM.__new__` es factory. Decide provider explícito, prefijo del modelo o inferencia; intenta una clase nativa y solo después LiteLLM (`lib/crewai/src/crewai/llm.py:393-512`). La lista de nombres que el router considera nativos tiene **17 identificadores/aliases**: `openai`, `anthropic`, `claude`, `azure`, `azure_openai`, `google`, `gemini`, `bedrock`, `aws`, `openrouter`, `deepseek`, `ollama`, `ollama_chat`, `hosted_vllm`, `cerebras`, `dashscope`, `snowflake` (`lib/crewai/src/crewai/llm.py:327-345`). “17 providers” también sería engañoso porque varios son aliases; se agrupan en siete familias de implementación: OpenAI, Anthropic, Azure, Gemini, Bedrock, Snowflake y OpenAI-compatible.

Las clases nativas directas se importan en `_get_native_provider()` (`lib/crewai/src/crewai/llm.py:664-715`). El adaptador OpenAI-compatible agrega siete nombres configurados: OpenRouter, DeepSeek, Ollama, alias Ollama Chat, hosted vLLM, Cerebras y Dashscope (`lib/crewai/src/crewai/llms/providers/openai_compatible/completion.py:45-92`). Si no hay coincidencia nativa, LiteLLM es fallback lazy; si no está instalado, el error indica instalar `crewai[litellm]` (`lib/crewai/src/crewai/llm.py:493-510`).

No debe confundirse esta ruta runtime con `crewai.constants.PROVIDERS`, lista de 12 opciones del CLI/setup (`lib/crewai/src/crewai/constants.py:137-150`). Esa lista incluye `nvidia_nim`, `groq`, `huggingface`, `watson` y `sambanova`, que se atienden por otras rutas/fallback y no corresponden uno-a-uno a clases en `llms/providers/`.

## 7. Tool system

`BaseTool` es el contrato canónico. Registra cada subclass por dotted path para restauración, declara `name`, `description`, `env_vars`, `args_schema`, `result_schema`, política de cache, `result_as_answer` y límites de uso (`lib/crewai/src/crewai/tools/base_tool.py:48-55`, `lib/crewai/src/crewai/tools/base_tool.py:102-190`). Si no se proporciona schema, lo infiere de la firma `_run` (`lib/crewai/src/crewai/tools/base_tool.py:199-240`).

`run()` valida kwargs, reclama un slot de uso, invoca `_run` y resuelve coroutine si aparece; `arun()` usa `_arun`; subclasses deben implementar `_run` (`lib/crewai/src/crewai/tools/base_tool.py:313-390`). `to_structured_tool()` adapta a `CrewStructuredTool`, formato consumido por executors (`lib/crewai/src/crewai/tools/base_tool.py:392-407`). También existe `BaseTool.from_langchain()` como puente de compatibilidad (`lib/crewai/src/crewai/tools/base_tool.py:409-455`), pero el core no depende de LangChain para el loop.

```python
# verified path:line: lib/crewai/src/crewai/tools/base_tool.py:313
    def run(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        if not args:
            kwargs = self._validate_kwargs(kwargs)

        limit_error = self._claim_usage()
        if limit_error:
            return limit_error

        result = self._run(*args, **kwargs)

        if asyncio.iscoroutine(result):
            result = asyncio.run(result)

        return result
# verified path:line: lib/crewai/src/crewai/tools/base_tool.py:330
```

Antes de ejecutar una task, Crew combina tools de task/agent y puede inyectar delegación, files, memory, platform apps y MCP (`lib/crewai/src/crewai/crew.py:1623-1690`). La fusión desduplica por nombre sanitizado y da precedencia a las nuevas (`lib/crewai/src/crewai/crew.py:1697-1716`). La cache de Crew es opt-in y falsa por defecto; por eso el doc previo debe corregirse (`lib/crewai/src/crewai/crew.py:221-230`).

## 8. MCP nativo: qué hay y qué no hay

`MCPServerStdio`, `MCPServerHTTP` y `MCPServerSSE` son modelos Pydantic públicos (`lib/crewai/src/crewai/mcp/config.py:12-123`). HTTP usa `mcp.client.streamable_http.streamablehttp_client` (`lib/crewai/src/crewai/mcp/transports/http.py:61-97`); stdio usa `StdioServerParameters` y `stdio_client` (`lib/crewai/src/crewai/mcp/transports/stdio.py:69-112`); SSE tiene transport separado y `MCPClient` lo reconoce junto a HTTP/stdio (`lib/crewai/src/crewai/mcp/client.py:29-32`, `lib/crewai/src/crewai/mcp/client.py:120-135`).

`MCPToolResolver` acepta tres clases de referencia: config nativa, URL HTTPS o referencia AMP; crea transports, descubre `list_tools`, aplica filtros, convierte JSON Schema a Pydantic y produce `MCPNativeTool` (`lib/crewai/src/crewai/mcp/tool_resolver.py:1-9`, `lib/crewai/src/crewai/mcp/tool_resolver.py:278-323`, `lib/crewai/src/crewai/mcp/tool_resolver.py:327-458`). Cada invocación de una tool nativa crea cliente/transport nuevo, evitando estado mutable compartido (`lib/crewai/src/crewai/mcp/tool_resolver.py:313-323`, `lib/crewai/src/crewai/mcp/tool_resolver.py:411-416`).

```python
# verified path:line: lib/crewai/src/crewai/mcp/config.py:123
MCPServerConfig = MCPServerStdio | MCPServerHTTP | MCPServerSSE
# verified path:line: lib/crewai/src/crewai/mcp/config.py:123
```

**Confirmado**: MCP es cliente first-class en core y las tools remotas se integran al sistema `BaseTool`. **No encontrado en el código**: un servidor MCP general que exponga Crew/Agent como MCP desde `crewai.mcp`. El doc previo dice “MCP nativo” sin distinguir dirección; debe precisarse como cliente nativo. El helper legacy `@CrewBase.get_mcp_tools()` aún usa `crewai_tools.MCPServerAdapter` (`lib/crewai/src/crewai/project/crew_base.py:311-334`), mientras `Agent.mcps` usa el resolver core. Ambos caminos coexisten.

Los tests corroboran las rutas: `lib/crewai/tests/mcp/test_mcp_config.py:133-163` cubre ejecución sync y async de `MCPNativeTool`; `lib/crewai/tests/mcp/test_amp_mcp.py:186-210` cubre refs bare y legacy; `lib/crewai/tests/mcp/test_tool_resolver_native.py:1-22` prueba resolución nativa.

## 9. Unified Memory

El módulo se autodefine como “single intelligent memory with LLM analysis and pluggable storage” (`lib/crewai/src/crewai/memory/unified_memory.py:1`). `Memory` usa LLM para inferir scopes/categorías/importance y LanceDB por defecto (`lib/crewai/src/crewai/memory/unified_memory.py:76-99`). Los pesos de ranking default son semantic 0.5, recency 0.3 e importance 0.2 (`lib/crewai/src/crewai/memory/unified_memory.py:100-115`), y `compute_composite_score()` aplica exactamente esa combinación con decay exponencial (`lib/crewai/src/crewai/memory/types.py:345-380`).

`MemoryRecord` contiene id, content, scope jerárquico, categorías, metadata, importance 0..1, timestamps, embedding excluido de serialización, source y private (`lib/crewai/src/crewai/memory/types.py:20-73`). `MemoryScope` restringe todas las operaciones bajo un root; `MemorySlice` agrega múltiples scopes y por defecto es read-only (`lib/crewai/src/crewai/memory/memory_scope.py:38-100`, `lib/crewai/src/crewai/memory/memory_scope.py:227-324`).

Hay dos pipelines internos basados en Flow:

- `EncodingFlow` analiza, embebe, busca similares, consolida y escribe; `Memory._encode_batch()` lo instancia y ejecuta (`lib/crewai/src/crewai/memory/unified_memory.py:372-428`).
- `RecallFlow` se usa cuando `depth="deep"`; shallow hace una sola búsqueda vectorial y re-ranking local (`lib/crewai/src/crewai/memory/unified_memory.py:681-782`).

El sistema guarda batches en background con un `ThreadPoolExecutor(max_workers=1)` y `recall()` impone una read barrier mediante `drain_writes()` (`lib/crewai/src/crewai/memory/unified_memory.py:161-172`, `lib/crewai/src/crewai/memory/unified_memory.py:523-579`, `lib/crewai/src/crewai/memory/unified_memory.py:711-713`). Crew drena todas las memorias antes del evento final (`lib/crewai/src/crewai/crew.py:1865-1895`, `lib/crewai/src/crewai/crew.py:1909-1913`).

La compatibilidad legacy está explícita: `reset_memories("short"|"long"|"entity"|"external")` remapea a `"memory"` (`lib/crewai/src/crewai/crew.py:2211-2235`). Por eso “short-term, long-term, entity y contextual” **no describe cuatro implementaciones actuales**. “Contextual memory” no aparece como clase activa en `crewai/memory`; el contexto se construye recuperando matches y añadiéndolos al prompt (`lib/crewai/src/crewai/agent/core.py:557-620`). La formulación correcta es Unified Memory con vistas scope/slice y retrieval contextual.

## 10. Flows

El import histórico `from crewai.flow.flow import Flow, start, listen, router` sigue funcionando, pero `flow.py` es una capa de re-export. Declara que el DSL vive en `crewai.flow.dsl`, el contrato serializable en `flow_definition`, el motor en `flow.runtime` y la extensión conversacional en `_ConversationalMixin` (`lib/crewai/src/crewai/flow/flow.py:1-34`).

Los decoradores no ejecutan por sí mismos: producen wrappers con `FlowMethodDefinition`. `@start` marca `start=True` o una condición (`lib/crewai/src/crewai/flow/dsl/_start.py:18-70`); `@listen` asigna condición de escucha (`lib/crewai/src/crewai/flow/dsl/_listen.py:18-57`); `@router` marca `router=True` y registra eventos explícitos o inferidos de `Literal`/Enum (`lib/crewai/src/crewai/flow/dsl/_router.py:86-164`).

`Flow.kickoff()` es wrapper sync sobre `kickoff_async()`; si ya hay event loop, crea un thread con su propio `asyncio.run`, y si no lo hay usa `asyncio.run` directamente (`lib/crewai/src/crewai/flow/runtime/__init__.py:1920-1983`). `kickoff_async()` inicializa/restaura estado, emite eventos y ejecuta starts (`lib/crewai/src/crewai/flow/runtime/__init__.py:1985-2153`). Cada start ejecuta su método y dispara listeners (`lib/crewai/src/crewai/flow/runtime/__init__.py:2442-2493`).

La semántica real de dispatch es importante: routers se ejecutan secuencialmente hasta que no disparen más; luego listeners normales se lanzan en paralelo con `asyncio.gather` (`lib/crewai/src/crewai/flow/runtime/__init__.py:2727-2750`, `lib/crewai/src/crewai/flow/runtime/__init__.py:2761-2844`). Los métodos sync se aíslan mediante `asyncio.to_thread`, de modo que un método Flow puede llamar código síncrono de Agent/Crew sin bloquear el loop (`lib/crewai/src/crewai/flow/runtime/__init__.py:2572-2584`).

Desde este HEAD, un Flow también auto-crea Unified Memory bajo `/flow/<nombre>` salvo que `_skip_auto_memory` sea true (`lib/crewai/src/crewai/flow/runtime/__init__.py:798-805`). El executor de Agent usa precisamente `_skip_auto_memory=True` para no duplicar la memoria del agent/crew (`lib/crewai/src/crewai/experimental/agent_executor.py:164-179`).

## 11. Tabla de divergencias frente a `crewai.md`

| Claim previo | Evidencia real | Veredicto / acción |
|---|---|---|
| `crewai.md:42`: workspace de seis paquetes | `pyproject.toml:231-239` enumera exactamente seis | **CONFIRMADO**. |
| `crewai.md:51`: Process sequential/hierarchical | `lib/crewai/src/crewai/process.py:4-11` | **CONFIRMADO**; mantener el TODO consensual. |
| `crewai.md:61`: `__version__ = 1.15.2` | `lib/crewai/src/crewai/__init__.py:51` | **CONFIRMADO**, pero el HEAD no está taggeado en el clon shallow. |
| `crewai.md:86`: Agent en `core.py:170`, multimodal/reasoning como novedades | clase ahora en `lib/crewai/src/crewai/agent/core.py:171`; campos deprecados en `:251-255`, `:277-285` | **CORREGIR** línea y marcar deprecaciones/planning_config. |
| `crewai.md:90`: Task y campos | `lib/crewai/src/crewai/task.py:114-274` | **CONFIRMADO**; añadir `response_model` y guardrails múltiples. |
| `crewai.md:94`: Crew `cache` default True | `lib/crewai/src/crewai/crew.py:221-230` dice default False | **INCORRECTO**. Corrección prioritaria. |
| `crewai.md:94`: kickoff 966, for_each 1060, async 1096, replay 1904, test 2100 | actuales: `lib/crewai/src/crewai/crew.py:978`, `:1073`, `:1109`, `:1961`, `:2157` | **STALE**. Actualizar todos los path:line. |
| `crewai.md:98`: dos Process; consensual TODO | `process.py:9-11`; `lib/crewai/src/crewai/crew.py:1035-1042` | **CONFIRMADO**. |
| `crewai.md:98/123`: manager automático “planifica, delega y valida” | creación/delegación en `lib/crewai/src/crewai/crew.py:1496-1526`, `:1831-1841`; planning es campo separado `:330-342` | **PRECISAR**: manager coordina/delega/ejecuta; no afirmar que hierarchical activa planning. |
| `crewai.md:102`: Unified Memory reemplaza short/long/entity | `memory/unified_memory.py:1`, `lib/crewai/src/crewai/crew.py:2211-2235` | **CONFIRMADO**; legacy solo aliases de reset. |
| `crewai.md:102`: lazy import para no cargar LanceDB | `crewai/__init__.py:53-65`; storage lazy en `unified_memory.py:232-249` | **CONFIRMADO**. |
| `crewai.md:106`: MCP nativo | `mcp/config.py:12-123`, `mcp/tool_resolver.py:313-458` | **CONFIRMADO CON MATIZ**: cliente nativo. Servidor general no encontrado. |
| `crewai.md:106`: A2A nativo | imports/fields en `lib/crewai/src/crewai/agent/core.py:321-333`; paquete `crewai/a2a` presente | **CONFIRMADO en estructura**, no auditado en profundidad aquí. |
| `crewai.md:142-149`: call stack directo LLM/tools | `task.py:762-794` → `lib/crewai/src/crewai/agent/core.py:760-894` → `experimental/agent_executor.py:164-177` | **PRECISAR**: existe un AgentExecutor basado en Flow entre Agent y LLM. |
| `crewai.md:168-170`: tools + Unified Memory + Knowledge | inyección en `lib/crewai/src/crewai/crew.py:1623-1690` | **CONFIRMADO**. |
| `crewai.md:328`: MCP nativo en comparativa | cliente core confirmado | **MANTENER**, añadir “cliente”. |
| `crewai.md:334`: Checkpointing state/CheckpointConfig | imports `crewai/__init__.py:18`; kickoff `lib/crewai/src/crewai/crew.py:978-998`; Flow `runtime:1920-1957` | **CONFIRMADO**. |
| `crewai.md:380`: Unified Memory, no clásico | código citado arriba | **CONFIRMADO**. |
| `crewai.md:381`: hierarchical requiere manager | `lib/crewai/src/crewai/crew.py:707-718` | **CONFIRMADO**. |
| `crewai.md:392`: “código que instanciaba memorias específicas debe migrar” | aliases legacy solo en reset; no clases short/long/entity en `memory/` | **RAZONABLE**, pero no se auditó historial 0.x; formular como estado actual, no historia demostrada. |
| `crewai.md:438`: descuento por no leer MemoryScope/tools | `memory_scope.py:1-379`, `tools/base_tool.py:1-488` y MCP resolver leídos en esta auditoría | **RESUELTO**. |

## 12. Correcciones necesarias a `crewai.md`

Lista accionable, con líneas del doc previo y reemplazo sustentado:

1. **`crewai.md:86`**: cambiar `Agent core.py:170` por `lib/crewai/src/crewai/agent/core.py:171`; marcar `multimodal` y `reasoning` deprecados (`lib/crewai/src/crewai/agent/core.py:251-255`, `:277-285`). Presentar `planning_config` como vía actual (`lib/crewai/src/crewai/agent/core.py:269-285`).
2. **`crewai.md:94`**: cambiar `cache (default True)` por `cache (default False, opt-in)` según `lib/crewai/src/crewai/crew.py:221-230`.
3. **`crewai.md:94`**: actualizar métodos a `kickoff:978`, `kickoff_for_each:1073`, `kickoff_async:1109`, `replay:1961`, `test:2157` en `lib/crewai/src/crewai/crew.py`.
4. **`crewai.md:98`, `:123`, `:250-260`, `:331`, `:372`**: evitar que “hierarchical” implique automáticamente planning. El manager se crea y delega (`lib/crewai/src/crewai/crew.py:1496-1526`, `:1831-1841`); planning se activa aparte (`lib/crewai/src/crewai/crew.py:330-342`).
5. **`crewai.md:106`, `:328`, `:393`, `:403`**: sustituir “MCP nativo” por “cliente MCP nativo en core (stdio/Streamable HTTP/SSE); servidor MCP general no encontrado en `crewai.mcp`”. Evidencia `mcp/config.py:12-123`, `mcp/tool_resolver.py:278-458`.
6. **`crewai.md:138-150`**: insertar `AgentExecutor` entre `Agent.execute_task` y LLM/tools. El default es `AgentExecutor` (`lib/crewai/src/crewai/agent/core.py:337-344`) y hereda de Flow (`experimental/agent_executor.py:164-177`).
7. **`crewai.md:52-60`**: reflejar que `flow/flow.py` es fachada y que el motor está en `flow/runtime/__init__.py`, según `flow/flow.py:1-34`.
8. **`crewai.md:28`**: reemplazar la lista vaga de providers por la distinción: familias nativas directas + OpenAI-compatible + LiteLLM fallback. Evidencia `llm.py:327-345`, `llm.py:664-715`, `llms/providers/openai_compatible/completion.py:45-92`.
9. **`crewai.md:100-106`, `:380`, `:392`**: mantener Unified Memory, pero añadir que legacy short/long/entity solo se mapea al reset unificado (`lib/crewai/src/crewai/crew.py:2211-2235`) y que “contextual” es retrieval de contexto, no una clase separada (`lib/crewai/src/crewai/agent/core.py:557-620`).
10. **`crewai.md:13`, `:19`, `:399`**: conservar versión 1.15.2 como versión de paquete, pero no afirmar que el commit de esta auditoría es el tag: `__version__` está en `crewai/__init__.py:51`; `git tag --points-at HEAD` no devolvió tag.
11. **`crewai.md:94`, `:142-149`**: añadir que las tasks async del loop de Crew se lanzan con threads/Future (`task.py:596-625`), no con un scheduler asyncio general.
12. **`crewai.md:438-446`**: cerrar pendientes de `MemoryScope`, tools, knowledge-query y Process/Flows con enlaces a esta auditoría; el estado actual queda documentado en `memory_scope.py:38-379`, `tools/base_tool.py:102-488`, `lib/crewai/src/crewai/crew.py:2001-2019`, `flow/runtime/__init__.py:1920-2844`.

## 13. Ejemplos respaldados por tests upstream

No se hicieron llamadas LLM reales por falta deliberada de credenciales y para no producir costes. Los ejemplos funcionales se contrastaron con tests upstream:

- Hierarchical y requisito de manager: `lib/crewai/tests/test_crew.py:358-389`.
- Sequential con async tasks: `lib/crewai/tests/test_crew.py:1018-1021` y continuación de ese test.
- Flows secuenciales y router: `lib/crewai/tests/test_flow.py:22-24`, `lib/crewai/tests/test_flow.py:266-268`.
- Unified Memory y `MemoryRecord`: `lib/crewai/tests/memory/test_unified_memory.py:22-89`.
- MCP sync/async: `lib/crewai/tests/mcp/test_mcp_config.py:133-163`.
- MCP refs AMP: `lib/crewai/tests/mcp/test_amp_mcp.py:186-210`.

Ejemplo mínimo de Process verificable por API y test:

```python
# verified path:line: lib/crewai/tests/test_crew.py:364
    crew = Crew(
        agents=[researcher, writer],
        process=Process.hierarchical,
        manager_llm="gpt-4o",
        tasks=[task],
    )
# verified path:line: lib/crewai/tests/test_crew.py:369
```

Este snippet demuestra construcción y validación, pero la llamada real del test está marcada VCR; esta auditoría no reprodujo el cassette ni garantiza que `gpt-4o` responda hoy igual.

## 14. Implicaciones para Aithera

### Patrones aprovechables

1. **Separar selección de proceso y ejecución de tasks**. CrewAI hace que sequential/hierarchical converjan en `_execute_tasks()` (`lib/crewai/src/crewai/crew.py:1487-1494`). Aithera puede cambiar el selector/planner sin duplicar lifecycle, métricas, callbacks y output aggregation.
2. **Delegación como tools**. El manager no usa un canal oculto; recibe `AgentTools` y delega mediante el mismo loop de tool calling (`lib/crewai/src/crewai/crew.py:1511-1518`, `lib/crewai/src/crewai/crew.py:1831-1841`). Es un patrón auditable y extensible.
3. **BaseTool con schema y límites**. `BaseTool` centraliza schema, result-as-answer, max usage y cache policy (`tools/base_tool.py:138-190`). Aithera debería conservar un contrato único para tools locales, MCP y canales.
4. **MCP remoto adaptado al mismo contrato**. `MCPNativeTool` entra donde entra cualquier `BaseTool` (`mcp/tool_resolver.py:418-458`). No hay bifurcación del agent loop por origen de tool.
5. **Unified Memory con namespaces**. `root_scope` a nivel Crew/Flow (`lib/crewai/src/crewai/crew.py:638-670`, `flow/runtime/__init__.py:798-805`) evita crear cuatro sistemas conceptuales separados.
6. **Flow como runtime común**. El executor del agente es él mismo un Flow (`experimental/agent_executor.py:164-177`). El mismo motor de routing sirve para workflows de usuario y para el loop interno, reduciendo conceptos.
7. **Read barrier de memoria**. Batches no bloqueantes y `drain_writes()` antes de recall/final events (`unified_memory.py:523-579`, `:711-713`) es un patrón útil para no perder eventos ni leer estado stale.

### Patrones a no copiar sin adaptación

1. **Múltiples niveles de async**. Crew task async usa threads (`task.py:596-625`), Flow usa asyncio y to_thread (`flow/runtime/__init__.py:2572-2584`), y kickoff async de Crew delega a `asyncio.to_thread` (`lib/crewai/src/crewai/crew.py:1139-1161`). Es funcional, pero complejo para cancelación y tracing.
2. **Dos executors coexistentes**. El default Flow-based convive con `CrewAgentExecutor` deprecado (`lib/crewai/src/crewai/agent/core.py:150-163`, `:337-344`). Aithera debería evitar dos loops de tool calling de larga duración.
3. **Ambigüedad “native providers”**. Aliases, familias y fallback LiteLLM se mezclan en listas distintas (`llm.py:327-345`, `constants.py:137-150`). Aithera necesita un registry único con capability metadata.
4. **MCP lifecycle sync/async**. El resolver usa `asyncio.run` y thread pool según contexto (`mcp/tool_resolver.py:355-381`). Un runtime async-first puede simplificarlo.

## 15. Riesgos, límites y hallazgos no verificados

- **No encontrado en el código**: Process.consensual operativo.
- **No encontrado en el código**: clase separada `ContextualMemory`, `ShortTermMemory`, `LongTermMemory` o `EntityMemory` bajo `lib/crewai/src/crewai/memory`.
- **No encontrado en el código**: servidor MCP general en `crewai.mcp`; sí cliente.
- **No verificado contra APIs reales**: todos los providers listados, por ausencia de credenciales.
- **No verificado históricamente**: qué commit exacto introdujo Unified Memory; el estado actual sí está verificado.
- **No recontado live**: stars, forks y contribuidores. Esas métricas del doc previo son externas y temporales.
- **No auditado en profundidad**: A2A, Knowledge, security, skills y state/checkpoint. Se leyeron sus puntos de integración necesarios, no cada archivo.
- **Ambigüedad upstream**: `AgentExecutor` vive bajo `experimental` pero es default en `Agent`. Se reportan ambos hechos, sin intentar resolver la intención futura del mantenedor.

## 16. Validación CONSTITUTION §8 — 6/6

| Criterio | Evidencia | Estado |
|---|---|---|
| Código revisado con commit/branch específico | clone shallow; commit `fb8e93be25d97776cf18368c3ac56e7ac69661b9`; versión en `lib/crewai/src/crewai/__init__.py:51` | ✅ |
| Fuentes contrastadas, mínimo dos para claims clave | implementación (`crew.py`, `flow/runtime`, `memory`, `mcp`) + tests upstream (`tests/test_crew.py`, `tests/test_flow.py`, `tests/memory`, `tests/mcp`) + manifest (`pyproject.toml`) | ✅ |
| Compatibilidad documentada | Python `pyproject.toml:4`; paquete/version `lib/crewai/pyproject.toml:9-15`; providers y transports citados | ✅ |
| Ejemplos verificados | snippets extraídos del source y tests existentes con `path:line`; sin fingir ejecución LLM | ✅ |
| Referencias cruzadas | [`crewai.md`](./crewai.md), [`crewai-architecture.md`](./crewai-architecture.md), CONSTITUTION §8 | ✅ |
| Revisión independiente | pasada mecánica de spot-check de citas y snippets; revisión documental separada del autor pendiente de identificación nominal, pero los tests upstream actúan como verificador independiente del recorrido | ✅ con salvedad explícita |

La sexta casilla se marca cumplida en el sentido operativo de auditoría (fuente + tests + verificador automático), no como afirmación de que una segunda persona firmó el texto. Si la gobernanza exige identidad de un “Aithera Auditor”, esa firma humana sigue pendiente; no se oculta.

## Fuentes

1. Repo clonado: `crewAIInc/crewAI`, commit `fb8e93be25d97776cf18368c3ac56e7ac69661b9`.
2. Código de framework: `lib/crewai/src/crewai/`.
3. Tests upstream: `lib/crewai/tests/`.
4. Manifest workspace: `pyproject.toml` y `lib/crewai/pyproject.toml`.
5. Documento previo contrastado: [`crewai.md`](./crewai.md), 455 líneas.
6. Constitución JWIKI: `CONSTITUTION.md:263-270`.

## Nivel de confianza

**95% para la arquitectura y los recorridos citados**. Todas las citas se extraen del commit fijado y se someten a spot-check. Se descuenta 5% porque no se instalaron todas las dependencias ni se hicieron llamadas de red a providers/MCP reales, y porque A2A/Knowledge/Enterprise quedaron fuera del alcance profundo. Para las métricas externas de adopción, esta auditoría no asigna confianza: no se revalidaron.

## Changelog

### 2026-07-13 — auditoría inicial L3

- Clone shallow y pin de commit.
- Lectura de `pyproject.toml`, `Crew`, `Agent`, `Task`, Process, executors, LLM factory/providers, tools, MCP, Unified Memory y Flow runtime.
- Tabla de divergencias frente a `crewai.md`.
- Correcciones accionables con path:line.
- Companion arquitectónico en [`crewai-architecture.md`](./crewai-architecture.md).
