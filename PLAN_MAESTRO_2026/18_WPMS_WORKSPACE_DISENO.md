# 18 — WPMS: Workspace & Project Management System (V0.87)

> **Origen**: briefing del usuario 2026-07-12 ("AITHERA — WPMS"). **Gobernado
> por**: doc 16 (principios — NO frameworkitis). **Posición**: V0.87, entre V0.85
> (MOS) y V0.9 (Automation Engine). **Módulo**: `backend/app/workspace/` +
> `frontend/src/pages/Workspace/`.
>
> **Consume**: MOS (Project Memory, doc 07/08 — la capa `mem_project` ya existe en
> V0.85), Event Bus (doc 17), tools/agents existentes. **Es consumido por**: TIE
> (doc 14), Automation Engine (doc 11-A), Learner (doc 15), Orchestrator/briefing.
>
> **Regla rectora** (del briefing): cada dato debe responder *"¿podrá Aithera
> usarlo para ayudar mejor al usuario?"*. Si no → no existe. Este doc borra más
> campos de los que añade respecto al briefing, y lo justifica.

---

## 0. Aviso de impacto en el MOS (lo que el usuario pidió señalar)

**El WPMS NO cambia ningún contrato del MOS. Un solo punto de replanificación,
menor:**

- El WPMS es el **primer escritor real de `mem_project`** (`MemoryType.PROJECT`,
  ya definido en doc 07 §3/§4). En V0.85 esa colección estaba prevista como *"stub:
  pocas escrituras"*. Con el WPMS pasa a recibir escrituras regulares (los
  destilados de proyecto — §5.1). **No es un contrato nuevo**: usa
  `memory_router.store(type=PROJECT, ...)` tal cual. El único ajuste es de
  expectativa: `mem_project` deja de ser stub y se usa de verdad en V0.87.
- **Capa 2 "Project Memory" del MOS** (la maquinaria rica: permisos granulares,
  Shared Project Memory) sigue en V1.2 como estaba (doc 08). El WPMS **no la
  necesita**: le basta el `store/search/context` de `IMemoryStore` que ya existe
  en V0.85. Diseñado así a propósito (§5.4).

Conclusión: **el artefacto del MOS (V0.85) no se replanifica.** Solo conviene que
la review de M-cierre de V0.85 confirme que `mem_project` acepta escrituras (ya lo
hace por ser una colección más). Nada bloquea empezar el MOS.

---

## 1. Tesis: el WPMS es estado operativo, el MOS es conocimiento

La distinción que gobierna todo el diseño (y que lo separa de Jira/Notion):

| | WPMS (SQL) | MOS Project Memory (`mem_project`) |
|---|---|---|
| Qué guarda | ESTADO operativo: qué tareas hay, en qué estado, con qué deadline, en qué milestone | CONOCIMIENTO: decisiones del proyecto, hechos, contexto semántico, resúmenes |
| Forma | filas relacionales, consulta exacta y barata | embeddings, búsqueda semántica |
| Verdad de | "la tarea #42 está en progreso, vence el jueves" | "en este proyecto decidimos usar Postgres por X" |
| Quién pregunta | el usuario (UI), el TIE (planificar), el AE (disparar) | el TIE/chat (contexto), el Learner |
| Ciclo de vida | vivo, cambia cada día; se archiva | permanente, se destila (RFC-007) |

**El WPMS no es una segunda memoria.** Escribe en `mem_project` los DESTILADOS
(no duplica el estado): cuando una tarea se cierra o un milestone se completa,
emite un hecho a `mem_project` ("completado milestone V0.85 MOS el 12-jul; 5
tareas; decisión clave: opción B"). El estado operativo vive en SQL; el
significado permanente, en el MOS. Cero solapamiento.

Esto responde de entrada a la revisión crítica: **no es otro Jira** porque Jira
guarda TODO en su propia base y no distingue estado de conocimiento; aquí el
conocimiento pertenece al MOS y el WPMS es solo la capa operativa mínima.

## 2. Benchmark — qué tomamos de cada uno (principios, no interfaces)

| Producto | Principio adoptado | Rechazado |
|---|---|---|
| **Linear** | velocidad como feature (todo con teclado, popup de task sin cambiar de pantalla, estados como ciudadanos de primera); opinión fuerte sobre el flujo | campos infinitos, configurabilidad extrema |
| **GitHub Projects/Issues** | el trabajo se ancla a versiones/milestones y al repo; issues enlazan a commits/PR | tableros genéricos multi-equipo |
| **Notion** | un proyecto enlaza sus docs; el proyecto es un contenedor de contexto | docs-como-base-de-datos anidada infinita (eso es el MOS, no el WPMS) |
| **Height / Superlist** | minimalismo radical; la IA integrada en el flujo, no en un panel aparte | — |
| **Todoist** | prioridad + fecha como los dos ejes que de verdad se usan a diario | proyectos-carpeta sin semántica |
| **Jira / Monday / ClickUp / Asana** | **lección negativa**: la muerte por mil campos. Cada uno empezó simple y murió de configurabilidad | prácticamente todo su modelo de datos |
| **Obsidian Projects** | los docs son archivos enlazables, no filas | plugin sprawl |

Síntesis: **la vara es Linear** — si una decisión de diseño no supera "¿lo tendría
Linear?", se corta. La disciplina de un solo usuario que trabaja 8 h/día con una IA
al lado favorece MENOS estructura, no más.

## 3. Modelo de datos

### 3.1 Evolución del modelo REAL existente (no reescritura)

Ya existen `Project` (con `name, description, status, progress, priority,
due_date, notes, created_at, updated_at`) y `Task` (con `title, description,
status, priority, project_id, due_date, assignee, created_at, updated_at`) —
`database.py:117-144`. **El WPMS los EXTIENDE**, no los sustituye (principio 2
AOS: evolución). Migración Alembic aditiva; los endpoints `/api/projects` y
`/api/tasks` actuales siguen funcionando por contrato.

### 3.2 Workspace — decisión: **implícito en V0.87, entidad en V2.0+**

El briefing pide un `Workspace` que contenga projects/docs/automatizaciones/
agentes/repos/skills/config. **Veredicto de producto: hoy es sobreingeniería.**
Para un usuario, hay UN workspace — el suyo. Crear la entidad ahora es una tabla
de una fila y un `workspace_id` muerto en todo lo demás.

**Solución**: el Workspace existe como CONCEPTO (la vista raíz que lista proyectos
+ config global en `Config`), no como tabla. La multiplicidad (varios workspaces,
Shared Workspace multiusuario) se reserva sin coste: el día que haga falta, se
crea la tabla `workspaces` y se añade `workspace_id` (nullable, default 1) a
`projects` — migración mecánica, cero rediseño. Esto es exactamente la garantía
que pide el briefing ("no diseñar multiusuario; garantizar que no se impida
después"). No hace falta la entidad para cumplirla.

### 3.3 Project (extensión)

Campos que se AÑADEN a la tabla `projects` existente (con justificación; los del
briefing que se rechazan van al final):

| Campo | Tipo | Por qué (¿lo usa Aithera o el usuario a diario?) |
|---|---|---|
| `repo_path` | str null | raíz del repo local → las tools (git/filesystem) y el TIE operan sobre él. **Aithera lo usa constantemente** |
| `current_version` | str null | "0.8.0" — versión activa; el briefing/estado lo muestra |
| `target_version` | str null | hacia dónde va; el milestone activo apunta aquí |
| `start_date` | date null | para que el Learner calcule ritmos reales |
| `tags` | JSON (list) | filtrado y agrupación; el TIE los usa para skills transferibles (doc 15 §análisis 3) |
| `docs` | JSON (list de `{label, kind, url_or_path}`) | enlaces a repo/roadmap/arquitectura SIN duplicar contenido (§6) |
| `archived_at` | datetime null | los proyectos no se borran, se archivan (fuera de la vista, en el MOS) |

**Rechazados del briefing** (y por qué): `Milestones`/`Automatizaciones
relacionadas`/`Progreso`/`Actividad reciente` **no son campos**, son relaciones o
cálculos (§3.4, §7, §8, §9) — meterlos como columnas sería denormalizar. `Versión
actual/objetivo` sí entran (arriba) porque Aithera trabaja por versiones (§7).
`Descripción` y `Estado` ya existen. Resultado: Project queda profesional y
minimalista, con 7 campos nuevos que TODOS alimentan a un sistema o a la vista.

### 3.4 Milestone (entidad nueva — la pieza que hace esto "Aithera", no "Trello")

```python
class Milestone(Base):
    __tablename__ = "milestones"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True)
    name = Column(String(120))          # "V0.85 — MOS Skeleton"
    version = Column(String(40), null)  # "0.8.5" — Aithera trabaja por versiones
    description = Column(Text, null)     # el objetivo de la versión
    status = Column(String(20), default="planned")  # planned|active|done|archived
    target_date = Column(DateTime, null)
    order = Column(Integer, default=0)   # orden en el roadmap del proyecto
    created_at, completed_at (null), updated_at
    # progress: NO es columna — se calcula (§8)
```

Por qué el milestone es superior a un simple listado de tareas: **es el eje de
versión.** Aithera ES un proyecto que avanza por versiones (V0.85→V0.87→V0.9); el
milestone modela eso literalmente. El TIE planifica "hacia el milestone activo",
el briefing reporta "estás al 60% de V0.9", el Learner mide "V0.85 tardó 6
sesiones vs 4 estimadas". Un listado plano de tareas no puede responder ninguna de
esas tres preguntas. El milestone es la unidad de progreso con significado.

### 3.5 Task (extensión) — completa pero sencilla

Campos que se AÑADEN a `tasks`:

| Campo | Tipo | Justificación |
|---|---|---|
| `milestone_id` | FK null, ix | la tarea pertenece a una versión (jerarquía §4) |
| `checklist` | JSON (list de `{text, done}`) | subtareas ligeras — NO tareas (§3.6). Inline, sin tabla |
| `depends_on` | JSON (list de task ids) | el TIE necesita el orden real; desbloqueo → briefing |
| `estimate` | str null (p.ej. "2 sesiones") | el Learner compara estimado vs real (doc 15) |
| `order` | int | posición en la lista (drag & drop) |
| `closed_at` | datetime null | para progreso y métricas de ciclo |
| `links` | JSON null (`{commit, pr, agent_execution_id, mission_id}`) | traza al trabajo REAL: commit que la cerró, misión del TIE que la ejecutó |

**Rechazados del briefing** (fuertemente — aquí es donde se evita el Jira):

| Campo pedido | Veredicto | Razón |
|---|---|---|
| Comentarios | ❌ tabla propia | un usuario solo NO conversa consigo mismo en hilos. Si hace falta una nota → `description`. Reservado para Shared (V2.0+) |
| Archivos adjuntos | ⚠️ reducido a `links` | no un gestor de ficheros; enlaza rutas/URLs. El contenido de un archivo, si importa, va al MOS |
| Tiempo invertido | ❌ | nadie con un cronómetro 8 h/día. El Learner INFIERE duración de `created_at→closed_at` sin fricción |
| Skills relacionadas | ❌ campo manual | lo DERIVA el Learner (doc 15), no lo teclea el usuario |
| Automatizaciones relacionadas | ❌ campo | es una relación inversa (la regla apunta a la tarea), no un campo de la tarea |
| Agentes relacionados | ⚠️ dentro de `links` | `mission_id`/`agent_execution_id` ya lo cubren |
| Assignee | se mantiene (ya existe) | hoy siempre el usuario o "aithera"; útil el día del multiusuario, coste 0 |

Resultado: la Task tiene lo que se toca a diario (título, descripción, estado,
prioridad, fecha, checklist, dependencias) + lo que alimenta a la IA (`estimate`,
`links`, `milestone_id`) — y NADA que el usuario acabaría ignorando.

### 3.6 Checklist — subtareas ligeras (no entidad)

`checklist` es un JSON en la tarea: `[{text, done}]`. Se marca con un clic, no
tiene estado/fecha/prioridad propios. Justo la línea que Jira cruzó y no debería:
en cuanto una subtarea necesita fecha propia, ES una tarea con `depends_on` — y el
usuario la promociona. Mientras sea un checkbox, es un checkbox.

## 4. Jerarquía y por qué es superior a un listado

```
Workspace (implícito)
  └─ Project           "Aithera"
      └─ Milestone      "V0.9 — Automation Engine"   ← eje de versión
          └─ Task       "Implementar ApprovalGate"
              └─ Checklist item  "escribir test de reanudación"
```

Una tarea puede vivir sin milestone (backlog suelto) — la jerarquía guía, no
obliga (lección de Linear). Por qué gana a un listado plano: cada nivel responde
una pregunta que la IA hace de verdad — Project: *"¿en qué trabajo?"*; Milestone:
*"¿cuánto falta para la próxima versión?"*; Task: *"¿qué hago ahora?"*; Checklist:
*"¿qué me queda de esto?"*. El TIE planifica en el nivel Task/Milestone; el
briefing reporta en Milestone/Project; el Learner mide en Milestone. Un listado
plano colapsa las cuatro preguntas en una lista sin contexto de versión —
inservible para trabajar por releases.

## 5. Integración con el MOS

### 5.1 Qué escribe el WPMS en `mem_project` (destilados, por evento)

Solo HECHOS permanentes, nunca el estado vivo (§1). Disparado por eventos (§10):
al completar un milestone → resumen del milestone; al cerrar una tarea con
`links.decision` → hecho de decisión (además espeja a `decisions`); al archivar
un proyecto → resumen final. `dedup_key` por entidad (idempotente). El estado
operativo (tareas abiertas, progreso) **jamás** se escribe al MOS: se consulta en
SQL, que es más rápido y exacto.

### 5.2 Qué consulta

`context(query, memory_types=[PROJECT])` para enriquecer la vista de proyecto con
"lo que Aithera recuerda de este proyecto" (decisiones pasadas, contexto) — junto
al estado operativo de SQL. Es la unión de las dos columnas de §1 en una sola
pantalla.

### 5.3 Qué permanece SOLO en Project Memory

Las decisiones con su razonamiento, los resúmenes semánticos, el contexto
conversacional del proyecto. El WPMS los MUESTRA (vía `context()`) pero no los
posee ni los edita — pertenecen al MOS.

### 5.4 Compatibilidad con las 4 capas y Shared futuro

El WPMS toca solo la Capa 2 (Project) vía `IMemoryStore` — no conoce Chroma ni la
maquinaria interna (doc 16 §9). El día del Shared Project Memory (V2.0+, multi-
usuario), el `MemoryRouter` enruta `mem_project` a un store compartido y el WPMS
**no se entera**: sigue llamando `store/context`. La garantía "no impedir Shared"
se cumple por usar la interfaz, no por diseñar hoy nada compartido.

## 6. Documentación y versionado

- **Docs**: `project.docs` es una lista de ENLACES (`{label, kind, url_or_path}`)
  a repo/roadmap/arquitectura. El WPMS no aloja el contenido — lo abre (ruta local
  o URL). Cero duplicación (regla del briefing). El contenido técnico que merezca
  memoria semántica ya está en el MOS.
- **Versionado**: `project.current_version` + el milestone `active` + el siguiente
  `planned` modelan la evolución. Al marcar un milestone `done`:
  `current_version ← milestone.version`, el siguiente milestone pasa a `active`,
  y se emite `milestone.completed` (→ destilado al MOS + material del Learner). Es
  el flujo real de Aithera (V0.85→V0.87→V0.9) modelado en datos.

## 7. Integración con TIE, Automation, Learner, Orchestrator

| Sistema | Punto de integración (solo eso — no se diseñan aquí) |
|---|---|
| **TIE** (doc 14) | lee Project/Milestone/Task como contexto de planificación; una Task puede "enviarse al TIE" → `tie.submit_mission(goal=task.title+desc, source="workspace")`; el TIE **divide** en un TaskGraph (sus nodos NO son Tasks del WPMS — son pasos de ejecución efímeros); al cerrar, escribe `mission_id` en `task.links`. Prioriza usando `priority`+`due_date`+`depends_on`. **El WPMS da el QUÉ; el TIE produce el CÓMO** |
| **Automation Engine** (doc 11-A) | `WorkspaceAction` (stub en V0.9, real luego): crear/cerrar/mover tarea, recordatorio de deadline, recalcular progreso. Reacciona a eventos del WPMS vía Event Bus. El AE nunca decide qué tarea crear — ejecuta reglas deterministas o delega el juicio al TIE |
| **Learner** (doc 15) | consume eventos del WPMS: estima vs real (`estimate` vs `created_at→closed_at`), detecta bloqueos (tareas mucho tiempo en `blocked`), patrones de tipo de tarea, retrasos por milestone. **Propone**, no toca el Workspace |
| **Orchestrator/briefing** (doc 11) | el `daily_briefing` lee el WPMS para el Morning/Evening Brief: milestone activo + progreso, deadlines próximos (`due_date`), tareas de alta prioridad, bloqueos (`depends_on` sin resolver), actividad reciente. Es una consulta SQL barata — sin Gmail, sin LLM en caliente |
| **Runtime Intelligence** (futuro, doc 17 §6) | podrá consumir los eventos del WPMS (`task.*`, `milestone.*`) para correlacionar velocidad de trabajo con carga del sistema, detectar milestones sistemáticamente subestimados, etc. Solo consumo de eventos — reservado, no diseñado |

## 8. Progreso automático (sin porcentajes manuales)

Métodos evaluados: (a) manual — **descartado** por el briefing y con razón (miente);
(b) por conteo de tareas cerradas; (c) ponderado por `estimate`; (d) por checklist.

**Elegido: (b) conteo de tareas, con matiz.** `progress = tareas_done /
tareas_totales` del milestone (y el del proyecto = media ponderada por milestone,
o del milestone activo). Por qué el conteo simple y no el ponderado por estimate:
las estimaciones de un solo usuario son ruidosas; ponderar por ellas da una
falsa precisión que se desvía tanto como el conteo pero parece exacta (Regla de
Oro: simplicidad > sofisticación sin valor). El conteo es transparente ("3 de 5")
y el usuario lo entiende sin explicación. Se recalcula por evento (cierre/apertura
de tarea), nunca se teclea. Las checklists NO cuentan para el progreso (son
intra-tarea) — evita que marcar checkboxes infle el porcentaje.

## 9. Interfaz (vara: Linear)

### 9.1 Vista Proyecto

Una columna de contenido, sin dashboard saturado: **cabecera** (nombre, versión
actual, estado) · **barra de progreso** del milestone activo · **descripción**
(1-2 líneas) · **enlaces** (repo, docs — iconos, no tarjetas) · **milestones**
(lista compacta con su progreso) · **tareas** del milestone activo (lista tipo
Linear: estado + título + prioridad + fecha, una línea por tarea) · **actividad
reciente** (feed derivado de eventos, solo lectura). Nada más. Sin gráficos de
burndown, sin widgets configurables.

### 9.2 Vista Task (popup, no pantalla)

Popup sobre la lista (patrón Linear): editar en el sitio descripción, prioridad,
fecha, checklist, `links`, proyecto, milestone. `Esc` cierra, `Cmd+Enter` guarda.
Nunca saca al usuario de su contexto.

### 9.3 Organización — velocidad ante todo

Drag & drop (reordenar / mover de milestone / cambiar estado en board opcional);
cambio de prioridad y estado con teclado sobre la fila seleccionada; búsqueda
global (`Cmd+K`) sobre títulos + fuzzy; atajos: `c` crear tarea, `/` buscar, `1-3`
prioridad, `x` cerrar. Todo con teclado; el ratón es opcional. Objetivo medible:
crear una tarea y asignarla a milestone en < 3 segundos sin tocar el ratón.

## 10. Eventos emitidos (Event Bus, doc 17)

`task.created`, `task.status_changed` (`{task_id, from, to}`), `task.closed`,
`milestone.completed`, `project.progress_changed`. Payloads de metadatos (§17
§2.2). Consumidores: AE (V0.9), Learner (V1.1), briefing, Runtime Intelligence
(futuro). El WPMS **emite y sigue**; no espera a nadie.

## 11. Estructura de código

```
backend/app/workspace/
├── __init__.py         # API pública: workspace_service (o funciones)
├── models.py           # Milestone (nuevo) + extensiones vía migración Alembic
├── service.py          # lógica: progreso, versionado, destilado a mem_project
├── progress.py         # cálculo de progreso (§8) — función pura, testeable
└── (endpoints en api/endpoints/workspace.py: projects/tasks/milestones/progress)
frontend/src/pages/Workspace/   # Vista Proyecto + popup Task + board (Linear-like)
```

`/api/projects` y `/api/tasks` actuales se ABSORBEN aquí manteniendo rutas por
contrato (patrón del split de email, doc CLAUDE §16.1). Migración Alembic única y
aditiva. Frontera modular vigilada por `test_module_boundaries.py` (doc 16).

## 12. Roadmap — por qué V0.87 (después del MOS, antes del AE)

- **Después del MOS (V0.85)**: el WPMS escribe destilados en `mem_project` y lee
  contexto con `context()`. Sin el MOS no tendría dónde poner el conocimiento del
  proyecto — sería un Trello aislado. El MOS es prerrequisito duro.
- **Antes del Automation Engine (V0.9)**: el AE quiere `WorkspaceAction` (crear/
  cerrar tareas, recordar deadlines, recalcular progreso) y el briefing quiere
  leer el estado del proyecto. Si el WPMS llegara después, el AE nacería sin su
  materia de trabajo más natural y habría que retrofit.
- **Antes de que el Orchestrator (V1.0) use proyectos/tareas**: el TIE planifica
  "hacia el milestone activo" y escribe `mission_id` en las tareas. El modelo del
  WPMS debe existir y estar poblado antes de que el TIE lo consuma.
- **Coste**: 2-3 sesiones (extiende modelos existentes, no crea de cero; la UI
  Linear-like es el grueso). Cabe holgado entre M5 de V0.85 y A1 de V0.9 sin
  amenazar la fecha de V1.0 (regla de oro del roadmap).

Sprints: **W1** modelo (migración + Milestone + progreso + endpoints + tests) ·
**W2** UI (Vista Proyecto + popup Task + board + atajos) · **W3** integración
(destilado a MOS + eventos + briefing lee WPMS + tarjeta Hub; tag `v0.8.7`).

## 13. Revisión crítica (Product Designer + Architect)

- **¿Otro Jira?** No: Jira separa mal estado de conocimiento y muere de campos.
  Aquí el conocimiento es del MOS y la Task tiene 7 campos nuevos, todos con
  consumidor. Se rechazaron explícitamente comentarios, adjuntos, time-tracking y
  3 campos "relacionados" (§3.5).
- **¿Otro Trello?** No: Trello es un listado plano sin versión. El milestone como
  eje de versión + los destilados al MOS + el enganche al TIE es justo lo que
  Trello no tiene.
- **¿Complico el flujo?** Riesgo real en el drag&drop/board — se marca OPCIONAL;
  el flujo primario es lista + teclado (Linear), no board.
- **¿Qué elimino?** Workspace-como-entidad (→ implícito), comentarios, adjuntos,
  time-tracking, campos "relacionados" manuales, progreso ponderado. Ya eliminado.
- **¿Qué info no usará la IA?** Comentarios en hilo, tiempo invertido manual,
  adjuntos binarios → fuera. Lo que queda lo consume TIE/Learner/briefing.
- **¿Qué no usará el usuario?** Un segundo nivel de subtareas, estados
  personalizables, plantillas de proyecto → no se incluyen.
- **¿Qué parece útil y se olvidará?** Burndown charts, dashboards de métricas,
  etiquetas de colores elaboradas → fuera; la "actividad reciente" se mantiene
  minimal (feed de eventos, no analytics).
- **¿Qué echaría de menos un profesional?** Búsqueda potente y atajos (incluidos),
  y ver el trabajo real enganchado (los `links` a commit/PR/misión lo dan). Vista
  de calendario de deadlines: se difiere — el Calendar existente (`/api/calendar`)
  ya cubre fechas; integrarlos es V1.2, no V0.87.
- **¿8 h/día sin cansancio?** Es el criterio de aceptación: si abrir una tarea
  saca de contexto, o crear una cuesta > 3 s, o hay que rellenar campos que no se
  usan, el diseño falló. Por eso el popup Linear, el progreso automático y el
  recorte agresivo de campos.

---
*Diseño 2026-07-12 (Fable 5). V0.87, entre MOS (07) y AE (11-A). Consume MOS
(Project Memory ya existente), Event Bus (17). Consumido por TIE (14), AE (11),
Learner (15), briefing (11). Impacto MOS: nulo en contratos — solo activa la
escritura real de `mem_project` (§0). Extiende el modelo Project/Task real.*
