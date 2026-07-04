# Roadmap actualizado — V0.7.2 → V1.2

> Evolución del roadmap de `AOS_Arquitectura_y_Roadmap.md` incorporando los patrones
> del benchmark (`01_BENCHMARK_JARVIS_OSS.md`). Los principios 1-8 del AOS siguen
> vigentes e inviolables. Cambios respecto al roadmap anterior marcados con 🆕.

---

## V0.7.2 – V0.7.3 — Email Assistant FINAL + Fundamentos

Ver `02_FASE_EMAIL_ASSISTANT_FINAL.md`. Resumen: commit inicial + pytest baseline +
auditoría legacy → split god-endpoint → triaje Inbox-Zero + autonomía gradual +
digest → pulido y release. 🆕 respecto al plan anterior: triaje por categorías,
autonomía gradual por regla, digest, y la red de seguridad (git/tests) como sesión 0.

## V0.8 — Clientes: Gateway + Telegram + Web + PWA + Seguridad

Base: `Fase_5_Clients_Telegram_Web_V08.md`, con dos adiciones estructurales.

🆕 **Gateway con message envelope único (patrón OpenClaw).** Antes de escribir el bot:
`app/gateway/` con `MessageEnvelope {channel, user_ref, text, attachments, reply_to,
metadata}` y `ChannelAdapter` base. El bot de Telegram y el chat web son adapters
finos que convierten su formato al envelope y entregan la respuesta. La lógica de
negocio no sabe qué canal la llamó. Coste: ~1 sesión extra. Beneficio: cualquier
canal futuro (Discord, WhatsApp) es solo un adapter.

🆕 **Security hardening (bloqueante para exponer la red):**
- ✅ CORS restringido a orígenes conocidos (localhost + `null` de Electron +
  `CORS_ALLOWED_ORIGINS` para IPs de LAN). Ya NO `allow_origins=['*']`.
- ✅ Cifrado de API keys en BD: DPAPI de Windows (`app/core/secrets.py`), cifrado
  al escribir / descifrado al instanciar en el `AIManager`; migración Alembic
  `d4e5f6a7b8c9_v08_encrypt_api_keys` re-cifra las existentes (idempotente).
- ✅ Autenticación del bot de Telegram por `chat_id` whitelist.
- ⏳ PIN/token de sesión para origen no-localhost — se implementa junto al
  cliente Web (post-V1.0), que es cuando hace falta exponer a la red.
- ⏳ Rate limiting básico (slowapi) — opcional, con el cliente Web.

**Estado V0.8**: ✅ Gateway + Telegram (adapter, comandos, chat natural,
config desde Ajustes) + Security Hardening (CORS + API keys cifradas) HECHOS.
⏳ **Cliente Web (`/app`) + PWA APLAZADOS a post-V1.0** (decisión 2026-07-04):
no bloquean Hub Visual, Voz, Memory, Automation ni Orchestrator.

## V0.82 — Hub Visual (pulido de UI, 🆕 2026-07-04)

Tras el hardening, mejora visual del Hub:
- Animación de conversación (el chat cobra vida en el Hub).
- Modo pantalla completa con botones para desplegar/plegar las barras laterales
  (tareas, proyectos, funcionalidades, etc.).

## V0.83 — Voz completa (🆕 2026-07-04)

- Terminar de configurar las voces principales de ElevenLabs.
- STT (speech-to-text) con reconocimiento de voz. (Adelanta parte de la antigua
  "Voice 2.0" de Post-V1.1.)

## V0.85 — Memory & Context (ANTES del Automation Engine)

Salto de memoria de verdad, previo a la automatización y al orchestrator
(decisión 2026-07-04). Objetivo: un sistema de memoria realmente bueno con
**captura automática de skills, contexto de proyectos, briefings ricos y
detección de patrones de trabajo**. Sobre esa base (patrón OpenHuman):

1. **Ingesta en background**: job asyncio (no APScheduler aún) cada 20 min que trae emails nuevos y eventos próximos y los indexa en ChromaDB con su categoría de triaje.
2. **Summary trees**: resúmenes jerárquicos email→hilo→día→semana, generados en batch nocturno con modelo local (Ollama) para coste cero.
3. **Contexto en el chat**: el endpoint de chat inyecta top-k de memoria relevante (ya existe RAG; ahora tendrá material fresco de verdad).
4. 🆕 opcional: **vault legible** — espejo en Markdown de lo que el asistente recuerda (`%APPDATA%/Aithera/vault/`), inspirado en OpenHuman/Obsidian. Transparencia total; borrar un .md = olvidar.

Criterio de cierre: preguntar "¿qué me ha llegado importante hoy?" responde desde
memoria sin llamar a Gmail en caliente.

## V0.9 — Automation Engine + Approval Gates

Base: `Fase_6_Automation_V08.md` (APScheduler, `AutomationRule`,
`AutomationExecution`, tipos de acción, UI). Adiciones:

🆕 **Approval gates genéricos (patrón LangGraph `interrupt()`).** Primitivo del
ExecutionEngine: cualquier tool puede declararse `requires_approval`. La ejecución
se pausa en estado `waiting_approval` (persistida en BD), notifica por el canal que
originó la acción (Hub toast / Telegram) y se reanuda o cancela con la respuesta.
La confirmación de envío de email se migra a este mecanismo — deja de ser caso especial.

🆕 **Checkpointing.** `agent_executions.checkpoint_data` (JSON) actualizado por paso.
Tras un crash, las ejecuciones `running` se recuperan o se marcan `interrupted` con
diagnóstico. Suficiente para un usuario; nada de Redis.

🆕 **Reglas predefinidas estilo Mark-XLVII** (desactivadas por defecto, principio HITL):
- `daily_briefing` — briefing matinal: digest de email (V0.7.3) + agenda + tareas del día, entregado en Hub y/o Telegram.
- `system_monitor` — chequeo de backend/BD/proveedores con aviso si algo cae (cooldown 5 min).
- `email_summary` y `agent_task` como estaban previstas.

## V1.0 — Orchestrator

Base: `Fase_8_Orchestrator_V10.md` (Intent Analyzer, Task Planner, Response Builder,
Claude Code Agent, UI de aprobación de planes). Adiciones:

🆕 **Routing por complejidad (patrón OpenJarvis).** El Intent Analyzer corre SIEMPRE
en el modelo más barato disponible (Ollama local > MiniMax highspeed). Solo si la
intención requiere planificación multi-paso se invoca el modelo potente. Config de
routing en Settings (`fast_model`, `smart_model`).

🆕 **Traces first-class.** Tabla `orchestrator_traces`: intent detectado, modelo
usado, plan, tools ejecutadas, resultado, latencia, tokens. Sin loop de optimización
todavía — solo capturar. Es la materia prima del futuro learning loop (Hermes/
OpenJarvis) y del debugging.

Sin cambios en la decisión clave: orchestrator custom (~200 líneas), sin LangChain/
LangGraph/CrewAI como dependencia.

## V1.1 — Hermes como sistema de agentes principal (🆕 2026-07-04)

Integrar **Hermes** (Nous Research, https://hermes-agent.nousresearch.com/) POR
DEBAJO del Orchestrator, como motor de agentes principal. La idea: el Orchestrator
(V1.0) sigue decidiendo intención y plan, pero delega la EJECUCIÓN de agentes en
Hermes, de forma que los agentes guiados por Hermes usen su propio sistema de
**skills, memoria y aprendizaje de trabajo**.

Trabajo de esta fase:
1. **Investigar la vía de integración**: cómo se invoca Hermes (API/SDK/local),
   qué contrato expone, y cómo encaja con el `AgentManager`/`ExecutionEngine`
   actuales sin romper la whitelist ni los approval gates (principio 5).
2. **Puente Orchestrator → Hermes**: el Orchestrator delega tareas de agente en
   Hermes y recibe resultados; Aithera conserva el control de ejecución.
3. **Skills/memoria de Hermes ↔ memoria de Aithera (V0.85)**: decidir qué es la
   fuente de verdad y cómo se sincronizan.
- **Estado**: idea de roadmap, pendiente de diseño.

## V1.2 — MCP Interop (antes V1.1, desplazada por Hermes)

MCP es el estándar de facto 2026 (OpenClaw, OpenJarvis, moltis). Dos mitades:

1. **Aithera como servidor MCP**: exponer el ToolManager (las 8 tools con sus schemas ya validados) vía MCP. Claude Code, Claude Desktop o cualquier cliente MCP podrán usar las tools de Aithera con la misma whitelist y los mismos approval gates.
2. **Aithera como cliente MCP**: `MCPToolProxy` que registra tools de servidores MCP externos en el ToolManager, pasando por las mismas validaciones que las tools nativas (principio 5: ejecución controlada — una tool MCP externa nunca se salta el gate).

Preparación barata antes de llegar: al tocar `tool_manager.py` en fases previas,
mantener los schemas de parámetros en JSON Schema puro (ya casi lo son).

## Post-V1.2 (sin comprometer)

- Voice 2.0: wake word / push-to-talk global, STT Whisper local (JWIKI 08_VOICE).
- Learning loop sobre `orchestrator_traces` (ajuste de prompts/routing).
- Auto-start del backend desde Electron + auto-update (deuda §16.5 — puede adelantarse a cualquier fase si molesta en el día a día).
- Skills SKILL.md para definir comportamiento de agentes (formato OpenClaw/agentskills.io).

## Tabla resumen

| Versión | Nombre | Estado | Entregable usable |
|---|---|---|---|
| V0.7.2-3 | Email FINAL + fundamentos | ✅ hecho | Email assistant terminado, repo con git+tests |
| V0.8 | Gateway + Telegram + Hardening | ✅ hecho | Aithera desde Telegram, CORS restringido, API keys cifradas |
| V0.82 | Hub Visual | ⏳ | Animación de conversación + modo pantalla completa con toggles laterales |
| V0.83 | Voz completa | ⏳ | Voces ElevenLabs principales + STT |
| V0.85 | Memory & Context | ⏳ | Skills auto-capturadas, contexto de proyectos, briefings ricos, patrones |
| V0.9 | Automation + approvals | ⏳ | Briefing matinal, reglas, aprobaciones |
| V1.0 | Orchestrator | ⏳ | Chat que decide, planifica y ejecuta |
| V1.1 | Hermes | ⏳ | Agentes con skills/memoria/aprendizaje de Hermes bajo el Orchestrator |
| V1.2 | MCP Interop | ⏳ | Interop con ecosistema MCP |
| post-V1.0 | Cliente Web + PWA | ⏳ aplazado | Web servida por FastAPI + PWA + PIN de red |

Regla de siempre: si una fase crece, se parte en dos (principio 7).

---
*Creado: 2026-07-02. Reordenado 2026-07-04: V0.8 (Gateway+Telegram+Hardening) cerrado;
añadidas V0.82 Hub Visual y V0.83 Voz; V0.85 Memory & Context antes de V0.9; V1.1 pasa
a ser Hermes (Nous Research) y MCP Interop se desplaza a V1.2; Cliente Web + PWA aplazados
a post-V1.0. Complementa a `AOS_Arquitectura_y_Roadmap.md` y a los docs Fase_5/6/8.*
