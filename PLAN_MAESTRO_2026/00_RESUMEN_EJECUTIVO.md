# Plan Maestro 2026 — Resumen Ejecutivo

> Análisis comparativo de Aithera V0.7.1 contra el landscape JARVIS-like 2026
> (JWIKI + investigación web julio 2026) y plan de acción resultante.
> Carpeta: `PLAN_MAESTRO_2026/`. Complementa (no sustituye) a `AOS_Arquitectura_y_Roadmap.md`.

---

## 1. Veredicto general

Aithera está **bien diseñada**. Sus 8 principios (evolución no reescritura, un backend
múltiples clientes, la IA razona / Aithera decide, ejecución con whitelist, sin
sobreingeniería) coinciden con lo que los mejores proyectos del landscape aprendieron
por las malas. No hay que cambiar la filosofía; hay que **cerrar deuda, endurecer
seguridad y adoptar 5 patrones concretos** que el ecosistema ha validado.

Lo que Aithera ya hace igual o mejor que los grandes:

- Whitelist de tools + validación de parámetros + timeout (patrón sandbox de OpenClaw, sin Docker pero adecuado para un solo usuario local).
- Confirmación humana antes de enviar email (patrón human-in-the-loop de LangGraph `interrupt()` e Inbox Zero).
- Multi-proveedor con fallback y health check (equivalente a Intelligence/Engine de OpenJarvis).
- Memoria semántica con degradación graceful (pocos OSS la tienen tan limpia).
- Detección de reuniones en dos etapas patrón AMD GAIA + cross-check de Calendar (V0.7.1) — nivel estado del arte.

## 2. Los 5 patrones a adoptar (del benchmark)

| # | Patrón | Origen | Dónde encaja en Aithera |
|---|--------|--------|--------------------------|
| P1 | **Rule engine + IA con autonomía gradual por regla** — la IA clasifica, un motor de reglas determinista ejecuta; cada regla empieza en "proponer" y el usuario la sube a "auto" cuando confía | Inbox Zero | Terminar Email Assistant (V0.7.2) |
| P2 | **Message envelope único channel-agnostic** — un Gateway normaliza input de todos los canales antes de tocar lógica de negocio | OpenClaw | V0.8 (Telegram + Web). Evita duplicar lógica por canal |
| P3 | **Ingesta proactiva de contexto** — sync en background (cada N min) de Gmail/Calendar hacia la memoria, con summary trees jerárquicos; el asistente ya tiene el contexto cuando preguntas | OpenHuman | V0.8.5 (nueva sub-fase Memory 2.0) |
| P4 | **Checkpointing + approval gates formales** — estado de ejecución persistente y reanudable; gate de aprobación genérico para toda acción sensible (no solo email) | LangGraph | V0.9 Automation Engine |
| P5 | **Routing por complejidad + traces** — clasificar intent con modelo barato/local (Ollama/MiniMax), planificar con modelo potente; loguear traces de cada decisión para optimización futura | OpenJarvis (Stanford), Leon 2.0 | V1.0 Orchestrator |

Patrón transversal: **MCP (Model Context Protocol)** es el estándar de facto 2026
(OpenClaw, OpenJarvis, moltis). Aithera debería exponer sus tools como servidor MCP
y poder consumir servidores MCP externos. Propuesto como V1.1, con diseño previo
del ToolManager compatible (no bloquea nada antes).

## 3. Lo que hay que arreglar ya (deuda crítica, orden de urgencia)

1. **Commit del trabajo pendiente** — verificado 2026-07-02: hay 5 commits (bootstrap + JWIKI) pero ~204 archivos con todo el trabajo V0.7.1 sin commitear. Primera tarea del primer sprint, sin excepción. (CLAUDE.md §1 dice "sin ningún commit" — desactualizado, corregir.)
2. **God-endpoint `email_assistant.py` (2038 líneas y creciendo)** — dividir en 5 routers (ya especificado en CLAUDE.md §16.1). Se hace como parte de terminar el Email Assistant, con OAuth probado en cuenta secundaria antes y después.
3. **Módulo legacy `backend/modules/email_assistant/`** — auditar, extraer lo útil (si hay), eliminar. Dos fuentes de verdad para email es la deuda más peligrosa del repo.
4. **Baseline de tests** — pytest + tests de los 5 routers nuevos de email + smoke test de arranque. Sin esto, el refactor del punto 2 es ruleta rusa. Los proyectos grandes del landscape (LangGraph, OpenClaw) liberan cada 2 días *porque* tienen tests.
5. **Seguridad antes de V0.8** — en cuanto haya Telegram/Web, la superficie de ataque deja de ser localhost: cerrar CORS, PIN de acceso, cifrar API keys en BD (DPAPI de Windows o Fernet con clave en `%APPDATA%`), rate limiting básico. Bloqueante para V0.8, no para V0.7.2.
6. **Docs duplicados de fase** — archivar `Fase_2_..._V04.md` y `Fase_5_Telegram_V07.md` en `archive/`. 15 minutos, elimina confusión permanente.

## 4. Lo que NO vamos a hacer (y por qué)

- **No adoptar LangGraph/CrewAI como framework** — el orchestrator custom de ~200 líneas previsto en V1.0 sigue siendo la decisión correcta para un solo usuario (principio 8). Copiamos sus *patrones* (checkpointing, interrupt), no su dependencia.
- **No multi-canal masivo estilo OpenClaw** (11+ canales) — Telegram + Web + PWA bastan. El Gateway P2 deja la puerta abierta si algún día hace falta.
- **No reescribir en Rust/Tauri** (OpenHuman, JarvisAgent) — Electron ya funciona; migrar sería reescritura, violando el principio 2. Se reevalúa solo si el peso de Electron se vuelve un problema real.
- **No self-evolving skills** (Hermes) — experimental, sin beneficio claro para un usuario. Los traces del P5 dejan la base para retomarlo en el futuro.
- **No marketplace de skills** — no hay comunidad que servir; somos un usuario.

## 5. Secuencia de fases actualizada

```
V0.7.2  Email Assistant FINAL      ← EMPEZAMOS AQUÍ (doc 02)
V0.7.3  Fundamentos: git + tests + limpieza docs (entrelazado con V0.7.2)
V0.8    Clientes: Gateway envelope + Telegram + Web + PWA + Security hardening
V0.8.5  Memory 2.0: ingesta proactiva + summary trees + briefing diario
V0.9    Automation Engine: APScheduler + approval gates + checkpointing
V1.0    Orchestrator: intent routing por complejidad + planner + traces
V1.1    MCP: exponer tools como MCP server + consumir MCP externos
```

Detalle por fase en `03_ROADMAP_ACTUALIZADO.md`. Backlog priorizado y primer
sprint en `04_BACKLOG_Y_SPRINTS.md`.

## 6. Fuentes

- JWIKI: `01_LANDSCAPE/` (openjarvis, openclaw, openhuman, clawdbot, langgraph, projects, history) — 6 docs verificados.
- Web (jul 2026): GitHub open-jarvis/OpenJarvis, FatihMakes/Mark-XL→XLVII, leon-ai/leon, elie222/inbox-zero; Scaling Intelligence Lab (Stanford); MarkTechPost; Vellum "8 Best Open-Source Personal AI Assistants 2026". URLs completas en `01_BENCHMARK_JARVIS_OSS.md` §7.

---
*Creado: 2026-07-02. Autor: Claude (análisis Aithera V0.7.1 + JWIKI + web).*
