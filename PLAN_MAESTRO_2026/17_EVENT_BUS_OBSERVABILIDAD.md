# 17 — Event Bus & Runtime Observability Foundation

> **Origen**: briefing del usuario 2026-07-12 ("Event Bus & Runtime Observability
> Foundation"). **Gobernado por**: doc 16 (prioridad máxima — este diseño es un
> ejercicio de contención, no de ambición).
>
> **Qué es**: la especificación canónica de `app/core/events.py` — el pub/sub
> in-process que el doc 16 §4.3 introdujo y que nace en V0.85 M2 (doc 07 §6 [Δ]).
> Este doc lo eleva de "~50 líneas mencionadas de pasada" a contrato formal, y
> reserva el punto de conexión para un futuro Runtime Intelligence (V2.0+).
>
> **Qué NO es**: aquí NO se diseña Runtime Intelligence, ni telemetría con
> métricas, ni dashboards, ni análisis, ni optimizadores. Solo la infraestructura
> mínima para que todo eso pueda existir algún día **sin tocar ningún módulo**.

---

## 1. Decisión y encaje

| Campo | Valor |
|---|---|
| Qué se construye | `app/core/events.py`: `emit` / `subscribe` / `unsubscribe` + contrato `Event`. **Nada más** |
| Cuándo | V0.85 sprint M2 (ya planificado — doc 07 §10); el resto de módulos emiten cuando nacen, no antes |
| Tamaño objetivo | ≤ 80 líneas de implementación + `test_events.py` |
| Qué se reserva | el enganche del futuro Runtime Intelligence: `subscribe("*", collector)` — una línea, detrás de un flag, en el lifespan (V2.0+) |
| Qué se prohíbe | que el bus crezca: sin persistencia, sin replay, sin prioridades, sin colas, sin red, sin brokers (Kafka/RabbitMQ/Redis/gRPC/REST interno — prohibidos por Principio 12) |

**El bus es una notificación, no un mecanismo de control.** La fuente de verdad
operativa siguen siendo las tablas SQL y los traces del TIE (doc 14). Ningún
módulo puede DEPENDER de que un evento sea consumido: si B necesita que A haga
algo, B llama a la API pública de A (doc 16 §4.1); el bus existe solo para el
acoplamiento inverso (avisar hacia arriba sin importar al consumidor) y para que
el funcionamiento del sistema sea observable en el futuro.

## 2. El Event Bus — API completa (y final)

```python
# backend/app/core/events.py — TODO el sistema es esto:

@dataclass(frozen=True)
class Event:
    name: str          # "memory.ingested" — convención §3
    source: str        # módulo emisor: "mos" | "tie" | "automation" | "learner"
                       #                | "skills" | "ai" | "gateway" | "core"
    ts: datetime       # UTC; lo estampa el bus en emit(), no el emisor
    payload: dict      # plano, pequeño, JSON-serializable — reglas en §2.2

Handler = Callable[[Event], Awaitable[None]]   # los handlers son async

def subscribe(name: str, handler: Handler) -> None:
    """name = nombre exacto ("mission.completed") o "*" (todos los eventos).
    El comodín existe por UNA razón: es el punto de conexión de la telemetría
    futura (§6). No hay patrones parciales ("mission.*") — YAGNI."""

def unsubscribe(name: str, handler: Handler) -> None: ...

def emit(name: str, source: str, payload: dict | None = None) -> None:
    """No bloqueante y a prueba de todo:
    - construye el Event (estampa ts) y busca handlers de `name` + de "*";
    - cada handler se programa con asyncio.create_task envuelto en try/except
      que LOGUEA y traga — un handler roto JAMÁS afecta al emisor ni a otros
      handlers;
    - sin handlers registrados, emit() es un lookup de dict y un return
      (~microsegundos): emitir hacia el vacío es gratis, y es el caso normal
      durante años para la mayoría de eventos."""
```

Registro interno: `dict[str, list[Handler]]` a nivel de módulo. Sin clases, sin
singleton ceremonioso, sin decoradores mágicos. Un desarrollador nuevo lo lee
entero en cinco minutos.

### 2.1 Justificación campo a campo (lo que entra y lo que NO)

| Campo | Veredicto | Razón |
|---|---|---|
| `name` | ✅ | identidad del evento |
| `source` | ✅ | la telemetría futura necesita atribución por módulo; cuesta un string |
| `ts` | ✅ | orden temporal para cualquier consumidor; lo pone el bus → consistente por construcción |
| `payload` | ✅ | los datos del hecho |
| `priority` | ❌ | no hay colas ni orden de despacho que priorizar: todos los handlers se programan igual. Sería un campo muerto durante años. Si un evento fuera "urgente", esa es una decisión del CONSUMIDOR, no un atributo del mensaje |
| `version` | ❌ | regla de evolución en su lugar (§3.3): payloads solo aditivos; cambio incompatible = evento de nombre nuevo. Un `version` por evento es burocracia sin consumidor |
| `id` (uuid por evento) | ❌ | nadie correlaciona eventos individuales hoy; si la telemetría futura lo necesita, lo genera ELLA al persistir |
| `correlation_id` | ❌ como campo | convención de payload en su lugar: cuando el hecho pertenece a una misión/regla, el payload incluye `mission_id` / `rule_id` (§3.2). Mismo valor, cero esquema extra |

### 2.2 Reglas del payload (las que protegen el futuro)

1. **Plano y pequeño**: dict de un nivel, valores escalares/listas cortas,
   < 1 KB. Un evento es un titular, no el artículo.
2. **Metadatos, nunca contenido**: ids, contadores, duraciones, estados,
   nombres de modelo — JAMÁS cuerpos de email, texto de conversaciones ni datos
   personales. Así, cualquier telemetría futura es inocua por construcción
   (misma filosofía que el PrivacyFilter, 08 RFC-001): no puede filtrar lo que
   nunca viajó.
3. **Datos ya calculados**: emitir jamás computa nada nuevo. Si el módulo no
   tiene el dato en la mano al terminar su trabajo, el dato no va en el evento.
4. **JSON-serializable**: para que un consumidor futuro pueda persistir sin
   adaptadores.

## 3. Naming convention

### 3.1 La forma

**`<dominio>.<hecho_en_pasado>`** — minúsculas, snake_case, en inglés:
`memory.ingested`, `email.triaged`, `mission.completed`, `approval.resolved`,
`skill.validated`, `model.call_completed`.

Por qué así y no `MissionStarted` (PascalCase del briefing): (a) es la forma ya
sembrada en los docs 07/11/14/16 — cambiarla ahora crearía dos convenciones;
(b) el prefijo de dominio hace el grep trivial (`grep "mission\."`) y agrupa
visualmente; (c) snake_case es Python idiomático. El contenido semántico es
idéntico.

### 3.2 Las reglas (filosofía, no catálogo)

1. **Pasado, siempre**: un evento es un HECHO consumado (`ingested`, no
   `ingest`). El bus nunca transporta órdenes ni peticiones — para pedir algo
   está la API pública del módulo. Esta regla sola impide que el bus degenere
   en un sistema RPC encubierto.
2. **Dominio = área semántica**, no nombre de archivo: `memory.*`, `email.*`,
   `mission.*`, `approval.*`, `automation.*`, `skill.*`, `learning.*`,
   `model.*`. El campo `source` ya dice qué módulo fue; el prefijo dice de qué
   se habla.
3. **Fronteras, no interioridades**: se emite al cerrar una unidad de trabajo
   observable (job terminado, misión cerrada, aprobación resuelta, skill que
   cambia de estado). Nunca "estoy en la línea 3 de mi bucle".
4. **Correlación por payload**: si el hecho pertenece a una misión/regla/skill,
   el payload lleva `mission_id`/`rule_id`/`skill_id`.
5. **Presupuesto de frecuencia — LA regla que mantiene el bus gratis**: nada
   que ocurra a más de ~1 evento/segundo sostenido entra al bus. Prohibido:
   chunks de streaming, tokens, frames del AVCS, ticks de polling. Todo lo que
   pasa esta regla suma, en la práctica de Aithera V1.x, **cientos de eventos
   al DÍA** — no por segundo.
6. **Sin catálogo especulativo**: un evento se añade cuando su módulo se
   implementa y el dato está en la mano (regla §2.2.3) — no se diseñan cientos
   de eventos por adelantado. La tabla de §4 es la semilla completa prevista
   hasta V1.2 y cabe en media pantalla.

### 3.3 Evolución sin versiones

Los payloads solo cambian AÑADIENDO claves (los consumidores usan `.get()`).
Si un evento necesita cambiar incompatiblemente de significado, se crea uno
nuevo con nombre más preciso y el viejo se deja de emitir (grep encuentra a los
suscriptores en segundos — es un monorepo, doc 16). Sin registros de esquemas,
sin negociación de versiones: eso es maquinaria de sistemas distribuidos que no
somos.

## 4. Integración — cuándo emite cada módulo (semilla completa hasta V1.2)

Regla general: **cada módulo emite en sus fronteras naturales, con datos que ya
tiene, y a nadie le importa si alguien escucha.** Cero cambios de lógica.

| Módulo (`source`) | Evento | Payload típico | Versión |
|---|---|---|---|
| MOS (`mos`) | `memory.ingested` | `{job, items_new, duration_ms}` | V0.85 M2 |
| MOS | `email.triaged` | `{email_id, category}` | V0.85 M2 |
| MOS | `memory.compacted` | `{pruned, merged, tier}` | V0.9 (lifecycle prune) |
| Automation (`automation`) | `automation.rule_fired` | `{rule_id, trigger, ok, duration_ms}` | V0.9 |
| Automation | `approval.requested` / `approval.resolved` | `{gate_id, action, resolution?}` | V0.9 |
| TIE (`tie`) | `mission.started` / `mission.completed` / `mission.cancelled` | `{mission_id, source, nodes, tokens, duration_ms, ok}` | V1.0 |
| AI (`ai`) | `model.call_completed` | `{provider, model, tokens, duration_ms, ok, purpose}` | V1.0 — EL evento más valioso para la telemetría futura (latencias/coste), y son datos que el AIManager ya tiene al volver cada llamada |
| Skills (`skills`) | `skill.created` / `skill.status_changed` | `{skill_id, status, from}` | V1.1 |
| Learner (`learner`) | `learning.proposed` / `learning.consolidated` | `{kind, ref_id, risk_class}` | V1.1 |
| TIE | `node.state_changed` | `{mission_id, node_id, state}` | V1.2 — cuando exista su consumidor real (vista del grafo en el Hub); hasta entonces NO se emite |
| Gateway (`gateway`) | — nada — | los traces ya cubren la actividad de canal; se añadirá si la telemetría lo pide | — |

**AVCS (caso especial)**: el bus vive en el proceso del backend; el AVCS es
frontend. NO se inventa un bus espejo en el navegador ni un WebSocket de eventos
hoy. El AVCS sigue recibiendo estado por las vías existentes (API + SSE del
chat). Punto de extensión reservado (no construir): un endpoint SSE de solo
lectura `GET /api/events/stream` que re-emita eventos seleccionados hacia el Hub
— V1.2+ y SOLO si la vista viva del grafo de misiones lo justifica. Eventos
propios del frontend (`animation.changed`) quedan fuera de alcance hasta que
exista un consumidor que los necesite.

**Consumidores internos ya previstos** (los que justificaron `events.py` en el
doc 16): `EventTrigger` del AE se suscribe a `memory.ingested`/`email.triaged`
(V0.9); el Learner a `mission.completed` (V1.1); el executor del TIE a
`approval.resolved` (V1.0). Nótese la simetría: los módulos usan el bus
exactamente igual que lo usaría la telemetría futura — no hay dos mecanismos.

## 5. Runtime Telemetry — solo la infraestructura (que ya quedó descrita)

No se implementa NADA de telemetría ahora. La infraestructura necesaria es,
íntegramente, lo ya especificado: (1) el comodín `subscribe("*")`; (2) el
contrato `Event` con `source`/`ts`/payload de metadatos; (3) la regla de
frecuencia §3.2.5 que garantiza volumen trivial; (4) la regla de privacidad
§2.2.2 que garantiza inocuidad.

Un colector futuro será, literalmente:

```python
# futuro módulo de telemetría — NO construir ahora
async def collector(event: Event):
    await telemetry_store.append(event)   # SU almacén (SQLite/parquet propio),
                                          # JAMÁS el MOS: el MOS guarda conocimiento
                                          # del usuario, no métricas del sistema
subscribe("*", collector)                 # ← una línea, detrás de un flag de Settings
```

Muestreo, agregación, retención y dashboards son problemas del colector, no del
bus. Si el colector se cae o se desactiva, Aithera ni se entera — esa es la
prueba de que el diseño es correcto.

## 6. Runtime Intelligence — el punto de conexión reservado (NO diseñar)

En una futura V2.0+, un módulo `app/runtime_intel/` podrá:

1. Suscribirse con `subscribe("*", ...)` — **cero cambios en MOS, TIE, Learner,
   AE o AVCS**: llevan años emitiendo estos eventos para entonces.
2. Persistir en su propio almacén y analizar en batch (patrón jobs del doc 09
   §2.3: micro-batch, idle, Ollama-first).
3. **Proponer, jamás modificar**: sus sugerencias entran por la MISMA cuarentena
   del Learning System (doc 15 §3, clase de riesgo ALTA → siempre HITL) y se
   presentan en el mismo panel de aprendizaje. Observa, aprende, propone — la
   decisión es del usuario, como en todo Aithera.

Deslinde para evitar un futuro god-module: el **Learner** (doc 15) estudia el
TRABAJO DEL USUARIO (skills, preferencias, patrones de tareas); el **Runtime
Intelligence** estudiará el COMPORTAMIENTO DEL SISTEMA (latencias, cuellos de
botella, coste, infrautilización). Objetos de estudio distintos, misma
disciplina (observar → proponer con cuarentena), y comparten el pipeline de
validación — no la implementación.

La lista completa de capacidades a largo plazo (detectar cuellos de botella,
analizar coste en tokens, sugerir paralelización/cacheo/lazy loading, generar
informes técnicos priorizados por impacto, etc.) queda registrada en el briefing
de origen como VISIÓN — deliberadamente sin diseño. Lo único que este documento
garantiza es que, cuando llegue el momento, nada de la arquitectura actual lo
impida: y con §2+§4, no lo impide.

## 7. Performance — el análisis pedido

| Dimensión | Coste | Detalle |
|---|---|---|
| CPU por `emit` sin suscriptores | ~0.1-1 µs | un lookup de dict + return. Es el caso mayoritario durante años |
| CPU por `emit` con k handlers | ~2-5 µs × k | construcción del dataclass + k × `create_task`. El trabajo del handler corre después, async, fuera del camino del emisor |
| CPU total estimada | **< 10 ms/día** | a ~1.000 eventos/día (estimación generosa para V1.x con la regla §3.2.5) |
| RAM | < 10 KB | el registro de suscripciones. Los eventos NO se almacenan (sin buffer, sin historia) — se despachan y se destruyen |
| Latencia añadida a operaciones | 0 medible | `emit` nunca espera a los handlers; nunca hay red ni serialización |
| Startup | ~0 ms | importar un módulo de 80 líneas; sin conexiones, sin hilos, sin inicialización |
| Ejecución continua | 0 | sin hilos propios, sin polling, sin timers: el bus solo existe cuando alguien emite |

Los dos guardarraíles que mantienen estos números para siempre: la regla de
frecuencia (§3.2.5) y la prohibición de persistencia/replay (§1). Si alguna vez
una medición contradice esta tabla, el bug estará en un handler lento mal
concebido — y el aislamiento de §2 garantiza que ni así se frena al emisor.

## 8. Semántica de fallos (explícita, para que nadie asuma de más)

- **At-most-once, best-effort**: sin reintentos, sin persistencia, sin replay.
  Un reinicio pierde los eventos en vuelo — correcto, porque nada crítico
  depende del bus (§1). Lo crítico ya vive en SQL (gates, grafos, jobs).
- **Sin garantía de orden** entre handlers ni entre eventos concurrentes.
- **Aislamiento total**: excepción en un handler → log + nada más.
- **Test** (`test_events.py`, V0.85 M2): subscribe/emit/unsubscribe, comodín,
  aislamiento de excepciones, emit sin suscriptores, payload inmutable (frozen).

## 9. Revisión crítica (las preguntas del briefing)

1. **¿Elegante o útil?** Útil: 3 funciones, 1 dataclass, 4 consumidores internos
   con fecha (AE, Learner, executor, tests) ANTES de hablar de telemetría. La
   telemetría futura es beneficio marginal de algo que ya se paga solo.
2. **¿Existe una versión más simple?** Sí: callbacks ad-hoc entre módulos
   (la ingesta con una lista de callbacks, el tracer con otra). Se rechaza
   porque son N mini-buses sin contrato — más código total, imports circulares
   de vuelta, y el futuro colector tendría que enchufarse en N sitios. Esta es
   la versión más simple QUE CUMPLE el objetivo; una más simple no lo cumple.
3. **¿Frameworkitis?** Los síntomas serían: prioridades, versionado por evento,
   patrones de suscripción, buffer de historia, puente a red, catálogo
   especulativo de eventos. Los seis se evaluaron y se rechazaron
   explícitamente (§2.1, §3.3, §4-AVCS, §3.2.6). Lo que queda no se puede
   recortar sin perder el objetivo.
4. **¿Lo entiende un dev nuevo en menos de una hora?** En ~10 minutos: 80
   líneas, tres funciones, una tabla de eventos. La convención cabe en 6 reglas.
5. **¿Futuro preparado sin complicar el presente?** Sí, verificable: el coste
   presente es ≤ 80 líneas + emits de una línea en fronteras que ya existen; y
   el futuro Runtime Telemetry → Intelligence → Optimizer se conecta entero con
   `subscribe("*")` sin tocar un solo módulo. Si algún día el bus "necesita"
   crecer para soportarlo, la respuesta correcta será revisar el consumidor,
   no el bus.

---
*Diseño 2026-07-12 (Fable 5). Especificación canónica de `app/core/events.py`
(sembrado en 16 §4.3; nace en V0.85 M2 — doc 07 §6/§10 [Δ]). Consumidores:
11 (EventTrigger), 14 (`mission.*`/`approval.resolved`), 15 (Learner). El
Runtime Intelligence de §6 es visión V2.0+: reservado, no diseñado.*
