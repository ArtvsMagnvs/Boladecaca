# 41 — EL LEARNER COGNITIVO (rediseño de V1.1, sesiones LC1-LC3)

> **Diseño 2026-08-07 (Fable 5), a raíz del primer contacto del Learner con el
> corpus real del usuario.** Este documento REABRE la fase V1.1: el tag
> `v1.1.0` NO se crea hasta cerrar LC3. Sustituye el criterio de aprendizaje de
> L2/L3 (no su infraestructura, que se conserva casi entera) y es la
> especificación ejecutable de las 3 sesiones de corrección. Regla de este doc:
> ninguna decisión abierta — los modelos de las sesiones implementan, no
> diseñan.
>
> **✅ LAS TRES SESIONES (LC1-LC3) ESTÁN EJECUTADAS (2026-08-07).** El Learner
> Cognitivo cierra V1.1 de verdad: el juez, la consolidación con IA y la cara
> con veredictos/calibración/comparación de mejoras, todo probado y verificado.
> Ver §8 para el detalle completo por sesión.

---

## §0 · Post-mortem: por qué el Learner salió mecánico

**El síntoma** (2026-08-07, panel del usuario): la bandeja proponía convertir
en procedimiento fijo *"inténtalo de nuevo, esta vez sin búsqueda web"* (visto
8 veces), *"pon la canción de Melendi"* (8 veces — ocho intentos porque NO
funcionaba), *"HOLA"* (4 veces), y misiones de las campañas de test. El sistema
estaba leyendo como hábito lo que era un usuario peleándose con algo roto, y
como trabajo real lo que eran bancos de prueba.

**Las tres causas, por orden de gravedad:**

1. **`state="done"` usado como señal de éxito.** `done` significa "la
   maquinaria terminó sin colgarse" — incluye rechazos honestos del planner
   (documentado en `pipeline.py` desde S2), rendiciones con texto, y "HOLA".
   El análisis 1 de L3 filtraba solo por `state="done"`. En TODO el sistema,
   nadie medía si al usuario le sirvió.
2. **La evidencia de la escalera era autogenerada.** `kind="execution_ok"` con
   `context_key=mission_id` es la propia máquina diciendo "terminé". El doc 15
   §3.3 exige señal EXTERNA — y el guardián de `ladder.py` comprobaba la FORMA
   de la evidencia, no su ORIGEN. Violábamos nuestro propio principio sin que
   saltara ninguna alarma.
3. **La sobre-corrección del §3.3.** La regla "el LLM diciendo que salió bien
   no es evidencia" se aplicó como "ningún LLM juzga nada", y el resultado fue
   un Learner sin capacidad de ENTENDER lo que observa: una tabla de procesos.
   La regla correcta es más precisa: **el EJECUTOR no se califica a sí mismo.**
   Un juez independiente —otro modelo, otra capacidad, con señales duras
   delante y el usuario como puerta final— no es el bucle de autoevaluación
   que el §3.3 teme: es exactamente el control externo que pedía.

**La decisión rectora del rediseño** (del usuario, literal): *"todos los
procesos del learner — lo que funciona en una misión y lo que no, los casos de
éxito y de error, incluso qué cosas van bien y mal en Aithera — lo tiene que
hacer una IA. […] Una propuesta para mejorar algo NUNCA la hace un sistema. La
hace una IA."*

---

## §1 · Principio rector v2: lo mecánico EXTRAE y PROTEGE; la IA ENTIENDE y PROPONE

El reparto deja de ser ambiguo. Cada pieza del Learner cae en una de dos
columnas, y el criterio para asignarla es fijo:

| Mecánico (determinista) | Por qué mecánico |
|---|---|
| Captura: snapshots, telemetría, contadores, atribución de fallos (L2b), etiquetado de origen | Extraer datos no requiere juicio; requiere no perder nada |
| La cuarentena: estados, transiciones de la escalera, undo, appliers | La SEGURIDAD debe ser determinista: una puerta que razona es una puerta con la que se puede discutir |
| Las matemáticas de justicia: `missions_excused`, denominadores, rankings | Una fórmula auditable no alucina |
| El grounding DEL PROPIO JUEZ (ver §3.5) | El control del controlador no puede ser otro LLM |

| IA (capacidad LEARN) | Por qué IA |
|---|---|
| **El veredicto de cada misión**: ¿sirvió, sirvió a medias, no sirvió? | "Servir" es una cuestión de sentido, no de estado de máquina |
| **La lección de cada misión**: ¿qué se aprendió aquí, si algo? | Distinguir un hecho de un procedimiento de un ruido exige entender |
| **La consolidación**: qué merece ser skill, qué mejora una existente, qué se agrupa con qué | El agrupado semántico y la redacción de procedimientos son lenguaje |
| **Las propuestas de mejora** (de skills, de configuración detectada por contexto, de sistema) | Una propuesta la hace una inteligencia, nunca un umbral |
| **La autopsia de los fallos** (ya existía en L3, se conserva) | ídem |

Lo que hoy hace de más el código mecánico (decidir que algo es candidata por
contar repeticiones, redactar el título de una propuesta, filtrar por
`state="done"`) **pasa a la columna IA**. Lo que hoy hace bien (escalera, undo,
atribución, stats justas) **no se toca**.

La comparación Jaccard de L2 (`same_work`) NO se borra: se degrada de juez a
**pre-agrupador barato** — una pista que la IA de consolidación confirma o
corrige, nunca una decisión final.

---

## §2 · La capacidad LEARN — "Aprendizaje" en Inteligencia

**Contrato MEL** (append-only, mismo régimen que VISION en B·WEB-2):

- `Capability.LEARN = "learn"` se AÑADE al enum de `mel/contracts.py` (nunca
  renombrar los existentes). Deja de estar "reservada" la etiqueta conceptual
  de doc 19: esta es su materialización.
- `catalog.py`: scores curados por (proveedor, modelo) para `learn` — los
  razonadores puntúan alto (DeepSeek R, familia o-series, Claude, MiniMax
  razonador; y locales tipo `deepseek-r1:14b`/`qwen3` marcados por nombre,
  mismo patrón de marcadores que `supports_vision`). **La lección de B·WEB-2
  aplica entera**: la aptitud se decide en `policies.is_capable` (punto único)
  para que compilación, ejecución retroactiva y UI no puedan divergir — hay
  test de invariante igual que el de visión.
- Políticas: Economy prefiere el mejor LOCAL apto (un razonador local lento es
  perfecto para un job de fondo — coste 0); Quality el mejor global; Custom
  editable. **No se limita a locales**: el usuario elige, exactamente como
  pidió.
- **UI**: fila **"Aprendizaje"** en Ajustes → Inteligencia
  (`MEL_CAPS_ORDER` en `Settings.tsx` — recordar que es una whitelist: si no
  se añade, no aparece; el bug de `vision` del 2026-08-05 fue exactamente
  este). Con su hint en el recuadro: *"El modelo que analiza lo que Aithera
  hace, juzga qué funcionó y redacta lo que aprende. Un razonador local va
  perfecto: trabaja en segundo plano, sin prisa."*
- Todos los consumidores del Learner (`juez`, `consolidación`, `autopsia`,
  `/learn`) migran a `capability=LEARN`. La autopsia de L3 deja
  `ANALYZE+quality` y pasa a `LEARN` — un solo mando para todo el aprendizaje.

**Regla anti-sesgo estructural**: la cadena de LEARN, al juzgar una misión,
SALTA los modelos que EJECUTARON esa misión (la telemetría ya sabe cuáles
fueron). Si no queda ningún candidato apto distinto, se juzga igual pero el
veredicto se marca `judge_bias=true` — visible, nunca silencioso (misma regla
que el juez del torneo SE1).

---

## §3 · El Juez: veredicto por misión

La pieza central nueva. Un modelo (capacidad LEARN) lee cada misión terminada
y dictamina si SIRVIÓ — con las señales duras delante y con lo que pasó
DESPUÉS delante.

### §3.1 Tabla `mission_verdicts` (migración nueva, encadenada)

```
id (uuid) · mission_id (ix) · trace_id · origin (user|test|campaign|e2e|automation)
verdict (served|partial|failed|unclear) · confidence (0-1)
reasons (text, 2-4 frases del juez)
evidence (JSON: qué señales citó — ids y citas literales)
signals (JSON: el paquete de señales duras que se le dio — auditable)
lesson (JSON: {type, content, related_skill_id} — ver §4.1)
judge_model (provider:model) · judge_bias (bool)
superseded_by (uuid nullable — re-juzgar es legítimo, la historia se conserva)
created_at
```

### §3.2 El paquete de señales duras (mecánico — extracción, no juicio)

Todo esto YA se registra; solo se empaqueta para el juez:

1. **Entregables verificados** (Sesión B): qué archivos afirmó y cuáles existen.
2. **Rendición detectada** (NEW-4 `is_surrender`).
3. **`PlanRejection`** (el planner declaró que no podía).
4. **Atasco** (Sesión A `stalled`) y fallos repetidos (S9c).
5. **Atribución de fallos** (L2b: kinds y blames del timeline).
6. **Limitaciones declaradas** (S11: tools rechazadas, avisos de incompletitud).
7. **EL DESPUÉS** — la señal que hoy nadie mira: los siguientes 1-3 mensajes
   del usuario en la misma sesión de chat tras la respuesta (recortados), y si
   el MISMO trabajo se volvió a pedir y cuánto tiempo después. **Esto es un
   INSUMO del juez, no una regla**: no hay ningún umbral mecánico de minutos
   decidiendo nada — el juez ve "el usuario respondió 'otra vez, sin búsqueda
   web' 3 minutos después" y entiende lo que eso significa, igual que lo
   entendería una persona.
8. **Origen** (§6): user/test/campaign/e2e.

### §3.3 El prompt del juez (marco, no literal — el literal lo fija LC1 con doc 36)

Encuadre ESCÉPTICO, en la dirección segura: *"Tu trabajo es encontrar por qué
esta misión NO sirvió al usuario. Declara `served` únicamente si la evidencia
lo sostiene: hay entregable verificado, o el usuario siguió adelante sin
corregir, o el resultado responde lo pedido de forma comprobable. Un texto
bonito sin efecto no es servir. Cita SIEMPRE qué señales sostienen tu
veredicto. Si no se puede saber, di `unclear` — es una respuesta legítima."*
Salida JSON con schema fijo (verdict/confidence/reasons/evidence/lesson).

### §3.4 Cuándo se juzga

- **Misiones no triviales**: en cola tras `mission.completed/failed`, con
  retardo `LEARNER_JUDGE_DELAY_MIN` (default 10) para que EXISTA el después —
  o antes si llega el siguiente mensaje del usuario. Cola con debounce; el
  juicio jamás toca el camino caliente.
- **Charla trivial** (camino corto): se juzga en LOTE nocturno — una llamada
  agrupada sobre N turnos, no una por turno. Todo recibe veredicto, como pidió
  el usuario; el coste se controla agrupando, no omitiendo.
- **Catch-up nocturno**: lo no juzgado del día (backend apagado, cola perdida)
  se juzga en la pasada de las 04:45, antes de la consolidación.

### §3.5 El grounding del juez (la única pieza mecánica nueva, y por qué)

El juez es un LLM y puede alucinar. Su control NO puede ser otro LLM (regresión
infinita), así que es un chequeo determinista mínimo, en la dirección segura:
un veredicto `served` que no cite NINGUNA señal del paquete, o que las cite
inexistentes, **se degrada a `unclear`** — nunca al revés (un `failed` nunca se
promociona mecánicamente). El mismo principio que el grounding del responder:
lo mecánico solo puede QUITAR confianza, jamás ponerla.

---

## §4 · Lecciones y consolidación: la IA que aprende y propone

### §4.1 La lección por misión (misma llamada del juez — coste: 1 llamada)

El juez devuelve, además del veredicto, `lesson`:
`{type: none|fact|procedure|skill_improvement|error_pattern|system_weakness,
content: texto, related_skill_id?: id}`. El catálogo de skills existentes
(nombres + descripciones, compacto) viaja en el prompt para que pueda decir
"esto mejora la skill X" en vez de proponer una duplicada. `none` es la
respuesta esperada para la mayoría — se le dice explícitamente que no invente
lecciones (reflection theater, doc 15 §10).

### §4.2 La consolidación nocturna (la IA decide; lo mecánico ejecuta)

Job a las 04:45 (sustituye al análisis 1 mecánico de L3; los análisis 2-5 se
conservan con las adaptaciones de §7). Entrada: los veredictos+lecciones
recientes **con `origin=user` y `verdict∈{served,partial}`**, el catálogo de
skills, las propuestas abiertas, y **las rechazadas por el usuario con sus
motivos** (la calibración: si rechazaste "resumen semanal" con nota "no me
sirve así", la IA lo ve y no re-propone lo mismo). El pre-agrupador Jaccard le
da una agrupación inicial como PISTA.

Salida (JSON con schema fijo) — las decisiones que hoy tomaba un umbral:
- **`create_skill`**: nombre, descripción, y **pasos extraídos de los
  transcripts REALES de las misiones que sirvieron** — nunca inventados.
  Post-chequeo determinista (grounding, no juicio): las tools que los pasos
  mencionan ⊆ tools realmente usadas en las misiones-evidencia; si no, la
  propuesta se degrada a "observación" sin pasos.
- **`improve_skill`**: skill existente + diff propuesto + por qué (con las
  misiones-evidencia).
- **`merge_candidates`** / **`drop_candidate`**: agrupar propuestas que son lo
  mismo dicho distinto; retirar candidatas que la evidencia nueva desmiente.
- **`config_fix`** contextual (además del determinista de L2b, que se queda).
- **`finding`**: lo que ve y no puede proponer (va al informe, como hasta ahora).

Lo mecánico APLICA esas decisiones a la cuarentena: crea/actualiza filas,
respeta la escalera, jamás salta un estado. **La IA propone; la máquina
tramita; el usuario decide.** Presupuesto: 1-3 llamadas LEARN por noche.

### §4.3 La evidencia v2 en la escalera

`ladder.is_valid_evidence` cambia su definición de señal externa:
- **VALE**: `kind="judged_success"` — veredicto `served` de un juez
  independiente que citó señales, con `origin=user` (referencia al
  `mission_verdicts.id`, verificable). Y por supuesto todo lo del usuario:
  aprobaciones, feedback, uso real.
- **DEJA DE VALER**: `execution_ok` a secas (la máquina diciendo "terminé").
  Migración de datos: las evidencias existentes de ese kind se marcan
  `legacy_unjudged` y NO cuentan para subir peldaños hasta que el re-juicio
  del backfill (§6) las convierta o las descarte.

El contrato de producto nº 1 se RE-ESPECIFICA: *"tres misiones del mismo
trabajo, **juzgadas como éxito por el juez**, en contextos distintos → una
candidata"*. El test se reescribe con el juez en la frontera del LLM (el único
doble, como siempre) — y con un caso negativo nuevo: tres repeticiones
juzgadas `failed` producen CERO candidatas (el caso Melendi, inmortalizado
como test).

---

## §5 · Anti-contaminación v2 (la regla, ahora precisa)

Reemplaza la lectura ambigua del doc 15 §3.3 por cuatro reglas exactas:

1. **El ejecutor jamás se califica a sí mismo.** El juez es otra llamada, otra
   capacidad, y salta a los modelos que ejecutaron (§2).
2. **Todo juicio de IA cita evidencia verificable** (ids, señales, citas) o se
   degrada a `unclear` (§3.5).
3. **Lo mecánico solo degrada, nunca promueve.** Ningún chequeo determinista
   puede convertir algo en éxito ni subir un peldaño.
4. **El usuario sigue siendo la única puerta de activación.** Nada de lo que la
   IA proponga se aplica sin su sí; el riesgo alto sigue siendo HITL siempre;
   el undo sigue intacto.

Con estas cuatro, meter IA en todos los juicios NO abre el bucle de
retroalimentación: el juez puede equivocarse, pero no puede activar nada, no
puede juzgarse a sí mismo, y su tasa de acierto es visible (§7, calibración).

---

## §6 · Higiene del corpus: origen, purga y re-juicio

- **Etiquetado de origen** (mecánico — es extracción): `Mission.source` ya
  distingue user/automation/learner/workspace; se añade la marca de PRUEBA:
  las campañas y `mission_lab` fijan `AITHERA_TEST_CORPUS=1` (env/config) y
  todo lo creado bajo esa marca nace `origin=test`; el E2E marca `e2e`.
  Refuerzo heurístico solo para lo HISTÓRICO (goals con `test-campanya`,
  `example.com`, `[Contexto interno:`) — el pasado no se puede re-etiquetar de
  otra forma. El juez además ve el goal y puede señalar "esto parece una
  prueba" en misiones futuras sin marca.
- **Purga de la bandeja actual**: las propuestas vivas nacidas del corpus
  contaminado se cierran en bloque como `rejected` con nota
  `"corpus de pruebas (purga LC2)"` — auditable, no borrado.
- **Re-juicio (backfill)**: el juez procesa las últimas `N=100` misiones
  reales (origin=user) del historial, de madrugada, a ritmo de batch. Con eso
  la consolidación arranca con veredictos de verdad en vez de con la nada.

---

## §7 · Lo que cambia en lo YA construido

| Pieza | Cambio |
|---|---|
| L2 `mission_learning._reflect/_accumulate_candidate` | La reflexión-por-misión SE FUSIONA con el juez (una llamada, no dos); la acumulación mecánica de candidatas SE RETIRA — la consolidación IA (§4.2) es quien crea/refuerza candidatas. Los contadores y `_propose_config_fixes` deterministas se quedan |
| L3 `analyze_repeated_missions` | SE RETIRA como decisor; su agrupación Jaccard queda como pre-agrupador de la consolidación. `analyze_cross_project`, `recompute_skill_quality` y el informe semanal se quedan (el informe gana la sección de calibración del juez) |
| L3 autopsia | Migra de `ANALYZE+quality` a `LEARN` |
| Contrato nº 1 | Re-especificado (§4.3) — el test actual afirma un contrato equivocado y se reescribe |
| Escalera (`ladder.py`) | `is_valid_evidence` v2 (§4.3); MIN_REP y las rutas por riesgo NO cambian |
| Panel L4 | Gana: chip de veredicto por misión (también en Mission Control), sección de calibración en Salud (% de propuestas del juez aceptadas/rechazadas, veredictos con bias), selector "Aprendizaje" enlazado. Las pestañas eran datos: es añadir, no refactorizar |
| V1.2 (doc 27 §6) | SE1/PE1/PE2 y ML1 consumen `mission_verdicts` en vez de `state="done"` — path_stats mide "sirvió", no "terminó". ML3 usa LEARN. Se anota en sus fichas, no se reescriben |
| `model_stats` (L2) | `mission_ok` pasa a derivarse del veredicto cuando existe (fallback al estado si aún no juzgado) — la nota del modelo por fin mide SERVIR |

---

## §8 · Las sesiones (V1.1 continúa; el tag `v1.1.0` espera a LC3)

> Orden estricto LC1 → LC2 → LC3. Cada una con la disciplina completa: tests +
> mutación confirmada y restaurada + regresión por lotes + cierre en docs.
> El E2E del Learner (`test_learner_e2e.py`) se ACTUALIZA en cada sesión — es
> la red que cazó el desastre y tiene que seguir pasando por el camino real.

### ✅ LC1 — El Juez · **Opus, esfuerzo EXTRA** — EJECUTADA (2026-08-07)

**Entregado**, todo verificado con tests + 6 mutaciones confirmadas y
restauradas byte a byte:

- **Capacidad `LEARN`** (`mel/contracts.py`, append-only) + `supports_learn()`
  en `catalog.py` (marcadores de razonador — deepseek-r1, qwq, qwen3, o1… — y
  suelo de puntuación; los agentes CLI quedan fuera: arrancan un proceso por
  llamada) enchufado en `policies.is_capable`, el punto ÚNICO de aptitud.
  Fila **"Aprendizaje"** en Ajustes → Inteligencia + i18n ×4 (1336 claves,
  paridad verificada) y aviso accionable cuando no hay ningún modelo apto
  (`settings.mel.learnNoModel`, con el `ollama pull` concreto).
  **Invariante UI↔ejecución** calcado del de visión: `list_models()` marca
  `learn` en `unfit_catalog` con el MISMO criterio que usa la ejecución, para
  que Inteligencia no ofrezca un modelo que `set_primary` rechazaría por
  dentro (el usuario vería "no se guarda" sin explicación).
- **`mission_verdicts`** (migración `1c1a5eb9d70f`) + **`orchestrator_traces`
  += `session_id`/`origin`** (migración `2f7b3c9a41de`). Las dos encadenadas,
  idempotentes, nunca editando una ya aplicada.
- **`app/learner/signals.py`** — el paquete de señales duras (§3.2), extracción
  pura y sin juicio: entregables verificados (Sesión B), rendición (NEW-4),
  PlanRejection, atascos y fallos repetidos (Sesión A / S9c), atribución L2b,
  limitaciones S11, **el DESPUÉS** (mensajes siguientes del usuario en la MISMA
  conversación + re-peticiones del mismo trabajo, con su distancia en minutos)
  y el origen. `citable_ids()` deriva qué puede citar el juez.
- **`app/core/corpus.py`** — origen `user|test|campaign|e2e|automation`, por
  env (`AITHERA_TEST_CORPUS`) o por `Config` (`learner.test_corpus`, la vía que
  necesita `mission_lab`, que dirige el backend desde fuera). Cableado en
  `mission_lab.py` con `try/finally`: la marca jamás se queda puesta.
  Heurística SOLO para lo histórico sin marca.
- **`app/learner/judge.py`** — cola con retardo (para que EXISTA el después) +
  juicio por misión + **grounding** (§3.5: un `served` sin evidencia citable, o
  con evidencia inventada, se degrada a `unclear`; un `failed` NUNCA se
  promociona) + **anti-sesgo** (`exclude` de los modelos que ejecutaron; si no
  hay alternativa se juzga igual pero con `judge_bias=True`) + catch-up y
  backfill nocturnos (04:20, antes del análisis y de la purga de telemetría) +
  lote agrupado de charla. Suscrito al bus en el `lifespan`.
  **`served(mission_id)` es fail-closed**: sin veredicto, no consta que
  sirviera — la función que sustituye a `state == "done"`.

**Tests**: `test_lc1_juez.py` NUEVO (23) + 3 en el E2E (el juez POR EL BUS, no
por llamada directa — el guardián anti-"correcto pero desconectado") + 2 en
`test_migracion_columnas.py`. **Mutaciones (6)**: sin degradación del grounding
caen 2 · sin `exclude` cae 1 · sin exclusión del corpus de pruebas cae 1 · sin
`session_id` en la traza caen 2 · sin suscripción al bus caen 3 · con id de
revisión duplicado caen 2. Regresión por lotes: 62 + 93 + 92 + 85, cero rotos;
`tsc --noEmit` limpio.

**Hallazgo real de la propia sesión** (y por eso los 2 tests nuevos de
migración): los ids "bonitos" que elegí primero — `d1e2f3a4b5c6` y
`f1a2b3c4d5e6` — YA estaban cogidos por migraciones anteriores. Alembic
identifica las revisiones por id, así que eso no rompe una tabla: rompe el
grafo entero y **ninguna** migración se aplica. Con 36 migraciones ese espacio
de nombres está agotado y a ojo no se ve. Ahora hay un test que exige ids
únicos, un solo head, y que la cadena desde el head recorra TODAS las
migraciones.

**Ajuste de alcance, dicho claro**: `hurry()` (adelantar el juicio en cuanto el
usuario escribe) existe y lo usa la pasada nocturna, pero NO se dispara desde
el chat. Hacerlo obligaría al TIE a importar del Learner, y el Learner observa
al TIE, no al revés (doc 16). No es una pérdida: el retardo existe justamente
para que haya después que leer.

**Pendiente en Windows**: `cd backend && alembic upgrade head` (verás
`c0d1e2f3a4b5 -> 1c1a5eb9d70f` y `-> 2f7b3c9a41de`), reiniciar el backend, y
en Ajustes → Inteligencia comprobar que aparece la fila "Aprendizaje" con un
modelo asignado (o el aviso de que hace falta un razonador).

---

### LC1 — plan original
- Capability `LEARN` completa (enum + catalog con marcadores de razonadores +
  `is_capable` punto único + test de invariante UI↔ejecución, calco del de
  visión) + fila "Aprendizaje" en Inteligencia + i18n ×4.
- Tabla `mission_verdicts` (migración encadenada) + empaquetador de señales
  duras (§3.2, incluido el DESPUÉS: captura de los mensajes siguientes por
  `session_id` de R6.5b) + etiquetado de origen (§6) con
  `AITHERA_TEST_CORPUS=1` cableado en mission_lab/campañas/E2E.
- El juez: cola con debounce + juicio por misión + lote nocturno de charla +
  catch-up + grounding del juez (§3.5) + anti-sesgo (salta ejecutores) +
  backfill de las últimas 100 misiones reales.
- Por qué Opus extra: cruza MEL (enum+políticas+UI), TIE (señales, aftermath),
  scheduler, y una migración — el tipo de sesión transversal donde un descuido
  cuesta caro.
- Tests clave: el caso Melendi (8 repeticiones + aftermath correctivo → el
  juez NO da served), served sin señales se degrada a unclear (mutación),
  el juez nunca es el ejecutor, origen test excluido, backfill idempotente.

### ✅ LC2 — El aprendizaje de verdad · **Opus, EXTRA** — EJECUTADA (2026-08-07)

**Se aprende igual del acierto que del error**, y son cosas distintas: de lo que
sirvió sale el procedimiento; de lo que falló, el porqué y —si es accionable— el
arreglo. Petición explícita del usuario al abrir la sesión, y la mitad que el
Learner mecánico no tenía.

- **Escalera v2** (`ladder.py`): nace `judged_success` — el veredicto de un juez
  independiente sobre trabajo REAL— y es lo único que empuja hacia arriba junto
  con la validación determinista y las señales del usuario. `execution_ok` (la
  máquina diciendo "terminé") pasa a `INERT_KINDS`: **se conserva y se puede
  leer, pero no promociona nada**. `judged_failure` cuenta como CONTRADICCIÓN —
  un trabajo que se hizo y no sirvió no es neutral respecto a convertirlo en
  procedimiento. Y los motivos lo explican: "3 sin juzgar todavía" en vez de
  dejar la propuesta parada sin decir por qué.
- **`app/learner/consolidation.py`** (NUEVO) — la pieza que sustituye al umbral.
  Una vez por noche (04:45, la primera de la pasada), un modelo LEARN ve los
  veredictos con sus lecciones —**los buenos y los malos**—, las propuestas
  abiertas, **los rechazos del usuario con su motivo** (calibración) y el
  catálogo de skills, y DECIDE: `create_skill` · `improve_skill` ·
  `merge_candidates` · `drop_candidate` · `config_fix` · `finding`. Lo mecánico
  solo TRAMITA por la escalera de siempre. Jaccard sobrevive degradado a
  pre-agrupador: sugiere qué mirar junto, ya no decide.
- **Grounding de los pasos**: las herramientas que la propuesta declara —y las
  que sus pasos nombran— tienen que estar entre las que las misiones-evidencia
  usaron de verdad. Si no, se degrada a observación SIN pasos: "esto se repite"
  sigue siendo cierto, "y se hace así" deja de constar. La comparación es contra
  el repertorio OBSERVADO y no contra el ToolManager — **el contrato de producto
  nº 4 cazó el primer intento de importar `app.tools` desde el Learner**, y la
  versión resultante es mejor: se compara con lo que se ha visto usar.
- **Retirados los dos decisores mecánicos**: la acumulación por misión de L2 y
  el análisis 1 de L3. Terminar una misión ya no abre nada en la bandeja.
- **`app/learner/cleanup.py`** (NUEVO, §6): las evidencias del criterio viejo se
  re-etiquetan `legacy_unjudged` (nunca se borran) y las propuestas vivas que
  solo se sostienen en corpus de pruebas o en misiones fallidas se cierran como
  `rejected` **con motivo**. Basta UNA misión real para que una propuesta
  sobreviva — retirar de más también es un error. Idempotente, en el arranque.
- **`model_stats.mission_ok` derivado del veredicto** (`stats.apply_verdict`):
  los contadores se escriben al terminar la misión y el veredicto llega minutos
  después, así que se CORRIGE cuando el juez discrepa. La nota de un modelo pasa
  a medir "¿cuántas de sus misiones sirvieron?".
- **Contrato de producto nº 1 RE-ESPECIFICADO**: estaba en verde sobre un
  criterio equivocado ("repetida 3 veces" se cumplía con ocho fracasos). Ahora:
  tres misiones **juzgadas como éxito** → candidata; y su negativo, **el caso
  Melendi inmortalizado como test** — tres repeticiones juzgadas `failed`
  producen CERO candidatas.

**Tests**: `test_lc2_consolidacion.py` NUEVO (24) + 3 contratos de producto
reescritos + E2E actualizado a la cadena nueva (misiones → veredictos →
consolidación → escalera, con dos casos nuevos: el que aprende y el Melendi).
**Mutaciones (5)**: devolver el valor a `execution_ok` tumba 4 · desactivar el
grounding tumba 1 · dejar que la IA se salte `MIN_REP` tumba 1 · quitar los
fallos de la entrada tumba 3 · quitar el guardia de "una misión real la salva"
tumba 1. Regresión: **155 + 109 + 64** en verde, cero rotos.

**Tests preexistentes actualizados al contrato nuevo, no debilitados**: los que
usaban `execution_ok` como evidencia pasan a `judged_success` (lo que
comprueban —rachas, umbrales, rutas de riesgo— no cambia; cambia qué cuenta), y
los dos del análisis 1 se sustituyen por el contrato de su RETIRADA.

**Pendiente en Windows**: además del `alembic upgrade head` de LC1, mirar el
panel tras un arranque: el saneado habrá cerrado con motivo las propuestas del
corpus contaminado y el resto aparecerá esperando veredicto.

---

### LC2 — plan original
- Lección en la llamada del juez (§4.1) + consolidación nocturna IA (§4.2) con
  sus post-chequeos de grounding (pasos ⊆ tools observadas — mutación
  obligada) + calibración con los rechazos del usuario en el prompt.
- Evidencia v2 en la escalera (§4.3) + migración `legacy_unjudged` + purga en
  bloque de la bandeja contaminada (§6) + retirada de la acumulación mecánica
  de L2 y del análisis 1 de L3 (Jaccard → pre-agrupador).
- Re-especificación del contrato nº 1 + el test negativo del caso Melendi +
  actualización del E2E completo (ahora con el juez en la cadena).
- `model_stats.mission_ok` derivado del veredicto.
- Por qué Opus extra: es el corazón — toca escalera, cuarentena, L2, L3, E2E y
  datos existentes (migración de evidencias). El coste de un error aquí es
  aprender mal en silencio otra vez.

### ✅ LC3 — La cara y la calibración · **Sonnet, esfuerzo ALTO** — EJECUTADA (2026-08-07)

**Petición del usuario, más allá del plan original**: que una "mejora de
skill" no llegue nunca a la bandeja solo porque la IA lo sugiera — tiene que
COMPARARSE con la versión actual y solo proponerse si hay una mejora
demostrable, de forma que valga para cualquier dominio (frontend, backend,
marketing…). Y que el panel sea rico e interactivo, no una lista plana:
el usuario tiene que poder VER de qué va una skill nueva, y comparar una
mejora con un clic.

- **`app/learner/comparison.py`** (NUEVO) — la prueba de mejora efectiva,
  domino-agnóstica por diseño: genera con capacidad ANALYZE la respuesta que
  daría un agente guiado por la versión ACTUAL de la skill y por la versión
  PROPUESTA, ante las mismas tareas reales (de las misiones-evidencia); un
  juez independiente (capacidad LEARN, excluyendo —anti-sesgo— a los modelos
  que generaron los candidatos) compara texto contra texto y decide si hay
  mejora clara y consistente. Nunca ejecuta nada (sin herramientas, sin
  efectos secundarios): compara SALIDAS, así que sirve igual para cualquier
  ámbito sin inventar un arnés de tests por dominio. Devuelve `None` cuando no
  se pudo comparar (sin tareas, MEL caído) — el llamador lo trata como "sin
  verificar", nunca como "mejora confirmada": lo mecánico solo quita
  confianza, igual que el resto del proyecto.
- **`consolidation._mejorar_skill`** (reescrita): antes de crear una
  propuesta `skill_improve`, llama a `comparison.compare_skill_change`. Si la
  comparación concluye explícitamente que NO hay mejora, la propuesta se
  DESCARTA — "incumbente que gana = sin propuesta" (el mismo criterio que
  SE1, V1.2, adelantado aquí en su forma segura). Si no se pudo comparar
  (sin tareas de ejemplo), la propuesta SÍ se crea pero marcada
  `verified=False` con `comparison=None`: no proponer nada por un fallo del
  banco de pruebas sería peor que ser honesto sobre no haberlo comprobado.
- **`judge.py` — re-juzgar enlaza, nunca borra**: `_save()` gana el enlace
  `superseded_by` que el esquema tenía desde LC1 pero nadie escribía —
  cualquier veredicto vigente anterior de la misma misión se marca como
  sustituido al guardar el nuevo. Nuevas `verdict_history()` (la cadena
  completa, del más antiguo al vigente) y `calibration_summary()` (cuántos
  veredictos hay en total, qué fracción se dio sin juez alternativo, cuántos
  re-juicios cambiaron de veredicto frente a cuántos lo confirmaron) — la
  materia prima de la sección de calibración, nunca una nota inventada.
- **`proposals.py` — applier de `skill_improve`** (NUEVO, registrado): "Aceptar"
  una mejora reusa `SkillLibrary.improve()` para añadir el cambio a la
  descripción de la skill; el undo restaura la descripción previa desde el
  propio snapshot de la propuesta (no depende de que nadie más haya tocado la
  skill entremedias).
- **Endpoints** (`endpoints/learner.py`): `GET /learner/verdicts?mission_ids=`
  (en bloque, para pintar la lista de Mission Control sin una llamada por
  fila), `GET /learner/verdicts/{mission_id}` (vigente + historia completa),
  `POST /learner/verdicts/{mission_id}/rejudge` (funciona igual si la misión
  nunca se juzgó — es "juzgar ahora" cuando aún no hay veredicto, "re-juzgar"
  cuando ya lo hay). `_propuesta_out()` gana `description`/`grounded` (skill
  nueva) y `skill_id`/`change`/`current_description`/`verified`/`comparison`
  (mejora) — la información completa para decidir sin creerse un título.
  `/learner/health` gana `calibration`.
- **Frontend rico, no plano** (petición explícita): `Missions.tsx` — chip de
  veredicto por misión en la lista (backend-traducido, mismo patrón que
  `kind_label`/`risk_label` del resto del Learner) + tarjeta de detalle con
  confianza, aviso de sesgo, razones a un clic, cuántas veces se re-juzgó, y
  el botón Re-juzgar/Juzgar ahora. `Learning.tsx` — una skill nueva muestra su
  `description` SIEMPRE visible (nunca detrás de un clic: no se puede decidir
  "Aceptar" solo con el título); una mejora muestra hoy/cambio propuesto
  siempre visible + insignia "mejora comprobada"/"sin verificar" + la
  comparación COMPLETA a un clic (antes/después por tarea, veredicto por
  tarea, confianza del juez); la pestaña Salud gana una tarjeta de
  calibración (veredictos dados, % sin juez alternativo, re-juicios, % que
  cambiaron de opinión) — se calla por completo si `total_verdicts == 0`.
  i18n ×4 (+28 claves, 1364 en los 4 idiomas, paridad verificada).

**Tests**: `test_lc3_ui.py` NUEVO (29 — la prueba de comparación con sus
casos negativos, la integración con la consolidación en sus 4 variantes
—mejora confirmada, sin mejora real, sin tareas de ejemplo, skill
inexistente—, re-juzgar enlazando sin borrar, calibración en sus 4
variantes, el applier de mejora aplicando y deshaciendo, y 11 de los
endpoints nuevos incluida la comparación completa expuesta con un clic).
**Mutaciones (3, restauradas y verificadas)**: desactivar el descarte por
"sin mejora real" tumba 1 · desactivar el enlace `superseded_by` tumba 3 (el
del historial + los 2 de calibración que dependen de él) · vaciar la
descripción nueva del applier tumba 1. Regresión: **109 passed** en el
subconjunto LC1+LC2+LC3+panel+contratos+boundaries; `tsc --noEmit` limpio y
`vite build` completo (869 módulos).

**Hallazgo honesto, no de esta sesión pero visto al correr la suite
completa**: 18 fallos preexistentes y AJENOS a LC3 (`test_action_intent.py`,
`test_mel_research.py`, `test_quick_memory.py::test_forget_ambiguo_lista_sin_borrar`
—ya documentado en §29 del CLAUDE.md— y `test_learner_mission.py`, este
último con causa clara: son los tests de la era L2 MECÁNICA, anteriores a
LC1/LC2, que afirman el contrato VIEJO que este mismo rediseño retiró a
propósito —`test_lc2_consolidacion.py::TestLoMecanicoYaNoDecide` prueba
justo lo contrario y está en verde—; nadie los retiró al cerrar LC2. Ninguno
de los 18 importa ni referencia código de LC3. Fuera del alcance de esta
sesión (no son Learner de cara al usuario ni fueron tocados aquí); se dejan
anotados para una sesión de limpieza aparte en vez de tocarse en silencio
bajo el paraguas de LC3.

**Pendiente en Windows**: `cd backend && alembic upgrade head` si quedara
alguna migración de LC1 sin aplicar; reiniciar backend y frontend; abrir
Mission Control y confirmar el chip de veredicto + el botón Re-juzgar; abrir
Aprendizaje y comprobar que una skill nueva muestra su descripción y que una
mejora (si la hay) muestra la comparación con un clic; mirar la tarjeta de
calibración en Salud tras algún re-juicio.

---

### LC3 — plan original
- Veredictos visibles: chip "¿sirvió?" por misión en Mission Control y en la
  página Aprendizaje (con las razones del juez a un clic); sección de
  calibración en Salud; pestaña/fila "Aprendizaje" pulida en Inteligencia;
  i18n ×4 completo; estados vacíos.
- Botón "Re-juzgar" por misión (para cuando el usuario discrepe — su
  discrepancia queda registrada y alimenta la calibración).
- Cierre de fase REAL: los 5 contratos de producto en verde con el nº 1 nuevo,
  E2E verde ×4 pasadas, suite Windows, y AHORA sí — tag `v1.1.0`.
- Por qué Sonnet alto: es UI + cableado sobre APIs ya construidas y probadas
  en LC1/LC2, el patrón exacto de las sesiones UI que Sonnet ya ha hecho bien
  (L4, PU10-visual).

---

## §9 · Registro de decisiones de este diseño

| Decisión | Resolución | Razón |
|---|---|---|
| ¿IA en los juicios viola la anti-contaminación? | **No, con las 4 reglas de §5** — la prohibición real siempre fue la AUTOevaluación del ejecutor | la sobre-aplicación del §3.3 es la causa raíz nº 3 del post-mortem; corregir el principio es parte del arreglo |
| ¿Umbrales temporales mecánicos para detectar re-peticiones? | **No** — el "después" es un INSUMO que el juez lee, no una regla que decide | decisión del usuario, literal: el aprendizaje no puede ser mecánico; una regla de minutos no entiende nada |
| ¿Modelo del juez limitado a locales? | **No** — capacidad LEARN seleccionable en Inteligencia, default Economy = mejor local razonador | decisión del usuario; el default local respeta coste-0 en fondo |
| ¿Se juzga TODO, incluida la charla? | **Sí** — misiones individualmente, charla en lote nocturno | petición del usuario ("cada proceso, misión, petición"); agrupar controla el coste sin omitir |
| ¿Qué queda mecánico? | Extracción, cuarentena/escalera/undo, matemáticas de justicia, grounding del juez | lo mecánico extrae y protege; la seguridad determinista no se negocia (y el control del controlador no puede ser otro LLM) |
| ¿El tag v1.1.0? | **Esperó a LC3** — cerrada 2026-08-07 | no se etiqueta como "Learner operativo" un learner que aprende mal; la fase se reabre con honestidad |
| ¿Una mejora de skill se propone solo porque la IA lo sugiere? | **No** — se compara con la versión actual (`comparison.py`, LC3) y solo se propone con mejora demostrable | petición directa del usuario al abrir LC3, extensión sobre el plan original |

---
*Diseño 2026-08-07 (Fable 5, a petición directa del usuario tras revisar el
panel con el corpus real). Deroga el criterio de aprendizaje de L2/L3 en lo que
contradiga a este doc; conserva su infraestructura. LC1-LC3 EJECUTADAS
(2026-08-07) — V1.1 cerrada de verdad. Actualiza: doc 27 §5
(sesiones LC1-LC3), doc 15 (addendum §12, la regla precisa), CLAUDE.md.*
