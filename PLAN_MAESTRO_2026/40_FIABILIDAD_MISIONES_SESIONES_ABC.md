# 40 — Fiabilidad de misiones largas: Sesiones A·B·C (diseño ejecutable)

> **Origen** (2026-08-04): fallos repetidos del encargo real "lee el GDD de
> Cordyceps, investiga en la web y escribe `CORDYCEPS_PLAN_2026.md`" — muro de
> 12 iteraciones, búsqueda web sin configurar quemando el presupuesto, misión
> en espera mostrada como completada, y una afirmación falsa de "he escrito el
> archivo" sin archivo. Diagnóstico completo en la conversación del 2026-08-04;
> mandato del usuario: **arreglos de raíz, no parches, sin que arreglar una
> cosa estropee otra — cualquier tipo de tarea tiene que funcionar**.
>
> **Principio rector** (modelo Claude Code / Claude Cowork): el límite de un
> bucle de trabajo es *"¿sigo progresando?"*, nunca *"¿cuántos pasos llevo?"*.
> Un bucle que avanza puede dar 60 pasos; uno atascado se corta al 4º. Todo lo
> de este doc son consecuencias de ese principio.
>
> **Reparto de modelos** (regla doc 27 §2): Sesión A = Fable 5 (contrato nuevo
> del bucle). Sesión B = Opus (grounding sobre patrón existente S2·S6/NEW-7).
> Sesión C = Sonnet (mecánico: logging + script).
>
> **Regla para B y C**: este doc deja el diseño CERRADO — archivo, función,
> cambio exacto, tests y mutaciones. El modelo que ejecute NO decide diseño;
> implementa y verifica. Si el código real contradice algo de aquí (patrón
> LOG-1: los docs envejecen), se documenta la desviación en el cierre, nunca
> se improvisa un diseño alternativo en silencio.

---

## Sesión A — ✅ EJECUTADA (2026-08-04, Fable 5)

Presupuesto por progreso + preflight de tools. Detalle del cierre en
CLAUDE.md §28. Resumen de lo que B y C pueden dar por existente:

- `settings.TIE_TOOL_HARD_CEILING` (60) y `settings.TIE_TOOL_STALL_LIMIT` (4)
  sustituyen a `TIE_TOOL_MAX_ITERS`/`TIE_TOOL_MAX_ITERS_WRITE` (retirados).
- `runtime._iters_for()` devuelve SIEMPRE el techo duro; el corte efectivo es
  el detector de atasco de `toolloop.run` (`_traba`/`_avanza`): N vueltas
  consecutivas sin una tool ejecutada con éxito → si hubo trabajo real previo,
  UNA última vuelta de cierre honesto ("ATASCO CONFIRMADO … responde AHORA
  contando lo que SÍ conseguiste"); si no, `ToolLoopResult(ok=False,
  error="detenido por falta de progreso: …")`.
- PREFLIGHT: `toolloop.run` consulta `tool.preflight() -> Optional[str]`
  (duck-typed, opcional) antes del bucle; una tool inoperativa se EXCLUYE del
  catálogo, entra en `limitations` desde el arranque, y el modelo ve el
  "AVISO PREVIO" en la cabecera del transcript. Si TODAS las tools del paso
  están inoperativas → fallo honesto inmediato con el motivo, 0 llamadas LLM.
  `SearchTool.preflight()` implementado (sin API key → motivo con "Ajustes →
  Búsqueda web"). Eventos de telemetría nuevos: `stalled`,
  `preflight_not_ready` (stage "toolloop").
- Tests: `tests/test_toolloop_progreso.py` (9). Actualizados al contrato
  nuevo: `test_audit_s2_fixes.py::test_b1_todo_nodo_recibe_el_techo_duro_unico`
  y `test_lectura_paginada.py::test_document_tiene_presupuesto_para_varias_
  lecturas`.

---

## Sesión B — ✅ EJECUTADA (2026-08-04) — Desenlaces honestos

**Cierre real** (detalle en CLAUDE.md §28). Desviaciones y hallazgos respecto
al diseño de abajo, para que quede constancia:

- **B4 no necesitó código**: `_template_failure` YA incluía `n.error` de cada
  nodo fallido, y la clave i18n `responder.failed_with_reasons` ya renderiza
  `{reasons}` en los 4 idiomas. Se fijó con dos tests (el motivo de preflight y
  el de atasco de la Sesión A llegan enteros al usuario) en vez de tocar nada.
- **B5, hallazgo real**: `Missions.tsx` solo correlacionaba
  `tie_tool_permission` — el gate de CONCESIÓN de S11 (`tie_tool_grant`) se
  quedó fuera cuando se escribió S7·S8, así que un gate de concesión no tenía
  botones NI en Misiones NI en el chat de agente. Corregido en los dos sitios
  desde el mismo sitio: `usePendingQuestions` pasa a devolver también `gates`
  (los dos action_types de gate en vuelo) y `Missions.tsx` amplía su `find`.
- **B2 detalle de implementación**: `claimed_written_files` ignora el contenido
  de los bloques ``` (`_strip_code_fences`) — un ejemplo de código con
  `open("x.md","w")` no es una afirmación de entregable. 14 de los 26 tests
  son negativos por el riesgo de ruido.

Diseño original (implementado tal cual salvo lo anotado arriba):

### Sesión B — diseño (Opus, esfuerzo alto)

**Los tres fallos que cierra**: (1) "Done — I wrote CORDYCEPS_PLAN_2026.md"
con el archivo SIN existir (fabricación de entregable en la síntesis de
misión — la capa que S2·S6/NEW-7 NO cubrieron: cubren el camino corto y el
responder por VERBOS, pero una afirmación "el plan está en PLAN.md" sin verbo
delator y con nodos DONE de por medio cuela); (2) el motivo real de un
fallo/atasco/preflight no siempre llega ENTERO a la respuesta final; (3)
verificación de que los gates de una misión lanzada desde el chat de agente
son visibles ahí (mecanismo ya existente — `usePendingQuestions.ts` +
`OrchestratorChat.tsx` — se verifica y se cierran huecos, no se construye).

**Regla de no-regresión de toda la sesión**: nada de esto añade fricción a
una misión que dice la verdad. Solo se descarta/reescribe texto cuando afirma
un entregable que NINGUNA escritura exitosa respalda. Una misión sin
escrituras que no afirma haber escrito pasa idéntica; una con escrituras
reales pasa idéntica.

### B1 — El toolloop registra el OBJETIVO de cada escritura exitosa

**Archivo**: `app/tie/toolloop.py`.

**Cambio**: constante de módulo nueva junto a `_CONTENT_ACTIONS`:

```python
# [Sesión B] Acciones que CREAN un entregable en disco con ruta explícita.
# El toolloop registra la ruta en tool_calls para que el responder pueda
# verificar que un entregable AFIRMADO tiene una escritura real detrás.
_DELIVERABLE_ACTIONS = frozenset({
    ("filesystem", "write_file"),
    ("document", "write_docx"), ("document", "write_xlsx"),
    ("download", "download_url"),
})
```

En la rama de ejecución exitosa (donde hoy se hace
`tool_calls.append({"tool_id": …, "action": …, "ok": …, "error": …})`,
~línea 1062): si `(tool_id, action) in _DELIVERABLE_ACTIONS`, añadir al dict
la clave `"target"` con `params.get("path") or params.get("file_path") or
params.get("dest") or ""` (recortada a 300 chars). APPEND-ONLY: nadie
existente lee `"target"`, cero regresión. El campo viaja gratis hasta
`node.tool_calls` (executor.py:353 ya copia la lista entera).

### B2 — `grounding.claimed_written_files()` (función pura, 0 LLM)

**Archivo**: `app/core/grounding.py` (la capa compartida — el responder y
cualquier capa futura la consumen; mismo criterio que S2·S6).

**Función nueva**:

```python
def claimed_written_files(text: str) -> list[str]:
```

Detecta nombres de archivo que el texto AFIRMA haber creado/escrito/guardado.
Diseño (calcado del estilo de `presents_unverifiable_evidence`):

- Regex de verbo de creación en pasado, ES+EN, ventana de ~80 chars hasta un
  nombre de archivo con extensión (reusar `_EVIDENCE_EXTENSIONS` ya existente
  para la lista de extensiones):
  `(?:he (?:creado|escrito|guardado|generado)|(?:queda|está) (?:guardado|escrito|creado)|(?:creado|escrito|guardado|generado) (?:el archivo|el documento|en)|i (?:created|wrote|saved|generated)|saved (?:to|as)|written to)`
  … seguido en esa ventana de `[\w\-./\\]+\.(ext)`.
- Devuelve los nombres BASE (sin ruta), en minúsculas, sin duplicados.
- **Negativos obligatorios** (el riesgo es el ruido, como en NEW-7): "voy a
  crear plan.md" (futuro — no afirma hecho), "¿quieres que guarde esto en
  notas.md?" (pregunta), "el archivo GDD.docx dice…" (lectura, no creación),
  un bloque de código que contiene `open("x.md", "w")` (código de ejemplo —
  excluir coincidencias dentro de fences ``` reutilizando `_CODE_FENCE`).

### B3 — El responder verifica el entregable antes de firmar la síntesis

**Archivo**: `app/tie/responder.py`.

**Cambio en `_synthesize`** (~línea 104, donde hoy está
`if text and _is_grounded(text, graph):`): segunda condición encadenada, misma
mecánica de descarte:

```python
if text and _is_grounded(text, graph) and _deliverables_backed(text, done):
    return text
```

**Función nueva `_deliverables_backed(text, done) -> bool`**:

1. `afirmados = grounding.claimed_written_files(text)`; si está vacío → True
   (la inmensa mayoría de misiones: cero coste).
2. `escritos = {basename(c["target"]).lower() for n in done
   for c in (n.tool_calls or []) if c.get("ok") and c.get("target")}`
   (usar `os.path.basename` sobre `str.replace("\\", "/")` para rutas
   Windows).
3. Para cada afirmado que NO esté en `escritos` → False (se descarta la
   síntesis del LLM y sale `_template_success`, que solo enumera los outputs
   reales de los nodos — la misma degradación que ya usa `_is_grounded`).
4. **Verificación de disco best-effort**: para los afirmados que SÍ casan,
   si el `target` registrado es ruta absoluta, `os.path.exists(target)`
   dentro de try/except; si NO existe → False también (el contrato de
   producto nº 5: "si te pido un archivo, el archivo existe"). Un error del
   chequeo (permisos, ruta rara) NUNCA descarta — en la duda, se acepta.

Añadir logger.info cuando se descarta, con los nombres afirmados vs escritos
(diagnóstico; nunca el contenido).

### B4 — El motivo real del fallo llega ENTERO a la respuesta final

**Archivo**: `app/tie/responder.py::_template_failure` (~línea 180).

**Verificar primero** (leer la función real): que el error de los nodos
FAILED se incluye en el texto. Si hoy solo dice "el paso X falló" sin el
`node.error`, extender: primera línea del error de cada nodo fallido
(recortada a 200 chars). Los mensajes de la Sesión A están diseñados para ser
mostrados tal cual: "detenido por falta de progreso: … Último obstáculo: …" y
"las herramientas de este paso no están operativas: search: la búsqueda web
no está configurada: añade una API key … en Ajustes → Búsqueda web". El
usuario tiene que leer ESO, no un genérico.

### B5 — Gate visible en el chat del agente (verificación + cierre de huecos)

**Archivos**: `frontend/src/hooks/usePendingQuestions.ts`,
`frontend/src/pages/Workspace/OrchestratorChat.tsx`.

**Qué verificar** (no construir de cero — ya existe la mitad): que el panel
de preguntas/aprobaciones pendientes del chat de agente muestra TODOS los
kinds que el toolloop puede abrir — `tool.<id>.<action>`
(action_type `tie_tool_permission`), `tool.grant.<id>` (`tie_tool_grant`) y
`user_question` — filtrados por el `mission_id` de la ejecución del agente
(el gate lleva `mission_id` en `action_payload` desde S7·S8, y el endpoint
`GET /api/automation/approvals` lo expone como campo propio). Si algún kind
no pasa el filtro actual, añadirlo al MISMO filtro — sin panel nuevo, sin
endpoint nuevo. Mientras haya un gate pendiente, el estado del chat debe
decir "esperando tu respuesta", nunca "escribiendo…" indefinido.

### Tests de la Sesión B — `tests/test_entregables_honestos.py` (NUEVO)

1. `claimed_written_files`: ≥6 positivos ES/EN (incl. la frase real del fallo:
   "He escrito CORDYCEPS_PLAN_2026.md con el plan completo") y ≥6 negativos
   (futuro, pregunta, lectura, código en fence, mención suelta, lista de
   archivos leídos).
2. Toolloop registra `target` en una escritura exitosa y NO en una lectura
   (fake TM, patrón `test_toolloop_progreso._FakeTM`).
3. Responder REAL (mock solo del LLM, patrón `test_audit_s2s6_grounding`):
   grafo con nodo DONE sin escrituras + síntesis del LLM afirmando
   "He creado PLAN.md" → el texto del LLM se DESCARTA (sale plantilla, sin la
   afirmación).
4. Mismo grafo pero con `tool_calls` incluyendo
   `{"ok": True, "target": "C:/x/PLAN.md"}` y el archivo real en `tmp_path` →
   la síntesis del LLM se ACEPTA tal cual.
5. Target registrado pero archivo BORRADO del disco → se descarta (contrato
   "el archivo existe").
6. No-regresión: síntesis sin ninguna afirmación de archivo pasa idéntica
   (byte a byte) con y sin el chequeo.
7. `_template_failure` incluye el error de la Sesión A ("falta de progreso" /
   "no están operativas") cuando el nodo falló por eso.

**Mutaciones obligatorias** (aplicar, ver fallar, restaurar byte a byte con
`cmp`): (a) quitar `_deliverables_backed` de la condición → caen 3 y 5;
(b) quitar el registro de `target` en toolloop → cae 2 (y 4 pasa a descartar);
(c) forzar `claimed_written_files` a lista vacía → caen los positivos de 1 y
el 3.

**Regresión mínima**: `test_audit_s2s6_grounding.py`,
`test_audit_new7_fabricacion.py`, `test_tie_e2e.py`, `test_tie_handle.py`,
`test_toolloop_progreso.py`, `test_product_contracts.py`,
`test_module_boundaries.py` — todos en verde, cero debilitados.

**NO tocar en B**: el camino corto del chat (ya cubierto por NEW-7), el
consolidator (ya determinista), `_is_grounded` existente, ningún timeout,
ningún gate del backend.

---

## Sesión C — ✅ EJECUTADA (2026-08-05, Sonnet) — Observabilidad que sobrevive

**Cierre real** (detalle también en CLAUDE.md §28). Implementado tal cual el
diseño de abajo, sin desviaciones de fondo — dos matices de implementación:

- **C3, `_collect_config_health`**: en vez de leer `google_credentials` como
  clave suelta de `Config` (que no existe con ese nombre), se usa
  `app.integrations.google_auth.is_connected()` — la función que YA existe y
  YA es la fuente de verdad de "¿Google está conectado?" (token en
  `%APPDATA%/Aithera/google_token.json`, no en la tabla `Config`). Mismo
  criterio que el resto del script: reusar, no reinventar.
- **`ai_providers.is_configured`**: se simplificó a `True` siempre que exista
  la fila en `ai_provider_configs` — es EXACTAMENTE el criterio real de
  `ai_manager.py` (`row is not None or provider in NO_KEY_PROVIDERS`; si hay
  fila, ya está configurado, cubre también a Claude Code/Codex que no llevan
  `api_key`).

Tests: `tests/test_observabilidad.py` (NUEVO, 11 — AITHERA_LOG_DIR respetado
vía subproceso + confirmado en el propio proceso de test, rollover bloqueado
NO trunca y desvía a un hermano con timestamp, prune acotado a `keep` sin
tocar archivos ajenos, prune nunca lanza con directorio roto, y 6 sobre
`aithera_doctor.collect()` con una BD sembrada: ve las misiones con su
`waiting_with_gate` correcto, cuenta el `stalled` de la Sesión A y el fallo de
tool con su detalle, las aprobaciones pendientes traen el `mission_id` real,
`config_health` no revienta sin ninguna key configurada, `check_schema_drift`
no revienta, y el doctor JAMÁS escribe — recuento de filas idéntico antes y
después de `collect()` sobre las 3 tablas que toca).

**Mutaciones obligatorias** (aplicadas, verificado el fallo, restauradas y
confirmadas byte a byte con `cmp`): (a) revertir el `except PermissionError`
al truncado viejo → cae `test_rollover_bloqueado_no_trunca`; (b) quitar la
lectura de `AITHERA_LOG_DIR` → caen los 2 tests de C1.

**Regresión**: 29 passed (`test_observabilidad.py` + `test_smoke.py` +
`test_startup_time.py` + `test_module_boundaries.py`) + 202 passed (todo
`test_tie_*.py` + Sesión A/B) + 285 passed/6 skipped (`test_automation*.py` +
`test_orchestrator*.py` + `test_agent_execution.py` + `test_agent_prompt.py` +
`test_audit_s*.py` + `test_module_boundaries.py` + `test_product_contracts.py`)
— **516 passed, 6 skipped, 0 failed** en el subconjunto ejercitado (sandbox).
El único fallo visto en una pasada más amplia de `tests/` (`test_action_intent.
py::test_el_detector_cubre_todas_las_acciones_del_catalogo`, sobre
`search_skills`) es **preexistente y ajeno** — no toca `logging_config.py`,
`conftest.py` ni ningún archivo nuevo de esta sesión (confirmado por grep: cero
referencias cruzadas).

**Pendiente en Windows**: `python scripts/aithera_doctor.py` contra el
Postgres real, con el backend APAGADO — debe imprimir las últimas 10 misiones,
salud de configuración (proveedores IA/búsqueda/Telegram/Google) y las
aprobaciones pendientes reales sin lanzar ninguna excepción. Y confirmar que
tras un `taskkill` forzado del backend, `logs/system.log` conserva su
contenido y aparece un hermano `system.<timestamp>.log` en vez de quedar
truncado a 0 bytes.

Diseño original (implementado tal cual):

### Sesión C — diseño original (Sonnet, esfuerzo medio)

**Los tres fallos que cierra** (diagnóstico 2026-08-04): (1) LOG-2 — la suite
de tests escribe en `logs/system.log` de PRODUCCIÓN (1368 de ~1400 líneas del
día eran fakes de tests; conocido desde la campaña 00, nunca arreglado);
(2) `WindowsSafeRotatingFileHandler` TRUNCA en vez de rotar cuando Windows
tiene el archivo bloqueado — destruye el forense en cada reinicio forzado
(confirmado: no existe ni un `system.log.1` pese a `backupCount=3`);
(3) no hay UN comando que responda "¿qué falló y por qué?" con el backend
apagado — hay piezas (`mission_report.py`, `check_schema_drift`) pero no
unificadas.

### C1 — Los tests escriben en su propio log (`AITHERA_LOG_DIR`)

**Archivo**: `app/core/logging_config.py`, línea 36. Cambio exacto:

```python
# [Sesión C] AITHERA_LOG_DIR: los TESTS (conftest.py) y cualquier entorno
# aislado apuntan los logs a su propia carpeta — mismo patrón exacto que
# AITHERA_CHROMA_PATH para la BD vectorial. Cierra LOG-2 (doc 34, campaña
# 00): la suite escribía miles de líneas fake en el system.log de producción.
_env_dir = os.getenv("AITHERA_LOG_DIR", "").strip()
LOGS_DIR = Path(_env_dir) if _env_dir else Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
```

**Archivo**: `backend/tests/conftest.py` — AL PRINCIPIO del módulo, ANTES de
cualquier `import app.*` (buscar dónde se fija `AITHERA_CHROMA_PATH` y poner
esto JUNTO, mismo bloque):

```python
os.environ.setdefault("AITHERA_LOG_DIR",
                      str(Path(tempfile.gettempdir()) / "aithera-test-logs"))
```

⚠️ El orden importa: `logging_config` computa `LOGS_DIR` al importarse, y
media app lo importa en cascada — si algún `import app.X` corre antes de
fijar la variable, no hace nada. Verificarlo con el test 1 de abajo.

### C2 — Rotar SIEMPRE, truncar JAMÁS

**Archivo**: `app/core/logging_config.py`,
`WindowsSafeRotatingFileHandler.doRollover` (líneas 20-33). Sustituir el
cuerpo del `except PermissionError` — en vez de truncar `baseFilename`
(destruye la historia), DESVIAR la escritura a un archivo hermano con
timestamp y dejar el bloqueado en paz:

```python
        except PermissionError:
            # [Sesión C] El proceso anterior aún bloquea el archivo (taskkill).
            # ANTES se truncaba — destruía el forense de cada sesión anterior
            # (por eso jamás existió un system.log.1 pese a backupCount=3).
            # AHORA: el bloqueado se queda intacto y este proceso escribe en
            # un hermano con timestamp. La historia SIEMPRE sobrevive.
            if self.stream:
                self.stream.close()
                self.stream = None
            base = Path(self.baseFilename)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            self.baseFilename = str(base.with_name(f"{base.stem}.{stamp}{base.suffix}"))
            self.stream = self._open()
```

**Limpieza acotada** (que los hermanos no crezcan sin límite): función de
módulo `_prune_sibling_logs(base: Path, keep: int = 10)` — lista
`base.stem.*` con timestamp en el mismo directorio, ordena por nombre, borra
los más viejos dejando `keep`, TODO en try/except (best-effort). Llamarla una
vez desde `setup_logger` al crear el file_handler.

### C3 — `scripts/aithera_doctor.py` (NUEVO): el comando único de diagnóstico

**Patrón**: calcado de `scripts/mission_report.py` (sys.path insert +
imports de app + BD directa; funciona con el backend APAGADO; read-only
ABSOLUTO — ni un UPDATE). Estructura OBLIGATORIA para que sea testeable:
un `collect(hours: int = 24) -> dict` con toda la lógica y un `main()` que
solo imprime — los tests llaman a `collect()`.

Secciones del dict (e impresión en este orden):

1. **`missions`**: últimas 10 filas de `orchestrator_traces` (id, mission_id,
   state, created_at, primeros 160 chars del outcome). Las `waiting` marcadas
   `⚠ ESPERANDO — con gate pendiente` si hay fila `approvals` en `pending`
   cuyo `action_payload.mission_id` coincida.
2. **`telemetry`**: por cada misión de (1) con eventos, el `summary` de
   `telemetry.mission_timeline(mission_id)` (llm_calls, path, within_budget,
   slowest_llm_ms) + recuento de eventos de bucle problemáticos (stage
   "toolloop": `stalled`, `preflight_not_ready`, `repeated_failure`,
   `repeated_denial`, `grant_denied`, `permission_denied`) y de `tool_call`
   con `ok=False` (agrupados por nombre, top 5 con su error).
3. **`config_health`**: búsqueda web configurada sí/no (reusar
   `app.tools.search_tool._configured_providers()`, mostrar solo sí/no por
   proveedor, JAMÁS la key), Telegram token presente sí/no, credenciales
   Google presentes sí/no, proveedores IA con `is_configured`/`is_active`
   (tabla `ai_provider_configs`, solo nombres).
4. **`schema`**: resultado de `app.db.database.check_schema_drift()` (ya
   existe y ya imprime una línea accionable — capturar/relanzar su output).
5. **`approvals_pending`**: filas `approvals` en `pending` con kind, edad en
   horas y mission_id — un gate olvidado hace días es exactamente lo que hay
   que ver aquí.

CLI: `python scripts/aithera_doctor.py [--hours 24]`. Cabecera del script:
nota de `PYTHONIOENCODING=utf-8` para consolas Windows cp1252 (lección de
`diagnose_new5.py`, campaña 02).

### Tests de la Sesión C — `tests/test_observabilidad.py` (NUEVO)

1. **AITHERA_LOG_DIR se respeta**: subproceso Python
   (`sys.executable -c "…"`) con la env fijada a un `tmp_path` que importa
   `app.core.logging_config`, escribe una línea con `get_system_logger` y
   sale; assert: el archivo existe bajo `tmp_path` y el `logs/system.log`
   del repo NO cambió de tamaño (medirlo antes/después). Subproceso porque
   el proceso de pytest ya importó logging_config con la env del conftest.
2. **Conftest lo fija**: en el propio proceso de tests,
   `logging_config.SYSTEM_LOG` está bajo `os.environ["AITHERA_LOG_DIR"]`.
3. **Rollover bloqueado NO trunca**: handler real sobre `tmp_path` con
   contenido previo; monkeypatch de `RotatingFileHandler.doRollover` para
   lanzar `PermissionError`; llamar `handler.doRollover()`; assert: el
   archivo original conserva su contenido ÍNTEGRO, `handler.baseFilename`
   cambió a un hermano con timestamp, y escribir un record después acaba en
   el hermano.
4. **Prune acotado**: crear 15 hermanos fake → `_prune_sibling_logs(keep=10)`
   deja 10 y no toca el base ni archivos ajenos.
5. **Doctor sobre BD sembrada** (SQLite de test, patrón
   `test_audit_s7s8_missions`): sembrar 1 traza `done` con outcome + 1
   `waiting` + 1 approval `pending` con su mission_id + 2 eventos de
   telemetría (`tool_call` fallida y `stalled`) → `collect()` devuelve las 2
   misiones, marca la waiting como esperando, cuenta el `stalled`, y
   `config_health` no revienta sin keys. Limpieza total al salir.
6. **Doctor jamás escribe**: tras `collect()`, los recuentos de filas de las
   tablas tocadas son idénticos a antes.

**Mutaciones obligatorias**: (a) revertir el `except` al truncado viejo →
cae 3; (b) quitar la lectura de `AITHERA_LOG_DIR` → caen 1 y 2.

**Regresión mínima**: suite de arranque (`test_smoke.py`,
`test_startup_time.py`) + `test_module_boundaries.py` + cualquier test que
lea logs. **NO tocar en C**: formato de las líneas de log (los scripts de
campaña las parsean), niveles, `get_error_logger` (errors.log funciona bien
y tiene historia — no romperla), ningún camino de ejecución del TIE.

---

## Orden, dependencias y criterio de cierre global

**A → B → C** (A ya ejecutada). B no depende de C; C no depende de B — pueden
invertirse si conviene, pero B primero maximiza el valor (la honestidad de
entregables es lo que el usuario sufrió).

**Criterio de cierre del bloque completo (verificación en vivo, Windows)**:
el encargo EXACTO que falló — "lee el GDD del proyecto Cordyceps, investiga
sobre Unity en la web y escribe CORDYCEPS_PLAN_2026.md con el plan por
sesiones" — en UNA sola misión debe: (a) leer el GDD entero (paginado), (b)
buscar de verdad o decir en el segundo 1 que la búsqueda no está configurada,
(c) escribir el archivo REAL en la carpeta del proyecto, y (d) que la
respuesta final solo afirme lo que existe en disco. Y `aithera_doctor.py`
debe poder contar la historia de esa misión con el backend apagado.
