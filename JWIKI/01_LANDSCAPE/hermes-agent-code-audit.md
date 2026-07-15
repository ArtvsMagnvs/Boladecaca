# Hermes Agent — auditoría técnica del código fuente real (commit `f96b2e6`)

## Resumen

Este documento sustituye la lectura de marketing por una auditoría del código real de `NousResearch/hermes-agent`. El repositorio se clonó con `git clone --depth 1` y se inspeccionó en el commit completo `f96b2e6ef75ba6ed678c99954bc8f3ee7f6a38ba` de `main`, fechado 2026-07-13. La versión declarada por Python sigue siendo `0.18.2`, pero el `HEAD` auditado contiene cambios posteriores al commit `9de9c25` de la release `v2026.7.7.2`; por tanto, este análisis describe **main post-release**, no una reconstrucción exacta de la etiqueta.

La conclusión central es que Hermes no es un paquete convencional bajo `src/hermes_agent/`. Es una aplicación monorepo Python/TypeScript con módulos top-level, varios “god files” aún grandes y una refactorización progresiva hacia módulos especializados. El agent loop real vive en `agent/conversation_loop.py`; `run_agent.py` conserva la clase pública `AIAgent` y un forwarder por compatibilidad. MCP funciona en las dos direcciones: Hermes es cliente de servidores externos mediante `tools/mcp_tool.py` y también expone un servidor MCP de mensajería mediante `mcp_serve.py`. Skills, MoA, gateway, memoria y TTS son implementaciones reales, pero varias frases de [hermes-agent.md](./hermes-agent.md) mezclan arquitectura, release notes y claims de producto de una manera que requiere corrección.

## Objetivo

1. Identificar los entry points, dependencias y organización real del repo.
2. Reconstruir el agent loop, la ejecución de tools y la persistencia con citas `path:line`.
3. Verificar MCP cliente/servidor, carga de skills, providers, MoA, mensajería y TTS.
4. Auditar la postura de seguridad y distinguir CVEs de dependencias, GHSAs mencionadas en código y advisories públicos.
5. Contrastar afirmaciones concretas del documento previo `JWIKI/01_LANDSCAPE/hermes-agent.md`.
6. Producir material trazable para decisiones de Aithera, sin convertir claims promocionales en hechos.

## Estado

🟢 **Verificado contra código clonado.**

- Repo auditado: `https://github.com/NousResearch/hermes-agent`.
- Branch: `main`.
- Commit: `f96b2e6ef75ba6ed678c99954bc8f3ee7f6a38ba`.
- Fecha del commit: `2026-07-13T16:15:04+05:30`.
- Asunto: `fix(whatsapp_cloud): gate interactive taps on DM allowlist`.
- Release pública contrastada: `v2026.7.7.2`, nombre `Hermes Agent v0.18.2`, commit de release `9de9c25`, publicada cinco días antes del audit según GitHub el 2026-07-13.
- El API REST anónimo y shields.io devolvieron HTTP 403 por rate limit. Se aplicó el fallback requerido: una consulta a la página HTML de GitHub confirmó `214k` stars, `39.7k` forks y la release; esos números redondeados no se usan para inferir valores exactos.
- El checkout tiene 6.282 archivos rastreados, 2.080 paths de tests, 112 módulos Python inmediatos bajo `tools/`, 174 `SKILL.md` rastreados entre `skills/` y `optional-skills/`, 20 directorios en `plugins/platforms/` y 8 providers de memoria empaquetados.

## Versiones compatibles

| Componente | Evidencia auditada | Interpretación |
|---|---|---|
| Hermes Agent | `pyproject.toml:8-12` declara `0.18.2` | La versión de paquete no cambió en el `main` auditado aunque hay commits post-release. |
| Python | `pyproject.toml:13-20` exige `>=3.11,<3.14` | 3.14 se rechaza deliberadamente hasta que transitivos Rust dispongan de wheels. |
| Build backend | `pyproject.toml:1-6` usa setuptools `>=77,<83` | El formato SPDX string de PEP 639 requiere ese floor. |
| Node | `package.json:43-45` exige `>=20.0.0` | Aplica a workspaces web/TUI/desktop, no al agent core Python solo. |
| MCP SDK | `pyproject.toml:200-207` fija `mcp==1.26.0` y Starlette `1.0.1` en el extra `mcp` | MCP es opcional; el código degrada a “disabled” si no está instalado. |
| ACP | `pyproject.toml:217` fija `agent-client-protocol==0.9.0` | El executable es `hermes-acp`. |
| TTS | `pyproject.toml:143-179,218-226` distribuye SDKs por extras/lazy install | Edge, ElevenLabs, Mistral y voz local no son todos deps core. |
| Terminal | `hermes_cli/web_server.py:623-628` enumera `local`, `docker`, `ssh`, `modal`, `daytona`, `singularity` | Seis backends públicos; `managed_modal` es un modo de Modal, no un séptimo selector. |
| Release auditada | GitHub release `v2026.7.7.2` apunta a `9de9c25`; checkout a `f96b2e6` | Los números de línea son válidos para `f96b2e6`, no necesariamente para el tag. |

## Proyectos compatibles

Hermes es una aplicación, no una librería destinada a ser embebida por Aithera. Sus seams de interoperabilidad reales son:

- proveedores de inferencia directos, OAuth, agregadores y endpoints OpenAI/Anthropic compatibles;
- clientes MCP stdio, Streamable HTTP y SSE;
- servidor MCP stdio para leer conversaciones y operar el bridge de mensajería;
- ACP para IDEs;
- gateway de adaptadores propios y plugins;
- API server agentic compatible con OpenAI;
- proxy OAuth compatible con OpenAI, separado del API server;
- skills `SKILL.md` con frontmatter y progressive disclosure;
- plugins de memoria mediante `MemoryProvider`.

La lista literal `PROVIDER_REGISTRY` contiene 33 entradas en `hermes_cli/auth.py:176-445`, y el picker canónico contiene 37 entradas antes de auto-extensión en `hermes_cli/models.py:1052-1090`. No debe traducirse esto a “37 modelos”: son **rutas/provider slugs**, algunas OAuth, algunas locales, algunas regionales y algunas agregadoras. Nous Portal anuncia 300+ modelos en el texto del picker (`hermes_cli/models.py:1053`), pero la cantidad es un claim de servicio dinámico, no un catálogo estático probado por el repo.

## Dependencias

### Core

`pyproject.toml:24-141` declara 30 dependencias core. Incluye OpenAI SDK, HTTP, CLI, serialización YAML, Pydantic, cron, JWT/crypto, FastAPI/uvicorn, PTY multiplataforma, Pillow y logging concurrente en Windows. La intención escrita es minimizar blast radius y mover backends específicos a extras (`pyproject.toml:25-44`).

Hay una discrepancia interna importante: el comentario dice “every direct dep is exact-pinned”, pero el propio array usa rangos para `urllib3`, `fastapi`, `uvicorn`, `python-multipart`, `ptyprocess` y `pywinpty` (`pyproject.toml:87-118`). El documento previo repite la política como una verdad absoluta. La formulación correcta es: **la mayoría de deps core está exact-pinned, con excepciones explícitas de rango**. Los extras también contienen rangos, por ejemplo `hindsight-client>=0.6.1` en el plugin y `fastapi>=0.104.0,<1` en core.

### Extras

Hay 42 grupos en `[project.optional-dependencies]` (`pyproject.toml:143-305`): providers, web search, image, terminal cloud, memoria, dev/MCP, messaging, Matrix, voice/TTS, ACP, Google, Termux, Teams y otros. La intención de lazy install está documentada en `pyproject.toml:187-225` y en la política de `[all]` (`pyproject.toml:273-305`).

### Entry points

Snippet verificado — `pyproject.toml:307-313`:

```toml
[project.scripts]
hermes = "hermes_cli.main:main"
hermes-agent = "run_agent:main"
hermes-acp = "acp_adapter.entry:main"

[tool.setuptools]
py-modules = ["run_agent", "model_tools", "toolsets", "batch_runner", ...]
```

Esto demuestra por qué buscar solamente `src/hermes_agent/` falla: los módulos principales son top-level y setuptools encuentra paquetes `agent`, `tools`, `gateway`, `hermes_cli`, `tui_gateway`, `cron`, `acp_adapter`, `plugins` y `providers` mediante `pyproject.toml:356-357`.

## Arquitectura

La arquitectura detallada y los diagramas ampliados están en [hermes-agent-architecture.md](./hermes-agent-architecture.md). La forma mínima demostrable es:

```text
CLI / TUI / Desktop / Gateway / ACP / API Server
                         │
                         ▼
                    AIAgent
         run_agent.py (API estable / forwarders)
                         │
                         ▼
       agent.conversation_loop.run_conversation
         │ prompt/context │ provider transport
         │                ▼
         │      OpenAI / Anthropic / Bedrock /
         │      Codex Responses / MoA facade
         ▼
  OpenAI-format tool schemas
         │
         ▼
 model_tools.handle_function_call
         │ middleware / hooks / scope
         ▼
 tools.registry.ToolRegistry.dispatch
         │
         ├── tools nativas
         ├── tools de plugins
         ├── tools MCP dinámicas
         └── tools de MemoryProvider
```

Tres propiedades dominan el diseño:

1. **Compatibilidad preservada mientras se extraen god-files.** `run_agent.py` sigue exponiendo `AIAgent`, pero su `run_conversation()` solo importa y delega (`run_agent.py:5787-5810`). El loop real tiene 5.355 líneas en `agent/conversation_loop.py`.
2. **Narrow waist de tools.** Cada módulo se registra en el singleton `ToolRegistry`; `model_tools.py` filtra schemas por toolsets y requisitos antes de enviarlos al modelo (`model_tools.py:279-354,357-445`).
3. **Edges extensibles.** Platforms, memory providers, model providers, MCPs y skills crecen en plugins/directorios sin obligar a convertir cada capability en core.

## Descripción técnica

### 1. Estructura real del repositorio

No hay un `src/` central. Los componentes relevantes son:

| Ruta | Responsabilidad real |
|---|---|
| `run_agent.py` | Clase pública `AIAgent`, estado y forwarders hacia módulos extraídos. |
| `agent/` | Loop, inicialización, transports, providers auxiliares, memoria, MoA, prompt, compresión y lifecycle. |
| `model_tools.py` | Descubrimiento, filtrado y dispatch de tools. |
| `tools/` | 112 módulos inmediatos; cada tool se autorregistra. |
| `toolsets.py` | Bundles/posturas de tools enviados al modelo. |
| `hermes_cli/` | Config, auth, model picker, setup y subcomandos. |
| `gateway/` | Runtime multi-canal, adapters built-in, routing, sesiones y API server. |
| `plugins/platforms/` | 20 directorios de plataformas empaquetadas como plugins. |
| `plugins/memory/` | 8 memory providers empaquetados. |
| `mcp_serve.py` | Servidor MCP stdio de bridge de conversaciones. |
| `tools/mcp_tool.py` | Cliente MCP, conexiones, discovery y registro dinámico de tools. |
| `acp_adapter/` | Servidor ACP y bridge de permisos/tools para IDEs. |
| `cron/` | Jobs y scheduler. |
| `skills/`, `optional-skills/` | Catálogo fuente; el runtime activo usa `$HERMES_HOME/skills` y external dirs. |
| `ui-tui/`, `apps/`, `web/`, `website/` | TUI, desktop/workspaces, dashboard y docs. |

El repo conserva archivos muy grandes: `gateway/run.py` ~1,04 MB, `cli.py` ~765 KB, `hermes_state.py` ~319 KB, `agent/conversation_loop.py` ~311 KB y `run_agent.py` ~278 KB. No es correcto presentar `run_agent.py` como el único monolito: el equipo extrajo el loop, pero gateway y CLI todavía concentran gran complejidad.

### 2. Agent loop real

`AIAgent.run_conversation()` es ahora un forwarder:

```python
# run_agent.py:5787-5810
def run_conversation(...):
    """Forwarder — see ``agent.conversation_loop.run_conversation``."""
    from agent.conversation_loop import run_conversation
    return run_conversation(self, user_message, system_message, ...)
```

El loop verdadero comienza en `agent/conversation_loop.py:523-533`. El prologue delega a `build_turn_context()` (`agent/conversation_loop.py:568-603`) para construir/restaurar system prompt, sanear entrada, hidratar todo/memory y persistir de forma crash-safe. Luego mantiene límites duales: `max_iterations` e `iteration_budget` (`agent/conversation_loop.py:605-627,643-668`).

Antes de cada request:

- repara secuencias de roles y tool results;
- elimina thinking-only turns del copy API, sin borrar el transcript;
- normaliza whitespace y JSON de tool calls para mejorar prompt/KV caching (`agent/conversation_loop.py:900-951`);
- sanea surrogates problemáticos de modelos Ollama/Qwen/GLM (`:953-957`);
- estima presión incluyendo schemas (`:959-969`);
- comprime preventivamente si rebasa threshold (`:988-1063`).

El request usa middleware, hooks y streaming preferente (`agent/conversation_loop.py:1156-1285`). El dispatch concreto no está cableado a una sola API: valida `codex_responses`, `anthropic_messages`, `bedrock_converse` o el transport normalizado de chat completions (`agent/conversation_loop.py:1370-1448`). Esto es una capa de transporte, no un simple `openai.chat.completions.create()` universal.

Cuando el modelo devuelve tools, valida nombres, intenta reparar typos, rechaza argumentos truncados, preserva role alternation y persiste el assistant tool-call **antes** de ejecutar efectos (`agent/conversation_loop.py:4446-4715`). Después ejecuta tools y vuelve al loop. Cuando no hay tools, toma el contenido como final (`agent/conversation_loop.py:4813-4816`) y aplica recuperaciones para stream parcial, respuesta vacía y thinking-only.

### 3. Tool discovery y dispatch

`model_tools.py:1-9` se define como capa fina sobre el registry. `discover_builtin_tools()` ocurre al importar (`model_tools.py:184-188`), mientras MCP se inicializa explícitamente por surface para evitar bloquear el event loop hasta 120 s (`model_tools.py:190-201`).

El schema provider filtra por toolsets y requisitos:

```python
# model_tools.py:357-445
if enabled_toolsets is not None:
    ... tools_to_include.update(resolve_toolset(toolset_name))
else:
    ... start with everything
...
filtered_tools = registry.get_definitions(tools_to_include, quiet=quiet_mode)
```

El singleton se crea en `tools/registry.py:755-756`. `register()` protege colisiones y exige opt-in para que un plugin reemplace una tool built-in (`tools/registry.py:356-448`). `dispatch()` resuelve sync/async, normaliza output y convierte excepciones en JSON saneado (`tools/registry.py:605-635`).

`model_tools.handle_function_call()` añade coerción de tipos, Tool Search bridge, scoping defensivo, middleware y hooks antes de `registry.dispatch()` (`model_tools.py:1025-1164,1264-1276`). Por ello el call stack inventado del documento previo —`ToolSelector.pick(task)` seguido de `Tool.run`— debe reemplazarse por nombres reales.

### 4. MCP: cliente y servidor, no uno solo

#### Cliente MCP

`tools/mcp_tool.py` soporta stdio, Streamable HTTP y SSE (`tools/mcp_tool.py:62-69`). Importa `ClientSession`, `stdio_client`, `streamablehttp_client` y opcionalmente `sse_client` (`tools/mcp_tool.py:207-233`). Cada server vive en un `MCPServerTask`, con una misma asyncio Task para que cancel scopes de anyio se abran/cierren en el contexto correcto (`tools/mcp_tool.py:1508-1516`).

El cliente:

- filtra el environment de subprocesses y solo pasa baseline más variables configuradas (`tools/mcp_tool.py:350-353,425-433`);
- descubre capacidades y evita `tools/list` en servers prompt/resource-only (`tools/mcp_tool.py:1595-1613`);
- refresca tools con `notifications/tools/list_changed` (`tools/mcp_tool.py:1662-1678`);
- prefija/normaliza nombres y evita colisiones con built-ins;
- registra tools y utility tools de resources/prompts en el registry (`tools/mcp_tool.py:4780-4842`);
- conecta servers en paralelo (`tools/mcp_tool.py:4938-4944`).

El API público `register_mcp_servers()` es idempotente, omite `enabled:false`, despierta conexiones aparcadas y registra toolsets `mcp-<server>` (`tools/mcp_tool.py:4876-4933`). `discover_mcp_tools()` carga config y reintenta solo servers faltantes (`tools/mcp_tool.py:4996-5042`).

#### Servidor MCP

`mcp_serve.py` es otra cosa: crea un `FastMCP("hermes")` con instrucciones de bridge de mensajería (`mcp_serve.py:543-558`). Expone tools como `conversations_list`, `conversation_get`, `messages_read` y attachments/approvals/event polling (`mcp_serve.py:562-722` y siguientes). Arranca por stdio con `server.run_stdio_async()` (`mcp_serve.py:959-990`).

Conclusión: Hermes es **MCP client y MCP server**. `optional-mcps/` es un catálogo empaquetado, no la implementación del cliente ni prueba de que todos estén activos.

### 5. Skills: discovery, progressive disclosure y auto-mejora

La fuente describe formato agentskills.io-compatible en `tools/skills_tool.py:3-32`. El runtime activo no lee directamente “todos los skills del repo” como única raíz. Resuelve `$HERMES_HOME/skills` y external dirs; `_find_all_skills()` escanea local primero, filtra disabled/platform/environment, cachea por firma+TTL y devuelve metadata (`tools/skills_tool.py:669-777`). `skills_list()` es tier 1: nombre, descripción y categoría (`tools/skills_tool.py:785-848`). `skill_view()` carga el body o un supporting file, soporta nombres cualificados de plugins, bloquea path traversal y detecta colisiones en lugar de adivinar (`tools/skills_tool.py:961-1218`).

Los tools se registran de verdad:

```python
# tools/skills_tool.py:1718-1759
registry.register(name="skills_list", toolset="skills", ...)
...
registry.register(name="skill_view", toolset="skills", ...)
```

`skill_manage` vive en `tools/skill_manager_tool.py`; create/edit/patch se despachan en `:1320-1368`, y las skills creadas por background review reciben provenance agent-created (`:1401-1407`).

Las slash skills son un segundo entry path. `scan_skill_commands()` recorre `SKILL.md`, filtra plataforma/environment/disabled y normaliza nombre a comando (`agent/skill_commands.py:320-387`). `reload_skills()` vuelve a escanear sin invalidar el prompt cache, porque el contenido se carga on demand (`agent/skill_commands.py:405-467`).

El “closed learning loop” sí tiene implementación concreta, pero no es magia determinista:

1. En init, `creation_nudge_interval` tiene default 10 (`agent/agent_init.py:1452-1458`).
2. Cada iteración con tools incrementa `_iters_since_skill` si `skill_manage` está disponible (`agent/conversation_loop.py:698-702`).
3. Al finalizar, si el threshold se cumple, se dispara review de skills en background, después de entregar la respuesta (`agent/turn_finalizer.py:484-510`).
4. El prompt del reviewer pide patch de skill cargada, umbrella existente, supporting file o nueva umbrella class-level (`agent/background_review.py:181-241`).
5. Bundled y hub-installed se protegen; las skills agent-created sí se pueden mantener (`agent/background_review.py:249-259`).

Por tanto: “crea y mejora skills desde experiencia” está respaldado; “lo hace siempre” no. Es best-effort, depende de que el toolset `skills` esté habilitado, del threshold, de un review LLM y de las protecciones de provenance. Curator tampoco “auto-mejora todo”: sus invariantes limitan su scope a agent-created y nunca auto-elimina, solo archiva (`agent/curator.py:15-19`).

### 6. Providers y modelos

La evidencia más sólida es `hermes_cli/auth.py:176-445`. Hay rutas para Nous, OpenAI Codex OAuth, OpenAI API, xAI OAuth/directo, Qwen OAuth, LM Studio, GitHub Copilot/API/ACP, Gemini, Z.AI, Kimi global/China, StepFun, Arcee, GMI, MiniMax direct/OAuth/China, Anthropic, Alibaba, DeepSeek, NVIDIA, OpenCode, Kilo, Hugging Face, Xiaomi, Tencent TokenHub, Ollama Cloud, Bedrock y Azure Foundry. El registry se auto-extiende con plugins de model provider (`hermes_cli/auth.py:447-475`).

Matices necesarios:

- `openrouter` se maneja fuera de ese literal registry; no confundir ausencia en el dict con falta de soporte (`hermes_cli/auth.py:457-462`).
- “Ollama” local funciona como endpoint OpenAI-compatible/autodetectado; la entrada canónica auditada es `ollama-cloud`, mientras LM Studio sí tiene slug propio (`hermes_cli/auth.py:212-219,421-427`).
- `openai-api` y `openai-codex` son rutas distintas.
- `gemini` puede usar un transport nativo; no todo termina en OpenAI wire.
- Bedrock y Azure tienen auth/transport particulares.
- “300+ modelos” es capacidad de Nous Portal, no 300 definiciones hardcoded.

### 7. MoA real

MoA es un virtual provider real, no solo un prompt. `agent/agent_init.py:846-894` construye `MoAClient`, fija outer `api_mode="chat_completions"`, usa `moa://local` como marcador y relaya eventos de referencias a todas las surfaces. El picker lo presenta como provider canónico (`hermes_cli/models.py:1053-1056`).

El código de `agent/moa_loop.py` deja claro el diseño:

- advisors son context-only, sin tools (`agent/moa_loop.py:93-117`);
- cada slot resuelve provider/model/runtime real;
- references se ejecutan en `ThreadPoolExecutor`, máximo 8, y se recogen conservando orden (`agent/moa_loop.py:336-385`);
- cada advisor se contabiliza con su propio provider/model y costo (`agent/moa_loop.py:251-323`);
- el facade `MoAChatCompletions.create()` resuelve preset, referencias y aggregator (`agent/moa_loop.py:800-834`);
- `fanout=per_iteration` reruns cuando cambia la vista por nuevos tool results; `fanout=user_turn` lo hace una vez por turno (`agent/moa_loop.py:847-884`);
- el aggregator es el modelo **actor**, recibe tools y puede continuar el loop normal (`agent/moa_loop.py:960-1022`);
- se rechaza MoA recursivo como aggregator (`agent/moa_loop.py:977-978`).

El documento previo acierta al decir que MoA aparece como provider/model. No se verificó con historia la afirmación “antes de v0.18 era un toggle”; el checkout actual no prueba por sí solo esa evolución. Debe citarse release notes o diff de tags si se conserva.

### 8. Gateway y plataformas

El contrato base es `BasePlatformAdapter`, no `ChannelAdapter`. Las subclases implementan conexión/auth, recepción, envío y media (`gateway/platforms/base.py:2276-2285`), con capabilities de async delivery, chunking y command prefix (`:2295-2346`). `set_message_handler()` y `connect()/disconnect()` son el contrato runtime (`gateway/platforms/base.py:2791-2909`).

`Platform` tiene 24 valores built-in, contando `local`, `api_server`, webhooks y relay además de mensajerías (`gateway/config.py:212-243`). También crea pseudo-members solo para plugins conocidos (`gateway/config.py:245-308`). Hay 20 directorios plugin verificados: DingTalk, Discord, email, Feishu, Google Chat, Home Assistant, IRC, LINE, Matrix, Mattermost, ntfy, Photon, Raft, SimpleX, Slack, SMS, Teams, Telegram, WeCom y WhatsApp.

`GatewayRunner._create_adapter()` consulta primero `platform_registry` y solo después cae al chain built-in (`gateway/run.py:8665-8708`). El registry valida dependencias/config y llama al factory (`gateway/platform_registry.py:278-328`). Los plugins usan loaders diferidos porque importar 20 SDKs en cada CLI era demasiado costoso (`gateway/platform_registry.py:169-183`).

No es preciso decir que todo lo que está en `gateway/platforms/` “se carga siempre”. Es built-in en el sentido de código core, pero solo se instancia si se configura/conecta y varios imports son lazy. Tampoco debe fijarse “22 plugin dirs”: el audit encontró 20. El total de transports externos es mayor porque built-ins y plugins se suman y WeCom registra más de una modalidad, pero contar `local`, webhook/API y aliases como “plataformas de mensajería” cambia la cifra. La redacción segura es **“20 plugins de plataforma + adapters built-in; más de 22 superficies/transports si se cuentan todos los tipos”**.

El claim de scale-to-zero también requiere scope: los archivos existen, pero en el runtime auditado el watcher obtiene específicamente el relay adapter para dormancy (`gateway/run.py:4291-4326`). No hay evidencia en esas líneas de que Telegram/Discord/Slack enteros se apaguen y despierten de forma transparente. “Relay-aware scale-to-zero” es correcto; “todo el gateway hiberna” es demasiado amplio.

### 9. TTS y voz

El doc previo subestima la implementación. `tools/tts_tool.py:3-22` enumera providers built-in: Edge, ElevenLabs, OpenAI, MiniMax, Mistral, Gemini, xAI, NeuTTS, KittenTTS y Piper, más providers `type: command`. El default es Edge (`tools/tts_tool.py:166-190`). Los límites de input son per-provider (`tools/tts_tool.py:219-249`). El dispatch selecciona plugin/command o branches ElevenLabs/OpenAI/MiniMax/xAI/Mistral/Gemini/NeuTTS/KittenTTS/Piper (`tools/tts_tool.py:2153-2347`).

En CLI, la respuesta se limpia de fenced code, links, URLs y markdown antes de sintetizar; se limita a 4.000 caracteres y reproduce el audio en background (`cli.py:11354-11415`). TTS no es un simple endpoint: también elige formato según surface (Opus/OGG para voice bubbles y MP3 para otras) y está integrado con gateway delivery.

### 10. API server vs OAuth proxy

El documento previo mezcla dos componentes distintos:

1. `gateway/platforms/api_server.py` es un **adapter agentic**. Expone `/v1/chat/completions`, `/v1/responses`, modelos, capabilities, runs y health; ejecuta Hermes con tools/memory/sessions (`gateway/platforms/api_server.py:1-28`).
2. `hermes_cli/proxy/server.py` es un **credential-attaching forwarder**. Reemplaza Authorization por un bearer OAuth fresco y transmite request/response/SSE sin mediar, loggear ni transformar cuerpos (`hermes_cli/proxy/server.py:1-10`). Default `127.0.0.1:8645` (`:51-56`).

Afirmar que `api_server.py` es el backend de `hermes proxy` es incorrecto. Son superficies complementarias: una convierte OpenAI requests en agent runs; la otra solo proxifica inferencia hacia un upstream OAuth.

### 11. Seguridad y CVEs

`SECURITY.md` define una postura sorprendentemente explícita: el único boundary contra un LLM adversarial es el sistema operativo; approvals, redaction, scanners y allowlists in-process son heurísticas (`SECURITY.md:58-65`). Terminal backend isolation solo confina shell/file paths, no code execution host-side, MCP subprocesses, plugins, hooks o skill loading (`SECURITY.md:70-88`). Whole-process wrapping sí cubre el process tree (`SECURITY.md:90-114`).

Esto corrige cualquier lectura de “approval gate = sandbox”. No lo es.

Sobre vulnerabilidades:

- La página pública `.../security/advisories` mostraba “There aren't any published security advisories” el 2026-07-13.
- Sin embargo, el código contiene referencias a identificadores GHSA como `GHSA-3vpc-7q5r-276h` (Telegram webhook secret), `GHSA-5qr3-c538-wm9j` (plugin API path traversal/RCE), `GHSA-rhgp-j443-p4rf` (credential passthrough), `GHSA-76xc-57q6-vm5m` (Ollama host gate), entre otras. Sus URLs directas devolvieron 404 sin login. No se puede afirmar desde este audit si son advisories privadas, drafts, reservadas, eliminadas o simplemente referencias internas.
- `pyproject.toml` cita CVEs/PYSEC/GHSA de **dependencias**, por ejemplo Requests, Anthropic SDK, aiohttp, cryptography, PyJWT, Starlette y urllib3 (`pyproject.toml:54,86-92,146-164,200-216`). Eso no equivale a CVEs asignadas a Hermes Agent.

La formulación correcta es: “No había advisories públicas listadas; el código sí incorpora fixes asociados a identificadores GHSA no públicamente resolubles en sesión anónima y fija versiones por vulnerabilidades upstream”. Decir “Hermes tiene 8 CVEs” es incorrecto.

## Flujo interno

```text
1. Surface obtiene texto/evento.
2. Surface resuelve sesión, provider, model, toolsets y callbacks.
3. AIAgent.run_conversation() delega a agent.conversation_loop.
4. build_turn_context() prepara mensajes, system prompt, memoria y persistencia.
5. El loop calcula presión de contexto y puede comprimir.
6. _build_api_kwargs() construye request según transport/provider.
7. Middleware + hooks procesan request.
8. Streaming/non-streaming transport devuelve respuesta normalizada.
9a. Si hay tool_calls:
    - validar nombre/JSON;
    - persistir assistant call;
    - ejecutar secuencial o concurrente;
    - adjuntar role=tool;
    - volver a 5.
9b. Si no hay tools:
    - validar contenido/recovery;
    - finalizar, persistir y entregar.
10. TurnFinalizer sincroniza memoria y puede lanzar background skill review.
```

## Call Stack / API

### Agent turn

```text
surface
└─ AIAgent.run_conversation                 run_agent.py:5787-5810
   └─ agent.conversation_loop.run_conversation
      ├─ build_turn_context                 agent/conversation_loop.py:568-603
      ├─ while budget                       agent/conversation_loop.py:643-668
      ├─ build/middleware/API               agent/conversation_loop.py:1156-1350
      ├─ normalize response                 agent/conversation_loop.py:1370-1448
      ├─ validate tool calls                agent/conversation_loop.py:4446-4629
      ├─ agent._execute_tool_calls          agent/conversation_loop.py:4715
      │  └─ model_tools.handle_function_call
      │     └─ ToolRegistry.dispatch        tools/registry.py:605-635
      └─ final response                     agent/conversation_loop.py:4813+
```

### MCP client

```text
startup/surface
└─ discover_mcp_tools                      tools/mcp_tool.py:4996-5042
   └─ register_mcp_servers                 tools/mcp_tool.py:4876-4993
      └─ asyncio.gather servers            tools/mcp_tool.py:4938-4944
         └─ MCPServerTask connection
            └─ list tools/capabilities
               └─ registry.register        tools/mcp_tool.py:4790-4835
```

### Skills learning

```text
tool iterations
└─ _iters_since_skill++                    agent/conversation_loop.py:698-702
   └─ threshold at finalization            agent/turn_finalizer.py:484-490
      └─ _spawn_background_review          agent/turn_finalizer.py:500-508
         └─ reviewer prompt                agent/background_review.py:181-283
            └─ skill_manage create/patch   tools/skill_manager_tool.py:1320-1407
```

## Diagramas

Ver [hermes-agent-architecture.md](./hermes-agent-architecture.md) para diagramas de componentes, secuencia, MCP, gateway, MoA y trust boundaries.

## Código relacionado

- `pyproject.toml:8-20,24-141,143-305,307-357` — metadata, deps, extras, scripts y packaging.
- `run_agent.py:393+` — clase pública `AIAgent`.
- `run_agent.py:5787-5810` — forwarder actual del loop.
- `agent/conversation_loop.py:523-668` — entrada y budget loop.
- `agent/conversation_loop.py:1156-1448` — request/transports.
- `agent/conversation_loop.py:4446-4816` — tools y finalización.
- `model_tools.py:188-208,279-445,1025-1276` — discovery, schemas y dispatch.
- `tools/registry.py:208-448,605-635` — registry.
- `tools/mcp_tool.py:207-233,1508-1613,4780-5042` — MCP client.
- `mcp_serve.py:543-722,959-990` — MCP server.
- `tools/skills_tool.py:669-848,961-1218,1718-1759` — skills runtime.
- `agent/skill_commands.py:320-467` — slash commands/reload.
- `agent/turn_finalizer.py:484-510` y `agent/background_review.py:181-283` — learning loop.
- `hermes_cli/auth.py:176-475` y `hermes_cli/models.py:1052-1109` — providers.
- `agent/moa_loop.py:220-385,800-1038` — MoA.
- `gateway/config.py:212-313` — platform identities.
- `gateway/platform_registry.py:162-328` — plugin registry.
- `gateway/run.py:8665-8783` — adapter creation.
- `gateway/platforms/base.py:2276-2405,2791-2909` — adapter contract.
- `tools/tts_tool.py:3-29,166-249,2153-2468` — TTS.
- `SECURITY.md:32-169` — trust model.

## Ejemplos

### Ejemplo 1 — entrada pública y loop extraído

```python
# run_agent.py:5798-5810
from agent.conversation_loop import run_conversation
return run_conversation(
    self,
    user_message,
    system_message,
    conversation_history,
    task_id,
    stream_callback,
    persist_user_message,
    persist_user_timestamp=persist_user_timestamp,
    moa_config=moa_config,
)
```

**Verificación:** el snippet es la implementación exacta del forwarder en el commit auditado.

### Ejemplo 2 — budget del loop

```python
# agent/conversation_loop.py:643-668
while (api_call_count < agent.max_iterations
       and agent.iteration_budget.remaining > 0) or agent._budget_grace_call:
    agent._checkpoint_mgr.new_turn()
    if agent._interrupt_requested:
        interrupted = True
        break
    api_call_count += 1
    if agent._budget_grace_call:
        agent._budget_grace_call = False
    elif not agent.iteration_budget.consume():
        break
```

**Verificación:** muestra que `max_iterations` no es el único stop condition.

### Ejemplo 3 — MCP tools como first-class registry entries

```python
# tools/mcp_tool.py:4790-4798
registry.register(
    name=tool_name_prefixed,
    toolset=toolset_name,
    schema=schema,
    handler=_make_tool_handler(name, mcp_tool.name, server.tool_timeout),
    check_fn=_make_check_fn(name),
    is_async=False,
    description=schema["description"],
)
```

**Verificación:** confirma que el modelo no usa una API MCP paralela; ve schemas normales del registry.

### Ejemplo 4 — skills progressive disclosure

```python
# tools/skills_tool.py:785-790
def skills_list(category: str = None, task_id: str = None) -> str:
    """List all available skills (progressive disclosure tier 1).

    Returns only name + description to minimize token usage. Use skill_view()
    to load full content, tags, related files, etc.
    """
```

**Verificación:** distingue índice barato de body on-demand.

### Ejemplo 5 — MoA paralelo y no recursivo

```python
# agent/moa_loop.py:359-379
workers = min(_MAX_REFERENCE_WORKERS, len(reference_models))
with ThreadPoolExecutor(max_workers=workers) as executor:
    for idx, slot in enumerate(reference_models):
        if slot.get("provider") == "moa":
            results[idx] = (..., "[skipped: MoA presets cannot recursively reference MoA]", ...)
            continue
        futures[executor.submit(_run_reference, slot, ref_messages, ...)] = idx
```

**Verificación:** fan-out real, límite ocho y recursion guard.

### Ejemplo 6 — trust boundary

```text
# SECURITY.md:58-65
The only security boundary against an adversarial LLM is the operating system.
Nothing inside the agent process constitutes containment — not the approval gate,
not output redaction, not any pattern scanner, not any tool allowlist.
```

**Verificación:** cita textual corta de la política; no se interpreta approval como sandbox.

### Ejemplo 7 — TTS dispatch multi-provider

```python
# tools/tts_tool.py:2286-2319
elif provider == "openai":
    _generate_openai_tts(text, file_str, tts_config)
elif provider == "minimax":
    _generate_minimax_tts(text, file_str, tts_config)
elif provider == "xai":
    _generate_xai_tts(text, file_str, tts_config)
elif provider == "mistral":
    _generate_mistral_tts(text, file_str, tts_config)
elif provider == "gemini":
    _generate_gemini_tts(text, file_str, tts_config)
```

**Verificación:** branches reales; Edge/local/plugin completan la lista fuera de este fragmento.

## Comparación con `hermes-agent.md`: correcciones necesarias

| # | Claim previo | Veredicto | Corrección basada en código |
|---|---|---|---|
| 1 | “El main loop está en `run_agent.py`” y call stack `Agent.run` | ⚠️ Desactualizado | `run_agent.py:5787-5810` es forwarder; loop real en `agent/conversation_loop.py:523+`. |
| 2 | Arquitectura usa `SkillStore.search`, `MemoryStore.retrieve`, `ToolSelector.pick`, `SelfVerification.check` | ❌ No trazable | Esos símbolos no corresponden al call stack auditado. Usar `build_turn_context`, transports, `handle_function_call`, `ToolRegistry.dispatch` y `turn_finalizer`. |
| 3 | “FTS5 session search + LLM summarization” | ❌ Incorrecto | `tools/session_search_tool.py:5-29` dice explícitamente zero LLM cost/no summary LLM path. |
| 4 | “Todas las deps directas exact-pinned” | ❌ Exagerado | El comentario lo dice, pero `urllib3`, FastAPI, uvicorn, multipart y PTY usan rangos (`pyproject.toml:87-118`). |
| 5 | “8 CVEs de Hermes” | ❌ Categoría incorrecta | Son CVEs/PYSEC/GHSAs upstream anotadas junto a dependencias. La página pública listó cero advisories publicados. |
| 6 | MCP descrito principalmente como `mcp_serve.py + optional-mcps` | ⚠️ Incompleto | El cliente first-class está en `tools/mcp_tool.py`; `mcp_serve.py` es servidor bridge separado. |
| 7 | `api_server.py` es “OpenAI-compatible local proxy backed por OAuth” | ❌ Conflación | API server ejecuta el agente (`gateway/platforms/api_server.py:1-28`); OAuth proxy es `hermes_cli/proxy/server.py:1-10`. |
| 8 | `gateway/platforms` se carga siempre | ❌ Incorrecto | Plugin registry es lazy; built-ins se importan/instancian solo al crear adapters configurados (`gateway/run.py:8665-8783`). |
| 9 | “22 plugin platform dirs” | ❌ Conteo desactualizado | Hay 20 directorios en `plugins/platforms/` en `f96b2e6`. Hay además adapters built-in y pseudo-members; separar ambos conteos. |
| 10 | “22+ mensajerías” como cifra exacta | ⚠️ Ambigua | Más de 22 transports/surfaces es defendible si se suman plugins+built-ins, pero el enum incluye local/API/webhook/relay. Documentar inventario, no solo headline. |
| 11 | “Gateway scale-to-zero” general | ⚠️ Sobre-generalizado | El watcher auditado llama a relay dormancy (`gateway/run.py:4291-4326`). Redactar “scale-to-zero del relay/deploy path” salvo evidencia adicional. |
| 12 | “Closed learning loop único/irrefutable” | ⚠️ Marketing no contrastado | La mecánica existe, pero la unicidad frente a todo OSS no se demuestra con este repo. |
| 13 | “Skills se crean automáticamente tras tareas complejas” | ✅ Con matiz | Threshold default 10 tool iterations + background LLM review + `skill_manage`; best-effort y condicionado al toolset. |
| 14 | “Skills se auto-mejoran con el uso” | ✅ Con matiz | Reviewer prioriza patch de skill cargada/umbrella; bundled/hub están protegidas; curator solo gestiona agent-created. |
| 15 | “MoA first-class provider” | ✅ Preciso | `agent/agent_init.py:846-894`, `hermes_cli/models.py:1055` y `agent/moa_loop.py:800-1038`. |
| 16 | “Antes v0.18 MoA era toggle” | 🔴 VERIFICACIÓN PENDIENTE | Requiere diff/tag histórico; no se prueba desde HEAD actual. |
| 17 | “6 terminal backends” | ✅ Preciso | Selector público en `hermes_cli/web_server.py:623-628`; managed Modal es modo interno. |
| 18 | “40+ tools” | ✅ Conservador pero stale | El audit estático encontró 69 nombres literales registrados solo en módulos inmediatos `tools/*.py`; plugins/MCP agregan más. No usar un total rígido global. |
| 19 | TTS presentado como Edge/ElevenLabs/OpenAI/MiniMax | ⚠️ Muy incompleto | Current code tiene 10 providers built-in más command/plugin providers (`tools/tts_tool.py:3-22`). |
| 20 | “300+ modelos soportados” | ⚠️ Claim de Portal | Es texto del catálogo dinámico de Nous; separar de los 33 provider routes literales. |
| 21 | “El repo top-level `skills/` es el runtime” | ⚠️ Incompleto | Runtime primario es `$HERMES_HOME/skills` + external dirs; repo dirs son fuente/bundle. |
| 22 | “Python 84.3%, TypeScript 14.2%” | 🔴 No revalidado | El API languages estuvo rate-limited. Mantener con fecha 2026-07-08 o refrescar luego, no atribuirlo al audit 2026-07-13. |
| 23 | “211.474 stars” como estado actual | ❌ Stale | HTML mostró 214k redondeado. No tenemos cifra exacta por rate limit; marcar temporal. |
| 24 | “Native desktop Electron” | ✅ Compatible | `package.json:6-18` tiene workspace `apps/desktop`; Node >=20. |
| 25 | “No sandbox caveats” implícito | ⚠️ Falta crítica | Añadir SECURITY trust model: terminal backend no confina MCP/code/plugins; solo whole-process wrapping. |
| 26 | “Memory = Honcho + Hindsight + FTS5” | ⚠️ Incompleto | Hay 8 memory plugins: byterover, hindsight, holographic, honcho, mem0, openviking, retaindb, supermemory. Session FTS5 es store separado. |

## Buenas prácticas

- Citar commit completo junto con cada conjunto de números de línea.
- Distinguir release tag de `main`; no llamar “v0.18.2 exacta” a un checkout post-release sin aclaración.
- Describir providers como rutas/transports, no equipararlos a “modelos”.
- Separar tool registry estático, plugin tools y MCP dynamic tools; un total global cambia con config.
- Separar API server agentic de OAuth proxy.
- En MCP, documentar ambos roles y transportes.
- En seguridad, repetir el trust model upstream: heurística no es boundary.
- En gateway, contar plugin dirs, built-ins y superficies no-messaging por separado.
- En skills, distinguir catálogo fuente, runtime profile-scoped, external dirs y plugin-qualified skills.
- En Aithera, copiar interfaces y invariantes, no god-file sizes ni headlines de feature count.

## Errores comunes

- Buscar `src/hermes_agent/` y concluir que no hay package.
- Citar líneas de `run_agent.py` de una release anterior para explicar el loop actual.
- Tratar `optional-mcps/` como servidores activos.
- Contar `api_server`, `webhook` y `local` como apps de mensajería sin declararlo.
- Suponer que los plugins son sandboxed porque están fuera de core.
- Suponer que MCP subprocesses quedan dentro del terminal backend.
- Equiparar `skill_view` con import de Python; SKILL.md es prompt/instrucción, aunque sus scripts/plugins asociados sí amplían riesgo.
- Decir “sin LLM cost” del learning loop: session search es zero-LLM, pero background skill review usa un agente/modelo.
- Convertir referencias GHSA del source en advisories públicas confirmadas.
- Confundir el `version: 1.0.0` del `package.json` workspace root con la release Python 0.18.2.

## Breaking Changes

El checkout shallow no contiene historia suficiente para certificar todos los breaking changes. Los siguientes son **cambios de arquitectura observables**, no necesariamente breaking releases:

| Área | Estado actual | Riesgo de compatibilidad |
|---|---|---|
| Agent loop | Extraído a `agent/conversation_loop.py`, forwarder en `run_agent.py` | Patches/tests que monkeypatch `run_agent` se preservan mediante lazy `_ra()` y exports. |
| MCP discovery | Ya no ocurre como side effect de import de `model_tools` | Cada surface debe inicializarlo explícitamente para no bloquear loops async. |
| Skills reload | Rescan sin reconstruir system prompt | Nuevas skills son visibles on demand; consumidores que esperen prompt mutation no deben asumirla. |
| Platforms | Registry plugin-first, fallback built-in | Plugins pueden reemplazar behavior si se registran; config validation puede fallar cerrado. |
| MoA | Virtual provider con aggregator actor | Integraciones que lo trataban como flag deberían usar provider/preset. Confirmar historia con tags. |
| Dependencies | Política de pinning/lazy extras | Instalaciones `[all]` ya no incluyen numerosos backends lazy. |

## Cambios entre versiones

| Referencia | Fecha | Qué se verificó |
|---|---|---|
| `v2026.7.7.2` / `9de9c25` | 2026-07-08 UTC según GitHub | Release 0.18.2, fix Baileys para builds tagged. |
| `main` / `f96b2e6` | 2026-07-13 +05:30 | Audit de código; fix de allowlist en taps de WhatsApp Cloud. |

No se reconstruyó un diff completo 0.18.0→0.18.2 porque el clone es `--depth 1`. Las afirmaciones históricas se mantienen como pendientes si no están verificadas por la página de release.

## Impacto sobre otros sistemas

### Aithera Orchestrator

El patrón útil no es copiar el archivo gigante, sino separar `TurnContext`, provider transport, tool registry y `TurnFinalizer`. Hermes demuestra el valor de persistir tool-call intent antes del side effect y de mantener role alternation incluso en recovery.

### Aithera Memory/MOS

Separar session FTS5, user memory provider y skills. Hermes no los fusiona en un único vector store. El background review post-response es transferible, pero debe ser opt-in/costeado y respetar provenance.

### Aithera Gateway

Adoptar registry/factory con lazy loading, capabilities y config validation. Evitar un enum rígido para plugins, pero no aceptar strings arbitrarios: Hermes solo crea pseudo-members para plugins conocidos.

### Aithera Voice

Un provider registry de TTS, límites per-provider, command providers y formato per-surface es más robusto que branches hardcoded en el endpoint de chat.

### Aithera Security

La lección principal es negativa: approvals y regexes no son sandbox. Si Aithera recibe web/email/multi-user input, necesita whole-process isolation para claims fuertes.

## Referencias cruzadas

- [Hermes Agent — landscape previo](./hermes-agent.md)
- [Hermes Agent — arquitectura real](./hermes-agent-architecture.md)
- [MCP](../06_AGENTS/mcp.md)
- [Approval flows](../06_AGENTS/approval-flows.md)
- [Plugin architecture](../02_ARCHITECTURE/plugin-architecture.md)
- [SSE streaming](../02_ARCHITECTURE/sse-streaming.md)
- [Memory overview](../07_MEMORY/README.md)
- [Voice](../08_VOICE/README.md)
- [Security](../11_SECURITY/README.md)

## Fuentes

1. Repo clonado: https://github.com/NousResearch/hermes-agent — acceso 2026-07-13.
2. Commit auditado: https://github.com/NousResearch/hermes-agent/commit/f96b2e6ef75ba6ed678c99954bc8f3ee7f6a38ba — acceso 2026-07-13.
3. Release 0.18.2: https://github.com/NousResearch/hermes-agent/releases/tag/v2026.7.7.2 — acceso 2026-07-13.
4. Security policy: https://github.com/NousResearch/hermes-agent/blob/f96b2e6ef75ba6ed678c99954bc8f3ee7f6a38ba/SECURITY.md — acceso 2026-07-13.
5. Security advisories listing: https://github.com/NousResearch/hermes-agent/security/advisories — acceso 2026-07-13; la página indicó cero advisories publicados.
6. MCP specification/client SDK utilizada por dependency: https://pypi.org/project/mcp/ — referencia independiente de compatibilidad, acceso 2026-07-13.
7. agentskills.io: https://agentskills.io — estándar externo citado por el código, acceso 2026-07-13.
8. Documentación oficial Hermes: https://hermes-agent.nousresearch.com/docs/ — fuente secundaria oficial, acceso 2026-07-13.
9. Constitución JWIKI: [CONSTITUTION.md](../CONSTITUTION.md), especialmente §2, §5, §7 y §8.

Los links `blob/<sha>` son el ancla estable; los `path:line` de este documento corresponden a ese SHA.

## Nivel de confianza

**94/100.**

- 100% para rutas, líneas, entry points, deps, providers literales, número de plugin dirs, agent loop, MCP, skills, MoA, TTS y trust model del checkout.
- 90% para el inventario de “plataformas” porque aliases, multi-platform plugins y superficies no-messaging hacen que un único headline sea semánticamente ambiguo.
- 80% para metadata GitHub actual: el HTML solo mostró redondeos y el API estuvo rate-limited.
- 70% para evolución histórica pre-v0.18: el clone shallow no permite certificar diffs antiguos.
- 50% para el estatus público de GHSAs citadas en source: no aparecen en listing público y URLs directas devolvieron 404 sin autenticación.

## Pendientes

- `VERIFICACIÓN PENDIENTE`: clonar tags/historia y confirmar exactamente cómo era MoA antes de 0.18.0.
- `VERIFICACIÓN PENDIENTE`: consultar GitHub API autenticada para stars/forks exactos y advisories privados/published metadata.
- `VERIFICACIÓN PENDIENTE`: ejecutar integración real con un MCP stdio y uno Streamable HTTP; este audit revisó código y tests existentes, no credenciales externas.
- `VERIFICACIÓN PENDIENTE`: medir qué tools se exponen con una config concreta; 69 nombres estáticos no es el total dinámico universal.
- `VERIFICACIÓN PENDIENTE`: comprobar binarios desktop de cada OS; el workspace se verificó, no se instalaron artifacts.
- No se modificó `hermes-agent.md`; la tabla anterior es la lista explícita de correcciones solicitada.

## Validación CONSTITUTION §8

- [x] **Código revisado:** clone real, branch y commit completo citados; no se usó solo README.
- [x] **Fuentes contrastadas:** código + release GitHub + security listing/policy + estándares externos.
- [x] **Compatibilidad documentada:** Python, Node, MCP, ACP, terminal, release vs main.
- [x] **Ejemplos verificados:** snippets copiados del checkout con `path:line`; call stacks contrastados con tests existentes (2.080 paths de test, 660 relacionados con gateway/MCP/skills/MoA/TTS/conversation por filtro de nombres).
- [x] **Referencias cruzadas:** landscape, arquitectura, MCP, memory, voice, security, plugins.
- [x] **Revisión independiente:** este documento es la auditoría de un subagente de código distinto del autor/orquestador del doc previo; sus claims se contrastaron de nuevo contra `f96b2e6`.

---

*Auditoría realizada 2026-07-13. Los números de línea son inmutables solo respecto a `f96b2e6ef75ba6ed678c99954bc8f3ee7f6a38ba`.*
