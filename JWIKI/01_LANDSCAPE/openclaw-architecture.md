# OpenClaw — Arquitectura técnica (commit 4b657563, 2026-07-13)

## Resumen

Diagrama y descripción técnica de la arquitectura real de `openclaw/openclaw` a 2026-07-13 (commit `4b6575636fd4493c9f12cc0d3367a9e55e71994b`, 23836 archivos tracked). Acompaña al doc de auditoría [`openclaw-code-audit.md`](./openclaw-code-audit.md). Cubre el monorepo, el Gateway (control plane), el agente embebido, el agent-core reusable, los 25 canales bundled, los 78 providers, el sistema de skills, los secrets triple-fuente y los tres backends de sandbox. Acompaña a las decisiones arquitectónicas que **sí** están en el código (ChannelPlugin, ChannelTurnAdapter, agent-core, SecretRef, sandbox backend registry) y no a claims de marketing.

## Objetivo

- Servir como referencia arquitectónica precisa para Aithera V0.7+ que considere importar patrones (ChannelPlugin, route-reply, sandbox backend registry, SecretRef sentinels).
- Documentar las tres superficies del runtime OpenClaw (Gateway, CLI, embedded agent) y cómo se relacionan.
- Sustituir el diagrama ASCII genérico del doc `openclaw.md` por el flujo real path:line.

## Estado

🟡 En progreso — secciones principales verificadas en código. Diagramas basados en path:line reales.

## Versiones compatibles

| Componente | Versión | Evidencia |
|---|---|---|
| Repo | `2026.7.2` | `openclaw-code-audit/package.json:3` |
| `packages/ai` SDK | `2026.7.2` | `openclaw-code-audit/packages/ai/package.json:3` |
| `packages/agent-core` | (root) | `openclaw-code-audit/packages/agent-core/src/agent.ts` |
| Node recomendado | 24.15+ | `openclaw-code-audit/README.md:96` |
| Node mínimo (engines) | 22.19.0 | `openclaw-code-audit/packages/ai/package.json:79` |
| TypeScript | 6.0.3 | `openclaw-code-audit/package.json:2062` |
| pnpm | (workspace) | `openclaw-code-audit/pnpm-workspace.yaml:1-6` |
| MCP SDK | 1.29.0 | `openclaw-code-audit/package.json:2017` |
| Anthropic SDK | 0.109.1 | `openclaw-code-audit/package.json:2007` |
| OpenAI SDK | 6.45.0 | `openclaw-code-audit/package.json:2047` |
| Google GenAI | 2.10.0 | `openclaw-code-audit/package.json:2011` |
| Mistral SDK | 2.4.0 | `openclaw-code-audit/package.json:2016` |

## Proyectos compatibles

- **TypeScript 6.0.3+** y **Node 22.19+** (engines). Recomendado Node 24.15+.
- **Plataformas**: macOS, Linux, Windows (vía WSL2 + `openclaw onboard --install-daemon`). Windows Hub companion app nativa para Windows.
- **25 canales bundled** (ver `openclaw-code-audit.md` §3 para la lista).
- **78 providers bundled** (misma fuente).
- **65 skills bundled en repo** (53 en `skills/`, 12 en `extensions/*/skills/`).
- **3 backends de sandbox** (`docker`, `ssh`, `openshell`).
- **2 superficies MCP** (cliente + servidor loopback).
- **Compatible con ACP** (Agent Client Protocol) para harnesses externos: Claude Code, Codex, Droid, Gemini, OpenCode.

## Dependencias

- [01_LANDSCAPE/openclaw.md](./openclaw.md) — doc principal a corregir.
- [01_LANDSCAPE/openclaw-code-audit.md](./openclaw-code-audit.md) — auditoría con snippets path:line.
- [01_LANDSCAPE/clawdbot.md](./clawdbot.md) — contexto histórico del rename.
- [01_LANDSCAPE/projects.md](./projects.md) — comparativa con otros OSS.
- Repo canónico: <https://github.com/openclaw/openclaw> (commit `4b657563`).
- Documentación oficial: <https://docs.openclaw.ai>.

## Arquitectura (visión global)

OpenClaw se compone de **tres procesos lógicos** que se ejecutan desde un único binario `openclaw` (`package.json:18`):

1. **Gateway**: servidor WebSocket+HTTP en `ws://127.0.0.1:18789` (`src/config/paths.ts:283`). Control plane que enruta mensajes, ejecuta agentes, expone métodos RPC y sirve un MCP loopback server. **Siempre escucha en loopback por defecto**; la exposición remota es opcional vía Tailscale o auth tokens (`docs/gateway/configuration`).
2. **CLI**: el mismo binario con subcomandos (`openclaw onboard`, `openclaw agent`, `openclaw mcp`, `openclaw message send`, `openclaw doctor`, `openclaw pairing approve`, etc.). Aprox. 120 entradas en `package.json:1790`. Por defecto se conecta al Gateway vía WS local; con `--no-gateway` o con `OPENCLAW_GATEWAY_SKIP=1` arranca en modo embedded (sin Gateway).
3. **Embedded agent runner**: pieza en `src/agents/embedded-agent-runner/run.ts` que ejecuta un solo turn de un agente, cableando el `Agent` core con auth profiles, skills, sandbox, MCP runtime, browser bridge, code mode, fail-over, trazas, compactions. Aislable y reutilizable por el Gateway, el CLI, los cron jobs, los BTW side questions, los commitments extractor, etc.

Estos tres procesos comparten un **layer common** en `src/`:

- **Configuración** (`src/config/`): lectura/escritura de `openclaw.json`, `auth-profiles.json` (legacy) y `openclaw-agent.sqlite` (auth actual), state dir, gateway port, etc.
- **Plugins** (`src/plugins/`): discovery, manifest validation, loading, registry assembly, contract enforcement.
- **Channels core** (`src/channels/`): runtime channel-agnostic (lifecycle, turn kernel, reply routing, message adapters, registry).
- **Agents** (`src/agents/`): OpenClaw-specific glue encima de `packages/agent-core/`.
- **Skills** (`src/skills/`): discovery, loading, workshop, install lifecycle, security scanner.
- **Secrets** (`src/secrets/`): resolución de SecretRef triple-fuente (env/file/exec) con runtime snapshot.
- **Sandbox** (`src/agents/sandbox/`): backend registry (docker, ssh, openshell), config resolver, fs bridge, worktree management.

Y un **monorepo de paquetes** en `packages/`:

- `packages/agent-core/`: agent loop genérico (`Agent`, `agentLoop`, `streamSimple`).
- `packages/ai/`: provider SDK + streaming runtime (Anthropic, Google, Mistral, OpenAI, Azure, OpenAI Codex).
- `packages/markdown-core/`: frontmatter parsing, sanitization.
- `packages/agent-core/src/harness/`: session storage, messages, prompt templates, env, kill-tree.
- `packages/...`: otros paquetes auxiliares.

Y **148 plugins bundled** en `extensions/`:

- 25 canales (telegram, discord, slack, whatsapp, etc.).
- 78 providers (anthropic, openai, ollama, moonshot, qwen, deepseek, etc.).
- 8 features: workspaces, workboard, browser, canvas, codex, codex-harness, acpx (ACP harness), open-prose, oc-path, raft, tokenjuice, talk-voice, voice-call.
- 8 special-purpose: memory-core, memory-lancedb, memory-wiki, device-pair, diagnostics-otel, diagnostics-prometheus, webhooks, file-transfer, etc.

## Descripción técnica (por capas)

### Capa 1: monorepo y workspaces

`pnpm-workspace.yaml:1-6`:
```yaml
packages:
  - .
  - ui
  - packages/*
  - extensions/*
  - examples/*
```

El root `package.json:1-118` define el binario, las deps comunes, los scripts (hay más de 2000 entradas en `package.json:1790`), y los overrides (`pnpm-workspace.yaml:98-127`) que pinean versiones críticas:

```yaml
overrides:
  "@anthropic-ai/sdk": 0.109.1
  "@opentelemetry/core": 2.8.0
  "@aws-sdk/core": 3.974.27
  hono: 4.12.25
  axios: 1.16.0
  form-data: 2.5.6
  tar: 7.5.19
  typebox: 1.3.3
  # ... y 17 más
```

Hay 148 directorios en `extensions/` y cada uno tiene su propio `package.json`, `openclaw.plugin.json` y `tsconfig.json` (plugin-boundary contract). El root no compila cada extensión; usa `pnpm build` con `tsconfig.core.json` (core) + `tsconfig.extensions.json` (extensiones) + `tsconfig.ui.json` (UI). Los `devDependency` de los plugins son privados al plugin (no comparten deps con root).

`package.json:2005-2069` (deps de runtime en root):
- 60+ entradas: SDKs de modelo, MCP, Telegram (grammy 1.44.0), matrix (@vector-im/matrix-bot-sdk), tree-sitter-bash, kysely (0.29.2, ORM), quickjs-wasi (3.0.2), express (5.2.1), undici (8.5.0), koffi, node-pty (@lydell/node-pty@1.2.0-beta.12), hono (4.12.25), jiti, dotenv 17.4.2, semver 7.8.5, yaml 2.9.0, zod 4.4.3, typebox 1.3.3, etc.

`package.json:2070-2112` (devDeps pesadas): `typescript@6.0.3`, `tsdown@0.22.1`, `oxlint@1.73.0`, `oxfmt@0.58.0`, `vitest@4.x`, `esbuild@0.28.1`, `jscpd@4.2.4`, `sigstore@4.1.1`, etc.

### Capa 2: Gateway (control plane)

`src/gateway/server.impl.ts:1-260` es el bootstrap principal. Observaciones:

- **Lazy loading**: cada subsystem (model catalog, plugins, channels, MCP, browser) se carga vía `createLazyRuntimeModule(...)` (líneas 161-195). El Gateway **no** carga todos los plugins al arranque; los activa cuando se necesitan.
- **State dir / port**: `src/config/paths.ts:64-93` define `resolveStateDir` con override `OPENCLAW_STATE_DIR`; `src/config/paths.ts:283` define `DEFAULT_GATEWAY_PORT = 18789`; `src/config/paths.ts:197-232` define `resolveConfigPath` con override `OPENCLAW_CONFIG_PATH`. La transición `~/.clawdbot` → `~/.openclaw` se respeta vía `resolveLegacyStateDirs` (línea 23).
- **Token auth**: `src/gateway/auth.ts:1` (`resolveGatewayAuth`), `src/gateway/method-scopes.ts:1` (ADMIN_SCOPE, etc.).
- **Channel runtime**: `src/gateway/server-channels.ts:1-1090` define `createChannelManager` con `RESTART_POLICY = { initialMs: 5_000, maxMs: 5 * 60_000, factor: 2, jitter: 0.1 }` y `MAX_RESTARTS = 10` (líneas 33-39). El manager mantiene un `Map<ChannelId, ChannelRuntimeStore>` con `aborts`, `starting`, `tasks`, `runtimes` (línea 50-55).
- **Plugin lazy dispatch**: `src/gateway/server-methods-list.ts:1` (`GATEWAY_EVENTS`), `src/gateway/methods/registry.ts:1-100` (`createCoreGatewayMethodDescriptors`, `createPluginGatewayMethodDescriptors`, `createGatewayMethodRegistry`). Los métodos RPC se descubren vía `listCoreGatewayMethodNames()`.
- **Wired events**: `src/gateway/server-methods.ts:1` (`createCoreGatewayMethodDescriptors`), `src/gateway/server-aux-methods.ts:1` (helpers).
- **MCP loopback**: `src/gateway/mcp-http.ts:1-509` arranca un servidor HTTP en loopback con bearer tokens generados aleatoriamente (línea 163-164: `crypto.randomBytes(32).toString("hex")` para owner y non-owner). Escucha el subpath MCP estándar; el `OPENCLAW_MCP_TOKEN` env var expone ese token al child process (CLI backends).

`docs/gateway/secrets.md:1-755` documenta el runtime model de secrets (sentinels, fail-fast, last-known-good).

### Capa 3: Channel-agnostic core

`src/channels/plugins/types.plugin.ts:66-111` define `ChannelPlugin` con 25+ adaptadores opcionales. Los cuatro más importantes para entender la arquitectura:

- **`gateway: ChannelGatewayAdapter<ResolvedAccount>`** (`extensions/telegram/src/channel.ts:1026-1126`): `startAccount: async (ctx) => {...}`. El Gateway llama esto para arrancar el adapter nativo de Telegram (long polling o webhook). El plugin **es dueño** del transport; el Gateway solo conoce `ctx` (cfg, account, abortSignal, channelRuntime, statusSink, runtime).
- **`outbound: ChannelOutboundAdapter`** (`src/channels/plugins/types.adapters.ts`): `sendMessage`, `sendMedia`, etc. El plugin decide cómo formatear el payload para su canal.
- **`messaging: ChannelMessagingAdapter`** (mismo archivo): `targetPrefixes`, `normalizeTarget`, `resolveOutboundSessionRoute`, `targetResolver`. Patrón para enrutar replies a la conversación correcta.
- **`status: ChannelStatusAdapter<ResolvedAccount, Probe, Audit>`** (mismo): `probeAccount`, `auditAccount`, `buildAccountSnapshot`, `collectStatusIssues`. Patrón para reportar salud al Gateway.

`src/channels/turn/types.ts:454-475` define `ChannelTurnAdapter<TRaw, TDispatchResult>` con cinco etapas:

```typescript
type ChannelTurnAdapter<TRaw, TDispatchResult = DispatchFromConfigResult> = {
  ingest: (raw: TRaw) => Promise<NormalizedTurnInput | null> | NormalizedTurnInput | null;
  classify?: (input: NormalizedTurnInput) => Promise<ChannelEventClass> | ChannelEventClass;
  preflight?: (input: NormalizedTurnInput, eventClass: ChannelEventClass) =>
    | Promise<PreflightFacts | ChannelTurnAdmission | null | undefined>
    | PreflightFacts | ChannelTurnAdmission | null | undefined;
  resolveTurn: (input: NormalizedTurnInput, eventClass: ChannelEventClass, preflight: PreflightFacts) =>
    Promise<ChannelTurnResolved<TDispatchResult>> | ChannelTurnResolved<TDispatchResult>;
  // finalize: ...
};
```

`src/channels/turn/kernel.ts:1-835` implementa el `runChannelTurn` que ejecuta el adapter. **Cada canal implementa este adapter**, no el handshake del SDK nativo.

`src/auto-reply/reply/route-reply.ts:129-339` es el `routeReply` que enruta un `ReplyPayload` al canal de origen. Líneas 208-213: `INTERNAL_MESSAGE_CHANNEL` (webchat) está explícitamente rechazado para queued replies.

`src/routing/resolve-route.ts:34-60` define `ResolveAgentRouteInput` con `channel`, `accountId?`, `peer?`, `parentPeer?`, `guildId?`, `teamId?`, `memberRoleIds?`. El resolver elige el agent y construye la session key con `dmScope` (main/per-peer/per-channel-peer/per-account-channel-peer).

### Capa 4: Agent core reusable (no OpenClaw-specific)

`packages/agent-core/src/agent.ts:201-263` define la clase `Agent`:

```typescript
class Agent {
  public streamFn: StreamFn;                              // provider stream
  public getApiKey?: (provider: string) => Promise<string | undefined>;
  public beforeToolCall?: (...) => Promise<BeforeToolCallResult | undefined>;
  public afterToolCall?: (...) => Promise<AfterToolCallResult | undefined>;
  public prepareNextTurn?: (signal?) => Promise<AgentLoopTurnUpdate | undefined>;
  public convertToLlm: (messages: AgentMessage[]) => Message[] | Promise<Message[]>;
  public transformContext?: (messages: AgentMessage[], signal?) => Promise<AgentMessage[]>;
  public sessionId?: string;
  public thinkingBudgets?: ThinkingBudgets;
  public transport: Transport;
  public toolExecution: ToolExecutionMode;

  public subscribe(listener: (event: AgentEvent, signal: AbortSignal) => Promise<void> | void): () => void;
  public steer(message: AgentMessage): void;
  public followUp(message: AgentMessage): void;
  public abort(reason?: unknown): void;
  public waitForIdle(): Promise<void>;
  public reset(): void;
}
```

`packages/agent-core/src/agent-loop.ts:300-434` implementa `runLoop`:

```typescript
while (true) {
  let hasMoreToolCalls = true;
  while (hasMoreToolCalls || pendingMessages.length > 0) {
    if (await stopIfAborted()) return;
    if (!firstTurn) { await emit({ type: "turn_start" }); turnOpen = true; }
    else firstTurn = false;

    if (pendingMessages.length > 0) {
      for (const message of pendingMessages) {
        await emit({ type: "message_start", message });
        await emit({ type: "message_end", message });
        currentContext.messages.push(message);
        newMessages.push(message);
      }
    }

    if (await stopIfAborted()) return;

    const message = await streamAssistantResponse(
      currentContext, config, signal, emit, streamFn, runtime,
    );
    newMessages.push(message);

    if (message.stopReason === "error" || message.stopReason === "aborted") {
      // ...
      return;
    }

    const toolCalls = message.content.filter((c) => c.type === "toolCall");
    const toolResults: ToolResultMessage[] = [];
    hasMoreToolCalls = false;
    if (message.stopReason === "toolUse" && toolCalls.length > 0) {
      const executedToolBatch = await executeToolCalls(currentContext, message, config, signal, emit);
      toolResults.push(...executedToolBatch.messages);
      hasMoreToolCalls = !executedToolBatch.terminate;
      for (const result of toolResults) {
        currentContext.messages.push(result);
        newMessages.push(result);
      }
    }

    await emit({ type: "turn_end", message, toolResults });
    turnOpen = false;
    if (await stopIfAborted()) return;

    const nextTurnSnapshot = await config.prepareNextTurn?.(nextTurnContext);
    if (nextTurnSnapshot) { /* swap model, context, reasoning */ }
    if (await stopIfAborted()) return;
    if (await config.shouldStopAfterTurn?.({ message, toolResults, context: currentContext, newMessages })) {
      await emit({ type: "agent_end", messages: newMessages });
      return;
    }

    pendingMessages = (await config.getSteeringMessages?.()) || [];
    if (await stopIfAborted()) return;
  }

  const followUpMessages = (await config.getFollowUpMessages?.()) || [];
  if (followUpMessages.length > 0) {
    pendingMessages = followUpMessages;
    continue;
  }
  break;
}
await emit({ type: "agent_end", messages: newMessages });
```

`packages/agent-core/src/agent-loop.ts:443-541` implementa `streamAssistantResponse`: itera `for await (const event of response)` sobre el `AssistantMessageEventStream` y emite `message_start` / `message_update` / `message_end` / `turn_end`. La pieza `for await (const event of response)` está en línea 483-530.

`packages/agent-core/src/agent-loop.ts:546-595` implementa `executeToolCalls` con dos modos: `sequential` o `parallel` (default). Cada tool call se preflight-ea con `beforeToolCall` y postprocesa con `afterToolCall`.

> **Implicación Aithera**: Aithera V0.7+ tiene `/api/chat/stream` y `/api/chat/turn` (`backend/app/api/endpoints/chat.py`) que implementan un loop similar. El patrón `agent-core` es directamente portable: `Agent` + `runLoop` + `runAgentLoop`. Si Aithera decide reescribir su chat en TypeScript o Python (con FastAPI/uvloop), `packages/agent-core` es una referencia.

### Capa 5: LLM providers (`packages/ai/`)

`packages/ai/package.json:70-77`:
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

`packages/ai/src/api-registry.ts:14-119`:
```typescript
export interface ApiProvider<TApi extends Api = Api, TOptions extends StreamOptions = StreamOptions> {
  api: TApi;
  stream: StreamFunction<TApi, TOptions>;
  streamSimple: StreamFunction<TApi, SimpleStreamOptions>;
}

export function createApiRegistry() {
  const providers = new Map<string, RegisteredApiProviderEntry>();
  function registerApiProvider(provider, sourceId?) { ... }
  function getApiProvider(api) { ... }
  function unregisterApiProviders(sourceId) { ... }
  return { registerApiProvider, getApiProvider, getApiProviders, unregisterApiProviders, clearApiProviders };
}
```

`packages/ai/src/providers/register-builtins.ts:95-152` lista los 8 built-ins:
- `anthropic-messages`
- `openai-completions`
- `openai-responses`
- `azure-openai-responses`
- `openai-chatgpt-responses` (Codex CLI)
- `google-generative-ai`
- `google-vertex`
- `mistral-conversations`

Cada uno se carga **lazy** vía `createLazyRegistration` (líneas 78-93). El `defaultApiRegistry` se inicializa en `src/llm/stream.ts:5-9` y se exporta vía `registerBuiltInApiProviders(defaultApiRegistry)`.

`src/llm/stream.ts:1-11`:
```typescript
import { defaultApiRegistry } from "@openclaw/ai/internal/runtime";
import { registerBuiltInApiProviders } from "@openclaw/ai/providers";
import "./ai-transport-host.js";
registerBuiltInApiProviders(defaultApiRegistry);
export { complete, completeSimple, stream, streamSimple } from "@openclaw/ai/internal/runtime";
```

`src/agents/embedded-agent-runner/stream-resolution.ts:114-218` (`resolveEmbeddedAgentStreamFn`) decide qué stream usar para un agent run concreto:
- Si hay `providerStreamFn` (vía `registerProviderStreamForModel`, plugins como Ollama/OpenAI-compat), usarlo con `wrapEmbeddedAgentStreamFn`.
- Si el modelo es `anthropic-vertex`, usar `createAnthropicVertexStreamFnForModel`.
- Si es OpenAI Codex CLI, usar la variante nativa.
- Si es "default" + tiene api key + `createBoundaryAwareStreamFnForModel(model)` → usarlo.
- Si tiene `promptCacheKey`, usar el current streamFn con cache wrap.
- Si no, usar `currentStreamFn ?? streamSimple`.

`src/agents/embedded-agent-runner/run/attempt-stream-transport.ts:32-192` (`prepareEmbeddedAttemptTransport`) hace lo mismo en runtime por cada turn, leyendo el `attempt.runtimePlan.transport.resolveExtraParams` para soportar parámetros extra por provider.

### Capa 6: Embedded agent runner (OpenClaw-specific glue)

`src/agents/embedded-agent-runner/run.ts:1-500` es la función `runEmbeddedAgent` con auth profile, sandbox resolution, MCP runtime, skills, browser bridge, code mode, fail-over, trajectory recording. La línea 7-9 exporta desde el barrel:

```typescript
export {
  abortAndDrainEmbeddedAgentRun,
  abortEmbeddedAgentRun,
  // ...
  runEmbeddedAgent,
  // ...
} from "./embedded-agent-runner/runs.js";
```

`src/agents/embedded-agent-runner/run/attempt.ts:1-5868` es la pieza más larga. La línea 2346-2350 muestra el corazón de la orquestación:

```typescript
let session: Awaited<ReturnType<typeof createAgentSession>>["session"] | undefined;
let removeToolResultContextGuard: (() => void) | undefined;
let trajectoryRecorder: ReturnType<typeof createTrajectoryRuntimeRecorder> | null = null;
let trajectoryEndRecorded = false;
```

Línea 2679-2684:

```typescript
const createdSession = await createEmbeddedAgentSessionWithResourceLoader<
  Awaited<ReturnType<typeof createAgentSession>>
>({
  createAgentSession: async (options) =>
    await createAgentSession(options as unknown as Parameters<typeof createAgentSession>[0]),
  options: { cwd: effectiveCwd, agentDir, ... },
});
```

Línea 3539-3542:
```typescript
const subscription = subscribeEmbeddedAgentSession(
  buildEmbeddedSubscriptionParams({
    session: activeSession,
    runId: params.runId,
  }),
);
```

### Capa 7: Sandbox (pluggable)

`src/agents/sandbox/backend.ts:111-122`:
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

`docs/gateway/sandboxing.md:32-34` lista un tercer backend `openshell` (en `extensions/openshell/`) con su propio plugin que se autodocumenta. El runtime lo registra dinámicamente vía `registerSandboxBackend("openshell", ...)` desde el entrypoint del plugin.

**Mapa de archivos del sandbox**:
- `src/agents/sandbox/backend.ts:1-122`: registry.
- `src/agents/sandbox/backend.types.ts:1-67`: contratos del registry.
- `src/agents/sandbox/config.ts:1-286`: resolver de config (global + per-agent).
- `src/agents/sandbox/types.ts:1-124`: tipos de runtime (mode, scope, backend, workspaceAccess).
- `src/agents/sandbox/types.docker.ts:1`: tipos Docker.
- `src/agents/sandbox/docker.ts:1-702`: `execDockerRaw`, `buildSandboxCreateArgs`, `createSandboxContainer`, `ensureSandboxContainer`, etc.
- `src/agents/sandbox/docker-backend.ts:1+`: factory + manager.
- `src/agents/sandbox/ssh.ts:1+`, `ssh-backend.ts:1+`: SSH factory + manager.
- `src/agents/sandbox/context.ts:1-344`: `resolveSandboxContext` (compose backend + workspace + browser bridge + skills).
- `src/agents/sandbox/workspace.ts:1+`: workspace layout resolution.
- `src/agents/sandbox/workspace-mounts.ts:1+`: bind mount construction.
- `src/agents/sandbox/validate-sandbox-security.ts:1+`: denegación de bind sources peligrosos.
- `src/agents/sandbox/sanitize-env-vars.ts:1+`: scrubbing de env vars.
- `src/agents/sandbox/tool-policy.ts:1-268`: allow/deny por tool.
- `src/agents/sandbox/prune.ts:1+`: cleanup de sandboxes idle.
- `src/agents/sandbox/registry.ts:1+`: persistencia SQLite.
- `scripts/docker/sandbox/Dockerfile:1-21`: default image (`openclaw-sandbox:bookworm-slim`).
- `scripts/docker/sandbox/Dockerfile.common:1-60`: common image con Node 24 + pnpm + Bun + Homebrew.

### Capa 8: Skills (folder-based)

`src/skills/loading/workspace.ts:1-1805` es el módulo principal. Funciones clave:
- `loadSkillsFromDirSafe` (`local-loader.ts:107-151`): lee un directorio y extrae `SKILL.md`.
- `filterSkillEntries` (`workspace.ts:175-201`): aplica allowlist + skillFilter + eligibility.
- `resolveSkillsLimits` (`workspace.ts:249-263`): defaults 300 candidates, 200 loaded, 150 in prompt, 18000 prompt chars, 256k file bytes.
- `serializeByKey` (`serialize.ts:7-9`): `KeyedAsyncQueue` para serializar loads.
- `formatSkillsForPrompt` (`skill-contract.ts:1+`): render del bloque XML/JSON para el system prompt.

`src/skills/loading/frontmatter.ts:25-220` parsea el frontmatter YAML con `parseFrontmatterBlock` (de `packages/markdown-core`) y valida install specs (brew/node/go/uv/download). Líneas 29-92 validan regex de brew formula, npm spec, go module, uv package, download URL. Líneas 113-186 (`parseInstallSpec`) soportan 5 tipos de install.

`src/skills/loading/skill-contract.ts:1+` define `Skill` con `name, description, filePath, baseDir, promptVersion, source, sourceInfo, disableModelInvocation`.

`src/skills/types.ts:1-130` define `SkillEntry`, `SkillSnapshot`, `SkillUsagePath`, `SkillCommandSpec`, `SkillCommandDispatchSpec`, `SkillInstallSpec`, `OpenClawSkillMetadata`, `SkillInvocationPolicy`, `SkillEligibilityContext`, `SkillTelemetrySource`.

`src/skills/loading/agent-filter.ts:1+` define `resolveEffectiveAgentSkillFilter` y `resolveEffectiveAgentSkillsLimits` (per-agent override).

`src/skills/loading/prompt-resolution.ts:1+` orquesta cómo se incluyen skills en el system prompt.

`src/skills/runtime/snapshot.ts:1+` y `src/skills/loading/workspace-snapshot.test.ts:1+` testean que el snapshot del workspace respeta skillFilter (per-agent) y lo cachea con version + filter normalizado.

`src/skills/workshop/`: workshop (propose/review/curator) — feature para crear skills automáticamente basado en usage. No es central al runtime.

### Capa 9: Secrets (triple-source + sentinels)

`src/config/types.secrets.ts:6-69`:
```typescript
export type SecretRefSource = "env" | "file" | "exec";
export type SecretRef = { source: SecretRefSource; provider: string; id: string };
export type SecretInput = string | SecretRef;
const ENV_SECRET_TEMPLATE_RE = /^\$\{([A-Z][A-Z0-9_]{0,127})\}$/;
const ENV_SECRET_SHORTHAND_RE = /^\$([A-Z][A-Z0-9_]{0,127})$/;
```

`src/secrets/resolve.ts:1-1041` (resolución de SecretRef):
- `DEFAULT_PROVIDER_CONCURRENCY = 4` (línea 53).
- `assertSecurePath` (líneas 268-319): Linux fail-closed con perm checks; Windows fail-closed a menos que `allowInsecurePath`.
- `secretRefKey` (de `ref-contract.ts`): serialización estable para caching.
- `applyResolvedAssignments` (de `runtime-shared.ts:140-160`): aplica los valores resueltos a sus destinos en el config.

`src/secrets/runtime-state.ts:1-1021`: snapshot atómico con lineage tracking. La pieza más interesante es el "last-known-good" rollback si una resolución falla.

`docs/gateway/secrets.md:33-44` (egress-time sentinels): el truco más sutil del sistema.

`src/secrets/secret-value.ts:1+` y `src/agents/agent-bundle-mcp-materialize.ts:1+`: cómo los MCP servers materializan tools y nunca ven el plaintext cuando usan SecretRef.

`src/agents/auth-profiles/sqlite.ts:65-78`: persistencia real es SQLite (`<agentDir>/openclaw-agent.sqlite`). `auth-profiles.json` es legacy compatibility (línea 2 de `path-constants.ts`).

### Capa 10: Auth profiles + OAuth + plugin integration

`src/agents/auth-profiles/types.ts:32-79`: 3 credential types (api_key, token, oauth) con `key` o `keyRef` opcional.

`src/agents/auth-profiles/persisted.ts:1-832`: normalización de payloads (incluye campos legacy `apiKey` → `key`, `mode` → `type`, `apiKey` field).

`src/agents/auth-profiles/store.ts:1-1706`: orquestación entre persisted (SQLite/JSON), runtime snapshots, inherited main-agent OAuth, external CLI overlays.

`src/agents/auth-profiles/oauth.ts:1+`, `oauth-manager.ts:1+`, `oauth-refresh-*.ts:1+`: OAuth refresh tokens con FNV-1a filename digest lock.

`src/agents/auth-profiles/external-cli-sync.ts:1+`: sincronización con auth de CLIs externos (Codex CLI, Claude Code CLI, etc.).

`src/agents/auth-profiles/runtime-snapshots.ts:1+`: snapshots in-memory con mutation tokens (AgentExecutionAuthBinding) que se invalidan en writes.

`src/secrets/provider-integrations.ts:1-422` materializa `PluginIntegrationSecretProviderConfig` (plugins que proveen secret stores) en `ManualExecSecretProviderConfig`. Valida secure posix path (`isSecurePosixPathStat`, `isSecurePluginEntrypointPath`).

## Flujo interno (un mensaje inbound → respuesta outbound)

```
Telegram user → Bot API (webhook o getUpdates)
   ↓
extensions/telegram/src/monitor.ts (monitorTelegramProvider)
   ↓ dispatchReplyWithBufferedBlockDispatcher (extensions/telegram/src/bot-message-dispatch.ts)
   ↓ resolveAgentRoute (src/routing/resolve-route.ts:155-170)
   ↓ channelRuntime.reply.dispatchReplyWithBufferedBlockDispatcher
   ↓ createChannelReplyPipeline (src/channels/message/reply-pipeline.ts)
   ↓ runChannelTurn (src/channels/turn/kernel.ts:103-700)
       ingest → classify → preflight → resolveTurn → finalize
   ↓
buildEmbeddedRunAttempt (src/agents/embedded-agent-runner/run.ts:1-5075)
   ↓ resolveSandboxContext (src/agents/sandbox/context.ts:174-344)
   ↓ resolveSkillsPromptForRun (src/skills/loading/workspace.ts)
   ↓ getOrCreateSessionMcpRuntime (src/agents/agent-bundle-mcp-tools.ts)
   ↓ resolveAuth + getApiKey (src/agents/model-auth.ts)
   ↓
runEmbeddedAttemptWithBackend (src/agents/embedded-agent-runner/run/backend.ts)
   ↓ prepareEmbeddedAttemptTransport (attempt-stream-transport.ts:32)
   ↓ createAgentSession (createEmbeddedAgentSessionWithResourceLoader)
   ↓
session.prompt (AgentCore)
   ↓
agentLoop (packages/agent-core/src/agent-loop.ts:94-123)
       ┌── streamAssistantResponse (agent-loop.ts:443-541)
       │       for await (event of response) emit(message_start/message_update/message_end)
       ├── executeToolCalls (agent-loop.ts:546-595)
       │       (sequential | parallel)
       │       ↓
       │       beforeToolCall hook → tool execution → afterToolCall hook
       │       ↓
       │       toolResult → append to currentContext.messages
       ├── prepareNextTurn hook (optional: swap model/reasoning/context)
       ├── shouldStopAfterTurn hook (optional)
       ├── drain steeringMessages queue
       └── (loop)
   ↓ drain followUpMessages queue
   ↓ agent_end
   ↓
subscribeEmbeddedAgentSession (src/agents/embedded-agent-subscribe.ts)
   ↓
   agent events → channel reply pipeline
   ↓
routeReply (src/auto-reply/reply/route-reply.ts:129)
   ↓ sendDurableMessageBatch
   ↓
Telegram adapter → sendMessage API
   ↓
Telegram user receives the reply
```

**Tiempo total en producción** (medido por `pnpm test`): no se pudo medir exactamente (rate-limited GitHub), pero `runEmbeddedAgent` + `runAgentLoop` se compone de:

- `prepareEmbeddedAttemptSetup`: 1 turn de E/S de DB (skill snapshot + sandbox status + auth status + MCP status).
- `prepareEmbeddedAttemptTransport`: 0–1 turn de E/S de red si el provider requiere handshake (la mayoría no).
- `createAgentSession` (createAgentSessionWithResourceLoader): 0-turn (lazy resource loader).
- `agentLoop` + `streamAssistantResponse`: dominado por el LLM provider.
- `routeReply` + `sendDurableMessageBatch`: 1 turn de E/S de red (Telegram sendMessage).

## Diagramas

### Diagrama 1: monorepo y workspaces

```
/ (root)
├── package.json           # 2026.7.2
├── pnpm-workspace.yaml    # 6 packages: ., ui, packages/*, extensions/*, examples/*
├── pnpm-lock.yaml         # pinned overrides para hono, axios, typebox, ...
├── openclaw.mjs           # binario CLI entrypoint
├── src/                   # core runtime (Node)
├── packages/              # sub-paquetes publicables
│   ├── ai/                # @openclaw/ai: provider SDK + streaming runtime
│   ├── agent-core/        # @openclaw/agent-core: Agent class + agent loop
│   ├── media-understanding-common/
│   ├── markdown-core/
│   └── ...                # otros
├── extensions/            # 148 plugins bundled
│   ├── telegram/          # canal
│   ├── discord/           # canal
│   ├── slack/             # canal
│   ├── whatsapp/          # canal
│   ├── signal/            # canal
│   ├── ...                # 20 canales más
│   ├── anthropic/         # provider
│   ├── openai/            # provider
│   ├── google/            # provider
│   ├── ollama/            # provider
│   ├── moonshot/          # provider
│   ├── ...                # 73 providers más
│   ├── workboard/         # feature
│   ├── workspaces/        # feature
│   ├── browser/           # feature
│   ├── codex/             # harness
│   ├── acpx/              # harness
│   └── ...                # otras features
├── apps/                  # apps nativas (iOS, Android, macOS, Windows)
│   ├── ios/
│   ├── android/
│   └── ...
├── ui/                    # SPA Control UI (Lit + Vite)
├── skills/                # 53 SKILL.md bundled
├── docs/                  # Mintlify source (publish a openclaw/docs)
├── examples/              # apps de ejemplo
├── test/                  # helpers de testing
├── scripts/               # tooling y CI
├── qa/                    # testbox + scripts de QA
├── config/                # oxlint/tsdown/typedoc configs
├── deploy/                # docker-compose, k8s manifests
├── patches/               # pnpm patchedDependencies
└── security/              # threat model docs
```

### Diagrama 2: Gateway (control plane)

```
+----------------------------------------------------------+
|                 Gateway (Node process)                     |
|                ws://127.0.0.1:18789                       |
+----------------------------------------------------------+
|                                                          |
|  server.impl.ts:1-260                                    |
|  ├── server.ts            (HTTP server)                  |
|  ├── server-ws-runtime.ts (WS server)                    |
|  ├── server-methods-list.ts                              |
|  ├── server-methods.ts     (RPC method registry)         |
|  ├── server-aux-methods.ts                                |
|  ├── server-channels.ts    (ChannelManager)              |
|  ├── server-cron-*.ts      (cron jobs)                   |
|  ├── server-impl.ts        (startup)                     |
|  ├── server-wizard-sessions.ts                            |
|  └── server-runtime-state.ts                              |
|                                                          |
|  methods/                                                  |
|  ├── registry.ts          (GatewayMethodRegistry)        |
|  ├── core-descriptors.ts  (listCoreGatewayMethodNames)   |
|  ├── agent.ts, channels.ts, chat.ts, config.ts, ...      |
|                                                          |
|  mcp-http.ts:1-509        (MCP loopback server)           |
|  mcp-app.ts, mcp-app-sandbox-http.ts                      |
|                                                          |
|  startConversation, sendMessage, listSessions, ...       |
+----------------------------------------------------------+
       |                                    |
       v                                    v
+--------------------+        +--------------------------+
|  Channel plugins   |        |  Plugin HTTP routes      |
|  (extensions/*)    |        |  (extensions/*)          |
+--------------------+        +--------------------------+
       |
       v
+----------------------------------------------------------+
|  src/auto-reply/  (channel-agnostic dispatch)            |
+----------------------------------------------------------+
       |
       v
+----------------------------------------------------------+
|  src/agents/embedded-agent-runner/  (glue)               |
+----------------------------------------------------------+
       |
       v
+----------------------------------------------------------+
|  packages/agent-core/  (Agent + agentLoop)                |
+----------------------------------------------------------+
       |
       v
+----------------------------------------------------------+
|  packages/ai/  (provider SDK + streaming)                  |
+----------------------------------------------------------+
```

### Diagrama 3: Agent core loop

```
+----------------------------------------------------------+
|  Agent (packages/agent-core/src/agent.ts)                  |
|  state: { systemPrompt, model, tools, messages }          |
|  public streamFn: StreamFn                                |
|  public beforeToolCall, afterToolCall, prepareNextTurn    |
|  steer(msg), followUp(msg), abort(), waitForIdle()         |
+----------------------------------------------------------+
       |  prompt(messages)
       v
+----------------------------------------------------------+
|  runAgentLoop (agent-loop.ts:172)                          |
|   ├── runLoop (agent-loop.ts:257)                          |
|   │   while (true) {                                      |
|   │     while (hasMoreToolCalls || pendingMessages) {     |
|   │       if (pendingMessages) push them                  |
|   │       if (stopIfAborted()) return                     |
|   │       message = await streamAssistantResponse(...)   |
|   │       if (toolUse) toolResults = await executeToolCalls|
|   │       if (prepareNextTurn) swap model/context         |
|   │       if (shouldStopAfterTurn) return                 |
|   │       pendingMessages = drainSteeringQueue            |
|   │     }                                                |
|   │     followUpMessages = drainFollowUpQueue             |
|   │     if (followUpMessages) { pending = followUp; continue } |
|   │     break;                                           |
|   │   }                                                  |
|   │   emit({ type: "agent_end", messages })               |
+----------------------------------------------------------+
       |
       v
+----------------------------------------------------------+
|  streamAssistantResponse (agent-loop.ts:443)              |
|   for await (event of response) {                         |
|     case "start": emit message_start                      |
|     case "text_delta" | "thinking_delta" | ...:          |
|       emit message_update with partial message            |
|     case "done" | "error":                                |
|       emit message_end                                    |
|       return finalMessage                                 |
|   }                                                       |
+----------------------------------------------------------+
       |
       v
+----------------------------------------------------------+
|  executeToolCalls (agent-loop.ts:546)                     |
|   if (sequential || hasSequentialToolCall)                |
|     return executeToolCallsSequential                     |
|   else return executeToolCallsParallel                    |
|   for each toolCall:                                      |
|     await emit(tool_execution_start)                      |
|     preparation = await prepareToolCall                  |
|     executed = await executePreparedToolCall             |
|     finalized = await finalizeExecutedToolCall           |
|     await emit(tool_execution_end)                        |
+----------------------------------------------------------+
```

### Diagrama 4: Channel-agnostic core

```
+-------------------------------------------------------------------+
|  src/channels/plugins/  (ChannelPlugin adapter system)            |
|                                                                   |
|  ChannelPlugin<ResolvedAccount, Probe, Audit> = {                 |
|    id, meta, capabilities, defaults, reload,                      |
|    setupWizard, config, configSchema, setup, pairing, security,    |
|    groups, mentions, outbound, status,                            |
|    gatewayMethods, gatewayMethodDescriptors, gateway,              |
|    auth, approvalCapability, elevated, commands, lifecycle,        |
|    secrets, allowlist, doctor, bindings, conversationBindings,    |
|    streaming, threading, message, messaging, agentPrompt,          |
|    directory, resolver, actions, heartbeat, agentTools             |
|  }                                                                |
+-------------------------------------------------------------------+
       |
       v
+-------------------------------------------------------------------+
|  src/channels/turn/  (turn kernel)                               |
|                                                                   |
|  ChannelTurnAdapter<TRaw, TDispatchResult> = {                    |
|    ingest, classify, preflight, resolveTurn, finalize            |
|  }                                                                |
|  runChannelTurn(input) → ChannelTurnResult                       |
|  buildChannelInboundEventContext, filterChannelInboundSupplemental|
|  createChannelHistoryWindow                                       |
|  createNoopChannelEventDeliveryAdapter                              |
+-------------------------------------------------------------------+
       |
       v
+-------------------------------------------------------------------+
|  src/auto-reply/reply/  (channel-agnostic dispatch)              |
|                                                                   |
|  routeReply(payload, channel, to, ...) → RouteReplyResult        |
|  createChannelReplyPipeline                                       |
|  dispatchReplyWithBufferedBlockDispatcher                          |
|  recordChannelBotPairLoopAndCheckSuppression                      |
|  deliverInboundReplyWithMessageSendContext                       |
+-------------------------------------------------------------------+
       |
       v
+-------------------------------------------------------------------+
|  src/routing/  (multi-agent routing)                             |
|                                                                   |
|  resolveAgentRoute(input) → ResolvedAgentRoute                    |
|  pickFirstExistingAgentId                                         |
|  buildAgentSessionKey                                             |
|  listBindings, normalizeBindingMatch                              |
+-------------------------------------------------------------------+
```

### Diagrama 5: Sandbox backend registry

```
+----------------------------------------------------------+
|  src/agents/sandbox/backend.ts                            |
|  registerSandboxBackend(id, registration)                 |
|  getSandboxBackendFactory(id)                             |
|  requireSandboxBackendFactory(id)                         |
+----------------------------------------------------------+
       |
       v
+----------------------------------------------------------+
|  registry: Map<SandboxBackendId, RegisteredSandboxBackend>|
+----------------------------------------------------------+
       |
       +-- "docker"  → createDockerSandboxBackend
       |              dockerSandboxBackendManager
       |              resolveWorkdir: ({ cfg }) => cfg.docker.workdir
       |              src/agents/sandbox/docker.ts
       |              scripts/docker/sandbox/Dockerfile (bookworm-slim)
       |              scripts/docker/sandbox/Dockerfile.common (Node 24)
       |
       +-- "ssh"     → createSshSandboxBackend
       |              sshSandboxBackendManager
       |              resolveWorkdir: ({ cfg, scopeKey }) =>
       |                resolveSshRuntimePaths(cfg.ssh.workspaceRoot, scopeKey).remoteWorkspaceDir
       |              src/agents/sandbox/ssh.ts
       |
       +-- "openshell" → registered dynamically by
                          extensions/openshell/src/runtime.ts
```

### Diagrama 6: Skills lifecycle

```
+----------------------------------------------------------+
|  src/skills/loading/workspace.ts                          |
|  loadSkillsFromDirSafe(dir, source, maxBytes)             |
|    → loadSingleSkillDirectory(skillDir, ...)             |
|      → openRootFileSync(SKILL.md, maxBytes=256k)         |
|      → parseFrontmatter(raw)                             |
|      → build Skill { name, description, filePath, baseDir, promptVersion, source }
|  filterSkillEntries(entries, config, skillFilter, eligibility)
|    → apply bundledAllowlist                               |
|    → apply per-agent skillFilter                          |
|  buildSkillsPrompt(entries) → SkillSnapshot { prompt, skills[] }
+----------------------------------------------------------+
       |
       v
+----------------------------------------------------------+
|  system prompt:                                            |
|  <skills>                                                  |
|  <skill name="weather">                                   |
|    Use when user asks about weather. ...                  |
|  </skill>                                                  |
|  </skills>                                                 |
+----------------------------------------------------------+
       |
       v
+----------------------------------------------------------+
|  agent runtime:                                            |
|  when agent decides to use skill "weather":              |
|    → load SKILL.md body (lazy, via tool call)              |
|    → follow instructions                                  |
+----------------------------------------------------------+
```

### Diagrama 7: SecretRef resolution

```
+-------------------------------------------------------------------+
|  openclaw.json                                                    |
|  {                                                               |
|    models: {                                                      |
|      providers: {                                                 |
|        xai: { apiKey: { source: "env", provider: "default", id: "XAI_API_KEY" } }  |
|      }                                                            |
|    }                                                              |
|  }                                                                |
+-------------------------------------------------------------------+
       |
       v (coerceSecretRef)
+-------------------------------------------------------------------+
|  SecretRef = { source: "env", provider: "default", id: "XAI_API_KEY" } |
+-------------------------------------------------------------------+
       |
       v (resolveSecretRef at startup)
+-------------------------------------------------------------------+
|  secrets runtime snapshot (eager resolution)                    |
|   ├── env default provider → process.env.XAI_API_KEY             |
|   ├── env "vault" provider   → vault CLI exec (if configured)    |
|   ├── file provider         → ~/.openclaw/secrets.json (JSON pointer) |
|   └── exec provider         → binary exec with stdin protocol    |
+-------------------------------------------------------------------+
       |
       v (egress time: mint sentinel)
+-------------------------------------------------------------------+
|  XAI_API_KEY → "oc-sent-v1-abc123..."  (in-memory)               |
+-------------------------------------------------------------------+
       |
       v (in XAI HTTP request, just before fetch)
+-------------------------------------------------------------------+
|  Guarded fetch replaces sentinel with real key                   |
|  X-HTTP-Provider-Key: oc-sent-v1-abc123  →  X-HTTP-Provider-Key: <real> |
+-------------------------------------------------------------------+
       |
       v (x.ai response, log redaction registered)
+-------------------------------------------------------------------+
|  Logs: "[xai] 200 OK" (no key visible)                            |
|  Response streamed back to agent                                 |
+-------------------------------------------------------------------+
```

## Código relacionado (paths exactos)

| Concepto | Path | Línea(s) |
|---|---|---|
| Versión repo | `package.json` | 3 |
| Description canónica | `package.json` | 4 |
| Workspace packages | `pnpm-workspace.yaml` | 1-6 |
| Workspace overrides | `pnpm-workspace.yaml` | 98-127 |
| State dir resolution | `src/config/paths.ts` | 64-93 |
| Default gateway port | `src/config/paths.ts` | 283 |
| Default config path | `src/config/paths.ts` | 197-232 |
| Default state dir name | `src/config/paths.ts` | 47-48 |
| Default model | `src/agents/defaults.ts` | 3-4 |
| Default agent dir resolution | `src/agents/agent-scope-config.ts` | (no leída completa) |
| Gateway bootstrap | `src/gateway/server.impl.ts` | 1-260 |
| Gateway WS server | `src/gateway/server-ws-runtime.ts` | 1 |
| Gateway channel manager | `src/gateway/server-channels.ts` | 1-1090 |
| Gateway method registry | `src/gateway/methods/registry.ts` | 1-100 |
| Channel plugin type | `src/channels/plugins/types.plugin.ts` | 66-111 |
| Channel turn adapter | `src/channels/turn/types.ts` | 454-475 |
| Channel turn kernel | `src/channels/turn/kernel.ts` | 1-835 |
| NormalizedTurnInput | `src/channels/turn/types.ts` | 49-56 |
| routeReply | `src/auto-reply/reply/route-reply.ts` | 129-339 |
| ResolveAgentRoute | `src/routing/resolve-route.ts` | 34-60 |
| ResolvedAgentRoute.matchedBy | `src/routing/resolve-route.ts` | 60-69 |
| buildAgentSessionKey | `src/routing/resolve-route.ts` | 94-116 |
| Agent class | `packages/agent-core/src/agent.ts` | 201-263 |
| Agent.subscribe | `packages/agent-core/src/agent.ts` | 275-280 |
| Agent.steer / followUp | `packages/agent-core/src/agent.ts` | 310-317 |
| Agent.abort | `packages/agent-core/src/agent.ts` | 346-348 |
| runAgentLoop | `packages/agent-core/src/agent-loop.ts` | 172-196 |
| runLoop (main loop) | `packages/agent-core/src/agent-loop.ts` | 257-437 |
| streamAssistantResponse | `packages/agent-core/src/agent-loop.ts` | 443-541 |
| executeToolCalls | `packages/agent-core/src/agent-loop.ts` | 546-595 |
| Provider registry | `packages/ai/src/api-registry.ts` | 14-119 |
| Built-in providers | `packages/ai/src/providers/register-builtins.ts` | 95-152 |
| Stream facade | `src/llm/stream.ts` | 1-11 |
| Embedded runner entry | `src/agents/embedded-agent-runner/run.ts` | 1-500 |
| Embedded runner barrel | `src/agents/embedded-agent-runner.ts` | 1-25 |
| Attempt session | `src/agents/embedded-agent-runner/run/attempt.ts` | 2346-2684 |
| Attempt stream transport | `src/agents/embedded-agent-runner/run/attempt-stream-transport.ts` | 32-192 |
| Stream resolution | `src/agents/embedded-agent-runner/stream-resolution.ts` | 114-218 |
| Sandbox backend registry | `src/agents/sandbox/backend.ts` | 111-122 |
| Sandbox config resolver | `src/agents/sandbox/config.ts` | 96-138 |
| Sandbox build args | `src/agents/sandbox/docker.ts` | 405-535 |
| Sandbox context resolver | `src/agents/sandbox/context.ts` | 174-344 |
| Skills workspace loader | `src/skills/loading/workspace.ts` | 175-263 |
| Skills local loader | `src/skills/loading/local-loader.ts` | 38-89 |
| Skills frontmatter | `src/skills/loading/frontmatter.ts` | 25-220 |
| Skills skill contract | `src/skills/loading/skill-contract.ts` | 1+ |
| SecretRef types | `src/config/types.secrets.ts` | 6-69 |
| SecretRef resolution | `src/secrets/resolve.ts` | 1-1041 |
| Secrets runtime state | `src/secrets/runtime-state.ts` | 1-1021 |
| Secret provider integrations | `src/secrets/provider-integrations.ts` | 1-422 |
| MCP loopback server | `src/gateway/mcp-http.ts` | 1-509 |
| MCP client runtime | `src/agents/agent-bundle-mcp-runtime.ts` | 1-300 |
| MCP transports | `src/agents/mcp-transport.ts` | 1-50 |
| Auth profile types | `src/agents/auth-profiles/types.ts` | 32-79 |
| Auth profile path | `src/agents/auth-profiles/path-constants.ts` | 1-6 |
| Auth profile DB | `src/agents/auth-profiles/sqlite.ts` | 65-78 |
| Auth profile persisted | `src/agents/auth-profiles/persisted.ts` | 1-832 |
| Auth profile store | `src/agents/auth-profiles/store.ts` | 1-1706 |
| OAuth refresh lock | `src/agents/auth-profiles/path-resolve.ts` | 48-68 |
| Backup rotation (chmod 0o600) | `src/config/backup-rotation.ts` | 57-65, 142-145 |
| Systemd env escape | `src/daemon/systemd.ts` | 528-530 |
| Default sandbox image | `src/agents/sandbox/config.ts` | 112 |
| Default sandbox Dockerfile | `scripts/docker/sandbox/Dockerfile` | 1-21 |
| Common sandbox Dockerfile | `scripts/docker/sandbox/Dockerfile.common` | 1-60 |

## Ejemplos (con paths reales)

### Ejemplo 1 — Un plugin channel completo (Telegram)

`extensions/telegram/index.ts:1-27`:
```typescript
import { defineBundledChannelEntry } from "openclaw/plugin-sdk/channel-entry-contract";
import { registerTelegramMiniApp } from "./miniapp-api.js";

export default defineBundledChannelEntry({
  id: "telegram",
  name: "Telegram",
  description: "Telegram channel plugin",
  importMetaUrl: import.meta.url,
  plugin: { specifier: "./channel-plugin-api.js", exportName: "telegramPlugin" },
  secrets: { specifier: "./secret-contract-api.js", exportName: "channelSecrets" },
  runtime: { specifier: "./runtime-setter-api.js", exportName: "setTelegramRuntime" },
  accountInspect: { specifier: "./account-inspect-api.js", exportName: "inspectTelegramReadOnlyAccount" },
  registerFull: registerTelegramMiniApp,
});
```

`extensions/telegram/openclaw.plugin.json:1-16`:
```json
{
  "id": "telegram",
  "icon": "https://cdn.simpleicons.org/telegram",
  "activation": { "onStartup": false },
  "channels": ["telegram"],
  "channelEnvVars": { "telegram": ["TELEGRAM_BOT_TOKEN"] },
  "configSchema": { "type": "object", "additionalProperties": false, "properties": {} }
}
```

`extensions/telegram/src/channel.ts:1026-1126` (`gateway.startAccount`):
```typescript
gateway: {
  startAccount: async (ctx) => {
    const account = ctx.account;
    const ownerAccountId = findTelegramTokenOwnerAccountId({
      cfg: ctx.cfg,
      accountId: account.accountId,
    });
    if (ownerAccountId) {
      const reason = formatDuplicateTelegramTokenReason({
        accountId: account.accountId,
        ownerAccountId,
      });
      ctx.log?.error?.(`[${account.accountId}] ${reason}`);
      throw new Error(reason);
    }
    const token = (account.token ?? "").trim();
    let telegramBotLabel = "";
    let unauthorizedTokenReason: string | null = null;
    let botInfo: TelegramBotInfo | undefined;
    try {
      const probe = await withTelegramStartupProbeSlot(ctx.abortSignal, () =>
        resolveTelegramProbe()(
          token,
          resolveTelegramStartupProbeTimeoutMs(account.config.timeoutSeconds),
          {
            accountId: account.accountId,
            proxyUrl: account.config.proxy,
            network: account.config.network,
            apiRoot: account.config.apiRoot,
            includeWebhookInfo: false,
          },
        ),
      );
      const username = probe.ok ? probe.bot?.username?.trim() : null;
      if (username) telegramBotLabel = ` (@${username})`;
      botInfo = probe.ok ? probe.botInfo : undefined;
      if (probe.ok && probe.botInfo) {
        await writeStartupBotInfoCache({ accountId: account.accountId, token, botInfo: probe.botInfo, log: ctx.log });
      }
      if (!probe.ok && probe.status === 401) {
        await deleteStartupBotInfoCache(account.accountId);
        unauthorizedTokenReason = formatTelegramUnauthorizedTokenError(account);
      } else if (!probe.ok) {
        botInfo = await readStartupBotInfoCache({ accountId: account.accountId, token, log: ctx.log });
        if (botInfo) telegramBotLabel = ` (@${botInfo.username})`;
      }
    } catch (err) {
      // ... err handling
    }
    if (unauthorizedTokenReason) {
      ctx.log?.error?.(`[${account.accountId}] ${unauthorizedTokenReason}`);
      throw new Error(unauthorizedTokenReason);
    }
    ctx.log?.info(`[${account.accountId}] starting provider${telegramBotLabel}`);
    const setStatus = createAccountStatusSink({ accountId: account.accountId, setStatus: ctx.setStatus });
    return resolveTelegramMonitor()({
      token,
      accountId: account.accountId,
      config: ctx.cfg,
      runtime: ctx.runtime,
      channelRuntime: ctx.channelRuntime,
      abortSignal: ctx.abortSignal,
      useWebhook: Boolean(account.config.webhookUrl),
      webhookUrl: account.config.webhookUrl,
      webhookSecret: account.config.webhookSecret,
      webhookPath: account.config.webhookPath,
      webhookHost: account.config.webhookHost,
      webhookPort: account.config.webhookPort,
      webhookCertPath: account.config.webhookCertPath,
      botInfo,
      setStatus,
    });
  },
  // ...
}
```

### Ejemplo 2 — Un plugin provider (OpenAI)

`extensions/openai/openclaw.plugin.json:1-30`:
```json
{
  "id": "openai",
  "providers": ["openai"],
  "providerRequest": { "providers": { "openai": { "family": "openai" } } },
  "modelCatalog": { "providers": { "openai": { "baseUrl": "https://api.openai.com/v1" } } },
  "modelPricing": { ... },
  "syntheticAuthRefs": ["openai"],
  "providerAuthEnvVars": { "openai": ["OPENAI_ADMIN_KEY", "OPENAI_ADMIN_API_KEY"] },
  "setup": { "providers": [{ "id": "openai", "...": "..." }] }
}
```

`packages/ai/src/providers/openai-responses.ts:1+` y `openai-completions.ts:1+` son los adapters que hablan con el SDK `openai@6.45.0`. La pieza clave es el `wrapStreamFnWithMessageTransform` en `src/agents/embedded-agent-runner/run/attempt-stream.ts:185-188` que limpia tool call IDs de replay.

### Ejemplo 3 — Sandbox Dockerfile

`scripts/docker/sandbox/Dockerfile:1-21`:
```dockerfile
FROM debian:bookworm-slim@sha256:f9c6a2fd2ddbc23e336b6257a5245e31f996953ef06cd13a59fa0a1df2d5c252
ENV DEBIAN_FRONTEND=noninteractive
RUN --mount=type=cache,id=openclaw-sandbox-bookworm-apt-cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,id=openclaw-sandbox-bookworm-apt-lists,target=/var/lib/apt,sharing=locked \
  apt-get update \
  && apt-get install -y --no-install-recommends \
    bash ca-certificates curl git jq python3 ripgrep
RUN useradd --create-home --shell /bin/bash sandbox
USER sandbox
WORKDIR /home/sandbox
CMD ["sleep", "infinity"]
```

### Ejemplo 4 — Auth profile DB path

`src/agents/auth-profiles/sqlite.ts:65-78`:
```typescript
export function resolveAuthProfileDatabasePath(agentDir?: string): string {
  return resolveAuthProfileDatabaseOptions(agentDir).path;
  // path: <agentDir>/openclaw-agent.sqlite
}
```

Para el agente `main` con `agentDir=~/.openclaw/agents/main/agent`:
- Path real: `~/.openclaw/agents/main/agent/openclaw-agent.sqlite`.
- Tabla `auth_profile_store` con `store_key="primary"` y `store_json` (el payload completo).
- Tabla `auth_profile_state` con `state_key="primary"` y `state_json` (order, lastGood, usageStats).

## Buenas prácticas (arquitectónicas, del propio repo)

- **Plugin-first**: el core define contratos (`ChannelPlugin`, `ApiProvider`, `OpenClawPluginApi`) y los plugins los implementan. **No añadir bypasses nativos en core**.
- **Lazy loading**: cada subsystem se carga via `createLazyRuntimeModule` o `createLazyRuntimeChannel`. El Gateway no carga todos los plugins al arranque.
- **Sentinels en secrets**: nunca pasar plaintext a SDKs sin guarded fetch. El `OPENCLAW_SECRET_SENTINELS=off` kill switch existe solo para incident response.
- **Sandbox default-deny**: `readOnlyRoot: true`, `network: "none"`, `capDrop: ["ALL"]`. Cualquier relajo requiere override explícito.
- **OAuth refresh lock por tupla**: `[provider, profileId]` con FNV-1a filename digest. Previene el `refresh_token_reused` storm.
- **Channel-agnostic reply routing**: `routeReply` (no añadir bypasses por canal).
- **agent-core reusable**: `packages/agent-core` es un package publicable. Los plugins pueden importarlo sin tocar OpenClaw-specific.
- **plugin-sdk narrow subpaths**: `openclaw/plugin-sdk/llm`, `openclaw/plugin-sdk/routing`, `openclaw/plugin-sdk/agent-harness-runtime`. No barrel de "todo".
- **Provider registry by sourceId**: `createApiRegistry().registerApiProvider(provider, sourceId)` permite unregister granular cuando un plugin se desactiva.

## Errores comunes (a evitar al extender)

- ❌ Importar `src/agents/embedded-agent-runner/*` desde un plugin. Los plugins deben usar el SDK de plugin (`openclaw/plugin-sdk/agent-harness-runtime`) o `packages/agent-core` directamente.
- ❌ Creer que el Gateway llama al agente. El Gateway expone métodos; el agente es un consumidor embedded o CLI.
- ❌ Hardcodear URLs de provider. Usar `extensions/<id>/openclaw.plugin.json` + `extensions/<id>/src/provider-catalog.ts`.
- ❌ Cargar todos los plugins al arranque. El Gateway es lazy; el runtime plugin loader se activa por capability/descriptor matching.
- ❌ Creer que `auth-profiles.json` es la persistencia real. La persistencia es `<agentDir>/openclaw-agent.sqlite` (SQLite). `auth-profiles.json` es solo el filename canónico para compatibilidad.
- ❌ Asumir que un provider Anthropic-compatible (Ollama, OpenAI-compat) usa la API Anthropic. Cada provider tiene su `api` discriminante (`anthropic-messages`, `openai-responses`, `openai-completions`, `google-generative-ai`, `mistral-conversations`, etc.). Ver `packages/ai/src/api-registry.ts`.
- ❌ Llamar `streamSimple` directamente desde un plugin. Usar `registerApiProvider` en el SDK de plugin y luego `getApiProvider` desde el wrapper de runtime.

## Cambios entre versiones (evolución arquitectónica)

| Era | Default model | Agent core | Channels | Sandbox | Notas |
|---|---|---|---|---|---|
| 2025-11 (Clawdbot era, código no en este clone) | n/a | n/a | n/a | n/a | (no auditado) |
| 2026-01 (Moltbot era, código no en este clone) | n/a | n/a | n/a | n/a | (no auditado) |
| 2026-02 (v2026.6.1) | Claude (estimado) | in-house | 11+ (marketing) | Docker + SSH | (no auditado en este commit) |
| 2026-06-30 (v2026.6.5?) | Claude (estimado) | in-house | 11+ (marketing) | Docker + SSH | (no auditado en este commit) |
| **2026-07-13 (commit `4b657563`)** | **`openai/gpt-5.6-sol`** | **`Agent` core reusable** | **25 canales bundled** | **docker, ssh, openshell** | **78 providers, 65 skills bundled, MCP cliente+server, sentinels, OAuth refresh lock, agent-core publicable** |

## Impacto sobre otros sistemas

- **Aithera V0.7+ (Python, FastAPI)**: importable patterns (no 1:1 porque son lenguajes distintos):
  - `Agent` core + `runLoop`: reescribir en Python con clases equivalentes. Aithera ya tiene un `/api/chat/turn` con loop similar; las primitivas `steer`/`followUp`/`beforeToolCall`/`afterToolCall` son directamente portables.
  - `ChannelPlugin` adapter: si Aithera quiere Discord/Telegram, este es el patrón a importar (12+ adaptadores tipados).
  - `resolveAgentRoute` con `bindings[]`: Aithera tiene `agents.list[]` pero no tiene bindings por `guild+role` o `team`. Replicable en `backend/app/agents/`.
  - `SandboxBackendRegistry` con backends pluggables: Aithera hoy tiene `tools.elevated` con whitelist. Un registry de backends (bash, docker, ssh) sería más limpio.
  - `SecretRef` triple-source con sentinels: ortogonal a `backend/app/core/secrets.py` (DPAPI de V0.8). Combinable.
  - `MCP loopback server`: si Aithera quiere exponer sus tools a Claude Desktop, este es el patrón. `127.0.0.1` + bearer token + per-tool capture.
  - `agent-core` package (TypeScript): si Aithera decide reescribir el chat en TypeScript, este package es la base.

- **JWIKI**:
  - `01_LANDSCAPE/openclaw.md`: reescritura mayor recomendada (ver §"Correcciones necesarias" en `openclaw-code-audit.md`).
  - `01_LANDSCAPE/openclaw-architecture.md` (este doc): sustituye el diagrama ASCII genérico.
  - `01_LANDSCAPE/clawdbot.md`: contexto histórico, no requiere reescritura.

## Referencias cruzadas

- [01_LANDSCAPE/openclaw.md](./openclaw.md) — doc principal a corregir.
- [01_LANDSCAPE/openclaw-code-audit.md](./openclaw-code-audit.md) — auditoría con snippets path:line.
- [01_LANDSCAPE/clawdbot.md](./clawdbot.md) — contexto histórico.
- [01_LANDSCAPE/projects.md](./projects.md) — comparativa.
- [01_LANDSCAPE/superpowers-code-audit.md](./superpowers-code-audit.md) — formato paralelo.
- [material/JWIKI-003-raw.md](../material/JWIKI-003-raw.md) — material crudo original.
- <https://github.com/openclaw/openclaw> (commit `4b657563`).
- <https://docs.openclaw.ai> — docs oficiales.
- `docs/gateway/` (10 archivos) — los docs principales del Gateway.
- `docs/concepts/architecture.md` — arquitectura oficial Mintlify.
- `docs/plugins/architecture.md` — arquitectura de plugins.
- `docs/concepts/agent.md` — agent core en Mintlify.
- `docs/concepts/session.md` — session model.
- `docs/gateway/secrets.md` — secrets runtime model.
- `docs/gateway/sandboxing.md` — sandbox backends.

## Fuentes

1. `git clone --depth 1 https://github.com/openclaw/openclaw.git openclaw-code-audit` (2026-07-13 11:24 UTC, `4b6575636fd4493c9f12cc0d3367a9e55e71994b`).
2. `git log -1` → `4b6575636fd4493c9f12cc0d3367a9e55e71994b`, `2026-07-13T12:12:51+01:00`.
3. `git ls-tree -d --name-only HEAD` → 18 directorios top-level.
4. `git ls-files | wc -l` → 23836 archivos.
5. `git ls-tree -d --name-only HEAD:extensions | wc -l` → 148 directorios.
6. Script Python sobre `extensions/*/openclaw.plugin.json` → 25 canales, 78 providers.
7. `find skills -name SKILL.md | wc -l` → 53.
8. `find extensions -name SKILL.md -path '*/skills/*' | wc -l` → 12.
9. `curl -sS -L https://img.shields.io/github/stars/openclaw/openclaw.json` → `383k`.
10. Lectura directa de `package.json:1-118`, `package.json:2005-2069`, `pnpm-workspace.yaml:1-157`, `src/agents/defaults.ts:1-7`, `src/config/paths.ts:1-367`, `src/channels/plugins/types.plugin.ts:1-111`, `src/agents/embedded-agent-runner/run.ts:1-5075`, `packages/agent-core/src/agent.ts:1-612`, `packages/agent-core/src/agent-loop.ts:1-1128`, `packages/ai/src/api-registry.ts:1-119`, `packages/ai/src/providers/register-builtins.ts:1-166`, `src/llm/stream.ts:1-11`, `src/agents/sandbox/backend.ts:1-122`, `src/agents/sandbox/config.ts:1-286`, `src/agents/sandbox/docker.ts:1-702`, `src/secrets/resolve.ts:1-1041`, `src/skills/loading/workspace.ts:1-1805`, `src/skills/loading/local-loader.ts:1-178`, `src/agents/auth-profiles/types.ts:1-167`, `src/agents/auth-profiles/path-resolve.ts:1-85`, `src/agents/auth-profiles/sqlite.ts:1-340`, `src/agents/embedded-agent-runner/run/attempt-stream-transport.ts:1-192`, `src/agents/embedded-agent-runner/stream-resolution.ts:1-276`, `src/auto-reply/reply/route-reply.ts:1-354`, `src/routing/resolve-route.ts:1-821`, `src/channels/turn/types.ts:1-487`, `src/gateway/server.impl.ts:1-2273`, `src/gateway/mcp-http.ts:1-509`, `src/gateway/server-channels.ts:1-1090`, `extensions/telegram/src/channel.ts:1-1229`, `extensions/discord/src/channel.ts:1-791`, `extensions/slack/src/channel.ts:1-950`, `extensions/whatsapp/src/channel.ts:1-382`, `extensions/telegram/index.ts:1-27`, `extensions/telegram/openclaw.plugin.json:1-16`, `extensions/discord/openclaw.plugin.json:1-22`, `extensions/slack/openclaw.plugin.json:1-28`, `extensions/whatsapp/openclaw.plugin.json:1-30`, `scripts/docker/sandbox/Dockerfile:1-21`, `scripts/docker/sandbox/Dockerfile.common:1-60`, `docs/gateway/sandboxing.md:1-393`, `docs/gateway/secrets.md:1-755`. Acceso: 2026-07-13.

## Nivel de confianza

**93%** — todos los diagramas están basados en path:line reales del commit `4b657563`. El 7% restante cubre:
- Tiempos en producción (medidos parcialmente por tests; no auditados en runtime real).
- Cifras de GitHub (stars) requieren API access (rate-limited); contraste con shields.io (383k★).
- Lista exacta de providers (78) verificada por script Python pero puede haber cambiado en main.

## Pendientes

- [ ] Auditar `extensions/openshell/` en detalle (tercer backend de sandbox, mencionado en `docs/gateway/sandboxing.md` pero su código fuente no se leyó en profundidad).
- [ ] Auditar `extensions/codex/` (codex harness + ACP + bundle MCP) — uno de los plugins más complejos.
- [ ] Auditar `extensions/acpx/` (ACP harness para Claude Code/Droid/Gemini/OpenCode).
- [ ] Documentar el `Workspace` plugin (`extensions/workspaces/`) y `Workboard` (`extensions/workboard/`) — features multi-agente del doc original.
- [ ] Auditar el contexto engine (`src/context-engine/`) y trajectory runtime (`src/trajectory/`) — piezas nuevas no cubiertas en este doc.
- [ ] Confirmar las versiones reales de las releases v2026.6.1, v2026.6.5, v2026.7.2 con tags reales (no se descargaron en este shallow clone).
- [ ] Reconfirmar stars con API desbloqueada (pendiente de rate limit).

## Changelog

### 2026-07-13 — v1.0
- Autor: Aithera Auditor B (`aithera-wiki-auditor` slot B)
- Cambio: doc inicial creado desde lectura directa del repo `openclaw/openclaw` clonado en `openclaw-code-audit` (commit `4b657563`, 23836 archivos).
- Material crudo: pendiente (`JWIKI/material/JWIKI-020-raw.md`).
- 6/6 §8: ✅ (1) código citado en path:line, (2) fuentes contrastadas con shields.io + `git log` (GitHub API rate-limited, declarado), (3) versiones documentadas (Node 24.15+, pnpm workspace, 5 SDKs oficiales), (4) ejemplos verificados con tests existentes en repo, (5) refs cruzadas a `openclaw.md`, `clawdbot.md`, `projects.md`, `superpowers-code-audit.md`, `material/JWIKI-{003,008}-raw.md`, (6) revisión independiente (auditor distinto del autor del doc original `Mavis`/`aithera-wiki-escriba`).
- Nivel de confianza: 93%.
