# Clawdbot (nombre viral Jan-2026 de OpenClaw)

## Resumen

**"Clawdbot" no es un proyecto OSS autónomo, sino el segundo nombre público del codebase que hoy se conoce como OpenClaw.** Surgido como Warelay a finales de noviembre 2025, el proyecto de Peter Steinberger se renombró internamente a CLAWDIS en diciembre, adoptó el nombre **Clawdbot** el 2 de enero de 2026 (momento en que se volvió viral en Hacker News y Reddit), fue forzado a cambiar a Moltbot el 27 de enero por una queja de marca registrada de Anthropic, y alcanzó el nombre final OpenClaw el 30 de enero tras un acuerdo con OpenAI. Este documento cubre la **era Clawdbot** (2-27 enero 2026) — su lanzamiento viral, la crisis del trademark, las controversias de seguridad posteriores — y complementa el documento canónico del proyecto en [01_LANDSCAPE/openclaw.md](./openclaw.md). Para el estado actual del proyecto (junio 2026), código, arquitectura y métricas modernas, consultar siempre ese documento hermano.

## Objetivo

Responder cinco preguntas que el documento canónico de OpenClaw no cubre:

1. ¿Qué fue exactamente Clawdbot y por qué generó tanta atención?
2. ¿Cómo y por qué se produjo la doble rename Clawdbot → Moltbot → OpenClaw en 72 horas?
3. ¿Qué controversias (MoltMatch, Cisco, China, Microsoft/Google) nacieron bajo ese nombre?
4. ¿Hasta qué punto el proyecto es realmente "MCP-based" o más bien "multi-canal-first con MCP como capa"?
5. ¿Qué proyectos OSS del landscape 2026 son **genuinamente** MCP-first puros — un nicho que Clawdbot no ocupa?

## Estado

🟡 En progreso — pendiente de validación por `aithera-wiki-auditor` (turno A) sobre los 6 criterios de la constitución.

## Versiones compatibles

| Proyecto | Versión / fecha | Notas |
|---|---|---|
| OpenClaw (canónico) | ~v2026.6.5 (jun 2026) | 381k stars, TypeScript-first, MIT (declarado en Wikipedia; discrepancia con GitHub API que marca `NOASSERTION`) |
| **Clawdbot (era)** | **2026-01-02 → 2026-01-27** | **Mismo codebase, mismo repo** `openclaw/openclaw`. Este doc cubre este periodo. |
| Moltbot (era) | 2026-01-27 → 2026-01-30 | Rename puente forzado por Anthropic |
| CLAWDIS (era) | ~2025-12-03 → 2026-01-01 | Rename interno pre-público |
| Warelay (origen) | 2025-11-24 → 2025-12-02 | Release inicial privado |
| Aithera | V0.7+ | Referencia cruzada al proyecto OSS local del usuario; Aithera **no implementa** este patrón multi-canal-first sino una arquitectura cliente único + backend único |

## Proyectos compatibles

Este doc se centra en Clawdbot/OpenClaw, pero referencia y compara activamente con los siguientes proyectos OSS activos en junio 2026 (cuya definición de "MCP-based" o "MCP-first" varía significativamente):

- **OpenHuman** (`tinyhumansai/openhuman`) — desktop-first Rust+TS, v0.53.43, 7.8k stars. Cubre `JWIKI-004`.
- **OpenJarvis** (`open-jarvis/OpenJarvis`) — Stanford, local-first Python+Rust. Cubre `JWIKI-005`.
- **JarvisAgent** (`myismu/JarvisAgent`) — Tauri 2.0 + Vue 3 + Rust, desktop con snapshot engine. Cubre `JWIKI-006`.
- **Hermes Agent** (`Hermes-AI/Hermes-Agent`) — Nous Research, self-evolving Python+Node.js. Cubre `JWIKI-007`.
- **moltis-org/moltis** — Rust single-binary secure personal agent server, **genuinamente MCP-first** (2.8k stars, MIT). Descubierto lateralmente en este tick; doc dedicado en JWIKI-267.
- **iOfficeAI/AionUi** — Cowork desktop app que incluye OpenClaw como agente bundled con MCP Unified Management (29k stars, Apache-2.0).
- **EverMind-AI/EverOS** — portable memory layer para AI agents, MCP-tagged (9.8k stars).
- **memovai/memov** — git-like traceable memory para OpenClaw + coding agents via MCP server dedicado (191 stars).
- **cloudflare/moltworker** — package OpenClaw sobre Cloudflare Workers Sandbox (9.9k stars).

## Dependencias

- **[01_LANDSCAPE/openclaw.md](./openclaw.md)** — documento canónico; este doc es su **complemento histórico** y debe leerse a la par.
- **[01_LANDSCAPE/openhuman.md](./openhuman.md)** — contraste desktop-first vs Clawdbot multi-canal-first.
- **[01_LANDSCAPE/hermes-agent.md](./hermes-agent.md)** — contraste con proyecto de Nous Research (auto-entrenado vs skill-marketplace).
- **[01_LANDSCAPE/projects.md](./projects.md)** — tabla comparativa de los 7 proyectos OSS principales del landscape.
- **[01_LANDSCAPE/history.md](./history.md)** — cronología del ecosistema JARVIS-like.
- **[02_ARCHITECTURE/](../02_ARCHITECTURE/)** — patrón multi-cliente vs multi-canal.
- **[06_AGENTS/](../06_AGENTS/)** — patrones de agente y skill loading.
- **[09_INTEGRATIONS/](../09_INTEGRATIONS/)** — channels adapters (WhatsApp, Telegram, Discord).
- **[11_SECURITY/](../11_SECURITY/)** — sandboxing, supply-chain risk, controversies de MoltMatch/Cisco.
- **[JWIKI-267](../17_DISCOVERY/)** — `moltis-org/moltis`, único proyecto genuinamente MCP-first puro del landscape.

## Arquitectura

En la era Clawdbot (enero 2026) la arquitectura del proyecto era sustancialmente la misma que la del OpenClaw actual, sin rupturas mayores — el repo fue renombrado sin refactor. La pieza más distintiva frente a otros asistentes OSS no es la integración con LLMs (delegada totalmente al modelo activo), sino el **message envelope unificado** que aísla los 11+ canales de entrada (WhatsApp, Telegram, Slack, Discord, Signal, iMessage, Matrix, WeChat, Lark, QQBot y otros) de la lógica del agente:

```
                          Era Clawdbot / OpenClaw (ene 2026 → presente)
                          ===========================================

   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
   │  WhatsApp   │  │  Telegram   │  │   Discord   │  │  Slack + 7  │
   │  adapter    │  │  adapter    │  │   adapter   │  │  más ...    │
   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
          │                │               │                │
          └────────────────┴───────┬───────┴────────────────┘
                                   ▼
                       ┌─────────────────────────┐
                       │  OpenClaw Gateway       │
                       │  Message envelope único │  ← pieza diferenciadora
                       │  (channel-agnostic)     │
                       └────────────┬────────────┘
                                    ▼
                       ┌─────────────────────────┐
                       │   Skill Engine +        │  ← docker sandbox /
                       │   Agent Runtime         │     fs.allow-path
                       └────────────┬────────────┘
                                    ▼
                       ┌─────────────────────────┐
                       │  MCP (Model Context     │  ← Anthropic 2024
                       │  Protocol) integrations │     (estandar integración)
                       └────────────┬────────────┘
                                    ▼
                       ┌─────────────────────────┐
                       │  Model provider         │  Claude / GPT-4o /
                       │  (modelo-agnóstico)     │  Gemini / Ollama /
                       └─────────────────────────┘  NVIDIA Nemotron / Kimi
```

Lo que **no** se ve en este diagrama es la pieza que **moltis-org/moltis** lleva hasta sus últimas consecuencias: cuando el **gateway MCP** se convierte en la **única** superficie de E/S — sin los adapters de chat por canal — se obtiene un agente "MCP-first puro". Clawdbot/OpenClaw nunca tomó ese camino; su identidad es multi-canal, no MCP-first.

## Descripción técnica

### Naturaleza del proyecto

El 2 de enero de 2026 el proyecto de Steinberger, hasta entonces un repositorio relativamente oscuro en GitHub, publicó bajo el nombre **Clawdbot** un README centrado en la idea de "tu propio asistente personal AI, en cualquier OS, en cualquier plataforma, a la manera del langosta". El eslogan oficial actual ("Your own personal AI assistant. Any OS. Any Platform. The lobster way.", mantenido desde entonces en el campo `description` del repo) es la herencia directa de esta fase. El anglicismo "the lobster way" — irónico, deliberado, casi troll — encajaba con la personalidad técnica de Steinberger (austriaco, ex-PSPDFKit) y contribuyó al boca a boca.

### Relación con el repo canónico

El repositorio donde se desarrolla el código no fue renombrado en bloque cinco veces; el org y repo son hoy **`openclaw/openclaw`** y ese ha sido el path estable desde finales de enero de 2026. Previamente, antes de la viralización de Clawdbot, el proyecto pasó por distintas ubicaciones privadas (Warelay), pero los commits iniciales que aún podrían consultarse en la rama principal se remontan a **`created_at: 2025-11-24T10:16:47Z`** — la fecha es uno de los pocos anclajes numéricos verificables del lineage.

### Stack real (idem durante la era Clawdbot)

- **Lenguaje principal**: TypeScript (Node.js >= 18). Wikipedia añade Swift como lenguaje secundario, coherente con la compatibilidad iMessage/macOS nativa.
- **Canales soportados**: WhatsApp, Telegram, Slack, Discord, Signal, iMessage, Matrix, WeChat, Lark, QQBot (+ adaptadores comunitarios). Todos convergen en un `Message` envelope común.
- **Proveedores de modelo**: Ollama (HTTP `:11434`), OpenRouter, OpenAI (v1 API con doble autenticación), NVIDIA Nemotron/NeMo (TRT-LLM + cuantización FP8), Moonshot Kimi (2M de contexto).
- **Sistema de skills**: cada skill es una carpeta con un archivo `SKILL.md` (Markdown con frontmatter YAML). El índice de skills se carga en el system prompt; el cuerpo se carga lazy con una tool `Read`. Esto es lo que hoy se conoce como el "Skill engine" de OpenClaw.
- **Sandbox**: cada skill corre en un contenedor Docker con `fs.allow-path` whitelist. Este aislamiento mínimo ya existía en la era Clawdbot y era — y sigue siendo — la principal línea de defensa contra el caos post-instalación.
- **MCP como capa, no como centro**: el proyecto adopta el protocolo MCP de Anthropic (estandarizado en 2024) como **integración externa preferente** desde el primer release público (Warelay, noviembre 2025). Importante: MCP aquí significa que si quieres exponer una tool al agente, lo haces mediante un MCP server. Pero el resto del proyecto (los adapters de chat, el skill loader, el sandbox, el workboard multi-agente) **no depende** de MCP. Es una decisión de diseño pragmática y útil, pero conceptualmente distinta del "MCP-first" puro.

### El bot se llama Molty

Una pieza menor pero recurrente en la documentación y blog posts del proyecto: el bot conversacional internamente se llama **Molty** (evolución de "Clawd"). El nombre, como el logo (un langosta espacial), forma parte de la identidad de marca del proyecto en todas sus encarnaciones — sobrevivió al rename Clawdbot → Moltbot → OpenClaw y se mantiene a junio 2026.

## Flujo interno

El flujo típico de un mensaje en la era Clawdbot (y válido hoy sin cambios relevantes):

1. **Entrada por canal**: un mensaje llega por el adapter de WhatsApp / Telegram / Discord / … y se mapea al `Message` envelope común.
2. **Gateway + identity**: el Gateway verifica el `chat_id` contra la allowlist interna, opcionalmente enriquece con contexto del usuario (preferencias, permisos), y construye la sesión.
3. **Skill loading**: el Skill Engine inspecciona las skills disponibles, calcula el índice por prioridad + dependencias, y lo inyecta en el system prompt del próximo turno.
4. **Agent Runtime → LLM**: el runtime arma el contexto (system prompt + skills index + mensaje + historial corto) y lo envía al modelo activo vía `httpx`-equivalente en TS.
5. **Tool / MCP call**: si el modelo pide una tool, el runtime valida contra la whitelist, resuelve contra el MCP server correspondiente y ejecuta en el sandbox Docker con `fs.allow-path` limitado.
6. **Streaming de vuelta**: los chunks de respuesta vuelven al runtime, se concatenan, y se emiten al canal de origen con un único `client.send` (adaptado al SDK del canal).
7. **Persistencia opcional**: en modo "24-hour butler", el mensaje y la respuesta pueden persistirse en una collection de ChromaDB (memoria semántica), en `Moltbook` (red social de agentes) o simplemente en un log de texto.

El usuario percibe este flujo como una experiencia de mensajería continua: el mismo bot, la misma "personalidad" (Molty), pero cambias de WhatsApp a Telegram sin perder contexto.

## Call Stack / API

En la era Clawdbot, el proyecto no exponía todavía una API HTTP REST pública comparable a la de Aithera V0.7; el Gateway hablaba directamente con los SDKs de cada canal. Hoy el símil más útil para entender el call stack es mapear el flujo al modelo Aithera:

```
Mensaje entrante (era Clawdbot)
  → Channel adapter (whatsapp/telegram/discord/...)
    → OpenClaw Gateway / Message envelope
      → Skill engine (index priority + dependency)
        → Agent runtime (armar system prompt + tools)
          → Model provider.generate_stream()  ← idem a Aithera AIManager
            → chunks via SDK del canal
              → (opcional) MCP server exec → tool result → loop
                → respuesta textual al canal
```

Comparativa con Aithera V0.7 (mismo patrón conceptual, distinto transport):

```
Aithera V0.7:
ChatRequest → POST /api/chat/stream (FastAPI endpoint)
  → AIManager.chat_stream()
    → Provider.generate_stream()  ← equivalente al Agent runtime
      → chunks via SSE
        → useRef en cliente  ← patrón específico de React 18
          → onChunk → message UI
```

Ambas pilas aplican la separación **transporte → modelo → tool**; la diferencia operativa es que Aithera sirve ese transporte por HTTP+SSE y OpenClaw lo hace por adapter nativo de cada messenger.

## Diagramas

### Lineage de renames (5 nombres en 9 semanas)

```
Warelay   ───▶  CLAWDIS   ───▶  Clawdbot   ───▶  Moltbot   ───▶  OpenClaw
24-nov         03-dic          02-ene          27-ene          30-ene
2025           2025            2026            2026            2026

release        rename          rename          rename          rename
inicial        interno         público         forzado         voluntario
                                                      (Anthropic)   (OpenAI)

mismo codebase (github.com/openclaw/openclaw) ──────────────────┘
```

Misma tabla en formato tabla (para grep rápido):

| Orden | Nombre | Fechas | Tipo de cambio | Motivo |
|---|---|---|---|---|
| 1 | **Warelay** | 2025-11-24 → 2025-12-02 | release inicial | primera publicación |
| 2 | **CLAWDIS** | ~2025-12-03 → 2026-01-01 | rename interno | pre-public naming |
| 3 | **Clawdbot** | 2026-01-02 → 2026-01-26 | nombre público | lanzamiento Hacker News |
| 4 | **Moltbot** | 2026-01-27 → 2026-01-29 | rename forzado | trademark Anthropic ("Claude") |
| 5 | **OpenClaw** | 2026-01-30 → presente | rename voluntario | licencia pre-acordada con OpenAI |

### Tabla de 4 MCP-native projects (no confundir con "MCP-based multi-canal")

| Proyecto | Stars | ¿Qué hace? | ¿Verdadero MCP-first? | Estado |
|---|---|---|---|---|
| **moltis-org/moltis** | 2.760 | Rust single-binary secure personal agent server | **Sí** — tiene `moltis-mcp` como crate core y `moltis-mcp-agent-bridge` | activo |
| **EverMind-AI/EverOS** | 9.858 | portable memory layer Markdown-native para AI agents | **Parcial** — MCP-tagged, requiere `evermemos-mcp` companion | activo |
| **memovai/memov** | 191 | git-like traceable memory para OpenClaw + coding agents | **Sí a nivel tool** — ships un `mem_mcp_server` package como verdadero MCP server | estancado (5 meses) |
| **iOfficeAI/AionUi** | 29.102 | Cowork desktop app con OpenClaw bundled, MCP Unified Management | **Sí** — ofrece gestión centralizada de MCP servers para múltiples agentes | activo, muy grande |

**No incluido en esta tabla**: `openclaw/openclaw` (Clawdbot) — porque su diseño es **multi-canal-first** con MCP como integración, no MCP-first puro. La línea divisoria práctica: si quitas todos los adapters de chat de un proyecto, ¿queda algo? En Clawdbot queda una app de skills huérfana; en moltis queda exactamente el mismo agente conversacional (porque su única E/S es MCP).

## Código relacionado

No se cita código de Clawdbot por SHA porque la era fue corta y los commits de enero 2026 sobreviven hoy (junio 2026) sin etiquetas específicas por nombre. Caminos útiles:

- Repo canónico moderno:
  - `https://github.com/openclaw/openclaw` — `description`, `created_at`, `topics`, `stargazers_count`, `forks_count`, `size`, `language`, `license`
- READMEs de terceros que confirman el rename lineage:
  - `https://github.com/cloudflare/moltworker/blob/main/README.md` — primera línea: "Run OpenClaw (formerly Moltbot, formerly Clawdbot) …"
  - `https://github.com/SamurAIGPT/awesome-openclaw/blob/main/README.md` — "OpenClaw (formerly Moltbot / Clawdbot) …"
- Wikipedia EN infobox (fuente del lineage completo):
  - `https://en.wikipedia.org/wiki/OpenClaw` — campo "Other names"
- Noticias del periodo (cronología):
  - TechCrunch 2026-01-27 "Everything you need to know about viral personal AI assistant Clawdbot (now Moltbot)"
  - Forbes 2026-01-27 "Viral AI sidekick Clawdbot changes name to Moltbot"
  - Forbes 2026-01-30 "Moltbot molts again and becomes OpenClaw"
  - CNBC 2026-02-02 "From Clawdbot to Moltbot to OpenClaw: Meet the AI agent generating buzz and fear globally"
  - TechCrunch 2026-02-15 "OpenClaw creator Peter Steinberger joins OpenAI"
- Repo homónimo (no relacionado, pequeño y archivado):
  - `https://github.com/Clawdbot/Clawdbot` — Python `discord.py` bot pre-viral, archivado. ⚠️ Fuente de confusión para nuevos investigadores.

## Ejemplos

### Ejemplo 1 — Mensaje típico usuario final (era Clawdbot, ene 2026)

```
[Usuario en WhatsApp → @Clawdbot_Bot]
"@clawd recordá que mañana tengo dentista a las 10"

[Clawdbot Gateway → Agent runtime → LLM]
→ tool call: add_to_calendar(date="2026-01-09", time="10:00",
                              title="Dentista", reminder_offset="2h")
  ↳ MCP server "calendar" ejecuta contra Google Calendar API
  ↳ respuesta: "Listo, agendado 'Dentista' 9-ene-26 10:00 con recordatorio 2h antes"

[Cliente recibe la confirmación textual por WhatsApp]
```

### Ejemplo 2 — Skill loading (equivalente conceptual al Aithera V0.7)

```typescript
// Equivalente OpenClaw (era Clawdbot / presente): SKILL.md
// File: skills/gmail-summary/SKILL.md
---
name: gmail-summary
priority: 80
dependencies: [gmail-mcp]
description: Resumen diario de emails no leídos en 3 viñetas
---

# gmail-summary

Carga perezosamente (`Read` tool cuando se invoca).
Body markdown: … instrucciones en lenguaje natural para el LLM …
```

Comparativa con Aithera V0.7:

```python
# backend/app/tools/gmail_tool.py  — Aithera 44KB
from app.tools.base import BaseTool

class GmailTool(BaseTool):
    name = "gmail"
    description = "Lee y resume la inbox de Gmail vía OAuth Google"
    allowed_scopes = ["gmail.readonly", "gmail.send"]

    def execute(self, params: dict, agent: Agent) -> dict:
        # valida scopes, llama Gmail API vía google_auth, devuelve resumen
        ...
```

Ambos enfoques (skill-markdown-driven vs class-driven) logran el mismo objetivo: exponer funcionalidad al agente con un contrato mínimo y validación. La diferencia operativa: OpenClaw permite a un usuario medio crear skills (cualquiera con un Markdown puede publicar); Aithera V0.7 requiere programación Python explícita.

### Ejemplo 3 — La crisis del trademark en acción (timeline real)

```
2026-01-26 (lunes)
  └─ Steinberger publica tweet/commits orgullo Clawdbot
  └─ Anthropic envía email privado: trademark notice ("Clawd" ≈ "Claude")
  └─ Alpaca Markets风格的律师-internal revisando

2026-01-27 (martes 09:00 UTC)
  └─ Steinberger anuncia rename "Clawdbot → Moltbot"
  └─ Commit al repo, Twitter/X bio actualizada
  └─ Migración de handle @clawdbot → abandono (cuenta tomada por squatters)

2026-01-27 (martes, horas después)
  └─ Squatters lanzan token cripto "$CLAWD" en pump.fun
  └─ Capitalización pico: USD 12-16M (estimaciones de Forbes)
  └─ Colapsa en < 24h → estafa confirmada

2026-01-28 (miércoles)
  └─ Forbes y TechCrunch publican la saga

2026-01-29 (jueves)
  └─ Steinberger ejecuta segunda rename "Moltbot → OpenClaw"
  └─ (LumaDock reporta 29; Forbes/CNBC/Wikipedia reportan 30 — discrepancia 24h)

2026-01-30 (viernes)
  └─ Confirmación pública con acuerdo pre-firmado con OpenAI
  └─ Handles sociales y dominios preasegurados (openclaw.ai, clawd.bot)
```

## Buenas prácticas

Aprendidas del caso Clawdbot/OpenClaw (tod，她们 aplicables a cualquier proyecto OSS con riesgo de trademark):

- ✅ **Pre-clear de trademarks antes de un renombre público.** Steinberger pagó este consejo con dos renames en 72 horas. OpenClaw (el nombre final) fue validado por un equipo legal externo.
- ✅ **Reservar handles sociales y dominios desde el día uno** (openclaw.ai, clawd.bot como alias, @openclaw en X). El squatter del handle @clawdbot en X convirtió un rename forzado en una estafa material.
- ✅ **Mantener un backup del handle aunque sea read-only** (ej. redireccionar `@clawdbot` a `@openclaw` durante la transición).
- ✅ **Skill system con sandbox + fs.allow-path** desde la v1. La defensa principal contra el caos post-instalación de skills third-party es estructural, no procedimental.
- ✅ **Cite el nombre anterior claramente en el README actual.** `cloudflare/moltworker` y `SamurAIGPT/awesome-openclaw` lo hacen perfecto: "OpenClaw (formerly Moltbot, formerly Clawdbot)". Esto evita que nuevos usuarios crean que están ante un proyecto distinto.
- ✅ **Adoptar MCP como capa de integración ANTES que como identidad de marca.** Es una decisión sana. La diferenciación práctica (los 11+ canales) sigue siendo la propuesta de valor del proyecto.

## Errores comunes

Errores documentados durante la era Clawdbot o atribuibles a decisiones tomadas en ella:

- ❌ **Nombrar el bot con fonética similar a un producto incumbent** ("Clawd" vs "Claude"). Atrae trademark complaints inevitables y alquila el proyecto a esa marca.
- ❌ **Abandonar handles sociales tras un rename forzado.** El hueco lo llenan squatters en horas; en Clawdbot el resultado fue un token cripto scam con pérdidas materiales para terceros.
- ❌ **Comercializar el bot sin gates de aprobación explícita para acciones irreversibles** (el incidente MoltMatch de febrero 2026 fue un agente que creó un perfil de dating sin autorización).
- ❌ **Confiar en "popular + MIT = seguro"** (las 23 plugins squat con prefijo `@openclaw/` en junio 2026 son exactamente este anti-patrón).
- ❌ **Asumir que el gateway MCP es la única superficie de ataque.** El incidente MoltMatch surgió por una integración HTTP estándar al servicio MoltMatch, no por un MCP server. La superficie real de E/S sigue siendo más amplia que el gateway.
- ❌ **Publicar un proyecto multi-canal sin alertar que NO es un agente MCP-puro.** La confusión "MCP-based" (marketing) vs "MCP-first" (arquitectónico) genera expectativas erróneas. moltis-org/moltis sí es MCP-first; Clawdbot nunca lo fue.

## Breaking Changes

Cada rename entre los cinco nombres fue, por definición, un breaking change de marca. A nivel técnico (no romper código de usuarios) los cambios son menores:

| Versión | Cambio | Impacto |
|---|---|---|
| Warelay → CLAWDIS (2025-12) | Interno | Sin impacto público |
| CLAWDIS → Clawdbot (2026-01-02) | Primer release público bajo nuevo nombre | Usuarios que ya tenían el repo deben sincronizar manualmente (clones privados) |
| Clawdbot → Moltbot (2026-01-27) | Forzado por trademark Anthropic | Nombre del repo GitHub cambia, URL `github.com/clawdbot/...` deja de existir, npm packages `@clawdbot/*` requieren migración |
| Moltbot → OpenClaw (2026-01-30) | Voluntario, preacuerdo OpenAI | Mismo código, nuevo nombre. Documentación y posts citan ambos nombres durante meses |
| (transversal) OpenClaw v2026.6.x | Skill scanner estático + hash lock + Workboard multi-agente | Las skills deben ser regeneradas o validadas bajo el nuevo scanner (v2026.6.1+) |

## Cambios entre versiones

| Nombre | Fecha in/out | Estrellas estimadas | Métrica clave del periodo |
|---|---|---|---|
| Warelay | 24-nov 2025 → 02-dic 2025 | n.d. | release inicial |
| CLAWDIS | 03-dic 2025 → 01-ene 2026 | n.d. | rename interno pre-public |
| **Clawdbot** | **02-ene → 26-ene 2026** | **~15k stars en 2 semanas** (r/ArtificialInteligence) | **viral launch HN/Reddit** |
| Moltbot | 27-ene → 29-ene 2026 | crecimiento rápido post-trademark | rename puente |
| OpenClaw | 30-ene 2026 → presente | ~145k (feb) → ~248k (60 días) → **381k (jun 2026)** | consolidación post-crisis |

> El proyecto canónico a junio 2026 es `openclaw/openclaw` con 381.150 stars, 79.834 forks, 6.730 open issues, 1.6 GB de tamaño, TypeScript como lenguaje principal. El campo `topics` oficial incluye `ai, assistant, crustacean, molty, openclaw, own-your-data, personal` y **no incluye** los nombres anteriores ("clawdbot" ni "moltbot" ya no son topics).

## Impacto sobre otros sistemas

El ecosistema creado en torno a Clawdbot/OpenClaw tiene efectos laterales concretos sobre los siguientes dominios de la JWIKI:

- **[02_ARCHITECTURE/multi-client.md](../02_ARCHITECTURE/multi-client.md)** — caso real de arquitectura multi-canal (vs multi-cliente que Aithera V0.7 prefiere).
- **[06_AGENTS/skill-loading.md](../06_AGENTS/skill-loading.md)** — patrón Skill = `SKILL.md` + priority/dependency index + lazy body load. Adoptado por otros proyectos (Hub del Aithera V0.7 no lo hace; Aithera usa class-driven tools).
- **[06_AGENTS/mcp.md](../06_AGENTS/mcp.md)** — Clawdbot/OpenClaw adopta MCP como capa, no como centro; discusión relevante para el debate "MCP-first vs MCP-as-integration".
- **[09_INTEGRATIONS/](../09_INTEGRATIONS/)** — los 11+ canales son hoy la integración más ambiciosa del landscape OSS; Aithera V0.7 cubre solo Gmail + Calendar.
- **[11_SECURITY/supply-chain.md](../11_SECURITY/supply-chain.md)** — caso de estudio: ClawHavoc (1,184 skills maliciosas), MoltMatch incident, scope squatting del prefijo `@openclaw/`.
- **[12_TOOLING/execution-engine.md](../12_TOOLING/execution-engine.md)** — el "Agent Runtime" de OpenClaw es la referencia externa más cercana al Aithera ToolManager.
- **[JWIKI-267 (moltis)](../17_DISCOVERY/)** — el "verdadero MCP-first puro" como contraste necesario para no confundir lectores.

## Referencias cruzadas

- [01_LANDSCAPE/openclaw.md](./openclaw.md) — **DOCUMENTO HERMANO CANÓNICO**, consultar para estado actual del proyecto
- [01_LANDSCAPE/openhuman.md](./openhuman.md) — contraste desktop-first
- [01_LANDSCAPE/openjarvis.md](./openjarvis.md) — contraste Stanford local-first
- [01_LANDSCAPE/jarvisagent.md](./jarvisagent.md) — contraste Tauri+Vue 3 desktop con snapshot engine
- [01_LANDSCAPE/hermes-agent.md](./hermes-agent.md) — contraste Nous Research self-evolving
- [01_LANDSCAPE/projects.md](./projects.md) — comparativa 7 proyectos OSS principales
- [01_LANDSCAPE/history.md](./history.md) — cronología del ecosistema JARVIS-like

## Fuentes

1. `https://en.wikipedia.org/wiki/OpenClaw` — infobox "Other names" y cuerpo — acceso 2026-06-30
2. `https://github.com/openclaw/openclaw` — repo canónico, descripción, topics, estadísticas — acceso 2026-06-30
3. `https://api.github.com/repos/openclaw/openclaw` — JSON oficial, campos `created_at`, `pushed_at`, `stargazers_count`, `forks_count`, `open_issues_count`, `size`, `language`, `license.spdx_id` — acceso 2026-06-30
4. `https://www.forbes.com/sites/ronschmelzer/2026/01/27/viral-ai-sidekick-clawdbot-changes-name-to-moltbot-and-sheds-its-old-skin/` — Ron Schmelzer — 27-ene-2026
5. `https://www.forbes.com/sites/ronschmelzer/2026/01/30/moltbot-molts-again-and-becomes-openclaw-pushback-and-concerns-grow/` — Ron Schmelzer — 30-ene-2026
6. `https://www.cnbc.com/2026/02/02/openclaw-open-source-ai-agent-rise-controversy-clawdbot-moltbot-moltbook.html` — 02-feb-2026
7. `https://techcrunch.com/2026/01/27/everything-you-need-to-know-about-viral-personal-ai-assistant-clawdbot-now-moltbot/` — Anna Heim — 27-ene-2026 (vía Wikipedia citation)
8. `https://techcrunch.com/2026/02/15/openclaw-creator-peter-steinberger-joins-openai/` — 15-feb-2026 (vía Wikipedia citation)
9. `https://hyperight.com/openclaw-ai-assistant-rebrand-security-guide/` — 02-feb-2026
10. `https://lumadock.com/blog/clawdbot-moltbot-openclaw-rebrand` — 30-ene-2026
11. `https://github.com/cloudflare/moltworker/blob/main/README.md` — confirmación textual del rename lineage
12. `https://github.com/SamurAIGPT/awesome-openclaw` — confirmación textual del rename lineage
13. `https://news.ycombinator.com/item?id=46760237` — Hacker News thread original "Clawdbot" — 22-ene-2026 (~405 points, 261 comments)
14. `https://www.reddit.com/r/ArtificialInteligence/comments/1qn3krp/clawdbot_an_opensource_personal_ai_assistant/` — Reddit crecimiento viral
15. `https://www.reddit.com/r/ClaudeAI/comments/1qn9c0b/whats_the_hype_around_clawdbot_these_days/` — Reddit hype
16. `https://www.lennysnewsletter.com/p/today-on-how-i-ai-i-gave-clawdbot` — Lenny's Newsletter "I gave Clawdbot full access to my computer"
17. `https://www.ibm.com/think/news/clawdbot-ai-agent-testing-limits-vertical-integration` — IBM Think — 29-ene-2026
18. `https://1password.com/blog/its-moltbot` — 1Password blog ene-2026 "It's incredible. It's terrifying. It's Moltbot" (usa "Clawdbot" en cuerpo)
19. `https://www.platformer.news/moltbot-clawdbot-review-ai-agent/` — Casey Newton / Platformer — ene-2026
20. `https://blogs.cisco.com/ai/personal-ai-agents-like-openclaw-are-a-security-nightmare` — Cisco Blogs security research — 28-ene-2026
21. `https://www.axios.com/2026/01/29/moltbot-cybersecurity-ai-agent-risks` — Axios — 29-ene-2026
22. `https://api.github.com/repos/moltis-org/moltis` — JSON oficial, genuino MCP-first project — acceso 2026-06-30
23. `https://api.github.com/repos/iOfficeAI/AionUi` — JSON oficial, MCP Unified Management — acceso 2026-06-30
24. `https://api.github.com/repos/EverMind-AI/EverOS` — JSON oficial, portable memory layer — acceso 2026-06-30
25. `https://api.github.com/repos/memovai/memov` — JSON oficial, git-like traceable memory — acceso 2026-06-30
26. `https://steipete.me/about` — bio del autor (Archivado en Wayback Machine 18-feb-2026, vía Wikipedia citation)
27. [01_LANDSCAPE/openclaw.md](./openclaw.md) — Aithera Escriba B / Mavis — 2026-06-30 — documento canónico hermano (autoridad técnica y de arquitectura)
28. [JWIKI-003-raw](../material/JWIKI-003-raw.md) — 63 hechos verificados sobre OpenClaw canónico — 2026-06-30

## Nivel de confianza

**78%** — El lineage de renames (5 nombres, 5 fechas) está confirmado por **6 fuentes independientes** (Wikipedia EN, Forbes, CNBC, TechCrunch, Hyperight, LumaDock + repos GitHub de terceros). La métrica canónica (381k stars, TypeScript, MIT según Wikipedia) está contrastada con la GitHub API oficial, aunque hay discrepancia menor: GitHub API devuelve `license.spdx_id = NOASSERTION` mientras Wikipedia infobox declara MIT (auditor debe leer el archivo `LICENSE` directamente para zanjar). Las controversias (MoltMatch, Cisco, China, Microsoft/Google) están reportadas por al menos 2 fuentes cada una. La distinción "MCP-based" (multi-canal-first con MCP) vs "MCP-first" (agente puro MCP-native) se basa en lectura del código del README canónico + el repositorio genuino `moltis-org/moltis`. La principal incertidumbre (22%) recae en:

- Stars exactos durante la era Clawdbot (2-26 ene): solo tenemos fuentes secundarias (Reddit ~15k en 2 semanas, HN ~405 points). Wayback Machine de la página del repo podría confirmar.
- Composición del "ClawCon" (4-feb-2026 en San Francisco): no investigada en profundidad.
- Conflicto `license.spdx_id` (NOASSERTION vs MIT).
- Si el MCP server de moltis realmente escala a producción sin adaptadores de chat adicionales.

## Pendientes

Tareas que el siguiente nivel (Aithera Auditor A) debe validar o que quedan abiertas explícitamente para iteraciones futuras:

- [ ] **Verificar licencia SPDX directamente en `LICENSE` file del repo** (resolver discrepancia entre GitHub API `NOASSERTION` y Wikipedia `MIT`).
- [ ] **Wayback Machine de `github.com/clawdbot/clawdbot` y `github.com/moltbot/moltbot`** para capturar stars exactos durante la era Clawdbot (2-26 ene) y la cuenta de forks pre-rename.
- [ ] **Conferir release tags de OpenClaw** entre nov-2025 (Warelay v1) y ene-2026 (era Clawdbot) para confirmar que no hubo rupturas arquitectónicas durante los renames.
- [ ] **Detalle del ClawCon** (4-feb-2026, San Francisco) — agenda, participantes, talks. Steinberger + Tomas Taylor confirmados pero faltan duración y talks.
- [ ] **Post original "Introducing OpenClaw"** en `https://openclaw.ai/blog/introducing-openclaw` referenciado por Forbes 30-ene pero no leído.
- [ ] **Confirmar estado archivado** del repo homónimo `Clawdbot/Clawdbot` (Python discord.py bot pre-viral) que php.cn describe como archivado.
- [ ] **Iniciar JWIKI-267 (moltis)** en próximo slot disponible — el proyecto genuinamente MCP-first puro es el caso de estudio perfecto para el debate de diseño que este doc abre.
- [ ] **Re-validar después de cambios del repo canónico** (cada release mayor OpenClaw 2026.x): verificar si MCP cambia de "capa" a "centro" en algún punto. A junio 2026 sigue siendo capa.

---

## Ecosistema post-Clawdbot (legado vivo en junio 2026)

Aunque Clawdbot dejó de existir como nombre el 27 de enero de 2026, el ecosistema que creció a su alrededor sigue activo y vale la pena documentar someramente para entender el impacto del proyecto:

- **Moltbook** — red social de AI agents lanzada cerca del rename Clawdbot → Moltbot. Los agentes con OpenClaw obtienen automáticamente un perfil "Molt" y pueden publicar / reaccionar. La controversia MoltMatch (feb 2026) nació de la intersección entre Moltbook y un servicio de dating para agentes.
- **ClawHub** (`clawhub.ai`) — marketplace de skills OpenClaw. A junio 2026 mantiene ~1.508 skills activos (decremento tras incidentes ClawHavoc) sobre un histórico >31.000.
- **`@openclaw/*` plugins oficiales** — prefijado para distinguir los plugin oficiales del proyecto de los comunitarios. La proliferación de plugins squat (23 a junio 2026 según ithome.com) que se hacen pasar por oficiales es uno de los riesgos actuales.
- **Comunidades derivadas** — subreddits `r/clawdbot` (creado en la era viral, hoy semiactivo), `r/Moltbot`, `r/openclaw`, y el canal Discord oficial del proyecto.
- **Forks destacados** — `cloudflare/moltworker` (OpenClaw sobre Cloudflare Workers Sandbox, 9.9k stars) es el fork infraestructura más popular; `iOfficeAI/AionUi` (29k stars) integra OpenClaw como un agente más dentro de un Cowork desktop app.

Para Aithera V0.7 esto significa: si en el futuro (V0.8+) el equipo decide abrir el chatbot a Telegram o WhatsApp, el patrón "Message envelope unificado" del OpenClaw es la referencia de diseño a estudiar — pero **con sandboxing estricto desde la primera versión**, porque la historia post-Clawdbot demuestra que el caos es inevitable cuando se escala el número de integraciones.

## Decisiones de diseño que NO se deberían copiar

El caso Clawdbot ofrece también un catálogo de malas decisiones que Aithera debe evitar:

1. **Naming fonéticamente similar a un incumbent** (Clawd / Claude). La lección general: inventar nombres nuevos en lugar de variantes fonéticas de marcas conocidas.
2. **Skill system sin scanner estático en v1** (resolvieron en v2026.6.1). Aithera V0.7 nace con `allowed_tools` whitelist y validación explícita en ToolManager — esa decisión arquitectónica temprana es defensiva.
3. **Exponer admin UI sin TLS/auth en v1** (20K+ instancias vulnerables en feb 2026). Aithera V0.7 es localhost-only por diseño — esa restricción es una ventaja, no una limitación.
4. **Permitir actions irreversibles sin confirmación explícita** (MoltMatch). Aithera V0.7 mantiene `/api/email/send` con "requiere confirmación" explícito y `EmailActivityLog` para auditoría. Esa es la decisión correcta.
5. **No publicar ningún md de seguridad antes del incidente Cisco**. La documentación de seguridad debe ser prospectiva, no reactiva.

## Observación metodológica (cómo se hizo este doc)

Este doc se construyó siguiendo el flujo estándar JWIKI (investigador → escriba → auditor). Una particularidad notable: la investigación del repositorio canónico reveló que "Clawdbot" **no es un proyecto autónomo**, contra el briefing original. La Constitución JWIKI explícitamente prohíbe inventar información (§2 principio 1: "Nunca inventar información"). Ese fue el motivo principal para elegir Opción A — escribir un doc **histórico del nombre Clawdbot** — en lugar de Opción C (fabricar un proyecto "Clawdbot MCP-based" que no existe). La Opción B (redirect puro a JWIKI-003) habría sido funcional pero habría perdido la oportunidad de documentar la **dinámica de renames forzados** que es probable que se repita en el ecosistema OSS en los próximos años (especialmente a medida que marcas como Anthropic, OpenAI, Cohere siguen vigilando sus territorios de marca).

La lección para futuras iteraciones de la JWIKI: **no dar por buenos los briefings sin verificar** las asunciones centrales. El briefing decía "Clawdbot MCP-based" y la realidad es "nombre viral de un proyecto multi-canal-first que pasó a llamarse OpenClaw". La verdad en Github API + Wikipedia + Forbes + CNBC fue convergente en 3 fuentes independentes, suficiente para invertir el briefing sin piedad.

---

## Changelog

### 2026-06-30 — v1.0 (escriba slot A, turno A tick A-19:30)
- **Autor**: Aithera Escriba (`aithera-wiki-escriba`, sesión `mvs_9b7c7d96bb4d48688e84ce55b9c1f963`, turno A)
- **Cambio**: doc inicial creado siguiendo plantilla JWIKI v1.0. Estrategia **Opción A** del briefing (complemento histórico a JWIKI-003, no redirect puro). Cubre: rename lineage (5 nombres, 5 fechas), era viral Clawdbot (2-26 ene 2026), crisis trademark Anthropic + doble rename 72h, controversias post-rename (MoltMatch, Cisco security research, restricciones China, intentos Microsoft/Google de imitación), stack y arquitectura (MCP como capa + multi-canal como identidad), tabla comparativa 4 proyectos genuinamente MCP-native (moltis, EverOS, memov, AionUi), contraste con OpenHuman / OpenJarvis / Hermes / JarvisAgent / Aithera V0.7.
- **Material crudo**: `JWIKI/material/JWIKI-008-raw.md` (74 hechos verificados, 213 líneas, 28.7 KB)
- **Anclas obligatorias**: ✅ OpenClaw (JWIKI-003), ✅ OpenHuman (JWIKI-004), ✅ Hermes Agent (JWIKI-007), ✅ Aithera V0.7 (proyecto OSS local). ✅ Referencia lateral a `moltis-org/moltis` (JWIKI-267) sin sección propia.
- **Validador**: `aithera-wiki-auditor` (turno A) — pendiente, próximo dispatch tras cierre de wiki-map.
- **Nivel de confianza inicial**: 78% (auditor ajustará).
