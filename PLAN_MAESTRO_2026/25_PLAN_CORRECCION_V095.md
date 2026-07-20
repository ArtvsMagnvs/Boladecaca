# PLAN DE CORRECCIÓN POST-AUDITORÍA — Aithera v0.9.5 → 1.0
### Fuente de verdad: `24_AUDITORIA_COMITE_V095.md` · Lead: Fable 5 · 2026-07-20

Bloque previo al MVP-beta. 4 sesiones. S1 y S2 las ejecuta Fable 5 (núcleo de
confianza y rediseño del flujo del goal); S3 y S4 son delegables con las
especificaciones de abajo. Cada sesión termina con la suite completa en verde
(`cd backend && python -m pytest tests/ -v`) y verificación en vivo cuando aplique.

---

## S1 — Honestidad, aprobaciones y permisos ✅ EJECUTADA (2026-07-20, Fable 5)

Hallazgos: **A-1, A-2, D-1, #9, #10**. Todo implementado en esta sesión:

**A-1 (`tie/toolloop.py`)** — contrato de grounding: `ok=True` exige ≥1 tool
ejecutada con éxito. Un `{"answer"}` sin intento de tools se RECHAZA con
feedback y se le exige usar herramientas; con intentos fallidos/denegados se
acepta al momento como FALLO honesto con la explicación del modelo conservada
(el responder la cuenta, nunca la disfraza de éxito). La prosa de última
vuelta se conserva pero ya no puede ser éxito sin fundamento.

**A-2 (`toolloop.py` + `automation/approval.py`)** — semántica de timeout
elegida: **expirar** (opción b de la auditoría). `ApprovalGate.expire(gate_id)`
nuevo: claim atómico pending→expired, sin ejecución, emite `approval.expired`;
si el usuario resolvió justo antes, expire() pierde la carrera y el veredicto
real se respeta. El toolloop lo invoca al agotar `approval_wait_s` — cero
aprobaciones cadáver en la UI. *La alternativa (pausar el nodo como gate T3)
exigiría persistir el transcript del bucle en el checkpoint: anotada como
evolución V1.1 (§Evoluciones), no implementada como parche.*

**D-1 (`automation/permissions.py` + `approval.py`)** — 2 permisos nuevos en
el CATALOG (grupo "Misiones"): `tie.plan_approval` (high; en `full`) y
`tie.checkpoint` (low; en `balanced` y `full`). Mapa `_GATE_KIND_PERMISSION`
(tie.plan→plan_approval, tie.node→plan_approval —mismo criterio que T4a:
aprobar el plan autoriza sus pasos—, tie.checkpoint→tie.checkpoint) y
`is_kind_pre_authorized()` como consulta única del gate. Fail-closed intacto
para kinds desconocidos. El frontend no se toca (renderiza grupos
dinámicamente, verificado).

**#9** — `app/desktop.py` (1207 líneas Tkinter muerto) vaciado a tombstone;
borrado físico final: `git rm backend/app/desktop.py`.

**#10 (`core/events.py`)** — set `_inflight` retiene las tasks de handlers
hasta terminar (footgun de GC de asyncio cerrado).

**Tests**: `tests/test_audit_s1_fixes.py` NUEVO (10 tests: grounding × 3,
expire × 2, permisos TIE × 4, events × 1). 4 tests existentes actualizados a
los contratos nuevos (documentado en cada uno; mismo criterio que T4a con
tests obsoletos por cambio de diseño): `test_tie_toolloop.py` × 3 y
`test_permissions.py` (9→11 permisos).

**⚠️ Pendiente de esta sesión (Windows, no ejecutable desde este entorno)**:
correr la suite completa y verificar en vivo con el escenario del fallo D
(perfil Autónomo → misión con plan sensible → cero preguntas, rastro en
`approvals` con `resolution_note="auto (permiso pre-autorizado)"`).

---

## S2 — Fidelidad del objetivo + presupuesto del planner ✅ EJECUTADA (2026-07-20, Fable 5)

Hallazgos: **C-1 + B-1**. Implementado:

**C-1 — fidelidad del objetivo**:
- `Intent.raw_text` (contracts.py, append-only): el texto ORIGINAL del usuario,
  estampado por `classify()` DESPUÉS de parsear el JSON del modelo — ningún
  campo del LLM puede pisarlo. `conversational_fallback` también lo estampa.
- `_complex_path` planifica sobre `intent.raw_text or text` — el goal
  reescrito por el clasificador queda SOLO para UI/trazas/gates.
- Prompt del clasificador: goal = "RESUMEN FIEL… NO añadas información que no
  esté en el mensaje" (antes decía literalmente "reformula el mensaje").
- Prompt del planner: REGLA DE ORO de fidelidad en el system prompt + el
  OBJETIVO etiquetado "la petición del usuario, tal cual — la ÚNICA fuente del
  plan" + el contexto etiquetado "SOLO REFERENCIA, nunca cambia el objetivo".
- `submit_mission(intent=…)` opcional (mismo patrón que `handle_stream`).
  **Decisión de diseño (alternativa al plan original, justificada)**: el
  conductor del Orquestador SIGUE clasificando por objetivo — ese intent
  per-objetivo (memory_types, requires_tools…) es más preciso que heredar el
  del mensaje compuesto, y el daño de la re-clasificación era SOLO la
  reescritura del goal, que raw_text ya elimina (classify estampa el goal
  literal del decomposer). Se cambia precisión por ~0 coste: classify es la
  capability barata.

**B-1 — capacidad honesta**:
- `_tools_catalog_text()`: el planner ve el catálogo REAL (tool_id +
  descripción + ids de acciones, 1 línea por tool), respetando la frontera R4.
- **`PlanRejection`** (dataclass nueva): el modelo puede devolver
  `{"cannot": "…"}` → el pipeline responde al usuario "No puedo hacer esto de
  forma completa…: <motivo>" sin ejecutar nada, estado `done` (es una
  respuesta honesta, no un fallo del sistema). Distinto de `None` (sin plan
  válido → degrada a camino corto, como siempre).
- Techo de nodos: prompt "2-5, hasta 8 si lo necesita";
  `_MAX_REASONABLE_NODES` 6→8.
- `TIE_TOOL_MAX_ITERS_WRITE=12` (config) + `runtime._iters_for()`: nodos con
  tools de construcción (filesystem/shell/powershell/git/browser/desktop/
  aithera/download) reciben el presupuesto ampliado; los de consulta, el base.

**Tests**: `tests/test_audit_s2_fixes.py` NUEVO (10: raw_text inviolable,
planner recibe el original y no el reescrito, etiquetas anti-contaminación +
orden objetivo<contexto, submit_mission sin re-clasificar, catálogo con
acciones en el prompt, cannot→PlanRejection, rechazo llega al usuario sin
ejecutar nada, techo 8, presupuesto write). Cero tests existentes rotos
(verificado: ninguno asertaba el techo viejo ni claves exactas del Intent).

## S2-extra — Aislamiento de memoria por proyecto ✅ EJECUTADA (2026-07-20, Fable 5)

Petición directa del usuario: trabaja en VARIOS videojuegos (y otros proyectos)
a la vez; la memoria de uno JAMÁS puede colarse en las misiones de otro. Antes
del fix, el enricher traía por similitud semántica recuerdos de cualquier
proyecto — dos juegos del mismo género se habrían mezclado.

**C-1b — aislamiento determinista de proyecto** (no confiado al LLM):
- `IMemoryStore.context()` + `MemoryRouter.context()` + `LocalMemoryStore.context()`
  ganan `project_id` (append-only, default None — mismo criterio que
  `TaskNode.gate_id`). Con project_id, todo item cuya metadata lleve un
  `project_id` DISTINTO se EXCLUYE; los items sin etiqueta (conocimiento
  general/preferencias) siempre entran. Post-filtro en Python (no `where` de
  Chroma) para que aplique a todos los tipos y a items indexados antes de que
  existiera la etiqueta (lección M3: los filtros de Chroma sobre strings ya
  mordieron).
- LECTURA: `enricher.enrich(project_id=…)` (con project_id en la clave de
  caché — dos proyectos no comparten contexto cacheado); el executor lo pasa
  desde `mission.project_id`; `_context_for`/`submit_mission` lo propagan;
  `chat_service` (`_mos_context_block`/`build_system_prompt`/`answer`) también.
- ESCRITURA: el toolloop etiqueta con `authority.project_id` toda memoria
  guardada dentro de una misión de proyecto (`memory.save_memory`) — la etiqueta
  que el filtro de lectura necesita se pone SIEMPRE, sin depender del LLM.

**Fix de entorno**: `pyproject.toml` de la raíz era el de CrewAI (resto ajeno,
como `crew.py`); sus `addopts` (`-n --timeout --dist --block-network`) exigían
plugins no instalados y ROMPÍAN `python -m pytest` — era EL motivo del error del
usuario. Sustituido por la config mínima real de Aithera.

**Tests**: 4 nuevos en `test_audit_s2_fixes.py` (contexto excluye otros
proyectos, sin project_id no filtra, enricher propaga+cachea por proyecto,
escritura queda etiquetada).

**✅ VERIFICADO EN EL SANDBOX contra el CÓDIGO REAL** (no reimplementado): el
entorno del usuario (Windows+Postgres+ChromaDB) no es replicable aquí, pero se
instalaron las deps ligeras (sqlalchemy/pydantic/pytest) y se ejercitó el
código real módulo a módulo con las deps pesadas (chromadb/torch) evitadas por
sus imports lazy:
- A-1 grounding contra `toolloop.run` REAL: answer sin tools → fallo honesto;
  con tool ejecutada → éxito. ✓
- A-2 contra `ApprovalGate` REAL + SQLite: pending→expired, resolve posterior
  no-op, expire pierde la carrera si ya se resolvió. ✓
- C-1b contra `LocalMemoryStore.context()` REAL: proyecto 1 no ve memoria del 2;
  sin project_id no filtra. ✓
- D-1 contra `permissions.py` REAL: catálogo 11, mapa de kinds, perfiles,
  fail-closed. ✓
- C-1 contra `contracts.py` REAL: raw_text presente/serializa/fallback. ✓
- B-1 contra `planner.py` REAL: techo=8, PlanRejection. #10 `events._inflight`. ✓
- 17/17 checks de lógica pura + import limpio de todos los módulos tocados.

**⚠️ Pendiente en la máquina del usuario**: `cd backend && python -m pytest
tests/ -v` (suite completa, ahora que el pyproject ya no la bloquea) +
verificación en vivo — la misión del videojuego debe ejecutar pasos reales o
rechazar honestamente, y una misión del juego A no debe traer nada del juego B.

---

## S3 — Browser: consent walls + aislamiento por misión ✅ EJECUTADA (2026-07-20, Fable 5)

Hallazgos: **A-3 + F-1**. Implementado (lo hizo Fable 5 en vez de delegarse: el
aislamiento tocaba el contrato `AgentTask`/toolloop, no solo la tool).

**A-3 — muros de consentimiento y estado real de la página**:
- `_dismiss_consent(page)`: 10 selectores de los CMP mayoritarios (OneTrust,
  Didomi, Quantcast/TCF, Google Funding Choices, formularios consent.google/
  youtube, Usercentrics, `#L2AGLb`) + variantes es/en de "Aceptar todo".
  Best-effort duro: timeout 1.2s por intento, máx 3 intentos, try/except por
  selector — si no hay muro (caso normal) el coste es ~0 y NUNCA rompe.
  Se ejecuta tras cada `goto`, **antes de reportar éxito**: llegar al muro no
  es llegar a la página.
- `_page_state(page, tab_id)`: `{tab_id, url, title, text_excerpt (500 chars
  del body visible), consent_dismissed}` — devuelto por `open_url`, `new_tab`
  y `google_search`. El modelo sabe dónde aterrizó SIN pagar otra llamada;
  antes solo veía url+status y no podía distinguir "estoy en el vídeo" de
  "estoy mirando un muro".

**F-1 — sesión de navegador por misión** (era una condición de carrera latente
con `ORCH_MAX_CONCURRENT=3`):
- El estado global `_pages`/`_current_tab` desaparece. Nace `_Session`
  (BrowserContext propio + sus pestañas + su pestaña activa) y
  `_sessions: dict[str, _Session]`. Cookies y pestañas aisladas por misión.
- Clave `"default"` cuando no hay misión (chat directo, tests) = comportamiento
  de siempre, cero regresión.
- `AgentTask.mission_id` (append-only) → `toolloop.run(session_key=…)` → el
  bucle inyecta `params["_session"]` SOLO para la tool `browser`. **Lo pone el
  código, no el modelo**: el LLM ni lo ve ni puede falsearlo (mismo criterio
  que el etiquetado de memoria de C-1b).
- `close_session(mission_id)` + `executor._release_mission_resources()` en
  `_finalize`: al terminar una misión (no si queda esperando) se libera su
  contexto. Sin esto cada misión con navegador dejaba un BrowserContext vivo
  hasta reiniciar el backend. Las tasks de limpieza se retienen en
  `_CLEANUP_TASKS` (misma lección que `events._inflight`, #10).

**Tests**: `tests/test_audit_s3_browser.py` NUEVO (10, sin red: dobles ligeros
de Page/Context/Browser) — muro cerrado y contenido real visible, sin muro no
hace nada, muro desconocido no rompe, page_state completo, 2 misiones = 2
contextos, misma misión reutiliza pestaña, sin sesión usa default, close_session
libera e idempotente, cerrar pestaña de A no toca B, el toolloop inyecta la
sesión. `test_new_tools.py`: fixture actualizada (`_pages`/`_current_tab` →
`_sessions.clear()`).

**✅ VERIFICADO CONTRA EL CÓDIGO REAL en el sandbox** (`browser_tool.py` y
`toolloop.py` reales, Chromium sustituido por dobles): los 6 escenarios de
A-3/F-1 + los 2 de integración TIE→browser, todos en verde.

**⚠️ Pendiente en la máquina del usuario**: verificación en vivo con Chromium
real — "abre youtube.com" debe devolver `title`/`text_excerpt` del contenido y
`consent_dismissed` con el selector que funcionó, no el muro.

---

## S4 — Suite de contratos de producto ✅ EJECUTADA (2026-07-20, Fable 5)

Hallazgo: **E-1**. `tests/test_product_contracts.py` NUEVO — **13 tests** que
validan COMPORTAMIENTO del producto en las costuras entre módulos, que es donde
vivían los 4 fallos que pasaron los 751 tests de módulo.

**Método**: UN solo fake (la frontera del LLM, `mel.complete`, enrutado por
`capability`). Todo lo demás REAL: ToolManager escribiendo en disco de verdad,
ApprovalGate contra la BD, permisos reales, executor/responder/tracer reales.
Sin red. Limpieza total (BD + disco) por test, antes Y después (lección de A4:
SQLite reutiliza ids y un residuo de otro archivo hace mentir al test).

**Los 8 contratos** (cada uno enuncia una promesa al usuario, no un detalle
de implementación):
1. **"Si digo que lo he hecho, lo he hecho"** — nodo con tools cuyo modelo
   responde sin usarlas → FAILED + disco intacto (protege A-1 a nivel de misión).
2. **"Lo que pido es lo que se planifica"** — el prompt del planner contiene mi
   texto literal y NO la reescritura del clasificador; el contexto de memoria
   va etiquetado como referencia y por debajo del objetivo (protege C-1).
3. **"Si te doy permiso de antemano, no me preguntas"** — perfil `full` → cero
   gates `pending` y rastro de lo autorizado; perfil `manual` → pregunta y NADA
   se ejecuta mientras espera (protege D-1 en ambos sentidos).
4. **"Una aprobación que no sirve para nada no se queda ahí"** — el timeout la
   deja `expired`, nunca `pending` (protege A-2).
5. **"Si te pido un archivo, el archivo existe"** — con permiso concedido, el
   archivo está en disco y el nodo es DONE; fuera de HOME es fallo auditado;
   **sin permiso el disco queda INTACTO** (protege B/A-1).
6. **"Si solo he hecho parte, te digo qué parte"** — 1 nodo DONE + 1 FAILED, lo
   que salió salió de verdad y el estado lo refleja.
7. **"Si te digo que pares, paras"** — kill-switch: el paso en vuelo no llega a
   escribir y el siguiente no se ejecuta.
8. **"Nunca te quedas sin respuesta"** — plan imposible de parsear → respuesta
   útil igualmente; objetivo fuera de capacidad → rechazo honesto que nombra lo
   que falta, sin ejecutar nada (protege B-1).

**Hallazgo REAL descubierto al escribir los tests** (el valor de S4 en acto):
`filesystem.write_file` exige confirmación, así que **sin el permiso
`filesystem.write` concedido una misión de archivos no escribe nada** — es el
comportamiento correcto, pero no estaba documentado ni cubierto. Se añadió como
contrato explícito (test propio + fixture `puede_escribir`), y explica en parte
el fallo B original: el usuario dijo "no me pidas permisos" pero el perfil no
cubría esa escritura.

**REGLA DE MANTENIMIENTO** (en el header del archivo): todo bug que llegue a
producción entra aquí como test que falla ANTES de arreglarse. Si un bug no se
puede expresar como contrato roto, es señal de que aún no se ha entendido qué
promesa rompió.

**✅ VERIFICADO CONTRA EL CÓDIGO REAL en el sandbox**: contratos 1, 4, 5 (a/b/c)
y 7 ejercitados de punta a punta con toolloop/ApprovalGate/FilesystemTool/
executor reales — incluido el kill-switch, que cortó un nodo de 30s en **0,04 s**
sin dejar nada escrito.

---

## Evoluciones documentadas (NO implementar ahora)

- **Pausa de toolloop como gate T3** (V1.1): persistir transcript del bucle en
  el checkpoint para que una aprobación tardía reanude el paso exacto. Requiere
  serializar el estado del bucle en `TaskNode` (append-only, campo `loop_state`).
- **Re-planning por nodo** (V1.1): un nodo fallido por presupuesto pide al
  planner subdividirse (`needs_decomposition` a nivel de nodo, simétrico al del
  decomposer).
- **snapshot_a11y en browser** (V1.1): accessibility tree de Playwright para que
  el modelo seleccione por rol/nombre en vez de CSS a ciegas.
- **Timeout global de misión** (V1.1): presupuesto de pared por misión con aviso
  al usuario (hoy solo hay timeouts por tool y por espera de permiso).
- **UI "completada parcialmente"** (V1.1, deuda doc 24 E-4): estado visual
  propio en Missions.tsx.
- **Playwright/Chromium en el instalador** (decisión de MVP-beta): incluir en
  NSIS (+~300MB) o descarga en primer arranque. SIN decidir — bloquea MVP-beta,
  no este plan.

---

## Estado

| Sesión | Hallazgos | Ejecutor | Estado |
|--------|-----------|----------|--------|
| S1 | A-1, A-2, D-1, #9, #10 | Fable 5 | ✅ código + verificado contra código real; suite completa+vivo en Windows |
| S2 | C-1, B-1 | Fable 5 | ✅ código + verificado contra código real; suite completa+vivo en Windows |
| S2-extra | C-1b aislamiento proyecto + fix pyproject | Fable 5 | ✅ código + verificado contra código real |
| S3 | A-3, F-1 | Fable 5 | ✅ código + verificado contra código real; vivo con Chromium pendiente |
| S4 | E-1 | Fable 5 | ✅ 13 contratos; verificado contra código real |

**BLOQUE DE CORRECCIÓN COMPLETO** — los 8 hallazgos bloqueantes de la auditoría
(doc 24) están tratados. Antes de declarar 1.0 queda, en la máquina del usuario:
1. `cd backend && python -m pytest tests/ -v` en verde (el `pyproject` de CrewAI
   que lo bloqueaba ya está corregido).
2. Verificación en vivo de los 3 escenarios de aceptación del §5 de doc 24:
   YouTube+canción, carpeta+archivos en el Escritorio, y misión compleja sin
   mutación de objetivo.
3. Decisión sobre Playwright/Chromium en el instalador (bloquea MVP-beta, no
   este bloque).
