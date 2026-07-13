# 16 — Principios Maestros aplicados: modularidad sin frameworkitis

> **Origen**: briefing del usuario 2026-07-12 ("AITHERA — Principios Maestros de
> Arquitectura (NO Frameworkitis)"). **Este documento tiene prioridad sobre cualquier
> otro documento técnico del plan**: si un RFC contradice estos principios, prevalecen
> estos. Los docs 14 (TIE) y 15 (Learning System) ya nacieron filtrados por él.
>
> Estructura: §1 los 17 principios (forma normativa condensada) · §2 la respuesta a
> las dos preguntas de viabilidad · §3 el mapa de módulos de Aithera · §4 reglas de
> frontera ejecutables · §5 lo que NO hacemos · §6 criterios de extracción futura.

---

## 1. Los principios (normativa condensada — el briefing original gobierna)

| # | Principio | Regla operativa |
|---|---|---|
| 1 | **Aithera es el producto** | No construimos plataforma para terceros; todo existe para un mejor Aithera |
| 2 | **Aithera es el primer consumidor** | Los grandes sistemas se diseñan como módulos reutilizables — solo arquitectónicamente. NO repos aparte, NO paquetes publicados, NO SDKs, NO APIs REST internas, NO microservicios |
| 3 | **Monorepo** | Todo vive en este repositorio; compila junto, se ejecuta junto, se importa directo. Nunca HTTP entre módulos |
| 4 | **Librerías internas** | Cada gran sistema = un paquete Python importable (`from app.memory import memory_router`). Cero procesos independientes |
| 5 | **Sin frameworkitis** | Toda capa de abstracción justifica su existencia o no existe. Factoría que envuelve factoría = borrar |
| 6 | **La modularidad es un medio** | Solo se modulariza con razón clara. Módulos válidos: MOS, TIE, Learner, Automation, Skill System, AVCS, Gateway, AI/Model Provider. No módulos para componentes pequeños |
| 7 | **Un módulo debe poder ser producto** | Test: "¿podría existir un repo GitHub independiente con este nombre?" Si no → no es módulo |
| 8 | **Responsabilidad única** | MOS recuerda, nunca planifica. TIE piensa, nunca almacena ni automatiza. AE ejecuta automatizaciones, nunca decide objetivos ni aprende. Learner aprende, nunca planifica. AVCS visualiza, nunca decide |
| 9 | **Bajo acoplamiento** | Un módulo conoce las interfaces públicas de los demás, jamás su implementación (TIE → `IMemoryStore`, nunca → ChromaDB) |
| 10 | **Alta cohesión** | El código relacionado vive junto; no repartir una responsabilidad entre módulos |
| 11 | **Arranque rápido** | Lazy loading: al iniciar solo UI + AVCS + Voice + gateway; el resto se carga al primer uso (coherente con doc 12 A1) |
| 12 | **El rendimiento es prioritario** | Comunicación *entre módulos de Aithera* = llamadas directas en memoria. Prohibido HTTP/REST/gRPC/sockets/procesos **como mecanismo de comunicación interna** entre esos módulos. **Aclaración (2026-07-13)**: NO prohíbe el aislamiento por proceso como medida de seguridad (p.ej. sandboxear ejecución de código no confiable/generado por IA en el futuro Agente del TIE, V1.0) — eso lo gobierna AOS principio 5 (ejecución controlada), no este |
| 13 | **Código comprensible** | Un dev nuevo entiende la arquitectura en horas. Si algo necesita 40 páginas, es demasiado complejo |
| 14 | **Sin sobreingeniería** | La solución más sencilla que permita evolucionar mañana. Nada "por si acaso". Si entra en tensión con el principio 17 sobre una decisión concreta, decide la Regla de Oro de abajo (simplicidad antes que escalabilidad) |
| 15 | **Aithera es el banco de pruebas** | Un módulo solo se considera extraíble tras meses de estabilidad dentro de Aithera. Nunca antes |
| 16 | **El usuario no nota la arquitectura** | Se siente UNA IA, no diez sistemas conectados |
| 17 | **Diseñar a cinco años** | "¿Tomaría esta decisión con un millón de usuarios y cinco años de evolución?" — sobre la CALIDAD de las fronteras del código (que un cambio futuro no obligue a reescribirlo todo), nunca sobre construir infraestructura de escala real (eso lo prohíbe AOS principio 6). Si entra en tensión con el 14, decide la Regla de Oro |

**Regla de Oro (orden inviolable)**: 1. Simplicidad · 2. Claridad · 3. Rendimiento ·
4. Mantenibilidad · 5. Escalabilidad · 6. Modularidad · 7. Reutilización.

---

## 2. Las dos preguntas de viabilidad — respondidas antes de aplicar

### 2.1 ¿Ralentiza el producto para el consumidor?

**No — coste de ejecución ≈ 0, con dos condiciones ya impuestas por los principios.**

- Un "módulo" aquí es un paquete Python con una API pública. Llamar
  `memory_router.context(...)` a través de una interfaz `ABC` cuesta nanosegundos:
  es una llamada de método en el mismo proceso. La sobrecarga medible aparece solo
  si se introduce serialización o red entre módulos — y el Principio 12 lo prohíbe.
- El riesgo real de rendimiento no es la modularidad sino la **carga** (imports
  pesados en el arranque). Condición 1: lazy loading (Principio 11) — ya es el fix
  A1 del doc 12 (ChromaDB init en background) y se generaliza: ningún módulo pesado
  se importa/inicializa hasta el primer uso o en background post-arranque.
- Condición 2: los **presupuestos vinculantes** del doc 12 §4 se mantienen como
  contrato de cada API pública (p.ej. `context()` ≤ 300 ms). La modularidad no
  exime del presupuesto; lo hereda.

### 2.2 ¿Ralentiza el desarrollo?

**No — si se aplica AHORA, antes de construir MOS/TIE/AE. El coste real es
disciplina, no trabajo.** Hacerlo hoy cuesta: (a) acordar el mapa de módulos (§3 —
ya coincide ~1:1 con las carpetas planificadas), (b) exponer la API pública de cada
módulo en su `__init__.py`, (c) un test de fronteras (~1 hora). Hacerlo en V1.2 con
MOS+TIE+AE ya construidos costaría un refactor multi-sesión de imports y contratos.
Es el mismo razonamiento de la Opción B del MOS (doc 07): arquitectura definitiva,
implementación mínima, deuda ≈ 0.

**Veredicto: SE APLICA, con efecto inmediato, empezando por V0.85 (sprint M1 del MOS).**

---

## 3. El mapa de módulos de Aithera

El "packages/" conceptual del briefing se materializa como paquetes Python bajo
`backend/app/` (y el AVCS en `frontend/`). **No se mueven carpetas**: la estructura
actual ya ES el monorepo modular; renombrar rutas hoy sería churn sin valor para el
usuario (Regla de Oro #1). Si algún día se extrae un módulo (§6), se mueve entonces.

| Módulo (nombre producto) | Paquete | API pública (por `__init__.py`) | Estado |
|---|---|---|---|
| **MOS** — Memory Operating System | `backend/app/memory/` | `memory_router` (IMemoryStore), `decision_service`, tipos de `interfaces.py` | V0.85 (docs 07/08) |
| **TIE** — Task Intelligence Engine | `backend/app/tie/` | `tie.handle(envelope)`, `tie.submit_mission(...)`, contratos `Mission/TaskGraph/TaskNode`, `AgentRuntime` | V1.0 (doc 14; antes "Orchestrator", doc 11-B) |
| **Learner** — Aithera Learning System | `backend/app/learner/` | `learner.record(...)` (pasivo), jobs de análisis/reflexión | V1.0 básico → V1.1+ (docs 09/15) |
| **Automation Engine** | `backend/app/automation/` | `automation_engine`, `ApprovalGate` | V0.9 (doc 11-A) |
| **Skill System** (LSL) | `backend/app/skills/` | `skill_library` (Skill API), `LocalSkill` | stub V0.85 → V1.1 (doc 09) |
| **WPMS** — Workspace & Project Mgmt | `backend/app/workspace/` | `workspace_service`, modelos Project/Milestone/Task | V0.87 (doc 18) |
| **Gateway** | `backend/app/gateway/` | `gateway`, `MessageEnvelope`, `ChannelAdapter` | ✅ V0.8 |
| **AI / Model Provider** | `backend/app/ai/` | `ai_manager`, `strip_reasoning` | ✅ (8 proveedores) |
| **Tools** | `backend/app/tools/` | `tool_manager`, `BaseTool` | ✅ V0.5 |
| **AVCS** | `frontend/src/avcs/` | componentes React del organismo visual | Fase 0 (doc 13) |
| *(compartido)* núcleo | `backend/app/core/` | config, logging, secrets, **`events.py` (nuevo, §4.3)** | ✅ + Δ |

Notas de mapeo contra el briefing del usuario:
- `graph-engine` NO es módulo propio: es un submódulo del TIE (`app/tie/graph.py`).
  Falla el test del Principio 7 *hoy* (sería una carpeta de 2 archivos); si madura y
  otro consumidor lo necesita, se promociona (Principio 15).
- `model-router` NO es módulo propio: `app/ai/` ya es el proveedor multi-modelo; la
  *política* de routing (barato/potente por nodo) vive en el TIE (doc 14 §3.5).
- `context-engine` NO es módulo propio: es la Context API del MOS (doc 08 RFC-002).

## 4. Reglas de frontera (ejecutables, no aspiracionales)

### 4.1 API pública = `__init__.py`

Cada módulo exporta su API pública en su `__init__.py`. Todo lo demás es interno.
Regla de import: **desde fuera de un módulo solo se importa su raíz**
(`from app.memory import memory_router` ✅ · `from app.memory.stores.local_store
import LocalMemoryStore` ❌ salvo dentro de `app/memory/`).

### 4.2 Dirección de dependencias (el grafo permitido)

```
gateway ──▶ TIE ──▶ AgentRuntime ──▶ tools ──▶ (mundo)
   │         │  └──▶ ai (modelos)      ▲
   │         └──▶ MOS ◀── learner ─────┘ (lee traces/errores; escribe por APIs MOS/Skills)
   │                ▲
automation ─────────┘  (AE ──▶ TIE para tareas no triviales; AE ──▶ MOS para briefing)
skills ──▶ MOS (espejo mem_skill)      core ◀── todos (config/log/events; core no importa a nadie)
```

Prohibiciones concretas: MOS no importa TIE/AE/learner (el que recuerda no piensa);
learner no importa gateway (aprende de datos, no de canales); AE no importa ai
directamente (si necesita inteligencia, delega en el TIE — doc 14 §4.2); nadie
importa implementaciones de stores de otro módulo.

### 4.3 Acoplamiento inverso = eventos, no imports

Cuando un módulo de "abajo" necesita avisar hacia "arriba" (la ingesta del MOS
avisa al AE; el TIE avisa al Learner al cerrar misión) **no importa al consumidor**:
emite un evento en `app/core/events.py` — un pub/sub en memoria, síncrono al
publicar, handlers async, ≤80 líneas, sin dependencias. Eventos iniciales:
`memory.ingested`, `email.triaged` (V0.85 M2), `mission.completed`,
`approval.resolved` (V0.9/V1.0). Es LA pieza que evita imports circulares en todo
el Cognitive Runtime. No es un message broker; si alguien propone Redis/colas para
esto, releer Principio 12. **Especificación canónica: doc 17** (contrato `Event`,
convención de nombres, semilla de eventos por módulo, y el punto de conexión
reservado para la observabilidad/Runtime Intelligence futura vía `subscribe("*")`).

### 4.4 Enforcement: `test_module_boundaries.py`

Test (nace en V0.85 M1, ~1 h): recorre los imports de `backend/app/` (AST o
grep) y falla si (a) un import cruza a internals de otro módulo, (b) aparece una
arista prohibida del grafo §4.2. Los tests de contrato por interfaz
(`test_memory_contracts.py`, etc.) siguen siendo la definición ejecutable de cada
API. Juntos, estos dos tipos de test SON la arquitectura — no hay documento que
proteja fronteras mejor que un test rojo.

## 5. Lo que explícitamente NO hacemos

1. **No** repos independientes, paquetes PyPI/npm, SDKs ni versionado semver
   interno entre módulos (compilan y se despliegan juntos).
2. **No** REST/gRPC/sockets/colas entre módulos del backend. El único HTTP es el
   de FastAPI hacia los clientes (Electron/Telegram/Web) — que son otro programa.
3. **No** mover `backend/app/` a `backend/packages/` hoy. Reevaluar solo si se
   extrae el primer módulo real.
4. **No** interfaces especulativas: una interfaz existe cuando tiene ≥2
   implementaciones reales o planificadas con fecha (`IMemoryStore` ✅ — local hoy,
   swap RFC-006 mañana; una `IGatewayRouter` ❌ — solo hay un gateway).
5. **No** DI containers, ni service locators, ni capas "manager de managers".
   Singletons a nivel de módulo (patrón `ai_manager`) + inyección por parámetro
   donde importa el aislamiento (patrón `AgentRuntime.execute_task(memory, tools,
   gate)` del doc 10 — que ya es ejemplar).

## 6. Extracción futura de un módulo (Principio 15)

Criterios acumulativos para considerar extraer (p.ej. el MOS como producto):
(1) ≥ 6 meses estable dentro de Aithera; (2) suite de contrato completa y verde;
(3) cero imports a internals de Aithera (solo su API pública ya lo garantiza);
(4) un segundo consumidor REAL esperando (no hipotético — Principio 14);
(5) decisión explícita del usuario. Hasta entonces: los módulos maduran aquí.

---

## Revisión crítica obligatoria (checklist del briefing, respondida)

- **¿Módulos innecesarios?** Se rechazaron 3 del briefing (graph-engine,
  model-router, context-engine como módulos propios — §3). El learner como módulo
  separado de skills SÍ se justifica: responsabilidades distintas (aprender vs
  almacenar/ejecutar skills) y ciclos de vida distintos.
- **¿Capas sin valor?** El event bus podría parecerlo — no lo es: tiene 4
  consumidores identificados con fecha y elimina imports circulares reales.
- **¿Solución más simple?** La alternativa "todo en app/ sin reglas" es más simple
  hoy y un monolito enredado en V1.2. La alternativa "packages/ + build tooling"
  es más pura y puro churn. Esto es el mínimo que evoluciona.
- **¿Se complica el flujo de ejecución?** No: sigue siendo llamadas directas; los
  eventos solo sustituyen imports que habrían sido circulares.
- **¿Se sacrifica rendimiento por elegancia?** No (§2.1). ¿Mantenibilidad? Mejora:
  las fronteras las vigila un test, no la memoria de nadie.
- **¿El usuario nota diferencia positiva?** Sí, indirecta: arranque rápido
  (Principio 11 forzado), y cada subsistema puede degradar sin tumbar al resto
  porque las fronteras son reales.

---
*Diseño 2026-07-12 (Fable 5). Gobierna a los docs 14 y 15 y, retroactivamente, a
07-13 (sin cambios de contrato: ya cumplían). Primera aplicación: V0.85 sprint M1.*

*Revisión 2026-07-13: aclaraciones en los principios 12, 14 y 17 tras una revisión
crítica pedida explícitamente por el usuario ("¿hay algún principio ambiguo o
peligroso?"). Ninguno se elimina ni se contradice a sí mismo — se cierran bordes
que una lectura literal futura (de un dev nuevo o de otra sesión sin este
contexto) podría aplicar mal: (12) el rendimiento no prohíbe sandboxing por
seguridad, solo HTTP/colas entre módulos; (14/17) la tensión "nada por si acaso"
vs "diseña a cinco años" ya tenía árbitro (la Regla de Oro) pero ningún principio
apuntaba a él. Auditoría del historial real del proyecto: no se encontró ningún
caso en que una decisión ya tomada se hiciera mal por esta ambigüedad (el CORS
abierto a `*` se corrigió correctamente en V0.8 pese a la redacción antigua del
principio 1 en AOS) — esto cierra el riesgo antes de que cause un error, no
corrige uno ya cometido.*
