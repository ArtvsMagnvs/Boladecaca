# 19 — MEL: Model Execution Layer — Documento Maestro de Diseño

> **Estatus**: fuente oficial de verdad del MEL. Mismo rango que 07/08 (MOS),
> 14 (TIE), 18 (WPMS). Gobernado por la disciplina modular del doc 16.
> **Misión en una frase**: el resto de Aithera pide *capacidades* ("clasifica
> esto", "razona sobre esto"); el MEL decide QUÉ modelo lo ejecuta, CÓMO, con qué
> respaldos, y aprende de la experiencia real — nadie más vuelve a escribir un
> nombre de modelo.
>
> **Posición en el roadmap** (decisión razonada en §12): **MEL v1 dentro de V1.0,
> tras el TIE v1, como bloque E1-E2 antes del cierre beta (O5)** — el wizard de
> onboarding del MVP beta ES el momento natural de la auto-configuración.
> MEL v2 (aprendizaje + Custom UI) en V1.2 junto al Learner.

---

## 1. Qué es (y qué NO es)

El MEL es la capa universal de ejecución de modelos de IA. Responsabilidad única:

1. Seleccionar el modelo adecuado para una capacidad solicitada.
2. Ejecutar la petición (con streaming si procede).
3. Aplicar la política activa (Economy/Quality/Offline/Custom).
4. Gestionar respaldos automáticos ante cualquier fallo.
5. Aprender —fuera del hot path— qué modelos funcionan mejor por capacidad.
6. Abstraer por completo a los llamadores de proveedores y nombres de modelos.

**NO contiene**: planificación (TIE), automatización (AE), memoria (MOS), proyectos
(WPMS), agentes (AgentRuntime), prompts de negocio (cada caller construye su
prompt; el MEL lo transporta). **NO gestiona**: embeddings (pertenecen a los stores
del MOS — son parte del motor de indexación, no de la generación; cambiarlos es una
migración RFC-006, no una decisión por-request) ni voz STT/TTS (capa `voice/`
propia, con su propia selección; podría adoptarse como capacidad futura §12).

### 1.1 Relación con lo existente (evolución, no reescritura)

`AIManager` (8 proveedores, health-check, fallback simple a Ollama) NO se borra:
**pasa a ser el Provider Registry interno del MEL**. MEL v1 lo envuelve
(`app/mel/` llama a `ai_manager` para instancias/salud/ejecución); en v2 los
providers se mueven físicamente a `app/mel/providers/` (cambio mecánico, cero
funcional). El `tie/router.py` del doc 14 ("política sobre ai_manager") **queda
como un shim de una línea que delega en el MEL** desde E1 — el TIE conserva su
API interna, el MEL absorbe la política. Nada se rompe; todo se recoloca.

### 1.2 Estructura de módulo (doc 16)

```
backend/app/mel/
├── __init__.py     # API pública: mel.complete(), mel.stream(), mel.policies(),
│                   #   mel.decision_trace(id) — NADA más es importable
├── contracts.py    # Capability, ExecutionRequest/Result, Policy, DecisionTrace — CONGELADOS
├── capabilities.py # taxonomía (§3) + mapeo de call-sites
├── policies.py     # Economy/Quality/Offline/Custom + compilador de políticas (§4-6)
├── decision.py     # Rule Engine (§9.1) — determinista, sin LLM, sin I/O
├── fallback.py     # clasificación de fallos + circuit breakers (§8)
├── executor.py     # ejecución + streaming + registro async de mel_executions
├── registry.py     # Provider Registry (envuelve ai_manager en v1)
├── learning.py     # Learning Engine (§9.2) — job periódico (v2)
├── recommender.py  # Recommendation Engine (§9.3) — propuestas HITL (v2)
└── catalog.py      # scores base por (modelo, capacidad) + coste relativo (§5.1)
```

Frontera dura: ningún módulo fuera de `app/mel/` importa `ai_manager` ni providers
(vigilado por `test_module_boundaries.py`). Migración de call-sites en E2 (§12).

## 2. API pública (contratos congelados)

```python
@dataclass(frozen=True)
class ExecutionRequest:
    capability: Capability            # §3 — NUNCA un nombre de modelo
    prompt: str                       # o messages: list[Message] (uno de los dos)
    system_prompt: str | None = None
    constraints: Constraints = ...    # max_tokens, timeout_s, priority (low|normal|high)
    context_tags: dict = ...          # dominio/proyecto/origen — SOLO para métricas
                                      # y aprendizaje; jamás para seleccionar en v1
    policy_override: str | None = None  # "offline" p.ej. para jobs nocturnos; raro

@dataclass(frozen=True)
class ExecutionResult:
    text: str                         # ya pasado por strip_reasoning (B21) si aplica
    ok: bool; error: str | None
    served_by: ServedBy               # provider, model, attempts, fallbacks_used
    usage: Usage                      # tokens in/out, coste estimado, latencia ms
    decision_id: str                  # enlaza con el DecisionTrace (§9.1)
```

`mel.complete(req) -> ExecutionResult` · `mel.stream(req) -> AsyncIterator[chunk]`
(mismo pipeline de decisión; el streaming aplica `StreamingReasoningFilter`).
Reglas: el caller JAMÁS conoce el modelo elegido salvo leyendo `served_by`
(observabilidad, no control); `context_tags` alimentan el aprendizaje, nunca la
selección determinista de v1 (evita acoplamiento negocio→MEL).

## 3. Sistema de Capacidades (taxonomía)

**Criterio de agrupación** (profesional, no improvisado): una capacidad agrupa
tareas que comparten los TRES ejes que determinan la elección de modelo —
(1) perfil de exigencia (¿cuánto razonamiento?), (2) forma del output (etiqueta /
prosa / estructura / código), (3) sensibilidad a latencia y coste. El *dominio* de
negocio (email, calendario, proyecto) NO define capacidades: viaja en
`context_tags` para que el aprendizaje pueda especializarse después sin fragmentar
la taxonomía hoy.

| Capability | Perfil | Call-sites reales hoy | Futuro |
|---|---|---|---|
| `CLASSIFY` | etiqueta corta, latencia mínima, volumen alto | triaje email etapa 2 (`llm_triage`), Intent Classifier del TIE | routing del AE, moderación |
| `EXTRACT` | estructura (JSON/fecha) desde texto, precisión literal | `extract_meeting_datetime`, detección de reuniones | parsing de facturas, formularios |
| `SUMMARIZE` | condensar sin inventar, coste bajo, batch | summarizer nocturno, briefing, digest, compactación RFC-007 | resúmenes de hilos, minutas |
| `DRAFT` | prosa en nombre del usuario, tono natural | `generate_ai_reply`, respuestas de reunión, plantillas | mensajes Telegram, documentos |
| `CHAT` | conversación general con memoria, streaming | `chat_service` (Electron/Telegram), camino corto del TIE | — |
| `REASON` | razonamiento profundo multi-paso, calidad ante todo | Planner del TIE, decisiones de arquitectura | plan negotiation, análisis complejos |
| `CODE` | generación/edición de código | Claude Code Agent, tareas WPMS | skills de código de la LSL |
| `ANALYZE` | análisis de datos/patrones, batch tolerante | Mission Learning y reflexiones del Learner (doc 15 §5), Learning Engine del propio MEL | AutomationLearner, LLL 2-4 |
| *reservadas* | `RESEARCH` (investigación larga), `VISION` (multimodal), `AGENTIC` (loops de tool-use del runtime) | — | se activan sin migración: el enum es append-only |

Reglas: enum **append-only** (como `MemoryType`); cada call-site declara UNA
capacidad (tabla de mapeo en `capabilities.py` — la revisión E2 migra los ~9
call-sites actuales); si dos futuras tareas exigen perfiles distintos dentro de
una capacidad, se subdivide creando capacidad nueva, nunca redefiniendo la vieja.

## 4. Políticas de ejecución

Una **política** = `{capability → cadena ordenada [primario, respaldo₁…ₙ]}` + metadatos
(límite de coste diario opcional, umbral de calidad mínima). Cuatro políticas:

- **Economy**: para cada capacidad, el candidato más barato cuyo score ≥ umbral
  aceptable (catálogo §5.1); locales primero a igualdad; cadenas terminan siempre
  en el mejor local disponible.
- **Quality**: orden puro por score de capacidad (coste solo desempata); cadenas
  terminan en el mejor cloud alternativo y después el mejor local.
- **Offline**: SOLO proveedores locales. Si una capacidad no tiene local viable,
  la política se marca `degraded` en esa capacidad: el MEL responde con error
  tipado `NoLocalModel` + el Hub/Settings muestran qué falta y qué modelo local
  descargar para cubrirla (sugerencia del catálogo). Nunca llama fuera. Jamás.
- **Custom**: definida por el usuario (§7). Las otras tres son editables, con
  **"Restaurar configuración recomendada"** que re-ejecuta el compilador (§6).

Una política está **activa** globalmente (Settings); `policy_override` por request
existe para jobs (p.ej. el summarizer siempre intenta `offline` primero — política
del caller documentada, no hardcode de modelo).

## 5. Configuración automática (post-wizard)

### 5.1 El catálogo (`catalog.py`)

Extiende el `PROVIDER_CATALOG` existente con, por modelo: `capability_scores`
(0-100 por capacidad, curados y versionados — el prior del aprendizaje),
`relative_cost` (0-100), `is_local`, `context_window`, `notes`. Es DATO editable
(archivo del repo actualizable en cada release), no código. Los scores de catálogo
son el punto de partida; la experiencia real (§9.2) los corrige por usuario.

### 5.2 El compilador de políticas (`policies.py`)

Al cerrar el wizard obligatorio de primer arranque (que YA está definido como
onboarding del MVP beta — roadmap V1.0 criterio 2):

```
entrada:  proveedores conectados + modelos locales detectados (via registry)
por cada política ∈ {Economy, Quality, Offline}:
    por cada capability:
        candidatos = modelos disponibles filtrados por la regla de la política
        cadena = orden según la política (§4), longitud 2-4
salida:   3 políticas compiladas + activa por defecto = Economy si hay ≥1 local
          sano, si no Quality; NUNCA vacías (con un solo proveedor, las tres
          políticas degeneran a cadenas de 1 — válido y explícito)
```

El resultado se muestra al usuario en 1 pantalla-resumen ("Aithera se ha
configurado así — puedes cambiarlo en Ajustes → Inteligencia") y se persiste
(tabla `mel_policies`, JSON versionado con `pristine=true`).

### 5.3 Reconfiguración automática

El MEL se suscribe a eventos del bus (doc 17): `provider.connected`,
`provider.disconnected`, `provider.model_added/removed` (los emite el registry al
detectar cambios en Settings/Ollama). Al recibirlos: recompila las 3 políticas
automáticas **en sombra** y compara con las vigentes:

- Política `pristine` (el usuario nunca la editó) → se actualiza en silencio +
  entrada en el historial ("Economy actualizada: Gemini Flash ahora cubre
  SUMMARIZE").
- Política editada → NO se toca: se crea una **propuesta de actualización**
  (diff por capacidad) que espera al usuario.
- **Custom NUNCA se modifica**: solo aparece el modelo nuevo en la paleta del
  builder, con un badge "nuevo".

**UX de aviso** (decisión): un **punto-ámbar discreto** sobre el icono de Ajustes
y sobre la pestaña "Inteligencia" + una línea en el digest/briefing ("Hay 1
propuesta de configuración de modelos pendiente") + panel de diff con
Aceptar/Rechazar por política. Sin popups modales, sin interrupciones: filosofía
calm-tech coherente con el AVCS y con la cuarentena HITL del Learner (doc 15 §3).

## 6. Botón Restaurar

En Economy/Quality/Offline editadas: "Restaurar configuración recomendada" →
re-ejecuta el compilador con el estado actual de proveedores + scores aprendidos
vigentes, muestra el diff, confirma, marca `pristine=true` de nuevo. El historial
de versiones de política (JSON) permite deshacer (mismo patrón undo del panel
"aprendido").

## 7. Modo Custom (builder drag & drop)

Pantalla "Inteligencia → Personalizado":

- **Izquierda — paleta de capacidades**: cada capacidad es UN chip único (con
  descripción y ejemplos reales al hover). Como cada chip existe una sola vez,
  **la regla "una tarea pertenece a un único bloque" se cumple por construcción**
  — arrastrar un chip a otro bloque lo QUITA del anterior (movimiento, nunca
  copia). Sin validaciones a posteriori: imposible el conflicto.
- **Derecha — bloques**: el usuario crea bloques ("+ Bloque"), les da nombre
  ("Trabajo serio", "Cosas rápidas") y arrastra chips dentro. Cada bloque tiene la
  lista ordenada: **Modelo principal** + Respaldo 1..n (botón "+" añade; drag
  reordena; cada fila es un selector con buscador de los modelos disponibles y su
  badge local/cloud + coste relativo).
- **Bloque implícito "Sin asignar"**: capacidades no arrastradas usan la política
  automática Economy (visible y explicado — nunca hay agujeros).
- Estados de validez: bloque sin modelo → borde ámbar + no se puede activar
  Custom hasta resolverlo. Guardado = nueva versión (undo disponible).
- Accesible sin ratón: cada acción de drag tiene equivalente por menú contextual.

## 8. Sistema de respaldos (fallback)

### 8.1 Clasificación de fallos → acción (determinista)

| Fallo | Detección | Acción |
|---|---|---|
| Sin tokens / cuota agotada | 402/429 con quota | marcar proveedor `exhausted` hasta reset conocido (o 1h) → siguiente de la cadena |
| Rate limit | 429 + retry-after | respetar retry-after solo si < 2 s, si no → siguiente; cooldown en memoria |
| API caída / 5xx / mantenimiento | 5xx, connection error | siguiente + abrir circuit breaker (§8.2) |
| Timeout | > timeout_s del request | 1 reintento inmediato SOLO si el caller marcó la petición idempotente; si no → siguiente |
| Auth inválida | 401/403 | NO rotar en bucle: siguiente + marcar `needs_attention` (punto-ámbar en Settings) |
| Modelo local no descargado | registry | siguiente + sugerencia de descarga en Settings |
| Modelo local ocupado | semáforo lleno (§10) | esperar ≤ 1.5 s en cola corta; si no → siguiente |
| Respuesta vacía / solo razonamiento | post-strip_reasoning vacío | 1 reintento mismo modelo; luego siguiente |
| Error de contenido/prompt inválido | 4xx de validación | **NO rotar** (el fallo es del request, no del proveedor): error tipado al caller |

Presupuesto por request: máx. 3 saltos de cadena y un timeout global
(`constraints.timeout_s` × 1.5). Cadena agotada → `ExecutionResult(ok=False)` con
el historial completo de intentos (el caller decide su degradación — p.ej. el
summarizer cae a plantilla determinista, patrón ya establecido en V0.85).

### 8.2 Circuit breakers

Por (proveedor): `closed → open` con ≥ 3 fallos 5xx/timeout en 60 s; `open`
durante 90 s (se salta sin intentar); `half-open`: 1 sonda; éxito → `closed`.
Estado EN MEMORIA (se pierde al reiniciar: correcto — reiniciar es re-sondear),
espejado al health-cache existente del registry. Cada salto/apertura emite
`mel.fallback` / `mel.breaker_opened` (doc 17) → observabilidad y materia prima
del Learning Engine.

## 9. Decision Engine (crítico)

Tres componentes estrictamente separados. **Justificación frente a "un LLM decide
qué LLM usar"**: una decisión por-request con LLM costaría 300-2000 ms y dinero,
sería no determinista (irreproducible, indepurable), acoplaría la disponibilidad
del selector a un proveedor (fallo circular: ¿quién decide cuando el decisor está
caído?) y aprendería sin control. Separando ejecución (reglas), aprendizaje
(batch) y mejora (propuestas): decisiones en microsegundos y coste cero,
explicables y testeables; el aprendizaje usa modelos potentes sin tocar la
latencia; y ningún cambio de comportamiento ocurre sin evidencia acumulada ni,
cuando importa, sin el usuario.

### 9.1 Rule Engine (tiempo real, sin LLM, sin I/O)

- Entrada: `ExecutionRequest` + estado en memoria (política activa COMPILADA a
  tabla `capability → cadena`, breakers, cuotas, semáforos locales, prioridad).
- Algoritmo: lookup O(1) de la cadena → primer candidato **viable** (breaker
  cerrado, no exhausted, local con hueco) → decisión. Coste: < 1 ms, cero I/O
  (todo estado vive en memoria; la persistencia es asíncrona).
- **Determinista y reproducible**: misma petición + mismo estado ⇒ mismo modelo.
- **Explicable**: produce `DecisionTrace {capability, policy, chain, skipped:
  [(modelo, razón)], chosen, ts}` — en memoria (ring buffer 500) + muestreo
  persistido; consultable vía `mel.decision_trace(id)` y visible en la pantalla
  Actividad. Los scores aprendidos NO se consultan aquí: ya están HORNEADOS en
  las cadenas compiladas (el aprendizaje reordena cadenas offline, no decide online).

### 9.2 Learning Engine (periódico)

- Registro operativo: cada ejecución escribe (async, fuera del hot path) en
  `mel_executions`: capability, provider, model, ok, latencia, tokens, coste,
  reintentos, fallback_reason, decision_id, context_tags.
- **Una sola tabla de verdad con el Learner**: `model_stats` (doc 15 §4) — el MEL
  aporta las señales OPERATIVAS (éxito técnico, latencia, coste, estabilidad,
  disponibilidad); el Learner aporta las señales de CALIDAD humana (correcciones
  posteriores, re-dos, iteraciones por misión, feedback ✓/✎/✗, satisfacción).
  Campos distintos, misma fila (capability × model). Cero duplicación de sistemas.
- Ciclo: job APScheduler nocturno + trigger "N≥200 ejecuciones nuevas". Recalcula
  `learned_score(capability, model)` con: **prior bayesiano** = score de catálogo
  (la evidencia desplaza al prior gradualmente), **decaimiento temporal**
  (half-life 30 días — lo viejo pesa menos), **mínimo de evidencia** (n ≥ 20 por
  celda antes de influir en cadenas), **cambio acotado** (± 10 puntos por ciclo).
  Estas cuatro reglas son la defensa anti-conclusiones-incorrectas: un mal día de
  una API no destrona a un modelo, y un resultado atípico no mueve nada.
- Puede usar un LLM para análisis cualitativo de patrones de fallo (`ANALYZE`,
  ejecutado A TRAVÉS del propio MEL respetando la política activa — en Offline
  usa el mejor local; en Economy el más barato aceptable). Su salida son números
  y etiquetas, jamás decisiones aplicadas.
- Al terminar: recompila EN SOMBRA las cadenas con los nuevos scores → si difieren
  de las vigentes, entrega el diff al Recommendation Engine. Emite `mel.learning_cycle`.

### 9.3 Recommendation Engine (HITL)

Convierte diffs con evidencia en recomendaciones legibles: *"En 42 tareas de CODE,
DeepSeek resolvió con 1.3 iteraciones de media vs 2.7 de X, con −38% de coste.
¿Promoverlo a principal en Economy?"* · *"Gemini lleva 30 días sin usarse — ¿retirar
de las cadenas?"* · *"El nuevo modelo local cubre SUMMARIZE: Offline dejaría de
estar degradado."* Entrega: mismas superficies que §5.3 (punto-ámbar + panel con
Aceptar/Rechazar + línea en el briefing) y misma escalera de confianza del Learner
(doc 15 §3): auto-aplicar SOLO sobre políticas pristine; todo lo demás, propuesta.
Rechazos se registran (el Learner aprende también de los "no").

## 10. Modelos locales y rendimiento

- **Runtime-agnóstico**: el registry trata "local" como un provider más
  (`OllamaProvider` hoy; `LlamaCppProvider`, `VLLMProvider`, o cualquier runtime
  futuro = un provider nuevo que declara sus modelos y capacidades — mismo patrón
  plug-in del AIManager). El MEL solo ve capacidades y flags `is_local`.
- **Concurrencia local**: semáforo por runtime (Ollama: 1-2 slots configurables) —
  evita colas invisibles; `BUSY` es un fallo clasificado (§8.1), no un cuelgue.
- **Hot path**: decisión < 1 ms (§9.1); overhead total del MEL por request < 5 ms
  (objetivo doc 12); registro y eventos async; conexiones httpx persistentes por
  provider (doc 12 A2, ya asignado a V0.9-A2 — el MEL las hereda del registry).
- **Escala**: con decenas de proveedores el coste sigue O(1) — las cadenas están
  precompiladas; añadir proveedor = recompilar políticas (ms, offline).
- Memoria: tablas compiladas + breakers + ring buffer ≈ decenas de KB.

## 11. Experiencia de usuario (pantallas)

Settings → **"Inteligencia"** (sustituye a la actual lista plana de proveedores,
que pasa a ser la pestaña "Proveedores"):

1. **Políticas**: 4 tarjetas (Economy/Quality/Offline/Custom), la activa
   destacada; cada tarjeta expandible muestra la tabla capacidad → cadena con
   badges (local/cloud, coste, "aprendido ↑"); botón Restaurar en las 3
   automáticas; selector de política activa (1 clic).
2. **Personalizado**: el builder drag & drop (§7).
3. **Actividad**: hoy/semana — qué capacidad usó qué modelo, latencias, coste
   estimado acumulado, fallbacks ocurridos (con su razón), estado de breakers.
   Es la cara visible del DecisionTrace: transparencia total.
4. **Recomendaciones**: bandeja de propuestas (§5.3 + §9.3) con evidencia y
   Aceptar/Rechazar.

Wizard de primer arranque: paso "Conecta tu inteligencia" (proveedores + detección
de Ollama) → pantalla-resumen de auto-configuración (§5.2) → listo. Un usuario no
técnico nunca necesita pasar de ahí; el que quiere control absoluto tiene Custom.

## 12. Posición en el roadmap y evolución

**Decisión de ubicación** (el usuario delegó el matiz técnico): tras el TIE v1
pero DENTRO de V1.0, como bloque **E1-E2 entre O4 y O5**. Razones: (1) el TIE v1
ya tiene su router mínimo (14 §Model Router) — no se bloquea; (2) el wizard del
MVP beta (O5) necesita la auto-configuración del MEL: hacerlo antes de O5 evita
construir el onboarding dos veces; (3) el Learning Engine necesita `model_stats`
y señales del Learner (V1.1/V1.2) — separar v1/v2 es obligatorio de todos modos.

| Versión | Alcance MEL | Sesiones |
|---|---|---|
| **V1.0 (E1)** | contratos + capacidades + registry (envuelve ai_manager) + Rule Engine + fallback/breakers + políticas Economy/Quality/Offline con compilador + `policy_override` | 1-1.5 |
| **V1.0 (E2)** | migración de los ~9 call-sites (chat_service, triaje, ai_reply, meetings, summarizer, TIE intents/planner/responder vía shim de router.py) + pantalla Políticas v1 + wizard integrado en O5 + `mel_executions` (solo registro) + tests de contrato | 1-1.5 |
| **V1.2 (v2)** | Learning Engine + Recommendation Engine (con el Learner y `model_stats`) + Custom builder drag&drop + Actividad/Recomendaciones + reconfiguración automática por eventos + presupuestos de coste | 2-3 |
| **V1.5+ (v3, solo si aporta)** | perfiles por proyecto (WPMS: "este proyecto usa Quality"), shadow-testing A/B de un modelo nuevo en % de tráfico, capacidad `VISION`/`RESEARCH` activadas, voz como capacidad | según demanda |

No hay v4 previsible: proveedores nuevos = plug-in; modelos nuevos = catálogo +
aprendizaje; capacidades nuevas = enum append-only. La arquitectura no necesita
rediseño para crecer — esa es la prueba de que está terminada.

## 13. Revisión crítica final (obligatoria)

1. **¿Desacoplado?** Sí: una sola API pública (`mel.complete/stream`); nadie
   fuera importa providers (test de fronteras); el MEL no importa TIE/AE/MOS/WPMS
   — solo `core/events`, `core/config`, y el Learner comparte una TABLA, no código.
2. **¿Responsabilidades duplicadas?** Revisado contra 14/11/15: el TIE decide QUÉ
   hacer y con qué prompt (queda dueño de `requires_planning`); el MEL decide CON
   QUÉ MODELO. El AE decide CUÁNDO. El Learner aporta calidad humana a
   `model_stats`; el Learning Engine del MEL aporta señales operativas a la misma
   tabla — coordinación por datos, cero solape de código. El único punto de roce
   detectado (el `tie/router.py` de doc 14) se resuelve por absorción explícita
   (§1.1) con delta anotado en doc 14.
3. **¿Años sin rediseño?** Contratos congelados + enum append-only + providers
   plug-in + scores como datos + políticas como JSON versionado ⇒ los cambios
   futuros son datos y plug-ins, no arquitectura.
4. **¿Rápido con decenas de proveedores?** O(1) por decisión (cadenas
   precompiladas), estado en memoria, aprendizaje offline. Sí.
5. **¿El aprendizaje mejora de verdad?** Mide experiencia REAL (operativa +
   humana), con prior/decaimiento/mínimos/acotación que garantizan estabilidad, y
   cierra el lazo reordenando cadenas con evidencia. Sí — y es auditable.
6. **¿UX para no técnicos?** El 90% vive con el wizard + política activa (2
   pantallas, 1 clic). El poder (Custom, Actividad) es opt-in. Sí.
7. **¿Preparado para la evolución de los modelos?** Un modelo/proveedor/runtime
   nuevo = provider plug-in + fila de catálogo; el aprendizaje lo calibra al uso
   real del usuario; las políticas se recompilan solas. Sí.

**Simplificaciones aplicadas en esta revisión** (anti-sobreingeniería): sin
selección por context_tags en v1 (solo métrica); sin coste-por-token exacto en v1
(coste relativo del catálogo basta hasta tener presupuestos en v2); sin routing
"por request LLM-assisted" jamás; sin tabla propia de stats (se comparte
`model_stats`); breakers en memoria sin persistencia.

---
*MEL v1.0 — diseño 2026-07-13 (Fable 5). Deltas emitidos: doc 14 (router.py delega
en MEL desde V1.0-E1), roadmap V1.0/V1.2, backlog. Consume: doc 16 (disciplina),
doc 17 (eventos), doc 15 (model_stats compartida), doc 12 (A2 httpx, presupuestos).*
