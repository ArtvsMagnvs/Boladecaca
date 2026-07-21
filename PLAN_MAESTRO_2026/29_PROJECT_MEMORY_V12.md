# 29 — PROJECT MEMORY (Capa 2 del MOS) · Diseño maestro V1.2+
## Memoria por-proyecto con permisos granulares

> **Estado**: DISEÑO MAESTRO (V1.2+, no en desarrollo). Desarrolla por completo
> la **Capa 2 — PROJECT MEMORY** reservada en `08_MOS_ARQUITECTURA_COMPLETA.md`
> ("V1.2+, por-proyecto, permisos granulares (stub antes)").
> **Prerrequisito**: V1.1 (LSL/LLL) cerrada. Se apoya en lo que YA existe:
> `MemoryType.PROJECT` (interfaces.py), el escritor real WPMS (V0.87), y el
> aislamiento por proyecto `context(project_id=…)` (C-1b, doc 25).
> **Redactado como equipo senior (+35 años)**: Principal Architect de sistemas
> de memoria, ingeniero de datos, experto en control de acceso, Staff de
> rendimiento, especialista UX y experto en ciberseguridad de IA.

---

## 0. RESUMEN EJECUTIVO

Aithera ya tiene una capa de memoria personal (Capa 1, `mem_personal`: emails,
agenda, preferencias) y un **stub** de memoria de proyecto (`mem_project`): hoy
el WPMS escribe unos pocos hechos permanentes cuando completas un milestone,
archivas un proyecto o cierras una tarea con decisión, y el aislamiento por
proyecto (C-1b) ya impide que la memoria de un proyecto se cuele en las misiones
de otro.

**La Capa 2 completa (V1.2+)** eleva ese stub a una **memoria de proyecto de
primera clase**: cada proyecto tiene su propio cuerpo de conocimiento rico
—decisiones, convenciones, documentos, contexto técnico, historia— que Aithera
consulta y actualiza cuando trabaja EN ese proyecto, con **permisos granulares**
que gobiernan qué puede leer y escribir cada quién (el usuario, cada agente, cada
automatización) en cada proyecto.

**Las dos capacidades nuevas que la definen**:
1. **Memoria por-proyecto rica y viva** — no cuatro hechos sueltos, sino el
   conocimiento operativo y permanente de cada proyecto, indexado y consultable,
   que hace que Aithera "entienda" un proyecto al entrar en él como lo entendería
   un compañero que lleva meses en él.
2. **Permisos granulares por proyecto** — el control de acceso deja de ser
   global (Ajustes → Permisos, doc 20 A3b) y pasa a ser *por proyecto y por
   actor*: el agente A puede leer y escribir en el proyecto X pero solo leer en
   el Y; una automatización solo ve el proyecto para el que se creó; un proyecto
   sensible puede requerir confirmación para cualquier escritura.

**Y tres extensiones que la convierten en un espacio de trabajo completo (Parte
II, §10-§12)**:
- **Grafo de memoria por proyecto (Graphify)**: cada proyecto tiene su propio
  grafo de conocimiento + su `CLAUDE.md`, auto-actualizados en cada cambio. Los
  agentes consultan el grafo en vez de leer archivos → **ahorro de tokens**. Con
  botón "Ver Grafo de Memoria" (abre el HTML interactivo de Graphify) y su
  sección en Ajustes.
- **Proyectos colaborativos**: invitar a otros usuarios de Aithera a trabajar
  juntos —esté la carpeta en un PC o en un VPS— con un enlace+clave sencillo y
  seguro. Los invitados crean agentes, milestones, tareas y configuran agentes,
  según su permiso.
- **Orquestador con chat por proyecto**: cada proyecto tiene su asistente-jefe
  (el orquestador que ya existe) con **chat propio en su tarjeta** — privado o
  compartido por el equipo.

**Regla rectora (heredada del MOS)**: la memoria operativa VOLÁTIL (estado,
progreso, tareas abiertas) vive en SQL (WPMS/Workspace); la Capa 2 guarda el
**conocimiento PERMANENTE** del proyecto — lo que seguirá siendo verdad cuando
el proyecto avance. Nunca duplica el estado; lo destila en conocimiento.

---

## 1. PUNTO DE PARTIDA — QUÉ EXISTE HOY (no inventado)

Para diseñar sobre lo real, esto es exactamente lo que hay:

- **`MemoryType.PROJECT = "mem_project"`** (`interfaces.py`): la colección
  existe, activa desde V0.85, marcada como "escritor real: WPMS V0.87".
- **El escritor real** (`workspace/service.py`): al completar un milestone
  (`_on_milestone_completed`), archivar un proyecto (`_on_project_archived`) o
  cerrar una tarea con `links.decision`, el WPMS destila un hecho a `mem_project`
  con `metadata={kind, project_id, ...}` y `dedup_key`. **Solo hechos
  permanentes, nunca estado operativo** (doc 18 §5.1) — esta regla ya está viva.
- **El aislamiento por proyecto** (C-1b, doc 25): `IMemoryStore.context()`,
  `MemoryRouter.context()` y `LocalMemoryStore.context()` ya reciben
  `project_id`; los items con `project_id` distinto se excluyen del contexto de
  una misión; los sin etiqueta (generales) entran. **El filtro determinista ya
  existe** — la Capa 2 lo aprovecha, no lo reinventa.
- **La lectura** (enricher, chat_service): ya leen `mem_project` como una fuente
  más del contexto, con el `project_id` de la misión.
- **RFC-007 (compactación)**: `mem_decision`/`mem_skill` NUNCA se compactan; los
  hechos de proyecto son conocimiento destilado, tamaño marginal — la Capa 2
  hereda esta política.

**Diagnóstico honesto del stub**: hoy `mem_project` tiene tres carencias que la
V1.2 resuelve. (a) Se escribe POCO (solo 3 disparadores del WPMS) → un proyecto
sabe muy poco de sí mismo. (b) No hay permisos por proyecto → el control de
acceso es global. (c) No hay estructura interna → todo hecho de proyecto es
"contenido + metadata plana", sin distinguir una decisión de una convención o un
documento.

---

## 2. LOS TRES PRINCIPIOS DE LA CAPA 2

1. **Conocimiento permanente, no estado**: la Capa 2 guarda lo que seguirá
   siendo verdad cuando el proyecto avance (decisiones, convenciones, contexto,
   documentos, lecciones). El estado volátil (tareas abiertas, progreso, quién
   hace qué) sigue en SQL (WPMS). Si algo cambia cada día, NO es memoria de
   proyecto; es estado operativo.

2. **Aislamiento por defecto, apertura explícita**: la memoria del proyecto X es
   invisible para las misiones del proyecto Y salvo permiso explícito. Es el
   principio C-1b elevado a política: un proyecto es una frontera de conocimiento
   por defecto. Compartir entre proyectos es una decisión, no un accidente.

3. **Permisos como topología, auditables**: el control de acceso por proyecto no
   es un flag que se comprueba a veces; es una capa que TODA lectura/escritura
   atraviesa, con rastro. Un actor sin permiso sobre un proyecto no puede leer su
   memoria porque el store capado no se la entrega (inyección de dependencias,
   mismo patrón que los Guardians del doc 27 y el MemoryRouter capado).

---

## 3. ARQUITECTURA

### 3.1 De dónde cuelga (sin romper nada)

```
MOS (MemoryRouter)
 ├─ Capa 1  Private Memory   (mem_personal, mem_conversational)  ← intocable
 ├─ Capa 2  PROJECT MEMORY   (mem_project)  ← ESTO
 │    ├─ ProjectMemoryStore(IMemoryStore)      — el store rico por proyecto
 │    ├─ ProjectAccessControl                  — permisos granulares por (proyecto, actor)
 │    └─ ProjectMemoryService                  — la fachada pública (API de la capa)
 ├─ Capa 3  Skills           (mem_skill / GSN)
 └─ Capa 4  Inteligencia     (LLL / CIE)
```

La Capa 2 NO es un módulo paralelo: es el `mem_project` que ya existe, envuelto
por un store especializado y una capa de control de acceso. El `MemoryRouter`
sigue siendo el único punto de entrada (RFC-001): nadie accede a
`ProjectMemoryStore` directo.

### 3.2 Estructura interna del conocimiento de proyecto

El stub actual mete todo en "contenido + metadata plana". La Capa 2 distingue
**tipos de conocimiento de proyecto** (un campo `kind` en metadata, ya presente
hoy pero sin taxonomía):

| kind | Qué es | Ejemplo | Se compacta |
|---|---|---|---|
| `decision` | Una decisión tomada y su porqué | "Usamos PostgreSQL, no MySQL, por las migraciones" | NUNCA |
| `convention` | Una convención/regla del proyecto | "Los commits van en imperativo, en español" | NUNCA |
| `context` | Contexto técnico/de dominio permanente | "El cliente es una clínica; GDPR aplica" | NUNCA |
| `document` | Referencia a un documento del proyecto (destilado) | "El brief está en docs/brief.md; su esencia es X" | roll-up a resumen |
| `milestone` | Hito completado (lo que YA escribe el WPMS) | "Milestone 'Beta' completado en v0.9" | NUNCA |
| `lesson` | Lección aprendida (del Learner, doc 15) | "Estimar tareas de UI x2; siempre nos pasamos" | NUNCA |
| `artifact` | Conocimiento sobre un entregable | "El endpoint /api/x quedó deprecado en v1" | roll-up |

Esta taxonomía es **append-only** (como `MemoryType`): añadir un `kind` nuevo
nunca rompe nada. Cada `kind` tiene su política de compactación (RFC-007).

### 3.3 Contrato `ProjectMemoryItem` (extiende, no rompe)

No hay un tipo nuevo: es `MemoryItem` (congelado) con una convención de metadata
formalizada y validada por el store:

```python
# Convención de metadata para MemoryType.PROJECT (validada por ProjectMemoryStore)
{
    "project_id": int,          # OBLIGATORIO — la frontera de aislamiento (C-1b)
    "kind": str,                # ∈ taxonomía §3.2 (decision|convention|context|...)
    "author": str,              # quién lo escribió: "user" | "agent:<id>" | "automation:<id>" | "wpms" | "learner"
    "confidence": float,        # 0-1: cuánta certeza (los destilados por IA < 1.0)
    "supersedes": Optional[str], # id del hecho que reemplaza (evolución del conocimiento)
    "pinned": bool,             # el usuario lo ancló → nunca se compacta ni se olvida solo
    "sensitivity": str,         # "normal" | "confidential" — gobierna permisos de escritura (§4)
    "created_at_iso": str,
    "dedup_key": str,           # idempotencia (ya lo usa el WPMS)
}
```

`author` es la pieza nueva clave: cada hecho de proyecto sabe QUIÉN lo puso, lo
que hace posibles los permisos granulares (§4) y la auditoría.

---

## 4. PERMISOS GRANULARES POR PROYECTO (la capacidad estrella)

Hoy los permisos son globales (Ajustes → Permisos, A3b: email.send, browser.use…
para toda Aithera). La Capa 2 introduce permisos **por (proyecto, actor,
operación)** — un actor puede tener acceso distinto en cada proyecto.

### 4.1 Modelo de acceso

```python
@dataclass(frozen=True)
class ProjectGrant:
    project_id: int
    actor: str              # "user" | "agent:<id>" | "automation:<id>" | "*"
    can_read: bool
    can_write: bool
    write_needs_approval: bool   # aunque pueda escribir, ¿pasa por el ApprovalGate?
    max_sensitivity: str         # "normal" | "confidential" — hasta qué nivel puede leer
```

Persistido en una tabla `project_grants` (SQL, no ChromaDB — es control de
acceso, no conocimiento). Defaults seguros por diseño:
- **El usuario**: read+write en todos sus proyectos (es su Aithera).
- **Un agente**: por defecto solo lee el proyecto al que está asignado
  (`Agent.project_id`, que ya existe desde WPMS W2c); escribir requiere concesión
  explícita. Nunca ve otros proyectos.
- **Una automatización**: por defecto solo el proyecto para el que se creó, solo
  las operaciones que su regla declara.
- **`sensitivity=confidential`**: un proyecto puede marcar conocimiento como
  confidencial (p.ej. datos de un cliente bajo NDA); solo actores con
  `max_sensitivity=confidential` lo leen. Fail-closed: sin grant explícito, no.

### 4.2 Dónde se aplica (topología, no comprobación esporádica)

El control de acceso vive en `ProjectAccessControl`, y TODA operación de la Capa
2 pasa por él:
- **Lectura**: `ProjectMemoryService.context(project_id, actor)` inyecta en el
  store un filtro que excluye lo que `actor` no puede leer (por proyecto y por
  `sensitivity`). Un actor sin `can_read` sobre un proyecto recibe contexto vacío
  de ese proyecto — no un error, simplemente no existe para él (mismo espíritu
  que C-1b).
- **Escritura**: `ProjectMemoryService.remember(project_id, actor, item)` verifica
  `can_write`; si `write_needs_approval`, abre un `ApprovalGate` (reusa A1/A3b —
  con el modo Autónomo, se auto-aprueba con rastro). Sin `can_write`, la
  escritura se rechaza y se audita.
- **Auditoría**: cada acceso denegado y cada escritura sensible dejan rastro
  (patrón Decision API). Un proyecto confidencial tiene trazabilidad total de
  quién leyó/escribió qué.

### 4.3 Integración con los permisos globales (A3b)

Los permisos globales (Ajustes → Permisos) y los de proyecto se COMPONEN: para
escribir en la memoria de un proyecto, un agente necesita (a) el permiso global
`memory.write` Y (b) el grant `can_write` sobre ese proyecto. La intersección es
el default seguro: ambos deben decir sí. El modo Autónomo (full) satura el nivel
global; los grants por proyecto siguen gobernando el "en qué proyecto".

---

## 5. CÓMO CONECTA CON AITHERA (componente a componente)

| Componente | Cómo conecta | Qué cambia |
|---|---|---|
| **WPMS (Workspace)** | Sigue siendo el escritor principal, pero ahora escribe MÁS `kinds` (convention, context, lesson) además de milestone/archived/decision. UI para que el usuario añada conocimiento de proyecto a mano. | +escrituras ricas; +panel "conocimiento del proyecto". |
| **TIE (planner/executor)** | Al ejecutar una misión de proyecto (`mission.project_id`), el enricher consulta la Capa 2 CON el `actor` de la misión — el contexto del proyecto informa el plan y cada nodo. Ya pasa el `project_id` (C-1b); ahora pasa también el `actor`. | +actor en la consulta de contexto; sin regresión. |
| **Agentes** | Un agente de proyecto (`Agent.project_id`) lee/escribe la memoria de SU proyecto según su grant. Un agente aprende del proyecto y deja lecciones en él. | Los agentes ganan memoria de proyecto real (hoy no tienen). |
| **Automation Engine** | Una regla ligada a un proyecto opera sobre su memoria con su grant. Los eventos del WPMS (task.closed, milestone.completed) siguen alimentando la Capa 2. | +grant por regla; reusa los eventos existentes. |
| **Chat** | Cuando el usuario chatea "en el contexto de" un proyecto (o Aithera lo infiere), el chat consulta la Capa 2 de ese proyecto. El aislamiento C-1b garantiza que no se mezcla con otros. | +conciencia de proyecto en el chat. |
| **MEL** | Ninguna: la memoria es conocimiento, no modelos. El MEL ejecuta igual. | Nada. |
| **Learner (doc 15)** | Escribe `lesson` en la Capa 2: las lecciones aprendidas de un proyecto (estimado-vs-real, bloqueos) se quedan EN el proyecto. | +destino "lesson" para el Learner. |
| **Graphify (§10)** | Cada proyecto tiene su grafo (`graphify-out/`) + `CLAUDE.md`, auto-actualizados; los agentes consultan el grafo en vez de leer archivos (ahorro de tokens). | +grafo por proyecto; botón "Ver Grafo"; Ajustes. |
| **Colaboración (§11)** | Un proyecto puede tener un HOST (dueño o VPS) al que se conectan invitados (actores con grant). Reusa la API del WPMS + la capa de red. | +invitaciones; +host; los invitados son actores. |
| **Orquestador por proyecto (§12)** | Cada proyecto tiene su orquestador (`orchestrator_of`, ya existe) con **chat propio** en su tarjeta; compartido en proyectos colaborativos. | +chat del orquestador; estándar al crear proyecto. |
| **RFC-007 lifecycle** | La Capa 2 hereda las políticas: decision/convention/context/milestone/lesson NUNCA se compactan; document/artifact hacen roll-up; pinned intocable. | Reusa `lifecycle.py`. |
| **GSE/CIE (doc 27, V2.0+)** | La memoria de proyecto es PRIVADA: NUNCA cruza a la red colectiva. Solo las skills técnicas destiladas (sin datos de proyecto) pueden ir a la GSN. La frontera topológica (§3.1 del doc 08) lo garantiza. | Nada sale; frontera intacta. |

**El punto clave**: como en el doc 27, la Capa 2 se enchufa por la puerta única
del MOS (`MemoryRouter`) y no toca el corazón de Aithera. Para el 95% del código,
la memoria de proyecto es "memoria con un `project_id` y un `actor`" — un
refinamiento de algo que ya existe, no un concepto nuevo.

---

## 6. RENDIMIENTO Y ESCALA

- **La consulta de contexto de proyecto respeta el presupuesto de latencia duro**
  (300ms, ya en el enricher). El filtro por proyecto+actor es en Python sobre el
  resultado de la búsqueda vectorial (mismo patrón que C-1b — determinista, no
  depende de la sintaxis de filtros de Chroma).
- **Índice por `project_id`**: la búsqueda vectorial se acota al proyecto antes
  de rankear (menos candidatos → más rápido). Con muchos proyectos, esto es una
  ganancia, no un coste.
- **Los grants se cachean** (son pocos y cambian raro): el control de acceso no
  añade una consulta SQL por lectura.
- **Compactación por proyecto**: el lifecycle nocturno procesa cada proyecto por
  separado; un proyecto muy activo no ralentiza los demás.

---

## 7. SEGURIDAD (experto en ciberseguridad de IA)

- **Fail-closed por proyecto y por sensibilidad**: sin grant explícito, un actor
  no lee ni escribe la memoria de un proyecto. Un proyecto confidencial es
  invisible para quien no tiene `max_sensitivity=confidential`.
- **Aislamiento entre proyectos por construcción** (C-1b): la memoria del
  proyecto X jamás informa una misión del proyecto Y. Esto no es solo privacidad;
  es correctitud — el fallo real que motivó C-1b (el usuario trabaja en varios
  videojuegos y la memoria de uno se colaba en otro).
- **Un agente comprometido no es un desastre**: si un agente se comporta mal, su
  grant lo acota a SU proyecto; no puede leer ni envenenar la memoria de otros.
  El blast radius de un actor es un proyecto, no todo.
- **Auditoría total de accesos confidenciales**: quién leyó/escribió qué en un
  proyecto sensible queda registrado (Decision API). Requisito para proyectos
  bajo NDA/GDPR.
- **La Capa 2 nunca cruza a la red** (doc 27): es memoria privada del usuario;
  la frontera topológica del MOS lo garantiza, no una promesa.

---

## 8. UX (especialista UX)

- **Panel "Conocimiento del proyecto"** en la vista de proyecto (WPMS): lista las
  decisiones, convenciones y lecciones del proyecto, con quién las puso y cuándo.
  El usuario puede añadir, editar, anclar (`pinned`) y olvidar cualquiera —
  transparencia con undo, como el perfil personal (R6.5c).
- **"Aithera entiende este proyecto"**: al entrar en un proyecto, una línea
  discreta resume lo que Aithera sabe de él ("12 decisiones, 4 convenciones, 3
  lecciones"). Da la sensación de un compañero que lleva meses, no de un becario
  que empieza cada día de cero.
- **Permisos por proyecto, simples**: un selector por agente/automatización
  ("solo lee" / "lee y escribe" / "lee y escribe con confirmación"), no una
  matriz de permisos que abruma. La granularidad existe pero se presenta simple.
- **Confidencialidad de un clic**: marcar un proyecto como confidencial es un
  interruptor; a partir de ahí, su conocimiento no sale de los actores
  autorizados y todo acceso queda auditado.

---

## 9. MIGRACIÓN DEL STUB A LA CAPA COMPLETA (sin romper V0.85-V1.1)

El stub actual es un subconjunto de la Capa 2, así que la migración es aditiva:
1. Los hechos que el WPMS ya escribió (milestone/archived/decision) son válidos:
   ya tienen `project_id` y `kind`. Se les asigna `author="wpms"` retroactivamente
   (default) y `sensitivity="normal"`.
2. La taxonomía de `kind` (§3.2) es append-only: los `kind` existentes siguen
   siendo válidos; se añaden los nuevos.
3. Los grants nacen con defaults seguros (§4.1): el usuario read+write en todo,
   los agentes read-only en su proyecto. Nadie pierde acceso que ya tenía.
4. `ProjectMemoryStore` valida la convención de metadata (§3.3) al escribir; los
   items viejos que no la cumplan se leen igual (tolerante), se completan al
   siguiente write (patrón de migración perezosa).
5. Migración Alembic aditiva para `project_grants` (idempotente, aplicada al
   Postgres real de inmediato — la lección dura del proyecto: no probar solo
   contra SQLite de usar-y-tirar).

---

# ══════════════════════════════════════════════════════════════════════
# PARTE II — EXTENSIONES V1.2+ (§10-§12)
# ══════════════════════════════════════════════════════════════════════

Tres capacidades que convierten la Capa 2 de "memoria por proyecto" en un
**espacio de trabajo por proyecto**: el grafo de memoria (Graphify) para que
Aithera entienda el proyecto barato, la colaboración multi-usuario, y el
orquestador con chat propio en cada proyecto.

## 10. GRAFO DE MEMORIA POR PROYECTO (Graphify integrado)

### 10.1 Qué es y por qué (el ahorro de tokens)
Hoy, cuando un agente trabaja en un proyecto, para "entenderlo" tendría que leer
sus archivos — caro en tokens y lento. **Graphify** (ya usado en el desarrollo de
Aithera) convierte una carpeta en un **grafo de conocimiento navegable**:
comunidades, relaciones entre archivos, un `GRAPH_REPORT.md` y un `graph.json`
consultable. Consultar el grafo (`graphify query "…"`) devuelve un subgrafo
acotado —mucho más pequeño que leer los archivos crudos— con la reducción de
tokens que Graphify anuncia. **La Capa 2 lo incorpora como producto: cada
proyecto tiene su propio grafo, su propio `CLAUDE.md`, y ambos se mantienen solos.**

### 10.2 Qué recibe cada proyecto al crearse
Al crear un proyecto con `repo_path` (carpeta local o en VPS, §11), Aithera
inicializa dentro de esa carpeta:
- **`CLAUDE.md` del proyecto**: la memoria persistente legible del proyecto
  (equivalente al `CLAUDE.md` de Aithera). Nace de una plantilla y se enriquece
  con el conocimiento de la Capa 2 (decisiones, convenciones, contexto — §3.2).
  Es a la vez documento humano y contexto para los agentes.
- **`graphify-out/`**: el grafo del proyecto (HTML interactivo + `graph.json` +
  `GRAPH_REPORT.md`), generado con `graphify <repo_path>`.

**Relación con la Capa 2 (importante, no duplicar)**: el grafo NO sustituye a la
memoria semántica de proyecto; la COMPLEMENTA. El grafo captura la ESTRUCTURA del
proyecto (qué archivos existen, cómo se relacionan) barata y determinista; la
Capa 2 (`mem_project`) captura el CONOCIMIENTO destilado (por qué se decidió X,
qué convención rige). El `CLAUDE.md` es el puente legible entre ambos. Un agente
consulta el grafo para "dónde está X" y la Capa 2 para "por qué X es así".

### 10.3 Auto-actualización (se mantiene solo)
- **Watcher de archivos**: un observador (patrón del `MemoryLifecycleManager`,
  pero por proyecto) detecta cambios en los archivos del proyecto y dispara
  `graphify update .` (AST-only, **sin coste de API** — clave: actualizar el
  grafo es gratis en tokens). Se hace con debounce (agrupa ráfagas de cambios)
  para no reindexar en cada tecla.
- **`CLAUDE.md` automático**: cuando la Capa 2 gana un hecho permanente
  (decisión, convención, lección — §3.2), Aithera actualiza la sección
  correspondiente del `CLAUDE.md` del proyecto (append/merge, nunca sobrescribe
  lo que el usuario escribió a mano). Así el `CLAUDE.md` refleja siempre lo que
  Aithera sabe del proyecto, y el usuario puede leerlo/editarlo.
- **Enganche por evento**: reusa los eventos del WPMS/Learner que ya alimentan la
  Capa 2 (`task.closed`, `milestone.completed`, `lesson`) — el mismo disparo que
  escribe `mem_project` actualiza el `CLAUDE.md`. Un solo camino.

### 10.4 Cómo lo consumen los agentes (el ahorro real)
El `ProjectMemoryService` gana un método `graph_query(project_id, question)` que
delega en el `graph.json`/MCP de Graphify del proyecto. El TIE/agentes, al
necesitar orientarse en el proyecto, **consultan el grafo en vez de leer los
archivos** — subgrafo acotado, no corpus entero. Esto se integra en el enricher
como una fuente más de contexto de proyecto (junto a `mem_project`), respetando
el presupuesto de latencia.

### 10.5 UI — "Ver Grafo de Memoria" + Ajustes
- **Botón "Ver Grafo de Memoria"** en la tarjeta del proyecto (WPMS): abre el
  **HTML interactivo** que Graphify genera (`graphify-out/…/index.html` o el
  visor) en el navegador — exactamente lo que Graphify ya produce. Un clic, el
  grafo del proyecto navegable.
- **Ajustes → Grafos de memoria** (sección nueva): activar/desactivar el grafo
  por proyecto, política de auto-actualización (en cada cambio / cada N min /
  manual), ver el `cost.json` (cuántos tokens ahorra), y regenerar a mano. Como
  Graphify se instala fuera de pip (es un CLI), Ajustes detecta si está presente
  y guía la instalación si falta (degradación graceful: sin Graphify, el proyecto
  funciona igual, solo sin el atajo del grafo).

### 10.6 Seguridad y aislamiento
El grafo de un proyecto vive DENTRO de su carpeta (`repo_path/graphify-out/`), así
que hereda el aislamiento del proyecto: un actor sin grant de lectura sobre el
proyecto no accede a su grafo. El `graph_query` pasa por el `ProjectAccessControl`
(§4) igual que cualquier lectura de la Capa 2. En proyectos colaborativos (§11),
el grafo lo genera y sirve el HOST del proyecto, no cada colaborador.

## 11. PROYECTOS COLABORATIVOS — invitar a otros usuarios de Aithera

### 11.1 Qué es
Un proyecto puede dejar de ser de un solo usuario: el dueño **invita** a otras
personas que usan Aithera a trabajar en el mismo proyecto, **sin importar en qué
PC o VPS esté la carpeta**. Los invitados crean agentes, milestones y tareas,
dan tareas a los agentes, los configuran — todo, según su permiso.

### 11.2 Dónde vive el proyecto: LOCAL o HOSTED
Un proyecto colaborativo necesita un **host** al que todos se conectan:
- **LOCAL (host = el Aithera del dueño)**: la carpeta está en el PC del dueño; su
  Aithera se expone a la red (reusa la capa de autenticación de red — PIN/token —
  que CLAUDE.md §5 ya prevé para post-V1.0). Los invitados se conectan al Aithera
  del dueño. Simple, cero coste, pero el dueño debe estar encendido y accesible.
- **HOSTED (host = un VPS)**: la carpeta y un "Aithera project-host" viven en un
  VPS (mismo stack: FastAPI + Postgres). Siempre disponible, independiente de que
  el dueño esté online. Es la opción para equipos serios. El project-host es una
  instancia de Aithera acotada a ese proyecto (no es el asistente personal de
  nadie; es el servidor del proyecto).

En ambos casos, el **transporte es el mismo**: los clientes (los Aithera de los
colaboradores) hablan con el host por su API (la misma que ya existe:
`/api/projects`, `/api/tasks`, `/api/milestones`, `/api/agents`, `/api/tie`…),
autenticados. El host es la fuente de verdad del proyecto (WPMS + Capa 2 + grafo).

### 11.3 La invitación (sencilla pero segura)
- El dueño genera un **enlace de invitación** con una **clave** (token firmado
  Ed25519 con caducidad y un `ProjectGrant` embebido — reusa la identidad de nodo
  del doc 27 §7.3). El enlace lleva: `host` (dónde está el proyecto), `project_id`,
  y el token de acceso.
- El invitado abre el enlace en su Aithera → su Aithera se conecta al host, se
  identifica con SU clave pública, y el host registra al invitado como
  **actor** `user:<pubkey>` con el grant que el dueño le asignó (§4).
- **Seguridad sin fricción**: no hay cuentas ni contraseñas — la clave pública ES
  la identidad (pseudónima), el token está firmado y caduca, y el grant limita
  qué puede hacer el invitado. El dueño puede revocar un invitado en cualquier
  momento (borra su grant → su clave deja de valer).

### 11.4 Qué pueden hacer los invitados (reusa los grants de §4)
Un invitado es un **actor** más en el modelo de permisos de la Capa 2. Su
`ProjectGrant` gobierna todo:
- **Roles típicos** (presets sobre el grant, UX simple): **Lector** (ve el
  proyecto, su memoria y su grafo, no cambia nada) · **Colaborador** (crea/edita
  tareas, milestones, agentes; da tareas a los agentes) · **Admin** (además,
  invita a otros y gestiona permisos).
- Crear y configurar agentes, darles tareas, crear milestones/tareas: son las
  operaciones del WPMS que YA existen, ahora ejecutadas por un actor invitado y
  gobernadas por su grant. El código del WPMS no cambia; cambia QUIÉN llama y con
  qué permiso.
- **Aislamiento**: un invitado solo ve ESE proyecto. Su clave no le da acceso a
  otros proyectos del host ni a la memoria personal del dueño (Capa 1 — frontera
  topológica intacta).

### 11.5 Concurrencia y consistencia
Varios colaboradores actuando a la vez sobre el mismo proyecto: el host serializa
las escrituras (Postgres transaccional, como hoy) y emite los eventos del WPMS
(`task.created`, etc.) a los clientes conectados para que sus UIs se refresquen
(el polling visibility-aware ya existe; se puede subir a SSE/websocket cuando
haga falta). Las misiones de los agentes corren en el host (donde está la carpeta
y las tools), no en el PC del invitado — así todos ven el mismo estado real.

## 12. ORQUESTADOR POR PROYECTO CON CHAT PROPIO

### 12.1 Ya existe la mitad
El orquestador por proyecto YA está en el código: `authority.orchestrator_of(project_id)`
devuelve el agente `role="orchestrator"` del proyecto, y `submit_mission` enruta
las misiones del proyecto a él con su frontera de autoridad (sus tools, su
carpeta — doc 14 §4.3c, R4). Lo que falta es **su chat dedicado**.

### 12.2 El chat del orquestador en la tarjeta del proyecto
Cada proyecto (privado O colaborativo — es una función general) tiene, en su
tarjeta principal (WPMS), un **chat con su orquestador**: escribes ahí y hablas
con el asistente DE ESE proyecto, que conoce su memoria (Capa 2), su grafo
(§10), sus agentes y su carpeta, y puede lanzar misiones acotadas al proyecto.
- **Reusa todo lo que ya existe**: el chat usa `submit_mission(project_id=…)` (que
  ya enruta al orquestador del proyecto) o el streaming del TIE con el
  `project_id` fijado. El aislamiento C-1b garantiza que este chat solo ve la
  memoria de SU proyecto. La personalidad (doc 26 V2) puede ser propia del
  orquestador del proyecto.
- **En proyectos colaborativos**: el chat del orquestador es COMPARTIDO — es el
  asistente común del equipo. Todos los colaboradores (según su grant) escriben
  en él y ven sus respuestas; el orquestador coordina el trabajo del proyecto
  para todos. Las misiones que lanza corren en el host.
- **Si el proyecto no tiene orquestador todavía**: al crear el proyecto se crea
  su agente orquestador por defecto (hoy es opcional; la Capa 2 lo hace estándar).

### 12.3 Por qué es potente
El chat del orquestador convierte cada proyecto en un espacio con su propio
"jefe de proyecto" IA: conoce el proyecto a fondo (memoria + grafo), tiene a los
agentes del proyecto a su cargo, y es el punto único donde el equipo (o el
usuario solo) le habla al proyecto. Es la diferencia entre "tengo carpetas" y
"cada proyecto tiene un cerebro que lo lleva".

---

# ══════════════════════════════════════════════════════════════════════
# PARTE III — PLAN Y CIERRE (§13-§15)
# ══════════════════════════════════════════════════════════════════════

## 13. PLAN DE SESIONES (modelo + esfuerzo)

Criterio de asignación (igual que los bloques anteriores):
- **Fable 5 / Max**: contratos, control de acceso, seguridad — donde un error
  expone conocimiento de proyecto entre fronteras o rompe el aislamiento.
- **Opus / Alto**: el store rico, la integración con TIE/WPMS/Learner.
- **Sonnet / Medio**: UI, migración, panel de conocimiento, tests de contrato.

> **Prerrequisito duro**: V1.1 (LSL/LLL) cerrada. La Capa 2 se apoya en el
> Learner (doc 15) para las `lesson`, y en un MOS maduro.

### BLOQUE PM-A — Contratos + store rico
| Sesión | Objetivo | Modelo | Esfuerzo |
|---|---|---|---|
| **PM-A1** | Formalizar la convención de metadata (§3.3) + la taxonomía `kind` (§3.2) validadas por `ProjectMemoryStore(IMemoryStore)`. Envuelve el `mem_project` existente sin romper lo que el WPMS ya escribe. Tests de contrato + tolerancia a items viejos. | **Fable 5** | **Max** |
| **PM-A2** | Escrituras ricas desde el WPMS: además de milestone/archived/decision, capturar convention/context/lesson (con `author`). El usuario añade conocimiento a mano. Idempotencia por `dedup_key`. | **Opus** | **Alto** |

### BLOQUE PM-B — Permisos granulares (el corazón)
| Sesión | Objetivo | Modelo | Esfuerzo |
|---|---|---|---|
| **PM-B1** | `ProjectGrant` + tabla `project_grants` (migración Alembic aditiva) + `ProjectAccessControl` con defaults seguros (§4.1). Fail-closed. Tests: sin grant no se lee/escribe; el usuario tiene acceso total. | **Fable 5** | **Max** |
| **PM-B2** | Aplicar el control de acceso en TODA lectura/escritura de la Capa 2 (§4.2): filtro de lectura por actor+sensitivity, escritura por `can_write`/`write_needs_approval` (reusa ApprovalGate A1/A3b). Composición con permisos globales (§4.3). Auditoría de accesos. | **Fable 5** | **Max** |

### BLOQUE PM-C — Integración con Aithera
| Sesión | Objetivo | Modelo | Esfuerzo |
|---|---|---|---|
| **PM-C1** | TIE/enricher: pasar `actor` además de `project_id` a la consulta de contexto (extiende C-1b). El plan y cada nodo ven el conocimiento del proyecto según el grant del actor. Sin regresión offline/local. | **Opus** | **Alto** |
| **PM-C2** | Agentes + Automation Engine: cada actor opera sobre la memoria de su proyecto con su grant. El Learner (doc 15) escribe `lesson` en la Capa 2. Eventos del WPMS siguen alimentándola. | **Opus** | **Alto** |

### BLOQUE PM-D — UX + lifecycle + cierre
| Sesión | Objetivo | Modelo | Esfuerzo |
|---|---|---|---|
| **PM-D1** | Panel "Conocimiento del proyecto" (WPMS): listar/añadir/editar/anclar/olvidar; selector de permisos por agente/automatización; interruptor de confidencialidad. Transparencia con undo. | **Sonnet** | **Medio** |
| **PM-D2** | Lifecycle por proyecto (RFC-007): políticas de compactación por `kind`, pinned intocable, roll-up de document/artifact. Migración del stub (§9). | **Sonnet** | **Medio** |
| **PM-D3** | Suite de contratos de producto (patrón `test_product_contracts`): "la memoria del proyecto X nunca informa una misión del Y", "sin grant no se lee/escribe", "un proyecto confidencial es invisible sin autorización", "olvidar es inmediato". Verificación en vivo. | **Fable 5** | **Max** |

### BLOQUE PM-E — Grafo de memoria por proyecto (Graphify, §10)
| Sesión | Objetivo | Modelo | Esfuerzo |
|---|---|---|---|
| **PM-E1** | Inicialización por proyecto: al crear un proyecto con `repo_path`, generar `CLAUDE.md` (plantilla + Capa 2) y `graphify-out/` (`graphify <path>`). Detección graceful de Graphify ausente. | **Opus** | **Alto** |
| **PM-E2** | Auto-actualización: watcher de archivos con debounce → `graphify update .` (sin coste API) + `CLAUDE.md` que se enriquece por evento (task.closed/milestone/lesson, reusa el disparo de la Capa 2). | **Opus** | **Alto** |
| **PM-E3** | `graph_query(project_id, question)` en el ProjectMemoryService (delega en graph.json/MCP) + integración en el enricher como fuente de contexto barata. Botón "Ver Grafo de Memoria" (abre el HTML) + Ajustes → Grafos de memoria. | **Sonnet** | **Medio** |

### BLOQUE PM-F — Proyectos colaborativos (§11)
| Sesión | Objetivo | Modelo | Esfuerzo |
|---|---|---|---|
| **PM-F1** | Capa de red del host: exponer la API del proyecto con autenticación (PIN/token de red, CLAUDE.md §5) + identidad de invitado por clave pública Ed25519 (reusa doc 27 §7.3). LOCAL (host=dueño) primero. | **Fable 5** | **Max** |
| **PM-F2** | Invitación: enlace + token firmado con `ProjectGrant` embebido y caducidad; alta del invitado como actor `user:<pubkey>` con su grant; revocación. Roles preset (Lector/Colaborador/Admin) sobre los grants de §4. | **Fable 5** | **Max** |
| **PM-F3** | Cliente colaborador: el Aithera del invitado opera el proyecto remoto (crear agentes/tareas/milestones, dar tareas) vía la API del host, gobernado por su grant. Concurrencia (host serializa; eventos a los clientes). | **Opus** | **Alto** |
| **PM-F4** | Opción HOSTED (VPS): "Aithera project-host" acotado a un proyecto (mismo stack). Mover un proyecto local↔VPS. Aislamiento (un invitado solo ve SU proyecto, nunca la Capa 1 del dueño). | **Opus** | **Alto** |

### BLOQUE PM-G — Orquestador con chat por proyecto (§12)
| Sesión | Objetivo | Modelo | Esfuerzo |
|---|---|---|---|
| **PM-G1** | Orquestador por defecto al crear un proyecto (hoy opcional → estándar). Chat del orquestador en la tarjeta del proyecto: `submit_mission(project_id)` / stream del TIE con project_id fijado; aislamiento C-1b; personalidad propia opcional. | **Opus** | **Alto** |
| **PM-G2** | Chat del orquestador COMPARTIDO en proyectos colaborativos: todos los colaboradores (según grant) escriben/ven; las misiones corren en el host; historial común. UI en la tarjeta. | **Sonnet** | **Medio** |

**Total ampliado**: 9 (PM-A..D) + 9 (PM-E/F/G) = **~18 sesiones en 7 bloques**.
Orden: PM-A → PM-B → PM-C → PM-D → **PM-E** → **PM-G** → **PM-F**. La
colaboración (PM-F) va la última porque depende de la capa de red (post-V1.0) y
de que la memoria/permisos/orquestador por proyecto ya funcionen en local — se
colabora sobre algo que ya es sólido en solitario. El orquestador-chat (PM-G) va
antes que la colaboración porque el chat compartido (PM-G2) se apoya en él.

---

## 14. RIESGOS Y MITIGACIONES

| Riesgo | Severidad | Mitigación |
|---|---|---|
| Fuga de conocimiento entre proyectos | ALTA | Aislamiento C-1b + fail-closed por grant; suite de contratos lo blinda |
| Memoria de proyecto que crece sin control | MEDIA | Lifecycle por `kind` (RFC-007) + pinned selectivo + presupuesto |
| Permisos demasiado complejos → el usuario no los usa | MEDIA | UX simple (3 niveles por actor), defaults seguros que funcionan sin configurar |
| Duplicar estado del WPMS en la memoria | MEDIA | Regla dura: solo conocimiento PERMANENTE, nunca estado volátil (§2.1) |
| Un agente comprometido lee/envenena otros proyectos | ALTA | Grant acota el blast radius a UN proyecto; auditoría |
| Migración del stub rompe lo que el WPMS ya escribió | MEDIA | Migración aditiva + tolerancia a items viejos + Alembic verificado en Postgres real |
| **Enlace de invitación filtrado** (§11) | ALTA | Token firmado con caducidad + grant limitado + revocación instantánea; una clave robada solo da el acceso de ESE grant a ESE proyecto, y se revoca borrando el grant |
| **Host colaborativo expuesto a la red** (§11) | ALTA | Autenticación de red (PIN/token) + solo la API del proyecto expuesta, nunca la Capa 1 personal; el invitado es un actor con grant, no un usuario del sistema |
| **VPS del proyecto comprometido** (§11.2) | ALTA | El project-host es acotado a UN proyecto (no aloja la memoria personal de nadie); cifrado en reposo (DPAPI/equivalente); mismo modelo de auditoría |
| **Grafo/CLAUDE.md desactualizados** (§10) | MEDIA | Auto-update por watcher (gratis en tokens) + regeneración manual; degradación graceful si Graphify falta |
| **Colaboradores concurrentes en conflicto** (§11.5) | MEDIA | El host serializa escrituras (Postgres transaccional) + eventos a los clientes; las misiones corren en el host, fuente única de verdad |

---

## 15. VEREDICTO DEL EQUIPO

**Principal Architect de memoria**: La Capa 2 no es un módulo nuevo; es el
`mem_project` existente madurado, envuelto por un store con taxonomía y una capa
de acceso. Que se enchufe por la puerta única del MOS es lo que la hace viable.
El aislamiento C-1b ya hizo el 40% del trabajo difícil; esto lo formaliza.

**Ingeniero de datos**: La taxonomía de `kind` con políticas de compactación por
tipo es correcta — distingue lo que nunca se olvida (decisiones) de lo que se
destila (documentos). El índice por `project_id` es una ganancia de rendimiento,
no un coste.

**Experto en control de acceso**: Permisos por (proyecto, actor, operación) con
composición sobre los globales (A3b) y fail-closed es el modelo correcto. El
blast radius acotado a un proyecto es la propiedad de seguridad que más importa
en un sistema con agentes autónomos.

**Staff de rendimiento**: Respeta el presupuesto de latencia, acota la búsqueda
por proyecto, cachea grants. Aprobado.

**Especialista UX**: La granularidad existe pero se presenta simple (3 niveles),
con defaults que funcionan sin configurar. El panel "Aithera entiende este
proyecto" es la diferencia entre un asistente que empieza de cero cada día y un
compañero con memoria. Bien.

**Experto en ciberseguridad de IA**: Fail-closed, aislamiento topológico,
auditoría de confidenciales, y la garantía de que la memoria de proyecto NUNCA
cruza a la red colectiva (doc 27). Un agente malicioso queda contenido en su
proyecto. Sólido.

**Sobre las tres extensiones (§10-§12)**: el grafo de memoria (Graphify)
convierte "entender un proyecto" de caro (leer archivos) a barato (consultar el
grafo) y se mantiene solo — es ahorro de tokens con cero fricción. La
colaboración multi-usuario reutiliza los grants (§4) como modelo de acceso, la
identidad por clave del doc 27 y la capa de red post-V1.0: un invitado es
simplemente un actor más, lo que hace la feature elegante en vez de un sistema
paralelo. El orquestador con chat por proyecto es en su mayor parte cablear un
chat a algo que YA existe (`orchestrator_of`), y en proyectos colaborativos se
vuelve el "jefe de proyecto" IA compartido del equipo. Las tres se enchufan por
la misma puerta del MOS/WPMS y no tocan el corazón de Aithera.

**Veredicto**: construir en V1.2, tras V1.1, en orden PM-A→B→C→D→E→G→F. La
colaboración (F) va la última por depender de la capa de red; el grafo (E) y el
orquestador-chat (G) son evolución de lo local. Es la capa que convierte a
Aithera de "asistente con memoria personal" en "espacio de trabajo por proyecto
—con su cerebro, su grafo y su equipo— sin mezclar un proyecto con otro". Se
apoya en lo que ya existe (mem_project, WPMS, C-1b, orchestrator_of, Graphify)
más de lo que inventa — la señal de un diseño maduro.

---
*Documento de diseño maestro. Capa 2 del MOS, V1.2+ (no en desarrollo).
Desarrolla la reserva de `08_MOS_ARQUITECTURA_COMPLETA.md`. Prerrequisito: V1.1.
Se apoya en MemoryType.PROJECT (interfaces.py), WPMS (V0.87) y el aislamiento
C-1b (doc 25). Redactado 2026-07-21.*
