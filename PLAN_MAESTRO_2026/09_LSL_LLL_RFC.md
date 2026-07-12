# 09 — RFC: Local Skill Library (LSL) y Local Learning Loop (LLL)

> **Origen**: `FABLE5_PROMPTS/PROMPT_05_LOCAL_LEARNING_LOOP.md`. Corrige la laguna de
> PROMPT_03: las Capas 3 y 4 del MOS existen en versión LOCAL, siempre, sin red.
> **Principio rector**: Aithera sin red debe ser tan inteligente como con red para un
> solo usuario. La GSN/CIE (V2.0+) amplifican; nunca son prerrequisito.
>
> Incorporación: LLL básico en **V1.0**, LSL completa en **V1.1**, sync GSN en V2.0+.
> El stub de V0.85 (`stores/skill_store.py`, doc 07) usa YA estos contratos.
>
> **Δ 2026-07-12**: este RFC queda EXTENDIDO por el doc 15 (Aithera Learning
> System): el LLL de aquí es su núcleo analítico; la evolución de skills
> (merge/split/specialize + `skill_events`) está en 15 §6 y la cuarentena de
> validación en 15 §3. `LocalSkill` gana 2 campos de linaje (marcados `[Δ]` abajo)
> que el stub de V0.85 ya debe incluir en su metadata.

---

## 1. Local Skill Library

### 1.1 Contrato `LocalSkill` (congelado — es el mismo de la futura GSN)

```python
@dataclass
class LocalSkill:
    id: str                    # UUID
    name: str
    version: str               # semver "1.0.0"
    description: str
    definition: dict           # instrucciones/prompt/workflow (runtime-agnostic)
    input_schema: dict         # JSON Schema
    output_schema: dict
    runtime_agnostic: bool     # True = ejecutable por cualquier AgentRuntime

    # Provenance (idéntico al de la GSN, pero local)
    created_by: str            # "hermes_detection" | "user" | "local_learning_loop"
    created_at: datetime
    evidence_count: int        # ejecuciones con éxito
    last_used: datetime | None
    use_count: int

    # Calidad (las alimenta el LLL)
    status: SkillStatus        # DRAFT|VALIDATED|LOCAL|PROPOSED|DEPRECATED
    quality_score: float       # 0-1
    error_rate: float          # % ejecuciones fallidas

    # Linaje [Δ 2026-07-12 — Skill Evolution, doc 15 §6]
    derived_from: list[str]    # ids de skills origen (merge/split/specialize); [] normal
    superseded_by: str | None  # id del reemplazo cuando status=DEPRECATED

    # Contexto
    projects: list[str]
    tags: list[str]

    # Sincronización GSN (V2.0+; None hasta entonces)
    gsn_id: str | None
    gsn_version: str | None
    gsn_last_sync: datetime | None
```

Persistencia: tabla PostgreSQL `skills` (fuente de verdad; una migración en V1.1)
+ espejo semántico en `mem_skill` (búsqueda por descripción). En V0.85-V1.0 el
stub guarda solo en `mem_skill` con el MISMO shape en metadata — la migración a
tabla en V1.1 es un backfill mecánico, no un rediseño.

### 1.2 Ciclo de vida

```
DETECTED → DRAFT → VALIDATED → LOCAL ──(usuario decide publicar)──▶ PROPOSED_TO_GSN → GLOBAL
                     ▲                                                   (V2.0+)
   [3 ejecuciones OK las valida el LLL automáticamente,
    o el usuario valida a mano — mismo patrón de autonomía
    gradual que las reglas de email (propose→auto, V0.7.3)]
```

`LOCAL` es el estado de reposo normal. `DEPRECATED` cuando el LLL detecta calidad
bajo umbral y existe reemplazo (nunca se borra: se archiva con historia). Las
operaciones de evolución — improve/split/merge/specialize/deprecate, todas como
propuestas del Learner con cuarentena — están especificadas en el doc 15 §6; el
linaje se reconstruye por `derived_from`/`superseded_by`.

### 1.3 Servicio `LocalSkillLibrary` (V1.1)

`app/skills/library.py` — operaciones: `create/get/list/execute/improve/validate/
deprecate` (implementa la Skill API de 08 RFC-002). Ejecución: una skill es un
workflow declarativo que corre a través del `AgentRuntime` activo con las tools de
Aithera (whitelist + approval gates SIEMPRE; una skill jamás ejecuta nada directo).
**Performance** (doc 12): skills `LOCAL`/`VALIDATED` cacheadas en memoria al
arrancar (<5KB c/u), invalidación al modificar; `execute()` local < 100 ms de
overhead sobre la tarea en sí.

## 2. Local Learning Loop

### 2.1 Qué es

El motor de inteligencia personal: analiza lo que Aithera ya sabe del usuario
(conversaciones, traces, errores, decisiones) para detectar patrones, proponer
skills y mejorar las existentes. Corre 100% local.

### 2.2 Los 5 análisis (algoritmos de diseño)

| # | Análisis | Entrada | Método | Salida |
|---|---|---|---|---|
| 1 | **Tareas repetidas** | `orchestrator_traces` + `mem_conversational` (30 días) | clustering por similitud de embeddings de la instrucción; cluster ≥ MIN_REP (3) → candidato | propuesta de skill (DRAFT) con plantilla extraída de los ejemplos |
| 2 | **Patrones de error** | `mem_error` | agrupación por firma (tipo+contexto); ≥3 repeticiones | skill preventiva o nota en briefing |
| 3 | **Skills transferibles** | `skills.projects` + actividad por proyecto | skill con éxito en proyecto A + proyecto B con tags/stack similar | sugerencia "añadir X a proyecto B" |
| 4 | **Calidad de skills** | ejecuciones (evidence/error_rate) | recálculo de quality_score = f(éxitos, recencia, feedback); umbral < 0.6 → analizar patrón de fallo | propuesta de mejora/split/deprecación |
| 5 | **Briefing de aprendizaje** | resultados 1-4 | plantilla semanal | "esta semana: 1 skill nueva, error_rate de X mejoró 0.28→0.09, patrón detectado..." |

Todas las propuestas son **no bloqueantes** (notificación suave en el Hub) y HITL:
el LLL propone, el usuario dispone — coherente con la autonomía gradual del email.

### 2.3 Ejecución (restricciones duras)

- Background task asyncio (V1.0) → job APScheduler (desde V0.9 existe scheduler).
- **Ciclo completo cada 6 h** (configurable) + micro-análisis post-conversación
  (encolado, no en el request) + análisis urgente si 3 errores iguales en sesión.
- **Micro-batch ≤ 50 items/ciclo**, prioridad idle, ≤ 3% CPU: el usuario no lo nota.
- Cada ciclo escribe `MemoryJobRun(job_name="lll_cycle")` — auditable como la ingesta.
- LLM: Ollama-first (coste 0), mismo esquema de degradación que el summarizer.

### 2.4 Incorporación por versión

| Versión | LLL |
|---|---|
| V1.0 | análisis 1 (tareas repetidas sobre traces) + propuesta de skill básica |
| V1.1 | análisis 2-5 completos + quality_score alimentando la LSL + panel "Lo que Aithera ha aprendido" en el Hub |
| V1.2+ | análisis predictivo (pre-cargar la skill que vas a necesitar) |

## 3. Sincronización LSL ↔ GSN (V2.0+, opcional)

- **Subida**: selección automática de candidatas (`LOCAL`, quality > 0.85,
  evidence > 10) → `PrivacyFilter` tipado (08 RFC-001: solo `PortableSkill`, sin
  texto personal) → **revisión explícita del usuario** (nunca automático) →
  proceso de Guardians de la GSN.
- **Descarga**: el LLL detecta necesidad ("ejecutas mucho SQL") → ofrece skills GSN
  relevantes → entran como `LOCAL` sin validar → el LLL las promociona a
  `VALIDATED` si funcionan (la confianza se gana, también para skills ajenas).
- **Bidireccional con el CIE**: el LLL puede publicar PATRONES anonimizados (no
  datos) y recibir insights globales que contrastan con el patrón local.

## 4. Mapa local vs global

| Componente | V0.85 | V1.0 | V1.1 | V2.0+ |
|---|---|---|---|---|
| Skill Memory básico (stub con contratos LSL) | ✅ | ✅ | — | — |
| LSL completa (tabla, ciclo de vida, métricas) | — | — | ✅ | ✅ |
| LLL básico (análisis 1) | — | ✅ | ✅ | ✅ |
| LLL completo (análisis 2-5 + panel Hub) | — | — | ✅ | ✅ |
| Sync GSN / contribución CIE | — | — | — | ✅ opcional |

---
*Diseño 2026-07-09 (Fable 5). Los contratos de LocalSkill se prefiguran en el stub
de V0.85 (doc 07) y son los mismos que usará la GSN (doc 08 RFC-004).*
