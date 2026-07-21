# 31 — OBSERVABILIDAD DE MISIONES + TEST-LAB
## El ciclo revisión → test → mejora del entorno Orchestrator/TIE/MEL

> **Origen**: fallo real de producción (2026-07-21, "caso Melendi"): una misión
> de navegador tardó minutos por paso, no logró el clic, y el modelo del chat
> (Claude CLI) respondió con su identidad de terminal ("soy Claude Code, no
> tengo navegador") en vez de usar las tools de Aithera. El usuario fijó el
> siguiente foco: **Misiones** — qué modelo funciona mejor y más rápido en cada
> tarea, qué tools fallan, y dónde se equivocan TIE/MEL/Orquestador. Este doc
> describe el sistema construido (YA implementado) y el ciclo que lo explota.

---

## 1. ANÁLISIS DEL CASO MELENDI (por qué pasó)

| Síntoma | Causa raíz | Corrección |
|---|---|---|
| Respuestas de minutos | El chat/clasificador iban por Claude CLI: un PROCESO por llamada (arranque + sin streaming) | **Gating de capacidades** (§3): Claude CLI ya no puede servir chat/classify/agentic |
| "Soy Claude Code, no tengo navegador" | El CLI conserva su identidad de asistente de código; `--append-system-prompt` no la sustituye | Ídem — fuera del chat interactivo; apto solo para trabajo de fondo (code/reason/draft/summarize/analyze) |
| El clic no llegó | Sin telemetría no se sabía QUÉ paso falló ni con qué modelo | **Telemetría punta a punta** (§2) — la próxima vez el timeline lo dirá exactamente |
| Ventana "de test" vs pestaña en Chrome real | Playwright (browser_tool) usa su Chromium propio; la pestaña en el Chrome del usuario apunta a otra vía (a investigar con el lab) | Escenario `browser_wikipedia` del lab + timeline |

## 2. TELEMETRÍA PUNTA A PUNTA (implementada)

**`app/telemetry/`** (disciplina modular doc 16) + tabla **`mission_events`**
(migración 26.ª `a7c8d9e0f1a2`): un evento por hecho relevante, con timings.

- **Etapas registradas**: `mission_start` · `intent` (tipo, camino corto/directo,
  requires_*) · `plan` (nº nodos, sensibles) · `llm_call` (capacidad, proveedor,
  modelo, latencia, ok, fallbacks) · `tool_call` (tool.acción, duración, ok,
  error) · `node_end` (estado, runtime, tools) · `mission_end` (estado, duración
  total).
- **Hooks quirúrgicos** (puntos únicos, nunca rompen el pipeline — best-effort
  como el tracer): `tracer.record_start/intent/plan/end` (TODAS las rutas pasan
  por ahí: handle, stream, submit_mission, acción directa) + `mel/executor.
  _record_async` (CADA llamada LLM, complete y stream) + `toolloop` (cada tool)
  + `tie/executor` (`run` fija el contexto al reanudar; `_transition` registra
  nodos terminales).
- **Contexto por `contextvars`**: el mission_id viaja solo por el task — los
  hooks no necesitan parámetros nuevos. Llamadas sueltas (chat corto) quedan
  con mission_id NULL (también se miden).
- **¿Por qué BD y no el bus?** El bus (doc 17) es in-process y sin
  persistencia: se pierde justo cuando más falta hace (tras un fallo/reinicio).
  La BD es la fuente de verdad; un espejo al bus para vistas en vivo es
  extensión futura. **Esto queda DENTRO de Aithera**: cuando haya usuarios,
  sus misiones generan la misma telemetría (retención 30 días, purga 04:35
  junto a la de trazas; sin contenido del usuario — solo metadatos/timings).
- **API**: `GET /api/telemetry/missions/{id}` (timeline + resumen) y
  `GET /api/telemetry/report?hours=` (agregado: latencia por capacidad|modelo,
  tasa de éxito por tool, misiones ok/failed, últimos errores).

## 3. GATING DE CAPACIDADES (implementado)

`mel/catalog.py::UNFIT_CAPABILITIES` — hoy: `claude_code` no apto para
`chat`, `classify`, `agentic`. Tres capas: (1) el compilador de políticas lo
excluye, (2) **filtro retroactivo en ejecución** (`active_chain`/
`chain_for_named` lo saltan aunque siga en una política guardada — sanea la
config del usuario sin tocarla), (3) la UI lo excluye de los selectores, marca
⛔ lo heredado y lo avisa en la tarjeta del proveedor. El primario "efectivo"
que muestran Sidebar/Hub/Estado ya salta los no-aptos.

## 4. TEST-LAB (implementado)

- **`test-lab/`** (gitignored): TODO lo que crean las misiones de prueba vive
  ahí. Regla dura: jamás una misión de test toca archivos reales.
- **`scripts/mission_lab.py`**: batería contra el backend real por HTTP (el
  mismo camino del usuario): archivos, mini-web, script Python, búsqueda web,
  navegador (Wikipedia), memoria, multi-objetivo. Desktop EXCLUIDO de la
  batería automática (solo con el usuario delante).
- **`scripts/mission_report.py`**: timeline legible por misión + `--aggregate`.

## 5. EL CICLO (siguientes sesiones)

1. **Baseline**: correr la batería completa con la config actual → guardar el
   reporte agregado como línea base (tiempos por capacidad/modelo, éxito por
   tool).
2. **Matriz de modelos**: repetir escenarios clave alternando el modelo del
   toolloop (`TIE_TOOL_POLICY`/`TIE_TOOL_MODEL`: qwen3:8b vs 14b vs nube
   barata) → decidir con datos, no a ojo.
3. **Tools con peor tasa de éxito** (el reporte las ordena): reproducir con el
   timeline delante, arreglar, re-correr. Candidato nº1: `browser.click` en
   sitios dinámicos (caso Melendi) y la ventana Chromium-vs-Chrome del usuario.
4. **Presupuestos**: fijar umbrales (p.ej. acción directa < 15s, paso de
   toolloop < 3s local) y convertirlos en tests de perf como los de T5.
5. **UI (futuro)**: pestaña "Actividad" en Misiones que pinte el timeline por
   misión (los endpoints ya existen).

---
*Implementado y verificado 2026-07-21 (timeline/reporte/gating ejercitados
contra el código real con BD real). El lab requiere el backend corriendo en
Windows.*
