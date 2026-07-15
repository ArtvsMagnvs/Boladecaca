# CrewAI — Arquitectura técnica derivada del código (commit `fb8e93be`, 2026-07-13)

## Resumen

Este documento describe la arquitectura **real** de `crewAIInc/crewAI` en el commit `fb8e93be25d97776cf18368c3ac56e7ac69661b9`, con versión de paquete `1.15.2` (`lib/crewai/src/crewai/__init__.py:51`). Es el companion diagramático de [`crewai-code-audit.md`](./crewai-code-audit.md). Los diagramas no se derivan del README: se construyen desde imports, entry points, herencia, factories y call sites de `pyproject.toml`, `crewai.__init__`, `Crew`, `Agent`, `Task`, `AgentExecutor`, Flow runtime, LLM providers, tools, MCP y Unified Memory.

La arquitectura tiene dos niveles de orquestación que se reutilizan entre sí:

1. **Crew orchestration**: una pasada ordenada de `Task` sobre una lista, con elección de ejecutor por `Process`, grupos async basados en threads, contexto acumulado, callbacks, checkpoints y agregación de output.
2. **Flow orchestration**: un runtime event-driven con estado tipado, `@start`, routers secuenciales y listeners paralelos. El executor por defecto de cada Agent es él mismo un `Flow[AgentExecutorState]`, así que Flow no es solo una API de workflow para usuarios: también implementa el loop interno del agente.

Alrededor de esos dos motores hay cuatro adaptadores principales: `BaseLLM`/`LLM` para modelos, `BaseTool` para capacidades ejecutables, `MCPToolResolver` para convertir herramientas remotas al mismo contrato y Unified `Memory` para persistencia semántica por scopes. La arquitectura no contiene un tercer Process consensual: es un TODO comentado (`lib/crewai/src/crewai/process.py:4-11`). Tampoco contiene cuatro memorias activas short/long/entity/contextual: existe una `Memory` unificada y aliases legacy solo en el reset (`lib/crewai/src/crewai/crew.py:2211-2235`).

## Objetivo, alcance y método

Este documento sirve para:

- mostrar límites de paquetes y dependencias reales;
- seguir un kickoff desde API pública hasta LLM/tool/memory;
- separar la arquitectura de Crew de la de Flow;
- explicar por qué hierarchical no es un segundo scheduler, sino una política de asignación manager sobre el mismo loop;
- identificar interfaces de extensión verificadas;
- contrastar diagramas y claims del documento previo [`crewai.md`](./crewai.md);
- extraer patrones aplicables al Orchestrator de Aithera sin adoptar CrewAI como dependencia.

Método: clone shallow del repo; lectura de cada archivo citado; búsqueda de definiciones/call sites; contraste con tests upstream; spot-check mecánico posterior de `path:line`. El inventario local obtuvo 21.326 archivos tracked, 1.269 Python y 504 Python bajo `lib/crewai/src/crewai/`. Los 19.259 archivos bajo `docs/` explican el tamaño del clone, pero la arquitectura se basa en `lib/`, no en ese corpus documental.

## Estado y compatibilidad

| Componente | Estado auditado | Evidencia |
|---|---|---|
| Repo | commit `fb8e93be25d97776cf18368c3ac56e7ac69661b9` | `git rev-parse HEAD` local |
| Paquete | `crewai 1.15.2` | `lib/crewai/src/crewai/__init__.py:51` |
| Python | `>=3.10,<3.14` | `pyproject.toml:4`, `lib/crewai/pyproject.toml:9` |
| Workspaces | 6 paquetes | `pyproject.toml:231-239` |
| CLI | comando `crewai` | `lib/crewai/pyproject.toml:147-148` |
| Processes | sequential, hierarchical | `lib/crewai/src/crewai/process.py:4-11` |
| LLM runtime | native-first, LiteLLM fallback opt-in | `lib/crewai/src/crewai/llm.py:393-512` |
| MCP | cliente stdio/HTTP/SSE | `lib/crewai/src/crewai/mcp/config.py:12-123` |
| Memory | Unified Memory, LanceDB default | `lib/crewai/src/crewai/memory/unified_memory.py:76-159` |
| Flow | DSL + definition + runtime + conversational mixin | `lib/crewai/src/crewai/flow/flow.py:1-47` |

## 1. Mapa del monorepo

La raíz es un workspace UV, no un solo paquete. `pyproject.toml:231-239` lista exactamente seis members. `lib/crewai` publica el API principal, `lib/cli` el comando, `lib/crewai-core` utilidades compartidas, `lib/crewai-tools` tools opcionales, `lib/crewai-files` contenido multimodal/files y `lib/devtools` tooling de desarrollo.

```text
# verified path:line: pyproject.toml:231-239
crewAI/
├── pyproject.toml                 # workspace, lint, tests, overrides
├── lib/
│   ├── crewai/                    # framework público: Agent/Task/Crew/Flow
│   │   └── src/crewai/
│   ├── cli/                       # crewai_cli; target del console script
│   ├── crewai-core/               # utilidades core compartidas
│   ├── crewai-tools/              # extra crewai[tools]
│   ├── crewai-files/              # procesamiento de FileInput/multimodal
│   └── devtools/                  # tooling de desarrollo
└── docs/                          # documentación versionada, no runtime
```

La relación de instalación es explícita. El paquete principal depende de versiones exactas `crewai-core==1.15.2` y `crewai-cli==1.15.2` (`lib/crewai/pyproject.toml:10-16`). `crewai-tools` no está en las dependencias core: aparece en el extra `tools` (`lib/crewai/pyproject.toml:56-59`). LiteLLM también es extra (`lib/crewai/pyproject.toml:90-92`), coherente con el fallback lazy del factory LLM.

```text
# verified path:line: lib/crewai/pyproject.toml:10-59
crewai
 ├── exact dependency ──> crewai-core 1.15.2
 ├── exact dependency ──> crewai-cli  1.15.2
 ├── runtime deps ──────> pydantic, openai, instructor, mcp, lancedb, ...
 └── optional extra ────> crewai-tools 1.15.2
```

El entry point público cruza el boundary hacia el paquete CLI:

```toml
# verified path:line: lib/crewai/pyproject.toml:147
[project.scripts]
crewai = "crewai_cli.cli:crewai"
# verified path:line: lib/crewai/pyproject.toml:148
```

Por tanto, `crewai create`, `crewai run` y otros comandos no nacen de `crewai/cli/` dentro del framework; el directorio `lib/crewai/src/crewai/cli` solo contiene compatibilidad mínima. La superficie de consola canónica es `crewai_cli` del workspace separado.

## 2. Superficie pública e import graph

`crewai.__init__` importa eager las primitivas ligeras: `Agent`, `Crew`, `CrewOutput`, `Flow`, `Knowledge`, `LLM`, `BaseLLM`, `Process`, `Task` y outputs (`lib/crewai/src/crewai/__init__.py:8-21`). `Memory` es la excepción: se registra en `_LAZY_IMPORTS` y se importa en `__getattr__` al primer acceso (`lib/crewai/src/crewai/__init__.py:53-66`). Esto evita cargar LanceDB y dependencias de memoria cuando una aplicación no las usa.

```text
# verified path:line: lib/crewai/src/crewai/__init__.py:8-21
from crewai import ...
   ├── Agent  ─────> crewai.agent.core.Agent
   ├── Crew   ─────> crewai.crew.Crew
   ├── Task   ─────> crewai.task.Task
   ├── Flow   ─────> crewai.flow.flow.Flow
   ├── Process ────> crewai.process.Process
   ├── LLM/BaseLLM > crewai.llm / crewai.llms.base_llm
   └── Memory ─────> lazy import on attribute access
```

La estructura de clases más importante es:

```text
# verified path:line: lib/crewai/src/crewai/agent/core.py:171
BaseModel/ABC
 ├── BaseAgent ───────────────> Agent
 │    └── executor_class ─────> AgentExecutor (default)
 │                              ├── Flow[AgentExecutorState]
 │                              └── BaseAgentExecutor
 ├── Task
 ├── Crew ────────────────────> FlowTrackable + BaseModel
 ├── BaseLLM (ABC) ───────────> provider implementations / LLM fallback
 ├── BaseTool (ABC) ──────────> local, delegation, memory, MCP tools
 └── RuntimeFlow[T] ──────────> public Flow via _ConversationalMixin
# verified path:line: lib/crewai/src/crewai/experimental/agent_executor.py:164
```

Esa herencia revela una decisión arquitectónica que no aparece en el diagrama antiguo de `crewai.md`: `AgentExecutor` no es solo un `while` alojado en Agent. Es un Flow completo con state, routers y listeners. `Crew` no hereda de Flow; hereda de `FlowTrackable`, un mixin de tracing/checkpoint association. Son composiciones distintas y no deben representarse como un único grafo homogéneo.

## 3. Dos motores y sus responsabilidades

### Motor A: Crew

`Crew` es el orquestador de tasks. Su responsabilidad es:

- validar agentes/tasks/proceso;
- preparar inputs, files, callbacks, knowledge, memory y tracing;
- elegir sequential/hierarchical;
- recorrer tasks y gestionar grupos async;
- construir context entre outputs;
- agregar `CrewOutput` y métricas;
- drenar memory writes y emitir eventos de lifecycle.

Evidencia central: `Crew.kickoff()` en `lib/crewai/src/crewai/crew.py:978-1068`; `_execute_tasks()` en `lib/crewai/src/crewai/crew.py:1536-1605`; output final en `lib/crewai/src/crewai/crew.py:1897-1933`.

### Motor B: Flow

`RuntimeFlow` es el engine event-driven. Su responsabilidad es:

- crear/restaurar estado dict o Pydantic;
- construir métodos desde `FlowDefinition` o desde la clase Python;
- ejecutar métodos start;
- encadenar routers de forma secuencial;
- lanzar listeners normales en paralelo;
- persistir/checkpoint, pausar para human feedback, emitir eventos y agregar usage.

Evidencia: `flow/runtime/__init__.py:749-846` inicializa definición/métodos/memory; `:1920-2030` expone kickoff; `:2442-2493` ejecuta start; `:2727-2844` despacha routers/listeners.

```text
# verified path:line: lib/crewai/src/crewai/crew.py:1487-1494
                    USER API
                       │
          ┌────────────┴────────────┐
          │                         │
   Crew.kickoff()              Flow.kickoff()
   ordered task loop           event-driven runtime
          │                         │
          │                    @start methods
          │                         │
          │                    routers (serial)
          │                         │
          │                    listeners (parallel)
          │                         │
          └──── Agent.execute_task ─┘
                       │
               AgentExecutor default
               = Flow[typed state]
# verified path:line: lib/crewai/src/crewai/experimental/agent_executor.py:164-177
```

El borde inferior muestra la reutilización: un Crew invoca Agent; el Agent usa `AgentExecutor`, que internamente reutiliza Flow. Un Flow de usuario también puede invocar un Crew dentro de un método sync/async. `RuntimeFlow._execute_method()` ejecuta métodos sync en `asyncio.to_thread`, precisamente para permitir llamadas sync de Agent/Crew sin bloquear el event loop (`lib/crewai/src/crewai/flow/runtime/__init__.py:2572-2584`).

## 4. Construcción declarativa: YAML → objetos

La carga YAML no ocurre dentro de `Agent` o `Task`. `@CrewBase` reemplaza la metaclase de una clase de proyecto por `CrewBaseMeta`. Al crear instancia, el metaclass llama `load_configurations()`, recopila métodos decorados y resuelve variables (`lib/crewai/src/crewai/project/crew_base.py:193-287`). Los paths default son `config/agents.yaml` y `config/tasks.yaml` (`lib/crewai/src/crewai/project/crew_base.py:147-166`).

```text
# verified path:line: lib/crewai/src/crewai/project/crew_base.py:229-287
@CrewBase class ProjectCrew
        │ instantiate
        ▼
CrewBaseMeta.__call__
        │
        ├─ load_configurations()
        ├─ _get_all_methods()
        ├─ map_all_agent_variables()
        ├─ map_all_task_variables()
        └─ register before/after/kickoff hooks
```

Los decoradores son wrappers memoizados:

```python
# verified path:line: lib/crewai/src/crewai/project/annotations.py:66
def task(meth: Callable[P, TaskResultT]) -> TaskMethod[P, TaskResultT]:
    """Marks a method as a crew task.

    Args:
        meth: The method to mark.

    Returns:
        A wrapped method marked as a task with memoization.
    """
    return TaskMethod(memoize(meth))


def agent(meth: Callable[P, R]) -> AgentMethod[P, R]:
    """Marks a method as a crew agent.

    Args:
        meth: The method to mark.

    Returns:
        A wrapped method marked as an agent with memoization.
    """
    return AgentMethod(memoize(meth))
# verified path:line: lib/crewai/src/crewai/project/annotations.py:87
```

El mapping de agents resuelve un nombre de LLM a una factory decorada si existe; si no, conserva el string. Resuelve nombres de tools a métodos `@tool`, callbacks y cache handler (`lib/crewai/src/crewai/project/crew_base.py:594-659`). El mapping de tasks convierte nombres de context a instancias memoizadas, tools a factories, y `agent: researcher` a `agents["researcher"]()` (`lib/crewai/src/crewai/project/crew_base.py:662-740`).

```text
# verified path:line: lib/crewai/src/crewai/project/crew_base.py:712-740
agents.yaml                        tasks.yaml
  researcher:                       research_task:
    llm: my_llm                       agent: researcher
    tools: [search]                   context: [...]
      │                               tools: [search]
      ▼                                  │
@llm/@tool factories                    ▼
      │                           @agent/@task methods
      └──────────── CrewBase mapping ────┘
                         │
                         ▼
                 Agent / Task instances
                         │
                         ▼
                      Crew(...)
```

Existe además config dict directo. Si `Crew.config` está presente, `_setup_from_config()` crea una lista de `Agent(**agent)` y luego tasks buscando al agente por role (`lib/crewai/src/crewai/crew.py:885-911`). Ese formato no es idéntico al YAML de `@CrewBase`: uno resuelve por role en un dict ya materializado; el otro resuelve por nombre de método/factory. La arquitectura debe distinguirlos.

## 5. Kickoff completo de Crew

### 5.1 Pre-kickoff

`Crew.kickoff()` puede restaurar un checkpoint (`lib/crewai/src/crewai/crew.py:978-998`). En streaming habilita agent streaming, crea `StreamingContext`, ejecuta recursivamente el kickoff no-stream en un productor y devuelve `CrewStreamingOutput` (`lib/crewai/src/crewai/crew.py:1000-1024`). En el recorrido normal:

- establece baggage OpenTelemetry;
- entra en scope del event bus;
- llama `prepare_kickoff` para inputs/files/hook setup;
- selecciona Process;
- aplica after callbacks;
- post-procesa y calcula usage;
- en `finally`, drena memory, limpia files y context (`lib/crewai/src/crewai/crew.py:1026-1068`).

```text
# verified path:line: lib/crewai/src/crewai/crew.py:978-1068
Crew.kickoff(inputs, input_files, checkpoint)
  ├─ apply_checkpoint
  ├─ if stream: producer thread/context -> CrewStreamingOutput
  ├─ set OpenTelemetry crew_context baggage
  ├─ event_bus.enter_runtime_scope
  ├─ prepare_kickoff
  ├─ dispatch Process
  ├─ after_kickoff callbacks
  ├─ _post_kickoff + usage
  └─ finally: drain memory + clear files + detach scope
```

### 5.2 Dispatch del proceso

El dispatch solo admite dos branches (`lib/crewai/src/crewai/crew.py:1033-1042`). Sequential llama `_execute_tasks`. Hierarchical crea manager y llama la misma función (`lib/crewai/src/crewai/crew.py:1487-1494`). La topología de tasks no cambia; cambia quién ejecuta y qué delegation tools tiene.

```text
# verified path:line: lib/crewai/src/crewai/crew.py:1033-1042
                  process
                    │
         ┌──────────┴──────────┐
         │                     │
  sequential              hierarchical
         │                     │
  task.agent           _create_manager_agent
         │                     │
         └─────── _execute_tasks(tasks) ───────┐
                                               │
                                    ordered list + async groups
```

### 5.3 Preparación por task

`prepare_task_execution()` está separado en `crewai/crews/utils.py`. Para replay, salta tasks anteriores preservando outputs. Para una task activa, llama `crew._get_agent_to_use`, toma tools de task o agente, llama `crew._prepare_tools`, registra start y devuelve `TaskExecutionData` (`lib/crewai/src/crewai/crews/utils.py:103-183`).

`_prepare_tools()` agrega capacidades condicionales: delegación, code execution legacy, multimodal fallback, platform apps, MCP, memory y file reader (`lib/crewai/src/crewai/crew.py:1623-1690`). Esta etapa es el “dependency injection” dinámico del runtime; Agent no tiene por qué conocer al construirlo todas sus tools finales.

```text
# verified path:line: lib/crewai/src/crewai/crew.py:1623-1690
base tools = task.tools OR executing_agent.tools
      │
      ├─ + delegation tools (allow_delegation)
      ├─ + code tools (legacy flag)
      ├─ + multimodal fallback tools
      ├─ + platform app tools
      ├─ + MCP tools
      ├─ + Recall/Remember memory tools
      └─ + ReadFileTool for non-native file types
              │
              ▼
        merged by sanitized name
```

### 5.4 Ejecución y concurrencia

El loop `for task_index, task in enumerate(tasks)` es secuencial en control (`lib/crewai/src/crewai/crew.py:1560`). Las tasks marcadas async se lanzan como `Future` mediante `Task.execute_async`; cuando llega una task sync, los futures se esperan antes de construir el contexto y ejecutar (`lib/crewai/src/crewai/crew.py:1575-1604`). `Task.execute_async()` abre un `threading.Thread(daemon=True)` (`task.py:596-625`). No es un DAG executor general ni un task group asyncio.

El contexto se resuelve así:

- si `task.context` es falsy: string vacío;
- si el sentinel indica no especificado: agregar raw outputs del listado recibido;
- si es lista explícita: agregar outputs de esas tasks (`lib/crewai/src/crewai/crew.py:1843-1852`).

```text
# verified path:line: lib/crewai/src/crewai/crew.py:1560-1605
Task 1 sync ── output A ────────────────┐
                                       │
Task 2 async ─ Future B ──┐             │
Task 3 async ─ Future C ──┼─ join ─────┤
                          │             │
Task 4 sync <─────────────┘ context(A,B,C)
   │
   └─ TaskOutput D
          │
          ▼
_create_crew_output([A,B,C,D]) -> D as final, all outputs preserved
```

### 5.5 Output y cierre

`_create_crew_output()` filtra outputs raw válidos, toma el último, finaliza RPM, calcula tokens, drena memory writes, hace `event_bus.flush`, emite `CrewKickoffCompletedEvent` y devuelve `CrewOutput` con raw/pydantic/json/tasks/token usage (`lib/crewai/src/crewai/crew.py:1897-1933`). La barrera de memory antes del evento final es una relación arquitectónica importante: listeners de tracing pueden cerrarse con ese evento; si memory emitiera después, perdería spans (`lib/crewai/src/crewai/crew.py:1865-1877`).

## 6. Sequential y Hierarchical como políticas sobre el mismo loop

### Sequential

La validación exige un agente por task (`lib/crewai/src/crewai/crew.py:752-763`). `_get_agent_to_use()` retorna `task.agent` (`lib/crewai/src/crewai/crew.py:1692-1695`). Si `allow_delegation=True`, `_add_delegation_tools` ofrece coworkers excepto el propio task agent (`lib/crewai/src/crewai/crew.py:1798-1808`). No hay manager central.

```text
# verified path:line: lib/crewai/src/crewai/crew.py:1692-1695
Task A(agent=Researcher) ──> Researcher.execute_task
Task B(agent=Writer)     ──> Writer.execute_task
Task C(agent=Reviewer)   ──> Reviewer.execute_task
```

### Hierarchical

La validación exige `manager_llm` o `manager_agent` (`lib/crewai/src/crewai/crew.py:707-718`). Si hay manager custom, se fuerza delegación y se prohíben sus tools propias; si no, se crea uno con prompts i18n, `AgentTools(agents=self.agents).tools()`, `allow_delegation=True` y el manager LLM (`lib/crewai/src/crewai/crew.py:1496-1520`). Después `_get_agent_to_use()` devuelve siempre manager (`lib/crewai/src/crewai/crew.py:1692-1695`).

```text
# verified path:line: lib/crewai/src/crewai/crew.py:1496-1521
                     Crew tasks
                        │
                        ▼
                Manager Agent executes
                  /             \
       DelegateWorkTool      AskQuestionTool
              │                    │
     specialist agent A     specialist agent B
              └──────── result/context ────────┘
```

Si la task ya declara `task.agent`, `_update_manager_tools` limita delegación a ese agente; si no declara, ofrece todos (`lib/crewai/src/crewai/crew.py:1831-1841`). Esto refuta una simplificación común: hierarchical no ignora necesariamente la asignación de task; puede convertirla en target de delegación.

El manager **no activa automáticamente `Crew.planning`**. `planning` y `planning_llm` son campos separados (`lib/crewai/src/crewai/crew.py:330-342`). A nivel Agent, planning se configura con `planning_config` (`lib/crewai/src/crewai/agent/core.py:269-285`). El diagrama correcto separa coordinación jerárquica de planificación:

```text
# verified path:line: lib/crewai/src/crewai/crew.py:330-342
Process.hierarchical ──> quién ejecuta y delega
Crew.planning         ──> plan global previo (flag separado)
Agent.planning_config ──> plan/todos/replan dentro del AgentExecutor
```

### Consensual

No hay caja de arquitectura para consensual porque no existe implementación. `Process` solo contiene comentario TODO (`process.py:9-11`) y kickoff rechaza otros valores (`lib/crewai/src/crewai/crew.py:1039-1042`). Dibujarlo como proceso disponible sería inventar.

## 7. Task → Agent → AgentExecutor

`Task._execute_core()` selecciona agente, registra context/tools, emite evento y llama `agent.execute_task()` (`task.py:762-794`). Después convierte output a raw/pydantic/json, aplica guardrails, callbacks y archivo (`task.py:798-880`). Agent prepara el prompt en varias capas:

1. `task.prompt()` y schema de structured output;
2. task context;
3. Unified Memory recall;
4. Knowledge retrieval de agent y crew;
5. skill context/training data;
6. executor invoke.

Las primeras capas están en `lib/crewai/src/crewai/agent/core.py:509-620`; la llamada al executor, en `lib/crewai/src/crewai/agent/core.py:866-894`.

```text
# verified path:line: lib/crewai/src/crewai/agent/core.py:509-620
Task.description + expected_output
             │
             ├─ structured schema instructions
             ├─ previous TaskOutput context
             ├─ Unified Memory recall(limit=5)
             ├─ Agent/Crew Knowledge query
             ├─ skills + training data
             └─ tool preparation
                    │
                    ▼
             final task prompt
```

`Agent.create_agent_executor()` convierte `BaseTool` a `CrewStructuredTool`, construye prompts/stop words y crea la clase indicada por `executor_class`; el default es `AgentExecutor` (`lib/crewai/src/crewai/agent/core.py:1048-1098`, `lib/crewai/src/crewai/agent/core.py:337-344`). El executor recibe LLM, task, agent, crew, tools parseadas y originales, max_iter, callbacks y response model.

```python
# verified path:line: lib/crewai/src/crewai/agent/core.py:1075
            self.agent_executor = self.executor_class(
                llm=self.llm,
                task=task,
                agent=self,
                crew=self.crew,
                tools=parsed_tools,
                prompt=prompt,
                original_tools=raw_tools,
                stop_words=stop_words,
                max_iter=self.max_iter,
                tools_handler=self.tools_handler,
                tools_names=get_tool_names(parsed_tools),
                tools_description=render_text_description_and_args(parsed_tools),
                step_callback=self.step_callback,
                function_calling_llm=self.function_calling_llm,
                respect_context_window=self.respect_context_window,
                request_within_rpm_limit=rpm_limit_fn,
                callbacks=[TokenCalcHandler(self._token_process)],
                response_model=(
                    task.response_model or task.output_pydantic or task.output_json
                )
                if task
                else None,
            )
# verified path:line: lib/crewai/src/crewai/agent/core.py:1098
```

El executor recibe un `invoke` sync o `ainvoke` async. Agent rechaza usar el invoke sync si éste devuelve awaitable dentro de un event loop, y obliga a la API async (`lib/crewai/src/crewai/agent/core.py:879-894`). La ruta async llama `agent_executor.ainvoke()` (`lib/crewai/src/crewai/agent/core.py:988-1009`).

## 8. Arquitectura del AgentExecutor basado en Flow

`AgentExecutorState` contiene mensajes, iteraciones, respuesta actual, flags, pending native tool calls, plan, todos, replan count, observations y audit log (`experimental/agent_executor.py:126-161`). `AgentExecutor` hereda `Flow[AgentExecutorState]` + `BaseAgentExecutor` y desactiva auto-memory porque usa la del Agent/Crew (`experimental/agent_executor.py:164-179`).

Tiene dos macro-rutas.

### 8.1 Ruta sin planning: ReAct/native tool loop

`generate_plan` es start pero retorna si planning está deshabilitado (`experimental/agent_executor.py:337-348`). `check_todos_available` dirige a `planning_disabled`; `initialize_reasoning` inicializa; `check_max_iterations` elige `continue_reasoning` o native; el LLM devuelve final o action; action ejecuta tool y vuelve al loop (`experimental/agent_executor.py:1043-1060`, `:1364-1404`, `:1476-1609`, `:2131-2183`).

```text
# verified path:line: lib/crewai/src/crewai/experimental/agent_executor.py:1364-1404
              @start generate_plan
                      │ no planning
                      ▼
             planning_disabled
                      │
             initialize_reasoning
                      │
              check_max_iterations ◄──────────────┐
                /              \                  │
      text/ReAct LLM        native-tools LLM      │
             │                    │               │
        AgentAction          native tool calls    │
             │                    │               │
       execute tool           execute tool        │
             └──── observation/result ────────────┘
                      │ final
                      ▼
                 AgentFinish
```

El executor viejo `CrewAgentExecutor` muestra la misma bifurcación conceptualmente: function calling nativo si el LLM lo soporta y hay tools, o ReAct textual (`agents/crew_agent_executor.py:309-335`). En el executor actual esas transiciones están modeladas con Flow routers. La coexistencia explica por qué hay utilidades compartidas para parseo, tool execution y max iterations.

### 8.2 Ruta con planning: Plan-and-Execute

`generate_plan` usa `AgentReasoning`, guarda plan y crea todos con dependencias (`experimental/agent_executor.py:337-397`). `get_ready_todos_method` determina si hay uno o varios listos; uno se ejecuta secuencialmente, varios en paralelo (`experimental/agent_executor.py:1058-1211`). Después `observe_step_result` usa heuristic u otro LLM según reasoning effort y puede continuar, refinar, replanificar o terminar (`experimental/agent_executor.py:633-770`, `:772-1041`).

```text
# verified path:line: lib/crewai/src/crewai/experimental/agent_executor.py:337-397
              generate_plan
                    │
        plan string + TodoList(dependencies)
                    │
             get ready todos
              /            \
       one ready          many ready
          │                  │
   StepExecutor sync    parallel StepExecutors
          └──────── result(s) ────────┘
                    │
             observe step
          / low      | medium      \ high
   heuristic      LLM/failure      full decision
          │             │               │
      continue      replan?     refine/replan/goal
          └─────────────┴───────────────┘
                    │
             next todo / finish
```

La observación no recibe traces completos de dependencias. `_build_context_for_todo` pasa solo resultados finales de dependencias, task description y goal (`experimental/agent_executor.py:600-631`). Este boundary evita contaminar el prompt con execution logs y tool histories.

## 9. Capa LLM

### 9.1 Interfaz

`BaseLLM` define campos comunes y el método abstracto `call()` (`llms/base_llm.py:150-190`, `:311-347`). También normaliza messages, emite eventos y mantiene usage; implementaciones custom pueden heredarlo. `create_llm()` acepta instancia, string, dict, `None` o objeto similar; instancias `BaseLLM` pasan sin envolver (`utilities/llm_utils.py:13-87`).

### 9.2 Routing

`LLM.__new__` decide route. Prioridad documentada en el propio método: custom OpenAI, provider explícito, prefijo, inferencia (`llm.py:393-475`). Luego obtiene clase nativa; si no aplica, inicializa LiteLLM de forma lazy (`llm.py:477-512`).

```text
# verified path:line: lib/crewai/src/crewai/llm.py:393-512
LLM(model, provider?, custom_openai?)
       │
       ├─ custom_openai -> OpenAI native + custom endpoint
       ├─ explicit provider
       ├─ prefix/model -> canonical mapping + model validation
       └─ no prefix -> infer known provider, default OpenAI
                  │
          native class available?
             /             \
           yes              no
           │                │
   provider SDK class   LiteLLM lazy fallback
                            │ missing extra
                            └─ ImportError with install guidance
```

### 9.3 Provider families

`SUPPORTED_NATIVE_PROVIDERS` expone 17 identificadores/aliases (`llm.py:327-345`). `_get_native_provider()` los consolida:

- OpenAI → `OpenAICompletion`;
- Anthropic/Claude → `AnthropicCompletion`;
- Azure/Azure OpenAI → `AzureCompletion`;
- Google/Gemini → `GeminiCompletion`;
- Bedrock → `BedrockCompletion`;
- Snowflake → `SnowflakeCompletion`;
- siete OpenAI-compatible → `OpenAICompatibleCompletion` (`llm.py:664-715`).

El diccionario OpenAI-compatible fija endpoint/env para OpenRouter, DeepSeek, Ollama, Ollama Chat, hosted vLLM, Cerebras y Dashscope (`llms/providers/openai_compatible/completion.py:45-92`). No se debe dibujar `constants.PROVIDERS` como el registry runtime: esa lista de 12 es otra superficie de selección/setup (`constants.py:137-150`).

```text
# verified path:line: lib/crewai/src/crewai/llm.py:664-715
BaseLLM
 ├─ OpenAICompletion
 │    └─ OpenAICompatibleCompletion
 │         ├─ OpenRouter
 │         ├─ DeepSeek
 │         ├─ Ollama / ollama_chat
 │         ├─ hosted_vLLM
 │         ├─ Cerebras
 │         └─ Dashscope
 ├─ AnthropicCompletion
 ├─ AzureCompletion
 ├─ GeminiCompletion
 ├─ BedrockCompletion
 ├─ SnowflakeCompletion
 └─ LLM (LiteLLM fallback when installed)
```

## 10. Capa de tools

### 10.1 Contrato BaseTool

`BaseTool` registra subclasses por dotted path, útil para deserializar checkpoints (`tools/base_tool.py:48-77`, `:102-136`). Campos importantes: `name`, `description`, env vars, `args_schema`, `result_schema`, cache function, `result_as_answer`, `max_usage_count` y counter (`tools/base_tool.py:138-190`). Schemas de args se infieren de `_run`/`_arun` si faltan (`tools/base_tool.py:199-240`).

```text
# verified path:line: lib/crewai/src/crewai/tools/base_tool.py:102-190
BaseTool
 ├─ identity: name + description
 ├─ contract: args_schema + result_schema
 ├─ environment: env_vars
 ├─ policy: cache_function
 ├─ control: max_usage_count/current_usage_count
 ├─ terminal behavior: result_as_answer
 ├─ sync: run -> _run
 └─ async: arun -> _arun
```

`to_structured_tool()` convierte ese contrato en `CrewStructuredTool`, que los executors usan para render prompt y function schemas (`tools/base_tool.py:392-407`). El sistema conserva el objeto original para límites/cache/result-as-answer. `from_langchain()` es un adaptador opcional, no la base arquitectónica (`tools/base_tool.py:409-455`).

### 10.2 Ejecución

En modo nativo, tools se convierten a schema OpenAI y funciones disponibles. El executor recibe tool calls estructuradas, ejecuta y devuelve resultados al historial. En fallback textual, renderiza nombre/schema/descripción en prompt y parsea `Action/Action Input`. El antiguo executor deja visible la bifurcación (`agents/crew_agent_executor.py:309-335`, `:484-595`); el executor Flow actual representa las mismas decisiones con routers (`experimental/agent_executor.py:1403-1609`, `:1678-2130`).

### 10.3 Delegación y memory como tools

Hierarchical funciona sobre tools de delegación (`lib/crewai/src/crewai/crew.py:1511-1518`, `:1831-1841`). Unified Memory también entra como `RecallMemoryTool` y `RememberTool` mediante `_add_memory_tools()` (`lib/crewai/src/crewai/crew.py:1768-1780`). Así, coworker, memory y MCP son capacidades bajo el mismo loop:

```text
# verified path:line: lib/crewai/src/crewai/crew.py:1768-1841
AgentExecutor tool set
 ├─ authored BaseTool
 ├─ task-specific BaseTool
 ├─ Delegate work / Ask coworker
 ├─ Recall memory / Remember
 ├─ Read input file
 ├─ Platform app actions
 └─ MCPNativeTool / MCPToolWrapper
```

## 11. MCP client architecture

### 11.1 Config y transport

Los configs son union de stdio, HTTP y SSE (`mcp/config.py:12-123`). `MCPClient` recibe un `BaseTransport`, conecta un `mcp.ClientSession`, inicializa protocolo y ofrece tools/prompts/resources (`mcp/client.py:54-90`, `:139-185`). Detecta el transport para eventos (`mcp/client.py:114-137`).

```text
# verified path:line: lib/crewai/src/crewai/mcp/config.py:12-123
Agent.mcps[]
   ├─ MCPServerStdio(command,args,env)
   ├─ MCPServerHTTP(url,headers,streamable=True)
   ├─ MCPServerSSE(url,headers)
   ├─ "https://server/mcp[#tool]"
   └─ "amp-slug[#tool]"
```

HTTP usa el Streamable HTTP client del SDK (`mcp/transports/http.py:61-97`). Stdio crea un proceso con environment mergeable y un hook opcional que puede filtrar credenciales (`mcp/transports/stdio.py:13-20`, `:69-112`). SSE es un transport separado importado por client y resolver (`mcp/client.py:29-32`, `mcp/tool_resolver.py:26-28`).

### 11.2 Resolver

`MCPToolResolver.resolve()` clasifica cada referencia como HTTPS, AMP string o config nativa (`mcp/tool_resolver.py:68-88`). En config nativa:

1. crea transport/client de discovery;
2. conecta y lista tools;
3. aplica tool_filter;
4. convierte JSON Schema a Pydantic;
5. crea `MCPNativeTool` con client factory;
6. cada invocation obtiene cliente/transporte fresco (`mcp/tool_resolver.py:313-458`).

```text
# verified path:line: lib/crewai/src/crewai/mcp/tool_resolver.py:313-458
MCP config/reference
       │
       ▼
MCPToolResolver
       │ discovery client
       ├─ initialize session
       ├─ list_tools
       ├─ filter + sanitize names
       ├─ JSON Schema -> Pydantic args schema
       └─ MCPNativeTool(client_factory, original_tool_name)
                    │ per call
                    ▼
          fresh transport + MCPClient
                    │
                 call_tool
```

URLs HTTPS legacy usan `MCPToolWrapper` on-demand (`mcp/tool_resolver.py:219-276`). AMP refs consultan CrewAI+ para obtener configs y luego reutilizan el camino nativo (`mcp/tool_resolver.py:118-217`). La arquitectura incluye, por tanto, una dependencia remota opcional en la resolución AMP, pero no en configs stdio/HTTP/SSE explícitos.

### 11.3 Dirección del protocolo

Todo el grafo anterior es **cliente**. `crewai.mcp` no contiene un servidor general que exponga CrewAI como MCP. El helper de `@CrewBase` llamado `get_mcp_tools()` usa un adapter de `crewai_tools` para conectar servidores (`project/crew_base.py:311-334`). En esta auditoría, “MCP nativo” significa cliente y tool ingestion; dibujar una flecha de clientes externos hacia un servidor CrewAI sería no encontrado en el código.

## 12. Unified Memory architecture

### 12.1 Objeto y storage

`Memory` es standalone, LLM-analyzed y pluggable. Defaults: LLM `gpt-5.4-mini`, storage `lancedb`, embedder OpenAI, weights 0.5 semantic / 0.3 recency / 0.2 importance (`memory/unified_memory.py:76-115`). Storage string se resuelve a custom backend, Qdrant Edge, LanceDB o LanceDB con path (`memory/unified_memory.py:232-251`).

```text
# verified path:line: lib/crewai/src/crewai/memory/unified_memory.py:76-159
Memory
 ├─ analysis LLM (lazy)
 ├─ embedder (lazy)
 ├─ StorageBackend
 │    ├─ LanceDB default
 │    ├─ Qdrant Edge
 │    └─ custom registered/path-backed
 ├─ root_scope
 ├─ scoring config
 ├─ EncodingFlow
 └─ RecallFlow
```

`MemoryRecord` es la unidad persistida: content, scope, categories, metadata, importance, timestamps, embedding, source y privacy (`memory/types.py:20-73`). Embedding se excluye de serialización; tests lo verifican (`tests/memory/test_unified_memory.py:76-89`).

### 12.2 Scope model

Crew con `memory=True` crea root `/crew/<sanitized-name>` y usa embedder/LLM del Crew/agent (`lib/crewai/src/crewai/crew.py:638-670`). Flow auto-crea root `/flow/<flow-name>` (`flow/runtime/__init__.py:798-805`). `MemoryScope` prefija todo bajo un root y `MemorySlice` consulta múltiples roots con merge/re-ranking (`memory/memory_scope.py:38-168`, `:227-324`).

```text
# verified path:line: lib/crewai/src/crewai/crew.py:638-670
Backing Memory
 ├─ /crew/research-crew/...
 │    ├─ agent/source/category scopes inferred by LLM
 │    └─ explicit subscopes
 ├─ /flow/order-processing/...
 └─ arbitrary user scopes

Views:
  MemoryScope(root=/crew/research-crew)
  MemorySlice(scopes=[/team/a, /team/b], read_only=True)
```

### 12.3 Save path

`remember()` envía una unidad al pool serializado y bloquea hasta obtener `MemoryRecord` (`memory/unified_memory.py:430-521`). `remember_many()` retorna inmediatamente y ejecuta encoding en background (`:523-665`). `_encode_batch()` crea `EncodingFlow`, que analiza, embebe, deduplica/consolida y persiste (`:372-428`; detalle del pipeline en `memory/encoding_flow.py:75-80`, `:426-462`).

```text
# verified path:line: lib/crewai/src/crewai/memory/unified_memory.py:372-428
remember / remember_many
          │
          ▼
serialized save pool (one worker)
          │
          ▼
EncodingFlow
  1. analyze/infer fields
  2. embeddings batch
  3. search similar records
  4. consolidation plan (insert/update/delete)
  5. StorageBackend write
          │
          ▼
MemorySaveCompleted/Failed events
```

### 12.4 Recall path

`recall()` primero drena writes pendientes (`memory/unified_memory.py:711-713`). Shallow embebe query, busca una vez, filtra private y calcula composite score (`:734-763`). Deep crea `RecallFlow`, que analiza query, genera subqueries/scopes, busca y enruta por confidence (`:764-782`; campos threshold en `memory/types.py:226-286`).

```text
# verified path:line: lib/crewai/src/crewai/memory/unified_memory.py:681-816
recall(query, depth)
    │
    ├─ read barrier: drain_writes
    │
    ├─ shallow
    │    ├─ embed query
    │    ├─ vector search
    │    ├─ privacy filter
    │    └─ semantic+recency+importance rank
    │
    └─ deep
         ├─ RecallFlow query analysis
         ├─ targeted queries + scopes
         ├─ parallel search
         ├─ confidence router
         └─ optional exploration -> final results
```

### 12.5 Inserción en Agent

Agent retrieval usa `task.description`, llama `unified_memory.recall(limit=5)` y añade `Relevant memories` al prompt (`lib/crewai/src/crewai/agent/core.py:557-620`). Guardado posterior ocurre desde el executor/base memory methods y se drena antes de cierre. Además, memory tools permiten que el LLM recuerde/recupere explícitamente (`lib/crewai/src/crewai/crew.py:1768-1780`). Hay así dos canales: contexto automático pre-LLM y tool calls deliberadas.

### 12.6 Lo que no existe

No hay subsistemas activos ShortTermMemory, LongTermMemory, EntityMemory y ContextualMemory en el directorio auditado. Los nombres legacy `long`, `short`, `entity`, `external` solo se convierten a `memory` en reset (`lib/crewai/src/crewai/crew.py:2211-2235`). La “contextual memory” de la narrativa es el resultado de recall insertado en prompt, no un storage adicional.

## 13. Flow architecture

### 13.1 Separación de módulos

`crewai.flow.flow` declara explícitamente cuatro concerns:

- DSL (`@start`, `@listen`, `@router`, `or_`, `and_`);
- `FlowDefinition` serializable;
- runtime engine;
- conversational mixin (`flow/flow.py:1-34`).

El public `Flow` hereda `_ConversationalMixin, RuntimeFlow[T]` (`flow/flow.py:33-34`). Esto corrige el diagrama antiguo que trataba `flow.py` como implementación monolítica.

### 13.2 Definition build

`@start` crea `StartMethod` y fusiona `FlowMethodDefinition(start=...)` (`flow/dsl/_start.py:54-68`). `@listen` crea `ListenMethod` con condición (`flow/dsl/_listen.py:45-55`). `@router` registra router, condition y eventos emitidos; puede inferir outputs desde `Literal`/Enum (`flow/dsl/_router.py:86-164`). `FlowMeta` y el runtime transforman esa metadata en `_definition` y `_methods` (`flow/runtime/__init__.py:749-846`).

```text
# verified path:line: lib/crewai/src/crewai/flow/dsl/_router.py:142-162
Python methods + decorators
          │
          ▼
FlowMethodDefinition per method
  ├─ do: action reference
  ├─ start condition
  ├─ listen condition
  ├─ router: bool
  ├─ emit labels
  ├─ persist config
  └─ human-feedback config
          │
          ▼
FlowDefinition (serializable)
          │
          ▼
RuntimeFlow._methods bound callables
```

### 13.3 Kickoff y state

`Flow.kickoff` valida exclusión de checkpoint vs restore-state, aplica checkpoint, puede devolver stream y envuelve el camino async (`flow/runtime/__init__.py:1920-1983`). `kickoff_async` configura baggage/contextvars, usage listener, limpia/restaura estado, aplica inputs y ejecuta starts (`:1985-2153` y continuación). Generic `Flow[StateModel]` fija `_initial_state_t` mediante `__class_getitem__` (`:734-740`).

Flow puede persistir por `@persist`, usar un backend resuelto y restaurar por state id; también soporta el sistema separado `CheckpointConfig`. El runtime prohíbe mezclar ambos parámetros en el mismo kickoff (`:1949-1954`, `:2015-2020`).

### 13.4 Dispatch

`_execute_start_method` ejecuta start y dispara listeners tanto por nombre del método como por label retornado si el start es router (`flow/runtime/__init__.py:2442-2493`). `_execute_method` ejecuta coroutine directamente o sync vía `asyncio.to_thread`, auto-await si un método sync devuelve coroutine y procesa human feedback (`:2532-2599`).

`_execute_listeners` tiene semántica en dos fases: routers repetidos secuencialmente, luego listeners normales paralelos. La condición `and_` acumula eventos en `_pending_events`; `or_` evita doble fire mediante `_fired_or_listeners` (`flow/runtime/__init__.py:2727-2894`).

```text
# verified path:line: lib/crewai/src/crewai/flow/runtime/__init__.py:2727-2844
trigger(method_name, result)
          │
          ▼
find routers for trigger
          │
          ├─ execute router 1 -> label A
          ├─ find router for A -> label B
          └─ repeat until no router
          │
          ▼
all triggers = method_name + labels
          │
          ├─ evaluate and_/or_ conditions
          ├─ racing group if configured
          └─ normal listeners -> asyncio.gather(parallel)
```

Esta semántica permite branching determinista de control y paralelismo fan-out. No equivale a Process.hierarchical: Flow decide qué método se ejecuta; Process decide qué Agent ejecuta una Task dentro de una lista.

## 14. Eventos, tracing, checkpoints y files como cross-cutting layers

### Event bus

Crew, Agent, Task, LLM, tools, MCP, Memory y Flow emiten eventos. Ejemplos: `CrewKickoffCompletedEvent` (`lib/crewai/src/crewai/crew.py:1914-1922`), Task events (`task.py:787-794`, `:749-757`), LLM events importados por `BaseLLM` (`llms/base_llm.py:31-44`), MCP events (`mcp/client.py:20-28`), Memory events (`memory/unified_memory.py:16-24`) y Flow method events (`flow/runtime/__init__.py:2551-2563`).

```text
# verified path:line: lib/crewai/src/crewai/memory/unified_memory.py:16-24
Crew ─┐
Task ─┤
Agent ┤
LLM ──┤
Tool ─┼──> crewai_event_bus ──> tracing / telemetry / listeners
MCP ──┤
Memory┤
Flow ─┘
```

El orden de finalización importa. Crew y Flow drenan memory antes de emitir finished events (`lib/crewai/src/crewai/crew.py:1865-1913`, `flow/runtime/__init__.py:959-973`). El runtime del event bus mantiene scopes de ejecución en kickoff para aislamiento (`lib/crewai/src/crewai/crew.py:1031-1068`, `flow/runtime/__init__.py:1973-1983`).

### Checkpoint y replay

Crew acepta `CheckpointConfig` en kickoff y puede replay desde task id usando outputs persistidos (`lib/crewai/src/crewai/crew.py:978-998`, `:1961-1999`). Flow acepta checkpoint y persist state id, pero no ambos a la vez (`flow/runtime/__init__.py:1949-1957`). Tool classes y LLM refs poseen registries/serializers para reconstrucción (`tools/base_tool.py:48-77`, `agents/agent_builder/base_agent.py:70-121`).

### Files

`crewai-files` es opcional/importado defensivamente. `BaseLLM` intenta `format_multimodal_content` (`llms/base_llm.py:54-59`), Agent/Crew inyecta `ReadFileTool` solo si el provider no auto-ingiere el content type (`lib/crewai/src/crewai/crew.py:1663-1689`), y Task normaliza input file paths si el paquete existe (`task.py:469-485`). Esto resuelve el pendiente del doc anterior: `crewai-files` proporciona types/formateo/procesamiento de archivos que cruza LLM, Task y Crew, no es simplemente Knowledge storage.

## 15. Diagrama end-to-end

```text
# verified path:line: lib/crewai/src/crewai/crew.py:978-1068
YAML/@CrewBase OR programmatic Agent/Task/Crew
                       │
                       ▼
                 Crew.kickoff
                       │ prepare inputs/files/checkpoint/events
                       ▼
        Process.sequential OR Process.hierarchical
             │                    │
       task.agent             manager_agent
             └─────────┬──────────┘
                       ▼
            prepare_task_execution
                       │ inject delegation/MCP/memory/file/tools
                       ▼
                Task.execute_sync
                       │
                Agent.execute_task
                       │ prompt + context + memory + knowledge + skills
                       ▼
        AgentExecutor Flow[AgentExecutorState]
                       │
      ┌────────────────┼───────────────────┐
      │                │                   │
     LLM            BaseTool            Memory
 native/LiteLLM   local/MCP/delegate   recall/remember
      │                │                   │
      └────────────────┼───────────────────┘
                       ▼
                  AgentFinish
                       │ guardrail/structured output/callback/file
                       ▼
                   TaskOutput
                       │ context for next task
                       ▼
                   CrewOutput
                       │ drain memory + flush events
                       ▼
                    caller
# verified path:line: lib/crewai/src/crewai/crew.py:1897-1933
```

Cada arista está respaldada por call sites: Crew a Task (`lib/crewai/src/crewai/crew.py:1592-1598`), Task a Agent (`task.py:790-794`), Agent a executor (`lib/crewai/src/crewai/agent/core.py:879-894`), executor a LLM/tools (`experimental/agent_executor.py:1403-1609`), Agent a memory (`lib/crewai/src/crewai/agent/core.py:557-620`) y Crew a output (`lib/crewai/src/crewai/crew.py:1897-1933`).

## 16. Contraste explícito con `crewai.md`

El documento previo acierta en el modelo de alto nivel, pero su diagrama necesita cambios arquitectónicos.

| Elemento de `crewai.md` | Código del HEAD | Cambio al diagrama |
|---|---|---|
| Seis paquetes workspace (`crewai.md:42`) | `pyproject.toml:231-239` | Confirmar. |
| Crew con process sequential/hierarchical (`:49-52`) | `process.py:4-11`, `lib/crewai/src/crewai/crew.py:1033-1042` | Confirmar; consensual solo TODO. |
| `flow/` como `Flow[State]` (`:52`) | `flow/flow.py:1-34`, runtime separado | Dividir DSL / definition / runtime / mixin. |
| Memory Unified (`:53`, `:100-102`) | `memory/unified_memory.py:1`, `:76-159` | Confirmar; quitar cajas short/long/entity. |
| MCP nativo (`:55`, `:104-106`) | configs/resolver cliente `mcp/config.py:12-123`, `tool_resolver.py:313-458` | Etiquetar “MCP client”; no dibujar server core. |
| Crew cache default True (`:94`) | `lib/crewai/src/crewai/crew.py:221-230` default False | Corregir. |
| Agent multimodal/reasoning como novedades (`:86`) | deprecados `lib/crewai/src/crewai/agent/core.py:251-255`, `:277-285` | Marcar legacy; usar files/planning_config. |
| Call stack Agent → LLM (`:142-149`) | Agent → default AgentExecutor Flow → LLM/tools | Insertar executor Flow-based. |
| Hierarchical manager “planifica” (`:98`, `:123`) | manager/delegation `lib/crewai/src/crewai/crew.py:1496-1526`; planning separado `:330-342` | Separar jerarquía de planning. |
| Flow puede invocar Crew (`:77-80`) | sync methods aislados en to_thread `flow/runtime:2572-2584` | Confirmar y explicar boundary async. |
| “contextual memory” implícita | retrieval en prompt `lib/crewai/src/crewai/agent/core.py:557-620` | Mostrar como data flow, no storage. |

El diagrama de `crewai.md:154-171` conecta Agent/Task/Tools/Memory, lo cual es direccionalmente correcto. Sin embargo, omite que el manager es el agente ejecutor de toda task hierarchical y que la delegación ocurre vía tools; omite `AgentExecutor`; dibuja “cache default True” en prose; y no refleja el split de Flow. Este documento no invalida el resumen conceptual “Crews autonomía, Flows control”, pero lo sustituye para decisiones de implementación.

## 17. Interfaces de extensión reales

### Custom Agent

`BaseAgent` es ABC para terceros (`agents/agent_builder/base_agent.py:200-253`). Debe preservar role/goal/backstory y métodos abstractos de ejecución/tool/delegación. Sin embargo, la ruta normal usa `Agent`; un custom BaseAgent debe integrarse con Crew validators y executor lifecycle.

### Custom LLM

Heredar `BaseLLM` e implementar `call()` (`llms/base_llm.py:150-167`, `:311-347`). `create_llm` conserva instancias (`utilities/llm_utils.py:26-27`). Esta es la extensión más limpia para modelos fuera de LiteLLM.

### Custom Tool

Heredar `BaseTool`, declarar name/description y `_run`; schema puede inferirse (`tools/base_tool.py:102-152`, `:199-240`, `:374-390`). Para async real, implementar `_arun` (`:332-364`).

### Custom Memory backend

Implementar `StorageBackend` y pasar instancia a `Memory.storage`; `Memory.model_post_init` acepta objeto directamente (`memory/unified_memory.py:92-95`, `:232-251`). El ranking/flows permanecen arriba del backend.

### Custom Flow persistence

Flow resuelve `FlowPersistence` desde definición o instancia (`flow/runtime/__init__.py:771-778`, `:2700-2715`). Persistencia y checkpoint son sistemas distintos.

### Custom MCP policy

Config tool_filter filtra discovery (`mcp/config.py:43-49`, `:80-87`, `:113-119`), y stdio ofrece `_env_filter_hook` para políticas de environment (`mcp/transports/stdio.py:13-20`, `:86-96`). Es una extensión de seguridad importante para enterprise.

## 18. Consecuencias para Aithera

### Patrón 1: unificar capacidades bajo Tool

CrewAI adapta delegación, memory, MCP y files al mismo contrato. Aithera puede evitar branches especiales en el loop: toda capacidad debería exponer nombre, schema, política, límites y resultado terminal. Evidencia de composición en `lib/crewai/src/crewai/crew.py:1623-1690` y contrato en `tools/base_tool.py:138-190`.

### Patrón 2: separar orquestación de asignación

El mismo `_execute_tasks` sirve para sequential e hierarchical (`lib/crewai/src/crewai/crew.py:1487-1494`). Aithera puede tener un Orchestrator que elige ejecutor/targets sin duplicar task lifecycle. El manager debería delegar por tools auditables, no por llamadas internas invisibles.

### Patrón 3: usar un runtime event-driven también dentro del agente

`AgentExecutor` como Flow demuestra reutilización de routers/state/persistence para loop interno (`experimental/agent_executor.py:164-177`). Aithera podría usar su Automation Engine tanto para flows de usuario como para plan/tool/observe del agente, siempre que proteja límites de complejidad.

### Patrón 4: memory namespaced, no cuatro stores rígidos

Root scopes por crew/flow (`lib/crewai/src/crewai/crew.py:638-670`, `flow/runtime:798-805`) son más composables que short/long/entity separados. Aithera MOS ya tiene tipos semánticos; puede adoptar scope views y slices sobre stores, conservando sus contratos propios.

### Patrón 5: native-first con fallback explícito

CrewAI intenta clases nativas y usa LiteLLM como extra (`llm.py:477-510`). Aithera debería registrar providers por capabilities, pero evitar dos listas divergentes como `SUPPORTED_NATIVE_PROVIDERS` y `constants.PROVIDERS`.

### Patrón 6: barreras de lifecycle

Drenar memory antes de finished event (`lib/crewai/src/crewai/crew.py:1865-1913`) es esencial. Aithera debe definir orden formal: tool results → memory writes → telemetry flush → completion event → adapter response.

### Riesgos si se copia literalmente

- threads para task async y asyncio para Flow pueden complicar cancelación;
- resolver MCP usa `asyncio.run`/thread según contexto (`mcp/tool_resolver.py:355-381`);
- dos executors coexisten durante transición (`lib/crewai/src/crewai/agent/core.py:150-163`, `:337-344`);
- aliases de providers y listas duplicadas dificultan capability discovery;
- `AgentExecutor` está en namespace experimental aunque sea default, señal de API en movimiento.

## 19. Casos no encontrados o no demostrables

- **Process consensual**: no encontrado; solo TODO en `process.py:11`.
- **Servidor MCP core**: no encontrado en `crewai.mcp`; cliente sí.
- **Short/Long/Entity/Contextual como cuatro clases activas**: no encontrado en `crewai/memory`; aliases legacy de reset sí.
- **Hierarchical activa planning automáticamente**: no encontrado; son flags/config separados.
- **Todos los providers funcionan hoy**: no demostrado sin APIs/credenciales; solo routing y adapters verificados.
- **El HEAD corresponde exactamente al tag 1.15.2**: `__version__` sí; `git tag --points-at HEAD` no devolvió tag en el clone shallow.
- **Métricas live de adopción**: fuera de alcance; esta arquitectura no usa stars como evidencia.

## 20. Validación CONSTITUTION §8 — 6/6

| Criterio | Evidencia en este documento | Estado |
|---|---|---|
| Código revisado, commit/branch citados | commit full al inicio; imports, classes y calls con `path:line` | ✅ |
| Fuentes contrastadas, mínimo dos para claims clave | implementación + tests upstream + manifests; referencias detalladas en companion audit | ✅ |
| Compatibilidad documentada | Python, paquete, workspace, transports y provider families | ✅ |
| Ejemplos verificados | diagramas derivados de calls; snippets copiados del source; tests `test_crew.py`, `test_flow.py`, `tests/mcp`, `tests/memory` citados en el audit | ✅ |
| Referencias cruzadas | [`crewai.md`](./crewai.md), [`crewai-code-audit.md`](./crewai-code-audit.md), CONSTITUTION | ✅ |
| Revisión independiente | spot-check mecánico de citations + tests upstream como verificador de recorridos; firma humana nominal no afirmada | ✅ con salvedad |

La salvedad es la misma del companion: la revisión es independiente a nivel de mecanismo/fuente, pero no se inventa la firma de una segunda persona. Si §8 exige nombre de auditor humano, debe añadirse posteriormente.

## Fuentes

1. `crewAIInc/crewAI`, commit `fb8e93be25d97776cf18368c3ac56e7ac69661b9`.
2. `pyproject.toml` y `lib/crewai/pyproject.toml`.
3. `lib/crewai/src/crewai/crew.py`, `task.py`, `agent/core.py`.
4. `lib/crewai/src/crewai/experimental/agent_executor.py`.
5. `lib/crewai/src/crewai/flow/flow.py`, `flow/dsl/*`, `flow/runtime/__init__.py`.
6. `lib/crewai/src/crewai/llm.py`, `llms/base_llm.py`, `llms/providers/*`.
7. `lib/crewai/src/crewai/tools/base_tool.py`, `mcp/*`.
8. `lib/crewai/src/crewai/memory/*`.
9. Tests upstream bajo `lib/crewai/tests/` enumerados en [`crewai-code-audit.md`](./crewai-code-audit.md).

## Nivel de confianza

**95%** para boundaries, call graph y relaciones representadas. La confianza proviene de leer implementaciones y call sites del commit fijado. El 5% descontado cubre no ejecutar integraciones de red/LLM reales, no auditar cada backend/provider/A2A y la transición activa entre executors. Ninguna caja no encontrada se presenta como implementada.

## Changelog

### 2026-07-13 — versión inicial

- Diagrama real del workspace y API pública.
- Separación Crew loop vs Flow runtime.
- Grafo de carga YAML y creación de objetos.
- Secuencias sequential/hierarchical y ausencia de consensual.
- AgentExecutor Flow-based incluido en el call stack.
- Capas LLM, BaseTool, MCP cliente y Unified Memory.
- Contraste explícito con `crewai.md`.
- Implicaciones y límites para Aithera.
