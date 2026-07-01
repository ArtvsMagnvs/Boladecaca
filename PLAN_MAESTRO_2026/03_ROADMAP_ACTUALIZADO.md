# Roadmap actualizado — V0.7.2 → V1.1

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
- CORS restringido a orígenes conocidos (localhost + IP local declarada).
- PIN/token de sesión para todo origen no-localhost (ya previsto; se implementa aquí, no después).
- Cifrado de API keys en BD: DPAPI de Windows (`win32crypt`) o Fernet con clave en `%APPDATA%/Aithera/.secret` fuera del repo. Migración Alembic para re-cifrar las existentes.
- Rate limiting básico (slowapi) en endpoints públicos.
- Autenticación del bot de Telegram por `chat_id` whitelist (ya previsto).

Resto igual que el doc de fase: python-telegram-bot v21 polling, comandos
`/proyectos`, `/tareas`, `/estado` + chat natural; React build servido por FastAPI
en `/app`; manifest + service worker.

## V0.8.5 — Memory 2.0: contexto proactivo (fase 🆕, patrón OpenHuman)

Hoy la memoria es pasiva. Esta fase la convierte en contexto vivo:

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

## V1.1 — MCP Interop (fase 🆕)

MCP es el estándar de facto 2026 (OpenClaw, OpenJarvis, moltis). Dos mitades:

1. **Aithera como servidor MCP**: exponer el ToolManager (las 8 tools con sus schemas ya validados) vía MCP. Claude Code, Claude Desktop o cualquier cliente MCP podrán usar las tools de Aithera con la misma whitelist y los mismos approval gates.
2. **Aithera como cliente MCP**: `MCPToolProxy` que registra tools de servidores MCP externos en el ToolManager, pasando por las mismas validaciones que las tools nativas (principio 5: ejecución controlada — una tool MCP externa nunca se salta el gate).

Preparación barata antes de llegar: al tocar `tool_manager.py` en fases previas,
mantener los schemas de parámetros en JSON Schema puro (ya casi lo son).

## Post-V1.1 (sin comprometer)

- Voice 2.0: wake word / push-to-talk global, STT Whisper local (JWIKI 08_VOICE).
- Learning loop sobre `orchestrator_traces` (ajuste de prompts/routing).
- Auto-start del backend desde Electron + auto-update (deuda §16.5 — puede adelantarse a cualquier fase si molesta en el día a día).
- Skills SKILL.md para definir comportamiento de agentes (formato OpenClaw/agentskills.io).

## Tabla resumen

| Versión | Nombre | Duración estimada | Entregable usable |
|---|---|---|---|
| V0.7.2-3 | Email FINAL + fundamentos | 5-6 sesiones | Email assistant terminado, repo con git+tests |
| V0.8 | Clientes + seguridad | 5-7 sesiones | Aithera desde Telegram y navegador, red segura |
| V0.8.5 | Memory 2.0 | 3-4 sesiones | Asistente con contexto fresco automático |
| V0.9 | Automation + approvals | 5-6 sesiones | Briefing matinal, reglas, aprobaciones |
| V1.0 | Orchestrator | 6-8 sesiones | Chat que decide, planifica y ejecuta |
| V1.1 | MCP | 3-4 sesiones | Interop con ecosistema MCP |

Regla de siempre: si una fase crece, se parte en dos (principio 7).

---
*Creado: 2026-07-02. Complementa a `AOS_Arquitectura_y_Roadmap.md` y a los docs Fase_5/6/8 existentes.*
