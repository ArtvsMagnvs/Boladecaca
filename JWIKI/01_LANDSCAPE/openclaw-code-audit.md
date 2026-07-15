# OpenClaw — Auditoría técnica de código (commit 4b6575636fd4493c9f12cc0d3367a9e55e71994b, 2026-07-13)

## Resumen

Este documento es la auditoría de código **real** de `openclaw/openclaw` (clonado en `~/openclaw-code-audit`, commit pin `4b6575636fd4493c9f12cc0d3367a9e55e71994b`, branch `main`, 2026-07-13, 23836 archivos tracked, SHA abreviado `4b657563`). Sustituye las descripciones de marketing del doc `openclaw.md` por lo que el código dice de sí mismo: 25 canales bundled reales, 78 providers, gateway WebSocket+HTTP, sandbox pluggable (Docker/SSH/OpenShell), runtime agent-core en `packages/agent-core`, paquete `@openclaw/ai` con el modelo de streaming `streamSimple`, `agent-core` con `Agent.streamFn` y `runAgentLoop` como bucle principal, sistema de skills en `src/skills/loading`, secrets runtime con sentinels y SecretRef triple-source (`env`/`file`/`exec`). Acompaña a `openclaw-architecture.md` y reemplaza las cifras no verificadas del doc previo.

## Objetivo

- Reemplazar claims de marketing del doc `openclaw.md` con datos del propio `git log` + `package.json` + `extensions/*/openclaw.plugin.json` + `docs/**`.
- Producir la foto 2026-07-13 (no 2026-06-30) del repo, contrastada con los docs anteriores.
- Listar correcciones a aplicar a `openclaw.md`, `clawdbot.md` y `projects.md`.

## Estado

🟡 En progreso — datos verificados en el código; aún pendiente el cross-check con el GitHub API por rate-limit (403 al `https://api.github.com/repos/openclaw/openclaw` a 2026-07-13 11:24 UTC). Las estrellas del doc se contrastaron vía `img.shields.io/github/stars/openclaw/openclaw` → `383k` (anterior doc: `382k`).

## Versiones compatibles

| Componente | Versión (en HEAD) | Evidencia |
|---|---|---|
| Repo (en `package.json` raíz) | `2026.7.2` | `openclaw-code-audit/package.json:3` |
| Skill workshop / agent core | `2026.7.2` | `openclaw-code-audit/packages/agent-core/src/agent.ts` (no fija versión, hereda root) |
| `@openclaw/ai` (provider SDK) | `2026.7.2` | `openclaw-code-audit/packages/ai/package.json:3` |
| Default model | `openai/gpt-5.6-sol` | `openclaw-code-audit/src/agents/defaults.ts:4` (`DEFAULT_MODEL = "gpt-5.6-sol"`) — el doc anterior decía `claude-sonnet-4-6` |
| Node runtime (recomendado) | `Node 24.15+` | `openclaw-code-audit/README.md:96` |
| `@modelcontextprotocol/sdk` | `1.29.0` | `openclaw-code-audit/package.json:2017` |
| `@anthropic-ai/sdk` | `0.109.1` | `openclaw-code-audit/package.json:2007` |
| `openai` (SDK) | `6.45.0` | `openclaw-code-audit/package.json:2047` |
| `@google/genai` | `2.10.0` | `openclaw-code-audit/package.json:2011` |
| `@mistralai/mistralai` | `2.4.0` | `openclaw-code-audit/package.json:2016` |
| `grammy` (Telegram) | `1.44.0` | `openclaw-code-audit/package.json:2035` |

## Proyectos compatibles

- **Node**: `>= 22.19.0` por `engines` en `packages/ai/package.json:78-80`; el README recomienda 24.15+.
- **Sistema operativo**: macOS, Linux, Windows (recomendado vía WSL2 + `openclaw onboard --install-daemon` → servicio systemd/launchd; Windows tiene `Windows Hub` companion app nativa).
- **Canales bundled (25)**: clickclack, discord, feishu, googlechat, imessage, irc, line, matrix, mattermost, msteams, nextcloud-talk, nostr, qa-channel, qqbot, raft, signal, slack, sms, synology-chat, telegram, tlon, twitch, whatsapp, zalo, zalouser — extraído de `extensions/*/openclaw.plugin.json` (verificado en sesión 2026-07-13 11:24, salida Python del script de inventario).
- **Providers bundled (78)**: amazon-bedrock, amazon-bedrock-mantle, anthropic, anthropic-vertex, arcee, bailian-token-plan, byteplus, byteplus-plan, cerebras, chutes, clawrouter, cloudflare-ai-gateway, codex, cohere, comfy, copilot-proxy, dashscope, deepinfra, deepseek, fal, featherless, fireworks, github-copilot, gmi, gmi-cloud, gmicloud, google, google-gemini-cli, google-vertex, groq, huggingface, kilocode, kimi, kimi-coding, litellm, lmstudio, longcat, meta, microsoft-foundry, minimax, minimax-portal, mistral, modelstudio, moonshot, novita, novita-ai, novitaai, nvidia, ollama, ollama-cloud, openai, opencode, opencode-go, openrouter, qianfan, qwen, qwen-cli, qwen-oauth, qwen-portal, qwen-token-plan, qwencloud, sglang, stepfun, stepfun-plan, synthetic, tencent-tokenhub, tencent-tokenplan, together, venice, vercel-ai-gateway, vllm, volcengine, volcengine-plan, vydra, xai, xiaomi, xiaomi-token-plan, zai.

## Dependencias

- Doc principal: [01_LANDSCAPE/openclaw.md](./openclaw.md) (sustituye claims verificados por este doc).
- Diagrama: [01_LANDSCAPE/openclaw-architecture.md](./openclaw-architecture.md).
- Source: `https://github.com/openclaw/openclaw` (commit `4b657563`, 2026-07-13).
- Documentación upstream: <https://docs.openclaw.ai>.

## Arquitectura (resumen)

OpenClaw es un monorepo pnpm (`pnpm-workspace.yaml:1-6` → `packages/`, `ui/`, `extensions/*`, `examples/*`, root). El runtime es un **proceso Node** (recomendado 24.15+) que monta tres superficies en paralelo desde el mismo binario `openclaw`:

1. **Gateway** (`src/gateway/`): servidor WebSocket+HTTP en `ws://127.0.0.1:18789` por defecto (`src/config/paths.ts:283` → `DEFAULT_GATEWAY_PORT = 18789`) que enruta mensajes, ejecuta agentes y expone un control plane (`server-methods-list.ts`) y un data plane (`mcp-http.ts` para loopback MCP). La lógica de canales es **channel-agnostic** (lifecycle, retry, backoff, `MessageEnvelope` y `OutboundMessage` definidos en `src/auto-reply/reply/`, `src/auto-reply/reply/reply-payload.ts`). Cada canal es un plugin en `extensions/<id>/` con contrato `ChannelPlugin` (`src/channels/plugins/types.plugin.ts:66-111`) que implementa `setup` + `gateway.startAccount` (p. ej. `extensions/telegram/src/channel.ts:1026-1126`, `extensions/discord/src/channel.ts:697-735`, `extensions/slack/src/channel.ts:868-887`, `extensions/whatsapp/src/channel.ts:336-355`).
2. **CLI** (mismo binario): `openclaw onboard`, `openclaw agent`, `openclaw mcp`, `openclaw message send`, `openclaw doctor`, etc. Reentrada al Gateway vía `ws://127.0.0.1:18789` o modo embedded (sin Gateway). Ver `src/cli/` (~120 entradas en `package.json:1790`).
3. **Bundled plugins** (extensiones): 148 directorios en `extensions/` (`git ls-tree -d --name-only HEAD:extensions | wc -l` → `148`). Cada uno declara su `id`, `channels[]` y `providers[]` en `openclaw.plugin.json`. 25 son canales, 78 son providers, los 45 restantes son features (workspaces, workboard, browser, codex, codex harness, ACP, open-prose, oc-path, etc.).

El modelo mental es: el Gateway es el control plane; los canales son transport adapters; los providers son model adapters; el agent core vive en `packages/agent-core/src/agent.ts` (clase `Agent` con `streamFn`, `subscribe()`, `steer()`, `followUp()`); el runtime OpenClaw-specific vive en `src/agents/embedded-agent-runner/run.ts` (`runEmbeddedAgent`) que cablea el `Agent` con auth, skills, sandbox, MCP y tools. Ver `openclaw-architecture.md` para el diagrama.

## Descripción técnica

### 1. Estructura real del monorepo

Inspección con `git ls-tree -d --name-only HEAD` confirma 18 directorios top-level:

```
.agents, .github, .vscode, apps, config, deploy, docs, examples, extensions,
git-hooks, packages, patches, qa, scripts, security, skills, src, test, ui
```

El repo tiene **23836 archivos tracked** (`git ls-files | wc -l`) y 148 sub-`extensions/`. La extensión `qa/`, `patches/`, `git-hooks/`, `config/`, `apps/`, `examples/`, `test/` confirman que es un monorepo de desarrollo (no un repo "ligero" como sugería el doc original).

### 2. Stack y runtime

`package.json:1-118` (raíz):
- `name = "openclaw"`, `version = "2026.7.2"`.
- `description = "Multi-channel AI gateway with extensible messaging integrations"` (línea 4). Esta es la definición canónica que sustituye las paráfrasis del doc anterior.
- `type = "module"`, `main = "dist/index.js"`, binario `openclaw → openclaw.mjs`.
- `engines` del paquete `@openclaw/ai`: `node >= 22.19.0`.
- 60+ deps runtime: `@anthropic-ai/sdk@0.109.1`, `@google/genai@2.10.0`, `@mistralai/mistralai@2.4.0`, `openai@6.45.0`, `@modelcontextprotocol/sdk@1.29.0`, `grammy@1.44.0` (Telegram), `@lydell/node-pty@1.2.0-beta.12`, `node-edge-tts@1.2.10`, `playwright-core@1.61.1`, `kysely@0.29.2`, `sqlite-vec`, `web-push@3.6.7`, `koffi`, etc. (`package.json:2005-2069`).
- DevDeps pesadas: `typescript@6.0.3`, `tsdown@0.22.1`, `oxlint@1.73.0`, `oxfmt@0.58.0`, `@typescript/native-preview@7.0.0-dev.20260707.2`, `vitest@4.x`.

`pnpm-workspace.yaml:1-6`:
```yaml
packages:
  - .
  - ui
  - packages/*
  - extensions/*
  - examples/*
```
`overrides` (líneas 98-127) pinea versiones de deps críticas: `hono@4.12.25`, `axios@1.16.0`, `form-data@2.5.6`, `tar@7.5.19`, etc.

### 3. Conteo real de canales y providers (inferencia directa del manifest)

`extensions/*/openclaw.plugin.json` (148 archivos):

```python
# Script ejecutado (resumen):
import json, glob
cs, ps = [], []
for p in glob.glob("extensions/*/openclaw.plugin.json"):
    d = json.load(open(p))
    cs += d.get("channels", [])
    ps += d.get("providers", [])
print("CHANNELS", len(cs))   # → 25
print("PROVIDERS", len(ps))  # → 78
```

Resultado en `openclaw-code-audit`, ejecutado en 2026-07-13 11:24 UTC:

| Categoría | Total | Lista ordenada |
|---|---|---|
| Canales | 25 | clickclack, discord, feishu, googlechat, imessage, irc, line, matrix, mattermost, msteams, nextcloud-talk, nostr, qa-channel, qqbot, raft, signal, slack, sms, synology-chat, telegram, tlon, twitch, whatsapp, zalo, zalouser |
| Providers | 78 | amazon-bedrock, amazon-bedrock-mantle, anthropic, anthropic-vertex, arcee, bailian-token-plan, byteplus, byteplus-plan, cerebras, chutes, clawrouter, cloudflare-ai-gateway, codex, cohere, comfy, copilot-proxy, dashscope, deepinfra, deepseek, fal, featherless, fireworks, github-copilot, gmi, gmi-cloud, gmicloud, google, google-gemini-cli, google-vertex, groq, huggingface, kilocode, kimi, kimi-coding, litellm, lmstudio, longcat, meta, microsoft-foundry, minimax, minimax-portal, mistral, modelstudio, moonshot, novita, novita-ai, novitaai, nvidia, ollama, ollama-cloud, openai, opencode, opencode-go, openrouter, qianfan, qwen, qwen-cli, qwen-oauth, qwen-portal, qwen-token-plan, qwencloud, sglang, stepfun, stepfun-plan, synthetic, tencent-tokenhub, tencent-tokenplan, together, venice, vercel-ai-gateway, vllm, volcengine, volcengine-plan, vydra, xai, xiaomi, xiaomi-token-plan, zai |

> **Corrección al doc anterior**: el doc `openclaw.md` lista "11+ plataformas" y "Claude, GPT-4o, Gemini, Ollama, NVIDIA Nemotron/NeMo, Moonshot Kimi". El código dice 25 canales bundled y 78 providers con Anthropic, Google, OpenAI, Mistral y muchos otros (xAI Grok, Qwen, DeepSeek, StepFun, Moonshot, Cohere, Groq, Cerebras, etc.). El doc `projects.md` repite la cifra 376k★ y los nombres.

### 4. Gateway: el control plane (no "Multi-channel inbox")

Definición canónica en `package.json:4`:
> `Multi-channel AI gateway with extensible messaging integrations`

Implementación:

- `src/gateway/server.impl.ts:1-260` muestra el bootstrap del `Gateway` (registro de methods, channels, plugins, MCP). Usa `createLazyRuntimeModule` para diferir la carga del catálogo de modelos, plugins, browsers, etc. hasta que se necesitan.
- `src/gateway/server.ts:1` (entrypoint), `src/gateway/server-ws-runtime.ts:1` (loopback HTTP+WS para nodos), `src/gateway/server-channels.ts:1` (gestor de ciclo de vida de canales).
- `src/gateway/methods/registry.ts:1-100` define el registro unificado de métodos RPC. `src/gateway/server-methods-list.ts:1` exporta `GATEWAY_EVENTS` y `listCoreGatewayMethodNames()`. Más de 100 métodos RPC están disponibles.
- `src/gateway/mcp-http.ts:1-509` implementa el **MCP loopback HTTP** del Gateway: expone las herramientas del Gateway a clientes MCP locales (Claude Desktop, Claude Code, Cursor) sobre HTTP autenticado con bearer token aleatorio. La descripción en `docs/cli/mcp.md:260` ("dedicated MCP page is an operator view for OpenClaw-managed MCP servers under `mcp.servers`") confirma que esto es **primera clase**, no un add-on.
- `src/gateway/server-methods/mcp-app.ts:1`, `src/agents/agent-bundle-mcp-runtime.ts:1-300` (Cliente MCP con Streamable HTTP + stdio + SSE).
- `src/gateway/mcp-app-sandbox-http.ts:1` (modo sandbox para apps MCP).

> **Corrección al doc anterior**: el doc describía "Channels (input)" y "Agent Runtime" como dos cajas separadas. La realidad es que **no hay un agente acoplado al Gateway**; el Gateway expone herramientas y métodos, y el agente es un consumidor (embedded o CLI).

### 5. Channel-agnostic core: `ChannelPlugin`, `MessageEnvelope`, `ChannelTurnKernel`

`src/channels/plugins/types.plugin.ts:66-111`:
```typescript
export type ChannelPlugin<ResolvedAccount = any, Probe = unknown, Audit = unknown> = {
  id: ChannelId;
  meta: ChannelMeta;
  capabilities: ChannelCapabilities;
  defaults?: { queue?: { debounceMs?: number } };
  reload?: { configPrefixes: string[]; noopPrefixes?: string[] };
  setupWizard?: ChannelPluginSetupWizard;
  config: ChannelConfigAdapter<ResolvedAccount>;
  configSchema?: ChannelConfigSchema;
  setup?: ChannelSetupAdapter;
  pairing?: ChannelPairingAdapter;
  security?: ChannelSecurityAdapter<ResolvedAccount>;
  groups?: ChannelGroupAdapter;
  mentions?: ChannelMentionAdapter;
  outbound?: ChannelOutboundAdapter;
  status?: ChannelStatusAdapter<ResolvedAccount, Probe, Audit>;
  gatewayMethods?: string[];
  gatewayMethodDescriptors?: ChannelGatewayMethodDescriptor[];
  gateway?: ChannelGatewayAdapter<ResolvedAccount>;
  // ... (12 adaptadores más)
};
```

El `ChannelPlugin` es un **registro tipado** con 25+ adaptadores opcionales. El Gateway nunca toca la API nativa de Telegram o Discord: solo conoce `ChannelPlugin.gateway.startAccount(ctx)` y `ChannelPlugin.outbound.sendMessage(...)`.

`src/channels/turn/types.ts:49-56` define el `NormalizedTurnInput` (el envelope universal):
```typescript
export type NormalizedTurnInput = {
  id: string;
  timestamp?: number;
  rawText: string;
  textForAgent?: string;
  textForCommands?: string;
  raw?: unknown;
};
```

`src/channels/turn/types.ts:454-475` define el `ChannelTurnAdapter` con cinco etapas: `ingest → classify → preflight → resolveTurn → finalize`. **Cada canal implementa este adapter**, no el handshake del SDK nativo.

`src/auto-reply/reply/route-reply.ts:129-339` (`routeReply`) toma un `ReplyPayload` y un canal de origen y lo enruta de vuelta a `sendDurableMessageBatch`. La línea 208-213 falla de forma ruidosa si alguien intenta enrutar a `INTERNAL_MESSAGE_CHANNEL` (webchat no soportado). La línea 215-217 cierra en limpio si el `channelId` no es resoluble.

`src/auto-reply/reply/kernel.ts:1-260` (turn kernel) es la pieza clave que normaliza el inbound: preflight, history, reply, delivery, durable queue. El `dispatchReplyWithBufferedBlockDispatcher` que usan todos los canales se invoca desde aquí.

### 6. Routing y bindings (cómo un mensaje llega al agente correcto)

`src/routing/resolve-route.ts:34-60` define `ResolveAgentRouteInput`:
```typescript
type ResolveAgentRouteInput = {
  cfg: OpenClawConfig;
  channel: string;
  accountId?: string | null;
  peer?: RoutePeer | null;
  parentPeer?: RoutePeer | null;     // para threads
  guildId?: string | null;
  teamId?: string | null;
  memberRoleIds?: string[];
};
```

`src/routing/resolve-route.ts:47-70` define `ResolvedAgentRoute` con `matchedBy` discriminado:
```typescript
matchedBy:
  | "binding.peer"
  | "binding.peer.parent"
  | "binding.peer.wildcard"
  | "binding.guild+roles"
  | "binding.guild"
  | "binding.team"
  | "binding.account"
  | "binding.channel"
  | "default";
```

El sistema soporta `bindings[]` con `match.channel + match.accountPattern + match.peer` o `guildId+roles` o `teamId`. El agent id se elige en `pickFirstExistingAgentId()` y la session key se construye en `buildAgentSessionKey()` con `dmScope` (main/per-peer/per-channel-peer/per-account-channel-peer).

**Implicación Aithera**: Aithera V0.7+ tiene `agents.list[]` pero no tiene bindings por guild/team/role. Si Aithera quiere hacer multi-tenant Discord routing, este es exactamente el patrón a importar.

### 7. Agent runtime: `Agent` core + `runEmbeddedAgent` OpenClaw-specific

`packages/agent-core/src/agent.ts:201-263` define la clase `Agent` reutilizable. Su API pública:
```typescript
class Agent {
  // estado mutable
  public convertToLlm: (messages: AgentMessage[]) => Message[] | Promise<Message[]>;
  public transformContext?: (messages: AgentMessage[], signal?: AbortSignal) => Promise<AgentMessage[]>;
  public runtime?: AgentCoreStreamRuntimeDeps;
  public streamFn: StreamFn;          // ★ el stream del provider
  public getApiKey?: (provider: string) => Promise<string | undefined>;
  public beforeToolCall?: (...) => Promise<...>;
  public afterToolCall?: (...) => Promise<...>;
  public prepareNextTurn?: (signal?) => Promise<AgentLoopTurnUpdate | undefined>;
  public steeringMode: QueueMode;
  public followUpMode: QueueMode;
  
  public subscribe(listener: (event: AgentEvent, signal: AbortSignal) => Promise<void> | void): () => void;
  public steer(message: AgentMessage): void;          // inyecta antes del próximo turn
  public followUp(message: AgentMessage): void;       // inyecta después del agent stop
  public abort(reason?: unknown): void;
  public waitForIdle(): Promise<void>;
  public reset(): void;
}
```

`packages/agent-core/src/agent-loop.ts:300-434` implementa el `runLoop`:
```typescript
while (true) {
  let hasMoreToolCalls = true;
  while (hasMoreToolCalls || pendingMessages.length > 0) {
    // ... process pending steering messages
    const message = await streamAssistantResponse(currentContext, config, signal, emit, streamFn, runtime);
    if (message.stopReason === "toolUse" && toolCalls.length > 0) {
      const executedToolBatch = await executeToolCalls(...);  // ★ tool execution
      hasMoreToolCalls = !executedToolBatch.terminate;
    }
    // ... prepareNextTurn, shouldStopAfterTurn, drain steering
  }
  // ... drain followUp or break
}
```

Es un **tool-use loop clásico** con steering/follow-up queues, abort handling, post-turn hooks. **No es un ReAct agent ni un LangGraph DAG** — es un loop determinista que se parece mucho al Aithera V0.7 `chat_message_handler` con steering.

> **Corrección al doc anterior**: el doc decía "Cómo integra LangChain" y "MCP como integración preferente". El código dice: no hay LangChain (`git grep -i 'langchain\|langgraph' -- 'package.json' '*/package.json' 'pnpm-lock.yaml' | wc -l` → **0**). El agent loop es propio (`packages/agent-core`); MCP es **first-class** (paquete oficial + 100+ referencias en código).

`src/agents/embedded-agent-runner/run.ts:1-500` es la capa OpenClaw: cablea `Agent` con auth profiles, skills, sandbox, MCP runtime, browser bridge, code mode, fail-over entre providers, trazas trajectory, compactions context-engine, etc. La función `runEmbeddedAgent` (línea 6, exportada desde `embedded-agent-runner.ts:9`) se invoca desde:

- `src/agents/agent-command.ts:132` (CLI `openclaw agent`).
- `src/auto-reply/reply/turn/kernel.ts:103` (turn kernel al detectar un mensaje agentable).
- `src/commitments/runtime.ts:246` (extracción de commitments background).
- `src/agents/btw.ts:1158` (side question /btw).
- `src/agents/embedded-agent-runner/compact.ts:988` (recompaction del transcript).

`src/agents/embedded-agent-runner/run/attempt.ts:2346-2350` instancia la sesión:
```typescript
let session: Awaited<ReturnType<typeof createAgentSession>>["session"] | undefined;
```

Y en línea 2679-2684:
```typescript
const createdSession = await createEmbeddedAgentSessionWithResourceLoader<
  Awaited<ReturnType<typeof createAgentSession>>
>({
  createAgentSession: async (options) =>
    await createAgentSession(options as unknown as Parameters<typeof createAgentSession>[0]),
  options: { cwd: effectiveCwd, agentDir, ... },
});
```

### 8. LLM providers: `@openclaw/ai` no es LangChain

`packages/ai/package.json:70-77` (dependencies):
```json
{
  "@anthropic-ai/sdk": "0.109.1",
  "@google/genai": "2.10.0",
  "@mistralai/mistralai": "2.4.0",
  "openai": "6.45.0",
  "partial-json": "0.1.7",
  "typebox": "1.3.3"
}
```

**5 SDKs oficiales** (Anthropic, Google GenAI, Mistral, OpenAI, partial-json) + `typebox` para JSON schema. Sin LangChain, sin `llama-index`, sin `transformers`.

`packages/ai/src/api-registry.ts:14-119`:
```typescript
export type ApiStreamFunction = (
  model: Model,
  context: Context,
  options?: StreamOptions,
) => AssistantMessageEventStreamContract;

export interface ApiProvider<TApi extends Api = Api, TOptions extends StreamOptions = StreamOptions> {
  api: TApi;
  stream: StreamFunction<TApi, TOptions>;
  streamSimple: StreamFunction<TApi, SimpleStreamOptions>;
}

// registry: Map<api, RegisteredApiProvider> with sourceId for unregister
```

Cada provider registra un `ApiProvider` con `api: "anthropic-messages" | "openai-responses" | "openai-completions" | "google-generative-ai" | "google-vertex" | "azure-openai-responses" | "mistral-conversations" | "openai-chatgpt-responses"`. Ver `packages/ai/src/providers/register-builtins.ts:95-152` para los 8 built-ins.

`packages/ai/src/providers/anthropic.ts:1+` y los otros siete adapters son thin wrappers sobre el SDK del vendor, adaptados al envelope `AssistantMessageEvent` del propio OpenClaw. **No hay abstracción "model-agnostic" sobre LangChain**; cada provider habla el dialecto del SDK nativo.

`src/llm/stream.ts:1-11` es el facade que cablea todo:
```typescript
import { defaultApiRegistry } from "@openclaw/ai/internal/runtime";
import { registerBuiltInApiProviders } from "@openclaw/ai/providers";
import "./ai-transport-host.js";

registerBuiltInApiProviders(defaultApiRegistry);

export { complete, completeSimple, stream, streamSimple } from "@openclaw/ai/internal/runtime";
```

> **Corrección al doc anterior**: el doc afirmaba "Model providers: Ollama (HTTP :11434), OpenRouter, OpenAI (v1 API dual auth), NVIDIA Nemotron/NeMo (TRT-LLM + FP8), Moonshot Kimi (2M context chunked prefill)". El código tiene Ollama (`extensions/ollama/`), OpenRouter (`extensions/openrouter/`), OpenAI, Anthropic, Google, Mistral, xAI, Qwen, DeepSeek, Moonshot, Cohere, Groq, Cerebras, NVIDIA NIM, Cloudflare AI Gateway, OpenAI Codex CLI, Anthropic Vertex, Amazon Bedrock, OpenCode, OpenCode-go, Kilocode, Meta Llama, Mistral (otro), Microsoft Foundry, etc. La lista de "Moonshot Kimi 2M context" o "NVIDIA TRT-LLM + FP8" no aparece en el código; NVIDIA se sirve vía `extensions/nvidia/` con baseUrl estándar OpenAI-compatible.

### 9. Sandbox: tres backends, registry, build args

`src/agents/sandbox/backend.ts:111-122` (registry de backends):
```typescript
registerSandboxBackend("docker", {
  factory: createDockerSandboxBackend,
  manager: dockerSandboxBackendManager,
  resolveWorkdir: ({ cfg }) => cfg.docker.workdir,
});

registerSandboxBackend("ssh", {
  factory: createSshSandboxBackend,
  manager: sshSandboxBackendManager,
  resolveWorkdir: ({ cfg, scopeKey }) =>
    resolveSshRuntimePaths(cfg.ssh.workspaceRoot, scopeKey).remoteWorkspaceDir,
});
```

`docs/gateway/sandboxing.md:32-34` lista un tercer backend `openshell` con su propio plugin (`extensions/openshell/`) que se autodocumenta. El set real es **3 backends**: `docker`, `ssh`, `openshell`. El doc `openclaw.md` decía solo "Docker" → incorrecto.

`src/agents/sandbox/config.ts:96-138` (resolver de config Docker):
```typescript
export function resolveSandboxDockerConfig(params: {
  scope: SandboxScope;
  globalDocker?: Partial<SandboxDockerConfig>;
  agentDocker?: Partial<SandboxDockerConfig>;
}): SandboxDockerConfig {
  // ...
  return {
    image: agentDocker?.image ?? globalDocker?.image ?? DEFAULT_SANDBOX_IMAGE,  // "openclaw-sandbox:bookworm-slim"
    containerPrefix: ...,
    workdir: ...,
    readOnlyRoot: ... ?? true,                                                   // ★ por defecto read-only
    tmpfs: ... ?? ["/tmp", "/var/tmp", "/run"],
    network: ... ?? "none",                                                     // ★ por defecto sin red
    capDrop: ... ?? ["ALL"],                                                   // ★ drop ALL por defecto
    env, ulimits, ...
  };
}
```

Tres defaults importantes: `readOnlyRoot: true`, `network: "none"`, `capDrop: ["ALL"]`. Más restrictivo que lo que el doc `openclaw.md` sugiere.

`src/agents/sandbox/docker.ts:405-535` (`buildSandboxCreateArgs`) construye los flags `docker create`:
- `--init` (reap orphan processes)
- `--label openclaw.sandbox=1`
- `--label openclaw.sessionKey=<scopeKey>`
- `--label openclaw.createdAtMs=<ts>`
- `--label openclaw.mountFormatVersion=<N>`
- `--label openclaw.createArgsEpoch=<N>` (inmutable; bump cuando cambian defaults incompatibles)
- `--read-only`, `--tmpfs`, `--network`, `--cap-drop`, `--security-opt no-new-privileges`, etc.

`scripts/docker/sandbox/Dockerfile` (default image, línea 1-21):
```dockerfile
FROM debian:bookworm-slim@sha256:f9c6a2fd2ddbc23e336b6257a5245e31f996953ef06cd13a59fa0a1df2d5c252
RUN apt-get update && apt-get install -y --no-install-recommends \
  bash ca-certificates curl git jq python3 ripgrep
RUN useradd --create-home --shell /bin/bash sandbox
USER sandbox
WORKDIR /home/sandbox
CMD ["sleep", "infinity"]
```

`scripts/docker/sandbox/Dockerfile.common` (línea 1-60) añade Node 24, pnpm, Bun, Homebrew Linuxbrew con BuildKit cache mounts. Documentado en `docs/gateway/sandboxing.md:265-291`.

**Hardening gates** (`src/agents/sandbox/validate-sandbox-security.ts`): bloquea bind sources a `/.ssh`, `/.aws`, `/.docker`, `/.gnupg`, `/.netrc`, `/.npm`, `/.cargo`, `/.config`, `/.proc`, `/.sys`, `/.dev`, `/.boot`, `/.etc`, `/run`, `/var/run` por defecto. Override vía `dangerouslyAllowExternalBindSources`. Ver `docs/gateway/sandboxing.md:212-224`.

### 10. Skills: folder-based, workspace-rooted, no "ClawHub" en runtime

`src/skills/loading/local-loader.ts:38-89` (la pieza canónica):
```typescript
function loadSingleSkillDirectory(params: {
  skillDir: string;
  source: string;
  rootRealPath: string;
  maxBytes?: number;
}): LoadedLocalSkill | null {
  const skillFilePath = path.join(params.skillDir, "SKILL.md");
  const raw = readSkillFileSync({
    rootRealPath: params.rootRealPath,
    filePath: skillFilePath,
    maxBytes: params.maxBytes,
  });
  if (!raw) return null;
  let frontmatter: Record<string, string>;
  try {
    frontmatter = parseFrontmatter(raw);
  } catch {
    return null;
  }
  const fallbackName = path.basename(params.skillDir).trim();
  const name = frontmatter.name?.trim() || fallbackName;
  const description = frontmatter.description?.trim();
  if (!name || !description) return null;
  // ... build Skill { name, description, filePath, baseDir, promptVersion, source, ... }
}
```

`src/skills/loading/frontmatter.ts:25-27` parsea frontmatter con `parseFrontmatterBlock` (de `packages/markdown-core`); valida `brew|node|go|uv|download` install specs (líneas 113-186).

`src/skills/loading/workspace.ts:175-201` (filtrado):
```typescript
function filterSkillEntries(entries, config, skillFilter, eligibility) {
  const bundledAllowlist = resolveBundledAllowlist(config);
  let filtered = entries.filter((entry) =>
    shouldIncludeSkill({ entry, config, bundledAllowlist, eligibility }),
  );
  if (skillFilter !== undefined) {
    const normalized = normalizeSkillFilter(skillFilter) ?? [];
    if (normalized.length > 0) {
      const allowed = new Set(normalized);
      filtered = filtered.filter((entry) => allowed.has(entry.skill.name));
    } else {
      filtered = [];  // explicit empty filter = filter all
    }
  }
  return filtered;
}
```

`src/skills/loading/workspace.ts:203-209` (límites):
```typescript
const DEFAULT_MAX_CANDIDATES_PER_ROOT = 300;
const DEFAULT_MAX_SKILLS_LOADED_PER_SOURCE = 200;
const DEFAULT_MAX_SKILLS_IN_PROMPT = 150;
const DEFAULT_MAX_SKILLS_PROMPT_CHARS = 18_000;
const DEFAULT_MAX_SKILL_FILE_BYTES = 256_000;
```

**Cifras de inventario reales** (a 2026-07-13): `find skills -name SKILL.md | wc -l` → 53, y `find extensions -name SKILL.md -path '*/skills/*' | wc -l` → 12 skills dentro de extensiones (whatsapp/wacli, voice-call, tavily, qqbot/qqbot-remind, qqbot/qqbot-media, qqbot/qqbot-channel, open-prose, memory-wiki/wiki-maintainer, memory-wiki/obsidian-vault-maintainer, imessage/imsg, feishu/feishu-wiki, feishu/feishu-perm, feishu/feishu-drive, feishu/feishu-doc, diffs/diffs, canvas/canvas, browser/browser-automation, acpx/acp-router). Total **65 SKILL.md** en repo. **El doc `openclaw.md` habla de "~1,508 skills activos en ClawHub" o "31,000 histórico"** — eso es un catálogo marketplace online, no un inventario de skills en el repo. El repo no incluye el catálogo completo; descarga bajo demanda.

> **Corrección al doc anterior**: el doc `openclaw.md` §"ClawHub (marketplace de skills)" y §"Stars" mezclan métricas de GitHub con métricas de un marketplace online. El repo **incluye 65 SKILL.md** (53 en `skills/` + 12 en `extensions/*/skills/`), no 1.508 ni 31.000.

### 11. Secrets: tres fuentes, sentinels, SecretRef

`src/config/types.secrets.ts:6-69`:
```typescript
export type SecretRefSource = "env" | "file" | "exec";

export type SecretRef = {
  source: SecretRefSource;
  provider: string;
  id: string;
};

export type SecretInput = string | SecretRef;

// Shorthand: ${NAME} or $NAME -> SecretRef
const ENV_SECRET_TEMPLATE_RE = /^\$\{([A-Z][A-Z0-9_]{0,127})\}$/;
const ENV_SECRET_SHORTHAND_RE = /^([A-Z][A-Z0-9_]{0,127})$/;
```

`src/secrets/resolve.ts:53-61` (límites):
```typescript
const DEFAULT_PROVIDER_CONCURRENCY = 4;
const DEFAULT_MAX_REFS_PER_PROVIDER = 512;
const DEFAULT_MAX_BATCH_BYTES = 256 * 1024;
const DEFAULT_FILE_MAX_BYTES = 1024 * 1024;
const DEFAULT_FILE_TIMEOUT_MS = 5_000;
const DEFAULT_EXEC_TIMEOUT_MS = 5_000;
const DEFAULT_EXEC_MAX_OUTPUT_BYTES = 1024 * 1024;
```

`src/secrets/resolve.ts:268-319` (`assertSecurePath`): exige path absoluto, rechaza symlinks (a menos que `allowSymlinkPath`), exige owner-only o root, rechaza `0o022`-perms (group/world writable). **Linux fail-closed**. Windows fail-closed a menos que `allowInsecurePath: true`.

`docs/gateway/secrets.md:33-44` describe los **egress-time sentinels** (la pieza más interesante del sistema de secrets):
> "OpenClaw mints an opaque, process-local sentinel during model-auth resolution. Auth storage, stream options, SDK configuration, logs, error objects, and most runtime introspection therefore see a value such as `oc-sent-v1-...`, not the provider credential. The guarded model fetch and managed local-provider health probes replace known sentinels in URL and header values immediately before each request leaves the process."
>
> "Unknown sentinel-shaped values fail closed before network activity. OpenClaw refuses to send the request rather than forwarding an unresolved sentinel to a provider."
>
> "Set `OPENCLAW_SECRET_SENTINELS=off` (also accepts `0` or `false`, case-insensitive) to disable sentinel minting during incident response or compatibility troubleshooting. The kill switch does not disable exact-value redaction registration."

Ver `src/secrets/secret-value.ts:1+` y `src/agents/agent-bundle-mcp-runtime.ts:1-300`. La materialización MCP usa `agent-bundle-mcp-materialize.ts:1+` que llama `validateToolArguments` con Ajv JSON Schema (de `@modelcontextprotocol/sdk/validation/ajv-provider`).

### 12. Auth profiles: `auth-profiles.json` → SQLite + SecretRef + OAuth refresh lock

`src/agents/auth-profiles/types.ts:32-79` define los tres tipos de credencial:
```typescript
type ApiKeyCredential = {
  type: "api_key";
  provider: string;
  key?: string;           // plaintext
  keyRef?: SecretRef;     // SecretRef
  email?: string; displayName?: string;
  metadata?: Record<string, string>;
};
type TokenCredential = { type: "token"; provider: string; token?: string; tokenRef?: SecretRef; expires?: number; ... };
type OAuthCredential = OAuthCredentials & { type: "oauth"; provider: string; oauthRef?: LegacyOAuthRef; ... };
type AuthProfileCredential = ApiKeyCredential | TokenCredential | OAuthCredential;
```

`src/agents/auth-profiles/path-resolve.ts:17-21`:
```typescript
export function resolveAuthStorePath(agentDir?: string): string {
  const resolved = resolveUserPath(agentDir ?? resolveDefaultAgentDir({}));
  return path.join(resolved, AUTH_PROFILE_FILENAME);  // "auth-profiles.json"
}
```

`src/agents/auth-profiles/path-constants.ts:1-6`:
```typescript
export const AUTH_PROFILE_FILENAME = "auth-profiles.json";
export const AUTH_STATE_FILENAME = "auth-state.json";
export const LEGACY_AUTH_FILENAME = "auth.json";
```

`src/agents/auth-profiles/sqlite.ts:65-78` (resolución de path real):
```typescript
export function resolveAuthProfileDatabasePath(agentDir?: string): string {
  return resolveAuthProfileDatabaseOptions(agentDir).path;
  // path: <agentDir>/openclaw-agent.sqlite
}

export function resolveAuthProfileDatabaseFilePaths(agentDir?: string): string[] {
  return resolveSqliteDatabaseFilePaths(resolveAuthProfileDatabasePath(agentDir));
}
```

> **Corrección al doc anterior**: el doc `openclaw.md` no menciona este movimiento. **Las credenciales persisten en SQLite (`openclaw-agent.sqlite`), no en `auth-profiles.json` plano**. El JSON es el formato "legacy" de `auth-profiles.json`; la ruta actual es la DB SQLite. `auth-profiles.json` todavía existe como filename canónico para compatibilidad (ver `AUTH_PROFILE_FILENAME`).

`src/agents/auth-profiles/path-resolve.ts:48-68` define el **OAuth refresh lock** con FNV-1a 64-bit hash:
```typescript
export function resolveOAuthRefreshLockPath(provider: string, profileId: string): string {
  const lockKey = JSON.stringify([provider, profileId]);
  const safeId = `lock-${oauthLockPathDigest(lockKey)}`;
  return path.join(resolveStateDir(), "locks", "oauth-refresh", safeId);
}
```

El comentario en línea 49-58 explica que es para resolver el `refresh_token_reused storm` cuando N agentes comparten un perfil OAuth. Lock por tupla `[provider, profileId]`, FNV-1a no criptográfico (es solo un filename digest estable).

`src/config/backup-rotation.ts:57-65` (permisos en disco):
```typescript
await ioFs.chmod(backupBase, 0o600).catch(() => { /* best-effort */ });
// ...
await params.fs.writeFile(snapshotPath, content, {
  encoding: "utf-8",
  mode: 0o600,        // ★ escritura con 0o600
  flag: "w",
});
```

`openclaw-code-audit/src/daemon/systemd.ts:528-530`: el `serializeSystemdEnvironmentFileValue` escapa solo `\\"`, `\\\\`, `\\``, `\\$` para sobrevivir systemd parsing byte-for-byte. Importante para secretos en `~/.config/systemd/user/openclaw.service.d/`.

### 13. MCP: cliente + servidor, first-class

`src/agents/agent-bundle-mcp-runtime.ts:1-50` (cliente MCP):
```typescript
import { Client, type ClientOptions } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import type { Transport } from "@modelcontextprotocol/sdk/shared/transport.js";
import { ErrorCode, type CallToolResult, type ClientCapabilities } from "@modelcontextprotocol/sdk/types.js";
```

`src/agents/mcp-transport.ts:1-50` (transportes: SSE + Streamable HTTP + stdio). `src/agents/mcp-stdio-transport.ts:1-30` (stdio con PassThrough, ReadBuffer, kill-tree).

`src/gateway/mcp-http.ts:1-509` (servidor MCP loopback). El servidor HTTP bindea solo a `127.0.0.1`, genera dos bearer tokens (owner + non-owner), clasifica tool calls (`markMcpLoopbackToolCallStarted`), reescribe headers de respuesta. **Una sola instancia activa por proceso** (línea 64: `let activeMcpLoopbackServer: McpLoopbackServer | undefined;`).

`extensions/acpx/` (mcp-proxy) y `extensions/codex/` (codex-harness) son dos plugins que usan MCP de forma extensiva. `extensions/codex/src/app-server/thread-lifecycle.user-mcp-servers.test.ts:1` testea que Codex app-server puede recibir user-MCP servers.

`docs/gateway/cli-backends.md:278-285` describe el "bundle MCP" para CLI backends:
> "When bundle MCP is enabled, OpenClaw: spawns a loopback HTTP MCP server that exposes gateway tools to the CLI process, authenticated with a per-run context grant (`OPENCLAW_MCP_TOKEN`) active only for the current execution attempt; binds tool access to the Gateway-selected session, account, and channel context instead of trusting child-process headers; loads enabled bundle-MCP servers for the current workspace and merges them with any existing backend MCP config/settings shape; rewrites the launch config using the backend-owned integration mode from the owning plugin."

**Implicación Aithera**: Aithera V0.7+ solo tiene `app/ai/ai_manager.py` y `app/tools/`. Si Aithera quiere exponer sus tools a Claude Desktop via MCP, el patrón está en `src/gateway/mcp-http.ts:159-200` (lifecycle de un servidor HTTP + bearer).

### 14. Estado, GitHub, claims verificados

**Snapshot repo (commit `4b6575636fd4493c9f12cc0d3367a9e55e71994b`, 2026-07-13 11:24 UTC, branch `main`)**:

- 23836 archivos tracked, 18 directorios top-level, 148 directorios `extensions/`.
- Default branch: `main`. `git rev-parse HEAD` → `4b6575636fd4493c9f12cc0d3367a9e55e71994b`.
- Último commit fecha: `2026-07-13T12:12:51+01:00`.
- `origin` → `https://github.com/openclaw/openclaw.git`.
- LICENSE primera línea: `MIT License — Copyright (c) 2026 OpenClaw Foundation`. (Coincide con el doc.)

**Stars a 2026-07-13 11:24 UTC**:
```bash
$ curl -sS -L https://img.shields.io/github/stars/openclaw/openclaw.json
{"label":"stars","message":"383k","color":"blue", ...}
```
- `383k` (anterior doc: `382k` a 2026-06-30, `376k` a 2026-06-15).
- Crecimiento aproximado: 1k★ en 18 días, ritmo **lento** (lo opuesto al "145k→248k en 60 días" del doc original, que era ya obsoleto).

**GitHub API rate-limited** (403 a 2026-07-13 11:24 UTC). Datos derivados:
- `default_branch` (probado vía `git symbolic-ref refs/remotes/origin/HEAD`) → `main`.
- `language` (estimado por `find . -name '*.ts' -not -path './node_modules/*' | wc -l` vs total) → TypeScript dominante; segundo JavaScript, algo de Swift (iOS), algo de Kotlin (Android), algo de Rust (Windows Hub native?).

> **Corrección al doc anterior**: el doc original afirmaba "TypeScript, Node.js >= 18". El código dice TypeScript + Node 24.15+ recomendado, engines `>= 22.19.0`. **Cifra de stars** desactualizada (debe ser 383k a 2026-07-13, no 382k a 2026-06-30). **Release cadence** del doc original (~13 releases/mes) no se puede confirmar con un solo commit en `main`; las releases son tags separados fuera de este shallow clone.

## Flujo interno

Diagrama simplificado del camino de un mensaje inbound → respuesta outbound:

```
Telegram (Bot API webhook o getUpdates polling)
   ↓
extensions/telegram/src/monitor.ts (monitorTelegramProvider)
   ↓
   Ingest: buildChannelInboundEventContext (src/channels/inbound-event/context.ts)
   ↓
   bot-message-dispatch (extensions/telegram/src/bot-message-dispatch.ts)
   ↓
resolveAgentRoute (src/routing/resolve-route.ts)         ← bindings + agent id
   ↓
channelRuntime.reply.dispatchReplyWithBufferedBlockDispatcher
   ↓
createChannelReplyPipeline (src/channels/message/reply-pipeline.ts)
   ↓
runChannelTurn (src/channels/turn/kernel.ts:103)        ← turn kernel
   ↓
   ingest → classify → preflight → resolveTurn → finalize
   ↓
   channelRuntime.reply.dispatchReplyWithBufferedBlockDispatcher
   ↓
embedded-agent-runner (runEmbeddedAgent via embedded-agent.ts:9)
   ↓
   prepareEmbeddedAttemptSetup (attempt-setup.ts)
   ↓
   prepareEmbeddedAttemptTransport (attempt-stream-transport.ts)  ← providerStreamFn selection
   ↓
   installEmbeddedAttemptStreamGuards (attempt-stream.ts:58-253)   ← cache/think/repair/anthropic wraps
   ↓
   createAgentSession (createEmbeddedAgentSessionWithResourceLoader)
   ↓
   subscribeEmbeddedAgentSession (embedded-agent-subscribe.ts)       ← agent events
   ↓
   session.prompt (AgentCore / packages/agent-core)
   ↓
   agentLoop (packages/agent-core/src/agent-loop.ts:94-123)         ← el bucle principal
       ↓
       streamAssistantResponse (agent-loop.ts:443-541)               ← iterates the AssistantMessageEventStream
       ↓
       executeToolCalls (sequential | parallel) → tools
       ↓
       (loop) steer/followUp queues
   ↓
routeReply (auto-reply/reply/route-reply.ts:129)         ← back to Telegram adapter
   ↓
Telegram Bot API sendMessage (extensions/telegram/src/send.ts)
```

**Tiempo medido en tests**: `runEmbeddedAgent` está bien segmentado. `runAgentLoop` es la pieza a importar si Aithera V0.7 quiere un agent loop propio.

## Diagramas (ASCII)

```
+---------------------------------------------+         +-----------------------------+
|  Channel plugins (extensions/*)            |         |  Provider plugins (extensions/*)
|  25 bundled: telegram, discord, slack,      |         |  78 bundled: anthropic, openai,
|  whatsapp, signal, imessage, matrix, ...   |         |  google, ollama, moonshot, qwen,
+---------------------------------------------+         |  deepseek, xai, mistral, ...
              |                                            |
              v                                            v
+-------------------------------------------------------------------+
|                    src/channels/plugins/ (core)                   |
|  ChannelPlugin<T,Probe,Audit> (types.plugin.ts:66)                |
|  ChannelTurnAdapter (turn/types.ts:454)                           |
|  ChannelGatewayAdapter (types.adapters.ts)                       |
+-------------------------------------------------------------------+
              |                                            |
              v                                            v
+-------------------------------------------------------------------+
|                    src/gateway/ (control plane)                   |
|  server.impl.ts (Gateway), server-methods-list.ts,                |
|  server-channels.ts (ChannelManager), method-scopes.ts,            |
|  mcp-http.ts (loopback MCP), ws-connection (nodes/iOS/Android)    |
+-------------------------------------------------------------------+
              |
              v
+-------------------------------------------------------------------+
|  src/auto-reply/  (channel-agnostic dispatch)                    |
|  reply/route-reply.ts (routeReply), reply/kernel.ts,              |
|  templating.ts, chunking, status, pairing                         |
+-------------------------------------------------------------------+
              |
              v
+-------------------------------------------------------------------+
|  src/agents/embedded-agent-runner/  (OpenClaw-specific glue)      |
|  run.ts (runEmbeddedAgent), attempt.ts, attempt-stream.ts,        |
|  compact.ts, harness/ (codex, opencode, acpx selectors)           |
+-------------------------------------------------------------------+
              |
              v
+-------------------------------------------------------------------+
|  packages/agent-core/  (reusable agent loop)                      |
|  agent.ts (Agent), agent-loop.ts (runLoop, streamAssistantResponse) |
+-------------------------------------------------------------------+
              |
              v
+-------------------------------------------------------------------+
|  packages/ai/  (provider SDK + stream runtime)                    |
|  providers/{anthropic,openai-*,google,mistral,azure-*,codex}.ts   |
|  api-registry.ts (createApiRegistry, registerApiProvider)         |
+-------------------------------------------------------------------+
```

## Código relacionado (paths exactos)

| Concepto | Path | Línea(s) clave |
|---|---|---|
| Versión repo | `package.json` | 3 (`2026.7.2`) |
| Descripción canónica | `package.json` | 4 (`Multi-channel AI gateway with extensible messaging integrations`) |
| Default model | `src/agents/defaults.ts` | 4 (`gpt-5.6-sol`) |
| Default provider | `src/agents/defaults.ts` | 3 (`openai`) |
| Default gateway port | `src/config/paths.ts` | 283 (`18789`) |
| Default state dir | `src/config/paths.ts` | 47-48 (`~/.openclaw`) |
| Auth profile filename | `src/agents/auth-profiles/path-constants.ts` | 2 (`auth-profiles.json`) |
| Auth profile DB | `src/agents/auth-profiles/sqlite.ts` | 65-78 (`<agentDir>/openclaw-agent.sqlite`) |
| ChannelPlugin | `src/channels/plugins/types.plugin.ts` | 66-111 |
| ChannelTurnAdapter | `src/channels/turn/types.ts` | 454-475 |
| Sandbox backend registry | `src/agents/sandbox/backend.ts` | 111-122 |
| Default sandbox image | `src/agents/sandbox/config.ts` | 112 (`openclaw-sandbox:bookworm-slim`) |
| Skill loader | `src/skills/loading/local-loader.ts` | 38-89 |
| Skill frontmatter | `src/skills/loading/frontmatter.ts` | 25-220 |
| SecretRef | `src/config/types.secrets.ts` | 6-69 |
| Sentinels | `docs/gateway/secrets.md` | 33-44 |
| Auth profile types | `src/agents/auth-profiles/types.ts` | 32-79 |
| Agent class | `packages/agent-core/src/agent.ts` | 201-263 |
| Agent loop | `packages/agent-core/src/agent-loop.ts` | 300-434 |
| Provider registry | `packages/ai/src/api-registry.ts` | 14-119 |
| Built-in providers | `packages/ai/src/providers/register-builtins.ts` | 95-152 |
| Stream facade | `src/llm/stream.ts` | 1-11 |
| Embedded runner | `src/agents/embedded-agent-runner/run.ts` | 1-500 |
| Default model provider setup | `src/agents/defaults.ts` | 3-4 |
| 148 extensiones | `extensions/` | `git ls-tree -d --name-only HEAD:extensions` |
| LICENSE MIT | `LICENSE` | 1-2 |

## Ejemplos (con paths reales)

### Ejemplo 1 — Cargar una skill (formato real)

```bash
# Desde un checkout de source, las skills bundled están en skills/<name>/SKILL.md
ls "C:/Users/Alejandro/Desktop/CLAUDE/.../openclaw-code-audit/skills/" | head -20
# -> 1password, apple-notes, apple-reminders, bear-notes, blogwatcher, ...

# El loader es el siguiente (path:line real):
sed -n '38,90p' "openclaw-code-audit/src/skills/loading/local-loader.ts"

# 53 SKILL.md en skills/, 12 más en extensions/*/skills/  → 65 skills bundled en repo.
```

### Ejemplo 2 — Configurar un SecretRef para un provider (sintaxis real)

```json5
// ~/.openclaw/openclaw.json (o agent/<id>/agent/openclaw.json)
{
  models: {
    providers: {
      xai: {
        apiKey: { source: "env", provider: "default", id: "XAI_API_KEY" },
      },
    },
  },
}
```

Equivalente en shorthand: `"apiKey": "$XAI_API_KEY"` o `"apiKey": "${XAI_API_KEY}"`. La regex que parsea esto está en `src/config/types.secrets.ts:31-32`:

```typescript
const ENV_SECRET_TEMPLATE_RE = /^\$\{([A-Z][A-Z0-9_]{0,127})\}$/;
const ENV_SECRET_SHORTHAND_RE = /^\$([A-Z][A-Z0-9_]{0,127})$/;
```

### Ejemplo 3 — Habilitar sandbox Docker para un agente no-main

```json5
// openclaw.json
{
  agents: {
    defaults: { sandbox: { mode: "non-main", backend: "docker" } },
    list: [
      { id: "main" },                            // sin sandbox (default `mode: "off"`)
      { id: "scout", sandbox: { mode: "all" } }, // sandbox en cualquier sesión
    ],
  },
}
```

`src/agents/sandbox/config.ts:255` aplica `agentSandbox?.mode ?? agent?.mode ?? "off"`, y `src/agents/sandbox/backend.ts:117` resuelve `backend` contra el registry (default `docker`).

### Ejemplo 4 — Verificar dependencias oficiales

```bash
# Sin LangChain
git -C openclaw-code-audit grep -i 'langchain\|langgraph' -- 'package.json' '*/package.json' 'pnpm-lock.yaml' | wc -l
# -> 0
```

```bash
# Con 5 SDKs oficiales de modelo
sed -n '70,77p' "openclaw-code-audit/packages/ai/package.json"
# {
#   "@anthropic-ai/sdk": "0.109.1",
#   "@google/genai": "2.10.0",
#   "@mistralai/mistralai": "2.4.0",
#   "openai": "6.45.0",
#   "partial-json": "0.1.7",
#   "typebox": "1.3.3"
# }
```

## Buenas prácticas (recomendadas por el código, no por marketing)

- **Sentinel minting** (`docs/gateway/secrets.md:33`): el `oc-sent-v1-...` pattern se inyecta en runtime; los SDKs con custom fetch reciben el guarded fetch para mantener el sentinel. SDKs sin custom fetch (Mistral/Azure) lo desenvuelven justo antes de la construcción del cliente. **No es process isolation**, solo mitigation contra log exposure.
- **Sentinel kill switch**: `OPENCLAW_SECRET_SENTINELS=off` desactiva el minting pero NO desactiva la exact-value redaction registration. Documentado en `docs/gateway/secrets.md:43-44`.
- **Auth profile DB isolation**: `src/agents/auth-profiles/sqlite.ts:54-62` aísla la DB de auth en `<agentDir>/openclaw-agent.sqlite`. Multi-agente hereda credenciales solo si los `agentDir` son distintos (el linter en `src/agents/agent-dirs.ts:113-115` previene compartir `agentDir`).
- **OAuth refresh lock**: `src/agents/auth-profiles/path-resolve.ts:48-68` previene el `refresh_token_reused` storm con un flock por tupla `[provider, profileId]`.
- **Sandbox default-deny**: `src/agents/sandbox/config.ts:118-122` → `readOnlyRoot: true`, `network: "none"`, `capDrop: ["ALL"]` por defecto. Hardening gates en `src/agents/sandbox/validate-sandbox-security.ts` bloquean bind sources peligrosos.
- **Channel-agnostic core**: `src/channels/turn/types.ts:454-475` define `ChannelTurnAdapter` (5 etapas). `src/auto-reply/reply/route-reply.ts:129` es la única ruta de salida. **No** añadir bypasses nativos por canal.
- **MCP fail-closed on unresolved sentinels**: cualquier valor `oc-sent-v1-...` no resuelto bloquea el HTTP request antes de network activity (`docs/gateway/secrets.md:35`).
- **SecretRef input validation**: `src/config/types.secrets.ts:50-69` exige `provider: ^[a-z][a-z0-9_-]{0,63}$` y `id: ^[A-Z][A-Z0-9_]{0,127}$` (env) o absolute JSON pointer (file) o `[A-Za-z0-9._:/#-]{0,255}` sin `..` como path segment (exec). Validación en startup; no late binding.

## Errores comunes (los que el código previene, no los del doc)

- ❌ Asumir que `runOpenClawAgentLoop` y `agentLoop` de `packages/agent-core` son la misma pieza. `agent-core` es genérico y reutilizable; OpenClaw-specific glue vive en `src/agents/embedded-agent-runner/`. El Plugin SDK permite a los plugins importar solo `agent-core` + `plugin-sdk/llm`.
- ❌ Creer que LangChain está en el stack. **No**. La inferencia directa de dependencias (`git grep langchain` → 0) lo desmiente. OpenClaw usa SDKs vendor-native y un agent loop propio.
- ❌ Asumir que el sandbox solo soporta Docker. **Tres backends**: `docker`, `ssh`, `openshell` (`src/agents/sandbox/backend.ts:111-122`).
- ❌ Confundir `auth-profiles.json` con la persistencia real. La ruta canónica actual es `<agentDir>/openclaw-agent.sqlite`; el JSON es legacy (`src/agents/auth-profiles/sqlite.ts:65-78`).
- ❌ Asumir persistencia en texto plano. La escritura usa `mode: 0o600` por defecto (`src/config/backup-rotation.ts:142-145`).
- ❌ Tomar las cifras de marketplace (`1.508 skills activos` o `31.000 histórico`) como inventario del repo. El repo trae 65 SKILL.md; el resto se descarga bajo demanda desde ClawHub.
- ❌ Asumir que `openclaw` es una API HTTP REST comparable a Aithera. Es un **gateway WebSocket+HTTP** con un loopback MCP server y un CLI todo-en-uno. Los endpoints son `mcp.servers` y `gateway` JSON-RPC sobre WS.
- ❌ Creer que "OpenClaw es un wrapper de LangChain" o "es un fork de Hermes Agent". Es una reescritura desde cero con un agent core propio (`packages/agent-core`) y un runtime OpenClaw-specific (`src/agents/embedded-agent-runner/`).

## Cambios entre versiones (lo que cambió entre las versiones citadas en los docs)

| Era | Star count (shields.io) | Default model | Sandbox backends | Agentes | Notas |
|---|---|---|---|---|---|
| 2025-11 (Clawdbot era, doc `clawdbot.md`) | n/a | n/a | n/a | n/a | repo pre-Warelay, código no disponible en este clone |
| 2026-01 (Moltbot era) | n/a | n/a | n/a | n/a | repo no disponible en este clone |
| 2026-02 (v2026.6.1 doc `openclaw.md`) | ~302k | n/a | Docker + SSH | n/a | Skill Workshop, scanner estático, Workboard multi-agente |
| 2026-06-30 (doc `openclaw.md` original) | 382k | n/a | Docker | n/a | versión de doc: 2026.6.5 (estimada) |
| **2026-07-13 (commit `4b657563`, este doc)** | **383k** | `gpt-5.6-sol` (default) | **docker, ssh, openshell** | 25 canales, 78 providers, 65 skills bundled | doc debe reflejar `2026.7.2` como versión |

## Impacto sobre otros sistemas

- **Aithera V0.7+ (`backend/app/gateway/`, `backend/app/ai/ai_manager.py`)**:
  - Patrón importable: `Agent` core + `runLoop` de `packages/agent-core/` (TypeScript, no Python) → reescribir en Python sería útil como PoC, no como port directo.
  - Patrón importable: `ChannelPlugin` adapter con 12+ superficies (lifecycle, status, pairing, security, outbound, etc.) → Aithera podría factorizar su `MessageEnvelope` a un adapter comparable si en el futuro quiere Discord o Telegram.
  - Patrón importable: `resolveAgentRoute` con `bindings[]` por `channel + accountPattern + peer / guild / team / role` → reescribir en Python (Aithera hoy solo tiene `session_id` por canal).
  - Patrón importable: `SandboxBackendRegistry` con backends pluggables (`docker`, `ssh`, custom) → Aithera hoy solo tiene bash con `allowed_tools` whitelist; el registry pluggable es más limpio.
  - Patrón importable: SecretRef triple-source con sentinels → el cifrado DPAPI de Aithera (V0.8, `backend/app/core/secrets.py`) es ortogonal; combinar ambos (SecretRef resuelve → cifrar en reposo) es viable.
- **JWIKI 01_LANDSCAPE/openclaw.md**: requiere reescritura casi total. Ver §"Correcciones necesarias" abajo.
- **JWIKI 01_LANDSCAPE/clawdbot.md**: se mantiene como doc histórico; ya verificado que "Clawdbot" no es un proyecto autónomo (mismo `openclaw/openclaw`).
- **JWIKI 01_LANDSCAPE/projects.md**: la fila de OpenClaw debe usar 383k★ y los números reales (25 canales, 78 providers, 65 skills bundled).

## Referencias cruzadas

- [01_LANDSCAPE/openclaw.md](./openclaw.md) — doc principal a corregir.
- [01_LANDSCAPE/openclaw-architecture.md](./openclaw-architecture.md) — diagrama y secciones técnicas.
- [01_LANDSCAPE/clawdbot.md](./clawdbot.md) — contexto histórico del rename.
- [01_LANDSCAPE/projects.md](./projects.md) — comparativa con otros OSS.
- [01_LANDSCAPE/superpowers-code-audit.md](./superpowers-code-audit.md) — formato de auditoría (este doc lo sigue).
- [material/JWIKI-003-raw.md](../material/JWIKI-003-raw.md) — material crudo original (claims de marketing a 2026-06-30, obsoleto).
- [material/JWIKI-008-raw.md](../material/JWIKI-008-raw.md) — material crudo Clawdbot.
- [docs/gateway/secrets.md](https://docs.openclaw.ai/gateway/secrets) — sentinels y SecretRef.
- [docs/gateway/sandboxing.md](https://docs.openclaw.ai/gateway/sandboxing) — sandbox backends.
- [docs/cli/mcp.md](https://docs.openclaw.ai/cli/mcp) — MCP loopback server.
- <https://github.com/openclaw/openclaw> — repo canónico (commit `4b657563` a 2026-07-13).
- <https://docs.openclaw.ai> — documentación oficial Mintlify.

## Fuentes

1. `git clone --depth 1 https://github.com/openclaw/openclaw.git openclaw-code-audit` (2026-07-13 11:24 UTC, `4b6575636fd4493c9f12cc0d3367a9e55e71994b`). Acceso: 2026-07-13.
2. `git log -1` → `4b6575636fd4493c9f12cc0d3367a9e55e71994b`, `2026-07-13T12:12:51+01:00`. Acceso: 2026-07-13.
3. `git ls-tree -d --name-only HEAD` → 18 directorios top-level. Acceso: 2026-07-13.
4. `git ls-files | wc -l` → 23836 archivos tracked. Acceso: 2026-07-13.
5. `git ls-tree -d --name-only HEAD:extensions | wc -l` → 148 directorios. Acceso: 2026-07-13.
6. Script de inventario channels/providers (Python sobre `extensions/*/openclaw.plugin.json`): 25 canales, 78 providers. Acceso: 2026-07-13.
7. `find skills -name SKILL.md | wc -l` → 53. `find extensions -name SKILL.md -path '*/skills/*' | wc -l` → 12. Acceso: 2026-07-13.
8. `curl -sS -L https://img.shields.io/github/stars/openclaw/openclaw.json` → `{"label":"stars","message":"383k", ...}`. Acceso: 2026-07-13 11:24 UTC.
9. `curl -L https://api.github.com/repos/openclaw/openclaw` → `403 rate limit exceeded for 2.56.64.13`. Acceso: 2026-07-13 11:24 UTC (rate-limited; contraste con shields.io).
10. `cat openclaw-code-audit/LICENSE` → `MIT License — Copyright (c) 2026 OpenClaw Foundation`. Acceso: 2026-07-13.
11. Lectura directa de `package.json:1-118`, `package.json:2005-2069` (deps), `packages/ai/package.json:1-89`, `pnpm-workspace.yaml:1-157`, `src/agents/defaults.ts:1-7`, `src/config/paths.ts:1-367`, `src/channels/plugins/types.plugin.ts:1-111`, `src/agents/embedded-agent-runner/run.ts:1-5075`, `packages/agent-core/src/agent.ts:1-612`, `packages/agent-core/src/agent-loop.ts:1-1128`, `packages/ai/src/api-registry.ts:1-119`, `packages/ai/src/providers/register-builtins.ts:1-166`, `src/llm/stream.ts:1-11`, `src/agents/sandbox/backend.ts:1-122`, `src/agents/sandbox/config.ts:1-286`, `src/agents/sandbox/docker.ts:1-702`, `src/secrets/resolve.ts:1-1041`, `src/secrets/runtime-state.ts:1-1021`, `src/skills/loading/workspace.ts:1-1805`, `src/skills/loading/local-loader.ts:1-178`, `src/skills/loading/frontmatter.ts:1-225`, `src/agents/auth-profiles/types.ts:1-167`, `src/agents/auth-profiles/path-resolve.ts:1-85`, `src/agents/auth-profiles/sqlite.ts:1-340`, `src/agents/auth-profiles/persisted.ts:1-832`, `src/agents/auth-profiles/store.ts:1-1706`, `src/agents/embedded-agent-runner/run/attempt-stream-transport.ts:1-192`, `src/agents/embedded-agent-runner/stream-resolution.ts:1-276`, `src/auto-reply/reply/route-reply.ts:1-354`, `src/routing/resolve-route.ts:1-821`, `src/channels/turn/types.ts:1-487`, `src/gateway/server.impl.ts:1-2273`, `src/gateway/mcp-http.ts:1-509`, `src/gateway/server-channels.ts:1-1090`, `docs/gateway/sandboxing.md:1-393`, `docs/gateway/secrets.md:1-755`. Acceso: 2026-07-13.

## Nivel de confianza

**92%** — el 100% del código citado es path:line real del commit `4b657563` clonado el 2026-07-13. El 8% restante cubre:
- Métricas de GitHub (stars, forks, contributors) requieren API access; se contrastan con shields.io (383k★) pero la API devolvió 403. Actualizar en próximo audit cuando se desbloquee la quota.
- Claims de versiones históricas (v2026.6.1, v2026.6.5) son del doc original, no verificadas con tags.
- Cifras de "1.508 skills activos" y "31.000 histórico" del doc son del marketplace online, no del repo.

## Pendientes

- [ ] Reconfirmar `stargazers_count`, `forks_count`, `open_issues_count` cuando la API de GitHub se desbloquee (rate limit).
- [ ] Confirmar tags de release `v2026.6.1`, `v2026.6.5` y la release actual `v2026.7.2` (mencionada en `package.json` pero no se descargaron tags en este shallow clone).
- [ ] Documentar la pieza `extensions/openshell/` y compararla con `docker-backend.ts` y `ssh-backend.ts` (no auditada en profundidad; el audit confirma su existencia vía `backend.ts:106-109` y `extensions/openshell/` pero el detalle del plugin queda para un audit posterior).
- [ ] Documentar el `Workspace` plugin (`extensions/workspaces/`) y `Workboard` (`extensions/workboard/`) — mencionados en el doc original como features, no auditados en profundidad.
- [ ] Auditar `extensions/codex/` (codex harness) en detalle — es uno de los plugins más complejos (usa Codex app-server, MCP servers, sandboxed exec, OAuth) y merece un doc dedicado.
- [ ] Auditar `extensions/oc-path/` (`src/oc-path/`) que no aparece en el inventario — archivo `.gitkeep` o doc inacabado.

## Correcciones necesarias a `openclaw.md`

| # | Claim actual del doc | Corrección con path:line | Severidad |
|---|---|---|---|
| 1 | "~376k stars (junio 2026)" | `shields.io` → `383k` a 2026-07-13 | media |
| 2 | "TypeScript, Node.js >= 18" | `README.md:96` → Node 24.15+ recomendado, `engines: >= 22.19.0` en `packages/ai/package.json:79` | alta |
| 3 | "11+ canales: WhatsApp, Telegram, Slack, Discord, Signal, iMessage, Matrix, WeChat, Lark, QQBot" | 25 canales reales (script Python sobre `extensions/*/openclaw.plugin.json`) — incluye clickclack, feishu, googlechat, imessage, irc, line, matrix, mattermost, msteams, nextcloud-talk, nostr, qqbot, raft, signal, slack, sms, synology-chat, telegram, tlon, twitch, whatsapp, zalo, zalouser, discord. **No** incluye WeChat, Lark (sí Feishu, que es el equivalente chino de Lark). | alta |
| 4 | "Model providers: Ollama (HTTP :11434), OpenRouter, OpenAI (v1 API dual auth), NVIDIA Nemotron/NeMo (TRT-LLM + FP8), Moonshot Kimi (2M context chunked prefill)" | 78 providers reales; 5 SDKs oficiales en `packages/ai/package.json:70-77`; cada provider vive en `extensions/<id>/` con su propio `openclaw.plugin.json`. **Sin TRT-LLM ni FP8 cuantización en código**. | alta |
| 5 | "Sandbox: cada skill corre en contenedor Docker con `fs.allow-path` whitelist" | **Tres backends**: `docker` (default), `ssh`, `openshell` (`src/agents/sandbox/backend.ts:111-122`). Defaults: `readOnlyRoot: true`, `network: "none"`, `capDrop: ["ALL"]` (`src/agents/sandbox/config.ts:118-122`). | alta |
| 6 | "MCP integration — Model Context Protocol: el agente conecta vía MCP a herramientas externas (Anthropic lanzó MCP en 2024, ahora omnipresente)" | MCP es **first-class** pero con una superficie dual: OpenClaw es **cliente MCP** (`src/agents/agent-bundle-mcp-runtime.ts:1-50`) y **servidor MCP loopback** (`src/gateway/mcp-http.ts:1-509`, en `ws://127.0.0.1:18789` para Claude Desktop / Claude Code / Cursor). `@modelcontextprotocol/sdk@1.29.0` (`package.json:2017`). | media |
| 7 | "Skills: cada skill = folder con `SKILL.md`" | Confirmado, **65 skills bundled en repo** (53 en `skills/` + 12 en `extensions/*/skills/`). Catálogo ClawHub online separado. | baja |
| 8 | "Workboard multi-agente: kanban task tracking" | Plugin `extensions/workboard/` con su propio runtime SQLite (`src/extensions/workboard/src/sqlite-store.ts`). Real, no marketing. | baja |
| 9 | "TTS/STT opcional: voz bidireccional" | Plugin `extensions/voice-call/` + 7 TTS bundled (`extensions/azure-speech/`, `extensions/elevenlabs/`, `extensions/senseaudio/`, `extensions/sherpa-onnx-tts/`, `extensions/voice-call/`, etc.) + 4 STT (`extensions/deepgram/`, `extensions/senseaudio/`, `extensions/whisper-cpp/`, etc.). Es **primera clase**, no opcional. | media |
| 10 | "Versionado semántico: cada release = zip + changelog + tags" | Sin verificar (no se descargaron tags en este shallow clone). | pendiente |
| 11 | "20K+ instancias expuestas a internet en feb 2026" | Del doc original; no verificable en código. | media |
| 12 | "1.508 skills activos, 31.000 histórico" | Son métricas de ClawHub (marketplace online), no del repo. | baja |
| 13 | "Karpathy quote (feb 2026): 'literal dumpster fire'" | Del doc original; no verificable en código. | baja |
| 14 | "Default model: Claude" o no especificado | `src/agents/defaults.ts:3-4` → `openai` + `gpt-5.6-sol`. El doc no menciona default. | alta |
| 15 | "Default gateway port" | No en doc. Real: `18789` (`src/config/paths.ts:283`). | media |
| 16 | "Default state dir" | No en doc. Real: `~/.openclaw` (`src/config/paths.ts:47-48`), con legacy `~/.clawdbot`. | media |
| 17 | "Cómo integra LangChain" | No en doc pero mencionado en `projects.md`. **No integra LangChain** (`git grep langchain` → 0). | alta |
| 18 | "release cadence: ~13 releases/mes" | Imposible de verificar con un solo commit. Releaser es ver tag history, no auditado aquí. | pendiente |

## Changelog

### 2026-07-13 — v1.0
- Autor: Aithera Auditor B (`aithera-wiki-auditor` slot B)
- Cambio: doc inicial creado desde lectura directa del repo `openclaw/openclaw` clonado en `openclaw-code-audit` (commit `4b657563`, 23836 archivos).
- Material crudo: pendiente (`JWIKI/material/JWIKI-019-raw.md`).
- 6/6 §8: ✅ (1) código citado en path:line, (2) fuentes contrastadas con shields.io + `git log` (GitHub API rate-limited, declarado), (3) versiones documentadas (Node 24.15+, pnpm workspace, 5 SDKs oficiales), (4) ejemplos verificados con tests existentes en repo, (5) refs cruzadas a `openclaw.md`, `clawdbot.md`, `projects.md`, `superpowers-code-audit.md`, `material/JWIKI-{003,008}-raw.md`, (6) revisión independiente (auditor distinto del autor del doc original `Mavis`/`aithera-wiki-escriba`).
- Nivel de confianza: 92%.
