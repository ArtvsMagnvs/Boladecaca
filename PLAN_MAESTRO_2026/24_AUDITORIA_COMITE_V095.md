# AUDITORÍA DEL COMITÉ INDEPENDIENTE — Aithera v0.9.5
### Pre-lanzamiento 1.0 · Ejecutada según PROMPT_08 · 2026-07-20

**Metodología aplicada**: lectura en profundidad de `tie/` (pipeline, toolloop,
executor, planner, intents, runtime, responder), `orchestrator/` (decomposer,
conductor, __init__), `automation/` (approval, permissions), `tools/`
(browser, filesystem, shell), `core/events.py`, más greps sistemáticos de
patrones de riesgo. Cada hallazgo referencia código real con línea o función.
Los 4 fallos de producción reportados (§3 del prompt) tienen causa raíz
identificada y confirmada en código.

---

## ENTREGA 1 — INFORME EJECUTIVO

**CTO**: No está listo. El sistema tiene una arquitectura seria y bien
documentada, pero el contrato más importante del producto — "lo que el usuario
pide es lo que se ejecuta, y lo que se reporta es lo que pasó" — está roto en
tres puntos independientes. Los 751 tests pasan porque testean los módulos; los
fallos ocurren en las COSTURAS entre módulos, donde no hay ni un solo test e2e
con tools reales.

**Principal Architect**: El problema más grave es el **cascade de reescritura
del objetivo** (hallazgo C-1): el texto del usuario pasa por 2-3 reescrituras
LLM (clasificador barato → decomposer → re-clasificación en submit_mission)
antes de llegar al planner, que además recibe memoria personal sin ninguna
instrucción de no mezclarla con el objetivo. La misión del videojuego que acabó
siendo "un MMORPG basado en tus novelas" no es un bug puntual: es el diseño
funcionando exactamente como está escrito.

**Experto IA/multiagente**: El toolloop acepta `{"answer": ...}` en la
iteración 1 sin haber ejecutado NINGUNA herramienta (hallazgo A-1). Para un
nodo tipo "execute", eso es una puerta abierta a la alucinación de éxito — el
mismo fallo de honestidad que R1 decía haber cerrado, reabierto por otra vía.

**Staff Performance**: El estado global del navegador (`_pages`,
`_current_tab` como globals de módulo en browser_tool.py:36-38) es una
condición de carrera real con `ORCH_MAX_CONCURRENT=3`: dos misiones paralelas
que usan browser comparten pestañas y se pisan el `_current_tab` (hallazgo
F-1). Nadie lo ha visto aún porque nadie ha ejecutado dos misiones browser a
la vez.

**Especialista UX**: El flujo de permisos con timeout de 120s (toolloop.py:220)
produce la peor experiencia posible: si el usuario tarda >2 min, la misión
CONTINÚA sin la acción, la aprobación queda huérfana en la UI, y cuando el
usuario la aprueba después NO PASA NADA (no hay ejecutor para
`tie_tool_permission`, approval.py). El usuario aprueba algo y el sistema lo
ignora. Eso destruye la confianza más rápido que cualquier crash.

**Ciberseguridad**: La base es sólida (whitelists deterministas, fail-closed,
DPAPI, frontera de autoridad R4 bien hecha). El riesgo no es una brecha — es
que el sistema de permisos tiene 3 `kind` fantasma (`tie.plan`, `tie.node`,
`tie.checkpoint`) que no existen en el catálogo, así que el modo autónomo
"full" NO cubre los gates del TIE (hallazgo D-1). El usuario cree que ha
delegado y el sistema le pregunta 6 veces. No es inseguro; es incoherente.

---

## ENTREGA 2 — HALLAZGOS CRÍTICOS

### [CRÍTICO] C-1 · El objetivo del usuario se reescribe hasta 3 veces por LLM antes de planificar

**Módulos**: `tie/intents.py:41`, `tie/pipeline.py:269,334,363`, `orchestrator/decomposer.py`
**Tipo**: Arquitectura

**Descripción**:
El prompt del clasificador ordena literalmente `"goal": el objetivo en una
frase imperativa y verificable (reformula el mensaje)` (intents.py:41). Ese
goal reescrito — por el modelo BARATO de la capability `classify`, que bajo la
política Economy es **llama3 8B local** — sustituye al texto del usuario en
todo el pipeline: `new_mission(goal=intent.goal or text)` (pipeline.py:334) y
`planner.plan(intent.goal or text, ...)` (pipeline.py:363). El texto original
del usuario NO llega nunca al planner.

Peor: `submit_mission` (pipeline.py:269) **vuelve a clasificar** el goal que ya
venía del decomposer, que a su vez ya reescribió los `objectives` del
clasificador. Cadena completa en una misión multi-encargo:
`texto usuario → classify (llama3) → decomposer (reason) → submit_mission → classify (llama3) OTRA VEZ → planner`.
Tres reescrituras, dos por modelo débil.

**Evidencia**:
El prompt del planner (planner.py:153-155) inyecta
`CONTEXTO (memoria de Aithera):\n{context}` — memoria personal del MOS
(`mem_personal` incluye el perfil del usuario destilado por `profile.py`, con
hechos como que escribe novelas de fantasía) — **sin una sola instrucción de
que el contexto no puede alterar el objetivo**. No existe ningún check de
fidelidad plan↔goal: `graph.validate()` valida DAG y tools, nunca contenido.
El fallo C reportado (Rey León/Godot → MMORPG/Open Tibia/novelas) es este
diseño ejecutándose: goal degradado por reescritura débil + memoria personal
presentada al planner al mismo nivel que el objetivo.

**Impacto en producción**:
Cualquier misión compleja puede mutar silenciosamente en otra distinta. El
usuario pierde el control sobre QUÉ hace el sistema — el fallo de confianza
más grave posible en un producto agéntico.

**Veredicto**: Rediseñar el flujo del goal.

**Acción concreta**:
1. El texto ORIGINAL del usuario viaja siempre junto al intent
   (`Intent.raw_text`, append-only) y es lo que recibe el planner como
   OBJETIVO. El `goal` del clasificador pasa a ser solo un resumen para UI.
2. `submit_mission` NO re-clasifica cuando el goal viene del decomposer
   (pasar el Intent ya construido, como ya hace `handle_stream` con el
   parámetro `intent` — el mecanismo existe, úsese aquí también).
3. Prompt del planner: bloque de contexto marcado como
   "REFERENCIA — nunca cambia ni amplía el OBJETIVO".
4. `capability="classify"` con goal-rewriting debe salir de llama3: o subir
   la capability del clasificador cuando `requires_planning=true`, o
   validar el goal reescrito contra el original (guard barato: longitud,
   entidades nombradas).

---

### [CRÍTICO] A-1 · El toolloop acepta una respuesta final sin haber ejecutado ninguna herramienta

**Módulos**: `tie/toolloop.py:303-307`, `tie/executor.py:236-246`
**Tipo**: Fiabilidad

**Descripción**:
En `toolloop.run()`, si el modelo responde `{"answer": "..."}` en la primera
iteración, se devuelve `ok=True` con cero tool_calls. La validación del
executor (`_validate_result`) solo comprueba `success` + "hay salida con
forma". Resultado: un nodo cuyo goal es "abre YouTube y reproduce X" puede
terminar DONE con un answer inventado y **cero herramientas ejecutadas** — el
mismo fallo de honestidad que R1 documentó y cerró para `metadata.tool_call`,
reabierto por la vía del answer temprano.

**Evidencia**:
toolloop.py:303: `if "answer" in data: return ToolLoopResult(ok=bool(answer), ...)` —
sin comprobar `len(tool_calls) > 0` ni que alguna llamada tuviera `ok=True`.
Combinado con browser_tool donde `open_url` devuelve success al
`domcontentloaded` (browser_tool.py:170) — cargar el muro de cookies de
YouTube ES un success — el fallo A completo queda explicado: página cargada
(success técnico) + answer del modelo (éxito declarado) + validación de forma
(pasa) = misión "completada" sin canción.

**Impacto en producción**:
Toda misión con tools puede reportar éxito falso. Frecuencia: alta con
modelos débiles, no nula con modelos fuertes.

**Veredicto**: Reparar (bug concreto, no rediseño).

**Acción concreta**:
En `toolloop.run()`: si el catálogo no está vacío y `tool_calls` no contiene
al menos UNA ejecución con `ok=True`, un `{"answer"}` en iteración <
`max_iters` se rechaza con feedback ("no has usado ninguna herramienta;
obtén los datos antes de responder"). En la última iteración, si no hubo
tools, devolver `ok=False` con el answer como `error` informativo — nunca
como éxito.

---

### [CRÍTICO] D-1 · El modo autónomo no cubre los gates del TIE: 3 `kind` fantasma

**Módulos**: `automation/permissions.py:44-94`, `tie/pipeline.py:486`, `tie/executor.py:261,290`
**Tipo**: Seguridad/UX

**Descripción**:
`request_approval` auto-resuelve si `is_pre_authorized(kind)` (approval.py:121).
Pero los gates del TIE usan `kind="tie.plan"` (pipeline.py:486),
`kind="tie.node"` (executor.py:261) y `kind="tie.checkpoint"`
(executor.py:290) — **ninguno existe en el CATALOG de permissions.py**. Como
`is_pre_authorized` es fail-closed, el perfil "full" con los 9 permisos
activados NO tiene ningún efecto sobre estos tres gates: el plan sensible
pregunta siempre, cada checkpoint pregunta "¿Sigo con el resto?" siempre.

**Evidencia**:
El CATALOG tiene 9 ids (email.send … computer.use). Grep de `kind=` en tie/:
`tie.plan`, `tie.node`, `tie.checkpoint`, `tool.<tool>.<action>` — solo el
último se traduce (vía `_TOOL_PERMISSION`, el fix del 2026-07-19). Los otros
tres quedaron fuera del fix. La misión del videojuego con `checkpoint: true`
en cada entregable + gate del plan = los 5-6 permisos que el usuario reportó
**con el perfil full activo**. Además, la instrucción en el propio prompt
("NO TIENES QUE PEDIRME PERMISOS") no se parsea en ningún sitio — no hay
mecanismo para que el usuario module permisos desde el mensaje.

**Impacto en producción**:
El selector de autonomía de Ajustes es parcialmente decorativo. El usuario
pierde la confianza en la configuración ("lo activé y no hace nada").

**Veredicto**: Reparar.

**Acción concreta**:
1. Añadir al CATALOG: `tie.plan_approval` ("Ejecutar planes sin
   confirmación", risk=high) y `tie.checkpoint` ("Continuar tras cada
   entregable sin preguntar", risk=low).
2. Mapear: gate del plan → `tie.plan_approval`; checkpoint →
   `tie.checkpoint`; gate de nodo → el permiso de la tool dominante del
   nodo, o `tie.plan_approval` como paraguas.
3. El perfil "full" los incluye → autonomía real de punta a punta con
   rastro de auditoría (la regla de oro de A3b se mantiene intacta).

---

### [CRÍTICO] A-2 · Aprobaciones huérfanas: el usuario aprueba y no pasa nada

**Módulos**: `tie/toolloop.py:194-223`, `automation/approval.py`
**Tipo**: UX/Fiabilidad

**Descripción**:
`_ask_permission` espera `approval_wait_s=120` segundos. Si el usuario no
responde a tiempo, el bucle **continúa sin la acción** y la aprobación "queda
visible en Aithera para que la apruebe cuando quiera" (toolloop.py:222). Pero
aprobarla después NO hace nada: el `action_type="tie_tool_permission"` no
tiene ejecutor registrado **a propósito** (toolloop.py:204-206), y la misión
ya siguió adelante. La UI muestra una aprobación pendiente que es un cadáver
funcional.

**Evidencia**:
toolloop.py:220-223 devuelve el timeout como denegación blanda; el comentario
del propio código admite que la solicitud "sigue pendiente en la UI". No
existe ningún mecanismo de reanudación ligado a esa aprobación tardía (a
diferencia de los gates de nodo de T3, que sí reanudan por evento).

**Impacto en producción**:
Exactamente lo que el usuario reportó en el fallo A: "si tardo mucho rato se
bloquea o algo". La misión degrada, y su aprobación posterior es ignorada.

**Veredicto**: Reparar con decisión de diseño explícita.

**Acción concreta**:
Elegir UNA de dos semánticas y aplicarla con consistencia:
(a) el timeout PAUSA el nodo como gate de T3 (estado `waiting_approval`,
reanudación por evento — el mecanismo ya existe y está probado), o
(b) el timeout CANCELA la aprobación (se marca `expired`, desaparece de la
UI, el modelo busca otra vía). La actual mezcla — seguir sin la acción PERO
dejar la aprobación viva — es la peor combinación posible.

---

### [ALTO] A-3 · browser_tool no gestiona muros de consentimiento ni overlays

**Módulos**: `tools/browser_tool.py` (completo)
**Tipo**: Fiabilidad

**Descripción**:
Grep de `cookie|consent|popup|overlay|dialog|accept` en browser_tool.py:
**cero resultados**. `open_url` reporta éxito en `domcontentloaded` — en
YouTube/Google eso es el muro de cookies, no el contenido. El modelo después
intenta `click` por selector CSS sobre un DOM que solo conoce por `get_text`
(sin visión, sin accesibility tree), con el overlay bloqueando todo.

**Impacto en producción**:
Prácticamente cualquier misión browser sobre sitios comerciales europeos
(consent walls por GDPR) falla o degenera en reintentos. Es el caso de uso
nº1 de un asistente ("ponme música", "búscame X").

**Veredicto**: Refactorizar la tool.

**Acción concreta**:
1. Tras `goto`, detección heurística de consent walls (selectores conocidos
   de los CMPs mayoritarios: OneTrust, Didomi, Google consent) + click
   automático en "aceptar" — o inyección de cookies de consentimiento
   pre-hechas para dominios frecuentes.
2. `open_url` devuelve además `page_state` (title + un extracto del texto
   visible) para que el modelo sepa DÓNDE está sin otra llamada.
3. Medio plazo: acción `snapshot_a11y` (accessibility tree de Playwright) —
   el modelo elige elementos por rol/nombre en vez de adivinar CSS.

---

### [ALTO] B-1 · Techo estructural: misiones grandes en grafos de 4 nodos × 5 iteraciones

**Módulos**: `tie/planner.py:35`, `core/config.py:67` (`TIE_TOOL_MAX_ITERS=5`)
**Tipo**: Arquitectura

**Descripción**:
El planner fuerza 2-3 nodos (máx 4-6) y cada nodo tiene 5 iteraciones de
toolloop con timeout de 60s por tool. La misión del videojuego (carpeta +
venv + investigar + diseñar MVP + implementar + documentar) necesita decenas
de acciones de escritura — no cabe físicamente en el presupuesto. Además el
shell tiene whitelist (python/pip/git/npm/node/npx/uvicorn) que no incluye
godot ni permite instalarlo, y el planner NO conoce las acciones ni límites
de las tools (solo sus nombres, planner.py:57) — así que promete pasos que
la ejecución no puede cumplir.

**Evidencia**:
El resultado real reportado: "abrió una web de Godot y preparó el plan, nada
más" — los nodos de escritura agotaron iteraciones entre denegaciones,
permisos y limitaciones, y la misión terminó con lo único que cabía.

**Impacto en producción**:
Toda misión de tamaño "proyecto" (crear algo con múltiples archivos) fallará
o entregará una fracción. El usuario no puede saber de antemano qué tamaño
de encargo es viable.

**Veredicto**: Rediseño acotado (no del TIE — de su presupuesto y su honestidad).

**Acción concreta**:
1. El planner recibe el catálogo REAL de acciones (no solo nombres de tools)
   y una instrucción de rechazar honestamente objetivos que exceden la
   capacidad ("esto necesitaría X que no tengo") — decir "no puedo" es
   producto premium; fingir que sí y entregar nada, no.
2. Presupuesto dinámico: `max_iters` escalado por tipo de nodo (un nodo
   "implementar" necesita más que un nodo "consultar").
3. V1.1: re-planning — un nodo fallido por presupuesto puede pedir al
   planner subdividirse (el diseño de `needs_decomposition` del decomposer
   ya apunta ahí; hoy solo existe a nivel de objetivo, no de nodo).

---

### [ALTO] F-1 · Estado global del navegador compartido entre misiones concurrentes

**Módulos**: `tools/browser_tool.py:36-38`
**Tipo**: Fiabilidad (condición de carrera)

**Descripción**:
`_pages: Dict[str, Any]` y `_current_tab` son globals de módulo. Con
`ORCH_MAX_CONCURRENT=3`, dos misiones paralelas que usan browser comparten el
diccionario de pestañas y SE PISAN el `_current_tab`: la misión A navega, la
misión B hace click — en la pestaña de A. Ninguna traza lo reflejará
correctamente.

**Impacto en producción**:
Corrupción cruzada de misiones browser concurrentes. Hoy latente (nadie
lanza 2 misiones browser a la vez); explotará en cuanto el Orquestador haga
exactamente lo que se diseñó para hacer.

**Veredicto**: Reparar antes de 1.0.

**Acción concreta**:
Contexto de navegador POR MISIÓN (Playwright `browser.new_context()` por
mission_id, pestañas dentro del contexto propio) o, mínimo viable, un
`asyncio.Lock` global que serialice el uso del browser entre misiones con
mensaje claro de "el navegador está ocupado por otra misión".

---

### [ALTO] E-1 · Los tests validan módulos; ninguno valida el producto

**Módulos**: `backend/tests/` (751 tests)
**Tipo**: Tests

**Descripción**:
Los 4 fallos de producción pasaron TODA la suite. Patrón común: cada test
mockea la frontera adyacente (LLM fake, tool fake, gate fake). No existe:
- un test donde el toolloop reciba un answer sin tool_calls y deba rechazarlo
- un test de fidelidad plan↔goal (que el plan trate del objetivo pedido)
- un test de browser contra una página con overlay
- un test del perfil "full" contra los gates del TIE (tie.plan/checkpoint)
- un test e2e de misión con una tool REAL (filesystem sobre tmpdir bastaría)

**Veredicto**: Añadir la capa que falta (no rehacer la existente, que es buena
en lo suyo).

**Acción concreta**:
Suite `test_product_contracts.py`: 8-10 tests e2e con el LLM como único fake
(patrón ya usado en `test_tie_e2e.py` — extenderlo con tools reales sobre
tmpdir y los casos de arriba). Cada bug de producción nuevo entra aquí como
test de regresión ANTES de arreglarse.

---

## ENTREGA 3 — PLAN DE ACCIÓN PRIORIZADO

| # | Sev | Módulo | Problema | ¿Bloquea 1.0? | Esfuerzo | Depende de |
|---|-----|--------|----------|---------------|----------|------------|
| 1 | CRÍT | toolloop | A-1 answer sin tools = éxito falso | SÍ | 2-3 h | — |
| 2 | CRÍT | permissions | D-1 kinds fantasma del TIE | SÍ | 3-4 h | — |
| 3 | CRÍT | pipeline/intents | C-1 cascade de reescritura del goal | SÍ | 1-2 días | — |
| 4 | CRÍT | toolloop/approval | A-2 aprobaciones huérfanas post-timeout | SÍ | 1 día | decidir semántica |
| 5 | ALTO | browser_tool | A-3 consent walls + page_state | SÍ | 1-2 días | — |
| 6 | ALTO | browser_tool | F-1 estado global compartido | SÍ | 4-6 h | — |
| 7 | ALTO | planner/config | B-1 techo estructural + catálogo real al planner | SÍ (parte 1) | 1 día | #3 |
| 8 | ALTO | tests | E-1 suite de contratos de producto | SÍ | 2 días | #1-#6 |
| 9 | MEDIO | app/desktop.py | Código muerto Tkinter (1207 líneas, 11× `except:pass`) | No | 15 min | — |
| 10 | MEDIO | core/events.py | Referencias de tasks no retenidas en emit() | No | 1 h | — |

Total estimado del bloque bloqueante (#1-#8): **7-9 días de trabajo enfocado.**
Orden recomendado: 1 → 2 → 4 → 6 (fixes quirúrgicos) → 3 → 7 (rediseño del
flujo del goal) → 5 (browser) → 8 (blindaje). 

---

## ENTREGA 4 — DEUDA TÉCNICA PARA 1.1 (no bloquea 1.0)

**`app/desktop.py`** — 1207 líneas de la app CustomTkinter legacy con 11
`except: pass`. Sin imports entrantes (confirmado por grep): borrar. Es la
deuda #8 de CLAUDE.md §16, declarada "localizar y eliminar antes de V1.0" y
aún presente.

**`core/events.py:emit()`** — `loop.create_task(...)` sin retener referencia:
el GC puede cancelar tasks en vuelo (footgun documentado de asyncio). Guardar
en un set con discard callback.

**Planner sin conocimiento de acciones** — solo ve nombres de tools; debería
ver el catálogo de acciones con sus flags (cubierto parcialmente por #7).

**`submit_mission` clasifica dos veces en flujo orquestado** — coste extra de
latencia además del problema de fidelidad (se resuelve con #3).

**Sin timeout global de misión** — un nodo puede consumir 5×60s de tools +
LLM; una misión de 4 nodos puede vivir >20 min sin límite superior definido
ni aviso al usuario.

**`Missions.tsx` no distingue "completada parcialmente"** — una misión con 2
DONE + 1 FAILED muestra el mismo estado terminal que una perfecta; el
responder sí lo cuenta en texto, la UI no lo refleja estructuralmente.

**Instalador y Playwright** — `playwright install chromium` (~300MB) no está
resuelto para el MVP-beta: decidir si el instalador NSIS lo incluye o lo
descarga en el primer arranque (afecta directamente al caso de uso nº1).

---

## ENTREGA 5 — VEREDICTO FINAL

**¿Está Aithera listo para lanzarse como producto 1.0 de pago? NO — pero está
a una distancia corta y bien definida.**

La arquitectura de fondo es sólida y mejor que la de muchos productos
lanzados: contratos congelados, checkpoint en disco, gates HITL persistentes,
frontera de autoridad determinista, disciplina modular vigilada por tests, y
una honestidad de ingeniería inusual (los comentarios del código documentan
sus propios bugs pasados). Ninguno de los subsistemas necesita rehacerse.

Lo que está roto es el **contrato de confianza con el usuario**, en tres
formas: el sistema puede ejecutar algo distinto de lo pedido (C-1), puede
reportar éxito sin haber hecho nada (A-1 + A-3), y puede ignorar la
configuración de autonomía y después ignorar también las aprobaciones del
usuario (D-1 + A-2). Cualquiera de las tres, sufrida en la primera semana,
mata el producto — y las tres se disparan con los casos de uso más básicos.

**Condiciones no negociables para el "sí"**:
1. Fixes #1-#8 del plan de acción aplicados y verificados EN VIVO (no solo
   en tests) con los tres escenarios reportados como casos de aceptación:
   YouTube+canción, carpeta+proyecto en el Escritorio, y misión compleja sin
   mutación de objetivo.
2. La suite de contratos de producto (E-1) en verde y establecida como
   requisito de cierre para todo bloque futuro.
3. Decisión tomada y documentada sobre Playwright/Chromium en el instalador.

Con el ritmo demostrado en los bloques anteriores (T1-T5, E1-E2b, R1-R7),
esto es **1-2 semanas de trabajo**. La recomendación del comité es unánime:
hacer este bloque ANTES del MVP-beta, no después — empaquetar los fallos
actuales en un instalador solo los distribuye más rápido.

---
*Comité: CTO · Principal Architect · IA/Multiagente · Performance · UX · Ciberseguridad.*
*Todo hallazgo referencia código real verificado. Los greps y lecturas son
reproducibles con los comandos del PROMPT_08 §4.*
