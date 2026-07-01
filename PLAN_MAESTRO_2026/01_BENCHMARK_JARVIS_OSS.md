# Benchmark — Proyectos JARVIS-like OSS (julio 2026) vs Aithera

> Síntesis de JWIKI (docs verificados) + investigación web 2026-07-02.
> Objetivo: extraer patrones de ingeniería aplicables a Aithera, no copiar features.

---

## 1. Tabla comparativa

| Proyecto | Stars | Stack | Categoría | Lección principal para Aithera |
|---|---|---|---|---|
| OpenClaw | ~376k | TypeScript | Multi-canal cloud/local | Message envelope único + skills SKILL.md + sandbox per-skill |
| Superpowers | ~215k | Shell/Markdown | Skill framework | Formato de skill estandarizado, lazy loading |
| Hermes Agent | ~53k | Python+Node | Self-evolving | Traces de uso como materia prima de mejora |
| OpenHuman | ~34k | Rust+TS (Tauri 2) | Desktop-first | Ingesta proactiva cada 20 min + memoria jerárquica + vault legible |
| LangGraph | ~36k | Python | Framework agentes | Checkpointing, interrupt() HITL, estado explícito |
| OpenJarvis (Stanford) | ~7.2k | Python | Local-first académico | 5 primitivas ortogonales, routing por complejidad, learning loop |
| Inbox Zero | (creciente) | TypeScript | Email agent | Rule engine + IA, autonomía gradual por regla, HITL por defecto |
| Mark-XL…XLVII (FatihMakes) | pequeño | Python | Voice/local | Proactividad concreta: morning briefing, monitor con umbrales |
| Leon 2.0 | ~17k | Node/TS | Personal assistant | De intent-classification a arquitectura agéntica; "bounded proactive pulse" |
| Aithera | privado | Python+TS (Electron) | Desktop personal | — |

## 2. Análisis por proyecto (lo aprovechable)

### OpenJarvis (Stanford) — el mejor diseño conceptual
Cinco primitivas ortogonales con interfaces limpias e intercambiables: Intelligence
(catálogo de modelos), Engine (runtime de inferencia), Agents (comportamiento),
Tools & Memory, Learning (loop cerrado sobre traces locales). Aithera ya tiene 4 de 5
(AIManager cubre Intelligence+Engine; AgentManager; ToolManager+MemoryManager).
**Falta Learning**: no guardamos traces de decisiones. Acción: desde V1.0, loguear
cada decisión del Orchestrator (intent, modelo usado, plan, resultado, latencia) en
una tabla `orchestrator_traces`. No construir el loop de optimización aún — solo
capturar los datos. Segundo diferenciador: **routing por complejidad** (query simple →
modelo local barato; compleja → modelo potente). Encaja perfecto con nuestros 8
proveedores: Ollama/MiniMax para clasificar, Claude/GPT para planificar.

### OpenClaw — la mejor ingeniería de plataforma
El **message envelope único** aísla 11+ canales de la lógica del agente: cada adapter
convierte su canal a un formato común y todo lo demás es channel-agnostic. Para V0.8
(Telegram + Web) es EL patrón: un `Gateway` con `MessageEnvelope {channel, user_ref,
text, attachments, reply_to}` y adapters finos. Así Telegram no duplica ni una línea
de lógica. Sus skills (folder + SKILL.md con frontmatter, carga lazy por prioridad)
son interesantes para V1.1+, no antes. Sus controversias de seguridad (skills de
terceros maliciosas) no nos aplican: no tenemos marketplace.

### OpenHuman — el mejor contexto
"Context in minutes, not weeks": sync automática cada 20 min desde conectores OAuth
hacia memoria local jerárquica (summary trees en SQLite) + vault .md legible
(Obsidian-compat). Aithera hoy consulta Gmail/Calendar **on-demand**; el asistente
no "sabe" nada hasta que preguntas. Acción (V0.8.5): job de background que ingiere
emails nuevos + eventos hacia ChromaDB con resúmenes jerárquicos (email → hilo →
día → semana). El vault legible en Markdown es opcional pero barato y da
transparencia total sobre qué recuerda el asistente.

### LangGraph — los mejores primitivos de ejecución
No adoptamos el framework (principio 8), copiamos 3 ideas: (1) **checkpointing** —
persistir el estado de una ejecución multi-paso para reanudar tras crash; nuestra
tabla `agent_executions` ya apunta ahí, hay que añadir `checkpoint_data` JSON;
(2) **interrupt()/approval gates** — pausar una ejecución hasta aprobación humana,
como primitivo genérico del ExecutionEngine, no como caso especial del email;
(3) **estado explícito** — cada paso del futuro Orchestrator recibe y devuelve
estado tipado, sin magia.

### Inbox Zero — el mejor email assistant real
Es exactamente el producto que queremos que sea nuestro módulo de email: la IA
**clasifica y propone**, un rule engine determinista **ejecuta**, y cada regla tiene
nivel de autonomía (`propose` → `auto`) que el usuario sube cuando confía. Reglas
describibles en lenguaje natural. HITL por defecto. Drafts con la voz del usuario
(aprendida de emails enviados). Nuestro `EmailAutoReplyRule` + `EmailActivityLog`
ya son la base; falta el triaje del inbox completo (categorías), el digest y la
autonomía gradual. Detalle en `02_FASE_EMAIL_ASSISTANT_FINAL.md`.

### Mark-XL → Mark-XLVII — proactividad concreta y barata
Proyecto pequeño pero con ideas directamente robables: **morning briefing** al primer
arranque del día (hora, noticias, clima, agenda), **monitor de sistema** con umbrales
y cooldown de avisos, búsqueda multi-modo con fallback. Todo encaja como reglas
predefinidas del Automation Engine V0.9 (`email_summary` ya estaba previsto; añadir
`daily_briefing` y `system_monitor`).

### Leon 2.0 — validación del camino
Leon pasó de clasificador de intents a arquitectura agéntica con memoria por capas,
skills nativas deterministas + workflows agénticos, y "bounded proactive pulse"
(proactividad acotada, no un agente suelto 24/7). Valida dos decisiones nuestras:
el Orchestrator V1.0 con modos (conversación / tool / plan) y la automatización
con aprobaciones V0.9. Su lección: mantener **skills deterministas** para lo
repetible y reservar el modo agéntico para lo abierto.

### Hermes Agent / Superpowers — para después
Self-evolving y skill-format estandarizado. Ambos dependen de tener traces (P5) y
formato de skill (OpenClaw). Nada que hacer antes de V1.1.

## 3. Matriz de brechas (Aithera vs estado del arte)

| Capacidad | Estado del arte | Aithera hoy | Brecha | Fase |
|---|---|---|---|---|
| Email triage + autonomía gradual | Inbox Zero | Reglas auto-reply + detección reuniones | Media | V0.7.2 |
| Tests + CI | Todos los grandes | Tests unitarios solo en meeting detection | **Alta** | V0.7.3 |
| Multi-canal sin duplicar lógica | OpenClaw envelope | Solo Electron | Media | V0.8 |
| Seguridad de red (auth, CORS, secrets) | Todos | CORS *, keys en texto plano, sin auth | **Alta** (al abrir red) | V0.8 |
| Contexto proactivo | OpenHuman | Memoria pasiva on-demand | Media | V0.8.5 |
| Approval gates genéricos | LangGraph | Solo confirmación de envío email | Media | V0.9 |
| Checkpointing ejecuciones | LangGraph | `agent_executions` sin resume | Baja | V0.9 |
| Routing por complejidad | OpenJarvis | Un proveedor activo global | Media | V1.0 |
| Traces para learning | OpenJarvis/Hermes | Nada | Baja (solo capturar) | V1.0 |
| MCP interop | OpenClaw/OpenJarvis/moltis | Nada | Media | V1.1 |
| Voz siempre disponible | Mark-XLVII, OpenHuman | Backend OK, UI básica | Baja | post-V1.0 |

## 4. Riesgos de adopción

- **Refactor email rompe OAuth** — mitigación: tests de contrato antes del split, cuenta Google secundaria, feature-freeze del módulo durante el refactor.
- **Ingesta proactiva dispara coste/latencia** — mitigación: solo Ollama/modelo local para resúmenes de ingesta; batch nocturno para summary trees.
- **Gateway V0.8 sobreingenierizado** — mitigación: envelope de 5 campos y 2 adapters (telegram, web). Nada de plugin system.
- **Security hardening rompe el flujo local** — mitigación: PIN/token solo para orígenes no-localhost.

## 5. Qué añadir a la JWIKI (para el equipo wiki)

- JWIKI-XXX: Inbox Zero (elie222/inbox-zero) — no está en el landscape y es la referencia directa de nuestro módulo estrella.
- JWIKI-XXX: Leon 2.0 (leon-ai/leon) — pendiente en `projects.md`.
- JWIKI-XXX: Mark-XL series (FatihMakes) — pendiente citado en `projects.md`.
- Completar auditoría de `openjarvis.md` y `clawdbot.md` (están 🟡 En progreso).

## 6. Conclusión

Nadie en el landscape combina lo que Aithera persigue (desktop personal + email/calendar
profundo + agentes con whitelist + memoria semántica + voz). OpenClaw es multi-canal
pero caótico en seguridad; OpenHuman tiene el mejor contexto pero sin motor de agentes
serio; OpenJarvis es el mejor diseño pero académico; Inbox Zero solo hace email.
**La posición de Aithera es defendible; la ejecución (deuda + tests + seguridad) es
lo único que la separa del nivel de los grandes.**

## 7. Fuentes web (2026-07-02)

- https://github.com/open-jarvis/OpenJarvis + https://scalingintelligence.stanford.edu/blogs/openjarvis/
- https://www.marktechpost.com/2026/03/12/stanford-researchers-release-openjarvis-a-local-first-framework-for-building-on-device-personal-ai-agents-with-tools-memory-and-learning/
- https://github.com/FatihMakes/Mark-XL · https://github.com/FatihMakes/Mark-XLVII
- https://github.com/leon-ai/leon + https://docs.getleon.ai/architecture + https://blog.getleon.ai/road-to-2-0/
- https://github.com/elie222/inbox-zero
- https://www.vellum.ai/blog/best-open-source-personal-ai-assistants
- JWIKI local: `JWIKI/01_LANDSCAPE/*.md` (6 verificados) + `JWIKI/material/JWIKI-001..011-raw.md`

---
*Creado: 2026-07-02.*
